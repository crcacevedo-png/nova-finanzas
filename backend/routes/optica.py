# /app/backend/routes/optica.py
# Módulo completo de Óptica - Médicos, Inventario, Ventas, Dashboard, Compras

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from utils.timezone import now_gt, today_str_gt, dia_gt_a_rango_utc
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import uuid

from config.database import db
from routes.auth import get_current_user, require_permission, require_role


# ==================== ROUTERS ====================
router = APIRouter(prefix="/optica", tags=["Óptica"])
doctors_router = APIRouter(prefix="/doctors", tags=["Médicos"])


# ==================== MODELS ====================

# Médicos
class DoctorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    specialty: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    license_number: Optional[str] = ""
    notes: Optional[str] = ""
    firma_digital: Optional[str] = ""
    # Horario laboral semanal: claves "1"(Lunes).."7"(Domingo),
    # cada día: {"activo": bool, "hora_inicio": "HH:MM", "hora_fin": "HH:MM"}
    horario_semanal: Optional[Dict[str, Any]] = None

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    notes: Optional[str] = None
    firma_digital: Optional[str] = None
    is_active: Optional[bool] = None
    horario_semanal: Optional[Dict[str, Any]] = None

class DoctorResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    usuario_id: Optional[str] = None
    specialty: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    license_number: Optional[str] = ""
    notes: Optional[str] = ""
    firma_digital: Optional[str] = ""
    is_active: bool = True
    horario_semanal: Optional[Dict[str, Any]] = None
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class DoctorListResponse(BaseModel):
    data: List[DoctorResponse]
    total: int

# Inventario de Aros
class FrameInventoryBase(BaseModel):
    brand: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    model: Optional[str] = ""
    color: Optional[str] = ""
    cost_price: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    stock: int = Field(ge=0)

class FrameInventoryCreate(FrameInventoryBase):
    pass

class FrameInventoryUpdate(BaseModel):
    brand: Optional[str] = None
    code: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    cost_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None

class FrameInventoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    brand: str
    code: str
    model: Optional[str] = ""
    color: Optional[str] = ""
    cost_price: Optional[float] = 0
    sale_price: Optional[float] = 0
    stock: int = 0
    entry_date: Optional[str] = None
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class FrameInventoryListResponse(BaseModel):
    data: List[FrameInventoryResponse]
    total: int

# Lentes de Contacto
class ContactLensInventoryBase(BaseModel):
    lens_type: Literal["esferico", "torico", "multifocal", "cosmetico"]
    brand: Optional[str] = ""
    name: Optional[str] = ""  # Nombre del producto
    description: Optional[str] = ""
    cost_price: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    stock: int = Field(ge=0)

class ContactLensInventoryCreate(ContactLensInventoryBase):
    pass

class ContactLensInventoryUpdate(BaseModel):
    lens_type: Optional[Literal["esferico", "torico", "multifocal", "cosmetico"]] = None
    brand: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    cost_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None

class ContactLensInventoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    lens_type: Optional[str] = "esferico"  # Default para datos legacy
    brand: Optional[str] = ""
    name: Optional[str] = ""
    description: Optional[str] = ""
    cost_price: Optional[float] = 0
    sale_price: Optional[float] = 0
    price: Optional[float] = 0
    stock: int = 0
    entry_date: Optional[str] = None
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ContactLensInventoryListResponse(BaseModel):
    data: List[ContactLensInventoryResponse]
    total: int

# Tipos de Lente
class LensTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""
    cost_price: Optional[float] = None
    default_price: float = Field(ge=0)

class LensTypeCreate(LensTypeBase):
    pass

class LensTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cost_price: Optional[float] = None
    default_price: Optional[float] = None
    is_active: Optional[bool] = None

class LensTypeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: Optional[str] = ""
    cost_price: Optional[float] = 0
    default_price: Optional[float] = 0
    price: Optional[float] = 0
    sale_price: Optional[float] = 0  # Agregado para compatibilidad con POS
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class LensTypeListResponse(BaseModel):
    data: List[LensTypeResponse]
    total: int

# Accesorios
class AccessoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    brand: Optional[str] = ""
    description: Optional[str] = ""
    cost_price: float = Field(ge=0, default=0)
    sale_price: float = Field(ge=0)
    stock: int = Field(ge=0, default=0)

class AccessoryCreate(AccessoryBase):
    pass

class AccessoryUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    cost_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None

class AccessoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    brand: Optional[str] = ""
    description: Optional[str] = ""
    cost_price: Optional[float] = 0
    sale_price: Optional[float] = 0
    price: Optional[float] = 0
    stock: int = 0
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AccessoryListResponse(BaseModel):
    data: List[AccessoryResponse]
    total: int

# Ventas
class SaleLineItem(BaseModel):
    lens_type_id: str
    lens_type_name: Optional[str] = ""
    quantity: int = Field(ge=1, default=1)
    unit_price: float = Field(ge=0)
    subtotal: float = Field(ge=0)


# Modelo V2 para ventas desde el POS (formato genérico con items[])
class SaleItemV2(BaseModel):
    """Item genérico para venta desde POS"""
    type: Literal["frame", "contact_lens", "lens_type", "accessory"]
    product_id: str
    quantity: int = Field(ge=1, default=1)
    unit_price: float = Field(ge=0)
    subtotal: float = Field(ge=0)


class SalePaymentV2(BaseModel):
    """Pago para venta desde POS"""
    method: str  # Efectivo, Tarjeta, Transferencia, Cheque
    amount: float = Field(ge=0)
    reference: Optional[str] = None


class OpticaSaleCreateV2(BaseModel):
    """Modelo V2 para crear venta desde el POS de Óptica"""
    patient_id: Optional[str] = None
    patient_name: str = "Consumidor Final"
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    items: List[SaleItemV2] = []
    subtotal: float = Field(ge=0)
    discount: float = Field(ge=0, default=0)
    discount_percent: float = Field(ge=0, le=100, default=0)
    discount_authorized_by: Optional[str] = None
    total: float = Field(ge=0)
    payments: List[SalePaymentV2] = []
    notes: Optional[str] = None
    prescription: Optional[dict] = None  # Receta óptica
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None
    # Campos para CxC
    tiene_cxc: bool = False
    monto_cxc: float = Field(ge=0, default=0)


class OpticaSaleBase(BaseModel):
    patient_id: str
    doctor_id: Optional[str] = None
    frame_id: Optional[str] = None
    contact_lens_id: Optional[str] = None
    lens_items: List[SaleLineItem] = []
    payment_method: Literal["efectivo", "tarjeta", "transferencia", "cheque", "mixto"]
    discount_percent: float = Field(ge=0, le=100, default=0)
    initial_payment: float = Field(ge=0, default=0)
    notes: Optional[str] = ""

class OpticaSaleCreate(OpticaSaleBase):
    pass

class OpticaSaleUpdate(BaseModel):
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None
    discount_percent: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[Literal["pendiente", "pagado", "cancelado"]] = None

class SalePaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    payment_method: Literal["efectivo", "tarjeta", "transferencia", "cheque"]
    reference: Optional[str] = ""
    notes: Optional[str] = ""

class SalePaymentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    sale_id: str
    amount: float
    payment_method: str
    reference: Optional[str] = ""
    notes: Optional[str] = ""
    created_by: str
    created_by_name: Optional[str] = ""
    created_at: str

class OpticaSaleResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    order_number: str
    patient_id: str
    patient_name: Optional[str] = ""
    patient_phone: Optional[str] = ""
    doctor_id: Optional[str] = ""
    doctor_name: Optional[str] = ""
    frame_id: Optional[str] = ""
    frame_info: Optional[str] = ""
    frame_price: float = 0
    contact_lens_id: Optional[str] = ""
    contact_lens_info: Optional[str] = ""
    contact_lens_price: float = 0
    lens_items: List[SaleLineItem] = []
    lens_total: float = 0
    items_v2: List[dict] = []
    subtotal: float
    discount_percent: float
    discount_amount: float
    discount_authorized_by: Optional[str] = ""
    total: float
    total_paid: float
    balance_due: float
    payment_method: str
    status: str
    payments: List[SalePaymentResponse] = []
    notes: Optional[str] = ""
    created_by: str
    created_by_name: Optional[str] = ""
    created_at: str
    updated_at: Optional[str] = None
    cancelled_by: Optional[str] = ""
    cancelled_by_name: Optional[str] = ""
    cancelled_at: Optional[str] = None

class OpticaSaleListResponse(BaseModel):
    data: List[OpticaSaleResponse]
    total: int

# Compras
class OpticaPurchaseBase(BaseModel):
    supplier_id: Optional[str] = None
    category: str
    description: str
    quantity: int = 1
    unit_price: float = 0
    total: float
    invoice_number: Optional[str] = None
    purchase_date: str
    notes: Optional[str] = ""

class OpticaPurchaseCreate(OpticaPurchaseBase):
    pass

class OpticaPurchaseUpdate(BaseModel):
    supplier_id: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None
    invoice_number: Optional[str] = None
    purchase_date: Optional[str] = None
    notes: Optional[str] = None

class OpticaPurchaseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    category: str
    description: str
    quantity: int
    unit_price: float
    total: float
    invoice_number: Optional[str] = None
    purchase_date: str
    notes: Optional[str] = ""
    created_at: str
    updated_at: str

class OpticaPurchaseListResponse(BaseModel):
    data: List[OpticaPurchaseResponse]
    total: int


# ==================== HELPERS ====================

async def get_next_order_number() -> str:
    """Genera el siguiente número de orden correlativo"""
    prefix = now_gt().strftime("ORD-%Y%m-")
    
    last_sale = await db.optica_sales.find_one(
        {"order_number": {"$regex": f"^{prefix}"}},
        {"order_number": 1},
        sort=[("order_number", -1)]
    )
    
    if last_sale:
        try:
            last_num = int(last_sale["order_number"].split("-")[-1])
            next_num = last_num + 1
        except Exception:
            next_num = 1
    else:
        next_num = 1
    
    return f"{prefix}{next_num:04d}"


