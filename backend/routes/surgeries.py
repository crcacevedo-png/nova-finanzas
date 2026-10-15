# /app/backend/routes/surgeries.py
# Rutas del módulo Sala de Operaciones (Cirugías)

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from utils.timezone import now_gt
import uuid
import io

# Importar dependencias compartidas
from routes.auth import get_current_user, require_permission, require_role
from config.database import db

router = APIRouter(prefix="/surgeries", tags=["Cirugías"])
reports_router = APIRouter(prefix="/reports", tags=["Reportes"])

# ==================== MODELOS ====================

class IGSSData(BaseModel):
    unit: Optional[str] = None
    sps: Optional[str] = None
    affiliation_number: Optional[str] = None
    code: Optional[str] = None
    procedure_cost: Optional[float] = None

class EquipmentItem(BaseModel):
    id: Optional[str] = None
    name: str
    quantity: int = 1
    notes: Optional[str] = ""
    added_at: Optional[str] = None
    added_by: Optional[str] = None

class SupplyItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: str = "otro"  # lente, medicamento, material, descartable, sutura, viscoelastico, otro
    quantity: int = 1
    unit_cost: float = 0
    total_cost: Optional[float] = None
    notes: Optional[str] = ""
    added_at: Optional[str] = None
    added_by: Optional[str] = None

class SurgeryBase(BaseModel):
    date: str
    time: str
    patient_name: str
    patient_id: Optional[str] = None
    procedure: str
    surgeon: str
    assistant_surgeon: Optional[str] = None
    eye: str  # OD, OI, AO
    anesthesia_type: str  # topica, local, local_asistida, general
    anesthesiologist: str
    institution: str  # Novavision, Alquiler, Seguro Privado, IGSS
    igss_data: Optional[IGSSData] = None
    insurance_name: Optional[str] = ""
    observations: Optional[str] = ""

class SurgeryCreate(SurgeryBase):
    pass

