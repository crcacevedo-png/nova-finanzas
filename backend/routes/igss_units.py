# /app/backend/routes/igss_units.py
# Rutas del catálogo de Unidades IGSS

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import uuid

from config.database import db

router = APIRouter(prefix="/igss-units", tags=["Unidades IGSS"])

# ==================== MODELS ====================

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

# ==================== PERMISOS ====================
# - GET /igss-units: Todos los roles autenticados
# - GET /igss-units/{id}: Todos los roles autenticados
# - POST /igss-units: Solo SuperAdmin (require_permission("manage_igss_units"))
# - PUT /igss-units/{id}: Solo SuperAdmin
# - DELETE /igss-units/{id}: Solo SuperAdmin (validación de pacientes asociados)

# ==================== VALIDACIONES ====================
# - No se puede eliminar una unidad IGSS si tiene pacientes asociados
# - No se permiten nombres duplicados

# Nota: Las rutas se mantienen en server.py por compatibilidad
# Este archivo sirve como referencia para la migración gradual
