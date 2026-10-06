# /app/backend/models/caja.py
# Modelos para el módulo de Caja - Área Clínica (aislado de óptica)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime


# ==================== CAJA MOVIMIENTOS ====================

class CajaMovimientoBase(BaseModel):
    tipo: str  # Ingreso / Egreso
    categoria: str  # Consulta, Procedimiento, Cirugía, Gasto menor, etc.
    concepto: str
    monto: float = Field(gt=0)
    metodo_pago: str  # Efectivo / Tarjeta / Transferencia / Cheque
    referencia: Optional[str] = ""
    paciente_id: Optional[str] = ""
    paciente_nombre: Optional[str] = ""


class CajaMovimientoCreate(CajaMovimientoBase):
    pass


class CajaMovimientoUpdate(BaseModel):
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    concepto: Optional[str] = None
    monto: Optional[float] = None
    metodo_pago: Optional[str] = None
    referencia: Optional[str] = None
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None


class CajaMovimientoResponse(CajaMovimientoBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    fecha: str
    cajero_id: str
    cajero_nombre: str
    cierre_id: Optional[str] = None
    origen: str = "clinica"
    bloqueado: bool = False
    creado_por: str = ""
    fecha_creacion: str = ""


class CajaMovimientoListResponse(BaseModel):
    data: List[CajaMovimientoResponse]
    total: int
    totales: Dict = {}


# ==================== CAJA CIERRES (DIARIOS) ====================

class CajaCierreApertura(BaseModel):
    monto_apertura: float = Field(ge=0)


class CajaCierreRequest(BaseModel):
    efectivo_contado: float = Field(ge=0)
    observaciones: Optional[str] = ""


class TotalesPorMetodo(BaseModel):
    efectivo: float = 0
    tarjeta: float = 0
    transferencia: float = 0
    cheque: float = 0


class CajaCierreResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    fecha: str
    estado: str  # Abierto / Cerrado
    monto_apertura: float
    abierto_por: str
    abierto_por_nombre: str
    fecha_apertura: str
    total_ingresos: float = 0
    total_egresos: float = 0
    ingresos_por_metodo: TotalesPorMetodo = Field(default_factory=TotalesPorMetodo)
    egresos_por_metodo: TotalesPorMetodo = Field(default_factory=TotalesPorMetodo)
    saldo_esperado_efectivo: float = 0
    efectivo_contado: Optional[float] = None
    diferencia: Optional[float] = None
    observaciones: Optional[str] = ""
    cerrado_por: Optional[str] = None
    cerrado_por_nombre: Optional[str] = None
    fecha_cierre: Optional[str] = None
    origen: str = "clinica"
    reabierto_por: Optional[str] = None
    fecha_reapertura: Optional[str] = None


class CajaEstadoResponse(BaseModel):
    caja_abierta: bool
    cierre: Optional[CajaCierreResponse] = None
    saldo_efectivo_vivo: float = 0
    totales_dia: Dict = {}


# ==================== CATÁLOGO DE PAGADORES ====================

class PagadorBase(BaseModel):
    nombre: str


class PagadorCreate(PagadorBase):
    pass


class PagadorUpdate(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None


class PagadorResponse(PagadorBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    activo: bool = True
    fecha_creacion: str
    creado_por: str


# ==================== CUENTAS POR COBRAR ====================

class AbonoCreate(BaseModel):
    monto: float = Field(gt=0)
    metodo_pago: str
    referencia: Optional[str] = ""
    registrar_en_caja: bool = False  # Si se registra como ingreso en caja diaria


class Abono(BaseModel):
    id: str
    fecha: str
    monto: float
    metodo_pago: str
    referencia: Optional[str] = ""
    registrado_por: str
    registrado_por_nombre: str
    movimiento_caja_id: Optional[str] = None  # Si se registró en caja


class CuentaCobrarBase(BaseModel):
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = ""
    tipo_pagador_id: Optional[str] = None
    tipo_pagador_nombre: str = ""
    pagador_nombre: Optional[str] = ""  # Aseguradora específica, No. IGSS, etc.
    concepto: str
    referencia: Optional[str] = ""
    monto_total: float = Field(gt=0)
    fecha_vencimiento: Optional[str] = None
    notas: Optional[str] = ""


class CuentaCobrarCreate(CuentaCobrarBase):
    pass


class CuentaCobrarUpdate(BaseModel):
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None
    tipo_pagador_id: Optional[str] = None
    tipo_pagador_nombre: Optional[str] = None
    pagador_nombre: Optional[str] = None
    concepto: Optional[str] = None
    referencia: Optional[str] = None
    monto_total: Optional[float] = None
    fecha_vencimiento: Optional[str] = None
    notas: Optional[str] = None


class CuentaCobrarResponse(CuentaCobrarBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    fecha_emision: str
    monto_pagado: float = 0
    saldo_pendiente: float = 0
    estado: str = "Pendiente"  # Pendiente / Parcial / Pagado / Vencido
    abonos: List[Abono] = []
    origen: str = "clinica"
    creado_por: str = ""
    fecha_creacion: str = ""


class CuentaCobrarListResponse(BaseModel):
    data: List[CuentaCobrarResponse]
    total: int


class ResumenCxCPorTipo(BaseModel):
    tipo_pagador_id: str
    tipo_pagador_nombre: str
    total_emitido: float = 0
    total_cobrado: float = 0
    saldo_pendiente: float = 0
    cantidad_cuentas: int = 0


class ResumenCxCResponse(BaseModel):
    por_tipo: List[ResumenCxCPorTipo] = []
    total_emitido: float = 0
    total_cobrado: float = 0
    saldo_pendiente: float = 0
    cantidad_cuentas: int = 0


# ==================== CIERRES FINANCIEROS ====================

class CierreFinancieroBase(BaseModel):
    tipo: str  # Mensual / Semestral
    mes: Optional[int] = None  # 1-12 para mensual
    semestre: Optional[int] = None  # 1 o 2 para semestral
    anio: int
    observaciones: Optional[str] = ""


class CierreFinancieroCreate(CierreFinancieroBase):
    pass


class CierreFinancieroUpdate(BaseModel):
    observaciones: Optional[str] = None
    estado: Optional[str] = None


class ResumenCxCFinanciero(BaseModel):
    tipo_pagador_id: str
    tipo_pagador_nombre: str
    emitido: float = 0
    cobrado: float = 0
    pendiente: float = 0


class CierreFinancieroResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    tipo: str
    periodo: Dict  # {mes, anio} o {semestre, anio}
    fecha_inicio: str
    fecha_fin: str
    ingresos_caja: float = 0
    egresos_caja: float = 0
    costo_ventas: float = 0
    gastos_pagados: float = 0
    utilidad_bruta: float = 0
    resultado_neto: float = 0
    cxc_por_tipo: List[ResumenCxCFinanciero] = []
    cxc_total_emitido: float = 0
    cxc_total_cobrado: float = 0
    cxc_saldo_pendiente: float = 0
    observaciones: Optional[str] = ""
    estado: str = "Borrador"  # Borrador / Finalizado
    editable: bool = True
    origen: str = "clinica"
    generado_por: str = ""
    fecha_generacion: str = ""
    editado_por: Optional[str] = None
    fecha_edicion: Optional[str] = None


class CierreFinancieroListResponse(BaseModel):
    data: List[CierreFinancieroResponse]
    total: int
