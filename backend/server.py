from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Request, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import logging
import secrets
import re
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

# ==================== SECURITY CONFIGURATION ====================

# Rate Limiter con configuración más estricta
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings - CRÍTICO: No usar fallback en producción
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET or JWT_SECRET == 'novavision_secret_key_2024':
    # Generar un secret seguro si no está configurado correctamente
    JWT_SECRET = secrets.token_urlsafe(64)
    logging.warning("⚠️ SEGURIDAD: JWT_SECRET no configurado. Usando valor temporal. Configure en .env para producción.")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8  # Reducido de 24 a 8 horas por seguridad

# CORS - Orígenes permitidos (restringir en producción)
ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip() and origin.strip() != '*']
if not ALLOWED_ORIGINS:
    # Orígenes por defecto para desarrollo
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://novavision-finanzas.preview.emergentagent.com",
        "https://novavision-finanzas.emergent.host"
    ]

# Create the main app
app = FastAPI(
    title="NovaVision - Sistema de Gastos y Finanzas",
    docs_url="/api/docs" if os.environ.get('ENABLE_DOCS', 'true').lower() == 'true' else None,
    redoc_url="/api/redoc" if os.environ.get('ENABLE_DOCS', 'true').lower() == 'true' else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()


# ==================== SECURITY MIDDLEWARE ====================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para agregar headers de seguridad a todas las respuestas"""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Protección contra Clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevenir MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Protección XSS (para navegadores antiguos)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (restringe APIs del navegador)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy básica
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        
        # Forzar HTTPS en producción
        if os.environ.get('ENVIRONMENT', 'development') == 'production':
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


# ==================== AUDIT LOGGING ====================

class AuditLogger:
    """Sistema de logging de auditoría para acciones sensibles"""
    
    @staticmethod
    async def log(action: str, user_id: str, user_name: str, details: dict = None, ip_address: str = None):
        """Registra una acción en el log de auditoría"""
        audit_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user_id": user_id,
            "user_name": user_name,
            "ip_address": ip_address,
            "details": details or {},
        }
        try:
            await db.audit_logs.insert_one(audit_entry)
        except Exception as e:
            logging.error(f"Error al guardar audit log: {e}")
    
    @staticmethod
    async def get_logs(limit: int = 100, user_id: str = None, action: str = None):
        """Obtiene logs de auditoría con filtros opcionales"""
        query = {}
        if user_id:
            query["user_id"] = user_id
        if action:
            query["action"] = action
        
        logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
        return logs

audit = AuditLogger()

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
        "export_patients": True,
        # Permisos de Óptica (SuperAdmin tiene acceso total)
        "view_optica": True,
        "manage_optica_inventory": True,
        "manage_optica_sales": True,
        "manage_optica_expenses": True,
        "view_optica_reports": True,
        "manage_doctors": True,
        "manage_lens_catalog": True,
        # Permisos de Auditoría (Solo SuperAdmin)
        "view_audit_logs": True
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
        "export_patients": True,
        # Sin acceso a Óptica
        "view_optica": False,
        "manage_optica_inventory": False,
        "manage_optica_sales": False,
        "manage_optica_expenses": False,
        "view_optica_reports": False,
        "manage_doctors": False,
        "manage_lens_catalog": False,
        # Sin acceso a Auditoría
        "view_audit_logs": False
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
        "export_patients": False,
        # Sin acceso a Óptica
        "view_optica": False,
        "manage_optica_inventory": False,
        "manage_optica_sales": False,
        "manage_optica_expenses": False,
        "view_optica_reports": False,
        "manage_doctors": False,
        "manage_lens_catalog": False,
        # Sin acceso a Auditoría
        "view_audit_logs": False
    },
    "optica": {
        # Sin acceso al módulo de finanzas general
        "view_dashboard": False,
        "view_expenses": False,
        "view_payment_history": False,
        "view_due_payments": False,
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
        # Acceso a Pacientes (para seleccionar clientes)
        "view_patients": True,
        "create_patients": True,
        "edit_patients": True,
        "delete_patients": False,
        "manage_igss_units": False,
        "import_patients": False,
        "export_patients": False,
        # Acceso a Proveedores (solo ver y crear)
        "view_suppliers": True,
        "create_suppliers": True,
        "edit_suppliers": False,
        "delete_suppliers": False,
        # Permisos completos de Óptica
        "view_optica": True,
        "manage_optica_inventory": True,
        "manage_optica_sales": True,
        "manage_optica_expenses": True,
        "view_optica_reports": True,
        "manage_doctors": True,
        "manage_lens_catalog": True,
        # Sin acceso a Auditoría
        "view_audit_logs": False
    }
}

def get_permissions(role: str) -> dict:
    return PERMISSIONS.get(role, PERMISSIONS["usuario"])

# ==================== MODELS ====================

# User Models
class UserBase(BaseModel):
    username: str
    name: str
    role: str = Field(default="usuario", pattern="^(superadmin|admin|usuario|optica)$")

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
    is_authorized: bool = False  # Marcado para autorización por SuperAdmin
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
    expense_number: Optional[str] = None  # Número correlativo del gasto
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
    expense_number: Optional[str] = None  # Número correlativo del gasto
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

# ==================== SURGERY MODELS (Sala de Operaciones) ====================

class IGSSData(BaseModel):
    unit: Optional[str] = None
    sps: Optional[str] = None
    affiliation_number: Optional[str] = None
    code: Optional[str] = None
    procedure_cost: Optional[float] = None

class EquipmentItem(BaseModel):
    id: Optional[str] = None
    name: str
    quantity: int = 1
    notes: Optional[str] = ""
    added_at: Optional[str] = None
    added_by: Optional[str] = None

class SupplyItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: str = "otro"  # lente, medicamento, material, descartable, sutura, viscoelastico, otro
    quantity: int = 1
    unit_cost: float = 0
    total_cost: Optional[float] = None
    notes: Optional[str] = ""
    added_at: Optional[str] = None
    added_by: Optional[str] = None

class SurgeryBase(BaseModel):
    date: str
    time: str
    patient_name: str
    procedure: str
    surgeon: str
    eye: str  # OD, OI, AO
    anesthesia_type: str  # local, topica, general, retrobulbar, peribulbar, sedacion
    anesthesiologist: str
    institution: str
    igss_data: Optional[IGSSData] = None
    observations: Optional[str] = ""

class SurgeryCreate(SurgeryBase):
    pass

class SurgeryUpdate(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    patient_name: Optional[str] = None
    procedure: Optional[str] = None
    surgeon: Optional[str] = None
    eye: Optional[str] = None
    anesthesia_type: Optional[str] = None
    anesthesiologist: Optional[str] = None
    institution: Optional[str] = None
    igss_data: Optional[IGSSData] = None
    observations: Optional[str] = None
    status: Optional[str] = None  # activo, cancelado
    cancellation_reason: Optional[str] = None
    rescheduled_to: Optional[str] = None

class SurgeryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    date: str
    time: str
    patient_name: str
    procedure: str
    surgeon: str
    eye: str
    anesthesia_type: str
    anesthesiologist: str
    institution: str
    igss_data: Optional[IGSSData] = None
    observations: Optional[str] = ""
    equipment: List[EquipmentItem] = []
    supplies: List[SupplyItem] = []
    status: str = "activo"
    cancellation_reason: Optional[str] = None
    rescheduled_to: Optional[str] = None
    created_by: str
    created_by_name: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

class SurgeryListResponse(BaseModel):
    data: List[SurgeryResponse]
    total: int
    page: int
    limit: int
    total_pages: int

# ==================== SUPPLIER/PROVIDER MODELS ====================

class SupplierBase(BaseModel):
    name: str
    contact_name: Optional[str] = ""
    phone: Optional[str] = ""
    bank_account: Optional[str] = ""  # Número de cuenta bancaria

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    bank_account: Optional[str] = None

class SupplierResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    contact_name: Optional[str] = ""
    phone: Optional[str] = ""
    bank_account: Optional[str] = ""
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
    duration_type: str = "ilimitado"  # "ilimitado" o "hasta_fecha"
    end_date: Optional[str] = None  # Fecha de último pago (YYYY-MM-DD), null si ilimitado

class FixedExpenseCreate(FixedExpenseBase):
    generate_first: bool = False  # Generar el primer gasto inmediatamente

class FixedExpenseUpdate(BaseModel):
    supplier_id: Optional[str] = None
    expense_name: Optional[str] = None
    amount: Optional[float] = None
    day_of_month: Optional[int] = None
    duration_type: Optional[str] = None
    end_date: Optional[str] = None
    is_active: Optional[bool] = None

class FixedExpenseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    supplier_id: str
    supplier_name: Optional[str] = ""
    expense_name: str
    amount: float
    day_of_month: int
    duration_type: str = "ilimitado"
    end_date: Optional[str] = None
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None
    last_generated: Optional[str] = None
    first_expense_generated: Optional[bool] = None  # Indica si se generó el primer gasto

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

# ==================== OPTICA MODELS ====================

# Médicos
class DoctorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    specialty: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    license_number: Optional[str] = ""  # Número de colegiado
    notes: Optional[str] = ""

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class DoctorResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    specialty: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    license_number: Optional[str] = ""
    notes: Optional[str] = ""
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class DoctorListResponse(BaseModel):
    data: List[DoctorResponse]
    total: int

# Inventario de Aros
class FrameInventoryBase(BaseModel):
    brand: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    model: Optional[str] = ""
    color: Optional[str] = ""
    cost_price: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    stock: int = Field(ge=0)

class FrameInventoryCreate(FrameInventoryBase):
    pass

class FrameInventoryUpdate(BaseModel):
    brand: Optional[str] = None
    code: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    cost_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None

class FrameInventoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    brand: str
    code: str
    model: Optional[str] = ""
    color: Optional[str] = ""
    cost_price: float
    sale_price: float
    stock: int
    entry_date: str
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class FrameInventoryListResponse(BaseModel):
    data: List[FrameInventoryResponse]
    total: int

# Inventario de Lentes de Contacto
class ContactLensInventoryBase(BaseModel):
    lens_type: Literal["esferico", "torico", "multifocal", "cosmetico"]
    brand: Optional[str] = ""
    description: Optional[str] = ""
    cost_price: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    stock: int = Field(ge=0)

class ContactLensInventoryCreate(ContactLensInventoryBase):
    pass

class ContactLensInventoryUpdate(BaseModel):
    lens_type: Optional[Literal["esferico", "torico", "multifocal", "cosmetico"]] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    cost_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None

class ContactLensInventoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    lens_type: str
    brand: Optional[str] = ""
    description: Optional[str] = ""
    cost_price: float
    sale_price: float
    stock: int
    entry_date: str
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class ContactLensInventoryListResponse(BaseModel):
    data: List[ContactLensInventoryResponse]
    total: int

# Catálogo de Tipos de Lente
class LensTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""
    default_price: float = Field(ge=0)

class LensTypeCreate(LensTypeBase):
    pass

class LensTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_price: Optional[float] = None
    is_active: Optional[bool] = None

class LensTypeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: Optional[str] = ""
    default_price: float
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

class LensTypeListResponse(BaseModel):
    data: List[LensTypeResponse]
    total: int

# Detalle de venta (líneas de lentes)
class SaleLineItem(BaseModel):
    lens_type_id: str
    lens_type_name: Optional[str] = ""
    quantity: int = Field(ge=1, default=1)
    unit_price: float = Field(ge=0)
    subtotal: float = Field(ge=0)

# Venta de Óptica
class OpticaSaleBase(BaseModel):
    patient_id: str
    doctor_id: Optional[str] = None
    frame_id: Optional[str] = None
    contact_lens_id: Optional[str] = None
    lens_items: List[SaleLineItem] = []
    payment_method: Literal["efectivo", "tarjeta", "transferencia", "cheque", "mixto"]
    discount_percent: float = Field(ge=0, le=100, default=0)
    initial_payment: float = Field(ge=0, default=0)
    notes: Optional[str] = ""

class OpticaSaleCreate(OpticaSaleBase):
    pass

class OpticaSaleUpdate(BaseModel):
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None
    discount_percent: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[Literal["pendiente", "pagado", "cancelado"]] = None

class SalePaymentCreate(BaseModel):
    """Modelo para registrar abonos"""
    amount: float = Field(gt=0)
    payment_method: Literal["efectivo", "tarjeta", "transferencia", "cheque"]
    reference: Optional[str] = ""
    notes: Optional[str] = ""

class SalePaymentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    sale_id: str
    amount: float
    payment_method: str
    reference: Optional[str] = ""
    notes: Optional[str] = ""
    created_by: str
    created_by_name: Optional[str] = ""
    created_at: str

class OpticaSaleResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    order_number: str
    patient_id: str
    patient_name: Optional[str] = ""
    patient_phone: Optional[str] = ""
    doctor_id: Optional[str] = ""
    doctor_name: Optional[str] = ""
    frame_id: Optional[str] = ""
    frame_info: Optional[str] = ""
    frame_price: float = 0
    contact_lens_id: Optional[str] = ""
    contact_lens_info: Optional[str] = ""
    contact_lens_price: float = 0
    lens_items: List[SaleLineItem] = []
    lens_total: float = 0
    subtotal: float
    discount_percent: float
    discount_amount: float
    total: float
    total_paid: float
    balance_due: float
    payment_method: str
    status: str  # pendiente, pagado, cancelado
    payments: List[SalePaymentResponse] = []
    notes: Optional[str] = ""
    created_by: str
    created_by_name: Optional[str] = ""
    created_at: str
    updated_at: Optional[str] = None

class OpticaSaleListResponse(BaseModel):
    data: List[OpticaSaleResponse]
    total: int

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
    """Hash de contraseña con bcrypt (costo 12 para mayor seguridad)"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verificar contraseña hasheada"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validar fortaleza de contraseña"""
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    if not re.search(r'[A-Z]', password):
        return False, "La contraseña debe contener al menos una mayúscula"
    if not re.search(r'[a-z]', password):
        return False, "La contraseña debe contener al menos una minúscula"
    if not re.search(r'\d', password):
        return False, "La contraseña debe contener al menos un número"
    return True, "OK"

def create_token(user_id: str, username: str, role: str) -> str:
    """Crear token JWT con claims seguros"""
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4())  # JWT ID único para prevenir replay attacks
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def is_token_blacklisted(token: str) -> bool:
    """Verificar si un token está en la blacklist (persistente en MongoDB)"""
    blacklisted = await db.token_blacklist.find_one({"token": token})
    return blacklisted is not None

async def blacklist_token(token: str, user_id: str):
    """Agregar token a la blacklist con expiración automática"""
    try:
        # Decodificar para obtener la fecha de expiración
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        exp_timestamp = payload.get("exp")
        exp_date = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) if exp_timestamp else datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        await db.token_blacklist.insert_one({
            "token": token,
            "user_id": user_id,
            "blacklisted_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": exp_date.isoformat()
        })
    except Exception as e:
        logging.error(f"Error al agregar token a blacklist: {e}")

async def cleanup_expired_tokens():
    """Limpiar tokens expirados de la blacklist (ejecutar periódicamente)"""
    try:
        result = await db.token_blacklist.delete_many({
            "expires_at": {"$lt": datetime.now(timezone.utc).isoformat()}
        })
        if result.deleted_count > 0:
            logging.info(f"Limpiados {result.deleted_count} tokens expirados de blacklist")
    except Exception as e:
        logging.error(f"Error limpiando tokens expirados: {e}")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        
        # Check if token is blacklisted (persistente)
        if await is_token_blacklisted(token):
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

def require_role(role: str):
    """Requiere que el usuario tenga un rol específico"""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] != role:
            raise HTTPException(status_code=403, detail=f"Se requiere rol {role} para esta acción")
        return current_user
    return role_checker

# ==================== EXPENSE HELPERS ====================

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
    # Formatear el número con ceros a la izquierda (4 dígitos)
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
    """Create default users if they don't exist - CONTRASEÑAS MÁS SEGURAS"""
    # IMPORTANTE: Cambiar estas contraseñas en producción
    default_users = [
        {"username": "superadmin", "name": "Administrador General", "password": "Nova$2024Secure!", "role": "superadmin"},
        {"username": "admin", "name": "Administrador", "password": "Admin$2024Secure!", "role": "admin"},
        {"username": "usuario", "name": "Usuario NovaVision", "password": "User$2024Secure!", "role": "usuario"}
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
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "password_changed_at": None,  # Para forzar cambio de contraseña
                "failed_login_attempts": 0
            }
            await db.users.insert_one(user_doc)
            print(f"Created default user: {user_data['username']}")
            logging.info(f"⚠️ Usuario creado con contraseña por defecto: {user_data['username']}. Cambiar en producción.")


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


