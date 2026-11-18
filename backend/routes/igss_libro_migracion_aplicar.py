# /app/backend/routes/igss_libro_migracion_aplicar.py
# Libro IGSS — Fase 4, paso (b): APLICAR la migración y DESHACERLA (solo superadmin).
# Aplicar: exactamente lo simulado (token de 30 minutos y los mismos datos), con un respaldo de
# menos de 24 h, sin bloqueos y una sola ejecución a la vez; todo lo creado lleva el id del lote.
# Deshacer: borra solo lo del lote y se niega, sin excepción ni deshacer parcial, si cualquier
# orden o cupo del lote cambió después de migrar.

import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from config.database import db
from routes.igss_libro import ESTADOS_CUPO, _audit, _nombre_usuario, siguiente_numero_libro
from routes.igss_libro_atenciones import agregar_atencion, programar_existentes
from routes.igss_libro_migracion import (CIFRAS_LOTE, SOLO_SUPERADMIN, emitir_token, huella_datos, leer_token,
                                         respaldo_reciente, simular_migracion)
from utils.timezone import today_str_gt

router = APIRouter(prefix="/igss-units/migracion", tags=["IGSS - Libro (migración)"])

PALABRA_APLICAR, PALABRA_DESHACER = "MIGRAR", "DESHACER"
TURNO_ID = "migracion_libro"
DESHACIBLES = ("aplicado", "incompleto")
COLECCION = {"orden": "igss_ordenes_libro", "ajuste": "igss_libro_ajustes_cupo"}
# Campos que deben seguir iguales al borrar (además del id): si algo cambió en el último
# instante, el borrado no coincide y se restaura todo.
GUARDA = {"orden": ("updated_at", "estado", "vigente", "atenciones", "cirugias_programadas", "dosis_autorizadas",
                    "dosis_por_confirmar", "sps_por_revisar", "no_sps", "facturado", "pagado"),
          "ajuste": ("activo",)}
NO_SE_MUESTRAN = {"updated_at", "updated_by", "fecha_primera_atencion", "fecha_completa"}
TEXTO_CAMPO = {
    "estado": "estado", "atenciones": "dosis / atenciones registradas", "dosis_autorizadas": "dosis autorizadas",
    "cirugias_programadas": "cirugías programadas (reprogramada, realizada, cancelada o eliminada)",
    "dosis_por_confirmar": "dosis confirmadas con la hoja", "sps_por_revisar": "No. SPS confirmado con la hoja",
    "dosis_confirmadas_por": "dosis confirmadas con la hoja", "dosis_confirmadas_por_nombre": "dosis confirmadas con la hoja",
    "fecha_confirmacion_dosis": "dosis confirmadas con la hoja", "sps_confirmado_por": "No. SPS confirmado con la hoja",
    "sps_confirmado_por_nombre": "No. SPS confirmado con la hoja", "sps_confirmado_en": "No. SPS confirmado con la hoja",
    "no_sps": "No. SPS corregido", "paciente_id": "paciente", "vigente": "anulación", "motivo_anulacion": "anulación",
    "anulada_por": "anulación", "anulada_por_nombre": "anulación", "fecha_anulacion": "anulación",
    "motivo_cierre": "cierre sin completar", "cerrada_por": "cierre sin completar", "fecha_cierre": "cierre sin completar",
    "cerrada_por_nombre": "cierre sin completar", "facturado": "facturado", "pagado": "pagado", "impreso": "impreso",
    "enviado": "enviado", "precio": "precio", "costo_override": "costo", "codigo": "código",
    "procedimiento": "procedimiento", "tipo": "tipo", "inyectable": "marca inyectable", "fecha_ingreso": "fecha de ingreso",
    "activo": "cupo liberado", "liberado_por": "cupo liberado", "liberado_por_nombre": "cupo liberado",
    "liberado_en": "cupo liberado", "motivo_liberacion": "cupo liberado",
}
ACCION_TEXTO = {
    "LIBRO_ATENCION_REGISTRADA": "Dosis o atención registrada", "LIBRO_ORDEN_EDITADA": "Orden editada",
    "LIBRO_ORDEN_ANULADA": "Orden anulada", "LIBRO_ORDEN_CERRADA_SIN_COMPLETAR": "Cerrada sin completar",
    "LIBRO_ORDEN_DOSIS_CONFIRMADAS": "Dosis confirmadas con la hoja", "LIBRO_ORDEN_SPS_CONFIRMADO": "No. SPS confirmado",
    "LIBRO_ATENCION_ASIGNADA": "Atención asignada", "LIBRO_ATENCION_REASIGNADA": "Atención reasignada",
    "LIBRO_AJUSTE_CUPO_LIBERADO": "Cupo sin SPS liberado", "CIRUGIA_REALIZADA": "Cirugía marcada realizada",
    "CIRUGIA_REALIZADA_REVERTIDA": "Cirugía desmarcada",
}


