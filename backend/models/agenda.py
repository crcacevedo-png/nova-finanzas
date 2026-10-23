# /app/backend/models/agenda.py
# Modelos Pydantic para el módulo de Agenda de Pacientes

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums para estados y tipos
class EstadoCita(str, Enum):
    AGENDADA = "Agendada"
    CONFIRMADA = "Confirmada"
    PRESENTE = "Presente"
    EN_CONSULTA = "En consulta"
    ATENDIDA = "Atendida"
    NO_ASISTIO = "No asistió"
    CANCELADA = "Cancelada"

class TipoCita(str, Enum):
    PRIMERA_VEZ = "Primera vez"
    SUBSECUENTE = "Subsecuente"
    CONTROL_POSTOPERATORIO = "Control post-operatorio"
    ESTUDIO = "Estudio"
    OTRO = "Otro"

# ==================== MÉDICOS (Extensión) ====================
class MedicoAgendaUpdate(BaseModel):
    """Campos adicionales para médico en agenda"""
    usuario_id: Optional[str] = None  # Vincula con usuario del sistema
    color: Optional[str] = "#0F6E56"  # Color para la agenda
    activo_agenda: Optional[bool] = True

# ==================== CITAS ====================
class CitaBase(BaseModel):
    paciente_id: str
    paciente_nombre: str
    medico_id: str
    medico_nombre: str
    fecha: str  # YYYY-MM-DD
    hora_inicio: str  # HH:MM
    hora_fin: Optional[str] = None
    duracion_minutos: int = 20
    tipo_cita: str = TipoCita.SUBSECUENTE
    notas: Optional[str] = None
    # Orden IGSS vinculada a la consulta (opcional)
    igss_orden_id: Optional[str] = None
    igss_nog: Optional[str] = None
    igss_no_sps: Optional[str] = None
    igss_procedimiento: Optional[str] = None

class CitaCreate(CitaBase):
    pass

class CitaUpdate(BaseModel):
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None
    medico_id: Optional[str] = None
    medico_nombre: Optional[str] = None
    fecha: Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    duracion_minutos: Optional[int] = None
    tipo_cita: Optional[str] = None
    notas: Optional[str] = None
    igss_orden_id: Optional[str] = None
    igss_nog: Optional[str] = None
    igss_no_sps: Optional[str] = None
    igss_procedimiento: Optional[str] = None

class CitaEstadoUpdate(BaseModel):
    estado: EstadoCita

class CitaAsignarUpdate(BaseModel):
    asignado_a_medico_id: str
    asignado_a_medico_nombre: str

class CitaResponse(BaseModel):
    id: str
    paciente_id: str
    paciente_nombre: str
    medico_id: str
    medico_nombre: str
    fecha: str
    hora_inicio: str
    hora_fin: Optional[str] = None
    duracion_minutos: int
    tipo_cita: str
    estado: str = EstadoCita.AGENDADA
    asistio: Optional[bool] = None
    hora_llegada: Optional[str] = None
    hora_inicio_consulta: Optional[str] = None
    hora_fin_consulta: Optional[str] = None
    asignado_a_medico_id: Optional[str] = None
    asignado_a_medico_nombre: Optional[str] = None
    notas: Optional[str] = None
    tipo_agenda: str = "pacientes"
    google_event_id: Optional[str] = None
    igss_orden_id: Optional[str] = None
    igss_nog: Optional[str] = None
    igss_no_sps: Optional[str] = None
    igss_procedimiento: Optional[str] = None
    referral_institution: Optional[str] = None
    referral_institution_label: Optional[str] = None
    creado_por: str
    creado_por_nombre: Optional[str] = ""
    fecha_creacion: str
    actualizado_por: Optional[str] = None
    fecha_actualizacion: Optional[str] = None

class CitaListResponse(BaseModel):
    data: List[CitaResponse]
    total: int

# ==================== CONFIGURACIÓN DE AGENDA ====================
class TipoCitaConfig(BaseModel):
    id: str
    nombre: str
    duracion_minutos: int = 20
    color: str = "#0F6E56"
    activo: bool = True

class AgendaConfigBase(BaseModel):
    hora_apertura: str = "07:00"
    hora_cierre: str = "18:00"
    duracion_slot_minutos: int = 15
    dias_laborables: List[int] = [1, 2, 3, 4, 5, 6]  # 1=Lunes, 6=Sábado
    tipos_cita: List[TipoCitaConfig] = []
    permitir_overbooking: bool = True
    max_citas_por_slot: int = 3

class AgendaConfigUpdate(BaseModel):
    hora_apertura: Optional[str] = None
    hora_cierre: Optional[str] = None
    duracion_slot_minutos: Optional[int] = None
    dias_laborables: Optional[List[int]] = None
    tipos_cita: Optional[List[TipoCitaConfig]] = None
    permitir_overbooking: Optional[bool] = None
    max_citas_por_slot: Optional[int] = None

