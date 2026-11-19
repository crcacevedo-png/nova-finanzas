# /app/backend/routes/igss_libro_atenciones.py
# Libro de órdenes IGSS — Fase 2: registro automático de atenciones (evaluación real /
# cirugía realizada), control de dosis, "atenciones sin orden", interruptor de exigencia
# y opciones de orden para roles clínicos (solo procedimiento y fecha de ingreso).
# El registro automático NO depende del rol de quien guarda y nunca devuelve datos del
# libro a roles fuera de LIBRO_IGSS_ROLES.

import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from config.database import db
from config.permissions import INGRESO_ORDEN_ROLES, LIBRO_IGSS_ROLES
from routes.auth import require_any_permission, require_role
from routes.igss_libro import (ESTADO_TEXTO, ESTADOS_VIGENTES, _audit, _expr_cirugias, _lit, _nombre_usuario,
                               _orden_out, crear_orden_libro, es_rol_libro, etapas_estado, normalizar_sps,
                               orden_ingreso_out, siguiente_numero_libro)
from routes.igss_nogs import TIPO_COMPRA_LABELS, etiqueta_catalogo, eval_es_borrador_vacio
from utils.timezone import today_str_gt

router = APIRouter(prefix="/igss-units/libro", tags=["IGSS - Libro de órdenes"])
pacientes_router = APIRouter(prefix="/patients", tags=["Pacientes"])
logger = logging.getLogger("igss_libro")

CONFIG_ID = "libro_igss"
NINGUNA = "ninguna"
AVISO_GENERICO = "La atención IGSS quedó pendiente de revisión por Administración IGSS."
MSG_SPS_SIN_ORDEN = ("El No. SPS indicado no corresponde a una orden IGSS vigente de este paciente. "
                     "Solicite a Administración IGSS que registre la orden.")


def msg_dosis_completas(n: int) -> str:
    return f"Esta orden ya completó sus {n} dosis. Se requiere una nueva orden (No. SPS)."


# ==================== CONFIGURACIÓN (INTERRUPTOR) ====================

async def get_config() -> dict:
    c = await db.igss_libro_config.find_one({"id": CONFIG_ID}, {"_id": 0})
    return c or {"id": CONFIG_ID, "exigir_orden": False, "usar_solo_libro": False}


async def exigencia_activa() -> bool:
    return bool((await get_config()).get("exigir_orden"))


async def _pendientes_sin_orden() -> int:
    return await db.igss_atenciones_sin_orden.count_documents({"estado": "pendiente"})


# ==================== OPERACIONES ATÓMICAS SOBRE LA ORDEN ====================

async def agregar_atencion(orden_id: str, atencion: dict, exigir_dosis: bool):
    """Agrega una atención a la orden en UNA operación atómica. En cirugías calcula
    numero_dosis (consecutivo) y marca excede_dosis; con exigir_dosis=True la condición
    impide superar dosis_autorizadas. El estado se recalcula (en curso / completa según el
    tipo de la orden). Devuelve la orden actualizada o None."""
    es_cx = atencion["tipo"] == "cirugia"
    filtro = {"id": orden_id, "estado": {"$in": list(ESTADOS_VIGENTES)},
              "atenciones": {"$not": {"$elemMatch": {"tipo": atencion["tipo"], "ref_id": atencion["ref_id"]}}}}
    if es_cx and exigir_dosis:
        filtro["$expr"] = {"$lt": [_expr_cirugias(), "$dosis_autorizadas"]}
    nueva = {k: _lit(v) for k, v in atencion.items()}
    nueva["numero_dosis"] = {"$add": [_expr_cirugias(), 1]} if es_cx else None
    nueva["excede_dosis"] = {"$gte": [_expr_cirugias(), "$dosis_autorizadas"]} if es_cx else False
    fecha = _lit(atencion.get("fecha") or "")
    pipeline = [{"$set": {
        "atenciones": {"$concatArrays": [{"$ifNull": ["$atenciones", []]}, [nueva]]},
        "fecha_primera_atencion": {"$cond": [
            {"$or": [{"$not": ["$fecha_primera_atencion"]}, {"$lt": [fecha, "$fecha_primera_atencion"]}]},
            fecha, "$fecha_primera_atencion"]},
        "updated_at": _lit(datetime.now(timezone.utc).isoformat()),
    }}, *etapas_estado()]
    return await db.igss_ordenes_libro.find_one_and_update(
        filtro, pipeline, projection={"_id": 0}, return_document=ReturnDocument.AFTER)


async def quitar_atencion(tipo: str, ref_id: str):
    """Quita la atención (tipo, ref_id) de la orden que la tenga, renumera las dosis y
    recalcula el estado (reservada si queda sin atenciones). Devuelve la orden ANTES."""
    sin_ella = {"$filter": {"input": {"$ifNull": ["$atenciones", []]},
                            "cond": {"$not": [{"$and": [{"$eq": ["$$this.tipo", _lit(tipo)]},
                                                        {"$eq": ["$$this.ref_id", _lit(ref_id)]}]}]}}}
    renumeradas = {"$reduce": {"input": sin_ella, "initialValue": {"n": 0, "arr": []}, "in": {"$let": {
        "vars": {"cx": {"$eq": ["$$this.tipo", "cirugia"]}},
        "in": {"n": {"$cond": ["$$cx", {"$add": ["$$value.n", 1]}, "$$value.n"]},
               "arr": {"$concatArrays": ["$$value.arr", [{"$cond": ["$$cx", {"$mergeObjects": [
                   "$$this", {"numero_dosis": {"$add": ["$$value.n", 1]},
                              "excede_dosis": {"$gt": [{"$add": ["$$value.n", 1]}, "$dosis_autorizadas"]}}]},
                   "$$this"]}]]}}}}}}
    pipeline = [
        {"$set": {"_tmp": renumeradas}},
        {"$set": {"atenciones": "$_tmp.arr"}},
        {"$unset": "_tmp"},
        {"$set": {
            "fecha_primera_atencion": {"$cond": [{"$gt": [{"$size": "$atenciones"}, 0]},
                                                 {"$min": "$atenciones.fecha"}, None]},
            "updated_at": _lit(datetime.now(timezone.utc).isoformat()),
        }},
        *etapas_estado(),
    ]
    return await db.igss_ordenes_libro.find_one_and_update(
        {"atenciones": {"$elemMatch": {"tipo": tipo, "ref_id": ref_id}}}, pipeline,
        projection={"_id": 0}, return_document=ReturnDocument.BEFORE)


def _sin_programada(ref_id: str):
    return {"$filter": {"input": {"$ifNull": ["$cirugias_programadas", []]},
                        "cond": {"$ne": ["$$this.ref_id", _lit(ref_id)]}}}


