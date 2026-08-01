# /app/backend/routes/payment_authorizations.py
# Módulo de Autorizaciones de Pago

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
import uuid

from config.database import db
from routes.auth import get_current_user, require_permission
from routes.expenses import update_expense_amounts

router = APIRouter(prefix="/payment-authorizations", tags=["Autorizaciones de Pago"])


# ==================== MODELS ====================

class PaymentAuthorizationBase(BaseModel):
    expense_id: str
    bank_account_id: str
    amount_to_pay: float = Field(gt=0)
    notes: Optional[str] = ""

class PaymentAuthorizationCreate(PaymentAuthorizationBase):
    pass

class PaymentAuthorizationUpdate(BaseModel):
    bank_account_id: Optional[str] = None
    amount_to_pay: Optional[float] = None
    notes: Optional[str] = None

class PaymentAuthorizationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    expense_id: str
    expense_name: Optional[str] = ""
    expense_provider: Optional[str] = ""
    expense_amount: Optional[float] = 0
    expense_remaining: Optional[float] = 0
    expense_due_date: Optional[str] = ""
    expense_number: Optional[str] = ""
    bank_account_id: str
    bank_account_alias: Optional[str] = ""
    bank_name: Optional[str] = ""
    amount_to_pay: float
    status: str
    notes: Optional[str] = ""
    authorized_by: str
    authorized_by_name: Optional[str] = ""
    authorized_at: str
    executed_by: Optional[str] = None
    executed_by_name: Optional[str] = ""
    executed_at: Optional[str] = None
    created_at: str
    updated_at: str

class PaymentAuthorizationListResponse(BaseModel):
    data: List[PaymentAuthorizationResponse]
    total: int
    pending_count: int = 0
    executed_count: int = 0


# ==================== HELPERS ====================

async def enrich_authorization(auth: dict) -> dict:
    """Enrich authorization with expense, bank account, and user data"""
    # Obtener datos del gasto
    expense = await db.expenses.find_one({"id": auth["expense_id"]}, {"_id": 0})
    if expense:
        auth["expense_name"] = expense.get("name", "N/A")
        auth["expense_provider"] = expense.get("provider", "")
        auth["expense_amount"] = expense.get("amount", 0)
        auth["expense_remaining"] = expense.get("remaining_amount", expense.get("amount", 0))
        auth["expense_due_date"] = expense.get("due_date", "")
        auth["expense_number"] = expense.get("expense_number", "")
    
    # Obtener datos de la cuenta bancaria
    bank_account = await db.bank_accounts.find_one({"id": auth["bank_account_id"]}, {"_id": 0})
    if bank_account:
        auth["bank_account_alias"] = bank_account.get("account_alias", "N/A")
        auth["bank_name"] = bank_account.get("bank_name", "N/A")
    
    # Obtener nombre del autorizador
    authorizer = await db.users.find_one({"id": auth["authorized_by"]}, {"_id": 0, "name": 1})
    if authorizer:
        auth["authorized_by_name"] = authorizer.get("name", "N/A")
    
    # Obtener nombre del ejecutor si existe
    if auth.get("executed_by"):
        executor = await db.users.find_one({"id": auth["executed_by"]}, {"_id": 0, "name": 1})
        if executor:
            auth["executed_by_name"] = executor.get("name", "N/A")
    
    return auth


# ==================== ROUTES ====================

@router.get("", response_model=PaymentAuthorizationListResponse)
async def get_payment_authorizations(
    status: Optional[str] = Query(None, pattern="^(pendiente|ejecutado|cancelado)$"),
    current_user: dict = Depends(require_permission("view_payment_authorizations"))
):
    """Obtener todas las autorizaciones de pago"""
    query = {}
    if status:
        query["status"] = status
    
    authorizations = await db.payment_authorizations.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    enriched = []
    for auth in authorizations:
        enriched_auth = await enrich_authorization(auth)
        enriched.append(PaymentAuthorizationResponse(**enriched_auth))
    
    pending_count = await db.payment_authorizations.count_documents({"status": "pendiente"})
    executed_count = await db.payment_authorizations.count_documents({"status": "ejecutado"})
    
    return PaymentAuthorizationListResponse(
        data=enriched,
        total=len(enriched),
        pending_count=pending_count,
        executed_count=executed_count
    )


@router.get("/{auth_id}", response_model=PaymentAuthorizationResponse)
async def get_payment_authorization(
    auth_id: str,
    current_user: dict = Depends(require_permission("view_payment_authorizations"))
):
    """Obtener una autorización específica"""
    auth = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    if not auth:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    
    enriched = await enrich_authorization(auth)
    return PaymentAuthorizationResponse(**enriched)


