from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'novavision_secret_key_2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8

# Create the main app
app = FastAPI(title="NovaVision - Sistema de Gastos y Finanzas")

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
        "export_reports": True
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
        "export_reports": True
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
        "export_reports": False
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
    name: str  # Nombre descriptivo del gasto
    type: Literal["fijo", "proveedor", "variable"]  # Tipo de gasto
    amount: float = Field(ge=0)  # Monto total en GTQ
    date: str  # Fecha de registro
    due_date: Optional[str] = None  # Fecha de vencimiento
    invoice_number: Optional[str] = None  # Número de factura
    notes: Optional[str] = ""

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
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
    name: str
    type: str
    amount: float
    date: str
    due_date: Optional[str] = None
    invoice_number: Optional[str] = None
    status: str  # pendiente, parcial, pagado, vencido
    notes: Optional[str] = ""
    paid_amount: float = 0
    remaining_amount: float = 0
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

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
    amount: float
    date: str
    method: str
    reference: Optional[str] = None
    notes: Optional[str] = ""
    created_by: str
    created_at: str

class DashboardStats(BaseModel):
    total_gastos: float
    gastos_pendientes: float
    gastos_pagados: float
    gastos_parciales: float
    gastos_vencidos: float
    total_fijos: float
    total_proveedores: float
    total_variables: float
    alertas_30_dias: int
    alertas_60_dias: int

class AlertResponse(BaseModel):
    id: str
    name: str
    amount: float
    remaining_amount: float
    due_date: str
    days_remaining: int
    type: str
    status: str

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
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
        user["permissions"] = get_permissions(user["role"])
        
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
    
    # Determine status
    status = "pendiente"
    if paid_amount >= expense["amount"]:
        status = "pagado"
    elif paid_amount > 0:
        status = "parcial"
    elif expense.get("due_date"):
        try:
            due_date = datetime.fromisoformat(expense["due_date"]).date()
            if due_date < datetime.now(timezone.utc).date():
                status = "vencido"
        except:
            pass
    
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
        {"_id": 0}
    ).to_list(10000)
    
    for expense in expenses:
        try:
            due_date = datetime.fromisoformat(expense["due_date"]).date()
            if due_date < today and expense["status"] != "vencido":
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
        {
            "username": "superadmin",
            "name": "Administrador General",
            "password": "nova2024",
            "role": "superadmin"
        },
        {
            "username": "admin",
            "name": "Administrador",
            "password": "admin2024",
            "role": "admin"
        },
        {
            "username": "usuario",
            "name": "Usuario NovaVision",
            "password": "user2024",
            "role": "usuario"
        }
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

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
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

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)

# ==================== USER MANAGEMENT ROUTES ====================

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_permission("view_user_management"))):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(**u, permissions=get_permissions(u["role"])) for u in users]

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

@api_router.get("/expenses", response_model=List[ExpenseResponse])
async def get_expenses(
    type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_expenses"))
):
    # Check for overdue expenses first
    await check_overdue_expenses()
    
    query = {}
    if type:
        query["type"] = type
    if status:
        query["status"] = status
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return [ExpenseResponse(**e) for e in expenses]

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

@api_router.get("/payments", response_model=List[PaymentResponse])
async def get_payments(
    expense_id: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_payment_history"))
):
    query = {}
    if expense_id:
        query["expense_id"] = expense_id
    
    payments = await db.payments.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return [PaymentResponse(**p) for p in payments]

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

