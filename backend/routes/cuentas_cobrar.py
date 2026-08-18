# /app/backend/routes/cuentas_cobrar.py
"""
Módulo de Cuentas por Cobrar separado para Óptica y Clínica NovaVision.
- Óptica: CxC asociadas al cliente/paciente de la orden
- Clínica: CxC con responsables configurables (médico, institución, seguro, etc.)
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
import uuid

from routes.auth import get_current_user
from config.database import db

router = APIRouter()


# ==================== MODELOS ====================

class ResponsableCxCBase(BaseModel):
    """Responsable de cuenta por cobrar (médico, institución, seguro, etc.)"""
    nombre: str = Field(..., min_length=1, max_length=200)
    tipo: str = Field(..., description="Tipo: medico, institucion, seguro, convenio, otro")
    nit: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    contacto: Optional[str] = None
    notas: Optional[str] = None
    plazo_dias: int = Field(default=30, ge=0, le=365)


class ResponsableCxCCreate(ResponsableCxCBase):
    pass


class ResponsableCxCResponse(ResponsableCxCBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CxCOpticaCreate(BaseModel):
    """Crear CxC para Óptica - asociada a una orden/venta"""
    venta_id: Optional[str] = None  # Opcional para soportar CxC sin venta previa
    paciente_id: str
    paciente_nombre: str
    monto_total: float = Field(..., ge=0)
    monto_pagado: float = Field(default=0, ge=0)
    concepto: str
    fecha_vencimiento: Optional[str] = None
    notas: Optional[str] = None


class CxCClinicaCreate(BaseModel):
    """Crear CxC para Clínica - con responsable configurable"""
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None
    responsable_id: str = Field(..., description="ID del responsable (médico, institución, etc.)")
    responsable_nombre: Optional[str] = None
    tipo_responsable: Optional[str] = None
    venta_id: Optional[str] = None
    monto_total: float = Field(..., ge=0)
    monto_pagado: float = Field(default=0, ge=0)
    concepto: str
    fecha_vencimiento: Optional[str] = None
    notas: Optional[str] = None


class CxCResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    origen: str  # "optica" o "clinica"
    numero_cuenta: str
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None
    responsable_id: Optional[str] = None
    responsable_nombre: Optional[str] = None
    tipo_responsable: Optional[str] = None
    venta_id: Optional[str] = None
    monto_total: float
    monto_pagado: float = 0
    saldo_pendiente: float
    concepto: str
    estado: str  # "Pendiente", "Parcial", "Pagado", "Vencido", "Anulado"
    fecha_emision: str
    fecha_vencimiento: Optional[str] = None
    notas: Optional[str] = None
    pagos: List[dict] = []
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AbonoCxC(BaseModel):
    """Registrar abono a cuenta por cobrar"""
    monto: float = Field(..., gt=0)
    metodo_pago: str = Field(default="Efectivo")
    referencia: Optional[str] = None
    notas: Optional[str] = None


# ==================== HELPERS ====================

async def generar_numero_cuenta(origen: str) -> str:
    """Genera número de cuenta secuencial"""
    prefijo = "CXC-OPT" if origen == "optica" else "CXC-NOV"
    fecha = datetime.now(timezone.utc).strftime("%Y%m")
    
    # Buscar último número del mes
    ultimo = await db.cuentas_por_cobrar.find_one(
        {"numero_cuenta": {"$regex": f"^{prefijo}-{fecha}"}},
        sort=[("numero_cuenta", -1)]
    )
    
    if ultimo:
        try:
            ultimo_num = int(ultimo["numero_cuenta"].split("-")[-1])
            nuevo_num = ultimo_num + 1
        except:
            nuevo_num = 1
    else:
        nuevo_num = 1
    
    return f"{prefijo}-{fecha}-{nuevo_num:04d}"


def calcular_estado(monto_total: float, monto_pagado: float, fecha_vencimiento: str = None) -> str:
    """Calcula el estado de la cuenta"""
    if monto_pagado >= monto_total:
        return "Pagado"
    
    if fecha_vencimiento:
        try:
            vencimiento = datetime.fromisoformat(fecha_vencimiento.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > vencimiento and monto_pagado < monto_total:
                return "Vencido"
        except:
            pass
    
    if monto_pagado > 0:
        return "Parcial"
    
    return "Pendiente"


# ==================== RESPONSABLES (CLÍNICA) ====================

@router.get("/responsables")
async def listar_responsables(
    tipo: Optional[str] = None,
    search: Optional[str] = None,
    is_active: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Lista responsables de CxC (médicos, instituciones, seguros, etc.)"""
    query = {"is_active": is_active}
    
    if tipo:
        query["tipo"] = tipo
    
    if search:
        query["$or"] = [
            {"nombre": {"$regex": search, "$options": "i"}},
            {"nit": {"$regex": search, "$options": "i"}}
        ]
    
    responsables = await db.responsables_cxc.find(query, {"_id": 0}).sort("nombre", 1).to_list(500)
    return {"data": responsables, "total": len(responsables)}


