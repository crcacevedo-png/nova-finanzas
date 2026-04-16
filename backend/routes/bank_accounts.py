# /app/backend/routes/bank_accounts.py
# Rutas de gestión de cuentas bancarias (Solo SuperAdmin)

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import uuid

from config.database import db

router = APIRouter(prefix="/bank-accounts", tags=["Cuentas Bancarias"])

# ==================== MODELS ====================

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

# Nota: Las rutas se mantienen en server.py por compatibilidad
# Este archivo sirve como referencia para la migración gradual
# Requiere rol SuperAdmin para todas las operaciones
