from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Request, Body, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.middleware.gzip import GZipMiddleware
from starlette.websockets import WebSocketState
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
import hashlib
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Dict, Set
import uuid
from datetime import datetime, timezone, timedelta
from utils.timezone import now_gt, GUATEMALA_TZ
import jwt
import bcrypt
import io
import json
import asyncio
from functools import lru_cache
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

# ==================== SECURITY CONFIGURATION ====================

# Rate Limiter con configuración más estricta
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings - CRÍTICO: No usar fallback en producción
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    if os.environ.get('ENVIRONMENT') == 'production':
        raise RuntimeError("❌ CRÍTICO: JWT_SECRET no configurado en producción. Configure en .env")
    # En desarrollo, generar un secret seguro temporal
    JWT_SECRET = secrets.token_urlsafe(64)
    logging.warning("⚠️ SEGURIDAD: JWT_SECRET no configurado. Usando valor temporal. Configure en .env para producción.")
elif JWT_SECRET in ['novavision_secret_key_2024', 'novavision_secure_secret_key_2024_gtq_production_v2', 'novavision-secret-key-2024-finanzas-seguro']:
    if os.environ.get('ENVIRONMENT') == 'production':
        raise RuntimeError("❌ CRÍTICO: JWT_SECRET es un valor conocido/publicado. Genere uno nuevo con: python -c \"import secrets; print(secrets.token_urlsafe(64))\" antes de desplegar a producción.")
    logging.warning("⚠️ SEGURIDAD: JWT_SECRET es un valor conocido. ROTE el secreto antes de producción con: python -c \"import secrets; print(secrets.token_urlsafe(64))\"")
elif len(JWT_SECRET) < 32:
    if os.environ.get('ENVIRONMENT') == 'production':
        raise RuntimeError("❌ CRÍTICO: JWT_SECRET demasiado corto para producción. Use 64+ caracteres.")
    logging.warning("⚠️ SEGURIDAD: JWT_SECRET demasiado corto. Recomendado: 64+ caracteres")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '8'))  # Por defecto 8 horas

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

# Middleware de compresión GZip para respuestas > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS Middleware - Configuración de seguridad para orígenes permitidos
# SEC-002: CORS debe estar correctamente configurado
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
    max_age=600,  # Cache preflight por 10 minutos
)

# Nota: SecurityHeadersMiddleware se agrega después de su definición (línea ~280)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()


# ==================== CACHE EN MEMORIA ====================

# Cache simple en memoria para consultas frecuentes
class SimpleCache:
    def __init__(self, default_ttl: int = 60):
        self._cache = {}
        self._timestamps = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str):
        if key in self._cache:
            if time.time() - self._timestamps.get(key, 0) < self.default_ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None
    
    def set(self, key: str, value, ttl: int = None):
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def invalidate(self, pattern: str = None):
        if pattern:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]
                del self._timestamps[key]
        else:
            self._cache.clear()
            self._timestamps.clear()

# Instancia global de caché (TTL: 30 segundos para datos dinámicos)
query_cache = SimpleCache(default_ttl=30)


# ==================== WEBSOCKET CONNECTION MANAGER ====================

class ConnectionManager:
    """Gestor de conexiones WebSocket para actualizaciones en tiempo real"""
    
    def __init__(self):
        # Conexiones por canal (caja, agenda, etc.)
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "caja": set(),
            "agenda": set(),
            "inventario": set(),
            "pos": set()
        }
        # Mapeo de websocket a usuario para tracking
        self.connection_users: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket, channel: str, user_info: dict = None):
        """Conectar un cliente a un canal específico"""
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        if user_info:
            self.connection_users[websocket] = user_info
        logging.info(f"WebSocket conectado al canal '{channel}'. Total: {len(self.active_connections[channel])}")
    
    def disconnect(self, websocket: WebSocket, channel: str):
        """Desconectar un cliente de un canal"""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        if websocket in self.connection_users:
            del self.connection_users[websocket]
        logging.info(f"WebSocket desconectado del canal '{channel}'. Total: {len(self.active_connections.get(channel, []))}")
    
    async def broadcast(self, channel: str, message: dict, exclude: WebSocket = None):
        """Enviar mensaje a todos los clientes conectados a un canal"""
        if channel not in self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections[channel]:
            if connection == exclude:
                continue
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
            except Exception as e:
                logging.warning(f"Error enviando mensaje WebSocket: {e}")
                disconnected.add(connection)
        
        # Limpiar conexiones muertas
        for conn in disconnected:
            self.active_connections[channel].discard(conn)
            if conn in self.connection_users:
                del self.connection_users[conn]
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """Enviar mensaje a un cliente específico"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as e:
            logging.warning(f"Error enviando mensaje personal: {e}")
    
    def get_channel_count(self, channel: str) -> int:
        """Obtener número de conexiones en un canal"""
        return len(self.active_connections.get(channel, []))

# Instancia global del gestor de conexiones
ws_manager = ConnectionManager()


# ==================== SECURITY MIDDLEWARE ====================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para agregar headers de seguridad y caché a todas las respuestas"""
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
        
        # Headers de caché para CDN y navegadores
        path = request.url.path
        
        # Assets estáticos: caché largo (1 año)
        if any(ext in path for ext in ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.ttf']):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            response.headers["Vary"] = "Accept-Encoding"
        
        # Archivos descargables: caché medio (1 hora)
        elif any(ext in path for ext in ['.xlsx', '.pdf', '.csv']):
            response.headers["Cache-Control"] = "public, max-age=3600"
        
        # API endpoints: NUNCA cachear datos dinámicos.
        # Con 10 usuarios en simultáneo, cachear listas (médicos, unidades IGSS,
        # catálogos) hacía que los cambios de un usuario no aparecieran a los
        # demás hasta que expiraba el caché (~5 min con directiva 'public').
        elif '/api/' in path:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response

# Agregar middleware de headers de seguridad a la aplicación
app.add_middleware(SecurityHeadersMiddleware)

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
        "view_audit_logs": True,
        # Permisos clínicos
        "view_agenda": True,
        "view_evaluacion": True,
        "manage_recetas": True,
        "view_sala_operaciones": True
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
        "view_audit_logs": False,
        # Permisos clínicos
        "view_agenda": True,
        "view_evaluacion": True,
        "manage_recetas": True,
        "view_sala_operaciones": True
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
        "view_audit_logs": False,
        # Permisos clínicos
        "view_agenda": True,
        "view_evaluacion": True,
        "manage_recetas": False,
        "view_sala_operaciones": False
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
        "view_audit_logs": False,
        # Permisos clínicos
        "view_agenda": False,
        "view_evaluacion": False,
        "manage_recetas": False,
        "view_sala_operaciones": False
    },
    "medico": {
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
        # Permisos de Pacientes (crear y editar, sin eliminar)
        "view_patients": True,
        "create_patients": True,
        "edit_patients": True,
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
        "view_audit_logs": False,
        # Permisos clínicos
        "view_agenda": True,
        "view_evaluacion": True,
        "manage_recetas": True,
        "view_sala_operaciones": True
    }
}

# SEC-003: Permisos de módulos clínicos (inventario, POS/ventas, caja)
_MODULE_PERMS = {
    "superadmin": {"view_inventory": True, "manage_inventory": True, "manage_sales": True, "manage_caja": True},
    "admin": {"view_inventory": True, "manage_inventory": True, "manage_sales": True, "manage_caja": True},
    "usuario": {"view_inventory": True, "manage_inventory": False, "manage_sales": True, "manage_caja": True},
    "optica": {"view_inventory": False, "manage_inventory": False, "manage_sales": False, "manage_caja": False},
}
for _rol, _perms_mod in _MODULE_PERMS.items():
    PERMISSIONS.setdefault(_rol, {}).update(_perms_mod)


def get_permissions(role: str) -> dict:
    return PERMISSIONS.get(role, PERMISSIONS["usuario"])


async def resolve_permissions(role: str) -> dict:
    """SEC-003/RBAC: Resuelve los permisos efectivos de un rol.
    - superadmin siempre tiene todos los permisos.
    - roles personalizados y personalizaciones de roles de sistema se leen de db.roles.
    - roles de sistema sin personalización usan la matriz por defecto.
    - rol desconocido => sin permisos (deny by default)."""
    if role == "superadmin":
        return PERMISSIONS["superadmin"]
    try:
        custom = await db.roles.find_one({"name": role})
    except Exception:
        custom = None
    if custom and isinstance(custom.get("permissions"), dict) and custom["permissions"]:
        # Fusionar: partir de los permisos por defecto del rol de sistema (si existe)
        # y aplicar encima las personalizaciones guardadas en db.roles.
        # Evita que un rol guardado antes de existir una clave nueva (p.ej. permisos
        # clínicos de 'medico') quede sin esa clave y se rompa el acceso.
        perms = dict(PERMISSIONS.get(role, {}))
        perms.update(custom["permissions"])
        return perms
    if role in PERMISSIONS:
        return PERMISSIONS[role]
    return {}


async def validar_rol_existe(role: str) -> bool:
    """RBAC: valida que un rol sea de sistema o exista como rol personalizado en db.roles."""
    if role in ["superadmin", "admin", "usuario", "optica", "medico"]:
        return True
    return await db.roles.find_one({"name": role}) is not None

# ==================== MODELS ====================

# User Models
class UserBase(BaseModel):
    username: str
    name: str
    # RBAC: se permite cualquier rol de sistema o personalizado (se valida en el endpoint contra db.roles)
    role: str = Field(default="usuario")

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

# ==================== MODELOS DE EXPENSE Y PAYMENT MOVIDOS A routes/expenses.py ====================

# ==================== BANK ACCOUNT MODELS ====================

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

# ==================== DOCTOR MODELS (Re-exportados desde optica.py) ====================
from routes.optica import DoctorResponse, DoctorListResponse, DoctorCreate, DoctorUpdate

# ==================== DASHBOARD MODELS ====================
class TypeBreakdown(BaseModel):
    type: str
    total: float
    percentage: float

class DashboardSummary(BaseModel):
    total_month: float = 0
    total_paid: float = 0
    total_pending: float = 0
    overdue_count: int = 0
    by_type: List[TypeBreakdown] = []

class MonthlyChartItem(BaseModel):
    month: str
    expenses: float
    payments: float

class AlertResponse(BaseModel):
    """Modelo para alertas de pagos pendientes/vencidos"""
    id: str
    name: str
    provider: Optional[str] = ""
    amount: float
    remaining_amount: float
    due_date: Optional[str] = None
    days_remaining: int
    type: str
    status: str
    invoice_number: Optional[str] = ""

class UpcomingPayments(BaseModel):
    overdue: List[AlertResponse] = []
    due30: List[AlertResponse] = []
    due60: List[AlertResponse] = []

# ==================== CÓDIGO MOVIDO A routes/surgeries.py ====================

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
    start_date: str  # Fecha de inicio del cobro (YYYY-MM-DD) - Obligatorio
    duration_type: str = "ilimitado"  # "ilimitado" o "hasta_fecha"
    end_date: Optional[str] = None  # Fecha de último pago (YYYY-MM-DD), null si ilimitado