class Ejecutar(BaseModel):
    token: str = Field(..., min_length=10)
    palabra: str = ""


class SimularDeshacer(BaseModel):
    lote_id: str = Field(..., min_length=1)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ensure_migracion_indexes():
    specs = [
        (db.igss_libro_ajustes_cupo, [("acreditacion_id", 1)], {"unique": True, "name": "ajuste_acreditacion"}),
        (db.igss_libro_ajustes_cupo, [("nog_id", 1), ("activo", 1)], {"name": "ajuste_nog_activo"}),
        (db.igss_libro_ajustes_cupo, [("lote_migracion", 1)], {"name": "ajuste_lote"}),
        (db.igss_ordenes_libro, [("lote_migracion", 1)], {"name": "libro_lote_migracion", "sparse": True}),
        (db.igss_migracion_fotos, [("lote_id", 1)], {"name": "foto_lote"}),
        (db.igss_migracion_lotes, [("id", 1)], {"unique": True, "name": "lote_id"}),
    ]
    for col, keys, opts in specs:
        try:
            await col.create_index(keys, **opts)
        except Exception:
            pass


# ==================== UNA SOLA EJECUCIÓN A LA VEZ ====================

async def _tomar_turno(user: dict) -> str:
    turno, now = str(uuid.uuid4()), datetime.now(timezone.utc)
    try:
        await db.igss_migracion_turno.find_one_and_update(
            {"_id": TURNO_ID, "$or": [{"activo": False}, {"expira": {"$lt": now.isoformat()}}]},
            {"$set": {"activo": True, "turno": turno, "por": user.get("id", ""), "desde": now.isoformat(),
                      "expira": (now + timedelta(minutes=10)).isoformat()}}, upsert=True)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail=(
            "Ya hay una migración o un deshacer en curso (doble clic u otra pantalla). Solo corre uno: "
            "esta solicitud no ejecutó nada."))
    return turno


async def _soltar_turno(turno: str):
    await db.igss_migracion_turno.update_one({"_id": TURNO_ID, "turno": turno}, {"$set": {"activo": False}})


def _palabra(body: Ejecutar, esperada: str):
    if body.palabra.strip() != esperada:
        raise HTTPException(status_code=422, detail=f"Para confirmar escriba exactamente {esperada}.")


# ==================== APLICAR ====================