async def seed_optica_data():
    """Create optica user and sample data"""
    # Crear usuario de óptica si no existe
    existing_optica_user = await db.users.find_one({"username": "optica"})
    if not existing_optica_user:
        hashed_password = hash_password("optica2024")
        now = datetime.now(timezone.utc).isoformat()
        optica_user = {
            "id": str(uuid.uuid4()),
            "username": "optica",
            "password": hashed_password,
            "name": "Usuario Óptica",
            "role": "optica",
            "is_active": True,
            "created_at": now,
            "last_login": None
        }
        await db.users.insert_one(optica_user)
        print("Created optica user (username: optica, password: optica2024)")
    
    # Verificar si ya hay datos de óptica
    doctors_count = await db.doctors.count_documents({})
    if doctors_count > 0:
        print(f"Optica data already exists ({doctors_count} doctors), skipping sample data")
        return
    
    # Obtener el usuario que creó (superadmin o optica)
    admin = await db.users.find_one({"username": "superadmin"})
    if not admin:
        admin = await db.users.find_one({"username": "optica"})
    created_by = admin["id"] if admin else "system"
    now = datetime.now(timezone.utc).isoformat()
    
    # Crear médicos de ejemplo
    doctors = [
        {"name": "Dr. Carlos Méndez", "specialty": "Oftalmología General", "phone": "5555-1001", "license_number": "12345"},
        {"name": "Dra. María Fernández", "specialty": "Oftalmología Pediátrica", "phone": "5555-1002", "license_number": "12346"},
        {"name": "Dr. Roberto Sánchez", "specialty": "Cirugía Refractiva", "phone": "5555-1003", "license_number": "12347"},
        {"name": "Dra. Ana García", "specialty": "Retina y Vítreo", "phone": "5555-1004", "license_number": "12348"},
    ]
    
    for doc in doctors:
        doctor_doc = {
            "id": str(uuid.uuid4()),
            "name": doc["name"],
            "specialty": doc["specialty"],
            "phone": doc["phone"],
            "email": "",
            "license_number": doc["license_number"],
            "notes": "",
            "is_active": True,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        }
        await db.doctors.insert_one(doctor_doc)
    print(f"Created {len(doctors)} sample doctors")
    
    # Crear inventario de aros
    frames = [
        {"brand": "Ray-Ban", "code": "RB-001", "model": "Aviator Classic", "color": "Dorado", "cost_price": 350, "sale_price": 650, "stock": 10},
        {"brand": "Ray-Ban", "code": "RB-002", "model": "Wayfarer", "color": "Negro", "cost_price": 300, "sale_price": 550, "stock": 8},
        {"brand": "Oakley", "code": "OAK-001", "model": "Holbrook", "color": "Negro Mate", "cost_price": 400, "sale_price": 750, "stock": 5},
        {"brand": "Gucci", "code": "GUC-001", "model": "GG0061S", "color": "Carey", "cost_price": 800, "sale_price": 1500, "stock": 3},
        {"brand": "Tommy Hilfiger", "code": "TH-001", "model": "TH1557", "color": "Azul", "cost_price": 250, "sale_price": 450, "stock": 12},
        {"brand": "Generic", "code": "GEN-001", "model": "Básico", "color": "Negro", "cost_price": 50, "sale_price": 150, "stock": 25},
    ]
    
    for frame in frames:
        frame_doc = {
            "id": str(uuid.uuid4()),
            "brand": frame["brand"],
            "code": frame["code"],
            "model": frame["model"],
            "color": frame["color"],
            "cost_price": frame["cost_price"],
            "sale_price": frame["sale_price"],
            "stock": frame["stock"],
            "entry_date": now[:10],
            "is_active": True,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        }
        await db.optica_frames.insert_one(frame_doc)
    print(f"Created {len(frames)} sample frames")
    
    # Crear inventario de lentes de contacto
    contact_lenses = [
        {"lens_type": "esferico", "brand": "Acuvue", "description": "Oasys diario", "cost_price": 150, "sale_price": 300, "stock": 20},
        {"lens_type": "torico", "brand": "Biofinity", "description": "Toric mensual", "cost_price": 200, "sale_price": 400, "stock": 15},
        {"lens_type": "multifocal", "brand": "Air Optix", "description": "Multifocal mensual", "cost_price": 250, "sale_price": 500, "stock": 10},
        {"lens_type": "cosmetico", "brand": "FreshLook", "description": "Colors mensual", "cost_price": 100, "sale_price": 250, "stock": 30},
    ]
    
    for lens in contact_lenses:
        lens_doc = {
            "id": str(uuid.uuid4()),
            "lens_type": lens["lens_type"],
            "brand": lens["brand"],
            "description": lens["description"],
            "cost_price": lens["cost_price"],
            "sale_price": lens["sale_price"],
            "stock": lens["stock"],
            "entry_date": now[:10],
            "is_active": True,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        }
        await db.optica_contact_lenses.insert_one(lens_doc)
    print(f"Created {len(contact_lenses)} sample contact lenses")
    
    # Crear catálogo de tipos de lente
    lens_types = [
        {"name": "Lente Monofocal", "description": "Lente de una sola graduación", "default_price": 200},
        {"name": "Lente Bifocal", "description": "Lente con dos graduaciones", "default_price": 350},
        {"name": "Lente Progresivo", "description": "Lente multifocal sin línea visible", "default_price": 600},
        {"name": "Filtro Azul", "description": "Protección contra luz azul de pantallas", "default_price": 150},
        {"name": "Antirreflejo", "description": "Tratamiento antirreflejo", "default_price": 100},
        {"name": "Fotocromático", "description": "Lente que se oscurece con el sol", "default_price": 250},
        {"name": "Polarizado", "description": "Lente polarizado para sol", "default_price": 200},
    ]
    
    for lt in lens_types:
        lens_type_doc = {
            "id": str(uuid.uuid4()),
            "name": lt["name"],
            "description": lt["description"],
            "default_price": lt["default_price"],
            "is_active": True,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        }
        await db.optica_lens_types.insert_one(lens_type_doc)
    print(f"Created {len(lens_types)} sample lens types")
    
    print("Optica sample data created successfully")


async def seed_surgeries_data():
    """Crear datos de ejemplo para el módulo de Sala de Operaciones"""
    surgeries_count = await db.surgeries.count_documents({})
    if surgeries_count > 0:
        print(f"Surgeries data already exists ({surgeries_count} surgeries), skipping")
        return
    
    admin = await db.users.find_one({"username": "superadmin"})
    created_by = admin["id"] if admin else "system"
    now = datetime.now(timezone.utc).isoformat()
    
    surgeries = [
        {
            "id": str(uuid.uuid4()),
            "date": "2026-04-07",
            "time": "08:00",
            "patient_name": "María Elena López García",
            "procedure": "Facoemulsificación + LIO",
            "surgeon": "Dr. Roberto Méndez",
            "eye": "OD",
            "anesthesia_type": "local",
            "anesthesiologist": "Dr. Carlos Ruiz",
            "institution": "IGSS",
            "igss_data": {
                "unit": "Consulta Externa Z.9",
                "sps": "2345678",
                "affiliation_number": "A-998877",
                "code": "OFT-001",
                "procedure_cost": 3500
            },
            "observations": "Paciente con catarata madura. Sin antecedentes relevantes.",
            "equipment": [
                {"id": str(uuid.uuid4()), "name": "Facoemulsificador Centurion", "quantity": 1, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "Microscopio Zeiss Lumera 700", "quantity": 1, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "Set instrumental cataratas", "quantity": 1, "notes": "", "added_at": now, "added_by": created_by}
            ],
            "supplies": [
                {"id": str(uuid.uuid4()), "name": "Lente AcrySof IQ", "category": "lente", "quantity": 1, "unit_cost": 2800, "total_cost": 2800, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "Viscoelástico Healon", "category": "viscoelastico", "quantity": 1, "unit_cost": 450, "total_cost": 450, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "Cuchillete 2.75mm", "category": "material", "quantity": 1, "unit_cost": 180, "total_cost": 180, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "BSS 500ml", "category": "medicamento", "quantity": 1, "unit_cost": 120, "total_cost": 120, "notes": "", "added_at": now, "added_by": created_by}
            ],
            "status": "activo",
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        },
        {
            "id": str(uuid.uuid4()),
            "date": "2026-04-07",
            "time": "09:30",
            "patient_name": "José Antonio Ramírez",
            "procedure": "Vitrectomía",
            "surgeon": "Dr. Roberto Méndez",
            "eye": "OI",
            "anesthesia_type": "retrobulbar",
            "anesthesiologist": "Dr. Carlos Ruiz",
            "institution": "Privado",
            "igss_data": None,
            "observations": "Hemorragia vítrea. Diabético tipo 2 controlado.",
            "equipment": [
                {"id": str(uuid.uuid4()), "name": "Vitrectomo Constellation", "quantity": 1, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "Microscopio Zeiss Lumera 700", "quantity": 1, "notes": "", "added_at": now, "added_by": created_by}
            ],
            "supplies": [
                {"id": str(uuid.uuid4()), "name": "Aceite de silicón", "category": "material", "quantity": 1, "unit_cost": 3200, "total_cost": 3200, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "Triamcinolona", "category": "medicamento", "quantity": 1, "unit_cost": 280, "total_cost": 280, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "Cánula de hidrodisección", "category": "descartable", "quantity": 1, "unit_cost": 95, "total_cost": 95, "notes": "", "added_at": now, "added_by": created_by}
            ],
            "status": "activo",
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        },
        {
            "id": str(uuid.uuid4()),
            "date": "2026-04-07",
            "time": "11:00",
            "patient_name": "Ana Lucía Morales",
            "procedure": "Pterigión",
            "surgeon": "Dra. Patricia Solares",
            "eye": "OD",
            "anesthesia_type": "topica",
            "anesthesiologist": "Dr. Luis Hernández",
            "institution": "IGSS",
            "igss_data": {
                "unit": "Periférica Z.11",
                "sps": "8876543",
                "affiliation_number": "A-554433",
                "code": "OFT-015",
                "procedure_cost": 1800
            },
            "observations": "Pterigión nasal grado II. Recidiva de cirugía previa.",
            "equipment": [
                {"id": str(uuid.uuid4()), "name": "Microscopio Leica M822", "quantity": 1, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "Set instrumental córnea", "quantity": 1, "notes": "", "added_at": now, "added_by": created_by}
            ],
            "supplies": [
                {"id": str(uuid.uuid4()), "name": "Mitomicina C", "category": "medicamento", "quantity": 1, "unit_cost": 220, "total_cost": 220, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "Sutura nylon 10-0", "category": "sutura", "quantity": 2, "unit_cost": 120, "total_cost": 240, "notes": "", "added_at": now, "added_by": created_by},
                {"id": str(uuid.uuid4()), "name": "Esponjas Weck-Cel", "category": "descartable", "quantity": 4, "unit_cost": 25, "total_cost": 100, "notes": "", "added_at": now, "added_by": created_by}
            ],
            "status": "activo",
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        },
        {
            "id": str(uuid.uuid4()),
            "date": "2026-04-06",
            "time": "14:00",
            "patient_name": "Carlos Eduardo Pérez",
            "procedure": "Capsulotomía YAG",
            "surgeon": "Dra. Patricia Solares",
            "eye": "OI",
            "anesthesia_type": "topica",
            "anesthesiologist": "Dr. Luis Hernández",
            "institution": "Privado",
            "igss_data": None,
            "observations": "Opacidad de cápsula posterior. Procedimiento ambulatorio.",
            "equipment": [
                {"id": str(uuid.uuid4()), "name": "Láser YAG", "quantity": 1, "notes": "", "added_at": now, "added_by": created_by}
            ],
            "supplies": [],
            "status": "activo",
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        }
    ]
    
    for surgery in surgeries:
        await db.surgeries.insert_one(surgery)
    
    print(f"Created {len(surgeries)} sample surgeries")