class FixedExpenseCreate(FixedExpenseBase):
    generate_first: bool = False  # Generar el primer gasto inmediatamente

class FixedExpenseUpdate(BaseModel):
    supplier_id: Optional[str] = None
    expense_name: Optional[str] = None
    amount: Optional[float] = None
    day_of_month: Optional[int] = None
    start_date: Optional[str] = None
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
    start_date: Optional[str] = None
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

# ==================== CÓDIGO MOVIDO A routes/patients.py ====================

# ==================== OPTICA MODELS MOVIDOS A routes/optica.py ====================

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

def create_token(user_id: str, username: str, role: str, token_version: int = 1) -> str:
    """Crear token JWT con claims seguros"""
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "token_version": token_version,  # SEC-004: revocación masiva de sesiones
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
            "expires_at": exp_date  # BSON date: habilita el índice TTL para purga automática
        })
    except Exception as e:
        logging.error(f"Error al agregar token a blacklist: {e}")

async def cleanup_expired_tokens():
    """Limpiar tokens expirados de la blacklist (ejecutar periódicamente)"""
    try:
        result = await db.token_blacklist.delete_many({
            "expires_at": {"$lt": datetime.now(timezone.utc)}
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
        
        # SEC-004: Verificar versión de token (revocación masiva de sesiones)
        token_tv = payload.get("token_version")
        if token_tv is not None and token_tv != user.get("token_version", 1):
            raise HTTPException(status_code=401, detail="Sesión revocada. Inicie sesión nuevamente.")
        
        user["permissions"] = await resolve_permissions(user["role"])
        user["_token"] = token  # Store token for logout
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

def require_permission(permission: str):
    async def permission_checker(current_user: dict = Depends(get_current_user)):
        user_permissions = current_user.get("permissions") or get_permissions(current_user["role"])
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

# ==================== EXPENSE HELPERS MOVIDOS A routes/expenses.py ====================

# ==================== SEED USERS ====================

async def seed_default_users():
    """Create default users if they don't exist - CONTRASEÑAS MÁS SEGURAS"""
    # IMPORTANTE: Cambiar estas contraseñas en producción
    # SEC-001: Usuarios sembrados deben forzar cambio de contraseña
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
                # SEC-001: Forzar cambio de contraseña en primer login
                "must_change_password": True,
                "password_changed_at": None,
                # SEC-005: Control de intentos fallidos
                "failed_login_attempts": 0,
                "locked_until": None,
                # SEC-006: Registro de dispositivos conocidos
                "known_devices": [],
                "token_version": 1  # SEC-013: Para revocación masiva de sesiones
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
            "last_login": None,
            # SEC-005: forzar cambio de contraseña por defecto + campos de seguridad
            "must_change_password": True,
            "password_changed_at": None,
            "failed_login_attempts": 0,
            "locked_until": None,
            "known_devices": [],
            "token_version": 1
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


async def seed_catalogos_igss():
    """Seed de catálogos IGSS (medicamentos y procedimientos) desde /data JSON. Idempotente."""
    import json as _json
    base = os.path.join(os.path.dirname(__file__), "data")
    now = datetime.now(timezone.utc).isoformat()
    mapping = [
        ("catalogo_igss_medicamentos", "igss_medicamentos.json"),
        ("catalogo_igss_procedimientos", "igss_procedimientos.json"),
    ]
    for coll_name, filename in mapping:
        coll = db[coll_name]
        existing = await coll.count_documents({})
        if existing > 0:
            print(f"Catálogo IGSS '{coll_name}' ya existe ({existing}), saltando seed")
            continue
        path = os.path.join(base, filename)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = _json.load(fh)
        except Exception as e:
            print(f"No se pudo leer {path}: {e}")
            continue
        docs = [{
            "id": str(uuid.uuid4()),
            "codigo": item.get("codigo", ""),
            "nombre": item.get("nombre", ""),
            "usos": 0,
            "fecha_creacion": now,
        } for item in data if item.get("nombre")]
        if docs:
            await coll.insert_many(docs)
        print(f"Catálogo IGSS '{coll_name}' sembrado: {len(docs)} registros")


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
        except Exception:
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
        except Exception:
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
        except Exception:
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
                except (ValueError, KeyError):
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


# ==================== SEED DATA INVENTARIO ====================

async def seed_inventario_data():
    """Seed de datos de ejemplo para el módulo de inventario"""
    # Verificar si ya existen datos
    productos_count = await db.productos_inventario.count_documents({"origen": "clinica"})
    if productos_count > 0:
        print(f"Datos de inventario ya existen ({productos_count} productos), saltando seed")
        return
    
    now = datetime.now(timezone.utc).isoformat()
    hoy = datetime.now(timezone.utc).date()
    
    # ========== BODEGAS ==========
    bodegas = [
        {"id": str(uuid.uuid4()), "nombre": "Bodega General", "codigo": "BOD-GRAL", "descripcion": "Bodega principal de almacenamiento", "es_punto_venta": False, "activo": True, "origen": "clinica", "created_at": now},
        {"id": str(uuid.uuid4()), "nombre": "Dispensario", "codigo": "BOD-DISP", "descripcion": "Dispensario para ventas", "es_punto_venta": True, "activo": True, "origen": "clinica", "created_at": now},
        {"id": str(uuid.uuid4()), "nombre": "Quirófano", "codigo": "BOD-QX", "descripcion": "Insumos de quirófano", "es_punto_venta": False, "activo": True, "origen": "clinica", "created_at": now},
    ]
    
    for b in bodegas:
        await db.bodegas_inventario.insert_one(b)
    print(f"Creadas {len(bodegas)} bodegas")
    
    bodega_general_id = bodegas[0]["id"]
    bodega_dispensario_id = bodegas[1]["id"]
    bodega_quirofano_id = bodegas[2]["id"]
    
    # ========== CATEGORÍAS ==========
    categorias = [
        {"id": str(uuid.uuid4()), "nombre": "Medicamentos", "icono": "pill", "color": "#EF4444", "orden": 1, "activo": True, "origen": "clinica"},
        {"id": str(uuid.uuid4()), "nombre": "Gotas y Soluciones", "icono": "droplet", "color": "#3B82F6", "orden": 2, "activo": True, "origen": "clinica"},
        {"id": str(uuid.uuid4()), "nombre": "Lentes de Contacto", "icono": "eye", "color": "#10B981", "orden": 3, "activo": True, "origen": "clinica"},
        {"id": str(uuid.uuid4()), "nombre": "Accesorios", "icono": "glasses", "color": "#8B5CF6", "orden": 4, "activo": True, "origen": "clinica"},
        {"id": str(uuid.uuid4()), "nombre": "Insumos Quirúrgicos", "icono": "syringe", "color": "#F59E0B", "orden": 5, "activo": True, "origen": "clinica"},
        {"id": str(uuid.uuid4()), "nombre": "Consultas", "icono": "stethoscope", "color": "#0EA5E9", "orden": 6, "activo": True, "origen": "clinica"},
        {"id": str(uuid.uuid4()), "nombre": "Procedimientos", "icono": "scissors", "color": "#EC4899", "orden": 7, "activo": True, "origen": "clinica"},
        {"id": str(uuid.uuid4()), "nombre": "Estudios", "icono": "scan", "color": "#6366F1", "orden": 8, "activo": True, "origen": "clinica"},
    ]
    
    for c in categorias:
        await db.categorias_inventario.insert_one(c)
    print(f"Creadas {len(categorias)} categorías")
    
    cat_medicamentos = categorias[0]["id"]
    cat_gotas = categorias[1]["id"]
    cat_lentes = categorias[2]["id"]
    cat_accesorios = categorias[3]["id"]
    cat_quirurgicos = categorias[4]["id"]
    cat_consultas = categorias[5]["id"]
    cat_procedimientos = categorias[6]["id"]
    cat_estudios = categorias[7]["id"]
    
    # ========== PROVEEDORES (usar los existentes o crear nuevos) ==========
    proveedores = await db.suppliers.find({}).to_list(10)
    if not proveedores:
        # Crear proveedores de ejemplo
        proveedores_data = [
            {"id": str(uuid.uuid4()), "name": "Laboratorios Visión S.A.", "company_name": "LabVision", "nit": "12345678-9", "contact_name": "Carlos Pérez", "contact_phone": "2222-1111", "contact_email": "ventas@labvision.gt", "payment_terms": 30, "notes": "Proveedor principal de medicamentos", "is_active": True, "created_at": now},
            {"id": str(uuid.uuid4()), "name": "Distribuidora Óptica Centro", "company_name": "DOC", "nit": "98765432-1", "contact_name": "María García", "contact_phone": "2222-2222", "contact_email": "compras@doc.gt", "payment_terms": 15, "notes": "Lentes de contacto y accesorios", "is_active": True, "created_at": now},
            {"id": str(uuid.uuid4()), "name": "Insumos Médicos GT", "company_name": "IMGT", "nit": "55667788-0", "contact_name": "Roberto Méndez", "contact_phone": "2222-3333", "contact_email": "ventas@imgt.gt", "payment_terms": 45, "notes": "Insumos quirúrgicos", "is_active": True, "created_at": now},
        ]
        for p in proveedores_data:
            await db.suppliers.insert_one(p)
        proveedores = proveedores_data
        print(f"Creados {len(proveedores)} proveedores")
    
    prov_labvision = proveedores[0]["id"]
    prov_doc = proveedores[1]["id"] if len(proveedores) > 1 else prov_labvision
    prov_imgt = proveedores[2]["id"] if len(proveedores) > 2 else prov_labvision
    
    # ========== PRODUCTOS ==========
    productos = [
        # Medicamentos (con control de lotes)
        {"nombre": "Prednisolona 1% gotas", "codigo": "PROD-00001", "categoria_id": cat_gotas, "tipo": "producto", "presentacion": "Frasco 5ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": True, "precio_venta": 85.00, "existencia_minima": 10, "existencia_maxima": 50, "proveedor_preferido_id": prov_labvision},
        {"nombre": "Moxifloxacino 0.5% gotas", "codigo": "PROD-00002", "categoria_id": cat_gotas, "tipo": "producto", "presentacion": "Frasco 5ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": True, "precio_venta": 120.00, "existencia_minima": 10, "existencia_maxima": 40, "proveedor_preferido_id": prov_labvision},
        {"nombre": "Tobramicina/Dexametasona gotas", "codigo": "PROD-00003", "categoria_id": cat_gotas, "tipo": "producto", "presentacion": "Frasco 5ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": True, "precio_venta": 95.00, "existencia_minima": 8, "existencia_maxima": 35, "proveedor_preferido_id": prov_labvision},
        {"nombre": "Tropicamida 1% gotas", "codigo": "PROD-00004", "categoria_id": cat_gotas, "tipo": "producto", "presentacion": "Frasco 15ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": True, "precio_venta": 45.00, "existencia_minima": 5, "existencia_maxima": 20, "proveedor_preferido_id": prov_labvision},
        {"nombre": "Fenilefrina 2.5% gotas", "codigo": "PROD-00005", "categoria_id": cat_gotas, "tipo": "producto", "presentacion": "Frasco 15ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": True, "precio_venta": 55.00, "existencia_minima": 5, "existencia_maxima": 20, "proveedor_preferido_id": prov_labvision},
        {"nombre": "Dorzolamida/Timolol gotas", "codigo": "PROD-00006", "categoria_id": cat_gotas, "tipo": "producto", "presentacion": "Frasco 5ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": True, "precio_venta": 180.00, "existencia_minima": 8, "existencia_maxima": 30, "proveedor_preferido_id": prov_labvision},
        {"nombre": "Latanoprost 0.005% gotas", "codigo": "PROD-00007", "categoria_id": cat_gotas, "tipo": "producto", "presentacion": "Frasco 2.5ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": True, "precio_venta": 220.00, "existencia_minima": 5, "existencia_maxima": 25, "proveedor_preferido_id": prov_labvision},
        {"nombre": "Lubricante Ocular Hialuronato", "codigo": "PROD-00008", "categoria_id": cat_gotas, "tipo": "producto", "presentacion": "Frasco 10ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": True, "precio_venta": 75.00, "existencia_minima": 15, "existencia_maxima": 60, "proveedor_preferido_id": prov_labvision},
        
        # Medicamentos orales (con control de lotes)
        {"nombre": "Acetazolamida 250mg tabletas", "codigo": "PROD-00009", "categoria_id": cat_medicamentos, "tipo": "producto", "presentacion": "Caja 20 tabletas", "unidad_medida": "caja", "unidad_compra": "caja", "factor_conversion": 1, "controla_inventario": True, "controla_lotes": True, "precio_venta": 150.00, "existencia_minima": 5, "existencia_maxima": 20, "proveedor_preferido_id": prov_labvision},
        {"nombre": "Prednisona 50mg tabletas", "codigo": "PROD-00010", "categoria_id": cat_medicamentos, "tipo": "producto", "presentacion": "Caja 10 tabletas", "unidad_medida": "caja", "controla_inventario": True, "controla_lotes": True, "precio_venta": 45.00, "existencia_minima": 10, "existencia_maxima": 40, "proveedor_preferido_id": prov_labvision},
        
        # Lentes de contacto (sin control de lotes)
        {"nombre": "Lente de Contacto Diario -1.00", "codigo": "PROD-00011", "categoria_id": cat_lentes, "tipo": "producto", "presentacion": "Caja 30 unidades", "unidad_medida": "caja", "controla_inventario": True, "controla_lotes": False, "precio_venta": 350.00, "existencia_minima": 3, "existencia_maxima": 15, "proveedor_preferido_id": prov_doc},
        {"nombre": "Lente de Contacto Mensual -2.00", "codigo": "PROD-00012", "categoria_id": cat_lentes, "tipo": "producto", "presentacion": "Caja 6 unidades", "unidad_medida": "caja", "controla_inventario": True, "controla_lotes": False, "precio_venta": 280.00, "existencia_minima": 3, "existencia_maxima": 12, "proveedor_preferido_id": prov_doc},
        {"nombre": "Solución Multipropósito 360ml", "codigo": "PROD-00013", "categoria_id": cat_lentes, "tipo": "producto", "presentacion": "Frasco 360ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": True, "precio_venta": 95.00, "existencia_minima": 10, "existencia_maxima": 40, "proveedor_preferido_id": prov_doc},
        
        # Accesorios (sin control de lotes)
        {"nombre": "Estuche para Lentes de Contacto", "codigo": "PROD-00014", "categoria_id": cat_accesorios, "tipo": "producto", "presentacion": "Unidad", "unidad_medida": "unidad", "controla_inventario": True, "controla_lotes": False, "precio_venta": 25.00, "existencia_minima": 20, "existencia_maxima": 100, "proveedor_preferido_id": prov_doc},
        {"nombre": "Paño Microfibra Limpiador", "codigo": "PROD-00015", "categoria_id": cat_accesorios, "tipo": "producto", "presentacion": "Unidad", "unidad_medida": "unidad", "controla_inventario": True, "controla_lotes": False, "precio_venta": 15.00, "existencia_minima": 30, "existencia_maxima": 150, "proveedor_preferido_id": prov_doc},
        {"nombre": "Spray Limpiador de Lentes 60ml", "codigo": "PROD-00016", "categoria_id": cat_accesorios, "tipo": "producto", "presentacion": "Frasco 60ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": False, "precio_venta": 35.00, "existencia_minima": 15, "existencia_maxima": 60, "proveedor_preferido_id": prov_doc},
        
        # Insumos quirúrgicos (con control de lotes)
        {"nombre": "Viscoelástico Cohesivo 0.85ml", "codigo": "PROD-00017", "categoria_id": cat_quirurgicos, "tipo": "insumo", "presentacion": "Jeringa 0.85ml", "unidad_medida": "jeringa", "controla_inventario": True, "controla_lotes": True, "precio_venta": 450.00, "existencia_minima": 5, "existencia_maxima": 20, "proveedor_preferido_id": prov_imgt},
        {"nombre": "Lente Intraocular Monofocal", "codigo": "PROD-00018", "categoria_id": cat_quirurgicos, "tipo": "insumo", "presentacion": "Unidad", "unidad_medida": "unidad", "controla_inventario": True, "controla_lotes": True, "precio_venta": 1200.00, "existencia_minima": 3, "existencia_maxima": 15, "proveedor_preferido_id": prov_imgt},
        {"nombre": "Cuchillete 2.75mm", "codigo": "PROD-00019", "categoria_id": cat_quirurgicos, "tipo": "insumo", "presentacion": "Unidad estéril", "unidad_medida": "unidad", "controla_inventario": True, "controla_lotes": True, "precio_venta": 180.00, "existencia_minima": 10, "existencia_maxima": 50, "proveedor_preferido_id": prov_imgt},
        {"nombre": "BSS Plus 500ml", "codigo": "PROD-00020", "categoria_id": cat_quirurgicos, "tipo": "insumo", "presentacion": "Frasco 500ml", "unidad_medida": "frasco", "controla_inventario": True, "controla_lotes": True, "precio_venta": 280.00, "existencia_minima": 5, "existencia_maxima": 20, "proveedor_preferido_id": prov_imgt},
        
        # Servicios (sin control de inventario)
        {"nombre": "Consulta Oftalmológica General", "codigo": "SERV-00001", "categoria_id": cat_consultas, "tipo": "servicio", "presentacion": "Consulta", "unidad_medida": "servicio", "controla_inventario": False, "controla_lotes": False, "precio_venta": 300.00, "existencia_minima": 0, "existencia_maxima": 0},
        {"nombre": "Consulta Oftalmológica Especializada", "codigo": "SERV-00002", "categoria_id": cat_consultas, "tipo": "servicio", "presentacion": "Consulta", "unidad_medida": "servicio", "controla_inventario": False, "controla_lotes": False, "precio_venta": 450.00, "existencia_minima": 0, "existencia_maxima": 0},
        {"nombre": "OCT de Mácula", "codigo": "SERV-00003", "categoria_id": cat_estudios, "tipo": "servicio", "presentacion": "Estudio", "unidad_medida": "servicio", "controla_inventario": False, "controla_lotes": False, "precio_venta": 400.00, "existencia_minima": 0, "existencia_maxima": 0},
        {"nombre": "Campimetría Computarizada", "codigo": "SERV-00004", "categoria_id": cat_estudios, "tipo": "servicio", "presentacion": "Estudio", "unidad_medida": "servicio", "controla_inventario": False, "controla_lotes": False, "precio_venta": 350.00, "existencia_minima": 0, "existencia_maxima": 0},
        {"nombre": "Topografía Corneal", "codigo": "SERV-00005", "categoria_id": cat_estudios, "tipo": "servicio", "presentacion": "Estudio", "unidad_medida": "servicio", "controla_inventario": False, "controla_lotes": False, "precio_venta": 300.00, "existencia_minima": 0, "existencia_maxima": 0},
    ]
    
    productos_creados = []
    for p in productos:
        producto_doc = {
            "id": str(uuid.uuid4()),
            **p,
            "costo_promedio": 0.0,
            "ultimo_costo": 0.0,
            "activo": True,
            "afecto_iva": True,
            "origen": "clinica",
            "created_at": now,
            "updated_at": now
        }
        await db.productos_inventario.insert_one(producto_doc)
        productos_creados.append(producto_doc)
    print(f"Creados {len(productos)} productos")
    
    # ========== LOTES Y EXISTENCIAS ==========
    # Crear lotes con vencimientos escalonados para productos que controlan lotes
    lotes_data = []
    
    # Fechas de vencimiento escalonadas
    fecha_vencido = (hoy - timedelta(days=15)).strftime("%Y-%m-%d")  # Ya vencido
    fecha_30d = (hoy + timedelta(days=25)).strftime("%Y-%m-%d")  # Vence en ~30 días
    fecha_60d = (hoy + timedelta(days=55)).strftime("%Y-%m-%d")  # Vence en ~60 días
    fecha_90d = (hoy + timedelta(days=85)).strftime("%Y-%m-%d")  # Vence en ~90 días
    fecha_180d = (hoy + timedelta(days=180)).strftime("%Y-%m-%d")  # Vence en 180 días
    
    for prod in productos_creados:
        if prod.get("controla_inventario", True) and prod.get("tipo") != "servicio":
            if prod.get("controla_lotes", False):
                # Crear múltiples lotes con diferentes vencimientos
                costo_base = prod["precio_venta"] * 0.5  # Costo = 50% del precio
                
                # Lote 1: Vencido (para alertas)
                if prod["codigo"] in ["PROD-00001", "PROD-00003"]:
                    lote_vencido = {
                        "id": str(uuid.uuid4()),
                        "producto_id": prod["id"],
                        "bodega_id": bodega_general_id,
                        "numero_lote": f"LOT-{prod['codigo'][-5:]}-VEN",
                        "fecha_vencimiento": fecha_vencido,
                        "cantidad_inicial": 5,
                        "cantidad_disponible": 3,
                        "costo_unitario": costo_base,
                        "proveedor_id": prod.get("proveedor_preferido_id"),
                        "estado": "disponible",
                        "origen": "clinica"
                    }
                    lotes_data.append(lote_vencido)
                
                # Lote 2: Por vencer en 30 días
                lote_30 = {
                    "id": str(uuid.uuid4()),
                    "producto_id": prod["id"],
                    "bodega_id": bodega_general_id,
                    "numero_lote": f"LOT-{prod['codigo'][-5:]}-30D",
                    "fecha_vencimiento": fecha_30d,
                    "cantidad_inicial": 10,
                    "cantidad_disponible": 8,
                    "costo_unitario": costo_base,
                    "proveedor_id": prod.get("proveedor_preferido_id"),
                    "estado": "disponible",
                    "origen": "clinica"
                }
                lotes_data.append(lote_30)
                
                # Lote 3: Por vencer en 90 días
                lote_90 = {
                    "id": str(uuid.uuid4()),
                    "producto_id": prod["id"],
                    "bodega_id": bodega_dispensario_id,
                    "numero_lote": f"LOT-{prod['codigo'][-5:]}-90D",
                    "fecha_vencimiento": fecha_90d,
                    "cantidad_inicial": 15,
                    "cantidad_disponible": 15,
                    "costo_unitario": costo_base * 1.05,  # Un poco más caro
                    "proveedor_id": prod.get("proveedor_preferido_id"),
                    "estado": "disponible",
                    "origen": "clinica"
                }
                lotes_data.append(lote_90)
                
                # Lote 4: Vence en 180 días (fresco)
                lote_180 = {
                    "id": str(uuid.uuid4()),
                    "producto_id": prod["id"],
                    "bodega_id": bodega_general_id,
                    "numero_lote": f"LOT-{prod['codigo'][-5:]}-180",
                    "fecha_vencimiento": fecha_180d,
                    "cantidad_inicial": 20,
                    "cantidad_disponible": 20,
                    "costo_unitario": costo_base * 1.1,
                    "proveedor_id": prod.get("proveedor_preferido_id"),
                    "estado": "disponible",
                    "origen": "clinica"
                }
                lotes_data.append(lote_180)
                
                # Actualizar costo promedio del producto
                total_unidades = 8 + 15 + 20 + (3 if prod["codigo"] in ["PROD-00001", "PROD-00003"] else 0)
                valor_total = (8 * costo_base) + (15 * costo_base * 1.05) + (20 * costo_base * 1.1)
                if prod["codigo"] in ["PROD-00001", "PROD-00003"]:
                    valor_total += 3 * costo_base
                costo_prom = valor_total / total_unidades if total_unidades > 0 else costo_base
                
                await db.productos_inventario.update_one(
                    {"id": prod["id"]},
                    {"$set": {"costo_promedio": round(costo_prom, 4), "ultimo_costo": round(costo_base * 1.1, 4)}}
                )
            else:
                # Productos sin control de lotes - solo existencias
                costo_base = prod["precio_venta"] * 0.5
                await db.productos_inventario.update_one(
                    {"id": prod["id"]},
                    {"$set": {"costo_promedio": round(costo_base, 4), "ultimo_costo": round(costo_base, 4)}}
                )
    
    # Insertar lotes
    for lote in lotes_data:
        await db.lotes_inventario.insert_one(lote)
    print(f"Creados {len(lotes_data)} lotes")
    
    # ========== EXISTENCIAS ==========
    # Calcular existencias por producto y bodega
    existencias_map = {}
    for lote in lotes_data:
        key = f"{lote['producto_id']}_{lote['bodega_id']}"
        if key not in existencias_map:
            existencias_map[key] = {"producto_id": lote["producto_id"], "bodega_id": lote["bodega_id"], "cantidad": 0}
        existencias_map[key]["cantidad"] += lote["cantidad_disponible"]
    
    # Agregar existencias para productos sin lotes
    for prod in productos_creados:
        if prod.get("controla_inventario", True) and not prod.get("controla_lotes", False) and prod.get("tipo") != "servicio":
            # Existencia en bodega general
            key_gral = f"{prod['id']}_{bodega_general_id}"
            if key_gral not in existencias_map:
                existencias_map[key_gral] = {
                    "producto_id": prod["id"],
                    "bodega_id": bodega_general_id,
                    "cantidad": prod.get("existencia_maxima", 20) // 2  # 50% del máximo
                }
            # Existencia en dispensario
            key_disp = f"{prod['id']}_{bodega_dispensario_id}"
            if key_disp not in existencias_map:
                existencias_map[key_disp] = {
                    "producto_id": prod["id"],
                    "bodega_id": bodega_dispensario_id,
                    "cantidad": prod.get("existencia_maxima", 20) // 4  # 25% del máximo
                }
    
    for key, exist in existencias_map.items():
        exist_doc = {
            "id": str(uuid.uuid4()),
            "producto_id": exist["producto_id"],
            "bodega_id": exist["bodega_id"],
            "cantidad": exist["cantidad"],
            "cantidad_reservada": 0,
            "ultima_actualizacion": now,
            "origen": "clinica"
        }
        await db.existencias_inventario.insert_one(exist_doc)
    print(f"Creadas {len(existencias_map)} existencias")
    
    # ========== ÓRDENES DE COMPRA Y RECEPCIONES ==========
    # Orden 1: Completada
    orden1_id = str(uuid.uuid4())
    orden1 = {
        "id": orden1_id,
        "numero_orden": "OC-000001",
        "proveedor_id": prov_labvision,
        "fecha": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "fecha_estimada_entrega": (datetime.now(timezone.utc) - timedelta(days=25)).isoformat(),
        "items": [
            {"producto_id": productos_creados[0]["id"], "codigo": productos_creados[0]["codigo"], "nombre": productos_creados[0]["nombre"], "cantidad": 20, "cantidad_recibida": 20, "costo_unitario": 42.50, "subtotal": 850.00},
            {"producto_id": productos_creados[1]["id"], "codigo": productos_creados[1]["codigo"], "nombre": productos_creados[1]["nombre"], "cantidad": 15, "cantidad_recibida": 15, "costo_unitario": 60.00, "subtotal": 900.00},
        ],
        "subtotal": 1750.00,
        "total": 1750.00,
        "estado": "recibida",
        "observaciones": "Pedido mensual de gotas oftálmicas",
        "creada_por": "system",
        "autorizada_por": "system",
        "fecha_autorizacion": (datetime.now(timezone.utc) - timedelta(days=28)).isoformat(),
        "origen": "clinica",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "updated_at": (datetime.now(timezone.utc) - timedelta(days=25)).isoformat()
    }
    await db.ordenes_compra.insert_one(orden1)
    
    # Orden 2: Parcial
    orden2_id = str(uuid.uuid4())
    orden2 = {
        "id": orden2_id,
        "numero_orden": "OC-000002",
        "proveedor_id": prov_imgt,
        "fecha": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
        "fecha_estimada_entrega": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        "items": [
            {"producto_id": productos_creados[16]["id"], "codigo": productos_creados[16]["codigo"], "nombre": productos_creados[16]["nombre"], "cantidad": 10, "cantidad_recibida": 5, "costo_unitario": 225.00, "subtotal": 2250.00},
            {"producto_id": productos_creados[17]["id"], "codigo": productos_creados[17]["codigo"], "nombre": productos_creados[17]["nombre"], "cantidad": 5, "cantidad_recibida": 0, "costo_unitario": 600.00, "subtotal": 3000.00},
        ],
        "subtotal": 5250.00,
        "total": 5250.00,
        "estado": "parcial",
        "observaciones": "Insumos para cirugías programadas",
        "creada_por": "system",
        "autorizada_por": "system",
        "fecha_autorizacion": (datetime.now(timezone.utc) - timedelta(days=9)).isoformat(),
        "origen": "clinica",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
        "updated_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    }
    await db.ordenes_compra.insert_one(orden2)
    print("Creadas 2 órdenes de compra")
    
    # Recepción de la orden 1
    recepcion1 = {
        "id": str(uuid.uuid4()),
        "numero_recepcion": "REC-000001",
        "orden_compra_id": orden1_id,
        "proveedor_id": prov_labvision,
        "bodega_id": bodega_general_id,
        "fecha": (datetime.now(timezone.utc) - timedelta(days=25)).isoformat(),
        "numero_factura": "FAC-12345",
        "items": [
            {"producto_id": productos_creados[0]["id"], "cantidad": 20, "costo_unitario": 42.50, "numero_lote": "LOT-00001-180", "fecha_vencimiento": fecha_180d},
            {"producto_id": productos_creados[1]["id"], "cantidad": 15, "costo_unitario": 60.00, "numero_lote": "LOT-00002-180", "fecha_vencimiento": fecha_180d},
        ],
        "total_costo": 1750.00,
        "usuario_id": "system",
        "observaciones": "Recepción completa de orden OC-000001",
        "origen": "clinica",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=25)).isoformat()
    }
    await db.recepciones_inventario.insert_one(recepcion1)
    print("Creada 1 recepción")
    
    # ========== MOVIMIENTOS DE KARDEX ==========
    # Crear algunos movimientos de ejemplo de los últimos 90 días
    for prod in productos_creados[:10]:  # Solo para los primeros 10 productos
        if prod.get("controla_inventario", True) and prod.get("tipo") != "servicio":
            # Entrada inicial
            mov_entrada = {
                "id": str(uuid.uuid4()),
                "fecha": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
                "producto_id": prod["id"],
                "bodega_id": bodega_general_id,
                "tipo": "entrada",
                "cantidad": 20,
                "existencia_anterior": 0,
                "existencia_nueva": 20,
                "costo_unitario": prod["precio_venta"] * 0.5,
                "costo_total": prod["precio_venta"] * 0.5 * 20,
                "referencia_tipo": "recepcion",
                "referencia_id": "REC-000001",
                "motivo": "Recepción inicial de inventario",
                "usuario_id": "system",
                "origen": "clinica"
            }
            await db.movimientos_inventario.insert_one(mov_entrada)
            
            # Algunas salidas/ventas
            for i in range(3):
                mov_venta = {
                    "id": str(uuid.uuid4()),
                    "fecha": (datetime.now(timezone.utc) - timedelta(days=45-i*10)).isoformat(),
                    "producto_id": prod["id"],
                    "bodega_id": bodega_dispensario_id,
                    "tipo": "venta",
                    "cantidad": 2,
                    "existencia_anterior": 20 - (i*2),
                    "existencia_nueva": 18 - (i*2),
                    "costo_unitario": prod["precio_venta"] * 0.5,
                    "costo_total": prod["precio_venta"] * 0.5 * 2,
                    "referencia_tipo": "venta",
                    "referencia_id": f"VENTA-{i+1:05d}",
                    "usuario_id": "system",
                    "origen": "clinica"
                }
                await db.movimientos_inventario.insert_one(mov_venta)
    
    print("Creados movimientos de kardex de ejemplo")
    
    # ========== CONFIGURACIÓN ==========
    config = {
        "metodo_valuacion": "promedio_ponderado",
        "metodo_salida_lotes": "FEFO",
        "permitir_existencia_negativa": False,
        "dias_alerta_vencimiento": [90, 60, 30],
        "bloquear_venta_producto_vencido": True,
        "generar_gasto_al_recibir": True,
        "bodega_predeterminada_pos": bodega_dispensario_id,
        "origen": "clinica"
    }
    await db.config_inventario.update_one(
        {"origen": "clinica"},
        {"$set": config},
        upsert=True
    )
    print("Configuración de inventario creada")
    
    print("✅ Seed de inventario completado exitosamente")


# ==================== AUTH ROUTES ====================

# SEC-006: Función para alertar a SuperAdmin
async def alert_superadmin(message: str, severity: str = "warning", details: dict = None):
    """Enviar alerta de seguridad al SuperAdmin"""
    alert_doc = {
        "id": str(uuid.uuid4()),
        "message": message,
        "severity": severity,
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "acknowledged": False
    }
    await db.security_alerts.insert_one(alert_doc)
    await audit.log(
        action="SECURITY_ALERT",
        user_id="system",
        user_name="system",
        details={"message": message, "severity": severity, **(details or {})}
    )
    logging.warning(f"🚨 ALERTA DE SEGURIDAD [{severity}]: {message}")

# SEC-006: Función para verificar y registrar dispositivo
async def check_and_register_device(user_id: str, ip_address: str, user_agent: str) -> bool:
    """Verificar si es un dispositivo nuevo y registrarlo. Retorna True si es nuevo."""
    device_fingerprint = hashlib.sha256(f"{ip_address}:{user_agent}".encode()).hexdigest()[:16]
    
    user = await db.users.find_one({"id": user_id})
    known_devices = user.get("known_devices", [])
    
    # Buscar si el dispositivo ya existe
    is_new = not any(d.get("fingerprint") == device_fingerprint for d in known_devices)
    
    if is_new:
        # Registrar nuevo dispositivo
        new_device = {
            "fingerprint": device_fingerprint,
            "ip_address": ip_address,
            "user_agent": user_agent[:200],  # Limitar longitud
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat()
        }
        await db.users.update_one(
            {"id": user_id},
            {"$push": {"known_devices": new_device}}
        )
    else:
        # Actualizar última vez visto
        await db.users.update_one(
            {"id": user_id, "known_devices.fingerprint": device_fingerprint},
            {"$set": {"known_devices.$.last_seen": datetime.now(timezone.utc).isoformat()}}
        )
    
    return is_new


class LoginResponse(BaseModel):
    """Respuesta extendida de login que incluye información de seguridad"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    must_change_password: bool = False
    is_new_device: bool = False


@api_router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin):
    """
    Login endpoint con seguridad mejorada:
    - Rate limiting (5 intentos por minuto)
    - Bloqueo tras 5 intentos fallidos (15 minutos)
    - Detección de nuevos dispositivos
    - Forzado de cambio de contraseña inicial
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")[:200]
    
    # Buscar usuario
    user = await db.users.find_one({"username": credentials.username.lower().strip()})
    
    # SEC-005: Verificar si la cuenta está bloqueada
    if user and user.get("locked_until"):
        locked_until = datetime.fromisoformat(user["locked_until"].replace('Z', '+00:00'))
        if locked_until > datetime.now(timezone.utc):
            remaining_minutes = int((locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
            await audit.log(
                action="LOGIN_BLOCKED",
                user_id=user["id"],
                user_name=user["username"],
                details={"reason": "Cuenta bloqueada", "remaining_minutes": remaining_minutes},
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=429, 
                detail=f"Cuenta bloqueada temporalmente. Intente en {remaining_minutes} minutos."
            )
        else:
            # Desbloquear si el tiempo expiró
            await db.users.update_one(
                {"id": user["id"]},
                {"$set": {"locked_until": None, "failed_login_attempts": 0}}
            )
    
    # Verificar credenciales
    if not user or not verify_password(credentials.password, user["password"]):
        # SEC-005: Incrementar intentos fallidos
        if user:
            attempts = user.get("failed_login_attempts", 0) + 1
            update_data = {"failed_login_attempts": attempts}
            
            if attempts >= 5:
                # Bloquear por 15 minutos
                lock_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                update_data["locked_until"] = lock_until.isoformat()
                
                # Alertar a SuperAdmin
                await alert_superadmin(
                    f"Cuenta '{user['username']}' bloqueada tras {attempts} intentos fallidos",
                    severity="warning",
                    details={"user_id": user["id"], "ip_address": client_ip, "attempts": attempts}
                )
            
            await db.users.update_one({"id": user["id"]}, {"$set": update_data})
        
        await audit.log(
            action="LOGIN_FAILED",
            user_id=user["id"] if user else "unknown",
            user_name=credentials.username,
            details={"reason": "Credenciales inválidas", "ip": client_ip},
            ip_address=client_ip
        )
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    # Verificar si está activo
    if not user.get("is_active", True):
        await audit.log(
            action="LOGIN_FAILED",
            user_id=user["id"],
            user_name=user["username"],
            details={"reason": "Usuario desactivado"},
            ip_address=client_ip
        )
        raise HTTPException(status_code=401, detail="Usuario desactivado")
    
    # Login exitoso - resetear contador de intentos
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "failed_login_attempts": 0, 
            "locked_until": None,
            "last_login": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # SEC-006: Verificar si es un dispositivo nuevo
    is_new_device = await check_and_register_device(user["id"], client_ip, user_agent)
    
    if is_new_device:
        await alert_superadmin(
            f"Nuevo dispositivo detectado para '{user['username']}' desde IP {client_ip}",
            severity="info",
            details={"user_id": user["id"], "ip_address": client_ip, "user_agent": user_agent}
        )
    
    # SEC-001: Verificar si debe cambiar contraseña
    must_change = user.get("must_change_password", False)
    
    # Crear token (SEC-004: incluye token_version para revocación de sesiones)
    token = create_token(user["id"], user["username"], user["role"], user.get("token_version", 1))
    
    # Log login exitoso
    await audit.log(
        action="LOGIN_SUCCESS",
        user_id=user["id"],
        user_name=user["username"],
        details={
            "role": user["role"], 
            "ip": client_ip, 
            "new_device": is_new_device,
            "must_change_password": must_change
        },
        ip_address=client_ip
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": must_change,
        "is_new_device": is_new_device,
        "user": UserResponse(
            id=user["id"],
            username=user["username"],
            name=user["name"],
            role=user["role"],
            is_active=user.get("is_active", True),
            last_login=datetime.now(timezone.utc).isoformat(),
            created_at=user["created_at"],
            updated_at=user.get("updated_at"),
            permissions=await resolve_permissions(user["role"])
        )
    }

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
    """
    Cambiar contraseña del usuario actual.
    SEC-001: Resetea el flag must_change_password después del cambio.
    """
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
    
    # Verificar que no sea igual a la actual
    if verify_password(new_password, user["password"]):
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser diferente a la actual")
    
    # Actualizar contraseña y resetear flag de cambio obligatorio
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "password": hash_password(new_password),
            "password_changed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "must_change_password": False  # SEC-001: Resetear flag
        }}
    )
    
    # Log cambio de contraseña
    was_forced = user.get("must_change_password", False)
    await audit.log(
        action="PASSWORD_CHANGED",
        user_id=current_user["id"],
        user_name=current_user.get("username", "unknown"),
        details={"forced_change": was_forced},
        ip_address=client_ip
    )
    
    return {"message": "Contraseña actualizada correctamente", "forced_change_completed": was_forced}