def _doc_orden(o: dict, nog: dict, lote_id: str, user: dict, ahora: str) -> dict:
    return {
        "id": str(uuid.uuid4()), "unidad_id": o["unidad_id"], "nog_id": o["nog_id"],
        "numero_nog": (nog.get("numero") or "").strip(), "tipo_compra": nog.get("tipo_compra", ""),
        "no_sps": o["no_sps"], "codigo": o["codigo"], "procedimiento": o["procedimiento"], "tipo": o["tipo"],
        "dosis_autorizadas": o["dosis_autorizadas"], "inyectable": o["inyectable"], "dosis_por_confirmar": o["viva"],
        "paciente_id": o["paciente_id"], "paciente_expediente": o["expediente"], "paciente_nombre": o["paciente_nombre"],
        "igss_afiliacion": o["igss_afiliacion"], "estado": "reservada" if o["viva"] else "historica", "vigente": True,
        "fecha_ingreso": o["fecha_ingreso"] or o["fecha_referencia"] or o["fecha_primera_atencion"] or today_str_gt(),
        "fecha_primera_atencion": None, "fecha_completa": None, "atenciones": [], "cirugias_programadas": [],
        "constancias": o["constancias"], "precio": o["precio"], "costo_override": None,
        "impreso": False, "enviado": False, "facturado": False, "pagado": False,
        "produccion_anterior": {k: o.get(k) for k in ("impreso", "enviado", "facturado", "pagado", "costo_override")},
        "anulada_por": None, "anulada_por_nombre": None, "fecha_anulacion": None, "motivo_anulacion": None,
        "sps_por_revisar": o["revisar_sps"], "sps_patron": o["sps_patron"],
        "origen": "migracion", "lote_migracion": lote_id, "migrada_en": ahora,
        "created_by": user.get("id", ""), "created_by_nombre": _nombre_usuario(user), "created_at": ahora, "updated_at": ahora,
    }


async def _crear_orden(o: dict, nog: dict, lote_id: str, user: dict, ahora: str) -> bool:
    doc = {**_doc_orden(o, nog, lote_id, user, ahora), "numero_libro": await siguiente_numero_libro()}
    try:
        await db.igss_ordenes_libro.insert_one(doc)
    except DuplicateKeyError:
        return False
    await db.igss_nogs.update_one({"id": o["nog_id"]}, {"$inc": {"libro_ocupados": 1}})
    if o["viva"]:
        for a in o["dosis_registradas"]:
            await agregar_atencion(doc["id"], {**a, "registrado_por": user.get("id", ""), "registrado_en": ahora}, exigir_dosis=False)
        await programar_existentes(doc)
    return True


async def _crear_ajuste(p: dict, lote_id: str, user: dict, ahora: str) -> bool:
    try:
        await db.igss_libro_ajustes_cupo.insert_one({
            "id": str(uuid.uuid4()), "lote_migracion": lote_id, "acreditacion_id": p["ref_id"], "nog_id": p["nog_id"],
            "unidad_id": p["unidad_id"], "paciente_id": p["paciente_id"], "paciente_nombre": p["paciente_nombre"],
            "paciente_expediente": p["expediente"], "fecha": p["fecha"], "activo": True,
            "created_by": user.get("id", ""), "created_by_nombre": _nombre_usuario(user), "created_at": ahora})
    except DuplicateKeyError:
        return False
    await db.igss_nogs.update_one({"id": p["nog_id"]}, {"$inc": {"libro_ocupados": 1}})
    return True


async def _guardar_fotos(lote_id: str) -> dict:
    """Foto de cada orden y cupo del lote tal como quedó al migrar (base del deshacer)."""
    await db.igss_migracion_fotos.delete_many({"lote_id": lote_id})
    n = {}
    for tipo, col in COLECCION.items():
        docs = await db[col].find({"lote_migracion": lote_id}, {"_id": 0}).to_list(None)
        if docs:
            await db.igss_migracion_fotos.insert_many([{"lote_id": lote_id, "tipo": tipo, "ref_id": x["id"], "doc": x} for x in docs])
        n[tipo] = len(docs)
    return n


