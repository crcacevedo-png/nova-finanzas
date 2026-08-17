# /app/backend/routes/agenda.py
# Rutas del módulo de Agenda de Pacientes
# IMPORTANTE: Esta agenda es INDEPENDIENTE de la agenda de Sala de Operaciones

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid

from models.agenda import (
    CitaCreate, CitaUpdate, CitaResponse, CitaListResponse,
    CitaEstadoUpdate, CitaAsignarUpdate,
    AgendaConfigUpdate, AgendaConfigResponse, TipoCitaConfig,
    PresentesResponse, PresentesPorMedicoResponse, PacientePresenteResponse,
    ContadoresDiaResponse, MiAgendaResponse, WalkInCreate, ProximaCitaCreate,
    EstadoCita, TipoCita
)
from config.database import db
from routes.auth import get_current_user, require_permission, require_role

# Routers
router = APIRouter(prefix="/agenda", tags=["Agenda"])
medicos_agenda_router = APIRouter(prefix="/medicos-agenda", tags=["Médicos Agenda"])
config_router = APIRouter(prefix="/agenda/configuracion", tags=["Configuración Agenda"])

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
    except:
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
        # Por defecto, hoy
        query["fecha"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    if medico_id:
        query["medico_id"] = medico_id
    
    if estado:
        query["estado"] = estado
    
    citas = await db.citas.find(query, {"_id": 0}).sort([("hora_inicio", 1)]).to_list(500)
    return CitaListResponse(data=citas, total=len(citas))


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
        "fecha": {"$gte": desde, "$lte": hasta}
    }
    
    if medico_id:
        query["medico_id"] = medico_id
    
    citas = await db.citas.find(query, {"_id": 0}).sort([("fecha", 1), ("hora_inicio", 1)]).to_list(1000)
    return CitaListResponse(data=citas, total=len(citas))


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
    """Crear nueva cita"""
    now = datetime.now(timezone.utc)
    
    # Calcular hora_fin si no se proporciona
    hora_fin = cita.hora_fin
    if not hora_fin:
        hora_inicio = datetime.strptime(cita.hora_inicio, "%H:%M")
        hora_fin_dt = hora_inicio + timedelta(minutes=cita.duracion_minutos)
        hora_fin = hora_fin_dt.strftime("%H:%M")
    
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
        "creado_por": current_user["id"],
        "creado_por_nombre": current_user["name"],
        "fecha_creacion": now.isoformat(),
        "actualizado_por": None,
        "fecha_actualizacion": None
    }
    
    await db.citas.insert_one(cita_doc)
    if "_id" in cita_doc:
        del cita_doc["_id"]
    
    # Notificar a clientes WebSocket
    await notify_agenda_update("cita_creada", {
        "cita": cita_doc,
        "fecha": cita.fecha,
        "medico_id": cita.medico_id
    })
    
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
    
    update_data["actualizado_por"] = current_user["id"]
    update_data["fecha_actualizacion"] = datetime.now(timezone.utc).isoformat()
    
    await db.citas.update_one({"id": cita_id}, {"$set": update_data})
    
    cita_actualizada = await db.citas.find_one({"id": cita_id}, {"_id": 0})
    
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
    elif estado_data.estado == EstadoCita.EN_CONSULTA:
        update_data["hora_inicio_consulta"] = now.isoformat()
    elif estado_data.estado == EstadoCita.ATENDIDA:
        update_data["hora_fin_consulta"] = now.isoformat()
        update_data["asistio"] = True
    elif estado_data.estado == EstadoCita.NO_ASISTIO:
        update_data["asistio"] = False
    
    await db.citas.update_one({"id": cita_id}, {"$set": update_data})
    
    cita_actualizada = await db.citas.find_one({"id": cita_id}, {"_id": 0})
    
    # Notificar a clientes WebSocket (cambio de estado es importante)
    await notify_agenda_update("cita_estado_cambiado", {
        "cita": cita_actualizada,
        "nuevo_estado": estado_data.estado,
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
    return {"message": "Cita eliminada"}


# ==================== PACIENTES PRESENTES ====================

@router.get("/presentes", response_model=PresentesResponse)
async def listar_presentes(
    fecha: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Listar pacientes presentes en clínica, agrupados por médico"""
    if not fecha:
        fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
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
            "asignado_a_medico_nombre": cita.get("asignado_a_medico_nombre")
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
        fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Pipeline de agregación para contar por estado
    pipeline = [
        {"$match": {"tipo_agenda": "pacientes", "fecha": fecha}},
        {"$group": {"_id": "$estado", "count": {"$sum": 1}}}
    ]
    
    resultados = await db.citas.aggregate(pipeline).to_list(20)
    contadores = {r["_id"]: r["count"] for r in resultados}
    
    # Pipeline para contar por médico
    pipeline_medico = [
        {"$match": {"tipo_agenda": "pacientes", "fecha": fecha}},
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
    current_user: dict = Depends(get_current_user)
):
    """Agenda del día para el médico autenticado"""
    # Buscar si el usuario está vinculado a un médico
    medico = await get_medico_vinculado(current_user["id"])
    
    if not medico and current_user["role"] not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Usuario no vinculado a un médico")
    
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    medico_id = medico["id"] if medico else None
    medico_nombre = medico["name"] if medico else current_user["name"]
    
    # Si es admin sin médico vinculado, mostrar todas las citas
    query = {"tipo_agenda": "pacientes", "fecha": fecha}
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


# ==================== WALK-IN (SIN CITA) ====================

@router.post("/walk-in", response_model=CitaResponse)
async def registrar_walk_in(
    walk_in: WalkInCreate,
    current_user: dict = Depends(get_current_user)
):
    """Registrar paciente que llega sin cita (walk-in)"""
    now = datetime.now(timezone.utc)
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
