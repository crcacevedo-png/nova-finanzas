# Diagnóstico de SOLO LECTURA para la simulación de migración al libro IGSS (Fase 4).
# Solo usa find(); no escribe nada. Imprime únicamente conteos (sin nombres ni datos clínicos).
# Uso: MONGO_URL=... DB_NAME=... python3 diag_migracion_prod_solo_lectura.py
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

GT = timezone(timedelta(hours=-6))
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HOY = datetime.now(GT).strftime("%Y-%m-%d")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def dia(v):
    s = str(v or "")[:10]
    return s if FECHA.match(s) else ""


def dia_gt(v):
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return dia(v)
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(GT).strftime("%Y-%m-%d")


def txt(v):
    return str(v or "").strip()


def dias_entre(a, b):
    return (datetime.strptime(a, "%Y-%m-%d") - datetime.strptime(b, "%Y-%m-%d")).days


def tramo(delta):
    if delta >= 0:
        return "a) igual o posterior al registro"
    d = -delta
    return ("b) 1-30 dias antes" if d <= 30 else "c) 31-90 dias antes" if d <= 90
            else "d) 91-365 dias antes" if d <= 365 else "e) mas de 365 dias antes")


def es_borrador(ev):
    if txt(ev.get("medico_id")) or txt(ev.get("medico_nombre")):
        return False
    if any(txt(ev.get(k)) for k in ("igss_procedimiento", "motivo_consulta", "padecimiento_actual", "plan")):
        return False
    return not any(isinstance(d, dict) and (txt(d.get("descripcion")) or txt(d.get("codigo_cie10")))
                   for d in ev.get("diagnosticos") or [])


def ordenes(p):
    ords = [o for o in (p.get("igss_ordenes") or []) if isinstance(o, dict)]
    if not ords and (p.get("igss_nog") or p.get("igss_no_sps")):
        ords = [{"id": f"{p['id']}_ord1", "nog": p.get("igss_nog"), "no_sps": p.get("igss_no_sps")}]
    return ords


out = {"hoy_guatemala": HOY}
nogs = list(db.igss_nogs.find({}, {"_id": 0, "id": 1, "unidad_id": 1, "numero": 1, "fecha_asignacion": 1,
                                   "created_at": 1, "is_active": 1}))
nog_id = {n["id"]: n for n in nogs}
nog_num = {(n.get("unidad_id"), txt(n.get("numero")).upper()): n for n in nogs if txt(n.get("numero"))}
acreds = list(db.igss_nog_acreditaciones.find({}, {"_id": 0, "paciente_id": 1, "nog_id": 1, "fecha_acreditacion": 1,
                                                   "origen": 1, "anulada": 1, "no_sps": 1, "evaluacion_id": 1}))
cxs = list(db.surgeries.find({"institution": "IGSS"}, {"_id": 0, "id": 1, "patient_id": 1, "date": 1, "status": 1,
                                                       "igss_data": 1, "rescheduled_to": 1}))
pac_proj = {"_id": 0, "id": 1, "igss_unit_id": 1, "igss_ordenes": 1, "igss_nog": 1, "igss_no_sps": 1,
            "referral_institution": 1, "created_at": 1}
pacs = {p["id"]: p for p in db.patients.find({"referral_institution": "igss"}, pac_proj)}
evs = list(db.evaluaciones_oftalmologicas.find(
    {"paciente_id": {"$in": list(pacs)}},
    {"_id": 0, "id": 1, "paciente_id": 1, "fecha": 1, "medico_id": 1, "medico_nombre": 1, "igss_procedimiento": 1,
     "motivo_consulta": 1, "padecimiento_actual": 1, "plan": 1, "diagnosticos": 1, "igss_nog": 1, "igss_nog_id": 1,
     "igss_no_sps": 1, "igss_orden_id": 1}))
evs = [e for e in evs if not es_borrador(e)]


def entrada_de(unidad, nid, numero):
    return nog_id.get(nid or "") or nog_num.get((unidad, txt(numero).upper()))


# ---------- 1. FECHA DEL CATÁLOGO ----------
con_fa = [n for n in nogs if dia(n.get("fecha_asignacion"))]
out["1_catalogo"] = {
    "entradas_total": len(nogs),
    "con_fecha_asignacion_valida": len(con_fa),
    "con_fecha_asignacion_texto_no_valido": sum(1 for n in nogs if txt(n.get("fecha_asignacion")) and not dia(n.get("fecha_asignacion"))),
    "con_created_at": sum(1 for n in nogs if dia_gt(n.get("created_at"))),
    "created_at_por_dia": dict(sorted(Counter(dia_gt(n.get("created_at")) or "(sin fecha)" for n in nogs).items())),
}
out["1_acreditaciones"] = {
    "total": len(acreds), "no_anuladas": sum(1 for a in acreds if a.get("anulada") is not True),
    "con_no_sps": sum(1 for a in acreds if txt(a.get("no_sps"))),
    "con_evaluacion_id": sum(1 for a in acreds if txt(a.get("evaluacion_id"))),
    "por_origen": dict(Counter(a.get("origen") or "(vacio)" for a in acreds)),
}
# Órdenes con No. SPS y entrada del catálogo identificable (las candidatas a migrar).
acred_pac_nog = {}
for a in acreds:
    if a.get("anulada") is not True and a.get("origen") in ("asignacion", "reasignacion", "evaluacion"):
        f = dia_gt(a.get("fecha_acreditacion"))
        k = (a.get("paciente_id"), a.get("nog_id"))
        if f and (k not in acred_pac_nog or f < acred_pac_nog[k]):
            acred_pac_nog[k] = f
