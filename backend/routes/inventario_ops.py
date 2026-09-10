# /app/backend/routes/inventario_ops.py
# Operaciones avanzadas de inventario: Órdenes de compra, Recepciones, Transferencias, Tomas físicas

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging

logger = logging.getLogger("inventario_ops")

router = APIRouter(prefix="/inventario", tags=["Inventario Operaciones"])

# Variable global para db
_db = None

def get_db():
    """Obtener instancia de la base de datos"""
    global _db
    if _db is None:
        from server import db
        _db = db
    return _db

def get_current_user_dependency():
    """Obtener la dependencia de usuario actual"""
    from server import get_current_user
    return get_current_user

# Importar modelos y funciones de inventario.py
from routes.inventario import (
    OrdenCompraCreate, OrdenCompraResponse, OrdenCompraListResponse, OrdenCompraItem,
    RecepcionCreate, RecepcionResponse, RecepcionListResponse,
    TransferenciaCreate, TransferenciaResponse, TransferenciaListResponse,
    TomaFisicaCreate, TomaFisicaResponse, TomaFisicaListResponse, TomaFisicaItem,
    generar_numero_orden, generar_numero_recepcion, generar_numero_transferencia, generar_numero_toma,
    obtener_existencia, actualizar_existencia, recalcular_costo_promedio, crear_movimiento_kardex,
    obtener_lotes_fefo, ConfigInventario, AlertaInventario, AlertasResponse, PanelInventarioResponse
)


# ==================== ÓRDENES DE COMPRA ====================

