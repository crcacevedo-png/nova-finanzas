# /app/backend/routes/igss_libro_migracion.py
# Libro de órdenes IGSS — Fase 4, paso (a): SIMULACIÓN de la migración. SOLO LECTURA: no
# escribe en ninguna colección (tampoco auditoría). Exclusivo de superadmin.
# Criterio por contrato, nunca por año calendario; contadores acumulados; nunca se inventa
# un No. SPS. Unidades duplicadas = advertencia. Un mismo No. SPS vigente en dos unidades
# duplicadas = BLOQUEO: la aplicación (paso b) se negará mientras exista alguno.

import io
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from config.database import db
from routes.auth import require_role
from routes.igss_libro import normalizar_sps
from routes.igss_libro_lecturas import (ESTADOS_PROD, _anchos, _descarga, _encabezado, _fila_titulos, _modalidad,
                                        _nombre_archivo, contadores_libro, fmt_fecha)
from routes.igss_nogs import _BORRADOR_PROJ, es_texto_baja_cuantia, etiqueta_catalogo, eval_es_borrador_vacio, norm_txt
from utils.timezone import GUATEMALA_TZ, now_gt

router = APIRouter(prefix="/igss-units/migracion", tags=["IGSS - Libro (migración)"])
SOLO_SUPERADMIN = require_role(["superadmin"])

FECHA_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Orígenes de acreditación cuya fecha es la del ingreso real de la orden (no un recálculo).
ORIGENES_INGRESO = ("asignacion", "reasignacion", "evaluacion")
SIN_ATENCION = "Sin atención (queda pendiente)"
SIN_SPS = {"cupo_sin_sps": "Cupo descontado sin SPS", "evaluacion": "Evaluación sin No. SPS",
           "cirugia": "Cirugía sin No. SPS"}
