# /app/backend/models/expense.py
# Modelos de Gastos y Pagos

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class ExpenseBase(BaseModel):
    supplier_id: Optional[str] = None
    description: str
    amount: float
    due_date: str
    category: str = "general"
    notes: Optional[str] = ""
    requires_authorization: bool = False


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    supplier_id: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    expense_number: Optional[str] = None  # Número correlativo automático (ej: GST-0001)
    status: str
    paid_amount: float
    remaining_amount: float
    created_by: str
    created_at: str
    updated_at: str
    supplier_name: Optional[str] = None


class ExpenseListResponse(BaseModel):
    data: List[ExpenseResponse]
    total: int


# Modelos de Pago
class PaymentCreate(BaseModel):
    expense_id: str
    amount: float
    payment_method: str = Field(pattern="^(efectivo|cheque|transferencia|tarjeta|deposito)$")
    bank_account_id: Optional[str] = None
    reference: Optional[str] = ""
    notes: Optional[str] = ""


class PaymentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    expense_id: str
    amount: float
    payment_method: str
    bank_account_id: Optional[str] = None
    reference: Optional[str] = ""
    notes: Optional[str] = ""
    created_by: str
    created_at: str
    expense_description: Optional[str] = None
    supplier_name: Optional[str] = None


class PaymentListResponse(BaseModel):
    data: List[PaymentResponse]
    total: int


# Modelos de Cuenta Bancaria
class BankAccountBase(BaseModel):
    bank_name: str
    account_number: str
    account_type: str = Field(pattern="^(monetaria|ahorro)$")
    current_balance: float = 0


class BankAccountCreate(BankAccountBase):
    pass


class BankAccountUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    current_balance: Optional[float] = None


class BankAccountResponse(BankAccountBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_active: bool
    created_at: str
    updated_at: str


class BankAccountListResponse(BaseModel):
    data: List[BankAccountResponse]
    total: int


# Modelos de Autorización de Pagos
class PaymentAuthorizationBase(BaseModel):
    expense_id: str
    amount: float
    notes: Optional[str] = ""


class PaymentAuthorizationCreate(PaymentAuthorizationBase):
    pass


class PaymentAuthorizationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    expense_id: str
    amount: float
    status: str
    notes: Optional[str] = ""
    requested_by: str
    requested_by_name: Optional[str] = None
    authorized_by: Optional[str] = None
    authorized_by_name: Optional[str] = None
    executed_by: Optional[str] = None
    executed_by_name: Optional[str] = None
    rejected_reason: Optional[str] = None
    created_at: str
    updated_at: str
    authorized_at: Optional[str] = None
    executed_at: Optional[str] = None
    expense_description: Optional[str] = None
    supplier_name: Optional[str] = None


class PaymentAuthorizationListResponse(BaseModel):
    data: List[PaymentAuthorizationResponse]
    total: int


class AuthorizationAction(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    reason: Optional[str] = None


class ExecuteAuthorization(BaseModel):
    payment_method: str = Field(pattern="^(efectivo|cheque|transferencia|tarjeta|deposito)$")
    bank_account_id: Optional[str] = None
    reference: Optional[str] = ""