async def programar_cirugia(cx: dict, destino: Optional[dict] = None):
    """Deja la cirugía IGSS PROGRAMADA (activa) anotada en `cirugias_programadas` de su
    orden (una orden de 1 servicio pasa a "en curso"); realizada, cancelada, eliminada o
    sin orden, la quita de donde esté. Recalcula el estado en la misma operación."""
    ref = cx["id"]
    if cx.get("institution") == "IGSS" and cx.get("status") == "activo":
        destino = destino or await orden_de_cirugia(cx)
    else:
        destino = None
    otras = {"cirugias_programadas.ref_id": ref}
    if destino:
        otras["id"] = {"$ne": destino["id"]}
    await db.igss_ordenes_libro.update_many(otras, [{"$set": {"cirugias_programadas": _sin_programada(ref)}}, *etapas_estado()])
    if destino:
        nueva = _lit({"ref_id": ref, "fecha": (cx.get("date") or "")[:10]})
        await db.igss_ordenes_libro.update_one(
            {"id": destino["id"], "estado": {"$in": list(ESTADOS_VIGENTES)}},
            [{"$set": {"cirugias_programadas": {"$concatArrays": [_sin_programada(ref), [nueva]]}}}, *etapas_estado()])


async def programar_existentes(orden: dict) -> dict:
    """Orden ingresada (o con No. SPS / paciente cambiado) DESPUÉS de programar su cirugía:
    anota las cirugías IGSS activas del paciente con ese No. SPS y quita las que ya no le
    corresponden. Devuelve la orden actualizada."""
    for p in orden.get("cirugias_programadas") or []:
        await programar_cirugia(await db.surgeries.find_one({"id": p["ref_id"]}, {"_id": 0}) or {"id": p["ref_id"]})
    async for cx in db.surgeries.find({"institution": "IGSS", "status": "activo", "patient_id": orden.get("paciente_id")},
                                      {"_id": 0}):
        if cx.get("igss_orden_id") == orden["id"] or normalizar_sps((cx.get("igss_data") or {}).get("sps")) == orden.get("no_sps"):
            await programar_cirugia(cx)
    return await db.igss_ordenes_libro.find_one({"id": orden["id"]}, {"_id": 0}) or orden


async def _motivo_no_admite(orden_id: str) -> str:
    o = await db.igss_ordenes_libro.find_one({"id": orden_id}, {"_id": 0, "no_sps": 1, "estado": 1}) or {}
    return f"La orden {o.get('no_sps', '')} está {ESTADO_TEXTO.get(o.get('estado'), o.get('estado', ''))} y no admite atenciones nuevas"


async def _orden_con_atencion(tipo: str, ref_id: str):
    return await db.igss_ordenes_libro.find_one(
        {"atenciones": {"$elemMatch": {"tipo": tipo, "ref_id": ref_id}}}, {"_id": 0})


def _atencion_de(orden: dict, tipo: str, ref_id: str) -> dict:
    return next((a for a in orden.get("atenciones") or [] if a.get("tipo") == tipo and a.get("ref_id") == ref_id), {})


def _cirugias(orden: dict) -> int:
    return sum(1 for a in orden.get("atenciones") or [] if a.get("tipo") == "cirugia")


# ==================== ATENCIONES SIN ORDEN ====================

async def registrar_sin_orden(tipo: str, ref_id: str, motivo: str, datos: dict, user: dict):
    """Crea o actualiza (idempotente) la entrada pendiente de "atenciones sin orden"."""
    now = datetime.now(timezone.utc).isoformat()
    campos = {"motivo": motivo, "updated_at": now, **datos}
    res = None
    for _ in range(2):
        try:
            res = await db.igss_atenciones_sin_orden.find_one_and_update(
                {"tipo": tipo, "ref_id": ref_id, "estado": "pendiente"},
                {"$set": campos, "$setOnInsert": {
                    "id": str(uuid.uuid4()), "created_at": now,
                    "registrado_por": (user or {}).get("id", ""), "registrado_por_nombre": _nombre_usuario(user)}},
                upsert=True, projection={"_id": 0}, return_document=ReturnDocument.BEFORE)
            break
        except DuplicateKeyError:
            continue
    if res is None or res.get("motivo") != motivo:
        await _audit("LIBRO_ATENCION_SIN_ORDEN", user, {"tipo": tipo, "ref_id": ref_id, "motivo": motivo,
                                                        "paciente_id": datos.get("paciente_id")})


async def cerrar_sin_orden(tipo: str, ref_id: str, estado: str, user: dict, orden_id: str = None, motivo: str = None):
    await db.igss_atenciones_sin_orden.update_many(
        {"tipo": tipo, "ref_id": ref_id, "estado": "pendiente"},
        {"$set": {"estado": estado, "orden_id": orden_id, "motivo_cierre": motivo,
                  "resuelta_por": (user or {}).get("id", ""), "resuelta_por_nombre": _nombre_usuario(user),
                  "resuelta_en": datetime.now(timezone.utc).isoformat()}})


# ==================== EVALUACIONES ====================

def _datos_paciente(p: dict) -> dict:
    return {"paciente_id": p.get("id", ""), "paciente_expediente": p.get("record_number", ""),
            "paciente_nombre": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "unidad_id": p.get("igss_unit_id", "")}


