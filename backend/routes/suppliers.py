# /app/backend/routes/suppliers.py
# Rutas de gestión de proveedores

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import uuid

from config.database import db

router = APIRouter(prefix="/suppliers", tags=["Proveedores"])

# ==================== MODELS ====================

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

# ==================== PERMISOS ====================
# - GET /suppliers: Admin, SuperAdmin, Optica
# - GET /suppliers/{id}: Admin, SuperAdmin, Optica  
# - POST /suppliers: Admin, SuperAdmin, Optica
# - PUT /suppliers/{id}: Admin, SuperAdmin (Optica NO puede editar)
# - DELETE /suppliers/{id}: Admin, SuperAdmin (Optica NO puede eliminar)

# Nota: Las rutas se mantienen en server.py por compatibilidad
# Este archivo sirve como referencia para la migración gradual
