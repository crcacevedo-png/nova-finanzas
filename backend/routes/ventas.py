# /app/backend/routes/ventas.py
# Módulo de Punto de Venta (POS) - NovaVision
# Integrado con Inventario (FEFO) y Caja Diaria
# IMPORTANTE: Este módulo está AISLADO del módulo de óptica (origen="clinica")

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from utils.timezone import now_gt, today_str_gt, dia_gt_a_rango_utc, GUATEMALA_TZ
from pymongo import ReturnDocument
import uuid
import logging

logger = logging.getLogger("ventas")

router = APIRouter(prefix="/ventas", tags=["Punto de Venta"])

# ==================== MODELOS PYDANTIC ====================

class VentaItem(BaseModel):
    """Item de una venta"""
    producto_id: str
    codigo: Optional[str] = None
    nombre: str
    cantidad: int = Field(ge=1)
    precio_unitario: float = Field(ge=0)
    descuento: float = Field(default=0, ge=0)
    subtotal: float = 0
    afecto_iva: bool = True
    # Precio variable (solo POS clínica): precio distinto al de lista para este renglón
    precio_variable: bool = False
    precio_lista: Optional[float] = None
    # Campos para trazabilidad de lotes (se llenan al confirmar)
    lotes_consumidos: List[dict] = []

class FormaPago(BaseModel):
    """Forma de pago en una venta"""
    metodo: Literal["Efectivo", "Tarjeta", "Transferencia", "Cheque", "Cuenta por Cobrar"]
    monto: float = Field(ge=0)
    referencia: Optional[str] = None
    # Para Cuenta por Cobrar
    tipo_pagador_id: Optional[str] = None
    tipo_pagador_nombre: Optional[str] = None

class VentaCreate(BaseModel):
    """Crear una nueva venta"""
    bodega_id: str
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None
    medico_id: Optional[str] = None
    medico_nombre: Optional[str] = None
    items: List[VentaItem]
    formas_pago: List[FormaPago]
    descuento_porcentaje: float = Field(default=0, ge=0, le=100)
    descuento_autoriza: Optional[str] = None
    observaciones: Optional[str] = None
    # FEL Guatemala - preparado pero deshabilitado
    datos_fel: Optional[dict] = None

class VentaResponse(BaseModel):
    """Respuesta de venta"""
    id: str
    numero_venta: str
    fecha: str
    bodega_id: Optional[str] = None
    bodega_nombre: Optional[str] = None
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None
    medico_id: Optional[str] = None
    medico_nombre: Optional[str] = None
    items: List[dict] = []
    cantidad_items: int = 0
    subtotal: float = 0
    descuento_total: float = 0
    descuento_porcentaje: float = 0
    descuento_monto: float = 0
    descuento_autoriza: Optional[str] = ""
    iva: float = 0
    total: float = 0
    formas_pago: List[dict] = []
    efectivo_recibido: float = 0
    cambio: float = 0
    estado: str = "completada"
    caja_sesion_id: Optional[str] = None
    movimiento_caja_id: Optional[str] = None
    cxc_id: Optional[str] = None
    observaciones: Optional[str] = None
    vendedor_id: Optional[str] = None
    vendedor_nombre: Optional[str] = None
    origen: str = "clinica"
    created_at: Optional[str] = None
    # FEL
    datos_fel: Optional[dict] = None
    fel_uuid: Optional[str] = None
    fel_numero: Optional[str] = None
    fel: Optional[dict] = None
    # Anulación
    motivo_anulacion: Optional[str] = None
    anulada_por_nombre: Optional[str] = None
    fecha_anulacion: Optional[str] = None

class VentaListResponse(BaseModel):
    """Lista de ventas"""
    data: List[VentaResponse]
    total: int
    page: int
    limit: int

class AnularVentaRequest(BaseModel):
    """Solicitud de anulación"""
    motivo: str = Field(min_length=5)
    devolver_inventario: bool = True

class ResumenVentasDia(BaseModel):
    """Resumen de ventas del día"""
    total_ventas: int
    total_monto: float
    por_metodo_pago: dict
    por_categoria: List[dict]
    productos_mas_vendidos: List[dict]

class ProductoPOSResponse(BaseModel):
    """Producto para búsqueda rápida en POS"""
    id: str
    codigo: str
    nombre: str
    categoria_nombre: Optional[str] = None
    precio_venta: float
    precio_compra: float = 0
    afecto_iva: bool
    existencia: int
    existencia_total: int = 0
    controla_inventario: bool = True
    controla_lotes: bool
    requiere_receta: bool
    imagen: Optional[str] = None

# ==================== FUNCIONES AUXILIARES ====================

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
    """Dependencia: usuario autenticado con permiso de Punto de Venta (SEC-003)."""
    from server import get_current_user

    async def _dep(current_user: dict = Depends(get_current_user)):
        perms = current_user.get("permissions") or {}
        if not perms.get("manage_sales"):
            raise HTTPException(status_code=403, detail="No tienes permiso para operar el Punto de Venta")
        return current_user

    return _dep

async def generar_numero_venta(db) -> str:
    """Genera número único para venta con formato VTA-YYYYMMDD-XXXX.

    Usa un contador atómico por día en la colección `counters` para evitar
    números DUPLICADOS cuando varios cajeros venden en simultáneo.
    """
    hoy = now_gt().strftime("%Y%m%d")
    prefijo = f"VTA-{hoy}-"
    counter_key = f"venta_num_{hoy}"

    # Inicialización idempotente del contador del día.
    if await db.counters.find_one({"_id": counter_key}) is None:
        ultima = await db.ventas.find_one(
            {"numero_venta": {"$regex": f"^{prefijo}"}},
            sort=[("numero_venta", -1)]
        )
        start = 0
        if ultima:
            try:
                start = int(ultima["numero_venta"].split("-")[-1])
            except Exception:
                start = 0
        await db.counters.update_one(
            {"_id": counter_key},
            {"$setOnInsert": {"seq": start}},
            upsert=True
        )

    candidato = f"{prefijo}0001"
    for _ in range(5):
        doc = await db.counters.find_one_and_update(
            {"_id": counter_key},
            {"$inc": {"seq": 1}},
            return_document=ReturnDocument.AFTER,
            upsert=True
        )
        num = doc.get("seq", 1)
        candidato = f"{prefijo}{num:04d}"
        if not await db.ventas.find_one({"numero_venta": candidato}):
            return candidato
    return candidato

async def obtener_existencia_bodega(db, producto_id: str, bodega_id: str) -> int:
    """Obtiene la existencia de un producto en una bodega específica"""
    existencia = await db.existencias_inventario.find_one({
        "producto_id": producto_id,
        "bodega_id": bodega_id,
        "origen": "clinica"
    })
    return existencia.get("cantidad", 0) if existencia else 0

