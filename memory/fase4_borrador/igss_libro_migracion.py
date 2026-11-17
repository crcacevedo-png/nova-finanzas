# /app/backend/routes/igss_libro_migracion.py
# Libro de órdenes IGSS — Fase 4, paso (a): SIMULACIÓN de la migración (solo lectura).
# Calcula qué órdenes (No. SPS) pasarían al libro y con qué atenciones, qué casos irían a
# "atenciones sin orden" para revisión manual y cuánto historial antiguo se ignora.
# No escribe en ninguna colección de datos; solo deja un registro en audit_logs.
# Criterio por contrato, nunca por año calendario. Nunca se inventa un No. SPS.

import io
import re
import uuid
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from config.database import db
from config.permissions import LIBRO_IGSS_ROLES
from routes.auth import require_role
from routes.igss_libro import normalizar_sps
from routes.igss_libro_lecturas import (ESTADOS_PROD, _anchos, _descarga, _encabezado, _fila_titulos, _modalidad,
                                        _si, contadores_libro, fmt_fecha)
from routes.igss_nogs import _BORRADOR_PROJ, es_texto_baja_cuantia, etiqueta_catalogo, eval_es_borrador_vacio, norm_txt
from utils.timezone import GUATEMALA_TZ, now_gt

router = APIRouter(prefix="/igss-units/migracion", tags=["IGSS - Libro (migración)"])

FECHA_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Orígenes de acreditación cuya fecha es la del ingreso real de la orden (no un recálculo).
ORIGENES_INGRESO = ("asignacion", "reasignacion", "evaluacion")
ETIQUETAS = {"cupo_sin_sps": "Cupo descontado sin SPS", "evaluacion": "Evaluación sin orden", "cirugia": "Cirugía sin orden"}
SIN_ATENCION = "Sin atención (queda pendiente)"
CRITERIOS = [
    "Se migra toda orden con unidad IGSS, No. SPS y entrada del catálogo (NOG o Baja Cuantía), de cualquier año, "
    "incluidas las de entradas inactivas o completas. Nunca se crea una orden con No. SPS vacío, provisional o inventado.",
    "Atenciones de cada orden: evaluaciones reales y cirugías realizadas con fecha igual o posterior a la fecha de "
    "asignación de su entrada del catálogo; si la entrada no la tiene, la fecha de ingreso de la orden; si tampoco "
    "existe, se incluyen todas y la orden queda marcada 'Revisar fecha'.",
    "Fecha de ingreso de una orden anterior al libro: la de su acreditación (asignación, reasignación o evaluación). "
    "Las acreditaciones de recálculos no se usan como fecha de ingreso.",
    "Sin No. SPS, sin contrato o con conflicto: va a la lista de revisión manual ('atenciones sin orden'). Las "
    "acreditaciones vigentes sin No. SPS van a esa lista como 'Cupo descontado sin SPS'.",
    "Historial ignorado (solo se cuenta): atenciones anteriores al contrato y evaluaciones de pacientes que aún no "
    "tenían unidad IGSS en esa fecha (antes de su primer registro IGSS: acreditación, orden o atención con datos IGSS).",
    "Pendientes de SPS no suman a consumidos ni a reservados. Los contadores son acumulados desde el inicio del contrato.",
]

_PAC_PROJ = {"_id": 0, "id": 1, "record_number": 1, "first_name": 1, "last_name": 1, "igss_afiliacion": 1,
             "igss_unit_id": 1, "igss_ordenes": 1, "igss_nog": 1, "igss_no_sps": 1, "igss_codigo": 1,
             "is_active": 1, "referral_institution": 1, "created_at": 1}
_EV_PROJ = {**_BORRADOR_PROJ, "igss_no_sps": 1, "igss_codigo": 1, "igss_nog_id": 1, "igss_orden_id": 1}
_CX_PROJ = {"_id": 0, "id": 1, "patient_id": 1, "patient_name": 1, "date": 1, "status": 1, "procedure": 1,
            "surgeon": 1, "igss_data": 1, "igss_orden_id": 1}


def _dia(v) -> str:
    s = str(v or "")[:10]
    return s if FECHA_RX.match(s) else ""


def _dia_gt(iso) -> str:
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return _dia(iso)
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(GUATEMALA_TZ).strftime("%Y-%m-%d")


def _nombre(p: dict) -> str:
    return f"{(p or {}).get('first_name', '')} {(p or {}).get('last_name', '')}".strip()


def _min(fechas) -> str:
    validas = [f for f in fechas if f]
    return min(validas) if validas else ""


def _ordenes_legado(p: dict) -> list:
    ords = [o for o in (p.get("igss_ordenes") or []) if isinstance(o, dict)]
    if not ords and (p.get("igss_nog") or p.get("igss_no_sps")):
        ords = [{"id": f"{p['id']}_ord1", "nog": p.get("igss_nog"), "no_sps": p.get("igss_no_sps"),
                 "codigo": p.get("igss_codigo"), "procedimiento": ""}]
    return ords


