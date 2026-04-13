from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import io
import json
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'novavision_secret_key_2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8

# Blacklisted tokens (for logout)
blacklisted_tokens = set()

# Create the main app
app = FastAPI(title="NovaVision - Sistema de Gastos y Finanzas")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# ==================== PERMISSIONS SYSTEM ====================

PERMISSIONS = {
    "superadmin": {
        "view_dashboard": True,
        "view_expenses": True,
        "view_payment_history": True,
        "view_due_payments": True,
        "create_expenses": True,
        "edit_expenses": True,
        "delete_expenses": True,
        "register_payments": True,
        "delete_payments": True,
        "manage_users": True,
        "view_user_management": True,
        "export_reports": True,
        "authorize_payments": True,
        "view_payment_authorizations": True,
        # Permisos de Pacientes
        "view_patients": True,
        "create_patients": True,
        "edit_patients": True,
        "delete_patients": True,
        "manage_igss_units": True,
        "import_patients": True,
        "export_patients": True
    },
    "admin": {
        "view_dashboard": True,
        "view_expenses": True,
        "view_payment_history": True,
        "view_due_payments": True,
        "create_expenses": True,
        "edit_expenses": True,
        "delete_expenses": False,
        "register_payments": True,
        "delete_payments": False,
        "manage_users": False,
        "view_user_management": False,
        "export_reports": True,
        "authorize_payments": False,
        "view_payment_authorizations": True,
        "execute_payment_authorizations": True,
        # Permisos de Pacientes
        "view_patients": True,
        "create_patients": True,
        "edit_patients": True,
        "delete_patients": False,
        "manage_igss_units": False,
        "import_patients": True,
        "export_patients": True
    },
    "usuario": {
        "view_dashboard": True,
        "view_expenses": True,
        "view_payment_history": True,
        "view_due_payments": True,
        "create_expenses": False,
        "edit_expenses": False,
        "delete_expenses": False,
        "register_payments": False,
        "delete_payments": False,
        "manage_users": False,
        "view_user_management": False,
        "export_reports": False,
        "authorize_payments": False,
        "view_payment_authorizations": False,
        "execute_payment_authorizations": False,
        # Permisos de Pacientes (solo lectura)
        "view_patients": True,
        "create_patients": False,
        "edit_patients": False,
        "delete_patients": False,
        "manage_igss_units": False,
        "import_patients": False,
        "export_patients": False
    }
}

def get_permissions(role: str) -> dict:
    return PERMISSIONS.get(role, PERMISSIONS["usuario"])

# ==================== MODELS ====================

# User Models
class UserBase(BaseModel):
    username: str
    name: str
    role: str = Field(default="usuario", pattern="^(superadmin|admin|usuario)$")

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    username: str
    name: str
    role: str
    is_active: bool = True
    last_login: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    permissions: dict = {}

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_in: int = JWT_EXPIRATION_HOURS * 3600

# Expense Models
class ExpenseBase(BaseModel):
    provider: Optional[str] = None
    name: str
    type: Literal["fijo", "proveedor", "variable", "igss"]
    amount: float = Field(ge=0)
    date: str
    due_date: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = ""

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    provider: Optional[str] = None
    name: Optional[str] = None
    type: Optional[Literal["fijo", "proveedor", "variable", "igss"]] = None
    amount: Optional[float] = None
    date: Optional[str] = None
    due_date: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None

class ExpenseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
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

# Bank Account Models
class BankAccountBase(BaseModel):
    bank_name: str
    account_number: str
    account_alias: str

class BankAccountCreate(BankAccountBase):
    pass

class BankAccountUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_alias: Optional[str] = None

class BankAccountResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    bank_name: str
    account_number: str
    account_alias: str
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class BankAccountListResponse(BaseModel):
    data: List[BankAccountResponse]
    total: int

# Payment Models
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

# ==================== PAYMENT AUTHORIZATION MODELS ====================

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
    expense_name: Optional[str] = None
    expense_provider: Optional[str] = None
    expense_amount: Optional[float] = None
    expense_remaining: Optional[float] = None
    expense_due_date: Optional[str] = None
    bank_account_id: str
    bank_account_alias: Optional[str] = None
    bank_name: Optional[str] = None
    amount_to_pay: float
    status: str  # pendiente, ejecutado, cancelado
    notes: Optional[str] = ""
    authorized_by: str
    authorized_by_name: Optional[str] = None
    authorized_at: str
    executed_by: Optional[str] = None
    executed_by_name: Optional[str] = None
    executed_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

class PaymentAuthorizationListResponse(BaseModel):
    data: List[PaymentAuthorizationResponse]
    total: int
    pending_count: int
    executed_count: int

# ==================== SUPPLIER/PROVIDER MODELS ====================

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

class SupplierResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    contact_name: Optional[str] = ""
    phone: Optional[str] = ""
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class SupplierListResponse(BaseModel):
    data: List[SupplierResponse]
    total: int

# ==================== FIXED EXPENSE MODELS ====================

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

# ==================== IGSS UNIT MODELS (Catálogo de Unidades IGSS) ====================

class IGSSUnitBase(BaseModel):
    name: str
    code: Optional[str] = ""
    description: Optional[str] = ""

class IGSSUnitCreate(IGSSUnitBase):
    pass

class IGSSUnitUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None

class IGSSUnitResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    code: Optional[str] = ""
    description: Optional[str] = ""
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class IGSSUnitListResponse(BaseModel):
    data: List[IGSSUnitResponse]
    total: int

# ==================== PATIENT MODELS ====================

class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    gender: Literal["masculino", "femenino", "otro"]
    birth_date: str  # YYYY-MM-DD
    profession: Optional[str] = ""
    phone: str = Field(..., min_length=8, max_length=20)
    email: Optional[str] = ""
    dpi: Optional[str] = Field(None, min_length=13, max_length=13)
    emergency_phone: Optional[str] = ""
    emergency_contact_name: Optional[str] = ""
    emergency_contact_relationship: Optional[str] = ""
    referral_institution: Literal["particular", "igss", "seguro_privado", "otra"]
    insurance_name: Optional[str] = ""  # Solo si seguro_privado
    other_institution_name: Optional[str] = ""  # Solo si otra
    igss_unit_id: Optional[str] = None  # Solo si igss
    comments: Optional[str] = ""

class PatientCreate(PatientBase):
    pass

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[Literal["masculino", "femenino", "otro"]] = None
    birth_date: Optional[str] = None
    profession: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    dpi: Optional[str] = None
    emergency_phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    referral_institution: Optional[Literal["particular", "igss", "seguro_privado", "otra"]] = None
    insurance_name: Optional[str] = None
    other_institution_name: Optional[str] = None
    igss_unit_id: Optional[str] = None
    comments: Optional[str] = None
    is_active: Optional[bool] = None

class PatientResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    record_number: str  # Número de expediente correlativo
    first_name: str
    last_name: str
    full_name: Optional[str] = ""
    gender: str
    birth_date: str
    age: int  # Calculado dinámicamente
    profession: Optional[str] = ""
    phone: str
    email: Optional[str] = ""
    dpi: Optional[str] = ""
    emergency_phone: Optional[str] = ""
    emergency_contact_name: Optional[str] = ""
    emergency_contact_relationship: Optional[str] = ""
    referral_institution: str
    referral_institution_label: Optional[str] = ""
    insurance_name: Optional[str] = ""
    other_institution_name: Optional[str] = ""
    igss_unit_id: Optional[str] = ""
    igss_unit_name: Optional[str] = ""
    comments: Optional[str] = ""
    is_active: bool = True
    created_by: str
    created_by_name: Optional[str] = ""
    created_at: str
    updated_by: Optional[str] = ""
    updated_by_name: Optional[str] = ""
    updated_at: Optional[str] = None

class PatientListResponse(BaseModel):
    data: List[PatientResponse]
    total: int
    page: int
    limit: int
    total_pages: int

class PatientSearchResponse(BaseModel):
    """Respuesta para autocompletado en otros módulos"""
    id: str
    record_number: str
    full_name: str
    dpi: Optional[str] = ""
    phone: str

class PatientDuplicateCheck(BaseModel):
    exists: bool
    match_type: Optional[str] = None  # "dpi" o "name_birthdate"
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    patient_record_number: Optional[str] = None

# Dashboard Models
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

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, username: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        
        # Check if token is blacklisted
        if token in blacklisted_tokens:
            raise HTTPException(status_code=401, detail="Token ha sido invalidado")
        
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
        user["permissions"] = get_permissions(user["role"])
        user["_token"] = token  # Store token for logout
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

def require_permission(permission: str):
    async def permission_checker(current_user: dict = Depends(get_current_user)):
        user_permissions = get_permissions(current_user["role"])
        if not user_permissions.get(permission, False):
            raise HTTPException(status_code=403, detail="No tienes permiso para realizar esta acción")
        return current_user
    return permission_checker

# ==================== EXPENSE HELPERS ====================

async def update_expense_amounts(expense_id: str):
    """Update paidAmount, remainingAmount, and status based on payments"""
    payments = await db.payments.find({"expense_id": expense_id}, {"_id": 0}).to_list(10000)
    paid_amount = sum(p["amount"] for p in payments)
    
    expense = await db.expenses.find_one({"id": expense_id})
    if not expense:
        return
    
    remaining_amount = max(0, expense["amount"] - paid_amount)
    
    # Determine status according to business rules:
    # SI paidAmount >= amount → status = "pagado"
    # SI paidAmount > 0 Y paidAmount < amount → status = "parcial"
    # SI dueDate existe Y dueDate < hoy Y paidAmount < amount → status = "vencido"
    # SI paidAmount == 0 Y (no hay dueDate O dueDate >= hoy) → status = "pendiente"
    
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

# ==================== SEED USERS ====================

async def seed_default_users():
    """Create default users if they don't exist"""
    default_users = [
        {"username": "superadmin", "name": "Administrador General", "password": "nova2024", "role": "superadmin"},
        {"username": "admin", "name": "Administrador", "password": "admin2024", "role": "admin"},
        {"username": "usuario", "name": "Usuario NovaVision", "password": "user2024", "role": "usuario"}
    ]
    
    for user_data in default_users:
        existing = await db.users.find_one({"username": user_data["username"]})
        if not existing:
            user_doc = {
                "id": str(uuid.uuid4()),
                "username": user_data["username"],
                "name": user_data["name"],
                "password": hash_password(user_data["password"]),
                "role": user_data["role"],
                "is_active": True,
                "last_login": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user_doc)
            print(f"Created default user: {user_data['username']}")