async def enrich_sale(sale: dict) -> dict:
    """Enriquece la venta con datos relacionados"""
    # Paciente: no sobreescribir el nombre guardado cuando la venta es de
    # Consumidor Final / walk-in (sin patient_id vinculado).
    patient = await db.patients.find_one({"id": sale["patient_id"]}, {"_id": 0}) if sale.get("patient_id") else None
    if patient:
        sale["patient_name"] = f"{patient['first_name']} {patient['last_name']}"
        sale["patient_phone"] = patient.get("phone", "")
    elif sale.get("patient_id"):
        sale["patient_name"] = "Paciente no encontrado"
        sale["patient_phone"] = ""
    else:
        sale["patient_name"] = sale.get("patient_name") or "Consumidor Final"
        sale["patient_phone"] = sale.get("patient_phone", "")
    
    # Médico: conservar el doctor_name guardado si no hay doctor_id vinculado
    if sale.get("doctor_id"):
        doctor = await db.doctors.find_one({"id": sale["doctor_id"]}, {"_id": 0})
        sale["doctor_name"] = doctor["name"] if doctor else sale.get("doctor_name", "")
    else:
        sale["doctor_name"] = sale.get("doctor_name", "")
    
    # Aro
    if sale.get("frame_id"):
        frame = await db.optica_frames.find_one({"id": sale["frame_id"]}, {"_id": 0})
        if frame:
            sale["frame_info"] = f"{frame['brand']} - {frame['code']}"
            sale["frame_price"] = sale.get("frame_price", frame["sale_price"])
    else:
        sale["frame_info"] = ""
        sale["frame_price"] = 0
    
    # Lente de contacto
    if sale.get("contact_lens_id"):
        contact_lens = await db.optica_contact_lenses.find_one({"id": sale["contact_lens_id"]}, {"_id": 0})
        if contact_lens:
            # Usar .get() para manejar datos legacy sin lens_type
            lens_type = contact_lens.get('lens_type', 'esferico')
            sale["contact_lens_info"] = f"{lens_type.capitalize()} - {contact_lens.get('brand', '')}"
            sale["contact_lens_price"] = sale.get("contact_lens_price", contact_lens.get("sale_price", 0))
    else:
        sale["contact_lens_info"] = ""
        sale["contact_lens_price"] = 0
    
    # Creador
    creator = await db.users.find_one({"id": sale["created_by"]}, {"_id": 0, "name": 1})
    sale["created_by_name"] = creator["name"] if creator else ""
    
    # Pagos/Abonos
    payments = await db.optica_sale_payments.find({"sale_id": sale["id"]}, {"_id": 0}).sort("created_at", 1).to_list(100)
    for payment in payments:
        creator = await db.users.find_one({"id": payment["created_by"]}, {"_id": 0, "name": 1})
        payment["created_by_name"] = creator["name"] if creator else ""
    sale["payments"] = payments
    
    return sale


# ==================== DOCTORS ROUTES ====================

@doctors_router.get("", response_model=DoctorListResponse)
async def get_doctors(
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Listar médicos"""
    query = {"is_active": True}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": search_regex},
            {"specialty": search_regex},
            {"license_number": search_regex}
        ]
    
    doctors = await db.doctors.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    return DoctorListResponse(data=doctors, total=len(doctors))


@doctors_router.get("/search")
async def search_doctors(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Búsqueda de médicos para autocompletado"""
    search_regex = {"$regex": q, "$options": "i"}
    query = {
        "is_active": True,
        "$or": [{"name": search_regex}, {"specialty": search_regex}]
    }
    
    doctors = await db.doctors.find(query, {"_id": 0, "id": 1, "name": 1, "specialty": 1}).limit(limit).to_list(limit)
    return doctors


@doctors_router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(doctor_id: str, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener médico por ID"""
    doctor = await db.doctors.find_one({"id": doctor_id, "is_active": True}, {"_id": 0})
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    return DoctorResponse(**doctor)


@doctors_router.post("", response_model=DoctorResponse)
async def create_doctor(doctor_data: DoctorCreate, current_user: dict = Depends(require_permission("manage_doctors"))):
    """Crear nuevo médico"""
    existing = await db.doctors.find_one({
        "name": {"$regex": f"^{doctor_data.name}$", "$options": "i"},
        "is_active": True
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un médico con este nombre")
    
    now = datetime.now(timezone.utc).isoformat()
    doctor_doc = {
        "id": str(uuid.uuid4()),
        "name": doctor_data.name,
        "specialty": doctor_data.specialty or "",
        "phone": doctor_data.phone or "",
        "email": doctor_data.email or "",
        "license_number": doctor_data.license_number or "",
        "notes": doctor_data.notes or "",
        "firma_digital": doctor_data.firma_digital or "",
        "is_active": True,
        "horario_semanal": doctor_data.horario_semanal or None,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.doctors.insert_one(doctor_doc)
    if "_id" in doctor_doc:
        del doctor_doc["_id"]
    return DoctorResponse(**doctor_doc)


@doctors_router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(doctor_id: str, doctor_data: DoctorUpdate, current_user: dict = Depends(require_permission("manage_doctors"))):
    """Actualizar médico"""
    doctor = await db.doctors.find_one({"id": doctor_id, "is_active": True})
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    
    update_data = {k: v for k, v in doctor_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.doctors.update_one({"id": doctor_id}, {"$set": update_data})
    updated = await db.doctors.find_one({"id": doctor_id}, {"_id": 0})
    return DoctorResponse(**updated)


@doctors_router.delete("/{doctor_id}")
async def delete_doctor(doctor_id: str, current_user: dict = Depends(require_permission("manage_doctors"))):
    """Eliminar médico (soft delete)"""
    doctor = await db.doctors.find_one({"id": doctor_id, "is_active": True})
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    
    await db.doctors.update_one(
        {"id": doctor_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Médico eliminado correctamente"}


# ==================== FRAMES ROUTES ====================

@router.get("/frames", response_model=FrameInventoryListResponse)
async def get_frames(
    search: Optional[str] = None,
    low_stock: Optional[bool] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Listar inventario de aros"""
    query = {"is_active": True}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"brand": search_regex},
            {"code": search_regex},
            {"model": search_regex}
        ]
    if low_stock:
        query["stock"] = {"$lte": 5}
    
    frames = await db.optica_frames.find(query, {"_id": 0}).sort("brand", 1).to_list(1000)
    return FrameInventoryListResponse(data=frames, total=len(frames))


