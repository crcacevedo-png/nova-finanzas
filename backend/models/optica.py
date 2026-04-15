# /app/backend/models/optica.py
# Modelos del Módulo Óptica

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


# Modelos de Doctor
class DoctorBase(BaseModel):
    name: str
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
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


class DoctorResponse(DoctorBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_active: bool = True
    created_at: str
    updated_at: str


class DoctorListResponse(BaseModel):
    data: List[DoctorResponse]
    total: int


# Modelos de Aros (Frames)
class FrameBase(BaseModel):
    brand: str
    model: Optional[str] = None
    code: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    cost_price: float = 0
    sell_price: float
    stock: int = 0
    min_stock: int = 2


class FrameCreate(FrameBase):
    pass


class FrameUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    code: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    cost_price: Optional[float] = None
    sell_price: Optional[float] = None
    stock: Optional[int] = None
    min_stock: Optional[int] = None


class FrameResponse(FrameBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_active: bool = True
    created_at: str
    updated_at: str


class FrameListResponse(BaseModel):
    data: List[FrameResponse]
    total: int
    total_stock: int = 0
    low_stock_count: int = 0
    total_value: float = 0


# Modelos de Lentes de Contacto
class ContactLensBase(BaseModel):
    brand: str
    type: str
    power_range: Optional[str] = None
    base_curve: Optional[str] = None
    diameter: Optional[str] = None
    cost_price: float = 0
    sell_price: float
    stock: int = 0
    min_stock: int = 5


class ContactLensCreate(ContactLensBase):
    pass


class ContactLensUpdate(BaseModel):
    brand: Optional[str] = None
    type: Optional[str] = None
    power_range: Optional[str] = None
    base_curve: Optional[str] = None
    diameter: Optional[str] = None
    cost_price: Optional[float] = None
    sell_price: Optional[float] = None
    stock: Optional[int] = None
    min_stock: Optional[int] = None


class ContactLensResponse(ContactLensBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_active: bool = True
    created_at: str
    updated_at: str


class ContactLensListResponse(BaseModel):
    data: List[ContactLensResponse]
    total: int


# Modelos de Tipos de Lente
class LensTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    cost_price: Optional[float] = None
    default_price: float


class LensTypeCreate(LensTypeBase):
    pass


class LensTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cost_price: Optional[float] = None
    default_price: Optional[float] = None


class LensTypeResponse(LensTypeBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_active: bool = True
    created_at: str
    updated_at: str


class LensTypeListResponse(BaseModel):
    data: List[LensTypeResponse]
    total: int


# Modelos de Venta de Óptica
class LensItem(BaseModel):
    lens_type_id: str
    name: str
    quantity: int = 1
    unit_price: float
    total: float


class OpticaSaleBase(BaseModel):
    patient_id: str
    doctor_id: Optional[str] = None
    frame_id: Optional[str] = None
    frame_price: float = 0
    contact_lens_id: Optional[str] = None
    contact_lens_price: float = 0
    lens_items: List[LensItem] = []
    subtotal: float
    discount_percent: float = 0
    total: float
    initial_payment: float = 0
    payment_method: str = "efectivo"
    notes: Optional[str] = ""


class OpticaSaleCreate(OpticaSaleBase):
    pass


class OpticaSalePayment(BaseModel):
    amount: float
    payment_method: str = "efectivo"
    reference: Optional[str] = ""
    notes: Optional[str] = ""


class OpticaSaleResponse(OpticaSaleBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    frame_info: Optional[str] = None
    paid_amount: float = 0
    status: str = "pendiente"
    payments: List[dict] = []
    created_by: Optional[str] = None
    created_at: str
    updated_at: str


class OpticaSaleListResponse(BaseModel):
    data: List[OpticaSaleResponse]
    total: int


# Modelos de Compras de Óptica
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


class OpticaPurchaseResponse(OpticaPurchaseBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    supplier_name: Optional[str] = None
    created_at: str
    updated_at: str


class OpticaPurchaseListResponse(BaseModel):
    data: List[OpticaPurchaseResponse]
    total: int