async def seed_sample_expenses():
    """Create sample expenses for demo if none exist"""
    # Check if there are already expenses
    count = await db.expenses.count_documents({})
    if count > 0:
        print(f"Expenses already exist ({count}), skipping sample data")
        return
    
    # Get superadmin user for created_by field
    superadmin = await db.users.find_one({"username": "superadmin"})
    if not superadmin:
        print("Superadmin not found, skipping sample expenses")
        return
    
    created_by = superadmin["id"]
    
    sample_expenses = [
        {
            "name": "Alquiler de local",
            "type": "fijo",
            "amount": 12000.00,
            "date": "2024-03-01",
            "due_date": "2024-03-31",
            "invoice_number": "FAC-0001",
            "status": "pagado",
            "notes": "Local principal Zona 10",
            "paid_amount": 12000.00,
            "remaining_amount": 0.00
        },
        {
            "name": "Lentes oftálmicos — Proveedor Óptica GT",
            "type": "proveedor",
            "amount": 8500.00,
            "date": "2024-03-05",
            "due_date": "2024-04-05",
            "invoice_number": "FAC-0045",
            "status": "parcial",
            "notes": "Pedido mensual de lentes",
            "paid_amount": 4000.00,
            "remaining_amount": 4500.00
        },
        {
            "name": "Mantenimiento equipo láser",
            "type": "variable",
            "amount": 3200.00,
            "date": "2024-03-10",
            "due_date": "2024-04-10",
            "invoice_number": None,
            "status": "pendiente",
            "notes": "Mantenimiento preventivo trimestral",
            "paid_amount": 0.00,
            "remaining_amount": 3200.00
        },
        {
            "name": "Servicios básicos (agua, luz, internet)",
            "type": "fijo",
            "amount": 4500.00,
            "date": "2024-03-01",
            "due_date": "2024-03-15",
            "invoice_number": "SRV-0312",
            "status": "vencido",
            "notes": "",
            "paid_amount": 0.00,
            "remaining_amount": 4500.00
        },
        {
            "name": "Insumos médicos descartables",
            "type": "proveedor",
            "amount": 6000.00,
            "date": "2024-03-12",
            "due_date": "2024-05-12",
            "invoice_number": "FAC-1122",
            "status": "pendiente",
            "notes": "Guantes, gasas, soluciones",
            "paid_amount": 0.00,
            "remaining_amount": 6000.00
        }
    ]
    
    for expense_data in sample_expenses:
        expense_doc = {
            "id": str(uuid.uuid4()),
            "name": expense_data["name"],
            "type": expense_data["type"],
            "amount": expense_data["amount"],
            "date": expense_data["date"],
            "due_date": expense_data["due_date"],
            "invoice_number": expense_data["invoice_number"],
            "status": expense_data["status"],
            "notes": expense_data["notes"],
            "paid_amount": expense_data["paid_amount"],
            "remaining_amount": expense_data["remaining_amount"],
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.expenses.insert_one(expense_doc)
        print(f"Created sample expense: {expense_data['name']}")
    
    # Create sample payment for the "pagado" expense
    alquiler = await db.expenses.find_one({"name": "Alquiler de local"})
    if alquiler:
        payment_doc = {
            "id": str(uuid.uuid4()),
            "expense_id": alquiler["id"],
            "amount": 12000.00,
            "date": "2024-03-15",
            "method": "Transferencia bancaria",
            "reference": "TRANS-001234",
            "notes": "Pago completo del alquiler",
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.payments.insert_one(payment_doc)
        print("Created sample payment for Alquiler")
    
    # Create sample partial payment for "Lentes oftálmicos"
    lentes = await db.expenses.find_one({"name": "Lentes oftálmicos — Proveedor Óptica GT"})
    if lentes:
        payment_doc = {
            "id": str(uuid.uuid4()),
            "expense_id": lentes["id"],
            "amount": 4000.00,
            "date": "2024-03-20",
            "method": "Cheque",
            "reference": "CHQ-5678",
            "notes": "Primer abono",
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.payments.insert_one(payment_doc)
        print("Created sample payment for Lentes oftálmicos")


async def seed_sample_patients():
    """Create sample patients for demo if none exist"""
    count = await db.patients.count_documents({})
    if count > 0:
        print(f"Patients already exist ({count}), skipping sample data")
        return
    
    superadmin = await db.users.find_one({"username": "superadmin"})
    if not superadmin:
        print("Superadmin not found, skipping sample patients")
        return
    
    created_by = superadmin["id"]
    now = datetime.now(timezone.utc).isoformat()
    
    sample_patients = [
        {
            "first_name": "María",
            "last_name": "García López",
            "gender": "femenino",
            "birth_date": "1985-06-15",
            "profession": "Contadora",
            "phone": "55512345",
            "email": "maria.garcia@email.com",
            "dpi": "1234567890123",
            "referral_institution": "particular",
        },
        {
            "first_name": "Juan",
            "last_name": "Pérez Morales",
            "gender": "masculino",
            "birth_date": "1978-03-22",
            "profession": "Ingeniero Civil",
            "phone": "55567890",
            "email": "juan.perez@email.com",
            "dpi": "2345678901234",
            "referral_institution": "igss",
            "emergency_contact_name": "Ana Pérez",
            "emergency_contact_relationship": "Esposa",
            "emergency_phone": "55511111"
        },
        {
            "first_name": "Ana",
            "last_name": "Rodríguez Castillo",
            "gender": "femenino",
            "birth_date": "1990-11-08",
            "profession": "Médico",
            "phone": "55598765",
            "email": "ana.rodriguez@hospital.gt",
            "dpi": "3456789012345",
            "referral_institution": "seguro_privado",
            "insurance_name": "Seguros G&T"
        },
        {
            "first_name": "Carlos",
            "last_name": "Mendoza Flores",
            "gender": "masculino",
            "birth_date": "1965-01-30",
            "profession": "Comerciante",
            "phone": "55543210",
            "dpi": "4567890123456",
            "referral_institution": "particular",
            "comments": "Paciente con diabetes. Control semestral."
        },
        {
            "first_name": "Lucía",
            "last_name": "Hernández Vega",
            "gender": "femenino",
            "birth_date": "2000-07-12",
            "profession": "Estudiante",
            "phone": "55577777",
            "email": "lucia.h@universidad.edu.gt",
            "dpi": "5678901234567",
            "referral_institution": "otra",
            "other_institution_name": "Universidad San Carlos"
        },
        {
            "first_name": "Roberto",
            "last_name": "Estrada Juárez",
            "gender": "masculino",
            "birth_date": "1955-12-03",
            "profession": "Jubilado",
            "phone": "55533333",
            "dpi": "6789012345678",
            "referral_institution": "igss",
            "emergency_contact_name": "Miguel Estrada",
            "emergency_contact_relationship": "Hijo",
            "emergency_phone": "55544444",
            "comments": "Paciente de la tercera edad. Revisión de cataratas."
        },
        {
            "first_name": "Sofía",
            "last_name": "Ramírez Torres",
            "gender": "femenino",
            "birth_date": "2010-04-25",
            "phone": "55599999",
            "dpi": "",
            "referral_institution": "particular",
            "emergency_contact_name": "Carmen Torres",
            "emergency_contact_relationship": "Madre",
            "emergency_phone": "55588888",
            "comments": "Paciente menor de edad"
        },
        {
            "first_name": "Fernando",
            "last_name": "López Díaz",
            "gender": "masculino",
            "birth_date": "1982-09-18",
            "profession": "Abogado",
            "phone": "55566666",
            "email": "fernando.lopez@bufete.gt",
            "dpi": "7890123456789",
            "referral_institution": "seguro_privado",
            "insurance_name": "El Roble Seguros"
        }
    ]
    
    for i, patient_data in enumerate(sample_patients, 1):
        record_number = f"EXP-202604-{i:04d}"
        
        patient_doc = {
            "id": str(uuid.uuid4()),
            "record_number": record_number,
            "first_name": patient_data["first_name"],
            "last_name": patient_data["last_name"],
            "gender": patient_data["gender"],
            "birth_date": patient_data["birth_date"],
            "profession": patient_data.get("profession", ""),
            "phone": patient_data["phone"],
            "email": patient_data.get("email", ""),
            "dpi": patient_data.get("dpi", ""),
            "emergency_phone": patient_data.get("emergency_phone", ""),
            "emergency_contact_name": patient_data.get("emergency_contact_name", ""),
            "emergency_contact_relationship": patient_data.get("emergency_contact_relationship", ""),
            "referral_institution": patient_data["referral_institution"],
            "insurance_name": patient_data.get("insurance_name", ""),
            "other_institution_name": patient_data.get("other_institution_name", ""),
            "igss_unit_id": patient_data.get("igss_unit_id", ""),
            "comments": patient_data.get("comments", ""),
            "is_active": True,
            "created_by": created_by,
            "created_at": now,
            "updated_by": "",
            "updated_at": now
        }
        
        await db.patients.insert_one(patient_doc)
        print(f"Created sample patient: {patient_data['first_name']} {patient_data['last_name']}")
    
    print(f"Created {len(sample_patients)} sample patients")


# ==================== AUTH ROUTES ====================

@api_router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin):
    """Login endpoint with rate limiting (5 attempts per minute)"""
    user = await db.users.find_one({"username": credentials.username.lower().strip()})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Usuario desactivado")
    
    # Update last login
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    token = create_token(user["id"], user["username"], user["role"])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            name=user["name"],
            role=user["role"],
            is_active=user.get("is_active", True),
            last_login=datetime.now(timezone.utc).isoformat(),
            created_at=user["created_at"],
            updated_at=user.get("updated_at"),
            permissions=get_permissions(user["role"])
        )
    )