class SurgeryUpdate(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    patient_name: Optional[str] = None
    procedure: Optional[str] = None
    surgeon: Optional[str] = None
    assistant_surgeon: Optional[str] = None
    eye: Optional[str] = None
    anesthesia_type: Optional[str] = None
    anesthesiologist: Optional[str] = None
    institution: Optional[str] = None
    igss_data: Optional[IGSSData] = None
    insurance_name: Optional[str] = None
    observations: Optional[str] = None
    status: Optional[str] = None  # activo, cancelado
    cancellation_reason: Optional[str] = None
    rescheduled_to: Optional[str] = None

class SurgeryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    date: str
    time: str
    patient_name: str
    patient_id: Optional[str] = None
    procedure: str
    surgeon: str
    assistant_surgeon: Optional[str] = None
    eye: str
    anesthesia_type: str
    anesthesiologist: str
    institution: str
    igss_data: Optional[IGSSData] = None
    insurance_name: Optional[str] = ""
    observations: Optional[str] = ""
    equipment: List[EquipmentItem] = []
    supplies: List[SupplyItem] = []
    status: str = "activo"
    cancellation_reason: Optional[str] = None
    rescheduled_to: Optional[str] = None
    created_by: str
    created_by_name: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

class SurgeryListResponse(BaseModel):
    data: List[SurgeryResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# ==================== HELPERS ====================

async def enrich_surgery(surgery: dict) -> dict:
    """Enriquecer cirugía con nombre del creador"""
    if surgery.get("created_by"):
        user = await db.users.find_one({"id": surgery["created_by"]}, {"_id": 0, "name": 1})
        surgery["created_by_name"] = user.get("name") if user else None
    return surgery


# ==================== RUTAS CRUD ====================

@router.get("", response_model=SurgeryListResponse)
async def get_surgeries(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    surgeon: Optional[str] = None,
    institution: Optional[str] = None,
    eye: Optional[str] = None,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    sort_by: str = Query("date", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
    current_user: dict = Depends(get_current_user)
):
    """Listar cirugías con filtros y paginación"""
    query = {}
    
    if search:
        query["$or"] = [
            {"patient_name": {"$regex": search, "$options": "i"}},
            {"procedure": {"$regex": search, "$options": "i"}},
            {"surgeon": {"$regex": search, "$options": "i"}}
        ]
    
    if surgeon:
        query["surgeon"] = {"$regex": surgeon, "$options": "i"}
    
    if institution:
        query["institution"] = institution
    
    if eye:
        query["eye"] = eye
    
    if date_from:
        query["date"] = query.get("date", {})
        query["date"]["$gte"] = date_from
    
    if date_to:
        query["date"] = query.get("date", {})
        query["date"]["$lte"] = date_to
    
    # Ordenamiento
    sort_direction = -1 if sort_order == "desc" else 1
    sort_field = sort_by if sort_by in ["date", "patient_name", "surgeon", "institution"] else "date"
    
    total = await db.surgeries.count_documents(query)
    skip = (page - 1) * limit
    
    cursor = db.surgeries.find(query, {"_id": 0}).sort([(sort_field, sort_direction), ("time", sort_direction)]).skip(skip).limit(limit)
    surgeries = await cursor.to_list(length=limit)
    
    # Enriquecer
    enriched = [await enrich_surgery(s) for s in surgeries]
    
    return SurgeryListResponse(
        data=enriched,
        total=total,
        page=page,
        limit=limit,
        total_pages=(total + limit - 1) // limit
    )


@router.get("/options")
async def get_surgery_options(current_user: dict = Depends(get_current_user)):
    """Obtener opciones únicas para filtros (cirujanos, instituciones, anestesiólogos)"""
    surgeons = await db.surgeries.distinct("surgeon")
    institutions = await db.surgeries.distinct("institution")
    anesthesiologists = await db.surgeries.distinct("anesthesiologist")
    
    return {
        "surgeons": sorted([s for s in surgeons if s]),
        "institutions": sorted([i for i in institutions if i]),
        "anesthesiologists": sorted([a for a in anesthesiologists if a])
    }


@router.get("/{surgery_id}", response_model=SurgeryResponse)
async def get_surgery(surgery_id: str, current_user: dict = Depends(get_current_user)):
    """Obtener detalle de una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    enriched = await enrich_surgery(surgery)
    return SurgeryResponse(**enriched)


@router.post("", response_model=SurgeryResponse)
async def create_surgery(
    surgery: SurgeryCreate,
    current_user: dict = Depends(require_permission("create_expenses"))
):
    """Registrar nueva cirugía"""
    # Validar campos IGSS si la institución es IGSS
    if surgery.institution == "IGSS":
        if not surgery.igss_data:
            raise HTTPException(status_code=400, detail="Los datos IGSS son requeridos")
        igss = surgery.igss_data
        if not all([igss.unit, igss.sps, igss.affiliation_number, igss.code, igss.procedure_cost is not None]):
            raise HTTPException(status_code=400, detail="Todos los campos IGSS son obligatorios")
    
    # Validar nombre del seguro si la institución es Seguro Privado
    if surgery.institution == "Seguro Privado" and not (surgery.insurance_name or "").strip():
        raise HTTPException(status_code=400, detail="El nombre del seguro es requerido")
    
    now = datetime.now(timezone.utc).isoformat()
    
    surgery_doc = {
        "id": str(uuid.uuid4()),
        **surgery.model_dump(),
        "equipment": [],
        "supplies": [],
        "status": "activo",
        "cancellation_reason": None,
        "rescheduled_to": None,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.surgeries.insert_one(surgery_doc)
    
    # Crear evento/nota de cirugía en el historial clínico si hay paciente registrado
    if surgery.patient_id:
        await crear_nota_cirugia(surgery_doc, current_user)
    
    created = await db.surgeries.find_one({"id": surgery_doc["id"]}, {"_id": 0})
    enriched = await enrich_surgery(created)
    return SurgeryResponse(**enriched)


@router.put("/{surgery_id}", response_model=SurgeryResponse)
async def update_surgery(
    surgery_id: str,
    surgery: SurgeryUpdate,
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Editar cirugía"""
    existing = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    update_data = surgery.model_dump(exclude_unset=True)
    
    # Validar campos IGSS si se cambia a IGSS
    new_institution = update_data.get("institution", existing.get("institution"))
    if new_institution == "IGSS":
        igss = update_data.get("igss_data", existing.get("igss_data"))
        if not igss:
            raise HTTPException(status_code=400, detail="Los datos IGSS son requeridos")
        if isinstance(igss, dict):
            if not all([igss.get("unit"), igss.get("sps"), igss.get("affiliation_number"), igss.get("code"), igss.get("procedure_cost") is not None]):
                raise HTTPException(status_code=400, detail="Todos los campos IGSS son obligatorios")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.surgeries.update_one({"id": surgery_id}, {"$set": update_data})
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)


@router.delete("/{surgery_id}")
async def delete_surgery(
    surgery_id: str,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Eliminar cirugía (solo superadmin)"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    await db.surgeries.delete_one({"id": surgery_id})
    return {"message": "Cirugía eliminada correctamente"}


@router.post("/{surgery_id}/cancel")
async def cancel_surgery(
    surgery_id: str,
    reason: str = Body(..., embed=True),
    reschedule_date: Optional[str] = Body(None, embed=True),
    current_user: dict = Depends(require_role("superadmin"))
):
    """Cancelar cirugía con motivo (solo superadmin)"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    update_data = {
        "status": "cancelado",
        "cancellation_reason": reason,
        "rescheduled_to": reschedule_date,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.surgeries.update_one({"id": surgery_id}, {"$set": update_data})
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)


# ==================== EQUIPO ====================

@router.post("/{surgery_id}/equipment")
async def add_equipment(
    surgery_id: str,
    name: str = Body(...),
    quantity: int = Body(1),
    notes: str = Body(""),
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Agregar equipo a una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    equipment_item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "quantity": quantity,
        "notes": notes,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "added_by": current_user["id"]
    }
    
    await db.surgeries.update_one(
        {"id": surgery_id},
        {
            "$push": {"equipment": equipment_item},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)


@router.delete("/{surgery_id}/equipment/{equipment_id}")
async def delete_equipment(
    surgery_id: str,
    equipment_id: str,
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Eliminar equipo de una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    await db.surgeries.update_one(
        {"id": surgery_id},
        {
            "$pull": {"equipment": {"id": equipment_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)


# ==================== INSUMOS ====================

@router.post("/{surgery_id}/supplies")
async def add_supply(
    surgery_id: str,
    name: str = Body(...),
    category: str = Body("otro"),
    quantity: int = Body(1),
    unit_cost: float = Body(0),
    notes: str = Body(""),
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Agregar insumo a una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    supply_item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "category": category,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "total_cost": quantity * unit_cost,
        "notes": notes,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "added_by": current_user["id"]
    }
    
    await db.surgeries.update_one(
        {"id": surgery_id},
        {
            "$push": {"supplies": supply_item},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)


@router.put("/{surgery_id}/supplies/{supply_id}")
async def update_supply(
    surgery_id: str,
    supply_id: str,
    quantity: Optional[int] = Body(None),
    unit_cost: Optional[float] = Body(None),
    notes: Optional[str] = Body(None),
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Editar insumo de una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    supplies = surgery.get("supplies", [])
    supply_index = next((i for i, s in enumerate(supplies) if s.get("id") == supply_id), None)
    
    if supply_index is None:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    
    supply = supplies[supply_index]
    
    if quantity is not None:
        supply["quantity"] = quantity
    if unit_cost is not None:
        supply["unit_cost"] = unit_cost
    if notes is not None:
        supply["notes"] = notes
    
    supply["total_cost"] = supply["quantity"] * supply["unit_cost"]
    
    supplies[supply_index] = supply
    
    await db.surgeries.update_one(
        {"id": surgery_id},
        {"$set": {"supplies": supplies, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)


@router.delete("/{surgery_id}/supplies/{supply_id}")
async def delete_supply(
    surgery_id: str,
    supply_id: str,
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Eliminar insumo de una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    await db.surgeries.update_one(
        {"id": surgery_id},
        {
            "$pull": {"supplies": {"id": supply_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)


# ==================== REPORTES ====================

@reports_router.get("/surgeries")
async def export_surgeries(
    format: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    surgeon: Optional[str] = None,
    institution: Optional[str] = None,
    eye: Optional[str] = None,
    current_user: dict = Depends(require_permission("export_reports"))
):
    """Exportar cirugías a Excel o PDF"""
    query = {"status": {"$ne": "cancelado"}}  # Excluir cirugías canceladas
    
    if surgeon:
        query["surgeon"] = surgeon
    if institution:
        query["institution"] = institution
    if eye:
        query["eye"] = eye
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["date"] = date_query
    
    surgeries = await db.surgeries.find(query, {"_id": 0}).sort([("date", -1), ("time", -1)]).to_list(10000)
    
    # Helper para calcular totales
    def get_supplies_total(supplies):
        return sum(s.get("total_cost", 0) for s in (supplies or []))
    
    def get_total_general(surgery):
        procedure_cost = surgery.get("igss_data", {}).get("procedure_cost", 0) if surgery.get("igss_data") else 0
        supplies_total = get_supplies_total(surgery.get("supplies", []))
        return procedure_cost + supplies_total
    
    def format_institution(surgery):
        """Institución; si es Seguro Privado agrega el nombre del seguro."""
        inst = surgery.get("institution", "") or ""
        if inst == "Seguro Privado" and (surgery.get("insurance_name") or "").strip():
            return f"Seguro Privado ({surgery['insurance_name'].strip()})"
        return inst
    
    if format == "xlsx":
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Cirugías"
            
            # Estilos
            header_fill = PatternFill(start_color="0d9488", end_color="0d9488", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True, size=10)
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Headers
            headers = ["Fecha", "Hora", "Paciente", "Procedimiento", "Cirujano", "Ojo", "Anestesia", "Institución", "Costo Proc.", "Insumos", "Total", "Equipo", "Observaciones"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = thin_border
            
            # Formato moneda
            currency_format = 'Q #,##0.00'
            
            # Etiquetas de anestesia
            anesthesia_labels = {
                "topica": "Tópica", "local": "Local", "local_asistida": "Local Asistida", "general": "General",
                "retrobulbar": "Retrobulbar", "peribulbar": "Peribulbar", "sedacion": "Sedación"
            }
            
            for row, s in enumerate(surgeries, 2):
                ws.cell(row=row, column=1, value=s["date"]).border = thin_border
                ws.cell(row=row, column=2, value=s["time"]).border = thin_border
                ws.cell(row=row, column=3, value=s["patient_name"]).border = thin_border
                ws.cell(row=row, column=4, value=s["procedure"]).border = thin_border
                ws.cell(row=row, column=5, value=s["surgeon"]).border = thin_border
                ws.cell(row=row, column=6, value=s["eye"]).border = thin_border
                ws.cell(row=row, column=7, value=anesthesia_labels.get(s.get("anesthesia_type", ""), s.get("anesthesia_type", ""))).border = thin_border
                ws.cell(row=row, column=8, value=format_institution(s)).border = thin_border
                
                proc_cost = s.get("igss_data", {}).get("procedure_cost", 0) if s.get("igss_data") else 0
                cell_proc = ws.cell(row=row, column=9, value=proc_cost)
                cell_proc.border = thin_border
                cell_proc.number_format = currency_format
                
                supplies_total = get_supplies_total(s.get("supplies", []))
                cell_supplies = ws.cell(row=row, column=10, value=supplies_total)
                cell_supplies.border = thin_border
                cell_supplies.number_format = currency_format
                
                total = get_total_general(s)
                cell_total = ws.cell(row=row, column=11, value=total)
                cell_total.border = thin_border
                cell_total.number_format = currency_format
                cell_total.font = Font(bold=True)
                
                equipment_list = ", ".join([eq["name"] for eq in s.get("equipment", [])])
                ws.cell(row=row, column=12, value=equipment_list).border = thin_border
                ws.cell(row=row, column=13, value=s.get("observations", "")).border = thin_border
            
            # Ajustar anchos
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 8
            ws.column_dimensions['C'].width = 28
            ws.column_dimensions['D'].width = 25
            ws.column_dimensions['E'].width = 20
            ws.column_dimensions['F'].width = 6
            ws.column_dimensions['G'].width = 12
            ws.column_dimensions['H'].width = 15
            ws.column_dimensions['I'].width = 12
            ws.column_dimensions['J'].width = 12
            ws.column_dimensions['K'].width = 12
            ws.column_dimensions['L'].width = 35
            ws.column_dimensions['M'].width = 30
            
            # Fila de totales
            total_row = len(surgeries) + 2
            ws.cell(row=total_row, column=8, value="TOTALES:").font = Font(bold=True)
            
            total_proc = sum(s.get("igss_data", {}).get("procedure_cost", 0) if s.get("igss_data") else 0 for s in surgeries)
            total_supplies = sum(get_supplies_total(s.get("supplies", [])) for s in surgeries)
            total_general = sum(get_total_general(s) for s in surgeries)
            
            cell_total_proc = ws.cell(row=total_row, column=9, value=total_proc)
            cell_total_proc.number_format = currency_format
            cell_total_proc.font = Font(bold=True)
            
            cell_total_supplies = ws.cell(row=total_row, column=10, value=total_supplies)
            cell_total_supplies.number_format = currency_format
            cell_total_supplies.font = Font(bold=True)
            
            cell_total_all = ws.cell(row=total_row, column=11, value=total_general)
            cell_total_all.number_format = currency_format
            cell_total_all.font = Font(bold=True, color="0d9488")
            
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=cirugias_novavision.xlsx"}
            )
        except ImportError:
            raise HTTPException(status_code=500, detail="Librería openpyxl no disponible")
    
    else:
        # PDF format
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            from datetime import datetime, timezone
            
            output = io.BytesIO()
            doc = SimpleDocTemplate(
                output, 
                pagesize=landscape(letter),
                rightMargin=0.4*inch,
                leftMargin=0.4*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )
            
            elements = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=8,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#0d9488')
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=15,
                alignment=TA_CENTER,
                textColor=colors.grey
            )
            
            elements.append(Paragraph("NovaVision — Reporte de Cirugías", title_style))
            
            generated_at = now_gt().strftime("%d/%m/%Y %H:%M")
            filters_text = []
            if date_from:
                filters_text.append(f"Desde: {date_from}")
            if date_to:
                filters_text.append(f"Hasta: {date_to}")
            if surgeon:
                filters_text.append(f"Cirujano: {surgeon}")
            if institution:
                filters_text.append(f"Institución: {institution}")
            
            filter_str = " | ".join(filters_text) if filters_text else "Todas las cirugías"
            elements.append(Paragraph(
                f"Generado: {generated_at} | Usuario: {current_user.get('name', 'N/A')} | {filter_str}",
                subtitle_style
            ))
            
            elements.append(Spacer(1, 0.15*inch))
            
            anesthesia_labels = {
                "topica": "Tópica", "local": "Local", "local_asistida": "Local Asist.", "general": "General",
                "retrobulbar": "Retrob.", "peribulbar": "Perib.", "sedacion": "Sedación"
            }
            
            table_data = [["Fecha", "Hora", "Paciente", "Procedimiento", "Cirujano", "Ojo", "Anest.", "Institución", "Costo Proc.", "Insumos", "Total"]]
            
            for s in surgeries:
                proc_cost = s.get("igss_data", {}).get("procedure_cost", 0) if s.get("igss_data") else 0
                supplies_total = get_supplies_total(s.get("supplies", []))
                total = get_total_general(s)
                
                table_data.append([
                    s["date"],
                    s["time"],
                    s["patient_name"][:25] + "..." if len(s["patient_name"]) > 25 else s["patient_name"],
                    s["procedure"][:20] + "..." if len(s["procedure"]) > 20 else s["procedure"],
                    s["surgeon"][:18] + "..." if len(s["surgeon"]) > 18 else s["surgeon"],
                    s["eye"],
                    anesthesia_labels.get(s.get("anesthesia_type", ""), s.get("anesthesia_type", "")[:6]),
                    (lambda inst: inst[:16] + "..." if len(inst) > 16 else inst)(format_institution(s)),
                    f'Q {proc_cost:,.2f}',
                    f'Q {supplies_total:,.2f}',
                    f'Q {total:,.2f}'
                ])
            
            col_widths = [0.7*inch, 0.5*inch, 1.1*inch, 1.1*inch, 1.1*inch, 0.4*inch, 0.55*inch, 1.3*inch, 0.75*inch, 0.75*inch, 0.75*inch]
            table = Table(table_data, colWidths=col_widths)
            
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d9488')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (5, 1), (5, -1), 'CENTER'),
                ('ALIGN', (8, 1), (10, -1), 'RIGHT'),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdfa')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0d9488')),
            ]))
            
            elements.append(table)
            
            total_proc = sum(s.get("igss_data", {}).get("procedure_cost", 0) if s.get("igss_data") else 0 for s in surgeries)
            total_supplies = sum(get_supplies_total(s.get("supplies", [])) for s in surgeries)
            total_general = sum(get_total_general(s) for s in surgeries)
            
            elements.append(Spacer(1, 0.2*inch))
            
            summary_style = ParagraphStyle(
                'Summary',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_RIGHT
            )
            
            elements.append(Paragraph(
                f"<b>Total Procedimientos:</b> Q {total_proc:,.2f} | <b>Total Insumos:</b> Q {total_supplies:,.2f} | <b>TOTAL GENERAL:</b> Q {total_general:,.2f}",
                summary_style
            ))
            
            elements.append(Paragraph(
                f"<b>Total de cirugías:</b> {len(surgeries)}",
                summary_style
            ))
            
            doc.build(elements)
            output.seek(0)
            
            return StreamingResponse(
                output,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=cirugias_novavision.pdf"}
            )
            
        except ImportError as e:
            raise HTTPException(status_code=500, detail=f"Librería PDF no disponible: {str(e)}")


# ==================== NOTAS DE CIRUGÍA (historial clínico) ====================

notas_router = APIRouter(prefix="/surgery-notes", tags=["Notas de Cirugía"])


def nota_bloqueada(note: dict):
    """Devuelve (bloqueada: bool, motivo: str|None) según cierre o vencimiento (1 mes)."""
    if note.get("estado") == "cerrada":
        return True, "Nota cerrada"
    bf = note.get("bloqueo_fecha")
    if bf and datetime.now(timezone.utc).isoformat() > bf:
        return True, "Bloqueada automáticamente (1 mes desde su creación)"
    return False, None


def serialize_note(note: dict, user: dict):
    bloqueada, motivo = nota_bloqueada(note)
    es_super = user.get("role") == "superadmin"
    data = {k: v for k, v in note.items() if k != "_id"}
    data["bloqueada"] = bloqueada
    data["motivo_bloqueo"] = motivo
    data["editable"] = (not bloqueada) or es_super
    return data


async def crear_nota_cirugia(surgery_doc: dict, user: dict):
    """Crea automáticamente la nota/evento de cirugía en el historial del paciente."""
    now = datetime.now(timezone.utc)
    note = {
        "id": str(uuid.uuid4()),
        "surgery_id": surgery_doc["id"],
        "patient_id": surgery_doc.get("patient_id"),
        "patient_name": surgery_doc.get("patient_name"),
        "procedure": surgery_doc.get("procedure"),
        "fecha": surgery_doc.get("date"),
        "time": surgery_doc.get("time"),
        "eye": surgery_doc.get("eye"),
        "surgeon": surgery_doc.get("surgeon"),
        "assistant_surgeon": surgery_doc.get("assistant_surgeon"),
        "institution": surgery_doc.get("institution"),
        "contenido": "",
        "estado": "abierta",
        "bloqueo_fecha": (now + timedelta(days=30)).isoformat(),
        "created_at": now.isoformat(),
        "created_by": user.get("id"),
        "updated_at": now.isoformat(),
        "cerrada_at": None,
        "cerrada_por": None,
    }
    await db.notas_cirugia.insert_one(note)
    return note


@notas_router.get("")
async def listar_notas_cirugia(
    patient_id: Optional[str] = Query(None),
    surgery_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Lista notas de cirugía del historial clínico (por paciente o por cirugía)."""
    query = {}
    if patient_id:
        query["patient_id"] = patient_id
    if surgery_id:
        query["surgery_id"] = surgery_id
    notas = await db.notas_cirugia.find(query, {"_id": 0}).sort("fecha", -1).to_list(500)
    return {"data": [serialize_note(n, current_user) for n in notas], "total": len(notas)}


@notas_router.get("/{note_id}")
async def obtener_nota_cirugia(note_id: str, current_user: dict = Depends(get_current_user)):
    note = await db.notas_cirugia.find_one({"id": note_id}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return serialize_note(note, current_user)


@notas_router.put("/{note_id}")
async def actualizar_nota_cirugia(
    note_id: str,
    body: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Edita el contenido de la nota. Bloqueada si está cerrada o venció el mes (excepto superadmin)."""
    note = await db.notas_cirugia.find_one({"id": note_id}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    bloqueada, motivo = nota_bloqueada(note)
    if bloqueada and current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail=f"Nota bloqueada: {motivo}")
    await db.notas_cirugia.update_one(
        {"id": note_id},
        {"$set": {
            "contenido": body.get("contenido", ""),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "actualizada_por": current_user.get("id"),
        }}
    )
    actualizada = await db.notas_cirugia.find_one({"id": note_id}, {"_id": 0})
    return serialize_note(actualizada, current_user)


@notas_router.post("/{note_id}/close")
async def cerrar_nota_cirugia(note_id: str, current_user: dict = Depends(get_current_user)):
    """Cierra la nota: queda bloqueada y de solo lectura (cualquier usuario puede cerrar)."""
    note = await db.notas_cirugia.find_one({"id": note_id}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    if note.get("estado") == "cerrada":
        raise HTTPException(status_code=400, detail="La nota ya está cerrada")
    bloqueada, _ = nota_bloqueada(note)
    if bloqueada and current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Nota ya bloqueada")
    now = datetime.now(timezone.utc).isoformat()
    await db.notas_cirugia.update_one(
        {"id": note_id},
        {"$set": {"estado": "cerrada", "cerrada_at": now, "cerrada_por": current_user.get("id"), "updated_at": now}}
    )
    actualizada = await db.notas_cirugia.find_one({"id": note_id}, {"_id": 0})
    return serialize_note(actualizada, current_user)


# Exportar modelos para uso externo
__all__ = [
    'router',
    'reports_router',
    'notas_router',
    'IGSSData',
    'EquipmentItem',
    'SupplyItem',
    'SurgeryBase',
    'SurgeryCreate',
    'SurgeryUpdate',
    'SurgeryResponse',
    'SurgeryListResponse',
    'enrich_surgery'
]