TIPO_CASO = {"orden": "Orden", "evaluacion": "Evaluación", "cirugia": "Cirugía"}
# (inicio del motivo, motivo agrupado, qué falta para poder migrarlo). El orden importa.
REGLAS_MOTIVO = [
    ("Orden del paciente sin No. SPS", "Orden sin No. SPS", "El No. SPS de la hoja de autorización"),
    ("El NOG ", "NOG no está en el catálogo de la unidad",
     "Registrar el NOG en el catálogo de la unidad o corregir el NOG de la orden"),
    ("Sin NOG indicado", "Orden sin NOG", "Indicar el NOG o la entrada de Baja Cuantía de la orden"),
    ("La unidad no tiene entrada de Baja Cuantía", "Unidad sin entrada de Baja Cuantía",
     "Crear la entrada de Baja Cuantía en el catálogo de la unidad"),
    ("Baja Cuantía: la unidad tiene", "Baja Cuantía sin identificar", "Indicar a qué entrada de Baja Cuantía corresponde"),
    ("El No. SPS ya está en el libro", "No. SPS ya usado en el libro por otro paciente",
     "Confirmar a qué paciente pertenece el No. SPS"),
    ("El No. SPS está en dos entradas", "No. SPS en dos entradas del catálogo",
     "Indicar a qué entrada del catálogo corresponde el No. SPS"),
    ("El No. SPS ", "No. SPS en varios pacientes", "Confirmar a qué paciente pertenece el No. SPS y corregir los demás"),
    ("Paciente sin unidad IGSS", "Paciente sin unidad IGSS", "Asignar la unidad IGSS del paciente"),
    ("La acreditación apunta", "Acreditación de una entrada que ya no existe", "Indicar la entrada del catálogo correcta"),
    ("El paciente tiene ", "Evaluación sin orden identificable", "Indicar el No. SPS de la orden que corresponde a la evaluación"),
    ("Cirugía sin paciente", "Cirugía sin paciente", "Vincular la cirugía a un paciente"),
    ("Sin paciente", "Sin paciente", "Identificar al paciente"),
    ("Sin entrada del catálogo", "Sin entrada del catálogo", "Indicar la entrada del catálogo"),
]
CRITERIOS = [
    "Solo lectura: la simulación no crea, edita ni borra ningún dato.",
    "Se migra toda orden con unidad IGSS, No. SPS y entrada del catálogo (NOG o Baja Cuantía), de cualquier año, "
    "incluidas las de entradas inactivas o completas. Nunca se crea una orden con No. SPS vacío, provisional o inventado.",
    "Atenciones de cada orden: evaluaciones reales y cirugías realizadas con fecha igual o posterior a la fecha de "
    "asignación de su entrada del catálogo; si la entrada no la tiene, la fecha de ingreso de la orden; si tampoco "
    "existe, se incluyen todas y la orden queda marcada 'Revisar fecha'.",
    "Fecha de ingreso de una orden anterior al libro: la de su acreditación (asignación, reasignación o evaluación).",
    "Sin No. SPS: la atención o la acreditación vigente va a 'Pendientes de SPS' (no suma a consumidos ni a reservados).",
    "Historial ignorado (solo se cuenta): atenciones anteriores al contrato y evaluaciones de pacientes que aún no "
    "tenían unidad IGSS en esa fecha.",
    "Contadores acumulados desde el inicio del contrato (no se reinician por año). Órdenes agrupadas por el año de su "
    "primera atención.",
    "Unidades con el mismo nombre: advertencia, no impide aplicar. Un mismo No. SPS vigente en dos unidades "
    "duplicadas: bloqueo, la aplicación se negará mientras exista.",
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


def _regla(motivo: str):
    return next(((m, f) for ini, m, f in REGLAS_MOTIVO if motivo.startswith(ini)), (motivo, "Revisar con la hoja física"))


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
        self.libro = d["libro"]
        self.libro_por_id = {o["id"]: o for o in d["libro"]}
        self.libro_por_clave = {(o["unidad_id"], o["no_sps"]): o for o in d["libro"]}
        self.en_libro = {(a.get("tipo"), a.get("ref_id")) for o in d["libro"] for a in o.get("atenciones") or []}
        self.cands, self.por_pac_sps, self.legado_por_id, self.legado_por_nog = {}, {}, {}, {}
        self.entradas_pac, self.inicio_igss = {}, {}
        self.sueltas, self.pac_sin_sps = [], []
        self.pendientes_sps, self.no_migrables, self.migrables, self.ya_en_libro = [], [], [], []
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
            c = self.cands[next((k for k in keys if k[0] == unidad), keys[0])]
            c["fuentes"].add(fuente)
            return c
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
                    self.pac_sin_sps.append((unidad, p["id"], entrada, numero))
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
                self.pendientes_sps.append(self._pendiente("cupo_sin_sps", a.get("id"), pid, entrada, dia,
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
            return None, SIN_SPS["evaluacion"], entrada
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
                    motivo = SIN_SPS["cirugia"]
                else:
                    c = self.cand_de(pid, unidad, sps, "cirugía", entrada, motivo_cat, g.get("code"), cx.get("procedure"))
            at = self._atencion("cirugia", cx["id"], pid, fecha, cx.get("surgeon"), cx.get("procedure"))
            at["paciente_nombre"] = cx.get("patient_name", "")
            at["unidad_id"] = unidad
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

    def _unidad_de(self, entrada, pid, unidad=""):
        return (entrada or {}).get("unidad_id") or unidad or (self.pacs.get(pid) or {}).get("igss_unit_id", "")

    def _ref_contrato(self, entrada, pid=""):
        """Inicio del contrato: la fecha de la entrada; si no se conoce, la más antigua de las
        entradas de las órdenes del paciente o, en último caso, de la unidad."""
        if entrada and _dia(entrada.get("fecha_asignacion")):
            return _dia(entrada.get("fecha_asignacion"))
        fechas = [_dia(e.get("fecha_asignacion")) for e in self.entradas_pac.get(pid, [])]
        p = self.pacs.get(pid) or {}
        return _min(fechas) or self.cat.inicio_unidad.get((entrada or {}).get("unidad_id") or p.get("igss_unit_id", ""), "")

    def _filtrar(self, ats, ref, unidad):
        if not ref:
            return ats, []
        dentro = [a for a in ats if not a["fecha"] or a["fecha"] >= ref]
        fuera = [a for a in ats if a["fecha"] and a["fecha"] < ref]
        for a in fuera:
            self.hist[(unidad, f"{a['tipo']}_anterior_contrato")] += 1
        return dentro, fuera

    def _ignorada(self, at, entrada) -> bool:
        """Historial que solo se cuenta: anterior al contrato o paciente aún sin unidad IGSS."""
        pid, fecha = at["paciente_id"], at["fecha"]
        unidad = self._unidad_de(entrada, pid, at.get("unidad_id", ""))
        ref = self._ref_contrato(entrada, pid)
        if ref and fecha and fecha < ref:
            self.hist[(unidad, f"{at['tipo']}_anterior_contrato")] += 1
            return True
        inicio = self.inicio_igss.get(pid) or _dia_gt((self.pacs.get(pid) or {}).get("created_at"))
        if at["tipo"] == "evaluacion" and inicio and fecha and fecha < inicio:
            self.hist[(unidad, "evaluacion_sin_unidad")] += 1
            return True
        return False

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
                entrada = next(iter(c["entradas"].values()), None) if len(c["entradas"]) == 1 else None
                ats = [a for a in c["evaluaciones"] + c["cirugias"] if not self._ignorada(a, entrada)]
                self.no_migrables.append(self._caso(
                    "orden", c["unidad_id"], _min(c["ingresos"] + [a["fecha"] for a in ats]), problema, c["pacientes"],
                    list(c["entradas"].values()), c["no_sps"], c["fuentes"], len(ats)))
            else:
                self.migrables.append(self._orden(c))
        for unidad, pid, entrada, numero in self.pac_sin_sps:
            fecha = self.inicio_igss.get(pid) or _dia_gt((self.pacs.get(pid) or {}).get("created_at"))
            caso = self._caso("orden", self._unidad_de(entrada, pid, unidad), fecha, "Orden del paciente sin No. SPS",
                              [pid], [entrada] if entrada else [], "", ["orden del paciente"], 0)
            caso["nog"] = caso["nog"] or numero
            self.no_migrables.append(caso)
        for at, entrada, motivo in self.sueltas:
            if self._ignorada(at, entrada):
                continue
            if motivo == SIN_SPS[at["tipo"]]:
                p = self._pendiente(at["tipo"], at["ref_id"], at["paciente_id"], entrada, at["fecha"],
                                    unidad=at.get("unidad_id", ""), procedimiento=at["procedimiento"],
                                    medico=at["medico"], nombre=at.get("paciente_nombre", ""))
                p["ya_en_lista"] = at["en_sin_orden"]
                self.pendientes_sps.append(p)
            else:
                self.no_migrables.append(self._caso(
                    at["tipo"], self._unidad_de(entrada, at["paciente_id"], at.get("unidad_id", "")), at["fecha"], motivo,
                    [at["paciente_id"]] if at["paciente_id"] else [], [entrada] if entrada else [], "",
                    [{"evaluacion": "evaluación", "cirugia": "cirugía"}[at["tipo"]]], 1,
                    nombre=at.get("paciente_nombre", "")))
        self._ordenes_probables()

    def _ordenes_probables(self):
        """Para cada cupo sin SPS, la orden con SPS del mismo paciente y NOG (si es una sola)."""
        idx = {}
        for o in self.migrables + self.libro:
            idx.setdefault((o.get("paciente_id"), o.get("nog_id")), set()).add(o.get("no_sps"))
        for i in self.pendientes_sps:
            if i["tipo"] == "cupo_sin_sps":
                ops = sorted(idx.get((i["paciente_id"], i["nog_id"])) or [])
                i["orden_probable"] = ops[0] if len(ops) == 1 else f"{len(ops)} órdenes posibles" if ops else ""

    def _orden(self, c):
        entrada, pid = next(iter(c["entradas"].values())), next(iter(c["pacientes"]))
        unidad = entrada.get("unidad_id", "")
        ingreso = _min(c["ingresos"])
        asignacion = _dia(entrada.get("fecha_asignacion"))
        ref = asignacion or ingreso
        evs, ev_fuera = self._filtrar(c["evaluaciones"], ref, unidad)
        cxs, cx_fuera = self._filtrar(c["cirugias"], ref, unidad)
        dentro = sorted(evs + cxs, key=lambda a: a["fecha"])
        tipo = "procedimiento" if c["cx_vinculadas"] else "consulta"
        p = self.pacs.get(pid) or {}
        obs = []
        if not ref:
            obs.append("Revisar fecha")
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
            "unidad_id": unidad, "nog_id": entrada["id"], "nog": etiqueta_catalogo(entrada),
            "modalidad": _modalidad(entrada), "no_sps": c["no_sps"], "paciente_id": pid,
            "paciente_nombre": _nombre(p), "expediente": p.get("record_number", ""),
            "igss_afiliacion": p.get("igss_afiliacion", ""),
            "codigo": c["codigo"], "procedimiento": c["procedimiento"] or entrada.get("nombre_servicio", ""),
            "tipo": tipo, "dosis_autorizadas": max(1, len(cxs)) if tipo == "procedimiento" else 1,
            "estado": "atendida" if dentro else "pendiente", "fecha_ingreso": ingreso,
            "fecha_referencia": ref, "fuente_referencia": "Asignación del NOG" if asignacion else "Ingreso de la orden" if ingreso else "",
            "fecha_primera_atencion": _min(a["fecha"] for a in dentro),
            "evaluaciones": len(evs), "cirugias": len(cxs), "fechas_atenciones": [a["fecha"] for a in dentro],
            "atenciones": [{k: a[k] for k in ("tipo", "ref_id", "fecha", "medico")} for a in dentro],
            "excluidas_anteriores": len(ev_fuera) + len(cx_fuera), "resuelve_sin_orden": resueltas,
            "revisar_fecha": not ref, "origen": sorted(c["fuentes"]), "precio": float(entrada.get("precio") or 0),
            **self._estados(c["evaluaciones"]), "observaciones": obs,
        }

    def _ya_en_libro(self, o, c):
        entrada = self.cat.por_id.get(o.get("nog_id"))
        unidad = o.get("unidad_id", "")
        ref = _dia((entrada or {}).get("fecha_asignacion")) or _dia(o.get("fecha_ingreso"))
        evs, _ = self._filtrar(c["evaluaciones"], ref, unidad)
        cxs, _ = self._filtrar(c["cirugias"], ref, unidad)
        if not evs and not cxs:
            return
        self.ya_en_libro.append({
            "orden_id": o["id"], "unidad_id": unidad, "nog_id": o.get("nog_id", ""),
            "nog": etiqueta_catalogo(entrada) if entrada else o.get("numero_nog", ""), "no_sps": o.get("no_sps", ""),
            "paciente_id": o.get("paciente_id", ""), "paciente_nombre": o.get("paciente_nombre", ""),
            "estado_actual": o.get("estado", ""), "estado_resultante": "atendida",
            "evaluaciones_a_agregar": len(evs), "cirugias_a_agregar": len(cxs),
            "fechas_atenciones": sorted(a["fecha"] for a in evs + cxs)})

    def _pac_datos(self, pids, nombre=""):
        ps = [self.pacs.get(x) or {} for x in sorted(pids)]
        return {"paciente_ids": sorted(pids),
                "paciente_nombre": ", ".join(_nombre(p) or x for p, x in zip(ps, sorted(pids))) or nombre or "",
                "expediente": ", ".join(p.get("record_number", "") for p in ps if p.get("record_number")),
                "igss_afiliacion": ", ".join(p.get("igss_afiliacion", "") for p in ps if p.get("igss_afiliacion"))}

    def _caso(self, tipo, unidad, fecha, motivo, pids, entradas, sps, fuentes, atenciones, nombre=""):
        agrupado, falta = _regla(motivo)
        return {"tipo_caso": tipo, "unidad_id": unidad or "", "fecha": fecha or "", "motivo": motivo,
                "motivo_agrupado": agrupado, "falta": falta, "no_sps": sps or "",
                "nog_id": entradas[0]["id"] if len(entradas) == 1 else "",
                "nog": ", ".join(sorted(etiqueta_catalogo(e) for e in entradas)),
                **self._pac_datos(pids, nombre), "origen": sorted(fuentes), "atenciones": atenciones}

    def _pendiente(self, tipo, ref_id, pid, entrada, fecha, unidad="", procedimiento="", medico="", nombre=""):
        return {"tipo": tipo, "etiqueta": SIN_SPS[tipo], "ref_id": ref_id or "", "paciente_id": pid or "",
                **{k: v for k, v in self._pac_datos([pid] if pid else [], nombre).items() if k != "paciente_ids"},
                "unidad_id": self._unidad_de(entrada, pid, unidad), "nog_id": (entrada or {}).get("id", ""),
                "nog": etiqueta_catalogo(entrada) if entrada else "", "fecha": fecha or "",
                "procedimiento": procedimiento, "medico": medico, "ya_en_lista": False, "orden_probable": ""}


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
    units = {u["id"]: u for u in await db.igss_units.find(
        {}, {"_id": 0, "id": 1, "name": 1, "is_active": 1, "created_at": 1}).to_list(None)}
    return {"nogs": nogs, "acreds": acreds, "cxs": cxs, "pacientes": pacs, "evals": evals, "prod": prod,
            "libro": libro, "sin_orden": sin_orden, "units": units}


# ==================== UNIDADES DUPLICADAS Y BLOQUEOS ====================

def _grupos_duplicados(units: dict) -> list:
    grupos = {}
    for uid, u in units.items():
        grupos.setdefault(norm_txt(u.get("name")), []).append(uid)
    return [sorted(ids, key=lambda i: units[i].get("created_at") or "") for k, ids in sorted(grupos.items())
            if k and len(ids) > 1]


def _advertencias(grupos, units, d, s) -> list:
    pacs = Counter(p.get("igss_unit_id") for p in d["pacientes"].values()
                   if p.get("referral_institution") == "igss" and p.get("is_active", True) is not False)
    nogs = Counter(n.get("unidad_id") for n in d["nogs"])
    migrar = Counter(o["unidad_id"] for o in s.migrables)
    return [{
        "tipo": "unidades_duplicadas", "nombre": units[g[0]].get("name", ""),
        "mensaje": f"{len(g)} unidades con el mismo nombre. No impide aplicar; queda pendiente su fusión.",
        "unidades": [{"unidad_id": u, "unidad": units[u].get("name", ""), "is_active": units[u].get("is_active", True) is not False,
                      "creada": _dia_gt(units[u].get("created_at")), "pacientes_activos": pacs[u], "nogs": nogs[u],
                      "ordenes_a_migrar": migrar[u]} for u in g]} for g in grupos]


def _bloqueos(grupos, units, s) -> list:
    """Mismo No. SPS vigente (ya en el libro o por migrar) en dos unidades duplicadas."""
    out = []
    for g in grupos:
        usos = {}
        for o in s.migrables:
            if o["unidad_id"] in g:
                usos.setdefault(o["no_sps"], []).append({
                    "unidad_id": o["unidad_id"], "origen": "por migrar", "nog": o["nog"],
                    "paciente_nombre": o["paciente_nombre"], "expediente": o["expediente"]})
        for o in s.libro:
            if o.get("unidad_id") in g:
                usos.setdefault(o["no_sps"], []).append({
                    "unidad_id": o["unidad_id"], "origen": "ya en el libro", "nog": o.get("numero_nog", ""),
                    "paciente_nombre": o.get("paciente_nombre", ""), "expediente": o.get("paciente_expediente", "")})
        for sps, lst in sorted(usos.items()):
            if len({x["unidad_id"] for x in lst}) > 1:
                out.append({"tipo": "sps_en_unidades_duplicadas", "no_sps": sps, "nombre": units[g[0]].get("name", ""),
                            "unidades_ids": g, "usos": [{**x, "unidad": units[x["unidad_id"]].get("name", "")} for x in lst]})
    return out


# ==================== RESÚMENES ====================

def _resumen_nog(s, nogs, cont, acreds, units) -> list:
    a_migrar, pasan = Counter(), Counter()
    pend_sps = Counter(i["nog_id"] for i in s.pendientes_sps if i["nog_id"])
    vigentes = Counter(a.get("nog_id") for a in acreds if a.get("anulada") is not True)
    for o in s.migrables:
        a_migrar[(o["nog_id"], o["estado"])] += 1
    for o in s.ya_en_libro:
        if o["estado_actual"] == "pendiente":
            pasan[o["nog_id"]] += 1
    filas = []
    for n in nogs:
        c = cont.get(n["id"], {})
        tope = not n.get("sin_tope") and int(n.get("cantidad") or 0) > 0
        cantidad = int(n.get("cantidad") or 0)
        atendidas, pendientes = a_migrar[(n["id"], "atendida")], a_migrar[(n["id"], "pendiente")]
        consumidos = int(c.get("consumidos", 0)) + atendidas + pasan[n["id"]]
        reservados = int(c.get("reservados", 0)) + pendientes - pasan[n["id"]]
        filas.append({
            "nog_id": n["id"], "unidad_id": n.get("unidad_id", ""), "unidad": units.get(n.get("unidad_id", ""), {}).get("name", ""),
            "nog": etiqueta_catalogo(n), "modalidad": _modalidad(n), "is_active": n.get("is_active", True) is not False,
            "sin_tope": not tope, "cantidad": cantidad if tope else None,
            "a_migrar": atendidas + pendientes, "consumidas": atendidas, "pendientes": pendientes,
            "pendientes_sps": pend_sps[n["id"]], "contador_actual": int(n.get("acreditados") or 0),
            "acreditaciones_vigentes": vigentes[n["id"]],
            "libro_consumidos": int(c.get("consumidos", 0)), "libro_reservados": int(c.get("reservados", 0)),
            "sobrecupo": max(consumidos + reservados - cantidad, 0) if tope else 0,
        })
    filas.sort(key=lambda f: (f["unidad"], f["nog"].startswith("Baja"), f["nog"]))
    return filas


def _por_unidad(units, ordenes, no_migrables, pendientes) -> list:
    filas = {}
    for lista, campo in ((ordenes, "a_migrar"), (no_migrables, "no_migrables"), (pendientes, "pendientes_sps")):
        for x in lista:
            f = filas.setdefault(x["unidad_id"], {"unidad_id": x["unidad_id"],
                                                  "unidad": units.get(x["unidad_id"], {}).get("name", "") or "(sin unidad)",
                                                  "a_migrar": 0, "consumidas": 0, "pendientes": 0,
                                                  "no_migrables": 0, "pendientes_sps": 0})
            f[campo] += 1
            if campo == "a_migrar":
                f["consumidas" if x["estado"] == "atendida" else "pendientes"] += 1
    return sorted(filas.values(), key=lambda f: f["unidad"])


def _por_anio(ordenes) -> list:
    anios = {}
    for o in ordenes:
        f = anios.setdefault(o["fecha_primera_atencion"][:4] or SIN_ATENCION, {"ordenes": 0, "consumidas": 0, "pendientes": 0})
        f["ordenes"] += 1
        f["consumidas" if o["estado"] == "atendida" else "pendientes"] += 1
    return [{"anio": a, **anios[a]} for a in sorted(anios, key=lambda x: (x == SIN_ATENCION, x))]


def _por_motivo(no_migrables, pendientes) -> list:
    c = Counter(("No se migra", x["motivo_agrupado"]) for x in no_migrables)
    c.update(("Pendiente de SPS", x["etiqueta"]) for x in pendientes)
    return [{"grupo": g, "motivo": m, "casos": n} for (g, m), n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))]


