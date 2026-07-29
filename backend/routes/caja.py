# /app/backend/routes/caja.py
# Módulo de Caja - Área Clínica
# IMPORTANTE: Este módulo está AISLADO del módulo de óptica.
# Todos los movimientos y cierres filtran por origen="clinica"

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from models.caja import (
    CajaMovimientoCreate, CajaMovimientoUpdate, CajaMovimientoResponse, CajaMovimientoListResponse,
    CajaCierreApertura, CajaCierreRequest, CajaCierreResponse, CajaEstadoResponse, TotalesPorMetodo,
    PagadorCreate, PagadorUpdate, PagadorResponse,
    CuentaCobrarCreate, CuentaCobrarUpdate, CuentaCobrarResponse, CuentaCobrarListResponse,
    AbonoCreate, Abono, ResumenCxCResponse, ResumenCxCPorTipo,
    CierreFinancieroCreate, CierreFinancieroUpdate, CierreFinancieroResponse, CierreFinancieroListResponse,
    ResumenCxCFinanciero
)

# Importar dependencias directamente
from config.database import db
from routes.auth import get_current_user, require_permission, require_role

# Router principal
router = APIRouter(prefix="/caja", tags=["Caja"])
# Router para catálogos de pagadores
catalogos_router = APIRouter(prefix="/catalogos", tags=["Catálogos"])
# Router para CxC
cxc_router = APIRouter(prefix="/cxc", tags=["Cuentas por Cobrar"])
# Router para cierres financieros
cierres_financieros_router = APIRouter(prefix="/cierres-financieros", tags=["Cierres Financieros"])

# Variable para audit logger (se inyecta desde server.py)
audit_logger = None

def init_caja_routes(log_action_func):
    """Inicializa el logger de auditoría"""
    global audit_logger
    audit_logger = log_action_func


# ==================== HELPERS ====================

async def calcular_totales_caja_dia(fecha_dia: str) -> dict:
    """Calcula totales del día para la caja clínica"""
    inicio = f"{fecha_dia}T00:00:00"
    fin = f"{fecha_dia}T23:59:59"
    
    movimientos = await db.caja_movimientos.find({
        "origen": "clinica",
        "fecha": {"$gte": inicio, "$lte": fin}
    }, {"_id": 0}).to_list(1000)
    
    totales = {
        "total_ingresos": 0, "total_egresos": 0,
        "ingresos": {"efectivo": 0, "tarjeta": 0, "transferencia": 0, "cheque": 0},
        "egresos": {"efectivo": 0, "tarjeta": 0, "transferencia": 0, "cheque": 0}
    }
    
    for mov in movimientos:
        metodo = mov.get("metodo_pago", "Efectivo").lower()
        if mov["tipo"] == "Ingreso":
            totales["total_ingresos"] += mov["monto"]
            if metodo in totales["ingresos"]:
                totales["ingresos"][metodo] += mov["monto"]
        else:
            totales["total_egresos"] += mov["monto"]
            if metodo in totales["egresos"]:
                totales["egresos"][metodo] += mov["monto"]
    
    return totales


# ==================== ESTADO DE CAJA ====================