# SEC-006: Endpoint para obtener alertas de seguridad (solo SuperAdmin)
@api_router.get("/security/alerts")
async def get_security_alerts(
    current_user: dict = Depends(require_role("superadmin")),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200)
):
    """Obtener alertas de seguridad (solo SuperAdmin)"""
    query = {}
    if acknowledged is not None:
        query["acknowledged"] = acknowledged
    
    cursor = db.security_alerts.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    alerts = await cursor.to_list(length=limit)
    
    return {
        "alerts": alerts,
        "total": await db.security_alerts.count_documents(query)
    }


@api_router.post("/security/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Marcar alerta de seguridad como reconocida"""
    result = await db.security_alerts.update_one(
        {"id": alert_id},
        {"$set": {
            "acknowledged": True,
            "acknowledged_at": datetime.now(timezone.utc).isoformat(),
            "acknowledged_by": current_user["id"]
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    
    return {"message": "Alerta reconocida"}


# SEC-006: Endpoint para ver dispositivos conocidos del usuario
@api_router.get("/security/my-devices")
async def get_my_devices(current_user: dict = Depends(get_current_user)):
    """Obtener lista de dispositivos conocidos del usuario actual"""
    user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0, "known_devices": 1})
    return {"devices": user.get("known_devices", [])}


# SEC-013: Endpoint para revocar todas las sesiones de un usuario (SuperAdmin)
@api_router.post("/users/{user_id}/revoke-sessions")
async def revoke_user_sessions(
    user_id: str,
    request: Request,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Revocar todas las sesiones activas de un usuario (incrementa token_version)"""
    client_ip = request.client.host if request.client else "unknown"
    
    # Verificar que el usuario existe
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Incrementar versión de token (invalida todos los tokens existentes)
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"token_version": 1}}
    )
    
    # Registrar en audit log
    await audit.log(
        action="SESSIONS_REVOKED",
        user_id=current_user["id"],
        user_name=current_user.get("username", "unknown"),
        details={
            "target_user_id": user_id,
            "target_username": target_user.get("username")
        },
        ip_address=client_ip
    )
    
    return {"message": f"Todas las sesiones de '{target_user.get('username')}' han sido revocadas"}


# SEC-013: Endpoint para revocar mis propias sesiones (cerrar en todos los dispositivos)
@api_router.post("/security/revoke-my-sessions")
async def revoke_my_sessions(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Revocar todas mis sesiones excepto la actual"""
    client_ip = request.client.host if request.client else "unknown"
    
    # Incrementar versión de token
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"token_version": 1}}
    )
    
    await audit.log(
        action="SELF_SESSIONS_REVOKED",
        user_id=current_user["id"],
        user_name=current_user.get("username", "unknown"),
        ip_address=client_ip
    )
    
    return {"message": "Todas tus otras sesiones han sido cerradas. Deberás iniciar sesión nuevamente."}


