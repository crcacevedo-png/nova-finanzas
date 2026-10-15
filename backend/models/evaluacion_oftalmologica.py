# /app/backend/models/evaluacion_oftalmologica.py
# Modelos para Evaluación Oftalmológica

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# ==================== CATÁLOGOS ====================

class CatalogoItemBase(BaseModel):
    nombre: str


class CatalogoItemCreate(CatalogoItemBase):
    pass


class CatalogoItemResponse(CatalogoItemBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    usos: int = 0
    fecha_creacion: str


# ==================== MEDICAMENTOS ====================

class MedicamentoActual(BaseModel):
    nombre: str = ""
    dosis: str = ""
    frecuencia: str = ""
    via: str = ""
    desde: str = ""  # Fecha aproximada


class MedicamentoPrevio(BaseModel):
    nombre: str = ""
    dosis: str = ""
    motivo: str = ""
    periodo: str = ""


# ==================== ANTECEDENTES ====================

class Antecedentes(BaseModel):
    personales_patologicos: str = ""
    diabetes: bool = False
    hipertension: bool = False
    cardiopatia: bool = False
    enfermedad_tiroidea: bool = False
    otros_patologicos: bool = False
    oftalmologicos: str = ""
    quirurgicos: str = ""
    alergias: str = ""
    familiares: str = ""
    habitos: str = ""


# ==================== EXAMEN OFTALMOLÓGICO ====================

class RefraccionOjo(BaseModel):
    esfera: str = ""
    cilindro: str = ""
    eje: str = ""
    adicion: str = ""


class SegmentoAnteriorOjo(BaseModel):
    parpados_anexos: str = ""
    conjuntiva: str = ""
    cornea: str = ""
    camara_anterior: str = ""
    iris: str = ""
    cristalino: str = ""


class FondoOjoDetalle(BaseModel):
    papila: str = ""
    macula: str = ""
    retina: str = ""
    vasos: str = ""


class ExamenOftalmologico(BaseModel):
    # Agudeza visual
    avsc_od: str = ""  # Sin corrección OD
    avsc_os: str = ""  # Sin corrección OS
    avcc_od: str = ""  # Con corrección OD
    avcc_os: str = ""  # Con corrección OS
    
    # Refracción
    refraccion_od: RefraccionOjo = Field(default_factory=RefraccionOjo)
    refraccion_os: RefraccionOjo = Field(default_factory=RefraccionOjo)
    
    # Queratometría
    queratometria_od: str = ""
    queratometria_os: str = ""
    
    # Presión intraocular
    pio_od: str = ""
    pio_os: str = ""
    pio_metodo: str = ""
    
    # Segmento anterior (simplificado a un solo campo de texto)
    segmento_anterior: str = ""
    
    # Segmento posterior (simplificado, incluye vítreo y fondo de ojo)
    segmento_posterior: str = ""
    
    # Motilidad y pupilas
    motilidad_ocular: str = ""
    pupilas_reflejos: str = ""
    
    # Campos legacy para compatibilidad con datos antiguos
    avsc_oi: Optional[str] = ""
    avcc_oi: Optional[str] = ""
    refraccion_oi: Optional[RefraccionOjo] = None
    queratometria_oi: Optional[str] = ""
    pio_oi: Optional[str] = ""
    segmento_anterior_od: Optional[SegmentoAnteriorOjo] = None
    segmento_anterior_oi: Optional[SegmentoAnteriorOjo] = None
    vitreo_od: Optional[str] = ""
    vitreo_oi: Optional[str] = ""
    fondo_ojo_od: Optional[FondoOjoDetalle] = None
    fondo_ojo_oi: Optional[FondoOjoDetalle] = None


# ==================== DIAGNÓSTICO Y PLAN ====================

class Diagnostico(BaseModel):
    descripcion: str = ""
    codigo_cie10: str = ""
    ojo: str = "OU"  # OD, OS, OU


class EstudioARealizar(BaseModel):
    estudio: str = ""
    ojo: str = "OU"  # OD, OS, OU
    indicaciones: str = ""


class Recomendaciones(BaseModel):
    estudios_a_realizar: List[EstudioARealizar] = Field(default_factory=list)
    recomendaciones_generales: str = ""


# ==================== PROCEDIMIENTOS ====================

class Procedimiento(BaseModel):
    categoria: str = "Clínico"  # Clínico o Quirúrgico
    tipo_nombre: str = ""
    ojo: str = "OU"  # OD, OS, OU
    fecha: str = ""
    descripcion: str = ""
    resultado_notas: str = ""


# ==================== RECETAS ====================

class RecetaMedicamentoItem(BaseModel):
    medicamento: str = ""
    presentacion: str = ""
    dosis: str = ""
    frecuencia: str = ""
    duracion: str = ""
    via: str = ""
    indicaciones: str = ""


class RecetaMedicamentos(BaseModel):
    items: List[RecetaMedicamentoItem] = Field(default_factory=list)


class RecetaAnteojosOjo(BaseModel):
    esfera: str = ""
    cilindro: str = ""
    eje: str = ""
    adicion: str = ""


class RecetaAnteojos(BaseModel):
    od: RecetaAnteojosOjo = Field(default_factory=RecetaAnteojosOjo)
    os: RecetaAnteojosOjo = Field(default_factory=RecetaAnteojosOjo)
    oi: Optional[RecetaAnteojosOjo] = None  # Legacy para compatibilidad
    distancia_pupilar: str = ""
    tipo_lente: str = ""  # Monofocal, Bifocal, Progresivo
    material: str = ""
    tratamientos: str = ""  # Antirreflejo, filtro azul, fotocromático
    uso: str = ""  # Permanente, Lectura, Distancia
    observaciones: str = ""


class RecetaLentesContactoOjo(BaseModel):
    poder: str = ""
    curva_base: str = ""
    diametro: str = ""


class RecetaLentesContacto(BaseModel):
    od: RecetaLentesContactoOjo = Field(default_factory=RecetaLentesContactoOjo)
    os: RecetaLentesContactoOjo = Field(default_factory=RecetaLentesContactoOjo)
    oi: Optional[RecetaLentesContactoOjo] = None  # Legacy para compatibilidad
    marca: str = ""
    tipo: str = ""  # Blando, Rígido, Tórico, Multifocal
    regimen_reemplazo: str = ""  # Diario, Quincenal, Mensual
    observaciones: str = ""


class Recetas(BaseModel):
    medicamentos: RecetaMedicamentos = Field(default_factory=RecetaMedicamentos)
    anteojos: RecetaAnteojos = Field(default_factory=RecetaAnteojos)
    lentes_contacto: RecetaLentesContacto = Field(default_factory=RecetaLentesContacto)
    # Nuevo formato multi-receta (arrays). Se guardan como dicts para no perder
    # campos extra (id, fecha_creacion, migrado_de_legacy, etc.). Sin esto el
    # response_model descartaría las recetas migradas/importadas.
    anteojos_lista: List[dict] = Field(default_factory=list)
    lentes_contacto_lista: List[dict] = Field(default_factory=list)


class MedicamentosProcedimientosIGSS(BaseModel):
    """Listas de texto libre (EXCLUSIVO IGSS)."""
    model_config = ConfigDict(extra="ignore")
    medicamentos: List[str] = Field(default_factory=list)
    estudios_procedimientos: List[str] = Field(default_factory=list)


# ==================== PRÓXIMA CITA ====================

class ProximaCita(BaseModel):
    agendar: bool = False
    fecha: str = ""
    hora: str = ""
    medico_id: str = ""
    medico_nombre: str = ""
    tipo_cita: str = ""
    notas: str = ""


# ==================== EVALUACIÓN COMPLETA ====================

class EvaluacionOftalmologicaBase(BaseModel):
    # Encabezado
    paciente_id: str
    paciente_nombre: str = ""
    paciente_edad: int = 0
    paciente_sexo: str = ""
    paciente_expediente: str = ""
    cita_id: Optional[str] = None  # Referencia a la cita que originó la evaluación
    fecha: str = ""
    medico_id: str = ""
    medico_nombre: str = ""
    motivo_consulta: str = ""
    padecimiento_actual: str = ""
    
    # Antecedentes
    antecedentes: Antecedentes = Field(default_factory=Antecedentes)
    
    # Medicamentos
    medicamentos_actuales: List[MedicamentoActual] = Field(default_factory=list)
    medicamentos_previos: List[MedicamentoPrevio] = Field(default_factory=list)
    
    # Examen oftalmológico
    examen: ExamenOftalmologico = Field(default_factory=ExamenOftalmologico)
    
    # Diagnóstico y plan
    diagnosticos: List[Diagnostico] = Field(default_factory=list)
    plan: str = ""
    
    # Medicamentos y Procedimientos (EXCLUSIVO IGSS)
    igss_med_proc: MedicamentosProcedimientosIGSS = Field(default_factory=MedicamentosProcedimientosIGSS)
    
    # Recomendaciones
    recomendaciones: Recomendaciones = Field(default_factory=Recomendaciones)
    
    # Procedimientos
    procedimientos: List[Procedimiento] = Field(default_factory=list)
    
    # Recetas
    recetas: Recetas = Field(default_factory=Recetas)
    
    # Próxima cita
    proxima_cita: ProximaCita = Field(default_factory=ProximaCita)


class EvaluacionOftalmologicaCreate(EvaluacionOftalmologicaBase):
    pass


class EvaluacionOftalmologicaUpdate(BaseModel):
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None
    paciente_edad: Optional[int] = None
    paciente_sexo: Optional[str] = None
    paciente_expediente: Optional[str] = None
    cita_id: Optional[str] = None
    fecha: Optional[str] = None
    medico_id: Optional[str] = None
    medico_nombre: Optional[str] = None
    motivo_consulta: Optional[str] = None
    padecimiento_actual: Optional[str] = None
    antecedentes: Optional[Antecedentes] = None
    medicamentos_actuales: Optional[List[MedicamentoActual]] = None
    medicamentos_previos: Optional[List[MedicamentoPrevio]] = None
    examen: Optional[ExamenOftalmologico] = None
    diagnosticos: Optional[List[Diagnostico]] = None
    plan: Optional[str] = None
    igss_med_proc: Optional[MedicamentosProcedimientosIGSS] = None
    recomendaciones: Optional[Recomendaciones] = None
    procedimientos: Optional[List[Procedimiento]] = None
    recetas: Optional[Recetas] = None
    proxima_cita: Optional[ProximaCita] = None


class EvaluacionOftalmologicaResponse(EvaluacionOftalmologicaBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    cita_id: Optional[str] = None
    creado_por: str = ""
    creado_por_nombre: str = ""
    fecha_creacion: str = ""
    actualizado_por: str = ""
    actualizado_por_nombre: str = ""
    fecha_actualizacion: str = ""
    sellado: bool = False
    fecha_sellado: Optional[str] = None
    ultimo_autoguardado: Optional[str] = None


class EvaluacionOftalmologicaListResponse(BaseModel):
    data: List[EvaluacionOftalmologicaResponse]
    total: int
    page: int
    total_pages: int