async def _cifras_aplicadas(lote_id: str, simuladas: dict) -> dict:
    """Lo que quedó realmente en el libro, leído de la base de datos."""
    ords = await db.igss_ordenes_libro.find({"lote_migracion": lote_id}, {"_id": 0}).to_list(None)
    vivas = [o for o in ords if o.get("estado") != "historica"]
    const = [c for o in ords for c in o.get("constancias") or []]
    return {
        "ordenes_vivas": len(vivas),
        "vivas_reservadas": sum(1 for o in vivas if o.get("estado") == "reservada"),
        "vivas_en_curso": sum(1 for o in vivas if o.get("estado") == "en_curso"),
        "ordenes_historicas": len(ords) - len(vivas),
        "constancias_evaluaciones": sum(1 for c in const if c.get("tipo") == "evaluacion"),
        "constancias_cirugias": sum(1 for c in const if c.get("tipo") == "cirugia"),
        "dosis_registradas": sum(1 for o in ords for a in o.get("atenciones") or [] if a.get("tipo") == "cirugia"),
        "cirugias_programadas_vivas": sum(len(o.get("cirugias_programadas") or []) for o in vivas),
        "sps_por_revisar": sum(1 for o in ords if o.get("sps_por_revisar")),
        "ajustes_cupo_sin_sps": await db.igss_libro_ajustes_cupo.count_documents({"lote_migracion": lote_id}),
        "no_migrables": simuladas["no_migrables"], "pendientes_sps": simuladas["pendientes_sps"],
    }


async def _aplicar(tok: dict, user: dict) -> dict:
    respaldo = await respaldo_reciente()
    if not respaldo["vigente"]:
        raise HTTPException(status_code=409, detail=(
            "No hay un respaldo completado en las últimas 24 horas. Haga un respaldo y vuelva a simular: no se ejecutó nada."))
    sim = await simular_migracion()
    if sim["huella"] != tok["huella"]:
        raise HTTPException(status_code=409, detail=(
            "Los datos cambiaron desde la simulación. Simule de nuevo y revise las cifras: no se ejecutó nada."))
    if not sim["aplicacion_permitida"]:
        raise HTTPException(status_code=409, detail=(
            f"La simulación tiene {sim['bloqueos_totales']} bloqueo(s) (mismo No. SPS en dos unidades duplicadas): "
            "no se ejecutó nada."))
    ajustes = [p for p in sim["pendientes_sps"] if p["tipo"] == "cupo_sin_sps" and p["nog_id"] and not p.get("ajuste_existente")]
    if not sim["ordenes"] and not ajustes:
        raise HTTPException(status_code=409, detail="No hay nada que migrar: todo ya está en el libro. No se creó nada.")
    simuladas = {c["clave"]: c["valor"] for c in sim["cifras_lote"]}
    lote_id, ahora = str(uuid.uuid4()), _ahora()
    await db.igss_migracion_lotes.insert_one({
        "id": lote_id, "estado": "aplicando", "creado_por": user.get("id", ""), "creado_por_nombre": _nombre_usuario(user),
        "creado_en": ahora, "simulacion_generada": sim["generado"], "huella": sim["huella"], "respaldo": respaldo,
        "cifras_simuladas": simuladas})
    nogs = {n["id"]: n for n in await db.igss_nogs.find(
        {"id": {"$in": list({o["nog_id"] for o in sim["ordenes"]})}}, {"_id": 0}).to_list(None)}
    omitidas, estado, error = [], "aplicado", None
    try:
        for o in sim["ordenes"]:
            if not await _crear_orden(o, nogs.get(o["nog_id"]) or {}, lote_id, user, ahora):
                omitidas.append({"no_sps": o["no_sps"], "unidad": o.get("unidad", ""), "paciente_nombre": o["paciente_nombre"],
                                 "motivo": "Ya había una orden vigente con ese No. SPS en la unidad"})
        for p in ajustes:
            await _crear_ajuste(p, lote_id, user, ahora)
    except Exception as e:
        estado, error = "incompleto", str(e)[:300]
    fotos = await _guardar_fotos(lote_id)
    aplicadas = await _cifras_aplicadas(lote_id, simuladas)
    comparacion = [{"clave": k, "concepto": t, "simulado": simuladas[k], "aplicado": aplicadas[k],
                    "igual": simuladas[k] == aplicadas[k]} for k, t in CIFRAS_LOTE]
    diferencias = [c["clave"] for c in comparacion if not c["igual"]]
    await db.igss_migracion_lotes.update_one({"id": lote_id}, {"$set": {
        "estado": estado, "error": error, "aplicado_en": _ahora(), "cifras_aplicadas": aplicadas, "comparacion": comparacion,
        "omitidas": omitidas, "ordenes": fotos.get("orden", 0), "ajustes": fotos.get("ajuste", 0)}})
    await _audit("MIGRACION_LIBRO_APLICADA", user, {"lote_id": lote_id, "estado": estado, "ordenes": fotos.get("orden", 0),
                                                    "ajustes": fotos.get("ajuste", 0), "diferencias": diferencias, "error": error})
    if error:
        raise HTTPException(status_code=500, detail=(
            f"La migración se detuvo por un error ({error}). Lo creado quedó en el lote {lote_id}: revíselo y deshágalo."))
    return {"lote_id": lote_id, "estado": estado, "comparacion": comparacion, "diferencias": diferencias,
            "omitidas": omitidas, "ordenes": fotos.get("orden", 0), "ajustes": fotos.get("ajuste", 0)}


