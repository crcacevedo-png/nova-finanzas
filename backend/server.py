from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
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
JWT_EXPIRATION_HOURS = 8  # Changed to 8 hours

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

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = Field(default="usuario", pattern="^(superadmin|admin|usuario)$")

class UserCreate(UserBase):
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    created_at: str
    is_active: bool = True
    permissions: dict = {}

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_in: int = JWT_EXPIRATION_HOURS * 3600

class ExpenseBase(BaseModel):
    concepto: str
    monto: float
    fecha: str
    categoria: str = Field(pattern="^(gastos_fijos|pagos_proveedores|gastos_variables)$")
    estado: str = Field(default="pendiente", pattern="^(pagado|pendiente)$")
    fecha_vencimiento: Optional[str] = None
    proveedor: Optional[str] = None
    notas: Optional[str] = None

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    concepto: Optional[str] = None
    monto: Optional[float] = None
    fecha: Optional[str] = None
    categoria: Optional[str] = None
    estado: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    proveedor: Optional[str] = None
    notas: Optional[str] = None

class ExpenseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    concepto: str
    monto: float
    fecha: str
    categoria: str
    estado: str
    fecha_vencimiento: Optional[str] = None
    proveedor: Optional[str] = None
    notas: Optional[str] = None
    created_by: str
    created_at: str

class DashboardStats(BaseModel):
    total_gastos: float
    gastos_pendientes: float
    gastos_pagados: float
    total_gastos_fijos: float
    total_pagos_proveedores: float
    total_gastos_variables: float
    alertas_30_dias: int
    alertas_60_dias: int

class AlertResponse(BaseModel):
    id: str
    concepto: str
    monto: float
    fecha_vencimiento: str
    dias_restantes: int
    proveedor: Optional[str] = None

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
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
        
        # Add permissions to user
        user["permissions"] = get_permissions(user["role"])
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

def require_role(allowed_roles: List[str]):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return current_user
    return role_checker

def require_permission(permission: str):
    async def permission_checker(current_user: dict = Depends(get_current_user)):
        user_permissions = get_permissions(current_user["role"])
        if not user_permissions.get(permission, False):
            raise HTTPException(status_code=403, detail="No tienes permiso para realizar esta acción")
        return current_user
    return permission_checker

# ==================== SEED USERS ====================

async def seed_default_users():
    """Create default users if they don't exist"""
    default_users = [
        {
            "email": "superadmin@novavision.gt",
            "name": "Administrador General",
            "password": "nova2024",
            "role": "superadmin"
        },
        {
            "email": "admin@novavision.gt",
            "name": "Administrador",
            "password": "admin2024",
            "role": "admin"
        },
        {
            "email": "usuario@novavision.gt",
            "name": "Usuario NovaVision",
            "password": "user2024",
            "role": "usuario"
        }
    ]
    
    for user_data in default_users:
        existing = await db.users.find_one({"email": user_data["email"]})
        if not existing:
            user_doc = {
                "id": str(uuid.uuid4()),
                "email": user_data["email"],
                "name": user_data["name"],
                "password": hash_password(user_data["password"]),
                "role": user_data["role"],
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user_doc)
            print(f"Created default user: {user_data['email']}")

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Check if this is the first user (make them superadmin)
    user_count = await db.users.count_documents({})
    role = "superadmin" if user_count == 0 else user_data.role
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password": hash_password(user_data.password),
        "role": role,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_token(user_id, user_data.email, role)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            role=role,
            created_at=user_doc["created_at"],
            is_active=True,
            permissions=get_permissions(role)
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Usuario desactivado")
    
    token = create_token(user["id"], user["email"], user["role"])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            created_at=user["created_at"],
            is_active=user.get("is_active", True),
            permissions=get_permissions(user["role"])
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)

@api_router.get("/auth/permissions")
async def get_user_permissions(current_user: dict = Depends(get_current_user)):
    return {"permissions": get_permissions(current_user["role"])}

# ==================== USER MANAGEMENT ROUTES ====================

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_permission("view_user_management"))):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(**u, permissions=get_permissions(u["role"])) for u in users]

@api_router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate, current_user: dict = Depends(require_permission("manage_users"))):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password": hash_password(user_data.password),
        "role": user_data.role,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    return UserResponse(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,
        created_at=user_doc["created_at"],
        is_active=True,
        permissions=get_permissions(user_data.role)
    )

@api_router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: str, current_user: dict = Depends(require_permission("manage_users"))):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    new_status = not user.get("is_active", True)
    await db.users.update_one({"id": user_id}, {"$set": {"is_active": new_status}})
    
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
    categoria: Optional[str] = None,
    estado: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_expenses"))
):
    query = {}
    if categoria:
        query["categoria"] = categoria
    if estado:
        query["estado"] = estado
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("fecha", -1).to_list(1000)
    return [ExpenseResponse(**e) for e in expenses]