# ==================== EVALUACIONES MOVIDAS A routes/evaluaciones.py ====================

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

# Inicializar módulo de caja con función de audit y WebSocket manager
init_caja_routes(caja_log_action, ws_manager)

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
    config_router as agenda_config_router,
    external_router as agenda_external_router,
    init_agenda_routes
)

# Inicializar módulo de agenda con WebSocket manager
init_agenda_routes(ws_manager)

# Incluir routers de agenda en api_router
api_router.include_router(agenda_router, tags=["Agenda"])
api_router.include_router(medicos_agenda_router, tags=["Agenda - Médicos"])
api_router.include_router(agenda_config_router, tags=["Agenda - Configuración"])
api_router.include_router(agenda_external_router, tags=["Agenda - Agente Externo"])

# ==================== MÓDULO DE ADMINISTRACIÓN Y DASHBOARD ====================
from routes.admin import router as admin_router
from routes.dashboard_financiero import router as dashboard_financiero_router

# Incluir routers de admin y dashboard
api_router.include_router(admin_router, tags=["Administración"])
api_router.include_router(dashboard_financiero_router, tags=["Dashboard Financiero"])

# ==================== CONFIGURACIÓN DE MENÚS ====================
from routes.menu_config import router as menu_config_router
api_router.include_router(menu_config_router, tags=["Configuración de Menús"])

