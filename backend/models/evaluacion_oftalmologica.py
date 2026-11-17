# /app/backend/models/evaluacion_oftalmologica.py
# Modelos para Evaluación Oftalmológica

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
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
    av_binocular: str = ""  # AV Binocular (texto libre, ej. 20/30)
    av_cerca: str = ""  # AV Cerca (texto libre, ej. 20/30)
    
    # Lensometría / Autorefractómetro (identificador solo visual en pantalla)
    tipo_lensometria: str = "Lensometria"  # "Lensometria" | "Autorefractometro"
    lensometria_od: Optional[RefraccionOjo] = None
    lensometria_os: Optional[RefraccionOjo] = None
    
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
    resuelto: bool = False  # Deja de copiarse a futuras consultas cuando es True


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
    observaciones: str = ""


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


class MedicamentoIGSS(BaseModel):
    """Medicamento IGSS con su frecuencia de uso."""
    model_config = ConfigDict(extra="ignore")
    nombre: str = ""
    frecuencia: str = ""


class EstudioProcedimientoIGSS(BaseModel):
    """Estudio/procedimiento IGSS con indicaciones de texto libre."""
    model_config = ConfigDict(extra="ignore")
    nombre: str = ""
    indicaciones: str = ""


class MedicamentosProcedimientosIGSS(BaseModel):
    """Listas (EXCLUSIVO IGSS). Medicamentos incluyen frecuencia de uso."""
    model_config = ConfigDict(extra="ignore")
    medicamentos: List[MedicamentoIGSS] = Field(default_factory=list)
    estudios_procedimientos: List[EstudioProcedimientoIGSS] = Field(default_factory=list)

    @field_validator("medicamentos", mode="before")
    @classmethod
    def _norm_medicamentos(cls, v):
        if not v:
            return []
        out = []
        for item in v:
            if isinstance(item, str):
                nombre = item.strip()
                if nombre:
                    out.append({"nombre": nombre, "frecuencia": ""})
            elif isinstance(item, dict):
                nombre = str(item.get("nombre", "")).strip()
                frecuencia = str(item.get("frecuencia", "")).strip()
                if nombre:
                    out.append({"nombre": nombre, "frecuencia": frecuencia})
        return out

    @field_validator("estudios_procedimientos", mode="before")
    @classmethod
    def _norm_estudios(cls, v):
        if not v:
            return []
        out = []
        for item in v:
            if isinstance(item, str):
                nombre = item.strip()
                if nombre:
                    out.append({"nombre": nombre, "indicaciones": ""})
            elif isinstance(item, dict):
                nombre = str(item.get("nombre", "")).strip()
                indicaciones = str(item.get("indicaciones", "")).strip()
                if nombre:
                    out.append({"nombre": nombre, "indicaciones": indicaciones})
        return out


# ==================== PRÓXIMA CITA ====================

class ProximaCita(BaseModel):
    agendar: bool = False
    fecha: str = ""
    hora: str = ""
    medico_id: str = ""
    medico_nombre: str = ""
    tipo_cita: str = ""
    notas: str = ""
    cita_id: Optional[str] = None


# Campo "identificador" usado para reconstruir un dict mínimo válido cuando un item de
# estas listas llegó como texto suelto (legacy) en vez de objeto — mismo criterio que la
# migración ya aplicada en el frontend para igss_med_proc (string -> {nombre/descripcion, ...}).
LEGACY_LIST_ITEM_KEY_FIELD = {
    "medicamentos_actuales": "nombre",
    "medicamentos_previos": "nombre",
    "diagnosticos": "descripcion",
    "procedimientos": "descripcion",
}


def _limpiar_none(d: dict) -> dict:
    """Quita las claves en None de un dict de primer nivel, para que apliquen los
    valores por defecto del modelo (string vacío, etc.) en vez de fallar la validación."""
    return {k: v for k, v in d.items() if v is not None} if isinstance(d, dict) else d


