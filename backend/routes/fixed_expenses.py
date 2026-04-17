# /app/backend/routes/fixed_expenses.py
# Rutas de gestión de gastos fijos recurrentes

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
import uuid

from config.database import db

router = APIRouter(prefix="/fixed-expenses", tags=["Gastos Fijos"])

# ==================== MODELS ====================

class FixedExpenseBase(BaseModel):
    supplier_id: str
    expense_name: str
    amount: float = Field(gt=0)
    day_of_month: int = Field(ge=1, le=31)

class FixedExpenseCreate(FixedExpenseBase):
    pass

class FixedExpenseUpdate(BaseModel):
    supplier_id: Optional[str] = None
    expense_name: Optional[str] = None
    amount: Optional[float] = None
    day_of_month: Optional[int] = None
    is_active: Optional[bool] = None

class FixedExpenseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    supplier_id: str
    supplier_name: Optional[str] = ""
    expense_name: str
    amount: float
    day_of_month: int
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None
    last_generated: Optional[str] = None

class FixedExpenseListResponse(BaseModel):
    data: List[FixedExpenseResponse]
    total: int

# ==================== HELPER FUNCTIONS ====================

async def enrich_fixed_expense(fixed_expense: dict) -> dict:
    """Enriquecer gasto fijo con nombre del proveedor"""
    supplier = await db.suppliers.find_one({"id": fixed_expense["supplier_id"]}, {"_id": 0})
    if supplier:
        fixed_expense["supplier_name"] = supplier.get("name", "")
    else:
        fixed_expense["supplier_name"] = "Proveedor eliminado"
    return fixed_expense

# ==================== PERMISOS ====================
# - GET /fixed-expenses: Admin, SuperAdmin
# - GET /fixed-expenses/{id}: Admin, SuperAdmin
# - POST /fixed-expenses: Admin, SuperAdmin
# - PUT /fixed-expenses/{id}: Admin, SuperAdmin
# - DELETE /fixed-expenses/{id}: Admin, SuperAdmin
# - POST /fixed-expenses/generate-now: Solo SuperAdmin

# Nota: Las rutas se mantienen en server.py por compatibilidad
# Este archivo sirve como referencia para la migración gradual