# ==================== MÓDULO DE ROLES ====================
from routes.roles import router as roles_router
api_router.include_router(roles_router, tags=["Roles"])


# ==================== MÓDULO DE PACIENTES (Refactorizado) ====================
from routes.patients import router as patients_router, pacientes_router

# Incluir routers de pacientes
api_router.include_router(patients_router, tags=["Pacientes"])
api_router.include_router(pacientes_router, tags=["Pacientes - Búsqueda rápida"])

# ==================== MÓDULO NOG POR UNIDAD IGSS ====================
from routes.igss_nogs import router as igss_nogs_router
api_router.include_router(igss_nogs_router, tags=["Unidades IGSS - NOG"])

# ==================== INTEGRACIÓN GOOGLE CALENDAR ====================
from routes.google_calendar import router as google_calendar_router
api_router.include_router(google_calendar_router, tags=["Google Calendar"])

# ==================== MÓDULO DE EVALUACIONES (Refactorizado) ====================
from routes.evaluaciones import router as evaluaciones_router, catalogos_router

# Incluir routers de evaluaciones
api_router.include_router(evaluaciones_router, tags=["Evaluaciones Oftalmológicas"])
api_router.include_router(catalogos_router, tags=["Catálogos - Evaluaciones"])

# ==================== MÓDULO DE CIRUGÍAS (Refactorizado) ====================
from routes.surgeries import router as surgeries_router, reports_router as surgeries_reports_router, notas_router as surgery_notes_router
from routes.surgery_crm import router as surgery_crm_router

