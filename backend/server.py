from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
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
        "view_payment_authorizations": True
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
        "execute_payment_authorizations": True
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
        "execute_payment_authorizations": False
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
    type: Literal["fijo", "proveedor", "variable"]
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
    type: Optional[Literal["fijo", "proveedor", "variable"]] = None
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
    amount: float
    remaining_amount: float
    due_date: str
    days_remaining: int
    type: str
    status: str

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
        except:
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
        except:
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
    if status and status in ["pendiente", "parcial", "pagado", "vencido"]:
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
        except:
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
        except:
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
        if e["status"] == "vencido":
            overdue.append(AlertResponse(
                id=e["id"],
                name=e["name"],
                amount=e["amount"],
                remaining_amount=e.get("remaining_amount", e["amount"]),
                due_date=e.get("due_date", e["date"]),
                days_remaining=0,
                type=e["type"],
                status=e["status"]
            ))
        elif e.get("due_date"):
            try:
                due_date = datetime.fromisoformat(e["due_date"]).date()
                days = (due_date - today).days
                
                alert = AlertResponse(
                    id=e["id"],
                    name=e["name"],
                    amount=e["amount"],
                    remaining_amount=e.get("remaining_amount", e["amount"]),
                    due_date=e["due_date"],
                    days_remaining=days,
                    type=e["type"],
                    status=e["status"]
                )
                
                if days < 0:
                    overdue.append(alert)
                elif 0 <= days <= 30:
                    due30.append(alert)
                elif 30 < days <= 60:
                    due60.append(alert)
            except:
                pass
    
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
        except:
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

@app.on_event("startup")
async def startup_event():
    """Run seed on startup and create indexes"""
    await seed_default_users()
    await seed_sample_expenses()
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
    try:
        await db.users.create_index([("username", 1)], unique=True)
    except:
        pass  # Index may already exist

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
