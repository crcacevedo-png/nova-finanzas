# /app/backend/routes/expenses.py
# Módulo de Gastos y Pagos - CRUD completo

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
import uuid

from config.database import db
from pymongo import ReturnDocument
from routes.auth import get_current_user, require_permission

# ==================== ROUTERS ====================
router = APIRouter(prefix="/expenses", tags=["Gastos"])
payments_router = APIRouter(prefix="/payments", tags=["Pagos"])


# ==================== EXPENSE MODELS ====================

class ExpenseBase(BaseModel):
    provider: Optional[str] = None
    name: str = Field(..., min_length=1)
    type: str = Field(..., pattern="^(fijo|proveedor|variable|igss)$")
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
    expense_number: Optional[str] = None
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
    is_authorized: Optional[bool] = False
    authorized_bank_account_id: Optional[str] = None
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


# ==================== PAYMENT MODELS ====================

class PaymentBase(BaseModel):
    expense_id: str
    amount: float = Field(gt=0)
    date: str
    method: Literal["Efectivo", "Transferencia bancaria", "Tarjeta de crédito", "Tarjeta de débito", "Cheque"]
    reference: Optional[str] = None
    notes: Optional[str] = ""


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    expense_id: str
    expense_number: Optional[str] = None
    expense_name: Optional[str] = None
    expense_provider: Optional[str] = None
    amount: float
    date: str
    method: str
    reference: Optional[str] = None
    notes: Optional[str] = ""
    created_by: str
    created_by_name: Optional[str] = None
    created_at: str


class PaymentListResponse(BaseModel):
    data: List[PaymentResponse]
    total: int


# ==================== AUTHORIZATION MODEL ====================

class AuthorizeExpenseRequest(BaseModel):
    bank_account_id: str


# ==================== HELPERS ====================