# Incluir routers de cirugías
api_router.include_router(surgeries_router, tags=["Cirugías"])
api_router.include_router(surgeries_reports_router, tags=["Reportes de Cirugías"])
api_router.include_router(surgery_notes_router, tags=["Notas de Cirugía"])
api_router.include_router(surgery_crm_router, tags=["CRM Cirugías"])

# ==================== MÓDULO DE GASTOS Y PAGOS (Refactorizado) ====================
from routes.expenses import router as expenses_router, payments_router, check_overdue_expenses, get_next_expense_number

# Incluir routers de gastos y pagos
api_router.include_router(expenses_router, tags=["Gastos"])
api_router.include_router(payments_router, tags=["Pagos"])

# ==================== MÓDULO DE ÓPTICA (Refactorizado) ====================
from routes.optica import router as optica_router, doctors_router

# Incluir routers de óptica
api_router.include_router(optica_router, tags=["Óptica"])
api_router.include_router(doctors_router, tags=["Médicos"])

# ==================== MÓDULO DE AUTORIZACIONES DE PAGO (Refactorizado) ====================
from routes.payment_authorizations import router as payment_auth_router

# Incluir router de autorizaciones de pago
api_router.include_router(payment_auth_router, tags=["Autorizaciones de Pago"])

# ==================== MÓDULO DE INVENTARIO ====================
from routes.inventario import router as inventario_router
from routes.inventario_ops import router as inventario_ops_router

# Incluir routers de inventario
api_router.include_router(inventario_router, tags=["Inventario"])
api_router.include_router(inventario_ops_router, tags=["Inventario - Operaciones"])

# ==================== MÓDULO DE PUNTO DE VENTA (POS) ====================
from routes.ventas import router as ventas_router

# Incluir router de ventas/POS
api_router.include_router(ventas_router, tags=["Punto de Venta"])

# Incluir router de Laboratorio de Pruebas (solo desarrollo)
from routes.laboratorio_pruebas import router as laboratorio_pruebas_router
api_router.include_router(laboratorio_pruebas_router, tags=["Laboratorio de Pruebas"])

# Incluir router de Cuentas por Cobrar (CxC independiente para Óptica y Clínica)
from routes.cuentas_cobrar import router as cuentas_cobrar_router
api_router.include_router(cuentas_cobrar_router, prefix="/cuentas-cobrar", tags=["Cuentas por Cobrar"])

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
    
    # RBAC: validar que el rol exista (sistema o personalizado)
    if not await validar_rol_existe(user_data.role):
        raise HTTPException(status_code=400, detail=f"El rol '{user_data.role}' no existe")
    
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
        "updated_at": now,
        "token_version": 1
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
        permissions=await resolve_permissions(user_data.role)
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
        if not await validar_rol_existe(user_data.role):
            raise HTTPException(status_code=400, detail=f"El rol '{user_data.role}' no existe")
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
    return UserResponse(**updated, permissions=await resolve_permissions(updated["role"]))

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

# ==================== GASTOS Y PAGOS MOVIDOS A routes/expenses.py ====================

# ==================== DASHBOARD ROUTES ====================

@api_router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(current_user: dict = Depends(require_permission("view_dashboard"))):
    await check_overdue_expenses()
    
    # Get current month - usar formato YYYY-MM-DD para coincidir con el campo date
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1).strftime("%Y-%m-%d")  # Formato: 2026-08-01
    
    # Get all expenses for the month
    expenses = await db.expenses.find({
        "date": {"$gte": month_start}
    }, {"_id": 0}).to_list(10000)
    
    total_month = sum(e["amount"] for e in expenses)
    total_paid = sum(e["paid_amount"] for e in expenses)
    total_pending = sum(e["remaining_amount"] for e in expenses)
    
    # Get overdue count efficiently
    overdue_count = await db.expenses.count_documents({"status": "vencido"})
    
    # Calculate by type
    by_type = []
    for expense_type in ["fijo", "proveedor", "variable", "igss"]:
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
    expenses = await db.expenses.find({}, {"_id": 0, "date": 1, "amount": 1, "paid_amount": 1}).to_list(10000)
    
    # Group by month (last 6 months) - usando cálculo explícito de (año, mes)
    now = datetime.now(timezone.utc)
    current_year = now.year
    current_month = now.month
    monthly_data = {}
    
    for i in range(6):
        # Calcular el mes correcto restando i meses
        target_month = current_month - i
        target_year = current_year
        
        # Ajustar año si el mes es <= 0
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        month_key = f"{target_year}-{target_month:02d}"
        month_name = datetime(target_year, target_month, 1).strftime("%b")
        monthly_data[month_key] = {"month": month_name, "expenses": 0, "payments": 0}
    
    for e in expenses:
        try:
            date = datetime.fromisoformat(e["date"])
            month_key = date.strftime("%Y-%m")
            if month_key in monthly_data:
                monthly_data[month_key]["expenses"] += e.get("amount", 0)
                monthly_data[month_key]["payments"] += e.get("paid_amount", 0)
        except Exception:
            pass
    
    # Sort by date and return
    sorted_keys = sorted(monthly_data.keys())
    return [MonthlyChartItem(**monthly_data[k]) for k in sorted_keys]

@api_router.get("/dashboard/upcoming", response_model=UpcomingPayments)
async def get_upcoming_payments(current_user: dict = Depends(require_permission("view_due_payments"))):
    await check_overdue_expenses()
    
    today = now_gt().date()
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
    # Calcular inicio del mes actual - usar formato YYYY-MM-DD para coincidir con el campo date
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1).strftime("%Y-%m-%d")  # Formato: 2026-08-01
    
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

def require_admin_or_superadmin():
    """Require admin or superadmin role (for read operations)"""
    async def checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in ["admin", "superadmin"]:
            raise HTTPException(status_code=403, detail="Se requiere rol Admin o SuperAdmin para esta función")
        return current_user
    return checker

@api_router.get("/bank-accounts", response_model=BankAccountListResponse)
async def get_bank_accounts(current_user: dict = Depends(require_admin_or_superadmin())):
    """Get all bank accounts (Admin+ can read, SuperAdmin can manage)"""
    accounts = await db.bank_accounts.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return BankAccountListResponse(data=[BankAccountResponse(**a) for a in accounts], total=len(accounts))

@api_router.get("/bank-accounts/{account_id}", response_model=BankAccountResponse)
async def get_bank_account(account_id: str, current_user: dict = Depends(require_admin_or_superadmin())):
    """Get a specific bank account (Admin+ can read)"""
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
    """Obtener todos los proveedores (Admin, SuperAdmin, Optica y Usuario)"""
    if current_user["role"] not in ["admin", "superadmin", "optica", "usuario"]:
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
        "start_date": fixed_expense_data.start_date,  # Fecha de inicio del cobro
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
            "provider": supplier["name"],  # Nombre del proveedor para mostrar en UI
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