# Importar función de descuento de inventario
async def descontar_inventario_pos(db, items, bodega_id, referencia_tipo, referencia_id, usuario_id):
    """
    Wrapper para la función descontarInventario del módulo de inventario.
    Retorna: {success: bool, detalle: [...], error: str}
    """
    from routes.inventario import descontar_inventario
    return await descontar_inventario(db, items, bodega_id, referencia_tipo, referencia_id, usuario_id)

# ==================== ENDPOINTS ====================

@router.get("/productos", response_model=List[ProductoPOSResponse])
async def buscar_productos_pos(
    search: Optional[str] = None,
    bodega_id: Optional[str] = None,
    categoria_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user_dependency())
):
    """
    Búsqueda rápida de productos para el POS.
    Optimizado para autocompletado y escaneo de código de barras.
    """
    db = get_db()
    
    filtro = {"origen": "clinica", "activo": True}
    
    if search:
        filtro["$or"] = [
            {"nombre": {"$regex": search, "$options": "i"}},
            {"codigo": {"$regex": search, "$options": "i"}},
            {"codigo_barras": search}  # Exacto para código de barras
        ]
    
    if categoria_id:
        filtro["categoria_id"] = categoria_id
    
    productos = await db.productos_inventario.find(filtro).sort("nombre", 1).limit(limit).to_list(limit)
    
    # Obtener categorías
    categorias = {c["id"]: c["nombre"] for c in await db.categorias_inventario.find({"origen": "clinica"}).to_list(100)}
    
    # Si hay bodega, obtener existencias
    existencias_map = {}
    if bodega_id:
        existencias = await db.existencias_inventario.find({
            "bodega_id": bodega_id,
            "origen": "clinica"
        }).to_list(1000)
        existencias_map = {e["producto_id"]: e.get("cantidad", 0) for e in existencias}

    # Existencia TOTAL (todas las bodegas) para cada producto
    from routes.inventario import obtener_existencias_totales
    totales_map = await obtener_existencias_totales(db, [p["id"] for p in productos])

    resultado = []
    for p in productos:
        controla_inv = p.get("controla_inventario", True)
        # Si no controla inventario, mostrar existencia como -1 (ilimitado)
        existencia = existencias_map.get(p["id"], 0) if bodega_id and controla_inv else (-1 if not controla_inv else 0)
        existencia_total = totales_map.get(p["id"], 0) if controla_inv else -1
        
        resultado.append(ProductoPOSResponse(
            id=p["id"],
            codigo=p.get("codigo", ""),
            nombre=p["nombre"],
            categoria_nombre=categorias.get(p.get("categoria_id")),
            precio_venta=p.get("precio_venta", 0),
            precio_compra=p.get("precio_compra", 0) or 0,
            afecto_iva=p.get("afecto_iva", True),
            existencia=existencia,
            existencia_total=existencia_total,
            controla_inventario=controla_inv,
            controla_lotes=p.get("controla_lotes", False),
            requiere_receta=p.get("requiere_receta", False),
            imagen=p.get("imagen")
        ))
    
    return resultado

@router.get("/productos-rapidos", response_model=List[ProductoPOSResponse])
async def obtener_productos_rapidos(
    bodega_id: Optional[str] = None,
    limit: int = Query(8, ge=1, le=20),
    current_user: dict = Depends(get_current_user_dependency())
):
    """
    Obtiene los productos más vendidos para acceso rápido en el POS.
    Basado en el historial de ventas de los últimos 30 días.
    """
    db = get_db()
    
    # Calcular fecha hace 30 días
    fecha_limite = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    # Agregar ventas por producto
    pipeline = [
        {
            "$match": {
                "origen": "clinica",
                "estado": "completada",
                "fecha": {"$gte": fecha_limite}
            }
        },
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.producto_id",
                "cantidad_vendida": {"$sum": "$items.cantidad"},
                "veces_vendido": {"$sum": 1},
                "ultimo_venta": {"$max": "$fecha"}
            }
        },
        {"$sort": {"cantidad_vendida": -1, "veces_vendido": -1}},
        {"$limit": limit * 2}  # Obtener más por si algunos están inactivos
    ]
    
    top_vendidos = await db.ventas.aggregate(pipeline).to_list(limit * 2)
    
    # Si no hay ventas, devolver productos populares por defecto
    if not top_vendidos:
        # Obtener productos más recientes activos
        productos = await db.productos_inventario.find({
            "origen": "clinica",
            "activo": True
        }).sort("created_at", -1).limit(limit).to_list(limit)
    else:
        # Obtener los productos
        producto_ids = [v["_id"] for v in top_vendidos]
        productos = await db.productos_inventario.find({
            "id": {"$in": producto_ids},
            "origen": "clinica",
            "activo": True
        }).to_list(limit * 2)
        
        # Ordenar por cantidad vendida
        productos_map = {p["id"]: p for p in productos}
        productos = [productos_map[v["_id"]] for v in top_vendidos if v["_id"] in productos_map]
    
    # Obtener categorías
    categorias = {c["id"]: c["nombre"] for c in await db.categorias_inventario.find({"origen": "clinica"}).to_list(100)}
    
    # Obtener existencias si hay bodega
    existencias_map = {}
    if bodega_id:
        existencias = await db.existencias_inventario.find({
            "bodega_id": bodega_id,
            "origen": "clinica"
        }).to_list(1000)
        existencias_map = {e["producto_id"]: e.get("cantidad", 0) for e in existencias}

    # Existencia TOTAL (todas las bodegas)
    from routes.inventario import obtener_existencias_totales
    totales_map = await obtener_existencias_totales(db, [p["id"] for p in productos[:limit]])

    resultado = []
    for p in productos[:limit]:
        controla_inv = p.get("controla_inventario", True)
        # Si no controla inventario, mostrar existencia como -1 (ilimitado)
        existencia = existencias_map.get(p["id"], 0) if bodega_id and controla_inv else (-1 if not controla_inv else 0)
        existencia_total = totales_map.get(p["id"], 0) if controla_inv else -1
        
        resultado.append(ProductoPOSResponse(
            id=p["id"],
            codigo=p.get("codigo", ""),
            nombre=p["nombre"],
            categoria_nombre=categorias.get(p.get("categoria_id")),
            precio_venta=p.get("precio_venta", 0),
            precio_compra=p.get("precio_compra", 0) or 0,
            afecto_iva=p.get("afecto_iva", True),
            existencia=existencia,
            existencia_total=existencia_total,
            controla_inventario=controla_inv,
            controla_lotes=p.get("controla_lotes", False),
            requiere_receta=p.get("requiere_receta", False),
            imagen=p.get("imagen")
        ))
    
    return resultado