async def sincronizar_evaluacion(evaluacion: dict, user: dict) -> dict:
    """Deja la evaluación registrada en la orden elegida (igss_orden_id) o en "atenciones
    sin orden". Idempotente: mueve la atención si cambió la orden, la fecha o el médico."""
    ev_id = evaluacion["id"]
    paciente = await db.patients.find_one(
        {"id": evaluacion.get("paciente_id")},
        {"_id": 0, "id": 1, "record_number": 1, "first_name": 1, "last_name": 1,
         "referral_institution": 1, "igss_unit_id": 1, "igss_ordenes": 1})
    if not paciente or paciente.get("referral_institution") != "igss" or eval_es_borrador_vacio(evaluacion):
        await quitar_atencion("evaluacion", ev_id)
        await cerrar_sin_orden("evaluacion", ev_id, "descartada", user, motivo="No aplica (paciente no IGSS o evaluación vacía)")
        return {"resultado": "no_aplica"}

    sel = (evaluacion.get("igss_orden_id") or "").strip()
    destino, motivo, falla = None, None, False
    if sel == NINGUNA:
        motivo = "Se eligió 'Ninguna de estas / no sé'"
    elif sel:
        destino = await db.igss_ordenes_libro.find_one({"id": sel, "vigente": True}, {"_id": 0})
        if destino and destino.get("paciente_id") != paciente["id"]:
            destino, motivo, falla = None, "La orden elegida pertenece a otro paciente", True
    if not destino and not motivo:
        sps = normalizar_sps(evaluacion.get("igss_no_sps"))
        if sps:
            destino = await db.igss_ordenes_libro.find_one(
                {"paciente_id": paciente["id"], "no_sps": sps, "vigente": True}, {"_id": 0})
            if not destino:
                legado = next((o for o in paciente.get("igss_ordenes") or [] if o.get("id") == sel), {})
                nog_id = evaluacion.get("igss_nog_id") or legado.get("nog_id")
                if nog_id:
                    try:
                        destino, _ = await crear_orden_libro({
                            "nog_id": nog_id, "paciente_id": paciente["id"], "no_sps": sps,
                            "tipo": "consulta", "codigo": evaluacion.get("igss_codigo") or legado.get("codigo", ""),
                            "procedimiento": evaluacion.get("igss_procedimiento") or legado.get("procedimiento", "")},
                            user, origen="evaluacion")
                    except HTTPException as e:
                        motivo, falla = f"No se pudo crear la orden {sps}: {e.detail}", True
                else:
                    motivo, falla = f"El No. SPS {sps} de la evaluación no tiene orden en el libro", True
        elif sel:
            motivo, falla = "La orden elegida no está en el libro (orden anterior al libro)", True
        else:
            motivo = "Sin orden seleccionada (el paciente no tenía órdenes abiertas)"

    atencion = {"tipo": "evaluacion", "ref_id": ev_id, "fecha": (evaluacion.get("fecha") or "")[:10],
                "medico": evaluacion.get("medico_nombre") or "",
                "registrado_por": (user or {}).get("id", ""), "registrado_en": datetime.now(timezone.utc).isoformat()}
    actual = await _orden_con_atencion("evaluacion", ev_id)
    if destino and actual and actual["id"] == destino["id"]:
        previa = _atencion_de(actual, "evaluacion", ev_id)
        if previa.get("fecha") == atencion["fecha"] and previa.get("medico") == atencion["medico"]:
            await cerrar_sin_orden("evaluacion", ev_id, "resuelta", user, orden_id=destino["id"])
            return {"resultado": "registrada", "orden_id": destino["id"]}
    if actual:
        await quitar_atencion("evaluacion", ev_id)
    if destino:
        if await agregar_atencion(destino["id"], atencion, exigir_dosis=False):
            await cerrar_sin_orden("evaluacion", ev_id, "resuelta", user, orden_id=destino["id"])
            await _audit("LIBRO_ATENCION_REGISTRADA", user, {"tipo": "evaluacion", "ref_id": ev_id,
                                                              "orden_id": destino["id"], "no_sps": destino.get("no_sps")})
            return {"resultado": "registrada", "orden_id": destino["id"]}
        motivo, falla = await _motivo_no_admite(destino["id"]), True
    await registrar_sin_orden("evaluacion", ev_id, motivo, {
        **_datos_paciente(paciente), "fecha": atencion["fecha"], "medico": atencion["medico"],
        "procedimiento": evaluacion.get("igss_procedimiento") or evaluacion.get("motivo_consulta", "")[:120]}, user)
    return {"resultado": "sin_orden", "motivo": motivo, "falla": falla}


async def registrar_evaluacion_seguro(evaluacion: dict, user: dict) -> Optional[str]:
    """Envuelve la sincronización: nunca bloquea el guardado. Devuelve el aviso genérico
    (sin datos del libro) si la atención no pudo registrarse por una falla."""
    try:
        r = await sincronizar_evaluacion(evaluacion, user)
        return AVISO_GENERICO if r.get("falla") else None
    except Exception as e:
        logger.exception("Registro de atención de evaluación %s falló", evaluacion.get("id"))
        try:
            await _audit("LIBRO_ATENCION_ERROR", user, {"tipo": "evaluacion", "ref_id": evaluacion.get("id"), "error": str(e)[:300]})
            await registrar_sin_orden("evaluacion", evaluacion.get("id"), f"Error al registrar: {str(e)[:200]}",
                                      {"paciente_id": evaluacion.get("paciente_id", ""),
                                       "paciente_nombre": evaluacion.get("paciente_nombre", ""),
                                       "fecha": (evaluacion.get("fecha") or "")[:10]}, user)
        except Exception:
            logger.exception("No se pudo registrar la atención sin orden")
        return AVISO_GENERICO


async def sincronizar_evaluacion_si_cambia(existing: dict, update_data: dict, user: dict) -> Optional[str]:
    """Tras editar/autoguardar: resincroniza si cambió la orden elegida, si la evaluación
    pasó a ser (o dejó de ser) borrador vacío, o si cambió fecha/médico/paciente de una
    evaluación que ya está en el libro o en "sin orden"."""
    def cambio(k):
        return k in update_data and (update_data.get(k) or "") != (existing.get(k) or "")
    ev_id = existing["id"]
    cambia_vacio = eval_es_borrador_vacio(existing) != eval_es_borrador_vacio({**existing, **update_data})
    if not (cambio("igss_orden_id") or cambio("igss_no_sps") or cambia_vacio):
        if not any(cambio(k) for k in ("fecha", "medico_nombre", "paciente_id")):
            return None
        en_libro = await db.igss_ordenes_libro.find_one({"atenciones": {"$elemMatch": {"tipo": "evaluacion", "ref_id": ev_id}}}, {"_id": 1})
        if not en_libro and not await db.igss_atenciones_sin_orden.find_one({"tipo": "evaluacion", "ref_id": ev_id, "estado": "pendiente"}, {"_id": 1}):
            return None
    ev = await db.evaluaciones_oftalmologicas.find_one({"id": ev_id}, {"_id": 0})
    return await registrar_evaluacion_seguro(ev, user) if ev else None


async def quitar_evaluacion(ev_id: str, user: dict):
    await quitar_atencion("evaluacion", ev_id)
    await cerrar_sin_orden("evaluacion", ev_id, "descartada", user, motivo="Evaluación eliminada")


# ==================== CIRUGÍAS ====================

async def orden_de_cirugia(cx: dict) -> Optional[dict]:
    """Orden vigente del paciente que corresponde a la cirugía (igss_orden_id o No. SPS)."""
    pid = cx.get("patient_id")
    if not pid:
        return None
    if cx.get("igss_orden_id"):
        o = await db.igss_ordenes_libro.find_one({"id": cx["igss_orden_id"], "vigente": True, "paciente_id": pid}, {"_id": 0})
        if o:
            return o
    sps = normalizar_sps((cx.get("igss_data") or {}).get("sps"))
    if not sps:
        return None
    return await db.igss_ordenes_libro.find_one({"paciente_id": pid, "no_sps": sps, "vigente": True}, {"_id": 0})


