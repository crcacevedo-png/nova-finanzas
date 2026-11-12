# /app/backend/models/caja_chica.py
# Caja Chica de Óptica: control simple de ingresos y egresos con saldo continuo.

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, List


class MovimientoCajaChicaBase(BaseModel):
    tipo: Literal["ingreso", "egreso"]
    monto: float = Field(gt=0)
    fecha: str  # "YYYY-MM-DD" — fecha real del movimiento, capturada manualmente
    solicitante: Optional[str] = None  # obligatorio solo si tipo == "egreso"
    motivo: Optional[str] = None  # obligatorio solo si tipo == "egreso"

    @field_validator("fecha")
    @classmethod
    def validar_fecha(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except (ValueError, TypeError):
            raise ValueError("fecha debe ser una fecha válida en formato YYYY-MM-DD")
        return v

    @model_validator(mode="after")
    def validar_campos_egreso(self):
        if self.tipo == "egreso":
            if not (self.solicitante and self.solicitante.strip()):
                raise ValueError("solicitante es obligatorio para un egreso")
            if not (self.motivo and self.motivo.strip()):
                raise ValueError("motivo es obligatorio para un egreso")
            self.solicitante = self.solicitante.strip()
            self.motivo = self.motivo.strip()
        return self


class MovimientoCajaChicaCreate(MovimientoCajaChicaBase):
    pass


class MovimientoCajaChicaUpdate(BaseModel):
    monto: Optional[float] = Field(default=None, gt=0)
    fecha: Optional[str] = None
    solicitante: Optional[str] = None
    motivo: Optional[str] = None

    @field_validator("fecha")
    @classmethod
    def validar_fecha(cls, v):
        from datetime import datetime
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except (ValueError, TypeError):
            raise ValueError("fecha debe ser una fecha válida en formato YYYY-MM-DD")
        return v


class MovimientoCajaChicaResponse(BaseModel):
    id: str
    tipo: str
    monto: float
    fecha: str
    solicitante: Optional[str] = None
    motivo: Optional[str] = None
    registrado_por_id: str
    registrado_por_nombre: str
    created_at: str
    updated_at: Optional[str] = None
    editado_por_nombre: Optional[str] = None


class MovimientoCajaChicaListResponse(BaseModel):
    data: List[MovimientoCajaChicaResponse]
    total: int


class ResumenCajaChicaResponse(BaseModel):
    total_ingresos: float
    total_egresos: float
    saldo: float
