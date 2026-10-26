# /app/backend/routes/evaluaciones.py
# Módulo de Evaluaciones Oftalmológicas - CRUD y catálogos

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from utils.timezone import now_gt, today_str_gt
from pydantic import BaseModel, ConfigDict
import uuid
import re
import io

from config.database import db
from routes.auth import get_current_user, require_role

from models.evaluacion_oftalmologica import (
    EvaluacionOftalmologicaCreate,
    EvaluacionOftalmologicaUpdate,
    EvaluacionOftalmologicaResponse,
    EvaluacionOftalmologicaListResponse,
    CatalogoItemResponse,
    MedicamentosProcedimientosIGSS
)

# PDF imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage, KeepTogether, KeepInFrame
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as _pdfcanvas
import base64 as _base64
import os as _os

LOGO_PATH = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "assets", "logo_nova.png")

INSTITUTION_LABELS_PDF = {
    "particular": "Particular",
    "igss": "IGSS",
    "seguro_privado": "Seguro Privado",
    "otra": "Otra Institución",
}

router = APIRouter(prefix="/evaluaciones", tags=["Evaluaciones Oftalmológicas"])
catalogos_router = APIRouter(prefix="/catalogos", tags=["Catálogos - Evaluaciones"])

# NOTA: El límite de 24 horas ha sido eliminado a petición del usuario.
# Los expedientes ahora pueden editarse sin restricción temporal.
# Solo el sellado manual (sellado=True) bloquea la edición.


# ==================== HELPERS ====================

def calcular_edad(fecha_nacimiento: str) -> int:
    """Calcula la edad a partir de fecha de nacimiento"""
    try:
        birth = datetime.strptime(fecha_nacimiento, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return age
    except Exception:
        return 0


def verificar_sellado(evaluacion: dict) -> tuple:
    """Verifica si una evaluación está sellada manualmente.
    Ya no se aplica el límite automático de 24 horas."""
    if evaluacion.get("sellado", False):
        return True, "Expediente sellado manualmente"
    return False, ""


async def actualizar_catalogo(coleccion: str, nombre: str):
    """Actualiza o inserta un item en el catálogo"""
    if not nombre or not nombre.strip():
        return
    
    nombre_normalizado = nombre.strip()
    existente = await db[coleccion].find_one(
        {"nombre": {"$regex": f"^{re.escape(nombre_normalizado)}$", "$options": "i"}}
    )
    
    if existente:
        await db[coleccion].update_one(
            {"id": existente["id"]},
            {"$inc": {"usos": 1}}
        )
    else:
        await db[coleccion].insert_one({
            "id": str(uuid.uuid4()),
            "nombre": nombre_normalizado,
            "usos": 1,
            "fecha_creacion": datetime.now(timezone.utc).isoformat()
        })


async def procesar_catalogos_evaluacion(evaluacion_data: dict):
    """Procesa y actualiza los catálogos con datos de la evaluación"""
    # Medicamentos actuales
    for med in evaluacion_data.get("medicamentos_actuales", []):
        if med.get("nombre"):
            await actualizar_catalogo("catalogo_medicamentos", med["nombre"])
    
    # Medicamentos previos
    for med in evaluacion_data.get("medicamentos_previos", []):
        if med.get("nombre"):
            await actualizar_catalogo("catalogo_medicamentos", med["nombre"])
    
    # Diagnósticos
    for diag in evaluacion_data.get("diagnosticos", []):
        if diag.get("descripcion"):
            await actualizar_catalogo("catalogo_diagnosticos", diag["descripcion"])
    
    # Estudios
    recomendaciones = evaluacion_data.get("recomendaciones", {})
    for estudio in recomendaciones.get("estudios_a_realizar", []):
        if estudio.get("estudio"):
            await actualizar_catalogo("catalogo_estudios", estudio["estudio"])
    
    # Medicamentos de receta
    recetas = evaluacion_data.get("recetas", {})
    medicamentos_receta = recetas.get("medicamentos", {})
    for item in medicamentos_receta.get("items", []):
        if item.get("medicamento"):
            await actualizar_catalogo("catalogo_medicamentos", item["medicamento"])


# ==================== AUDIT HELPER ====================

class AuditLogger:
    @staticmethod
    async def log(action: str, user_id: str, user_name: str, details: dict = None, ip_address: str = None):
        audit_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user_id": user_id,
            "user_name": user_name,
            "ip_address": ip_address,
            "details": details or {},
        }
        try:
            await db.audit_logs.insert_one(audit_entry)
        except Exception:
            pass

audit = AuditLogger()


# ==================== IMPORTACIÓN MASIVA DE EVALUACIONES ====================
# Enlaza cada evaluación (extraída de Access) con su paciente por el
# número de expediente (record_number) o, en su defecto, por DPI.

class ImportEvaluacionItem(BaseModel):
    """Esquema flexible para importar evaluaciones.
    Los campos clínicos adicionales se conservan tal cual (extra='allow')."""
    model_config = ConfigDict(extra="allow")
    # Clave de enlace al paciente (al menos una es obligatoria)
    expediente: Optional[str] = None
    record_number: Optional[str] = None
    paciente_expediente: Optional[str] = None
    dpi: Optional[str] = None
    # Identificador de origen (PK de Access) para deduplicar reimportaciones
    id_origen: Optional[str] = None
    source_id: Optional[str] = None
    # Campos clínicos comunes (el resto fluye por extra='allow')
    fecha: Optional[str] = None
    medico_nombre: Optional[str] = None


class ImportEvalBatchRequest(BaseModel):
    items: List[ImportEvaluacionItem]
    batch_number: int = 1
    skip_duplicates: bool = True


# Claves meta que NO forman parte del documento clínico de la evaluación
_EVAL_LINK_KEYS = {"expediente", "record_number", "dpi", "id_origen", "source_id", "_id"}


def _norm_fecha_eval(value) -> str:
    """Normaliza una fecha a YYYY-MM-DD; si no reconoce el formato la deja igual."""
    if not value:
        return ""
    v = str(value).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}', v):
        return v[:10]
    m = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', v)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    m = re.match(r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$', v)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    return v


def _get_expediente(data: dict) -> str:
    """Obtiene la clave de expediente desde cualquiera de los alias aceptados."""
    return (
        data.get("record_number")
        or data.get("expediente")
        or data.get("paciente_expediente")
        or ""
    ).strip()


async def _mapear_pacientes(expedientes: set, dpis: set):
    """Construye mapas expediente->paciente y dpi->paciente para enlazar en lote."""
    proj = {"_id": 0, "id": 1, "record_number": 1, "first_name": 1,
            "last_name": 1, "gender": 1, "birth_date": 1, "dpi": 1}
    mapa_exp, mapa_dpi = {}, {}
    if expedientes:
        cursor = db.patients.find({"record_number": {"$in": list(expedientes)}}, proj)
        async for p in cursor:
            if p.get("record_number"):
                mapa_exp[p["record_number"]] = p
    if dpis:
        cursor = db.patients.find({"dpi": {"$in": list(dpis)}}, proj)
        async for p in cursor:
            if p.get("dpi"):
                mapa_dpi[p["dpi"]] = p
    return mapa_exp, mapa_dpi


# ==================== CATÁLOGOS ENDPOINTS ====================