@router.get("/estado", response_model=CajaEstadoResponse)
async def get_caja_estado(
    fecha: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Obtener estado de la caja del día"""
    fecha_hoy = fecha or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    cierre = await db.caja_cierres.find_one({
        "fecha": fecha_hoy,
        "origen": "clinica"
    }, {"_id": 0})
    
    totales = await calcular_totales_caja_dia(fecha_hoy)
    
    # Calcular saldo efectivo vivo
    saldo_efectivo = 0
    if cierre:
        saldo_efectivo = cierre.get("monto_apertura", 0) + totales["ingresos"]["efectivo"] - totales["egresos"]["efectivo"]
    
    return {
        "caja_abierta": cierre is not None and cierre.get("estado") == "Abierto",
        "cierre": cierre,
        "totales_dia": totales,
        "saldo_efectivo_vivo": saldo_efectivo
    }


# ==================== APERTURA DE CAJA ====================

@router.post("/apertura", response_model=CajaCierreResponse)
async def abrir_caja(
    apertura: CajaCierreApertura,
    current_user: dict = Depends(get_current_user)
):
    """Abrir caja del día"""
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc)
    
    # Verificar que no existe caja abierta para hoy
    existing = await db.caja_cierres.find_one({
        "fecha": fecha_hoy,
        "origen": "clinica"
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una caja para el día de hoy")
    
    cierre = {
        "id": str(uuid.uuid4()),
        "fecha": fecha_hoy,
        "origen": "clinica",
        "estado": "Abierto",
        "monto_apertura": apertura.monto_apertura,
        "total_ingresos": 0,
        "total_egresos": 0,
        "saldo_esperado_efectivo": apertura.monto_apertura,
        "efectivo_contado": None,
        "diferencia": None,
        "observaciones": None,
        "abierto_por": current_user["id"],
        "abierto_por_nombre": current_user["name"],
        "fecha_apertura": now.isoformat(),
        "cerrado_por": None,
        "cerrado_por_nombre": None,
        "fecha_cierre": None
    }
    
    await db.caja_cierres.insert_one(cierre)
    
    if audit_logger:
        await audit_logger(
            current_user["id"],
            "CAJA_APERTURA",
            "caja_cierres",
            cierre["id"],
            details={"fecha": fecha_hoy, "monto_apertura": apertura.monto_apertura}
        )
    
    if "_id" in cierre:
        del cierre["_id"]
    return cierre


# ==================== MOVIMIENTOS DE CAJA ====================

@router.get("/movimientos", response_model=CajaMovimientoListResponse)
async def get_movimientos(
    fecha: Optional[str] = None,
    tipo: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Listar movimientos del día"""
    fecha_hoy = fecha or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    inicio = f"{fecha_hoy}T00:00:00"
    fin = f"{fecha_hoy}T23:59:59"
    
    query = {
        "origen": "clinica",
        "fecha": {"$gte": inicio, "$lte": fin}
    }
    if tipo:
        query["tipo"] = tipo
    
    total = await db.caja_movimientos.count_documents(query)
    movimientos = await db.caja_movimientos.find(
        query, {"_id": 0}
    ).sort("fecha", -1).skip(offset).limit(limit).to_list(limit)
    
    return {"data": movimientos, "total": total}


@router.post("/movimientos", response_model=CajaMovimientoResponse)
async def crear_movimiento(
    movimiento: CajaMovimientoCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nuevo movimiento de caja"""
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc)
    
    # Verificar que la caja está abierta
    cierre = await db.caja_cierres.find_one({
        "fecha": fecha_hoy,
        "origen": "clinica",
        "estado": "Abierto"
    })
    if not cierre:
        raise HTTPException(status_code=400, detail="La caja del día no está abierta")
    
    mov_dict = {
        "id": str(uuid.uuid4()),
        "origen": "clinica",
        "fecha": now.isoformat(),
        "tipo": movimiento.tipo,
        "categoria": movimiento.categoria,
        "concepto": movimiento.concepto,
        "monto": movimiento.monto,
        "metodo_pago": movimiento.metodo_pago,
        "referencia": movimiento.referencia,
        "paciente_id": movimiento.paciente_id,
        "paciente_nombre": movimiento.paciente_nombre,
        "bloqueado": False,
        "cajero_id": current_user["id"],
        "cajero_nombre": current_user["name"],
        "creado_por": current_user["id"],
        "creado_por_nombre": current_user["name"],
        "fecha_creacion": now.isoformat()
    }
    
    await db.caja_movimientos.insert_one(mov_dict)
    
    if "_id" in mov_dict:
        del mov_dict["_id"]
    return mov_dict


@router.put("/movimientos/{movimiento_id}", response_model=CajaMovimientoResponse)
async def actualizar_movimiento(
    movimiento_id: str,
    movimiento: CajaMovimientoUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar movimiento existente"""
    existing = await db.caja_movimientos.find_one({"id": movimiento_id, "origen": "clinica"}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if existing.get("bloqueado"):
        raise HTTPException(status_code=400, detail="No se puede modificar un movimiento bloqueado")
    
    update_data = {k: v for k, v in movimiento.model_dump().items() if v is not None}
    update_data["modificado_por"] = current_user["id"]
    update_data["fecha_modificacion"] = datetime.now(timezone.utc).isoformat()
    
    await db.caja_movimientos.update_one({"id": movimiento_id}, {"$set": update_data})
    updated = await db.caja_movimientos.find_one({"id": movimiento_id}, {"_id": 0})
    return updated


@router.delete("/movimientos/{movimiento_id}")
async def eliminar_movimiento(
    movimiento_id: str,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Eliminar movimiento (solo SuperAdmin)"""
    existing = await db.caja_movimientos.find_one({"id": movimiento_id, "origen": "clinica"}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if existing.get("bloqueado"):
        raise HTTPException(status_code=400, detail="No se puede eliminar un movimiento bloqueado")
    
    await db.caja_movimientos.delete_one({"id": movimiento_id})
    return {"message": "Movimiento eliminado"}


# ==================== CIERRE DIARIO ====================

@router.post("/cierre", response_model=CajaCierreResponse)
async def cerrar_caja(
    cierre_req: CajaCierreRequest,
    current_user: dict = Depends(get_current_user)
):
    """Cerrar caja del día"""
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc)
    
    cierre = await db.caja_cierres.find_one({
        "fecha": fecha_hoy,
        "origen": "clinica",
        "estado": "Abierto"
    })
    if not cierre:
        raise HTTPException(status_code=400, detail="No hay caja abierta para cerrar")
    
    # Calcular totales
    totales = await calcular_totales_caja_dia(fecha_hoy)
    
    # Calcular saldo esperado en efectivo
    saldo_esperado = cierre["monto_apertura"] + totales["ingresos"]["efectivo"] - totales["egresos"]["efectivo"]
    diferencia = cierre_req.efectivo_contado - saldo_esperado
    
    # Actualizar cierre
    update_data = {
        "estado": "Cerrado",
        "total_ingresos": totales["total_ingresos"],
        "total_egresos": totales["total_egresos"],
        "saldo_esperado_efectivo": saldo_esperado,
        "efectivo_contado": cierre_req.efectivo_contado,
        "diferencia": diferencia,
        "observaciones": cierre_req.observaciones,
        "cerrado_por": current_user["id"],
        "cerrado_por_nombre": current_user["name"],
        "fecha_cierre": now.isoformat()
    }
    
    await db.caja_cierres.update_one({"id": cierre["id"]}, {"$set": update_data})
    
    # Bloquear todos los movimientos del día
    await db.caja_movimientos.update_many(
        {"origen": "clinica", "fecha": {"$gte": f"{fecha_hoy}T00:00:00", "$lte": f"{fecha_hoy}T23:59:59"}},
        {"$set": {"bloqueado": True}}
    )
    
    if audit_logger:
        await audit_logger(
            current_user["id"],
            "CAJA_CIERRE",
            "caja_cierres",
            cierre["id"],
            details={"fecha": fecha_hoy, "diferencia": diferencia}
        )
    
    updated = await db.caja_cierres.find_one({"id": cierre["id"]}, {"_id": 0})
    return updated


@router.get("/cierres")
async def get_historial_cierres(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Obtener historial de cierres"""
    total = await db.caja_cierres.count_documents({"origen": "clinica"})
    cierres = await db.caja_cierres.find(
        {"origen": "clinica"}, {"_id": 0}
    ).sort("fecha", -1).skip(offset).limit(limit).to_list(limit)
    
    return {"data": cierres, "total": total}


@router.get("/cierres/{cierre_id}", response_model=CajaCierreResponse)
async def get_cierre(
    cierre_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener detalle de un cierre"""
    cierre = await db.caja_cierres.find_one({"id": cierre_id, "origen": "clinica"}, {"_id": 0})
    if not cierre:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    return cierre


@router.post("/cierres/{cierre_id}/reabrir")
async def reabrir_caja(
    cierre_id: str,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Reabrir un cierre de caja (solo SuperAdmin)"""
    cierre = await db.caja_cierres.find_one({"id": cierre_id, "origen": "clinica"}, {"_id": 0})
    if not cierre:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    if cierre.get("estado") == "Abierto":
        raise HTTPException(status_code=400, detail="La caja ya está abierta")
    
    # Reabrir
    await db.caja_cierres.update_one(
        {"id": cierre_id},
        {"$set": {
            "estado": "Abierto",
            "efectivo_contado": None,
            "diferencia": None,
            "cerrado_por": None,
            "cerrado_por_nombre": None,
            "fecha_cierre": None
        }}
    )
    
    # Desbloquear movimientos del día
    await db.caja_movimientos.update_many(
        {"origen": "clinica", "fecha": {"$gte": f"{cierre['fecha']}T00:00:00", "$lte": f"{cierre['fecha']}T23:59:59"}},
        {"$set": {"bloqueado": False}}
    )
    
    if audit_logger:
        await audit_logger(
            current_user["id"],
            "CAJA_REABRIR",
            "caja_cierres",
            cierre_id,
            details={"fecha": cierre["fecha"]}
        )
    
    return {"message": "Caja reabierta exitosamente"}


# ==================== CATÁLOGO DE PAGADORES ====================

@catalogos_router.get("/pagadores")
async def get_pagadores(
    current_user: dict = Depends(get_current_user)
):
    """Listar tipos de pagador"""
    pagadores = await db.catalogo_pagadores.find(
        {"origen": "clinica"}, {"_id": 0}
    ).sort("nombre", 1).to_list(100)
    return pagadores


@catalogos_router.post("/pagadores", response_model=PagadorResponse)
async def crear_pagador(
    pagador: PagadorCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nuevo tipo de pagador"""
    now = datetime.now(timezone.utc)
    
    pagador_dict = {
        "id": str(uuid.uuid4()),
        "origen": "clinica",
        "nombre": pagador.nombre,
        "activo": True,
        "fecha_creacion": now.isoformat(),
        "creado_por": current_user["id"]
    }
    
    await db.catalogo_pagadores.insert_one(pagador_dict)
    if "_id" in pagador_dict:
        del pagador_dict["_id"]
    return pagador_dict


@catalogos_router.put("/pagadores/{pagador_id}", response_model=PagadorResponse)
async def actualizar_pagador(
    pagador_id: str,
    pagador: PagadorUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar tipo de pagador"""
    existing = await db.catalogo_pagadores.find_one({"id": pagador_id, "origen": "clinica"}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Pagador no encontrado")
    
    update_data = {k: v for k, v in pagador.model_dump().items() if v is not None}
    await db.catalogo_pagadores.update_one({"id": pagador_id}, {"$set": update_data})
    updated = await db.catalogo_pagadores.find_one({"id": pagador_id}, {"_id": 0})
    return updated


@catalogos_router.delete("/pagadores/{pagador_id}")
async def eliminar_pagador(
    pagador_id: str,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Eliminar tipo de pagador (solo SuperAdmin)"""
    existing = await db.catalogo_pagadores.find_one({"id": pagador_id, "origen": "clinica"}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Pagador no encontrado")
    
    await db.catalogo_pagadores.delete_one({"id": pagador_id})
    return {"message": "Pagador eliminado"}


# ==================== CUENTAS POR COBRAR ====================

@cxc_router.get("", response_model=CuentaCobrarListResponse)
async def get_cuentas_cobrar(
    tipo_pagador: Optional[str] = None,
    estado: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Listar cuentas por cobrar"""
    query = {"origen": "clinica"}
    if tipo_pagador:
        query["tipo_pagador_id"] = tipo_pagador
    if estado:
        query["estado"] = estado
    if search:
        query["$or"] = [
            {"paciente_nombre": {"$regex": search, "$options": "i"}},
            {"concepto": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.cuentas_por_cobrar.count_documents(query)
    cuentas = await db.cuentas_por_cobrar.find(
        query, {"_id": 0}
    ).sort("fecha_emision", -1).skip(offset).limit(limit).to_list(limit)
    
    return {"data": cuentas, "total": total}


@cxc_router.get("/resumen", response_model=ResumenCxCResponse)
async def get_resumen_cxc(
    current_user: dict = Depends(get_current_user)
):
    """Obtener resumen de cuentas por cobrar"""
    cuentas = await db.cuentas_por_cobrar.find(
        {"origen": "clinica", "estado": {"$ne": "Cancelado"}},
        {"_id": 0}
    ).to_list(1000)
    
    total_emitido = sum(c.get("monto_total", 0) for c in cuentas)
    total_cobrado = sum(c.get("monto_pagado", 0) for c in cuentas)
    saldo_pendiente = total_emitido - total_cobrado
    
    # Agrupar por tipo de pagador
    por_tipo = {}
    for c in cuentas:
        tipo_id = c.get("tipo_pagador_id", "otro")
        tipo_nombre = c.get("tipo_pagador_nombre", "Otro")
        if tipo_id not in por_tipo:
            por_tipo[tipo_id] = {"tipo_pagador_id": tipo_id, "tipo_pagador_nombre": tipo_nombre, "emitido": 0, "cobrado": 0, "pendiente": 0}
        por_tipo[tipo_id]["emitido"] += c.get("monto_total", 0)
        por_tipo[tipo_id]["cobrado"] += c.get("monto_pagado", 0)
        por_tipo[tipo_id]["pendiente"] += c.get("saldo_pendiente", 0)
    
    return {
        "total_emitido": total_emitido,
        "total_cobrado": total_cobrado,
        "saldo_pendiente": saldo_pendiente,
        "cantidad_cuentas": len(cuentas),
        "por_tipo": list(por_tipo.values())
    }


@cxc_router.post("", response_model=CuentaCobrarResponse)
async def crear_cuenta_cobrar(
    cuenta: CuentaCobrarCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nueva cuenta por cobrar"""
    now = datetime.now(timezone.utc)
    
    # Obtener nombre del tipo de pagador si no viene
    tipo_pagador_nombre = cuenta.tipo_pagador_nombre
    if not tipo_pagador_nombre and cuenta.tipo_pagador_id:
        pagador = await db.catalogo_pagadores.find_one({"id": cuenta.tipo_pagador_id}, {"_id": 0})
        if pagador:
            tipo_pagador_nombre = pagador["nombre"]
    
    cuenta_dict = {
        "id": str(uuid.uuid4()),
        "origen": "clinica",
        "paciente_id": cuenta.paciente_id,
        "paciente_nombre": cuenta.paciente_nombre,
        "tipo_pagador_id": cuenta.tipo_pagador_id,
        "tipo_pagador_nombre": tipo_pagador_nombre,
        "pagador_nombre": cuenta.pagador_nombre,
        "concepto": cuenta.concepto,
        "referencia": cuenta.referencia,
        "monto_total": cuenta.monto_total,
        "monto_pagado": 0,
        "saldo_pendiente": cuenta.monto_total,
        "estado": "Pendiente",
        "fecha_emision": now.strftime("%Y-%m-%d"),
        "fecha_vencimiento": cuenta.fecha_vencimiento,
        "notas": cuenta.notas,
        "abonos": [],
        "creado_por": current_user["id"],
        "creado_por_nombre": current_user["name"]
    }
    cuenta_dict["fecha_creacion"] = now.isoformat()
    
    await db.cuentas_por_cobrar.insert_one(cuenta_dict)
    
    if "_id" in cuenta_dict:
        del cuenta_dict["_id"]
    return cuenta_dict


@cxc_router.get("/{cuenta_id}", response_model=CuentaCobrarResponse)
async def get_cuenta_cobrar(
    cuenta_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener detalle de cuenta por cobrar"""
    cuenta = await db.cuentas_por_cobrar.find_one({"id": cuenta_id, "origen": "clinica"}, {"_id": 0})
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return cuenta


@cxc_router.put("/{cuenta_id}", response_model=CuentaCobrarResponse)
async def actualizar_cuenta_cobrar(
    cuenta_id: str,
    cuenta: CuentaCobrarUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar cuenta por cobrar"""
    existing = await db.cuentas_por_cobrar.find_one({"id": cuenta_id, "origen": "clinica"}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    update_data = {k: v for k, v in cuenta.model_dump().items() if v is not None}
    
    # Si se actualiza monto_total, recalcular saldo
    if "monto_total" in update_data:
        update_data["saldo_pendiente"] = update_data["monto_total"] - existing.get("monto_pagado", 0)
        if update_data["saldo_pendiente"] <= 0:
            update_data["estado"] = "Pagado"
        elif update_data["saldo_pendiente"] < update_data["monto_total"]:
            update_data["estado"] = "Parcial"
        else:
            update_data["estado"] = "Pendiente"
    
    await db.cuentas_por_cobrar.update_one({"id": cuenta_id}, {"$set": update_data})
    updated = await db.cuentas_por_cobrar.find_one({"id": cuenta_id}, {"_id": 0})
    return updated


@cxc_router.post("/{cuenta_id}/abono", response_model=CuentaCobrarResponse)
async def registrar_abono(
    cuenta_id: str,
    abono: AbonoCreate,
    current_user: dict = Depends(get_current_user)
):
    """Registrar abono a cuenta por cobrar"""
    cuenta = await db.cuentas_por_cobrar.find_one({"id": cuenta_id, "origen": "clinica"}, {"_id": 0})
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    if abono.monto > cuenta.get("saldo_pendiente", 0):
        raise HTTPException(status_code=400, detail="El abono excede el saldo pendiente")
    
    now = datetime.now(timezone.utc)
    
    # Crear registro de abono
    abono_dict = {
        "id": str(uuid.uuid4()),
        "fecha": now.isoformat(),
        "monto": abono.monto,
        "metodo_pago": abono.metodo_pago,
        "referencia": abono.referencia,
        "registrado_por": current_user["id"],
        "registrado_por_nombre": current_user["name"]
    }
    
    # Actualizar cuenta
    nuevo_pagado = cuenta.get("monto_pagado", 0) + abono.monto
    nuevo_saldo = cuenta.get("monto_total", 0) - nuevo_pagado
    nuevo_estado = "Pagado" if nuevo_saldo <= 0 else ("Parcial" if nuevo_pagado > 0 else "Pendiente")
    
    abonos = cuenta.get("abonos", [])
    abonos.append(abono_dict)
    
    await db.cuentas_por_cobrar.update_one(
        {"id": cuenta_id},
        {"$set": {
            "monto_pagado": nuevo_pagado,
            "saldo_pendiente": nuevo_saldo,
            "estado": nuevo_estado,
            "abonos": abonos
        }}
    )
    
    # Si se solicita, registrar en caja
    if abono.registrar_en_caja:
        fecha_hoy = now.strftime("%Y-%m-%d")
        caja_abierta = await db.caja_cierres.find_one({
            "fecha": fecha_hoy,
            "origen": "clinica",
            "estado": "Abierto"
        })
        
        if caja_abierta:
            mov_dict = {
                "id": str(uuid.uuid4()),
                "origen": "clinica",
                "fecha": now.isoformat(),
                "tipo": "Ingreso",
                "categoria": "Cobro CxC",
                "concepto": f"Abono CxC: {cuenta.get('concepto', '')} - {cuenta.get('paciente_nombre', '')}",
                "monto": abono.monto,
                "metodo_pago": abono.metodo_pago,
                "referencia": abono.referencia,
                "paciente_id": cuenta.get("paciente_id"),
                "paciente_nombre": cuenta.get("paciente_nombre"),
                "bloqueado": False,
                "creado_por": current_user["id"],
                "creado_por_nombre": current_user["name"],
                "fecha_creacion": now.isoformat(),
                "cxc_id": cuenta_id
            }
            await db.caja_movimientos.insert_one(mov_dict)
    
    updated = await db.cuentas_por_cobrar.find_one({"id": cuenta_id}, {"_id": 0})
    return updated


@cxc_router.delete("/{cuenta_id}")
async def eliminar_cuenta_cobrar(
    cuenta_id: str,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Eliminar cuenta por cobrar (solo SuperAdmin)"""
    existing = await db.cuentas_por_cobrar.find_one({"id": cuenta_id, "origen": "clinica"}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    if existing.get("monto_pagado", 0) > 0:
        raise HTTPException(status_code=400, detail="No se puede eliminar una cuenta con abonos registrados")
    
    await db.cuentas_por_cobrar.delete_one({"id": cuenta_id})
    return {"message": "Cuenta eliminada"}


# ==================== CIERRES FINANCIEROS ====================

async def calcular_cierre_financiero(tipo: str, periodo: dict) -> dict:
    """Calcula los totales para un cierre financiero"""
    if tipo == "Mensual":
        year = periodo["anio"]
        month = periodo["mes"]
        inicio = f"{year}-{month:02d}-01"
        if month == 12:
            fin = f"{year + 1}-01-01"
        else:
            fin = f"{year}-{month + 1:02d}-01"
    else:  # Semestral
        year = periodo["anio"]
        if periodo["semestre"] == 1:
            inicio = f"{year}-01-01"
            fin = f"{year}-07-01"
        else:
            inicio = f"{year}-07-01"
            fin = f"{year + 1}-01-01"
    
    # Movimientos de caja del período
    movimientos = await db.caja_movimientos.find({
        "origen": "clinica",
        "fecha": {"$gte": f"{inicio}T00:00:00", "$lt": f"{fin}T00:00:00"}
    }, {"_id": 0}).to_list(10000)
    
    ingresos = sum(m["monto"] for m in movimientos if m["tipo"] == "Ingreso")
    egresos = sum(m["monto"] for m in movimientos if m["tipo"] == "Egreso")
    
    # CxC del período
    cuentas = await db.cuentas_por_cobrar.find({
        "origen": "clinica",
        "fecha_emision": {"$gte": inicio, "$lt": fin}
    }, {"_id": 0}).to_list(1000)
    
    cxc_por_tipo = {}
    for c in cuentas:
        tipo_id = c.get("tipo_pagador_id", "otro")
        tipo_nombre = c.get("tipo_pagador_nombre", "Otro")
        if tipo_id not in cxc_por_tipo:
            cxc_por_tipo[tipo_id] = {"tipo_pagador_id": tipo_id, "tipo_pagador_nombre": tipo_nombre, "emitido": 0, "cobrado": 0, "pendiente": 0}
        cxc_por_tipo[tipo_id]["emitido"] += c.get("monto_total", 0)
        cxc_por_tipo[tipo_id]["cobrado"] += c.get("monto_pagado", 0)
        cxc_por_tipo[tipo_id]["pendiente"] += c.get("saldo_pendiente", 0)
    
    return {
        "ingresos_caja": ingresos,
        "egresos_caja": egresos,
        "resultado_neto": ingresos - egresos,
        "cxc_por_tipo": list(cxc_por_tipo.values()),
        "cxc_total_emitido": sum(t["emitido"] for t in cxc_por_tipo.values()),
        "cxc_total_cobrado": sum(t["cobrado"] for t in cxc_por_tipo.values()),
        "cxc_saldo_pendiente": sum(t["pendiente"] for t in cxc_por_tipo.values())
    }


@cierres_financieros_router.get("", response_model=CierreFinancieroListResponse)
async def get_cierres_financieros(
    tipo: Optional[str] = None,
    anio: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Listar cierres financieros"""
    query = {"origen": "clinica"}
    if tipo:
        query["tipo"] = tipo
    if anio:
        query["periodo.anio"] = anio
    
    total = await db.cierres_financieros.count_documents(query)
    cierres = await db.cierres_financieros.find(
        query, {"_id": 0}
    ).sort([("periodo.anio", -1), ("periodo.mes", -1)]).skip(offset).limit(limit).to_list(limit)
    
    return {"data": cierres, "total": total}


@cierres_financieros_router.post("", response_model=CierreFinancieroResponse)
async def crear_cierre_financiero(
    cierre: CierreFinancieroCreate,
    current_user: dict = Depends(get_current_user)
):
    """Generar cierre financiero"""
    now = datetime.now(timezone.utc)
    
    periodo = {"anio": cierre.anio}
    if cierre.tipo == "Mensual":
        periodo["mes"] = cierre.mes
        # Calcular fecha_inicio y fecha_fin para mensual
        fecha_inicio = f"{cierre.anio}-{cierre.mes:02d}-01"
        if cierre.mes == 12:
            fecha_fin = f"{cierre.anio + 1}-01-01"
        else:
            fecha_fin = f"{cierre.anio}-{cierre.mes + 1:02d}-01"
    else:
        periodo["semestre"] = cierre.semestre
        # Calcular fecha_inicio y fecha_fin para semestral
        if cierre.semestre == 1:
            fecha_inicio = f"{cierre.anio}-01-01"
            fecha_fin = f"{cierre.anio}-07-01"
        else:
            fecha_inicio = f"{cierre.anio}-07-01"
            fecha_fin = f"{cierre.anio + 1}-01-01"
    
    # Verificar que no exista
    query = {"origen": "clinica", "tipo": cierre.tipo, "periodo": periodo}
    existing = await db.cierres_financieros.find_one(query)
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un cierre para este período")
    
    # Calcular totales
    calculos = await calcular_cierre_financiero(cierre.tipo, periodo)
    
    cierre_dict = {
        "id": str(uuid.uuid4()),
        "origen": "clinica",
        "tipo": cierre.tipo,
        "periodo": periodo,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "estado": "Borrador",
        "ingresos_caja": calculos["ingresos_caja"],
        "egresos_caja": calculos["egresos_caja"],
        "resultado_neto": calculos["resultado_neto"],
        "cxc_por_tipo": calculos["cxc_por_tipo"],
        "cxc_total_emitido": calculos["cxc_total_emitido"],
        "cxc_total_cobrado": calculos["cxc_total_cobrado"],
        "cxc_saldo_pendiente": calculos["cxc_saldo_pendiente"],
        "observaciones": cierre.observaciones,
        "creado_por": current_user["id"],
        "creado_por_nombre": current_user["name"],
        "fecha_generacion": now.isoformat()
    }
    
    await db.cierres_financieros.insert_one(cierre_dict)
    
    if "_id" in cierre_dict:
        del cierre_dict["_id"]
    return cierre_dict


@cierres_financieros_router.get("/{cierre_id}", response_model=CierreFinancieroResponse)
async def get_cierre_financiero(
    cierre_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener detalle de cierre financiero"""
    cierre = await db.cierres_financieros.find_one({"id": cierre_id, "origen": "clinica"}, {"_id": 0})
    if not cierre:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    return cierre


@cierres_financieros_router.put("/{cierre_id}", response_model=CierreFinancieroResponse)
async def actualizar_cierre_financiero(
    cierre_id: str,
    cierre: CierreFinancieroUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar cierre financiero"""
    existing = await db.cierres_financieros.find_one({"id": cierre_id, "origen": "clinica"}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    
    update_data = {k: v for k, v in cierre.model_dump().items() if v is not None}
    update_data["modificado_por"] = current_user["id"]
    update_data["fecha_modificacion"] = datetime.now(timezone.utc).isoformat()
    
    await db.cierres_financieros.update_one({"id": cierre_id}, {"$set": update_data})
    updated = await db.cierres_financieros.find_one({"id": cierre_id}, {"_id": 0})
    return updated


@cierres_financieros_router.post("/{cierre_id}/recalcular", response_model=CierreFinancieroResponse)
async def recalcular_cierre_financiero(
    cierre_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Recalcular totales de cierre financiero"""
    cierre = await db.cierres_financieros.find_one({"id": cierre_id, "origen": "clinica"}, {"_id": 0})
    if not cierre:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    
    # Recalcular
    calculos = await calcular_cierre_financiero(cierre["tipo"], cierre["periodo"])
    
    update_data = {
        "ingresos_caja": calculos["ingresos_caja"],
        "egresos_caja": calculos["egresos_caja"],
        "resultado_neto": calculos["resultado_neto"],
        "cxc_por_tipo": calculos["cxc_por_tipo"],
        "cxc_total_emitido": calculos["cxc_total_emitido"],
        "cxc_total_cobrado": calculos["cxc_total_cobrado"],
        "cxc_saldo_pendiente": calculos["cxc_saldo_pendiente"],
        "fecha_recalculo": datetime.now(timezone.utc).isoformat()
    }
    
    await db.cierres_financieros.update_one({"id": cierre_id}, {"$set": update_data})
    updated = await db.cierres_financieros.find_one({"id": cierre_id}, {"_id": 0})
    return updated


@cierres_financieros_router.delete("/{cierre_id}")
async def delete_cierre_financiero(
    cierre_id: str,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Eliminar cierre financiero (solo SuperAdmin)"""
    existing = await db.cierres_financieros.find_one({"id": cierre_id, "origen": "clinica"}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    
    await db.cierres_financieros.delete_one({"id": cierre_id})
    
    return {"message": "Cierre eliminado"}
