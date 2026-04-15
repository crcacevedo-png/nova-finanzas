# /app/backend/models/patient.py
# Modelos de Pacientes y Unidades IGSS

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


# Modelos de Unidad IGSS
class IGSSUnitBase(BaseModel):
    name: str


class IGSSUnitCreate(IGSSUnitBase):
    pass


class IGSSUnitUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class IGSSUnitResponse(IGSSUnitBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_active: bool
    created_at: str
    updated_at: str


class IGSSUnitListResponse(BaseModel):
    data: List[IGSSUnitResponse]
    total: int


# Modelos de Paciente
class PatientBase(BaseModel):
    first_name: str
    last_name: str
    dpi: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = Field(default=None, pattern="^(masculino|femenino|otro)?$")
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    referral_institution: Optional[str] = Field(default=None, pattern="^(ninguna|igss|otro)?$")
    igss_affiliation_number: Optional[str] = None
    igss_unit_id: Optional[str] = None
    other_institution_name: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_notes: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dpi: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    referral_institution: Optional[str] = None
    igss_affiliation_number: Optional[str] = None
    igss_unit_id: Optional[str] = None
    other_institution_name: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_notes: Optional[str] = None


class PatientResponse(PatientBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    age: Optional[int] = None
    igss_unit_name: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str


class PatientListResponse(BaseModel):
    data: List[PatientResponse]
    total: int


class PatientSearchResponse(BaseModel):
    data: List[PatientResponse]
    total: int