@router.get("/bodega-pos")
async def obtener_bodega_pos(
    current_user: dict = Depends(get_current_user_dependency())
):
    """
    Obtiene la bodega configurada como punto de venta predeterminado.
    Si no hay configuración, devuelve la primera bodega activa marcada como punto de venta.
    """
    db = get_db()
    
    # Buscar en configuración
    config = await db.config_inventario.find_one({"origen": "clinica"})
    bodega_id = config.get("bodega_predeterminada_pos") if config else None
    
    if bodega_id:
        bodega = await db.bodegas_inventario.find_one({"id": bodega_id, "origen": "clinica"})
        # Tratar 'activo' ausente como activo (bodegas creadas por seed/import pueden no tener el campo)
        if bodega and bodega.get("activo", True) is not False:
            return {"bodega_id": bodega["id"], "bodega_nombre": bodega["nombre"]}
    
    # Buscar primera bodega marcada como punto de venta
    bodega = await db.bodegas_inventario.find_one({
        "origen": "clinica",
        "activo": {"$ne": False},
        "es_punto_venta": True
    })
    
    if bodega:
        return {"bodega_id": bodega["id"], "bodega_nombre": bodega["nombre"]}
    
    # Si no hay ninguna, devolver la primera activa (o sin el campo 'activo')
    bodega = await db.bodegas_inventario.find_one({
        "origen": "clinica",
        "activo": {"$ne": False}
    })
    
    if bodega:
        return {"bodega_id": bodega["id"], "bodega_nombre": bodega["nombre"]}
    
    raise HTTPException(status_code=404, detail="No hay bodegas configuradas para punto de venta")

@router.post("/verificar-stock")
async def verificar_stock_items(
    items: List[dict] = Body(...),
    bodega_id: str = Body(...),
    current_user: dict = Depends(get_current_user_dependency())
):
    """
    Verifica el stock disponible de una lista de items antes de confirmar la venta.
    Retorna items con información de disponibilidad.
    """
    db = get_db()
    
    resultado = []
    tiene_problemas = False
    
    for item in items:
        producto = await db.productos_inventario.find_one({
            "id": item["producto_id"],
            "origen": "clinica"
        })
        
        if not producto:
            resultado.append({
                **item,
                "disponible": False,
                "existencia": 0,
                "mensaje": "Producto no encontrado"
            })
            tiene_problemas = True
            continue
        
        # Si es servicio, no verificar stock
        if producto.get("tipo") == "servicio" or not producto.get("controla_inventario", True):
            resultado.append({
                **item,
                "disponible": True,
                "existencia": -1,  # Indica que no aplica
                "mensaje": "Servicio - no requiere stock"
            })
            continue
        
        # Verificar existencia
        existencia = await obtener_existencia_bodega(db, item["producto_id"], bodega_id)
        cantidad_requerida = item.get("cantidad", 1)
        
        # Verificar configuración de existencia negativa
        config = await db.config_inventario.find_one({"origen": "clinica"})
        permitir_negativo = config.get("permitir_existencia_negativa", False) if config else False
        
        if existencia >= cantidad_requerida or permitir_negativo:
            resultado.append({
                **item,
                "disponible": True,
                "existencia": existencia,
                "mensaje": "Stock disponible" if existencia >= cantidad_requerida else "Stock insuficiente (negativo permitido)"
            })
        else:
            resultado.append({
                **item,
                "disponible": False,
                "existencia": existencia,
                "mensaje": f"Stock insuficiente. Disponible: {existencia}, Requerido: {cantidad_requerida}"
            })
            tiene_problemas = True
    
    return {
        "items": resultado,
        "puede_proceder": not tiene_problemas,
        "mensaje": "Stock verificado" if not tiene_problemas else "Algunos productos tienen problemas de stock"
    }

