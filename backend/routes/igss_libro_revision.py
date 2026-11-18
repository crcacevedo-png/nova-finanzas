# /app/backend/routes/igss_libro_revision.py
# Libro IGSS — listas de revisión que nacen con la migración: órdenes con "Revisar SPS" (forma de
# No. SPS poco común) y cupos descontados sin No. SPS guardados como cupo ocupado del NOG.

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from config.database import db
from config.permissions import LIBRO_IGSS_ROLES
from routes.auth import require_role
from routes.igss_libro import ESTADOS_VIGENTES, _audit, _liberar_cupo, _nombre_usuario, _orden_out
from routes.igss_nogs import etiqueta_catalogo

router = APIRouter(prefix="/igss-units/libro", tags=["IGSS - Libro de órdenes"])
ROL_LIBRO = require_role(LIBRO_IGSS_ROLES)


class Liberar(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)


async def _nogs(ids) -> dict:
    return {n["id"]: n for n in await db.igss_nogs.find({"id": {"$in": list(ids)}}, {"_id": 0}).to_list(None)}


@router.get("/sps-por-revisar")
async def sps_por_revisar(current_user: dict = Depends(ROL_LIBRO)):
    """Órdenes VIVAS con una forma de No. SPS poco común: no se marcan facturadas hasta confirmar
    el número contra la hoja. Las históricas marcadas solo se ven en la ficha (es informativo)."""
    docs = await db.igss_ordenes_libro.find({"sps_por_revisar": True, "estado": {"$in": list(ESTADOS_VIGENTES)}}, {"_id": 0}) \
        .sort([("estado", 1), ("numero_libro", 1)]).to_list(None)
    nogs = await _nogs({o.get("nog_id") for o in docs})
    data = [_orden_out(o, nogs.get(o.get("nog_id"))) for o in docs]
    return {"data": data, "total": len(data)}


@router.get("/ajustes-cupo")
async def ajustes_cupo(current_user: dict = Depends(ROL_LIBRO)):
    """Cupos descontados sin No. SPS (de la migración): ocupan cupo del NOG sin ser una orden."""
    docs = await db.igss_libro_ajustes_cupo.find({"activo": True}, {"_id": 0}).sort([("unidad_id", 1), ("fecha", 1)]).to_list(None)
    nogs = await _nogs({a.get("nog_id") for a in docs})
    units = {u["id"]: u.get("name", "") for u in await db.igss_units.find(
        {"id": {"$in": list({a.get("unidad_id") for a in docs})}}, {"_id": 0, "id": 1, "name": 1}).to_list(None)}
    data = [{**a, "etiqueta_nog": etiqueta_catalogo(nogs[a["nog_id"]]) if a.get("nog_id") in nogs else "",
             "unidad": units.get(a.get("unidad_id"), "")} for a in docs]
    return {"data": data, "total": len(data)}


@router.post("/ajustes-cupo/{ajuste_id}/liberar")
async def liberar_ajuste(ajuste_id: str, body: Liberar, current_user: dict = Depends(ROL_LIBRO)):
    """Libera un cupo sin No. SPS (p. ej. ya se ingresó la orden real con su No. SPS). Queda en auditoría."""
    now = datetime.now(timezone.utc).isoformat()
    a = await db.igss_libro_ajustes_cupo.find_one_and_update(
        {"id": ajuste_id, "activo": True},
        {"$set": {"activo": False, "liberado_por": current_user.get("id", ""), "liberado_por_nombre": _nombre_usuario(current_user),
                  "liberado_en": now, "motivo_liberacion": body.motivo.strip()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not a:
        raise HTTPException(status_code=404, detail="Cupo sin SPS no encontrado o ya liberado")
    await _liberar_cupo(a["nog_id"])
    await _audit("LIBRO_AJUSTE_CUPO_LIBERADO", current_user, {
        "ajuste_id": ajuste_id, "nog_id": a["nog_id"], "lote_migracion": a.get("lote_migracion"), "motivo": body.motivo.strip()})
    return a