class Catalogo:
    """Entradas del catálogo por id, por (unidad, número) y Baja Cuantía sin número por unidad."""

    def __init__(self, nogs: list):
        self.por_id = {n["id"]: n for n in nogs}
        self.por_numero = {(n.get("unidad_id", ""), normalizar_sps(n.get("numero"))): n
                           for n in nogs if (n.get("numero") or "").strip()}
        self.bc, self.inicio_unidad = {}, {}
        for n in nogs:
            u = n.get("unidad_id", "")
            if not (n.get("numero") or "").strip():
                self.bc.setdefault(u, []).append(n)
            f = _dia(n.get("fecha_asignacion"))
            if f and (u not in self.inicio_unidad or f < self.inicio_unidad[u]):
                self.inicio_unidad[u] = f

    def resolver(self, unidad_id: str, nog_id: str = "", numero: str = "", servicio: str = ""):
        """(entrada, motivo): la entrada del catálogo de una orden, o por qué no se encontró."""
        if nog_id and nog_id in self.por_id:
            return self.por_id[nog_id], None
        numero = (numero or "").strip()
        if not numero:
            return None, "Sin NOG indicado"
        if not es_texto_baja_cuantia(numero):
            n = self.por_numero.get((unidad_id, normalizar_sps(numero)))
            return (n, None) if n else (None, f"El NOG {numero} no está en el catálogo de la unidad")
        bcs = self.bc.get(unidad_id, [])
        if len(bcs) == 1:
            return bcs[0], None
        hint = norm_txt(servicio)
        cand = [n for n in bcs if hint and (n.get("nombre_servicio_norm") or norm_txt(n.get("nombre_servicio"))) in hint]
        if len(cand) == 1:
            return cand[0], None
        if not bcs:
            return None, "La unidad no tiene entrada de Baja Cuantía en el catálogo"
        return None, f"Baja Cuantía: la unidad tiene {len(bcs)} entradas y no se pudo identificar cuál"