async def seed_catalogos_oftalmologicos():
    """Seed de catálogos oftalmológicos y evaluación de ejemplo"""
    # Verificar si ya existen datos
    medicamentos_count = await db.catalogo_medicamentos.count_documents({})
    if medicamentos_count > 0:
        print(f"Catálogos oftalmológicos ya existen ({medicamentos_count} medicamentos), saltando seed")
        return
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Catálogo de medicamentos oftalmológicos comunes
    medicamentos = [
        "Prednisolona 1% gotas", "Moxifloxacino 0.5% gotas", "Tobramicina/Dexametasona gotas",
        "Tropicamida 1% gotas", "Fenilefrina 2.5% gotas", "Ciclopentolato 1% gotas",
        "Dorzolamida/Timolol gotas", "Latanoprost 0.005% gotas", "Brimonidina 0.2% gotas",
        "Lubricante ocular (carboximetilcelulosa)", "Lubricante ocular (hialuronato)",
        "Ketorolaco 0.5% gotas", "Nepafenaco 0.1% gotas", "Ofloxacino 0.3% gotas",
        "Eritromicina ungüento oftálmico", "Ganciclovir gel oftálmico",
        "Acetazolamida 250mg tabletas", "Manitol 20% IV", "Prednisona 50mg tabletas",
        "Vitamina A 50,000 UI cápsulas", "Omega 3 cápsulas"
    ]
    
    for med in medicamentos:
        try:
            await db.catalogo_medicamentos.insert_one({
                "id": str(uuid.uuid4()),
                "nombre": med,
                "usos": 5,
                "fecha_creacion": now
            })
        except:
            pass  # Duplicado
    
    # Catálogo de estudios oftalmológicos
    estudios = [
        "OCT de mácula", "OCT de nervio óptico", "OCT de segmento anterior",
        "Campimetría computarizada", "Topografía corneal", "Paquimetría",
        "Biometría óptica (IOL Master)", "Ecografía modo B", "Ecografía UBM",
        "Angiografía con fluoresceína", "Angiografía con indocianina verde",
        "Electrorretinograma (ERG)", "Potenciales visuales evocados (PVE)",
        "Fotografía de fondo de ojo", "Aberrometría", "Microscopía especular",
        "Test de Schirmer", "Test de Rosa de Bengala", "Meibografía",
        "Gonioscopia", "Tonometría de aplanación", "Curva tonométrica diaria"
    ]
    
    for est in estudios:
        try:
            await db.catalogo_estudios.insert_one({
                "id": str(uuid.uuid4()),
                "nombre": est,
                "usos": 3,
                "fecha_creacion": now
            })
        except:
            pass
    
    # Catálogo de diagnósticos oftalmológicos comunes
    diagnosticos = [
        "Catarata senil nuclear", "Catarata cortical", "Catarata subcapsular posterior",
        "Glaucoma primario de ángulo abierto", "Glaucoma de ángulo cerrado", "Hipertensión ocular",
        "Retinopatía diabética no proliferativa", "Retinopatía diabética proliferativa",
        "Edema macular diabético", "Degeneración macular relacionada con la edad (seca)",
        "Degeneración macular relacionada con la edad (húmeda)",
        "Pterigión", "Pinguécula", "Queratocono", "Queratitis bacteriana",
        "Conjuntivitis alérgica", "Conjuntivitis viral", "Blefaritis",
        "Ojo seco (síndrome de disfunción lagrimal)", "Uveítis anterior",
        "Desprendimiento de vítreo posterior", "Miodesopsias",
        "Miopía", "Hipermetropía", "Astigmatismo", "Presbicia",
        "Oclusión de vena retiniana", "Oclusión de arteria retiniana",
        "Neuropatía óptica isquémica", "Papiledema"
    ]
    
    for diag in diagnosticos:
        try:
            await db.catalogo_diagnosticos.insert_one({
                "id": str(uuid.uuid4()),
                "nombre": diag,
                "usos": 2,
                "fecha_creacion": now
            })
        except:
            pass
    
    print(f"Catálogos oftalmológicos creados: {len(medicamentos)} medicamentos, {len(estudios)} estudios, {len(diagnosticos)} diagnósticos")
    
    # Crear evaluación de ejemplo si hay pacientes
    paciente = await db.patients.find_one({"is_active": True}, {"_id": 0})
    doctor = await db.doctors.find_one({"is_active": True}, {"_id": 0})
    superadmin = await db.users.find_one({"role": "superadmin"}, {"_id": 0})
    
    if paciente and superadmin:
        # Verificar si ya existe una evaluación
        eval_count = await db.evaluaciones_oftalmologicas.count_documents({})
        if eval_count == 0:
            edad = 0
            if paciente.get("birth_date"):
                try:
                    birth = datetime.strptime(paciente["birth_date"], "%Y-%m-%d")
                    today = datetime.now()
                    edad = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
                except:
                    pass
            
            # Evaluación de ejemplo completa
            evaluacion_ejemplo = {
                "id": str(uuid.uuid4()),
                "paciente_id": paciente["id"],
                "paciente_nombre": f"{paciente.get('first_name', '')} {paciente.get('last_name', '')}".strip(),
                "paciente_edad": edad,
                "paciente_sexo": paciente.get("gender", ""),
                "paciente_expediente": paciente.get("record_number", ""),
                "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "medico_id": doctor["id"] if doctor else "",
                "medico_nombre": doctor["name"] if doctor else "Dr. Ejemplo",
                "motivo_consulta": "Visión borrosa progresiva de 6 meses de evolución",
                "padecimiento_actual": "Paciente refiere disminución gradual de la agudeza visual en ambos ojos, más notoria en ojo derecho. Dificultad para conducir de noche. No refiere dolor, enrojecimiento ni secreción.",
                "antecedentes": {
                    "personales_patologicos": "Diabetes mellitus tipo 2 diagnosticada hace 10 años, en tratamiento con metformina. Hipertensión arterial controlada.",
                    "diabetes": True,
                    "hipertension": True,
                    "cardiopatia": False,
                    "enfermedad_tiroidea": False,
                    "otros_patologicos": False,
                    "oftalmologicos": "Uso de lentes desde los 45 años. Última refracción hace 3 años. No cirugías oculares previas. Antecedente de retinopatía diabética no proliferativa leve hace 2 años.",
                    "quirurgicos": "Colecistectomía laparoscópica 2018",
                    "alergias": "Penicilina",
                    "familiares": "Padre con glaucoma. Madre con diabetes y catarata.",
                    "habitos": "No fuma. Alcohol ocasional."
                },
                "medicamentos_actuales": [
                    {"nombre": "Metformina 850mg", "dosis": "850mg", "frecuencia": "Cada 12 horas", "via": "Oral", "desde": "2016"},
                    {"nombre": "Losartán 50mg", "dosis": "50mg", "frecuencia": "Cada 24 horas", "via": "Oral", "desde": "2018"},
                    {"nombre": "Lubricante ocular (carboximetilcelulosa)", "dosis": "1 gota", "frecuencia": "4 veces al día", "via": "Oftálmica", "desde": "2024"}
                ],
                "medicamentos_previos": [
                    {"nombre": "Ketorolaco 0.5% gotas", "dosis": "1 gota c/6h", "motivo": "Inflamación postoperatoria (cirugía previa)", "periodo": "2018, 1 mes"}
                ],
                "examen": {
                    "avsc_od": "20/80",
                    "avsc_oi": "20/50",
                    "avcc_od": "20/40",
                    "avcc_oi": "20/30",
                    "refraccion_od": {"esfera": "-1.50", "cilindro": "-0.75", "eje": "90", "adicion": "+2.50"},
                    "refraccion_oi": {"esfera": "-1.25", "cilindro": "-0.50", "eje": "85", "adicion": "+2.50"},
                    "queratometria_od": "43.50 x 44.25 @ 90",
                    "queratometria_oi": "43.25 x 44.00 @ 85",
                    "pio_od": "16",
                    "pio_oi": "15",
                    "pio_metodo": "Tonometría de aplanación (Goldmann)",
                    "segmento_anterior_od": {
                        "parpados_anexos": "Sin alteraciones",
                        "conjuntiva": "Sin hiperemia",
                        "cornea": "Transparente, sin opacidades",
                        "camara_anterior": "Formada, sin células ni flare",
                        "iris": "Sin sinequias",
                        "cristalino": "Opacidad nuclear 2+ y cortical 1+"
                    },
                    "segmento_anterior_oi": {
                        "parpados_anexos": "Sin alteraciones",
                        "conjuntiva": "Sin hiperemia",
                        "cornea": "Transparente",
                        "camara_anterior": "Formada, sin células",
                        "iris": "Normal",
                        "cristalino": "Opacidad nuclear 1+"
                    },
                    "vitreo_od": "Transparente, sin opacidades",
                    "vitreo_oi": "Transparente",
                    "fondo_ojo_od": {
                        "papila": "Bordes definidos, excavación 0.3, coloración normal",
                        "macula": "Reflejo foveal presente, sin edema",
                        "retina": "Aplicada, 2 microaneurismas temporales",
                        "vasos": "Relación A/V 2:3, sin cruces patológicos"
                    },
                    "fondo_ojo_oi": {
                        "papila": "Bordes definidos, excavación 0.3",
                        "macula": "Sin alteraciones",
                        "retina": "Aplicada, 1 microaneurisma",
                        "vasos": "Sin alteraciones"
                    },
                    "motilidad_ocular": "Versiones y ducciones completas. Sin restricciones.",
                    "pupilas_reflejos": "Isocóricas, reactivas a la luz. Sin defecto pupilar aferente."
                },
                "diagnosticos": [
                    {"descripcion": "Catarata senil nuclear", "codigo_cie10": "H25.1", "ojo": "OD"},
                    {"descripcion": "Catarata cortical", "codigo_cie10": "H25.0", "ojo": "OI"},
                    {"descripcion": "Retinopatía diabética no proliferativa", "codigo_cie10": "H36.0", "ojo": "AO"},
                    {"descripcion": "Presbicia", "codigo_cie10": "H52.4", "ojo": "AO"}
                ],
                "plan": "1. Se explica al paciente diagnóstico de catarata bilateral con predominio en OD, asociada a retinopatía diabética no proliferativa leve estable.\n2. Se recomienda cirugía de catarata en OD como primer tiempo.\n3. Control metabólico estricto previo a cirugía (HbA1c < 7%).\n4. Estudios preoperatorios.\n5. Seguimiento de retinopatía diabética cada 6 meses.",
                "recomendaciones": {
                    "estudios_a_realizar": [
                        {"estudio": "Biometría óptica (IOL Master)", "ojo": "AO", "indicaciones": "Para cálculo de lente intraocular"},
                        {"estudio": "OCT de mácula", "ojo": "AO", "indicaciones": "Descartar edema macular diabético subclínico"},
                        {"estudio": "Topografía corneal", "ojo": "AO", "indicaciones": "Evaluación prequirúrgica"}
                    ],
                    "recomendaciones_generales": "Mantener control glucémico estricto. Evitar frotarse los ojos. Usar lubricante ocular. Acudir a cita de control en 1 mes con resultados de estudios."
                },
                "procedimientos": [],
                "recetas": {
                    "medicamentos": {
                        "items": [
                            {"medicamento": "Lubricante ocular (hialuronato)", "presentacion": "Frasco 10ml", "dosis": "1 gota", "frecuencia": "4 veces al día", "duracion": "Uso continuo", "via": "Oftálmica", "indicaciones": "Aplicar en ambos ojos"},
                            {"medicamento": "Vitamina A 50,000 UI cápsulas", "presentacion": "Caja 30 cápsulas", "dosis": "1 cápsula", "frecuencia": "Cada semana", "duracion": "3 meses", "via": "Oral", "indicaciones": "Tomar con alimentos"}
                        ]
                    },
                    "anteojos": {
                        "od": {"esfera": "-1.50", "cilindro": "-0.75", "eje": "90", "adicion": "+2.50"},
                        "oi": {"esfera": "-1.25", "cilindro": "-0.50", "eje": "85", "adicion": "+2.50"},
                        "distancia_pupilar": "62mm",
                        "tipo_lente": "Progresivo",
                        "material": "Policarbonato",
                        "tratamientos": "Antirreflejo, filtro azul",
                        "uso": "Permanente",
                        "observaciones": "Lentes progresivos para visión lejana y cercana. Se recomienda adaptación gradual."
                    },
                    "lentes_contacto": {
                        "od": {"poder": "", "curva_base": "", "diametro": ""},
                        "oi": {"poder": "", "curva_base": "", "diametro": ""},
                        "marca": "",
                        "tipo": "",
                        "regimen_reemplazo": "",
                        "observaciones": "No se indica uso de lentes de contacto por presencia de catarata y antecedente de ojo seco."
                    }
                },
                "creado_por": superadmin["id"],
                "creado_por_nombre": superadmin.get("name", "Super Admin"),
                "fecha_creacion": now,
                "actualizado_por": superadmin["id"],
                "actualizado_por_nombre": superadmin.get("name", "Super Admin"),
                "fecha_actualizacion": now,
                "sellado": False,
                "fecha_sellado": None,
                "ultimo_autoguardado": now
            }
            
            await db.evaluaciones_oftalmologicas.insert_one(evaluacion_ejemplo)
            print("Evaluación oftalmológica de ejemplo creada")
            
            # Crear una evaluación sellada de ejemplo (más de 24h)
            eval_sellada = {
                "id": str(uuid.uuid4()),
                "paciente_id": paciente["id"],
                "paciente_nombre": f"{paciente.get('first_name', '')} {paciente.get('last_name', '')}".strip(),
                "paciente_edad": edad,
                "paciente_sexo": paciente.get("gender", ""),
                "paciente_expediente": paciente.get("record_number", ""),
                "fecha": (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d"),
                "medico_id": doctor["id"] if doctor else "",
                "medico_nombre": doctor["name"] if doctor else "Dr. Ejemplo",
                "motivo_consulta": "Control de glaucoma",
                "padecimiento_actual": "Paciente en seguimiento por glaucoma primario de ángulo abierto. Usa tratamiento tópico con buena tolerancia.",
                "antecedentes": {
                    "personales_patologicos": "",
                    "diabetes": False,
                    "hipertension": True,
                    "cardiopatia": False,
                    "enfermedad_tiroidea": False,
                    "otros_patologicos": False,
                    "oftalmologicos": "Glaucoma diagnosticado hace 5 años",
                    "quirurgicos": "",
                    "alergias": "Ninguna conocida",
                    "familiares": "Madre con glaucoma",
                    "habitos": ""
                },
                "medicamentos_actuales": [
                    {"nombre": "Dorzolamida/Timolol gotas", "dosis": "1 gota", "frecuencia": "Cada 12 horas", "via": "Oftálmica", "desde": "2021"}
                ],
                "medicamentos_previos": [],
                "examen": {
                    "avsc_od": "20/25", "avsc_oi": "20/25",
                    "avcc_od": "20/20", "avcc_oi": "20/20",
                    "refraccion_od": {"esfera": "-0.50", "cilindro": "", "eje": "", "adicion": ""},
                    "refraccion_oi": {"esfera": "-0.50", "cilindro": "", "eje": "", "adicion": ""},
                    "queratometria_od": "", "queratometria_oi": "",
                    "pio_od": "14", "pio_oi": "15", "pio_metodo": "Goldmann",
                    "segmento_anterior_od": {"parpados_anexos": "Normal", "conjuntiva": "Normal", "cornea": "Clara", "camara_anterior": "Profunda", "iris": "Normal", "cristalino": "Transparente"},
                    "segmento_anterior_oi": {"parpados_anexos": "Normal", "conjuntiva": "Normal", "cornea": "Clara", "camara_anterior": "Profunda", "iris": "Normal", "cristalino": "Transparente"},
                    "vitreo_od": "Normal", "vitreo_oi": "Normal",
                    "fondo_ojo_od": {"papila": "Excavación 0.6, palidez temporal", "macula": "Normal", "retina": "Aplicada", "vasos": "Normales"},
                    "fondo_ojo_oi": {"papila": "Excavación 0.5", "macula": "Normal", "retina": "Aplicada", "vasos": "Normales"},
                    "motilidad_ocular": "Normal", "pupilas_reflejos": "Normales"
                },
                "diagnosticos": [
                    {"descripcion": "Glaucoma primario de ángulo abierto", "codigo_cie10": "H40.1", "ojo": "AO"}
                ],
                "plan": "Continuar tratamiento actual. Control en 4 meses con campimetría.",
                "recomendaciones": {
                    "estudios_a_realizar": [
                        {"estudio": "Campimetría computarizada", "ojo": "AO", "indicaciones": "Control de progresión"}
                    ],
                    "recomendaciones_generales": "No suspender tratamiento. Acudir a urgencias si presenta dolor ocular o visión borrosa súbita."
                },
                "procedimientos": [],
                "recetas": {
                    "medicamentos": {"items": []},
                    "anteojos": {"od": {}, "oi": {}, "distancia_pupilar": "", "tipo_lente": "", "material": "", "tratamientos": "", "uso": "", "observaciones": ""},
                    "lentes_contacto": {"od": {}, "oi": {}, "marca": "", "tipo": "", "regimen_reemplazo": "", "observaciones": ""}
                },
                "creado_por": superadmin["id"],
                "creado_por_nombre": superadmin.get("name", "Super Admin"),
                "fecha_creacion": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
                "actualizado_por": superadmin["id"],
                "actualizado_por_nombre": superadmin.get("name", "Super Admin"),
                "fecha_actualizacion": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
                "sellado": True,
                "fecha_sellado": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                "ultimo_autoguardado": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
            }
            
            await db.evaluaciones_oftalmologicas.insert_one(eval_sellada)
            print("Evaluación sellada de ejemplo creada")


# ==================== AUTH ROUTES ====================

@api_router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin):
    """Login endpoint with rate limiting (5 attempts per minute) y audit logging"""
    client_ip = request.client.host if request.client else "unknown"
    
    user = await db.users.find_one({"username": credentials.username.lower().strip()})
    if not user or not verify_password(credentials.password, user["password"]):
        # Log intento fallido
        await audit.log(
            action="LOGIN_FAILED",
            user_id="unknown",
            user_name=credentials.username,
            details={"reason": "Credenciales inválidas"},
            ip_address=client_ip
        )
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    if not user.get("is_active", True):
        await audit.log(
            action="LOGIN_FAILED",
            user_id=user["id"],
            user_name=user["username"],
            details={"reason": "Usuario desactivado"},
            ip_address=client_ip
        )
        raise HTTPException(status_code=401, detail="Usuario desactivado")
    
    # Update last login
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    token = create_token(user["id"], user["username"], user["role"])
    
    # Log login exitoso
    await audit.log(
        action="LOGIN_SUCCESS",
        user_id=user["id"],
        user_name=user["username"],
        details={"role": user["role"]},
        ip_address=client_ip
    )
    
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
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """Invalidar el token actual (persistente en MongoDB)"""
    token = current_user.get("_token")
    client_ip = request.client.host if request.client else "unknown"
    
    if token:
        await blacklist_token(token, current_user["id"])
        
        # Log logout
        await audit.log(
            action="LOGOUT",
            user_id=current_user["id"],
            user_name=current_user.get("username", "unknown"),
            ip_address=client_ip
        )
    
    return {"message": "Sesión cerrada correctamente"}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**{k: v for k, v in current_user.items() if k != "_token"})


# ==================== SECURITY & AUDIT ROUTES ====================

class AuditLogResponse(BaseModel):
    id: str
    timestamp: str
    action: str
    user_id: str
    user_name: str
    ip_address: Optional[str] = None
    details: dict = {}

class AuditLogListResponse(BaseModel):
    data: List[AuditLogResponse]
    total: int
    page: int
    total_pages: int


@api_router.get("/security/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Obtener logs de auditoría con paginación (solo superadmin)"""
    query = {}
    
    if action and action != "all":
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    if date_from:
        query["timestamp"] = {"$gte": date_from}
    if date_to:
        if "timestamp" in query:
            query["timestamp"]["$lte"] = date_to + "T23:59:59"
        else:
            query["timestamp"] = {"$lte": date_to + "T23:59:59"}
    if search:
        query["$or"] = [
            {"user_name": {"$regex": search, "$options": "i"}},
            {"action": {"$regex": search, "$options": "i"}},
            {"ip_address": {"$regex": search, "$options": "i"}}
        ]
    
    # Total count
    total = await db.audit_logs.count_documents(query)
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    # Paginated results
    skip = (page - 1) * limit
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "data": logs,
        "total": total,
        "page": page,
        "total_pages": total_pages
    }


@api_router.get("/security/audit-actions")
async def get_audit_actions(current_user: dict = Depends(require_role("superadmin"))):
    """Obtener lista de acciones únicas para filtros"""
    actions = await db.audit_logs.distinct("action")
    return {"actions": sorted(actions)}

@api_router.get("/security/status")
async def get_security_status(current_user: dict = Depends(require_role("superadmin"))):
    """Estado de seguridad del sistema (solo superadmin)"""
    # Contar tokens blacklisteados
    blacklisted_count = await db.token_blacklist.count_documents({})
    
    # Contar intentos de login fallidos recientes (últimas 24h)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    failed_logins = await db.audit_logs.count_documents({
        "action": "LOGIN_FAILED",
        "timestamp": {"$gte": yesterday}
    })
    
    # Usuarios activos
    active_users = await db.users.count_documents({"is_active": True})
    
    return {
        "cors_origins": ALLOWED_ORIGINS,
        "jwt_expiration_hours": JWT_EXPIRATION_HOURS,
        "blacklisted_tokens": blacklisted_count,
        "failed_logins_24h": failed_logins,
        "active_users": active_users,
        "security_headers_enabled": True,
        "rate_limiting_enabled": True,
        "audit_logging_enabled": True
    }

