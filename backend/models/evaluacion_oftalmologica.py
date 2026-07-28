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
    avsc_oi: str = ""  # Sin corrección OI
    avcc_od: str = ""  # Con corrección OD
    avcc_oi: str = ""  # Con corrección OI
    
    # Refracción
    refraccion_od: RefraccionOjo = Field(default_factory=RefraccionOjo)
    refraccion_oi: RefraccionOjo = Field(default_factory=RefraccionOjo)
    
    # Queratometría
    queratometria_od: str = ""
    queratometria_oi: str = ""
    
    # Presión intraocular
    pio_od: str = ""
    pio_oi: str = ""
    pio_metodo: str = ""
    
    # Segmento anterior
    segmento_anterior_od: SegmentoAnteriorOjo = Field(default_factory=SegmentoAnteriorOjo)
    segmento_anterior_oi: SegmentoAnteriorOjo = Field(default_factory=SegmentoAnteriorOjo)
    
    # Vítreo
    vitreo_od: str = ""
    vitreo_oi: str = ""
    
    # Fondo de ojo
    fondo_ojo_od: FondoOjoDetalle = Field(default_factory=FondoOjoDetalle)
    fondo_ojo_oi: FondoOjoDetalle = Field(default_factory=FondoOjoDetalle)
    
    # Motilidad y pupilas
    motilidad_ocular: str = ""
    pupilas_reflejos: str = ""


# ==================== DIAGNÓSTICO Y PLAN ====================

class Diagnostico(BaseModel):
    descripcion: str = ""
    codigo_cie10: str = ""
    ojo: str = "AO"  # OD, OI, AO


class EstudioARealizar(BaseModel):
    estudio: str = ""
    ojo: str = "AO"  # OD, OI, AO
    indicaciones: str = ""


class Recomendaciones(BaseModel):
    estudios_a_realizar: List[EstudioARealizar] = Field(default_factory=list)
    recomendaciones_generales: str = ""


# ==================== PROCEDIMIENTOS ====================

class Procedimiento(BaseModel):
    categoria: str = "Clínico"  # Clínico o Quirúrgico
    tipo_nombre: str = ""
    ojo: str = "AO"  # OD, OI, AO
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
    oi: RecetaAnteojosOjo = Field(default_factory=RecetaAnteojosOjo)
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
    oi: RecetaLentesContactoOjo = Field(default_factory=RecetaLentesContactoOjo)
    marca: str = ""
    tipo: str = ""  # Blando, Rígido, Tórico, Multifocal
    regimen_reemplazo: str = ""  # Diario, Quincenal, Mensual
    observaciones: str = ""


class Recetas(BaseModel):
    medicamentos: RecetaMedicamentos = Field(default_factory=RecetaMedicamentos)
    anteojos: RecetaAnteojos = Field(default_factory=RecetaAnteojos)
    lentes_contacto: RecetaLentesContacto = Field(default_factory=RecetaLentesContacto)


# ==================== EVALUACIÓN COMPLETA ====================

class EvaluacionOftalmologicaBase(BaseModel):
    # Encabezado
    paciente_id: str
    paciente_nombre: str = ""
    paciente_edad: int = 0
    paciente_sexo: str = ""
    paciente_expediente: str = ""
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
    
    # Recomendaciones
    recomendaciones: Recomendaciones = Field(default_factory=Recomendaciones)
    
    # Procedimientos
    procedimientos: List[Procedimiento] = Field(default_factory=list)
    
    # Recetas
    recetas: Recetas = Field(default_factory=Recetas)


class EvaluacionOftalmologicaCreate(EvaluacionOftalmologicaBase):
    pass


class EvaluacionOftalmologicaUpdate(BaseModel):
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None
    paciente_edad: Optional[int] = None
    paciente_sexo: Optional[str] = None
    paciente_expediente: Optional[str] = None
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
    recomendaciones: Optional[Recomendaciones] = None
    procedimientos: Optional[List[Procedimiento]] = None
    recetas: Optional[Recetas] = None


class EvaluacionOftalmologicaResponse(EvaluacionOftalmologicaBase):
    model_config = ConfigDict(extra="ignore")
    id: str
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
