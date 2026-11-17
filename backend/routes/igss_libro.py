# /app/backend/routes/igss_libro.py
# Libro de órdenes IGSS (colección `igss_ordenes_libro`): una orden por hoja de
# autorización (No. SPS) y unidad. Estados: reservada, en_curso, completa (consulta = la
# evaluación con contenido; procedimiento = la cirugía realizada / la dosis N de N),
# historica (servicio anterior al sistema), cerrada (sin completar, no cobrable) y anulada.
# Cupo ocupado = reservadas + en curso + completas + históricas. Cobrable = solo completas.

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from config.database import db
from config.permissions import LIBRO_IGSS_ROLES
from routes.auth import require_role
from routes.igss_nogs import TIPO_COMPRA_LABELS, UMBRAL_AVISO, _get_nog_or_404, etiqueta_catalogo, norm_txt
from utils.timezone import today_str_gt

router = APIRouter(prefix="/igss-units/libro", tags=["IGSS - Libro de órdenes"])
logger = logging.getLogger("igss_libro")

MSG_SIN_SPS = "El No. SPS es obligatorio: sin No. SPS no se puede registrar la orden."
CAMPOS_EDITABLES = ("codigo", "procedimiento", "precio", "costo_override", "fecha_ingreso",
                    "impreso", "enviado", "facturado", "pagado")
ESTADOS_VIGENTES = ("reservada", "en_curso", "completa")
ESTADOS_CUPO = (*ESTADOS_VIGENTES, "historica")
ESTADOS_FIJOS = ("anulada", "cerrada", "historica")
ESTADO_TEXTO = {"reservada": "reservada", "en_curso": "en curso", "completa": "completa", "anulada": "anulada",
                "historica": "histórica", "cerrada": "cerrada sin completar"}
CAMPOS_COBRO = ("facturado", "pagado")


# ==================== MODELOS ====================

class OrdenCreate(BaseModel):
    nog_id: str = Field(..., min_length=1)
    paciente_id: str = Field(..., min_length=1)
    no_sps: Optional[str] = ""
    tipo: Literal["consulta", "procedimiento"] = "consulta"
    dosis_autorizadas: int = Field(1, ge=1)
    codigo: Optional[str] = ""
    procedimiento: Optional[str] = ""
    precio: Optional[float] = Field(None, ge=0)
    costo_override: Optional[float] = Field(None, ge=0)
    fecha_ingreso: Optional[str] = None


class OrdenUpdate(BaseModel):
    no_sps: Optional[str] = None
    paciente_id: Optional[str] = None
    tipo: Optional[Literal["consulta", "procedimiento"]] = None
    dosis_autorizadas: Optional[int] = Field(None, ge=1)
    codigo: Optional[str] = None
    procedimiento: Optional[str] = None
    precio: Optional[float] = Field(None, ge=0)
    costo_override: Optional[float] = Field(None, ge=0)
    fecha_ingreso: Optional[str] = None
    impreso: Optional[bool] = None
    enviado: Optional[bool] = None
    facturado: Optional[bool] = None
    pagado: Optional[bool] = None


class OrdenAnular(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)


OrdenCerrar = OrdenAnular


# ==================== HELPERS ====================

def normalizar_sps(v) -> str:
    return str(v or "").strip().upper()


def _nombre_usuario(user: dict) -> str:
    return (user or {}).get("name") or (user or {}).get("username", "")


async def _audit(action: str, user: dict, details: dict):
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": action,
        "user_id": (user or {}).get("id", ""),
        "user_name": _nombre_usuario(user),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details,
    })


def _lit(v):
    return {"$literal": v}


def _de_tipo(tipo: str):
    return {"$filter": {"input": {"$ifNull": ["$atenciones", []]}, "cond": {"$eq": ["$$this.tipo", tipo]}}}


def _expr_cirugias():
    return {"$size": _de_tipo("cirugia")}