async def validar_cirugia_nueva(cx: dict):
    """Con el interruptor encendido, una cirugía IGSS nueva exige paciente y un No. SPS de
    una orden vigente del paciente con dosis disponibles. Devuelve la orden (o None)."""
    orden = await orden_de_cirugia(cx) if cx.get("institution") == "IGSS" else None
    if cx.get("institution") != "IGSS" or not await exigencia_activa():
        return orden
    if not cx.get("patient_id"):
        raise HTTPException(status_code=422, detail="La cirugía IGSS requiere un paciente registrado en el sistema.")
    if not orden:
        raise HTTPException(status_code=422, detail=MSG_SPS_SIN_ORDEN)
    if _cirugias(orden) >= int(orden.get("dosis_autorizadas") or 1):
        raise HTTPException(status_code=422, detail=msg_dosis_completas(int(orden.get("dosis_autorizadas") or 1)))
    return orden


async def validar_dosis_para_realizar(cx: dict):
    """Antes de marcar como realizada: con el interruptor encendido rechaza si la orden ya
    completó sus dosis. Sin orden no se bloquea (queda en atenciones sin orden)."""
    if cx.get("institution") != "IGSS" or not await exigencia_activa():
        return
    orden = await orden_de_cirugia(cx)
    if orden and not _atencion_de(orden, "cirugia", cx["id"]) and _cirugias(orden) >= int(orden.get("dosis_autorizadas") or 1):
        raise HTTPException(status_code=422, detail=msg_dosis_completas(int(orden.get("dosis_autorizadas") or 1)))


async def sincronizar_cirugia(cx: dict, user: dict) -> dict:
    """Registra la cirugía REALIZADA en su orden (numero_dosis consecutivo) o en
    "atenciones sin orden"; si ya no está realizada / no es IGSS, quita la atención."""
    ref = cx["id"]
    await programar_cirugia(cx)
    if cx.get("institution") != "IGSS" or cx.get("status") != "realizado":
        await quitar_atencion("cirugia", ref)
        await cerrar_sin_orden("cirugia", ref, "descartada", user, motivo="Cirugía no realizada o no IGSS")
        return {"resultado": "no_aplica"}
    exigir = await exigencia_activa()
    destino = await orden_de_cirugia(cx)
    atencion = {"tipo": "cirugia", "ref_id": ref, "fecha": (cx.get("date") or "")[:10],
                "medico": cx.get("surgeon") or "", "registrado_por": (user or {}).get("id", ""),
                "registrado_en": datetime.now(timezone.utc).isoformat()}
    actual = await _orden_con_atencion("cirugia", ref)
    if destino and actual and actual["id"] == destino["id"]:
        previa = _atencion_de(actual, "cirugia", ref)
        if previa.get("fecha") == atencion["fecha"] and previa.get("medico") == atencion["medico"]:
            return {"resultado": "registrada", "orden": actual}
    if actual:
        await quitar_atencion("cirugia", ref)
    if destino:
        orden = await agregar_atencion(destino["id"], atencion, exigir_dosis=True)
        if orden:
            if destino["id"] != cx.get("igss_orden_id"):
                await db.surgeries.update_one({"id": ref}, {"$set": {"igss_orden_id": destino["id"]}})
            await cerrar_sin_orden("cirugia", ref, "resuelta", user, orden_id=destino["id"])
            reg = _atencion_de(orden, "cirugia", ref)
            await _audit("LIBRO_ATENCION_REGISTRADA", user, {"tipo": "cirugia", "ref_id": ref, "orden_id": destino["id"],
                                                              "no_sps": destino.get("no_sps"), "numero_dosis": reg.get("numero_dosis")})
            return {"resultado": "registrada", "orden": orden}
        # Dosis completas: nunca se anota una dosis de más. Con el interruptor encendido se
        # rechaza; apagado, la cirugía queda en "atenciones sin orden" hasta elegir otra orden.
        fresca = await db.igss_ordenes_libro.find_one({"id": destino["id"]}, {"_id": 0}) or destino
        if fresca.get("estado") not in ESTADOS_VIGENTES:
            motivo = await _motivo_no_admite(destino["id"])
        else:
            n = int(fresca.get("dosis_autorizadas") or 1)
            if exigir:
                raise HTTPException(status_code=422, detail=msg_dosis_completas(n))
            motivo = f"La orden {fresca.get('no_sps', '')} ya completó sus {n} dosis: asigne una orden nueva (No. SPS)"
    elif not cx.get("patient_id"):
        motivo = "Cirugía sin paciente registrado"
    elif not normalizar_sps((cx.get("igss_data") or {}).get("sps")):
        motivo = "Cirugía sin No. SPS"
    else:
        motivo = f"El No. SPS {normalizar_sps(cx['igss_data'].get('sps'))} no corresponde a una orden vigente del paciente"
    pac = await db.patients.find_one({"id": cx.get("patient_id")}, {"_id": 0}) if cx.get("patient_id") else None
    datos = _datos_paciente(pac) if pac else {"paciente_id": "", "paciente_nombre": cx.get("patient_name", ""),
                                                 "paciente_expediente": "", "unidad_id": (cx.get("igss_data") or {}).get("unit_id", "")}
    await registrar_sin_orden("cirugia", ref, motivo, {
        **datos, "fecha": atencion["fecha"], "medico": atencion["medico"], "procedimiento": cx.get("procedure", ""),
        "no_sps_indicado": normalizar_sps((cx.get("igss_data") or {}).get("sps"))}, user)
    return {"resultado": "sin_orden", "motivo": motivo, "falla": True}


async def quitar_cirugia(ref_id: str, user: dict):
    await programar_cirugia({"id": ref_id})
    await quitar_atencion("cirugia", ref_id)
    await cerrar_sin_orden("cirugia", ref_id, "descartada", user, motivo="Cirugía eliminada")