class Simulacion:
    """Cruza órdenes del paciente, acreditaciones, evaluaciones, cirugías y el libro actual."""

    def __init__(self, d: dict):
        self.cat = Catalogo(d["nogs"])
        self.pacs = d["pacientes"]
        self.prod = d["prod"]
        self.sin_orden = d["sin_orden"]
        self.libro_por_id = {o["id"]: o for o in d["libro"]}
        self.libro_por_clave = {(o["unidad_id"], o["no_sps"]): o for o in d["libro"]}
        self.en_libro = {(a.get("tipo"), a.get("ref_id")) for o in d["libro"] for a in o.get("atenciones") or []}
        self.cands, self.por_pac_sps, self.legado_por_id, self.legado_por_nog = {}, {}, {}, {}
        self.entradas_pac, self.inicio_igss = {}, {}
        self.sueltas, self.manual, self.no_migrables, self.migrables, self.ya_en_libro = [], [], [], [], []
        self.hist = Counter()
        for o in d["libro"]:
            self.aportar(o["unidad_id"], o["no_sps"], o.get("paciente_id"), "libro")
            self.evidencia(o.get("paciente_id"), _dia(o.get("fecha_ingreso")))

    # ---------- fuentes ----------

    def evidencia(self, pid, dia):
        if pid and dia and (pid not in self.inicio_igss or dia < self.inicio_igss[pid]):
            self.inicio_igss[pid] = dia

    def aportar(self, unidad_id, sps, pid, fuente, entrada=None, motivo=None, codigo="", proc="", ingreso=""):
        unidad_id = (entrada or {}).get("unidad_id") or unidad_id or ""
        key = (unidad_id, sps)
        c = self.cands.setdefault(key, {
            "unidad_id": unidad_id, "no_sps": sps, "pacientes": set(), "entradas": {}, "motivos": [], "codigo": "",
            "procedimiento": "", "fuentes": set(), "ingresos": [], "evaluaciones": [], "cirugias": [], "cx_vinculadas": 0})
        if pid:
            c["pacientes"].add(pid)
            self.por_pac_sps.setdefault((pid, sps), set()).add(key)
        c["fuentes"].add(fuente)
        if entrada:
            c["entradas"][entrada["id"]] = entrada
        elif motivo:
            c["motivos"].append(motivo)
        c["codigo"] = c["codigo"] or (codigo or "").strip()
        c["procedimiento"] = c["procedimiento"] or (proc or "").strip()
        if ingreso:
            c["ingresos"].append(ingreso)
        return c

    def cand_de(self, pid, unidad, sps, fuente, entrada, motivo, codigo="", proc=""):
        """Orden ya conocida del paciente con ese No. SPS (prefiere su unidad) o una nueva."""
        keys = sorted(self.por_pac_sps.get((pid, sps)) or [])
        if keys:
            return self.cands[next((k for k in keys if k[0] == unidad), keys[0])]
        return self.aportar(unidad, sps, pid, fuente, entrada, motivo, codigo, proc)

    def ordenes_pacientes(self):
        for p in self.pacs.values():
            if p.get("referral_institution") != "igss":
                continue
            unidad = p.get("igss_unit_id") or ""
            for o in _ordenes_legado(p):
                sps, numero = normalizar_sps(o.get("no_sps")), (o.get("nog") or "").strip()
                entrada, motivo = self.cat.resolver(unidad, o.get("nog_id") or "", numero, o.get("procedimiento"))
                self.legado_por_id[o.get("id")] = (p["id"], sps)
                if entrada:
                    self.entradas_pac.setdefault(p["id"], []).append(entrada)
                if not sps:
                    self.no_migrables.append(self._fila_nm(unidad, "", [p["id"]], [entrada] if entrada else [],
                                                           "Orden del paciente sin No. SPS", ["orden del paciente"]))
                    continue
                if numero:
                    self.legado_por_nog.setdefault((p["id"], normalizar_sps(numero)), set()).add(sps)
                self.aportar(unidad, sps, p["id"], "orden del paciente", entrada, motivo, o.get("codigo"), o.get("procedimiento"))

    def acreditaciones(self, acreds):
        for a in acreds:
            pid, dia = a.get("paciente_id") or "", _dia_gt(a.get("fecha_acreditacion"))
            self.evidencia(pid, dia)
            if a.get("anulada") is True:
                continue
            entrada, sps = self.cat.por_id.get(a.get("nog_id")), normalizar_sps(a.get("no_sps"))
            if not sps:
                self.manual.append(self._item("cupo_sin_sps", a.get("id"), pid, entrada, dia, "Cupo descontado sin SPS",
                                              unidad=a.get("unidad_id"), nombre=a.get("paciente_nombre")))
                continue
            self.aportar(a.get("unidad_id"), sps, pid, "acreditación", entrada,
                         None if entrada else "La acreditación apunta a una entrada que ya no está en el catálogo",
                         ingreso=dia if a.get("origen") in ORIGENES_INGRESO else "")

    def _atencion(self, tipo, ref, pid, fecha, medico, proc):
        return {"tipo": tipo, "ref_id": ref, "paciente_id": pid, "fecha": fecha, "medico": medico or "",
                "procedimiento": (proc or "")[:120], "en_sin_orden": (tipo, ref) in self.sin_orden}

    def _orden_libro(self, orden_id, pid):
        o = self.libro_por_id.get(orden_id or "")
        return self.cands[(o["unidad_id"], o["no_sps"])] if o and o.get("paciente_id") == pid else None

    def _orden_de_evaluacion(self, ev, p):
        pid, unidad = p["id"], p.get("igss_unit_id") or ""
        entrada, motivo_cat = self.cat.resolver(unidad, ev.get("igss_nog_id") or "", ev.get("igss_nog") or "",
                                                ev.get("igss_procedimiento"))
        c = self._orden_libro(ev.get("igss_orden_id"), pid)
        if c:
            return c, None, entrada
        sps = normalizar_sps(ev.get("igss_no_sps"))
        leg = self.legado_por_id.get(ev.get("igss_orden_id") or "")
        if not sps and leg and leg[0] == pid:
            sps = leg[1]
        numero = (ev.get("igss_nog") or "").strip()
        if not sps and numero:
            opciones = self.legado_por_nog.get((pid, normalizar_sps(numero))) or set()
            if len(opciones) > 1:
                return None, f"El paciente tiene {len(opciones)} órdenes del NOG {numero} y la evaluación no indica cuál", entrada
            sps = next(iter(opciones), "")
        if not sps:
            return None, "Evaluación sin No. SPS", entrada
        return self.cand_de(pid, unidad, sps, "evaluación", entrada, motivo_cat, ev.get("igss_codigo"),
                            ev.get("igss_procedimiento")), None, entrada

    def evaluaciones(self, evals):
        for ev in evals:
            p = self.pacs.get(ev.get("paciente_id"))
            if not p or p.get("referral_institution") != "igss" or eval_es_borrador_vacio(ev):
                continue
            fecha = _dia(ev.get("fecha"))
            if (ev.get("igss_nog") or "").strip() or (ev.get("igss_no_sps") or "").strip():
                self.evidencia(p["id"], fecha)
            if ("evaluacion", ev["id"]) in self.en_libro:
                continue
            at = self._atencion("evaluacion", ev["id"], p["id"], fecha, ev.get("medico_nombre"),
                                ev.get("igss_procedimiento") or ev.get("motivo_consulta"))
            c, motivo, entrada = self._orden_de_evaluacion(ev, p)
            if c:
                c["evaluaciones"].append(at)
            else:
                self.sueltas.append((at, entrada, motivo))

    def cirugias(self, cxs):
        for cx in cxs:
            if cx.get("status") == "cancelado":
                continue
            g, pid = cx.get("igss_data") or {}, cx.get("patient_id") or ""
            p = self.pacs.get(pid) or {}
            unidad, fecha = g.get("unit_id") or p.get("igss_unit_id") or "", _dia(cx.get("date"))
            realizada = cx.get("status") == "realizado"
            self.evidencia(pid, fecha)
            if realizada and ("cirugia", cx["id"]) in self.en_libro:
                continue
            entrada, motivo_cat = self.cat.resolver(unidad, g.get("nog_id") or "", g.get("nog_number") or "", cx.get("procedure"))
            sps, motivo = normalizar_sps(g.get("sps")), None
            c = self._orden_libro(cx.get("igss_orden_id"), pid) if pid else None
            if c is None:
                if not pid:
                    motivo = "Cirugía sin paciente registrado"
                elif not sps:
                    motivo = "Cirugía sin No. SPS"
                else:
                    c = self.cand_de(pid, unidad, sps, "cirugía", entrada, motivo_cat, g.get("code"), cx.get("procedure"))
            at = self._atencion("cirugia", cx["id"], pid, fecha, cx.get("surgeon"), cx.get("procedure"))
            at["paciente_nombre"] = cx.get("patient_name", "")
            if c:
                c["cx_vinculadas"] += 1
                if realizada:
                    c["cirugias"].append(at)
            elif realizada:
                self.sueltas.append((at, entrada, motivo))

    # ---------- clasificación ----------

    def _problema(self, key, c):
        if not c["pacientes"]:
            return "Sin paciente"
        if len(c["pacientes"]) > 1:
            return f"El No. SPS {c['no_sps']} aparece en {len(c['pacientes'])} pacientes distintos"
        libro = self.libro_por_clave.get(key)
        if libro:
            return "libro" if libro.get("paciente_id") in c["pacientes"] else (
                f"El No. SPS ya está en el libro para otro paciente ({libro.get('paciente_nombre', '')})")
        if not c["unidad_id"]:
            return "Paciente sin unidad IGSS"
        if not c["entradas"]:
            return c["motivos"][0] if c["motivos"] else "Sin entrada del catálogo"
        if len(c["entradas"]) > 1:
            return "El No. SPS está en dos entradas del catálogo: " + ", ".join(
                sorted(etiqueta_catalogo(e) for e in c["entradas"].values()))
        return None

    def _ref_contrato(self, entrada, pid=""):
        """Fecha de inicio del contrato: la de la entrada; si no se conoce, la más antigua de las
        entradas de las órdenes del paciente o, en último caso, de la unidad."""
        if entrada and _dia(entrada.get("fecha_asignacion")):
            return _dia(entrada.get("fecha_asignacion"))
        fechas = [_dia(e.get("fecha_asignacion")) for e in self.entradas_pac.get(pid, [])]
        p = self.pacs.get(pid) or {}
        return _min(fechas) or self.cat.inicio_unidad.get((entrada or {}).get("unidad_id") or p.get("igss_unit_id", ""), "")

    def _filtrar(self, ats, ref):
        if not ref:
            return ats, []
        dentro = [a for a in ats if not a["fecha"] or a["fecha"] >= ref]
        fuera = [a for a in ats if a["fecha"] and a["fecha"] < ref]
        for a in fuera:
            self.hist[f"{a['tipo']}_anterior_contrato"] += 1
        return dentro, fuera

    def _estados(self, evs):
        docs = [self.prod[a["ref_id"]] for a in evs if a["ref_id"] in self.prod]
        est = {k: any(bool(x.get(k)) for x in docs) for k in ESTADOS_PROD}
        con_costo = [x for x in docs if x.get("costo_override") is not None]
        est["costo_override"] = max(con_costo, key=lambda x: x.get("updated_at") or "")["costo_override"] if con_costo else None
        return est

    def clasificar(self):
        for key, c in sorted(self.cands.items()):
            problema = self._problema(key, c)
            if problema == "libro":
                self._ya_en_libro(self.libro_por_clave[key], c)
            elif problema:
                self.no_migrables.append(self._fila_nm(c["unidad_id"], c["no_sps"], c["pacientes"], list(c["entradas"].values()),
                                                       problema, c["fuentes"]))
                entrada = next(iter(c["entradas"].values()), None) if len(c["entradas"]) == 1 else None
                self.sueltas += [(a, entrada, problema) for a in c["evaluaciones"] + c["cirugias"]]
            else:
                self.migrables.append(self._orden(c))
        for at, entrada, motivo in self.sueltas:
            self._revisar(at, entrada, motivo)
        self._ordenes_probables()

    def _ordenes_probables(self):
        """Para cada cupo sin SPS, la orden con SPS del mismo paciente y NOG (si es una sola)."""
        idx = {}
        for o in self.migrables + list(self.libro_por_id.values()):
            idx.setdefault((o.get("paciente_id"), o.get("nog_id")), set()).add(o.get("no_sps"))
        for i in self.manual:
            if i["tipo"] == "cupo_sin_sps":
                ops = sorted(idx.get((i["paciente_id"], i["nog_id"])) or [])
                i["orden_probable"] = ops[0] if len(ops) == 1 else f"{len(ops)} órdenes posibles" if ops else ""

    def _orden(self, c):
        entrada, pid = next(iter(c["entradas"].values())), next(iter(c["pacientes"]))
        ingreso = _min(c["ingresos"])
        asignacion = _dia(entrada.get("fecha_asignacion"))
        ref = asignacion or ingreso
        evs, ev_fuera = self._filtrar(c["evaluaciones"], ref)
        cxs, cx_fuera = self._filtrar(c["cirugias"], ref)
        dentro = sorted(evs + cxs, key=lambda a: a["fecha"])
        tipo = "procedimiento" if c["cx_vinculadas"] else "consulta"
        p = self.pacs.get(pid) or {}
        obs = []
        if entrada.get("is_active") is False:
            obs.append("Entrada del catálogo inactiva")
        if tipo == "procedimiento":
            obs.append("Dosis autorizadas = cirugías realizadas encontradas (mínimo 1); confirmar con la hoja")
        if ev_fuera or cx_fuera:
            obs.append(f"{len(ev_fuera) + len(cx_fuera)} atención(es) anterior(es) al contrato no incluida(s)")
        resueltas = sum(1 for a in dentro if a["en_sin_orden"])
        if resueltas:
            obs.append(f"Resuelve {resueltas} atención(es) que hoy están en 'sin orden'")
        return {
            "unidad_id": entrada.get("unidad_id", ""), "nog_id": entrada["id"], "nog": etiqueta_catalogo(entrada),
            "modalidad": _modalidad(entrada), "no_sps": c["no_sps"], "paciente_id": pid,
            "paciente_nombre": _nombre(p), "expediente": p.get("record_number", ""), "igss_afiliacion": p.get("igss_afiliacion", ""),
            "codigo": c["codigo"], "procedimiento": c["procedimiento"] or entrada.get("nombre_servicio", ""),
            "tipo": tipo, "dosis_autorizadas": max(1, len(cxs)) if tipo == "procedimiento" else 1,
            "estado": "atendida" if dentro else "pendiente", "fecha_ingreso": ingreso,
            "fecha_referencia": ref, "fuente_referencia": "Asignación del NOG" if asignacion else "Ingreso de la orden" if ingreso else "",
            "fecha_primera_atencion": _min(a["fecha"] for a in dentro),
            "evaluaciones": len(evs), "cirugias": len(cxs), "fechas_atenciones": [a["fecha"] for a in dentro],
            "atenciones": [{k: a[k] for k in ("tipo", "ref_id", "fecha", "medico")} for a in dentro],
            "excluidas_anteriores": len(ev_fuera) + len(cx_fuera), "resuelve_sin_orden": resueltas,
            "revisar_fecha": not ref, "solo_anteriores": bool((ev_fuera or cx_fuera) and not dentro),
            "fuentes": sorted(c["fuentes"]), "precio": float(entrada.get("precio") or 0),
            **self._estados(c["evaluaciones"]), "observaciones": obs,
        }

    def _ya_en_libro(self, o, c):
        entrada = self.cat.por_id.get(o.get("nog_id"))
        ref = _dia((entrada or {}).get("fecha_asignacion")) or _dia(o.get("fecha_ingreso"))
        evs, _ = self._filtrar(c["evaluaciones"], ref)
        cxs, _ = self._filtrar(c["cirugias"], ref)
        if not evs and not cxs:
            return
        self.ya_en_libro.append({
            "orden_id": o["id"], "unidad_id": o.get("unidad_id", ""), "nog_id": o.get("nog_id", ""),
            "nog": etiqueta_catalogo(entrada) if entrada else o.get("numero_nog", ""), "no_sps": o.get("no_sps", ""),
            "paciente_id": o.get("paciente_id", ""), "paciente_nombre": o.get("paciente_nombre", ""),
            "expediente": o.get("paciente_expediente", ""), "estado_actual": o.get("estado", ""),
            "estado_resultante": "atendida", "evaluaciones_a_agregar": len(evs), "cirugias_a_agregar": len(cxs),
            "fechas_atenciones": sorted(a["fecha"] for a in evs + cxs),
            "atenciones": [{k: a[k] for k in ("tipo", "ref_id", "fecha", "medico")} for a in evs + cxs]})

    def _revisar(self, at, entrada, motivo):
        pid, fecha = at["paciente_id"], at["fecha"]
        ref = self._ref_contrato(entrada, pid)
        if ref and fecha and fecha < ref:
            self.hist[f"{at['tipo']}_anterior_contrato"] += 1
            return
        inicio = self.inicio_igss.get(pid) or _dia_gt((self.pacs.get(pid) or {}).get("created_at"))
        if at["tipo"] == "evaluacion" and inicio and fecha and fecha < inicio:
            self.hist["evaluacion_sin_unidad"] += 1
            return
        item = self._item(at["tipo"], at["ref_id"], pid, entrada, fecha, motivo, procedimiento=at["procedimiento"],
                          medico=at["medico"], revisar=not ref, nombre=at.get("paciente_nombre", ""))
        item["ya_en_lista"] = at["en_sin_orden"]
        self.manual.append(item)

    def _item(self, tipo, ref_id, pid, entrada, fecha, motivo, unidad="", procedimiento="", medico="", revisar=False, nombre=""):
        p = self.pacs.get(pid) or {}
        return {"tipo": tipo, "etiqueta": ETIQUETAS[tipo], "ref_id": ref_id or "", "paciente_id": pid or "",
                "paciente_nombre": _nombre(p) or nombre or "", "expediente": p.get("record_number", ""),
                "unidad_id": (entrada or {}).get("unidad_id") or unidad or p.get("igss_unit_id", ""),
                "nog_id": (entrada or {}).get("id", ""), "nog": etiqueta_catalogo(entrada) if entrada else "",
                "fecha": fecha, "procedimiento": procedimiento, "medico": medico, "motivo": motivo,
                "revisar_fecha": revisar, "ya_en_lista": False, "orden_probable": ""}

    def _fila_nm(self, unidad, sps, pids, entradas, motivo, fuentes):
        return {"unidad_id": unidad or "", "no_sps": sps,
                "pacientes": sorted(_nombre(self.pacs.get(x)) or x for x in pids),
                "expedientes": sorted((self.pacs.get(x) or {}).get("record_number", "") for x in pids),
                "nogs": sorted(etiqueta_catalogo(e) for e in entradas), "motivo": motivo, "fuentes": sorted(fuentes)}