def _orden_caso(x, units):
    return (units.get(x["unidad_id"], {}).get("name", "") or "~", x["fecha"] or "9999", x.get("paciente_nombre", ""))


async def simular_migracion(unidad_id: Optional[str] = None) -> dict:
    d = await _cargar()
    units = d["units"]
    if unidad_id and unidad_id not in units:
        raise HTTPException(status_code=404, detail="Unidad IGSS no encontrada")
    s = Simulacion(d)
    s.ordenes_pacientes()
    s.acreditaciones(d["acreds"])
    s.evaluaciones(d["evals"])
    s.cirugias(d["cxs"])
    s.clasificar()
    grupos = _grupos_duplicados(units)
    advertencias, bloqueos = _advertencias(grupos, units, d, s), _bloqueos(grupos, units, s)
    resumen = _resumen_nog(s, d["nogs"], await contadores_libro(), d["acreds"], units)

    def de_unidad(x):
        return not unidad_id or x.get("unidad_id") == unidad_id

    ordenes = sorted(filter(de_unidad, s.migrables),
                     key=lambda o: (units.get(o["unidad_id"], {}).get("name", ""), o["nog"], o["fecha_primera_atencion"] or "9", o["no_sps"]))
    no_migrables = sorted(filter(de_unidad, s.no_migrables), key=lambda x: _orden_caso(x, units))
    pendientes = sorted(filter(de_unidad, s.pendientes_sps), key=lambda x: _orden_caso(x, units))
    ya_en_libro = list(filter(de_unidad, s.ya_en_libro))
    resumen = list(filter(de_unidad, resumen))
    if unidad_id:
        advertencias = [a for a in advertencias if any(u["unidad_id"] == unidad_id for u in a["unidades"])]
    bloqueos_unidad = [b for b in bloqueos if not unidad_id or unidad_id in b["unidades_ids"]]
    for lista in (ordenes, no_migrables, pendientes, ya_en_libro):
        for x in lista:
            x["unidad"] = units.get(x["unidad_id"], {}).get("name", "")
    hist = Counter()
    for (u, k), n in s.hist.items():
        if not unidad_id or u == unidad_id:
            hist[k] += n
    totales = {
        "ordenes_a_migrar": len(ordenes),
        "consumidas": sum(1 for o in ordenes if o["estado"] == "atendida"),
        "pendientes": sum(1 for o in ordenes if o["estado"] == "pendiente"),
        "no_se_migra": len(no_migrables) + len(pendientes),
        "no_migrables": len(no_migrables),
        "pendientes_sps": len(pendientes),
        "evaluaciones_a_registrar": sum(o["evaluaciones"] for o in ordenes),
        "cirugias_a_registrar": sum(o["cirugias"] for o in ordenes),
        "revisar_fecha": sum(1 for o in ordenes if o["revisar_fecha"]),
        "ordenes_ya_en_libro_con_atenciones_nuevas": len(ya_en_libro),
        "atenciones_a_agregar_en_libro": sum(o["evaluaciones_a_agregar"] + o["cirugias_a_agregar"] for o in ya_en_libro),
        "evaluaciones_historicas_ignoradas": hist["evaluacion_anterior_contrato"] + hist["evaluacion_sin_unidad"],
        "evaluaciones_anteriores_al_contrato": hist["evaluacion_anterior_contrato"],
        "evaluaciones_sin_unidad_igss_en_la_fecha": hist["evaluacion_sin_unidad"],
        "cirugias_anteriores_al_contrato": hist["cirugia_anterior_contrato"],
        "nogs_con_sobrecupo": sum(1 for f in resumen if f["sobrecupo"]),
        "unidades_duplicadas": len(advertencias),
        "bloqueos": len(bloqueos_unidad),
    }
    return {
        "generado": now_gt().isoformat(), "solo_lectura": True, "unidad_id": unidad_id or "",
        "unidad": units.get(unidad_id, {}).get("name", "") if unidad_id else "Todas las unidades",
        "aplicacion_permitida": not bloqueos, "bloqueos_totales": len(bloqueos),
        "criterios": CRITERIOS, "totales": totales,
        "por_unidad": _por_unidad(units, ordenes, no_migrables, pendientes), "por_anio": _por_anio(ordenes),
        "por_motivo": _por_motivo(no_migrables, pendientes), "advertencias": advertencias, "bloqueos": bloqueos_unidad,
        "unidades": sorted(({"id": u["id"], "name": u.get("name", ""), "is_active": u.get("is_active", True) is not False}
                            for u in units.values()), key=lambda u: u["name"]),
        "resumen_nog": resumen, "ordenes": ordenes, "no_migrables": no_migrables, "pendientes_sps": pendientes,
        "ya_en_libro": ya_en_libro,
    }