@api_router.post("/expenses", response_model=ExpenseResponse)
async def create_expense(expense_data: ExpenseCreate, current_user: dict = Depends(require_permission("create_expenses"))):
    expense_id = str(uuid.uuid4())
    expense_doc = {
        "id": expense_id,
        **expense_data.model_dump(),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
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
    if update_data:
        await db.expenses.update_one({"id": expense_id}, {"$set": update_data})
    
    updated = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    return ExpenseResponse(**updated)

@api_router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str, current_user: dict = Depends(require_permission("delete_expenses"))):
    result = await db.expenses.delete_one({"id": expense_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return {"message": "Gasto eliminado"}

# ==================== PAYMENT ROUTES ====================

@api_router.put("/expenses/{expense_id}/pay")
async def register_payment(expense_id: str, current_user: dict = Depends(require_permission("register_payments"))):
    expense = await db.expenses.find_one({"id": expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    await db.expenses.update_one(
        {"id": expense_id}, 
        {"$set": {"estado": "pagado", "paid_at": datetime.now(timezone.utc).isoformat(), "paid_by": current_user["id"]}}
    )
    
    updated = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    return ExpenseResponse(**updated)

# ==================== DASHBOARD & ALERTS ====================

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(require_permission("view_dashboard"))):
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(10000)
    
    total_gastos = sum(e["monto"] for e in expenses)
    gastos_pendientes = sum(e["monto"] for e in expenses if e["estado"] == "pendiente")
    gastos_pagados = sum(e["monto"] for e in expenses if e["estado"] == "pagado")
    
    total_gastos_fijos = sum(e["monto"] for e in expenses if e["categoria"] == "gastos_fijos")
    total_pagos_proveedores = sum(e["monto"] for e in expenses if e["categoria"] == "pagos_proveedores")
    total_gastos_variables = sum(e["monto"] for e in expenses if e["categoria"] == "gastos_variables")
    
    # Calculate alerts
    today = datetime.now(timezone.utc).date()
    alertas_30 = 0
    alertas_60 = 0
    
    for e in expenses:
        if e["estado"] == "pendiente" and e.get("fecha_vencimiento"):
            try:
                venc = datetime.fromisoformat(e["fecha_vencimiento"]).date()
                dias = (venc - today).days
                if 0 <= dias <= 30:
                    alertas_30 += 1
                elif 30 < dias <= 60:
                    alertas_60 += 1
            except:
                pass
    
    return DashboardStats(
        total_gastos=total_gastos,
        gastos_pendientes=gastos_pendientes,
        gastos_pagados=gastos_pagados,
        total_gastos_fijos=total_gastos_fijos,
        total_pagos_proveedores=total_pagos_proveedores,
        total_gastos_variables=total_gastos_variables,
        alertas_30_dias=alertas_30,
        alertas_60_dias=alertas_60
    )

@api_router.get("/dashboard/alerts/30", response_model=List[AlertResponse])
async def get_alerts_30_days(current_user: dict = Depends(require_permission("view_due_payments"))):
    today = datetime.now(timezone.utc).date()
    expenses = await db.expenses.find({"estado": "pendiente"}, {"_id": 0}).to_list(10000)
    
    alerts = []
    for e in expenses:
        if e.get("fecha_vencimiento"):
            try:
                venc = datetime.fromisoformat(e["fecha_vencimiento"]).date()
                dias = (venc - today).days
                if 0 <= dias <= 30:
                    alerts.append(AlertResponse(
                        id=e["id"],
                        concepto=e["concepto"],
                        monto=e["monto"],
                        fecha_vencimiento=e["fecha_vencimiento"],
                        dias_restantes=dias,
                        proveedor=e.get("proveedor")
                    ))
            except:
                pass
    
    return sorted(alerts, key=lambda x: x.dias_restantes)

@api_router.get("/dashboard/alerts/60", response_model=List[AlertResponse])
async def get_alerts_60_days(current_user: dict = Depends(require_permission("view_due_payments"))):
    today = datetime.now(timezone.utc).date()
    expenses = await db.expenses.find({"estado": "pendiente"}, {"_id": 0}).to_list(10000)
    
    alerts = []
    for e in expenses:
        if e.get("fecha_vencimiento"):
            try:
                venc = datetime.fromisoformat(e["fecha_vencimiento"]).date()
                dias = (venc - today).days
                if 30 < dias <= 60:
                    alerts.append(AlertResponse(
                        id=e["id"],
                        concepto=e["concepto"],
                        monto=e["monto"],
                        fecha_vencimiento=e["fecha_vencimiento"],
                        dias_restantes=dias,
                        proveedor=e.get("proveedor")
                    ))
            except:
                pass
    
    return sorted(alerts, key=lambda x: x.dias_restantes)

@api_router.get("/dashboard/chart-data")
async def get_chart_data(current_user: dict = Depends(require_permission("view_dashboard"))):
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(10000)
    
    # Group by month and category
    monthly_data = {}
    for e in expenses:
        try:
            date = datetime.fromisoformat(e["fecha"])
            month_key = date.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "mes": date.strftime("%b %Y"),
                    "gastos_fijos": 0,
                    "pagos_proveedores": 0,
                    "gastos_variables": 0
                }
            
            monthly_data[month_key][e["categoria"]] += e["monto"]
        except:
            pass
    
    # Sort by month
    sorted_data = sorted(monthly_data.values(), key=lambda x: x["mes"])
    
    return sorted_data[-12:]  # Last 12 months

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
    """Run seed on startup"""
    await seed_default_users()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