async def _cargar() -> dict:
    """Carga cada colección una sola vez (proyección mínima). Solo lectura."""
    nogs = await db.igss_nogs.find({}, {"_id": 0}).to_list(None)
    acreds = await db.igss_nog_acreditaciones.find({}, {"_id": 0}).to_list(None)
    cxs = await db.surgeries.find({"institution": "IGSS"}, _CX_PROJ).to_list(None)
    pacs = {p["id"]: p for p in await db.patients.find({"referral_institution": "igss"}, _PAC_PROJ).to_list(None)}
    faltan = list({x for x in [a.get("paciente_id") for a in acreds] + [c.get("patient_id") for c in cxs] if x and x not in pacs})
    if faltan:
        pacs.update({p["id"]: p for p in await db.patients.find({"id": {"$in": faltan}}, _PAC_PROJ).to_list(None)})
    ids_igss = [pid for pid, p in pacs.items() if p.get("referral_institution") == "igss"]
    evals = await db.evaluaciones_oftalmologicas.find({"paciente_id": {"$in": ids_igss}}, _EV_PROJ).to_list(None)
    prod = {x["evaluacion_id"]: x for x in await db.igss_produccion.find(
        {"evaluacion_id": {"$in": [e["id"] for e in evals]}}, {"_id": 0}).to_list(None)}
    libro = await db.igss_ordenes_libro.find({"vigente": True}, {"_id": 0}).to_list(None)
    sin_orden = {(x.get("tipo"), x.get("ref_id")) async for x in db.igss_atenciones_sin_orden.find(
        {"estado": "pendiente"}, {"_id": 0, "tipo": 1, "ref_id": 1})}
    units = {u["id"]: u.get("name", "") for u in await db.igss_units.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(None)}
    return {"nogs": nogs, "acreds": acreds, "cxs": cxs, "pacientes": pacs, "evals": evals, "prod": prod,
            "libro": libro, "sin_orden": sin_orden, "units": units}


