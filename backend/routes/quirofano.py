"""Quirófano: catálogo de insumos/equipos y módulo de Procedimientos de Anestesia.

- Catálogo (sin precio) de insumos y equipos quirúrgicos que alimenta el registro
  de cada cirugía.
- Tipos de anestesia con honorario fijo por tipo.
- Registros de anestesia (automáticos desde la cirugía + manuales).
- Cierre mensual por anestesiólogo con monto total a pagar y marcado de pago.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import StreamingResponse

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from routes.auth import get_current_user, require_permission, require_role

load_dotenv()
_client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = _client[os.environ['DB_NAME']]

router = APIRouter(prefix="/quirofano", tags=["Quirófano"])

ANESTHESIA_LABELS = {
    "topica": "Tópica", "local": "Local", "local_asistida": "Local asistida",
    "general": "General", "retrobulbar": "Retrobulbar", "peribulbar": "Peribulbar",
    "sedacion": "Sedación",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


# ==================== CATÁLOGO DE INSUMOS / EQUIPOS ====================
@router.get("/catalog")
async def list_catalog(
    tipo: Optional[str] = Query(None, description="insumo | equipo"),
    active: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if tipo:
        query["tipo"] = tipo
    if active is not None:
        query["active"] = active
    items = await db.surgery_catalog.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    return {"data": items, "total": len(items)}


@router.post("/catalog")
async def create_catalog_item(
    body: dict = Body(...),
    current_user: dict = Depends(require_role(["admin", "superadmin"])),
):
    tipo = (body.get("tipo") or "").strip()
    name = (body.get("name") or "").strip()
    if tipo not in ("insumo", "equipo"):
        raise HTTPException(status_code=400, detail="tipo debe ser 'insumo' o 'equipo'")
    if not name:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    doc = {
        "id": str(uuid.uuid4()),
        "tipo": tipo,
        "name": name,
        "note": (body.get("note") or "").strip(),
        "active": True,
        "created_at": _now(),
        "created_by": current_user.get("id"),
    }
    await db.surgery_catalog.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@router.put("/catalog/{item_id}")
async def update_catalog_item(
    item_id: str,
    body: dict = Body(...),
    current_user: dict = Depends(require_role(["admin", "superadmin"])),
):
    item = await db.surgery_catalog.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Elemento no encontrado")
    update = {"updated_at": _now()}
    for f in ("name", "note", "active"):
        if f in body:
            update[f] = body[f]
    await db.surgery_catalog.update_one({"id": item_id}, {"$set": update})
    return await db.surgery_catalog.find_one({"id": item_id}, {"_id": 0})


@router.delete("/catalog/{item_id}")
async def deactivate_catalog_item(
    item_id: str,
    current_user: dict = Depends(require_role(["admin", "superadmin"])),
):
    res = await db.surgery_catalog.update_one({"id": item_id}, {"$set": {"active": False, "updated_at": _now()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Elemento no encontrado")
    return {"message": "Elemento desactivado"}


# ==================== TIPOS DE ANESTESIA ====================
@router.get("/anesthesia/types")
async def list_anesthesia_types(
    active: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if active is not None:
        query["active"] = active
    items = await db.anesthesia_types.find(query, {"_id": 0}).sort("name", 1).to_list(500)
    return {"data": items, "total": len(items)}


@router.post("/anesthesia/types")
async def create_anesthesia_type(
    body: dict = Body(...),
    current_user: dict = Depends(require_role(["admin", "superadmin"])),
):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    try:
        value = float(body.get("value") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="El valor debe ser numérico")
    doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "value": value,
        "active": True,
        "created_at": _now(),
        "created_by": current_user.get("id"),
    }
    await db.anesthesia_types.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@router.put("/anesthesia/types/{type_id}")
async def update_anesthesia_type(
    type_id: str,
    body: dict = Body(...),
    current_user: dict = Depends(require_role(["admin", "superadmin"])),
):
    item = await db.anesthesia_types.find_one({"id": type_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    update = {"updated_at": _now()}
    if "name" in body:
        update["name"] = (body["name"] or "").strip()
    if "value" in body:
        try:
            update["value"] = float(body["value"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="El valor debe ser numérico")
    if "active" in body:
        update["active"] = body["active"]
    await db.anesthesia_types.update_one({"id": type_id}, {"$set": update})
    return await db.anesthesia_types.find_one({"id": type_id}, {"_id": 0})


@router.delete("/anesthesia/types/{type_id}")
async def deactivate_anesthesia_type(
    type_id: str,
    current_user: dict = Depends(require_role(["admin", "superadmin"])),
):
    res = await db.anesthesia_types.update_one({"id": type_id}, {"$set": {"active": False, "updated_at": _now()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    return {"message": "Tipo desactivado"}


# ==================== REGISTROS DE ANESTESIA ====================
async def _resolve_type_value(type_id: Optional[str], type_name: Optional[str]):
    """Devuelve (type_id, type_name, value) resolviendo por id o por nombre/label."""
    if type_id:
        t = await db.anesthesia_types.find_one({"id": type_id}, {"_id": 0})
        if t:
            return t["id"], t["name"], t.get("value", 0)
    if type_name:
        label = ANESTHESIA_LABELS.get(type_name, type_name)
        t = await db.anesthesia_types.find_one(
            {"name": {"$regex": f"^{label}$", "$options": "i"}, "active": True}, {"_id": 0}
        )
        if t:
            return t["id"], t["name"], t.get("value", 0)
        return None, label, 0
    return None, None, 0


async def upsert_anesthesia_from_surgery(surgery: dict):
    """Crea/actualiza el registro de anestesia asociado a una cirugía."""
    if not surgery.get("anesthesiologist"):
        return
    type_id, type_name, value = await _resolve_type_value(None, surgery.get("anesthesia_type"))
    fecha = surgery.get("date")
    month = (fecha or "")[:7]
    existing = await db.anesthesia_records.find_one({"surgery_id": surgery["id"]}, {"_id": 0})
    if existing:
        # No modificar registros de meses ya cerrados
        if await _month_closed(existing.get("month")):
            return
        await db.anesthesia_records.update_one(
            {"id": existing["id"]},
            {"$set": {
                "anesthesiologist": surgery.get("anesthesiologist"),
                "anesthesia_type_id": type_id,
                "anesthesia_type_name": type_name,
                "value": value if existing.get("value_locked") is not True else existing.get("value"),
                "patient_name": surgery.get("patient_name"),
                "date": fecha, "month": month, "updated_at": _now(),
            }}
        )
    else:
        doc = {
            "id": str(uuid.uuid4()),
            "surgery_id": surgery["id"],
            "patient_name": surgery.get("patient_name"),
            "anesthesiologist": surgery.get("anesthesiologist"),
            "anesthesia_type_id": type_id,
            "anesthesia_type_name": type_name,
            "value": value,
            "date": fecha,
            "month": month,
            "source": "surgery",
            "paid": False,
            "created_at": _now(),
        }
        await db.anesthesia_records.insert_one(doc)


async def _month_closed(month: Optional[str]) -> bool:
    if not month:
        return False
    c = await db.anesthesia_closures.find_one({"month": month, "closed": True})
    return c is not None


async def delete_anesthesia_for_surgery(surgery_id: str):
    """Elimina el registro de anestesia de una cirugía si su mes no está cerrado."""
    rec = await db.anesthesia_records.find_one({"surgery_id": surgery_id}, {"_id": 0})
    if not rec:
        return
    if await _month_closed(rec.get("month")):
        return
    await db.anesthesia_records.delete_one({"surgery_id": surgery_id})


@router.get("/anesthesia/records")
async def list_anesthesia_records(
    month: Optional[str] = Query(None),
    anesthesiologist: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if month:
        query["month"] = month
    if anesthesiologist:
        query["anesthesiologist"] = {"$regex": anesthesiologist, "$options": "i"}
    items = await db.anesthesia_records.find(query, {"_id": 0}).sort("date", -1).to_list(2000)
    return {"data": items, "total": len(items)}


@router.post("/anesthesia/records")
async def create_anesthesia_record(
    body: dict = Body(...),
    current_user: dict = Depends(require_permission("edit_expenses")),
):
    anesthesiologist = (body.get("anesthesiologist") or "").strip()
    fecha = body.get("date")
    if not anesthesiologist or not fecha:
        raise HTTPException(status_code=400, detail="Anestesiólogo y fecha son obligatorios")
    month = fecha[:7]
    if await _month_closed(month):
        raise HTTPException(status_code=400, detail="El mes está cerrado, no se pueden agregar registros")
    type_id, type_name, value = await _resolve_type_value(body.get("anesthesia_type_id"), body.get("anesthesia_type_name"))
    doc = {
        "id": str(uuid.uuid4()),
        "surgery_id": body.get("surgery_id"),
        "patient_name": (body.get("patient_name") or "").strip(),
        "anesthesiologist": anesthesiologist,
        "anesthesia_type_id": type_id,
        "anesthesia_type_name": type_name,
        "value": value,
        "date": fecha,
        "month": month,
        "source": "manual",
        "paid": False,
        "created_at": _now(),
        "created_by": current_user.get("id"),
    }
    await db.anesthesia_records.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@router.put("/anesthesia/records/{record_id}")
async def update_anesthesia_record(
    record_id: str,
    body: dict = Body(...),
    current_user: dict = Depends(require_permission("edit_expenses")),
):
    rec = await db.anesthesia_records.find_one({"id": record_id}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    if await _month_closed(rec.get("month")) and current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="El mes está cerrado")
    update = {"updated_at": _now(), "value_locked": True}
    if "anesthesiologist" in body:
        update["anesthesiologist"] = (body["anesthesiologist"] or "").strip()
    if "date" in body and body["date"]:
        update["date"] = body["date"]
        update["month"] = body["date"][:7]
    if "anesthesia_type_id" in body or "anesthesia_type_name" in body:
        type_id, type_name, value = await _resolve_type_value(body.get("anesthesia_type_id"), body.get("anesthesia_type_name"))
        update["anesthesia_type_id"] = type_id
        update["anesthesia_type_name"] = type_name
        update["value"] = value
    if "value" in body:
        try:
            update["value"] = float(body["value"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="El valor debe ser numérico")
    await db.anesthesia_records.update_one({"id": record_id}, {"$set": update})
    return await db.anesthesia_records.find_one({"id": record_id}, {"_id": 0})


@router.delete("/anesthesia/records/{record_id}")
async def delete_anesthesia_record(
    record_id: str,
    current_user: dict = Depends(require_permission("edit_expenses")),
):
    rec = await db.anesthesia_records.find_one({"id": record_id}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    if await _month_closed(rec.get("month")) and current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="El mes está cerrado")
    await db.anesthesia_records.delete_one({"id": record_id})
    return {"message": "Registro eliminado"}


# ==================== CIERRE MENSUAL ====================
async def _build_closure(month: str) -> dict:
    """Agrega los registros de anestesia del mes agrupados por anestesiólogo."""
    records = await db.anesthesia_records.find({"month": month}, {"_id": 0}).to_list(5000)
    por_anest = {}
    for r in records:
        key = r.get("anesthesiologist") or ""
        if key.strip().upper() in ("", "N/A", "NA", "—"):
            continue
        grp = por_anest.setdefault(key, {"anesthesiologist": key, "count": 0, "total": 0.0, "tipos": {}})
        grp["count"] += 1
        grp["total"] += (r.get("value") or 0)
        tname = r.get("anesthesia_type_name") or "Sin tipo"
        t = grp["tipos"].setdefault(tname, {"tipo": tname, "count": 0, "value": r.get("value") or 0, "subtotal": 0.0})
        t["count"] += 1
        t["subtotal"] += (r.get("value") or 0)
    resultado = []
    for grp in por_anest.values():
        grp["total"] = round(grp["total"], 2)
        grp["tipos"] = sorted(grp["tipos"].values(), key=lambda x: x["tipo"])
        resultado.append(grp)
    resultado.sort(key=lambda x: x["total"], reverse=True)
    closure = await db.anesthesia_closures.find_one({"month": month}, {"_id": 0})
    return {
        "month": month,
        "closed": bool(closure and closure.get("closed")),
        "closed_at": closure.get("closed_at") if closure else None,
        "por_anestesiologo": resultado,
        "total_general": round(sum(g["total"] for g in resultado), 2),
        "num_registros": len(records),
    }


@router.get("/anesthesia/closure")
async def get_monthly_closure(
    month: str = Query(..., description="YYYY-MM"),
    current_user: dict = Depends(require_role(["admin", "superadmin"])),
):
    return await _build_closure(month)


@router.get("/anesthesia/closure/export")
async def export_monthly_closure(
    month: str = Query(..., description="YYYY-MM"),
    format: str = Query("xlsx", description="xlsx | pdf"),
    current_user: dict = Depends(require_role(["admin", "superadmin"])),
):
    import io
    data = await _build_closure(month)
    grupos = data["por_anestesiologo"]
    estado = "CERRADO (pagado)" if data["closed"] else "ABIERTO (pendiente)"

    if format == "xlsx":
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Anestesia {month}"
        header_fill = PatternFill("solid", fgColor="4F46E5")
        white_bold = Font(bold=True, color="FFFFFF")
        bold = Font(bold=True)
        thin = Side(style="thin", color="E2E8F0")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        ws["A1"] = "Novavisión — Cierre de Procedimientos de Anestesia"
        ws["A1"].font = Font(bold=True, size=14, color="4F46E5")
        ws["A2"] = f"Mes: {month}   |   Estado: {estado}   |   Total a pagar: Q {data['total_general']:,.2f}   |   Procedimientos: {data['num_registros']}"
        ws["A3"] = ""

        headers = ["Anestesiólogo", "Tipo de anestesia", "Cantidad", "Honorario unit.", "Subtotal"]
        row = 4
        for c, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=c, value=h)
            cell.fill = header_fill
            cell.font = white_bold
            cell.alignment = Alignment(horizontal="center")
            cell.border = border
        row += 1

        for g in grupos:
            first = True
            for t in g["tipos"]:
                ws.cell(row=row, column=1, value=g["anesthesiologist"] if first else "").border = border
                ws.cell(row=row, column=2, value=t["tipo"]).border = border
                ws.cell(row=row, column=3, value=t["count"]).border = border
                ws.cell(row=row, column=4, value=round(t["value"], 2)).border = border
                ws.cell(row=row, column=5, value=round(t["subtotal"], 2)).border = border
                first = False
                row += 1
            # Subtotal por anestesiólogo
            lbl = ws.cell(row=row, column=2, value=f"Total {g['anesthesiologist']} ({g['count']} proc.)")
            lbl.font = bold
            tot = ws.cell(row=row, column=5, value=round(g["total"], 2))
            tot.font = bold
            row += 1

        row += 1
        ws.cell(row=row, column=2, value="TOTAL GENERAL").font = Font(bold=True, size=12)
        ws.cell(row=row, column=5, value=round(data["total_general"], 2)).font = Font(bold=True, size=12)

        widths = [28, 24, 12, 16, 14]
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=anestesia_{month}.xlsx"},
        )

    # PDF
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=0.5 * inch,
                            leftMargin=0.5 * inch, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=15, alignment=TA_CENTER,
                                 textColor=colors.HexColor('#4F46E5'), spaceAfter=6)
    sub_style = ParagraphStyle('S', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER,
                               textColor=colors.grey, spaceAfter=14)
    elements = [
        Paragraph("Novavisión — Cierre de Procedimientos de Anestesia", title_style),
        Paragraph(f"Mes: {month} &nbsp;|&nbsp; Estado: {estado} &nbsp;|&nbsp; Total a pagar: Q {data['total_general']:,.2f} &nbsp;|&nbsp; Procedimientos: {data['num_registros']}", sub_style),
    ]

    table_data = [["Anestesiólogo", "Tipo de anestesia", "Cant.", "Honorario", "Subtotal"]]
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (1, 0), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#4F46E5')),
    ]
    r = 1
    for g in grupos:
        first = True
        for t in g["tipos"]:
            table_data.append([
                g["anesthesiologist"] if first else "",
                t["tipo"], str(t["count"]),
                f"Q {t['value']:,.2f}", f"Q {t['subtotal']:,.2f}",
            ])
            first = False
            r += 1
        table_data.append(["", f"Total {g['anesthesiologist']} ({g['count']} proc.)", "", "", f"Q {g['total']:,.2f}"])
        style_cmds.append(('FONTNAME', (0, r), (-1, r), 'Helvetica-Bold'))
        style_cmds.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor('#EEF2FF')))
        r += 1

    table = Table(table_data, colWidths=[1.9 * inch, 2.2 * inch, 0.7 * inch, 1.1 * inch, 1.1 * inch])
    table.setStyle(TableStyle(style_cmds))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))
    total_style = ParagraphStyle('Tot', parent=styles['Normal'], fontSize=12, alignment=TA_RIGHT)
    elements.append(Paragraph(f"<b>TOTAL GENERAL: Q {data['total_general']:,.2f}</b>", total_style))
    if not grupos:
        elements.append(Paragraph("Sin registros de anestesia este mes.", sub_style))

    doc.build(elements)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=anestesia_{month}.pdf"},
    )


@router.post("/anesthesia/closure/close")
async def close_month(
    body: dict = Body(...),
    current_user: dict = Depends(require_role(["admin", "superadmin"])),
):
    month = body.get("month")
    if not month:
        raise HTTPException(status_code=400, detail="Mes requerido")
    existing = await db.anesthesia_closures.find_one({"month": month})
    if existing and existing.get("closed"):
        raise HTTPException(status_code=400, detail="El mes ya está cerrado")
    now = _now()
    await db.anesthesia_closures.update_one(
        {"month": month},
        {"$set": {"month": month, "closed": True, "paid": True, "closed_at": now,
                  "closed_by": current_user.get("id")}},
        upsert=True,
    )
    await db.anesthesia_records.update_many({"month": month}, {"$set": {"paid": True, "updated_at": now}})
    return {"message": f"Mes {month} cerrado y honorarios marcados como pagados"}


@router.post("/anesthesia/closure/reopen")
async def reopen_month(
    body: dict = Body(...),
    current_user: dict = Depends(require_role(["superadmin"])),
):
    month = body.get("month")
    if not month:
        raise HTTPException(status_code=400, detail="Mes requerido")
    now = _now()
    await db.anesthesia_closures.update_one(
        {"month": month}, {"$set": {"closed": False, "paid": False, "reopened_at": now}}, upsert=True
    )
    await db.anesthesia_records.update_many({"month": month}, {"$set": {"paid": False}})
    return {"message": f"Mes {month} reabierto"}