@catalogos_router.get("/medicamentos")
async def get_catalogo_medicamentos(
    search: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Autocomplete de medicamentos"""
    query = {}
    if search:
        query["nombre"] = {"$regex": re.escape(search), "$options": "i"}
    
    items = await db.catalogo_medicamentos.find(query, {"_id": 0}).sort("usos", -1).limit(limit).to_list(limit)
    return items


@catalogos_router.get("/estudios")
async def get_catalogo_estudios(
    search: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Autocomplete de estudios"""
    query = {}
    if search:
        query["nombre"] = {"$regex": re.escape(search), "$options": "i"}
    
    items = await db.catalogo_estudios.find(query, {"_id": 0}).sort("usos", -1).limit(limit).to_list(limit)
    return items


@catalogos_router.get("/diagnosticos")
async def get_catalogo_diagnosticos(
    search: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Autocomplete de diagnósticos"""
    query = {}
    if search:
        query["nombre"] = {"$regex": re.escape(search), "$options": "i"}
    
    items = await db.catalogo_diagnosticos.find(query, {"_id": 0}).sort("usos", -1).limit(limit).to_list(limit)
    return items


@catalogos_router.get("/igss-medicamentos")
async def get_catalogo_igss_medicamentos(
    search: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Autocomplete de medicamentos oftalmológicos IGSS (nombre o código)."""
    query = {}
    if search:
        rx = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [{"nombre": rx}, {"codigo": rx}]
    items = await db.catalogo_igss_medicamentos.find(query, {"_id": 0}).sort("nombre", 1).limit(limit).to_list(limit)
    return items


@catalogos_router.get("/igss-procedimientos")
async def get_catalogo_igss_procedimientos(
    search: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Autocomplete de estudios/procedimientos oftalmológicos IGSS (nombre o código)."""
    query = {}
    if search:
        rx = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [{"nombre": rx}, {"codigo": rx}]
    items = await db.catalogo_igss_procedimientos.find(query, {"_id": 0}).sort("nombre", 1).limit(limit).to_list(limit)
    return items


# ==================== EVALUACIONES ENDPOINTS ====================

@router.get("", response_model=EvaluacionOftalmologicaListResponse)
async def get_evaluaciones(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    paciente_id: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Listar evaluaciones oftalmológicas"""
    query = {}
    
    if paciente_id:
        query["paciente_id"] = paciente_id
    if fecha_desde:
        query["fecha"] = {"$gte": fecha_desde}
    if fecha_hasta:
        if "fecha" in query:
            query["fecha"]["$lte"] = fecha_hasta
        else:
            query["fecha"] = {"$lte": fecha_hasta}
    if search:
        query["$or"] = [
            {"paciente_nombre": {"$regex": search, "$options": "i"}},
            {"paciente_expediente": {"$regex": search, "$options": "i"}},
            {"motivo_consulta": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.evaluaciones_oftalmologicas.count_documents(query)
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    skip = (page - 1) * limit
    
    evaluaciones = await db.evaluaciones_oftalmologicas.find(query, {"_id": 0}).sort("fecha_creacion", -1).skip(skip).limit(limit).to_list(limit)
    
    # Verificar y actualizar sellado para cada evaluación
    for eval in evaluaciones:
        debe_sellar, _ = verificar_sellado(eval)
        if debe_sellar and not eval.get("sellado"):
            await db.evaluaciones_oftalmologicas.update_one(
                {"id": eval["id"]},
                {"$set": {"sellado": True, "fecha_sellado": datetime.now(timezone.utc).isoformat()}}
            )
            eval["sellado"] = True
            eval["fecha_sellado"] = datetime.now(timezone.utc).isoformat()
    
    return {
        "data": evaluaciones,
        "total": total,
        "page": page,
        "total_pages": total_pages
    }


@router.get("/{evaluacion_id}", response_model=EvaluacionOftalmologicaResponse)
async def get_evaluacion(
    evaluacion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener una evaluación por ID"""
    evaluacion = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # Verificar y actualizar sellado
    debe_sellar, _ = verificar_sellado(evaluacion)
    if debe_sellar and not evaluacion.get("sellado"):
        await db.evaluaciones_oftalmologicas.update_one(
            {"id": evaluacion_id},
            {"$set": {"sellado": True, "fecha_sellado": datetime.now(timezone.utc).isoformat()}}
        )
        evaluacion["sellado"] = True
        evaluacion["fecha_sellado"] = datetime.now(timezone.utc).isoformat()
    
    return evaluacion


@router.get("/{evaluacion_id}/pdf")
async def get_evaluacion_pdf(
    evaluacion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generar PDF de evaluación oftalmológica completa"""
    evaluacion = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # Obtener datos del paciente
    paciente = await db.patients.find_one({"id": evaluacion.get("paciente_id")}, {"_id": 0}) or {}
    
    # Resolver nombre de unidad IGSS si aplica
    igss_unit_name = ""
    if paciente.get("igss_unit_id"):
        unit = await db.igss_units.find_one({"id": paciente["igss_unit_id"]}, {"_id": 0, "name": 1})
        igss_unit_name = unit["name"] if unit else ""
    
    # Obtener datos del médico (para firma, colegiado y especialidad)
    medico = None
    if evaluacion.get("medico_id"):
        medico = await db.doctors.find_one({"id": evaluacion.get("medico_id")}, {"_id": 0})
    if not medico and evaluacion.get("medico_nombre"):
        medico = await db.doctors.find_one(
            {"name": {"$regex": f"^{re.escape(evaluacion['medico_nombre'].strip())}$", "$options": "i"}, "is_active": True},
            {"_id": 0}
        )
    if not medico and evaluacion.get("creado_por"):
        medico = await db.doctors.find_one({"usuario_id": evaluacion.get("creado_por"), "is_active": True}, {"_id": 0})
    
    # Crear PDF en memoria
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=20, bottomMargin=150)
    
    # Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=13, spaceAfter=2))
    styles.add(ParagraphStyle(name='SubtitleCenter', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, textColor=colors.grey))
    styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading2'], fontSize=9.5, spaceBefore=5, spaceAfter=2, textColor=colors.HexColor('#0F6E56')))
    styles.add(ParagraphStyle(name='FieldLabel', parent=styles['Normal'], fontSize=7.5, textColor=colors.grey))
    styles.add(ParagraphStyle(name='FieldValue', parent=styles['Normal'], fontSize=8, spaceBefore=1))
    styles.add(ParagraphStyle(name='SmallText', parent=styles['Normal'], fontSize=7, textColor=colors.grey))
    styles.add(ParagraphStyle(name='CellLabel', parent=styles['Normal'], fontSize=8.25, leading=10, fontName='Helvetica-Bold', textColor=colors.grey))
    styles.add(ParagraphStyle(name='CellValue', parent=styles['Normal'], fontSize=8.25, leading=10, fontName='Helvetica'))
    
    elements = []
    
    # ===== ENCABEZADO CON LOGO =====
    titulo_cell = [
        Paragraph("EVALUACIÓN OFTALMOLÓGICA", styles['TitleCenter']),
        Paragraph("Novavisión - Clínica Oftalmológica", styles['SubtitleCenter']),
    ]
    if _os.path.exists(LOGO_PATH):
        logo = RLImage(LOGO_PATH, width=1.125*inch, height=1.5*inch)
        header_table = Table([[logo, titulo_cell]], colWidths=[1.6*inch, 5.4*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
    else:
        elements.extend(titulo_cell)
    elements.append(Spacer(1, 1))
    
    # Línea divisoria
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0F6E56')))
    elements.append(Spacer(1, 4))
    
    # ===== DATOS DEL PACIENTE =====
    fecha_eval = evaluacion.get("fecha", "")
    if fecha_eval:
        try:
            fecha_obj = datetime.fromisoformat(fecha_eval.replace("Z", "+00:00"))
            fecha_eval = fecha_obj.strftime("%d/%m/%Y")
        except Exception:
            pass
    
    # ===== DATOS DEL PACIENTE (completos) =====
    def _calc_edad(bd):
        try:
            b = datetime.fromisoformat(str(bd))
            today = datetime.now()
            return today.year - b.year - ((today.month, today.day) < (b.month, b.day))
        except Exception:
            return None

    gender_label = {"masculino": "Masculino", "femenino": "Femenino", "otro": "Otro"}
    _apellidos = (paciente.get('last_name') or '').strip()
    _nombres = (paciente.get('first_name') or '').strip()
    nombre = f"{_apellidos} {_nombres}".strip() or paciente.get("full_name") or evaluacion.get("paciente_nombre", "N/A")
    expediente = paciente.get("record_number") or evaluacion.get("paciente_expediente", "N/A")
    edad_calc = _calc_edad(paciente.get("birth_date")) if paciente.get("birth_date") else evaluacion.get("paciente_edad")
    edad_str = f"{edad_calc} años" if edad_calc is not None else "N/A"
    sexo = gender_label.get(paciente.get("gender", ""), paciente.get("gender") or evaluacion.get("paciente_sexo", "N/A"))
    inst_label = INSTITUTION_LABELS_PDF.get(paciente.get("referral_institution", ""), paciente.get("referral_institution", ""))

    # Fecha de nacimiento formateada
    fnac = paciente.get("birth_date", "")
    if fnac:
        try:
            fnac = datetime.fromisoformat(str(fnac)).strftime("%d/%m/%Y")
        except Exception:
            pass

    # Construir pares (label, value) solo con datos presentes
    pares = [
        ('Paciente:', nombre),
        ('Expediente:', expediente),
        ('Edad:', edad_str),
        ('Sexo:', sexo),
        ('Fecha Nac.:', fnac),
        ('DPI:', paciente.get("dpi")),
        ('Email:', paciente.get("email")),
    ]
    if paciente.get("referral_institution") == "igss":
        # Preferir el snapshot de la orden vinculada a la evaluación; fallback al paciente
        _nog = (evaluacion.get("igss_nog") or paciente.get("igss_nog") or "")
        _sps = (evaluacion.get("igss_no_sps") or paciente.get("igss_no_sps") or "")
        _cod = (evaluacion.get("igss_codigo") or paciente.get("igss_codigo") or "")
        _proc = (evaluacion.get("igss_procedimiento") or "")
        _tipo_compra_labels = {
            "compra_directa": "Compra Directa",
            "baja_cuantia": "Baja Cuantía",
            "contrato": "Contrato",
            "convenio": "Convenio",
        }
        _tc_raw = (paciente.get("igss_tipo_compra") or "")
        _tc = _tipo_compra_labels.get(_tc_raw, _tc_raw)
        pares.extend([
            ('IGSS Unidad:', igss_unit_name),
            ('IGSS Afiliación:', paciente.get("igss_afiliacion")),
            ('IGSS NOG:', _nog),
            ('IGSS No. SPS:', _sps),
            ('IGSS Código:', _cod),
            ('IGSS Tipo de Compra:', _tc),
        ])
        if _proc:
            pares.append(('IGSS Procedimiento:', _proc))
    pares.extend([
        ('Fecha Evaluación:', fecha_eval),
        ('Médico:', evaluacion.get("medico_nombre")),
    ])

    # Filtrar vacíos y armar filas de 2 pares (4 columnas), con celdas Paragraph para que el texto se ajuste
    pares = [(l, str(v)) for l, v in pares if v not in (None, "", "N/A años") and str(v).strip() not in ("", "None")]
    import html as _html
    paciente_data = []
    for i in range(0, len(pares), 2):
        p1 = pares[i]
        fila = [Paragraph(p1[0], styles['CellLabel']), Paragraph(_html.escape(p1[1]), styles['CellValue'])]
        if i + 1 < len(pares):
            p2 = pares[i + 1]
            fila += [Paragraph(p2[0], styles['CellLabel']), Paragraph(_html.escape(p2[1]), styles['CellValue'])]
        else:
            fila += ['', '']
        paciente_data.append(fila)

    if paciente_data:
        t = Table(paciente_data, colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        elements.append(t)
    elements.append(Spacer(1, 4))
    
    # ===== MOTIVO DE CONSULTA =====
    elements.append(Paragraph("MOTIVO DE CONSULTA", styles['SectionTitle']))
    elements.append(Paragraph(evaluacion.get("motivo_consulta", "No especificado") or "No especificado", styles['FieldValue']))
    
    # ===== PADECIMIENTO ACTUAL =====
    if evaluacion.get("padecimiento_actual"):
        elements.append(Paragraph("PADECIMIENTO ACTUAL", styles['SectionTitle']))
        elements.append(Paragraph(evaluacion.get("padecimiento_actual", ""), styles['FieldValue']))
    
    # ===== ANTECEDENTES =====
    antecedentes = evaluacion.get("antecedentes", {})
    if any(antecedentes.values()):
        elements.append(Paragraph("ANTECEDENTES", styles['SectionTitle']))
        
        # Patológicos
        patologicos = []
        if antecedentes.get("diabetes"): patologicos.append("Diabetes")
        if antecedentes.get("hipertension"): patologicos.append("Hipertensión")
        if antecedentes.get("cardiopatia"): patologicos.append("Cardiopatía")
        if antecedentes.get("enfermedad_tiroidea"): patologicos.append("Enf. Tiroidea")
        
        if patologicos or antecedentes.get("personales_patologicos"):
            elementos_ant = ", ".join(patologicos)
            if antecedentes.get("personales_patologicos"):
                elementos_ant += f". {antecedentes.get('personales_patologicos')}" if elementos_ant else antecedentes.get('personales_patologicos')
            elements.append(Paragraph(f"<b>Personales Patológicos:</b> {elementos_ant or 'Ninguno'}", styles['FieldValue']))
        
        if antecedentes.get("oftalmologicos"):
            elements.append(Paragraph(f"<b>Oftalmológicos:</b> {antecedentes.get('oftalmologicos')}", styles['FieldValue']))
        if antecedentes.get("quirurgicos"):
            elements.append(Paragraph(f"<b>Quirúrgicos:</b> {antecedentes.get('quirurgicos')}", styles['FieldValue']))
        if antecedentes.get("alergias"):
            elements.append(Paragraph(f"<b>Alergias:</b> {antecedentes.get('alergias')}", styles['FieldValue']))
        if antecedentes.get("familiares"):
            elements.append(Paragraph(f"<b>Familiares:</b> {antecedentes.get('familiares')}", styles['FieldValue']))
    
    # ===== EXAMEN OFTALMOLÓGICO =====
    examen = evaluacion.get("examen", {})
    elements.append(Paragraph("EXAMEN OFTALMOLÓGICO", styles['SectionTitle']))
    
    # Agudeza Visual y PIO en tabla
    av_data = [
        ['', 'OD (Ojo Derecho)', 'OS (Ojo Izquierdo)'],
        ['AV sin corrección', examen.get("avsc_od", "-"), examen.get("avsc_os", examen.get("avsc_oi", "-"))],
        ['AV con corrección', examen.get("avcc_od", "-"), examen.get("avcc_os", examen.get("avcc_oi", "-"))],
        ['Presión Intraocular', examen.get("pio_od", "-"), examen.get("pio_os", examen.get("pio_oi", "-"))],
    ]
    
    av_table = Table(av_data, colWidths=[1.4*inch, 1.4*inch, 1.4*inch])
    av_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f9f6')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
    ]))
    av_table.hAlign = 'LEFT'
    elements.append(av_table)
    elements.append(Spacer(1, 3))
    
    # Refracción
    ref_od = examen.get("refraccion_od", {})
    ref_os = examen.get("refraccion_os", examen.get("refraccion_oi", {}))
    
    if any([ref_od.get("esfera"), ref_od.get("cilindro"), ref_os.get("esfera"), ref_os.get("cilindro")]):
        ref_data = [
            ['Refracción', 'Esfera', 'Cilindro', 'Eje', 'Adición'],
            ['OD', ref_od.get("esfera", "-"), ref_od.get("cilindro", "-"), ref_od.get("eje", "-"), ref_od.get("adicion", "-")],
            ['OS', ref_os.get("esfera", "-"), ref_os.get("cilindro", "-"), ref_os.get("eje", "-"), ref_os.get("adicion", "-")],
        ]
        
        ref_table = Table(ref_data, colWidths=[0.85*inch, 0.6*inch, 0.6*inch, 0.5*inch, 0.6*inch])
        ref_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f9f6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
        ]))
        ref_table.hAlign = 'LEFT'
        elements.append(Paragraph("<b>Refracción:</b>", styles['FieldValue']))
        elements.append(ref_table)
        elements.append(Spacer(1, 4))
    
    # Segmento anterior y posterior
    if examen.get("segmento_anterior"):
        elements.append(Paragraph(f"<b>Segmento Anterior:</b> {examen.get('segmento_anterior')}", styles['FieldValue']))
    if examen.get("segmento_posterior"):
        elements.append(Paragraph(f"<b>Segmento Posterior / Fondo de Ojo:</b> {examen.get('segmento_posterior')}", styles['FieldValue']))
    if examen.get("motilidad_ocular"):
        elements.append(Paragraph(f"<b>Motilidad Ocular:</b> {examen.get('motilidad_ocular')}", styles['FieldValue']))
    if examen.get("pupilas_reflejos"):
        elements.append(Paragraph(f"<b>Pupilas y Reflejos:</b> {examen.get('pupilas_reflejos')}", styles['FieldValue']))
    
    # ===== DIAGNÓSTICOS =====
    diagnosticos = evaluacion.get("diagnosticos", [])
    if diagnosticos:
        elements.append(Paragraph("DIAGNÓSTICOS", styles['SectionTitle']))
        for idx, diag in enumerate(diagnosticos, 1):
            ojo_str = {"OD": "Ojo Derecho", "OS": "Ojo Izquierdo", "OU": "Ambos Ojos"}.get(diag.get("ojo", "OU"), "Ambos")
            cie = f" (CIE-10: {diag.get('codigo_cie10')})" if diag.get("codigo_cie10") else ""
            elements.append(Paragraph(f"{idx}. {diag.get('descripcion', 'N/A')} - {ojo_str}{cie}", styles['FieldValue']))
    
    # ===== PLAN DE TRATAMIENTO =====
    if evaluacion.get("plan"):
        elements.append(Paragraph("PLAN DE TRATAMIENTO", styles['SectionTitle']))
        elements.append(Paragraph(evaluacion.get("plan", ""), styles['FieldValue']))
    
    # ===== RECOMENDACIONES =====
    recomendaciones = evaluacion.get("recomendaciones", {})
    estudios = recomendaciones.get("estudios_a_realizar", [])
    rec_generales = recomendaciones.get("recomendaciones_generales", "")
    
    if estudios or rec_generales:
        elements.append(Paragraph("RECOMENDACIONES", styles['SectionTitle']))
        if estudios:
            elements.append(Paragraph("<b>Estudios a realizar:</b>", styles['FieldValue']))
            for est in estudios:
                ojo_str = {"OD": "OD", "OS": "OS", "OU": "AO"}.get(est.get("ojo", "OU"), "AO")
                elements.append(Paragraph(f"• {est.get('estudio', '')} ({ojo_str})", styles['FieldValue']))
        if rec_generales:
            elements.append(Paragraph(f"<b>Generales:</b> {rec_generales}", styles['FieldValue']))
    
    # ===== RECETAS =====
    recetas = evaluacion.get("recetas", {})
    
    # Receta de Medicamentos
    med_receta = recetas.get("medicamentos", {}).get("items", [])
    if med_receta:
        elements.append(Paragraph("RECETA DE MEDICAMENTOS", styles['SectionTitle']))
        for med in med_receta:
            med_line = f"• <b>{med.get('medicamento', '')}</b>"
            if med.get("presentacion"): med_line += f" ({med.get('presentacion')})"
            if med.get("dosis"): med_line += f" - {med.get('dosis')}"
            if med.get("frecuencia"): med_line += f", {med.get('frecuencia')}"
            if med.get("duracion"): med_line += f" por {med.get('duracion')}"
            if med.get("via"): med_line += f" ({med.get('via')})"
            elements.append(Paragraph(med_line, styles['FieldValue']))
            if med.get("indicaciones"):
                elements.append(Paragraph(f"   <i>Indicaciones: {med.get('indicaciones')}</i>", styles['SmallText']))
        _obs_med = (recetas.get("medicamentos", {}).get("observaciones", "") or "").strip()
        if _obs_med:
            elements.append(Paragraph(f"<b>Observaciones:</b> {_html.escape(_obs_med)}", styles['FieldValue']))
    
    # Receta de Anteojos
    anteojos = recetas.get("anteojos", {})
    ant_od = anteojos.get("od", {})
    ant_os = anteojos.get("os", anteojos.get("oi", {}))
    
    if any([ant_od.get("esfera"), ant_od.get("cilindro"), ant_os.get("esfera"), ant_os.get("cilindro")]):
        elements.append(Paragraph("RECETA DE ANTEOJOS", styles['SectionTitle']))
        
        ant_data = [
            ['', 'Esfera', 'Cilindro', 'Eje', 'Adición'],
            ['OD', ant_od.get("esfera", "-"), ant_od.get("cilindro", "-"), ant_od.get("eje", "-"), ant_od.get("adicion", "-")],
            ['OS', ant_os.get("esfera", "-"), ant_os.get("cilindro", "-"), ant_os.get("eje", "-"), ant_os.get("adicion", "-")],
        ]
        
        ant_table = Table(ant_data, colWidths=[0.6*inch, 0.7*inch, 0.7*inch, 0.6*inch, 0.6*inch])
        ant_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fff9e6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
        ]))
        ant_table.hAlign = 'LEFT'
        elements.append(ant_table)
        
        extras = []
        if anteojos.get("distancia_pupilar"): extras.append(f"DP: {anteojos.get('distancia_pupilar')}")
        if anteojos.get("tipo_lente"): extras.append(f"Tipo: {anteojos.get('tipo_lente')}")
        if anteojos.get("material"): extras.append(f"Material: {anteojos.get('material')}")
        if anteojos.get("uso"): extras.append(f"Uso: {anteojos.get('uso')}")
        if extras:
            elements.append(Paragraph(" | ".join(extras), styles['SmallText']))
    
    # ===== MEDICAMENTOS Y ESTUDIOS / PROCEDIMIENTOS =====
    igss_mp = evaluacion.get("igss_med_proc", {}) or {}
    med_rows = []
    for m in (igss_mp.get("medicamentos", []) or []):
        if isinstance(m, str):
            nom, frec = m.strip(), ""
        else:
            nom, frec = (m.get("nombre", "") or "").strip(), (m.get("frecuencia", "") or "").strip()
        if nom:
            med_rows.append((nom, frec))
    est_rows = []
    for e in (igss_mp.get("estudios_procedimientos", []) or []):
        if isinstance(e, str):
            nom, ind = e.strip(), ""
        else:
            nom, ind = (e.get("nombre", "") or "").strip(), (e.get("indicaciones", "") or "").strip()
        if nom:
            est_rows.append((nom, ind))

    if med_rows:
        elements.append(Paragraph("MEDICAMENTOS", styles['SectionTitle']))
        med_style = ParagraphStyle('MedItem', parent=styles['Normal'], fontSize=8, leading=10, leftIndent=10)
        for i, (nom, frec) in enumerate(med_rows, 1):
            txt = f"<b>{i}.</b> {_html.escape(nom)}"
            if frec:
                txt += f" <font color='#555555'>— {_html.escape(frec)}</font>"
            elements.append(Paragraph(txt, med_style))
        elements.append(Spacer(1, 4))

    if est_rows:
        elements.append(Paragraph("ESTUDIOS / PROCEDIMIENTOS", styles['SectionTitle']))
        est_style = ParagraphStyle('EstItem', parent=styles['Normal'], fontSize=8, leading=10, leftIndent=10)
        est_ind_style = ParagraphStyle('EstInd', parent=styles['Normal'], fontSize=7.5, leading=9.5, leftIndent=22, textColor=colors.HexColor('#555555'))
        for i, (nom, ind) in enumerate(est_rows, 1):
            elements.append(Paragraph(f"<b>{i}.</b> {_html.escape(nom)}", est_style))
            if ind:
                elements.append(Paragraph(f"<i>Indicaciones: {_html.escape(ind)}</i>", est_ind_style))
        elements.append(Spacer(1, 4))

    # ===== FIRMA Y SELLO DEL MÉDICO (al pie de la última página, misma hoja) =====
    medico_nombre = (medico.get("name") if medico else None) or evaluacion.get("medico_nombre", "") or ""
    colegiado = (medico.get("license_number") if medico else "") or ""
    especialidad = (medico.get("specialty") if medico else "") or ""

    firma_bytes = None
    firma_dims = None
    if medico and medico.get("firma_digital"):
        try:
            data = medico["firma_digital"]
            if "," in data:
                data = data.split(",", 1)[1]
            firma_bytes = _base64.b64decode(data)
            firma_dims = ImageReader(io.BytesIO(firma_bytes)).getSize()
        except Exception:
            firma_bytes = None
            firma_dims = None

    sig_info = {
        "nombre": medico_nombre,
        "colegiado": colegiado,
        "especialidad": especialidad,
        "img_bytes": firma_bytes,
        "img_dims": firma_dims,
    }

    class SignatureCanvas(_pdfcanvas.Canvas):
        """Dibuja la firma en la banda inferior reservada, solo en la última página."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_states = []

        def showPage(self):
            self._saved_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_states)
            for idx, state in enumerate(self._saved_states):
                self.__dict__.update(state)
                if idx == total - 1:
                    self._draw_signature()
                _pdfcanvas.Canvas.showPage(self)
            _pdfcanvas.Canvas.save(self)

        def _draw_signature(self):
            cx = letter[0] / 2.0
            line_w = 3.2 * inch
            line_y = 90
            if sig_info["img_bytes"] and sig_info["img_dims"]:
                iw, ih = sig_info["img_dims"]
                ratio = min((3 * cm) / iw, (2 * cm) / ih)
                w, h = iw * ratio, ih * ratio
                try:
                    self.drawImage(
                        ImageReader(io.BytesIO(sig_info["img_bytes"])),
                        cx - w / 2, line_y + 4, width=w, height=h, mask='auto'
                    )
                except Exception:
                    pass
            self.setStrokeColor(colors.black)
            self.setLineWidth(0.8)
            self.line(cx - line_w / 2, line_y, cx + line_w / 2, line_y)
            ty = line_y - 13
            if sig_info["nombre"]:
                self.setFont("Helvetica-Bold", 10)
                self.setFillColor(colors.black)
                self.drawCentredString(cx, ty, sig_info["nombre"])
                ty -= 12
            self.setFont("Helvetica", 9)
            self.setFillColor(colors.grey)
            self.drawCentredString(cx, ty, "Oftalmólogo")
            ty -= 11
            if sig_info["colegiado"]:
                self.drawCentredString(cx, ty, f"Colegiado No. {sig_info['colegiado']}")
            self.setFillColor(colors.black)

    # Garantizar que el reporte entre en 1 sola página: KeepInFrame encoge el
    # contenido proporcionalmente solo cuando excede el área disponible.
    avail_w = letter[0] - doc.leftMargin - doc.rightMargin
    avail_h = letter[1] - doc.topMargin - doc.bottomMargin
    story = [KeepInFrame(avail_w, avail_h, elements, mode='shrink', hAlign='LEFT', vAlign='TOP')]

    # Generar PDF (la firma se dibuja al pie de la última página)
    doc.build(story, canvasmaker=SignatureCanvas)
    buffer.seek(0)
    
    # Nombre del archivo
    paciente_nombre_safe = re.sub(r'[^\w\s-]', '', evaluacion.get("paciente_nombre", "paciente")).replace(" ", "_")
    filename = f"evaluacion_{paciente_nombre_safe}_{fecha_eval.replace('/', '-')}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("", response_model=EvaluacionOftalmologicaResponse)
async def create_evaluacion(
    evaluacion: EvaluacionOftalmologicaCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nueva evaluación (Admin, SuperAdmin, Usuario y Médico)"""
    if current_user["role"] not in ["superadmin", "admin", "usuario", "medico", "administrador_igss"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear evaluaciones")
    
    # Obtener datos del paciente si existe
    paciente = await db.patients.find_one({"id": evaluacion.paciente_id}, {"_id": 0})
    
    now = datetime.now(timezone.utc).isoformat()
    evaluacion_dict = evaluacion.model_dump()
    
    # Enriquecer con datos del paciente
    if paciente:
        evaluacion_dict["paciente_nombre"] = f"{paciente.get('first_name', '')} {paciente.get('last_name', '')}".strip()
        evaluacion_dict["paciente_expediente"] = paciente.get("record_number", "")
        evaluacion_dict["paciente_sexo"] = paciente.get("gender", "")
        if paciente.get("birth_date"):
            evaluacion_dict["paciente_edad"] = calcular_edad(paciente["birth_date"])
    
    evaluacion_dict["id"] = str(uuid.uuid4())
    evaluacion_dict["creado_por"] = current_user["id"]
    evaluacion_dict["creado_por_nombre"] = current_user.get("name", current_user.get("username", ""))
    evaluacion_dict["fecha_creacion"] = now
    evaluacion_dict["actualizado_por"] = current_user["id"]
    evaluacion_dict["actualizado_por_nombre"] = current_user.get("name", current_user.get("username", ""))
    evaluacion_dict["fecha_actualizacion"] = now
    evaluacion_dict["sellado"] = False
    evaluacion_dict["fecha_sellado"] = None
    evaluacion_dict["ultimo_autoguardado"] = now
    
    if not evaluacion_dict.get("fecha"):
        evaluacion_dict["fecha"] = today_str_gt()
    
    await db.evaluaciones_oftalmologicas.insert_one(evaluacion_dict)
    
    # Acreditar servicio al NOG del paciente (IGSS) si corresponde. Nunca bloquea la evaluación.
    try:
        from routes.igss_nogs import _acreditar_evaluacion
        await _acreditar_evaluacion(paciente, evaluacion_dict, current_user)
    except Exception:
        pass
    
    # Agendar próxima cita si corresponde (idempotente)
    await sincronizar_proxima_cita(
        evaluacion_dict["id"], evaluacion_dict.get("proxima_cita"),
        evaluacion_dict.get("paciente_id"), evaluacion_dict.get("paciente_nombre", ""), current_user
    )
    
    # Marcar al paciente como Atendido en la agenda del día de la evaluación
    await marcar_cita_atendida_por_evaluacion(
        evaluacion_dict.get("paciente_id"), evaluacion_dict.get("fecha"), current_user
    )
    
    # Procesar catálogos
    await procesar_catalogos_evaluacion(evaluacion_dict)
    
    # Audit log
    await audit.log(
        action="EVALUACION_CREATED",
        user_id=current_user["id"],
        user_name=current_user.get("username", "unknown"),
        details={"evaluacion_id": evaluacion_dict["id"], "paciente": evaluacion_dict.get("paciente_nombre")}
    )
    
    if "_id" in evaluacion_dict:
        del evaluacion_dict["_id"]
    return evaluacion_dict


async def sincronizar_proxima_cita(evaluacion_id: str, proxima_cita: dict, paciente_id: str,
                                   paciente_nombre: str, current_user: dict):
    """Crea/actualiza la próxima cita en la agenda de forma idempotente a partir de la
    sección 'Próxima Cita' de la evaluación. Funciona con guardado manual y autoguardado.
    Nunca lanza excepción que rompa el guardado de la evaluación."""
    try:
        pc = proxima_cita or {}
        if not pc.get("agendar"):
            return
        fecha = (pc.get("fecha") or "").strip()
        hora = (pc.get("hora") or "").strip()
        medico_id = (pc.get("medico_id") or "").strip()
        if not (fecha and hora and medico_id):
            return
        # No agendar en el pasado
        if fecha < today_str_gt():
            return
        try:
            hora_fin = (datetime.strptime(hora, "%H:%M") + timedelta(minutes=20)).strftime("%H:%M")
        except ValueError:
            return
        medico_nombre = pc.get("medico_nombre") or ""
        tipo_cita = pc.get("tipo_cita") or "Control"
        notas = pc.get("notas") or ""
        cita_id = pc.get("cita_id")

        estados_vivos = ["Cancelada", "No asistió"]
        existente = await db.citas.find_one({"id": cita_id}) if cita_id else None
        if existente:
            cambios = (existente.get("fecha") != fecha or existente.get("hora_inicio") != hora
                       or existente.get("medico_id") != medico_id or existente.get("tipo_cita") != tipo_cita
                       or (existente.get("notas") or "") != notas)
            if cambios and existente.get("estado") not in estados_vivos:
                await db.citas.update_one({"id": cita_id}, {"$set": {
                    "fecha": fecha, "hora_inicio": hora, "hora_fin": hora_fin,
                    "medico_id": medico_id, "medico_nombre": medico_nombre,
                    "asignado_a_medico_id": medico_id, "asignado_a_medico_nombre": medico_nombre,
                    "tipo_cita": tipo_cita, "notas": notas,
                    "fecha_actualizacion": datetime.now(timezone.utc).isoformat()
                }})
            return cita_id

        # Evitar duplicado para el mismo paciente/fecha/hora
        dup = await db.citas.find_one({
            "tipo_agenda": "pacientes", "paciente_id": paciente_id,
            "fecha": fecha, "hora_inicio": hora,
            "estado": {"$nin": estados_vivos}
        })
        if dup:
            nuevo_cita_id = dup["id"]
        else:
            now = datetime.now(timezone.utc).isoformat()
            cita_doc = {
                "id": str(uuid.uuid4()),
                "paciente_id": paciente_id, "paciente_nombre": paciente_nombre,
                "medico_id": medico_id, "medico_nombre": medico_nombre,
                "fecha": fecha, "hora_inicio": hora, "hora_fin": hora_fin,
                "duracion_minutos": 20, "tipo_cita": tipo_cita,
                "estado": "Agendada", "asistio": None,
                "hora_llegada": None, "hora_inicio_consulta": None, "hora_fin_consulta": None,
                "asignado_a_medico_id": medico_id, "asignado_a_medico_nombre": medico_nombre,
                "notas": notas, "tipo_agenda": "pacientes", "google_event_id": None,
                "evaluacion_origen_id": evaluacion_id,
                "creado_por": current_user["id"], "creado_por_nombre": current_user.get("name", ""),
                "fecha_creacion": now, "actualizado_por": None, "fecha_actualizacion": None
            }
            await db.citas.insert_one(cita_doc)
            nuevo_cita_id = cita_doc["id"]

        # Guardar la referencia de la cita en la evaluación (idempotencia)
        await db.evaluaciones_oftalmologicas.update_one(
            {"id": evaluacion_id}, {"$set": {"proxima_cita.cita_id": nuevo_cita_id}}
        )
        return nuevo_cita_id
    except Exception:
        return None


async def marcar_cita_atendida_por_evaluacion(paciente_id: str, fecha: str, current_user: dict):
    """Marca como 'Atendida' la cita del día del paciente (si está Presente/En consulta)
    cuando el médico guarda/completa su evaluación. No bloquea el guardado."""
    try:
        if not paciente_id:
            return
        fecha = (fecha or "")[:10]
        if len(fecha) != 10:
            fecha = today_str_gt()
        now = datetime.now(timezone.utc).isoformat()
        await db.citas.update_many(
            {
                "tipo_agenda": "pacientes",
                "paciente_id": paciente_id,
                "fecha": fecha,
                "estado": {"$in": ["Presente", "En consulta"]},
            },
            {"$set": {
                "estado": "Atendida",
                "asistio": True,
                "hora_fin_consulta": now,
                "actualizado_por": current_user["id"],
                "fecha_actualizacion": now,
            }},
        )
    except Exception:
        pass




# ==================== LIMPIEZA DE EVALUACIONES VACÍAS ====================

def _evaluacion_esta_vacia(ev: dict) -> bool:
    """Determina si una evaluación es un borrador vacío del autoguardado.
    NO considera vacías las selladas ni las importadas (por seguridad)."""
    if ev.get("sellado"):
        return False
    if ev.get("imported"):
        return False
    # Campos de texto libres
    for f in ["motivo_consulta", "padecimiento_actual", "plan", "lectura_examenes"]:
        if (ev.get(f) or "").strip():
            return False
    # Diagnósticos y procedimientos
    if ev.get("diagnosticos"):
        return False
    if ev.get("procedimientos"):
        return False
    # Examen: cualquier subcampo con valor
    examen = ev.get("examen") or {}
    for v in examen.values():
        if isinstance(v, dict):
            if any(str(x).strip() for x in v.values() if x is not None):
                return False
        elif v is not None and str(v).strip():
            return False
    # Recetas
    recetas = ev.get("recetas") or {}
    if (recetas.get("medicamentos") or {}).get("items"):
        return False
    if recetas.get("anteojos_lista"):
        return False
    if recetas.get("lentes_contacto_lista"):
        return False
    # Recomendaciones
    rec = ev.get("recomendaciones") or {}
    if (rec.get("recomendaciones_generales") or "").strip():
        return False
    if rec.get("estudios_a_realizar"):
        return False
    # Antecedentes (solo texto libre; los booleanos en false no cuentan)
    ant = ev.get("antecedentes") or {}
    for v in ant.values():
        if isinstance(v, str) and v.strip():
            return False
    return True


@router.get("/vacias/contar")
async def contar_evaluaciones_vacias(
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """Cuenta las evaluaciones vacías (borradores del autoguardado, no selladas ni importadas)."""
    total = 0
    cursor = db.evaluaciones_oftalmologicas.find(
        {"sellado": {"$ne": True}, "imported": {"$ne": True}}, {"_id": 0}
    )
    async for ev in cursor:
        if _evaluacion_esta_vacia(ev):
            total += 1
    return {"vacias": total}


@router.delete("/vacias/purgar")
async def purgar_evaluaciones_vacias(
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """Elimina de forma segura las evaluaciones vacías (no selladas ni importadas)."""
    ids = []
    cursor = db.evaluaciones_oftalmologicas.find(
        {"sellado": {"$ne": True}, "imported": {"$ne": True}}, {"_id": 0, "id": 1,
         "motivo_consulta": 1, "padecimiento_actual": 1, "plan": 1, "lectura_examenes": 1,
         "diagnosticos": 1, "procedimientos": 1, "examen": 1, "recetas": 1,
         "recomendaciones": 1, "antecedentes": 1, "sellado": 1, "imported": 1}
    )
    async for ev in cursor:
        if _evaluacion_esta_vacia(ev):
            ids.append(ev["id"])
    eliminadas = 0
    if ids:
        res = await db.evaluaciones_oftalmologicas.delete_many({"id": {"$in": ids}})
        eliminadas = res.deleted_count
    return {"eliminadas": eliminadas}



# ==================== IMPORTACIÓN MASIVA - ENDPOINTS ====================

@router.get("/import/template")
async def get_import_template_evaluaciones(
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """Devuelve la plantilla/esquema JSON esperado para importar evaluaciones."""
    return {
        "descripcion": "Plantilla para importación masiva de evaluaciones oftalmológicas NovaVision",
        "instrucciones": [
            "El archivo debe ser un array JSON de objetos (una evaluación por objeto).",
            "Cada evaluación DEBE incluir la clave de enlace al paciente: 'expediente' (igual al record_number del paciente) o 'dpi'.",
            "Importa los PACIENTES primero, preservando su expediente, para que el enlace funcione.",
            "Incluye 'id_origen' (PK de la evaluación en Access) para poder deduplicar reimportaciones.",
            "La fecha acepta YYYY-MM-DD, DD/MM/YYYY o DD-MM-YYYY.",
            "Las recetas de anteojos/lentes de contacto van como ARRAYS en 'anteojos_lista' y 'lentes_contacto_lista'.",
            "Recomendado importar en lotes de 500 registros."
        ],
        "diccionario_campos": {
            "_enlace_al_paciente": {
                "expediente": "Clave de enlace. DEBE ser igual al record_number del paciente. Alias: record_number, paciente_expediente.",
                "dpi": "Enlace alternativo si no hay expediente (13 dígitos).",
                "id_origen": "PK de la evaluación en Access. Se usa para deduplicar reimportaciones. Alias: source_id."
            },
            "_encabezado": {
                "fecha": "Fecha de la evaluación. Formatos: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY.",
                "medico_nombre": "Nombre del médico que atendió.",
                "motivo_consulta": "Motivo de la consulta (texto).",
                "padecimiento_actual": "Historia de la enfermedad actual (texto)."
            },
            "antecedentes": {
                "personales_patologicos": "Texto.",
                "diabetes": "true/false", "hipertension": "true/false", "cardiopatia": "true/false",
                "enfermedad_tiroidea": "true/false", "otros_patologicos": "true/false",
                "oftalmologicos": "Texto.", "quirurgicos": "Texto.", "alergias": "Texto.",
                "familiares": "Texto.", "habitos": "Texto."
            },
            "medicamentos_actuales": "Array de objetos: {nombre, dosis, frecuencia, via, desde}.",
            "medicamentos_previos": "Array de objetos: {nombre, dosis, motivo, periodo}.",
            "examen": {
                "avsc_od / avsc_os": "Agudeza visual SIN corrección OD/OS (ej. '20/40').",
                "avcc_od / avcc_os": "Agudeza visual CON corrección OD/OS.",
                "refraccion_od / refraccion_os": "Objeto {esfera, cilindro, eje, adicion}.",
                "queratometria_od / queratometria_os": "Texto.",
                "pio_od / pio_os": "Presión intraocular OD/OS. pio_metodo: método de medición.",
                "segmento_anterior": "Hallazgos del segmento anterior (texto).",
                "segmento_posterior": "Hallazgos del segmento posterior / fondo de ojo (texto).",
                "motilidad_ocular": "Texto.", "pupilas_reflejos": "Texto."
            },
            "diagnosticos": "Array de objetos: {descripcion, codigo_cie10, ojo} (ojo: OD/OS/OU).",
            "plan": "Plan de tratamiento (texto).",
            "recomendaciones": {
                "estudios_a_realizar": "Array de objetos: {estudio, ojo, indicaciones}.",
                "recomendaciones_generales": "Texto."
            },
            "procedimientos": "Array de objetos: {categoria (Clínico/Quirúrgico), tipo_nombre, ojo, fecha, descripcion, resultado_notas}.",
            "recetas": {
                "medicamentos": "Objeto {items: [{medicamento, presentacion, dosis, frecuencia, duracion, via, indicaciones}]}.",
                "anteojos_lista": "ARRAY de recetas de anteojos: [{od:{esfera,cilindro,eje,adicion}, os:{...}, tipo_lente, material, tratamientos, uso, distancia_pupilar, observaciones}].",
                "lentes_contacto_lista": "ARRAY de recetas de lentes de contacto: [{od:{poder,curva_base,diametro}, os:{...}, marca, tipo, regimen_reemplazo, adicion, observaciones}]."
            },
            "_notas": [
                "NO envíes 'paciente_id', 'id' ni 'paciente_nombre': el sistema los rellena al enlazar por expediente/dpi.",
                "Cualquier campo adicional que envíes se guarda tal cual (esquema flexible).",
                "Campos que no tengas: simplemente omítelos (todos tienen valor por defecto)."
            ]
        },
        "ejemplo": [
            {
                "id_origen": "ACCESS-EVAL-000123",
                "expediente": "EXP-202401-0001",
                "fecha": "2024-03-15",
                "medico_nombre": "Dr. Juan Pérez",
                "motivo_consulta": "Control anual",
                "padecimiento_actual": "",
                "antecedentes": {"diabetes": False, "hipertension": False, "alergias": ""},
                "examen": {
                    "avsc_od": "20/40", "avsc_os": "20/30",
                    "avcc_od": "20/20", "avcc_os": "20/20",
                    "refraccion_od": {"esfera": "-1.00", "cilindro": "-0.50", "eje": "180", "adicion": ""},
                    "refraccion_os": {"esfera": "-0.75", "cilindro": "", "eje": "", "adicion": ""},
                    "pio_od": "14", "pio_os": "15",
                    "segmento_anterior": "Sin alteraciones",
                    "segmento_posterior": "Papila y mácula normales"
                },
                "diagnosticos": [{"descripcion": "Miopía simple", "codigo_cie10": "H52.1", "ojo": "OU"}],
                "plan": "Uso de anteojos permanente",
                "recetas": {
                    "anteojos_lista": [{
                        "od": {"esfera": "-1.00", "cilindro": "-0.50", "eje": "180", "adicion": ""},
                        "os": {"esfera": "-0.75", "cilindro": "", "eje": "", "adicion": ""},
                        "tipo_lente": "Monofocal", "material": "", "tratamientos": "Antirreflejo",
                        "uso": "Permanente", "distancia_pupilar": "62", "observaciones": ""
                    }],
                    "lentes_contacto_lista": []
                }
            }
        ]
    }


@router.post("/import/validate")
async def validate_import_evaluaciones(
    items: List[ImportEvaluacionItem] = Body(...),
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """Valida (dry-run) cuántas evaluaciones enlazan con un paciente existente."""
    dumped = [it.model_dump() for it in items]
    exps, dpis = set(), set()
    for d in dumped:
        e = _get_expediente(d)
        if e:
            exps.add(e)
        elif d.get("dpi"):
            dpis.add(str(d["dpi"]).strip())
    mapa_exp, mapa_dpi = await _mapear_pacientes(exps, dpis)

    linkable = 0
    sin_clave = 0
    huerfanas = []
    sample = []
    for idx, d in enumerate(dumped):
        e = _get_expediente(d)
        dpi = str(d.get("dpi") or "").strip()
        if not e and not dpi:
            sin_clave += 1
            continue
        pac = mapa_exp.get(e) if e else None
        if not pac and dpi:
            pac = mapa_dpi.get(dpi)
        if not pac:
            if len(huerfanas) < 50:
                huerfanas.append({"row": idx + 1, "clave": e or dpi})
            continue
        linkable += 1
        if len(sample) < 5:
            sample.append({
                "row": idx + 1,
                "clave": e or dpi,
                "paciente": f"{pac.get('first_name', '')} {pac.get('last_name', '')}".strip(),
                "fecha": _norm_fecha_eval(d.get("fecha"))
            })
    total = len(dumped)
    return {
        "valid": linkable > 0 and sin_clave == 0,
        "total_records": total,
        "linkable_records": linkable,
        "sin_clave_enlace": sin_clave,
        "huerfanas_count": total - linkable - sin_clave,
        "huerfanas": huerfanas,
        "sample": sample
    }


@router.post("/import/batch")
async def import_evaluaciones_batch(
    request: ImportEvalBatchRequest,
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """Importa un lote de evaluaciones enlazándolas al paciente por expediente/DPI."""
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    huerfanas = 0
    sin_clave = 0
    duplicados = 0
    error_details = []
    huerfana_details = []

    dumped = [it.model_dump() for it in request.items]
    exps, dpis, source_ids = set(), set(), set()
    for d in dumped:
        e = _get_expediente(d)
        if e:
            exps.add(e)
        elif d.get("dpi"):
            dpis.add(str(d["dpi"]).strip())
        sid = d.get("id_origen") or d.get("source_id")
        if sid:
            source_ids.add(str(sid))

    mapa_exp, mapa_dpi = await _mapear_pacientes(exps, dpis)

    existentes_sid = set()
    if request.skip_duplicates and source_ids:
        cursor = db.evaluaciones_oftalmologicas.find(
            {"import_source_id": {"$in": list(source_ids)}},
            {"_id": 0, "import_source_id": 1}
        )
        async for ev in cursor:
            if ev.get("import_source_id"):
                existentes_sid.add(ev["import_source_id"])

    docs = []
    for idx, d in enumerate(dumped):
        e = _get_expediente(d)
        dpi = str(d.get("dpi") or "").strip()
        if not e and not dpi:
            sin_clave += 1
            error_details.append({"row": idx + 1, "error": "Sin clave de enlace (expediente/dpi)"})
            continue
        pac = mapa_exp.get(e) if e else None
        if not pac and dpi:
            pac = mapa_dpi.get(dpi)
        if not pac:
            huerfanas += 1
            if len(huerfana_details) < 20:
                huerfana_details.append({"row": idx + 1, "clave": e or dpi})
            continue

        sid = str(d.get("id_origen") or d.get("source_id") or "")
        if request.skip_duplicates and sid and sid in existentes_sid:
            duplicados += 1
            continue

        # Documento clínico: quitar claves meta de enlace, conservar el resto
        clinico = {k: v for k, v in d.items() if k not in _EVAL_LINK_KEYS and v is not None}

        # Enriquecer con datos del paciente
        clinico["id"] = str(uuid.uuid4())
        clinico["paciente_id"] = pac["id"]
        clinico["paciente_nombre"] = f"{pac.get('first_name', '')} {pac.get('last_name', '')}".strip()
        clinico["paciente_expediente"] = pac.get("record_number", "")
        clinico["paciente_sexo"] = pac.get("gender", "")
        if pac.get("birth_date"):
            clinico["paciente_edad"] = calcular_edad(pac["birth_date"])
        else:
            clinico.setdefault("paciente_edad", 0)

        clinico["fecha"] = _norm_fecha_eval(clinico.get("fecha")) or now[:10]

        # Asegurar estructura de recetas con arrays (formato actual)
        recetas = clinico.get("recetas")
        if not isinstance(recetas, dict):
            recetas = {}
        recetas.setdefault("anteojos_lista", [])
        recetas.setdefault("lentes_contacto_lista", [])
        clinico["recetas"] = recetas
        clinico.setdefault("diagnosticos", [])

        # Metadatos
        clinico["creado_por"] = current_user["id"]
        clinico["creado_por_nombre"] = current_user.get("name", current_user.get("username", ""))
        clinico["fecha_creacion"] = clinico.get("fecha_creacion") or now
        clinico["actualizado_por"] = current_user["id"]
        clinico["actualizado_por_nombre"] = current_user.get("name", current_user.get("username", ""))
        clinico["fecha_actualizacion"] = now
        clinico["sellado"] = False
        clinico["fecha_sellado"] = None
        clinico["ultimo_autoguardado"] = now
        clinico["imported"] = True
        clinico["import_batch"] = request.batch_number
        if sid:
            clinico["import_source_id"] = sid
            existentes_sid.add(sid)

        docs.append(clinico)

    if docs:
        try:
            res = await db.evaluaciones_oftalmologicas.insert_many(docs, ordered=False)
            inserted = len(res.inserted_ids)
        except Exception as ex:
            error_str = str(ex)
            if "duplicate key" in error_str.lower():
                inserted = len(docs) - 1
            else:
                raise HTTPException(status_code=500, detail=f"Error de base de datos: {error_str}")

    return {
        "success": True,
        "batch_number": request.batch_number,
        "total_processed": len(request.items),
        "inserted": inserted,
        "orphaned": huerfanas,
        "sin_clave": sin_clave,
        "duplicates": duplicados,
        "error_details": error_details[:20],
        "orphaned_details": huerfana_details
    }


@router.post("/admin/relink-por-expediente")
async def relink_evaluaciones_por_expediente(
    current_user: dict = Depends(require_role("superadmin"))
):
    """Mantenimiento: re-vincula cada evaluación a su paciente usando el
    número de expediente (paciente_expediente == patients.record_number).
    Corrige evaluaciones cuyo paciente_id quedó apuntando a un id inexistente."""
    from pymongo import UpdateOne

    # Mapa record_number -> datos del paciente
    mapa = {}
    cursor = db.patients.find(
        {"record_number": {"$ne": None}},
        {"_id": 0, "id": 1, "record_number": 1, "first_name": 1,
         "last_name": 1, "gender": 1, "birth_date": 1}
    )
    async for p in cursor:
        rn = str(p.get("record_number"))
        mapa[rn] = p

    actualizadas = 0
    sin_cambio = 0
    sin_expediente = 0
    no_enlazables = 0
    ops = []

    ev_cursor = db.evaluaciones_oftalmologicas.find(
        {}, {"_id": 0, "id": 1, "paciente_id": 1, "paciente_expediente": 1}
    )
    async for ev in ev_cursor:
        exp = str(ev.get("paciente_expediente") or "").strip()
        if not exp:
            sin_expediente += 1
            continue
        pac = mapa.get(exp)
        if not pac:
            no_enlazables += 1
            continue
        if ev.get("paciente_id") == pac["id"]:
            sin_cambio += 1
            continue
        set_doc = {
            "paciente_id": pac["id"],
            "paciente_nombre": f"{pac.get('first_name', '')} {pac.get('last_name', '')}".strip(),
            "paciente_sexo": pac.get("gender", ""),
        }
        if pac.get("birth_date"):
            set_doc["paciente_edad"] = calcular_edad(pac["birth_date"])
        ops.append(UpdateOne({"id": ev["id"]}, {"$set": set_doc}))
        if len(ops) >= 1000:
            res = await db.evaluaciones_oftalmologicas.bulk_write(ops, ordered=False)
            actualizadas += res.modified_count
            ops = []
    if ops:
        res = await db.evaluaciones_oftalmologicas.bulk_write(ops, ordered=False)
        actualizadas += res.modified_count

    return {
        "actualizadas": actualizadas,
        "sin_cambio": sin_cambio,
        "sin_expediente": sin_expediente,
        "no_enlazables": no_enlazables,
        "pacientes_en_mapa": len(mapa),
    }



@router.put("/{evaluacion_id}", response_model=EvaluacionOftalmologicaResponse)
async def update_evaluacion(
    evaluacion_id: str,
    evaluacion: EvaluacionOftalmologicaUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar evaluación (Admin, SuperAdmin, Usuario y Médico; el médico solo las suyas; solo si no está sellada)"""
    if current_user["role"] not in ["superadmin", "admin", "usuario", "medico", "administrador_igss"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para editar evaluaciones")
    
    existing = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # El médico solo puede editar las evaluaciones que él mismo creó
    if current_user["role"] == "medico" and existing.get("creado_por") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Solo puede editar las evaluaciones que usted creó")
    
    # Verificar sellado
    debe_sellar, mensaje = verificar_sellado(existing)
    if debe_sellar:
        if not existing.get("sellado"):
            await db.evaluaciones_oftalmologicas.update_one(
                {"id": evaluacion_id},
                {"$set": {"sellado": True, "fecha_sellado": datetime.now(timezone.utc).isoformat()}}
            )
        raise HTTPException(status_code=423, detail=f"Expediente sellado. {mensaje}")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = evaluacion.model_dump(exclude_unset=True)
    
    # Si se actualiza paciente_id, enriquecer datos
    if "paciente_id" in update_data:
        paciente = await db.patients.find_one({"id": update_data["paciente_id"]}, {"_id": 0})
        if paciente:
            update_data["paciente_nombre"] = f"{paciente.get('first_name', '')} {paciente.get('last_name', '')}".strip()
            update_data["paciente_expediente"] = paciente.get("record_number", "")
            update_data["paciente_sexo"] = paciente.get("gender", "")
            if paciente.get("birth_date"):
                update_data["paciente_edad"] = calcular_edad(paciente["birth_date"])
    
    update_data["actualizado_por"] = current_user["id"]
    update_data["actualizado_por_nombre"] = current_user.get("name", current_user.get("username", ""))
    update_data["fecha_actualizacion"] = now
    
    await db.evaluaciones_oftalmologicas.update_one(
        {"id": evaluacion_id},
        {"$set": update_data}
    )
    
    # Procesar catálogos con datos actualizados
    merged_data = {**existing, **update_data}
    await procesar_catalogos_evaluacion(merged_data)
    
    # Agendar/actualizar próxima cita si corresponde (idempotente)
    await sincronizar_proxima_cita(
        evaluacion_id, merged_data.get("proxima_cita"),
        merged_data.get("paciente_id"), merged_data.get("paciente_nombre", ""), current_user
    )
    
    # Marcar al paciente como Atendido en la agenda del día de la evaluación
    await marcar_cita_atendida_por_evaluacion(
        merged_data.get("paciente_id"), merged_data.get("fecha"), current_user
    )
    
    updated = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    return updated


@router.patch("/{evaluacion_id}/autoguardar", response_model=EvaluacionOftalmologicaResponse)
async def autoguardar_evaluacion(
    evaluacion_id: str,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Autoguardado parcial de evaluación (solo si no está sellada)"""
    if current_user["role"] not in ["superadmin", "admin", "usuario", "medico", "administrador_igss"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para editar evaluaciones")
    
    existing = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # El médico solo puede editar (autoguardar) las evaluaciones que él mismo creó
    if current_user["role"] == "medico" and existing.get("creado_por") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Solo puede editar las evaluaciones que usted creó")
    
    # Verificar sellado
    debe_sellar, mensaje = verificar_sellado(existing)
    if debe_sellar:
        if not existing.get("sellado"):
            await db.evaluaciones_oftalmologicas.update_one(
                {"id": evaluacion_id},
                {"$set": {"sellado": True, "fecha_sellado": datetime.now(timezone.utc).isoformat()}}
            )
        raise HTTPException(status_code=423, detail=f"Expediente sellado. {mensaje}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Filtrar campos permitidos
    allowed_fields = [
        "paciente_id", "paciente_nombre", "paciente_edad", "paciente_sexo", "paciente_expediente",
        "fecha", "medico_id", "medico_nombre", "motivo_consulta", "padecimiento_actual",
        "antecedentes", "medicamentos_actuales", "medicamentos_previos", "examen",
        "diagnosticos", "plan", "recomendaciones", "procedimientos", "recetas", "igss_med_proc",
        "proxima_cita",
        "igss_orden_id", "igss_nog", "igss_no_sps", "igss_codigo", "igss_procedimiento"
    ]
    
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    # Normalizar sección IGSS (medicamentos {nombre, frecuencia} + estudios)
    if "igss_med_proc" in update_data:
        update_data["igss_med_proc"] = MedicamentosProcedimientosIGSS(
            **(update_data["igss_med_proc"] or {})
        ).model_dump()
    # Preservar cita_id ya existente en proxima_cita (el frontend podría no enviarlo)
    if "proxima_cita" in update_data and isinstance(update_data["proxima_cita"], dict):
        if not update_data["proxima_cita"].get("cita_id"):
            prev_cid = (existing.get("proxima_cita") or {}).get("cita_id")
            if prev_cid:
                update_data["proxima_cita"]["cita_id"] = prev_cid
    update_data["actualizado_por"] = current_user["id"]
    update_data["actualizado_por_nombre"] = current_user.get("name", current_user.get("username", ""))
    update_data["fecha_actualizacion"] = now
    update_data["ultimo_autoguardado"] = now
    
    await db.evaluaciones_oftalmologicas.update_one(
        {"id": evaluacion_id},
        {"$set": update_data}
    )
    
    # Procesar catálogos
    merged_data = {**existing, **update_data}
    await procesar_catalogos_evaluacion(merged_data)
    
    # Agendar/actualizar próxima cita si corresponde (idempotente), también en autoguardado
    await sincronizar_proxima_cita(
        evaluacion_id, merged_data.get("proxima_cita"),
        merged_data.get("paciente_id"), merged_data.get("paciente_nombre", ""), current_user
    )
    
    updated = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    return updated


@router.delete("/{evaluacion_id}")
async def delete_evaluacion(
    evaluacion_id: str,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Eliminar evaluación (solo SuperAdmin, solo si no está sellada)"""
    existing = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # Verificar sellado
    debe_sellar, mensaje = verificar_sellado(existing)
    if debe_sellar:
        raise HTTPException(status_code=423, detail=f"Expediente sellado. No se puede eliminar. {mensaje}")
    
    await db.evaluaciones_oftalmologicas.delete_one({"id": evaluacion_id})
    
    await audit.log(
        action="EVALUACION_DELETED",
        user_id=current_user["id"],
        user_name=current_user.get("username", "unknown"),
        details={"evaluacion_id": evaluacion_id, "paciente": existing.get("paciente_nombre")}
    )
    
    return {"message": "Evaluación eliminada"}


# ==================== ANTECEDENTES Y MEDICAMENTOS DEL PACIENTE ====================

@router.get("/paciente/{paciente_id}/historial-medico")
async def get_historial_medico_paciente(
    paciente_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtener antecedentes y medicamentos actuales del paciente.
    Estos datos persisten entre evaluaciones.
    """
    # Buscar en la colección de historial médico del paciente
    historial = await db.pacientes_historial_medico.find_one(
        {"paciente_id": paciente_id}, 
        {"_id": 0}
    )
    
    if not historial:
        # Intentar obtener de la última evaluación del paciente
        ultima_evaluacion = await db.evaluaciones_oftalmologicas.find_one(
            {"paciente_id": paciente_id},
            {"_id": 0, "antecedentes": 1, "medicamentos_actuales": 1, "medicamentos_previos": 1}
        )
        
        if ultima_evaluacion:
            return {
                "paciente_id": paciente_id,
                "antecedentes": ultima_evaluacion.get("antecedentes", {}),
                "medicamentos_actuales": ultima_evaluacion.get("medicamentos_actuales", []),
                "medicamentos_previos": ultima_evaluacion.get("medicamentos_previos", []),
                "fuente": "ultima_evaluacion"
            }
        
        # Retornar vacío si no hay historial
        return {
            "paciente_id": paciente_id,
            "antecedentes": {
                "personales_patologicos": "",
                "oftalmologicos": "",
                "quirurgicos": "",
                "alergias": "",
                "familiares": "",
                "habitos": ""
            },
            "medicamentos_actuales": [],
            "medicamentos_previos": [],
            "fuente": "nuevo"
        }
    
    return {
        **historial,
        "fuente": "historial_guardado"
    }


@router.put("/paciente/{paciente_id}/historial-medico")
async def update_historial_medico_paciente(
    paciente_id: str,
    antecedentes: dict = Body(None),
    medicamentos_actuales: list = Body(None),
    medicamentos_previos: list = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Actualizar antecedentes y medicamentos del paciente.
    Estos datos persisten entre evaluaciones.
    """
    if current_user["role"] not in ["superadmin", "admin", "usuario", "medico", "administrador_igss"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para actualizar historial médico")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "paciente_id": paciente_id,
        "updated_at": now,
        "updated_by": current_user["id"],
        "updated_by_name": current_user.get("name", "")
    }
    
    if antecedentes is not None:
        update_data["antecedentes"] = antecedentes
    
    if medicamentos_actuales is not None:
        update_data["medicamentos_actuales"] = medicamentos_actuales
    
    if medicamentos_previos is not None:
        update_data["medicamentos_previos"] = medicamentos_previos
    
    # Upsert - crear si no existe, actualizar si existe
    await db.pacientes_historial_medico.update_one(
        {"paciente_id": paciente_id},
        {"$set": update_data, "$setOnInsert": {"created_at": now}},
        upsert=True
    )
    
    historial = await db.pacientes_historial_medico.find_one(
        {"paciente_id": paciente_id}, 
        {"_id": 0}
    )
    
    return historial


@router.post("/paciente/{paciente_id}/agregar-medicamento-receta")
async def agregar_medicamento_desde_receta(
    paciente_id: str,
    medicamento: str = Body(...),
    dosis: str = Body(""),
    frecuencia: str = Body(""),
    via: str = Body(""),
    current_user: dict = Depends(get_current_user)
):
    """
    Agregar un medicamento de receta a los medicamentos actuales del paciente.
    Se llama automáticamente cuando se guarda una receta con medicamentos.
    """
    if current_user["role"] not in ["superadmin", "admin", "usuario", "medico", "administrador_igss"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Obtener historial actual
    historial = await db.pacientes_historial_medico.find_one(
        {"paciente_id": paciente_id}, 
        {"_id": 0}
    )
    
    medicamentos_actuales = historial.get("medicamentos_actuales", []) if historial else []
    
    # Verificar si el medicamento ya existe
    existe = any(m.get("nombre", "").lower() == medicamento.lower() for m in medicamentos_actuales)
    
    if not existe:
        nuevo_medicamento = {
            "nombre": medicamento,
            "dosis": dosis,
            "frecuencia": frecuencia,
            "via": via,
            "desde": now[:10],  # Solo fecha
            "origen": "receta"
        }
        medicamentos_actuales.append(nuevo_medicamento)
        
        await db.pacientes_historial_medico.update_one(
            {"paciente_id": paciente_id},
            {
                "$set": {
                    "medicamentos_actuales": medicamentos_actuales,
                    "updated_at": now,
                    "updated_by": current_user["id"]
                },
                "$setOnInsert": {"created_at": now, "antecedentes": {}}
            },
            upsert=True
        )
    
    return {"message": "Medicamento agregado", "medicamento": medicamento}


# ==================== CRM CIRUGÍAS DESDE EVALUACIÓN ====================

@router.post("/{evaluacion_id}/agregar-crm-cirugia")
async def agregar_a_crm_cirugia(
    evaluacion_id: str,
    tipo_cirugia: str = Body(...),
    ojo: str = Body("OU"),
    diagnostico: str = Body(""),
    prioridad: str = Body("normal"),
    nivel_interes: str = Body("interesado"),
    notas: str = Body(""),
    current_user: dict = Depends(get_current_user)
):
    """
    Agregar paciente al CRM de cirugías desde una evaluación oftalmológica.
    """
    if current_user["role"] not in ["superadmin", "admin", "usuario", "medico", "administrador_igss"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    # Obtener evaluación
    evaluacion = await db.evaluaciones_oftalmologicas.find_one(
        {"id": evaluacion_id}, 
        {"_id": 0}
    )
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    paciente_id = evaluacion.get("paciente_id")
    
    # Verificar si ya existe en CRM para este tipo de cirugía
    existing = await db.surgery_crm.find_one({
        "paciente_id": paciente_id,
        "tipo_cirugia": tipo_cirugia,
        "estado": {"$nin": ["operado", "descartado"]}
    })
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"El paciente ya está registrado en CRM para {tipo_cirugia}"
        )
    
    # Obtener datos del paciente
    paciente = await db.patients.find_one({"id": paciente_id}, {"_id": 0})
    
    now = datetime.now(timezone.utc).isoformat()
    
    crm_entry = {
        "id": str(uuid.uuid4()),
        "paciente_id": paciente_id,
        "paciente_nombre": evaluacion.get("paciente_nombre", ""),
        "paciente_telefono": paciente.get("phone", "") if paciente else "",
        "paciente_email": paciente.get("email", "") if paciente else "",
        "tipo_cirugia": tipo_cirugia,
        "ojo": ojo,
        "diagnostico": diagnostico or ", ".join([d.get("descripcion", "") for d in evaluacion.get("diagnosticos", [])]),
        "prioridad": prioridad,
        "nivel_interes": nivel_interes,
        "notas": notas,
        "origen": "evaluacion",
        "evaluacion_id": evaluacion_id,
        "estado": "pendiente",
        "seguimientos": [],
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.surgery_crm.insert_one(crm_entry)
    
    # Limpiar _id para la respuesta
    if "_id" in crm_entry:
        del crm_entry["_id"]
    
    return {
        "message": "Paciente agregado al CRM de cirugías",
        "crm_id": crm_entry["id"],
        "tipo_cirugia": tipo_cirugia
    }