def _resumen_nog(s: Simulacion, nogs: list, cont: dict, units: dict) -> list:
    a_migrar, pasan, pend_sps = Counter(), Counter(), Counter(i["nog_id"] for i in s.manual)
    for o in s.migrables:
        a_migrar[(o["nog_id"], o["estado"])] += 1
    for o in s.ya_en_libro:
        if o["estado_actual"] == "pendiente":
            pasan[o["nog_id"]] += 1
    filas = []
    for n in nogs:
        c = cont.get(n["id"], {})
        tope = not n.get("sin_tope") and int(n.get("cantidad") or 0) > 0
        consumidos = int(c.get("consumidos", 0)) + a_migrar[(n["id"], "atendida")] + pasan[n["id"]]
        reservados = int(c.get("reservados", 0)) + a_migrar[(n["id"], "pendiente")] - pasan[n["id"]]
        cantidad = int(n.get("cantidad") or 0)
        filas.append({
            "nog_id": n["id"], "unidad_id": n.get("unidad_id", ""), "unidad": units.get(n.get("unidad_id", ""), ""),
            "nog": etiqueta_catalogo(n), "modalidad": _modalidad(n), "is_active": n.get("is_active", True) is not False,
            "fecha_asignacion": _dia(n.get("fecha_asignacion")), "sin_tope": not tope, "cantidad": cantidad if tope else None,
            "libro_consumidos": int(c.get("consumidos", 0)), "libro_reservados": int(c.get("reservados", 0)),
            "migrar_atendidas": a_migrar[(n["id"], "atendida")], "migrar_pendientes": a_migrar[(n["id"], "pendiente")],
            "consumidos": consumidos, "reservados": reservados,
            "disponibles": max(cantidad - consumidos - reservados, 0) if tope else None,
            "sobrecupo": max(consumidos + reservados - cantidad, 0) if tope else 0,
            "pendientes_sps": pend_sps[n["id"]], "contador_anterior": int(n.get("acreditados") or 0),
        })
    filas.sort(key=lambda f: (f["unidad"], f["nog"].startswith("Baja"), f["nog"]))
    return filas