@router.post("", response_model=VentaResponse)
async def crear_venta(
    venta: VentaCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """
    Crea una nueva venta y descuenta inventario usando FEFO.
    También registra el movimiento en caja diaria si corresponde.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    fecha_hoy = today_str_gt()
    
    # El permiso manage_sales ya se valida en get_current_user_dependency().
    # Validar que hay items
    if not venta.items or len(venta.items) == 0:
        raise HTTPException(status_code=400, detail="La venta debe tener al menos un producto")
    
    # Validar formas de pago
    if not venta.formas_pago or len(venta.formas_pago) == 0:
        raise HTTPException(status_code=400, detail="Debe especificar al menos una forma de pago")
    
    # Verificar bodega
    bodega = await db.bodegas_inventario.find_one({"id": venta.bodega_id, "origen": "clinica"})
    if not bodega:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    
    # Verificar que la caja esté abierta
    caja_abierta = await db.caja_cierres.find_one({
        "fecha": fecha_hoy,
        "origen": "clinica",
        "estado": "Abierto"
    })
    if not caja_abierta:
        raise HTTPException(status_code=400, detail="La caja del día no está abierta. Debe abrir caja antes de realizar ventas.")
    
    # Calcular totales
    subtotal = 0
    descuento_total = 0
    afecto_subtotal = 0
    items_procesados = []
    items_para_descuento = []
    
    for item in venta.items:
        # Obtener producto para validar
        producto = await db.productos_inventario.find_one({
            "id": item.producto_id,
            "origen": "clinica"
        })
        
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no encontrado")
        
        if not producto.get("activo", True):
            raise HTTPException(status_code=400, detail=f"Producto '{producto['nombre']}' no está activo")
        
        # Precio variable: validar que no sea menor al costo registrado del artículo.
        # Un renglón NO variable usa siempre el precio de lista (no se puede alterar).
        precio_lista = producto.get("precio_venta", item.precio_unitario)
        costo = producto.get("precio_compra", 0) or 0
        if item.precio_variable:
            precio_aplicado = item.precio_unitario
            if costo > 0 and precio_aplicado < costo:
                raise HTTPException(
                    status_code=400,
                    detail=f"El precio de '{producto['nombre']}' no puede ser menor al costo (Q{costo:.2f})"
                )
        else:
            precio_aplicado = precio_lista
        
        # Calcular subtotal del item
        item_subtotal = item.cantidad * precio_aplicado - item.descuento
        subtotal += item_subtotal
        descuento_total += item.descuento
        
        # Base afecta a IVA (el IVA se calcula luego del descuento global)
        if item.afecto_iva:
            afecto_subtotal += item_subtotal
        
        items_procesados.append({
            "producto_id": item.producto_id,
            "codigo": producto.get("codigo", ""),
            "nombre": producto["nombre"],
            "cantidad": item.cantidad,
            "precio_unitario": precio_aplicado,
            "descuento": item.descuento,
            "subtotal": item_subtotal,
            "afecto_iva": item.afecto_iva,
            "precio_variable": item.precio_variable,
            "precio_lista": precio_lista if item.precio_variable else None,
            "lotes_consumidos": []
        })
        
        # Agregar a lista para descuento de inventario (solo si controla inventario)
        if producto.get("controla_inventario", True):
            items_para_descuento.append({
                "producto_id": item.producto_id,
                "cantidad": item.cantidad
            })
    
    # Descuento global por porcentaje sobre el total de la venta
    descuento_pct = venta.descuento_porcentaje or 0
    descuento_monto = round(subtotal * descuento_pct / 100, 2) if descuento_pct > 0 else 0
    if descuento_monto > 0 and not (venta.descuento_autoriza or "").strip():
        raise HTTPException(status_code=400, detail="Debe indicar quién autoriza el descuento")
    descuento_autoriza = (venta.descuento_autoriza or "").strip()
    # El precio ya incluye el IVA: el total es la suma de precios menos el descuento,
    # SIN sumar 12% por encima. El IVA se calcula "hacia adentro" (parte ya incluida)
    # sobre el total con descuento aplicado, solo para efectos contables.
    descuento_total = round(descuento_total + descuento_monto, 2)
    total = round(subtotal - descuento_monto, 2)
    iva_total = round(total - total / 1.12, 2)
    
    # Validar que las formas de pago cubren el total
    total_pagado = sum(fp.monto for fp in venta.formas_pago)
    if total_pagado < total:
        raise HTTPException(
            status_code=400, 
            detail=f"El monto pagado ({total_pagado:.2f}) no cubre el total ({total:.2f})"
        )
    
    # Calcular efectivo recibido y cambio
    efectivo_recibido = sum(fp.monto for fp in venta.formas_pago if fp.metodo == "Efectivo")
    cambio = max(0, total_pagado - total)
    
    # Generar número de venta
    numero_venta = await generar_numero_venta(db)
    venta_id = str(uuid.uuid4())
    
    # Descontar inventario
    if items_para_descuento:
        resultado_descuento = await descontar_inventario_pos(
            db=db,
            items=items_para_descuento,
            bodega_id=venta.bodega_id,
            referencia_tipo="venta",
            referencia_id=venta_id,
            usuario_id=current_user["id"]
        )
        
        if not resultado_descuento["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Error al descontar inventario: {resultado_descuento['error']}"
            )
        
        # Actualizar items con información de lotes consumidos
        lotes_por_producto = {}
        for detalle in resultado_descuento.get("detalle", []):
            pid = detalle["producto_id"]
            if pid not in lotes_por_producto:
                lotes_por_producto[pid] = []
            lotes_por_producto[pid].append(detalle)
        
        for item in items_procesados:
            item["lotes_consumidos"] = lotes_por_producto.get(item["producto_id"], [])
    
    # Procesar formas de pago
    formas_pago_procesadas = []
    movimiento_caja_id = None
    cxc_id = None
    
    for fp in venta.formas_pago:
        fp_dict = {
            "metodo": fp.metodo,
            "monto": fp.monto,
            "referencia": fp.referencia
        }
        
        if fp.metodo == "Cuenta por Cobrar":
            fp_dict["tipo_pagador_id"] = fp.tipo_pagador_id
            fp_dict["tipo_pagador_nombre"] = fp.tipo_pagador_nombre
            
            # Buscar información del responsable en el catálogo de CxC
            responsable_nombre = fp.tipo_pagador_nombre or "Otro"
            tipo_responsable = "otro"
            
            if fp.tipo_pagador_id:
                responsable_doc = await db.responsables_cxc.find_one(
                    {"id": fp.tipo_pagador_id, "is_active": True},
                    {"_id": 0}
                )
                if responsable_doc:
                    responsable_nombre = responsable_doc.get("nombre", fp.tipo_pagador_nombre or "Otro")
                    tipo_responsable = responsable_doc.get("tipo", "otro")
            
            # Crear cuenta por cobrar con el nuevo esquema
            cxc_id = str(uuid.uuid4())
            cxc_doc = {
                "id": cxc_id,
                "origen": "clinica",
                "numero_cuenta": f"CXC-CLI-{now_gt().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
                "paciente_id": venta.paciente_id,
                "paciente_nombre": venta.paciente_nombre or "Cliente General",
                # Campos del nuevo sistema de responsables
                "responsable_id": fp.tipo_pagador_id,
                "responsable_nombre": responsable_nombre,
                "tipo_responsable": tipo_responsable,
                # Campos legacy para compatibilidad
                "tipo_pagador_id": fp.tipo_pagador_id,
                "tipo_pagador_nombre": responsable_nombre,
                "pagador_nombre": responsable_nombre,
                "concepto": ", ".join(it["nombre"] for it in items_procesados) if items_procesados else f"Venta {numero_venta}",
                "descripcion": None,
                "referencia": numero_venta,
                "monto_total": fp.monto,
                "monto_pagado": 0,
                "saldo_pendiente": fp.monto,
                "estado": "Pendiente",
                "fecha_emision": fecha_hoy,
                "fecha_vencimiento": None,
                "notas": f"Generado automáticamente por venta {numero_venta}",
                "abonos": [],
                "venta_id": venta_id,
                "creado_por": current_user["id"],
                "creado_por_nombre": current_user.get("name"),
                "fecha_creacion": now.isoformat()
            }
            await db.cuentas_por_cobrar.insert_one(cxc_doc)
            fp_dict["cxc_id"] = cxc_id
        
        formas_pago_procesadas.append(fp_dict)
    
    # Registrar movimiento en caja (para métodos que no son CxC)
    monto_a_caja = sum(fp.monto for fp in venta.formas_pago if fp.metodo != "Cuenta por Cobrar")
    
    if monto_a_caja > 0:
        # Determinar método de pago principal para el movimiento de caja
        metodos_caja = [fp for fp in venta.formas_pago if fp.metodo != "Cuenta por Cobrar"]
        metodo_principal = metodos_caja[0].metodo if metodos_caja else "Efectivo"
        
        movimiento_caja_id = str(uuid.uuid4())
        mov_caja = {
            "id": movimiento_caja_id,
            "origen": "clinica",
            "fecha": now.isoformat(),
            "tipo": "Ingreso",
            "categoria": "Venta",
            "concepto": f"Venta {numero_venta}" + (f" - {venta.paciente_nombre}" if venta.paciente_nombre else ""),
            "monto": monto_a_caja,
            "metodo_pago": metodo_principal,
            "referencia": numero_venta,
            "paciente_id": venta.paciente_id,
            "paciente_nombre": venta.paciente_nombre,
            "bloqueado": False,
            "venta_id": venta_id,
            "cajero_id": current_user["id"],
            "cajero_nombre": current_user.get("name"),
            "creado_por": current_user["id"],
            "creado_por_nombre": current_user.get("name"),
            "fecha_creacion": now.isoformat()
        }
        await db.caja_movimientos.insert_one(mov_caja)
    
    # Crear documento de venta
    venta_doc = {
        "id": venta_id,
        "numero_venta": numero_venta,
        "fecha": now.isoformat(),
        "bodega_id": venta.bodega_id,
        "bodega_nombre": bodega.get("nombre"),
        "paciente_id": venta.paciente_id,
        "paciente_nombre": venta.paciente_nombre,
        "medico_id": venta.medico_id,
        "medico_nombre": venta.medico_nombre,
        "items": items_procesados,
        "cantidad_items": sum(item["cantidad"] for item in items_procesados),
        "subtotal": round(subtotal, 2),
        "descuento_total": round(descuento_total, 2),
        "descuento_porcentaje": descuento_pct,
        "descuento_monto": descuento_monto,
        "descuento_autoriza": descuento_autoriza,
        "iva": round(iva_total, 2),
        "total": round(total, 2),
        "formas_pago": formas_pago_procesadas,
        "efectivo_recibido": round(efectivo_recibido, 2),
        "cambio": round(cambio, 2),
        "estado": "completada",
        "caja_sesion_id": caja_abierta.get("id"),
        "movimiento_caja_id": movimiento_caja_id,
        "cxc_id": cxc_id,
        "observaciones": venta.observaciones,
        "vendedor_id": current_user["id"],
        "vendedor_nombre": current_user.get("name"),
        "origen": "clinica",
        "created_at": now.isoformat(),
        # FEL Guatemala (deshabilitado por ahora)
        "datos_fel": venta.datos_fel,
        "fel_uuid": None,
        "fel_numero": None
    }
    
    await db.ventas.insert_one(venta_doc)
    
    logger.info(f"Venta {numero_venta} creada exitosamente. Total: Q{total:.2f}")
    
    return VentaResponse(**venta_doc)

@router.get("", response_model=VentaListResponse)
async def listar_ventas(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    paciente_id: Optional[str] = None,
    estado: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista ventas con filtros y paginación"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    
    if fecha_desde or fecha_hasta:
        rango = {}
        try:
            if fecha_desde:
                rango["$gte"] = dia_gt_a_rango_utc(fecha_desde)[0]
            if fecha_hasta:
                rango["$lte"] = dia_gt_a_rango_utc(fecha_hasta)[1]
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Fechas inválidas (use formato YYYY-MM-DD)")
        filtro["fecha"] = rango
    if paciente_id:
        filtro["paciente_id"] = paciente_id
    if estado:
        filtro["estado"] = estado
    if search:
        import re
        patron = re.escape(search.strip())
        filtro["$or"] = [
            {"numero_venta": {"$regex": patron, "$options": "i"}},
            {"paciente_nombre": {"$regex": patron, "$options": "i"}}
        ]
    
    total = await db.ventas.count_documents(filtro)
    skip = (page - 1) * limit
    
    ventas = await db.ventas.find(filtro, {"_id": 0}).sort("fecha", -1).skip(skip).limit(limit).to_list(limit)
    
    return VentaListResponse(
        data=[VentaResponse(**v) for v in ventas],
        total=total,
        page=page,
        limit=limit
    )

@router.get("/hoy")
async def ventas_del_dia(
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene las ventas del día actual"""
    db = get_db()
    fecha_hoy = today_str_gt()
    _ini, _fin = dia_gt_a_rango_utc(fecha_hoy)
    
    ventas = await db.ventas.find({
        "origen": "clinica",
        "fecha": {"$gte": _ini, "$lte": _fin}
    }, {"_id": 0}).sort("fecha", -1).to_list(500)
    
    return {"data": ventas, "total": len(ventas)}

@router.get("/resumen-dia", response_model=ResumenVentasDia)
async def resumen_ventas_dia(
    fecha: Optional[str] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene un resumen de las ventas del día"""
    db = get_db()
    fecha_consulta = fecha or today_str_gt()
    _ini, _fin = dia_gt_a_rango_utc(fecha_consulta)
    
    ventas = await db.ventas.find({
        "origen": "clinica",
        "estado": "completada",
        "fecha": {"$gte": _ini, "$lte": _fin}
    }, {"_id": 0}).to_list(500)
    
    total_ventas = len(ventas)
    total_monto = sum(v.get("total", 0) for v in ventas)
    
    # Por método de pago
    por_metodo = {"Efectivo": 0, "Tarjeta": 0, "Transferencia": 0, "Cheque": 0, "Cuenta por Cobrar": 0}
    for v in ventas:
        for fp in v.get("formas_pago", []):
            metodo = fp.get("metodo", "Efectivo")
            if metodo in por_metodo:
                por_metodo[metodo] += fp.get("monto", 0)
    
    # Por categoría (necesita lookup a productos)
    productos_vendidos = {}
    categorias_monto = {}
    
    for v in ventas:
        for item in v.get("items", []):
            pid = item.get("producto_id")
            nombre = item.get("nombre", "")
            cantidad = item.get("cantidad", 0)
            subtotal = item.get("subtotal", 0)
            
            if pid in productos_vendidos:
                productos_vendidos[pid]["cantidad"] += cantidad
                productos_vendidos[pid]["monto"] += subtotal
            else:
                productos_vendidos[pid] = {
                    "producto_id": pid,
                    "nombre": nombre,
                    "cantidad": cantidad,
                    "monto": subtotal
                }
    
    # Top 10 productos más vendidos
    productos_ordenados = sorted(productos_vendidos.values(), key=lambda x: x["cantidad"], reverse=True)[:10]
    
    return ResumenVentasDia(
        total_ventas=total_ventas,
        total_monto=round(total_monto, 2),
        por_metodo_pago=por_metodo,
        por_categoria=[],  # TODO: Agregar categorías si se necesita
        productos_mas_vendidos=productos_ordenados
    )

def require_superadmin_dep():
    """Dependencia: solo superadmin."""
    from server import get_current_user

    async def _dep(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Solo el superadministrador puede ver este análisis")
        return current_user

    return _dep


@router.get("/analisis")
async def analisis_produccion(
    periodo: str = Query("hoy"),
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    current_user: dict = Depends(require_superadmin_dep())
):
    """Análisis de producción de ventas de clínica (POS). Solo superadmin."""
    db = get_db()
    n = now_gt()
    hoy = n.strftime("%Y-%m-%d")

    if periodo == "semana":
        start = n - timedelta(days=n.weekday())
        f_desde, f_hasta = start.strftime("%Y-%m-%d"), hoy
    elif periodo == "mes":
        f_desde, f_hasta = n.strftime("%Y-%m-01"), hoy
    elif periodo == "rango" and desde and hasta:
        f_desde, f_hasta = desde, hasta
    else:
        f_desde, f_hasta = hoy, hoy
    if f_desde > f_hasta:
        f_desde, f_hasta = f_hasta, f_desde

    try:
        ini = dia_gt_a_rango_utc(f_desde)[0]
        fin = dia_gt_a_rango_utc(f_hasta)[1]
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Fechas inválidas (use formato YYYY-MM-DD)")

    ventas = await db.ventas.find({
        "origen": "clinica",
        "estado": "completada",
        "fecha": {"$gte": ini, "$lte": fin}
    }, {"_id": 0}).to_list(20000)

    num_ventas = len(ventas)
    total_vendido = round(sum(v.get("total", 0) or 0 for v in ventas), 2)
    ticket_promedio = round(total_vendido / num_ventas, 2) if num_ventas else 0.0

    productos = {}
    por_cajero = {}
    por_medico = {}
    tendencia = {}
    producto_ids = set()

    for v in ventas:
        # Tendencia por día (hora Guatemala)
        try:
            dia = datetime.fromisoformat(v["fecha"]).astimezone(GUATEMALA_TZ).strftime("%Y-%m-%d")
        except Exception:
            dia = (v.get("fecha") or "")[:10]
        t = tendencia.setdefault(dia, {"fecha": dia, "monto": 0.0, "num_ventas": 0})
        t["monto"] += v.get("total", 0) or 0
        t["num_ventas"] += 1

        # Por cajero / vendedor
        cid = v.get("vendedor_id") or "sin"
        rc = por_cajero.setdefault(cid, {
            "vendedor_id": cid,
            "vendedor_nombre": v.get("vendedor_nombre") or "Sin vendedor",
            "monto": 0.0, "num_ventas": 0
        })
        rc["monto"] += v.get("total", 0) or 0
        rc["num_ventas"] += 1

        # Por médico que refiere
        mid = v.get("medico_id") or "sin"
        rm = por_medico.setdefault(mid, {
            "medico_id": mid,
            "medico_nombre": v.get("medico_nombre") or "Sin médico",
            "monto": 0.0, "num_ventas": 0
        })
        rm["monto"] += v.get("total", 0) or 0
        rm["num_ventas"] += 1

        # Productos
        for item in v.get("items", []):
            pid = item.get("producto_id")
            if pid:
                producto_ids.add(pid)
            p = productos.setdefault(pid, {
                "producto_id": pid,
                "nombre": item.get("nombre", ""),
                "cantidad": 0, "monto": 0.0
            })
            p["cantidad"] += item.get("cantidad", 0) or 0
            p["monto"] += item.get("subtotal", 0) or 0

    # Categorías: lookup producto -> categoria_id -> nombre
    cat_de_producto = {}
    if producto_ids:
        async for pr in db.productos_inventario.find(
            {"id": {"$in": list(producto_ids)}}, {"_id": 0, "id": 1, "categoria_id": 1}
        ):
            cat_de_producto[pr["id"]] = pr.get("categoria_id")
    cat_ids = {c for c in cat_de_producto.values() if c}
    nombre_categoria = {}
    if cat_ids:
        async for c in db.categorias_inventario.find(
            {"id": {"$in": list(cat_ids)}}, {"_id": 0, "id": 1, "nombre": 1}
        ):
            nombre_categoria[c["id"]] = c.get("nombre")

    por_categoria = {}
    for p in productos.values():
        cat_id = cat_de_producto.get(p["producto_id"])
        cat_nombre = nombre_categoria.get(cat_id, "Sin categoría") if cat_id else "Sin categoría"
        rcat = por_categoria.setdefault(cat_nombre, {"categoria": cat_nombre, "monto": 0.0, "cantidad": 0})
        rcat["monto"] += p["monto"]
        rcat["cantidad"] += p["cantidad"]

    def _round_list(items, keys=("monto",)):
        for it in items:
            for k in keys:
                if k in it:
                    it[k] = round(it[k], 2)
        return items

    prod_list = list(productos.values())
    top_ingresos = _round_list(sorted(prod_list, key=lambda x: x["monto"], reverse=True)[:10])
    top_unidades = _round_list(sorted(prod_list, key=lambda x: x["cantidad"], reverse=True)[:10])

    return {
        "periodo": periodo,
        "desde": f_desde,
        "hasta": f_hasta,
        "kpis": {
            "total_vendido": total_vendido,
            "num_ventas": num_ventas,
            "ticket_promedio": ticket_promedio,
        },
        "top_productos_ingresos": top_ingresos,
        "top_productos_unidades": top_unidades,
        "por_cajero": _round_list(sorted(por_cajero.values(), key=lambda x: x["monto"], reverse=True)),
        "por_medico": _round_list(sorted(por_medico.values(), key=lambda x: x["monto"], reverse=True)),
        "por_categoria": _round_list(sorted(por_categoria.values(), key=lambda x: x["monto"], reverse=True)),
        "tendencia": _round_list(sorted(tendencia.values(), key=lambda x: x["fecha"])),
    }


# ==================== DASHBOARD DE VENTAS DE CLÍNICA ====================

def _rango_mes_utc(year: int, month: int):
    """Devuelve (inicio_utc, fin_utc) ISO para un mes en zona horaria de Guatemala."""
    from calendar import monthrange
    last_day = monthrange(year, month)[1]
    ini = dia_gt_a_rango_utc(f"{year}-{month:02d}-01")[0]
    fin = dia_gt_a_rango_utc(f"{year}-{month:02d}-{last_day:02d}")[1]
    return ini, fin


@router.get("/dashboard/stats")
async def ventas_dashboard_stats(
    current_user: dict = Depends(get_current_user_dependency())
):
    """Estadísticas del mes actual para el módulo de Ventas de Clínica."""
    db = get_db()
    n = now_gt()
    ini_mes, fin_mes = _rango_mes_utc(n.year, n.month)

    ventas_mes = await db.ventas.find({
        "origen": "clinica", "estado": "completada",
        "fecha": {"$gte": ini_mes, "$lte": fin_mes}
    }, {"_id": 0, "total": 1}).to_list(5000)
    total_mes = round(sum(v.get("total", 0) or 0 for v in ventas_mes), 2)
    ordenes_mes = len(ventas_mes)
    ticket_promedio = round(total_mes / ordenes_mes, 2) if ordenes_mes else 0

    anuladas_mes = await db.ventas.count_documents({
        "origen": "clinica", "estado": "anulada",
        "fecha": {"$gte": ini_mes, "$lte": fin_mes}
    })

    hoy = today_str_gt()
    ini_hoy, fin_hoy = dia_gt_a_rango_utc(hoy)
    ventas_hoy = await db.ventas.find({
        "origen": "clinica", "estado": "completada",
        "fecha": {"$gte": ini_hoy, "$lte": fin_hoy}
    }, {"_id": 0, "total": 1}).to_list(2000)
    total_hoy = round(sum(v.get("total", 0) or 0 for v in ventas_hoy), 2)

    return {
        "ventas_mes": total_mes,
        "ordenes_mes": ordenes_mes,
        "ticket_promedio": ticket_promedio,
        "ventas_hoy": total_hoy,
        "ordenes_hoy": len(ventas_hoy),
        "anuladas_mes": anuladas_mes,
    }


@router.get("/dashboard/monthly-chart")
async def ventas_monthly_chart(
    current_user: dict = Depends(get_current_user_dependency())
):
    """Ventas de clínica de los últimos 6 meses."""
    db = get_db()
    month_names = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    n = now_gt()
    chart = []
    year, month = n.year, n.month
    meses = []
    for _ in range(6):
        meses.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    for (y, m) in reversed(meses):
        ini, fin = _rango_mes_utc(y, m)
        ventas = await db.ventas.find({
            "origen": "clinica", "estado": "completada",
            "fecha": {"$gte": ini, "$lte": fin}
        }, {"_id": 0, "total": 1}).to_list(5000)
        chart.append({
            "mes": f"{month_names[m]} {y}",
            "ventas": round(sum(v.get("total", 0) or 0 for v in ventas), 2),
            "ordenes": len(ventas),
        })
    return chart


async def _ventas_mes_items(db):
    """Ventas completadas del mes actual (con items) para rankings."""
    n = now_gt()
    ini, fin = _rango_mes_utc(n.year, n.month)
    return await db.ventas.find({
        "origen": "clinica", "estado": "completada",
        "fecha": {"$gte": ini, "$lte": fin}
    }, {"_id": 0}).to_list(5000)


@router.get("/dashboard/top-medicos")
async def ventas_top_medicos(
    limit: int = 5,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Top médicos que refieren ventas en el mes actual."""
    db = get_db()
    ventas = await _ventas_mes_items(db)
    agg = {}
    for v in ventas:
        nombre = v.get("medico_nombre")
        if not nombre:
            continue
        r = agg.setdefault(nombre, {"medico_nombre": nombre, "total_ventas": 0.0, "count": 0})
        r["total_ventas"] += v.get("total", 0) or 0
        r["count"] += 1
    for r in agg.values():
        r["total_ventas"] = round(r["total_ventas"], 2)
    return sorted(agg.values(), key=lambda x: x["total_ventas"], reverse=True)[:limit]


@router.get("/dashboard/top-productos")
async def ventas_top_productos(
    limit: int = 5,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Top productos más vendidos (por unidades) en el mes actual."""
    db = get_db()
    ventas = await _ventas_mes_items(db)
    agg = {}
    for v in ventas:
        for item in v.get("items", []):
            nombre = item.get("nombre", "Producto")
            r = agg.setdefault(nombre, {"nombre": nombre, "cantidad": 0, "total_ventas": 0.0})
            r["cantidad"] += item.get("cantidad", 0) or 0
            r["total_ventas"] += item.get("subtotal", 0) or 0
    for r in agg.values():
        r["total_ventas"] = round(r["total_ventas"], 2)
    return sorted(agg.values(), key=lambda x: x["cantidad"], reverse=True)[:limit]


@router.get("/dashboard/top-categorias")
async def ventas_top_categorias(
    limit: int = 5,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Top categorías de producto por ventas en el mes actual."""
    db = get_db()
    ventas = await _ventas_mes_items(db)
    productos = {}
    producto_ids = set()
    for v in ventas:
        for item in v.get("items", []):
            pid = item.get("producto_id")
            if pid:
                producto_ids.add(pid)
            p = productos.setdefault(pid, {"cantidad": 0, "monto": 0.0})
            p["cantidad"] += item.get("cantidad", 0) or 0
            p["monto"] += item.get("subtotal", 0) or 0
    cat_de_producto = {}
    if producto_ids:
        async for pr in db.productos_inventario.find(
            {"id": {"$in": list(producto_ids)}}, {"_id": 0, "id": 1, "categoria_id": 1}
        ):
            cat_de_producto[pr["id"]] = pr.get("categoria_id")
    cat_ids = {c for c in cat_de_producto.values() if c}
    nombre_categoria = {}
    if cat_ids:
        async for c in db.categorias_inventario.find(
            {"id": {"$in": list(cat_ids)}}, {"_id": 0, "id": 1, "nombre": 1}
        ):
            nombre_categoria[c["id"]] = c.get("nombre")
    agg = {}
    for pid, p in productos.items():
        cat_id = cat_de_producto.get(pid)
        cat_nombre = nombre_categoria.get(cat_id, "Sin categoría") if cat_id else "Sin categoría"
        r = agg.setdefault(cat_nombre, {"categoria": cat_nombre, "cantidad": 0, "total_ventas": 0.0})
        r["cantidad"] += p["cantidad"]
        r["total_ventas"] += p["monto"]
    for r in agg.values():
        r["total_ventas"] = round(r["total_ventas"], 2)
    return sorted(agg.values(), key=lambda x: x["total_ventas"], reverse=True)[:limit]


@router.get("/reports/monthly")
async def ventas_reporte_mensual(
    year: int,
    month: int,
    format: str = "excel",
    current_user: dict = Depends(get_current_user_dependency())
):
    """Exporta el informe mensual de ventas de clínica en Excel o PDF."""
    import io
    from fastapi.responses import StreamingResponse
    db = get_db()
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Mes inválido")
    ini, fin = _rango_mes_utc(year, month)
    ventas = await db.ventas.find({
        "origen": "clinica",
        "fecha": {"$gte": ini, "$lte": fin}
    }, {"_id": 0}).sort("fecha", 1).to_list(10000)

    month_names = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    titulo = f"Ventas de Clínica - {month_names[month]} {year}"

    def _fecha_corta(iso):
        try:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(GUATEMALA_TZ)
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return iso or ""

    completadas = [v for v in ventas if v.get("estado") == "completada"]
    total_vendido = round(sum(v.get("total", 0) or 0 for v in completadas), 2)
    filas = []
    for v in ventas:
        filas.append([
            v.get("numero_venta", ""),
            _fecha_corta(v.get("fecha", "")),
            v.get("paciente_nombre") or "Consumidor Final",
            v.get("medico_nombre") or "-",
            v.get("vendedor_nombre") or "-",
            round(v.get("total", 0) or 0, 2),
            "Anulada" if v.get("estado") == "anulada" else "Completada",
        ])

    headers = ["Orden", "Fecha", "Cliente", "Médico", "Vendedor", "Total (Q)", "Estado"]
    fname_base = f"ventas_clinica_{year}_{month:02d}"

    if format == "excel":
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        wb = Workbook()
        ws = wb.active
        ws.title = "Ventas"
        ws.merge_cells("A1:G1")
        ws["A1"] = titulo
        ws["A1"].font = Font(size=14, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center")
        ws.append([])
        ws.append(headers)
        header_fill = PatternFill(start_color="0F6E56", end_color="0F6E56", fill_type="solid")
        for col in range(1, len(headers) + 1):
            c = ws.cell(row=3, column=col)
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = header_fill
        for fila in filas:
            ws.append(fila)
        ws.append([])
        ws.append(["", "", "", "", "TOTAL VENDIDO", total_vendido, ""])
        ws.cell(row=ws.max_row, column=5).font = Font(bold=True)
        ws.cell(row=ws.max_row, column=6).font = Font(bold=True)
        widths = [18, 18, 30, 24, 22, 14, 14]
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[chr(64 + i)].width = w
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={fname_base}.xlsx"}
        )

    elif format == "pdf":
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(letter), topMargin=1*cm, bottomMargin=1*cm)
        styles = getSampleStyleSheet()
        elems = [Paragraph(titulo, styles["Title"]), Spacer(1, 8)]
        data = [headers] + [[str(c) for c in fila] for fila in filas]
        data.append(["", "", "", "", "TOTAL", f"{total_vendido:,.2f}", ""])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F6E56")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("ALIGN", (5, 1), (5, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F1F5F9")]),
        ]))
        elems.append(t)
        doc.build(elems)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={fname_base}.pdf"}
        )

    raise HTTPException(status_code=400, detail="Formato inválido (excel|pdf)")