@router.post("/aplicar")
async def aplicar(body: Ejecutar, current_user: dict = Depends(SOLO_SUPERADMIN)):
    """Paso (b): crea en el libro exactamente lo de la simulación revisada (token de 30 minutos)."""
    _palabra(body, PALABRA_APLICAR)
    tok = leer_token(body.token, "aplicar", current_user)
    turno = await _tomar_turno(current_user)
    try:
        return await _aplicar(tok, current_user)
    finally:
        await _soltar_turno(turno)


@router.get("/lotes")
async def lotes(current_user: dict = Depends(SOLO_SUPERADMIN)):
    docs = await db.igss_migracion_lotes.find({}, {"_id": 0, "huella": 0}).sort("creado_en", -1).to_list(50)
    return {"data": docs, "total": len(docs)}


# ==================== DESHACER ====================

async def _lote_or_404(lote_id: str) -> dict:
    lote = await db.igss_migracion_lotes.find_one({"id": lote_id}, {"_id": 0})
    if not lote:
        raise HTTPException(status_code=404, detail="Lote de migración no encontrado")
    return lote


def _diferencias(foto: dict, actual) -> list:
    if actual is None:
        return ["se borró del libro"]
    doc = foto["doc"]
    claves = {k for k in set(doc) | set(actual) if doc.get(k) != actual.get(k)}
    return sorted({TEXTO_CAMPO.get(k, k) for k in claves if k not in NO_SE_MUESTRAN}) or ["datos de control"]


def _cirugias_tocadas(foto: dict, actual) -> set:
    ref = lambda lst: {(x.get("ref_id"), x.get("fecha")) for x in lst or []}  # noqa: E731
    antes = ref(foto["doc"].get("cirugias_programadas")) | ref(foto["doc"].get("atenciones"))
    despues = ref((actual or {}).get("cirugias_programadas")) | ref((actual or {}).get("atenciones"))
    return {r for r, _ in antes ^ despues if r}