async def simular_migracion() -> dict:
    d = await _cargar()
    s = Simulacion(d)
    s.ordenes_pacientes()
    s.acreditaciones(d["acreds"])
    s.evaluaciones(d["evals"])
    s.cirugias(d["cxs"])
    s.clasificar()
    units = d["units"]
    for fila in s.migrables + s.ya_en_libro + s.manual + s.no_migrables:
        fila["unidad"] = units.get(fila.get("unidad_id", ""), "")
    s.migrables.sort(key=lambda o: (o["unidad"], o["nog"], o["fecha_primera_atencion"] or "9", o["no_sps"]))
    s.manual.sort(key=lambda i: (i["unidad"], i["nog"], i["fecha"], i["paciente_nombre"]))
    resumen = _resumen_nog(s, d["nogs"], await contadores_libro(), units)
    anios = Counter((o["fecha_primera_atencion"][:4] or SIN_ATENCION) for o in s.migrables)
    por_anio = [{"anio": a, "ordenes": anios[a]} for a in sorted(anios, key=lambda x: (x == SIN_ATENCION, x))]
    tipos_manual = Counter(i["tipo"] for i in s.manual)
    totales = {
        "ordenes_a_migrar": len(s.migrables),
        "atendidas": sum(1 for o in s.migrables if o["estado"] == "atendida"),
        "pendientes": sum(1 for o in s.migrables if o["estado"] == "pendiente"),
        "evaluaciones_a_registrar": sum(o["evaluaciones"] for o in s.migrables),
        "cirugias_a_registrar": sum(o["cirugias"] for o in s.migrables),
        "revisar_fecha": sum(1 for o in s.migrables if o["revisar_fecha"]),
        "solo_anteriores_al_contrato": sum(1 for o in s.migrables if o["solo_anteriores"]),
        "ordenes_ya_en_libro_con_atenciones_nuevas": len(s.ya_en_libro),
        "atenciones_a_agregar_en_libro": sum(o["evaluaciones_a_agregar"] + o["cirugias_a_agregar"] for o in s.ya_en_libro),
        "no_migrables": len(s.no_migrables),
        "revision_manual": len(s.manual),
        "revision_manual_evaluaciones": tipos_manual["evaluacion"],
        "revision_manual_cirugias": tipos_manual["cirugia"],
        "revision_manual_cupo_sin_sps": tipos_manual["cupo_sin_sps"],
        "revision_manual_sin_nog": sum(1 for i in s.manual if not i["nog_id"]),
        "cupo_sin_sps_con_orden_probable": sum(1 for i in s.manual if i["tipo"] == "cupo_sin_sps" and i["orden_probable"]
                                               and not i["orden_probable"].endswith("posibles")),
        "sin_orden_hoy_resueltas": sum(o["resuelve_sin_orden"] for o in s.migrables),
        "evaluaciones_historicas_ignoradas": s.hist["evaluacion_anterior_contrato"] + s.hist["evaluacion_sin_unidad"],
        "evaluaciones_anteriores_al_contrato": s.hist["evaluacion_anterior_contrato"],
        "evaluaciones_sin_unidad_igss_en_la_fecha": s.hist["evaluacion_sin_unidad"],
        "cirugias_anteriores_al_contrato": s.hist["cirugia_anterior_contrato"],
        "nogs_con_sobrecupo": sum(1 for f in resumen if f["sobrecupo"]),
    }
    return {"generado": now_gt().isoformat(), "solo_lectura": True, "criterios": CRITERIOS, "totales": totales,
            "por_anio": por_anio, "resumen_nog": resumen, "ordenes": s.migrables, "ya_en_libro": s.ya_en_libro,
            "revision_manual": s.manual, "no_migrables": s.no_migrables}


