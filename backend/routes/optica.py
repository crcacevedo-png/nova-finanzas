# /app/backend/routes/optica.py
# Módulo completo de Óptica - Médicos, Inventario, Ventas, Dashboard, Compras

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
import uuid

from config.database import db
from routes.auth import get_current_user, require_permission


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

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class DoctorResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    specialty: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    license_number: Optional[str] = ""
    notes: Optional[str] = ""
    is_active: bool = True
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
    cost_price: float
    sale_price: float
    stock: int
    entry_date: str
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class FrameInventoryListResponse(BaseModel):
    data: List[FrameInventoryResponse]
    total: int

# Lentes de Contacto
class ContactLensInventoryBase(BaseModel):
    lens_type: Literal["esferico", "torico", "multifocal", "cosmetico"]
    brand: Optional[str] = ""
    description: Optional[str] = ""
    cost_price: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    stock: int = Field(ge=0)

class ContactLensInventoryCreate(ContactLensInventoryBase):
    pass

class ContactLensInventoryUpdate(BaseModel):
    lens_type: Optional[Literal["esferico", "torico", "multifocal", "cosmetico"]] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    cost_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None

class ContactLensInventoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    lens_type: str
    brand: Optional[str] = ""
    description: Optional[str] = ""
    cost_price: float
    sale_price: float
    stock: int
    entry_date: str
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class ContactLensInventoryListResponse(BaseModel):
    data: List[ContactLensInventoryResponse]
    total: int

# Tipos de Lente
class LensTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""
    default_price: float = Field(ge=0)

class LensTypeCreate(LensTypeBase):
    pass

class LensTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_price: Optional[float] = None
    is_active: Optional[bool] = None

class LensTypeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: Optional[str] = ""
    default_price: float
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class LensTypeListResponse(BaseModel):
    data: List[LensTypeResponse]
    total: int

# Ventas
class SaleLineItem(BaseModel):
    lens_type_id: str
    lens_type_name: Optional[str] = ""
    quantity: int = Field(ge=1, default=1)
    unit_price: float = Field(ge=0)
    subtotal: float = Field(ge=0)

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
    subtotal: float
    discount_percent: float
    discount_amount: float
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
    prefix = datetime.now(timezone.utc).strftime("ORD-%Y%m-")
    
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
    # Paciente
    patient = await db.patients.find_one({"id": sale["patient_id"]}, {"_id": 0})
    if patient:
        sale["patient_name"] = f"{patient['first_name']} {patient['last_name']}"
        sale["patient_phone"] = patient.get("phone", "")
    else:
        sale["patient_name"] = "Paciente no encontrado"
        sale["patient_phone"] = ""
    
    # Médico
    if sale.get("doctor_id"):
        doctor = await db.doctors.find_one({"id": sale["doctor_id"]}, {"_id": 0})
        sale["doctor_name"] = doctor["name"] if doctor else ""
    else:
        sale["doctor_name"] = ""
    
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
            sale["contact_lens_info"] = f"{contact_lens['lens_type'].capitalize()} - {contact_lens.get('brand', '')}"
            sale["contact_lens_price"] = sale.get("contact_lens_price", contact_lens["sale_price"])
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
        "is_active": True,
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
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to + "T23:59:59"
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
async def cancel_optica_sale(sale_id: str, current_user: dict = Depends(require_permission("manage_optica_sales"))):
    """Cancelar una venta y restaurar stock"""
    sale = await db.optica_sales.find_one({"id": sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    if sale["status"] == "cancelado":
        raise HTTPException(status_code=400, detail="Esta venta ya está cancelada")
    
    if sale.get("frame_id"):
        await db.optica_frames.update_one({"id": sale["frame_id"]}, {"$inc": {"stock": 1}})
    
    if sale.get("contact_lens_id"):
        await db.optica_contact_lenses.update_one({"id": sale["contact_lens_id"]}, {"$inc": {"stock": 1}})
    
    await db.optica_sales.update_one(
        {"id": sale_id},
        {"$set": {"status": "cancelado", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Venta cancelada correctamente. Stock restaurado."}


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
            "total_cobrado": {"$sum": "$paid_amount"},
            "count": {"$sum": 1}
        }}
    ]
    
    month_result = await db.optica_sales.aggregate(pipeline_month).to_list(1)
    month_stats = month_result[0] if month_result else {"total_ventas": 0, "total_cobrado": 0, "count": 0}
    
    pipeline_pending = [
        {"$match": {"status": "pendiente"}},
        {"$group": {
            "_id": None,
            "saldo_pendiente": {"$sum": {"$subtract": ["$total", "$paid_amount"]}},
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