async def _registros(desde: str, orden_ids: list, cx_por_orden: dict) -> dict:
    """Quién y cuándo: la auditoría desde la migración, por orden (o por su cirugía)."""
    cx_ids = [c for cs in cx_por_orden.values() for c in cs]
    filtro = {"timestamp": {"$gte": desde}, "$or": [
        {"details.orden_id": {"$in": orden_ids}}, {"details.orden_anterior": {"$in": orden_ids}},
        {"details.orden_destino": {"$in": orden_ids}}, {"details.ajuste_id": {"$in": orden_ids}},
        {"details.surgery_id": {"$in": cx_ids}}]}
    out = {}
    async for a in db.audit_logs.find(filtro, {"_id": 0}).sort("timestamp", 1):
        det = a.get("details") or {}
        destinos = {det.get(k) for k in ("orden_id", "orden_anterior", "orden_destino", "ajuste_id")} & set(orden_ids)
        destinos |= {oid for oid, cs in cx_por_orden.items() if det.get("surgery_id") in cs}
        for oid in destinos:
            out.setdefault(oid, []).append({"accion": ACCION_TEXTO.get(a.get("action"), a.get("action", "")),
                                            "quien": a.get("user_name") or "—", "cuando": a.get("timestamp", "")})
    return out


async def _revisar(lote: dict) -> dict:
    """Compara cada orden y cupo del lote con su foto al migrar. Cualquier diferencia impide deshacer."""
    fotos = await db.igss_migracion_fotos.find({"lote_id": lote["id"]}, {"_id": 0}).to_list(None)
    actuales = {}
    for tipo, col in COLECCION.items():
        for x in await db[col].find({"lote_migracion": lote["id"]}, {"_id": 0}).to_list(None):
            actuales[(tipo, x["id"])] = x
    cambiadas = [f for f in fotos if actuales.get((f["tipo"], f["ref_id"])) != f["doc"]]
    cx_por_orden = {f["ref_id"]: _cirugias_tocadas(f, actuales.get((f["tipo"], f["ref_id"]))) for f in cambiadas}
    regs = await _registros(lote.get("creado_en", ""), [f["ref_id"] for f in cambiadas], cx_por_orden)
    cambios = []
    for f in cambiadas:
        actual = actuales.get((f["tipo"], f["ref_id"]))
        base = actual or f["doc"]
        cambios.append({
            "tipo": f["tipo"], "id": f["ref_id"], "numero_libro": base.get("numero_libro", ""), "no_sps": base.get("no_sps", ""),
            "paciente_nombre": base.get("paciente_nombre", ""),
            "estado": base.get("estado") or ("cupo activo" if base.get("activo") else "cupo liberado"),
            "que_cambio": _diferencias(f, actual),
            "registros": regs.get(f["ref_id"]) or [{"accion": "Cambio sin registro de auditoría (automático)",
                                                    "quien": "—", "cuando": (actual or {}).get("updated_at", "")}]})
    fotos_ids = {(f["tipo"], f["ref_id"]) for f in fotos}
    for (tipo, rid), x in actuales.items():
        if (tipo, rid) not in fotos_ids:
            cambios.append({"tipo": tipo, "id": rid, "numero_libro": x.get("numero_libro", ""), "no_sps": x.get("no_sps", ""),
                            "paciente_nombre": x.get("paciente_nombre", ""), "estado": x.get("estado", ""),
                            "que_cambio": ["registro agregado al lote después de migrar"], "registros": []})
    return {"fotos": fotos, "cambios": cambios, "huella": huella_datos({"fotos": fotos, "actuales": list(actuales.values())})}


def _motivo_no(lote: dict, cambios: list) -> str:
    if lote["estado"] not in DESHACIBLES:
        return "Este lote ya se deshizo." if lote["estado"] == "deshecho" else "Este lote no terminó de aplicarse."
    if cambios:
        return (f"No se puede deshacer: {len(cambios)} orden(es) o cupo(s) del lote cambiaron después de migrar. "
                "El deshacer es todo o nada y no se puede forzar.")
    return ""