async def _auditar(user: dict, modo: str, totales: dict):
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "LIBRO_MIGRACION_SIMULADA", "user_id": user.get("id", ""),
        "user_name": user.get("name") or user.get("username", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(), "details": {"modo": modo, "totales": totales}})


# ==================== EXCEL ====================

def _tabla(ws, r, titulos, filas):
    _fila_titulos(ws, r, titulos)
    for fila in filas:
        r += 1
        for c, v in enumerate(fila, 1):
            ws.cell(row=r, column=c, value=v)
    _anchos(ws, len(titulos))
    return r


def _fechas(lst):
    return ", ".join(fmt_fecha(f) for f in lst if f)


def _hoja_resumen(ws, sim):
    t = sim["totales"]
    r = _encabezado(ws, [("Simulación de migración al Libro de órdenes IGSS", "SOLO LECTURA: no se aplicó ningún cambio"),
                         ("Generado", fmt_fecha(sim["generado"]) + " " + sim["generado"][11:16])])
    filas = [
        ("Órdenes a migrar", t["ordenes_a_migrar"]), ("  · quedarían atendidas (consumen cupo)", t["atendidas"]),
        ("  · quedarían pendientes (reservan cupo)", t["pendientes"]),
        ("Evaluaciones a registrar como atención", t["evaluaciones_a_registrar"]),
        ("Cirugías realizadas a registrar como dosis", t["cirugias_a_registrar"]),
        ("Órdenes marcadas 'Revisar fecha'", t["revisar_fecha"]),
        ("Órdenes con solo atenciones anteriores al contrato", t["solo_anteriores_al_contrato"]),
        ("Órdenes que ya están en el libro y recibirían atenciones", t["ordenes_ya_en_libro_con_atenciones_nuevas"]),
        ("Atenciones a agregar en órdenes que ya están en el libro", t["atenciones_a_agregar_en_libro"]),
        ("Órdenes no migrables", t["no_migrables"]),
        ("Casos para revisión manual (atenciones sin orden)", t["revision_manual"]),
        ("  · evaluaciones", t["revision_manual_evaluaciones"]), ("  · cirugías", t["revision_manual_cirugias"]),
        ("  · Cupo descontado sin SPS", t["revision_manual_cupo_sin_sps"]),
        ("  · sin NOG identificado", t["revision_manual_sin_nog"]),
        ("  · cupos sin SPS cuyo paciente tiene una sola orden con SPS de ese NOG", t["cupo_sin_sps_con_orden_probable"]),
        ("Atenciones que hoy están en 'sin orden' y quedarían resueltas", t["sin_orden_hoy_resueltas"]),
        (f"{t['evaluaciones_historicas_ignoradas']} evaluaciones históricas ignoradas", t["evaluaciones_historicas_ignoradas"]),
        ("  · anteriores a la fecha de asignación del contrato", t["evaluaciones_anteriores_al_contrato"]),
        ("  · paciente aún sin unidad IGSS en esa fecha", t["evaluaciones_sin_unidad_igss_en_la_fecha"]),
        ("Cirugías anteriores al contrato ignoradas", t["cirugias_anteriores_al_contrato"]),
        ("Entradas del catálogo que quedarían sobre su cupo", t["nogs_con_sobrecupo"]),
    ]
    r = _tabla(ws, r, ["Concepto", "Cantidad"], filas) + 2
    r = _tabla(ws, r, ["Año de primera atención", "Órdenes a migrar"], [(a["anio"], a["ordenes"]) for a in sim["por_anio"]]) + 2
    _tabla(ws, r, ["Criterios aplicados"], [(c,) for c in sim["criterios"]])
    ws.column_dimensions["A"].width = 70