def etapas_estado() -> list:
    """Recalcula estado y fecha_completa (anulada, cerrada e histórica no cambian).
    Consulta: reservada → completa con la evaluación (los seguimientos no cambian nada).
    Procedimiento: en curso con la 1.ª dosis o con una consulta previa (si es de 1 servicio,
    también con la cirugía programada); completa con la dosis N de N / cirugía realizada."""
    fechas = lambda tipo: {"$map": {"input": _de_tipo(tipo), "in": "$$this.fecha"}}  # noqa: E731
    consulta = {"$eq": ["$tipo", "consulta"]}
    dosis = {"$ifNull": ["$dosis_autorizadas", 1]}
    evals = {"$size": _de_tipo("evaluacion")}
    completa = {"$cond": [consulta, {"$gte": [evals, 1]}, {"$gte": [_expr_cirugias(), dosis]}]}
    programada = {"$and": [{"$lte": [dosis, 1]}, {"$gt": [{"$size": {"$ifNull": ["$cirugias_programadas", []]}}, 0]}]}
    en_curso = {"$and": [{"$not": [consulta]}, {"$or": [{"$gte": [_expr_cirugias(), 1]}, {"$gte": [evals, 1]}, programada]}]}
    fijo = {"$in": ["$estado", list(ESTADOS_FIJOS)]}
    return [{"$set": {
        "estado": {"$cond": [fijo, "$estado", {"$cond": [completa, "completa", {"$cond": [en_curso, "en_curso", "reservada"]}]}]},
        "fecha_completa": {"$cond": [fijo, "$fecha_completa", {"$cond": [
            completa, {"$cond": [consulta, {"$min": fechas("evaluacion")}, {"$max": fechas("cirugia")}]}, None]}]},
    }}]


def _orden_out(o: dict, nog: Optional[dict] = None) -> dict:
    out = {k: v for k, v in o.items() if k not in ("_id", "vigente")}
    atenciones = out.get("atenciones") or []
    out["dosis_aplicadas"] = sum(1 for a in atenciones if a.get("tipo") == "cirugia")
    out["total_atenciones"] = len(atenciones)
    if nog:
        out["modalidad"] = TIPO_COMPRA_LABELS.get(nog.get("tipo_compra", ""), nog.get("tipo_compra", ""))
        out["etiqueta_nog"] = etiqueta_catalogo(nog)
        out["nombre_servicio"] = nog.get("nombre_servicio", "")
        out["sin_tope"] = bool(nog.get("sin_tope"))
    return out


async def _reservar_cupo(nog_id: str):
    """Reserva atómica de 1 cupo: solo si la entrada está activa y es sin tope o
    aún tiene cupo (órdenes vigentes < cantidad). Nunca hay sobregiro."""
    return await db.igss_nogs.find_one_and_update(
        {"id": nog_id, "is_active": {"$ne": False},
         "$expr": {"$or": [
             {"$eq": ["$sin_tope", True]},
             {"$lt": [{"$ifNull": ["$libro_ocupados", 0]}, {"$ifNull": ["$cantidad", 0]}]},
         ]}},
        {"$inc": {"libro_ocupados": 1}},
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,
    )


async def _liberar_cupo(nog_id: str):
    await db.igss_nogs.update_one({"id": nog_id, "libro_ocupados": {"$gt": 0}}, {"$inc": {"libro_ocupados": -1}})