def respuesta_registro(r: dict, user: dict) -> dict:
    """Lo que ve quien guarda: LIBRO_IGSS_ROLES reciben el detalle; los demás, solo un
    aviso genérico si hubo una falla."""
    if (user or {}).get("role") in LIBRO_IGSS_ROLES:
        o = r.get("orden") or {}
        out = {"resultado": r.get("resultado"), "motivo": r.get("motivo"), "no_sps": o.get("no_sps"),
               "numero_libro": o.get("numero_libro"), "estado": o.get("estado"),
               "dosis_aplicadas": _cirugias(o) if o else None, "dosis_autorizadas": o.get("dosis_autorizadas")}
        if o.get("dosis_por_confirmar") and out["dosis_aplicadas"] >= int(o.get("dosis_autorizadas") or 1):
            out["aviso"] = (f"La orden {o.get('numero_libro', '')} ({o.get('no_sps', '')}) llegó a sus "
                            f"{out['dosis_aplicadas']} dosis conocidas, pero falta confirmar las dosis con la hoja: "
                            "queda en curso y no se cobra hasta confirmarlas.")
        return {"libro": out}
    return {"aviso_igss": AVISO_GENERICO} if r.get("falla") else {}


# ==================== ÍNDICES ====================

async def ensure_atenciones_indexes():
    specs = [
        (db.igss_atenciones_sin_orden, [("tipo", 1), ("ref_id", 1)],
         {"unique": True, "name": "sin_orden_ref_pendiente", "partialFilterExpression": {"estado": "pendiente"}}),
        (db.igss_atenciones_sin_orden, [("estado", 1), ("created_at", -1)], {"name": "sin_orden_estado"}),
        (db.igss_ordenes_libro, [("atenciones.tipo", 1), ("atenciones.ref_id", 1)], {"name": "libro_atencion_ref"}),
    ]
    for col, keys, opts in specs:
        try:
            await col.create_index(keys, **opts)
        except Exception as e:
            logger.warning(f"Índice {opts['name']} no creado: {e}")


# ==================== ENDPOINTS: INTERRUPTOR ====================

class ConfigUpdate(BaseModel):
    exigir_orden: Optional[bool] = None
    usar_solo_libro: Optional[bool] = None


@router.get("/config")
async def ver_config(current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    return _config_out(await get_config(), await _pendientes_sin_orden())


def _config_out(c: dict, pendientes: int) -> dict:
    return {"exigir_orden": bool(c.get("exigir_orden")), "actualizado_por_nombre": c.get("actualizado_por_nombre"),
            "actualizado_en": c.get("actualizado_en"), "atenciones_sin_orden_pendientes": pendientes,
            "usar_solo_libro": bool(c.get("usar_solo_libro")),
            "solo_libro_actualizado_por_nombre": c.get("solo_libro_actualizado_por_nombre"),
            "solo_libro_actualizado_en": c.get("solo_libro_actualizado_en")}


@router.put("/config")
async def cambiar_config(body: ConfigUpdate, current_user: dict = Depends(require_role(["superadmin"]))):
    """Interruptores del libro (solo superadmin), cada cambio queda en audit_logs.
    exigir_orden — apagado: las cirugías sin orden o con la orden ya completa se guardan y
    quedan en "atenciones sin orden"; encendido: cirugía IGSS nueva exige orden y se
    rechaza la dosis de más.
    usar_solo_libro — encendido: nada escribe en el sistema anterior (acreditaciones,
    igss_produccion, contador acreditados) y sus recálculos quedan deshabilitados."""
    if body.exigir_orden is None and body.usar_solo_libro is None:
        raise HTTPException(status_code=400, detail="Indique el interruptor a cambiar")
    antes = await get_config()
    pendientes = await _pendientes_sin_orden()
    now = datetime.now(timezone.utc).isoformat()
    quien = {"id": current_user.get("id", ""), "nombre": _nombre_usuario(current_user)}
    cambios = {}
    if body.exigir_orden is not None:
        cambios.update({"exigir_orden": body.exigir_orden, "actualizado_por": quien["id"],
                        "actualizado_por_nombre": quien["nombre"], "actualizado_en": now})
    if body.usar_solo_libro is not None:
        cambios.update({"usar_solo_libro": body.usar_solo_libro, "solo_libro_actualizado_por": quien["id"],
                        "solo_libro_actualizado_por_nombre": quien["nombre"], "solo_libro_actualizado_en": now})
    await db.igss_libro_config.update_one({"id": CONFIG_ID}, {"$set": cambios}, upsert=True)
    if body.exigir_orden is not None:
        await _audit("LIBRO_INTERRUPTOR_CAMBIADO", current_user, {
            "antes": bool(antes.get("exigir_orden")), "despues": body.exigir_orden,
            "atenciones_sin_orden_pendientes": pendientes})
    if body.usar_solo_libro is not None:
        await _audit("LIBRO_SOLO_LIBRO_CAMBIADO", current_user, {
            "antes": bool(antes.get("usar_solo_libro")), "despues": body.usar_solo_libro})
    return _config_out({**antes, **cambios}, pendientes)


# ==================== ENDPOINTS: ATENCIONES SIN ORDEN Y REASIGNACIÓN ====================

class AsignarBody(BaseModel):
    orden_id: str = Field(..., min_length=1)


class DescartarBody(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)


class ReasignarBody(BaseModel):
    tipo: Literal["evaluacion", "cirugia"]
    ref_id: str = Field(..., min_length=1)
    orden_destino_id: Optional[str] = None


@router.get("/atenciones-sin-orden")
async def listar_sin_orden(
    estado: Literal["pendiente", "resuelta", "descartada"] = "pendiente",
    tipo: Optional[Literal["evaluacion", "cirugia"]] = None,
    unidad_id: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES)),
):
    filtro = {"estado": estado}
    if tipo:
        filtro["tipo"] = tipo
    if unidad_id:
        filtro["unidad_id"] = unidad_id
    if q and q.strip():
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        filtro["$or"] = [{"paciente_nombre": rx}, {"paciente_expediente": rx}, {"no_sps_indicado": rx}]
    total = await db.igss_atenciones_sin_orden.count_documents(filtro)
    docs = await db.igss_atenciones_sin_orden.find(filtro, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"data": docs, "total": total, "pendientes": await _pendientes_sin_orden()}


async def _vincular_fuente(tipo: str, ref_id: str, orden_id: Optional[str]):
    if tipo == "evaluacion":
        await db.evaluaciones_oftalmologicas.update_one({"id": ref_id}, {"$set": {"igss_orden_id": orden_id or NINGUNA}})
    else:
        await db.surgeries.update_one({"id": ref_id}, {"$set": {"igss_orden_id": orden_id}})


