# /app/backend/routes/agenda.py
# Rutas del módulo de Agenda de Pacientes
# IMPORTANTE: Esta agenda es INDEPENDIENTE de la agenda de Sala de Operaciones

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from utils.timezone import now_gt, today_str_gt
import uuid

from models.agenda import (
    CitaCreate, CitaUpdate, CitaResponse, CitaListResponse,
    CitaEstadoUpdate, CitaAsignarUpdate,
    AgendaConfigUpdate, AgendaConfigResponse, TipoCitaConfig,
    PresentesResponse, PresentesPorMedicoResponse, PacientePresenteResponse,
    ContadoresDiaResponse, MiAgendaResponse, WalkInCreate, ProximaCitaCreate,
    EstadoCita, TipoCita,
    BloqueoAgendaCreate, BloqueoAgendaResponse, BloqueoCreateResult,
    BloqueoListResponse, CitaExternaCreate, DisponibilidadResponse
)
from config.database import db
from routes.auth import get_current_user, require_permission, require_role
import os
from fastapi import Header

# Routers
router = APIRouter(prefix="/agenda", tags=["Agenda"])
medicos_agenda_router = APIRouter(prefix="/medicos-agenda", tags=["Médicos Agenda"])
config_router = APIRouter(prefix="/agenda/configuracion", tags=["Configuración Agenda"])
# Router para agente externo (n8n/Claude) autenticado con clave fija (X-API-Key)
external_router = APIRouter(prefix="/agenda/external", tags=["Agenda - Agente Externo"])


async def verificar_clave_api_externa(x_api_key: str = Header(None)):
    """Valida la clave fija de API para el agente externo."""
    clave = os.environ.get("AGENDA_API_KEY")
    if not clave:
        raise HTTPException(status_code=503, detail="API externa de agenda no configurada")
    if not x_api_key or x_api_key != clave:
        raise HTTPException(status_code=401, detail="Clave de API inválida o faltante")
    return True

# Variable para WebSocket manager (se inyecta desde server.py)
ws_manager = None

def init_agenda_routes(websocket_manager=None):
    """Inicializa el WebSocket manager para agenda"""
    global ws_manager
    ws_manager = websocket_manager