# ==================== EXCEL ====================

REVISION = ["No. SPS correcto", "Revisado por"]


def _tabla(ws, r, titulos, filas):
    _fila_titulos(ws, r, titulos)
    for fila in filas:
        r += 1
        for c, v in enumerate(fila, 1):
            ws.cell(row=r, column=c, value=v)
    return r


def _hoja_resumen(ws, sim):
    t = sim["totales"]
    r = _encabezado(ws, [("Simulación de migración al Libro de órdenes IGSS", "SOLO LECTURA: no se aplicó ningún cambio"),
                         ("Unidad", sim["unidad"]),
                         ("Generado", fmt_fecha(sim["generado"]) + " " + sim["generado"][11:16]),
                         ("Aplicación", "PERMITIDA" if sim["aplicacion_permitida"] else
                          f"BLOQUEADA: {sim['bloqueos_totales']} No. SPS vigente(s) repetido(s) en unidades duplicadas")])
    r = _tabla(ws, r, ["Concepto", "Cantidad"], [
        ("Órdenes a migrar", t["ordenes_a_migrar"]), ("  · consumidas (atendidas)", t["consumidas"]),
        ("  · pendientes (reservan cupo)", t["pendientes"]),
        ("Total que NO se migra", t["no_se_migra"]), ("  · no migrables", t["no_migrables"]),
        ("  · pendientes de SPS", t["pendientes_sps"]),
        ("Evaluaciones a registrar como atención", t["evaluaciones_a_registrar"]),
        ("Cirugías realizadas a registrar como dosis", t["cirugias_a_registrar"]),
        ("Órdenes marcadas 'Revisar fecha'", t["revisar_fecha"]),
        ("Órdenes que ya están en el libro y recibirían atenciones", t["ordenes_ya_en_libro_con_atenciones_nuevas"]),
        (f"{t['evaluaciones_historicas_ignoradas']} evaluaciones históricas ignoradas", t["evaluaciones_historicas_ignoradas"]),
        ("  · anteriores a la fecha de asignación del contrato", t["evaluaciones_anteriores_al_contrato"]),
        ("  · paciente aún sin unidad IGSS en esa fecha", t["evaluaciones_sin_unidad_igss_en_la_fecha"]),
        ("Cirugías anteriores al contrato ignoradas", t["cirugias_anteriores_al_contrato"]),
        ("Entradas del catálogo que quedarían sobre su cupo", t["nogs_con_sobrecupo"]),
        ("Unidades duplicadas (advertencia)", t["unidades_duplicadas"]),
        ("No. SPS repetidos en unidades duplicadas (bloqueo)", t["bloqueos"])]) + 2
    r = _tabla(ws, r, ["Unidad", "Órdenes a migrar", "Consumidas", "Pendientes", "No migrables", "Pendientes de SPS"],
               [(u["unidad"], u["a_migrar"], u["consumidas"], u["pendientes"], u["no_migrables"], u["pendientes_sps"])
                for u in sim["por_unidad"]]) + 2
    r = _tabla(ws, r, ["Año de primera atención", "Órdenes a migrar", "Consumidas", "Pendientes"],
               [(a["anio"], a["ordenes"], a["consumidas"], a["pendientes"]) for a in sim["por_anio"]]) + 2
    r = _tabla(ws, r, ["Motivo de no migración", "Grupo", "Casos"],
               [(m["motivo"], m["grupo"], m["casos"]) for m in sim["por_motivo"]]) + 2
    if sim["bloqueos"]:
        r = _tabla(ws, r, ["BLOQUEO: No. SPS", "Unidad", "Origen", "NOG", "Paciente", "Expediente"],
                   [(b["no_sps"], u["unidad"], u["origen"], u["nog"], u["paciente_nombre"], u["expediente"])
                    for b in sim["bloqueos"] for u in b["usos"]]) + 2
    if sim["advertencias"]:
        r = _tabla(ws, r, ["ADVERTENCIA: unidad duplicada", "Id", "Activa", "Creada", "Pacientes activos", "NOG",
                           "Órdenes a migrar"],
                   [(u["unidad"], u["unidad_id"], "Sí" if u["is_active"] else "No", fmt_fecha(u["creada"]),
                     u["pacientes_activos"], u["nogs"], u["ordenes_a_migrar"])
                    for a in sim["advertencias"] for u in a["unidades"]]) + 2
    _tabla(ws, r, ["Criterios aplicados"], [(c,) for c in sim["criterios"]])
    _anchos(ws, 7)
    ws.column_dimensions["A"].width = 62