@router.post("", response_model=PaymentAuthorizationResponse)
async def create_payment_authorization(
    auth_data: PaymentAuthorizationCreate,
    current_user: dict = Depends(require_permission("authorize_payments"))
):
    """Crear una nueva autorización de pago (SuperAdmin only)"""
    expense = await db.expenses.find_one({"id": auth_data.expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    remaining = expense.get("remaining_amount", expense["amount"])
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Este gasto ya está completamente pagado")
    
    if auth_data.amount_to_pay > remaining:
        raise HTTPException(
            status_code=400, 
            detail=f"El monto a autorizar (Q{auth_data.amount_to_pay:.2f}) excede el monto pendiente (Q{remaining:.2f})"
        )
    
    bank_account = await db.bank_accounts.find_one({"id": auth_data.bank_account_id}, {"_id": 0})
    if not bank_account:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    
    existing = await db.payment_authorizations.find_one({
        "expense_id": auth_data.expense_id,
        "status": "pendiente"
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una autorización pendiente para este gasto")
    
    now = datetime.now(timezone.utc).isoformat()
    auth_doc = {
        "id": str(uuid.uuid4()),
        "expense_id": auth_data.expense_id,
        "bank_account_id": auth_data.bank_account_id,
        "amount_to_pay": auth_data.amount_to_pay,
        "status": "pendiente",
        "notes": auth_data.notes or "",
        "authorized_by": current_user["id"],
        "authorized_at": now,
        "executed_by": None,
        "executed_at": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.payment_authorizations.insert_one(auth_doc)
    
    if "_id" in auth_doc:
        del auth_doc["_id"]
    
    enriched = await enrich_authorization(auth_doc)
    return PaymentAuthorizationResponse(**enriched)


@router.put("/{auth_id}", response_model=PaymentAuthorizationResponse)
async def update_payment_authorization(
    auth_id: str,
    auth_data: PaymentAuthorizationUpdate,
    current_user: dict = Depends(require_permission("authorize_payments"))
):
    """Actualizar una autorización de pago (SuperAdmin only)"""
    auth = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    if not auth:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    
    if auth["status"] != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se pueden editar autorizaciones pendientes")
    
    update_data = {k: v for k, v in auth_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    if "amount_to_pay" in update_data:
        expense = await db.expenses.find_one({"id": auth["expense_id"]}, {"_id": 0})
        if expense:
            remaining = expense.get("remaining_amount", expense["amount"])
            if update_data["amount_to_pay"] > remaining:
                raise HTTPException(
                    status_code=400,
                    detail=f"El monto a autorizar excede el monto pendiente (Q{remaining:.2f})"
                )
    
    if "bank_account_id" in update_data:
        bank_account = await db.bank_accounts.find_one({"id": update_data["bank_account_id"]}, {"_id": 0})
        if not bank_account:
            raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.payment_authorizations.update_one({"id": auth_id}, {"$set": update_data})
    updated = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    
    enriched = await enrich_authorization(updated)
    return PaymentAuthorizationResponse(**enriched)


@router.post("/{auth_id}/execute", response_model=PaymentAuthorizationResponse)
async def execute_payment_authorization(
    auth_id: str,
    payment_method: Optional[str] = Body(None),
    reference: Optional[str] = Body(None),
    notes: Optional[str] = Body(None),
    current_user: dict = Depends(require_permission("execute_payment_authorizations"))
):
    """Ejecutar una autorización de pago - crea el pago y actualiza el gasto (Admin only)"""
    auth = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    if not auth:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    
    if auth["status"] != "pendiente":
        raise HTTPException(status_code=400, detail="Esta autorización ya fue procesada")
    
    expense = await db.expenses.find_one({"id": auth["expense_id"]}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="El gasto asociado ya no existe")
    
    remaining = expense.get("remaining_amount", expense["amount"])
    
    if remaining <= 0:
        now = datetime.now(timezone.utc).isoformat()
        await db.payment_authorizations.update_one(
            {"id": auth_id},
            {"$set": {
                "status": "cancelado",
                "notes": f"{auth.get('notes', '')} [Auto-cancelado: gasto ya pagado completamente]".strip(),
                "updated_at": now
            }}
        )
        raise HTTPException(
            status_code=400, 
            detail="El gasto ya fue pagado completamente. La autorización ha sido cancelada automáticamente."
        )
    
    amount_to_pay = min(auth["amount_to_pay"], remaining)
    amount_adjusted = amount_to_pay < auth["amount_to_pay"]
    
    bank_account = await db.bank_accounts.find_one({"id": auth["bank_account_id"]}, {"_id": 0})
    bank_ref = f"{bank_account['bank_name']} - {bank_account['account_alias']}" if bank_account else "N/A"
    
    now = datetime.now(timezone.utc).isoformat()
    
    payment_method_labels = {
        "transferencia": "Transferencia bancaria",
        "efectivo": "Efectivo",
        "cheque": "Cheque",
        "tarjeta": "Tarjeta de crédito/débito",
        "otro": "Otro"
    }
    
    method_label = payment_method_labels.get(payment_method, "Transferencia bancaria")
    payment_reference = reference if reference else f"Auth: {auth_id[:8]} | Cuenta: {bank_ref}"
    
    adjustment_note = f" [Ajustado de Q{auth['amount_to_pay']:.2f} a Q{amount_to_pay:.2f}]" if amount_adjusted else ""
    user_notes = notes if notes else ""
    combined_notes = f"Pago autorizado.{adjustment_note} {user_notes}".strip()
    
    payment_doc = {
        "id": str(uuid.uuid4()),
        "expense_id": auth["expense_id"],
        "amount": amount_to_pay,
        "date": now.split("T")[0],
        "method": method_label,
        "reference": payment_reference,
        "notes": combined_notes,
        "created_by": current_user["id"],
        "created_at": now
    }
    
    await db.payments.insert_one(payment_doc)
    
    await update_expense_amounts(auth["expense_id"])
    
    auth_update = {
        "status": "ejecutado",
        "executed_by": current_user["id"],
        "executed_at": now,
        "updated_at": now
    }
    
    if amount_adjusted:
        auth_update["notes"] = f"{auth.get('notes', '')} [Ejecutado con monto ajustado: Q{amount_to_pay:.2f} de Q{auth['amount_to_pay']:.2f}]".strip()
    
    await db.payment_authorizations.update_one({"id": auth_id}, {"$set": auth_update})
    
    updated = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    enriched = await enrich_authorization(updated)
    return PaymentAuthorizationResponse(**enriched)


@router.post("/{auth_id}/cancel", response_model=PaymentAuthorizationResponse)
async def cancel_payment_authorization(
    auth_id: str,
    current_user: dict = Depends(require_permission("authorize_payments"))
):
    """Cancelar una autorización de pago (SuperAdmin only)"""
    auth = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    if not auth:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    
    if auth["status"] != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se pueden cancelar autorizaciones pendientes")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.payment_authorizations.update_one(
        {"id": auth_id},
        {"$set": {"status": "cancelado", "updated_at": now}}
    )
    
    updated = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    enriched = await enrich_authorization(updated)
    return PaymentAuthorizationResponse(**enriched)


@router.delete("/{auth_id}")
async def delete_payment_authorization(
    auth_id: str,
    current_user: dict = Depends(require_permission("authorize_payments"))
):
    """Eliminar una autorización de pago (SuperAdmin only)"""
    auth = await db.payment_authorizations.find_one({"id": auth_id})
    if not auth:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    
    if auth["status"] == "ejecutado":
        raise HTTPException(status_code=400, detail="No se pueden eliminar autorizaciones ejecutadas")
    
    await db.payment_authorizations.delete_one({"id": auth_id})
    return {"message": "Autorización eliminada correctamente"}


# ==================== EXPENSES PENDING AUTHORIZATION ====================

@router.get("/expenses/pending")
async def get_expenses_pending_authorization(
    current_user: dict = Depends(require_permission("authorize_payments"))
):
    """Obtener gastos pendientes que pueden ser autorizados para pago"""
    expenses = await db.expenses.find(
        {
            "status": {"$in": ["pendiente", "parcial", "vencido"]},
            "remaining_amount": {"$gt": 0}
        },
        {"_id": 0}
    ).sort("due_date", 1).to_list(10000)
    
    existing_auths = await db.payment_authorizations.find(
        {"status": "pendiente"},
        {"_id": 0, "expense_id": 1}
    ).to_list(10000)
    authorized_expense_ids = {a["expense_id"] for a in existing_auths}
    
    available_expenses = [
        e for e in expenses if e["id"] not in authorized_expense_ids
    ]
    
    return {"data": available_expenses, "total": len(available_expenses)}