@router.get("/ordenes", response_model=OrdenCompraListResponse)
async def listar_ordenes_compra(
    estado: Optional[str] = None,
    proveedor_id: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista órdenes de compra"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    if estado:
        filtro["estado"] = estado
    if proveedor_id:
        filtro["proveedor_id"] = proveedor_id
    if fecha_desde:
        filtro["fecha"] = {"$gte": fecha_desde}
    if fecha_hasta:
        if "fecha" not in filtro:
            filtro["fecha"] = {}
        filtro["fecha"]["$lte"] = fecha_hasta + "T23:59:59"
    
    ordenes = await db.ordenes_compra.find(filtro).sort("fecha", -1).to_list(500)
    
    proveedores = {p["id"]: p for p in await db.suppliers.find({}).to_list(500)}
    
    data = []
    for o in ordenes:
        prov = proveedores.get(o["proveedor_id"], {})
        data.append(OrdenCompraResponse(
            id=o["id"],
            numero_orden=o["numero_orden"],
            proveedor_id=o["proveedor_id"],
            proveedor_nombre=prov.get("name", ""),
            fecha=o["fecha"],
            fecha_estimada_entrega=o.get("fecha_estimada_entrega"),
            items=o.get("items", []),
            subtotal=o.get("subtotal", 0),
            total=o.get("total", 0),
            estado=o.get("estado", "borrador"),
            observaciones=o.get("observaciones"),
            creada_por=o.get("creada_por", ""),
            autorizada_por=o.get("autorizada_por"),
            fecha_autorizacion=o.get("fecha_autorizacion"),
            origen=o.get("origen", "clinica"),
            created_at=o.get("created_at"),
            updated_at=o.get("updated_at")
        ))
    
    return OrdenCompraListResponse(data=data, total=len(data))


@router.get("/ordenes/sugerir-bajo-minimo")
async def sugerir_productos_bajo_minimo(
    current_user: dict = Depends(get_current_user_dependency())
):
    """Sugiere productos bajo mínimo para una orden de compra"""
    db = get_db()
    
    productos = await db.productos_inventario.find({
        "origen": "clinica",
        "activo": True,
        "controla_inventario": True
    }).to_list(1000)
    
    sugerencias = []
    for p in productos:
        # Calcular existencia total
        pipeline = [
            {"$match": {"producto_id": p["id"], "origen": "clinica"}},
            {"$group": {"_id": None, "total": {"$sum": "$cantidad"}}}
        ]
        result = await db.existencias_inventario.aggregate(pipeline).to_list(1)
        existencia = result[0]["total"] if result else 0
        
        min_stock = p.get("existencia_minima", 0)
        max_stock = p.get("existencia_maxima", 0)
        
        if existencia < min_stock:
            cantidad_sugerida = max(max_stock - existencia, min_stock - existencia + 10)
            sugerencias.append({
                "producto_id": p["id"],
                "codigo": p.get("codigo"),
                "nombre": p["nombre"],
                "existencia_actual": existencia,
                "existencia_minima": min_stock,
                "existencia_maxima": max_stock,
                "cantidad_sugerida": cantidad_sugerida,
                "ultimo_costo": p.get("ultimo_costo", 0),
                "proveedor_preferido_id": p.get("proveedor_preferido_id")
            })
    
    return {"sugerencias": sugerencias, "total": len(sugerencias)}


@router.get("/ordenes/{orden_id}", response_model=OrdenCompraResponse)
async def obtener_orden_compra(
    orden_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene una orden de compra por ID"""
    db = get_db()
    
    orden = await db.ordenes_compra.find_one({"id": orden_id, "origen": "clinica"})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    proveedor = await db.suppliers.find_one({"id": orden["proveedor_id"]})
    
    return OrdenCompraResponse(
        id=orden["id"],
        numero_orden=orden["numero_orden"],
        proveedor_id=orden["proveedor_id"],
        proveedor_nombre=proveedor.get("name", "") if proveedor else "",
        fecha=orden["fecha"],
        fecha_estimada_entrega=orden.get("fecha_estimada_entrega"),
        items=orden.get("items", []),
        subtotal=orden.get("subtotal", 0),
        total=orden.get("total", 0),
        estado=orden.get("estado", "borrador"),
        observaciones=orden.get("observaciones"),
        creada_por=orden.get("creada_por", ""),
        autorizada_por=orden.get("autorizada_por"),
        fecha_autorizacion=orden.get("fecha_autorizacion"),
        origen=orden.get("origen", "clinica"),
        created_at=orden.get("created_at"),
        updated_at=orden.get("updated_at")
    )

@router.post("/ordenes", response_model=OrdenCompraResponse)
async def crear_orden_compra(
    orden: OrdenCompraCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Crea una nueva orden de compra"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos para crear órdenes de compra")
    
    # Verificar proveedor
    proveedor = await db.suppliers.find_one({"id": orden.proveedor_id})
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    # Calcular totales
    subtotal = 0
    items_procesados = []
    for item in orden.items:
        item_subtotal = item.cantidad * item.costo_unitario
        subtotal += item_subtotal
        items_procesados.append({
            "producto_id": item.producto_id,
            "codigo": item.codigo,
            "nombre": item.nombre,
            "cantidad": item.cantidad,
            "cantidad_recibida": 0,
            "costo_unitario": item.costo_unitario,
            "subtotal": item_subtotal
        })
    
    numero_orden = await generar_numero_orden(db)
    
    nueva_orden = {
        "id": str(uuid.uuid4()),
        "numero_orden": numero_orden,
        "proveedor_id": orden.proveedor_id,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "fecha_estimada_entrega": orden.fecha_estimada_entrega,
        "items": items_procesados,
        "subtotal": subtotal,
        "total": subtotal,
        "estado": "borrador",
        "observaciones": orden.observaciones,
        "creada_por": current_user["id"],
        "origen": "clinica",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ordenes_compra.insert_one(nueva_orden)
    
    return OrdenCompraResponse(
        **nueva_orden,
        proveedor_nombre=proveedor.get("name", "")
    )

@router.put("/ordenes/{orden_id}", response_model=OrdenCompraResponse)
async def actualizar_orden_compra(
    orden_id: str,
    orden: OrdenCompraCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Actualiza una orden de compra en borrador"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    existente = await db.ordenes_compra.find_one({"id": orden_id, "origen": "clinica"})
    if not existente:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if existente.get("estado") != "borrador":
        raise HTTPException(status_code=400, detail="Solo se pueden editar órdenes en borrador")
    
    # Recalcular totales
    subtotal = 0
    items_procesados = []
    for item in orden.items:
        item_subtotal = item.cantidad * item.costo_unitario
        subtotal += item_subtotal
        items_procesados.append({
            "producto_id": item.producto_id,
            "codigo": item.codigo,
            "nombre": item.nombre,
            "cantidad": item.cantidad,
            "cantidad_recibida": 0,
            "costo_unitario": item.costo_unitario,
            "subtotal": item_subtotal
        })
    
    await db.ordenes_compra.update_one(
        {"id": orden_id},
        {"$set": {
            "proveedor_id": orden.proveedor_id,
            "fecha_estimada_entrega": orden.fecha_estimada_entrega,
            "items": items_procesados,
            "subtotal": subtotal,
            "total": subtotal,
            "observaciones": orden.observaciones,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    actualizada = await db.ordenes_compra.find_one({"id": orden_id})
    proveedor = await db.suppliers.find_one({"id": actualizada["proveedor_id"]})
    
    return OrdenCompraResponse(
        **actualizada,
        proveedor_nombre=proveedor.get("name", "") if proveedor else ""
    )

@router.patch("/ordenes/{orden_id}/autorizar")
async def autorizar_orden_compra(
    orden_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Autoriza una orden de compra (cambia estado a 'enviada')"""
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede autorizar órdenes")
    
    orden = await db.ordenes_compra.find_one({"id": orden_id, "origen": "clinica"})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if orden.get("estado") != "borrador":
        raise HTTPException(status_code=400, detail="Solo se pueden autorizar órdenes en borrador")
    
    await db.ordenes_compra.update_one(
        {"id": orden_id},
        {"$set": {
            "estado": "enviada",
            "autorizada_por": current_user["id"],
            "fecha_autorizacion": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Orden autorizada y marcada como enviada"}

@router.patch("/ordenes/{orden_id}/cancelar")
async def cancelar_orden_compra(
    orden_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Cancela una orden de compra"""
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede cancelar órdenes")
    
    orden = await db.ordenes_compra.find_one({"id": orden_id, "origen": "clinica"})
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if orden.get("estado") == "recibida":
        raise HTTPException(status_code=400, detail="No se puede cancelar una orden ya recibida completamente")
    
    await db.ordenes_compra.update_one(
        {"id": orden_id},
        {"$set": {
            "estado": "cancelada",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Orden cancelada"}


# ==================== RECEPCIONES ====================

@router.get("/recepciones", response_model=RecepcionListResponse)
async def listar_recepciones(
    proveedor_id: Optional[str] = None,
    bodega_id: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista recepciones de mercadería"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    if proveedor_id:
        filtro["proveedor_id"] = proveedor_id
    if bodega_id:
        filtro["bodega_id"] = bodega_id
    if fecha_desde:
        filtro["fecha"] = {"$gte": fecha_desde}
    if fecha_hasta:
        if "fecha" not in filtro:
            filtro["fecha"] = {}
        filtro["fecha"]["$lte"] = fecha_hasta + "T23:59:59"
    
    recepciones = await db.recepciones_inventario.find(filtro).sort("fecha", -1).to_list(500)
    
    proveedores = {p["id"]: p for p in await db.suppliers.find({}).to_list(500)}
    bodegas = {b["id"]: b for b in await db.bodegas_inventario.find({"origen": "clinica"}).to_list(100)}
    usuarios = {u["id"]: u for u in await db.users.find({}).to_list(100)}
    
    data = []
    for r in recepciones:
        prov = proveedores.get(r["proveedor_id"], {})
        bod = bodegas.get(r["bodega_id"], {})
        user = usuarios.get(r.get("usuario_id"), {})
        
        data.append(RecepcionResponse(
            id=r["id"],
            numero_recepcion=r["numero_recepcion"],
            orden_compra_id=r.get("orden_compra_id"),
            proveedor_id=r["proveedor_id"],
            proveedor_nombre=prov.get("name", ""),
            bodega_id=r["bodega_id"],
            bodega_nombre=bod.get("nombre", ""),
            fecha=r["fecha"],
            numero_factura=r.get("numero_factura"),
            numero_envio=r.get("numero_envio"),
            items=r.get("items", []),
            total_costo=r.get("total_costo", 0),
            gasto_id=r.get("gasto_id"),
            usuario_id=r.get("usuario_id", ""),
            usuario_nombre=user.get("name"),
            observaciones=r.get("observaciones"),
            origen=r.get("origen", "clinica"),
            created_at=r.get("created_at")
        ))
    
    return RecepcionListResponse(data=data, total=len(data))

@router.post("/recepciones", response_model=RecepcionResponse)
async def crear_recepcion(
    recepcion: RecepcionCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Crea una recepción de mercadería"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos para registrar recepciones")
    
    # Verificar bodega
    bodega = await db.bodegas_inventario.find_one({"id": recepcion.bodega_id, "origen": "clinica"})
    if not bodega:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    
    # Verificar proveedor
    proveedor = await db.suppliers.find_one({"id": recepcion.proveedor_id})
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    numero_recepcion = await generar_numero_recepcion(db)
    total_costo = 0
    items_procesados = []
    
    for item in recepcion.items:
        # Verificar producto
        producto = await db.productos_inventario.find_one({"id": item.producto_id, "origen": "clinica"})
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no encontrado")
        
        # Validar lote si el producto lo requiere
        lote_id = None
        if producto.get("controla_lotes", False):
            if not item.numero_lote or not item.fecha_vencimiento:
                raise HTTPException(
                    status_code=400, 
                    detail=f"El producto {producto['nombre']} requiere número de lote y fecha de vencimiento"
                )
            
            # Verificar lote único
            lote_existente = await db.lotes_inventario.find_one({
                "producto_id": item.producto_id,
                "numero_lote": item.numero_lote,
                "origen": "clinica"
            })
            if lote_existente:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ya existe el lote {item.numero_lote} para el producto {producto['nombre']}"
                )
            
            # Crear lote
            lote_id = str(uuid.uuid4())
            nuevo_lote = {
                "id": lote_id,
                "producto_id": item.producto_id,
                "bodega_id": recepcion.bodega_id,
                "numero_lote": item.numero_lote,
                "fecha_vencimiento": item.fecha_vencimiento,
                "cantidad_inicial": item.cantidad,
                "cantidad_disponible": item.cantidad,
                "costo_unitario": item.costo_unitario,
                "proveedor_id": recepcion.proveedor_id,
                "estado": "disponible",
                "origen": "clinica"
            }
            await db.lotes_inventario.insert_one(nuevo_lote)
        
        # Crear movimiento de kardex
        await crear_movimiento_kardex(
            db=db,
            producto_id=item.producto_id,
            bodega_id=recepcion.bodega_id,
            tipo="entrada",
            cantidad=item.cantidad,
            costo_unitario=item.costo_unitario,
            usuario_id=current_user["id"],
            lote_id=lote_id,
            referencia_tipo="recepcion",
            referencia_id=numero_recepcion
        )
        
        # Actualizar existencia
        await actualizar_existencia(db, item.producto_id, recepcion.bodega_id, item.cantidad)
        
        # Recalcular costo promedio
        await recalcular_costo_promedio(db, item.producto_id, item.cantidad, item.costo_unitario)
        
        item_costo = item.cantidad * item.costo_unitario
        total_costo += item_costo
        
        items_procesados.append({
            "producto_id": item.producto_id,
            "cantidad": item.cantidad,
            "costo_unitario": item.costo_unitario,
            "numero_lote": item.numero_lote,
            "fecha_vencimiento": item.fecha_vencimiento,
            "lote_id": lote_id
        })
    
    # Actualizar orden de compra si existe
    if recepcion.orden_compra_id:
        orden = await db.ordenes_compra.find_one({"id": recepcion.orden_compra_id})
        if orden:
            # Actualizar cantidades recibidas
            items_orden = orden.get("items", [])
            for item_recibido in recepcion.items:
                for item_orden in items_orden:
                    if item_orden["producto_id"] == item_recibido.producto_id:
                        item_orden["cantidad_recibida"] = item_orden.get("cantidad_recibida", 0) + item_recibido.cantidad
            
            # Determinar nuevo estado
            todas_recibidas = all(
                item.get("cantidad_recibida", 0) >= item["cantidad"] 
                for item in items_orden
            )
            alguna_recibida = any(
                item.get("cantidad_recibida", 0) > 0 
                for item in items_orden
            )
            
            nuevo_estado = "recibida" if todas_recibidas else ("parcial" if alguna_recibida else orden["estado"])
            
            await db.ordenes_compra.update_one(
                {"id": recepcion.orden_compra_id},
                {"$set": {
                    "items": items_orden,
                    "estado": nuevo_estado,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    
    # Crear la recepción
    nueva_recepcion = {
        "id": str(uuid.uuid4()),
        "numero_recepcion": numero_recepcion,
        "orden_compra_id": recepcion.orden_compra_id,
        "proveedor_id": recepcion.proveedor_id,
        "bodega_id": recepcion.bodega_id,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "numero_factura": recepcion.numero_factura,
        "numero_envio": recepcion.numero_envio,
        "items": items_procesados,
        "total_costo": total_costo,
        "usuario_id": current_user["id"],
        "observaciones": recepcion.observaciones,
        "origen": "clinica",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.recepciones_inventario.insert_one(nueva_recepcion)
    
    return RecepcionResponse(
        **nueva_recepcion,
        proveedor_nombre=proveedor.get("name", ""),
        bodega_nombre=bodega.get("nombre", ""),
        usuario_nombre=current_user.get("name")
    )


# ==================== TRANSFERENCIAS ====================

@router.get("/transferencias", response_model=TransferenciaListResponse)
async def listar_transferencias(
    estado: Optional[str] = None,
    bodega_origen_id: Optional[str] = None,
    bodega_destino_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista transferencias entre bodegas"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    if estado:
        filtro["estado"] = estado
    if bodega_origen_id:
        filtro["bodega_origen_id"] = bodega_origen_id
    if bodega_destino_id:
        filtro["bodega_destino_id"] = bodega_destino_id
    
    transferencias = await db.transferencias_inventario.find(filtro).sort("fecha", -1).to_list(500)
    
    bodegas = {b["id"]: b for b in await db.bodegas_inventario.find({"origen": "clinica"}).to_list(100)}
    
    data = []
    for t in transferencias:
        bod_origen = bodegas.get(t["bodega_origen_id"], {})
        bod_destino = bodegas.get(t["bodega_destino_id"], {})
        
        data.append(TransferenciaResponse(
            id=t["id"],
            numero_transferencia=t["numero_transferencia"],
            bodega_origen_id=t["bodega_origen_id"],
            bodega_origen_nombre=bod_origen.get("nombre", ""),
            bodega_destino_id=t["bodega_destino_id"],
            bodega_destino_nombre=bod_destino.get("nombre", ""),
            fecha=t["fecha"],
            items=t.get("items", []),
            estado=t.get("estado", "pendiente"),
            solicitada_por=t.get("solicitada_por", ""),
            recibida_por=t.get("recibida_por"),
            fecha_recepcion=t.get("fecha_recepcion"),
            observaciones=t.get("observaciones"),
            origen=t.get("origen", "clinica"),
            created_at=t.get("created_at")
        ))
    
    return TransferenciaListResponse(data=data, total=len(data))

@router.post("/transferencias", response_model=TransferenciaResponse)
async def crear_transferencia(
    transferencia: TransferenciaCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Crea y ejecuta una transferencia entre bodegas"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos para realizar transferencias")
    
    if transferencia.bodega_origen_id == transferencia.bodega_destino_id:
        raise HTTPException(status_code=400, detail="La bodega origen y destino no pueden ser la misma")
    
    # Verificar bodegas
    bodega_origen = await db.bodegas_inventario.find_one({"id": transferencia.bodega_origen_id, "origen": "clinica"})
    bodega_destino = await db.bodegas_inventario.find_one({"id": transferencia.bodega_destino_id, "origen": "clinica"})
    
    if not bodega_origen:
        raise HTTPException(status_code=404, detail="Bodega origen no encontrada")
    if not bodega_destino:
        raise HTTPException(status_code=404, detail="Bodega destino no encontrada")
    
    numero_transferencia = await generar_numero_transferencia(db)
    items_procesados = []
    
    for item in transferencia.items:
        # Verificar producto
        producto = await db.productos_inventario.find_one({"id": item.producto_id, "origen": "clinica"})
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no encontrado")
        
        # Verificar existencia en origen
        existencia_origen = await obtener_existencia(db, item.producto_id, transferencia.bodega_origen_id)
        if existencia_origen < item.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente de {producto['nombre']} en bodega origen. Disponible: {existencia_origen}"
            )
        
        costo = producto.get("costo_promedio", 0)
        
        # Si tiene lote específico, transferir ese lote
        if item.lote_id:
            lote = await db.lotes_inventario.find_one({"id": item.lote_id, "origen": "clinica"})
            if not lote:
                raise HTTPException(status_code=404, detail=f"Lote {item.lote_id} no encontrado")
            
            if lote["cantidad_disponible"] < item.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente en el lote {lote['numero_lote']}")
            
            costo = lote.get("costo_unitario", costo)
            
            # Actualizar lote origen (reducir cantidad)
            await db.lotes_inventario.update_one(
                {"id": item.lote_id},
                {"$inc": {"cantidad_disponible": -item.cantidad}}
            )
            
            # Crear o actualizar lote en destino
            lote_destino = await db.lotes_inventario.find_one({
                "producto_id": item.producto_id,
                "bodega_id": transferencia.bodega_destino_id,
                "numero_lote": lote["numero_lote"],
                "origen": "clinica"
            })
            
            if lote_destino:
                await db.lotes_inventario.update_one(
                    {"id": lote_destino["id"]},
                    {"$inc": {"cantidad_disponible": item.cantidad}}
                )
            else:
                nuevo_lote = {
                    "id": str(uuid.uuid4()),
                    "producto_id": item.producto_id,
                    "bodega_id": transferencia.bodega_destino_id,
                    "numero_lote": lote["numero_lote"],
                    "fecha_vencimiento": lote["fecha_vencimiento"],
                    "cantidad_inicial": item.cantidad,
                    "cantidad_disponible": item.cantidad,
                    "costo_unitario": lote.get("costo_unitario", 0),
                    "proveedor_id": lote.get("proveedor_id"),
                    "estado": "disponible",
                    "origen": "clinica"
                }
                await db.lotes_inventario.insert_one(nuevo_lote)
        
        # Movimiento de salida en origen
        await crear_movimiento_kardex(
            db=db,
            producto_id=item.producto_id,
            bodega_id=transferencia.bodega_origen_id,
            tipo="transferencia_salida",
            cantidad=item.cantidad,
            costo_unitario=costo,
            usuario_id=current_user["id"],
            lote_id=item.lote_id,
            referencia_tipo="transferencia",
            referencia_id=numero_transferencia
        )
        
        # Movimiento de entrada en destino
        await crear_movimiento_kardex(
            db=db,
            producto_id=item.producto_id,
            bodega_id=transferencia.bodega_destino_id,
            tipo="transferencia_entrada",
            cantidad=item.cantidad,
            costo_unitario=costo,
            usuario_id=current_user["id"],
            lote_id=item.lote_id,
            referencia_tipo="transferencia",
            referencia_id=numero_transferencia
        )
        
        # Actualizar existencias
        await actualizar_existencia(db, item.producto_id, transferencia.bodega_origen_id, -item.cantidad)
        await actualizar_existencia(db, item.producto_id, transferencia.bodega_destino_id, item.cantidad)
        
        items_procesados.append({
            "producto_id": item.producto_id,
            "lote_id": item.lote_id,
            "cantidad": item.cantidad
        })
    
    # Crear la transferencia
    nueva_transferencia = {
        "id": str(uuid.uuid4()),
        "numero_transferencia": numero_transferencia,
        "bodega_origen_id": transferencia.bodega_origen_id,
        "bodega_destino_id": transferencia.bodega_destino_id,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "items": items_procesados,
        "estado": "completada",
        "solicitada_por": current_user["id"],
        "recibida_por": current_user["id"],
        "fecha_recepcion": datetime.now(timezone.utc).isoformat(),
        "observaciones": transferencia.observaciones,
        "origen": "clinica",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transferencias_inventario.insert_one(nueva_transferencia)
    
    return TransferenciaResponse(
        **nueva_transferencia,
        bodega_origen_nombre=bodega_origen.get("nombre", ""),
        bodega_destino_nombre=bodega_destino.get("nombre", "")
    )


# ==================== TOMAS FÍSICAS ====================

@router.get("/tomas", response_model=TomaFisicaListResponse)
async def listar_tomas_fisicas(
    estado: Optional[str] = None,
    bodega_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista tomas físicas de inventario"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    if estado:
        filtro["estado"] = estado
    if bodega_id:
        filtro["bodega_id"] = bodega_id
    
    tomas = await db.tomas_fisicas.find(filtro).sort("fecha_inicio", -1).to_list(100)
    
    bodegas = {b["id"]: b for b in await db.bodegas_inventario.find({"origen": "clinica"}).to_list(100)}
    
    data = []
    for t in tomas:
        bod = bodegas.get(t["bodega_id"], {})
        data.append(TomaFisicaResponse(
            id=t["id"],
            numero_toma=t["numero_toma"],
            bodega_id=t["bodega_id"],
            bodega_nombre=bod.get("nombre", ""),
            fecha_inicio=t["fecha_inicio"],
            fecha_cierre=t.get("fecha_cierre"),
            estado=t.get("estado", "en_proceso"),
            items=t.get("items", []),
            total_diferencia_unidades=t.get("total_diferencia_unidades", 0),
            total_diferencia_valor=t.get("total_diferencia_valor", 0),
            realizada_por=t.get("realizada_por", ""),
            autorizada_por=t.get("autorizada_por"),
            origen=t.get("origen", "clinica")
        ))
    
    return TomaFisicaListResponse(data=data, total=len(data))

@router.post("/tomas", response_model=TomaFisicaResponse)
async def iniciar_toma_fisica(
    toma: TomaFisicaCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Inicia una nueva toma física de inventario"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos para iniciar tomas físicas")
    
    # Verificar bodega
    bodega = await db.bodegas_inventario.find_one({"id": toma.bodega_id, "origen": "clinica"})
    if not bodega:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    
    # Verificar que no haya otra toma en proceso para esta bodega
    toma_existente = await db.tomas_fisicas.find_one({
        "bodega_id": toma.bodega_id,
        "estado": "en_proceso",
        "origen": "clinica"
    })
    if toma_existente:
        raise HTTPException(status_code=400, detail="Ya existe una toma física en proceso para esta bodega")
    
    numero_toma = await generar_numero_toma(db)
    
    # Obtener todos los productos con existencia en esta bodega
    existencias = await db.existencias_inventario.find({
        "bodega_id": toma.bodega_id,
        "origen": "clinica"
    }).to_list(1000)
    
    productos = {p["id"]: p for p in await db.productos_inventario.find({"origen": "clinica"}).to_list(1000)}
    
    items = []
    for e in existencias:
        prod = productos.get(e["producto_id"], {})
        if prod.get("controla_inventario", True):
            items.append({
                "producto_id": e["producto_id"],
                "producto_nombre": prod.get("nombre", ""),
                "producto_codigo": prod.get("codigo", ""),
                "existencia_sistema": e.get("cantidad", 0),
                "existencia_contada": None,
                "diferencia": 0,
                "costo_unitario": prod.get("costo_promedio", 0),
                "impacto_valor": 0,
                "observacion": None
            })
    
    nueva_toma = {
        "id": str(uuid.uuid4()),
        "numero_toma": numero_toma,
        "bodega_id": toma.bodega_id,
        "fecha_inicio": datetime.now(timezone.utc).isoformat(),
        "estado": "en_proceso",
        "items": items,
        "total_diferencia_unidades": 0,
        "total_diferencia_valor": 0,
        "realizada_por": current_user["id"],
        "origen": "clinica"
    }
    
    await db.tomas_fisicas.insert_one(nueva_toma)
    
    return TomaFisicaResponse(
        **nueva_toma,
        bodega_nombre=bodega.get("nombre", "")
    )

@router.put("/tomas/{toma_id}/conteo")
async def actualizar_conteo(
    toma_id: str,
    items: List[dict] = Body(...),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Actualiza el conteo de una toma física"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    toma = await db.tomas_fisicas.find_one({"id": toma_id, "origen": "clinica"})
    if not toma:
        raise HTTPException(status_code=404, detail="Toma física no encontrada")
    
    if toma.get("estado") != "en_proceso":
        raise HTTPException(status_code=400, detail="La toma física ya está cerrada")
    
    # Actualizar items con las cantidades contadas
    items_actualizados = toma.get("items", [])
    total_diferencia_unidades = 0
    total_diferencia_valor = 0
    
    for conteo in items:
        for item in items_actualizados:
            if item["producto_id"] == conteo["producto_id"]:
                item["existencia_contada"] = conteo.get("existencia_contada")
                if item["existencia_contada"] is not None:
                    item["diferencia"] = item["existencia_contada"] - item["existencia_sistema"]
                    item["impacto_valor"] = round(item["diferencia"] * item["costo_unitario"], 2)
                    total_diferencia_unidades += item["diferencia"]
                    total_diferencia_valor += item["impacto_valor"]
                item["observacion"] = conteo.get("observacion")
                break
    
    await db.tomas_fisicas.update_one(
        {"id": toma_id},
        {"$set": {
            "items": items_actualizados,
            "total_diferencia_unidades": total_diferencia_unidades,
            "total_diferencia_valor": round(total_diferencia_valor, 2)
        }}
    )
    
    return {
        "message": "Conteo actualizado",
        "total_diferencia_unidades": total_diferencia_unidades,
        "total_diferencia_valor": round(total_diferencia_valor, 2)
    }

@router.post("/tomas/{toma_id}/cerrar")
async def cerrar_toma_fisica(
    toma_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Cierra una toma física y aplica los ajustes automáticamente"""
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede cerrar tomas físicas")
    
    toma = await db.tomas_fisicas.find_one({"id": toma_id, "origen": "clinica"})
    if not toma:
        raise HTTPException(status_code=404, detail="Toma física no encontrada")
    
    if toma.get("estado") != "en_proceso":
        raise HTTPException(status_code=400, detail="La toma física ya está cerrada")
    
    # Verificar que todos los items tengan conteo
    items = toma.get("items", [])
    sin_contar = [i for i in items if i.get("existencia_contada") is None]
    if sin_contar:
        raise HTTPException(
            status_code=400, 
            detail=f"Hay {len(sin_contar)} productos sin contar. Complete el conteo antes de cerrar."
        )
    
    # Aplicar ajustes
    ajustes_aplicados = 0
    for item in items:
        diferencia = item.get("diferencia", 0)
        if diferencia != 0:
            tipo = "ajuste_positivo" if diferencia > 0 else "ajuste_negativo"
            
            # Crear movimiento de kardex
            await crear_movimiento_kardex(
                db=db,
                producto_id=item["producto_id"],
                bodega_id=toma["bodega_id"],
                tipo=tipo,
                cantidad=abs(diferencia),
                costo_unitario=item.get("costo_unitario", 0),
                usuario_id=current_user["id"],
                referencia_tipo="toma_fisica",
                referencia_id=toma["numero_toma"],
                motivo=f"Ajuste por toma física {toma['numero_toma']}"
            )
            
            # Actualizar existencia
            await actualizar_existencia(db, item["producto_id"], toma["bodega_id"], diferencia)
            
            ajustes_aplicados += 1
    
    # Cerrar la toma
    await db.tomas_fisicas.update_one(
        {"id": toma_id},
        {"$set": {
            "estado": "cerrada",
            "fecha_cierre": datetime.now(timezone.utc).isoformat(),
            "autorizada_por": current_user["id"]
        }}
    )
    
    return {
        "message": f"Toma física cerrada. Se aplicaron {ajustes_aplicados} ajustes.",
        "ajustes_aplicados": ajustes_aplicados,
        "total_diferencia_unidades": toma.get("total_diferencia_unidades", 0),
        "total_diferencia_valor": toma.get("total_diferencia_valor", 0)
    }

@router.get("/tomas/{toma_id}/hoja-conteo")
async def obtener_hoja_conteo(
    toma_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene la hoja de conteo para impresión (sin mostrar existencia del sistema)"""
    db = get_db()
    
    toma = await db.tomas_fisicas.find_one({"id": toma_id, "origen": "clinica"})
    if not toma:
        raise HTTPException(status_code=404, detail="Toma física no encontrada")
    
    bodega = await db.bodegas_inventario.find_one({"id": toma["bodega_id"]})
    
    items_para_impresion = []
    for item in toma.get("items", []):
        items_para_impresion.append({
            "producto_id": item["producto_id"],
            "producto_codigo": item.get("producto_codigo", ""),
            "producto_nombre": item.get("producto_nombre", ""),
            "existencia_contada": "_______"  # Campo para llenar manualmente
        })
    
    return {
        "numero_toma": toma["numero_toma"],
        "bodega_nombre": bodega.get("nombre", "") if bodega else "",
        "fecha_inicio": toma["fecha_inicio"],
        "items": items_para_impresion,
        "total_items": len(items_para_impresion)
    }


# ==================== ALERTAS ====================

@router.get("/alertas", response_model=AlertasResponse)
async def obtener_alertas(
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene todas las alertas de inventario activas"""
    db = get_db()
    
    alertas = []
    total_minimo = 0
    total_por_vencer = 0
    total_vencidos = 0
    
    # Obtener configuración
    config = await db.config_inventario.find_one({"origen": "clinica"})
    dias_alerta = config.get("dias_alerta_vencimiento", [90, 60, 30]) if config else [90, 60, 30]
    max_dias = max(dias_alerta)
    
    hoy = datetime.now(timezone.utc).date()
    
    # Alertas de productos bajo mínimo
    productos = await db.productos_inventario.find({
        "origen": "clinica",
        "activo": True,
        "controla_inventario": True
    }).to_list(1000)
    
    for p in productos:
        # Calcular existencia total
        pipeline = [
            {"$match": {"producto_id": p["id"], "origen": "clinica"}},
            {"$group": {"_id": None, "total": {"$sum": "$cantidad"}}}
        ]
        result = await db.existencias_inventario.aggregate(pipeline).to_list(1)
        existencia = result[0]["total"] if result else 0
        
        if existencia < p.get("existencia_minima", 0):
            total_minimo += 1
            alertas.append(AlertaInventario(
                tipo="minimo",
                producto_id=p["id"],
                producto_nombre=p["nombre"],
                producto_codigo=p.get("codigo", ""),
                mensaje=f"Stock bajo mínimo: {existencia} unidades (mínimo: {p.get('existencia_minima', 0)})",
                severidad="alta" if existencia == 0 else "media",
                valor=existencia
            ))
    
    # Alertas de lotes por vencer y vencidos
    fecha_limite = (hoy + timedelta(days=max_dias)).strftime("%Y-%m-%d")
    
    lotes = await db.lotes_inventario.find({
        "origen": "clinica",
        "estado": "disponible",
        "cantidad_disponible": {"$gt": 0},
        "fecha_vencimiento": {"$lte": fecha_limite}
    }).to_list(500)
    
    productos_dict = {p["id"]: p for p in productos}
    bodegas = {b["id"]: b for b in await db.bodegas_inventario.find({"origen": "clinica"}).to_list(100)}
    
    for lote in lotes:
        try:
            fecha_venc = datetime.strptime(lote["fecha_vencimiento"], "%Y-%m-%d").date()
            dias_para_vencer = (fecha_venc - hoy).days
        except Exception:
            continue
        
        prod = productos_dict.get(lote["producto_id"], {})
        bod = bodegas.get(lote["bodega_id"], {})
        
        valor_en_riesgo = lote.get("cantidad_disponible", 0) * lote.get("costo_unitario", 0)
        
        if dias_para_vencer < 0:
            # Ya vencido
            total_vencidos += 1
            alertas.append(AlertaInventario(
                tipo="vencido",
                producto_id=lote["producto_id"],
                producto_nombre=prod.get("nombre", ""),
                producto_codigo=prod.get("codigo", ""),
                bodega_id=lote["bodega_id"],
                bodega_nombre=bod.get("nombre", ""),
                lote_id=lote["id"],
                numero_lote=lote["numero_lote"],
                mensaje=f"Lote VENCIDO hace {abs(dias_para_vencer)} días",
                severidad="alta",
                valor=valor_en_riesgo,
                fecha_vencimiento=lote["fecha_vencimiento"],
                dias_para_vencer=dias_para_vencer
            ))
        else:
            # Por vencer
            total_por_vencer += 1
            severidad = "alta" if dias_para_vencer <= 30 else ("media" if dias_para_vencer <= 60 else "baja")
            alertas.append(AlertaInventario(
                tipo="vencimiento",
                producto_id=lote["producto_id"],
                producto_nombre=prod.get("nombre", ""),
                producto_codigo=prod.get("codigo", ""),
                bodega_id=lote["bodega_id"],
                bodega_nombre=bod.get("nombre", ""),
                lote_id=lote["id"],
                numero_lote=lote["numero_lote"],
                mensaje=f"Vence en {dias_para_vencer} días ({lote['fecha_vencimiento']})",
                severidad=severidad,
                valor=valor_en_riesgo,
                fecha_vencimiento=lote["fecha_vencimiento"],
                dias_para_vencer=dias_para_vencer
            ))
    
    # Ordenar alertas por severidad
    orden_severidad = {"alta": 0, "media": 1, "baja": 2}
    alertas.sort(key=lambda x: orden_severidad.get(x.severidad, 3))
    
    return AlertasResponse(
        alertas=alertas,
        total_minimo=total_minimo,
        total_por_vencer=total_por_vencer,
        total_vencidos=total_vencidos,
        total=len(alertas)
    )


# ==================== PANEL/DASHBOARD ====================

@router.get("/panel", response_model=PanelInventarioResponse)
async def obtener_panel_inventario(
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene datos del panel/dashboard del módulo de inventario"""
    db = get_db()
    
    # Valor total del inventario
    pipeline_valor = [
        {"$match": {"origen": "clinica"}},
        {"$lookup": {
            "from": "productos_inventario",
            "localField": "producto_id",
            "foreignField": "id",
            "as": "producto"
        }},
        {"$unwind": "$producto"},
        {"$project": {
            "valor": {"$multiply": ["$cantidad", "$producto.costo_promedio"]}
        }},
        {"$group": {"_id": None, "total": {"$sum": "$valor"}}}
    ]
    result_valor = await db.existencias_inventario.aggregate(pipeline_valor).to_list(1)
    valor_total = round(result_valor[0]["total"], 2) if result_valor else 0
    
    # Total productos activos
    total_productos = await db.productos_inventario.count_documents({
        "origen": "clinica",
        "activo": True
    })
    
    # Productos bajo mínimo
    productos = await db.productos_inventario.find({
        "origen": "clinica",
        "activo": True,
        "controla_inventario": True
    }).to_list(1000)
    
    bajo_minimo = 0
    for p in productos:
        pipeline = [
            {"$match": {"producto_id": p["id"], "origen": "clinica"}},
            {"$group": {"_id": None, "total": {"$sum": "$cantidad"}}}
        ]
        result = await db.existencias_inventario.aggregate(pipeline).to_list(1)
        existencia = result[0]["total"] if result else 0
        if existencia < p.get("existencia_minima", 0):
            bajo_minimo += 1
    
    # Lotes por vencer en 90 días
    hoy = datetime.now(timezone.utc).date()
    fecha_90 = (hoy + timedelta(days=90)).strftime("%Y-%m-%d")
    lotes_por_vencer = await db.lotes_inventario.count_documents({
        "origen": "clinica",
        "estado": "disponible",
        "cantidad_disponible": {"$gt": 0},
        "fecha_vencimiento": {"$lte": fecha_90, "$gt": hoy.strftime("%Y-%m-%d")}
    })
    
    # Lotes vencidos
    lotes_vencidos = await db.lotes_inventario.count_documents({
        "origen": "clinica",
        "estado": "disponible",
        "cantidad_disponible": {"$gt": 0},
        "fecha_vencimiento": {"$lt": hoy.strftime("%Y-%m-%d")}
    })
    
    # Movimientos del día
    inicio_hoy = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    movimientos_hoy = await db.movimientos_inventario.count_documents({
        "origen": "clinica",
        "fecha": {"$gte": inicio_hoy}
    })
    
    # Valor por categoría
    categorias = await db.categorias_inventario.find({"origen": "clinica"}).to_list(100)
    valor_por_categoria = []
    
    for cat in categorias:
        pipeline = [
            {"$match": {"categoria_id": cat["id"], "origen": "clinica"}},
            {"$lookup": {
                "from": "existencias_inventario",
                "localField": "id",
                "foreignField": "producto_id",
                "as": "existencias"
            }},
            {"$unwind": {"path": "$existencias", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "valor": {"$multiply": [
                    {"$ifNull": ["$existencias.cantidad", 0]},
                    {"$ifNull": ["$costo_promedio", 0]}
                ]}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$valor"}}}
        ]
        result = await db.productos_inventario.aggregate(pipeline).to_list(1)
        valor = round(result[0]["total"], 2) if result else 0
        
        if valor > 0:
            valor_por_categoria.append({
                "categoria_id": cat["id"],
                "categoria_nombre": cat["nombre"],
                "color": cat.get("color", "#0F6E56"),
                "valor": valor
            })
    
    valor_por_categoria.sort(key=lambda x: x["valor"], reverse=True)
    
    # Últimos 10 movimientos
    ultimos_movimientos = await db.movimientos_inventario.find(
        {"origen": "clinica"}
    ).sort("fecha", -1).limit(10).to_list(10)
    
    productos_dict = {p["id"]: p for p in productos}
    
    movimientos_data = []
    for m in ultimos_movimientos:
        prod = productos_dict.get(m["producto_id"], {})
        movimientos_data.append({
            "id": m["id"],
            "fecha": m["fecha"],
            "tipo": m["tipo"],
            "producto_nombre": prod.get("nombre", ""),
            "cantidad": m["cantidad"],
            "costo_total": m.get("costo_total", 0)
        })
    
    # Productos con mayor rotación del mes
    inicio_mes = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    pipeline_rotacion = [
        {"$match": {
            "origen": "clinica",
            "fecha": {"$gte": inicio_mes},
            "tipo": {"$in": ["venta", "salida", "consumo"]}
        }},
        {"$group": {
            "_id": "$producto_id",
            "total_salidas": {"$sum": "$cantidad"}
        }},
        {"$sort": {"total_salidas": -1}},
        {"$limit": 10}
    ]
    
    rotacion = await db.movimientos_inventario.aggregate(pipeline_rotacion).to_list(10)
    
    productos_rotacion = []
    for r in rotacion:
        prod = productos_dict.get(r["_id"], {})
        if prod:
            productos_rotacion.append({
                "producto_id": r["_id"],
                "producto_nombre": prod.get("nombre", ""),
                "producto_codigo": prod.get("codigo", ""),
                "total_salidas": r["total_salidas"]
            })
    
    return PanelInventarioResponse(
        valor_total_inventario=valor_total,
        total_productos_activos=total_productos,
        productos_bajo_minimo=bajo_minimo,
        lotes_por_vencer_90=lotes_por_vencer,
        lotes_vencidos=lotes_vencidos,
        movimientos_hoy=movimientos_hoy,
        valor_por_categoria=valor_por_categoria,
        ultimos_movimientos=movimientos_data,
        productos_mayor_rotacion=productos_rotacion
    )


# ==================== CONFIGURACIÓN ====================

@router.get("/config")
async def obtener_configuracion(
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene la configuración del módulo de inventario"""
    db = get_db()
    
    config = await db.config_inventario.find_one({"origen": "clinica"}, {"_id": 0})
    
    if not config:
        # Configuración por defecto
        config = {
            "metodo_valuacion": "promedio_ponderado",
            "metodo_salida_lotes": "FEFO",
            "permitir_existencia_negativa": False,
            "dias_alerta_vencimiento": [90, 60, 30],
            "bloquear_venta_producto_vencido": True,
            "generar_gasto_al_recibir": True,
            "bodega_predeterminada_pos": None,
            "origen": "clinica"
        }
    
    return config

@router.put("/config")
async def actualizar_configuracion(
    config: ConfigInventario,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Actualiza la configuración del módulo de inventario"""
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede configurar el inventario")
    
    await db.config_inventario.update_one(
        {"origen": "clinica"},
        {"$set": {**config.model_dump(), "origen": "clinica"}},
        upsert=True
    )
    
    return {"message": "Configuración actualizada"}