@router.post("/responsables", response_model=ResponsableCxCResponse)
async def crear_responsable(
    responsable: ResponsableCxCCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nuevo responsable de CxC"""
    now = datetime.now(timezone.utc).isoformat()
    
    responsable_dict = {
        "id": str(uuid.uuid4()),
        **responsable.model_dump(),
        "is_active": True,
        "created_by": current_user.get("id"),
        "created_at": now,
        "updated_at": now
    }
    
    await db.responsables_cxc.insert_one(responsable_dict)
    
    return {k: v for k, v in responsable_dict.items() if k != "_id"}


@router.put("/responsables/{responsable_id}")
async def actualizar_responsable(
    responsable_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar responsable"""
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {k: v for k, v in data.items() if v is not None and k not in ["id", "created_at", "created_by"]}
    update_data["updated_at"] = now
    
    result = await db.responsables_cxc.update_one(
        {"id": responsable_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Responsable no encontrado")
    
    return {"success": True, "message": "Responsable actualizado"}


@router.delete("/responsables/{responsable_id}")
async def desactivar_responsable(
    responsable_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Desactivar responsable (soft delete)"""
    result = await db.responsables_cxc.update_one(
        {"id": responsable_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Responsable no encontrado")
    
    return {"success": True, "message": "Responsable desactivado"}


# ==================== CXC ÓPTICA ====================

@router.get("/optica")
async def listar_cxc_optica(
    estado: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Listar cuentas por cobrar de Óptica"""
    query = {"origen": "optica"}
    
    if estado:
        query["estado"] = estado
    
    if search:
        query["$or"] = [
            {"paciente_nombre": {"$regex": search, "$options": "i"}},
            {"numero_cuenta": {"$regex": search, "$options": "i"}},
            {"concepto": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.cuentas_por_cobrar.count_documents(query)
    cuentas = await db.cuentas_por_cobrar.find(
        query, {"_id": 0}
    ).sort("fecha_emision", -1).skip(offset).limit(limit).to_list(limit)
    
    return {"data": cuentas, "total": total}


@router.get("/optica/resumen")
async def resumen_cxc_optica(
    current_user: dict = Depends(get_current_user)
):
    """Resumen de CxC de Óptica"""
    cuentas = await db.cuentas_por_cobrar.find(
        {"origen": "optica", "estado": {"$ne": "Anulado"}},
        {"_id": 0}
    ).to_list(1000)
    
    total_emitido = sum(c.get("monto_total", 0) for c in cuentas)
    total_cobrado = sum(c.get("monto_pagado", 0) for c in cuentas)
    
    # Por estado
    por_estado = {}
    for c in cuentas:
        estado = c.get("estado", "Pendiente")
        if estado not in por_estado:
            por_estado[estado] = {"cantidad": 0, "monto": 0}
        por_estado[estado]["cantidad"] += 1
        por_estado[estado]["monto"] += c.get("saldo_pendiente", 0)
    
    return {
        "total_emitido": total_emitido,
        "total_cobrado": total_cobrado,
        "saldo_pendiente": total_emitido - total_cobrado,
        "cantidad_cuentas": len(cuentas),
        "por_estado": por_estado
    }


@router.post("/optica", response_model=CxCResponse)
async def crear_cxc_optica(
    cuenta: CxCOpticaCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear cuenta por cobrar de Óptica"""
    now = datetime.now(timezone.utc)
    
    numero = await generar_numero_cuenta("optica")
    saldo = cuenta.monto_total - cuenta.monto_pagado
    estado = calcular_estado(cuenta.monto_total, cuenta.monto_pagado, cuenta.fecha_vencimiento)
    
    cuenta_dict = {
        "id": str(uuid.uuid4()),
        "origen": "optica",
        "numero_cuenta": numero,
        "paciente_id": cuenta.paciente_id,
        "paciente_nombre": cuenta.paciente_nombre,
        "venta_id": cuenta.venta_id,
        "monto_total": cuenta.monto_total,
        "monto_pagado": cuenta.monto_pagado,
        "saldo_pendiente": saldo,
        "concepto": cuenta.concepto,
        "estado": estado,
        "fecha_emision": now.isoformat(),
        "fecha_vencimiento": cuenta.fecha_vencimiento,
        "notas": cuenta.notas,
        "pagos": [],
        "created_by": current_user.get("id"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.cuentas_por_cobrar.insert_one(cuenta_dict)
    
    return {k: v for k, v in cuenta_dict.items() if k != "_id"}


# ==================== CXC CLÍNICA (NOVAVISION) ====================

@router.get("/clinica")
async def listar_cxc_clinica(
    responsable_id: Optional[str] = None,
    tipo_responsable: Optional[str] = None,
    estado: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Listar cuentas por cobrar de Clínica NovaVision"""
    query = {"origen": "clinica"}
    
    if responsable_id:
        query["responsable_id"] = responsable_id
    
    if tipo_responsable:
        query["tipo_responsable"] = tipo_responsable
    
    if estado:
        query["estado"] = estado
    
    if search:
        query["$or"] = [
            {"paciente_nombre": {"$regex": search, "$options": "i"}},
            {"responsable_nombre": {"$regex": search, "$options": "i"}},
            {"numero_cuenta": {"$regex": search, "$options": "i"}},
            {"concepto": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.cuentas_por_cobrar.count_documents(query)
    cuentas = await db.cuentas_por_cobrar.find(
        query, {"_id": 0}
    ).sort("fecha_emision", -1).skip(offset).limit(limit).to_list(limit)
    
    return {"data": cuentas, "total": total}


@router.get("/clinica/resumen")
async def resumen_cxc_clinica(
    current_user: dict = Depends(get_current_user)
):
    """Resumen de CxC de Clínica"""
    cuentas = await db.cuentas_por_cobrar.find(
        {"origen": "clinica", "estado": {"$ne": "Anulado"}},
        {"_id": 0}
    ).to_list(1000)
    
    total_emitido = sum(c.get("monto_total", 0) for c in cuentas)
    total_cobrado = sum(c.get("monto_pagado", 0) for c in cuentas)
    
    # Por tipo de responsable
    por_tipo = {}
    for c in cuentas:
        tipo = c.get("tipo_responsable", "otro")
        if tipo not in por_tipo:
            por_tipo[tipo] = {"cantidad": 0, "emitido": 0, "cobrado": 0, "pendiente": 0}
        por_tipo[tipo]["cantidad"] += 1
        por_tipo[tipo]["emitido"] += c.get("monto_total", 0)
        por_tipo[tipo]["cobrado"] += c.get("monto_pagado", 0)
        por_tipo[tipo]["pendiente"] += c.get("saldo_pendiente", 0)
    
    # Por estado
    por_estado = {}
    for c in cuentas:
        estado = c.get("estado", "Pendiente")
        if estado not in por_estado:
            por_estado[estado] = {"cantidad": 0, "monto": 0}
        por_estado[estado]["cantidad"] += 1
        por_estado[estado]["monto"] += c.get("saldo_pendiente", 0)
    
    return {
        "total_emitido": total_emitido,
        "total_cobrado": total_cobrado,
        "saldo_pendiente": total_emitido - total_cobrado,
        "cantidad_cuentas": len(cuentas),
        "por_tipo": por_tipo,
        "por_estado": por_estado
    }


@router.post("/clinica", response_model=CxCResponse)
async def crear_cxc_clinica(
    cuenta: CxCClinicaCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear cuenta por cobrar de Clínica"""
    now = datetime.now(timezone.utc)
    
    # Obtener datos del responsable
    responsable_nombre = cuenta.responsable_nombre
    tipo_responsable = cuenta.tipo_responsable
    
    if cuenta.responsable_id:
        responsable = await db.responsables_cxc.find_one(
            {"id": cuenta.responsable_id},
            {"_id": 0}
        )
        if responsable:
            responsable_nombre = responsable.get("nombre")
            tipo_responsable = responsable.get("tipo")
    
    numero = await generar_numero_cuenta("clinica")
    saldo = cuenta.monto_total - cuenta.monto_pagado
    estado = calcular_estado(cuenta.monto_total, cuenta.monto_pagado, cuenta.fecha_vencimiento)
    
    cuenta_dict = {
        "id": str(uuid.uuid4()),
        "origen": "clinica",
        "numero_cuenta": numero,
        "paciente_id": cuenta.paciente_id,
        "paciente_nombre": cuenta.paciente_nombre,
        "responsable_id": cuenta.responsable_id,
        "responsable_nombre": responsable_nombre,
        "tipo_responsable": tipo_responsable,
        "venta_id": cuenta.venta_id,
        "monto_total": cuenta.monto_total,
        "monto_pagado": cuenta.monto_pagado,
        "saldo_pendiente": saldo,
        "concepto": cuenta.concepto,
        "estado": estado,
        "fecha_emision": now.isoformat(),
        "fecha_vencimiento": cuenta.fecha_vencimiento,
        "notas": cuenta.notas,
        "pagos": [],
        "created_by": current_user.get("id"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.cuentas_por_cobrar.insert_one(cuenta_dict)
    
    return {k: v for k, v in cuenta_dict.items() if k != "_id"}


# ==================== OPERACIONES COMUNES ====================

@router.get("/{cuenta_id}")
async def obtener_cuenta(
    cuenta_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener detalle de una cuenta por cobrar"""
    cuenta = await db.cuentas_por_cobrar.find_one(
        {"id": cuenta_id},
        {"_id": 0}
    )
    
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    return cuenta


@router.post("/{cuenta_id}/abono")
async def registrar_abono(
    cuenta_id: str,
    abono: AbonoCxC,
    current_user: dict = Depends(get_current_user)
):
    """Registrar abono a cuenta por cobrar"""
    cuenta = await db.cuentas_por_cobrar.find_one({"id": cuenta_id})
    
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    if cuenta.get("estado") in ["Pagado", "Anulado"]:
        raise HTTPException(status_code=400, detail=f"No se puede abonar a cuenta {cuenta.get('estado')}")
    
    saldo_actual = cuenta.get("saldo_pendiente", cuenta.get("monto_total", 0) - cuenta.get("monto_pagado", 0))
    
    if abono.monto > saldo_actual:
        raise HTTPException(status_code=400, detail=f"El abono ({abono.monto}) excede el saldo pendiente ({saldo_actual})")
    
    now = datetime.now(timezone.utc)
    
    # Crear registro de pago
    pago = {
        "id": str(uuid.uuid4()),
        "monto": abono.monto,
        "metodo_pago": abono.metodo_pago,
        "referencia": abono.referencia,
        "notas": abono.notas,
        "fecha": now.isoformat(),
        "registrado_por": current_user.get("id"),
        "registrado_por_nombre": current_user.get("name", current_user.get("username"))
    }
    
    nuevo_pagado = cuenta.get("monto_pagado", 0) + abono.monto
    nuevo_saldo = cuenta.get("monto_total", 0) - nuevo_pagado
    nuevo_estado = calcular_estado(cuenta.get("monto_total", 0), nuevo_pagado, cuenta.get("fecha_vencimiento"))
    
    await db.cuentas_por_cobrar.update_one(
        {"id": cuenta_id},
        {
            "$push": {"pagos": pago},
            "$set": {
                "monto_pagado": nuevo_pagado,
                "saldo_pendiente": nuevo_saldo,
                "estado": nuevo_estado,
                "updated_at": now.isoformat()
            }
        }
    )
    
    # Crear movimiento de caja si es de clínica
    if cuenta.get("origen") == "clinica":
        mov_caja = {
            "id": str(uuid.uuid4()),
            "tipo": "Ingreso",
            "categoria": "Abono CxC",
            "subcategoria": cuenta.get("tipo_responsable", "General"),
            "monto": abono.monto,
            "metodo_pago": abono.metodo_pago,
            "referencia": cuenta.get("numero_cuenta"),
            "descripcion": f"Abono a {cuenta.get('numero_cuenta')} - {cuenta.get('responsable_nombre', cuenta.get('paciente_nombre'))}",
            "fecha": now.isoformat(),
            "usuario_id": current_user.get("id"),
            "usuario_nombre": current_user.get("name", current_user.get("username")),
            "origen": "clinica",
            "cxc_id": cuenta_id
        }
        await db.caja_movimientos.insert_one(mov_caja)
    
    return {
        "success": True,
        "message": "Abono registrado exitosamente",
        "pago": pago,
        "nuevo_saldo": nuevo_saldo,
        "nuevo_estado": nuevo_estado
    }


@router.put("/{cuenta_id}/anular")
async def anular_cuenta(
    cuenta_id: str,
    motivo: str = Query(..., min_length=5),
    current_user: dict = Depends(get_current_user)
):
    """Anular cuenta por cobrar"""
    cuenta = await db.cuentas_por_cobrar.find_one({"id": cuenta_id})
    
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    if cuenta.get("monto_pagado", 0) > 0:
        raise HTTPException(status_code=400, detail="No se puede anular una cuenta con pagos registrados")
    
    now = datetime.now(timezone.utc)
    
    await db.cuentas_por_cobrar.update_one(
        {"id": cuenta_id},
        {"$set": {
            "estado": "Anulado",
            "motivo_anulacion": motivo,
            "anulado_por": current_user.get("id"),
            "anulado_por_nombre": current_user.get("name", current_user.get("username")),
            "fecha_anulacion": now.isoformat(),
            "updated_at": now.isoformat()
        }}
    )
    
    return {"success": True, "message": "Cuenta anulada"}


@router.get("/tipos-responsable/lista")
async def listar_tipos_responsable():
    """Lista los tipos de responsable disponibles"""
    return {
        "tipos": [
            {"value": "medico", "label": "Médico", "descripcion": "Médico referente o tratante"},
            {"value": "institucion", "label": "Institución", "descripcion": "Hospital, clínica, laboratorio"},
            {"value": "seguro", "label": "Seguro", "descripcion": "Compañía de seguros"},
            {"value": "convenio", "label": "Convenio", "descripcion": "Convenio empresarial"},
            {"value": "igss", "label": "IGSS", "descripcion": "Instituto Guatemalteco de Seguridad Social"},
            {"value": "otro", "label": "Otro", "descripcion": "Otro tipo de responsable"}
        ]
    }
