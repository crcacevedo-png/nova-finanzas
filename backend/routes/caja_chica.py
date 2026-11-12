# /app/backend/routes/caja_chica.py
# Caja Chica de Óptica: ingresos, egresos, saldo continuo e informe mensual.

import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from config.database import db
from routes.auth import get_current_user, require_permission
from models.caja_chica import (
    MovimientoCajaChicaCreate,
    MovimientoCajaChicaUpdate,
    MovimientoCajaChicaResponse,
    MovimientoCajaChicaListResponse,
    ResumenCajaChicaResponse,
)

router = APIRouter(prefix="/caja-chica", tags=["Caja Chica Óptica"])


def _puede_editar(existing: dict, current_user: dict) -> bool:
    if current_user.get("role") == "superadmin":
        return True
    return existing.get("registrado_por_id") == current_user["id"]


async def _calcular_totales(query_extra: Optional[dict] = None) -> dict:
    query = dict(query_extra or {})
    movimientos = await db.caja_chica_movimientos.find(query, {"_id": 0, "tipo": 1, "monto": 1}).to_list(100000)
    total_ingresos = sum(m["monto"] for m in movimientos if m["tipo"] == "ingreso")
    total_egresos = sum(m["monto"] for m in movimientos if m["tipo"] == "egreso")
    return {
        "total_ingresos": round(total_ingresos, 2),
        "total_egresos": round(total_egresos, 2),
        "saldo": round(total_ingresos - total_egresos, 2),
    }


@router.get("/resumen", response_model=ResumenCajaChicaResponse)
async def get_resumen(current_user: dict = Depends(require_permission("view_caja_chica"))):
    """Saldo continuo: total ingresado, total egresado y saldo disponible (histórico completo)."""
    return await _calcular_totales()


@router.get("/movimientos", response_model=MovimientoCajaChicaListResponse)
async def get_movimientos(
    mes: Optional[str] = Query(None, description="Filtrar por mes YYYY-MM"),
    tipo: Optional[str] = Query(None, description="ingreso | egreso"),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_permission("view_caja_chica")),
):
    """Historial de movimientos, más recientes primero."""
    query = {}
    if mes:
        query["fecha"] = {"$gte": f"{mes}-01", "$lte": f"{mes}-31"}
    if tipo in ("ingreso", "egreso"):
        query["tipo"] = tipo

    total = await db.caja_chica_movimientos.count_documents(query)
    movimientos = await db.caja_chica_movimientos.find(query, {"_id": 0}).sort(
        [("fecha", -1), ("created_at", -1)]
    ).skip(offset).limit(limit).to_list(limit)

    return {"data": movimientos, "total": total}


@router.post("/movimientos", response_model=MovimientoCajaChicaResponse)
async def crear_movimiento(
    movimiento: MovimientoCajaChicaCreate,
    current_user: dict = Depends(require_permission("view_caja_chica")),
):
    """Registrar un ingreso o un egreso de caja chica."""
    now = datetime.now(timezone.utc).isoformat()
    mov_dict = {
        "id": str(uuid.uuid4()),
        "tipo": movimiento.tipo,
        "monto": movimiento.monto,
        "fecha": movimiento.fecha,
        "solicitante": movimiento.solicitante if movimiento.tipo == "egreso" else None,
        "motivo": movimiento.motivo if movimiento.tipo == "egreso" else None,
        "registrado_por_id": current_user["id"],
        "registrado_por_nombre": current_user["name"],
        "created_at": now,
        "updated_at": None,
        "editado_por_nombre": None,
    }
    await db.caja_chica_movimientos.insert_one(mov_dict)
    mov_dict.pop("_id", None)
    return mov_dict