async def _paciente_campos(paciente_id: str) -> dict:
    p = await db.patients.find_one(
        {"id": paciente_id},
        {"_id": 0, "id": 1, "record_number": 1, "first_name": 1, "last_name": 1, "igss_afiliacion": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return {
        "paciente_id": p["id"],
        "paciente_expediente": p.get("record_number", ""),
        "paciente_nombre": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
        "igss_afiliacion": p.get("igss_afiliacion", ""),
    }


def _msg_sps_duplicado(sps: str) -> str:
    return f"Ya existe una orden vigente con el No. SPS {sps} en esta unidad"


async def crear_orden_libro(data: dict, user: dict, origen: str = "manual"):
    """Crea una orden en estado "reservada" (ya ocupa cupo). Valida No. SPS
    obligatorio y único por unidad (índice único parcial) y cupo de la entrada del
    catálogo (reserva atómica). Devuelve (orden, entrada_catalogo)."""
    sps = normalizar_sps(data.get("no_sps"))
    if not sps:
        raise HTTPException(status_code=422, detail=MSG_SIN_SPS)
    tipo = data.get("tipo") or "consulta"
    dosis = int(data.get("dosis_autorizadas") or 1)
    if tipo == "consulta" and dosis != 1:
        raise HTTPException(status_code=422, detail="Una orden de consulta cubre una sola atención (dosis autorizadas = 1)")
    nog = await _get_nog_or_404(data.get("nog_id"))
    if nog.get("is_active") is False:
        raise HTTPException(status_code=400, detail="La entrada del catálogo está inactiva y no admite órdenes nuevas")
    pac = await _paciente_campos(data.get("paciente_id"))
    unidad_id = nog.get("unidad_id", "")
    if await db.igss_ordenes_libro.find_one({"unidad_id": unidad_id, "no_sps": sps, "vigente": True}, {"_id": 1}):
        raise HTTPException(status_code=409, detail=_msg_sps_duplicado(sps))

    reservado = await _reservar_cupo(nog["id"])
    if not reservado:
        fresh = await _get_nog_or_404(nog["id"])
        if fresh.get("is_active") is False:
            raise HTTPException(status_code=400, detail="La entrada del catálogo está inactiva y no admite órdenes nuevas")
        raise HTTPException(status_code=409, detail=(
            f"{etiqueta_catalogo(fresh)} alcanzó el 100 % de su cupo ({int(fresh.get('cantidad') or 0)}). "
            "No se pueden ingresar más órdenes en esta entrada del catálogo."))

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "unidad_id": unidad_id,
        "nog_id": nog["id"],
        "numero_nog": (nog.get("numero") or "").strip(),
        "tipo_compra": nog.get("tipo_compra", ""),
        "no_sps": sps,
        "codigo": (data.get("codigo") or "").strip(),
        "procedimiento": (data.get("procedimiento") or "").strip(),
        "tipo": tipo,
        "dosis_autorizadas": dosis,
        **pac,
        "estado": "reservada",
        "vigente": True,
        "fecha_ingreso": (data.get("fecha_ingreso") or "").strip() or today_str_gt(),
        "fecha_primera_atencion": None,
        "fecha_completa": None,
        "atenciones": [],
        "cirugias_programadas": [],
        "precio": float(data["precio"]) if data.get("precio") is not None else float(nog.get("precio") or 0),
        "costo_override": data.get("costo_override"),
        "impreso": False, "enviado": False, "facturado": False, "pagado": False,
        "anulada_por": None, "anulada_por_nombre": None, "fecha_anulacion": None, "motivo_anulacion": None,
        "origen": origen,
        "created_by": (user or {}).get("id", ""),
        "created_by_nombre": _nombre_usuario(user),
        "created_at": now,
        "updated_at": now,
    }
    try:
        await db.igss_ordenes_libro.insert_one(doc)
    except DuplicateKeyError:
        await _liberar_cupo(nog["id"])
        raise HTTPException(status_code=409, detail=_msg_sps_duplicado(sps))
    except Exception:
        await _liberar_cupo(nog["id"])
        raise
    doc.pop("_id", None)
    await _audit("LIBRO_ORDEN_CREADA", user, {
        "orden_id": doc["id"], "unidad_id": unidad_id, "nog_id": nog["id"], "no_sps": sps,
        "paciente_id": pac["paciente_id"], "tipo": tipo, "dosis_autorizadas": dosis, "origen": origen})
    return doc, reservado


async def _orden_or_404(orden_id: str) -> dict:
    o = await db.igss_ordenes_libro.find_one({"id": orden_id}, {"_id": 0})
    if not o:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return o


async def ensure_libro_indexes():
    """Índices del libro y del catálogo (idempotente; se llama al arrancar)."""
    col = db.igss_ordenes_libro
    specs = [
        ([("unidad_id", 1), ("no_sps", 1)], {"unique": True, "name": "libro_unidad_sps_vigente",
                                              "partialFilterExpression": {"vigente": True}}),
        ([("nog_id", 1), ("estado", 1)], {"name": "libro_nog_estado"}),
        ([("paciente_id", 1)], {"name": "libro_paciente"}),
        ([("estado", 1), ("unidad_id", 1), ("fecha_primera_atencion", 1)], {"name": "libro_estado_unidad_fecha"}),
        ([("id", 1)], {"unique": True, "name": "libro_id"}),
    ]
    for keys, opts in specs:
        try:
            await col.create_index(keys, **opts)
        except Exception as e:
            logger.warning(f"Índice {opts['name']} no creado: {e}")

    # Catálogo: el único (unidad, número) pasa a parcial (solo número no vacío) y se
    # agrega un único parcial (unidad, servicio normalizado) para entradas sin número.
    try:
        info = await db.igss_nogs.index_information()
        if "nog_unidad_numero" in info and not info["nog_unidad_numero"].get("partialFilterExpression"):
            await db.igss_nogs.drop_index("nog_unidad_numero")
        sin_norm = db.igss_nogs.find({"nombre_servicio_norm": {"$exists": False}}, {"_id": 0, "id": 1, "nombre_servicio": 1})
        async for n in sin_norm:
            await db.igss_nogs.update_one({"id": n["id"]}, {"$set": {"nombre_servicio_norm": norm_txt(n.get("nombre_servicio"))}})
    except Exception as e:
        logger.warning(f"Preparación de índices del catálogo NOG: {e}")
    cat_specs = [
        ([("unidad_id", 1), ("numero", 1)], {"unique": True, "name": "nog_unidad_numero_parcial",
                                             "partialFilterExpression": {"numero": {"$gt": ""}}}),
        ([("unidad_id", 1), ("nombre_servicio_norm", 1)], {"unique": True, "name": "nog_unidad_servicio_sin_numero",
                                                           "partialFilterExpression": {"numero": ""}}),
    ]
    for keys, opts in cat_specs:
        try:
            await db.igss_nogs.create_index(keys, **opts)
        except Exception as e:
            logger.warning(f"Índice {opts['name']} no creado (revise duplicados en el catálogo): {e}")


# ==================== ENDPOINTS ====================

@router.get("/ordenes")
async def listar_ordenes(
    unidad_id: Optional[str] = None,
    nog_id: Optional[str] = None,
    paciente_id: Optional[str] = None,
    estado: Optional[Literal["reservada", "en_curso", "completa", "historica", "cerrada", "anulada"]] = None,
    no_sps: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES)),
):
    filtro = {}
    for k, v in (("unidad_id", unidad_id), ("nog_id", nog_id), ("paciente_id", paciente_id), ("estado", estado)):
        if v:
            filtro[k] = v
    if no_sps:
        filtro["no_sps"] = normalizar_sps(no_sps)
    if q and q.strip():
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        filtro["$or"] = [{"paciente_nombre": rx}, {"paciente_expediente": rx}, {"no_sps": rx}, {"igss_afiliacion": rx}]
    total = await db.igss_ordenes_libro.count_documents(filtro)
    docs = await db.igss_ordenes_libro.find(filtro, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    nog_ids = list({d.get("nog_id") for d in docs})
    nogs = {n["id"]: n for n in await db.igss_nogs.find({"id": {"$in": nog_ids}}, {"_id": 0}).to_list(None)}
    return {"data": [_orden_out(d, nogs.get(d.get("nog_id"))) for d in docs], "total": total}


@router.get("/ordenes/{orden_id}")
async def obtener_orden(orden_id: str, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    o = await _orden_or_404(orden_id)
    nog = await db.igss_nogs.find_one({"id": o.get("nog_id")}, {"_id": 0})
    return _orden_out(o, nog)


@router.post("/ordenes")
async def crear_orden(data: OrdenCreate, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    doc, nog = await crear_orden_libro(data.model_dump(), current_user, origen="manual")
    out = _orden_out(doc, nog)
    cantidad, ocupados = int(nog.get("cantidad") or 0), int(nog.get("libro_ocupados") or 0)
    if not nog.get("sin_tope") and cantidad > 0 and ocupados >= cantidad * UMBRAL_AVISO:
        out["aviso_cupo"] = (f"{etiqueta_catalogo(nog)} ya ocupa {ocupados} de {cantidad} cupos "
                             f"({round(ocupados / cantidad * 100, 1)} %). Gestione la renovación a tiempo.")
    return out


@router.put("/ordenes/{orden_id}")
async def editar_orden(orden_id: str, data: OrdenUpdate, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Edita una orden vigente en una sola operación atómica: las reglas que dependen
    del estado actual (dosis ya aplicadas, tipo, atenciones, completa para cobrar) van
    como condiciones, y el estado se recalcula en la misma operación."""
    upd = data.model_dump(exclude_unset=True)
    upd = {k: v for k, v in upd.items() if v is not None or k == "costo_override"}
    if not upd:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    filtro = {"id": orden_id, "estado": {"$ne": "anulada"}}
    expr = []
    set_ = {k: (v.strip() if isinstance(v, str) else v) for k, v in upd.items() if k in CAMPOS_EDITABLES}

    if "no_sps" in upd:
        sps = normalizar_sps(upd["no_sps"])
        if not sps:
            raise HTTPException(status_code=422, detail=MSG_SIN_SPS)
        set_["no_sps"] = sps
    tipo = upd.get("tipo")
    dosis = upd.get("dosis_autorizadas")
    if tipo == "consulta":
        if dosis not in (None, 1):
            raise HTTPException(status_code=422, detail="Una orden de consulta cubre una sola atención (dosis autorizadas = 1)")
        dosis = 1
    elif tipo is None and dosis not in (None, 1):
        filtro["tipo"] = "procedimiento"
    if tipo:
        set_["tipo"] = tipo
    if dosis is not None:
        set_["dosis_autorizadas"] = int(dosis)
        expr.append({"$lte": [_expr_cirugias(), int(dosis)]})
    if "paciente_id" in upd:
        set_.update(await _paciente_campos(upd["paciente_id"]))
        expr.append({"$eq": [{"$size": {"$ifNull": ["$atenciones", []]}}, 0]})
    cobro = [k for k in CAMPOS_COBRO if upd.get(k) is True]
    if cobro:
        filtro["estado"] = "completa"
    cambia_tipo = "tipo" in set_ or "dosis_autorizadas" in set_
    if cambia_tipo:
        filtro.update({"facturado": {"$ne": True}, "pagado": {"$ne": True}})
    if expr:
        filtro["$expr"] = {"$and": expr}
    set_["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_["updated_by"] = current_user.get("id", "")

    try:
        antes = await db.igss_ordenes_libro.find_one_and_update(
            filtro, [{"$set": {k: _lit(v) for k, v in set_.items()}}, *etapas_estado()],
            projection={"_id": 0}, return_document=ReturnDocument.BEFORE)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail=_msg_sps_duplicado(set_.get("no_sps", "")))
    if not antes:
        cur = await _orden_or_404(orden_id)
        if cur.get("estado") == "anulada":
            raise HTTPException(status_code=400, detail="La orden está anulada y no se puede editar")
        if cobro and cur.get("estado") != "completa":
            raise HTTPException(status_code=422, detail=(
                f"Solo una orden completa se puede marcar como {' o '.join(cobro)}: "
                f"esta orden está {ESTADO_TEXTO.get(cur.get('estado'), cur.get('estado'))}."))
        if cambia_tipo and (cur.get("facturado") or cur.get("pagado")):
            raise HTTPException(status_code=422, detail="No se puede cambiar el tipo ni las dosis de una orden ya facturada o pagada")
        aplicadas = sum(1 for a in cur.get("atenciones") or [] if a.get("tipo") == "cirugia")
        if "tipo" in filtro:
            raise HTTPException(status_code=422, detail="Solo las órdenes de procedimiento admiten más de 1 dosis")
        if dosis is not None and aplicadas > int(dosis):
            raise HTTPException(status_code=422, detail=f"La orden ya tiene {aplicadas} dosis aplicadas; las dosis autorizadas no pueden ser menos")
        raise HTTPException(status_code=422, detail="No se puede cambiar el paciente de una orden con atenciones registradas")

    despues = await _orden_or_404(orden_id)
    await _audit("LIBRO_ORDEN_EDITADA", current_user, {
        "orden_id": orden_id, "no_sps": despues.get("no_sps"),
        "antes": {k: antes.get(k) for k in set_ if k not in ("updated_at", "updated_by")},
        "despues": {k: v for k, v in set_.items() if k not in ("updated_at", "updated_by")}})
    nog = await db.igss_nogs.find_one({"id": despues.get("nog_id")}, {"_id": 0})
    return _orden_out(despues, nog)


@router.post("/ordenes/{orden_id}/anular")
async def anular_orden(orden_id: str, body: OrdenAnular, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Anula una orden (nunca se elimina) y libera su cupo. Una orden cerrada sin completar
    no se anula: ya liberó su cupo y queda como constancia del tratamiento suspendido."""
    now = datetime.now(timezone.utc).isoformat()
    antes = await db.igss_ordenes_libro.find_one_and_update(
        {"id": orden_id, "estado": {"$nin": ["anulada", "cerrada"]}},
        {"$set": {"estado": "anulada", "vigente": False,
                  "anulada_por": current_user.get("id", ""), "anulada_por_nombre": _nombre_usuario(current_user),
                  "fecha_anulacion": now, "motivo_anulacion": body.motivo.strip(), "updated_at": now}},
        projection={"_id": 0}, return_document=ReturnDocument.BEFORE)
    if not antes:
        cur = await _orden_or_404(orden_id)
        if cur.get("estado") == "cerrada":
            raise HTTPException(status_code=400, detail=(
                "Una orden cerrada sin completar no se puede anular: ya liberó su cupo, no se cobra "
                "y queda como constancia del tratamiento suspendido."))
        raise HTTPException(status_code=400, detail="La orden ya está anulada")
    if antes.get("estado") in ESTADOS_CUPO:
        await _liberar_cupo(antes["nog_id"])
    await _audit("LIBRO_ORDEN_ANULADA", current_user, {
        "orden_id": orden_id, "nog_id": antes["nog_id"], "no_sps": antes.get("no_sps"),
        "estado_previo": antes.get("estado"), "motivo": body.motivo.strip()})
    o = await _orden_or_404(orden_id)
    nog = await db.igss_nogs.find_one({"id": o.get("nog_id")}, {"_id": 0})
    return _orden_out(o, nog)


@router.post("/ordenes/{orden_id}/cerrar")
async def cerrar_sin_completar(orden_id: str, body: OrdenCerrar, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Cierra SIN COMPLETAR una orden en curso (tratamiento suspendido): exige motivo, queda
    en auditoría, libera su cupo, no admite más atenciones y nunca es cobrable."""
    now = datetime.now(timezone.utc).isoformat()
    antes = await db.igss_ordenes_libro.find_one_and_update(
        {"id": orden_id, "estado": "en_curso"},
        {"$set": {"estado": "cerrada", "cerrada_por": current_user.get("id", ""),
                  "cerrada_por_nombre": _nombre_usuario(current_user), "fecha_cierre": now,
                  "motivo_cierre": body.motivo.strip(), "updated_at": now}},
        projection={"_id": 0}, return_document=ReturnDocument.BEFORE)
    if not antes:
        cur = await _orden_or_404(orden_id)
        raise HTTPException(status_code=400, detail=(
            "Solo una orden en curso se puede cerrar sin completar: esta orden está "
            f"{ESTADO_TEXTO.get(cur.get('estado'), cur.get('estado'))}."))
    await _liberar_cupo(antes["nog_id"])
    await _audit("LIBRO_ORDEN_CERRADA_SIN_COMPLETAR", current_user, {
        "orden_id": orden_id, "nog_id": antes["nog_id"], "no_sps": antes.get("no_sps"),
        "estado_previo": antes.get("estado"), "dosis_aplicadas": _orden_out(antes)["dosis_aplicadas"],
        "dosis_autorizadas": antes.get("dosis_autorizadas"), "motivo": body.motivo.strip()})
    o = await _orden_or_404(orden_id)
    nog = await db.igss_nogs.find_one({"id": o.get("nog_id")}, {"_id": 0})
    return _orden_out(o, nog)


@router.get("/nogs/{nog_id}/contador")
async def contador_nog(nog_id: str, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Contador de una entrada del catálogo leído del libro: reservadas, en curso,
    completas e históricas por separado (ocupan cupo las cuatro); cobrable = solo
    completas. Aviso 90 % / bloqueo 100 % sobre los ocupados, solo con tope."""
    nog = await _get_nog_or_404(nog_id)
    grupos = await db.igss_ordenes_libro.aggregate([
        {"$match": {"nog_id": nog_id}},
        {"$group": {"_id": "$estado", "n": {"$sum": 1}, "monto": {"$sum": {"$ifNull": ["$costo_override", {"$ifNull": ["$precio", 0]}]}}}},
    ]).to_list(None)
    por = {g["_id"]: g for g in grupos}
    n = {e: int((por.get(e) or {}).get("n", 0)) for e in (*ESTADOS_CUPO, "cerrada", "anulada")}
    sin_tope = bool(nog.get("sin_tope"))
    cantidad = int(nog.get("cantidad") or 0)
    usados = sum(n[e] for e in ESTADOS_CUPO)
    res = {
        "nog_id": nog_id, "unidad_id": nog.get("unidad_id", ""), "etiqueta": etiqueta_catalogo(nog),
        "modalidad": TIPO_COMPRA_LABELS.get(nog.get("tipo_compra", ""), nog.get("tipo_compra", "")),
        "sin_tope": sin_tope, "cantidad": None if sin_tope else cantidad,
        "reservadas": n["reservada"], "en_curso": n["en_curso"], "completas": n["completa"],
        "historicas": n["historica"], "ocupados": usados, "cerradas": n["cerrada"], "anuladas": n["anulada"],
        "monto_cobrable": round(float((por.get("completa") or {}).get("monto", 0)), 2),
        "disponibles": None, "porcentaje": None, "aviso_90": False, "bloqueado": False,
    }
    if not sin_tope and cantidad > 0:
        res.update({
            "disponibles": max(cantidad - usados, 0),
            "porcentaje": round(usados / cantidad * 100, 1),
            "aviso_90": usados >= cantidad * UMBRAL_AVISO,
            "bloqueado": usados >= cantidad,
        })
    return res
