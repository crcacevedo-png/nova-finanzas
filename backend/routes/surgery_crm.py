# /app/backend/routes/surgery_crm.py
# Módulo CRM de Cirugías - Gestión de pacientes interesados en cirugía

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from routes.auth import get_current_user, require_permission
from config.database import db

router = APIRouter(prefix="/surgery-crm", tags=["CRM Cirugías"])


# ==================== MODELOS ====================

class SurgeryCandidateBase(BaseModel):
    """Modelo base para candidato a cirugía"""
    paciente_id: str
    paciente_nombre: str
    paciente_telefono: Optional[str] = None
    paciente_email: Optional[str] = None
    tipo_cirugia: str  # Catarata, Pterigión, Glaucoma, etc.
    ojo: str = "OU"  # OD, OS, OU
    diagnostico: Optional[str] = None
    prioridad: str = "normal"  # alta, normal, baja
    notas: Optional[str] = None
    origen: str = "manual"  # manual, evaluacion
    evaluacion_id: Optional[str] = None  # Si viene de evaluación oftalmológica


class SurgeryCandidateCreate(SurgeryCandidateBase):
    pass


class SurgeryCandidateUpdate(BaseModel):
    tipo_cirugia: Optional[str] = None
    ojo: Optional[str] = None
    diagnostico: Optional[str] = None
    prioridad: Optional[str] = None
    notas: Optional[str] = None
    estado: Optional[str] = None  # pendiente, contactado, programado, operado, descartado
    fecha_contacto: Optional[str] = None
    fecha_programada: Optional[str] = None
    motivo_descarte: Optional[str] = None


class FollowUpCreate(BaseModel):
    """Modelo para seguimiento/contacto"""
    tipo: str  # llamada, whatsapp, email, presencial
    notas: str
    resultado: str  # interesado, no_contesta, reprogramar, no_interesado
    proxima_accion: Optional[str] = None
    fecha_proxima_accion: Optional[str] = None


class SurgeryCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    paciente_id: str
    paciente_nombre: str
    paciente_telefono: Optional[str] = None
    paciente_email: Optional[str] = None
    tipo_cirugia: str
    ojo: str
    diagnostico: Optional[str] = None
    prioridad: str
    notas: Optional[str] = None
    origen: str
    evaluacion_id: Optional[str] = None
    estado: str = "pendiente"
    fecha_contacto: Optional[str] = None
    fecha_programada: Optional[str] = None
    motivo_descarte: Optional[str] = None
    seguimientos: List[dict] = []
    created_by: str
    created_by_name: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class SurgeryCRMListResponse(BaseModel):
    data: List[SurgeryCandidateResponse]
    total: int
    page: int
    limit: int
    stats: dict


# ==================== HELPERS ====================

async def enrich_candidate(candidate: dict) -> dict:
    """Enriquecer candidato con datos adicionales"""
    if candidate.get("created_by"):
        user = await db.users.find_one({"id": candidate["created_by"]}, {"_id": 0, "name": 1})
        candidate["created_by_name"] = user.get("name") if user else None
    return candidate


# ==================== RUTAS ====================