async def _fuente(tipo: str, ref_id: str) -> dict:
    if tipo == "evaluacion":
        ev = await db.evaluaciones_oftalmologicas.find_one({"id": ref_id}, {"_id": 0, "id": 1, "paciente_id": 1, "fecha": 1, "medico_nombre": 1})
        if not ev:
            raise HTTPException(status_code=404, detail="La evaluación ya no existe")
        return {"paciente_id": ev.get("paciente_id"), "fecha": (ev.get("fecha") or "")[:10], "medico": ev.get("medico_nombre") or ""}
    cx = await db.surgeries.find_one({"id": ref_id}, {"_id": 0, "id": 1, "patient_id": 1, "date": 1, "surgeon": 1, "status": 1, "institution": 1})
    if not cx:
        raise HTTPException(status_code=404, detail="La cirugía ya no existe")
    if cx.get("status") != "realizado":
        raise HTTPException(status_code=400, detail="La cirugía no está marcada como realizada")
    return {"paciente_id": cx.get("patient_id"), "fecha": (cx.get("date") or "")[:10], "medico": cx.get("surgeon") or ""}


async def _asignar(tipo: str, ref_id: str, orden_id: str, user: dict) -> dict:
    fuente = await _fuente(tipo, ref_id)
    destino = await db.igss_ordenes_libro.find_one({"id": orden_id}, {"_id": 0})
    if not destino or not destino.get("vigente", False):
        raise HTTPException(status_code=404, detail="Orden de destino no encontrada o anulada")
    if not fuente["paciente_id"] or destino.get("paciente_id") != fuente["paciente_id"]:
        raise HTTPException(status_code=422, detail="La orden de destino pertenece a otro paciente")
    if destino.get("estado") not in ESTADOS_VIGENTES:
        raise HTTPException(status_code=422, detail=await _motivo_no_admite(orden_id))
    if tipo == "cirugia" and not _atencion_de(destino, tipo, ref_id) \
            and _cirugias(destino) >= int(destino.get("dosis_autorizadas") or 1):
        raise HTTPException(status_code=422, detail=msg_dosis_completas(int(destino.get("dosis_autorizadas") or 1)))
    origen = await quitar_atencion(tipo, ref_id)
    atencion = {"tipo": tipo, "ref_id": ref_id, "fecha": fuente["fecha"], "medico": fuente["medico"],
                "registrado_por": user.get("id", ""), "registrado_en": datetime.now(timezone.utc).isoformat()}
    orden = await agregar_atencion(orden_id, atencion, exigir_dosis=(tipo == "cirugia"))
    if not orden:
        if origen and origen.get("vigente", False):
            await agregar_atencion(origen["id"], _atencion_de(origen, tipo, ref_id) or atencion, exigir_dosis=False)
        raise HTTPException(status_code=409, detail="No se pudo asignar: la orden cambió mientras tanto. Intente de nuevo.")
    await _vincular_fuente(tipo, ref_id, orden_id)
    await cerrar_sin_orden(tipo, ref_id, "resuelta", user, orden_id=orden_id)
    return {"orden_anterior": origen.get("id") if origen else None, "orden": orden}