def normalizar_items_evaluacion_legacy(data: dict) -> dict:
    """Normaliza datos heredados de evaluaciones legacy/importadas para que nunca
    rompan la validación (al guardar o al leer), ni al guardarse exitosamente
    devuelvan igual un error al frontend:
    - items de listas clínicas que llegaron como texto suelto -> dict mínimo válido
    - claves en None DENTRO de esos items (ej. {"descripcion": None}) -> se descartan
    - recomendaciones.estudios_a_realizar y recetas.medicamentos.items: mismo criterio
    - descarta cualquier item que no sea ni dict ni texto no vacío
    """
    for campo, key_field in LEGACY_LIST_ITEM_KEY_FIELD.items():
        valor = data.get(campo)
        if not isinstance(valor, list):
            continue
        normalizados = []
        for item in valor:
            if isinstance(item, dict):
                normalizados.append(_limpiar_none(item))
            elif isinstance(item, str) and item.strip():
                normalizados.append({key_field: item.strip()})
        data[campo] = normalizados

    recomendaciones = data.get("recomendaciones")
    if isinstance(recomendaciones, dict):
        recomendaciones = _limpiar_none(recomendaciones)
        estudios = recomendaciones.get("estudios_a_realizar")
        if isinstance(estudios, list):
            recomendaciones["estudios_a_realizar"] = [
                _limpiar_none(e) if isinstance(e, dict) else {"estudio": e}
                for e in estudios
                if (isinstance(e, dict)) or (isinstance(e, str) and e.strip())
            ]
        elif "estudios_a_realizar" in recomendaciones and estudios is None:
            recomendaciones["estudios_a_realizar"] = []
        data["recomendaciones"] = recomendaciones

    recetas = data.get("recetas")
    if isinstance(recetas, dict):
        medicamentos = recetas.get("medicamentos")
        if isinstance(medicamentos, dict):
            medicamentos = _limpiar_none(medicamentos)
            items = medicamentos.get("items")
            if isinstance(items, list):
                medicamentos["items"] = [_limpiar_none(it) for it in items if isinstance(it, dict)]
            elif "items" in medicamentos and items is None:
                medicamentos["items"] = []
            recetas["medicamentos"] = medicamentos
        data["recetas"] = recetas

    return data


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
    lectura_examenes: str = ""
    
    # Orden IGSS vinculada a esta consulta (para expediente/informe por orden)
    igss_orden_id: Optional[str] = None
    igss_nog_id: Optional[str] = None
    igss_nog: Optional[str] = ""
    igss_no_sps: Optional[str] = ""
    igss_codigo: Optional[str] = ""
    igss_procedimiento: Optional[str] = ""
    
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
    @model_validator(mode="before")
    @classmethod
    def _drop_none_values(cls, data):
        # El formulario puede heredar campos en null de una evaluación anterior/legacy
        # (ej. importada desde Access) al armar un borrador "nuevo" a partir de ella.
        # Se descartan para que apliquen los valores por defecto (listas/objetos vacíos)
        # en vez de que la validación rechace la petición con 422 y el guardado se
        # pierda silenciosamente en el frontend. Mismo criterio ya usado en
        # EvaluacionOftalmologicaResponse para lecturas de documentos legacy.
        if isinstance(data, dict):
            data = {k: v for k, v in data.items() if v is not None}
            data = normalizar_items_evaluacion_legacy(data)
        return data


class EvaluacionOftalmologicaUpdate(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _normalizar(cls, data):
        # Mismo saneo que en Create: descarta None explícitos (el campo queda "no
        # enviado" para exclude_unset) y normaliza items legacy en texto suelto.
        if isinstance(data, dict):
            data = normalizar_items_evaluacion_legacy({k: v for k, v in data.items()})
            data = {k: v for k, v in data.items() if v is not None}
        return data

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
    lectura_examenes: Optional[str] = None
    igss_orden_id: Optional[str] = None
    igss_nog_id: Optional[str] = None
    igss_nog: Optional[str] = None
    igss_no_sps: Optional[str] = None
    igss_codigo: Optional[str] = None
    igss_procedimiento: Optional[str] = None
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

    @model_validator(mode="before")
    @classmethod
    def _drop_none_values(cls, data):
        # Documentos antiguos/parciales pueden tener campos en null, o items de texto
        # suelto en listas que ya migraron a objetos; se normalizan para que apliquen
        # los valores por defecto y no falle la validación al leer el documento.
        if isinstance(data, dict):
            data = {k: v for k, v in data.items() if v is not None}
            data = normalizar_items_evaluacion_legacy(data)
        return data

    id: str
    cita_id: Optional[str] = None
    aviso_igss: Optional[str] = None
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