# Endpoint de migración para corregir gastos sin proveedor
@api_router.post("/expenses/fix-missing-providers")
async def fix_missing_providers(current_user: dict = Depends(get_current_user)):
    """Corrige gastos que tienen supplier_id pero no tienen provider (solo SuperAdmin)"""
    if current_user["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Solo el SuperAdmin puede ejecutar esta acción")
    
    # Buscar gastos que tienen supplier_id pero provider vacío o null
    expenses_to_fix = await db.expenses.find({
        "$or": [
            {"provider": None},
            {"provider": ""},
            {"provider": {"$exists": False}}
        ],
        "supplier_id": {"$exists": True, "$ne": None}
    }, {"_id": 0}).to_list(1000)
    
    fixed_count = 0
    fixed_details = []
    
    for expense in expenses_to_fix:
        supplier = await db.suppliers.find_one({"id": expense["supplier_id"]}, {"_id": 0, "name": 1})
        if supplier:
            await db.expenses.update_one(
                {"id": expense["id"]},
                {"$set": {"provider": supplier["name"], "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            fixed_count += 1
            fixed_details.append({
                "expense_number": expense.get("expense_number", "Sin número"),
                "name": expense.get("name", ""),
                "provider_added": supplier["name"]
            })
    
    return {
        "message": f"Se corrigieron {fixed_count} gastos",
        "fixed_count": fixed_count,
        "details": fixed_details
    }


# ==================== IGSS UNIT ROUTES (Catálogo) ====================

@api_router.get("/igss-units", response_model=IGSSUnitListResponse)
async def get_igss_units(current_user: dict = Depends(get_current_user)):
    """Obtener todas las unidades IGSS (todos los roles)"""
    units = await db.igss_units.find({"is_active": True}, {"_id": 0}).sort("name", 1).to_list(1000)
    return IGSSUnitListResponse(data=units, total=len(units))


@api_router.get("/igss-units/reporte")
async def get_igss_units_report(current_user: dict = Depends(require_permission("manage_igss_units"))):
    """Reporte por Unidad IGSS: cantidad de pacientes y evaluaciones por cada unidad.
    Las evaluaciones se asocian a la unidad del paciente (evaluaciones -> paciente_id -> patient.igss_unit_id).
    Incluye un renglón 'sin unidad' para pacientes/evaluaciones sin unidad IGSS asignada."""
    # Unidades (activas e inactivas para un reporte completo)
    units = await db.igss_units.find({}, {"_id": 0, "id": 1, "name": 1, "code": 1, "is_active": 1}).to_list(1000)
    unit_map = {u["id"]: u for u in units}

    # Mapa paciente -> unidad + conteo de pacientes por unidad (una sola lectura, campos mínimos)
    pacientes = await db.patients.find({}, {"_id": 0, "id": 1, "igss_unit_id": 1}).to_list(None)
    pac_unit = {}
    pacientes_por_unidad = {}
    sin_unidad_pacientes = 0
    for p in pacientes:
        uid = p.get("igss_unit_id") or None
        pac_unit[p["id"]] = uid
        if uid and uid in unit_map:
            pacientes_por_unidad[uid] = pacientes_por_unidad.get(uid, 0) + 1
        else:
            sin_unidad_pacientes += 1

    # Evaluaciones agrupadas por paciente (una sola agregación) -> se acumulan por unidad
    eval_por_paciente = await db.evaluaciones_oftalmologicas.aggregate([
        {"$group": {"_id": "$paciente_id", "count": {"$sum": 1}}}
    ]).to_list(None)
    evals_por_unidad = {}
    sin_unidad_evals = 0
    total_evals = 0
    for row in eval_por_paciente:
        cnt = row.get("count", 0)
        total_evals += cnt
        uid = pac_unit.get(row["_id"])
        if uid and uid in unit_map:
            evals_por_unidad[uid] = evals_por_unidad.get(uid, 0) + cnt
        else:
            sin_unidad_evals += cnt

    filas = []
    for u in sorted(units, key=lambda x: (x.get("name") or "").lower()):
        uid = u["id"]
        pac = pacientes_por_unidad.get(uid, 0)
        evs = evals_por_unidad.get(uid, 0)
        # Mostrar unidades activas o cualquiera con datos (oculta unidades inactivas vacías)
        if not u.get("is_active", True) and pac == 0 and evs == 0:
            continue
        filas.append({
            "unidad_id": uid,
            "nombre": u.get("name", ""),
            "codigo": u.get("code", ""),
            "activa": u.get("is_active", True),
            "pacientes": pac,
            "evaluaciones": evs,
        })

    return {
        "unidades": filas,
        "sin_unidad": {"pacientes": sin_unidad_pacientes, "evaluaciones": sin_unidad_evals},
        "totales": {
            "unidades": len(filas),
            "pacientes_con_unidad": sum(f["pacientes"] for f in filas),
            "evaluaciones_con_unidad": sum(f["evaluaciones"] for f in filas),
            "pacientes_total": len(pacientes),
            "evaluaciones_total": total_evals,
        },
    }


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
        "name": {"$regex": f"^{re.escape(unit_data.name.strip())}$", "$options": "i"},
        "is_active": True
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una unidad IGSS con este nombre")
    
    now = datetime.now(timezone.utc).isoformat()
    unit_doc = {
        "id": str(uuid.uuid4()),
        "name": unit_data.name.strip(),
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
            "name": {"$regex": f"^{re.escape(update_data['name'].strip())}$", "$options": "i"},
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


# ==================== CÓDIGO MOVIDO A routes/patients.py ====================

# ==================== CÓDIGO MOVIDO A routes/patients.py ====================

# ==================== OPTICA ROUTES MOVIDAS A routes/optica.py ====================

# ==================== PAYMENT AUTH ROUTES MOVIDAS A routes/payment_authorizations.py ====================

# ==================== CÓDIGO MOVIDO A routes/surgeries.py ====================

# ==================== CÓDIGO MOVIDO A routes/surgeries.py ====================

# ==================== FIXED EXPENSE SCHEDULER ====================

scheduler = AsyncIOScheduler()

async def generate_fixed_expenses_for_today() -> int:
    """Genera gastos a partir de los gastos fijos configurados para el día actual"""
    today = now_gt()
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
        
        # Verificar si el gasto fijo aún no ha iniciado (tiene fecha de inicio y aún no llega)
        start_date = fe.get("start_date")
        if start_date and today_str < start_date:
            logger.info(f"Gasto fijo {fe['id']} aún no inicia (fecha inicio: {start_date}), saltando...")
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
        
        # Calcular fecha de vencimiento basada en day_of_month configurado
        expense_date = today.strftime("%Y-%m-%d")
        
        # Usar el día del mes configurado para calcular la fecha de vencimiento
        configured_day = fe.get("day_of_month", today.day)
        
        # Calcular el próximo mes de vencimiento
        # Si hoy es el día configurado, el vencimiento es este mes
        # Si el día ya pasó, el vencimiento es el próximo mes
        import calendar
        
        target_year = today.year
        target_month = today.month
        
        # Si el día configurado ya pasó este mes, usar el próximo mes
        if today.day > configured_day:
            target_month += 1
            if target_month > 12:
                target_month = 1
                target_year += 1
        
        # Ajustar el día si el mes no tiene tantos días (ej: día 31 en febrero)
        last_day_of_month = calendar.monthrange(target_year, target_month)[1]
        actual_day = min(configured_day, last_day_of_month)
        
        due_date = f"{target_year}-{target_month:02d}-{actual_day:02d}"
        
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
    # Ejecutar todos los días a las 00:05 hora de Guatemala
    scheduler.add_job(
        generate_fixed_expenses_for_today,
        CronTrigger(hour=0, minute=5, timezone=GUATEMALA_TZ),
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
    
    # Sincronización automática con Google Calendar cada 10 minutos
    from routes.google_calendar import run_sync_all
    async def _sync_gcal_job():
        try:
            res = await run_sync_all()
            if res.get("configured") and res.get("medicos_sincronizados"):
                logger.info(f"Google Calendar sync: {res}")
        except Exception as e:
            logger.error(f"Error en sync automático de Google Calendar: {e}")
    scheduler.add_job(
        _sync_gcal_job,
        CronTrigger(minute="*/10"),
        id="google_calendar_sync",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler iniciado (gastos fijos: 00:05 diario, limpieza tokens: cada 6h, Google Calendar: cada 10min)")


# ==================== INCLUIR ROUTER PRINCIPAL ====================
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """Run seed on startup and create indexes"""
    # SEC-004: Backfill de token_version para usuarios legados (evita que la
    # revocación de sesiones falle en cuentas creadas sin este campo)
    await db.users.update_many(
        {"token_version": {"$exists": False}},
        {"$set": {"token_version": 1}}
    )
    await seed_default_users()
    await seed_sample_expenses()
    await seed_sample_patients()
    await seed_optica_data()

    # Rol personalizado "Administrador IGSS" (se crea una sola vez; editable desde Usuarios → Roles).
    # Base funcional: gestionar Unidades IGSS + pacientes. El SuperAdmin puede ajustar permisos y menús.
    if not await db.roles.find_one({"name": "administrador_igss"}):
        _now_igss = datetime.now(timezone.utc).isoformat()
        await db.roles.insert_one({
            "name": "administrador_igss",
            "display_name": "Administrador IGSS",
            "description": "Administra las Unidades IGSS y los pacientes IGSS",
            "permissions": {
                "view_patients": True,
                "create_patients": True,
                "edit_patients": True,
                "import_patients": True,
                "export_patients": True,
                "manage_igss_units": True,
            },
            "color": "teal",
            "is_active": True,
            "created_at": _now_igss,
            "updated_at": _now_igss,
            "created_by": "system",
        })
    
    # ==================== ÍNDICES DE SEGURIDAD ====================
    # Índice único por token de la blacklist
    await db.token_blacklist.create_index([("token", 1)], unique=True)
    # Backfill: convertir expires_at de string ISO a datetime (BSON date) para que
    # el índice TTL pueda purgar automáticamente los tokens ya expirados
    async for _bl in db.token_blacklist.find({"expires_at": {"$type": "string"}}, {"expires_at": 1}):
        try:
            await db.token_blacklist.update_one(
                {"_id": _bl["_id"]},
                {"$set": {"expires_at": datetime.fromisoformat(_bl["expires_at"])}}
            )
        except Exception:
            pass
    # Entradas de logout legadas sin expires_at: se marcan como expiradas de inmediato
    await db.token_blacklist.update_many(
        {"expires_at": {"$exists": False}},
        {"$set": {"expires_at": datetime.now(timezone.utc)}}
    )
    # Índice TTL: MongoDB elimina automáticamente cada token una vez expirado
    try:
        await db.token_blacklist.drop_index("expires_at_1")
    except Exception:
        pass
    try:
        await db.token_blacklist.create_index(
            [("expires_at", 1)], expireAfterSeconds=0, name="blacklist_ttl"
        )
    except Exception as _e:
        logging.warning(f"No se pudo crear índice TTL de token_blacklist: {_e}")
    
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
    
    # Índices de pacientes - Básicos (con manejo de conflictos)
    try:
        await db.patients.create_index([("record_number", 1)], unique=True)
    except Exception:
        pass
    try:
        # Dropear índice viejo si existe y crear nuevo con sparse
        await db.patients.drop_index("dpi_1")
    except Exception:
        pass
    try:
        await db.patients.create_index([("dpi", 1)], sparse=True, name="dpi_1_sparse")
    except Exception:
        pass
    try:
        await db.patients.create_index([("phone", 1)])
        await db.patients.create_index([("is_active", 1)])
        await db.patients.create_index([("created_at", -1)])
    except Exception:
        pass
    
    # Índices compuestos optimizados para pacientes (consultas frecuentes)
    try:
        await db.patients.create_index([("is_active", 1), ("created_at", -1)], name="patients_active_created")
        await db.patients.create_index([("first_name", 1), ("last_name", 1), ("is_active", 1)], name="patients_name_active")
        await db.patients.create_index([("referral_institution", 1), ("is_active", 1)], name="patients_institution_active")
        await db.patients.create_index([("igss_unit_id", 1), ("is_active", 1)], name="patients_igss_active")
    except Exception:
        pass
    
    # Índice de texto para búsqueda full-text
    try:
        await db.patients.create_index([
            ("first_name", "text"), 
            ("last_name", "text"), 
            ("dpi", "text"),
            ("record_number", "text"),
            ("phone", "text")
        ], name="patients_text_search")
    except Exception:
        pass  # El índice ya existe
    
    # Índices de unidades IGSS
    await db.igss_units.create_index([("name", 1)])
    await db.igss_units.create_index([("is_active", 1)])
    # Índices de NOG por unidad IGSS
    try:
        await db.igss_nogs.create_index([("unidad_id", 1), ("numero", 1)], unique=True, name="nog_unidad_numero")
        await db.igss_nogs.create_index([("id", 1)], name="nog_id_lookup")
        await db.igss_nog_acreditaciones.create_index([("nog_id", 1), ("anulada", 1)], name="acred_nog_anulada")
        await db.igss_nog_acreditaciones.create_index([("nog_id", 1), ("evaluacion_id", 1)], name="acred_nog_eval")
        await db.igss_nog_acreditaciones.create_index([("paciente_id", 1)], name="acred_paciente")
        await db.igss_nog_acreditaciones.create_index([("id", 1)], name="acred_id_lookup")
    except Exception:
        pass
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
    
    # Índices de Evaluaciones Oftalmológicas (con manejo de conflictos)
    try:
        await db.evaluaciones_oftalmologicas.create_index([("paciente_id", 1)])
        await db.evaluaciones_oftalmologicas.create_index([("fecha", -1)])
        await db.evaluaciones_oftalmologicas.create_index([("fecha_creacion", -1)])
        await db.evaluaciones_oftalmologicas.create_index([("sellado", 1)])
        await db.evaluaciones_oftalmologicas.create_index([("medico_id", 1)])
        # Índices compuestos optimizados
        await db.evaluaciones_oftalmologicas.create_index([("paciente_id", 1), ("fecha_creacion", -1)], name="eval_paciente_fecha")
        await db.evaluaciones_oftalmologicas.create_index([("medico_id", 1), ("fecha", -1)], name="eval_medico_fecha")
        await db.evaluaciones_oftalmologicas.create_index([("sellado", 1), ("fecha_creacion", -1)], name="eval_sellado_fecha")
    except Exception:
        pass
    
    # Índices para Agenda/Citas
    try:
        await db.citas.create_index([("fecha", 1)])
        await db.citas.create_index([("paciente_id", 1)])
        await db.citas.create_index([("medico_id", 1)])
        await db.citas.create_index([("estado", 1)])
        await db.citas.create_index([("fecha", 1), ("medico_id", 1), ("estado", 1)], name="citas_agenda_diaria")
        await db.citas.create_index([("paciente_id", 1), ("fecha", -1)], name="citas_paciente_fecha")
        await db.citas.create_index([("google_event_id", 1)], name="citas_google_event", sparse=True)
    except Exception:
        pass
    
    # Índices para Inventario
    try:
        await db.inventario_productos.create_index([("codigo", 1)], unique=True, sparse=True)
        await db.inventario_productos.create_index([("nombre", 1)])
        await db.inventario_productos.create_index([("categoria_id", 1)])
        await db.inventario_productos.create_index([("activo", 1)])
        await db.inventario_productos.create_index([("activo", 1), ("nombre", 1)], name="productos_activos_nombre")
        await db.inventario_productos.create_index([
            ("nombre", "text"),
            ("codigo", "text"),
            ("descripcion", "text")
        ], name="productos_text_search")
    except Exception:
        pass
    
    # Índices para Ventas POS
    try:
        await db.ventas.create_index([("numero_venta", 1)], unique=True)
        await db.ventas.create_index([("fecha", -1)])
        await db.ventas.create_index([("paciente_id", 1)])
        await db.ventas.create_index([("estado", 1)])
        await db.ventas.create_index([("fecha", -1), ("estado", 1)], name="ventas_fecha_estado")
    except Exception:
        pass
    
    # Índices para Caja
    try:
        await db.caja_sesiones.create_index([("fecha_apertura", -1)])
        await db.caja_sesiones.create_index([("estado", 1)])
        await db.caja_movimientos.create_index([("sesion_id", 1)])
        await db.caja_movimientos.create_index([("fecha", -1)])
        await db.caja_movimientos.create_index([("tipo", 1)])
    except Exception:
        pass
    
    # Índices para CRM Cirugías
    try:
        await db.surgery_candidates.create_index([("estado", 1)])
        await db.surgery_candidates.create_index([("prioridad", 1)])
        await db.surgery_candidates.create_index([("paciente_id", 1)])
        await db.surgery_candidates.create_index([("created_at", -1)])
        await db.surgery_candidates.create_index([("estado", 1), ("prioridad", 1), ("created_at", -1)], name="crm_candidatos_listado")
    except Exception:
        pass
    
    # Índices de Catálogos
    await db.catalogo_medicamentos.create_index([("nombre", 1)], unique=True)
    await db.catalogo_medicamentos.create_index([("usos", -1)])
    await db.catalogo_estudios.create_index([("nombre", 1)], unique=True)
    await db.catalogo_estudios.create_index([("usos", -1)])
    await db.catalogo_diagnosticos.create_index([("nombre", 1)], unique=True)
    await db.catalogo_diagnosticos.create_index([("usos", -1)])
    
    # Seed de catálogos oftalmológicos
    await seed_catalogos_oftalmologicos()
    await seed_catalogos_igss()
    
    # Índices de Inventario
    await db.bodegas_inventario.create_index([("codigo", 1)], unique=True)
    await db.bodegas_inventario.create_index([("origen", 1)])
    await db.categorias_inventario.create_index([("nombre", 1)])
    await db.categorias_inventario.create_index([("origen", 1)])
    await db.productos_inventario.create_index([("codigo", 1)])
    await db.productos_inventario.create_index([("codigo_barras", 1)])
    await db.productos_inventario.create_index([("nombre", "text")])
    await db.productos_inventario.create_index([("categoria_id", 1)])
    await db.productos_inventario.create_index([("origen", 1)])
    await db.existencias_inventario.create_index([("producto_id", 1), ("bodega_id", 1)], unique=True)
    await db.existencias_inventario.create_index([("origen", 1)])
    await db.lotes_inventario.create_index([("producto_id", 1), ("numero_lote", 1)], unique=True)
    await db.lotes_inventario.create_index([("fecha_vencimiento", 1)])
    await db.lotes_inventario.create_index([("origen", 1)])
    await db.movimientos_inventario.create_index([("producto_id", 1)])
    await db.movimientos_inventario.create_index([("fecha", -1)])
    await db.movimientos_inventario.create_index([("origen", 1)])
    await db.ordenes_compra.create_index([("numero_orden", 1)], unique=True)
    await db.ordenes_compra.create_index([("origen", 1)])
    await db.recepciones_inventario.create_index([("numero_recepcion", 1)], unique=True)
    await db.recepciones_inventario.create_index([("origen", 1)])
    await db.transferencias_inventario.create_index([("numero_transferencia", 1)], unique=True)
    await db.transferencias_inventario.create_index([("origen", 1)])
    await db.tomas_fisicas.create_index([("numero_toma", 1)], unique=True)
    await db.tomas_fisicas.create_index([("origen", 1)])
    
    # Seed de inventario
    await seed_inventario_data()
    
    try:
        await db.users.create_index([("username", 1)], unique=True)
    except Exception:
        pass  # Index may already exist

    # PERF: Índices sobre el campo 'id' (uuid) — evita COLLSCAN en búsquedas/updates por id.
    # A escala (17k pacientes, 68k evaluaciones) un find_one({"id": ...}) sin índice escanea
    # toda la colección; con este índice es una búsqueda directa.
    _id_index_cols = [
        "patients", "evaluaciones_oftalmologicas", "ventas", "users", "citas",
        "productos_inventario", "payments", "expenses", "payment_authorizations",
        "optica_sales", "optica_sale_payments", "optica_frames", "optica_contact_lenses",
        "optica_lens_types", "surgeries", "surgery_candidates", "surgery_crm",
        "cuentas_por_cobrar", "caja_sesiones", "caja_movimientos", "caja_cierres",
        "movimientos_inventario", "existencias_inventario", "kardex_inventario",
        "doctors", "medicos_agenda", "proveedores", "suppliers", "sociedades",
        "bodegas_inventario", "categorias_inventario", "ordenes_compra",
        "recepciones_inventario", "cierres_financieros", "responsables_cxc",
        "transferencias_inventario", "lotes_inventario", "tomas_fisicas",
        "bank_accounts", "fixed_expenses"
    ]
    for _col in _id_index_cols:
        try:
            await db[_col].create_index([("id", 1)], name="id_lookup")
        except Exception:
            pass
    # roles.name: usado por resolve_permissions en cada request no-superadmin
    try:
        await db.roles.create_index([("name", 1)], name="roles_name")
    except Exception:
        pass
    # import_source_id: usado por deduplicación del importador de evaluaciones
    try:
        await db.evaluaciones_oftalmologicas.create_index([("import_source_id", 1)], sparse=True, name="eval_import_source")
    except Exception:
        pass
    
    # Iniciar scheduler
    start_scheduler()
    
    # Log de inicio del sistema
    logger.info("🔒 Sistema iniciado con configuración de seguridad activa")
    logger.info(f"   - CORS Origins: {ALLOWED_ORIGINS}")
    logger.info(f"   - JWT Expiration: {JWT_EXPIRATION_HOURS}h")
    logger.info(f"   - Security Headers: Enabled")
    logger.info(f"   - Audit Logging: Enabled")
    logger.info(f"   - WebSocket Manager: Initialized")


# ==================== WEBSOCKET ENDPOINTS ====================

def verify_ws_token(token: str) -> Optional[dict]:
    """Verificar token JWT para WebSocket"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@app.websocket("/ws/caja")
async def websocket_caja(websocket: WebSocket, token: str = Query(None)):
    """WebSocket para actualizaciones en tiempo real de la Caja"""
    # Verificar autenticación
    user_info = None
    if token:
        user_info = verify_ws_token(token)
    
    if not user_info:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await ws_manager.connect(websocket, "caja", user_info)
    
    try:
        # Enviar estado inicial de la caja
        caja_estado = await db.caja_sesiones.find_one(
            {"estado": "abierta"},
            {"_id": 0}
        )
        await ws_manager.send_personal(websocket, {
            "type": "caja_estado_inicial",
            "data": {
                "abierta": caja_estado is not None,
                "sesion": caja_estado
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Mantener conexión activa y escuchar mensajes
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                
                # Ping/Pong para mantener conexión
                if data.get("type") == "ping":
                    await ws_manager.send_personal(websocket, {"type": "pong"})
                
            except asyncio.TimeoutError:
                # Enviar ping para verificar conexión
                try:
                    await ws_manager.send_personal(websocket, {"type": "ping"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "caja")
    except Exception as e:
        logging.error(f"Error en WebSocket caja: {e}")
        ws_manager.disconnect(websocket, "caja")


@app.websocket("/ws/agenda")
async def websocket_agenda(websocket: WebSocket, token: str = Query(None)):
    """WebSocket para actualizaciones en tiempo real de la Agenda"""
    user_info = None
    if token:
        user_info = verify_ws_token(token)
    
    if not user_info:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await ws_manager.connect(websocket, "agenda", user_info)
    
    try:
        # Enviar confirmación de conexión
        await ws_manager.send_personal(websocket, {
            "type": "connected",
            "channel": "agenda",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                
                if data.get("type") == "ping":
                    await ws_manager.send_personal(websocket, {"type": "pong"})
                
                # Suscribirse a una fecha específica
                elif data.get("type") == "subscribe_fecha":
                    fecha = data.get("fecha")
                    await ws_manager.send_personal(websocket, {
                        "type": "subscribed",
                        "fecha": fecha
                    })
                    
            except asyncio.TimeoutError:
                try:
                    await ws_manager.send_personal(websocket, {"type": "ping"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "agenda")
    except Exception as e:
        logging.error(f"Error en WebSocket agenda: {e}")
        ws_manager.disconnect(websocket, "agenda")


@app.websocket("/ws/pos")
async def websocket_pos(websocket: WebSocket, token: str = Query(None)):
    """WebSocket para actualizaciones en tiempo real del POS"""
    user_info = None
    if token:
        user_info = verify_ws_token(token)
    
    if not user_info:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await ws_manager.connect(websocket, "pos", user_info)
    
    try:
        await ws_manager.send_personal(websocket, {
            "type": "connected",
            "channel": "pos",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                
                if data.get("type") == "ping":
                    await ws_manager.send_personal(websocket, {"type": "pong"})
                    
            except asyncio.TimeoutError:
                try:
                    await ws_manager.send_personal(websocket, {"type": "ping"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "pos")
    except Exception as e:
        logging.error(f"Error en WebSocket pos: {e}")
        ws_manager.disconnect(websocket, "pos")


# Endpoint para obtener estadísticas de WebSocket (solo admin)
@api_router.get("/ws/stats")
async def get_websocket_stats(current_user: dict = Depends(require_role(["admin", "superadmin"]))):
    """Obtener estadísticas de conexiones WebSocket activas"""
    return {
        "channels": {
            channel: ws_manager.get_channel_count(channel)
            for channel in ws_manager.active_connections.keys()
        },
        "total_connections": sum(
            ws_manager.get_channel_count(ch) 
            for ch in ws_manager.active_connections.keys()
        )
    }


@app.on_event("shutdown")
async def shutdown_db_client():
    scheduler.shutdown(wait=False)
    client.close()