async def notify_agenda_update(event_type: str, data: dict, exclude_ws=None):
    """Notifica a todos los clientes conectados al canal de agenda"""
    if ws_manager:
        try:
            await ws_manager.broadcast("agenda", {
                "type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, exclude=exclude_ws)
        except Exception as e:
            print(f"Error notificando WebSocket agenda: {e}")


# ==================== HELPERS ====================

async def get_medico_vinculado(user_id: str):
    """Obtiene el médico vinculado al usuario (si existe)"""
    medico = await db.doctors.find_one({"usuario_id": user_id, "is_active": True}, {"_id": 0})
    return medico

async def es_medico_o_admin(current_user: dict):
    """Verifica si el usuario es médico vinculado o admin"""
    if current_user["role"] in ["superadmin", "admin"]:
        return True, None
    medico = await get_medico_vinculado(current_user["id"])
    return medico is not None, medico

async def calcular_tiempo_espera(hora_llegada: str) -> int:
    """Calcula minutos de espera desde hora de llegada"""
    try:
        llegada = datetime.fromisoformat(hora_llegada.replace('Z', '+00:00'))
        ahora = datetime.now(timezone.utc)
        return int((ahora - llegada).total_seconds() / 60)
    except (ValueError, TypeError):
        return 0

async def get_agenda_config():
    """Obtiene la configuración de agenda o crea una por defecto"""
    config = await db.agenda_config.find_one({"tipo": "pacientes"}, {"_id": 0})
    if not config:
        # Crear configuración por defecto
        tipos_cita_default = [
            {"id": "primera_vez", "nombre": "Primera vez", "duracion_minutos": 30, "color": "#0F6E56", "activo": True},
            {"id": "subsecuente", "nombre": "Subsecuente", "duracion_minutos": 20, "color": "#38B2AC", "activo": True},
            {"id": "control_post", "nombre": "Control post-operatorio", "duracion_minutos": 20, "color": "#805AD5", "activo": True},
            {"id": "estudio", "nombre": "Estudio", "duracion_minutos": 30, "color": "#DD6B20", "activo": True},
            {"id": "otro", "nombre": "Otro", "duracion_minutos": 15, "color": "#718096", "activo": True}
        ]
        config = {
            "id": str(uuid.uuid4()),
            "tipo": "pacientes",
            "hora_apertura": "07:00",
            "hora_cierre": "18:00",
            "duracion_slot_minutos": 15,
            "dias_laborables": [1, 2, 3, 4, 5, 6],
            "tipos_cita": tipos_cita_default,
            "permitir_overbooking": True,
            "max_citas_por_slot": 3,
            "fecha_creacion": datetime.now(timezone.utc).isoformat()
        }
        await db.agenda_config.insert_one(config)
        if "_id" in config:
            del config["_id"]
    return config

# ==================== HELPERS DE BLOQUEOS ====================

async def verificar_bloqueo(medico_id: str, fecha: str, hora_inicio: Optional[str] = None, hora_fin: Optional[str] = None):
    """Devuelve el bloqueo que impide agendar en ese espacio, o None si está libre.

    - Bloqueos de clínica: aplican a todos los médicos en el rango de fechas (día completo).
    - Bloqueos de médico: día completo o franja de horas con solape.
    Las fechas (YYYY-MM-DD) y horas (HH:MM) se comparan lexicográficamente.
    """
    # 1) Bloqueo de clínica que cubra la fecha
    clinica = await db.bloqueos_agenda.find_one({
        "tipo": "clinica",
        "fecha_inicio": {"$lte": fecha},
        "fecha_fin": {"$gte": fecha}
    }, {"_id": 0})
    if clinica:
        return clinica

    # 2) Bloqueos del médico que cubran la fecha
    cursor = db.bloqueos_agenda.find({
        "tipo": "medico",
        "medico_id": medico_id,
        "fecha_inicio": {"$lte": fecha},
        "fecha_fin": {"$gte": fecha}
    }, {"_id": 0})
    async for b in cursor:
        if b.get("dia_completo"):
            return b
        b_ini, b_fin = b.get("hora_inicio"), b.get("hora_fin")
        if hora_inicio and hora_fin and b_ini and b_fin:
            # Solape de franjas: inicio < fin_bloqueo y fin > inicio_bloqueo
            if hora_inicio < b_fin and hora_fin > b_ini:
                return b
        else:
            # Sin información de horas suficiente: se considera bloqueado ese día
            return b
    return None


async def verificar_horario_medico(medico_id: str, fecha: str, hora_inicio: Optional[str] = None, hora_fin: Optional[str] = None):
    """Devuelve un motivo (str) si la cita queda FUERA del horario laboral del médico, o None.

    El horario se define por día de semana en el documento del médico
    (`horario_semanal`, claves "1"=Lunes.."7"=Domingo). Si el médico no tiene
    horario configurado, no se restringe (compatibilidad con datos existentes).
    """
    medico = await db.doctors.find_one({"id": medico_id}, {"_id": 0, "horario_semanal": 1})
    if not medico:
        return None
    horario = medico.get("horario_semanal")
    if not horario:
        return None
    # Si ningún día está marcado como activo, el médico no tiene restricción de horario
    if not any((v or {}).get("activo") for v in horario.values()):
        return None
    try:
        dia = str(datetime.strptime(fecha, "%Y-%m-%d").isoweekday())  # 1=Lun .. 7=Dom
    except ValueError:
        return None
    cfg = horario.get(dia)
    if not cfg or not cfg.get("activo"):
        return "El médico no atiende ese día"
    h_ini = cfg.get("hora_inicio")
    h_fin = cfg.get("hora_fin")
    if h_ini and h_fin and hora_inicio and hora_fin:
        if hora_inicio < h_ini or hora_fin > h_fin:
            return f"Fuera del horario del médico ({h_ini}–{h_fin})"
    return None


async def motivo_no_disponible(medico_id: str, fecha: str, hora_inicio: Optional[str] = None, hora_fin: Optional[str] = None):
    """Combina bloqueos y horario del médico. Devuelve (motivo, bloqueo) o (None, None)."""
    bloqueo = await verificar_bloqueo(medico_id, fecha, hora_inicio, hora_fin)
    if bloqueo:
        motivo = bloqueo.get("motivo") or ("Feriado/Vacaciones" if bloqueo["tipo"] == "clinica" else "Horario bloqueado")
        return motivo, bloqueo
    motivo_h = await verificar_horario_medico(medico_id, fecha, hora_inicio, hora_fin)
    if motivo_h:
        return motivo_h, None
    return None, None


async def listar_citas_conflicto(bloqueo: dict):
    """Lista las citas activas que caen dentro de un bloqueo (para reprogramación manual)."""
    query = {
        "tipo_agenda": "pacientes",
        "estado": {"$nin": [EstadoCita.ATENDIDA.value, EstadoCita.NO_ASISTIO.value, EstadoCita.CANCELADA.value]},
        "fecha": {"$gte": bloqueo["fecha_inicio"], "$lte": bloqueo["fecha_fin"]}
    }
    if bloqueo["tipo"] == "medico":
        query["medico_id"] = bloqueo.get("medico_id")
    citas = await db.citas.find(query, {"_id": 0}).to_list(2000)
    # Para franjas de horas de médico, filtrar por solape horario
    if bloqueo["tipo"] == "medico" and not bloqueo.get("dia_completo") and bloqueo.get("hora_inicio"):
        hi, hf = bloqueo["hora_inicio"], bloqueo["hora_fin"]
        citas = [
            c for c in citas
            if c.get("hora_inicio", "") < hf and (c.get("hora_fin") or c.get("hora_inicio", "")) > hi
        ]
    return citas


async def insertar_cita(cita: CitaCreate, creado_por_id: str, creado_por_nombre: str):
    """Inserta una cita respetando los bloqueos de agenda (enforcement duro).

    Reutilizado por la agenda interna y el agente externo. Lanza HTTP 409 si el
    espacio está bloqueado.
    """
    now = datetime.now(timezone.utc)

    hora_fin = cita.hora_fin
    if not hora_fin:
        hora_inicio_dt = datetime.strptime(cita.hora_inicio, "%H:%M")
        hora_fin_dt = hora_inicio_dt + timedelta(minutes=cita.duracion_minutos)
        hora_fin = hora_fin_dt.strftime("%H:%M")

    # Enforcement: verificar bloqueos y horario del médico antes de crear
    motivo, _bloqueo = await motivo_no_disponible(cita.medico_id, cita.fecha, cita.hora_inicio, hora_fin)
    if motivo:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede agendar: {motivo}"
        )

    cita_doc = {
        "id": str(uuid.uuid4()),
        "paciente_id": cita.paciente_id,
        "paciente_nombre": cita.paciente_nombre,
        "medico_id": cita.medico_id,
        "medico_nombre": cita.medico_nombre,
        "fecha": cita.fecha,
        "hora_inicio": cita.hora_inicio,
        "hora_fin": hora_fin,
        "duracion_minutos": cita.duracion_minutos,
        "tipo_cita": cita.tipo_cita,
        "estado": EstadoCita.AGENDADA,
        "asistio": None,
        "hora_llegada": None,
        "hora_inicio_consulta": None,
        "hora_fin_consulta": None,
        "asignado_a_medico_id": cita.medico_id,
        "asignado_a_medico_nombre": cita.medico_nombre,
        "notas": cita.notas,
        "tipo_agenda": "pacientes",
        "google_event_id": None,
        "creado_por": creado_por_id,
        "creado_por_nombre": creado_por_nombre,
        "fecha_creacion": now.isoformat(),
        "actualizado_por": None,
        "fecha_actualizacion": None
    }

    await db.citas.insert_one(cita_doc)
    if "_id" in cita_doc:
        del cita_doc["_id"]

    try:
        from routes.google_calendar import push_cita
        await push_cita(cita_doc)
    except Exception:
        pass

    await notify_agenda_update("cita_creada", {
        "cita": cita_doc,
        "fecha": cita.fecha,
        "medico_id": cita.medico_id
    })

    return cita_doc


# ==================== CITAS ====================

@router.get("/citas", response_model=CitaListResponse)
async def listar_citas(
    fecha: Optional[str] = None,
    medico_id: Optional[str] = None,
    estado: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Listar citas del día (o filtradas)"""
    query = {"tipo_agenda": "pacientes"}
    
    if fecha:
        query["fecha"] = fecha
    else:
        # Por defecto, hoy (hora Guatemala)
        query["fecha"] = today_str_gt()
    
    if medico_id:
        query["medico_id"] = medico_id
    
    if estado:
        # Filtro explícito por estado (permite ver Canceladas si se solicita, p.ej. Fase 2)
        query["estado"] = estado
    else:
        # Por defecto, ocultar las citas canceladas de las vistas activas
        query["estado"] = {"$ne": EstadoCita.CANCELADA.value}
    
    citas = await db.citas.find(query, {"_id": 0}).sort([("hora_inicio", 1)]).to_list(500)
    return CitaListResponse(data=citas, total=len(citas))


@router.post("/admin/relink-citas")
async def relink_citas(current_user: dict = Depends(require_role("superadmin"))):
    """Mantenimiento: re-vincula citas cuyo paciente_id ya no existe (p.ej. tras una
    migración). Empareja por nombre completo del paciente; si el nombre identifica a un
    único paciente activo lo re-vincula, de lo contrario deja la cita sin expediente
    (paciente_id vacío) para vincularla manualmente."""
    import unicodedata

    def norm(s: str) -> str:
        s = (s or "").strip().lower()
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        return " ".join(s.split())

    # Ids de pacientes activos existentes + mapa nombre->ids
    existing_ids = set()
    nombre_map = {}
    cursor = db.patients.find(
        {"is_active": True},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}
    )
    async for p in cursor:
        existing_ids.add(p["id"])
        full = norm(f"{p.get('first_name','')} {p.get('last_name','')}")
        if full:
            nombre_map.setdefault(full, []).append(p["id"])

    revinculadas = 0
    liberadas = 0
    ok = 0
    citas = db.citas.find({"paciente_id": {"$nin": [None, ""]}}, {"_id": 0, "id": 1, "paciente_id": 1, "paciente_nombre": 1})
    async for c in citas:
        if c["paciente_id"] in existing_ids:
            ok += 1
            continue
        candidatos = nombre_map.get(norm(c.get("paciente_nombre", "")), [])
        if len(candidatos) == 1:
            await db.citas.update_one({"id": c["id"]}, {"$set": {"paciente_id": candidatos[0]}})
            revinculadas += 1
        else:
            await db.citas.update_one({"id": c["id"]}, {"$set": {"paciente_id": ""}})
            liberadas += 1

    return {"revinculadas": revinculadas, "liberadas": liberadas, "ya_ok": ok}



@router.get("/citas/rango", response_model=CitaListResponse)
async def listar_citas_rango(
    desde: str = Query(..., description="Fecha inicio YYYY-MM-DD"),
    hasta: str = Query(..., description="Fecha fin YYYY-MM-DD"),
    medico_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Listar citas en un rango de fechas (para vista semanal)"""
    query = {
        "tipo_agenda": "pacientes",
        "fecha": {"$gte": desde, "$lte": hasta},
        # Ocultar canceladas de las vistas de semana/mes
        "estado": {"$ne": EstadoCita.CANCELADA.value}
    }
    
    if medico_id:
        query["medico_id"] = medico_id
    
    citas = await db.citas.find(query, {"_id": 0}).sort([("fecha", 1), ("hora_inicio", 1)]).to_list(1000)
    return CitaListResponse(data=citas, total=len(citas))


@router.get("/cita-hoy-paciente/{paciente_id}")
async def cita_hoy_paciente(
    paciente_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Devuelve el médico de la cita activa de HOY (hora Guatemala) para un paciente.
    Se usa en el POS para sugerir automáticamente el médico. Si no hay cita, devuelve null."""
    cita = await db.citas.find_one(
        {
            "tipo_agenda": "pacientes",
            "paciente_id": paciente_id,
            "fecha": today_str_gt(),
            "estado": {"$ne": EstadoCita.CANCELADA.value},
            "medico_id": {"$nin": [None, ""]},
        },
        {"_id": 0, "medico_id": 1, "medico_nombre": 1, "hora_inicio": 1},
        sort=[("hora_inicio", 1)],
    )
    if not cita:
        return {"medico": None}
    return {"medico": {"id": cita.get("medico_id"), "name": cita.get("medico_nombre")}}


@router.get("/citas/{cita_id}", response_model=CitaResponse)
async def obtener_cita(
    cita_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener una cita por ID"""
    cita = await db.citas.find_one({"id": cita_id, "tipo_agenda": "pacientes"}, {"_id": 0})
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return CitaResponse(**cita)


@router.post("/citas", response_model=CitaResponse)
async def crear_cita(
    cita: CitaCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nueva cita (respeta bloqueos de agenda)"""
    cita_doc = await insertar_cita(cita, current_user["id"], current_user["name"])
    return CitaResponse(**cita_doc)


@router.put("/citas/{cita_id}", response_model=CitaResponse)
async def actualizar_cita(
    cita_id: str,
    cita_data: CitaUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar/reprogramar cita"""
    cita = await db.citas.find_one({"id": cita_id, "tipo_agenda": "pacientes"})
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    # No permitir editar citas ya atendidas
    if cita["estado"] in [EstadoCita.ATENDIDA, EstadoCita.NO_ASISTIO]:
        raise HTTPException(status_code=400, detail="No se puede modificar una cita ya finalizada")
    
    update_data = {k: v for k, v in cita_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    # Recalcular hora_fin si cambia hora_inicio o duración
    if "hora_inicio" in update_data or "duracion_minutos" in update_data:
        hora_inicio = update_data.get("hora_inicio", cita["hora_inicio"])
        duracion = update_data.get("duracion_minutos", cita["duracion_minutos"])
        hora_inicio_dt = datetime.strptime(hora_inicio, "%H:%M")
        hora_fin_dt = hora_inicio_dt + timedelta(minutes=duracion)
        update_data["hora_fin"] = hora_fin_dt.strftime("%H:%M")
    
    # Enforcement de bloqueos al reprogramar (si cambia fecha/hora/médico)
    if any(k in update_data for k in ("fecha", "hora_inicio", "duracion_minutos", "medico_id")):
        nuevo_medico = update_data.get("medico_id", cita["medico_id"])
        nueva_fecha = update_data.get("fecha", cita["fecha"])
        nueva_hora_ini = update_data.get("hora_inicio", cita["hora_inicio"])
        nueva_hora_fin = update_data.get("hora_fin", cita.get("hora_fin"))
        motivo, _bloqueo = await motivo_no_disponible(nuevo_medico, nueva_fecha, nueva_hora_ini, nueva_hora_fin)
        if motivo:
            raise HTTPException(status_code=409, detail=f"No se puede reprogramar: {motivo}")
        # Bloquear choque de horario: otra cita activa del mismo médico a la misma hora de inicio ese día
        conflicto = await db.citas.find_one({
            "tipo_agenda": "pacientes",
            "id": {"$ne": cita_id},
            "medico_id": nuevo_medico,
            "fecha": nueva_fecha,
            "hora_inicio": nueva_hora_ini,
            "estado": {"$nin": [EstadoCita.ATENDIDA.value, EstadoCita.NO_ASISTIO.value, EstadoCita.CANCELADA.value]}
        })
        if conflicto:
            raise HTTPException(status_code=409, detail="Ese horario ya está ocupado para este médico")
    
    update_data["actualizado_por"] = current_user["id"]
    update_data["fecha_actualizacion"] = datetime.now(timezone.utc).isoformat()
    
    await db.citas.update_one({"id": cita_id}, {"$set": update_data})
    
    cita_actualizada = await db.citas.find_one({"id": cita_id}, {"_id": 0})
    
    # Reflejar cambios en Google Calendar (reprogramación)
    try:
        from routes.google_calendar import push_cita
        await push_cita(cita_actualizada)
    except Exception:
        pass
    
    # Notificar a clientes WebSocket
    await notify_agenda_update("cita_actualizada", {
        "cita": cita_actualizada,
        "fecha": cita_actualizada.get("fecha"),
        "medico_id": cita_actualizada.get("medico_id")
    })
    
    return CitaResponse(**cita_actualizada)


@router.patch("/citas/{cita_id}/estado", response_model=CitaResponse)
async def cambiar_estado_cita(
    cita_id: str,
    estado_data: CitaEstadoUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Cambiar estado de cita (confirmar, presente, en consulta, atendida, no asistió, cancelar)"""
    cita = await db.citas.find_one({"id": cita_id, "tipo_agenda": "pacientes"})
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    now = datetime.now(timezone.utc)
    update_data = {
        "estado": estado_data.estado,
        "actualizado_por": current_user["id"],
        "fecha_actualizacion": now.isoformat()
    }
    
    # Acciones específicas según el nuevo estado
    if estado_data.estado == EstadoCita.PRESENTE:
        update_data["hora_llegada"] = now.isoformat()
        # Guardar el estado anterior para poder revertir la llegada si fue por error
        if cita.get("estado") in [EstadoCita.AGENDADA, EstadoCita.CONFIRMADA]:
            update_data["estado_previo"] = cita["estado"]
    elif estado_data.estado == EstadoCita.EN_CONSULTA:
        update_data["hora_inicio_consulta"] = now.isoformat()
    elif estado_data.estado == EstadoCita.ATENDIDA:
        update_data["hora_fin_consulta"] = now.isoformat()
        update_data["asistio"] = True
    elif estado_data.estado == EstadoCita.NO_ASISTIO:
        update_data["asistio"] = False
    
    await db.citas.update_one({"id": cita_id}, {"$set": update_data})
    
    cita_actualizada = await db.citas.find_one({"id": cita_id}, {"_id": 0})
    
    # Sincronizar con Google Calendar: al cancelar se elimina el evento; otros estados lo actualizan
    try:
        from routes.google_calendar import push_cita, delete_cita_event
        if estado_data.estado == EstadoCita.CANCELADA:
            await delete_cita_event(cita_actualizada)
        else:
            await push_cita(cita_actualizada)
    except Exception:
        pass
    
    # Notificar a clientes WebSocket (cambio de estado es importante)
    await notify_agenda_update("cita_estado_cambiado", {
        "cita": cita_actualizada,
        "nuevo_estado": estado_data.estado,
        "fecha": cita_actualizada.get("fecha"),
        "medico_id": cita_actualizada.get("medico_id")
    })
    
    return CitaResponse(**cita_actualizada)


@router.patch("/citas/{cita_id}/revertir-llegada", response_model=CitaResponse)
async def revertir_llegada_cita(
    cita_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancelar la marca de llegada (paciente marcado Presente/En consulta por error).
    Devuelve la cita a su estado original (Agendada/Confirmada) y limpia los tiempos de llegada."""
    cita = await db.citas.find_one({"id": cita_id, "tipo_agenda": "pacientes"})
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    if cita["estado"] not in [EstadoCita.PRESENTE, EstadoCita.EN_CONSULTA]:
        raise HTTPException(status_code=400, detail="Solo se puede cancelar la llegada de pacientes presentes o en consulta")
    
    estado_original = cita.get("estado_previo") or EstadoCita.AGENDADA
    update_data = {
        "estado": estado_original,
        "hora_llegada": None,
        "hora_inicio_consulta": None,
        "asistio": None,
        "estado_previo": None,
        "actualizado_por": current_user["id"],
        "fecha_actualizacion": datetime.now(timezone.utc).isoformat()
    }
    
    await db.citas.update_one({"id": cita_id}, {"$set": update_data})
    
    cita_actualizada = await db.citas.find_one({"id": cita_id}, {"_id": 0})
    
    # Reflejar en Google Calendar
    try:
        from routes.google_calendar import push_cita
        await push_cita(cita_actualizada)
    except Exception:
        pass
    
    # Notificar a clientes WebSocket
    await notify_agenda_update("cita_estado_cambiado", {
        "cita": cita_actualizada,
        "nuevo_estado": estado_original,
        "fecha": cita_actualizada.get("fecha"),
        "medico_id": cita_actualizada.get("medico_id")
    })
    
    return CitaResponse(**cita_actualizada)


@router.patch("/citas/{cita_id}/asignar", response_model=CitaResponse)
async def asignar_cita(
    cita_id: str,
    asignar_data: CitaAsignarUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Asignar/reasignar paciente presente a otro médico"""
    cita = await db.citas.find_one({"id": cita_id, "tipo_agenda": "pacientes"})
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    # Solo se puede reasignar si está Presente o En consulta
    if cita["estado"] not in [EstadoCita.PRESENTE, EstadoCita.EN_CONSULTA, EstadoCita.CONFIRMADA]:
        raise HTTPException(status_code=400, detail="Solo se puede reasignar pacientes presentes o confirmados")
    
    update_data = {
        "asignado_a_medico_id": asignar_data.asignado_a_medico_id,
        "asignado_a_medico_nombre": asignar_data.asignado_a_medico_nombre,
        "actualizado_por": current_user["id"],
        "fecha_actualizacion": datetime.now(timezone.utc).isoformat()
    }
    
    await db.citas.update_one({"id": cita_id}, {"$set": update_data})
    
    cita_actualizada = await db.citas.find_one({"id": cita_id}, {"_id": 0})
    return CitaResponse(**cita_actualizada)


@router.delete("/citas/{cita_id}")
async def eliminar_cita(
    cita_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Eliminar/cancelar cita"""
    cita = await db.citas.find_one({"id": cita_id, "tipo_agenda": "pacientes"})
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    # Solo admin puede eliminar citas ya atendidas
    if cita["estado"] in [EstadoCita.ATENDIDA, EstadoCita.NO_ASISTIO]:
        if current_user["role"] not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar citas finalizadas")
    
    await db.citas.delete_one({"id": cita_id})
    
    # Eliminar el evento asociado en Google Calendar
    try:
        from routes.google_calendar import delete_cita_event
        await delete_cita_event(cita)
    except Exception:
        pass
    
    return {"message": "Cita eliminada"}


# ==================== PACIENTES PRESENTES ====================

@router.get("/presentes", response_model=PresentesResponse)
async def listar_presentes(
    fecha: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Listar pacientes presentes en clínica, agrupados por médico"""
    if not fecha:
        fecha = today_str_gt()
    
    # Obtener citas con estado Presente o En consulta
    citas = await db.citas.find({
        "tipo_agenda": "pacientes",
        "fecha": fecha,
        "estado": {"$in": [EstadoCita.PRESENTE, EstadoCita.EN_CONSULTA]}
    }, {"_id": 0}).sort("hora_llegada", 1).to_list(500)
    
    # Obtener médicos para colores
    medicos = await db.doctors.find({"is_active": True}, {"_id": 0}).to_list(100)
    medicos_dict = {m["id"]: m for m in medicos}
    
    # Agrupar por médico asignado
    por_medico = {}
    for cita in citas:
        medico_id = cita.get("asignado_a_medico_id") or cita["medico_id"]
        if medico_id not in por_medico:
            medico = medicos_dict.get(medico_id, {})
            por_medico[medico_id] = {
                "medico_id": medico_id,
                "medico_nombre": cita.get("asignado_a_medico_nombre") or cita["medico_nombre"],
                "medico_color": medico.get("color", "#0F6E56"),
                "pacientes": [],
                "total": 0
            }
        
        tiempo_espera = await calcular_tiempo_espera(cita.get("hora_llegada", ""))
        
        por_medico[medico_id]["pacientes"].append({
            "cita_id": cita["id"],
            "paciente_id": cita["paciente_id"],
            "paciente_nombre": cita["paciente_nombre"],
            "hora_llegada": cita.get("hora_llegada", ""),
            "tiempo_espera_minutos": tiempo_espera,
            "estado": cita["estado"],
            "tipo_cita": cita["tipo_cita"],
            "medico_id": cita["medico_id"],
            "medico_nombre": cita["medico_nombre"],
            "asignado_a_medico_id": cita.get("asignado_a_medico_id"),
            "asignado_a_medico_nombre": cita.get("asignado_a_medico_nombre"),
            "notas": cita.get("notas", "")
        })
        por_medico[medico_id]["total"] += 1
    
    return PresentesResponse(
        fecha=fecha,
        por_medico=list(por_medico.values()),
        total_presentes=len(citas)
    )


# ==================== CONTADORES DEL DÍA ====================

@router.get("/contadores", response_model=ContadoresDiaResponse)
async def obtener_contadores(
    fecha: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Obtener contadores del día (para tablero)"""
    if not fecha:
        fecha = today_str_gt()
    
    # Pipeline de agregación para contar por estado
    pipeline = [
        {"$match": {"tipo_agenda": "pacientes", "fecha": fecha}},
        {"$group": {"_id": "$estado", "count": {"$sum": 1}}}
    ]
    
    resultados = await db.citas.aggregate(pipeline).to_list(20)
    contadores = {r["_id"]: r["count"] for r in resultados}
    
    # Pipeline para contar por médico (excluye canceladas del total activo)
    pipeline_medico = [
        {"$match": {"tipo_agenda": "pacientes", "fecha": fecha, "estado": {"$ne": EstadoCita.CANCELADA.value}}},
        {"$group": {
            "_id": "$medico_id",
            "medico_nombre": {"$first": "$medico_nombre"},
            "total": {"$sum": 1},
            "presentes": {"$sum": {"$cond": [{"$in": ["$estado", ["Presente", "En consulta"]]}, 1, 0]}},
            "atendidos": {"$sum": {"$cond": [{"$eq": ["$estado", "Atendida"]}, 1, 0]}}
        }}
    ]
    
    por_medico = await db.citas.aggregate(pipeline_medico).to_list(50)
    
    return ContadoresDiaResponse(
        fecha=fecha,
        total_agendados=contadores.get(EstadoCita.AGENDADA, 0),
        total_confirmados=contadores.get(EstadoCita.CONFIRMADA, 0),
        total_presentes=contadores.get(EstadoCita.PRESENTE, 0),
        total_en_consulta=contadores.get(EstadoCita.EN_CONSULTA, 0),
        total_atendidos=contadores.get(EstadoCita.ATENDIDA, 0),
        total_no_asistio=contadores.get(EstadoCita.NO_ASISTIO, 0),
        total_cancelados=contadores.get(EstadoCita.CANCELADA, 0),
        por_medico=[{
            "medico_id": m["_id"],
            "medico_nombre": m["medico_nombre"],
            "total": m["total"],
            "presentes": m["presentes"],
            "atendidos": m["atendidos"]
        } for m in por_medico]
    )


# ==================== MI AGENDA (MÉDICO) ====================

@router.get("/mi-dia", response_model=MiAgendaResponse)
async def mi_agenda_del_dia(
    fecha: Optional[str] = Query(None, description="Fecha YYYY-MM-DD; por defecto hoy (hora Guatemala)"),
    current_user: dict = Depends(get_current_user)
):
    """Agenda del día para el médico autenticado.
    Respeta la fecha que se está trabajando (param `fecha`); si no se envía usa hoy en hora Guatemala (UTC-6)."""
    # Buscar si el usuario está vinculado a un médico
    medico = await get_medico_vinculado(current_user["id"])
    
    if not medico and current_user["role"] not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Usuario no vinculado a un médico")
    
    # Fecha de trabajo: la enviada por el frontend o el día actual en hora Guatemala
    if not fecha:
        fecha = today_str_gt()
    medico_id = medico["id"] if medico else None
    medico_nombre = medico["name"] if medico else current_user["name"]
    
    # Si es admin sin médico vinculado, mostrar todas las citas
    query = {"tipo_agenda": "pacientes", "fecha": fecha, "estado": {"$ne": EstadoCita.CANCELADA.value}}
    if medico_id:
        query["$or"] = [
            {"medico_id": medico_id},
            {"asignado_a_medico_id": medico_id}
        ]
    
    citas = await db.citas.find(query, {"_id": 0}).sort("hora_inicio", 1).to_list(500)
    
    # Separar presentes
    presentes = []
    for cita in citas:
        if cita["estado"] in [EstadoCita.PRESENTE, EstadoCita.EN_CONSULTA]:
            tiempo_espera = await calcular_tiempo_espera(cita.get("hora_llegada", ""))
            presentes.append({
                "cita_id": cita["id"],
                "paciente_id": cita["paciente_id"],
                "paciente_nombre": cita["paciente_nombre"],
                "hora_llegada": cita.get("hora_llegada", ""),
                "tiempo_espera_minutos": tiempo_espera,
                "estado": cita["estado"],
                "tipo_cita": cita["tipo_cita"],
                "medico_id": cita["medico_id"],
                "medico_nombre": cita["medico_nombre"],
                "asignado_a_medico_id": cita.get("asignado_a_medico_id"),
                "asignado_a_medico_nombre": cita.get("asignado_a_medico_nombre")
            })
    
    # Contadores
    contadores = {
        "total": len(citas),
        "agendados": len([c for c in citas if c["estado"] == EstadoCita.AGENDADA]),
        "confirmados": len([c for c in citas if c["estado"] == EstadoCita.CONFIRMADA]),
        "presentes": len([c for c in citas if c["estado"] == EstadoCita.PRESENTE]),
        "en_consulta": len([c for c in citas if c["estado"] == EstadoCita.EN_CONSULTA]),
        "atendidos": len([c for c in citas if c["estado"] == EstadoCita.ATENDIDA]),
        "no_asistio": len([c for c in citas if c["estado"] == EstadoCita.NO_ASISTIO])
    }
    
    return MiAgendaResponse(
        fecha=fecha,
        medico_id=medico_id or "",
        medico_nombre=medico_nombre,
        citas_del_dia=citas,
        pacientes_presentes=presentes,
        contadores=contadores
    )


@router.get("/mi-semana")
async def mi_agenda_semana(
    desde: str = Query(..., description="Fecha inicio YYYY-MM-DD"),
    hasta: str = Query(..., description="Fecha fin YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user)
):
    """Resumen semanal del médico autenticado: sus citas activas en el rango [desde, hasta]."""
    medico = await get_medico_vinculado(current_user["id"])
    if not medico and current_user["role"] not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Usuario no vinculado a un médico")

    medico_id = medico["id"] if medico else None
    medico_nombre = medico["name"] if medico else current_user["name"]

    query = {
        "tipo_agenda": "pacientes",
        "fecha": {"$gte": desde, "$lte": hasta},
        "estado": {"$ne": EstadoCita.CANCELADA.value}
    }
    if medico_id:
        query["$or"] = [
            {"medico_id": medico_id},
            {"asignado_a_medico_id": medico_id}
        ]

    citas = await db.citas.find(query, {"_id": 0}).sort([("fecha", 1), ("hora_inicio", 1)]).to_list(1000)
    return {
        "desde": desde,
        "hasta": hasta,
        "medico_id": medico_id or "",
        "medico_nombre": medico_nombre,
        "citas": citas,
        "total": len(citas)
    }


# ==================== PREFERENCIAS DE MÉDICOS (POR USUARIO) ====================

class PreferenciasMedicos(BaseModel):
    orden: List[str] = []
    ocultos: List[str] = []


@router.get("/preferencias-medicos")
async def get_preferencias_medicos(current_user: dict = Depends(get_current_user)):
    """Devuelve el orden y los médicos ocultos configurados por el usuario para la vista Día/Tablero."""
    pref = await db.user_preferences.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not pref:
        return {"orden": [], "ocultos": []}
    return {
        "orden": pref.get("medicos_orden", []),
        "ocultos": pref.get("medicos_ocultos", [])
    }


@router.put("/preferencias-medicos")
async def set_preferencias_medicos(
    prefs: PreferenciasMedicos,
    current_user: dict = Depends(get_current_user)
):
    """Guarda el orden y los médicos ocultos del usuario (se recuerda en su cuenta)."""
    await db.user_preferences.update_one(
        {"user_id": current_user["id"]},
        {"$set": {
            "user_id": current_user["id"],
            "medicos_orden": prefs.orden,
            "medicos_ocultos": prefs.ocultos,
            "updated_at": now_gt().isoformat()
        }},
        upsert=True
    )
    return {"orden": prefs.orden, "ocultos": prefs.ocultos}



# ==================== WALK-IN (SIN CITA) ====================

@router.post("/walk-in", response_model=CitaResponse)
async def registrar_walk_in(
    walk_in: WalkInCreate,
    current_user: dict = Depends(get_current_user)
):
    """Registrar paciente que llega sin cita (walk-in)"""
    now = now_gt()
    fecha = now.strftime("%Y-%m-%d")
    hora = now.strftime("%H:%M")
    
    cita_doc = {
        "id": str(uuid.uuid4()),
        "paciente_id": walk_in.paciente_id,
        "paciente_nombre": walk_in.paciente_nombre,
        "medico_id": walk_in.medico_id,
        "medico_nombre": walk_in.medico_nombre,
        "fecha": fecha,
        "hora_inicio": hora,
        "hora_fin": None,
        "duracion_minutos": 20,
        "tipo_cita": walk_in.tipo_cita,
        "estado": EstadoCita.PRESENTE,  # Directo a presente
        "asistio": None,
        "hora_llegada": now.isoformat(),
        "hora_inicio_consulta": None,
        "hora_fin_consulta": None,
        "asignado_a_medico_id": walk_in.medico_id,
        "asignado_a_medico_nombre": walk_in.medico_nombre,
        "notas": f"Walk-in. {walk_in.notas or ''}".strip(),
        "tipo_agenda": "pacientes",
        "google_event_id": None,
        "creado_por": current_user["id"],
        "creado_por_nombre": current_user["name"],
        "fecha_creacion": now.isoformat(),
        "actualizado_por": None,
        "fecha_actualizacion": None
    }
    
    await db.citas.insert_one(cita_doc)
    if "_id" in cita_doc:
        del cita_doc["_id"]
    
    return CitaResponse(**cita_doc)


# ==================== CONFIGURACIÓN ====================

@config_router.get("", response_model=AgendaConfigResponse)
async def obtener_configuracion(
    current_user: dict = Depends(get_current_user)
):
    """Obtener configuración de agenda"""
    config = await get_agenda_config()
    return AgendaConfigResponse(**config)


@config_router.put("", response_model=AgendaConfigResponse)
async def actualizar_configuracion(
    config_data: AgendaConfigUpdate,
    current_user: dict = Depends(require_role(["superadmin", "admin"]))
):
    """Actualizar configuración de agenda (solo admin)"""
    config = await get_agenda_config()
    
    update_data = {k: v for k, v in config_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    # Serializar tipos_cita si se proporciona
    if "tipos_cita" in update_data:
        update_data["tipos_cita"] = [t.model_dump() if hasattr(t, 'model_dump') else t for t in update_data["tipos_cita"]]
    
    update_data["actualizado_por"] = current_user["id"]
    update_data["fecha_actualizacion"] = datetime.now(timezone.utc).isoformat()
    
    await db.agenda_config.update_one({"tipo": "pacientes"}, {"$set": update_data})
    
    config_actualizada = await db.agenda_config.find_one({"tipo": "pacientes"}, {"_id": 0})
    return AgendaConfigResponse(**config_actualizada)


# ==================== MÉDICOS PARA AGENDA ====================

@medicos_agenda_router.get("")
async def listar_medicos_agenda(
    current_user: dict = Depends(get_current_user)
):
    """Listar médicos activos para la agenda (con colores)"""
    medicos = await db.doctors.find(
        {"is_active": True},
        {"_id": 0, "id": 1, "name": 1, "specialty": 1, "color": 1, "usuario_id": 1}
    ).sort("name", 1).to_list(100)
    
    # Asignar colores por defecto si no tienen
    colores_default = ["#0F6E56", "#38B2AC", "#805AD5", "#DD6B20", "#E53E3E", "#3182CE", "#D69E2E"]
    for i, m in enumerate(medicos):
        if not m.get("color"):
            m["color"] = colores_default[i % len(colores_default)]
    
    return {"data": medicos, "total": len(medicos)}


@medicos_agenda_router.patch("/{medico_id}")
async def actualizar_medico_agenda(
    medico_id: str,
    data: dict,
    current_user: dict = Depends(require_role(["superadmin", "admin"]))
):
    """Actualizar campos de agenda del médico (color, usuario_id)"""
    medico = await db.doctors.find_one({"id": medico_id})
    if not medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    
    update_fields = {}
    if "color" in data:
        update_fields["color"] = data["color"]
    if "usuario_id" in data:
        update_fields["usuario_id"] = data["usuario_id"]
    
    if update_fields:
        await db.doctors.update_one({"id": medico_id}, {"$set": update_fields})
    
    medico_actualizado = await db.doctors.find_one({"id": medico_id}, {"_id": 0})
    return medico_actualizado


# ==================== PRÓXIMA CITA (DESDE EVALUACIÓN) ====================

@router.post("/proxima-cita", response_model=CitaResponse)
async def crear_proxima_cita(
    cita_data: ProximaCitaCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear próxima cita desde Evaluación Oftalmológica"""
    now = datetime.now(timezone.utc)
    
    # Verificar que no exista duplicado
    existente = await db.citas.find_one({
        "tipo_agenda": "pacientes",
        "paciente_id": cita_data.paciente_id,
        "fecha": cita_data.fecha,
        "hora_inicio": cita_data.hora_inicio,
        "estado": {"$nin": [EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO]}
    })
    
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una cita para este paciente en esa fecha y hora")
    
    # Calcular hora fin
    duracion = 20  # Por defecto
    hora_inicio_dt = datetime.strptime(cita_data.hora_inicio, "%H:%M")
    hora_fin_dt = hora_inicio_dt + timedelta(minutes=duracion)
    hora_fin = hora_fin_dt.strftime("%H:%M")
    
    # Enforcement de bloqueos y horario del médico
    motivo, _bloqueo = await motivo_no_disponible(cita_data.medico_id, cita_data.fecha, cita_data.hora_inicio, hora_fin)
    if motivo:
        raise HTTPException(status_code=409, detail=f"No se puede agendar: {motivo}")

    # No permitir fechas/horas pasadas (consistente con horarios-disponibles)
    hoy = today_str_gt()
    if cita_data.fecha < hoy:
        raise HTTPException(status_code=409, detail="No se puede agendar: la fecha ya pasó")
    if cita_data.fecha == hoy and cita_data.hora_inicio <= now_gt().strftime("%H:%M"):
        raise HTTPException(status_code=409, detail="No se puede agendar: la hora ya pasó")

    # Respetar el sobrecupo máximo por horario (max_citas_por_slot)
    config = await get_agenda_config()
    max_por_slot = int(config.get("max_citas_por_slot") or 1)
    ocupados = await db.citas.count_documents({
        "tipo_agenda": "pacientes",
        "medico_id": cita_data.medico_id,
        "fecha": cita_data.fecha,
        "hora_inicio": cita_data.hora_inicio,
        "estado": {"$nin": [EstadoCita.CANCELADA.value, EstadoCita.NO_ASISTIO.value]}
    })
    if ocupados >= max_por_slot:
        raise HTTPException(status_code=409, detail="No se puede agendar: el horario ya está lleno")
    
    cita_doc = {
        "id": str(uuid.uuid4()),
        "paciente_id": cita_data.paciente_id,
        "paciente_nombre": cita_data.paciente_nombre,
        "medico_id": cita_data.medico_id,
        "medico_nombre": cita_data.medico_nombre,
        "fecha": cita_data.fecha,
        "hora_inicio": cita_data.hora_inicio,
        "hora_fin": hora_fin,
        "duracion_minutos": duracion,
        "tipo_cita": cita_data.tipo_cita,
        "estado": EstadoCita.AGENDADA,
        "asistio": None,
        "hora_llegada": None,
        "hora_inicio_consulta": None,
        "hora_fin_consulta": None,
        "asignado_a_medico_id": cita_data.medico_id,
        "asignado_a_medico_nombre": cita_data.medico_nombre,
        "notas": cita_data.notas,
        "tipo_agenda": "pacientes",
        "google_event_id": None,
        "evaluacion_origen_id": cita_data.evaluacion_id,
        "creado_por": current_user["id"],
        "creado_por_nombre": current_user["name"],
        "fecha_creacion": now.isoformat(),
        "actualizado_por": None,
        "fecha_actualizacion": None
    }
    
    await db.citas.insert_one(cita_doc)
    if "_id" in cita_doc:
        del cita_doc["_id"]
    
    return CitaResponse(**cita_doc)


@router.get("/horarios-disponibles")
async def horarios_disponibles(
    medico_id: str = Query(...),
    fecha: str = Query(..., description="YYYY-MM-DD"),
    duracion: int = Query(20, description="Duración de la cita en minutos"),
    current_user: dict = Depends(get_current_user)
):
    """Devuelve las horas libres de un médico para una fecha, considerando
    su horario laboral, bloqueos y citas existentes (respeta el sobrecupo)."""
    try:
        dia_semana = datetime.strptime(fecha, "%Y-%m-%d").isoweekday()  # 1=Lun..7=Dom
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")

    config = await get_agenda_config()
    paso = int(config.get("duracion_slot_minutos") or 15)
    max_por_slot = int(config.get("max_citas_por_slot") or 1)

    # 1) Determinar ventana de atención del médico
    medico = await db.doctors.find_one({"id": medico_id}, {"_id": 0, "horario_semanal": 1})
    win_ini, win_fin = None, None
    horario = (medico or {}).get("horario_semanal")
    # Un horario sin ningún día activo equivale a "sin restricción"
    if horario and not any((v or {}).get("activo") for v in horario.values()):
        horario = None
    if horario:
        cfg = horario.get(str(dia_semana))
        if not cfg or not cfg.get("activo"):
            return {"disponible": False, "motivo": "El médico no atiende ese día", "slots": [], "duracion": duracion}
        win_ini = cfg.get("hora_inicio") or config.get("hora_apertura", "07:00")
        win_fin = cfg.get("hora_fin") or config.get("hora_cierre", "18:00")
    else:
        # Fallback: configuración general de la agenda
        if dia_semana not in (config.get("dias_laborables") or [1, 2, 3, 4, 5, 6]):
            return {"disponible": False, "motivo": "La clínica no atiende ese día", "slots": [], "duracion": duracion}
        win_ini = config.get("hora_apertura", "07:00")
        win_fin = config.get("hora_cierre", "18:00")

    # 2) Bloqueos de día completo (clínica o médico)
    clinica = await db.bloqueos_agenda.find_one({
        "tipo": "clinica", "fecha_inicio": {"$lte": fecha}, "fecha_fin": {"$gte": fecha}
    }, {"_id": 0})
    if clinica:
        return {"disponible": False, "motivo": clinica.get("motivo") or "Feriado/Vacaciones", "slots": [], "duracion": duracion}

    franjas_bloqueadas = []
    async for b in db.bloqueos_agenda.find({
        "tipo": "medico", "medico_id": medico_id,
        "fecha_inicio": {"$lte": fecha}, "fecha_fin": {"$gte": fecha}
    }, {"_id": 0}):
        if b.get("dia_completo"):
            return {"disponible": False, "motivo": b.get("motivo") or "Horario bloqueado", "slots": [], "duracion": duracion}
        if b.get("hora_inicio") and b.get("hora_fin"):
            franjas_bloqueadas.append((b["hora_inicio"], b["hora_fin"]))

    # 3) Citas existentes (para contar sobrecupo por hora de inicio)
    citas = await db.citas.find({
        "tipo_agenda": "pacientes", "medico_id": medico_id, "fecha": fecha,
        "estado": {"$nin": [EstadoCita.CANCELADA.value, EstadoCita.NO_ASISTIO.value]}
    }, {"_id": 0, "hora_inicio": 1}).to_list(2000)
    conteo = {}
    for c in citas:
        hi = c.get("hora_inicio")
        if hi:
            conteo[hi] = conteo.get(hi, 0) + 1

    # 4) Hora actual (para no ofrecer horas pasadas si la fecha es hoy)
    ahora_hhmm = None
    if fecha == today_str_gt():
        ahora_hhmm = now_gt().strftime("%H:%M")

    def to_min(hhmm):
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)

    def to_hhmm(mins):
        return f"{mins // 60:02d}:{mins % 60:02d}"

    win_ini_m, win_fin_m = to_min(win_ini), to_min(win_fin)
    slots = []
    t = win_ini_m
    while t + duracion <= win_fin_m:
        slot = to_hhmm(t)
        slot_fin = to_hhmm(t + duracion)
        # franja bloqueada (solape)
        bloqueado = any(slot < bf and slot_fin > bi for (bi, bf) in franjas_bloqueadas)
        # hora pasada
        pasada = ahora_hhmm is not None and slot <= ahora_hhmm
        # lleno (sobrecupo)
        lleno = conteo.get(slot, 0) >= max_por_slot
        if not bloqueado and not pasada and not lleno:
            slots.append(slot)
        t += paso

    motivo = None if slots else "No hay horarios disponibles ese día"
    return {"disponible": bool(slots), "motivo": motivo, "slots": slots, "duracion": duracion}


@router.get("/verificar-horario")
async def verificar_horario(
    medico_id: str = Query(...),
    fecha: str = Query(..., description="YYYY-MM-DD"),
    hora: str = Query(..., description="HH:MM"),
    duracion: int = Query(20),
    current_user: dict = Depends(get_current_user)
):
    """Verifica un horario puntual para agendar desde la Agenda.
    Devuelve estado: 'no_disponible' (bloqueo/horario médico), 'lleno' (alcanzó
    el cupo máximo por franja) o 'libre'. No crea nada; el sobrecupo se permite
    tras confirmación del usuario."""
    try:
        hora_inicio_dt = datetime.strptime(hora, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Hora inválida")
    hora_fin = (hora_inicio_dt + timedelta(minutes=duracion)).strftime("%H:%M")

    motivo, _bloqueo = await motivo_no_disponible(medico_id, fecha, hora, hora_fin)
    if motivo:
        return {"estado": "no_disponible", "motivo": motivo, "ocupadas": 0}

    config = await get_agenda_config()
    max_por_slot = int(config.get("max_citas_por_slot") or 1)
    ocupadas = await db.citas.count_documents({
        "tipo_agenda": "pacientes",
        "medico_id": medico_id,
        "fecha": fecha,
        "hora_inicio": hora,
        "estado": {"$nin": [EstadoCita.CANCELADA.value, EstadoCita.NO_ASISTIO.value]}
    })
    if ocupadas >= max_por_slot:
        return {"estado": "lleno", "motivo": None, "ocupadas": ocupadas}
    return {"estado": "libre", "motivo": None, "ocupadas": ocupadas}


# ==================== BLOQUEOS DE AGENDA ====================

def _bloqueo_to_response(b: dict) -> dict:
    """Normaliza un documento de bloqueo para la respuesta."""
    return {
        "id": b["id"],
        "tipo": b["tipo"],
        "medico_id": b.get("medico_id"),
        "medico_nombre": b.get("medico_nombre"),
        "fecha_inicio": b["fecha_inicio"],
        "fecha_fin": b["fecha_fin"],
        "dia_completo": b.get("dia_completo", True),
        "hora_inicio": b.get("hora_inicio"),
        "hora_fin": b.get("hora_fin"),
        "motivo": b.get("motivo"),
        "creado_por": b.get("creado_por"),
        "creado_por_nombre": b.get("creado_por_nombre"),
        "fecha_creacion": b.get("fecha_creacion"),
    }


@router.post("/bloqueos", response_model=BloqueoCreateResult)
async def crear_bloqueo(
    bloqueo: BloqueoAgendaCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear un bloqueo de agenda (por médico o de clínica).

    Cualquier usuario puede crear bloqueos. Si ya existen citas en el horario/día
    bloqueado, el bloqueo se crea igual y se devuelven las citas en conflicto para
    reprogramación manual (no se cancelan automáticamente).
    """
    tipo = bloqueo.tipo.value if hasattr(bloqueo.tipo, "value") else bloqueo.tipo

    # Validaciones
    if tipo == "medico" and not bloqueo.medico_id:
        raise HTTPException(status_code=400, detail="medico_id es requerido para bloqueos de médico")

    fecha_inicio = bloqueo.fecha_inicio
    fecha_fin = bloqueo.fecha_fin or bloqueo.fecha_inicio
    if fecha_fin < fecha_inicio:
        raise HTTPException(status_code=400, detail="fecha_fin no puede ser anterior a fecha_inicio")

    # Clínica = siempre día(s) completo(s)
    dia_completo = True if tipo == "clinica" else bloqueo.dia_completo
    hora_inicio = None
    hora_fin = None
    if tipo == "medico" and not dia_completo:
        if not bloqueo.hora_inicio or not bloqueo.hora_fin:
            raise HTTPException(status_code=400, detail="hora_inicio y hora_fin son requeridas para un bloqueo por franja de horas")
        if bloqueo.hora_fin <= bloqueo.hora_inicio:
            raise HTTPException(status_code=400, detail="hora_fin debe ser posterior a hora_inicio")
        hora_inicio = bloqueo.hora_inicio
        hora_fin = bloqueo.hora_fin

    doc = {
        "id": str(uuid.uuid4()),
        "tipo": tipo,
        "medico_id": bloqueo.medico_id if tipo == "medico" else None,
        "medico_nombre": bloqueo.medico_nombre if tipo == "medico" else None,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "dia_completo": dia_completo,
        "hora_inicio": hora_inicio,
        "hora_fin": hora_fin,
        "motivo": bloqueo.motivo,
        "creado_por": current_user["id"],
        "creado_por_nombre": current_user["name"],
        "fecha_creacion": datetime.now(timezone.utc).isoformat(),
    }

    await db.bloqueos_agenda.insert_one(doc)
    if "_id" in doc:
        del doc["_id"]

    citas_conflicto = await listar_citas_conflicto(doc)

    await notify_agenda_update("bloqueo_creado", {"bloqueo": _bloqueo_to_response(doc)})

    return BloqueoCreateResult(
        bloqueo=BloqueoAgendaResponse(**_bloqueo_to_response(doc)),
        citas_en_conflicto=[CitaResponse(**c) for c in citas_conflicto]
    )


@router.get("/bloqueos", response_model=BloqueoListResponse)
async def listar_bloqueos(
    medico_id: Optional[str] = Query(None),
    fecha: Optional[str] = Query(None, description="Devuelve bloqueos que cubran esta fecha"),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Listar bloqueos vigentes (por médico y de clínica)."""
    query = {}
    if medico_id:
        # Incluir bloqueos del médico y los de clínica (aplican a todos)
        query["$or"] = [{"tipo": "clinica"}, {"tipo": "medico", "medico_id": medico_id}]
    if fecha:
        query["fecha_inicio"] = {"$lte": fecha}
        query["fecha_fin"] = {"$gte": fecha}
    else:
        if desde:
            query["fecha_fin"] = {"$gte": desde}
        if hasta:
            query["fecha_inicio"] = {"$lte": hasta}

    bloqueos = await db.bloqueos_agenda.find(query, {"_id": 0}).sort("fecha_inicio", 1).to_list(2000)
    data = [BloqueoAgendaResponse(**_bloqueo_to_response(b)) for b in bloqueos]
    return BloqueoListResponse(data=data, total=len(data))


@router.delete("/bloqueos/{bloqueo_id}")
async def eliminar_bloqueo(
    bloqueo_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Eliminar un bloqueo (cualquier usuario puede eliminar cualquier bloqueo)."""
    result = await db.bloqueos_agenda.delete_one({"id": bloqueo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bloqueo no encontrado")
    await notify_agenda_update("bloqueo_eliminado", {"bloqueo_id": bloqueo_id})
    return {"message": "Bloqueo eliminado", "id": bloqueo_id}


# ==================== API AGENTE EXTERNO (clave fija) ====================

@external_router.get("/disponibilidad", response_model=DisponibilidadResponse)
async def disponibilidad_externa(
    medico_id: str = Query(...),
    fecha: str = Query(..., description="YYYY-MM-DD"),
    hora_inicio: Optional[str] = Query(None, description="HH:MM"),
    hora_fin: Optional[str] = Query(None, description="HH:MM"),
    _: bool = Depends(verificar_clave_api_externa)
):
    """Consulta disponibilidad de un médico considerando bloqueos, horario laboral y citas existentes."""
    bloqueo = await verificar_bloqueo(medico_id, fecha, hora_inicio, hora_fin)
    if bloqueo:
        motivo = bloqueo.get("motivo") or ("Feriado/Vacaciones" if bloqueo["tipo"] == "clinica" else "Horario bloqueado")
        return DisponibilidadResponse(
            disponible=False,
            motivo=motivo,
            bloqueo=BloqueoAgendaResponse(**_bloqueo_to_response(bloqueo)),
            citas_existentes=[]
        )

    # Fuera del horario laboral del médico
    motivo_horario = await verificar_horario_medico(medico_id, fecha, hora_inicio, hora_fin)
    if motivo_horario:
        return DisponibilidadResponse(
            disponible=False,
            motivo=motivo_horario,
            bloqueo=None,
            citas_existentes=[]
        )

    # Citas existentes del médico en esa fecha (y solape de hora si se indica)
    citas = await db.citas.find({
        "tipo_agenda": "pacientes",
        "medico_id": medico_id,
        "fecha": fecha,
        "estado": {"$nin": [EstadoCita.CANCELADA.value, EstadoCita.NO_ASISTIO.value]}
    }, {"_id": 0}).to_list(2000)

    if hora_inicio and hora_fin:
        citas = [
            c for c in citas
            if c.get("hora_inicio", "") < hora_fin and (c.get("hora_fin") or c.get("hora_inicio", "")) > hora_inicio
        ]

    return DisponibilidadResponse(
        disponible=True,
        motivo=None,
        bloqueo=None,
        citas_existentes=[CitaResponse(**c) for c in citas]
    )


@external_router.get("/bloqueos", response_model=BloqueoListResponse)
async def listar_bloqueos_externo(
    medico_id: Optional[str] = Query(None),
    fecha: Optional[str] = Query(None),
    _: bool = Depends(verificar_clave_api_externa)
):
    """Lista los bloqueos vigentes para el agente externo."""
    query = {}
    if medico_id:
        query["$or"] = [{"tipo": "clinica"}, {"tipo": "medico", "medico_id": medico_id}]
    if fecha:
        query["fecha_inicio"] = {"$lte": fecha}
        query["fecha_fin"] = {"$gte": fecha}
    bloqueos = await db.bloqueos_agenda.find(query, {"_id": 0}).sort("fecha_inicio", 1).to_list(2000)
    data = [BloqueoAgendaResponse(**_bloqueo_to_response(b)) for b in bloqueos]
    return BloqueoListResponse(data=data, total=len(data))


@external_router.post("/citas", response_model=CitaResponse)
async def crear_cita_externa(
    cita: CitaExternaCreate,
    _: bool = Depends(verificar_clave_api_externa)
):
    """Agenda una cita desde el agente externo, respetando los bloqueos (rechaza si está bloqueado)."""
    cita_create = CitaCreate(
        paciente_id=cita.paciente_id,
        paciente_nombre=cita.paciente_nombre,
        medico_id=cita.medico_id,
        medico_nombre=cita.medico_nombre,
        fecha=cita.fecha,
        hora_inicio=cita.hora_inicio,
        hora_fin=cita.hora_fin,
        duracion_minutos=cita.duracion_minutos,
        tipo_cita=cita.tipo_cita,
        notas=cita.notas
    )
    cita_doc = await insertar_cita(cita_create, creado_por_id="agente_externo", creado_por_nombre="Agente Externo (n8n)")
    return CitaResponse(**cita_doc)
