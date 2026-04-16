# /app/backend/routes/dashboard.py
# Rutas del Dashboard principal

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from config.database import db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# ==================== MODELS ====================

class TypeBreakdown(BaseModel):
    type: str
    total: float
    percentage: float

class DashboardSummary(BaseModel):
    total_month: float
    total_paid: float
    total_pending: float
    overdue_count: int
    by_type: List[TypeBreakdown]

class MonthlyChartItem(BaseModel):
    month: str
    year: int
    total: float

class AlertResponse(BaseModel):
    id: str
    name: str
    provider: Optional[str] = ""
    amount: float
    remaining_amount: float
    due_date: str
    days_remaining: int
    type: str
    status: str
    invoice_number: Optional[str] = ""

class UpcomingPayments(BaseModel):
    overdue: List[AlertResponse]
    due30: List[AlertResponse]
    due60: List[AlertResponse]

# ==================== HELPER FUNCTIONS ====================

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

# Nota: Las rutas se mantienen en server.py por compatibilidad
# Este archivo sirve como referencia para la migración gradual
