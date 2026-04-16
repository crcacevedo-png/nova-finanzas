# /app/backend/routes/expenses.py
# Rutas de gestión de gastos

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
import uuid

from config.database import db
from config.permissions import get_permissions
from pymongo import ReturnDocument

router = APIRouter(prefix="/expenses", tags=["Gastos"])

# Importar helpers de autenticación (se configurará después)
# Por ahora, estas funciones se importarán desde el módulo principal

# ==================== MODELS ====================

class ExpenseBase(BaseModel):
    provider: Optional[str] = None
    name: str = Field(..., min_length=1)
    type: str = Field(..., pattern="^(fijo|proveedor|variable)$")
    amount: float = Field(..., gt=0)
    date: str
    due_date: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = ""

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    provider: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[str] = None
    due_date: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class ExpenseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    expense_number: Optional[str] = None  # Número correlativo automático (ej: GST-0001)
    provider: Optional[str] = None
    name: str
    type: str
    amount: float
    date: str
    due_date: Optional[str] = None
    invoice_number: Optional[str] = None
    status: str
    notes: Optional[str] = ""
    paid_amount: float = 0
    remaining_amount: float = 0
    created_by: str
    created_at: str
    updated_at: Optional[str] = None
    payments: Optional[List] = None

class ExpenseListResponse(BaseModel):
    data: List[ExpenseResponse]
    total: int
    page: int
    limit: int
    total_pages: int

# ==================== HELPERS ====================

async def get_next_expense_number() -> str:
    """
    Genera el siguiente número correlativo para gastos.
    Usa una colección 'counters' con find_one_and_update para operaciones atómicas.
    Formato: GST-0001, GST-0002, etc.
    """
    result = await db.counters.find_one_and_update(
        {"_id": "expense_number"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    seq_num = result["seq"]
    return f"GST-{seq_num:04d}"

async def update_expense_amounts(expense_id: str):
    """Update paidAmount, remainingAmount, and status based on payments"""
    payments = await db.payments.find({"expense_id": expense_id}, {"_id": 0}).to_list(10000)
    paid_amount = sum(p["amount"] for p in payments)
    
    expense = await db.expenses.find_one({"id": expense_id})
    if not expense:
        return
    
    remaining_amount = max(0, expense["amount"] - paid_amount)
    
    if paid_amount >= expense["amount"]:
        status = "pagado"
    elif expense.get("due_date"):
        try:
            due_date = datetime.fromisoformat(expense["due_date"]).date()
            today = datetime.now(timezone.utc).date()
            if due_date < today and paid_amount < expense["amount"]:
                status = "vencido"
            elif paid_amount > 0:
                status = "parcial"
            else:
                status = "pendiente"
        except Exception:
            status = "parcial" if paid_amount > 0 else "pendiente"
    else:
        status = "parcial" if paid_amount > 0 else "pendiente"
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "paid_amount": paid_amount,
            "remaining_amount": remaining_amount,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

async def check_overdue_expenses():
    """Check and update status for overdue expenses"""
    today = datetime.now(timezone.utc).date()
    expenses = await db.expenses.find(
        {"status": {"$in": ["pendiente", "parcial"]}, "due_date": {"$ne": None}},
        {"_id": 0, "id": 1, "due_date": 1, "status": 1}
    ).to_list(10000)
    
    for expense in expenses:
        try:
            due_date = datetime.fromisoformat(expense["due_date"]).date()
            if due_date < today and expense["status"] not in ["pagado", "vencido"]:
                await db.expenses.update_one(
                    {"id": expense["id"]},
                    {"$set": {"status": "vencido", "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
        except Exception:
            pass

# Nota: Las rutas se definirán usando las funciones de autenticación del módulo principal
# Este archivo sirve como referencia para la refactorización gradual