async def get_next_expense_number() -> str:
    """Genera el siguiente número correlativo para gastos (GST-0001)"""
    result = await db.counters.find_one_and_update(
        {"_id": "expense_number"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    seq_num = result["seq"]
    return f"GST-{seq_num:04d}"


async def update_expense_amounts(expense_id: str):
    """Actualiza montos pagados, pendientes y estado basado en pagos"""
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
    """Verifica y actualiza gastos vencidos"""
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


# ==================== EXPENSE ROUTES ====================

@router.get("", response_model=ExpenseListResponse)
async def get_expenses(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    sort_by: Optional[str] = Query("date", alias="sortBy"),
    sort_order: Optional[str] = Query("desc", alias="sortOrder"),
    current_user: dict = Depends(require_permission("view_expenses"))
):
    """Listar gastos con filtros y paginación"""
    await check_overdue_expenses()
    
    query = {}
    
    # Filtro por tipo
    if type and type in ["fijo", "proveedor", "variable", "igss"]:
        query["type"] = type
    
    # Filtro por estado
    if status:
        if status == "no_pagado":
            query["status"] = {"$in": ["pendiente", "parcial", "vencido"]}
        elif status in ["pendiente", "parcial", "pagado", "vencido"]:
            query["status"] = status
    
    # Búsqueda por texto
    if search:
        query["$or"] = [
            {"provider": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
            {"invoice_number": {"$regex": search, "$options": "i"}},
            {"expense_number": {"$regex": search, "$options": "i"}}
        ]
    
    # Filtro por rango de fechas
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["date"] = date_query
    
    total = await db.expenses.count_documents(query)
    
    sort_direction = -1 if sort_order == "desc" else 1
    sort_field = sort_by if sort_by in ["date", "amount", "due_date", "name", "status"] else "date"
    
    skip = (page - 1) * limit
    expenses = await db.expenses.find(query, {"_id": 0}).sort(sort_field, sort_direction).skip(skip).limit(limit).to_list(limit)
    
    total_pages = (total + limit - 1) // limit
    
    return ExpenseListResponse(
        data=[ExpenseResponse(**e) for e in expenses],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(expense_id: str, current_user: dict = Depends(require_permission("view_expenses"))):
    """Obtener detalle de un gasto"""
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    # Obtener pagos asociados
    payments = await db.payments.find({"expense_id": expense_id}, {"_id": 0}).sort("date", -1).to_list(1000)
    expense["payments"] = payments
    
    return ExpenseResponse(**expense)


@router.post("", response_model=ExpenseResponse)
async def create_expense(expense_data: ExpenseCreate, current_user: dict = Depends(require_permission("create_expenses"))):
    """Crear nuevo gasto"""
    expense_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    expense_number = await get_next_expense_number()
    
    # Determinar estado inicial
    status = "pendiente"
    if expense_data.due_date:
        try:
            due_date = datetime.fromisoformat(expense_data.due_date).date()
            if due_date < datetime.now(timezone.utc).date():
                status = "vencido"
        except Exception:
            pass
    
    expense_doc = {
        "id": expense_id,
        "expense_number": expense_number,
        "provider": expense_data.provider,
        "name": expense_data.name,
        "type": expense_data.type,
        "amount": expense_data.amount,
        "date": expense_data.date,
        "due_date": expense_data.due_date,
        "invoice_number": expense_data.invoice_number,
        "status": status,
        "notes": expense_data.notes or "",
        "paid_amount": 0,
        "remaining_amount": expense_data.amount,
        "is_authorized": False,
        "authorized_bank_account_id": None,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.expenses.insert_one(expense_doc)
    
    return ExpenseResponse(**expense_doc)


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    expense_data: ExpenseUpdate,
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Actualizar gasto"""
    expense = await db.expenses.find_one({"id": expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    update_data = {k: v for k, v in expense_data.model_dump().items() if v is not None}
    
    # Si cambia el monto, recalcular pendiente
    if "amount" in update_data:
        update_data["remaining_amount"] = max(0, update_data["amount"] - expense.get("paid_amount", 0))
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    if update_data:
        await db.expenses.update_one({"id": expense_id}, {"$set": update_data})
    
    await update_expense_amounts(expense_id)
    
    updated = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    return ExpenseResponse(**updated)


@router.delete("/{expense_id}")
async def delete_expense(expense_id: str, current_user: dict = Depends(require_permission("delete_expenses"))):
    """Eliminar gasto y sus pagos asociados"""
    await db.payments.delete_many({"expense_id": expense_id})
    
    result = await db.expenses.delete_one({"id": expense_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return {"message": "Gasto eliminado"}


@router.put("/{expense_id}/toggle-authorization")
async def toggle_expense_authorization(expense_id: str, current_user: dict = Depends(require_permission("authorize_payments"))):
    """Toggle estado de autorización (Solo SuperAdmin)"""
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    if expense.get("remaining_amount", 0) <= 0:
        raise HTTPException(status_code=400, detail="Este gasto ya está completamente pagado")
    
    new_status = not expense.get("is_authorized", False)
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "is_authorized": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    updated = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    return ExpenseResponse(**updated)


@router.post("/{expense_id}/authorize")
async def authorize_expense_with_bank(
    expense_id: str, 
    auth_data: AuthorizeExpenseRequest,
    current_user: dict = Depends(require_permission("authorize_payments"))
):
    """Autorizar gasto con cuenta bancaria específica (Solo SuperAdmin)"""
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    remaining = expense.get("remaining_amount", expense.get("amount", 0))
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Este gasto ya está completamente pagado")
    
    bank_account = await db.bank_accounts.find_one({"id": auth_data.bank_account_id}, {"_id": 0})
    if not bank_account:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    
    existing_auth = await db.payment_authorizations.find_one({
        "expense_id": expense_id, 
        "status": "pendiente"
    }, {"_id": 0})
    
    if existing_auth:
        raise HTTPException(status_code=400, detail="Ya existe una autorización pendiente para este gasto")
    
    now = datetime.now(timezone.utc).isoformat()
    
    auth_doc = {
        "id": str(uuid.uuid4()),
        "expense_id": expense_id,
        "bank_account_id": auth_data.bank_account_id,
        "amount_to_pay": remaining,
        "status": "pendiente",
        "notes": "Autorizado desde módulo de Gastos",
        "authorized_by": current_user["id"],
        "authorized_at": now,
        "executed_by": None,
        "executed_at": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.payment_authorizations.insert_one(auth_doc)
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "is_authorized": True,
            "authorized_bank_account_id": auth_data.bank_account_id,
            "updated_at": now
        }}
    )
    
    updated = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    return ExpenseResponse(**updated)


@router.post("/confirm-authorizations")
async def confirm_expense_authorizations(current_user: dict = Depends(require_permission("authorize_payments"))):
    """Confirmar gastos autorizados y crear autorizaciones de pago"""
    authorized_expenses = await db.expenses.find(
        {"is_authorized": True, "remaining_amount": {"$gt": 0}},
        {"_id": 0}
    ).to_list(1000)
    
    if not authorized_expenses:
        raise HTTPException(status_code=400, detail="No hay gastos autorizados pendientes de confirmar")
    
    default_bank = await db.bank_accounts.find_one({"is_active": True}, {"_id": 0})
    
    created_count = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for expense in authorized_expenses:
        bank_id = expense.get("authorized_bank_account_id") or (default_bank["id"] if default_bank else None)
        
        if not bank_id:
            continue
        
        auth_doc = {
            "id": str(uuid.uuid4()),
            "expense_id": expense["id"],
            "bank_account_id": bank_id,
            "amount_to_pay": expense["remaining_amount"],
            "status": "pendiente",
            "notes": "Autorizado desde módulo de Gastos",
            "authorized_by": current_user["id"],
            "authorized_at": now,
            "executed_by": None,
            "executed_at": None,
            "created_at": now,
            "updated_at": now
        }
        
        await db.payment_authorizations.insert_one(auth_doc)
        
        await db.expenses.update_one(
            {"id": expense["id"]},
            {"$set": {
                "is_authorized": False, 
                "authorized_bank_account_id": None,
                "updated_at": now
            }}
        )
        
        created_count += 1
    
    return {
        "message": f"Se crearon {created_count} autorizaciones de pago",
        "count": created_count
    }


# ==================== PAYMENT ROUTES ====================

@payments_router.get("", response_model=PaymentListResponse)
async def get_payments(
    expense_id: Optional[str] = Query(None, alias="expenseId"),
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    method: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_payment_history"))
):
    """Listar pagos con filtros"""
    query = {}
    
    if expense_id:
        query["expense_id"] = expense_id
    
    if method:
        query["method"] = method
    
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["date"] = date_query
    
    payments_pipeline = [
        {"$match": query},
        {"$sort": {"date": -1}},
        {"$limit": 10000},
        {"$lookup": {
            "from": "expenses",
            "localField": "expense_id",
            "foreignField": "id",
            "as": "expense_data"
        }},
        {"$lookup": {
            "from": "users",
            "localField": "created_by",
            "foreignField": "id",
            "as": "user_data"
        }},
        {"$addFields": {
            "expense_name": {"$ifNull": [{"$arrayElemAt": ["$expense_data.name", 0]}, "N/A"]},
            "expense_provider": {"$ifNull": [{"$arrayElemAt": ["$expense_data.provider", 0]}, ""]},
            "expense_number": {"$ifNull": [{"$arrayElemAt": ["$expense_data.expense_number", 0]}, ""]},
            "created_by_name": {"$ifNull": [{"$arrayElemAt": ["$user_data.name", 0]}, "N/A"]}
        }},
        {"$project": {"expense_data": 0, "user_data": 0, "_id": 0}}
    ]
    
    payments = await db.payments.aggregate(payments_pipeline).to_list(10000)
    
    return PaymentListResponse(
        data=[PaymentResponse(**p) for p in payments],
        total=len(payments)
    )


@payments_router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str, current_user: dict = Depends(require_permission("view_payment_history"))):
    """Obtener detalle de un pago"""
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return PaymentResponse(**payment)


@router.get("/{expense_id}/payments", response_model=List[PaymentResponse])
async def get_expense_payments(
    expense_id: str,
    current_user: dict = Depends(require_permission("view_payment_history"))
):
    """Obtener pagos de un gasto específico"""
    expense = await db.expenses.find_one({"id": expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    payments = await db.payments.find({"expense_id": expense_id}, {"_id": 0}).sort("date", -1).to_list(1000)
    return [PaymentResponse(**p) for p in payments]


@payments_router.post("", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: dict = Depends(require_permission("register_payments"))
):
    """Registrar nuevo pago"""
    expense = await db.expenses.find_one({"id": payment_data.expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    if payment_data.amount > expense.get("remaining_amount", expense["amount"]):
        raise HTTPException(
            status_code=400,
            detail=f"El monto del pago (Q{payment_data.amount:.2f}) excede el monto pendiente (Q{expense.get('remaining_amount', expense['amount']):.2f})"
        )
    
    payment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    payment_doc = {
        "id": payment_id,
        "expense_id": payment_data.expense_id,
        "amount": payment_data.amount,
        "date": payment_data.date,
        "method": payment_data.method,
        "reference": payment_data.reference,
        "notes": payment_data.notes or "",
        "created_by": current_user["id"],
        "created_at": now
    }
    
    await db.payments.insert_one(payment_doc)
    
    await update_expense_amounts(payment_data.expense_id)
    
    return PaymentResponse(**payment_doc)


@payments_router.delete("/{payment_id}")
async def delete_payment(
    payment_id: str,
    current_user: dict = Depends(require_permission("delete_payments"))
):
    """Eliminar pago"""
    payment = await db.payments.find_one({"id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    expense_id = payment["expense_id"]
    
    result = await db.payments.delete_one({"id": payment_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    await update_expense_amounts(expense_id)
    
    return {"message": "Pago eliminado"}