@router.get("", response_model=SurgeryCRMListResponse)
async def get_surgery_candidates(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    estado: Optional[str] = None,
    tipo_cirugia: Optional[str] = None,
    prioridad: Optional[str] = None,
    origen: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Listar candidatos a cirugía con filtros"""
    query = {}
    
    if search:
        query["$or"] = [
            {"paciente_nombre": {"$regex": search, "$options": "i"}},
            {"diagnostico": {"$regex": search, "$options": "i"}},
            {"tipo_cirugia": {"$regex": search, "$options": "i"}}
        ]
    
    if estado:
        query["estado"] = estado
    
    if tipo_cirugia:
        query["tipo_cirugia"] = tipo_cirugia
    
    if prioridad:
        query["prioridad"] = prioridad
    
    if origen:
        query["origen"] = origen
    
    total = await db.surgery_crm.count_documents(query)
    skip = (page - 1) * limit
    
    # Ordenar por prioridad y fecha
    cursor = db.surgery_crm.find(query, {"_id": 0}).sort([
        ("prioridad", 1),  # alta primero
        ("created_at", -1)
    ]).skip(skip).limit(limit)
    
    candidates = await cursor.to_list(length=limit)
    enriched = [await enrich_candidate(c) for c in candidates]
    
    # Calcular estadísticas
    stats_pipeline = [
        {"$group": {
            "_id": "$estado",
            "count": {"$sum": 1}
        }}
    ]
    stats_cursor = db.surgery_crm.aggregate(stats_pipeline)
    stats_list = await stats_cursor.to_list(length=100)
    
    stats = {
        "pendiente": 0,
        "contactado": 0,
        "programado": 0,
        "operado": 0,
        "descartado": 0
    }
    for s in stats_list:
        if s["_id"] in stats:
            stats[s["_id"]] = s["count"]
    
    stats["total"] = sum(stats.values())
    
    return SurgeryCRMListResponse(
        data=enriched,
        total=total,
        page=page,
        limit=limit,
        stats=stats
    )


@router.get("/stats")
async def get_crm_stats(current_user: dict = Depends(get_current_user)):
    """Obtener estadísticas del CRM"""
    # Por estado
    estado_pipeline = [
        {"$group": {"_id": "$estado", "count": {"$sum": 1}}}
    ]
    estados = await db.surgery_crm.aggregate(estado_pipeline).to_list(100)
    
    # Por tipo de cirugía
    tipo_pipeline = [
        {"$group": {"_id": "$tipo_cirugia", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    tipos = await db.surgery_crm.aggregate(tipo_pipeline).to_list(100)
    
    # Por prioridad
    prioridad_pipeline = [
        {"$group": {"_id": "$prioridad", "count": {"$sum": 1}}}
    ]
    prioridades = await db.surgery_crm.aggregate(prioridad_pipeline).to_list(100)
    
    # Por origen
    origen_pipeline = [
        {"$group": {"_id": "$origen", "count": {"$sum": 1}}}
    ]
    origenes = await db.surgery_crm.aggregate(origen_pipeline).to_list(100)
    
    return {
        "por_estado": {s["_id"]: s["count"] for s in estados if s["_id"]},
        "por_tipo_cirugia": {t["_id"]: t["count"] for t in tipos if t["_id"]},
        "por_prioridad": {p["_id"]: p["count"] for p in prioridades if p["_id"]},
        "por_origen": {o["_id"]: o["count"] for o in origenes if o["_id"]}
    }


@router.get("/tipos-cirugia")
async def get_surgery_types(current_user: dict = Depends(get_current_user)):
    """Obtener tipos de cirugía disponibles"""
    tipos = await db.surgery_crm.distinct("tipo_cirugia")
    
    # Tipos predefinidos + los existentes
    tipos_default = [
        "Catarata",
        "Pterigión",
        "Glaucoma",
        "Estrabismo",
        "Vitrectomía",
        "Desprendimiento de Retina",
        "Trasplante de Córnea",
        "LASIK/PRK",
        "Blefaroplastia",
        "Chalazión",
        "Otros"
    ]
    
    all_tipos = list(set(tipos_default + [t for t in tipos if t]))
    return sorted(all_tipos)


@router.get("/{candidate_id}", response_model=SurgeryCandidateResponse)
async def get_surgery_candidate(
    candidate_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener detalle de un candidato"""
    candidate = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    enriched = await enrich_candidate(candidate)
    return SurgeryCandidateResponse(**enriched)


@router.post("", response_model=SurgeryCandidateResponse)
async def create_surgery_candidate(
    candidate: SurgeryCandidateCreate,
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Crear nuevo candidato a cirugía"""
    # Verificar si el paciente existe
    paciente = await db.patients.find_one({"id": candidate.paciente_id}, {"_id": 0})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Verificar si ya existe un registro activo para este paciente y tipo de cirugía
    existing = await db.surgery_crm.find_one({
        "paciente_id": candidate.paciente_id,
        "tipo_cirugia": candidate.tipo_cirugia,
        "estado": {"$nin": ["operado", "descartado"]}
    })
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un registro activo para este paciente con {candidate.tipo_cirugia}"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    candidate_doc = {
        "id": str(uuid.uuid4()),
        **candidate.model_dump(),
        "paciente_nombre": paciente.get("nombre_completo") or candidate.paciente_nombre,
        "paciente_telefono": paciente.get("phone") or candidate.paciente_telefono,
        "paciente_email": paciente.get("email") or candidate.paciente_email,
        "estado": "pendiente",
        "seguimientos": [],
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.surgery_crm.insert_one(candidate_doc)
    
    created = await db.surgery_crm.find_one({"id": candidate_doc["id"]}, {"_id": 0})
    enriched = await enrich_candidate(created)
    return SurgeryCandidateResponse(**enriched)


@router.put("/{candidate_id}", response_model=SurgeryCandidateResponse)
async def update_surgery_candidate(
    candidate_id: str,
    update_data: SurgeryCandidateUpdate,
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Actualizar candidato a cirugía"""
    candidate = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.surgery_crm.update_one({"id": candidate_id}, {"$set": update_dict})
    
    updated = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    enriched = await enrich_candidate(updated)
    return SurgeryCandidateResponse(**enriched)


@router.post("/{candidate_id}/seguimiento", response_model=SurgeryCandidateResponse)
async def add_followup(
    candidate_id: str,
    followup: FollowUpCreate,
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Agregar seguimiento a un candidato"""
    candidate = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    seguimiento = {
        "id": str(uuid.uuid4()),
        **followup.model_dump(),
        "fecha": now,
        "usuario_id": current_user["id"],
        "usuario_nombre": current_user.get("name", "")
    }
    
    # Actualizar estado basado en resultado
    nuevo_estado = candidate.get("estado", "pendiente")
    if followup.resultado == "interesado":
        nuevo_estado = "contactado"
    elif followup.resultado == "no_interesado":
        nuevo_estado = "descartado"
    
    await db.surgery_crm.update_one(
        {"id": candidate_id},
        {
            "$push": {"seguimientos": seguimiento},
            "$set": {
                "estado": nuevo_estado,
                "fecha_contacto": now,
                "updated_at": now
            }
        }
    )
    
    updated = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    enriched = await enrich_candidate(updated)
    return SurgeryCandidateResponse(**enriched)


@router.post("/{candidate_id}/programar", response_model=SurgeryCandidateResponse)
async def schedule_surgery(
    candidate_id: str,
    fecha_programada: str = Body(..., embed=True),
    notas: str = Body("", embed=True),
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Programar cirugía para un candidato"""
    candidate = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.surgery_crm.update_one(
        {"id": candidate_id},
        {"$set": {
            "estado": "programado",
            "fecha_programada": fecha_programada,
            "notas": f"{candidate.get('notas', '')}\n[Programado] {notas}".strip(),
            "updated_at": now
        }}
    )
    
    updated = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    enriched = await enrich_candidate(updated)
    return SurgeryCandidateResponse(**enriched)


@router.post("/{candidate_id}/marcar-operado", response_model=SurgeryCandidateResponse)
async def mark_as_operated(
    candidate_id: str,
    notas: str = Body("", embed=True),
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Marcar candidato como operado"""
    candidate = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.surgery_crm.update_one(
        {"id": candidate_id},
        {"$set": {
            "estado": "operado",
            "notas": f"{candidate.get('notas', '')}\n[Operado] {notas}".strip(),
            "updated_at": now
        }}
    )
    
    updated = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    enriched = await enrich_candidate(updated)
    return SurgeryCandidateResponse(**enriched)


@router.post("/{candidate_id}/descartar", response_model=SurgeryCandidateResponse)
async def discard_candidate(
    candidate_id: str,
    motivo: str = Body(..., embed=True),
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Descartar candidato"""
    candidate = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.surgery_crm.update_one(
        {"id": candidate_id},
        {"$set": {
            "estado": "descartado",
            "motivo_descarte": motivo,
            "updated_at": now
        }}
    )
    
    updated = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    enriched = await enrich_candidate(updated)
    return SurgeryCandidateResponse(**enriched)


@router.delete("/{candidate_id}")
async def delete_surgery_candidate(
    candidate_id: str,
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Eliminar candidato (solo si está descartado)"""
    candidate = await db.surgery_crm.find_one({"id": candidate_id}, {"_id": 0})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    if candidate.get("estado") not in ["descartado", "operado"]:
        raise HTTPException(
            status_code=400, 
            detail="Solo se pueden eliminar candidatos descartados u operados"
        )
    
    await db.surgery_crm.delete_one({"id": candidate_id})
    return {"message": "Candidato eliminado correctamente"}


# Exportar para uso externo
__all__ = ['router']