@router.post("/deshacer/simular")
async def simular_deshacer(body: SimularDeshacer, current_user: dict = Depends(SOLO_SUPERADMIN)):
    """Revisión previa del deshacer (solo lectura): qué se borraría y si algo cambió desde la migración."""
    lote = await _lote_or_404(body.lote_id)
    rev = await _revisar(lote)
    n = Counter(f["tipo"] for f in rev["fotos"])
    motivo = _motivo_no(lote, rev["cambios"])
    out = {"lote_id": lote["id"], "estado": lote["estado"], "creado_en": lote.get("creado_en", ""),
           "creado_por_nombre": lote.get("creado_por_nombre", ""), "ordenes": n["orden"], "ajustes": n["ajuste"],
           "cambios": rev["cambios"], "puede_deshacer": not motivo, "motivo": motivo}
    if not motivo:
        out["token_deshacer"], out["vence"] = emitir_token("deshacer", current_user, rev["huella"], lote_id=lote["id"])
    return out


async def _borrar_todo(fotos: list):
    """Borra cada registro solo si sigue igual a su foto; si uno no coincide, restaura lo borrado."""
    borrados = []
    for f in fotos:
        filtro = {"id": f["ref_id"], "lote_migracion": f["doc"].get("lote_migracion"),
                  **{k: f["doc"].get(k) for k in GUARDA[f["tipo"]]}}
        r = await db[COLECCION[f["tipo"]]].delete_one(filtro)
        if r.deleted_count != 1:
            for b in borrados:
                await db[COLECCION[b["tipo"]]].insert_one(dict(b["doc"]))
            raise HTTPException(status_code=409, detail={
                "mensaje": "Un registro del lote cambió mientras se deshacía: se restauró todo y no se deshizo nada.",
                "cambios": []})
        borrados.append(f)


async def _deshacer(tok: dict, user: dict) -> dict:
    lote = await _lote_or_404(tok.get("lote_id", ""))
    rev = await _revisar(lote)
    motivo = _motivo_no(lote, rev["cambios"])
    if motivo:
        raise HTTPException(status_code=409, detail={"mensaje": motivo, "cambios": rev["cambios"]})
    if rev["huella"] != tok["huella"]:
        raise HTTPException(status_code=409, detail={
            "mensaje": "El lote cambió desde la revisión del deshacer. Revise de nuevo: no se ejecutó nada.", "cambios": []})
    await _borrar_todo(rev["fotos"])
    cupos = Counter(f["doc"]["nog_id"] for f in rev["fotos"]
                    if (f["tipo"] == "orden" and f["doc"].get("estado") in ESTADOS_CUPO)
                    or (f["tipo"] == "ajuste" and f["doc"].get("activo")))
    for nog_id, n in cupos.items():
        await db.igss_nogs.update_one({"id": nog_id}, [{"$set": {"libro_ocupados": {
            "$max": [0, {"$subtract": [{"$ifNull": ["$libro_ocupados", 0]}, n]}]}}}])
    n = Counter(f["tipo"] for f in rev["fotos"])
    await db.igss_migracion_lotes.update_one({"id": lote["id"]}, {"$set": {
        "estado": "deshecho", "deshecho_por": user.get("id", ""), "deshecho_por_nombre": _nombre_usuario(user),
        "deshecho_en": _ahora(), "ordenes_borradas": n["orden"], "ajustes_borrados": n["ajuste"]}})
    await _audit("MIGRACION_LIBRO_DESHECHA", user, {"lote_id": lote["id"], "ordenes_borradas": n["orden"],
                                                    "ajustes_borrados": n["ajuste"]})
    return {"lote_id": lote["id"], "estado": "deshecho", "ordenes_borradas": n["orden"], "ajustes_borrados": n["ajuste"]}


@router.post("/deshacer")
async def deshacer(body: Ejecutar, current_user: dict = Depends(SOLO_SUPERADMIN)):
    """Borra todo lo del lote (órdenes y cupos sin SPS) y devuelve los cupos. Se niega si algo cambió."""
    _palabra(body, PALABRA_DESHACER)
    tok = leer_token(body.token, "deshacer", current_user)
    turno = await _tomar_turno(current_user)
    try:
        return await _deshacer(tok, current_user)
    finally:
        await _soltar_turno(turno)