class AgendaConfigResponse(AgendaConfigBase):
    id: str
    actualizado_por: Optional[str] = None
    fecha_actualizacion: Optional[str] = None

# ==================== PRESENTES EN CLÍNICA ====================
class PacientePresenteResponse(BaseModel):
    cita_id: str
    paciente_id: str
    paciente_nombre: str
    hora_llegada: str
    tiempo_espera_minutos: int
    estado: str
    tipo_cita: str
    medico_id: str
    medico_nombre: str
    asignado_a_medico_id: Optional[str] = None
    asignado_a_medico_nombre: Optional[str] = None
    notas: Optional[str] = None
    referral_institution: Optional[str] = None
    referral_institution_label: Optional[str] = None

class PresentesPorMedicoResponse(BaseModel):
    medico_id: str
    medico_nombre: str
    medico_color: str
    pacientes: List[PacientePresenteResponse]
    total: int

class PresentesResponse(BaseModel):
    fecha: str
    por_medico: List[PresentesPorMedicoResponse]
    total_presentes: int

# ==================== CONTADORES DEL DÍA ====================
class ContadoresDiaResponse(BaseModel):
    fecha: str
    total_agendados: int
    total_confirmados: int
    total_presentes: int
    total_en_consulta: int
    total_atendidos: int
    total_no_asistio: int
    total_cancelados: int
    por_medico: List[dict]

# ==================== MI AGENDA (MÉDICO) ====================
class MiAgendaResponse(BaseModel):
    fecha: str
    medico_id: str
    medico_nombre: str
    citas_del_dia: List[CitaResponse]
    pacientes_presentes: List[PacientePresenteResponse]
    contadores: dict

# ==================== WALK-IN (SIN CITA) ====================
class WalkInCreate(BaseModel):
    paciente_id: str
    paciente_nombre: str
    medico_id: str
    medico_nombre: str
    tipo_cita: str = TipoCita.SUBSECUENTE
    notas: Optional[str] = None

# ==================== PRÓXIMA CITA (DESDE EVALUACIÓN) ====================
class ProximaCitaCreate(BaseModel):
    paciente_id: str
    paciente_nombre: str
    medico_id: str
    medico_nombre: str
    fecha: str
    hora_inicio: str
    tipo_cita: str = TipoCita.SUBSECUENTE
    notas: Optional[str] = None
    evaluacion_id: Optional[str] = None  # Referencia a la evaluación origen


# ==================== BLOQUEOS DE AGENDA ====================
# Permiten reservar espacios/días para que no se puedan agendar citas.
# tipo="medico": bloqueo por médico (franja de horas en una fecha o día completo)
# tipo="clinica": bloqueo para toda la clínica (un día o rango de fechas)

class TipoBloqueo(str, Enum):
    MEDICO = "medico"
    CLINICA = "clinica"

class BloqueoAgendaCreate(BaseModel):
    tipo: TipoBloqueo
    medico_id: Optional[str] = None       # Requerido si tipo="medico"
    medico_nombre: Optional[str] = None
    fecha_inicio: str                      # YYYY-MM-DD
    fecha_fin: Optional[str] = None        # YYYY-MM-DD (para rango de clínica). Si None = fecha_inicio
    dia_completo: bool = True              # Para médico: True=día completo, False=franja de horas
    hora_inicio: Optional[str] = None      # HH:MM (solo franja de horas)
    hora_fin: Optional[str] = None         # HH:MM (solo franja de horas)
    motivo: Optional[str] = None

class BloqueoAgendaResponse(BaseModel):
    id: str
    tipo: str
    medico_id: Optional[str] = None
    medico_nombre: Optional[str] = None
    fecha_inicio: str
    fecha_fin: str
    dia_completo: bool
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    motivo: Optional[str] = None
    creado_por: Optional[str] = None
    creado_por_nombre: Optional[str] = None
    fecha_creacion: Optional[str] = None

class BloqueoCreateResult(BaseModel):
    bloqueo: BloqueoAgendaResponse
    citas_en_conflicto: List[CitaResponse] = []

class BloqueoListResponse(BaseModel):
    data: List[BloqueoAgendaResponse]
    total: int

# Modelo para agendado por agente externo (API con clave fija)
class CitaExternaCreate(BaseModel):
    paciente_id: str
    paciente_nombre: str
    medico_id: str
    medico_nombre: str
    fecha: str                 # YYYY-MM-DD
    hora_inicio: str           # HH:MM
    hora_fin: Optional[str] = None
    duracion_minutos: int = 20
    tipo_cita: str = TipoCita.SUBSECUENTE
    notas: Optional[str] = None

class DisponibilidadResponse(BaseModel):
    disponible: bool
    motivo: Optional[str] = None
    bloqueo: Optional[BloqueoAgendaResponse] = None
    citas_existentes: List[CitaResponse] = []