@router.get("/{venta_id}", response_model=VentaResponse)
async def obtener_venta(
    venta_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene una venta por ID"""
    db = get_db()
    
    venta = await db.ventas.find_one({"id": venta_id, "origen": "clinica"}, {"_id": 0})
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    return VentaResponse(**venta)

@router.post("/{venta_id}/anular")
async def anular_venta(
    venta_id: str,
    anulacion: AnularVentaRequest,
    current_user: dict = Depends(get_current_user_dependency())
):
    """
    Anula una venta. Solo administradores (admin/superadmin) pueden anular.
    Opcionalmente devuelve el inventario al stock.
    """
    db = get_db()
    
    if current_user.get("role") not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="Solo administradores pueden anular ventas")
    
    venta = await db.ventas.find_one({"id": venta_id, "origen": "clinica"})
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    if venta.get("estado") == "anulada":
        raise HTTPException(status_code=400, detail="La venta ya está anulada")
    
    now = datetime.now(timezone.utc)
    
    # Devolver inventario si se solicita (solo si la venta tiene bodega registrada)
    if anulacion.devolver_inventario and venta.get("bodega_id"):
        from routes.inventario import crear_movimiento_kardex, actualizar_existencia
        
        for item in venta.get("items", []):
            producto_id = item.get("producto_id")
            if not producto_id:
                continue
            # Verificar si el producto controla inventario
            producto = await db.productos_inventario.find_one({"id": producto_id, "origen": "clinica"})
            if producto and producto.get("controla_inventario", True):
                # Crear movimiento de devolución
                await crear_movimiento_kardex(
                    db=db,
                    producto_id=producto_id,
                    bodega_id=venta["bodega_id"],
                    tipo="anulacion",
                    cantidad=item.get("cantidad", 0),
                    costo_unitario=producto.get("costo_promedio", 0),
                    usuario_id=current_user["id"],
                    referencia_tipo="anulacion_venta",
                    referencia_id=venta_id,
                    motivo=f"Anulación de venta {venta['numero_venta']}: {anulacion.motivo}"
                )
                
                # Actualizar existencia (devolver stock)
                await actualizar_existencia(db, producto_id, venta["bodega_id"], item.get("cantidad", 0))
                
                # Si hay lotes consumidos, restaurarlos
                for lote_info in item.get("lotes_consumidos", []):
                    if lote_info.get("lote_id"):
                        await db.lotes_inventario.update_one(
                            {"id": lote_info["lote_id"]},
                            {"$inc": {"cantidad_disponible": lote_info.get("cantidad", 0)}}
                        )
    
    # Anular movimiento de caja si existe
    if venta.get("movimiento_caja_id"):
        await db.caja_movimientos.update_one(
            {"id": venta["movimiento_caja_id"]},
            {"$set": {
                "anulado": True,
                "anulado_por": current_user["id"],
                "fecha_anulacion": now.isoformat(),
                "motivo_anulacion": anulacion.motivo
            }}
        )
    
    # Anular cuenta por cobrar si existe
    if venta.get("cxc_id"):
        await db.cuentas_por_cobrar.update_one(
            {"id": venta["cxc_id"]},
            {"$set": {
                "estado": "Cancelado",
                "notas": f"Anulada por anulación de venta: {anulacion.motivo}"
            }}
        )
    
    # Actualizar venta
    await db.ventas.update_one(
        {"id": venta_id},
        {"$set": {
            "estado": "anulada",
            "anulada_por": current_user["id"],
            "anulada_por_nombre": current_user.get("name"),
            "fecha_anulacion": now.isoformat(),
            "motivo_anulacion": anulacion.motivo,
            "inventario_devuelto": anulacion.devolver_inventario
        }}
    )
    
    logger.info(f"Venta {venta['numero_venta']} anulada por {current_user.get('name')}. Motivo: {anulacion.motivo}")
    
    return {
        "message": f"Venta {venta['numero_venta']} anulada exitosamente",
        "inventario_devuelto": anulacion.devolver_inventario
    }

@router.get("/{venta_id}/ticket")
async def obtener_ticket_venta(
    venta_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """
    Obtiene los datos formateados para impresión de ticket térmico.
    Optimizado para impresoras de 58mm y 80mm.
    """
    db = get_db()
    
    venta = await db.ventas.find_one({"id": venta_id, "origen": "clinica"}, {"_id": 0})
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    # Formatear fecha para Guatemala (GMT-6)
    fecha_dt = datetime.fromisoformat(venta["fecha"].replace("Z", "+00:00")).astimezone(GUATEMALA_TZ)
    fecha_formateada = fecha_dt.strftime("%d/%m/%Y %H:%M")
    
    # Obtener nombre del vendedor si existe
    vendedor_nombre = venta.get("vendedor_nombre", "")
    if not vendedor_nombre and venta.get("creado_por"):
        usuario = await db.users.find_one({"id": venta["creado_por"]})
        if usuario:
            vendedor_nombre = usuario.get("name", usuario.get("username", ""))
    
    # Obtener configuración de empresa (si existe)
    config = await db.configuracion.find_one({"origen": "clinica"})
    empresa_config = config.get("empresa", {}) if config else {}
    
    ticket_data = {
        "empresa": {
            "nombre": empresa_config.get("nombre", "Novavisión - Clínica Oftalmológica"),
            "direccion": empresa_config.get("direccion", ""),
            "nit": empresa_config.get("nit", ""),
            "telefono": empresa_config.get("telefono", "")
        },
        "venta": {
            "id": venta["id"],
            "numero": venta["numero_venta"],
            "fecha": fecha_formateada,
            "vendedor": vendedor_nombre
        },
        "cliente": {
            "nombre": venta.get("paciente_nombre") or "Consumidor Final",
            "id": venta.get("paciente_id"),
            "nit": venta.get("paciente_nit", "C/F")
        },
        "items": [
            {
                "cantidad": item["cantidad"],
                "nombre": item["nombre"],
                "precio_unitario": item["precio_unitario"],
                "descuento": item.get("descuento", 0),
                "subtotal": item["subtotal"]
            }
            for item in venta.get("items", [])
        ],
        "totales": {
            "subtotal": venta["subtotal"],
            "descuento": venta.get("descuento_total", 0),
            "iva": venta["iva"],
            "total": venta["total"]
        },
        "pago": {
            "formas": [
                {
                    "metodo": fp.get("metodo", "Efectivo"),
                    "monto": fp.get("monto", 0),
                    "referencia": fp.get("referencia", "")
                }
                for fp in venta.get("formas_pago", [])
            ],
            "efectivo_recibido": venta.get("efectivo_recibido", 0),
            "cambio": venta.get("cambio", 0)
        },
        "observaciones": venta.get("observaciones"),
        "estado": venta.get("estado")
    }
    
    return ticket_data