c_ord = Counter()
for p in pacs.values():
    for o in ordenes(p):
        if not txt(o.get("no_sps")):
            c_ord["sin_no_sps"] += 1
            continue
        e = entrada_de(p.get("igss_unit_id"), o.get("nog_id"), o.get("nog"))
        if not e:
            c_ord["con_sps_sin_entrada_identificable"] += 1
            continue
        c_ord["con_sps_y_entrada"] += 1
        if dia(e.get("fecha_asignacion")):
            c_ord["  entrada_con_fecha_asignacion"] += 1
        elif (p["id"], e["id"]) in acred_pac_nog:
            c_ord["  sin_fecha_asig_pero_con_acreditacion_mismo_paciente_y_entrada"] += 1
        else:
            c_ord["  sin_fecha_asig_ni_acreditacion (solo created_at de la entrada)"] += 1
out["1_ordenes_de_pacientes"] = dict(c_ord)
# Atenciones reales frente al created_at de su entrada (¿sirve created_at como inicio del contrato?).
tr_ev, tr_ac, tr_cx = Counter(), Counter(), Counter()
for e in evs:
    p = pacs[e["paciente_id"]]
    n = entrada_de(p.get("igss_unit_id"), e.get("igss_nog_id"), e.get("igss_nog"))
    if n and dia(e.get("fecha")) and dia_gt(n.get("created_at")):
        tr_ev[tramo(dias_entre(dia(e["fecha"]), dia_gt(n["created_at"])))] += 1
for a in acreds:
    n = nog_id.get(a.get("nog_id"))
    if n and dia_gt(a.get("fecha_acreditacion")) and dia_gt(n.get("created_at")):
        tr_ac[tramo(dias_entre(dia_gt(a["fecha_acreditacion"]), dia_gt(n["created_at"])))] += 1
for c in cxs:
    g = c.get("igss_data") or {}
    p = pacs.get(c.get("patient_id")) or {}
    n = entrada_de(g.get("unit_id") or p.get("igss_unit_id"), g.get("nog_id"), g.get("nog_number"))
    if c.get("status") != "cancelado" and n and dia(c.get("date")) and dia_gt(n.get("created_at")):
        tr_cx[tramo(dias_entre(dia(c["date"]), dia_gt(n["created_at"])))] += 1
out["1_atencion_vs_registro_de_su_entrada"] = {"evaluaciones": dict(sorted(tr_ev.items())),
                                               "acreditaciones": dict(sorted(tr_ac.items())),
                                               "cirugias_no_canceladas": dict(sorted(tr_cx.items()))}
# Por orden: su atención más antigua frente a la referencia de respaldo
# (la más antigua entre la acreditación del mismo paciente y entrada, y el registro de la entrada).
ev_pac = {}
for e in evs:
    ev_pac.setdefault(e["paciente_id"], []).append(e)
cx_pac = {}
for c in cxs:
    if c.get("status") != "cancelado" and c.get("patient_id"):
        cx_pac.setdefault(c["patient_id"], []).append(c)
por_orden = Counter()
for p in pacs.values():
    ords = [o for o in ordenes(p) if txt(o.get("no_sps"))]
    for o in ords:
        e = entrada_de(p.get("igss_unit_id"), o.get("nog_id"), o.get("nog"))
        if not e or dia(e.get("fecha_asignacion")):
            continue
        sps, nog = txt(o["no_sps"]).upper(), txt(o.get("nog"))
        unica = sum(1 for x in ords if txt(x.get("nog")) == nog) == 1
        fechas = [dia(v.get("fecha")) for v in ev_pac.get(p["id"], [])
                  if v.get("igss_orden_id") == o.get("id") or txt(v.get("igss_no_sps")).upper() == sps
                  or (not txt(v.get("igss_no_sps")) and nog and txt(v.get("igss_nog")) == nog and unica)]
        fechas += [dia(c.get("date")) for c in cx_pac.get(p["id"], []) if txt((c.get("igss_data") or {}).get("sps")).upper() == sps]
        fechas = [f for f in fechas if f]
        refs = [f for f in (acred_pac_nog.get((p["id"], e["id"])), dia_gt(e.get("created_at"))) if f]
        if not fechas:
            por_orden["sin atenciones (queda pendiente)"] += 1
        elif not refs:
            por_orden["sin ninguna fecha de referencia"] += 1
        else:
            por_orden[tramo(dias_entre(min(fechas), min(refs)))] += 1
