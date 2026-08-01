# /app/backend/routes/evaluaciones.py
# Módulo de Evaluaciones Oftalmológicas - CRUD y catálogos

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid
import re

from config.database import db
from routes.auth import get_current_user, require_role

from models.evaluacion_oftalmologica import (
    EvaluacionOftalmologicaCreate,
    EvaluacionOftalmologicaUpdate,
    EvaluacionOftalmologicaResponse,
    EvaluacionOftalmologicaListResponse,
    CatalogoItemResponse
)

router = APIRouter(prefix="/evaluaciones", tags=["Evaluaciones Oftalmológicas"])
catalogos_router = APIRouter(prefix="/catalogos", tags=["Catálogos - Evaluaciones"])

# Tiempo límite para sellado (24 horas)
SELLADO_HORAS = 24


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
    """Verifica si una evaluación debe estar sellada"""
    if evaluacion.get("sellado", False):
        return True, "Expediente sellado"
    
    fecha_creacion = evaluacion.get("fecha_creacion", "")
    if fecha_creacion:
        try:
            creacion = datetime.fromisoformat(fecha_creacion.replace("Z", "+00:00"))
            ahora = datetime.now(timezone.utc)
            if (ahora - creacion).total_seconds() > SELLADO_HORAS * 3600:
                return True, "Expediente sellado por tiempo (24h)"
        except Exception:
            pass
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


@router.post("", response_model=EvaluacionOftalmologicaResponse)
async def create_evaluacion(
    evaluacion: EvaluacionOftalmologicaCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nueva evaluación (solo Admin y SuperAdmin)"""
    if current_user["role"] not in ["superadmin", "admin"]:
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
        evaluacion_dict["fecha"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    await db.evaluaciones_oftalmologicas.insert_one(evaluacion_dict)
    
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


@router.put("/{evaluacion_id}", response_model=EvaluacionOftalmologicaResponse)
async def update_evaluacion(
    evaluacion_id: str,
    evaluacion: EvaluacionOftalmologicaUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar evaluación (solo Admin y SuperAdmin, solo si no está sellada)"""
    if current_user["role"] not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para editar evaluaciones")
    
    existing = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
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
    
    updated = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    return updated


@router.patch("/{evaluacion_id}/autoguardar", response_model=EvaluacionOftalmologicaResponse)
async def autoguardar_evaluacion(
    evaluacion_id: str,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Autoguardado parcial de evaluación (solo si no está sellada)"""
    if current_user["role"] not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para editar evaluaciones")
    
    existing = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
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
        "diagnosticos", "plan", "recomendaciones", "procedimientos", "recetas"
    ]
    
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
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
