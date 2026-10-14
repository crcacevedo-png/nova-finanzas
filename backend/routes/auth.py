# /app/backend/routes/auth.py
# Rutas de autenticación y gestión de usuarios

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone, timedelta
from typing import List
import uuid
import jwt
import bcrypt

from config.database import db, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, blacklisted_tokens
from config.permissions import PERMISSIONS, get_permissions, resolve_permissions

# Pydantic imports
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal

router = APIRouter(prefix="/auth", tags=["Autenticación"])
users_router = APIRouter(prefix="/users", tags=["Usuarios"])

security = HTTPBearer()

# ==================== MODELS ====================

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, pattern=r'^[a-zA-Z0-9_]+$')
    name: str = Field(..., min_length=2)
    password: str = Field(..., min_length=6)
    role: Literal["superadmin", "admin", "usuario", "optica"] = "usuario"

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[Literal["superadmin", "admin", "usuario", "optica"]] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    username: str
    name: str
    role: str
    is_active: bool
    last_login: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    permissions: Optional[dict] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, username: str, role: str, token_version: int = 1) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "token_version": token_version,  # SEC-004: revocación masiva de sesiones
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        
        # SEC-004: Verificar blacklist persistente en MongoDB
        if await db.token_blacklist.find_one({"token": token}):
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

def require_role(roles):
    """Requiere que el usuario tenga uno de los roles especificados"""
    if isinstance(roles, str):
        roles = [roles]
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in roles:
            raise HTTPException(status_code=403, detail=f"Se requiere rol {roles} para esta acción")
        return current_user
    return role_checker

# ==================== AUTH ROUTES ====================

@router.post("/login", response_model=TokenResponse)
async def login(request: Request, credentials: UserLogin):
    """Login endpoint"""
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
            permissions=await resolve_permissions(user["role"])
        )
    )

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Invalidate the current token (SEC-004: blacklist persistente en MongoDB)"""
    token = current_user.get("_token")
    if token:
        await db.token_blacklist.insert_one({
            "token": token,
            "user_id": current_user.get("id"),
            "blacklisted_at": datetime.now(timezone.utc).isoformat()
        })
    return {"message": "Sesión cerrada correctamente"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**{k: v for k, v in current_user.items() if k != "_token"})

# ==================== USER MANAGEMENT ROUTES ====================

@users_router.get("", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_permission("view_user_management"))):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(**u, permissions=get_permissions(u["role"])) for u in users]

@users_router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: dict = Depends(require_permission("view_user_management"))):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UserResponse(**user, permissions=get_permissions(user["role"]))

@users_router.post("", response_model=UserResponse)
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

@users_router.put("/{user_id}", response_model=UserResponse)
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

@users_router.put("/{user_id}/toggle-active")
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

@users_router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_permission("manage_users"))):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {"message": "Usuario eliminado"}