out["1_ordenes_sin_fecha_asignacion_atencion_mas_antigua_vs_respaldo"] = dict(sorted(por_orden.items()))

# ---------- 2. CIRUGÍAS ----------
anest = {r["surgery_id"]: r for r in db.anesthesia_records.find(
    {"surgery_id": {"$in": [c["id"] for c in cxs]}}, {"_id": 0, "surgery_id": 1, "paid": 1})}


def momento(c):
    d = dia(c.get("date"))
    return "fecha invalida" if not d else "pasada" if d < HOY else "hoy" if d == HOY else "futura"


def destino(c):
    if not txt(c.get("patient_id")):
        return "no migrable (sin paciente)"
    if txt((c.get("igss_data") or {}).get("sps")):
        return "atencion de una orden (tiene No. SPS)"
    return "pendiente de SPS (sin No. SPS)"


realizadas = [c for c in cxs if c.get("status") == "realizado"]
propuesta = [c for c in cxs if c.get("status") != "cancelado" and momento(c) == "pasada"]
out["2_cirugias"] = {
    "total_igss": len(cxs),
    "valores_de_status": dict(Counter(str(c.get("status")) if "status" in c else "(campo ausente)" for c in cxs)),
    "status_x_fecha": dict(Counter(f"{c.get('status')} / {momento(c)}" for c in cxs)),
    "canceladas_con_reprogramacion": sum(1 for c in cxs if c.get("status") == "cancelado" and c.get("rescheduled_to")),
    "criterio_actual_status_realizado": {"total": len(realizadas), "destino": dict(Counter(map(destino, realizadas)))},
    "propuesta_fecha_pasada_y_no_cancelada": {
        "total": len(propuesta), "destino": dict(Counter(map(destino, propuesta))),
        "con_registro_de_anestesia": sum(1 for c in propuesta if c["id"] in anest),
        "con_anestesia_pagada": sum(1 for c in propuesta if (anest.get(c["id"]) or {}).get("paid") is True)},
}

# ---------- 3. EVALUACIONES "SIN UNIDAD IGSS EN ESA FECHA" ----------
inicio, fuente_ini = {}, {}


def evidencia(pid, d, fuente):
    if pid and d and (pid not in inicio or d < inicio[pid]):
        inicio[pid], fuente_ini[pid] = d, fuente


for a in acreds:
    evidencia(a.get("paciente_id"), dia_gt(a.get("fecha_acreditacion")), "primera acreditacion de cupo")
for e in evs:
    if txt(e.get("igss_nog")) or txt(e.get("igss_no_sps")):
        evidencia(e["paciente_id"], dia(e.get("fecha")), "primera evaluacion con NOG o No. SPS")
for c in cxs:
    if c.get("status") != "cancelado":
        evidencia(c.get("patient_id"), dia(c.get("date")), "primera cirugia IGSS")
orden_ids = {o.get("id") for p in pacs.values() for o in ordenes(p) if txt(o.get("no_sps"))}
c3, anios, pac3 = Counter(), Counter(), set()
for e in evs:
    p, f = pacs[e["paciente_id"]], dia(e.get("fecha"))
    if e.get("igss_orden_id") in orden_ids:
        continue
    ini = inicio.get(p["id"]) or dia_gt(p.get("created_at"))
    if f and ini and f < ini:
        c3["total"] += 1
        c3["referencia: " + fuente_ini.get(p["id"], "creacion del expediente")] += 1
        c3["paciente CON unidad IGSS hoy" if txt(p.get("igss_unit_id")) else "paciente SIN unidad IGSS hoy"] += 1
        anios[f[:4]] += 1
        pac3.add(p["id"])
sin_unidad = [p["id"] for p in pacs.values() if not txt(p.get("igss_unit_id"))]
audit = list(db.audit_logs.find({"action": "PATIENT_UPDATED", "details.campos_modificados": {
    "$in": ["igss_unit_id", "referral_institution"]}}, {"_id": 0, "timestamp": 1, "details.patient_id": 1}))
out["3_evaluaciones_ignoradas_sin_unidad"] = {
    **dict(c3), "pacientes_distintos": len(pac3), "por_anio": dict(sorted(anios.items())),
    "pacientes_igss_total": len(pacs), "pacientes_igss_sin_unidad_hoy": len(sin_unidad),
    "evaluaciones_de_pacientes_sin_unidad_hoy": sum(1 for e in evs if e["paciente_id"] in set(sin_unidad)),
    "auditoria_cambios_de_unidad_o_institucion": {
        "registros": len(audit), "pacientes": len({(x.get("details") or {}).get("patient_id") for x in audit}),
        "desde": min((x.get("timestamp") or "" for x in audit), default="")[:10]},
}
print(json.dumps(out, ensure_ascii=False, indent=2))