@api_router.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Invalidate the current token"""
    token = current_user.get("_token")
    if token:
        blacklisted_tokens.add(token)
    return {"message": "Sesión cerrada correctamente"}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**{k: v for k, v in current_user.items() if k != "_token"})

# ==================== USER MANAGEMENT ROUTES ====================

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_permission("view_user_management"))):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(**u, permissions=get_permissions(u["role"])) for u in users]

@api_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: dict = Depends(require_permission("view_user_management"))):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UserResponse(**user, permissions=get_permissions(user["role"]))

@api_router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate, current_user: dict = Depends(require_permission("manage_users"))):
    username = user_data.username.lower().strip()
    existing = await db.users.find_one({"username": username})
    if existing:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    user_doc = {
        "id": user_id,
        "username": username,
        "name": user_data.name,
        "password": hash_password(user_data.password),
        "role": user_data.role,
        "is_active": True,
        "last_login": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.users.insert_one(user_doc)
    
    return UserResponse(
        id=user_id,
        username=username,
        name=user_data.name,
        role=user_data.role,
        is_active=True,
        last_login=None,
        created_at=now,
        updated_at=now,
        permissions=get_permissions(user_data.role)
    )

@api_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(require_permission("manage_users"))
):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    update_data = {}
    if user_data.name is not None:
        update_data["name"] = user_data.name
    if user_data.role is not None:
        update_data["role"] = user_data.role
    if user_data.password is not None:
        update_data["password"] = hash_password(user_data.password)
    if user_data.is_active is not None:
        update_data["is_active"] = user_data.is_active
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return UserResponse(**updated, permissions=get_permissions(updated["role"]))

@api_router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: str, current_user: dict = Depends(require_permission("manage_users"))):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    new_status = not user.get("is_active", True)
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Estado actualizado", "is_active": new_status}

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_permission("manage_users"))):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {"message": "Usuario eliminado"}

# ==================== EXPENSE ROUTES ====================

@api_router.get("/expenses", response_model=ExpenseListResponse)
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
    # Check for overdue expenses first
    await check_overdue_expenses()
    
    query = {}
    
    # Type filter
    if type and type in ["fijo", "proveedor", "variable"]:
        query["type"] = type
    
    # Status filter
    if status:
        if status == "no_pagado":
            # Filtro especial: mostrar pendiente, parcial y vencido (excluir pagado)
            query["status"] = {"$in": ["pendiente", "parcial", "vencido"]}
        elif status in ["pendiente", "parcial", "pagado", "vencido"]:
            query["status"] = status
    
    # Search filter (name or invoice_number)
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"invoice_number": {"$regex": search, "$options": "i"}}
        ]
    
    # Date range filter
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["date"] = date_query
    
    # Count total
    total = await db.expenses.count_documents(query)
    
    # Sort
    sort_direction = -1 if sort_order == "desc" else 1
    sort_field = sort_by if sort_by in ["date", "amount", "due_date", "name", "status"] else "date"
    
    # Pagination
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

@api_router.post("/expenses", response_model=ExpenseResponse)
async def create_expense(expense_data: ExpenseCreate, current_user: dict = Depends(require_permission("create_expenses"))):
    expense_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Determine initial status
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
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.expenses.insert_one(expense_doc)
    
    return ExpenseResponse(**expense_doc)

@api_router.get("/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(expense_id: str, current_user: dict = Depends(require_permission("view_expenses"))):
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    # Get associated payments
    payments = await db.payments.find({"expense_id": expense_id}, {"_id": 0}).sort("date", -1).to_list(1000)
    expense["payments"] = payments
    
    return ExpenseResponse(**expense)

@api_router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    expense_data: ExpenseUpdate,
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    expense = await db.expenses.find_one({"id": expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    update_data = {k: v for k, v in expense_data.model_dump().items() if v is not None}
    
    # If amount changed, recalculate remaining
    if "amount" in update_data:
        update_data["remaining_amount"] = max(0, update_data["amount"] - expense.get("paid_amount", 0))
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    if update_data:
        await db.expenses.update_one({"id": expense_id}, {"$set": update_data})
    
    # Recalculate status
    await update_expense_amounts(expense_id)
    
    updated = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    return ExpenseResponse(**updated)

@api_router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str, current_user: dict = Depends(require_permission("delete_expenses"))):
    # Delete associated payments first
    await db.payments.delete_many({"expense_id": expense_id})
    
    result = await db.expenses.delete_one({"id": expense_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return {"message": "Gasto eliminado"}

# ==================== PAYMENT ROUTES ====================

@api_router.get("/payments", response_model=PaymentListResponse)
async def get_payments(
    expense_id: Optional[str] = Query(None, alias="expenseId"),
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    method: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_payment_history"))
):
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
            "created_by_name": {"$ifNull": [{"$arrayElemAt": ["$user_data.name", 0]}, "N/A"]}
        }},
        {"$project": {"expense_data": 0, "user_data": 0, "_id": 0}}
    ]
    
    payments = await db.payments.aggregate(payments_pipeline).to_list(10000)
    
    return PaymentListResponse(
        data=[PaymentResponse(**p) for p in payments],
        total=len(payments)
    )

@api_router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str, current_user: dict = Depends(require_permission("view_payment_history"))):
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return PaymentResponse(**payment)

@api_router.get("/expenses/{expense_id}/payments", response_model=List[PaymentResponse])
async def get_expense_payments(
    expense_id: str,
    current_user: dict = Depends(require_permission("view_payment_history"))
):
    expense = await db.expenses.find_one({"id": expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    payments = await db.payments.find({"expense_id": expense_id}, {"_id": 0}).sort("date", -1).to_list(1000)
    return [PaymentResponse(**p) for p in payments]

@api_router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: dict = Depends(require_permission("register_payments"))
):
    # Verify expense exists
    expense = await db.expenses.find_one({"id": payment_data.expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    # Check if payment would exceed remaining amount
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
    
    # Update expense amounts and status
    await update_expense_amounts(payment_data.expense_id)
    
    return PaymentResponse(**payment_doc)

@api_router.delete("/payments/{payment_id}")
async def delete_payment(
    payment_id: str,
    current_user: dict = Depends(require_permission("delete_payments"))
):
    payment = await db.payments.find_one({"id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    expense_id = payment["expense_id"]
    
    result = await db.payments.delete_one({"id": payment_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    # Update expense amounts and status
    await update_expense_amounts(expense_id)
    
    return {"message": "Pago eliminado"}

# ==================== DASHBOARD ROUTES ====================

@api_router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(current_user: dict = Depends(require_permission("view_dashboard"))):
    await check_overdue_expenses()
    
    # Get current month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get all expenses for the month
    expenses = await db.expenses.find({
        "date": {"$gte": month_start.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    total_month = sum(e["amount"] for e in expenses)
    total_paid = sum(e["paid_amount"] for e in expenses)
    total_pending = sum(e["remaining_amount"] for e in expenses)
    
    # Get overdue count efficiently
    overdue_count = await db.expenses.count_documents({"status": "vencido"})
    
    # Calculate by type
    by_type = []
    for expense_type in ["fijo", "proveedor", "variable"]:
        type_total = sum(e["amount"] for e in expenses if e["type"] == expense_type)
        percentage = (type_total / total_month * 100) if total_month > 0 else 0
        by_type.append(TypeBreakdown(
            type=expense_type,
            total=type_total,
            percentage=round(percentage, 1)
        ))
    
    return DashboardSummary(
        total_month=total_month,
        total_paid=total_paid,
        total_pending=total_pending,
        overdue_count=overdue_count,
        by_type=by_type
    )

@api_router.get("/dashboard/monthly-chart", response_model=List[MonthlyChartItem])
async def get_monthly_chart(current_user: dict = Depends(require_permission("view_dashboard"))):
    expenses = await db.expenses.find({}, {"_id": 0, "date": 1, "amount": 1}).to_list(10000)
    
    # Group by month (last 6 months)
    now = datetime.now(timezone.utc)
    monthly_data = {}
    
    for i in range(6):
        month_date = now - timedelta(days=30 * i)
        month_key = month_date.strftime("%Y-%m")
        month_name = month_date.strftime("%b")
        year = month_date.year
        monthly_data[month_key] = {"month": month_name, "year": year, "total": 0}
    
    for e in expenses:
        try:
            date = datetime.fromisoformat(e["date"])
            month_key = date.strftime("%Y-%m")
            if month_key in monthly_data:
                monthly_data[month_key]["total"] += e["amount"]
        except Exception:
            pass
    
    # Sort by date and return
    sorted_keys = sorted(monthly_data.keys())
    return [MonthlyChartItem(**monthly_data[k]) for k in sorted_keys]

@api_router.get("/dashboard/upcoming", response_model=UpcomingPayments)
async def get_upcoming_payments(current_user: dict = Depends(require_permission("view_due_payments"))):
    await check_overdue_expenses()
    
    today = datetime.now(timezone.utc).date()
    expenses = await db.expenses.find(
        {"status": {"$in": ["pendiente", "parcial", "vencido"]}},
        {"_id": 0}
    ).to_list(10000)
    
    overdue = []
    due30 = []
    due60 = []
    
    for e in expenses:
        if e.get("due_date"):
            try:
                due_date = datetime.fromisoformat(e["due_date"]).date()
                days = (due_date - today).days
                
                alert = AlertResponse(
                    id=e["id"],
                    name=e["name"],
                    provider=e.get("provider", ""),
                    amount=e["amount"],
                    remaining_amount=e.get("remaining_amount", e["amount"]),
                    due_date=e["due_date"],
                    days_remaining=days,
                    type=e["type"],
                    status=e["status"],
                    invoice_number=e.get("invoice_number", "")
                )
                
                if days < 0:
                    overdue.append(alert)
                elif 0 <= days <= 30:
                    due30.append(alert)
                elif 30 < days <= 60:
                    due60.append(alert)
            except Exception:
                pass
        elif e["status"] == "vencido":
            # Sin fecha de vencimiento pero marcado como vencido
            overdue.append(AlertResponse(
                id=e["id"],
                name=e["name"],
                provider=e.get("provider", ""),
                amount=e["amount"],
                remaining_amount=e.get("remaining_amount", e["amount"]),
                due_date=e.get("due_date", e["date"]),
                days_remaining=0,
                type=e["type"],
                status=e["status"],
                invoice_number=e.get("invoice_number", "")
            ))
    
    # Sort by days remaining
    overdue.sort(key=lambda x: x.days_remaining)
    due30.sort(key=lambda x: x.days_remaining)
    due60.sort(key=lambda x: x.days_remaining)
    
    return UpcomingPayments(overdue=overdue, due30=due30, due60=due60)

# Legacy endpoints for backwards compatibility
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(require_permission("view_dashboard"))):
    """Legacy endpoint - redirects to summary"""
    # Use aggregation for efficient stats calculation
    pipeline = [
        {"$group": {
            "_id": None,
            "total_gastos": {"$sum": "$amount"},
            "gastos_pendientes": {"$sum": {"$cond": [{"$eq": ["$status", "pendiente"]}, "$amount", 0]}},
            "gastos_pagados": {"$sum": {"$cond": [{"$eq": ["$status", "pagado"]}, "$amount", 0]}},
            "gastos_parciales": {"$sum": {"$cond": [{"$eq": ["$status", "parcial"]}, "$amount", 0]}},
            "gastos_vencidos": {"$sum": {"$cond": [{"$eq": ["$status", "vencido"]}, "$amount", 0]}},
            "total_fijos": {"$sum": {"$cond": [{"$eq": ["$type", "fijo"]}, "$amount", 0]}},
            "total_proveedores": {"$sum": {"$cond": [{"$eq": ["$type", "proveedor"]}, "$amount", 0]}},
            "total_variables": {"$sum": {"$cond": [{"$eq": ["$type", "variable"]}, "$amount", 0]}},
            "alertas_30_dias": {"$sum": {"$cond": [{"$in": ["$status", ["pendiente", "parcial"]]}, 1, 0]}}
        }}
    ]
    
    result = await db.expenses.aggregate(pipeline).to_list(1)
    
    if result:
        stats = result[0]
        del stats["_id"]
        stats["alertas_60_dias"] = 0
        return stats
    
    return {
        "total_gastos": 0,
        "gastos_pendientes": 0,
        "gastos_pagados": 0,
        "gastos_parciales": 0,
        "gastos_vencidos": 0,
        "total_fijos": 0,
        "total_proveedores": 0,
        "total_variables": 0,
        "alertas_30_dias": 0,
        "alertas_60_dias": 0
    }

@api_router.get("/dashboard/alerts/30")
async def get_alerts_30(current_user: dict = Depends(require_permission("view_due_payments"))):
    """Legacy endpoint"""
    upcoming = await get_upcoming_payments(current_user)
    return upcoming.due30

@api_router.get("/dashboard/alerts/60")
async def get_alerts_60(current_user: dict = Depends(require_permission("view_due_payments"))):
    """Legacy endpoint"""
    upcoming = await get_upcoming_payments(current_user)
    return upcoming.due60

@api_router.get("/dashboard/chart-data")
async def get_chart_data(current_user: dict = Depends(require_permission("view_dashboard"))):
    """Legacy endpoint for chart data"""
    expenses = await db.expenses.find({}, {"_id": 0, "date": 1, "type": 1, "amount": 1}).to_list(10000)
    
    monthly_data = {}
    for e in expenses:
        try:
            date = datetime.fromisoformat(e["date"])
            month_key = date.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "mes": date.strftime("%b %Y"),
                    "fijo": 0,
                    "proveedor": 0,
                    "variable": 0
                }
            
            monthly_data[month_key][e["type"]] += e["amount"]
        except Exception:
            pass
    
    sorted_data = sorted(monthly_data.values(), key=lambda x: x["mes"])
    return sorted_data[-12:]


# ==================== BANK ACCOUNTS ROUTES (SuperAdmin only) ====================

def require_superadmin():
    """Require superadmin role"""
    async def checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] != "superadmin":
            raise HTTPException(status_code=403, detail="Solo SuperAdmin puede acceder a esta función")
        return current_user
    return checker

@api_router.get("/bank-accounts", response_model=BankAccountListResponse)
async def get_bank_accounts(current_user: dict = Depends(require_superadmin())):
    """Get all bank accounts (SuperAdmin only)"""
    accounts = await db.bank_accounts.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return BankAccountListResponse(data=[BankAccountResponse(**a) for a in accounts], total=len(accounts))

@api_router.get("/bank-accounts/{account_id}", response_model=BankAccountResponse)
async def get_bank_account(account_id: str, current_user: dict = Depends(require_superadmin())):
    """Get a specific bank account (SuperAdmin only)"""
    account = await db.bank_accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    return BankAccountResponse(**account)

@api_router.post("/bank-accounts", response_model=BankAccountResponse)
async def create_bank_account(account_data: BankAccountCreate, current_user: dict = Depends(require_superadmin())):
    """Create a new bank account (SuperAdmin only)"""
    # Check for duplicate account number
    existing = await db.bank_accounts.find_one({"account_number": account_data.account_number})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una cuenta con este número")
    
    now = datetime.now(timezone.utc).isoformat()
    account_doc = {
        "id": str(uuid.uuid4()),
        "bank_name": account_data.bank_name,
        "account_number": account_data.account_number,
        "account_alias": account_data.account_alias,
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.bank_accounts.insert_one(account_doc)
    if "_id" in account_doc:
        del account_doc["_id"]
    return BankAccountResponse(**account_doc)

@api_router.put("/bank-accounts/{account_id}", response_model=BankAccountResponse)
async def update_bank_account(account_id: str, account_data: BankAccountUpdate, current_user: dict = Depends(require_superadmin())):
    """Update a bank account (SuperAdmin only)"""
    account = await db.bank_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    
    update_data = {k: v for k, v in account_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    # Check for duplicate account number if updating
    if "account_number" in update_data and update_data["account_number"] != account["account_number"]:
        existing = await db.bank_accounts.find_one({"account_number": update_data["account_number"]})
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe una cuenta con este número")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.bank_accounts.update_one({"id": account_id}, {"$set": update_data})
    updated = await db.bank_accounts.find_one({"id": account_id}, {"_id": 0})
    return BankAccountResponse(**updated)

@api_router.delete("/bank-accounts/{account_id}")
async def delete_bank_account(account_id: str, current_user: dict = Depends(require_superadmin())):
    """Delete a bank account (SuperAdmin only)"""
    account = await db.bank_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    
    await db.bank_accounts.delete_one({"id": account_id})
    return {"message": "Cuenta bancaria eliminada correctamente"}


# ==================== SUPPLIER/PROVIDER ROUTES ====================

@api_router.get("/suppliers", response_model=SupplierListResponse)
async def get_suppliers(current_user: dict = Depends(get_current_user)):
    """Obtener todos los proveedores (Admin y SuperAdmin)"""
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para ver proveedores")
    
    suppliers = await db.suppliers.find({"is_active": True}, {"_id": 0}).sort("name", 1).to_list(1000)
    return SupplierListResponse(data=suppliers, total=len(suppliers))


@api_router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    """Obtener un proveedor específico"""
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    supplier = await db.suppliers.find_one({"id": supplier_id, "is_active": True}, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return SupplierResponse(**supplier)


@api_router.post("/suppliers", response_model=SupplierResponse)
async def create_supplier(supplier_data: SupplierCreate, current_user: dict = Depends(get_current_user)):
    """Crear nuevo proveedor (Admin y SuperAdmin)"""
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear proveedores")
    
    # Verificar si ya existe un proveedor con el mismo nombre
    existing = await db.suppliers.find_one({"name": {"$regex": f"^{supplier_data.name}$", "$options": "i"}, "is_active": True})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un proveedor con este nombre")
    
    now = datetime.now(timezone.utc).isoformat()
    supplier_doc = {
        "id": str(uuid.uuid4()),
        "name": supplier_data.name,
        "contact_name": supplier_data.contact_name or "",
        "phone": supplier_data.phone or "",
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.suppliers.insert_one(supplier_doc)
    if "_id" in supplier_doc:
        del supplier_doc["_id"]
    return SupplierResponse(**supplier_doc)


@api_router.put("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(supplier_id: str, supplier_data: SupplierUpdate, current_user: dict = Depends(get_current_user)):
    """Actualizar proveedor (Admin y SuperAdmin)"""
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    supplier = await db.suppliers.find_one({"id": supplier_id, "is_active": True})
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    update_data = {k: v for k, v in supplier_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    # Verificar nombre duplicado si se está actualizando
    if "name" in update_data and update_data["name"].lower() != supplier["name"].lower():
        existing = await db.suppliers.find_one({
            "name": {"$regex": f"^{update_data['name']}$", "$options": "i"},
            "is_active": True,
            "id": {"$ne": supplier_id}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un proveedor con este nombre")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.suppliers.update_one({"id": supplier_id}, {"$set": update_data})
    updated = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})
    return SupplierResponse(**updated)


@api_router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    """Eliminar proveedor (soft delete) - Admin y SuperAdmin"""
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    supplier = await db.suppliers.find_one({"id": supplier_id, "is_active": True})
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    # Soft delete
    await db.suppliers.update_one(
        {"id": supplier_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Proveedor eliminado correctamente"}


# ==================== FIXED EXPENSE ROUTES ====================

async def enrich_fixed_expense(fixed_expense: dict) -> dict:
    """Enrich fixed expense with supplier name"""
    supplier = await db.suppliers.find_one({"id": fixed_expense["supplier_id"]}, {"_id": 0})
    if supplier:
        fixed_expense["supplier_name"] = supplier.get("name", "")
    else:
        fixed_expense["supplier_name"] = "Proveedor eliminado"
    return fixed_expense


@api_router.get("/fixed-expenses", response_model=FixedExpenseListResponse)
async def get_fixed_expenses(current_user: dict = Depends(get_current_user)):
    """Obtener todos los gastos fijos (Admin y SuperAdmin)"""
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para ver gastos fijos")
    
    fixed_expenses = await db.fixed_expenses.find({"is_active": True}, {"_id": 0}).sort("day_of_month", 1).to_list(1000)
    
    # Enriquecer con nombre del proveedor
    enriched = []
    for fe in fixed_expenses:
        enriched.append(await enrich_fixed_expense(fe))
    
    return FixedExpenseListResponse(data=enriched, total=len(enriched))


@api_router.get("/fixed-expenses/{fixed_expense_id}", response_model=FixedExpenseResponse)
async def get_fixed_expense(fixed_expense_id: str, current_user: dict = Depends(get_current_user)):
    """Obtener un gasto fijo específico"""
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    fixed_expense = await db.fixed_expenses.find_one({"id": fixed_expense_id, "is_active": True}, {"_id": 0})
    if not fixed_expense:
        raise HTTPException(status_code=404, detail="Gasto fijo no encontrado")
    
    enriched = await enrich_fixed_expense(fixed_expense)
    return FixedExpenseResponse(**enriched)


@api_router.post("/fixed-expenses", response_model=FixedExpenseResponse)
async def create_fixed_expense(fixed_expense_data: FixedExpenseCreate, current_user: dict = Depends(get_current_user)):
    """Crear nuevo gasto fijo (Admin y SuperAdmin)"""
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear gastos fijos")
    
    # Verificar que el proveedor existe
    supplier = await db.suppliers.find_one({"id": fixed_expense_data.supplier_id, "is_active": True})
    if not supplier:
        raise HTTPException(status_code=400, detail="Proveedor no encontrado")
    
    # Verificar duplicados (mismo proveedor + nombre de gasto)
    existing = await db.fixed_expenses.find_one({
        "supplier_id": fixed_expense_data.supplier_id,
        "expense_name": {"$regex": f"^{fixed_expense_data.expense_name}$", "$options": "i"},
        "is_active": True
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un gasto fijo con este nombre para este proveedor")
    
    now = datetime.now(timezone.utc).isoformat()
    fixed_expense_doc = {
        "id": str(uuid.uuid4()),
        "supplier_id": fixed_expense_data.supplier_id,
        "expense_name": fixed_expense_data.expense_name,
        "amount": fixed_expense_data.amount,
        "day_of_month": fixed_expense_data.day_of_month,
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
        "last_generated": None
    }
    
    await db.fixed_expenses.insert_one(fixed_expense_doc)
    if "_id" in fixed_expense_doc:
        del fixed_expense_doc["_id"]
    
    enriched = await enrich_fixed_expense(fixed_expense_doc)
    return FixedExpenseResponse(**enriched)


@api_router.put("/fixed-expenses/{fixed_expense_id}", response_model=FixedExpenseResponse)
async def update_fixed_expense(fixed_expense_id: str, fixed_expense_data: FixedExpenseUpdate, current_user: dict = Depends(get_current_user)):
    """Actualizar gasto fijo (Admin y SuperAdmin)"""
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    fixed_expense = await db.fixed_expenses.find_one({"id": fixed_expense_id, "is_active": True})
    if not fixed_expense:
        raise HTTPException(status_code=404, detail="Gasto fijo no encontrado")
    
    update_data = {k: v for k, v in fixed_expense_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    # Verificar proveedor si se está actualizando
    if "supplier_id" in update_data:
        supplier = await db.suppliers.find_one({"id": update_data["supplier_id"], "is_active": True})
        if not supplier:
            raise HTTPException(status_code=400, detail="Proveedor no encontrado")
    
    # Verificar duplicados si se actualiza el nombre
    if "expense_name" in update_data:
        supplier_id = update_data.get("supplier_id", fixed_expense["supplier_id"])
        existing = await db.fixed_expenses.find_one({
            "supplier_id": supplier_id,
            "expense_name": {"$regex": f"^{update_data['expense_name']}$", "$options": "i"},
            "is_active": True,
            "id": {"$ne": fixed_expense_id}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un gasto fijo con este nombre para este proveedor")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.fixed_expenses.update_one({"id": fixed_expense_id}, {"$set": update_data})
    updated = await db.fixed_expenses.find_one({"id": fixed_expense_id}, {"_id": 0})
    
    enriched = await enrich_fixed_expense(updated)
    return FixedExpenseResponse(**enriched)


@api_router.delete("/fixed-expenses/{fixed_expense_id}")
async def delete_fixed_expense(fixed_expense_id: str, current_user: dict = Depends(get_current_user)):
    """Eliminar gasto fijo (soft delete) - Admin y SuperAdmin"""
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    fixed_expense = await db.fixed_expenses.find_one({"id": fixed_expense_id, "is_active": True})
    if not fixed_expense:
        raise HTTPException(status_code=404, detail="Gasto fijo no encontrado")
    
    # Soft delete
    await db.fixed_expenses.update_one(
        {"id": fixed_expense_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Gasto fijo eliminado correctamente"}


# Endpoint manual para generar gastos fijos (testing/admin)
@api_router.post("/fixed-expenses/generate-now")
async def generate_fixed_expenses_now(current_user: dict = Depends(get_current_user)):
    """Generar manualmente los gastos fijos del día actual (solo SuperAdmin)"""
    if current_user["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Solo el SuperAdmin puede ejecutar esta acción")
    
    generated = await generate_fixed_expenses_for_today()
    return {"message": f"Se generaron {generated} gastos fijos", "count": generated}


# ==================== IGSS UNIT ROUTES (Catálogo) ====================

@api_router.get("/igss-units", response_model=IGSSUnitListResponse)
async def get_igss_units(current_user: dict = Depends(get_current_user)):
    """Obtener todas las unidades IGSS (todos los roles)"""
    units = await db.igss_units.find({"is_active": True}, {"_id": 0}).sort("name", 1).to_list(1000)
    return IGSSUnitListResponse(data=units, total=len(units))


@api_router.get("/igss-units/{unit_id}", response_model=IGSSUnitResponse)
async def get_igss_unit(unit_id: str, current_user: dict = Depends(get_current_user)):
    """Obtener una unidad IGSS específica"""
    unit = await db.igss_units.find_one({"id": unit_id, "is_active": True}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad IGSS no encontrada")
    return IGSSUnitResponse(**unit)


@api_router.post("/igss-units", response_model=IGSSUnitResponse)
async def create_igss_unit(unit_data: IGSSUnitCreate, current_user: dict = Depends(require_permission("manage_igss_units"))):
    """Crear nueva unidad IGSS (solo SuperAdmin)"""
    # Verificar duplicado por nombre
    existing = await db.igss_units.find_one({
        "name": {"$regex": f"^{unit_data.name}$", "$options": "i"},
        "is_active": True
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una unidad IGSS con este nombre")
    
    now = datetime.now(timezone.utc).isoformat()
    unit_doc = {
        "id": str(uuid.uuid4()),
        "name": unit_data.name,
        "code": unit_data.code or "",
        "description": unit_data.description or "",
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.igss_units.insert_one(unit_doc)
    if "_id" in unit_doc:
        del unit_doc["_id"]
    return IGSSUnitResponse(**unit_doc)


@api_router.put("/igss-units/{unit_id}", response_model=IGSSUnitResponse)
async def update_igss_unit(unit_id: str, unit_data: IGSSUnitUpdate, current_user: dict = Depends(require_permission("manage_igss_units"))):
    """Actualizar unidad IGSS (solo SuperAdmin)"""
    unit = await db.igss_units.find_one({"id": unit_id, "is_active": True})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad IGSS no encontrada")
    
    update_data = {k: v for k, v in unit_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    # Verificar duplicado de nombre
    if "name" in update_data and update_data["name"].lower() != unit["name"].lower():
        existing = await db.igss_units.find_one({
            "name": {"$regex": f"^{update_data['name']}$", "$options": "i"},
            "is_active": True,
            "id": {"$ne": unit_id}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe una unidad IGSS con este nombre")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.igss_units.update_one({"id": unit_id}, {"$set": update_data})
    updated = await db.igss_units.find_one({"id": unit_id}, {"_id": 0})
    return IGSSUnitResponse(**updated)


@api_router.delete("/igss-units/{unit_id}")
async def delete_igss_unit(unit_id: str, current_user: dict = Depends(require_permission("manage_igss_units"))):
    """Eliminar unidad IGSS (soft delete, solo SuperAdmin)"""
    unit = await db.igss_units.find_one({"id": unit_id, "is_active": True})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad IGSS no encontrada")
    
    # Verificar si hay pacientes usando esta unidad
    patients_using = await db.patients.count_documents({"igss_unit_id": unit_id, "is_active": True})
    if patients_using > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar: {patients_using} paciente(s) están usando esta unidad IGSS"
        )
    
    await db.igss_units.update_one(
        {"id": unit_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Unidad IGSS eliminada correctamente"}


# ==================== PATIENT HELPER FUNCTIONS ====================

def calculate_age(birth_date_str: str) -> int:
    """Calcula la edad a partir de la fecha de nacimiento"""
    try:
        birth_date = datetime.strptime(birth_date_str[:10], "%Y-%m-%d")
        today = datetime.now(timezone.utc)
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        return max(0, age)
    except Exception:
        return 0


def validate_dpi(dpi: str) -> bool:
    """Valida formato de DPI guatemalteco (13 dígitos)"""
    if not dpi:
        return True  # DPI es opcional
    return dpi.isdigit() and len(dpi) == 13


def validate_phone(phone: str) -> bool:
    """Valida formato de teléfono (básico)"""
    import re
    # Acepta formatos: 12345678, 1234-5678, +502 1234 5678, etc.
    cleaned = re.sub(r'[\s\-\+\(\)]', '', phone)
    return cleaned.isdigit() and 8 <= len(cleaned) <= 15


def validate_email(email: str) -> bool:
    """Valida formato de email"""
    if not email:
        return True  # Email es opcional
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


async def get_next_record_number() -> str:
    """Genera el siguiente número de expediente correlativo"""
    # Formato: EXP-YYYYMM-XXXX (ej: EXP-202604-0001)
    prefix = datetime.now(timezone.utc).strftime("EXP-%Y%m-")
    
    # Buscar el último expediente de este mes
    last_patient = await db.patients.find_one(
        {"record_number": {"$regex": f"^{prefix}"}},
        {"record_number": 1},
        sort=[("record_number", -1)]
    )
    
    if last_patient:
        # Extraer el número y sumar 1
        try:
            last_num = int(last_patient["record_number"].split("-")[-1])
            next_num = last_num + 1
        except Exception:
            next_num = 1
    else:
        next_num = 1
    
    return f"{prefix}{next_num:04d}"


REFERRAL_LABELS = {
    "particular": "Particular",
    "igss": "IGSS",
    "seguro_privado": "Seguro Privado",
    "otra": "Otra Institución"
}


async def enrich_patient(patient: dict) -> dict:
    """Enriquece el paciente con datos calculados y relacionados"""
    # Calcular edad
    patient["age"] = calculate_age(patient.get("birth_date", ""))
    
    # Nombre completo
    patient["full_name"] = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
    
    # Etiqueta de institución
    patient["referral_institution_label"] = REFERRAL_LABELS.get(patient.get("referral_institution", ""), "")
    
    # Nombre de unidad IGSS
    if patient.get("igss_unit_id"):
        igss_unit = await db.igss_units.find_one({"id": patient["igss_unit_id"]}, {"_id": 0, "name": 1})
        patient["igss_unit_name"] = igss_unit["name"] if igss_unit else ""
    else:
        patient["igss_unit_name"] = ""
    
    # Nombre del creador
    if patient.get("created_by"):
        creator = await db.users.find_one({"id": patient["created_by"]}, {"_id": 0, "name": 1})
        patient["created_by_name"] = creator["name"] if creator else ""
    
    # Nombre del último modificador
    if patient.get("updated_by"):
        updater = await db.users.find_one({"id": patient["updated_by"]}, {"_id": 0, "name": 1})
        patient["updated_by_name"] = updater["name"] if updater else ""
    else:
        patient["updated_by_name"] = ""
    
    return patient


# ==================== PATIENT ROUTES ====================

@api_router.get("/patients", response_model=PatientListResponse)
async def get_patients(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    referral_institution: Optional[str] = None,
    igss_unit_id: Optional[str] = None,
    gender: Optional[str] = None,
    age_from: Optional[int] = None,
    age_to: Optional[int] = None,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    is_active: bool = True,
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Listar pacientes con filtros y paginación"""
    query = {"is_active": is_active}
    
    # Búsqueda por texto
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"dpi": search_regex},
            {"phone": search_regex},
            {"record_number": search_regex}
        ]
    
    # Filtros
    if referral_institution:
        query["referral_institution"] = referral_institution
    if igss_unit_id:
        query["igss_unit_id"] = igss_unit_id
    if gender:
        query["gender"] = gender
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["created_at"] = date_query
    
    # Conteo total
    total = await db.patients.count_documents(query)
    total_pages = (total + limit - 1) // limit
    
    # Obtener pacientes
    skip = (page - 1) * limit
    patients = await db.patients.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enriquecer y filtrar por edad
    enriched_patients = []
    for patient in patients:
        enriched = await enrich_patient(patient)
        
        # Filtro de rango de edad (post-query porque la edad es calculada)
        if age_from is not None and enriched["age"] < age_from:
            continue
        if age_to is not None and enriched["age"] > age_to:
            continue
        
        enriched_patients.append(enriched)
    
    return PatientListResponse(
        data=enriched_patients,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@api_router.get("/patients/search", response_model=List[PatientSearchResponse])
async def search_patients(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Búsqueda de pacientes para autocompletado en otros módulos"""
    search_regex = {"$regex": q, "$options": "i"}
    query = {
        "is_active": True,
        "$or": [
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"dpi": search_regex},
            {"phone": search_regex},
            {"record_number": search_regex}
        ]
    }
    
    patients = await db.patients.find(query, {"_id": 0}).limit(limit).to_list(limit)
    
    results = []
    for p in patients:
        results.append(PatientSearchResponse(
            id=p["id"],
            record_number=p["record_number"],
            full_name=f"{p['first_name']} {p['last_name']}",
            dpi=p.get("dpi", ""),
            phone=p["phone"]
        ))
    
    return results


@api_router.get("/patients/check-duplicate", response_model=PatientDuplicateCheck)
async def check_patient_duplicate(
    dpi: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    birth_date: Optional[str] = None,
    exclude_id: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Verificar si existe un paciente duplicado"""
    # Primero verificar por DPI (más preciso)
    if dpi and len(dpi) == 13:
        query = {"dpi": dpi, "is_active": True}
        if exclude_id:
            query["id"] = {"$ne": exclude_id}
        
        existing = await db.patients.find_one(query, {"_id": 0})
        if existing:
            return PatientDuplicateCheck(
                exists=True,
                match_type="dpi",
                patient_id=existing["id"],
                patient_name=f"{existing['first_name']} {existing['last_name']}",
                patient_record_number=existing["record_number"]
            )
    
    # Luego verificar por nombre + apellido + fecha de nacimiento
    if first_name and last_name and birth_date:
        query = {
            "first_name": {"$regex": f"^{first_name}$", "$options": "i"},
            "last_name": {"$regex": f"^{last_name}$", "$options": "i"},
            "birth_date": birth_date,
            "is_active": True
        }
        if exclude_id:
            query["id"] = {"$ne": exclude_id}
        
        existing = await db.patients.find_one(query, {"_id": 0})
        if existing:
            return PatientDuplicateCheck(
                exists=True,
                match_type="name_birthdate",
                patient_id=existing["id"],
                patient_name=f"{existing['first_name']} {existing['last_name']}",
                patient_record_number=existing["record_number"]
            )
    
    return PatientDuplicateCheck(exists=False)


@api_router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, current_user: dict = Depends(require_permission("view_patients"))):
    """Obtener detalle de un paciente"""
    patient = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    enriched = await enrich_patient(patient)
    return PatientResponse(**enriched)


@api_router.post("/patients", response_model=PatientResponse)
async def create_patient(patient_data: PatientCreate, current_user: dict = Depends(require_permission("create_patients"))):
    """Crear nuevo paciente"""
    # Validaciones
    if not validate_phone(patient_data.phone):
        raise HTTPException(status_code=400, detail="Formato de teléfono inválido")
    
    if patient_data.email and not validate_email(patient_data.email):
        raise HTTPException(status_code=400, detail="Formato de email inválido")
    
    if patient_data.dpi and not validate_dpi(patient_data.dpi):
        raise HTTPException(status_code=400, detail="DPI debe tener exactamente 13 dígitos numéricos")
    
    # Validar fecha de nacimiento no futura
    try:
        birth_date = datetime.strptime(patient_data.birth_date[:10], "%Y-%m-%d")
        if birth_date > datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(status_code=400, detail="La fecha de nacimiento no puede ser futura")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha de nacimiento inválido (YYYY-MM-DD)")
    
    # Validar unidad IGSS si es requerida
    if patient_data.referral_institution == "igss":
        if not patient_data.igss_unit_id:
            raise HTTPException(status_code=400, detail="Debe seleccionar una unidad IGSS")
        unit = await db.igss_units.find_one({"id": patient_data.igss_unit_id, "is_active": True})
        if not unit:
            raise HTTPException(status_code=400, detail="Unidad IGSS no encontrada")
    
    # Verificar DPI único
    if patient_data.dpi:
        existing_dpi = await db.patients.find_one({"dpi": patient_data.dpi, "is_active": True})
        if existing_dpi:
            raise HTTPException(status_code=400, detail="Ya existe un paciente con este DPI")
    
    now = datetime.now(timezone.utc).isoformat()
    record_number = await get_next_record_number()
    
    patient_doc = {
        "id": str(uuid.uuid4()),
        "record_number": record_number,
        "first_name": patient_data.first_name.strip(),
        "last_name": patient_data.last_name.strip(),
        "gender": patient_data.gender,
        "birth_date": patient_data.birth_date[:10],
        "profession": patient_data.profession or "",
        "phone": patient_data.phone,
        "email": patient_data.email or "",
        "dpi": patient_data.dpi or "",
        "emergency_phone": patient_data.emergency_phone or "",
        "emergency_contact_name": patient_data.emergency_contact_name or "",
        "emergency_contact_relationship": patient_data.emergency_contact_relationship or "",
        "referral_institution": patient_data.referral_institution,
        "insurance_name": patient_data.insurance_name or "",
        "other_institution_name": patient_data.other_institution_name or "",
        "igss_unit_id": patient_data.igss_unit_id if patient_data.referral_institution == "igss" else "",
        "comments": patient_data.comments or "",
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_by": "",
        "updated_at": now
    }
    
    await db.patients.insert_one(patient_doc)
    if "_id" in patient_doc:
        del patient_doc["_id"]
    
    enriched = await enrich_patient(patient_doc)
    return PatientResponse(**enriched)


@api_router.put("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: str, patient_data: PatientUpdate, current_user: dict = Depends(require_permission("edit_patients"))):
    """Actualizar paciente"""
    patient = await db.patients.find_one({"id": patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    update_data = {k: v for k, v in patient_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    # Validaciones
    if "phone" in update_data and not validate_phone(update_data["phone"]):
        raise HTTPException(status_code=400, detail="Formato de teléfono inválido")
    
    if "email" in update_data and update_data["email"] and not validate_email(update_data["email"]):
        raise HTTPException(status_code=400, detail="Formato de email inválido")
    
    if "dpi" in update_data and update_data["dpi"] and not validate_dpi(update_data["dpi"]):
        raise HTTPException(status_code=400, detail="DPI debe tener exactamente 13 dígitos numéricos")
    
    # Validar fecha de nacimiento
    if "birth_date" in update_data:
        try:
            birth_date = datetime.strptime(update_data["birth_date"][:10], "%Y-%m-%d")
            if birth_date > datetime.now(timezone.utc).replace(tzinfo=None):
                raise HTTPException(status_code=400, detail="La fecha de nacimiento no puede ser futura")
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha de nacimiento inválido")
    
    # Verificar DPI único si cambió
    if "dpi" in update_data and update_data["dpi"]:
        existing_dpi = await db.patients.find_one({
            "dpi": update_data["dpi"],
            "is_active": True,
            "id": {"$ne": patient_id}
        })
        if existing_dpi:
            raise HTTPException(status_code=400, detail="Ya existe un paciente con este DPI")
    
    # Validar unidad IGSS si es requerida
    referral = update_data.get("referral_institution", patient["referral_institution"])
    if referral == "igss":
        igss_unit = update_data.get("igss_unit_id", patient.get("igss_unit_id"))
        if not igss_unit:
            raise HTTPException(status_code=400, detail="Debe seleccionar una unidad IGSS")
        unit = await db.igss_units.find_one({"id": igss_unit, "is_active": True})
        if not unit:
            raise HTTPException(status_code=400, detail="Unidad IGSS no encontrada")
    
    # Limpiar campos condicionales si cambia la institución
    if "referral_institution" in update_data:
        if update_data["referral_institution"] != "igss":
            update_data["igss_unit_id"] = ""
        if update_data["referral_institution"] != "seguro_privado":
            update_data["insurance_name"] = ""
        if update_data["referral_institution"] != "otra":
            update_data["other_institution_name"] = ""
    
    update_data["updated_by"] = current_user["id"]
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.patients.update_one({"id": patient_id}, {"$set": update_data})
    updated = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    
    enriched = await enrich_patient(updated)
    return PatientResponse(**enriched)


@api_router.delete("/patients/{patient_id}")
async def delete_patient(patient_id: str, current_user: dict = Depends(require_permission("delete_patients"))):
    """Desactivar paciente (soft delete, solo SuperAdmin)"""
    patient = await db.patients.find_one({"id": patient_id, "is_active": True})
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    await db.patients.update_one(
        {"id": patient_id},
        {"$set": {
            "is_active": False,
            "updated_by": current_user["id"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    return {"message": "Paciente desactivado correctamente"}


@api_router.post("/patients/{patient_id}/reactivate", response_model=PatientResponse)
async def reactivate_patient(patient_id: str, current_user: dict = Depends(require_permission("delete_patients"))):
    """Reactivar un paciente desactivado (solo SuperAdmin)"""
    patient = await db.patients.find_one({"id": patient_id, "is_active": False})
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o ya está activo")
    
    await db.patients.update_one(
        {"id": patient_id},
        {"$set": {
            "is_active": True,
            "updated_by": current_user["id"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    updated = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    enriched = await enrich_patient(updated)
    return PatientResponse(**enriched)


@api_router.get("/patients/export/template")
async def download_import_template(current_user: dict = Depends(require_permission("import_patients"))):
    """Descargar plantilla para importación de pacientes"""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Pacientes"
        
        # Headers
        headers = [
            "Nombre*", "Apellido*", "Género* (masculino/femenino/otro)",
            "Fecha Nacimiento* (YYYY-MM-DD)", "Profesión", "Teléfono*",
            "Email", "DPI (13 dígitos)", "Teléfono Emergencia",
            "Nombre Contacto Emergencia", "Parentesco",
            "Institución* (particular/igss/seguro_privado/otra)",
            "Nombre Aseguradora", "Otra Institución", "Código Unidad IGSS",
            "Comentarios"
        ]
        
        header_fill = PatternFill(start_color="0F6E56", end_color="0F6E56", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20
        
        # Ejemplo
        example = [
            "Juan", "Pérez García", "masculino", "1985-03-15", "Ingeniero",
            "55551234", "juan@email.com", "1234567890123", "55559876",
            "María Pérez", "Esposa", "particular", "", "", "", "Paciente de ejemplo"
        ]
        for col, value in enumerate(example, 1):
            ws.cell(row=2, column=col, value=value)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=plantilla_pacientes.xlsx"}
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Librería Excel no disponible")


@api_router.post("/patients/import")
async def import_patients(
    current_user: dict = Depends(require_permission("import_patients"))
):
    """Importar pacientes desde Excel (placeholder - requiere upload de archivo)"""
    # Nota: La implementación completa requiere multipart/form-data
    # Este endpoint está preparado para recibir el archivo
    raise HTTPException(status_code=501, detail="Funcionalidad de importación en desarrollo")


@api_router.get("/patients/export/excel")
async def export_patients_excel(
    search: Optional[str] = None,
    referral_institution: Optional[str] = None,
    igss_unit_id: Optional[str] = None,
    gender: Optional[str] = None,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    current_user: dict = Depends(require_permission("export_patients"))
):
    """Exportar pacientes a Excel"""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        
        # Construir query
        query = {"is_active": True}
        if search:
            search_regex = {"$regex": search, "$options": "i"}
            query["$or"] = [
                {"first_name": search_regex},
                {"last_name": search_regex},
                {"dpi": search_regex}
            ]
        if referral_institution:
            query["referral_institution"] = referral_institution
        if igss_unit_id:
            query["igss_unit_id"] = igss_unit_id
        if gender:
            query["gender"] = gender
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            if date_query:
                query["created_at"] = date_query
        
        patients = await db.patients.find(query, {"_id": 0}).sort("record_number", 1).to_list(10000)
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Pacientes"
        
        headers = [
            "No. Expediente", "Nombre", "Apellido", "Género", "Fecha Nacimiento",
            "Edad", "Profesión", "Teléfono", "Email", "DPI", "Institución",
            "Unidad IGSS", "Fecha Registro"
        ]
        
        header_fill = PatternFill(start_color="0F6E56", end_color="0F6E56", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        
        for row, patient in enumerate(patients, 2):
            enriched = await enrich_patient(patient)
            data = [
                enriched["record_number"],
                enriched["first_name"],
                enriched["last_name"],
                enriched["gender"].capitalize(),
                enriched["birth_date"],
                enriched["age"],
                enriched.get("profession", ""),
                enriched["phone"],
                enriched.get("email", ""),
                enriched.get("dpi", ""),
                enriched["referral_institution_label"],
                enriched.get("igss_unit_name", ""),
                enriched["created_at"][:10]
            ]
            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = thin_border
        
        # Ajustar anchos
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=pacientes_novavision.xlsx"}
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Librería Excel no disponible")


@api_router.get("/patients/export/pdf")
async def export_patients_pdf(
    search: Optional[str] = None,
    referral_institution: Optional[str] = None,
    gender: Optional[str] = None,
    current_user: dict = Depends(require_permission("export_patients"))
):
    """Exportar pacientes a PDF"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER
        
        # Construir query
        query = {"is_active": True}
        if search:
            search_regex = {"$regex": search, "$options": "i"}
            query["$or"] = [
                {"first_name": search_regex},
                {"last_name": search_regex},
                {"dpi": search_regex}
            ]
        if referral_institution:
            query["referral_institution"] = referral_institution
        if gender:
            query["gender"] = gender
        
        patients = await db.patients.find(query, {"_id": 0}).sort("record_number", 1).to_list(10000)
        
        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(letter),
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#0F6E56')
        )
        elements.append(Paragraph("NovaVision - Lista de Pacientes", title_style))
        elements.append(Paragraph(f"Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Tabla
        table_data = [["Expediente", "Nombre Completo", "Género", "Edad", "Teléfono", "DPI", "Institución"]]
        
        for patient in patients:
            enriched = await enrich_patient(patient)
            table_data.append([
                enriched["record_number"],
                enriched["full_name"],
                enriched["gender"].capitalize(),
                str(enriched["age"]),
                enriched["phone"],
                enriched.get("dpi", "-"),
                enriched["referral_institution_label"]
            ])
        
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F6E56')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        
        elements.append(table)
        doc.build(elements)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=pacientes_novavision.pdf"}
        )
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Librería PDF no disponible: {str(e)}")


# ==================== PAYMENT AUTHORIZATION ROUTES ====================

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


@api_router.get("/payment-authorizations", response_model=PaymentAuthorizationListResponse)
async def get_payment_authorizations(
    status: Optional[str] = Query(None, pattern="^(pendiente|ejecutado|cancelado)$"),
    current_user: dict = Depends(require_permission("view_payment_authorizations"))
):
    """Obtener todas las autorizaciones de pago"""
    query = {}
    if status:
        query["status"] = status
    
    authorizations = await db.payment_authorizations.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    # Enriquecer cada autorización con datos relacionados
    enriched = []
    for auth in authorizations:
        enriched_auth = await enrich_authorization(auth)
        enriched.append(PaymentAuthorizationResponse(**enriched_auth))
    
    # Contar pendientes y ejecutados
    pending_count = await db.payment_authorizations.count_documents({"status": "pendiente"})
    executed_count = await db.payment_authorizations.count_documents({"status": "ejecutado"})
    
    return PaymentAuthorizationListResponse(
        data=enriched,
        total=len(enriched),
        pending_count=pending_count,
        executed_count=executed_count
    )


@api_router.get("/payment-authorizations/{auth_id}", response_model=PaymentAuthorizationResponse)
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


@api_router.get("/expenses-pending-authorization")
async def get_expenses_pending_authorization(
    current_user: dict = Depends(require_permission("authorize_payments"))
):
    """Obtener gastos pendientes que pueden ser autorizados para pago (SuperAdmin only)"""
    # Obtener gastos con status pendiente, parcial o vencido que aún tienen monto pendiente
    expenses = await db.expenses.find(
        {
            "status": {"$in": ["pendiente", "parcial", "vencido"]},
            "remaining_amount": {"$gt": 0}
        },
        {"_id": 0}
    ).sort("due_date", 1).to_list(10000)
    
    # Obtener IDs de gastos que ya tienen autorización pendiente
    existing_auths = await db.payment_authorizations.find(
        {"status": "pendiente"},
        {"_id": 0, "expense_id": 1}
    ).to_list(10000)
    authorized_expense_ids = {a["expense_id"] for a in existing_auths}
    
    # Filtrar gastos que no tienen autorización pendiente
    available_expenses = [
        e for e in expenses if e["id"] not in authorized_expense_ids
    ]
    
    return {"data": available_expenses, "total": len(available_expenses)}


@api_router.post("/payment-authorizations", response_model=PaymentAuthorizationResponse)
async def create_payment_authorization(
    auth_data: PaymentAuthorizationCreate,
    current_user: dict = Depends(require_permission("authorize_payments"))
):
    """Crear una nueva autorización de pago (SuperAdmin only)"""
    # Verificar que el gasto existe
    expense = await db.expenses.find_one({"id": auth_data.expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    # Verificar que el gasto tiene monto pendiente
    remaining = expense.get("remaining_amount", expense["amount"])
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Este gasto ya está completamente pagado")
    
    # Verificar que el monto a pagar no excede el pendiente
    if auth_data.amount_to_pay > remaining:
        raise HTTPException(
            status_code=400, 
            detail=f"El monto a autorizar (Q{auth_data.amount_to_pay:.2f}) excede el monto pendiente (Q{remaining:.2f})"
        )
    
    # Verificar que la cuenta bancaria existe
    bank_account = await db.bank_accounts.find_one({"id": auth_data.bank_account_id}, {"_id": 0})
    if not bank_account:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    
    # Verificar que no existe una autorización pendiente para este gasto
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
    
    # Eliminar _id si existe
    if "_id" in auth_doc:
        del auth_doc["_id"]
    
    enriched = await enrich_authorization(auth_doc)
    return PaymentAuthorizationResponse(**enriched)


@api_router.put("/payment-authorizations/{auth_id}", response_model=PaymentAuthorizationResponse)
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
    
    # Validar nuevo monto si se está actualizando
    if "amount_to_pay" in update_data:
        expense = await db.expenses.find_one({"id": auth["expense_id"]}, {"_id": 0})
        if expense:
            remaining = expense.get("remaining_amount", expense["amount"])
            if update_data["amount_to_pay"] > remaining:
                raise HTTPException(
                    status_code=400,
                    detail=f"El monto a autorizar excede el monto pendiente (Q{remaining:.2f})"
                )
    
    # Validar cuenta bancaria si se está actualizando
    if "bank_account_id" in update_data:
        bank_account = await db.bank_accounts.find_one({"id": update_data["bank_account_id"]}, {"_id": 0})
        if not bank_account:
            raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.payment_authorizations.update_one({"id": auth_id}, {"$set": update_data})
    updated = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    
    enriched = await enrich_authorization(updated)
    return PaymentAuthorizationResponse(**enriched)


@api_router.post("/payment-authorizations/{auth_id}/execute", response_model=PaymentAuthorizationResponse)
async def execute_payment_authorization(
    auth_id: str,
    current_user: dict = Depends(require_permission("execute_payment_authorizations"))
):
    """Ejecutar una autorización de pago - crea el pago y actualiza el gasto (Admin only)"""
    auth = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    if not auth:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    
    if auth["status"] != "pendiente":
        raise HTTPException(status_code=400, detail="Esta autorización ya fue procesada")
    
    # Verificar que el gasto todavía existe y tiene saldo
    expense = await db.expenses.find_one({"id": auth["expense_id"]}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="El gasto asociado ya no existe")
    
    remaining = expense.get("remaining_amount", expense["amount"])
    if auth["amount_to_pay"] > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"El monto autorizado (Q{auth['amount_to_pay']:.2f}) excede el saldo pendiente actual (Q{remaining:.2f})"
        )
    
    # Obtener información de la cuenta bancaria para la referencia
    bank_account = await db.bank_accounts.find_one({"id": auth["bank_account_id"]}, {"_id": 0})
    bank_ref = f"{bank_account['bank_name']} - {bank_account['account_alias']}" if bank_account else "N/A"
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Crear el pago real
    payment_doc = {
        "id": str(uuid.uuid4()),
        "expense_id": auth["expense_id"],
        "amount": auth["amount_to_pay"],
        "date": now.split("T")[0],  # Solo fecha
        "method": "Transferencia bancaria",
        "reference": f"Auth: {auth_id[:8]} | Cuenta: {bank_ref}",
        "notes": f"Pago autorizado. {auth.get('notes', '')}".strip(),
        "created_by": current_user["id"],
        "created_at": now
    }
    
    await db.payments.insert_one(payment_doc)
    
    # Actualizar montos del gasto
    await update_expense_amounts(auth["expense_id"])
    
    # Actualizar la autorización a ejecutado
    await db.payment_authorizations.update_one(
        {"id": auth_id},
        {"$set": {
            "status": "ejecutado",
            "executed_by": current_user["id"],
            "executed_at": now,
            "updated_at": now
        }}
    )
    
    updated = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    enriched = await enrich_authorization(updated)
    return PaymentAuthorizationResponse(**enriched)


@api_router.post("/payment-authorizations/{auth_id}/cancel", response_model=PaymentAuthorizationResponse)
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
        {"$set": {
            "status": "cancelado",
            "updated_at": now
        }}
    )
    
    updated = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
    enriched = await enrich_authorization(updated)
    return PaymentAuthorizationResponse(**enriched)


@api_router.delete("/payment-authorizations/{auth_id}")
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


# ==================== REPORTS ROUTES ====================

@api_router.get("/reports/expenses")
async def export_expenses(
    format: str = Query("xlsx", pattern="^(xlsx|pdf|csv)$"),
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(require_permission("export_reports"))
):
    """Export expenses as Excel, CSV or PDF"""
    query = {}
    
    if type:
        query["type"] = type
    if status:
        query["status"] = status
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["date"] = date_query
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("date", -1).to_list(10000)
    
    if format == "csv":
        # CSV Export
        output = io.StringIO()
        output.write("ID,Nombre,Tipo,Monto,Fecha,Fecha Vencimiento,Factura,Estado,Pagado,Pendiente\n")
        
        for e in expenses:
            output.write(f'"{e["id"]}","{e["name"]}","{e["type"]}",{e["amount"]},"{e["date"]}","{e.get("due_date", "")}","{e.get("invoice_number", "")}","{e["status"]}",{e.get("paid_amount", 0)},{e.get("remaining_amount", e["amount"])}\n')
        
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=gastos_novavision.csv"}
        )
    
    elif format == "xlsx":
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Gastos"
            
            # Header style - Purple theme
            header_fill = PatternFill(start_color="7c3aed", end_color="7c3aed", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Headers
            headers = ["Nombre", "Tipo", "Monto (GTQ)", "Fecha", "Vencimiento", "Factura", "Estado", "Pagado", "Pendiente"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')
                cell.border = thin_border
            
            # Data
            type_labels = {"fijo": "Gasto Fijo", "proveedor": "Pago Proveedor", "variable": "Gasto Variable"}
            status_labels = {"pendiente": "Pendiente", "parcial": "Parcial", "pagado": "Pagado", "vencido": "Vencido"}
            
            # Currency format
            currency_format = 'Q #,##0.00'
            
            for row, e in enumerate(expenses, 2):
                ws.cell(row=row, column=1, value=e["name"]).border = thin_border
                ws.cell(row=row, column=2, value=type_labels.get(e["type"], e["type"])).border = thin_border
                
                # Monto with currency format
                cell_amount = ws.cell(row=row, column=3, value=e["amount"])
                cell_amount.border = thin_border
                cell_amount.number_format = currency_format
                
                ws.cell(row=row, column=4, value=e["date"][:10]).border = thin_border
                ws.cell(row=row, column=5, value=e.get("due_date", "")[:10] if e.get("due_date") else "").border = thin_border
                ws.cell(row=row, column=6, value=e.get("invoice_number", "")).border = thin_border
                ws.cell(row=row, column=7, value=status_labels.get(e["status"], e["status"])).border = thin_border
                
                # Pagado with currency format
                cell_paid = ws.cell(row=row, column=8, value=e.get("paid_amount", 0))
                cell_paid.border = thin_border
                cell_paid.number_format = currency_format
                
                # Pendiente with currency format
                cell_pending = ws.cell(row=row, column=9, value=e.get("remaining_amount", e["amount"]))
                cell_pending.border = thin_border
                cell_pending.number_format = currency_format
            
            # Adjust column widths
            ws.column_dimensions['A'].width = 35
            ws.column_dimensions['B'].width = 15
            ws.column_dimensions['C'].width = 15
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 12
            ws.column_dimensions['F'].width = 15
            ws.column_dimensions['G'].width = 12
            ws.column_dimensions['H'].width = 12
            ws.column_dimensions['I'].width = 12
            
            # Save to buffer
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=gastos_novavision.xlsx"}
            )
        except ImportError:
            # Fallback to CSV if openpyxl not installed
            return await export_expenses(format="csv", date_from=date_from, date_to=date_to, type=type, status=status, current_user=current_user)
    
    else:
        # PDF format
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            
            output = io.BytesIO()
            doc = SimpleDocTemplate(
                output, 
                pagesize=landscape(letter),
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )
            
            elements = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=12,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#7c3aed')
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=colors.grey
            )
            
            # Title
            elements.append(Paragraph("NovaVision — Reporte de Gastos", title_style))
            
            # Subtitle with date and user
            generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            elements.append(Paragraph(
                f"Generado el: {generated_at} | Usuario: {current_user.get('name', 'N/A')}",
                subtitle_style
            ))
            
            elements.append(Spacer(1, 0.2*inch))
            
            # Table data
            type_labels = {"fijo": "Gasto Fijo", "proveedor": "Pago Proveedor", "variable": "Gasto Variable"}
            status_labels = {"pendiente": "Pendiente", "parcial": "Parcial", "pagado": "Pagado", "vencido": "Vencido"}
            
            # Header row
            table_data = [["Nombre", "Tipo", "Monto (Q)", "Fecha", "Vencimiento", "Factura", "Estado", "Pagado (Q)", "Pendiente (Q)"]]
            
            # Data rows
            for e in expenses:
                table_data.append([
                    e["name"][:30] + "..." if len(e["name"]) > 30 else e["name"],
                    type_labels.get(e["type"], e["type"]),
                    f'{e["amount"]:,.2f}',
                    e["date"][:10] if e.get("date") else "",
                    e["due_date"][:10] if e.get("due_date") else "-",
                    e.get("invoice_number", "-") or "-",
                    status_labels.get(e["status"], e["status"]),
                    f'{e.get("paid_amount", 0):,.2f}',
                    f'{e.get("remaining_amount", e["amount"]):,.2f}'
                ])
            
            # Create table
            col_widths = [2*inch, 1*inch, 0.9*inch, 0.8*inch, 0.8*inch, 1*inch, 0.8*inch, 0.9*inch, 0.9*inch]
            table = Table(table_data, colWidths=col_widths)
            
            # Table style
            table.setStyle(TableStyle([
                # Header style
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c3aed')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                # Data rows style
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Monto
                ('ALIGN', (7, 1), (8, -1), 'RIGHT'),  # Pagado, Pendiente
                ('ALIGN', (3, 1), (5, -1), 'CENTER'),  # Fechas
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#7c3aed')),
            ]))
            
            elements.append(table)
            
            # Summary
            total_amount = sum(e["amount"] for e in expenses)
            total_paid = sum(e.get("paid_amount", 0) for e in expenses)
            total_pending = sum(e.get("remaining_amount", e["amount"]) for e in expenses)
            
            elements.append(Spacer(1, 0.3*inch))
            
            summary_style = ParagraphStyle(
                'Summary',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_RIGHT
            )
            
            elements.append(Paragraph(
                f"<b>Total Gastos:</b> Q {total_amount:,.2f} | <b>Total Pagado:</b> Q {total_paid:,.2f} | <b>Total Pendiente:</b> Q {total_pending:,.2f}",
                summary_style
            ))
            
            # Build PDF
            doc.build(elements)
            output.seek(0)
            
            return StreamingResponse(
                output,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=gastos_novavision.pdf"}
            )
            
        except ImportError as e:
            raise HTTPException(status_code=500, detail=f"Librería PDF no disponible: {str(e)}")

@api_router.get("/")
async def root():
    return {"message": "NovaVision API - Sistema de Gastos y Finanzas"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== FIXED EXPENSE SCHEDULER ====================

scheduler = AsyncIOScheduler()

async def generate_fixed_expenses_for_today() -> int:
    """Genera gastos a partir de los gastos fijos configurados para el día actual"""
    today = datetime.now(timezone.utc)
    day_of_month = today.day
    current_month = today.strftime("%Y-%m")
    
    logger.info(f"Ejecutando generación de gastos fijos para el día {day_of_month} del mes {current_month}")
    
    # Obtener todos los gastos fijos activos para el día actual
    fixed_expenses = await db.fixed_expenses.find({
        "is_active": True,
        "day_of_month": day_of_month
    }, {"_id": 0}).to_list(1000)
    
    generated_count = 0
    
    for fe in fixed_expenses:
        # Verificar si ya se generó este mes
        last_generated = fe.get("last_generated")
        if last_generated and last_generated.startswith(current_month):
            logger.info(f"Gasto fijo {fe['id']} ya fue generado este mes, saltando...")
            continue
        
        # Obtener el proveedor para el nombre
        supplier = await db.suppliers.find_one({"id": fe["supplier_id"]}, {"_id": 0})
        supplier_name = supplier["name"] if supplier else "Proveedor"
        
        # Calcular fecha de vencimiento (+30 días)
        expense_date = today.strftime("%Y-%m-%d")
        due_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Crear el gasto
        expense_doc = {
            "id": str(uuid.uuid4()),
            "provider": supplier_name,
            "name": fe["expense_name"],
            "type": "fijo",
            "amount": fe["amount"],
            "date": expense_date,
            "due_date": due_date,
            "invoice_number": f"GF-{current_month}-{fe['id'][:8]}",
            "status": "pendiente",
            "notes": f"Gasto fijo generado automáticamente (ID: {fe['id'][:8]})",
            "paid_amount": 0,
            "remaining_amount": fe["amount"],
            "created_by": "system",
            "created_at": now,
            "updated_at": now
        }
        
        await db.expenses.insert_one(expense_doc)
        
        # Actualizar la fecha de última generación
        await db.fixed_expenses.update_one(
            {"id": fe["id"]},
            {"$set": {"last_generated": current_month, "updated_at": now}}
        )
        
        generated_count += 1
        logger.info(f"Gasto fijo generado: {fe['expense_name']} - Q{fe['amount']:.2f}")
    
    logger.info(f"Generación completada. Total gastos generados: {generated_count}")
    return generated_count


def start_scheduler():
    """Inicia el scheduler para tareas programadas"""
    # Ejecutar todos los días a las 00:05 hora del servidor
    scheduler.add_job(
        generate_fixed_expenses_for_today,
        CronTrigger(hour=0, minute=5),
        id="generate_fixed_expenses",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler de gastos fijos iniciado (ejecuta diariamente a las 00:05)")


@app.on_event("startup")
async def startup_event():
    """Run seed on startup and create indexes"""
    await seed_default_users()
    await seed_sample_expenses()
    await seed_sample_patients()
    # Create indexes
    await db.expenses.create_index([("date", -1)])
    await db.expenses.create_index([("due_date", 1)])
    await db.expenses.create_index([("status", 1)])
    await db.expenses.create_index([("type", 1)])
    await db.payments.create_index([("expense_id", 1)])
    await db.payments.create_index([("date", -1)])
    await db.payment_authorizations.create_index([("expense_id", 1)])
    await db.payment_authorizations.create_index([("status", 1)])
    await db.payment_authorizations.create_index([("created_at", -1)])
    await db.suppliers.create_index([("name", 1)])
    await db.suppliers.create_index([("is_active", 1)])
    await db.fixed_expenses.create_index([("supplier_id", 1)])
    await db.fixed_expenses.create_index([("day_of_month", 1)])
    await db.fixed_expenses.create_index([("is_active", 1)])
    # Índices de pacientes
    await db.patients.create_index([("record_number", 1)], unique=True)
    await db.patients.create_index([("dpi", 1)])
    await db.patients.create_index([("first_name", 1), ("last_name", 1)])
    await db.patients.create_index([("phone", 1)])
    await db.patients.create_index([("referral_institution", 1)])
    await db.patients.create_index([("igss_unit_id", 1)])
    await db.patients.create_index([("is_active", 1)])
    await db.patients.create_index([("created_at", -1)])
    # Índices de unidades IGSS
    await db.igss_units.create_index([("name", 1)])
    await db.igss_units.create_index([("is_active", 1)])
    try:
        await db.users.create_index([("username", 1)], unique=True)
    except Exception:
        pass  # Index may already exist
    
    # Iniciar scheduler de gastos fijos
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_db_client():
    scheduler.shutdown(wait=False)
    client.close()
