# /app/backend/models/supplier.py
# Modelos de Proveedores y Gastos Fijos

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


# Modelos de Proveedor
class SupplierBase(BaseModel):
    name: str
    contact_name: Optional[str] = ""
    phone: Optional[str] = ""


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None


class SupplierResponse(SupplierBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_active: bool
    created_at: str
    updated_at: str


class SupplierListResponse(BaseModel):
    data: List[SupplierResponse]
    total: int


# Modelos de Gastos Fijos
class FixedExpenseBase(BaseModel):
    supplier_id: str
    expense_name: str
    description: Optional[str] = ""
    amount: float
    category: str = "servicios"
    day_of_month: int
    is_active: bool = True


class FixedExpenseCreate(FixedExpenseBase):
    pass


class FixedExpenseUpdate(BaseModel):
    supplier_id: Optional[str] = None
    expense_name: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    day_of_month: Optional[int] = None
    is_active: Optional[bool] = None


class FixedExpenseResponse(FixedExpenseBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    supplier_name: Optional[str] = None
    created_at: str
    updated_at: str


class FixedExpenseListResponse(BaseModel):
    data: List[FixedExpenseResponse]
    total: int