def simulacion_excel(sim: dict) -> io.BytesIO:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    _hoja_resumen(ws, sim)
    hojas = [
        ("Por NOG", ["Unidad", "NOG / Entrada", "Modalidad", "Activo", "Cupos", "Órdenes a migrar", "Consumidas",
                     "Pendientes", "Pendientes de SPS", "Contador actual (acreditados)", "Acreditaciones vigentes hoy",
                     "Quedaría sobre el cupo"],
         [(f["unidad"], f["nog"], f["modalidad"], "Sí" if f["is_active"] else "No",
           "Sin tope" if f["sin_tope"] else f["cantidad"], f["a_migrar"], f["consumidas"], f["pendientes"],
           f["pendientes_sps"], f["contador_actual"], f["acreditaciones_vigentes"], f["sobrecupo"])
          for f in sim["resumen_nog"]]),
        ("Órdenes", ["Unidad", "Modalidad", "NOG", "No. SPS", "Expediente", "Paciente", "Afiliación", "Procedimiento",
                     "Fecha 1ª atención", "Estado propuesto", "Dosis autorizadas", "Origen", "Observaciones"],
         [(o["unidad"], o["modalidad"], o["nog"], o["no_sps"], o["expediente"], o["paciente_nombre"], o["igss_afiliacion"],
           o["procedimiento"], fmt_fecha(o["fecha_primera_atencion"]), "Atendida" if o["estado"] == "atendida" else "Pendiente",
           o["dosis_autorizadas"], ", ".join(o["origen"]), "; ".join(o["observaciones"])) for o in sim["ordenes"]]),
        ("No migrables", ["Unidad", "Fecha", "Tipo", "Motivo", "Qué falta para migrarlo", "NOG", "No. SPS registrado",
                          "Expediente", "Paciente", "Afiliación", "Origen", "Atenciones afectadas", *REVISION],
         [(x["unidad"], fmt_fecha(x["fecha"]), TIPO_CASO[x["tipo_caso"]], x["motivo"], x["falta"], x["nog"],
           x["no_sps"] or "(vacío)", x["expediente"], x["paciente_nombre"], x["igss_afiliacion"], ", ".join(x["origen"]),
           x["atenciones"]) for x in sim["no_migrables"]]),
        ("Pendientes de SPS", ["Unidad", "Fecha", "Tipo", "NOG", "Expediente", "Paciente", "Afiliación",
                               "Procedimiento", "Médico", "Orden probable (mismo paciente y NOG)", *REVISION],
         [(x["unidad"], fmt_fecha(x["fecha"]), x["etiqueta"], x["nog"] or "Sin NOG identificado", x["expediente"],
           x["paciente_nombre"], x["igss_afiliacion"], x["procedimiento"], x["medico"], x["orden_probable"])
          for x in sim["pendientes_sps"]]),
    ]
    for nombre, titulos, filas in hojas:
        hoja = wb.create_sheet(nombre)
        _tabla(hoja, 1, titulos, filas)
        _anchos(hoja, len(titulos))
        hoja.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ==================== ENDPOINTS ====================

@router.get("/simular")
async def simular(unidad_id: Optional[str] = None, detalle: bool = Query(True),
                  current_user: dict = Depends(SOLO_SUPERADMIN)):
    """Paso (a): simulación de solo lectura. No crea, edita ni borra ningún dato.
    detalle=false devuelve solo totales y desgloses (pantalla)."""
    sim = await simular_migracion(unidad_id)
    if not detalle:
        for k in ("resumen_nog", "ordenes", "no_migrables", "pendientes_sps", "ya_en_libro"):
            sim.pop(k)
    return sim


@router.get("/simular/excel")
async def simular_excel(unidad_id: Optional[str] = None, current_user: dict = Depends(SOLO_SUPERADMIN)):
    """Mismo cálculo de solo lectura, en Excel. Puede descargarse las veces que haga falta."""
    sim = await simular_migracion(unidad_id)
    return _descarga(simulacion_excel(sim), _nombre_archivo("Simulacion_migracion_libro_IGSS",
                                                            sim["unidad"] if unidad_id else "", sim["generado"][:10]))