@router.post("/atenciones-sin-orden/{entrada_id}/asignar")
async def asignar_sin_orden(entrada_id: str, body: AsignarBody, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    e = await db.igss_atenciones_sin_orden.find_one({"id": entrada_id}, {"_id": 0})
    if not e:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    if e.get("estado") != "pendiente":
        raise HTTPException(status_code=400, detail="La entrada ya fue resuelta o descartada")
    r = await _asignar(e["tipo"], e["ref_id"], body.orden_id, current_user)
    await _audit("LIBRO_ATENCION_ASIGNADA", current_user, {"entrada_id": entrada_id, "tipo": e["tipo"], "ref_id": e["ref_id"],
                                                          "orden_id": body.orden_id, "no_sps": r["orden"].get("no_sps")})
    return {"ok": True, "orden": _orden_out(r["orden"])}


@router.post("/atenciones-sin-orden/{entrada_id}/descartar")
async def descartar_sin_orden(entrada_id: str, body: DescartarBody, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    e = await db.igss_atenciones_sin_orden.find_one_and_update(
        {"id": entrada_id, "estado": "pendiente"},
        {"$set": {"estado": "descartada", "motivo_cierre": body.motivo.strip(), "resuelta_por": current_user.get("id", ""),
                  "resuelta_por_nombre": _nombre_usuario(current_user), "resuelta_en": datetime.now(timezone.utc).isoformat()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not e:
        raise HTTPException(status_code=404, detail="Entrada pendiente no encontrada")
    await _audit("LIBRO_ATENCION_DESCARTADA", current_user, {"entrada_id": entrada_id, "tipo": e["tipo"],
                                                            "ref_id": e["ref_id"], "motivo": body.motivo.strip()})
    return e


@router.post("/atenciones/reasignar")
async def reasignar_atencion(body: ReasignarBody, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Mueve una atención a otra orden del mismo paciente, o la deja "sin orden"."""
    if body.orden_destino_id:
        r = await _asignar(body.tipo, body.ref_id, body.orden_destino_id, current_user)
        destino = r["orden"]
    else:
        origen = await quitar_atencion(body.tipo, body.ref_id)
        if not origen:
            raise HTTPException(status_code=404, detail="La atención no está registrada en ninguna orden")
        await _vincular_fuente(body.tipo, body.ref_id, None)
        await registrar_sin_orden(body.tipo, body.ref_id, f"Quitada de su orden por {_nombre_usuario(current_user)}", {
            "paciente_id": origen.get("paciente_id", ""), "paciente_nombre": origen.get("paciente_nombre", ""),
            "paciente_expediente": origen.get("paciente_expediente", ""), "unidad_id": origen.get("unidad_id", ""),
            "fecha": _atencion_de(origen, body.tipo, body.ref_id).get("fecha", ""),
            "medico": _atencion_de(origen, body.tipo, body.ref_id).get("medico", "")}, current_user)
        r, destino = {"orden_anterior": origen["id"]}, None
    await _audit("LIBRO_ATENCION_REASIGNADA", current_user, {
        "tipo": body.tipo, "ref_id": body.ref_id, "orden_anterior": r.get("orden_anterior"),
        "orden_destino": body.orden_destino_id})
    return {"ok": True, "orden_anterior": r.get("orden_anterior"), "orden": _orden_out(destino) if destino else None}


# ==================== ENDPOINT: CATÁLOGO PARA LA FICHA (LIBRO) ====================

@router.get("/catalogo")
async def catalogo_para_ordenes(unidad_id: str = Query(..., min_length=1),
                                current_user: dict = Depends(require_role(INGRESO_ORDEN_ROLES))):
    """Entradas activas del catálogo de la unidad (con y sin número) y su cupo. Fuera del
    libro solo se indica si hay cupo (sin cifras ni precio)."""
    libro = es_rol_libro(current_user)
    nogs = await db.igss_nogs.find({"unidad_id": unidad_id, "is_active": {"$ne": False}}, {"_id": 0}).to_list(None)
    out = []
    for n in nogs:
        cant = int(n.get("cantidad") or 0)
        usados = int(n.get("libro_ocupados") or 0)
        sin_tope = bool(n.get("sin_tope"))
        fila = {"id": n["id"], "etiqueta": etiqueta_catalogo(n), "numero": n.get("numero", ""),
                "nombre_servicio": n.get("nombre_servicio", ""),
                "modalidad": TIPO_COMPRA_LABELS.get(n.get("tipo_compra", ""), n.get("tipo_compra", "")), "sin_tope": sin_tope}
        if libro:
            fila.update({"cantidad": None if sin_tope else cant, "ocupados": usados,
                         "disponibles": None if sin_tope else max(cant - usados, 0), "precio": n.get("precio", 0)})
        else:
            fila["con_cupo"] = sin_tope or usados < cant
        out.append(fila)
    out.sort(key=lambda x: (x["numero"] == "", x["etiqueta"]))
    return out


async def _procedimiento_constancias(docs: list):
    """Constancias de la migración (solo lectura): a las de cirugía les agrega el procedimiento y el ojo."""
    ids = {c.get("ref_id") for d in docs for c in d.get("constancias") or [] if c.get("tipo") == "cirugia"}
    if not ids:
        return
    cxs = {s["id"]: s for s in await db.surgeries.find(
        {"id": {"$in": list(ids)}}, {"_id": 0, "id": 1, "procedure": 1, "eye": 1}).to_list(None)}
    for d in docs:
        for c in d.get("constancias") or []:
            s = cxs.get(c.get("ref_id")) if c.get("tipo") == "cirugia" else None
            if s:
                c["procedimiento"] = " · ".join(x for x in (s.get("procedure"), s.get("eye")) if x)


@pacientes_router.get("/{patient_id}/igss-ordenes")
async def ordenes_del_paciente(patient_id: str, current_user: dict = Depends(require_role(INGRESO_ORDEN_ROLES))):
    """Órdenes del libro de un paciente para la ficha: con No. SPS y NOG. Los roles del libro
    reciben todo; quien solo ingresa no ve precio ni marcas de cobro, y sabe cuáles puede corregir."""
    docs = await db.igss_ordenes_libro.find({"paciente_id": patient_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    await _procedimiento_constancias(docs)
    nogs = {n["id"]: n for n in await db.igss_nogs.find(
        {"id": {"$in": list({d.get("nog_id") for d in docs})}}, {"_id": 0}).to_list(None)}
    out = [_orden_out(d, nogs.get(d.get("nog_id"))) for d in docs]
    return out if es_rol_libro(current_user) else [orden_ingreso_out(o, current_user) for o in out]


# ==================== ENDPOINT: OPCIONES PARA ROLES CLÍNICOS ====================

@pacientes_router.get("/{patient_id}/igss-ordenes-abiertas")
async def ordenes_abiertas_paciente(
    patient_id: str,
    current_user: dict = Depends(require_any_permission(["view_patients", "view_agenda", "view_evaluacion"])),
):
    """Órdenes abiertas del paciente (pendientes, o atendidas con dosis disponibles) para
    elegir en evaluación/cita. SOLO procedimiento y fecha de ingreso: nunca No. SPS,
    NOG, dosis ni precio."""
    ordenes = await db.igss_ordenes_libro.find(
        {"paciente_id": patient_id, "vigente": True, "estado": {"$in": list(ESTADOS_VIGENTES)},
         "$expr": {"$lt": [_expr_cirugias(), "$dosis_autorizadas"]}}, _PROJ_CLINICA).sort("fecha_ingreso", 1).to_list(200)
    return await _vista_clinica(ordenes)


_PROJ_CLINICA = {"_id": 0, "id": 1, "numero_libro": 1, "procedimiento": 1, "tipo": 1, "fecha_ingreso": 1, "nog_id": 1,
                 "estado": 1, "dosis_autorizadas": 1, "inyectable": 1, "atenciones.tipo": 1}


async def _vista_clinica(ordenes: list) -> list:
    """Lo que ven médico y recepción: número del libro, procedimiento, fecha de ingreso,
    estado y avance de dosis. Nunca No. SPS, NOG, código ni precio."""
    servicios = {n["id"]: n.get("nombre_servicio", "") for n in await db.igss_nogs.find(
        {"id": {"$in": list({o.get("nog_id") for o in ordenes})}}, {"_id": 0, "id": 1, "nombre_servicio": 1}).to_list(None)}
    return [{"id": o["id"], "numero_libro": o.get("numero_libro", ""),
             "procedimiento": o.get("procedimiento") or servicios.get(o.get("nog_id")) or
                              ("Consulta" if o.get("tipo") == "consulta" else "Procedimiento"),
             "tipo": o.get("tipo", "consulta"), "fecha_ingreso": o.get("fecha_ingreso", ""), "estado": o.get("estado", ""),
             "inyectable": bool(o.get("inyectable")), "dosis_aplicadas": _cirugias(o),
             "dosis_autorizadas": int(o.get("dosis_autorizadas") or 1),
             "motivo_sugerido": servicios.get(o.get("nog_id"), "")} for o in ordenes]


@pacientes_router.get("/{patient_id}/igss-ordenes-ficha")
async def ordenes_ficha_clinica(
    patient_id: str,
    current_user: dict = Depends(require_any_permission(["view_patients", "view_agenda", "view_evaluacion"])),
):
    """Sección de solo lectura de la ficha para médico y recepción: solo órdenes reservadas y
    en curso (nunca completas, históricas, cerradas ni anuladas), sin No. SPS ni NOG."""
    ordenes = await db.igss_ordenes_libro.find(
        {"paciente_id": patient_id, "estado": {"$in": ["reservada", "en_curso"]}}, _PROJ_CLINICA,
    ).sort([("fecha_ingreso", -1), ("numero_libro", -1)]).to_list(200)
    return await _vista_clinica(ordenes)


# ==================== REVISIÓN: CIRUGÍAS SIN MARCAR Y ÓRDENES DETENIDAS ====================

def _dias_desde(fecha: str, hoy: date) -> Optional[int]:
    try:
        return (hoy - date.fromisoformat(str(fecha)[:10])).days
    except ValueError:
        return None


ORDENES_VIVAS = ("reservada", "en_curso")


@router.get("/cirugias-por-marcar")
async def cirugias_por_marcar(current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Cirugías IGSS cuya fecha ya pasó y siguen sin marcarse como realizadas, SOLO de
    órdenes vivas (reservada o en curso), que son las que se pueden cobrar. No salen las
    de órdenes históricas, cerradas o completas ni las cirugías sin orden."""
    hoy = today_str_gt()
    cxs = await db.surgeries.find(
        {"institution": "IGSS", "status": "activo", "date": {"$lt": hoy}, "patient_id": {"$nin": [None, ""]}},
        {"_id": 0, "id": 1, "date": 1, "time": 1, "patient_id": 1, "patient_name": 1, "procedure": 1,
         "surgeon": 1, "eye": 1, "igss_data": 1, "igss_orden_id": 1}).sort([("date", 1), ("time", 1)]).to_list(None)
    por_id, por_sps = {}, {}
    async for o in db.igss_ordenes_libro.find(
            {"paciente_id": {"$in": list({c["patient_id"] for c in cxs})}, "vigente": True},
            {"_id": 0, "id": 1, "no_sps": 1, "estado": 1, "paciente_id": 1, "inyectable": 1, "numero_libro": 1}):
        por_id[o["id"]] = o
        por_sps[(o["paciente_id"], o.get("no_sps"))] = o

    def orden_de(c):  # misma prioridad que orden_de_cirugia: igss_orden_id y luego paciente + No. SPS
        o = por_id.get(c.get("igss_orden_id"))
        if o and o["paciente_id"] == c["patient_id"]:
            return o
        sps = normalizar_sps((c.get("igss_data") or {}).get("sps"))
        return por_sps.get((c["patient_id"], sps)) if sps else None

    cxs = [(c, o) for c in cxs if (o := orden_de(c)) and o.get("estado") in ORDENES_VIVAS]
    d = date.fromisoformat(hoy)
    data = [{"id": c["id"], "fecha": c.get("date", ""), "hora": c.get("time", ""), "paciente_id": c.get("patient_id"),
             "paciente_nombre": c.get("patient_name", ""), "procedimiento": c.get("procedure", ""),
             "cirujano": c.get("surgeon", ""), "ojo": c.get("eye", ""), "unidad": (c.get("igss_data") or {}).get("unit", ""),
             "no_sps_indicado": normalizar_sps((c.get("igss_data") or {}).get("sps")),
             "orden": {k: o.get(k) for k in ("id", "no_sps", "estado", "inyectable", "numero_libro")},
             "dias_atraso": _dias_desde(c.get("date"), d)} for c, o in cxs]
    return {"data": data, "total": len(data)}


@router.get("/en-curso-sin-movimiento")
async def en_curso_sin_movimiento(dias: int = Query(90, ge=1, le=3650),
                                  current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Órdenes "en curso" sin dosis ni atención nueva (ni cirugía programada) en más de
    `dias` días: candidatas a revisar o a cerrar sin completar."""
    d = date.fromisoformat(today_str_gt())
    limite = (d - timedelta(days=dias)).isoformat()
    docs = await db.igss_ordenes_libro.aggregate([
        {"$match": {"estado": "en_curso"}},
        {"$set": {"_ultima": {"$max": {"$concatArrays": [
            {"$map": {"input": {"$ifNull": ["$atenciones", []]}, "in": "$$this.fecha"}},
            {"$map": {"input": {"$ifNull": ["$cirugias_programadas", []]}, "in": "$$this.fecha"}}]}}}},
        {"$match": {"$expr": {"$lt": [{"$ifNull": ["$_ultima", "$fecha_ingreso"]}, limite]}}},
        {"$project": {"_id": 0}},
    ]).to_list(None)
    nogs = {n["id"]: n for n in await db.igss_nogs.find(
        {"id": {"$in": list({o.get("nog_id") for o in docs})}}, {"_id": 0}).to_list(None)}
    data = []
    for o in docs:
        ultima = o.pop("_ultima", None) or o.get("fecha_ingreso", "")
        data.append({**_orden_out(o, nogs.get(o.get("nog_id"))), "ultima_actividad": ultima,
                     "dias_sin_movimiento": _dias_desde(ultima, d)})
    data.sort(key=lambda x: x["ultima_actividad"] or "")
    return {"data": data, "total": len(data), "dias": dias}


@router.get("/dosis-por-confirmar")
async def dosis_por_confirmar(current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Órdenes marcadas "Confirmar dosis con la hoja": no llegan a completa ni se cobran
    hasta que se confirmen."""
    docs = await db.igss_ordenes_libro.find(
        {"dosis_por_confirmar": True, "estado": {"$in": list(ESTADOS_VIGENTES)}}, {"_id": 0},
    ).sort([("fecha_ingreso", 1), ("numero_libro", 1)]).to_list(None)
    nogs = {n["id"]: n for n in await db.igss_nogs.find(
        {"id": {"$in": list({o.get("nog_id") for o in docs})}}, {"_id": 0}).to_list(None)}
    data = [_orden_out(o, nogs.get(o.get("nog_id"))) for o in docs]
    return {"data": data, "total": len(data)}


# ==================== ARRANQUE: ESTADOS DEL LIBRO (BLOQUE 1) ====================

async def _numerar_existentes():
    """Órdenes creadas antes del número fijo del libro: se numeran por fecha de creación."""
    async for o in db.igss_ordenes_libro.find({"numero_libro": {"$exists": False}}, {"_id": 0, "id": 1}).sort("created_at", 1):
        await db.igss_ordenes_libro.update_one({"id": o["id"], "numero_libro": {"$exists": False}},
                                               {"$set": {"numero_libro": await siguiente_numero_libro()}})


async def preparar_estados_libro():
    """Una sola vez por entorno: anota en su orden las cirugías IGSS programadas y
    recalcula el estado de las órdenes (pendiente/atendida → reservada/en curso/completa)."""
    await _numerar_existentes()
    flag = "libro_estados_bloque1_v2"
    if await db.system_flags.find_one({"key": flag, "done": True}):
        return
    programadas = 0
    async for cx in db.surgeries.find({"institution": "IGSS", "status": "activo", "patient_id": {"$nin": [None, ""]}},
                                      {"_id": 0, "id": 1, "institution": 1, "status": 1, "patient_id": 1,
                                       "igss_orden_id": 1, "igss_data": 1, "date": 1}):
        orden = await orden_de_cirugia(cx)
        if orden:
            await programar_cirugia(cx, orden)
            programadas += 1
    r = await db.igss_ordenes_libro.update_many({"estado": {"$nin": ["anulada", "cerrada", "historica"]}}, etapas_estado())
    await db.system_flags.update_one({"key": flag}, {"$set": {
        "done": True, "cirugias_programadas": programadas, "ordenes_recalculadas": r.modified_count,
        "at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    logger.info("Libro IGSS: %s cirugías programadas anotadas, %s órdenes recalculadas", programadas, r.modified_count)
