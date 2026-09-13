# /app/backend/routes/ventas.py
# Módulo de Punto de Venta (POS) - NovaVision
# Integrado con Inventario (FEFO) y Caja Diaria
# IMPORTANTE: Este módulo está AISLADO del módulo de óptica (origen="clinica")

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
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
    items: List[VentaItem]
    formas_pago: List[FormaPago]
    observaciones: Optional[str] = None
    # FEL Guatemala - preparado pero deshabilitado
    datos_fel: Optional[dict] = None

class VentaResponse(BaseModel):
    """Respuesta de venta"""
    id: str
    numero_venta: str
    fecha: str
    bodega_id: str
    bodega_nombre: Optional[str] = None
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None
    items: List[dict]
    cantidad_items: int
    subtotal: float
    descuento_total: float
    iva: float
    total: float
    formas_pago: List[dict]
    efectivo_recibido: float = 0
    cambio: float = 0
    estado: str = "completada"
    caja_sesion_id: Optional[str] = None
    movimiento_caja_id: Optional[str] = None
    cxc_id: Optional[str] = None
    observaciones: Optional[str] = None
    vendedor_id: str
    vendedor_nombre: Optional[str] = None
    origen: str = "clinica"
    created_at: str
    # FEL
    datos_fel: Optional[dict] = None
    fel_uuid: Optional[str] = None
    fel_numero: Optional[str] = None

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
    afecto_iva: bool
    existencia: int
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
    """Genera número único para venta con formato VTA-YYYYMMDD-XXXX"""
    hoy = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefijo = f"VTA-{hoy}-"
    
    # Buscar la última venta del día
    ultima = await db.ventas.find_one(
        {"numero_venta": {"$regex": f"^{prefijo}"}},
        sort=[("numero_venta", -1)]
    )
    
    if ultima:
        try:
            ultimo_num = int(ultima["numero_venta"].split("-")[-1]) + 1
        except Exception:
            ultimo_num = 1
    else:
        ultimo_num = 1
    
    return f"{prefijo}{ultimo_num:04d}"

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
    
    resultado = []
    for p in productos:
        controla_inv = p.get("controla_inventario", True)
        # Si no controla inventario, mostrar existencia como -1 (ilimitado)
        existencia = existencias_map.get(p["id"], 0) if bodega_id and controla_inv else (-1 if not controla_inv else 0)
        
        resultado.append(ProductoPOSResponse(
            id=p["id"],
            codigo=p.get("codigo", ""),
            nombre=p["nombre"],
            categoria_nombre=categorias.get(p.get("categoria_id")),
            precio_venta=p.get("precio_venta", 0),
            afecto_iva=p.get("afecto_iva", True),
            existencia=existencia,
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
    
    resultado = []
    for p in productos[:limit]:
        controla_inv = p.get("controla_inventario", True)
        # Si no controla inventario, mostrar existencia como -1 (ilimitado)
        existencia = existencias_map.get(p["id"], 0) if bodega_id and controla_inv else (-1 if not controla_inv else 0)
        
        resultado.append(ProductoPOSResponse(
            id=p["id"],
            codigo=p.get("codigo", ""),
            nombre=p["nombre"],
            categoria_nombre=categorias.get(p.get("categoria_id")),
            precio_venta=p.get("precio_venta", 0),
            afecto_iva=p.get("afecto_iva", True),
            existencia=existencia,
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
    fecha_hoy = now.strftime("%Y-%m-%d")
    
    # Verificar permisos
    if current_user.get("role") not in ["superadmin", "admin", "usuario"]:
        raise HTTPException(status_code=403, detail="Sin permisos para realizar ventas")
    
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
    iva_total = 0
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
        
        # Calcular subtotal del item
        item_subtotal = item.cantidad * item.precio_unitario - item.descuento
        subtotal += item_subtotal
        descuento_total += item.descuento
        
        # Calcular IVA (12% en Guatemala)
        if item.afecto_iva:
            iva_item = item_subtotal * 0.12
            iva_total += iva_item
        
        items_procesados.append({
            "producto_id": item.producto_id,
            "codigo": producto.get("codigo", ""),
            "nombre": producto["nombre"],
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "descuento": item.descuento,
            "subtotal": item_subtotal,
            "afecto_iva": item.afecto_iva,
            "lotes_consumidos": []
        })
        
        # Agregar a lista para descuento de inventario (solo si controla inventario)
        if producto.get("controla_inventario", True):
            items_para_descuento.append({
                "producto_id": item.producto_id,
                "cantidad": item.cantidad
            })
    
    total = subtotal + iva_total
    
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
                "numero_cuenta": f"CXC-CLI-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
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
                "concepto": f"Venta {numero_venta}",
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
        "items": items_procesados,
        "cantidad_items": sum(item["cantidad"] for item in items_procesados),
        "subtotal": round(subtotal, 2),
        "descuento_total": round(descuento_total, 2),
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
    
    if fecha_desde:
        filtro["fecha"] = {"$gte": fecha_desde}
    if fecha_hasta:
        if "fecha" not in filtro:
            filtro["fecha"] = {}
        filtro["fecha"]["$lte"] = fecha_hasta + "T23:59:59"
    if paciente_id:
        filtro["paciente_id"] = paciente_id
    if estado:
        filtro["estado"] = estado
    if search:
        filtro["$or"] = [
            {"numero_venta": {"$regex": search, "$options": "i"}},
            {"paciente_nombre": {"$regex": search, "$options": "i"}}
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
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    ventas = await db.ventas.find({
        "origen": "clinica",
        "fecha": {"$gte": f"{fecha_hoy}T00:00:00", "$lte": f"{fecha_hoy}T23:59:59"}
    }, {"_id": 0}).sort("fecha", -1).to_list(500)
    
    return {"data": ventas, "total": len(ventas)}

@router.get("/resumen-dia", response_model=ResumenVentasDia)
async def resumen_ventas_dia(
    fecha: Optional[str] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene un resumen de las ventas del día"""
    db = get_db()
    fecha_consulta = fecha or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    ventas = await db.ventas.find({
        "origen": "clinica",
        "estado": "completada",
        "fecha": {"$gte": f"{fecha_consulta}T00:00:00", "$lte": f"{fecha_consulta}T23:59:59"}
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
    Anula una venta. Solo SuperAdmin puede anular.
    Opcionalmente devuelve el inventario al stock.
    """
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede anular ventas")
    
    venta = await db.ventas.find_one({"id": venta_id, "origen": "clinica"})
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    if venta.get("estado") == "anulada":
        raise HTTPException(status_code=400, detail="La venta ya está anulada")
    
    now = datetime.now(timezone.utc)
    
    # Devolver inventario si se solicita
    if anulacion.devolver_inventario:
        from routes.inventario import crear_movimiento_kardex, actualizar_existencia
        
        for item in venta.get("items", []):
            # Verificar si el producto controla inventario
            producto = await db.productos_inventario.find_one({"id": item["producto_id"], "origen": "clinica"})
            if producto and producto.get("controla_inventario", True):
                # Crear movimiento de devolución
                await crear_movimiento_kardex(
                    db=db,
                    producto_id=item["producto_id"],
                    bodega_id=venta["bodega_id"],
                    tipo="anulacion",
                    cantidad=item["cantidad"],
                    costo_unitario=producto.get("costo_promedio", 0),
                    usuario_id=current_user["id"],
                    referencia_tipo="anulacion_venta",
                    referencia_id=venta_id,
                    motivo=f"Anulación de venta {venta['numero_venta']}: {anulacion.motivo}"
                )
                
                # Actualizar existencia (devolver stock)
                await actualizar_existencia(db, item["producto_id"], venta["bodega_id"], item["cantidad"])
                
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
    fecha_dt = datetime.fromisoformat(venta["fecha"].replace("Z", "+00:00"))
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
            "nombre": empresa_config.get("nombre", "NovaVision - Clínica Oftalmológica"),
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