def simulacion_excel(sim: dict) -> io.BytesIO:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    _hoja_resumen(ws, sim)
    _tabla(wb.create_sheet("Por NOG"), 1, [
        "Unidad", "NOG / Entrada", "Modalidad", "Activo", "Fecha asignación", "Cupos", "Libro hoy: consumidos",
        "Libro hoy: reservados", "Migrar: atendidas", "Migrar: pendientes", "Resultado: consumidos",
        "Resultado: reservados", "Resultado: disponibles", "Pendientes de SPS", "Sobrecupo", "Contador anterior"],
        [(f["unidad"], f["nog"], f["modalidad"], _si(f["is_active"]), fmt_fecha(f["fecha_asignacion"]),
          "Sin tope" if f["sin_tope"] else f["cantidad"], f["libro_consumidos"], f["libro_reservados"],
          f["migrar_atendidas"], f["migrar_pendientes"], f["consumidos"], f["reservados"],
          "Sin tope" if f["sin_tope"] else f["disponibles"], f["pendientes_sps"], f["sobrecupo"], f["contador_anterior"])
         for f in sim["resumen_nog"]])
    _tabla(wb.create_sheet("Órdenes a migrar"), 1, [
        "Unidad", "NOG / Entrada", "Modalidad", "No. SPS", "Paciente", "Expediente", "Tipo", "Dosis autorizadas",
        "Estado resultante", "Fecha ingreso", "Fecha de referencia", "Fuente de la fecha", "Fecha 1ª atención",
        "Evaluaciones", "Cirugías", "Fechas de atenciones", "Anteriores al contrato (no incluidas)", "Revisar fecha",
        "Fuentes", "Precio (Q)", *[e.capitalize() for e in ESTADOS_PROD], "Observaciones"],
        [(o["unidad"], o["nog"], o["modalidad"], o["no_sps"], o["paciente_nombre"], o["expediente"], o["tipo"],
          o["dosis_autorizadas"], o["estado"], fmt_fecha(o["fecha_ingreso"]), fmt_fecha(o["fecha_referencia"]),
          o["fuente_referencia"], fmt_fecha(o["fecha_primera_atencion"]), o["evaluaciones"], o["cirugias"],
          _fechas(o["fechas_atenciones"]), o["excluidas_anteriores"], _si(o["revisar_fecha"]), ", ".join(o["fuentes"]),
          o["precio"], *[_si(o[e]) for e in ESTADOS_PROD], "; ".join(o["observaciones"])) for o in sim["ordenes"]])
    _tabla(wb.create_sheet("Ya en el libro"), 1, [
        "Unidad", "NOG / Entrada", "No. SPS", "Paciente", "Expediente", "Estado actual", "Estado resultante",
        "Evaluaciones a agregar", "Cirugías a agregar", "Fechas"],
        [(o["unidad"], o["nog"], o["no_sps"], o["paciente_nombre"], o["expediente"], o["estado_actual"],
          o["estado_resultante"], o["evaluaciones_a_agregar"], o["cirugias_a_agregar"], _fechas(o["fechas_atenciones"]))
         for o in sim["ya_en_libro"]])
    _tabla(wb.create_sheet("Revisión manual"), 1, [
        "Etiqueta", "Unidad", "NOG / Entrada", "Paciente", "Expediente", "Fecha", "Procedimiento", "Médico", "Motivo",
        "Revisar fecha", "Ya en la lista hoy", "Orden probable (mismo paciente y NOG)"],
        [(i["etiqueta"], i["unidad"], i["nog"] or "Sin NOG identificado", i["paciente_nombre"], i["expediente"],
          fmt_fecha(i["fecha"]), i["procedimiento"], i["medico"], i["motivo"], _si(i["revisar_fecha"]), _si(i["ya_en_lista"]),
          i["orden_probable"])
         for i in sim["revision_manual"]])
    _tabla(wb.create_sheet("No migrables"), 1, ["Unidad", "No. SPS", "Paciente(s)", "Expediente(s)", "NOG(s)", "Motivo", "Fuentes"],
           [(n["unidad"], n["no_sps"] or "(vacío)", ", ".join(n["pacientes"]), ", ".join(n["expedientes"]),
             ", ".join(n["nogs"]), n["motivo"], ", ".join(n["fuentes"])) for n in sim["no_migrables"]])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ==================== ENDPOINTS ====================

@router.get("/simular")
async def simular(current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Paso (a): simulación de solo lectura. No crea, edita ni borra ningún dato."""
    sim = await simular_migracion()
    await _auditar(current_user, "json", sim["totales"])
    return sim


@router.get("/simular/excel")
async def simular_excel(current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    sim = await simular_migracion()
    await _auditar(current_user, "excel", sim["totales"])
    return _descarga(simulacion_excel(sim), f"simulacion_migracion_libro_igss_{sim['generado'][:10]}.xlsx")