@router.put("/movimientos/{movimiento_id}", response_model=MovimientoCajaChicaResponse)
async def actualizar_movimiento(
    movimiento_id: str,
    movimiento: MovimientoCajaChicaUpdate,
    current_user: dict = Depends(require_permission("view_caja_chica")),
):
    """Editar un movimiento. Solo quien lo registró (o SuperAdmin) puede corregirlo."""
    existing = await db.caja_chica_movimientos.find_one({"id": movimiento_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if not _puede_editar(existing, current_user):
        raise HTTPException(status_code=403, detail="Solo quien registró este movimiento puede editarlo")

    update_data = {k: v for k, v in movimiento.model_dump().items() if v is not None}
    if existing["tipo"] == "egreso":
        if "solicitante" in update_data and not update_data["solicitante"].strip():
            raise HTTPException(status_code=400, detail="El solicitante no puede quedar vacío en un egreso")
        if "motivo" in update_data and not update_data["motivo"].strip():
            raise HTTPException(status_code=400, detail="El motivo no puede quedar vacío en un egreso")
    else:
        update_data.pop("solicitante", None)
        update_data.pop("motivo", None)

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["editado_por_nombre"] = current_user["name"]

    await db.caja_chica_movimientos.update_one({"id": movimiento_id}, {"$set": update_data})
    updated = await db.caja_chica_movimientos.find_one({"id": movimiento_id}, {"_id": 0})
    return updated


@router.delete("/movimientos/{movimiento_id}")
async def eliminar_movimiento(
    movimiento_id: str,
    current_user: dict = Depends(require_permission("delete_caja_chica")),
):
    """Eliminar un movimiento (solo SuperAdmin)."""
    existing = await db.caja_chica_movimientos.find_one({"id": movimiento_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    await db.caja_chica_movimientos.delete_one({"id": movimiento_id})
    return {"message": "Movimiento eliminado"}


async def _construir_informe_mensual(mes: str) -> dict:
    """Informe de un mes: movimientos del mes + totales del mes + saldo acumulado
    (histórico completo) al cierre de ese mes."""
    movimientos_mes = await db.caja_chica_movimientos.find(
        {"fecha": {"$gte": f"{mes}-01", "$lte": f"{mes}-31"}}, {"_id": 0}
    ).sort([("fecha", 1), ("created_at", 1)]).to_list(100000)

    total_ingresos_mes = round(sum(m["monto"] for m in movimientos_mes if m["tipo"] == "ingreso"), 2)
    total_egresos_mes = round(sum(m["monto"] for m in movimientos_mes if m["tipo"] == "egreso"), 2)

    # Saldo acumulado real de la caja desde siempre, hasta el fin de ese mes
    saldo_acumulado = await _calcular_totales({"fecha": {"$lte": f"{mes}-31"}})

    return {
        "mes": mes,
        "total_ingresos_mes": total_ingresos_mes,
        "total_egresos_mes": total_egresos_mes,
        "saldo_neto_mes": round(total_ingresos_mes - total_egresos_mes, 2),
        "saldo_acumulado_fin_mes": saldo_acumulado["saldo"],
        "movimientos": movimientos_mes,
    }


@router.get("/informe")
async def get_informe_mensual(
    mes: str = Query(..., description="Mes a revisar, formato YYYY-MM"),
    current_user: dict = Depends(require_permission("view_caja_chica")),
):
    """Informe de fin de mes: totales del mes + saldo acumulado + detalle de movimientos."""
    return await _construir_informe_mensual(mes)


@router.get("/informe/excel")
async def exportar_informe_excel(
    mes: str = Query(..., description="Mes a exportar, formato YYYY-MM"),
    current_user: dict = Depends(require_permission("view_caja_chica")),
):
    """Descarga del informe de fin de mes en Excel."""
    informe = await _construir_informe_mensual(mes)

    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Caja Chica {mes}"
    header_fill = PatternFill("solid", fgColor="0F6E56")
    white_bold = Font(bold=True, color="FFFFFF")
    bold = Font(bold=True)
    thin = Side(style="thin", color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["A1"] = "NovaVisión Óptica — Informe de Caja Chica"
    ws["A1"].font = Font(bold=True, size=14, color="0F6E56")
    ws["A2"] = (
        f"Mes: {mes}   |   Ingresos del mes: Q {informe['total_ingresos_mes']:,.2f}   |   "
        f"Egresos del mes: Q {informe['total_egresos_mes']:,.2f}   |   "
        f"Saldo acumulado al cierre: Q {informe['saldo_acumulado_fin_mes']:,.2f}"
    )
    ws["A3"] = ""

    headers = ["Fecha", "Tipo", "Solicitante", "Motivo", "Monto", "Registrado por"]
    row = 4
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=c, value=h)
        cell.fill = header_fill
        cell.font = white_bold
        cell.alignment = Alignment(horizontal="center")
        cell.border = border
    row += 1

    for m in informe["movimientos"]:
        ws.cell(row=row, column=1, value=m["fecha"]).border = border
        ws.cell(row=row, column=2, value="Ingreso" if m["tipo"] == "ingreso" else "Egreso").border = border
        ws.cell(row=row, column=3, value=m.get("solicitante") or "—").border = border
        ws.cell(row=row, column=4, value=m.get("motivo") or "—").border = border
        ws.cell(row=row, column=5, value=round(m["monto"], 2)).border = border
        ws.cell(row=row, column=6, value=m.get("registrado_por_nombre") or "—").border = border
        row += 1

    row += 1
    ws.cell(row=row, column=4, value="TOTAL INGRESOS DEL MES").font = bold
    ws.cell(row=row, column=5, value=informe["total_ingresos_mes"]).font = bold
    row += 1
    ws.cell(row=row, column=4, value="TOTAL EGRESOS DEL MES").font = bold
    ws.cell(row=row, column=5, value=informe["total_egresos_mes"]).font = bold
    row += 1
    ws.cell(row=row, column=4, value="SALDO ACUMULADO AL CIERRE DEL MES").font = Font(bold=True, size=12)
    ws.cell(row=row, column=5, value=informe["saldo_acumulado_fin_mes"]).font = Font(bold=True, size=12)

    widths = [14, 12, 24, 36, 14, 22]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=caja_chica_{mes}.xlsx"},
    )