@router.get("/frames/search")
async def search_frames(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Búsqueda de aros para autocompletado"""
    search_regex = {"$regex": q, "$options": "i"}
    query = {
        "is_active": True,
        "stock": {"$gt": 0},
        "$or": [{"brand": search_regex}, {"code": search_regex}, {"model": search_regex}]
    }
    
    frames = await db.optica_frames.find(query, {"_id": 0}).limit(limit).to_list(limit)
    result = []
    for f in frames:
        result.append({
            "id": f["id"],
            "label": f"{f['brand']} - {f['code']} ({f.get('model', '')})",
            "brand": f["brand"],
            "code": f["code"],
            "model": f.get("model", ""),
            "color": f.get("color", ""),
            "sale_price": f["sale_price"],
            "stock": f["stock"]
        })
    return result


@router.get("/frames/{frame_id}", response_model=FrameInventoryResponse)
async def get_frame(frame_id: str, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener aro por ID"""
    frame = await db.optica_frames.find_one({"id": frame_id, "is_active": True}, {"_id": 0})
    if not frame:
        raise HTTPException(status_code=404, detail="Aro no encontrado")
    return FrameInventoryResponse(**frame)


@router.post("/frames", response_model=FrameInventoryResponse)
async def create_frame(frame_data: FrameInventoryCreate, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Crear nuevo aro"""
    existing = await db.optica_frames.find_one({"code": frame_data.code, "is_active": True})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un aro con este código")
    
    now = datetime.now(timezone.utc).isoformat()
    frame_doc = {
        "id": str(uuid.uuid4()),
        "brand": frame_data.brand,
        "code": frame_data.code,
        "model": frame_data.model or "",
        "color": frame_data.color or "",
        "cost_price": frame_data.cost_price,
        "sale_price": frame_data.sale_price,
        "stock": frame_data.stock,
        "entry_date": now[:10],
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.optica_frames.insert_one(frame_doc)
    if "_id" in frame_doc:
        del frame_doc["_id"]
    return FrameInventoryResponse(**frame_doc)


@router.put("/frames/{frame_id}", response_model=FrameInventoryResponse)
async def update_frame(frame_id: str, frame_data: FrameInventoryUpdate, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Actualizar aro"""
    frame = await db.optica_frames.find_one({"id": frame_id, "is_active": True})
    if not frame:
        raise HTTPException(status_code=404, detail="Aro no encontrado")
    
    update_data = {k: v for k, v in frame_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    if "code" in update_data and update_data["code"] != frame["code"]:
        existing = await db.optica_frames.find_one({
            "code": update_data["code"], 
            "is_active": True, 
            "id": {"$ne": frame_id}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un aro con este código")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.optica_frames.update_one({"id": frame_id}, {"$set": update_data})
    updated = await db.optica_frames.find_one({"id": frame_id}, {"_id": 0})
    return FrameInventoryResponse(**updated)


@router.delete("/frames/{frame_id}")
async def delete_frame(frame_id: str, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Eliminar aro (soft delete)"""
    frame = await db.optica_frames.find_one({"id": frame_id, "is_active": True})
    if not frame:
        raise HTTPException(status_code=404, detail="Aro no encontrado")
    
    await db.optica_frames.update_one(
        {"id": frame_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Aro eliminado correctamente"}


# ==================== CONTACT LENSES ROUTES ====================

@router.get("/contact-lenses", response_model=ContactLensInventoryListResponse)
async def get_contact_lenses(
    search: Optional[str] = None,
    lens_type: Optional[str] = None,
    low_stock: Optional[bool] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Listar inventario de lentes de contacto"""
    query = {"is_active": True}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [{"brand": search_regex}, {"description": search_regex}]
    if lens_type:
        query["lens_type"] = lens_type
    if low_stock:
        query["stock"] = {"$lte": 5}
    
    lenses = await db.optica_contact_lenses.find(query, {"_id": 0}).sort("lens_type", 1).to_list(1000)
    return ContactLensInventoryListResponse(data=lenses, total=len(lenses))


@router.get("/contact-lenses/search")
async def search_contact_lenses(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Búsqueda de lentes de contacto"""
    search_regex = {"$regex": q, "$options": "i"}
    query = {
        "is_active": True,
        "stock": {"$gt": 0},
        "$or": [{"brand": search_regex}, {"description": search_regex}, {"lens_type": search_regex}]
    }
    
    lenses = await db.optica_contact_lenses.find(query, {"_id": 0}).limit(limit).to_list(limit)
    result = []
    for l in lenses:
        result.append({
            "id": l["id"],
            "label": f"{l['lens_type'].capitalize()} - {l.get('brand', '')} ({l.get('description', '')})",
            "lens_type": l["lens_type"],
            "brand": l.get("brand", ""),
            "sale_price": l["sale_price"],
            "stock": l["stock"]
        })
    return result


@router.post("/contact-lenses", response_model=ContactLensInventoryResponse)
async def create_contact_lens(lens_data: ContactLensInventoryCreate, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Crear nuevo lente de contacto"""
    now = datetime.now(timezone.utc).isoformat()
    lens_doc = {
        "id": str(uuid.uuid4()),
        "lens_type": lens_data.lens_type,
        "brand": lens_data.brand or "",
        "name": lens_data.name or "",
        "description": lens_data.description or "",
        "cost_price": lens_data.cost_price,
        "sale_price": lens_data.sale_price,
        "stock": lens_data.stock,
        "entry_date": now[:10],
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.optica_contact_lenses.insert_one(lens_doc)
    if "_id" in lens_doc:
        del lens_doc["_id"]
    return ContactLensInventoryResponse(**lens_doc)


@router.put("/contact-lenses/{lens_id}", response_model=ContactLensInventoryResponse)
async def update_contact_lens(lens_id: str, lens_data: ContactLensInventoryUpdate, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Actualizar lente de contacto"""
    lens = await db.optica_contact_lenses.find_one({"id": lens_id, "is_active": True})
    if not lens:
        raise HTTPException(status_code=404, detail="Lente de contacto no encontrado")
    
    update_data = {k: v for k, v in lens_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.optica_contact_lenses.update_one({"id": lens_id}, {"$set": update_data})
    updated = await db.optica_contact_lenses.find_one({"id": lens_id}, {"_id": 0})
    return ContactLensInventoryResponse(**updated)


@router.delete("/contact-lenses/{lens_id}")
async def delete_contact_lens(lens_id: str, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Eliminar lente de contacto (soft delete)"""
    lens = await db.optica_contact_lenses.find_one({"id": lens_id, "is_active": True})
    if not lens:
        raise HTTPException(status_code=404, detail="Lente de contacto no encontrado")
    
    await db.optica_contact_lenses.update_one(
        {"id": lens_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Lente de contacto eliminado correctamente"}


# ==================== LENS TYPES ROUTES ====================

@router.get("/lens-types", response_model=LensTypeListResponse)
async def get_lens_types(current_user: dict = Depends(require_permission("view_optica"))):
    """Listar catálogo de tipos de lente"""
    lens_types = await db.optica_lens_types.find({"is_active": True}, {"_id": 0}).sort("name", 1).to_list(1000)
    # Mapear default_price a price y sale_price para compatibilidad con POS
    for lt in lens_types:
        default_p = lt.get("default_price", 0) or 0
        lt["price"] = default_p
        lt["sale_price"] = default_p
    return LensTypeListResponse(data=lens_types, total=len(lens_types))


@router.post("/lens-types", response_model=LensTypeResponse)
async def create_lens_type(lens_type_data: LensTypeCreate, current_user: dict = Depends(require_permission("manage_lens_catalog"))):
    """Crear nuevo tipo de lente"""
    existing = await db.optica_lens_types.find_one({
        "name": {"$regex": f"^{lens_type_data.name}$", "$options": "i"},
        "is_active": True
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un tipo de lente con este nombre")
    
    now = datetime.now(timezone.utc).isoformat()
    lens_type_doc = {
        "id": str(uuid.uuid4()),
        "name": lens_type_data.name,
        "description": lens_type_data.description or "",
        "cost_price": lens_type_data.cost_price,
        "default_price": lens_type_data.default_price,
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.optica_lens_types.insert_one(lens_type_doc)
    if "_id" in lens_type_doc:
        del lens_type_doc["_id"]
    return LensTypeResponse(**lens_type_doc)


@router.put("/lens-types/{lens_type_id}", response_model=LensTypeResponse)
async def update_lens_type(lens_type_id: str, lens_type_data: LensTypeUpdate, current_user: dict = Depends(require_permission("manage_lens_catalog"))):
    """Actualizar tipo de lente"""
    lens_type = await db.optica_lens_types.find_one({"id": lens_type_id, "is_active": True})
    if not lens_type:
        raise HTTPException(status_code=404, detail="Tipo de lente no encontrado")
    
    update_data = {k: v for k, v in lens_type_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.optica_lens_types.update_one({"id": lens_type_id}, {"$set": update_data})
    updated = await db.optica_lens_types.find_one({"id": lens_type_id}, {"_id": 0})
    return LensTypeResponse(**updated)


@router.delete("/lens-types/{lens_type_id}")
async def delete_lens_type(lens_type_id: str, current_user: dict = Depends(require_permission("manage_lens_catalog"))):
    """Eliminar tipo de lente (soft delete)"""
    lens_type = await db.optica_lens_types.find_one({"id": lens_type_id, "is_active": True})
    if not lens_type:
        raise HTTPException(status_code=404, detail="Tipo de lente no encontrado")
    
    await db.optica_lens_types.update_one(
        {"id": lens_type_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Tipo de lente eliminado correctamente"}


# ==================== ACCESSORIES ROUTES ====================

@router.get("/accessories", response_model=AccessoryListResponse)
async def get_accessories(
    search: Optional[str] = None,
    low_stock: Optional[bool] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Listar inventario de accesorios"""
    query = {"is_active": True}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [{"name": search_regex}, {"brand": search_regex}, {"description": search_regex}]
    if low_stock:
        query["stock"] = {"$lte": 5}
    accessories = await db.optica_accessories.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    for a in accessories:
        a["price"] = a.get("sale_price", 0) or 0
    return AccessoryListResponse(data=accessories, total=len(accessories))


@router.post("/accessories", response_model=AccessoryResponse)
async def create_accessory(accessory_data: AccessoryCreate, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Crear nuevo accesorio"""
    now = datetime.now(timezone.utc).isoformat()
    accessory_doc = {
        "id": str(uuid.uuid4()),
        "name": accessory_data.name.strip(),
        "brand": accessory_data.brand or "",
        "description": accessory_data.description or "",
        "cost_price": accessory_data.cost_price,
        "sale_price": accessory_data.sale_price,
        "stock": accessory_data.stock,
        "entry_date": now[:10],
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    await db.optica_accessories.insert_one(accessory_doc)
    if "_id" in accessory_doc:
        del accessory_doc["_id"]
    accessory_doc["price"] = accessory_doc["sale_price"]
    return AccessoryResponse(**accessory_doc)


@router.put("/accessories/{accessory_id}", response_model=AccessoryResponse)
async def update_accessory(accessory_id: str, accessory_data: AccessoryUpdate, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Actualizar accesorio"""
    accessory = await db.optica_accessories.find_one({"id": accessory_id, "is_active": True})
    if not accessory:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")
    update_data = {k: v for k, v in accessory_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.optica_accessories.update_one({"id": accessory_id}, {"$set": update_data})
    updated = await db.optica_accessories.find_one({"id": accessory_id}, {"_id": 0})
    updated["price"] = updated.get("sale_price", 0) or 0
    return AccessoryResponse(**updated)


@router.delete("/accessories/{accessory_id}")
async def delete_accessory(accessory_id: str, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Eliminar accesorio (soft delete)"""
    accessory = await db.optica_accessories.find_one({"id": accessory_id, "is_active": True})
    if not accessory:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")
    await db.optica_accessories.update_one(
        {"id": accessory_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Accesorio eliminado correctamente"}


# ==================== SALES ROUTES ====================

@router.get("/sales", response_model=OpticaSaleListResponse)
async def get_optica_sales(
    status: Optional[str] = None,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    search: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Listar ventas de óptica"""
    query = {}
    
    if status and status != "all":
        query["status"] = status
    
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = dia_gt_a_rango_utc(date_from)[0]
        if date_to:
            date_query["$lte"] = dia_gt_a_rango_utc(date_to)[1]
        if date_query:
            query["created_at"] = date_query
    
    sales = await db.optica_sales.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    enriched_sales = []
    for sale in sales:
        enriched = await enrich_sale(sale)
        
        if search:
            search_lower = search.lower()
            if not (
                search_lower in enriched.get("patient_name", "").lower() or
                search_lower in enriched.get("order_number", "").lower() or
                search_lower in enriched.get("doctor_name", "").lower()
            ):
                continue
        
        enriched_sales.append(enriched)
    
    return OpticaSaleListResponse(data=enriched_sales, total=len(enriched_sales))


@router.get("/sales/pending")
async def get_pending_sales(current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener ventas con saldo pendiente"""
    sales = await db.optica_sales.find(
        {"status": "pendiente", "balance_due": {"$gt": 0}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    enriched_sales = []
    total_pending = 0
    for sale in sales:
        enriched = await enrich_sale(sale)
        enriched_sales.append(enriched)
        total_pending += sale.get("balance_due", 0)
    
    return {
        "data": enriched_sales,
        "total": len(enriched_sales),
        "total_pending_amount": total_pending
    }


async def _resumen_ventas(cajero_id: Optional[str], inicio: str, fin: str) -> dict:
    """Resumen de ventas de óptica en un rango: total vendido, cobrado y desglose por método."""
    sales_query = {"created_at": {"$gte": inicio, "$lte": fin}, "status": {"$ne": "cancelado"}}
    if cajero_id:
        sales_query["created_by"] = cajero_id
    sales = await db.optica_sales.find(sales_query, {"_id": 0}).to_list(5000)
    cantidad = len(sales)
    total_vendido = sum(s.get("total", 0) for s in sales)

    # Excluir pagos de ventas canceladas
    cancel_ids = await db.optica_sales.distinct(
        "id", {"created_at": {"$gte": inicio, "$lte": fin}, "status": "cancelado"}
    )
    pay_query = {"created_at": {"$gte": inicio, "$lte": fin}}
    if cajero_id:
        pay_query["created_by"] = cajero_id
    if cancel_ids:
        pay_query["sale_id"] = {"$nin": cancel_ids}
    pagos = await db.optica_sale_payments.find(pay_query, {"_id": 0}).to_list(10000)
    por_metodo = {"Efectivo": 0, "Tarjeta": 0, "Transferencia": 0, "Cheque": 0}
    total_cobrado = 0
    for p in pagos:
        metodo = (p.get("payment_method") or "Efectivo").strip().title()
        monto = p.get("amount", 0)
        total_cobrado += monto
        por_metodo[metodo] = por_metodo.get(metodo, 0) + monto

    return {
        "cantidad_ventas": cantidad,
        "total_vendido": round(total_vendido, 2),
        "total_cobrado": round(total_cobrado, 2),
        "por_metodo": por_metodo
    }


@router.get("/sales/resumen-dia")
async def get_resumen_ventas_dia(
    fecha: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Resumen de ventas del día del vendedor actual."""
    fecha_dia = fecha or today_str_gt()
    inicio, fin = dia_gt_a_rango_utc(fecha_dia)
    resumen = await _resumen_ventas(current_user["id"], inicio, fin)
    sales = await db.optica_sales.find(
        {"created_at": {"$gte": inicio, "$lte": fin}, "created_by": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(5000)
    sales = [await enrich_sale(s) for s in sales]
    return {"fecha": fecha_dia, "vendedor": current_user.get("name"), "sales": sales, **resumen}


@router.get("/sales/resumen-dia/consolidado")
async def get_resumen_ventas_consolidado(
    fecha: Optional[str] = None,
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """Resumen de ventas del día de todos los vendedores (Admin/SuperAdmin)."""
    fecha_dia = fecha or today_str_gt()
    inicio, fin = dia_gt_a_rango_utc(fecha_dia)

    sales = await db.optica_sales.find(
        {"created_at": {"$gte": inicio, "$lte": fin}}, {"_id": 0}
    ).to_list(5000)
    vendedores = {}
    for s in sales:
        vid = s.get("created_by") or "sin_vendedor"
        if vid not in vendedores:
            vendedores[vid] = s.get("created_by_name") or "Sin vendedor"

    data = []
    total_general = 0
    cobrado_general = 0
    for vid, nombre in vendedores.items():
        r = await _resumen_ventas(vid, inicio, fin)
        total_general += r["total_vendido"]
        cobrado_general += r["total_cobrado"]
        data.append({"vendedor_id": vid, "vendedor_nombre": nombre, **r})

    data.sort(key=lambda x: x["total_vendido"], reverse=True)
    return {
        "fecha": fecha_dia,
        "data": data,
        "total_vendedores": len(data),
        "total_vendido": round(total_general, 2),
        "total_cobrado": round(cobrado_general, 2)
    }


@router.get("/sales/{sale_id}", response_model=OpticaSaleResponse)
async def get_optica_sale(sale_id: str, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener detalle de una venta"""
    sale = await db.optica_sales.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    enriched = await enrich_sale(sale)
    return OpticaSaleResponse(**enriched)


@router.post("/sales", response_model=OpticaSaleResponse)
async def create_optica_sale(sale_data: OpticaSaleCreate, current_user: dict = Depends(require_permission("manage_optica_sales"))):
    """Crear nueva venta de óptica"""
    patient = await db.patients.find_one({"id": sale_data.patient_id, "is_active": True})
    if not patient:
        raise HTTPException(status_code=400, detail="Paciente no encontrado")
    
    if sale_data.doctor_id:
        doctor = await db.doctors.find_one({"id": sale_data.doctor_id, "is_active": True})
        if not doctor:
            raise HTTPException(status_code=400, detail="Médico no encontrado")
    
    subtotal = 0
    frame_price = 0
    contact_lens_price = 0
    lens_total = 0
    
    if sale_data.frame_id:
        frame = await db.optica_frames.find_one({"id": sale_data.frame_id, "is_active": True})
        if not frame:
            raise HTTPException(status_code=400, detail="Aro no encontrado")
        if frame["stock"] < 1:
            raise HTTPException(status_code=400, detail="No hay stock disponible para este aro")
        frame_price = frame["sale_price"]
        subtotal += frame_price
        await db.optica_frames.update_one({"id": sale_data.frame_id}, {"$inc": {"stock": -1}})
    
    if sale_data.contact_lens_id:
        contact_lens = await db.optica_contact_lenses.find_one({"id": sale_data.contact_lens_id, "is_active": True})
        if not contact_lens:
            raise HTTPException(status_code=400, detail="Lente de contacto no encontrado")
        if contact_lens["stock"] < 1:
            raise HTTPException(status_code=400, detail="No hay stock disponible para este lente")
        contact_lens_price = contact_lens["sale_price"]
        subtotal += contact_lens_price
        await db.optica_contact_lenses.update_one({"id": sale_data.contact_lens_id}, {"$inc": {"stock": -1}})
    
    lens_items = []
    for item in sale_data.lens_items:
        lens_type = await db.optica_lens_types.find_one({"id": item.lens_type_id, "is_active": True})
        if not lens_type:
            raise HTTPException(status_code=400, detail=f"Tipo de lente no encontrado: {item.lens_type_id}")
        
        item_subtotal = item.unit_price * item.quantity
        lens_items.append({
            "lens_type_id": item.lens_type_id,
            "lens_type_name": lens_type["name"],
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "subtotal": item_subtotal
        })
        lens_total += item_subtotal
    
    subtotal += lens_total
    discount_amount = subtotal * (sale_data.discount_percent / 100)
    total = subtotal - discount_amount
    
    if sale_data.initial_payment > total:
        raise HTTPException(status_code=400, detail="El pago inicial no puede ser mayor al total")
    
    total_paid = sale_data.initial_payment
    balance_due = total - total_paid
    status = "pagado" if balance_due <= 0 else "pendiente"
    
    now = datetime.now(timezone.utc).isoformat()
    order_number = await get_next_order_number()
    
    sale_doc = {
        "id": str(uuid.uuid4()),
        "order_number": order_number,
        "patient_id": sale_data.patient_id,
        "doctor_id": sale_data.doctor_id or "",
        "frame_id": sale_data.frame_id or "",
        "frame_price": frame_price,
        "contact_lens_id": sale_data.contact_lens_id or "",
        "contact_lens_price": contact_lens_price,
        "lens_items": lens_items,
        "lens_total": lens_total,
        "subtotal": subtotal,
        "discount_percent": sale_data.discount_percent,
        "discount_amount": discount_amount,
        "total": total,
        "total_paid": total_paid,
        "balance_due": balance_due,
        "payment_method": sale_data.payment_method,
        "status": status,
        "notes": sale_data.notes or "",
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", current_user.get("username", "")),
        "created_at": now,
        "updated_at": now
    }
    
    await db.optica_sales.insert_one(sale_doc)
    if "_id" in sale_doc:
        del sale_doc["_id"]
    
    if sale_data.initial_payment > 0:
        payment_doc = {
            "id": str(uuid.uuid4()),
            "sale_id": sale_doc["id"],
            "amount": sale_data.initial_payment,
            "payment_method": sale_data.payment_method,
            "reference": "",
            "notes": "Pago inicial",
            "created_by": current_user["id"],
            "created_at": now
        }
        await db.optica_sale_payments.insert_one(payment_doc)
    
    enriched = await enrich_sale(sale_doc)
    return OpticaSaleResponse(**enriched)


@router.post("/sales/v2")
async def create_optica_sale_v2(sale_data: OpticaSaleCreateV2, current_user: dict = Depends(require_permission("manage_optica_sales"))):
    """
    Crear nueva venta de óptica (formato V2 desde POS)
    Acepta items[] genéricos en lugar del formato legacy con frame_id/contact_lens_id
    """
    if not sale_data.items:
        raise HTTPException(status_code=400, detail="Debe agregar al menos un producto")
    
    # Verificar paciente si se proporciona
    patient_name = sale_data.patient_name or "Consumidor Final"
    if sale_data.patient_id:
        patient = await db.patients.find_one({"id": sale_data.patient_id, "is_active": True})
        if patient:
            patient_name = f"{patient.get('primer_nombre', '')} {patient.get('primer_apellido', '')}".strip()
    
    # Procesar items y calcular totales
    processed_items = []
    frame_id = None
    frame_price = 0
    contact_lens_id = None
    contact_lens_price = 0
    lens_items = []
    subtotal = 0
    
    for item in sale_data.items:
        if item.type == "frame":
            frame = await db.optica_frames.find_one({"id": item.product_id, "is_active": True})
            if not frame:
                raise HTTPException(status_code=400, detail=f"Armazón no encontrado: {item.product_id}")
            if frame["stock"] < item.quantity:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para: {frame.get('brand', '')} {frame.get('model', '')}")
            
            frame_id = item.product_id
            frame_price = item.unit_price * item.quantity
            subtotal += frame_price
            
            # Descontar stock
            await db.optica_frames.update_one({"id": item.product_id}, {"$inc": {"stock": -item.quantity}})
            
            processed_items.append({
                "type": "frame",
                "product_id": item.product_id,
                "name": f"{frame.get('brand', '')} {frame.get('model', '')}",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal
            })
            
        elif item.type == "contact_lens":
            contact_lens = await db.optica_contact_lenses.find_one({"id": item.product_id, "is_active": True})
            if not contact_lens:
                raise HTTPException(status_code=400, detail=f"Lente de contacto no encontrado: {item.product_id}")
            if contact_lens["stock"] < item.quantity:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para lente de contacto")
            
            contact_lens_id = item.product_id
            contact_lens_price = item.unit_price * item.quantity
            subtotal += contact_lens_price
            
            # Descontar stock
            await db.optica_contact_lenses.update_one({"id": item.product_id}, {"$inc": {"stock": -item.quantity}})
            
            processed_items.append({
                "type": "contact_lens",
                "product_id": item.product_id,
                "name": f"{contact_lens.get('lens_type', '')} - {contact_lens.get('brand', '')}",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal
            })
            
        elif item.type == "lens_type":
            lens_type = await db.optica_lens_types.find_one({"id": item.product_id, "is_active": True})
            if not lens_type:
                raise HTTPException(status_code=400, detail=f"Tipo de lente no encontrado: {item.product_id}")
            
            lens_item = {
                "lens_type_id": item.product_id,
                "lens_type_name": lens_type["name"],
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal
            }
            lens_items.append(lens_item)
            subtotal += item.subtotal
            
            processed_items.append({
                "type": "lens_type",
                "product_id": item.product_id,
                "name": lens_type["name"],
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal
            })

        elif item.type == "accessory":
            accessory = await db.optica_accessories.find_one({"id": item.product_id, "is_active": True})
            if not accessory:
                raise HTTPException(status_code=400, detail=f"Accesorio no encontrado: {item.product_id}")
            if accessory["stock"] < item.quantity:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para: {accessory.get('name', '')}")

            subtotal += item.subtotal

            # Descontar stock
            await db.optica_accessories.update_one({"id": item.product_id}, {"$inc": {"stock": -item.quantity}})

            processed_items.append({
                "type": "accessory",
                "product_id": item.product_id,
                "name": f"{accessory.get('brand', '')} {accessory.get('name', '')}".strip(),
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal
            })
    
    # Calcular totales
    discount_percent = sale_data.discount_percent or 0
    if discount_percent > 0:
        discount_amount = round(subtotal * discount_percent / 100, 2)
    else:
        discount_amount = sale_data.discount or 0
        discount_percent = round(discount_amount / subtotal * 100, 2) if subtotal > 0 else 0
    autoriza = (sale_data.discount_authorized_by or "").strip()
    if discount_amount > 0 and not autoriza:
        raise HTTPException(status_code=400, detail="Debe indicar quién autoriza el descuento")
    total = round(subtotal - discount_amount, 2)
    # El precio ya incluye el IVA: se calcula "hacia adentro" sobre el total con
    # descuento, solo para efectos contables (no altera el total cobrado).
    iva_incluido = round(total - total / 1.12, 2)
    
    # Calcular total pagado (excluyendo montos de CxC)
    total_paid = sum(p.amount for p in sale_data.payments if p.method != 'Cuenta por Cobrar')
    balance_due = total - total_paid
    
    # Determinar método de pago principal
    if sale_data.payments:
        payment_method = sale_data.payments[0].method.lower()
        if len(sale_data.payments) > 1:
            payment_method = "mixto"
    else:
        payment_method = "efectivo"
    
    status = "pagado" if balance_due <= 0.01 else "pendiente"
    
    now = datetime.now(timezone.utc).isoformat()
    order_number = await get_next_order_number()
    
    sale_doc = {
        "id": str(uuid.uuid4()),
        "order_number": order_number,
        "patient_id": sale_data.patient_id or "",
        "patient_name": patient_name,
        "doctor_id": sale_data.doctor_id or "",
        "doctor_name": sale_data.doctor_name or "",
        "frame_id": frame_id or "",
        "frame_price": frame_price,
        "contact_lens_id": contact_lens_id or "",
        "contact_lens_price": contact_lens_price,
        "lens_items": lens_items,
        "lens_total": sum(li["subtotal"] for li in lens_items),
        "items_v2": processed_items,  # Guardar items en formato V2 también
        "subtotal": subtotal,
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "discount_authorized_by": autoriza,
        "total": total,
        "iva": iva_incluido,
        "total_paid": total_paid,
        "balance_due": balance_due,
        "payment_method": payment_method,
        "status": status,
        "notes": sale_data.notes or "",
        "prescription": sale_data.prescription,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", current_user.get("username", "")),
        "created_at": now,
        "updated_at": now,
        "tiene_cxc": sale_data.tiene_cxc,
        "monto_cxc": sale_data.monto_cxc
    }
    
    await db.optica_sales.insert_one(sale_doc)
    if "_id" in sale_doc:
        del sale_doc["_id"]
    
    # Registrar pagos
    for payment in sale_data.payments:
        if payment.method != 'Cuenta por Cobrar' and payment.amount > 0:
            payment_doc = {
                "id": str(uuid.uuid4()),
                "sale_id": sale_doc["id"],
                "amount": payment.amount,
                "payment_method": payment.method,
                "reference": payment.reference or "",
                "notes": "",
                "created_by": current_user["id"],
                "created_at": now
            }
            await db.optica_sale_payments.insert_one(payment_doc)
    
    # Retornar la venta creada
    return {
        "id": sale_doc["id"],
        "sale_number": order_number,
        "order_number": order_number,
        "patient_name": patient_name,
        "total": total,
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "discount_authorized_by": autoriza,
        "total_paid": total_paid,
        "balance_due": balance_due,
        "status": status,
        "tiene_cxc": sale_data.tiene_cxc,
        "monto_cxc": sale_data.monto_cxc,
        "message": "Venta registrada exitosamente"
    }


@router.post("/sales/{sale_id}/payments", response_model=SalePaymentResponse)
async def add_sale_payment(sale_id: str, payment_data: SalePaymentCreate, current_user: dict = Depends(require_permission("manage_optica_sales"))):
    """Registrar abono a una venta"""
    sale = await db.optica_sales.find_one({"id": sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    if sale["status"] == "pagado":
        raise HTTPException(status_code=400, detail="Esta venta ya está pagada")
    
    if sale["status"] == "cancelado":
        raise HTTPException(status_code=400, detail="No se pueden registrar abonos en una venta cancelada")
    
    if payment_data.amount > sale["balance_due"]:
        raise HTTPException(status_code=400, detail=f"El abono no puede ser mayor al saldo pendiente (Q{sale['balance_due']:.2f})")
    
    now = datetime.now(timezone.utc).isoformat()
    
    payment_doc = {
        "id": str(uuid.uuid4()),
        "sale_id": sale_id,
        "amount": payment_data.amount,
        "payment_method": payment_data.payment_method,
        "reference": payment_data.reference or "",
        "notes": payment_data.notes or "",
        "created_by": current_user["id"],
        "created_at": now
    }
    
    await db.optica_sale_payments.insert_one(payment_doc)
    if "_id" in payment_doc:
        del payment_doc["_id"]
    
    new_total_paid = sale["total_paid"] + payment_data.amount
    new_balance_due = sale["total"] - new_total_paid
    new_status = "pagado" if new_balance_due <= 0 else "pendiente"
    
    await db.optica_sales.update_one(
        {"id": sale_id},
        {"$set": {
            "total_paid": new_total_paid,
            "balance_due": max(0, new_balance_due),
            "status": new_status,
            "updated_at": now
        }}
    )
    
    creator = await db.users.find_one({"id": current_user["id"]}, {"_id": 0, "name": 1})
    payment_doc["created_by_name"] = creator["name"] if creator else ""
    
    return SalePaymentResponse(**payment_doc)


@router.put("/sales/{sale_id}/cancel")
async def cancel_optica_sale(sale_id: str, current_user: dict = Depends(require_role(["admin", "superadmin"]))):
    """Anular una venta de óptica y restaurar el inventario. Solo admin/superadmin.
    Revierte el stock de armazones, lentes de contacto y accesorios según los items
    de la venta; la caja/CxC de óptica se revierten al quedar la venta en estado
    'cancelado' (queda excluida de saldos, pendientes y reportes)."""
    sale = await db.optica_sales.find_one({"id": sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    if sale["status"] == "cancelado":
        raise HTTPException(status_code=400, detail="Esta venta ya está cancelada")

    # Revertir inventario a partir de los items V2 (respeta cantidades y tipo)
    items_v2 = sale.get("items_v2") or []
    if items_v2:
        for it in items_v2:
            qty = it.get("quantity", 1) or 1
            pid = it.get("product_id")
            if not pid:
                continue
            if it.get("type") == "frame":
                await db.optica_frames.update_one({"id": pid}, {"$inc": {"stock": qty}})
            elif it.get("type") == "contact_lens":
                await db.optica_contact_lenses.update_one({"id": pid}, {"$inc": {"stock": qty}})
            elif it.get("type") == "accessory":
                await db.optica_accessories.update_one({"id": pid}, {"$inc": {"stock": qty}})
            # lens_type no controla stock
    else:
        # Legacy: venta sin items_v2
        if sale.get("frame_id"):
            await db.optica_frames.update_one({"id": sale["frame_id"]}, {"$inc": {"stock": 1}})
        if sale.get("contact_lens_id"):
            await db.optica_contact_lenses.update_one({"id": sale["contact_lens_id"]}, {"$inc": {"stock": 1}})

    await db.optica_sales.update_one(
        {"id": sale_id},
        {"$set": {
            "status": "cancelado",
            "cancelled_by": current_user["id"],
            "cancelled_by_name": current_user.get("name", current_user.get("username", "")),
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    return {"message": "Venta anulada correctamente. Inventario restaurado."}


# ==================== DASHBOARD ROUTES ====================

@router.get("/dashboard/stats")
async def get_optica_dashboard_stats(current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener estadísticas del dashboard de óptica"""
    now = datetime.now(timezone.utc)
    first_day_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    pipeline_month = [
        {"$match": {
            "created_at": {"$gte": first_day_month.isoformat()},
            "status": {"$ne": "cancelado"}
        }},
        {"$group": {
            "_id": None,
            "total_ventas": {"$sum": "$total"},
            "total_cobrado": {"$sum": "$total_paid"},
            "count": {"$sum": 1}
        }}
    ]
    
    month_result = await db.optica_sales.aggregate(pipeline_month).to_list(1)
    month_stats = month_result[0] if month_result else {"total_ventas": 0, "total_cobrado": 0, "count": 0}
    
    pipeline_pending = [
        {"$match": {"status": "pendiente"}},
        {"$group": {
            "_id": None,
            "saldo_pendiente": {"$sum": {"$subtract": ["$total", "$total_paid"]}},
            "count_pendientes": {"$sum": 1}
        }}
    ]
    
    pending_result = await db.optica_sales.aggregate(pipeline_pending).to_list(1)
    pending_stats = pending_result[0] if pending_result else {"saldo_pendiente": 0, "count_pendientes": 0}
    
    return {
        "ventas_mes": month_stats.get("total_ventas", 0),
        "cobrado_mes": month_stats.get("total_cobrado", 0),
        "ordenes_mes": month_stats.get("count", 0),
        "saldo_pendiente": pending_stats.get("saldo_pendiente", 0),
        "ordenes_pendientes": pending_stats.get("count_pendientes", 0)
    }


@router.get("/dashboard/monthly-chart")
async def get_optica_monthly_chart(current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener datos de ventas por mes (últimos 6 meses)"""
    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=180)
    
    pipeline = [
        {"$match": {
            "created_at": {"$gte": six_months_ago.isoformat()},
            "status": {"$ne": "cancelado"}
        }},
        {"$addFields": {
            "created_date": {"$dateFromString": {"dateString": "$created_at"}}
        }},
        {"$group": {
            "_id": {
                "year": {"$year": "$created_date"},
                "month": {"$month": "$created_date"}
            },
            "total": {"$sum": "$total"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]
    
    results = await db.optica_sales.aggregate(pipeline).to_list(12)
    
    month_names = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    chart_data = []
    for r in results:
        chart_data.append({
            "mes": f"{month_names[r['_id']['month']]} {r['_id']['year']}",
            "ventas": r["total"],
            "ordenes": r["count"]
        })
    
    return chart_data


@router.get("/dashboard/top-doctors")
async def get_optica_top_doctors(limit: int = 5, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener top médicos por ventas"""
    pipeline = [
        {"$match": {"doctor_id": {"$ne": None}, "status": {"$ne": "cancelado"}}},
        {"$group": {
            "_id": "$doctor_id",
            "total_ventas": {"$sum": "$total"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"total_ventas": -1}},
        {"$limit": limit}
    ]
    
    results = await db.optica_sales.aggregate(pipeline).to_list(limit)
    
    top_doctors = []
    for r in results:
        doctor = await db.doctors.find_one({"id": r["_id"]}, {"_id": 0, "name": 1})
        top_doctors.append({
            "doctor_id": r["_id"],
            "doctor_name": doctor.get("name", "Sin nombre") if doctor else "Sin nombre",
            "total_ventas": r["total_ventas"],
            "count": r["count"]
        })
    
    return top_doctors


@router.get("/dashboard/top-brands")
async def get_optica_top_brands(limit: int = 5, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener top marcas de aros por ventas"""
    pipeline = [
        {"$match": {"frame_id": {"$ne": None}, "status": {"$ne": "cancelado"}}},
        {"$lookup": {
            "from": "optica_frames",
            "localField": "frame_id",
            "foreignField": "id",
            "as": "frame"
        }},
        {"$unwind": "$frame"},
        {"$group": {
            "_id": "$frame.brand",
            "total_ventas": {"$sum": "$frame_price"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    
    results = await db.optica_sales.aggregate(pipeline).to_list(limit)
    
    return [{"brand": r["_id"], "total_ventas": r["total_ventas"], "count": r["count"]} for r in results]


# ==================== PURCHASES ROUTES ====================

@router.get("/purchases", response_model=OpticaPurchaseListResponse)
async def get_optica_purchases(
    search: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Obtener lista de compras de óptica"""
    query = {}
    
    if search:
        query["$or"] = [
            {"description": {"$regex": search, "$options": "i"}},
            {"invoice_number": {"$regex": search, "$options": "i"}}
        ]
    
    if category:
        query["category"] = category
    
    purchases = await db.optica_purchases.find(query, {"_id": 0}).sort("purchase_date", -1).to_list(500)
    
    for purchase in purchases:
        if purchase.get("supplier_id"):
            supplier = await db.suppliers.find_one({"id": purchase["supplier_id"]}, {"_id": 0, "name": 1})
            purchase["supplier_name"] = supplier.get("name") if supplier else None
        else:
            purchase["supplier_name"] = None
    
    return {"data": purchases, "total": len(purchases)}


@router.get("/purchases/{purchase_id}", response_model=OpticaPurchaseResponse)
async def get_optica_purchase(purchase_id: str, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener detalle de una compra"""
    purchase = await db.optica_purchases.find_one({"id": purchase_id}, {"_id": 0})
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    if purchase.get("supplier_id"):
        supplier = await db.suppliers.find_one({"id": purchase["supplier_id"]}, {"_id": 0, "name": 1})
        purchase["supplier_name"] = supplier.get("name") if supplier else None
    
    return purchase


@router.post("/purchases", response_model=OpticaPurchaseResponse)
async def create_optica_purchase(
    purchase: OpticaPurchaseCreate,
    current_user: dict = Depends(require_permission("manage_optica_inventory"))
):
    """Crear una nueva compra de óptica"""
    now = datetime.now(timezone.utc).isoformat()
    
    new_purchase = {
        "id": str(uuid.uuid4()),
        **purchase.model_dump(),
        "created_at": now,
        "updated_at": now,
        "created_by": current_user["id"]
    }
    
    await db.optica_purchases.insert_one(new_purchase)
    del new_purchase["_id"]
    
    if new_purchase.get("supplier_id"):
        supplier = await db.suppliers.find_one({"id": new_purchase["supplier_id"]}, {"_id": 0, "name": 1})
        new_purchase["supplier_name"] = supplier.get("name") if supplier else None
    else:
        new_purchase["supplier_name"] = None
    
    return new_purchase


@router.put("/purchases/{purchase_id}", response_model=OpticaPurchaseResponse)
async def update_optica_purchase(
    purchase_id: str,
    purchase: OpticaPurchaseUpdate,
    current_user: dict = Depends(require_permission("manage_optica_inventory"))
):
    """Actualizar una compra de óptica"""
    existing = await db.optica_purchases.find_one({"id": purchase_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    update_data = {k: v for k, v in purchase.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.optica_purchases.update_one({"id": purchase_id}, {"$set": update_data})
    
    updated = await db.optica_purchases.find_one({"id": purchase_id}, {"_id": 0})
    
    if updated.get("supplier_id"):
        supplier = await db.suppliers.find_one({"id": updated["supplier_id"]}, {"_id": 0, "name": 1})
        updated["supplier_name"] = supplier.get("name") if supplier else None
    else:
        updated["supplier_name"] = None
    
    return updated


@router.delete("/purchases/{purchase_id}")
async def delete_optica_purchase(
    purchase_id: str,
    current_user: dict = Depends(require_permission("manage_optica_inventory"))
):
    """Eliminar una compra de óptica"""
    existing = await db.optica_purchases.find_one({"id": purchase_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    await db.optica_purchases.delete_one({"id": purchase_id})
    
    return {"message": "Compra eliminada correctamente"}


# ==================== DASHBOARD AVANZADO DE ÓPTICA ====================

@router.get("/dashboard/ventas-dia")
async def get_ventas_del_dia(current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener ventas del día actual (hora de Guatemala) con desglose"""
    inicio_utc, fin_utc = dia_gt_a_rango_utc(today_str_gt())

    pipeline = [
        {"$match": {
            "created_at": {"$gte": inicio_utc, "$lte": fin_utc},
            "status": {"$ne": "cancelado"}
        }},
        {"$group": {
            "_id": None,
            "total_ventas": {"$sum": "$total"},
            "total_cobrado": {"$sum": "$total_paid"},
            "total_descuentos": {"$sum": "$discount_amount"},
            "num_ordenes": {"$sum": 1}
        }}
    ]
    
    result = await db.optica_sales.aggregate(pipeline).to_list(1)
    stats = result[0] if result else {"total_ventas": 0, "total_cobrado": 0, "total_descuentos": 0, "num_ordenes": 0}
    
    # Obtener ventas individuales del día
    ventas_dia = await db.optica_sales.find(
        {"created_at": {"$gte": inicio_utc, "$lte": fin_utc}, "status": {"$ne": "cancelado"}},
        {"_id": 0, "id": 1, "order_number": 1, "patient_name": 1, "total": 1, "total_paid": 1, "status": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(100)

    # Cuentas por cobrar (saldo pendiente global, no solo del día)
    pend_result = await db.optica_sales.aggregate([
        {"$match": {"status": "pendiente", "balance_due": {"$gt": 0}}},
        {"$group": {"_id": None, "total": {"$sum": "$balance_due"}, "count": {"$sum": 1}}}
    ]).to_list(1)
    cxc = pend_result[0] if pend_result else {"total": 0, "count": 0}

    return {
        "fecha": today_str_gt(),
        "total_ventas": round(stats.get("total_ventas", 0), 2),
        "total_cobrado": round(stats.get("total_cobrado", 0), 2),
        "total_descuentos": round(stats.get("total_descuentos", 0), 2),
        "num_ordenes": stats.get("num_ordenes", 0),
        "saldo_pendiente": round(stats.get("total_ventas", 0) - stats.get("total_cobrado", 0), 2),
        "cuentas_por_cobrar": round(cxc.get("total", 0), 2),
        "cuentas_por_cobrar_count": cxc.get("count", 0),
        "ventas": ventas_dia
    }


class MetasVentasUpdate(BaseModel):
    meta_diaria: float = Field(default=0, ge=0)
    meta_mensual: float = Field(..., ge=0)


async def _get_metas_doc() -> dict:
    doc = await db.optica_dashboard_config.find_one({"_id": "metas_ventas"})
    return {
        "meta_diaria": (doc or {}).get("meta_diaria", 0),
        "meta_mensual": (doc or {}).get("meta_mensual", 0),
    }


@router.get("/dashboard/metas")
async def get_metas_ventas(current_user: dict = Depends(require_permission("view_optica"))):
    """Metas de ventas (día y mes) con el progreso actual en hora de Guatemala."""
    metas = await _get_metas_doc()

    # Ventas de hoy (día local de Guatemala)
    inicio_dia_utc, fin_dia_utc = dia_gt_a_rango_utc(today_str_gt())
    dia_result = await db.optica_sales.aggregate([
        {"$match": {"created_at": {"$gte": inicio_dia_utc, "$lte": fin_dia_utc}, "status": {"$ne": "cancelado"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]).to_list(1)
    ventas_hoy = round(dia_result[0]["total"], 2) if dia_result else 0

    # Ventas del mes en curso (día 1 local de Guatemala -> ahora)
    inicio_mes_str = now_gt().date().replace(day=1).strftime("%Y-%m-%d")
    inicio_mes_utc, _ = dia_gt_a_rango_utc(inicio_mes_str)
    mes_result = await db.optica_sales.aggregate([
        {"$match": {"created_at": {"$gte": inicio_mes_utc}, "status": {"$ne": "cancelado"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]).to_list(1)
    ventas_mes = round(mes_result[0]["total"], 2) if mes_result else 0

    # Proyección de cierre de mes al ritmo actual (hora de Guatemala)
    import calendar
    ahora_gt = now_gt()
    dias_mes = calendar.monthrange(ahora_gt.year, ahora_gt.month)[1]
    dia_actual = ahora_gt.day
    proyeccion_mes = round(ventas_mes / dia_actual * dias_mes, 2) if dia_actual > 0 else ventas_mes

    meta_d = metas["meta_diaria"]
    meta_m = metas["meta_mensual"]
    return {
        "meta_diaria": meta_d,
        "meta_mensual": meta_m,
        "ventas_hoy": ventas_hoy,
        "ventas_mes": ventas_mes,
        "progreso_dia": round(ventas_hoy / meta_d * 100, 1) if meta_d > 0 else 0,
        "progreso_mes": round(ventas_mes / meta_m * 100, 1) if meta_m > 0 else 0,
        "falta_dia": round(max(meta_d - ventas_hoy, 0), 2),
        "falta_mes": round(max(meta_m - ventas_mes, 0), 2),
        "proyeccion_mes": proyeccion_mes,
        "dias_transcurridos": dia_actual,
        "dias_mes": dias_mes,
    }


@router.put("/dashboard/metas")
async def set_metas_ventas(
    data: MetasVentasUpdate,
    current_user: dict = Depends(require_permission("manage_optica_sales"))
):
    """Definir las metas de ventas (día y mes)."""
    await db.optica_dashboard_config.update_one(
        {"_id": "metas_ventas"},
        {"$set": {
            "meta_diaria": round(data.meta_diaria, 2),
            "meta_mensual": round(data.meta_mensual, 2),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user.get("id"),
        }},
        upsert=True
    )
    return {"meta_diaria": round(data.meta_diaria, 2), "meta_mensual": round(data.meta_mensual, 2)}


@router.get("/dashboard/rentabilidad")
async def get_rentabilidad_optica(
    periodo: str = Query("mes", description="dia, semana, mes, año"),
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Calcular rentabilidad entre precio costo y precio venta de productos vendidos"""
    now = datetime.now(timezone.utc)
    hoy_gt = now_gt()

    # Determinar fecha de inicio (día local de Guatemala) según período
    if periodo == "dia":
        inicio_date_gt = hoy_gt.date()
    elif periodo == "semana":
        inicio_date_gt = (hoy_gt - timedelta(days=7)).date()
    elif periodo == "año":
        inicio_date_gt = hoy_gt.date().replace(month=1, day=1)
    else:  # mes
        inicio_date_gt = hoy_gt.date().replace(day=1)
    inicio_str = inicio_date_gt.strftime("%Y-%m-%d")
    # Inicio del día local de Guatemala expresado en UTC ISO
    inicio_utc, _ = dia_gt_a_rango_utc(inicio_str)
    fecha_inicio = datetime.fromisoformat(inicio_utc)
    
    # Obtener todas las ventas del período
    ventas = await db.optica_sales.find({
        "created_at": {"$gte": inicio_utc},
        "status": {"$ne": "cancelado"}
    }, {"_id": 0}).to_list(5000)
    
    # Cargar catálogos de productos
    frames = {f["id"]: f for f in await db.optica_frames.find({}, {"_id": 0}).to_list(1000)}
    lentes_contacto = {l["id"]: l for l in await db.optica_contact_lenses.find({}, {"_id": 0}).to_list(1000)}
    tipos_lente = {t["id"]: t for t in await db.optica_lens_types.find({}, {"_id": 0}).to_list(1000)}
    accesorios = {a["id"]: a for a in await db.optica_accessories.find({}, {"_id": 0}).to_list(1000)}
    
    # Calcular rentabilidad
    total_ingresos = 0
    total_costos = 0
    desglose_categorias = {
        "aros": {"ingresos": 0, "costos": 0, "cantidad": 0},
        "lentes_contacto": {"ingresos": 0, "costos": 0, "cantidad": 0},
        "tipos_lente": {"ingresos": 0, "costos": 0, "cantidad": 0},
        "accesorios": {"ingresos": 0, "costos": 0, "cantidad": 0},
        "otros": {"ingresos": 0, "costos": 0, "cantidad": 0}
    }
    
    for venta in ventas:
        items_v2 = venta.get("items_v2", [])

        if items_v2:
            # Ventas del POS (V2): contienen TODOS los productos vendidos
            for item in items_v2:
                tipo_item = item.get("type")
                producto_id = item.get("product_id")
                subtotal = item.get("subtotal", 0)
                cantidad = item.get("quantity", 1)

                if tipo_item == "frame":
                    frame = frames.get(producto_id)
                    costo = frame.get("cost_price", 0) * cantidad if frame else 0
                    cat = "aros"
                elif tipo_item == "contact_lens":
                    lente = lentes_contacto.get(producto_id)
                    costo = lente.get("cost_price", 0) * cantidad if lente else 0
                    cat = "lentes_contacto"
                elif tipo_item == "lens_type":
                    tipo = tipos_lente.get(producto_id)
                    costo = tipo.get("cost_price", tipo.get("default_price", 0) * 0.5) * cantidad if tipo else 0
                    cat = "tipos_lente"
                elif tipo_item == "accessory":
                    acc = accesorios.get(producto_id)
                    costo = acc.get("cost_price", 0) * cantidad if acc else 0
                    cat = "accesorios"
                else:
                    costo = 0
                    cat = "otros"

                desglose_categorias[cat]["ingresos"] += subtotal
                desglose_categorias[cat]["costos"] += costo
                desglose_categorias[cat]["cantidad"] += cantidad
                total_ingresos += subtotal
                total_costos += costo
        else:
            # Ventas legacy (sin items_v2): usar campos individuales
            if venta.get("frame_id"):
                frame = frames.get(venta["frame_id"])
                if frame:
                    precio_venta = venta.get("frame_price", frame.get("sale_price", 0))
                    precio_costo = frame.get("cost_price", 0)
                    total_ingresos += precio_venta
                    total_costos += precio_costo
                    desglose_categorias["aros"]["ingresos"] += precio_venta
                    desglose_categorias["aros"]["costos"] += precio_costo
                    desglose_categorias["aros"]["cantidad"] += 1

            if venta.get("contact_lens_id"):
                lente = lentes_contacto.get(venta["contact_lens_id"])
                if lente:
                    precio_venta = venta.get("contact_lens_price", lente.get("sale_price", 0))
                    precio_costo = lente.get("cost_price", 0)
                    total_ingresos += precio_venta
                    total_costos += precio_costo
                    desglose_categorias["lentes_contacto"]["ingresos"] += precio_venta
                    desglose_categorias["lentes_contacto"]["costos"] += precio_costo
                    desglose_categorias["lentes_contacto"]["cantidad"] += 1

            for item in venta.get("lens_items", []):
                tipo = tipos_lente.get(item.get("lens_type_id"))
                if tipo:
                    subtotal = item.get("subtotal", 0)
                    cantidad = item.get("quantity", 1)
                    costo_unitario = tipo.get("cost_price", tipo.get("default_price", 0) * 0.5)
                    total_ingresos += subtotal
                    total_costos += costo_unitario * cantidad
                    desglose_categorias["tipos_lente"]["ingresos"] += subtotal
                    desglose_categorias["tipos_lente"]["costos"] += costo_unitario * cantidad
                    desglose_categorias["tipos_lente"]["cantidad"] += cantidad
    
    ganancia = total_ingresos - total_costos
    margen = (ganancia / total_ingresos * 100) if total_ingresos > 0 else 0

    # Compras/pagos de óptica del mismo período (egresos)
    # purchase_date puede estar en formato 'YYYY-MM-DD' o ISO; comparar contra
    # la fecha-only garantiza incluir compras del primer día del período.
    compras_result = await db.optica_purchases.aggregate([
        {"$match": {"purchase_date": {"$gte": inicio_str}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}, "count": {"$sum": 1}}}
    ]).to_list(1)
    total_compras = compras_result[0]["total"] if compras_result else 0
    num_compras = compras_result[0]["count"] if compras_result else 0
    utilidad = total_ingresos - total_compras
    
    # Calcular margen por categoría
    for cat in desglose_categorias:
        ing = desglose_categorias[cat]["ingresos"]
        cost = desglose_categorias[cat]["costos"]
        desglose_categorias[cat]["ganancia"] = ing - cost
        desglose_categorias[cat]["margen"] = round((ing - cost) / ing * 100, 2) if ing > 0 else 0
    
    return {
        "periodo": periodo,
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_fin": now.isoformat(),
        "total_ingresos": round(total_ingresos, 2),
        "total_costos": round(total_costos, 2),
        "ganancia_bruta": round(ganancia, 2),
        "margen_porcentaje": round(margen, 2),
        "total_compras": round(total_compras, 2),
        "num_compras": num_compras,
        "utilidad": round(utilidad, 2),
        "desglose_categorias": desglose_categorias,
        "num_ventas": len(ventas)
    }


@router.get("/dashboard/ventas-por-origen")
async def get_ventas_por_origen(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Obtener ventas agrupadas por origen de paciente (Particular, IGSS, Seguro Privado, Otra institución)"""
    now = datetime.now(timezone.utc)
    
    # Fechas por defecto: mes actual
    if not fecha_inicio:
        fecha_inicio = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    if not fecha_fin:
        fecha_fin = now.isoformat()
    
    # Obtener ventas del período
    ventas = await db.optica_sales.find({
        "created_at": {"$gte": fecha_inicio, "$lte": fecha_fin},
        "status": {"$ne": "cancelado"}
    }, {"_id": 0, "patient_id": 1, "total": 1, "total_paid": 1, "discount_amount": 1}).to_list(10000)
    
    # Obtener info de pacientes
    patient_ids = list(set(v.get("patient_id") for v in ventas if v.get("patient_id")))
    patients = {p["id"]: p for p in await db.patients.find(
        {"id": {"$in": patient_ids}}, 
        {"_id": 0, "id": 1, "referral_institution": 1, "other_institution_name": 1, "igss_unit_id": 1}
    ).to_list(10000)}
    
    # Obtener unidades IGSS
    igss_units = {u["id"]: u["name"] for u in await db.igss_units.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(100)}
    
    # Agrupar por origen
    origenes = {
        "particular": {"label": "Particular", "total": 0, "cobrado": 0, "descuentos": 0, "count": 0},
        "igss": {"label": "IGSS", "total": 0, "cobrado": 0, "descuentos": 0, "count": 0, "unidades": {}},
        "seguro_privado": {"label": "Seguro Privado", "total": 0, "cobrado": 0, "descuentos": 0, "count": 0},
        "otra": {"label": "Otra Institución", "total": 0, "cobrado": 0, "descuentos": 0, "count": 0, "instituciones": {}},
        "sin_paciente": {"label": "Sin Paciente Asociado", "total": 0, "cobrado": 0, "descuentos": 0, "count": 0}
    }
    
    for venta in ventas:
        patient = patients.get(venta.get("patient_id"))
        
        if not patient:
            origenes["sin_paciente"]["total"] += venta.get("total", 0)
            origenes["sin_paciente"]["cobrado"] += venta.get("total_paid", 0)
            origenes["sin_paciente"]["descuentos"] += venta.get("discount_amount", 0)
            origenes["sin_paciente"]["count"] += 1
            continue
        
        origen = patient.get("referral_institution", "particular")
        
        if origen not in origenes:
            origen = "particular"
        
        origenes[origen]["total"] += venta.get("total", 0)
        origenes[origen]["cobrado"] += venta.get("total_paid", 0)
        origenes[origen]["descuentos"] += venta.get("discount_amount", 0)
        origenes[origen]["count"] += 1
        
        # Desglose por unidad IGSS
        if origen == "igss":
            igss_unit_id = patient.get("igss_unit_id")
            if igss_unit_id:
                unit_name = igss_units.get(igss_unit_id, "Unidad Desconocida")
                if unit_name not in origenes["igss"]["unidades"]:
                    origenes["igss"]["unidades"][unit_name] = {"total": 0, "count": 0}
                origenes["igss"]["unidades"][unit_name]["total"] += venta.get("total", 0)
                origenes["igss"]["unidades"][unit_name]["count"] += 1
        
        # Desglose por otra institución
        if origen == "otra":
            inst_name = patient.get("other_institution_name", "Sin especificar")
            if inst_name not in origenes["otra"]["instituciones"]:
                origenes["otra"]["instituciones"][inst_name] = {"total": 0, "count": 0}
            origenes["otra"]["instituciones"][inst_name]["total"] += venta.get("total", 0)
            origenes["otra"]["instituciones"][inst_name]["count"] += 1
    
    # Calcular totales
    total_general = sum(o["total"] for o in origenes.values())
    
    # Agregar porcentaje a cada origen
    for key in origenes:
        origenes[key]["porcentaje"] = round(origenes[key]["total"] / total_general * 100, 2) if total_general > 0 else 0
    
    return {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "total_general": round(total_general, 2),
        "origenes": origenes
    }


@router.get("/dashboard/informe-mensual")
async def get_informe_mensual_optica(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Generar informe mensual completo de ventas y compras de óptica"""
    # Calcular rango de fechas
    fecha_inicio = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        fecha_fin = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fecha_fin = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    
    month_names = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    # === VENTAS ===
    ventas = await db.optica_sales.find({
        "created_at": {"$gte": fecha_inicio.isoformat(), "$lt": fecha_fin.isoformat()},
        "status": {"$ne": "cancelado"}
    }, {"_id": 0}).to_list(5000)
    
    total_ventas = sum(v.get("total", 0) for v in ventas)
    total_cobrado = sum(v.get("total_paid", 0) for v in ventas)
    total_descuentos = sum(v.get("discount_amount", 0) for v in ventas)
    
    # Ventas por día
    ventas_por_dia = {}
    for v in ventas:
        fecha = v.get("created_at", "")[:10]
        if fecha not in ventas_por_dia:
            ventas_por_dia[fecha] = {"total": 0, "count": 0}
        ventas_por_dia[fecha]["total"] += v.get("total", 0)
        ventas_por_dia[fecha]["count"] += 1
    
    # === COMPRAS ===
    compras = await db.optica_purchases.find({
        "purchase_date": {"$gte": fecha_inicio.isoformat(), "$lt": fecha_fin.isoformat()}
    }, {"_id": 0}).to_list(1000)
    
    total_compras = sum(c.get("total_amount", 0) for c in compras)
    
    # Compras por categoría
    compras_por_categoria = {}
    for c in compras:
        cat = c.get("category", "Otros")
        if cat not in compras_por_categoria:
            compras_por_categoria[cat] = {"total": 0, "count": 0}
        compras_por_categoria[cat]["total"] += c.get("total_amount", 0)
        compras_por_categoria[cat]["count"] += 1
    
    # === TOP PRODUCTOS (todos los tipos vendidos) ===
    productos_vendidos = {}
    frames_db = {f["id"]: f for f in await db.optica_frames.find({}, {"_id": 0}).to_list(1000)}
    lc_db = {l["id"]: l for l in await db.optica_contact_lenses.find({}, {"_id": 0}).to_list(1000)}
    tipos_db = {t["id"]: t for t in await db.optica_lens_types.find({}, {"_id": 0}).to_list(1000)}
    acc_db = {a["id"]: a for a in await db.optica_accessories.find({}, {"_id": 0}).to_list(1000)}

    def _acumular(key, cantidad, total):
        if key not in productos_vendidos:
            productos_vendidos[key] = {"cantidad": 0, "total": 0}
        productos_vendidos[key]["cantidad"] += cantidad
        productos_vendidos[key]["total"] += total

    for v in ventas:
        items_v2 = v.get("items_v2", [])
        if items_v2:
            for item in items_v2:
                tipo_item = item.get("type")
                pid = item.get("product_id")
                cant = item.get("quantity", 1)
                sub = item.get("subtotal", 0)
                if tipo_item == "frame":
                    frame = frames_db.get(pid)
                    nombre = f"ARO: {frame.get('brand', '')} {frame.get('model', '')}".strip() if frame else f"ARO: {item.get('name', 'Armazón')}"
                elif tipo_item == "contact_lens":
                    lc = lc_db.get(pid)
                    nombre = f"LC: {lc.get('brand', '')} {lc.get('name', '')}".strip() if lc else f"LC: {item.get('name', 'Lente contacto')}"
                elif tipo_item == "lens_type":
                    tipo = tipos_db.get(pid)
                    nombre = f"LENTE: {tipo.get('name', '')}".strip() if tipo else f"LENTE: {item.get('name', 'Lente')}"
                elif tipo_item == "accessory":
                    acc = acc_db.get(pid)
                    nombre = f"ACC: {acc.get('brand', '')} {acc.get('name', '')}".strip() if acc else f"ACC: {item.get('name', 'Accesorio')}"
                else:
                    nombre = item.get("name", "Otro")
                _acumular(nombre, cant, sub)
        else:
            # Ventas legacy sin items_v2
            if v.get("frame_id"):
                frame = frames_db.get(v["frame_id"])
                if frame:
                    _acumular(f"ARO: {frame.get('brand', '')} {frame.get('model', '')}".strip(), 1, v.get("frame_price", 0))
            if v.get("contact_lens_id"):
                lc = lc_db.get(v["contact_lens_id"])
                if lc:
                    _acumular(f"LC: {lc.get('brand', '')} {lc.get('name', '')}".strip(), 1, v.get("contact_lens_price", 0))
            for item in v.get("lens_items", []):
                tipo = tipos_db.get(item.get("lens_type_id"))
                nombre = tipo.get("name", "Lente") if tipo else "Lente"
                _acumular(f"LENTE: {nombre}", item.get("quantity", 1), item.get("subtotal", 0))
    
    top_productos = sorted(
        [{"nombre": k, **v} for k, v in productos_vendidos.items()],
        key=lambda x: x["total"],
        reverse=True
    )[:10]
    
    return {
        "periodo": f"{month_names[month]} {year}",
        "year": year,
        "month": month,
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_fin": fecha_fin.isoformat(),
        "ventas": {
            "total": round(total_ventas, 2),
            "cobrado": round(total_cobrado, 2),
            "pendiente": round(total_ventas - total_cobrado, 2),
            "descuentos": round(total_descuentos, 2),
            "num_ordenes": len(ventas),
            "promedio_orden": round(total_ventas / len(ventas), 2) if ventas else 0,
            "por_dia": ventas_por_dia
        },
        "compras": {
            "total": round(total_compras, 2),
            "num_compras": len(compras),
            "por_categoria": compras_por_categoria
        },
        "balance": {
            "ingresos": round(total_cobrado, 2),
            "egresos": round(total_compras, 2),
            "resultado": round(total_cobrado - total_compras, 2)
        },
        "top_productos": top_productos
    }


@router.get("/dashboard/historial-mensual")
async def get_historial_mensual_optica(
    meses: int = Query(12, ge=1, le=24),
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Obtener historial de ventas y compras mensuales"""
    now = datetime.now(timezone.utc)
    
    month_names = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    historial = []
    
    for i in range(meses):
        # Calcular mes
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        
        fecha_inicio = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            fecha_fin = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            fecha_fin = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        # Ventas
        pipeline_ventas = [
            {"$match": {
                "created_at": {"$gte": fecha_inicio.isoformat(), "$lt": fecha_fin.isoformat()},
                "status": {"$ne": "cancelado"}
            }},
            {"$group": {
                "_id": None,
                "total": {"$sum": "$total"},
                "cobrado": {"$sum": "$total_paid"},
                "count": {"$sum": 1}
            }}
        ]
        ventas_result = await db.optica_sales.aggregate(pipeline_ventas).to_list(1)
        ventas = ventas_result[0] if ventas_result else {"total": 0, "cobrado": 0, "count": 0}
        
        # Compras
        pipeline_compras = [
            {"$match": {
                "purchase_date": {"$gte": fecha_inicio.isoformat(), "$lt": fecha_fin.isoformat()}
            }},
            {"$group": {
                "_id": None,
                "total": {"$sum": "$total_amount"},
                "count": {"$sum": 1}
            }}
        ]
        compras_result = await db.optica_purchases.aggregate(pipeline_compras).to_list(1)
        compras = compras_result[0] if compras_result else {"total": 0, "count": 0}
        
        historial.append({
            "mes": f"{month_names[month]} {year}",
            "year": year,
            "month": month,
            "ventas": round(ventas.get("total", 0), 2),
            "cobrado": round(ventas.get("cobrado", 0), 2),
            "compras": round(compras.get("total", 0), 2),
            "ganancia": round(ventas.get("cobrado", 0) - compras.get("total", 0), 2),
            "num_ventas": ventas.get("count", 0),
            "num_compras": compras.get("count", 0)
        })
    
    # Invertir para tener el más antiguo primero
    historial.reverse()
    
    return {
        "meses_analizados": meses,
        "historial": historial
    }