# ==================== DASHBOARD & ALERTS ====================

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(require_permission("view_dashboard"))):
    # Check for overdue expenses first
    await check_overdue_expenses()
    
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(10000)
    
    total_gastos = sum(e["amount"] for e in expenses)
    gastos_pendientes = sum(e["amount"] for e in expenses if e["status"] == "pendiente")
    gastos_pagados = sum(e["amount"] for e in expenses if e["status"] == "pagado")
    gastos_parciales = sum(e["amount"] for e in expenses if e["status"] == "parcial")
    gastos_vencidos = sum(e["amount"] for e in expenses if e["status"] == "vencido")
    
    total_fijos = sum(e["amount"] for e in expenses if e["type"] == "fijo")
    total_proveedores = sum(e["amount"] for e in expenses if e["type"] == "proveedor")
    total_variables = sum(e["amount"] for e in expenses if e["type"] == "variable")
    
    # Calculate alerts
    today = datetime.now(timezone.utc).date()
    alertas_30 = 0
    alertas_60 = 0
    
    for e in expenses:
        if e["status"] in ["pendiente", "parcial"] and e.get("due_date"):
            try:
                due_date = datetime.fromisoformat(e["due_date"]).date()
                days = (due_date - today).days
                if 0 <= days <= 30:
                    alertas_30 += 1
                elif 30 < days <= 60:
                    alertas_60 += 1
            except:
                pass
    
    return DashboardStats(
        total_gastos=total_gastos,
        gastos_pendientes=gastos_pendientes,
        gastos_pagados=gastos_pagados,
        gastos_parciales=gastos_parciales,
        gastos_vencidos=gastos_vencidos,
        total_fijos=total_fijos,
        total_proveedores=total_proveedores,
        total_variables=total_variables,
        alertas_30_dias=alertas_30,
        alertas_60_dias=alertas_60
    )

@api_router.get("/dashboard/alerts/30", response_model=List[AlertResponse])
async def get_alerts_30_days(current_user: dict = Depends(require_permission("view_due_payments"))):
    today = datetime.now(timezone.utc).date()
    expenses = await db.expenses.find(
        {"status": {"$in": ["pendiente", "parcial"]}},
        {"_id": 0}
    ).to_list(10000)
    
    alerts = []
    for e in expenses:
        if e.get("due_date"):
            try:
                due_date = datetime.fromisoformat(e["due_date"]).date()
                days = (due_date - today).days
                if 0 <= days <= 30:
                    alerts.append(AlertResponse(
                        id=e["id"],
                        name=e["name"],
                        amount=e["amount"],
                        remaining_amount=e.get("remaining_amount", e["amount"]),
                        due_date=e["due_date"],
                        days_remaining=days,
                        type=e["type"],
                        status=e["status"]
                    ))
            except:
                pass
    
    return sorted(alerts, key=lambda x: x.days_remaining)

@api_router.get("/dashboard/alerts/60", response_model=List[AlertResponse])
async def get_alerts_60_days(current_user: dict = Depends(require_permission("view_due_payments"))):
    today = datetime.now(timezone.utc).date()
    expenses = await db.expenses.find(
        {"status": {"$in": ["pendiente", "parcial"]}},
        {"_id": 0}
    ).to_list(10000)
    
    alerts = []
    for e in expenses:
        if e.get("due_date"):
            try:
                due_date = datetime.fromisoformat(e["due_date"]).date()
                days = (due_date - today).days
                if 30 < days <= 60:
                    alerts.append(AlertResponse(
                        id=e["id"],
                        name=e["name"],
                        amount=e["amount"],
                        remaining_amount=e.get("remaining_amount", e["amount"]),
                        due_date=e["due_date"],
                        days_remaining=days,
                        type=e["type"],
                        status=e["status"]
                    ))
            except:
                pass
    
    return sorted(alerts, key=lambda x: x.days_remaining)

@api_router.get("/dashboard/chart-data")
async def get_chart_data(current_user: dict = Depends(require_permission("view_dashboard"))):
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(10000)
    
    # Group by month and type
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
    # Create indexes
    await db.expenses.create_index([("date", -1)])
    await db.expenses.create_index([("due_date", 1)])
    await db.expenses.create_index([("status", 1)])
    await db.expenses.create_index([("type", 1)])
    await db.payments.create_index([("expense_id", 1)])
    await db.payments.create_index([("date", -1)])
    await db.users.create_index([("username", 1)], unique=True)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