@api_router.post("/security/change-password")
async def change_password(
    request: Request,
    current_password: str = Body(...),
    new_password: str = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Cambiar contraseña del usuario actual"""
    client_ip = request.client.host if request.client else "unknown"
    
    # Verificar contraseña actual
    user = await db.users.find_one({"id": current_user["id"]})
    if not user or not verify_password(current_password, user["password"]):
        await audit.log(
            action="PASSWORD_CHANGE_FAILED",
            user_id=current_user["id"],
            user_name=current_user.get("username", "unknown"),
            details={"reason": "Contraseña actual incorrecta"},
            ip_address=client_ip
        )
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    
    # Validar nueva contraseña
    is_valid, message = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    # Actualizar contraseña
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "password": hash_password(new_password),
            "password_changed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Log cambio de contraseña
    await audit.log(
        action="PASSWORD_CHANGED",
        user_id=current_user["id"],
        user_name=current_user.get("username", "unknown"),
        ip_address=client_ip
    )
    
    return {"message": "Contraseña actualizada correctamente"}


# ==================== EVALUACIÓN OFTALMOLÓGICA - MODELS & ROUTES ====================

from models.evaluacion_oftalmologica import (
    EvaluacionOftalmologicaCreate,
    EvaluacionOftalmologicaUpdate,
    EvaluacionOftalmologicaResponse,
    EvaluacionOftalmologicaListResponse,
    CatalogoItemResponse
)

# Tiempo límite para sellado (24 horas)
SELLADO_HORAS = 24


def calcular_edad(fecha_nacimiento: str) -> int:
    """Calcula la edad a partir de fecha de nacimiento"""
    try:
        birth = datetime.strptime(fecha_nacimiento, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return age
    except:
        return 0


def verificar_sellado(evaluacion: dict) -> tuple[bool, str]:
    """Verifica si una evaluación debe estar sellada"""
    if evaluacion.get("sellado", False):
        return True, "Expediente sellado"
    
    fecha_creacion = evaluacion.get("fecha_creacion", "")
    if fecha_creacion:
        try:
            creacion = datetime.fromisoformat(fecha_creacion.replace("Z", "+00:00"))
            ahora = datetime.now(timezone.utc)
            if (ahora - creacion).total_seconds() > SELLADO_HORAS * 3600:
                return True, "Expediente sellado por tiempo (24h)"
        except:
            pass
    return False, ""


async def actualizar_catalogo(coleccion: str, nombre: str):
    """Actualiza o inserta un item en el catálogo"""
    if not nombre or not nombre.strip():
        return
    
    nombre_normalizado = nombre.strip()
    existente = await db[coleccion].find_one(
        {"nombre": {"$regex": f"^{re.escape(nombre_normalizado)}$", "$options": "i"}}
    )
    
    if existente:
        await db[coleccion].update_one(
            {"id": existente["id"]},
            {"$inc": {"usos": 1}}
        )
    else:
        await db[coleccion].insert_one({
            "id": str(uuid.uuid4()),
            "nombre": nombre_normalizado,
            "usos": 1,
            "fecha_creacion": datetime.now(timezone.utc).isoformat()
        })


async def procesar_catalogos_evaluacion(evaluacion_data: dict):
    """Procesa y actualiza los catálogos con datos de la evaluación"""
    # Medicamentos actuales
    for med in evaluacion_data.get("medicamentos_actuales", []):
        if med.get("nombre"):
            await actualizar_catalogo("catalogo_medicamentos", med["nombre"])
    
    # Medicamentos previos
    for med in evaluacion_data.get("medicamentos_previos", []):
        if med.get("nombre"):
            await actualizar_catalogo("catalogo_medicamentos", med["nombre"])
    
    # Diagnósticos
    for diag in evaluacion_data.get("diagnosticos", []):
        if diag.get("descripcion"):
            await actualizar_catalogo("catalogo_diagnosticos", diag["descripcion"])
    
    # Estudios
    recomendaciones = evaluacion_data.get("recomendaciones", {})
    for estudio in recomendaciones.get("estudios_a_realizar", []):
        if estudio.get("estudio"):
            await actualizar_catalogo("catalogo_estudios", estudio["estudio"])
    
    # Medicamentos de receta
    recetas = evaluacion_data.get("recetas", {})
    medicamentos_receta = recetas.get("medicamentos", {})
    for item in medicamentos_receta.get("items", []):
        if item.get("medicamento"):
            await actualizar_catalogo("catalogo_medicamentos", item["medicamento"])


# --- Catálogos Endpoints ---

@api_router.get("/catalogos/medicamentos")
async def get_catalogo_medicamentos(
    search: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Autocomplete de medicamentos"""
    query = {}
    if search:
        query["nombre"] = {"$regex": re.escape(search), "$options": "i"}
    
    items = await db.catalogo_medicamentos.find(query, {"_id": 0}).sort("usos", -1).limit(limit).to_list(limit)
    return items


@api_router.get("/catalogos/estudios")
async def get_catalogo_estudios(
    search: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Autocomplete de estudios"""
    query = {}
    if search:
        query["nombre"] = {"$regex": re.escape(search), "$options": "i"}
    
    items = await db.catalogo_estudios.find(query, {"_id": 0}).sort("usos", -1).limit(limit).to_list(limit)
    return items


@api_router.get("/catalogos/diagnosticos")
async def get_catalogo_diagnosticos(
    search: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Autocomplete de diagnósticos"""
    query = {}
    if search:
        query["nombre"] = {"$regex": re.escape(search), "$options": "i"}
    
    items = await db.catalogo_diagnosticos.find(query, {"_id": 0}).sort("usos", -1).limit(limit).to_list(limit)
    return items


# --- Evaluaciones Endpoints ---

@api_router.get("/evaluaciones", response_model=EvaluacionOftalmologicaListResponse)
async def get_evaluaciones(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    paciente_id: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Listar evaluaciones oftalmológicas"""
    query = {}
    
    if paciente_id:
        query["paciente_id"] = paciente_id
    if fecha_desde:
        query["fecha"] = {"$gte": fecha_desde}
    if fecha_hasta:
        if "fecha" in query:
            query["fecha"]["$lte"] = fecha_hasta
        else:
            query["fecha"] = {"$lte": fecha_hasta}
    if search:
        query["$or"] = [
            {"paciente_nombre": {"$regex": search, "$options": "i"}},
            {"paciente_expediente": {"$regex": search, "$options": "i"}},
            {"motivo_consulta": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.evaluaciones_oftalmologicas.count_documents(query)
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    skip = (page - 1) * limit
    
    evaluaciones = await db.evaluaciones_oftalmologicas.find(query, {"_id": 0}).sort("fecha_creacion", -1).skip(skip).limit(limit).to_list(limit)
    
    # Verificar y actualizar sellado para cada evaluación
    for eval in evaluaciones:
        debe_sellar, _ = verificar_sellado(eval)
        if debe_sellar and not eval.get("sellado"):
            await db.evaluaciones_oftalmologicas.update_one(
                {"id": eval["id"]},
                {"$set": {"sellado": True, "fecha_sellado": datetime.now(timezone.utc).isoformat()}}
            )
            eval["sellado"] = True
            eval["fecha_sellado"] = datetime.now(timezone.utc).isoformat()
    
    return {
        "data": evaluaciones,
        "total": total,
        "page": page,
        "total_pages": total_pages
    }


@api_router.get("/evaluaciones/{evaluacion_id}", response_model=EvaluacionOftalmologicaResponse)
async def get_evaluacion(
    evaluacion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener una evaluación por ID"""
    evaluacion = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # Verificar y actualizar sellado
    debe_sellar, _ = verificar_sellado(evaluacion)
    if debe_sellar and not evaluacion.get("sellado"):
        await db.evaluaciones_oftalmologicas.update_one(
            {"id": evaluacion_id},
            {"$set": {"sellado": True, "fecha_sellado": datetime.now(timezone.utc).isoformat()}}
        )
        evaluacion["sellado"] = True
        evaluacion["fecha_sellado"] = datetime.now(timezone.utc).isoformat()
    
    return evaluacion


@api_router.post("/evaluaciones", response_model=EvaluacionOftalmologicaResponse)
async def create_evaluacion(
    evaluacion: EvaluacionOftalmologicaCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nueva evaluación (solo Admin y SuperAdmin)"""
    if current_user["role"] not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear evaluaciones")
    
    # Obtener datos del paciente si existe
    paciente = await db.patients.find_one({"id": evaluacion.paciente_id}, {"_id": 0})
    
    now = datetime.now(timezone.utc).isoformat()
    evaluacion_dict = evaluacion.model_dump()
    
    # Enriquecer con datos del paciente
    if paciente:
        evaluacion_dict["paciente_nombre"] = f"{paciente.get('first_name', '')} {paciente.get('last_name', '')}".strip()
        evaluacion_dict["paciente_expediente"] = paciente.get("record_number", "")
        evaluacion_dict["paciente_sexo"] = paciente.get("gender", "")
        if paciente.get("birth_date"):
            evaluacion_dict["paciente_edad"] = calcular_edad(paciente["birth_date"])
    
    evaluacion_dict["id"] = str(uuid.uuid4())
    evaluacion_dict["creado_por"] = current_user["id"]
    evaluacion_dict["creado_por_nombre"] = current_user.get("name", current_user.get("username", ""))
    evaluacion_dict["fecha_creacion"] = now
    evaluacion_dict["actualizado_por"] = current_user["id"]
    evaluacion_dict["actualizado_por_nombre"] = current_user.get("name", current_user.get("username", ""))
    evaluacion_dict["fecha_actualizacion"] = now
    evaluacion_dict["sellado"] = False
    evaluacion_dict["fecha_sellado"] = None
    evaluacion_dict["ultimo_autoguardado"] = now
    
    if not evaluacion_dict.get("fecha"):
        evaluacion_dict["fecha"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    await db.evaluaciones_oftalmologicas.insert_one(evaluacion_dict)
    
    # Procesar catálogos
    await procesar_catalogos_evaluacion(evaluacion_dict)
    
    # Audit log
    await audit.log(
        action="EVALUACION_CREATED",
        user_id=current_user["id"],
        user_name=current_user.get("username", "unknown"),
        details={"evaluacion_id": evaluacion_dict["id"], "paciente": evaluacion_dict.get("paciente_nombre")}
    )
    
    if "_id" in evaluacion_dict:
        del evaluacion_dict["_id"]
    return evaluacion_dict


@api_router.put("/evaluaciones/{evaluacion_id}", response_model=EvaluacionOftalmologicaResponse)
async def update_evaluacion(
    evaluacion_id: str,
    evaluacion: EvaluacionOftalmologicaUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar evaluación (solo Admin y SuperAdmin, solo si no está sellada)"""
    if current_user["role"] not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para editar evaluaciones")
    
    existing = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # Verificar sellado
    debe_sellar, mensaje = verificar_sellado(existing)
    if debe_sellar:
        if not existing.get("sellado"):
            await db.evaluaciones_oftalmologicas.update_one(
                {"id": evaluacion_id},
                {"$set": {"sellado": True, "fecha_sellado": datetime.now(timezone.utc).isoformat()}}
            )
        raise HTTPException(status_code=423, detail=f"Expediente sellado. {mensaje}")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = evaluacion.model_dump(exclude_unset=True)
    
    # Si se actualiza paciente_id, enriquecer datos
    if "paciente_id" in update_data:
        paciente = await db.patients.find_one({"id": update_data["paciente_id"]}, {"_id": 0})
        if paciente:
            update_data["paciente_nombre"] = f"{paciente.get('first_name', '')} {paciente.get('last_name', '')}".strip()
            update_data["paciente_expediente"] = paciente.get("record_number", "")
            update_data["paciente_sexo"] = paciente.get("gender", "")
            if paciente.get("birth_date"):
                update_data["paciente_edad"] = calcular_edad(paciente["birth_date"])
    
    update_data["actualizado_por"] = current_user["id"]
    update_data["actualizado_por_nombre"] = current_user.get("name", current_user.get("username", ""))
    update_data["fecha_actualizacion"] = now
    
    await db.evaluaciones_oftalmologicas.update_one(
        {"id": evaluacion_id},
        {"$set": update_data}
    )
    
    # Procesar catálogos con datos actualizados
    merged_data = {**existing, **update_data}
    await procesar_catalogos_evaluacion(merged_data)
    
    updated = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    return updated


@api_router.patch("/evaluaciones/{evaluacion_id}/autoguardar", response_model=EvaluacionOftalmologicaResponse)
async def autoguardar_evaluacion(
    evaluacion_id: str,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Autoguardado parcial de evaluación (solo si no está sellada)"""
    if current_user["role"] not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para editar evaluaciones")
    
    existing = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # Verificar sellado
    debe_sellar, mensaje = verificar_sellado(existing)
    if debe_sellar:
        if not existing.get("sellado"):
            await db.evaluaciones_oftalmologicas.update_one(
                {"id": evaluacion_id},
                {"$set": {"sellado": True, "fecha_sellado": datetime.now(timezone.utc).isoformat()}}
            )
        raise HTTPException(status_code=423, detail=f"Expediente sellado. {mensaje}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Filtrar campos permitidos
    allowed_fields = [
        "paciente_id", "paciente_nombre", "paciente_edad", "paciente_sexo", "paciente_expediente",
        "fecha", "medico_id", "medico_nombre", "motivo_consulta", "padecimiento_actual",
        "antecedentes", "medicamentos_actuales", "medicamentos_previos", "examen",
        "diagnosticos", "plan", "recomendaciones", "procedimientos", "recetas"
    ]
    
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    update_data["actualizado_por"] = current_user["id"]
    update_data["actualizado_por_nombre"] = current_user.get("name", current_user.get("username", ""))
    update_data["fecha_actualizacion"] = now
    update_data["ultimo_autoguardado"] = now
    
    await db.evaluaciones_oftalmologicas.update_one(
        {"id": evaluacion_id},
        {"$set": update_data}
    )
    
    # Procesar catálogos
    merged_data = {**existing, **update_data}
    await procesar_catalogos_evaluacion(merged_data)
    
    updated = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    return updated


@api_router.delete("/evaluaciones/{evaluacion_id}")
async def delete_evaluacion(
    evaluacion_id: str,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Eliminar evaluación (solo SuperAdmin, solo si no está sellada)"""
    existing = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # Verificar sellado
    debe_sellar, mensaje = verificar_sellado(existing)
    if debe_sellar:
        raise HTTPException(status_code=423, detail=f"Expediente sellado. No se puede eliminar. {mensaje}")
    
    await db.evaluaciones_oftalmologicas.delete_one({"id": evaluacion_id})
    
    await audit.log(
        action="EVALUACION_DELETED",
        user_id=current_user["id"],
        user_name=current_user.get("username", "unknown"),
        details={"evaluacion_id": evaluacion_id, "paciente": existing.get("paciente_nombre")}
    )
    
    return {"message": "Evaluación eliminada"}


# --- Pacientes búsqueda rápida para evaluaciones ---

@api_router.get("/pacientes/buscar")
async def buscar_pacientes_rapido(
    search: str = Query("", min_length=0),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Búsqueda rápida de pacientes para autocomplete"""
    
    # Función para generar regex que coincida con variantes acentuadas
    def generate_accent_variants(text):
        """Genera un patrón regex que ignora diacríticos en la búsqueda"""
        accent_map = {
            'a': '[aáàäâ]', 'e': '[eéèëê]', 'i': '[iíìïî]', 
            'o': '[oóòöô]', 'u': '[uúùüû]', 'n': '[nñ]'
        }
        regex_pattern = ""
        for char in text:
            lower_char = char.lower()
            if lower_char in accent_map:
                # Clase de caracteres funciona con case-insensitive flag
                regex_pattern += accent_map[lower_char]
            else:
                # Escapar caracteres especiales de regex
                if char in r'\.^$*+?{}[]|()':
                    regex_pattern += '\\' + char
                else:
                    regex_pattern += char
        return regex_pattern
    
    query = {"is_active": True}
    if search:
        search_pattern = generate_accent_variants(search)
        search_regex = {"$regex": search_pattern, "$options": "i"}
        query["$or"] = [
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"record_number": {"$regex": search, "$options": "i"}},
            {"dpi": {"$regex": search, "$options": "i"}}
        ]
    
    pacientes = await db.patients.find(
        query, 
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "record_number": 1, "birth_date": 1, "gender": 1, "phone": 1}
    ).limit(limit).to_list(limit)
    
    # Enriquecer con edad y nombre completo
    for p in pacientes:
        p["nombre_completo"] = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        if p.get("birth_date"):
            p["edad"] = calcular_edad(p["birth_date"])
        else:
            p["edad"] = 0
    
    return pacientes


# ==================== MÓDULO DE CAJA - REFACTORIZADO ====================
# Rutas extraídas a /app/backend/routes/caja.py
from routes.caja import (
    router as caja_router, 
    catalogos_router as caja_catalogos_router,
    cxc_router as caja_cxc_router,
    cierres_financieros_router as caja_cierres_financieros_router,
    init_caja_routes
)

# Función wrapper para audit log compatible con el módulo caja
async def caja_log_action(user_id: str, action: str, collection: str, doc_id: str, details: dict = None):
    """Wrapper de audit.log para el módulo de caja"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "name": 1})
    user_name = user.get("name", "Sistema") if user else "Sistema"
    await audit.log(action, user_id, user_name, details)

# Inicializar módulo de caja con función de audit
init_caja_routes(caja_log_action)

# Incluir routers de caja en api_router
api_router.include_router(caja_router, tags=["Caja"])
api_router.include_router(caja_catalogos_router, tags=["Caja - Catálogos"])
api_router.include_router(caja_cxc_router, tags=["Caja - CxC"])
api_router.include_router(caja_cierres_financieros_router, tags=["Caja - Cierres Financieros"])

# ==================== MÓDULO DE AGENDA - PACIENTES ====================
# Rutas para la agenda de citas de pacientes (INDEPENDIENTE de Sala de Operaciones)
from routes.agenda import (
    router as agenda_router,
    medicos_agenda_router,
    config_router as agenda_config_router
)

# Incluir routers de agenda en api_router
api_router.include_router(agenda_router, tags=["Agenda"])
api_router.include_router(medicos_agenda_router, tags=["Agenda - Médicos"])
api_router.include_router(agenda_config_router, tags=["Agenda - Configuración"])

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
    request: Request,
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(require_permission("manage_users"))
):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    client_ip = request.client.host if request.client else "unknown"
    update_data = {}
    changes = []
    
    if user_data.name is not None and user_data.name != user.get("name"):
        update_data["name"] = user_data.name
        changes.append(f"nombre: {user.get('name')} → {user_data.name}")
    
    if user_data.role is not None and user_data.role != user.get("role"):
        update_data["role"] = user_data.role
        changes.append(f"rol: {user.get('role')} → {user_data.role}")
    
    if user_data.password is not None:
        # Validar fortaleza de contraseña
        is_valid, message = validate_password_strength(user_data.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        update_data["password"] = hash_password(user_data.password)
        update_data["password_changed_at"] = datetime.now(timezone.utc).isoformat()
        changes.append("contraseña actualizada")
    
    if user_data.is_active is not None and user_data.is_active != user.get("is_active"):
        update_data["is_active"] = user_data.is_active
        changes.append(f"estado: {'activo' if user_data.is_active else 'inactivo'}")
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.users.update_one({"id": user_id}, {"$set": update_data})
        
        # Audit log
        await audit.log(
            action="USER_UPDATED",
            user_id=current_user["id"],
            user_name=current_user.get("username", "unknown"),
            details={
                "target_user_id": user_id,
                "target_username": user.get("username"),
                "changes": changes
            },
            ip_address=client_ip
        )
    
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
    
    # Search filter (provider, name, invoice_number, or expense_number)
    if search:
        query["$or"] = [
            {"provider": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
            {"invoice_number": {"$regex": search, "$options": "i"}},
            {"expense_number": {"$regex": search, "$options": "i"}}
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
    
    # Generar número correlativo automático
    expense_number = await get_next_expense_number()
    
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
        "expense_number": expense_number,  # Número correlativo automático
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

@api_router.put("/expenses/{expense_id}/toggle-authorization")
async def toggle_expense_authorization(expense_id: str, current_user: dict = Depends(require_permission("authorize_payments"))):
    """Toggle el estado de autorización de un gasto (Solo SuperAdmin)"""
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    # Solo gastos con saldo pendiente pueden ser autorizados
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

class AuthorizeExpenseRequest(BaseModel):
    bank_account_id: str

@api_router.post("/expenses/{expense_id}/authorize")
async def authorize_expense_with_bank(
    expense_id: str, 
    auth_data: AuthorizeExpenseRequest,
    current_user: dict = Depends(require_permission("authorize_payments"))
):
    """Autoriza un gasto con una cuenta bancaria específica y crea la autorización de pago (Solo SuperAdmin)"""
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    # Solo gastos con saldo pendiente pueden ser autorizados
    remaining = expense.get("remaining_amount", expense.get("amount", 0))
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Este gasto ya está completamente pagado")
    
    # Verificar que la cuenta bancaria existe
    bank_account = await db.bank_accounts.find_one({"id": auth_data.bank_account_id}, {"_id": 0})
    if not bank_account:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    
    # Verificar si ya existe una autorización pendiente para este gasto
    existing_auth = await db.payment_authorizations.find_one({
        "expense_id": expense_id, 
        "status": "pendiente"
    }, {"_id": 0})
    
    if existing_auth:
        raise HTTPException(status_code=400, detail="Ya existe una autorización pendiente para este gasto")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Crear autorización de pago directamente (sin necesidad de "Confirmar")
    auth_doc = {
        "id": str(uuid.uuid4()),
        "expense_id": expense_id,
        "bank_account_id": auth_data.bank_account_id,
        "amount_to_pay": remaining,
        "status": "pendiente",
        "notes": f"Autorizado desde módulo de Gastos",
        "authorized_by": current_user["id"],
        "authorized_at": now,
        "executed_by": None,
        "executed_at": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.payment_authorizations.insert_one(auth_doc)
    
    # Marcar el gasto como autorizado
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

@api_router.post("/expenses/confirm-authorizations")
async def confirm_expense_authorizations(current_user: dict = Depends(require_permission("authorize_payments"))):
    """Confirma los gastos autorizados y crea autorizaciones de pago para el admin"""
    # Buscar gastos marcados como autorizados con saldo pendiente
    authorized_expenses = await db.expenses.find(
        {"is_authorized": True, "remaining_amount": {"$gt": 0}},
        {"_id": 0}
    ).to_list(1000)
    
    if not authorized_expenses:
        raise HTTPException(status_code=400, detail="No hay gastos autorizados pendientes de confirmar")
    
    # Obtener cuenta bancaria por defecto si algún gasto no tiene cuenta asignada
    default_bank = await db.bank_accounts.find_one({"is_active": True}, {"_id": 0})
    
    created_count = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for expense in authorized_expenses:
        # Usar la cuenta bancaria asignada al gasto o la por defecto
        bank_id = expense.get("authorized_bank_account_id") or (default_bank["id"] if default_bank else None)
        
        if not bank_id:
            continue  # Saltar si no hay cuenta bancaria
        
        # Crear autorización de pago
        auth_doc = {
            "id": str(uuid.uuid4()),
            "expense_id": expense["id"],
            "bank_account_id": bank_id,
            "amount_to_pay": expense["remaining_amount"],
            "status": "pendiente",
            "notes": f"Autorizado desde módulo de Gastos",
            "authorized_by": current_user["id"],
            "authorized_at": now,
            "executed_by": None,
            "executed_at": None,
            "created_at": now,
            "updated_at": now
        }
        
        await db.payment_authorizations.insert_one(auth_doc)
        
        # Quitar marca de autorización del gasto y limpiar cuenta asignada
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
    """Estadísticas del dashboard - filtrado por mes actual"""
    # Calcular inicio del mes actual
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    # Use aggregation for efficient stats calculation - filtrado por mes actual
    pipeline = [
        {"$match": {"date": {"$gte": month_start}}},  # Filtrar solo mes actual
        {"$group": {
            "_id": None,
            "total_gastos": {"$sum": "$amount"},
            "gastos_pendientes": {"$sum": {"$cond": [{"$in": ["$status", ["pendiente", "parcial"]]}, "$remaining_amount", 0]}},
            "gastos_pagados": {"$sum": "$paid_amount"},
            "gastos_parciales": {"$sum": {"$cond": [{"$eq": ["$status", "parcial"]}, "$amount", 0]}},
            "gastos_vencidos": {"$sum": {"$cond": [{"$eq": ["$status", "vencido"]}, "$remaining_amount", 0]}},
            "total_fijos": {"$sum": {"$cond": [{"$eq": ["$type", "fijo"]}, "$amount", 0]}},
            "total_proveedores": {"$sum": {"$cond": [{"$eq": ["$type", "proveedor"]}, "$amount", 0]}},
            "total_variables": {"$sum": {"$cond": [{"$eq": ["$type", "variable"]}, "$amount", 0]}},
            "alertas_30_dias_count": {"$sum": {"$cond": [{"$in": ["$status", ["pendiente", "parcial"]]}, 1, 0]}},
            "vencidos_count": {"$sum": {"$cond": [{"$eq": ["$status", "vencido"]}, 1, 0]}}
        }}
    ]
    
    result = await db.expenses.aggregate(pipeline).to_list(1)
    
    if result:
        stats = result[0]
        del stats["_id"]
        stats["alertas_30_dias"] = stats.pop("alertas_30_dias_count", 0)
        stats["alertas_60_dias"] = 0  # Se puede calcular con otro query si se necesita
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
    """Obtener todos los proveedores (Admin, SuperAdmin y Optica)"""
    if current_user["role"] not in ["admin", "superadmin", "optica"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para ver proveedores")
    
    suppliers = await db.suppliers.find({"is_active": True}, {"_id": 0}).sort("name", 1).to_list(1000)
    return SupplierListResponse(data=suppliers, total=len(suppliers))


@api_router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    """Obtener un proveedor específico"""
    if current_user["role"] not in ["admin", "superadmin", "optica"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    supplier = await db.suppliers.find_one({"id": supplier_id, "is_active": True}, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return SupplierResponse(**supplier)


@api_router.post("/suppliers", response_model=SupplierResponse)
async def create_supplier(supplier_data: SupplierCreate, current_user: dict = Depends(get_current_user)):
    """Crear nuevo proveedor (Admin, SuperAdmin y Optica)"""
    if current_user["role"] not in ["admin", "superadmin", "optica"]:
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
    
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    current_month = now.strftime("%Y-%m")
    
    fixed_expense_doc = {
        "id": str(uuid.uuid4()),
        "supplier_id": fixed_expense_data.supplier_id,
        "expense_name": fixed_expense_data.expense_name,
        "amount": fixed_expense_data.amount,
        "day_of_month": fixed_expense_data.day_of_month,
        "duration_type": fixed_expense_data.duration_type,
        "end_date": fixed_expense_data.end_date,
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now_str,
        "updated_at": now_str,
        "last_generated": None
    }
    
    await db.fixed_expenses.insert_one(fixed_expense_doc)
    if "_id" in fixed_expense_doc:
        del fixed_expense_doc["_id"]
    
    first_expense_generated = False
    
    # Generar el primer gasto si se solicitó
    if fixed_expense_data.generate_first:
        # Obtener próximo número de gasto
        last_expense = await db.expenses.find_one(
            {"expense_number": {"$exists": True}},
            sort=[("created_at", -1)]
        )
        if last_expense and last_expense.get("expense_number"):
            try:
                last_num = int(last_expense["expense_number"].split("-")[1])
                next_num = last_num + 1
            except (IndexError, ValueError):
                next_num = 1
        else:
            next_num = 1
        expense_number = f"GST-{next_num:04d}"
        
        # Crear el gasto
        expense_doc = {
            "id": str(uuid.uuid4()),
            "expense_number": expense_number,
            "date": now.strftime("%Y-%m-%d"),
            "supplier_id": fixed_expense_data.supplier_id,
            "name": f"{fixed_expense_data.expense_name} ({supplier['name']})",
            "amount": fixed_expense_data.amount,
            "type": "fijo",
            "due_date": now.strftime("%Y-%m-%d"),  # Vence hoy
            "status": "pendiente",
            "paid_amount": 0,
            "remaining_amount": fixed_expense_data.amount,
            "is_authorized": False,
            "notes": f"Generado automáticamente desde gasto fijo al crearlo",
            "created_by": current_user["id"],
            "created_at": now_str,
            "updated_at": now_str,
            "fixed_expense_id": fixed_expense_doc["id"]
        }
        
        await db.expenses.insert_one(expense_doc)
        
        # Actualizar last_generated del gasto fijo
        await db.fixed_expenses.update_one(
            {"id": fixed_expense_doc["id"]},
            {"$set": {"last_generated": current_month}}
        )
        fixed_expense_doc["last_generated"] = current_month
        first_expense_generated = True
    
    enriched = await enrich_fixed_expense(fixed_expense_doc)
    enriched["first_expense_generated"] = first_expense_generated
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
    
    # Función para generar regex que coincida con variantes acentuadas
    def generate_accent_regex(text):
        """Genera un patrón regex que ignora diacríticos en la búsqueda"""
        accent_map = {
            'a': '[aáàäâ]', 'e': '[eéèëê]', 'i': '[iíìïî]', 
            'o': '[oóòöô]', 'u': '[uúùüû]', 'n': '[nñ]',
            'A': '[AÁÀÄÂ]', 'E': '[EÉÈËÊ]', 'I': '[IÍÌÏÎ]',
            'O': '[OÓÒÖÔ]', 'U': '[UÚÙÜÛ]', 'N': '[NÑ]'
        }
        regex_pattern = ""
        for char in text:
            lower_char = char.lower()
            if lower_char in accent_map:
                # Usar clase de caracteres que incluye todas las variantes
                regex_pattern += accent_map[lower_char]
            else:
                # Escapar caracteres especiales de regex
                if char in r'\.^$*+?{}[]|()':
                    regex_pattern += '\\' + char
                else:
                    regex_pattern += char
        return regex_pattern
    
    query = {"is_active": is_active}
    
    # Búsqueda por texto con soporte para acentos
    if search:
        search_pattern = generate_accent_regex(search)
        search_regex = {"$regex": search_pattern, "$options": "i"}
        query["$or"] = [
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"dpi": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"record_number": {"$regex": search, "$options": "i"}}
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
    import unicodedata
    
    # Función para normalizar texto (remover diacríticos)
    def normalize_text(text):
        if not text:
            return ""
        normalized = unicodedata.normalize('NFD', text)
        return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    
    # Función para generar variantes con/sin acentos
    def generate_accent_variants(text):
        """Genera variantes del texto con y sin acentos comunes en español"""
        variants = [text]
        # Mapeo de caracteres acentuados a no acentuados y viceversa
        accent_map = {
            'a': '[aáàäâ]', 'e': '[eéèëê]', 'i': '[iíìïî]', 
            'o': '[oóòöô]', 'u': '[uúùüû]', 'n': '[nñ]',
            'A': '[AÁÀÄÂ]', 'E': '[EÉÈËÊ]', 'I': '[IÍÌÏÎ]',
            'O': '[OÓÒÖÔ]', 'U': '[UÚÙÜÛ]', 'N': '[NÑ]'
        }
        # Crear regex que coincida con cualquier variante
        regex_pattern = ""
        for char in text:
            if char.lower() in accent_map:
                regex_pattern += accent_map.get(char.lower(), char) if char.islower() else accent_map.get(char.lower(), char).upper()
            else:
                regex_pattern += char
        return regex_pattern
    
    # Generar patrón regex que coincida con variantes acentuadas
    search_pattern = generate_accent_variants(q)
    search_regex = {"$regex": search_pattern, "$options": "i"}
    
    query = {
        "is_active": True,
        "$or": [
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"dpi": {"$regex": q, "$options": "i"}},
            {"phone": {"$regex": q, "$options": "i"}},
            {"record_number": {"$regex": q, "$options": "i"}}
        ]
    }
    
    patients = await db.patients.find(query, {"_id": 0}).limit(limit).to_list(limit)
    
    results = []
    seen_ids = set()
    for p in patients:
        if p["id"] not in seen_ids:
            seen_ids.add(p["id"])
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


# ==================== OPTICA ROUTES ====================

# -------------------- DOCTORS (Médicos) --------------------

@api_router.get("/doctors", response_model=DoctorListResponse)
async def get_doctors(
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Listar médicos (acceso para todos los usuarios autenticados)"""
    query = {"is_active": True}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": search_regex},
            {"specialty": search_regex},
            {"license_number": search_regex}
        ]
    
    doctors = await db.doctors.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    return DoctorListResponse(data=doctors, total=len(doctors))


@api_router.get("/doctors/search")
async def search_doctors(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Búsqueda de médicos para autocompletado"""
    search_regex = {"$regex": q, "$options": "i"}
    query = {
        "is_active": True,
        "$or": [{"name": search_regex}, {"specialty": search_regex}]
    }
    
    doctors = await db.doctors.find(query, {"_id": 0, "id": 1, "name": 1, "specialty": 1}).limit(limit).to_list(limit)
    return doctors


@api_router.get("/doctors/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(doctor_id: str, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener médico por ID"""
    doctor = await db.doctors.find_one({"id": doctor_id, "is_active": True}, {"_id": 0})
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    return DoctorResponse(**doctor)


@api_router.post("/doctors", response_model=DoctorResponse)
async def create_doctor(doctor_data: DoctorCreate, current_user: dict = Depends(require_permission("manage_doctors"))):
    """Crear nuevo médico"""
    # Verificar duplicado por nombre
    existing = await db.doctors.find_one({
        "name": {"$regex": f"^{doctor_data.name}$", "$options": "i"},
        "is_active": True
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un médico con este nombre")
    
    now = datetime.now(timezone.utc).isoformat()
    doctor_doc = {
        "id": str(uuid.uuid4()),
        "name": doctor_data.name,
        "specialty": doctor_data.specialty or "",
        "phone": doctor_data.phone or "",
        "email": doctor_data.email or "",
        "license_number": doctor_data.license_number or "",
        "notes": doctor_data.notes or "",
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.doctors.insert_one(doctor_doc)
    if "_id" in doctor_doc:
        del doctor_doc["_id"]
    return DoctorResponse(**doctor_doc)


@api_router.put("/doctors/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(doctor_id: str, doctor_data: DoctorUpdate, current_user: dict = Depends(require_permission("manage_doctors"))):
    """Actualizar médico"""
    doctor = await db.doctors.find_one({"id": doctor_id, "is_active": True})
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    
    update_data = {k: v for k, v in doctor_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.doctors.update_one({"id": doctor_id}, {"$set": update_data})
    updated = await db.doctors.find_one({"id": doctor_id}, {"_id": 0})
    return DoctorResponse(**updated)


@api_router.delete("/doctors/{doctor_id}")
async def delete_doctor(doctor_id: str, current_user: dict = Depends(require_permission("manage_doctors"))):
    """Eliminar médico (soft delete)"""
    doctor = await db.doctors.find_one({"id": doctor_id, "is_active": True})
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    
    await db.doctors.update_one(
        {"id": doctor_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Médico eliminado correctamente"}


# -------------------- FRAME INVENTORY (Inventario de Aros) --------------------

@api_router.get("/optica/frames", response_model=FrameInventoryListResponse)
async def get_frames(
    search: Optional[str] = None,
    low_stock: Optional[bool] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Listar inventario de aros"""
    query = {"is_active": True}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"brand": search_regex},
            {"code": search_regex},
            {"model": search_regex}
        ]
    if low_stock:
        query["stock"] = {"$lte": 5}
    
    frames = await db.optica_frames.find(query, {"_id": 0}).sort("brand", 1).to_list(1000)
    return FrameInventoryListResponse(data=frames, total=len(frames))


@api_router.get("/optica/frames/search")
async def search_frames(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Búsqueda de aros para autocompletado"""
    search_regex = {"$regex": q, "$options": "i"}
    query = {
        "is_active": True,
        "stock": {"$gt": 0},
        "$or": [{"brand": search_regex}, {"code": search_regex}, {"model": search_regex}]
    }
    
    frames = await db.optica_frames.find(query, {"_id": 0}).limit(limit).to_list(limit)
    result = []
    for f in frames:
        result.append({
            "id": f["id"],
            "label": f"{f['brand']} - {f['code']} ({f.get('model', '')})",
            "brand": f["brand"],
            "code": f["code"],
            "model": f.get("model", ""),
            "color": f.get("color", ""),
            "sale_price": f["sale_price"],
            "stock": f["stock"]
        })
    return result


@api_router.get("/optica/frames/{frame_id}", response_model=FrameInventoryResponse)
async def get_frame(frame_id: str, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener aro por ID"""
    frame = await db.optica_frames.find_one({"id": frame_id, "is_active": True}, {"_id": 0})
    if not frame:
        raise HTTPException(status_code=404, detail="Aro no encontrado")
    return FrameInventoryResponse(**frame)


@api_router.post("/optica/frames", response_model=FrameInventoryResponse)
async def create_frame(frame_data: FrameInventoryCreate, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Crear nuevo aro en inventario"""
    # Verificar código único
    existing = await db.optica_frames.find_one({"code": frame_data.code, "is_active": True})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un aro con este código")
    
    now = datetime.now(timezone.utc).isoformat()
    frame_doc = {
        "id": str(uuid.uuid4()),
        "brand": frame_data.brand,
        "code": frame_data.code,
        "model": frame_data.model or "",
        "color": frame_data.color or "",
        "cost_price": frame_data.cost_price,
        "sale_price": frame_data.sale_price,
        "stock": frame_data.stock,
        "entry_date": now[:10],
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.optica_frames.insert_one(frame_doc)
    if "_id" in frame_doc:
        del frame_doc["_id"]
    return FrameInventoryResponse(**frame_doc)


@api_router.put("/optica/frames/{frame_id}", response_model=FrameInventoryResponse)
async def update_frame(frame_id: str, frame_data: FrameInventoryUpdate, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Actualizar aro"""
    frame = await db.optica_frames.find_one({"id": frame_id, "is_active": True})
    if not frame:
        raise HTTPException(status_code=404, detail="Aro no encontrado")
    
    update_data = {k: v for k, v in frame_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    # Verificar código único si se cambia
    if "code" in update_data and update_data["code"] != frame["code"]:
        existing = await db.optica_frames.find_one({
            "code": update_data["code"], 
            "is_active": True, 
            "id": {"$ne": frame_id}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un aro con este código")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.optica_frames.update_one({"id": frame_id}, {"$set": update_data})
    updated = await db.optica_frames.find_one({"id": frame_id}, {"_id": 0})
    return FrameInventoryResponse(**updated)


@api_router.delete("/optica/frames/{frame_id}")
async def delete_frame(frame_id: str, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Eliminar aro (soft delete)"""
    frame = await db.optica_frames.find_one({"id": frame_id, "is_active": True})
    if not frame:
        raise HTTPException(status_code=404, detail="Aro no encontrado")
    
    await db.optica_frames.update_one(
        {"id": frame_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Aro eliminado correctamente"}


# -------------------- CONTACT LENS INVENTORY (Lentes de Contacto) --------------------

@api_router.get("/optica/contact-lenses", response_model=ContactLensInventoryListResponse)
async def get_contact_lenses(
    search: Optional[str] = None,
    lens_type: Optional[str] = None,
    low_stock: Optional[bool] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Listar inventario de lentes de contacto"""
    query = {"is_active": True}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"brand": search_regex},
            {"description": search_regex}
        ]
    if lens_type:
        query["lens_type"] = lens_type
    if low_stock:
        query["stock"] = {"$lte": 5}
    
    lenses = await db.optica_contact_lenses.find(query, {"_id": 0}).sort("lens_type", 1).to_list(1000)
    return ContactLensInventoryListResponse(data=lenses, total=len(lenses))


@api_router.get("/optica/contact-lenses/search")
async def search_contact_lenses(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Búsqueda de lentes de contacto para autocompletado"""
    search_regex = {"$regex": q, "$options": "i"}
    query = {
        "is_active": True,
        "stock": {"$gt": 0},
        "$or": [{"brand": search_regex}, {"description": search_regex}, {"lens_type": search_regex}]
    }
    
    lenses = await db.optica_contact_lenses.find(query, {"_id": 0}).limit(limit).to_list(limit)
    result = []
    for l in lenses:
        result.append({
            "id": l["id"],
            "label": f"{l['lens_type'].capitalize()} - {l.get('brand', '')} ({l.get('description', '')})",
            "lens_type": l["lens_type"],
            "brand": l.get("brand", ""),
            "sale_price": l["sale_price"],
            "stock": l["stock"]
        })
    return result


@api_router.post("/optica/contact-lenses", response_model=ContactLensInventoryResponse)
async def create_contact_lens(lens_data: ContactLensInventoryCreate, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Crear nuevo lente de contacto en inventario"""
    now = datetime.now(timezone.utc).isoformat()
    lens_doc = {
        "id": str(uuid.uuid4()),
        "lens_type": lens_data.lens_type,
        "brand": lens_data.brand or "",
        "description": lens_data.description or "",
        "cost_price": lens_data.cost_price,
        "sale_price": lens_data.sale_price,
        "stock": lens_data.stock,
        "entry_date": now[:10],
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.optica_contact_lenses.insert_one(lens_doc)
    if "_id" in lens_doc:
        del lens_doc["_id"]
    return ContactLensInventoryResponse(**lens_doc)


@api_router.put("/optica/contact-lenses/{lens_id}", response_model=ContactLensInventoryResponse)
async def update_contact_lens(lens_id: str, lens_data: ContactLensInventoryUpdate, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Actualizar lente de contacto"""
    lens = await db.optica_contact_lenses.find_one({"id": lens_id, "is_active": True})
    if not lens:
        raise HTTPException(status_code=404, detail="Lente de contacto no encontrado")
    
    update_data = {k: v for k, v in lens_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.optica_contact_lenses.update_one({"id": lens_id}, {"$set": update_data})
    updated = await db.optica_contact_lenses.find_one({"id": lens_id}, {"_id": 0})
    return ContactLensInventoryResponse(**updated)


@api_router.delete("/optica/contact-lenses/{lens_id}")
async def delete_contact_lens(lens_id: str, current_user: dict = Depends(require_permission("manage_optica_inventory"))):
    """Eliminar lente de contacto (soft delete)"""
    lens = await db.optica_contact_lenses.find_one({"id": lens_id, "is_active": True})
    if not lens:
        raise HTTPException(status_code=404, detail="Lente de contacto no encontrado")
    
    await db.optica_contact_lenses.update_one(
        {"id": lens_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Lente de contacto eliminado correctamente"}


# -------------------- LENS TYPE CATALOG (Catálogo Tipos de Lente) --------------------

@api_router.get("/optica/lens-types", response_model=LensTypeListResponse)
async def get_lens_types(current_user: dict = Depends(require_permission("view_optica"))):
    """Listar catálogo de tipos de lente"""
    lens_types = await db.optica_lens_types.find({"is_active": True}, {"_id": 0}).sort("name", 1).to_list(1000)
    return LensTypeListResponse(data=lens_types, total=len(lens_types))


@api_router.post("/optica/lens-types", response_model=LensTypeResponse)
async def create_lens_type(lens_type_data: LensTypeCreate, current_user: dict = Depends(require_permission("manage_lens_catalog"))):
    """Crear nuevo tipo de lente"""
    # Verificar nombre único
    existing = await db.optica_lens_types.find_one({
        "name": {"$regex": f"^{lens_type_data.name}$", "$options": "i"},
        "is_active": True
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un tipo de lente con este nombre")
    
    now = datetime.now(timezone.utc).isoformat()
    lens_type_doc = {
        "id": str(uuid.uuid4()),
        "name": lens_type_data.name,
        "description": lens_type_data.description or "",
        "default_price": lens_type_data.default_price,
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.optica_lens_types.insert_one(lens_type_doc)
    if "_id" in lens_type_doc:
        del lens_type_doc["_id"]
    return LensTypeResponse(**lens_type_doc)


@api_router.put("/optica/lens-types/{lens_type_id}", response_model=LensTypeResponse)
async def update_lens_type(lens_type_id: str, lens_type_data: LensTypeUpdate, current_user: dict = Depends(require_permission("manage_lens_catalog"))):
    """Actualizar tipo de lente"""
    lens_type = await db.optica_lens_types.find_one({"id": lens_type_id, "is_active": True})
    if not lens_type:
        raise HTTPException(status_code=404, detail="Tipo de lente no encontrado")
    
    update_data = {k: v for k, v in lens_type_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.optica_lens_types.update_one({"id": lens_type_id}, {"$set": update_data})
    updated = await db.optica_lens_types.find_one({"id": lens_type_id}, {"_id": 0})
    return LensTypeResponse(**updated)


@api_router.delete("/optica/lens-types/{lens_type_id}")
async def delete_lens_type(lens_type_id: str, current_user: dict = Depends(require_permission("manage_lens_catalog"))):
    """Eliminar tipo de lente (soft delete)"""
    lens_type = await db.optica_lens_types.find_one({"id": lens_type_id, "is_active": True})
    if not lens_type:
        raise HTTPException(status_code=404, detail="Tipo de lente no encontrado")
    
    await db.optica_lens_types.update_one(
        {"id": lens_type_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Tipo de lente eliminado correctamente"}


# -------------------- OPTICA SALES (Ventas) --------------------

async def get_next_order_number() -> str:
    """Genera el siguiente número de orden correlativo"""
    prefix = datetime.now(timezone.utc).strftime("ORD-%Y%m-")
    
    last_sale = await db.optica_sales.find_one(
        {"order_number": {"$regex": f"^{prefix}"}},
        {"order_number": 1},
        sort=[("order_number", -1)]
    )
    
    if last_sale:
        try:
            last_num = int(last_sale["order_number"].split("-")[-1])
            next_num = last_num + 1
        except Exception:
            next_num = 1
    else:
        next_num = 1
    
    return f"{prefix}{next_num:04d}"


async def enrich_sale(sale: dict) -> dict:
    """Enriquece la venta con datos relacionados"""
    # Paciente
    patient = await db.patients.find_one({"id": sale["patient_id"]}, {"_id": 0})
    if patient:
        sale["patient_name"] = f"{patient['first_name']} {patient['last_name']}"
        sale["patient_phone"] = patient.get("phone", "")
    else:
        sale["patient_name"] = "Paciente no encontrado"
        sale["patient_phone"] = ""
    
    # Médico
    if sale.get("doctor_id"):
        doctor = await db.doctors.find_one({"id": sale["doctor_id"]}, {"_id": 0})
        sale["doctor_name"] = doctor["name"] if doctor else ""
    else:
        sale["doctor_name"] = ""
    
    # Aro
    if sale.get("frame_id"):
        frame = await db.optica_frames.find_one({"id": sale["frame_id"]}, {"_id": 0})
        if frame:
            sale["frame_info"] = f"{frame['brand']} - {frame['code']}"
            sale["frame_price"] = sale.get("frame_price", frame["sale_price"])
    else:
        sale["frame_info"] = ""
        sale["frame_price"] = 0
    
    # Lente de contacto
    if sale.get("contact_lens_id"):
        contact_lens = await db.optica_contact_lenses.find_one({"id": sale["contact_lens_id"]}, {"_id": 0})
        if contact_lens:
            sale["contact_lens_info"] = f"{contact_lens['lens_type'].capitalize()} - {contact_lens.get('brand', '')}"
            sale["contact_lens_price"] = sale.get("contact_lens_price", contact_lens["sale_price"])
    else:
        sale["contact_lens_info"] = ""
        sale["contact_lens_price"] = 0
    
    # Creador
    creator = await db.users.find_one({"id": sale["created_by"]}, {"_id": 0, "name": 1})
    sale["created_by_name"] = creator["name"] if creator else ""
    
    # Pagos/Abonos
    payments = await db.optica_sale_payments.find({"sale_id": sale["id"]}, {"_id": 0}).sort("created_at", 1).to_list(100)
    for payment in payments:
        creator = await db.users.find_one({"id": payment["created_by"]}, {"_id": 0, "name": 1})
        payment["created_by_name"] = creator["name"] if creator else ""
    sale["payments"] = payments
    
    return sale


@api_router.get("/optica/sales", response_model=OpticaSaleListResponse)
async def get_optica_sales(
    status: Optional[str] = None,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    search: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Listar ventas de óptica"""
    query = {}
    
    if status and status != "all":
        query["status"] = status
    
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to + "T23:59:59"
        if date_query:
            query["created_at"] = date_query
    
    sales = await db.optica_sales.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Enriquecer y filtrar por búsqueda
    enriched_sales = []
    for sale in sales:
        enriched = await enrich_sale(sale)
        
        # Filtro de búsqueda post-query
        if search:
            search_lower = search.lower()
            if not (
                search_lower in enriched.get("patient_name", "").lower() or
                search_lower in enriched.get("order_number", "").lower() or
                search_lower in enriched.get("doctor_name", "").lower()
            ):
                continue
        
        enriched_sales.append(enriched)
    
    return OpticaSaleListResponse(data=enriched_sales, total=len(enriched_sales))


@api_router.get("/optica/sales/pending")
async def get_pending_sales(current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener ventas con saldo pendiente"""
    sales = await db.optica_sales.find(
        {"status": "pendiente", "balance_due": {"$gt": 0}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    enriched_sales = []
    total_pending = 0
    for sale in sales:
        enriched = await enrich_sale(sale)
        enriched_sales.append(enriched)
        total_pending += sale.get("balance_due", 0)
    
    return {
        "data": enriched_sales,
        "total": len(enriched_sales),
        "total_pending_amount": total_pending
    }


@api_router.get("/optica/sales/{sale_id}", response_model=OpticaSaleResponse)
async def get_optica_sale(sale_id: str, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener detalle de una venta"""
    sale = await db.optica_sales.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    enriched = await enrich_sale(sale)
    return OpticaSaleResponse(**enriched)


@api_router.post("/optica/sales", response_model=OpticaSaleResponse)
async def create_optica_sale(sale_data: OpticaSaleCreate, current_user: dict = Depends(require_permission("manage_optica_sales"))):
    """Crear nueva venta de óptica"""
    # Validar paciente
    patient = await db.patients.find_one({"id": sale_data.patient_id, "is_active": True})
    if not patient:
        raise HTTPException(status_code=400, detail="Paciente no encontrado")
    
    # Validar médico (opcional)
    if sale_data.doctor_id:
        doctor = await db.doctors.find_one({"id": sale_data.doctor_id, "is_active": True})
        if not doctor:
            raise HTTPException(status_code=400, detail="Médico no encontrado")
    
    # Calcular totales
    subtotal = 0
    frame_price = 0
    contact_lens_price = 0
    lens_total = 0
    
    # Validar y obtener precio del aro
    if sale_data.frame_id:
        frame = await db.optica_frames.find_one({"id": sale_data.frame_id, "is_active": True})
        if not frame:
            raise HTTPException(status_code=400, detail="Aro no encontrado")
        if frame["stock"] < 1:
            raise HTTPException(status_code=400, detail="No hay stock disponible para este aro")
        frame_price = frame["sale_price"]
        subtotal += frame_price
        # Descontar stock
        await db.optica_frames.update_one(
            {"id": sale_data.frame_id},
            {"$inc": {"stock": -1}}
        )
    
    # Validar y obtener precio del lente de contacto
    if sale_data.contact_lens_id:
        contact_lens = await db.optica_contact_lenses.find_one({"id": sale_data.contact_lens_id, "is_active": True})
        if not contact_lens:
            raise HTTPException(status_code=400, detail="Lente de contacto no encontrado")
        if contact_lens["stock"] < 1:
            raise HTTPException(status_code=400, detail="No hay stock disponible para este lente de contacto")
        contact_lens_price = contact_lens["sale_price"]
        subtotal += contact_lens_price
        # Descontar stock
        await db.optica_contact_lenses.update_one(
            {"id": sale_data.contact_lens_id},
            {"$inc": {"stock": -1}}
        )
    
    # Procesar líneas de lentes
    lens_items = []
    for item in sale_data.lens_items:
        lens_type = await db.optica_lens_types.find_one({"id": item.lens_type_id, "is_active": True})
        if not lens_type:
            raise HTTPException(status_code=400, detail=f"Tipo de lente no encontrado: {item.lens_type_id}")
        
        item_subtotal = item.unit_price * item.quantity
        lens_items.append({
            "lens_type_id": item.lens_type_id,
            "lens_type_name": lens_type["name"],
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "subtotal": item_subtotal
        })
        lens_total += item_subtotal
    
    subtotal += lens_total
    
    # Calcular descuento y total
    discount_amount = subtotal * (sale_data.discount_percent / 100)
    total = subtotal - discount_amount
    
    # Validar pago inicial
    if sale_data.initial_payment > total:
        raise HTTPException(status_code=400, detail="El pago inicial no puede ser mayor al total")
    
    total_paid = sale_data.initial_payment
    balance_due = total - total_paid
    status = "pagado" if balance_due <= 0 else "pendiente"
    
    now = datetime.now(timezone.utc).isoformat()
    order_number = await get_next_order_number()
    
    sale_doc = {
        "id": str(uuid.uuid4()),
        "order_number": order_number,
        "patient_id": sale_data.patient_id,
        "doctor_id": sale_data.doctor_id or "",
        "frame_id": sale_data.frame_id or "",
        "frame_price": frame_price,
        "contact_lens_id": sale_data.contact_lens_id or "",
        "contact_lens_price": contact_lens_price,
        "lens_items": lens_items,
        "lens_total": lens_total,
        "subtotal": subtotal,
        "discount_percent": sale_data.discount_percent,
        "discount_amount": discount_amount,
        "total": total,
        "total_paid": total_paid,
        "balance_due": balance_due,
        "payment_method": sale_data.payment_method,
        "status": status,
        "notes": sale_data.notes or "",
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.optica_sales.insert_one(sale_doc)
    if "_id" in sale_doc:
        del sale_doc["_id"]
    
    # Registrar pago inicial si existe
    if sale_data.initial_payment > 0:
        payment_doc = {
            "id": str(uuid.uuid4()),
            "sale_id": sale_doc["id"],
            "amount": sale_data.initial_payment,
            "payment_method": sale_data.payment_method,
            "reference": "",
            "notes": "Pago inicial",
            "created_by": current_user["id"],
            "created_at": now
        }
        await db.optica_sale_payments.insert_one(payment_doc)
    
    enriched = await enrich_sale(sale_doc)
    return OpticaSaleResponse(**enriched)


@api_router.post("/optica/sales/{sale_id}/payments", response_model=SalePaymentResponse)
async def add_sale_payment(sale_id: str, payment_data: SalePaymentCreate, current_user: dict = Depends(require_permission("manage_optica_sales"))):
    """Registrar abono a una venta"""
    sale = await db.optica_sales.find_one({"id": sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    if sale["status"] == "pagado":
        raise HTTPException(status_code=400, detail="Esta venta ya está pagada completamente")
    
    if sale["status"] == "cancelado":
        raise HTTPException(status_code=400, detail="No se pueden registrar abonos en una venta cancelada")
    
    if payment_data.amount > sale["balance_due"]:
        raise HTTPException(status_code=400, detail=f"El abono no puede ser mayor al saldo pendiente (Q{sale['balance_due']:.2f})")
    
    now = datetime.now(timezone.utc).isoformat()
    
    payment_doc = {
        "id": str(uuid.uuid4()),
        "sale_id": sale_id,
        "amount": payment_data.amount,
        "payment_method": payment_data.payment_method,
        "reference": payment_data.reference or "",
        "notes": payment_data.notes or "",
        "created_by": current_user["id"],
        "created_at": now
    }
    
    await db.optica_sale_payments.insert_one(payment_doc)
    if "_id" in payment_doc:
        del payment_doc["_id"]
    
    # Actualizar totales de la venta
    new_total_paid = sale["total_paid"] + payment_data.amount
    new_balance_due = sale["total"] - new_total_paid
    new_status = "pagado" if new_balance_due <= 0 else "pendiente"
    
    await db.optica_sales.update_one(
        {"id": sale_id},
        {"$set": {
            "total_paid": new_total_paid,
            "balance_due": max(0, new_balance_due),
            "status": new_status,
            "updated_at": now
        }}
    )
    
    # Obtener nombre del creador
    creator = await db.users.find_one({"id": current_user["id"]}, {"_id": 0, "name": 1})
    payment_doc["created_by_name"] = creator["name"] if creator else ""
    
    return SalePaymentResponse(**payment_doc)


@api_router.put("/optica/sales/{sale_id}/cancel")
async def cancel_optica_sale(sale_id: str, current_user: dict = Depends(require_permission("manage_optica_sales"))):
    """Cancelar una venta y restaurar stock"""
    sale = await db.optica_sales.find_one({"id": sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    if sale["status"] == "cancelado":
        raise HTTPException(status_code=400, detail="Esta venta ya está cancelada")
    
    # Restaurar stock del aro
    if sale.get("frame_id"):
        await db.optica_frames.update_one(
            {"id": sale["frame_id"]},
            {"$inc": {"stock": 1}}
        )
    
    # Restaurar stock del lente de contacto
    if sale.get("contact_lens_id"):
        await db.optica_contact_lenses.update_one(
            {"id": sale["contact_lens_id"]},
            {"$inc": {"stock": 1}}
        )
    
    await db.optica_sales.update_one(
        {"id": sale_id},
        {"$set": {
            "status": "cancelado",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Venta cancelada correctamente. Stock restaurado."}


# ==================== OPTICA DASHBOARD & REPORTS ====================

@api_router.get("/optica/dashboard/stats")
async def get_optica_dashboard_stats(current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener estadísticas del dashboard de óptica"""
    now = datetime.now(timezone.utc)
    first_day_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Pipeline para ventas del mes actual
    pipeline_month = [
        {"$match": {
            "created_at": {"$gte": first_day_month.isoformat()},
            "status": {"$ne": "cancelado"}
        }},
        {"$group": {
            "_id": None,
            "total_ventas": {"$sum": "$total"},
            "total_cobrado": {"$sum": "$paid_amount"},
            "count": {"$sum": 1}
        }}
    ]
    
    month_result = await db.optica_sales.aggregate(pipeline_month).to_list(1)
    month_stats = month_result[0] if month_result else {"total_ventas": 0, "total_cobrado": 0, "count": 0}
    
    # Saldo pendiente total (todas las ventas pendientes)
    pipeline_pending = [
        {"$match": {"status": "pendiente"}},
        {"$group": {
            "_id": None,
            "saldo_pendiente": {"$sum": {"$subtract": ["$total", "$paid_amount"]}},
            "count_pendientes": {"$sum": 1}
        }}
    ]
    
    pending_result = await db.optica_sales.aggregate(pipeline_pending).to_list(1)
    pending_stats = pending_result[0] if pending_result else {"saldo_pendiente": 0, "count_pendientes": 0}
    
    return {
        "ventas_mes": month_stats.get("total_ventas", 0),
        "cobrado_mes": month_stats.get("total_cobrado", 0),
        "ordenes_mes": month_stats.get("count", 0),
        "saldo_pendiente": pending_stats.get("saldo_pendiente", 0),
        "ordenes_pendientes": pending_stats.get("count_pendientes", 0)
    }


@api_router.get("/optica/dashboard/monthly-chart")
async def get_optica_monthly_chart(current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener datos de ventas por mes (últimos 6 meses)"""
    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=180)
    
    pipeline = [
        {"$match": {
            "created_at": {"$gte": six_months_ago.isoformat()},
            "status": {"$ne": "cancelado"}
        }},
        {"$addFields": {
            "created_date": {"$dateFromString": {"dateString": "$created_at"}}
        }},
        {"$group": {
            "_id": {
                "year": {"$year": "$created_date"},
                "month": {"$month": "$created_date"}
            },
            "total": {"$sum": "$total"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]
    
    results = await db.optica_sales.aggregate(pipeline).to_list(12)
    
    month_names = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    chart_data = []
    for r in results:
        chart_data.append({
            "mes": f"{month_names[r['_id']['month']]} {r['_id']['year']}",
            "ventas": r["total"],
            "ordenes": r["count"]
        })
    
    return chart_data


@api_router.get("/optica/dashboard/top-doctors")
async def get_optica_top_doctors(limit: int = 5, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener top médicos por ventas"""
    pipeline = [
        {"$match": {"doctor_id": {"$ne": None}, "status": {"$ne": "cancelado"}}},
        {"$group": {
            "_id": "$doctor_id",
            "total_ventas": {"$sum": "$total"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"total_ventas": -1}},
        {"$limit": limit}
    ]
    
    results = await db.optica_sales.aggregate(pipeline).to_list(limit)
    
    # Enriquecer con nombres de médicos
    top_doctors = []
    for r in results:
        doctor = await db.doctors.find_one({"id": r["_id"]}, {"_id": 0, "name": 1})
        top_doctors.append({
            "doctor_id": r["_id"],
            "doctor_name": doctor.get("name", "Sin nombre") if doctor else "Sin nombre",
            "total_ventas": r["total_ventas"],
            "count": r["count"]
        })
    
    return top_doctors


@api_router.get("/optica/dashboard/top-brands")
async def get_optica_top_brands(limit: int = 5, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener top marcas de aros por ventas"""
    pipeline = [
        {"$match": {"frame_id": {"$ne": None}, "status": {"$ne": "cancelado"}}},
        {"$lookup": {
            "from": "optica_frames",
            "localField": "frame_id",
            "foreignField": "id",
            "as": "frame"
        }},
        {"$unwind": "$frame"},
        {"$group": {
            "_id": "$frame.brand",
            "total_ventas": {"$sum": "$frame_price"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    
    results = await db.optica_sales.aggregate(pipeline).to_list(limit)
    
    return [{"brand": r["_id"], "total_ventas": r["total_ventas"], "count": r["count"]} for r in results]


@api_router.get("/optica/reports/monthly")
async def get_optica_monthly_report(
    year: int = None, 
    month: int = None, 
    format: str = "json",
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Obtener informe mensual de ventas de óptica"""
    now = datetime.now(timezone.utc)
    year = year or now.year
    month = month or now.month
    
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    
    # Obtener ventas del mes
    sales = await db.optica_sales.find({
        "created_at": {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()},
        "status": {"$ne": "cancelado"}
    }, {"_id": 0}).sort("created_at", 1).to_list(1000)
    
    # Enriquecer con nombres
    for sale in sales:
        if sale.get("patient_id"):
            patient = await db.patients.find_one({"id": sale["patient_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
            if patient:
                sale["patient_name"] = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
        if sale.get("doctor_id"):
            doctor = await db.doctors.find_one({"id": sale["doctor_id"]}, {"_id": 0, "name": 1})
            if doctor:
                sale["doctor_name"] = doctor.get("name", "")
    
    # Calcular totales
    total_ventas = sum(s.get("total", 0) for s in sales)
    total_cobrado = sum(s.get("paid_amount", 0) for s in sales)
    total_pendiente = total_ventas - total_cobrado
    
    report_data = {
        "year": year,
        "month": month,
        "month_name": ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                      "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][month],
        "total_ventas": total_ventas,
        "total_cobrado": total_cobrado,
        "total_pendiente": total_pendiente,
        "count": len(sales),
        "sales": sales
    }
    
    if format == "json":
        return report_data
    
    # Generar Excel
    if format == "excel":
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from io import BytesIO
        
        wb = Workbook()
        ws = wb.active
        ws.title = f"Ventas {report_data['month_name']} {year}"
        
        # Estilos
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0F6E56", end_color="0F6E56", fill_type="solid")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Título
        ws.merge_cells('A1:H1')
        ws['A1'] = f"Informe de Ventas Óptica - {report_data['month_name']} {year}"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # Resumen
        ws['A3'] = "Total Ventas:"
        ws['B3'] = total_ventas
        ws['B3'].number_format = '"Q"#,##0.00'
        ws['A4'] = "Total Cobrado:"
        ws['B4'] = total_cobrado
        ws['B4'].number_format = '"Q"#,##0.00'
        ws['A5'] = "Saldo Pendiente:"
        ws['B5'] = total_pendiente
        ws['B5'].number_format = '"Q"#,##0.00'
        ws['A6'] = "Total Órdenes:"
        ws['B6'] = len(sales)
        
        # Headers de tabla
        headers = ["Fecha", "Paciente", "Médico", "Aro", "Lentes", "Subtotal", "Descuento", "Total", "Pagado", "Pendiente", "Estado"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=8, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='center')
        
        # Datos
        for row_num, sale in enumerate(sales, 9):
            ws.cell(row=row_num, column=1, value=sale.get("created_at", "")[:10]).border = border
            ws.cell(row=row_num, column=2, value=sale.get("patient_name", "")).border = border
            ws.cell(row=row_num, column=3, value=sale.get("doctor_name", "")).border = border
            ws.cell(row=row_num, column=4, value=sale.get("frame_info", "")).border = border
            ws.cell(row=row_num, column=5, value=", ".join([l.get("name", "") for l in sale.get("lens_items", [])])).border = border
            
            subtotal_cell = ws.cell(row=row_num, column=6, value=sale.get("subtotal", 0))
            subtotal_cell.number_format = '"Q"#,##0.00'
            subtotal_cell.border = border
            
            discount_cell = ws.cell(row=row_num, column=7, value=f"{sale.get('discount_percent', 0)}%")
            discount_cell.border = border
            
            total_cell = ws.cell(row=row_num, column=8, value=sale.get("total", 0))
            total_cell.number_format = '"Q"#,##0.00'
            total_cell.border = border
            
            paid_cell = ws.cell(row=row_num, column=9, value=sale.get("paid_amount", 0))
            paid_cell.number_format = '"Q"#,##0.00'
            paid_cell.border = border
            
            pending = sale.get("total", 0) - sale.get("paid_amount", 0)
            pending_cell = ws.cell(row=row_num, column=10, value=pending)
            pending_cell.number_format = '"Q"#,##0.00'
            pending_cell.border = border
            
            status_labels = {"pendiente": "Pendiente", "pagado": "Pagado", "cancelado": "Cancelado"}
            ws.cell(row=row_num, column=11, value=status_labels.get(sale.get("status", ""), sale.get("status", ""))).border = border
        
        # Ajustar anchos
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 25
        ws.column_dimensions['E'].width = 30
        ws.column_dimensions['F'].width = 12
        ws.column_dimensions['G'].width = 10
        ws.column_dimensions['H'].width = 12
        ws.column_dimensions['I'].width = 12
        ws.column_dimensions['J'].width = 12
        ws.column_dimensions['K'].width = 12
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=ventas_optica_{year}_{month:02d}.xlsx"}
        )
    
    # Generar PDF
    if format == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
        elements.append(Paragraph(f"Informe de Ventas Óptica - {report_data['month_name']} {year}", title_style))
        elements.append(Spacer(1, 20))
        
        # Resumen
        summary_data = [
            ["Total Ventas", f"Q {total_ventas:,.2f}"],
            ["Total Cobrado", f"Q {total_cobrado:,.2f}"],
            ["Saldo Pendiente", f"Q {total_pendiente:,.2f}"],
            ["Total Órdenes", str(len(sales))]
        ]
        summary_table = Table(summary_data, colWidths=[150, 150])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Tabla de ventas
        table_data = [["Fecha", "Paciente", "Médico", "Total", "Pagado", "Pendiente", "Estado"]]
        for sale in sales:
            pending = sale.get("total", 0) - sale.get("paid_amount", 0)
            status_labels = {"pendiente": "Pendiente", "pagado": "Pagado", "cancelado": "Cancelado"}
            table_data.append([
                sale.get("created_at", "")[:10],
                sale.get("patient_name", "")[:25],
                sale.get("doctor_name", "")[:20],
                f"Q {sale.get('total', 0):,.2f}",
                f"Q {sale.get('paid_amount', 0):,.2f}",
                f"Q {pending:,.2f}",
                status_labels.get(sale.get("status", ""), sale.get("status", ""))
            ])
        
        if len(table_data) > 1:
            sales_table = Table(table_data, colWidths=[70, 140, 120, 80, 80, 80, 70])
            sales_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F6E56')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F9F6')])
            ]))
            elements.append(sales_table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=ventas_optica_{year}_{month:02d}.pdf"}
        )
    
    return report_data


# ==================== OPTICA PURCHASES ROUTES ====================

class OpticaPurchaseBase(BaseModel):
    supplier_id: Optional[str] = None
    category: str  # aros, lentes_contacto, cristales, accesorios, insumos, otros
    description: str
    quantity: int = 1
    unit_price: float = 0
    total: float
    invoice_number: Optional[str] = None
    purchase_date: str
    notes: Optional[str] = ""

class OpticaPurchaseCreate(OpticaPurchaseBase):
    pass

class OpticaPurchaseUpdate(BaseModel):
    supplier_id: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None
    invoice_number: Optional[str] = None
    purchase_date: Optional[str] = None
    notes: Optional[str] = None

class OpticaPurchaseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    category: str
    description: str
    quantity: int
    unit_price: float
    total: float
    invoice_number: Optional[str] = None
    purchase_date: str
    notes: Optional[str] = ""
    created_at: str
    updated_at: str

class OpticaPurchaseListResponse(BaseModel):
    data: List[OpticaPurchaseResponse]
    total: int


@api_router.get("/optica/purchases", response_model=OpticaPurchaseListResponse)
async def get_optica_purchases(
    search: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_optica"))
):
    """Obtener lista de compras de óptica"""
    query = {}
    
    if search:
        query["$or"] = [
            {"description": {"$regex": search, "$options": "i"}},
            {"invoice_number": {"$regex": search, "$options": "i"}}
        ]
    
    if category:
        query["category"] = category
    
    purchases = await db.optica_purchases.find(query, {"_id": 0}).sort("purchase_date", -1).to_list(500)
    
    # Enriquecer con nombre de proveedor
    for purchase in purchases:
        if purchase.get("supplier_id"):
            supplier = await db.suppliers.find_one({"id": purchase["supplier_id"]}, {"_id": 0, "name": 1})
            purchase["supplier_name"] = supplier.get("name") if supplier else None
        else:
            purchase["supplier_name"] = None
    
    return {"data": purchases, "total": len(purchases)}


@api_router.get("/optica/purchases/{purchase_id}", response_model=OpticaPurchaseResponse)
async def get_optica_purchase(purchase_id: str, current_user: dict = Depends(require_permission("view_optica"))):
    """Obtener detalle de una compra"""
    purchase = await db.optica_purchases.find_one({"id": purchase_id}, {"_id": 0})
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    if purchase.get("supplier_id"):
        supplier = await db.suppliers.find_one({"id": purchase["supplier_id"]}, {"_id": 0, "name": 1})
        purchase["supplier_name"] = supplier.get("name") if supplier else None
    
    return purchase


@api_router.post("/optica/purchases", response_model=OpticaPurchaseResponse)
async def create_optica_purchase(
    purchase: OpticaPurchaseCreate,
    current_user: dict = Depends(require_permission("manage_optica_inventory"))
):
    """Crear una nueva compra de óptica"""
    now = datetime.now(timezone.utc).isoformat()
    
    new_purchase = {
        "id": str(uuid.uuid4()),
        **purchase.model_dump(),
        "created_at": now,
        "updated_at": now,
        "created_by": current_user["id"]
    }
    
    await db.optica_purchases.insert_one(new_purchase)
    del new_purchase["_id"]
    
    # Agregar nombre del proveedor
    if new_purchase.get("supplier_id"):
        supplier = await db.suppliers.find_one({"id": new_purchase["supplier_id"]}, {"_id": 0, "name": 1})
        new_purchase["supplier_name"] = supplier.get("name") if supplier else None
    else:
        new_purchase["supplier_name"] = None
    
    return new_purchase


@api_router.put("/optica/purchases/{purchase_id}", response_model=OpticaPurchaseResponse)
async def update_optica_purchase(
    purchase_id: str,
    purchase: OpticaPurchaseUpdate,
    current_user: dict = Depends(require_permission("manage_optica_inventory"))
):
    """Actualizar una compra de óptica"""
    existing = await db.optica_purchases.find_one({"id": purchase_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    update_data = {k: v for k, v in purchase.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.optica_purchases.update_one({"id": purchase_id}, {"$set": update_data})
    
    updated = await db.optica_purchases.find_one({"id": purchase_id}, {"_id": 0})
    
    if updated.get("supplier_id"):
        supplier = await db.suppliers.find_one({"id": updated["supplier_id"]}, {"_id": 0, "name": 1})
        updated["supplier_name"] = supplier.get("name") if supplier else None
    else:
        updated["supplier_name"] = None
    
    return updated


@api_router.delete("/optica/purchases/{purchase_id}")
async def delete_optica_purchase(
    purchase_id: str,
    current_user: dict = Depends(require_permission("manage_optica_inventory"))
):
    """Eliminar una compra de óptica"""
    existing = await db.optica_purchases.find_one({"id": purchase_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    await db.optica_purchases.delete_one({"id": purchase_id})
    
    return {"message": "Compra eliminada correctamente"}


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
        auth["expense_number"] = expense.get("expense_number", "")  # Número correlativo
    
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
    
    # Verificar que el gasto todavía existe y tiene saldo
    expense = await db.expenses.find_one({"id": auth["expense_id"]}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="El gasto asociado ya no existe")
    
    remaining = expense.get("remaining_amount", expense["amount"])
    
    # Si el gasto ya está completamente pagado, cancelar la autorización automáticamente
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
        updated = await db.payment_authorizations.find_one({"id": auth_id}, {"_id": 0})
        enriched = await enrich_authorization(updated)
        # Retornar respuesta especial indicando que se canceló
        raise HTTPException(
            status_code=400, 
            detail=f"El gasto ya fue pagado completamente. La autorización ha sido cancelada automáticamente."
        )
    
    # Determinar el monto a pagar (usar el menor entre lo autorizado y lo pendiente)
    amount_to_pay = min(auth["amount_to_pay"], remaining)
    amount_adjusted = amount_to_pay < auth["amount_to_pay"]
    
    # Obtener información de la cuenta bancaria para la referencia
    bank_account = await db.bank_accounts.find_one({"id": auth["bank_account_id"]}, {"_id": 0})
    bank_ref = f"{bank_account['bank_name']} - {bank_account['account_alias']}" if bank_account else "N/A"
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Mapeo de métodos de pago a etiquetas legibles
    payment_method_labels = {
        "transferencia": "Transferencia bancaria",
        "efectivo": "Efectivo",
        "cheque": "Cheque",
        "tarjeta": "Tarjeta de crédito/débito",
        "otro": "Otro"
    }
    
    # Usar el método de pago proporcionado o el valor por defecto
    method_label = payment_method_labels.get(payment_method, "Transferencia bancaria")
    
    # Construir referencia
    payment_reference = reference if reference else f"Auth: {auth_id[:8]} | Cuenta: {bank_ref}"
    
    # Crear el pago real (con monto ajustado si es necesario)
    adjustment_note = f" [Ajustado de Q{auth['amount_to_pay']:.2f} a Q{amount_to_pay:.2f}]" if amount_adjusted else ""
    user_notes = notes if notes else ""
    combined_notes = f"Pago autorizado.{adjustment_note} {user_notes}".strip()
    
    payment_doc = {
        "id": str(uuid.uuid4()),
        "expense_id": auth["expense_id"],
        "amount": amount_to_pay,
        "date": now.split("T")[0],  # Solo fecha
        "method": method_label,
        "reference": payment_reference,
        "notes": combined_notes,
        "created_by": current_user["id"],
        "created_at": now
    }
    
    await db.payments.insert_one(payment_doc)
    
    # Actualizar montos del gasto
    await update_expense_amounts(auth["expense_id"])
    
    # Preparar datos de actualización de la autorización
    auth_update = {
        "status": "ejecutado",
        "executed_by": current_user["id"],
        "executed_at": now,
        "updated_at": now
    }
    
    # Si el monto fue ajustado, agregar nota
    if amount_adjusted:
        auth_update["notes"] = f"{auth.get('notes', '')} [Ejecutado con monto ajustado: Q{amount_to_pay:.2f} de Q{auth['amount_to_pay']:.2f}]".strip()
    
    # Actualizar la autorización a ejecutado
    await db.payment_authorizations.update_one(
        {"id": auth_id},
        {"$set": auth_update}
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


# ==================== SURGERY ROUTES (Sala de Operaciones) ====================

async def enrich_surgery(surgery: dict) -> dict:
    """Enriquecer cirugía con nombre del creador"""
    if surgery.get("created_by"):
        user = await db.users.find_one({"id": surgery["created_by"]}, {"_id": 0, "full_name": 1})
        surgery["created_by_name"] = user.get("full_name") if user else None
    return surgery

@api_router.get("/surgeries", response_model=SurgeryListResponse)
async def get_surgeries(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    surgeon: Optional[str] = None,
    institution: Optional[str] = None,
    eye: Optional[str] = None,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    sort_by: str = Query("date", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
    current_user: dict = Depends(get_current_user)
):
    """Listar cirugías con filtros y paginación"""
    query = {}
    
    if search:
        query["$or"] = [
            {"patient_name": {"$regex": search, "$options": "i"}},
            {"procedure": {"$regex": search, "$options": "i"}},
            {"surgeon": {"$regex": search, "$options": "i"}}
        ]
    
    if surgeon:
        query["surgeon"] = {"$regex": surgeon, "$options": "i"}
    
    if institution:
        query["institution"] = institution
    
    if eye:
        query["eye"] = eye
    
    if date_from:
        query["date"] = query.get("date", {})
        query["date"]["$gte"] = date_from
    
    if date_to:
        query["date"] = query.get("date", {})
        query["date"]["$lte"] = date_to
    
    # Ordenamiento
    sort_direction = -1 if sort_order == "desc" else 1
    sort_field = sort_by if sort_by in ["date", "patient_name", "surgeon", "institution"] else "date"
    
    total = await db.surgeries.count_documents(query)
    skip = (page - 1) * limit
    
    cursor = db.surgeries.find(query, {"_id": 0}).sort([(sort_field, sort_direction), ("time", sort_direction)]).skip(skip).limit(limit)
    surgeries = await cursor.to_list(length=limit)
    
    # Enriquecer
    enriched = [await enrich_surgery(s) for s in surgeries]
    
    return SurgeryListResponse(
        data=enriched,
        total=total,
        page=page,
        limit=limit,
        total_pages=(total + limit - 1) // limit
    )

@api_router.get("/surgeries/options")
async def get_surgery_options(current_user: dict = Depends(get_current_user)):
    """Obtener opciones únicas para filtros (cirujanos, instituciones, anestesiólogos)"""
    surgeons = await db.surgeries.distinct("surgeon")
    institutions = await db.surgeries.distinct("institution")
    anesthesiologists = await db.surgeries.distinct("anesthesiologist")
    
    return {
        "surgeons": sorted([s for s in surgeons if s]),
        "institutions": sorted([i for i in institutions if i]),
        "anesthesiologists": sorted([a for a in anesthesiologists if a])
    }

@api_router.get("/surgeries/{surgery_id}", response_model=SurgeryResponse)
async def get_surgery(surgery_id: str, current_user: dict = Depends(get_current_user)):
    """Obtener detalle de una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    enriched = await enrich_surgery(surgery)
    return SurgeryResponse(**enriched)

@api_router.post("/surgeries", response_model=SurgeryResponse)
async def create_surgery(
    surgery: SurgeryCreate,
    current_user: dict = Depends(require_permission("create_expenses"))
):
    """Registrar nueva cirugía"""
    # Validar campos IGSS si la institución es IGSS
    if surgery.institution == "IGSS":
        if not surgery.igss_data:
            raise HTTPException(status_code=400, detail="Los datos IGSS son requeridos")
        igss = surgery.igss_data
        if not all([igss.unit, igss.sps, igss.affiliation_number, igss.code, igss.procedure_cost is not None]):
            raise HTTPException(status_code=400, detail="Todos los campos IGSS son obligatorios")
    
    now = datetime.now(timezone.utc).isoformat()
    
    surgery_doc = {
        "id": str(uuid.uuid4()),
        **surgery.model_dump(),
        "equipment": [],
        "supplies": [],
        "status": "activo",
        "cancellation_reason": None,
        "rescheduled_to": None,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.surgeries.insert_one(surgery_doc)
    
    created = await db.surgeries.find_one({"id": surgery_doc["id"]}, {"_id": 0})
    enriched = await enrich_surgery(created)
    return SurgeryResponse(**enriched)

@api_router.put("/surgeries/{surgery_id}", response_model=SurgeryResponse)
async def update_surgery(
    surgery_id: str,
    surgery: SurgeryUpdate,
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Editar cirugía"""
    existing = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    update_data = surgery.model_dump(exclude_unset=True)
    
    # Validar campos IGSS si se cambia a IGSS
    new_institution = update_data.get("institution", existing.get("institution"))
    if new_institution == "IGSS":
        igss = update_data.get("igss_data", existing.get("igss_data"))
        if not igss:
            raise HTTPException(status_code=400, detail="Los datos IGSS son requeridos")
        if isinstance(igss, dict):
            if not all([igss.get("unit"), igss.get("sps"), igss.get("affiliation_number"), igss.get("code"), igss.get("procedure_cost") is not None]):
                raise HTTPException(status_code=400, detail="Todos los campos IGSS son obligatorios")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.surgeries.update_one({"id": surgery_id}, {"$set": update_data})
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)

@api_router.delete("/surgeries/{surgery_id}")
async def delete_surgery(
    surgery_id: str,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Eliminar cirugía (solo superadmin)"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    await db.surgeries.delete_one({"id": surgery_id})
    return {"message": "Cirugía eliminada correctamente"}

@api_router.post("/surgeries/{surgery_id}/cancel")
async def cancel_surgery(
    surgery_id: str,
    reason: str = Body(..., embed=True),
    reschedule_date: Optional[str] = Body(None, embed=True),
    current_user: dict = Depends(require_role("superadmin"))
):
    """Cancelar cirugía con motivo (solo superadmin)"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    update_data = {
        "status": "cancelado",
        "cancellation_reason": reason,
        "rescheduled_to": reschedule_date,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.surgeries.update_one({"id": surgery_id}, {"$set": update_data})
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)

# ---- Equipo ----

@api_router.post("/surgeries/{surgery_id}/equipment")
async def add_equipment(
    surgery_id: str,
    name: str = Body(...),
    quantity: int = Body(1),
    notes: str = Body(""),
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Agregar equipo a una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    equipment_item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "quantity": quantity,
        "notes": notes,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "added_by": current_user["id"]
    }
    
    await db.surgeries.update_one(
        {"id": surgery_id},
        {
            "$push": {"equipment": equipment_item},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)

@api_router.delete("/surgeries/{surgery_id}/equipment/{equipment_id}")
async def delete_equipment(
    surgery_id: str,
    equipment_id: str,
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Eliminar equipo de una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    await db.surgeries.update_one(
        {"id": surgery_id},
        {
            "$pull": {"equipment": {"id": equipment_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)

# ---- Insumos ----

@api_router.post("/surgeries/{surgery_id}/supplies")
async def add_supply(
    surgery_id: str,
    name: str = Body(...),
    category: str = Body("otro"),
    quantity: int = Body(1),
    unit_cost: float = Body(0),
    notes: str = Body(""),
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Agregar insumo a una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    supply_item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "category": category,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "total_cost": quantity * unit_cost,
        "notes": notes,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "added_by": current_user["id"]
    }
    
    await db.surgeries.update_one(
        {"id": surgery_id},
        {
            "$push": {"supplies": supply_item},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)

@api_router.put("/surgeries/{surgery_id}/supplies/{supply_id}")
async def update_supply(
    surgery_id: str,
    supply_id: str,
    quantity: Optional[int] = Body(None),
    unit_cost: Optional[float] = Body(None),
    notes: Optional[str] = Body(None),
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Editar insumo de una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    supplies = surgery.get("supplies", [])
    supply_index = next((i for i, s in enumerate(supplies) if s.get("id") == supply_id), None)
    
    if supply_index is None:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    
    supply = supplies[supply_index]
    
    if quantity is not None:
        supply["quantity"] = quantity
    if unit_cost is not None:
        supply["unit_cost"] = unit_cost
    if notes is not None:
        supply["notes"] = notes
    
    supply["total_cost"] = supply["quantity"] * supply["unit_cost"]
    
    supplies[supply_index] = supply
    
    await db.surgeries.update_one(
        {"id": surgery_id},
        {"$set": {"supplies": supplies, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)

@api_router.delete("/surgeries/{surgery_id}/supplies/{supply_id}")
async def delete_supply(
    surgery_id: str,
    supply_id: str,
    current_user: dict = Depends(require_permission("edit_expenses"))
):
    """Eliminar insumo de una cirugía"""
    surgery = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    await db.surgeries.update_one(
        {"id": surgery_id},
        {
            "$pull": {"supplies": {"id": supply_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    updated = await db.surgeries.find_one({"id": surgery_id}, {"_id": 0})
    enriched = await enrich_surgery(updated)
    return SurgeryResponse(**enriched)


# ==================== SURGERY REPORTS ====================

@api_router.get("/reports/surgeries")
async def export_surgeries(
    format: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    surgeon: Optional[str] = None,
    institution: Optional[str] = None,
    eye: Optional[str] = None,
    current_user: dict = Depends(require_permission("export_reports"))
):
    """Exportar cirugías a Excel o PDF"""
    query = {"status": {"$ne": "cancelado"}}  # Excluir cirugías canceladas
    
    if surgeon:
        query["surgeon"] = surgeon
    if institution:
        query["institution"] = institution
    if eye:
        query["eye"] = eye
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["date"] = date_query
    
    surgeries = await db.surgeries.find(query, {"_id": 0}).sort([("date", -1), ("time", -1)]).to_list(10000)
    
    # Helper para calcular totales
    def get_supplies_total(supplies):
        return sum(s.get("total_cost", 0) for s in (supplies or []))
    
    def get_total_general(surgery):
        procedure_cost = surgery.get("igss_data", {}).get("procedure_cost", 0) if surgery.get("igss_data") else 0
        supplies_total = get_supplies_total(surgery.get("supplies", []))
        return procedure_cost + supplies_total
    
    if format == "xlsx":
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Cirugías"
            
            # Estilos
            header_fill = PatternFill(start_color="0d9488", end_color="0d9488", fill_type="solid")  # Teal
            header_font = Font(color="FFFFFF", bold=True, size=10)
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Headers
            headers = ["Fecha", "Hora", "Paciente", "Procedimiento", "Cirujano", "Ojo", "Anestesia", "Institución", "Costo Proc.", "Insumos", "Total", "Equipo", "Observaciones"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = thin_border
            
            # Formato moneda
            currency_format = 'Q #,##0.00'
            
            # Datos
            anesthesia_labels = {
                "local": "Local", "topica": "Tópica", "general": "General",
                "retrobulbar": "Retrobulbar", "peribulbar": "Peribulbar", "sedacion": "Sedación"
            }
            
            for row, s in enumerate(surgeries, 2):
                ws.cell(row=row, column=1, value=s["date"]).border = thin_border
                ws.cell(row=row, column=2, value=s["time"]).border = thin_border
                ws.cell(row=row, column=3, value=s["patient_name"]).border = thin_border
                ws.cell(row=row, column=4, value=s["procedure"]).border = thin_border
                ws.cell(row=row, column=5, value=s["surgeon"]).border = thin_border
                ws.cell(row=row, column=6, value=s["eye"]).border = thin_border
                ws.cell(row=row, column=7, value=anesthesia_labels.get(s.get("anesthesia_type", ""), s.get("anesthesia_type", ""))).border = thin_border
                ws.cell(row=row, column=8, value=s["institution"]).border = thin_border
                
                # Costo del procedimiento
                proc_cost = s.get("igss_data", {}).get("procedure_cost", 0) if s.get("igss_data") else 0
                cell_proc = ws.cell(row=row, column=9, value=proc_cost)
                cell_proc.border = thin_border
                cell_proc.number_format = currency_format
                
                # Total insumos
                supplies_total = get_supplies_total(s.get("supplies", []))
                cell_supplies = ws.cell(row=row, column=10, value=supplies_total)
                cell_supplies.border = thin_border
                cell_supplies.number_format = currency_format
                
                # Total general
                total = get_total_general(s)
                cell_total = ws.cell(row=row, column=11, value=total)
                cell_total.border = thin_border
                cell_total.number_format = currency_format
                cell_total.font = Font(bold=True)
                
                # Equipo (lista separada por comas)
                equipment_list = ", ".join([eq["name"] for eq in s.get("equipment", [])])
                ws.cell(row=row, column=12, value=equipment_list).border = thin_border
                
                # Observaciones
                ws.cell(row=row, column=13, value=s.get("observations", "")).border = thin_border
            
            # Ajustar anchos de columna
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 8
            ws.column_dimensions['C'].width = 28
            ws.column_dimensions['D'].width = 25
            ws.column_dimensions['E'].width = 20
            ws.column_dimensions['F'].width = 6
            ws.column_dimensions['G'].width = 12
            ws.column_dimensions['H'].width = 15
            ws.column_dimensions['I'].width = 12
            ws.column_dimensions['J'].width = 12
            ws.column_dimensions['K'].width = 12
            ws.column_dimensions['L'].width = 35
            ws.column_dimensions['M'].width = 30
            
            # Fila de totales
            total_row = len(surgeries) + 2
            ws.cell(row=total_row, column=8, value="TOTALES:").font = Font(bold=True)
            
            total_proc = sum(s.get("igss_data", {}).get("procedure_cost", 0) if s.get("igss_data") else 0 for s in surgeries)
            total_supplies = sum(get_supplies_total(s.get("supplies", [])) for s in surgeries)
            total_general = sum(get_total_general(s) for s in surgeries)
            
            cell_total_proc = ws.cell(row=total_row, column=9, value=total_proc)
            cell_total_proc.number_format = currency_format
            cell_total_proc.font = Font(bold=True)
            
            cell_total_supplies = ws.cell(row=total_row, column=10, value=total_supplies)
            cell_total_supplies.number_format = currency_format
            cell_total_supplies.font = Font(bold=True)
            
            cell_total_all = ws.cell(row=total_row, column=11, value=total_general)
            cell_total_all.number_format = currency_format
            cell_total_all.font = Font(bold=True, color="0d9488")
            
            # Guardar
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=cirugias_novavision.xlsx"}
            )
        except ImportError:
            raise HTTPException(status_code=500, detail="Librería openpyxl no disponible")
    
    else:
        # PDF format
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            
            output = io.BytesIO()
            doc = SimpleDocTemplate(
                output, 
                pagesize=landscape(letter),
                rightMargin=0.4*inch,
                leftMargin=0.4*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )
            
            elements = []
            styles = getSampleStyleSheet()
            
            # Estilos personalizados
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=8,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#0d9488')
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=15,
                alignment=TA_CENTER,
                textColor=colors.grey
            )
            
            # Título
            elements.append(Paragraph("NovaVision — Reporte de Cirugías", title_style))
            
            # Subtítulo
            generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            filters_text = []
            if date_from:
                filters_text.append(f"Desde: {date_from}")
            if date_to:
                filters_text.append(f"Hasta: {date_to}")
            if surgeon:
                filters_text.append(f"Cirujano: {surgeon}")
            if institution:
                filters_text.append(f"Institución: {institution}")
            
            filter_str = " | ".join(filters_text) if filters_text else "Todas las cirugías"
            elements.append(Paragraph(
                f"Generado: {generated_at} | Usuario: {current_user.get('name', 'N/A')} | {filter_str}",
                subtitle_style
            ))
            
            elements.append(Spacer(1, 0.15*inch))
            
            # Etiquetas
            anesthesia_labels = {
                "local": "Local", "topica": "Tópica", "general": "General",
                "retrobulbar": "Retrob.", "peribulbar": "Perib.", "sedacion": "Sedación"
            }
            
            # Datos de la tabla
            table_data = [["Fecha", "Hora", "Paciente", "Procedimiento", "Cirujano", "Ojo", "Anest.", "Institución", "Costo Proc.", "Insumos", "Total"]]
            
            for s in surgeries:
                proc_cost = s.get("igss_data", {}).get("procedure_cost", 0) if s.get("igss_data") else 0
                supplies_total = get_supplies_total(s.get("supplies", []))
                total = get_total_general(s)
                
                table_data.append([
                    s["date"],
                    s["time"],
                    s["patient_name"][:25] + "..." if len(s["patient_name"]) > 25 else s["patient_name"],
                    s["procedure"][:20] + "..." if len(s["procedure"]) > 20 else s["procedure"],
                    s["surgeon"][:18] + "..." if len(s["surgeon"]) > 18 else s["surgeon"],
                    s["eye"],
                    anesthesia_labels.get(s.get("anesthesia_type", ""), s.get("anesthesia_type", "")[:6]),
                    s["institution"][:12] + "..." if len(s["institution"]) > 12 else s["institution"],
                    f'Q {proc_cost:,.2f}',
                    f'Q {supplies_total:,.2f}',
                    f'Q {total:,.2f}'
                ])
            
            # Crear tabla
            col_widths = [0.7*inch, 0.5*inch, 1.5*inch, 1.2*inch, 1.1*inch, 0.4*inch, 0.55*inch, 0.8*inch, 0.75*inch, 0.75*inch, 0.75*inch]
            table = Table(table_data, colWidths=col_widths)
            
            # Estilo de tabla
            table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d9488')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                
                # Data
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Ojo
                ('ALIGN', (8, 1), (10, -1), 'RIGHT'),  # Montos
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                
                # Filas alternadas
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdfa')]),
                
                # Bordes
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0d9488')),
            ]))
            
            elements.append(table)
            
            # Resumen
            total_proc = sum(s.get("igss_data", {}).get("procedure_cost", 0) if s.get("igss_data") else 0 for s in surgeries)
            total_supplies = sum(get_supplies_total(s.get("supplies", [])) for s in surgeries)
            total_general = sum(get_total_general(s) for s in surgeries)
            
            elements.append(Spacer(1, 0.2*inch))
            
            summary_style = ParagraphStyle(
                'Summary',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_RIGHT
            )
            
            elements.append(Paragraph(
                f"<b>Total Procedimientos:</b> Q {total_proc:,.2f} | <b>Total Insumos:</b> Q {total_supplies:,.2f} | <b>TOTAL GENERAL:</b> Q {total_general:,.2f}",
                summary_style
            ))
            
            elements.append(Paragraph(
                f"<b>Total de cirugías:</b> {len(surgeries)}",
                summary_style
            ))
            
            # Construir PDF
            doc.build(elements)
            output.seek(0)
            
            return StreamingResponse(
                output,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=cirugias_novavision.pdf"}
            )
            
        except ImportError as e:
            raise HTTPException(status_code=500, detail=f"Librería PDF no disponible: {str(e)}")


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

# ==================== MIDDLEWARES DE SEGURIDAD ====================

# Agregar middleware de headers de seguridad PRIMERO
app.add_middleware(SecurityHeadersMiddleware)

# CORS con orígenes específicos (NO usar '*' en producción)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
    max_age=600,  # Cache preflight por 10 minutos
)

# Configure logging con formato seguro
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
    today_str = today.strftime("%Y-%m-%d")
    
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
        
        # Verificar si el gasto fijo ha expirado (tiene fecha de fin y ya pasó)
        end_date = fe.get("end_date")
        duration_type = fe.get("duration_type", "ilimitado")
        
        if duration_type == "hasta_fecha" and end_date:
            if today_str > end_date:
                logger.info(f"Gasto fijo {fe['id']} ha expirado (fecha fin: {end_date}), desactivando...")
                # Desactivar el gasto fijo automáticamente
                await db.fixed_expenses.update_one(
                    {"id": fe["id"]},
                    {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                continue
        
        # Obtener el proveedor para el nombre
        supplier = await db.suppliers.find_one({"id": fe["supplier_id"]}, {"_id": 0})
        supplier_name = supplier["name"] if supplier else "Proveedor"
        
        # Calcular fecha de vencimiento (+30 días)
        expense_date = today.strftime("%Y-%m-%d")
        due_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Generar número correlativo automático
        expense_number = await get_next_expense_number()
        
        # Crear el gasto
        expense_doc = {
            "id": str(uuid.uuid4()),
            "expense_number": expense_number,  # Número correlativo automático
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
    
    # Limpiar tokens expirados cada 6 horas
    scheduler.add_job(
        cleanup_expired_tokens,
        CronTrigger(hour="*/6"),
        id="cleanup_expired_tokens",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler iniciado (gastos fijos: 00:05 diario, limpieza tokens: cada 6h)")


@app.on_event("startup")
async def startup_event():
    """Run seed on startup and create indexes"""
    await seed_default_users()
    await seed_sample_expenses()
    await seed_sample_patients()
    await seed_optica_data()
    
    # ==================== ÍNDICES DE SEGURIDAD ====================
    # Índice para blacklist de tokens con TTL
    await db.token_blacklist.create_index([("token", 1)], unique=True)
    await db.token_blacklist.create_index([("expires_at", 1)])
    
    # Índice para audit logs
    await db.audit_logs.create_index([("timestamp", -1)])
    await db.audit_logs.create_index([("action", 1)])
    await db.audit_logs.create_index([("user_id", 1)])
    
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
    # Índices de Óptica
    await db.doctors.create_index([("name", 1)])
    await db.doctors.create_index([("is_active", 1)])
    await db.optica_frames.create_index([("code", 1)], unique=True)
    await db.optica_frames.create_index([("brand", 1)])
    await db.optica_frames.create_index([("is_active", 1)])
    await db.optica_contact_lenses.create_index([("lens_type", 1)])
    await db.optica_contact_lenses.create_index([("is_active", 1)])
    await db.optica_lens_types.create_index([("name", 1)])
    await db.optica_sales.create_index([("order_number", 1)], unique=True)
    await db.optica_sales.create_index([("patient_id", 1)])
    await db.optica_sales.create_index([("status", 1)])
    await db.optica_sales.create_index([("created_at", -1)])
    await db.optica_sale_payments.create_index([("sale_id", 1)])
    # Índices de Sala de Operaciones
    await db.surgeries.create_index([("date", -1)])
    await db.surgeries.create_index([("surgeon", 1)])
    await db.surgeries.create_index([("institution", 1)])
    await db.surgeries.create_index([("patient_name", "text"), ("procedure", "text")])
    # Seed de cirugías
    await seed_surgeries_data()
    
    # Índices de Evaluaciones Oftalmológicas
    await db.evaluaciones_oftalmologicas.create_index([("paciente_id", 1)])
    await db.evaluaciones_oftalmologicas.create_index([("fecha", -1)])
    await db.evaluaciones_oftalmologicas.create_index([("fecha_creacion", -1)])
    await db.evaluaciones_oftalmologicas.create_index([("sellado", 1)])
    await db.evaluaciones_oftalmologicas.create_index([("medico_id", 1)])
    
    # Índices de Catálogos
    await db.catalogo_medicamentos.create_index([("nombre", 1)], unique=True)
    await db.catalogo_medicamentos.create_index([("usos", -1)])
    await db.catalogo_estudios.create_index([("nombre", 1)], unique=True)
    await db.catalogo_estudios.create_index([("usos", -1)])
    await db.catalogo_diagnosticos.create_index([("nombre", 1)], unique=True)
    await db.catalogo_diagnosticos.create_index([("usos", -1)])
    
    # Seed de catálogos oftalmológicos
    await seed_catalogos_oftalmologicos()
    
    try:
        await db.users.create_index([("username", 1)], unique=True)
    except Exception:
        pass  # Index may already exist
    
    # Iniciar scheduler
    start_scheduler()
    
    # Log de inicio del sistema
    logger.info("🔒 Sistema iniciado con configuración de seguridad activa")
    logger.info(f"   - CORS Origins: {ALLOWED_ORIGINS}")
    logger.info(f"   - JWT Expiration: {JWT_EXPIRATION_HOURS}h")
    logger.info(f"   - Security Headers: Enabled")
    logger.info(f"   - Audit Logging: Enabled")

@app.on_event("shutdown")
async def shutdown_db_client():
    scheduler.shutdown(wait=False)
    client.close()
