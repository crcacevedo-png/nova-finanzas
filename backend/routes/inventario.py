# /app/backend/routes/inventario.py
# Módulo de Inventario Completo para NovaVision
# Control de productos, lotes, existencias, kardex, órdenes de compra, recepciones, transferencias y tomas físicas

from fastapi import APIRouter, HTTPException, Depends, Query, Body, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import uuid
import logging
import csv
import io

logger = logging.getLogger("inventario")

router = APIRouter(prefix="/inventario", tags=["Inventario"])

# ==================== MODELOS PYDANTIC ====================

# --- Bodegas ---
class BodegaBase(BaseModel):
    nombre: str
    codigo: str
    descripcion: Optional[str] = None
    responsable_id: Optional[str] = None
    es_punto_venta: bool = False
    activo: bool = True

class BodegaCreate(BodegaBase):
    pass

class BodegaResponse(BodegaBase):
    id: str
    origen: str = "clinica"
    created_at: Optional[str] = None

class BodegaListResponse(BaseModel):
    data: List[BodegaResponse]
    total: int

# --- Categorías ---
class CategoriaBase(BaseModel):
    nombre: str
    icono: str = "package"
    color: Optional[str] = "#0F6E56"
    orden: int = 0
    activo: bool = True

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id: str
    origen: str = "clinica"

class CategoriaListResponse(BaseModel):
    data: List[CategoriaResponse]
    total: int

# --- Productos ---
class ProductoBase(BaseModel):
    codigo: Optional[str] = None
    codigo_barras: Optional[str] = None
    nombre: str
    nombre_generico: Optional[str] = None
    descripcion: Optional[str] = None
    categoria_id: Optional[str] = None
    tipo: Literal["producto", "servicio", "insumo", "medicamento"] = "producto"
    presentacion: Optional[str] = None
    unidad_medida: str = "unidad"
    unidad_compra: Optional[str] = None
    factor_conversion: int = 1
    controla_inventario: bool = True
    controla_lotes: bool = False
    requiere_receta: bool = False
    precio_compra: float = 0.0
    precio_venta: float = 0.0
    afecto_iva: bool = True
    existencia_minima: int = 0
    existencia_maxima: int = 0
    proveedor_preferido_id: Optional[str] = None
    imagen: Optional[str] = None
    activo: bool = True

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(BaseModel):
    codigo: Optional[str] = None
    codigo_barras: Optional[str] = None
    nombre: Optional[str] = None
    nombre_generico: Optional[str] = None
    descripcion: Optional[str] = None
    categoria_id: Optional[str] = None
    tipo: Optional[Literal["producto", "servicio", "insumo", "medicamento"]] = None
    presentacion: Optional[str] = None
    unidad_medida: Optional[str] = None
    unidad_compra: Optional[str] = None
    factor_conversion: Optional[int] = None
    controla_inventario: Optional[bool] = None
    controla_lotes: Optional[bool] = None
    requiere_receta: Optional[bool] = None
    precio_compra: Optional[float] = None
    precio_venta: Optional[float] = None
    afecto_iva: Optional[bool] = None
    existencia_minima: Optional[int] = None
    existencia_maxima: Optional[int] = None
    proveedor_preferido_id: Optional[str] = None
    imagen: Optional[str] = None
    activo: Optional[bool] = None

class ProductoResponse(ProductoBase):
    id: str
    precio_compra: float = 0.0
    costo_promedio: float = 0.0
    ultimo_costo: float = 0.0
    existencia_total: int = 0
    origen: str = "clinica"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    categoria_nombre: Optional[str] = None

class ProductoListResponse(BaseModel):
    data: List[ProductoResponse]
    total: int
    page: int
    limit: int

# --- Existencias ---
class ExistenciaResponse(BaseModel):
    id: str
    producto_id: str
    producto_nombre: str
    producto_codigo: str
    bodega_id: str
    bodega_nombre: str
    cantidad: int
    cantidad_reservada: int = 0
    cantidad_disponible: int = 0
    ultima_actualizacion: Optional[str] = None

class ExistenciaMatrizResponse(BaseModel):
    producto_id: str
    producto_nombre: str
    producto_codigo: str
    categoria_nombre: Optional[str] = None
    costo_promedio: float = 0.0
    precio_venta: float = 0.0
    existencias_por_bodega: dict = {}
    total: int = 0

# --- Lotes ---
class LoteBase(BaseModel):
    producto_id: str
    bodega_id: str
    numero_lote: str
    fecha_vencimiento: str
    cantidad_inicial: int
    costo_unitario: float = 0.0
    proveedor_id: Optional[str] = None

class LoteCreate(LoteBase):
    pass

class LoteResponse(LoteBase):
    id: str
    cantidad_disponible: int
    recepcion_id: Optional[str] = None
    estado: str = "disponible"
    origen: str = "clinica"
    producto_nombre: Optional[str] = None
    bodega_nombre: Optional[str] = None
    dias_para_vencer: Optional[int] = None

class LoteListResponse(BaseModel):
    data: List[LoteResponse]
    total: int

# --- Movimientos (Kardex) ---
class MovimientoBase(BaseModel):
    producto_id: str
    bodega_id: str
    lote_id: Optional[str] = None
    tipo: Literal[
        "entrada", "salida", "venta", "devolucion",
        "ajuste_positivo", "ajuste_negativo",
        "transferencia_salida", "transferencia_entrada",
        "consumo", "baja", "anulacion"
    ]
    cantidad: int
    costo_unitario: float = 0.0
    referencia_tipo: Optional[str] = None
    referencia_id: Optional[str] = None
    motivo: Optional[str] = None

class MovimientoResponse(MovimientoBase):
    id: str
    fecha: str
    existencia_anterior: int
    existencia_nueva: int
    costo_total: float
    usuario_id: str
    usuario_nombre: Optional[str] = None
    producto_nombre: Optional[str] = None
    bodega_nombre: Optional[str] = None
    origen: str = "clinica"

class MovimientoListResponse(BaseModel):
    data: List[MovimientoResponse]
    total: int
    page: int
    limit: int

# --- Órdenes de Compra ---
class OrdenCompraItem(BaseModel):
    producto_id: str
    codigo: Optional[str] = None
    nombre: str
    cantidad: int
    cantidad_recibida: int = 0
    costo_unitario: float = 0.0
    subtotal: float = 0.0

class OrdenCompraBase(BaseModel):
    proveedor_id: str
    fecha_estimada_entrega: Optional[str] = None
    items: List[OrdenCompraItem]
    observaciones: Optional[str] = None

class OrdenCompraCreate(OrdenCompraBase):
    pass

class OrdenCompraResponse(OrdenCompraBase):
    id: str
    numero_orden: str
    fecha: str
    subtotal: float
    total: float
    estado: str = "borrador"
    creada_por: str
    autorizada_por: Optional[str] = None
    fecha_autorizacion: Optional[str] = None
    proveedor_nombre: Optional[str] = None
    origen: str = "clinica"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class OrdenCompraListResponse(BaseModel):
    data: List[OrdenCompraResponse]
    total: int

# --- Recepciones ---
class RecepcionItem(BaseModel):
    producto_id: str
    cantidad: int
    costo_unitario: float
    numero_lote: Optional[str] = None
    fecha_vencimiento: Optional[str] = None

class RecepcionBase(BaseModel):
    orden_compra_id: Optional[str] = None
    proveedor_id: str
    bodega_id: str
    numero_factura: Optional[str] = None
    numero_envio: Optional[str] = None
    items: List[RecepcionItem]
    observaciones: Optional[str] = None

class RecepcionCreate(RecepcionBase):
    pass

class RecepcionResponse(RecepcionBase):
    id: str
    numero_recepcion: str
    fecha: str
    total_costo: float
    gasto_id: Optional[str] = None
    usuario_id: str
    usuario_nombre: Optional[str] = None
    proveedor_nombre: Optional[str] = None
    bodega_nombre: Optional[str] = None
    origen: str = "clinica"
    created_at: Optional[str] = None

class RecepcionListResponse(BaseModel):
    data: List[RecepcionResponse]
    total: int

# --- Transferencias ---
class TransferenciaItem(BaseModel):
    producto_id: str
    lote_id: Optional[str] = None
    cantidad: int

class TransferenciaBase(BaseModel):
    bodega_origen_id: str
    bodega_destino_id: str
    items: List[TransferenciaItem]
    observaciones: Optional[str] = None

class TransferenciaCreate(TransferenciaBase):
    pass

class TransferenciaResponse(TransferenciaBase):
    id: str
    numero_transferencia: str
    fecha: str
    estado: str = "pendiente"
    solicitada_por: str
    recibida_por: Optional[str] = None
    fecha_recepcion: Optional[str] = None
    bodega_origen_nombre: Optional[str] = None
    bodega_destino_nombre: Optional[str] = None
    origen: str = "clinica"
    created_at: Optional[str] = None

class TransferenciaListResponse(BaseModel):
    data: List[TransferenciaResponse]
    total: int

# --- Tomas Físicas ---
class TomaFisicaItem(BaseModel):
    producto_id: str
    existencia_sistema: int = 0
    existencia_contada: Optional[int] = None
    diferencia: int = 0
    costo_unitario: float = 0.0
    impacto_valor: float = 0.0
    observacion: Optional[str] = None

class TomaFisicaBase(BaseModel):
    bodega_id: str

class TomaFisicaCreate(TomaFisicaBase):
    pass

class TomaFisicaResponse(TomaFisicaBase):
    id: str
    numero_toma: str
    fecha_inicio: str
    fecha_cierre: Optional[str] = None
    estado: str = "en_proceso"
    items: List[TomaFisicaItem]
    total_diferencia_unidades: int = 0
    total_diferencia_valor: float = 0.0
    realizada_por: str
    autorizada_por: Optional[str] = None
    bodega_nombre: Optional[str] = None
    origen: str = "clinica"

class TomaFisicaListResponse(BaseModel):
    data: List[TomaFisicaResponse]
    total: int

# --- Configuración ---
class ConfigInventario(BaseModel):
    metodo_valuacion: str = "promedio_ponderado"
    metodo_salida_lotes: str = "FEFO"
    permitir_existencia_negativa: bool = False
    dias_alerta_vencimiento: List[int] = [90, 60, 30]
    bloquear_venta_producto_vencido: bool = True
    generar_gasto_al_recibir: bool = True
    bodega_predeterminada_pos: Optional[str] = None

# --- Alertas ---
class AlertaInventario(BaseModel):
    tipo: str  # "minimo", "vencimiento", "vencido"
    producto_id: str
    producto_nombre: str
    producto_codigo: str
    bodega_id: Optional[str] = None
    bodega_nombre: Optional[str] = None
    lote_id: Optional[str] = None
    numero_lote: Optional[str] = None
    mensaje: str
    severidad: str  # "alta", "media", "baja"
    valor: Optional[float] = None
    fecha_vencimiento: Optional[str] = None
    dias_para_vencer: Optional[int] = None

class AlertasResponse(BaseModel):
    alertas: List[AlertaInventario]
    total_minimo: int
    total_por_vencer: int
    total_vencidos: int
    total: int

# --- Entrada Rápida ---
class EntradaRapida(BaseModel):
    producto_id: str
    bodega_id: str
    cantidad: int
    costo_unitario: float
    numero_lote: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    motivo: str = "Entrada manual"

# --- Ajuste ---
class AjusteInventario(BaseModel):
    producto_id: str
    bodega_id: str
    lote_id: Optional[str] = None
    cantidad_nueva: int
    motivo: str

# --- Baja de Lote ---
class BajaLote(BaseModel):
    motivo: str

# --- Dashboard/Panel ---
class PanelInventarioResponse(BaseModel):
    valor_total_inventario: float
    total_productos_activos: int
    productos_bajo_minimo: int
    lotes_por_vencer_90: int
    lotes_vencidos: int
    movimientos_hoy: int
    valor_por_categoria: List[dict]
    ultimos_movimientos: List[dict]
    productos_mayor_rotacion: List[dict]

# --- Reportes ---
class ReporteRequest(BaseModel):
    tipo: str
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    bodega_id: Optional[str] = None
    categoria_id: Optional[str] = None
    producto_id: Optional[str] = None


# ==================== FUNCIONES AUXILIARES ====================

# Variable global para db, se inicializa cuando se importa desde server
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

async def generar_codigo_producto(db) -> str:
    """Genera código único para producto"""
    ultimo = await db.productos_inventario.find_one(
        {"origen": "clinica"},
        sort=[("codigo", -1)]
    )
    if ultimo and ultimo.get("codigo", "").startswith("PROD-"):
        try:
            num = int(ultimo["codigo"].split("-")[1]) + 1
        except Exception:
            num = 1
    else:
        num = 1
    return f"PROD-{num:05d}"

async def generar_numero_orden(db) -> str:
    """Genera número único para orden de compra"""
    ultimo = await db.ordenes_compra.find_one(
        {"origen": "clinica"},
        sort=[("numero_orden", -1)]
    )
    if ultimo and ultimo.get("numero_orden", "").startswith("OC-"):
        try:
            num = int(ultimo["numero_orden"].split("-")[1]) + 1
        except Exception:
            num = 1
    else:
        num = 1
    return f"OC-{num:06d}"

async def generar_numero_recepcion(db) -> str:
    """Genera número único para recepción"""
    ultimo = await db.recepciones_inventario.find_one(
        {"origen": "clinica"},
        sort=[("numero_recepcion", -1)]
    )
    if ultimo and ultimo.get("numero_recepcion", "").startswith("REC-"):
        try:
            num = int(ultimo["numero_recepcion"].split("-")[1]) + 1
        except Exception:
            num = 1
    else:
        num = 1
    return f"REC-{num:06d}"

async def generar_numero_transferencia(db) -> str:
    """Genera número único para transferencia"""
    ultimo = await db.transferencias_inventario.find_one(
        {"origen": "clinica"},
        sort=[("numero_transferencia", -1)]
    )
    if ultimo and ultimo.get("numero_transferencia", "").startswith("TR-"):
        try:
            num = int(ultimo["numero_transferencia"].split("-")[1]) + 1
        except Exception:
            num = 1
    else:
        num = 1
    return f"TR-{num:06d}"

async def generar_numero_toma(db) -> str:
    """Genera número único para toma física"""
    ultimo = await db.tomas_fisicas.find_one(
        {"origen": "clinica"},
        sort=[("numero_toma", -1)]
    )
    if ultimo and ultimo.get("numero_toma", "").startswith("TF-"):
        try:
            num = int(ultimo["numero_toma"].split("-")[1]) + 1
        except Exception:
            num = 1
    else:
        num = 1
    return f"TF-{num:06d}"

async def obtener_existencia(db, producto_id: str, bodega_id: str) -> int:
    """Obtiene la existencia actual de un producto en una bodega"""
    existencia = await db.existencias_inventario.find_one({
        "producto_id": producto_id,
        "bodega_id": bodega_id,
        "origen": "clinica"
    })
    return existencia.get("cantidad", 0) if existencia else 0

async def obtener_existencia_total(db, producto_id: str) -> int:
    """Obtiene la existencia total de un producto en todas las bodegas"""
    pipeline = [
        {"$match": {"producto_id": producto_id, "origen": "clinica"}},
        {"$group": {"_id": None, "total": {"$sum": "$cantidad"}}}
    ]
    result = await db.existencias_inventario.aggregate(pipeline).to_list(1)
    return result[0]["total"] if result else 0

async def actualizar_existencia(db, producto_id: str, bodega_id: str, cantidad_cambio: int):
    """Actualiza la existencia de un producto en una bodega"""
    await db.existencias_inventario.update_one(
        {"producto_id": producto_id, "bodega_id": bodega_id, "origen": "clinica"},
        {
            "$inc": {"cantidad": cantidad_cambio},
            "$set": {"ultima_actualizacion": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )

async def recalcular_costo_promedio(db, producto_id: str, cantidad_nueva: int, costo_nuevo: float):
    """Recalcula el costo promedio ponderado de un producto"""
    producto = await db.productos_inventario.find_one({"id": producto_id, "origen": "clinica"})
    if not producto:
        return costo_nuevo
    
    existencia_actual = await obtener_existencia_total(db, producto_id)
    costo_actual = producto.get("costo_promedio", 0.0)
    
    # Si no hay existencia, el nuevo costo es el costo promedio
    if existencia_actual <= 0:
        nuevo_costo = round(costo_nuevo, 4)
    else:
        # Costo promedio ponderado
        valor_actual = existencia_actual * costo_actual
        valor_nuevo = cantidad_nueva * costo_nuevo
        nuevo_costo = round((valor_actual + valor_nuevo) / (existencia_actual + cantidad_nueva), 4)
    
    # Actualizar producto
    await db.productos_inventario.update_one(
        {"id": producto_id},
        {
            "$set": {
                "costo_promedio": nuevo_costo,
                "ultimo_costo": costo_nuevo,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return nuevo_costo

async def crear_movimiento_kardex(
    db,
    producto_id: str,
    bodega_id: str,
    tipo: str,
    cantidad: int,
    costo_unitario: float,
    usuario_id: str,
    lote_id: Optional[str] = None,
    referencia_tipo: Optional[str] = None,
    referencia_id: Optional[str] = None,
    motivo: Optional[str] = None
):
    """Crea un movimiento inmutable en el kardex"""
    existencia_anterior = await obtener_existencia(db, producto_id, bodega_id)
    
    # Calcular nueva existencia según tipo
    tipos_entrada = ["entrada", "devolucion", "ajuste_positivo", "transferencia_entrada"]
    tipos_salida = ["salida", "venta", "ajuste_negativo", "transferencia_salida", "consumo", "baja", "anulacion"]
    
    if tipo in tipos_entrada:
        existencia_nueva = existencia_anterior + cantidad
    elif tipo in tipos_salida:
        existencia_nueva = existencia_anterior - cantidad
    else:
        existencia_nueva = existencia_anterior
    
    movimiento = {
        "id": str(uuid.uuid4()),
        "fecha": datetime.now(timezone.utc).isoformat(),
        "producto_id": producto_id,
        "bodega_id": bodega_id,
        "lote_id": lote_id,
        "tipo": tipo,
        "cantidad": cantidad,
        "existencia_anterior": existencia_anterior,
        "existencia_nueva": existencia_nueva,
        "costo_unitario": costo_unitario,
        "costo_total": round(cantidad * costo_unitario, 2),
        "referencia_tipo": referencia_tipo,
        "referencia_id": referencia_id,
        "motivo": motivo,
        "usuario_id": usuario_id,
        "origen": "clinica"
    }
    
    await db.movimientos_inventario.insert_one(movimiento)
    return movimiento

async def obtener_lotes_fefo(db, producto_id: str, bodega_id: str, cantidad_requerida: int) -> List[dict]:
    """
    Obtiene los lotes a consumir usando FEFO (First Expired, First Out).
    Retorna lista de {lote_id, cantidad_a_consumir} hasta completar la cantidad requerida.
    """
    # Obtener config
    config = await db.config_inventario.find_one({"origen": "clinica"})
    bloquear_vencidos = config.get("bloquear_venta_producto_vencido", True) if config else True
    
    # Filtro base
    filtro = {
        "producto_id": producto_id,
        "bodega_id": bodega_id,
        "cantidad_disponible": {"$gt": 0},
        "estado": "disponible",
        "origen": "clinica"
    }
    
    # Excluir lotes vencidos si está configurado
    if bloquear_vencidos:
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filtro["fecha_vencimiento"] = {"$gt": hoy}
    
    # Ordenar por fecha de vencimiento (primero el que vence antes)
    lotes = await db.lotes_inventario.find(filtro).sort("fecha_vencimiento", 1).to_list(100)
    
    resultado = []
    cantidad_restante = cantidad_requerida
    
    for lote in lotes:
        if cantidad_restante <= 0:
            break
        
        cantidad_a_usar = min(lote["cantidad_disponible"], cantidad_restante)
        resultado.append({
            "lote_id": lote["id"],
            "numero_lote": lote["numero_lote"],
            "cantidad": cantidad_a_usar,
            "costo_unitario": lote.get("costo_unitario", 0)
        })
        cantidad_restante -= cantidad_a_usar
    
    if cantidad_restante > 0:
        # No hay suficiente stock
        return None
    
    return resultado

async def descontar_inventario(
    db,
    items: List[dict],
    bodega_id: str,
    referencia_tipo: str,
    referencia_id: str,
    usuario_id: str
) -> dict:
    """
    Función transaccional para descontar inventario.
    items: Lista de {producto_id, cantidad}
    Retorna: {success: bool, detalle: [...], error: str}
    
    Esta función es usada por el módulo de Punto de Venta.
    """
    detalle_lotes = []
    
    try:
        for item in items:
            producto_id = item["producto_id"]
            cantidad = item["cantidad"]
            
            # Verificar producto
            producto = await db.productos_inventario.find_one({
                "id": producto_id,
                "origen": "clinica"
            })
            
            if not producto:
                raise ValueError(f"Producto {producto_id} no encontrado")
            
            if not producto.get("controla_inventario", True):
                # Servicios no descuentan inventario
                continue
            
            # Verificar existencia
            existencia = await obtener_existencia(db, producto_id, bodega_id)
            
            # Obtener config para permitir negativo
            config = await db.config_inventario.find_one({"origen": "clinica"})
            permitir_negativo = config.get("permitir_existencia_negativa", False) if config else False
            
            if existencia < cantidad and not permitir_negativo:
                raise ValueError(f"Stock insuficiente para {producto['nombre']}. Disponible: {existencia}, Requerido: {cantidad}")
            
            # Si controla lotes, usar FEFO
            if producto.get("controla_lotes", False):
                lotes_a_usar = await obtener_lotes_fefo(db, producto_id, bodega_id, cantidad)
                
                if lotes_a_usar is None:
                    raise ValueError(f"No hay lotes disponibles suficientes para {producto['nombre']}")
                
                for lote_info in lotes_a_usar:
                    # Actualizar lote
                    await db.lotes_inventario.update_one(
                        {"id": lote_info["lote_id"]},
                        {"$inc": {"cantidad_disponible": -lote_info["cantidad"]}}
                    )
                    
                    # Crear movimiento de kardex
                    await crear_movimiento_kardex(
                        db=db,
                        producto_id=producto_id,
                        bodega_id=bodega_id,
                        tipo="venta",
                        cantidad=lote_info["cantidad"],
                        costo_unitario=lote_info["costo_unitario"],
                        usuario_id=usuario_id,
                        lote_id=lote_info["lote_id"],
                        referencia_tipo=referencia_tipo,
                        referencia_id=referencia_id
                    )
                    
                    detalle_lotes.append({
                        "producto_id": producto_id,
                        "lote_id": lote_info["lote_id"],
                        "numero_lote": lote_info["numero_lote"],
                        "cantidad": lote_info["cantidad"],
                        "costo_unitario": lote_info["costo_unitario"]
                    })
                
                # Actualizar existencia total
                await actualizar_existencia(db, producto_id, bodega_id, -cantidad)
            else:
                # Sin control de lotes
                costo = producto.get("costo_promedio", 0)
                
                # Crear movimiento de kardex
                await crear_movimiento_kardex(
                    db=db,
                    producto_id=producto_id,
                    bodega_id=bodega_id,
                    tipo="venta",
                    cantidad=cantidad,
                    costo_unitario=costo,
                    usuario_id=usuario_id,
                    referencia_tipo=referencia_tipo,
                    referencia_id=referencia_id
                )
                
                # Actualizar existencia
                await actualizar_existencia(db, producto_id, bodega_id, -cantidad)
                
                detalle_lotes.append({
                    "producto_id": producto_id,
                    "cantidad": cantidad,
                    "costo_unitario": costo
                })
        
        return {"success": True, "detalle": detalle_lotes, "error": None}
    
    except Exception as e:
        logger.error(f"Error en descontar_inventario: {str(e)}")
        return {"success": False, "detalle": [], "error": str(e)}


# ==================== ENDPOINTS DE BODEGAS ====================

@router.get("/bodegas", response_model=BodegaListResponse)
async def listar_bodegas(
    activo: Optional[bool] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista todas las bodegas"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    if activo is not None:
        filtro["activo"] = activo
    
    bodegas = await db.bodegas_inventario.find(filtro).sort("nombre", 1).to_list(100)
    
    data = []
    for b in bodegas:
        data.append(BodegaResponse(
            id=b["id"],
            nombre=b["nombre"],
            codigo=b["codigo"],
            descripcion=b.get("descripcion"),
            responsable_id=b.get("responsable_id"),
            es_punto_venta=b.get("es_punto_venta", False),
            activo=b.get("activo", True),
            origen=b.get("origen", "clinica"),
            created_at=b.get("created_at")
        ))
    
    return BodegaListResponse(data=data, total=len(data))

@router.post("/bodegas", response_model=BodegaResponse)
async def crear_bodega(
    bodega: BodegaCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Crea una nueva bodega"""
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede crear bodegas")
    
    # Verificar código único
    existente = await db.bodegas_inventario.find_one({
        "codigo": bodega.codigo,
        "origen": "clinica"
    })
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una bodega con ese código")
    
    nueva_bodega = {
        "id": str(uuid.uuid4()),
        **bodega.model_dump(),
        "origen": "clinica",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bodegas_inventario.insert_one(nueva_bodega)
    
    return BodegaResponse(**nueva_bodega)

@router.put("/bodegas/{bodega_id}", response_model=BodegaResponse)
async def actualizar_bodega(
    bodega_id: str,
    bodega: BodegaCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Actualiza una bodega"""
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede editar bodegas")
    
    existente = await db.bodegas_inventario.find_one({"id": bodega_id, "origen": "clinica"})
    if not existente:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    
    await db.bodegas_inventario.update_one(
        {"id": bodega_id},
        {"$set": {**bodega.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    actualizada = await db.bodegas_inventario.find_one({"id": bodega_id})
    return BodegaResponse(**actualizada)

@router.delete("/bodegas/{bodega_id}")
async def eliminar_bodega(
    bodega_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Elimina una bodega si no tiene existencias"""
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede eliminar bodegas")
    
    # Verificar existencias
    existencias = await db.existencias_inventario.find_one({
        "bodega_id": bodega_id,
        "cantidad": {"$gt": 0},
        "origen": "clinica"
    })
    if existencias:
        raise HTTPException(status_code=400, detail="No se puede eliminar una bodega con existencias")
    
    await db.bodegas_inventario.delete_one({"id": bodega_id})
    return {"message": "Bodega eliminada"}


# ==================== ENDPOINTS DE CATEGORÍAS ====================

@router.get("/categorias", response_model=CategoriaListResponse)
async def listar_categorias(
    activo: Optional[bool] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista todas las categorías de productos"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    if activo is not None:
        filtro["activo"] = activo
    
    categorias = await db.categorias_inventario.find(filtro).sort("orden", 1).to_list(100)
    
    data = [CategoriaResponse(
        id=c["id"],
        nombre=c["nombre"],
        icono=c.get("icono", "package"),
        color=c.get("color", "#0F6E56"),
        orden=c.get("orden", 0),
        activo=c.get("activo", True),
        origen=c.get("origen", "clinica")
    ) for c in categorias]
    
    return CategoriaListResponse(data=data, total=len(data))

@router.post("/categorias", response_model=CategoriaResponse)
async def crear_categoria(
    categoria: CategoriaCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Crea una nueva categoría"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos para crear categorías")
    
    nueva_categoria = {
        "id": str(uuid.uuid4()),
        **categoria.model_dump(),
        "origen": "clinica"
    }
    
    await db.categorias_inventario.insert_one(nueva_categoria)
    return CategoriaResponse(**nueva_categoria)

@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
async def actualizar_categoria(
    categoria_id: str,
    categoria: CategoriaCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Actualiza una categoría"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos para editar categorías")
    
    existente = await db.categorias_inventario.find_one({"id": categoria_id, "origen": "clinica"})
    if not existente:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    await db.categorias_inventario.update_one(
        {"id": categoria_id},
        {"$set": categoria.model_dump()}
    )
    
    actualizada = await db.categorias_inventario.find_one({"id": categoria_id})
    return CategoriaResponse(**actualizada)


@router.delete("/categorias/{categoria_id}")
async def eliminar_categoria(
    categoria_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Elimina una categoría de inventario (solo si no tiene productos asociados)"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar categorías")
    
    # Verificar que existe
    categoria = await db.categorias_inventario.find_one({"id": categoria_id, "origen": "clinica"})
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    # Verificar que no tiene productos
    productos_count = await db.productos_inventario.count_documents({
        "categoria_id": categoria_id,
        "origen": "clinica"
    })
    
    if productos_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar. La categoría tiene {productos_count} productos asociados."
        )
    
    await db.categorias_inventario.delete_one({"id": categoria_id})
    
    return {"message": "Categoría eliminada", "nombre": categoria.get("nombre", "")}


# ==================== ENDPOINTS DE PRODUCTOS ====================

@router.get("/productos", response_model=ProductoListResponse)
async def listar_productos(
    search: Optional[str] = None,
    categoria_id: Optional[str] = None,
    tipo: Optional[str] = None,
    activo: Optional[bool] = None,
    bajo_minimo: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista productos con filtros y paginación"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    
    if search:
        filtro["$or"] = [
            {"nombre": {"$regex": search, "$options": "i"}},
            {"codigo": {"$regex": search, "$options": "i"}},
            {"codigo_barras": {"$regex": search, "$options": "i"}},
            {"nombre_generico": {"$regex": search, "$options": "i"}}
        ]
    
    if categoria_id:
        filtro["categoria_id"] = categoria_id
    if tipo:
        filtro["tipo"] = tipo
    if activo is not None:
        filtro["activo"] = activo
    
    # Total sin paginación
    total = await db.productos_inventario.count_documents(filtro)
    
    # Obtener productos con paginación
    skip = (page - 1) * limit
    productos = await db.productos_inventario.find(filtro).sort("nombre", 1).skip(skip).limit(limit).to_list(limit)
    
    # Obtener categorías para nombres
    categorias = {c["id"]: c["nombre"] for c in await db.categorias_inventario.find({"origen": "clinica"}).to_list(100)}
    
    data = []
    for p in productos:
        # Calcular existencia total
        existencia = await obtener_existencia_total(db, p["id"])
        
        # Filtrar por bajo mínimo si se solicita
        if bajo_minimo is not None:
            es_bajo_minimo = existencia < p.get("existencia_minima", 0)
            if bajo_minimo and not es_bajo_minimo:
                continue
            if not bajo_minimo and es_bajo_minimo:
                continue
        
        data.append(ProductoResponse(
            id=p["id"],
            codigo=p.get("codigo"),
            codigo_barras=p.get("codigo_barras"),
            nombre=p["nombre"],
            nombre_generico=p.get("nombre_generico"),
            descripcion=p.get("descripcion"),
            categoria_id=p.get("categoria_id"),
            categoria_nombre=categorias.get(p.get("categoria_id")),
            tipo=p.get("tipo", "producto"),
            presentacion=p.get("presentacion"),
            unidad_medida=p.get("unidad_medida", "unidad"),
            unidad_compra=p.get("unidad_compra"),
            factor_conversion=p.get("factor_conversion", 1),
            controla_inventario=p.get("controla_inventario", True),
            controla_lotes=p.get("controla_lotes", False),
            requiere_receta=p.get("requiere_receta", False),
            precio_compra=p.get("precio_compra", 0),
            precio_venta=p.get("precio_venta", 0),
            costo_promedio=p.get("costo_promedio", 0),
            ultimo_costo=p.get("ultimo_costo", 0),
            afecto_iva=p.get("afecto_iva", True),
            existencia_minima=p.get("existencia_minima", 0),
            existencia_maxima=p.get("existencia_maxima", 0),
            existencia_total=existencia,
            proveedor_preferido_id=p.get("proveedor_preferido_id"),
            imagen=p.get("imagen"),
            activo=p.get("activo", True),
            origen=p.get("origen", "clinica"),
            created_at=p.get("created_at"),
            updated_at=p.get("updated_at")
        ))
    
    return ProductoListResponse(data=data, total=total, page=page, limit=limit)

@router.get("/productos/{producto_id}", response_model=ProductoResponse)
async def obtener_producto(
    producto_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene un producto por ID"""
    db = get_db()
    
    producto = await db.productos_inventario.find_one({"id": producto_id, "origen": "clinica"})
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Obtener categoría
    categoria = await db.categorias_inventario.find_one({"id": producto.get("categoria_id")})
    existencia = await obtener_existencia_total(db, producto_id)
    
    return ProductoResponse(
        id=producto["id"],
        codigo=producto.get("codigo"),
        codigo_barras=producto.get("codigo_barras"),
        nombre=producto["nombre"],
        nombre_generico=producto.get("nombre_generico"),
        descripcion=producto.get("descripcion"),
        categoria_id=producto.get("categoria_id"),
        categoria_nombre=categoria["nombre"] if categoria else None,
        tipo=producto.get("tipo", "producto"),
        presentacion=producto.get("presentacion"),
        unidad_medida=producto.get("unidad_medida", "unidad"),
        unidad_compra=producto.get("unidad_compra"),
        factor_conversion=producto.get("factor_conversion", 1),
        controla_inventario=producto.get("controla_inventario", True),
        controla_lotes=producto.get("controla_lotes", False),
        requiere_receta=producto.get("requiere_receta", False),
        precio_compra=producto.get("precio_compra", 0),
        precio_venta=producto.get("precio_venta", 0),
        costo_promedio=producto.get("costo_promedio", 0),
        ultimo_costo=producto.get("ultimo_costo", 0),
        afecto_iva=producto.get("afecto_iva", True),
        existencia_minima=producto.get("existencia_minima", 0),
        existencia_maxima=producto.get("existencia_maxima", 0),
        existencia_total=existencia,
        proveedor_preferido_id=producto.get("proveedor_preferido_id"),
        imagen=producto.get("imagen"),
        activo=producto.get("activo", True),
        origen=producto.get("origen", "clinica"),
        created_at=producto.get("created_at"),
        updated_at=producto.get("updated_at")
    )

@router.post("/productos", response_model=ProductoResponse)
async def crear_producto(
    producto: ProductoCreate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Crea un nuevo producto"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos para crear productos")
    
    # Generar código si no se proporciona
    codigo = producto.codigo or await generar_codigo_producto(db)
    
    # Verificar código único
    existente = await db.productos_inventario.find_one({
        "$or": [
            {"codigo": codigo},
            {"codigo_barras": producto.codigo_barras} if producto.codigo_barras else {"_id": None}
        ],
        "origen": "clinica"
    })
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un producto con ese código o código de barras")
    
    # Servicios no controlan inventario
    controla_inventario = producto.controla_inventario
    if producto.tipo == "servicio":
        controla_inventario = False
    
    nuevo_producto = {
        "id": str(uuid.uuid4()),
        **producto.model_dump(),
        "codigo": codigo,
        "controla_inventario": controla_inventario,
        "costo_promedio": 0.0,
        "ultimo_costo": 0.0,
        "origen": "clinica",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.productos_inventario.insert_one(nuevo_producto)
    
    return ProductoResponse(**nuevo_producto, existencia_total=0)

@router.put("/productos/{producto_id}", response_model=ProductoResponse)
async def actualizar_producto(
    producto_id: str,
    producto: ProductoUpdate,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Actualiza un producto"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos para editar productos")
    
    # Verificar permisos para editar precio
    if producto.precio_venta is not None and current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede editar precios de venta")
    
    existente = await db.productos_inventario.find_one({"id": producto_id, "origen": "clinica"})
    if not existente:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Preparar actualización (solo campos no nulos)
    update_data = {k: v for k, v in producto.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.productos_inventario.update_one(
        {"id": producto_id},
        {"$set": update_data}
    )
    
    actualizado = await db.productos_inventario.find_one({"id": producto_id})
    existencia = await obtener_existencia_total(db, producto_id)
    
    return ProductoResponse(**actualizado, existencia_total=existencia)

@router.patch("/productos/{producto_id}/estado")
async def cambiar_estado_producto(
    producto_id: str,
    activo: bool = Body(..., embed=True),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Activa o desactiva un producto"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    existente = await db.productos_inventario.find_one({"id": producto_id, "origen": "clinica"})
    if not existente:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    await db.productos_inventario.update_one(
        {"id": producto_id},
        {"$set": {"activo": activo, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": f"Producto {'activado' if activo else 'desactivado'}"}

@router.delete("/productos/{producto_id}")
async def eliminar_producto(
    producto_id: str,
    force: bool = Query(False, description="Forzar eliminación incluso con movimientos (solo superadmin)"),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Elimina un producto. Con force=true elimina incluso si tiene movimientos (solo superadmin)"""
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede eliminar productos")
    
    # Obtener datos del producto antes de eliminar (para auditoría)
    producto = await db.productos_inventario.find_one({"id": producto_id, "origen": "clinica"}, {"_id": 0})
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Verificar movimientos
    movimientos_count = await db.movimientos_inventario.count_documents({
        "producto_id": producto_id,
        "origen": "clinica"
    })
    
    tiene_movimientos = movimientos_count > 0
    
    if tiene_movimientos and not force:
        raise HTTPException(
            status_code=400, 
            detail=f"Este producto tiene {movimientos_count} movimientos registrados. Use force=true para eliminación forzada o desactívelo."
        )
    
    # Si es eliminación forzada, también eliminar movimientos y existencias relacionadas
    if tiene_movimientos and force:
        # Eliminar movimientos
        await db.movimientos_inventario.delete_many({"producto_id": producto_id, "origen": "clinica"})
        # Eliminar existencias por bodega
        await db.existencias_bodega.delete_many({"producto_id": producto_id})
        # Eliminar lotes
        await db.lotes_inventario.delete_many({"producto_id": producto_id, "origen": "clinica"})
    
    # Eliminar producto
    await db.productos_inventario.delete_one({"id": producto_id})
    
    # Registrar en auditoría
    audit_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "PRODUCT_DELETED_FORCE" if (tiene_movimientos and force) else "PRODUCT_DELETED",
        "user_id": current_user.get("id"),
        "user_name": current_user.get("name", current_user.get("username", "Unknown")),
        "ip_address": None,
        "details": {
            "producto_id": producto_id,
            "producto_codigo": producto.get("codigo", ""),
            "producto_nombre": producto.get("nombre", ""),
            "producto_tipo": producto.get("tipo", ""),
            "precio_venta": producto.get("precio_venta", 0),
            "existencia_total": producto.get("existencia_total", 0),
            "movimientos_eliminados": movimientos_count if (tiene_movimientos and force) else 0,
            "eliminacion_forzada": force and tiene_movimientos
        }
    }
    await db.audit_logs.insert_one(audit_entry)
    
    return {
        "message": "Producto eliminado" + (" (forzado)" if tiene_movimientos and force else ""),
        "producto_nombre": producto.get("nombre", ""),
        "movimientos_eliminados": movimientos_count if (tiene_movimientos and force) else 0
    }


# ==================== IMPORTACIÓN MASIVA DESDE EXCEL/CSV ====================

@router.post("/productos/importar/preview")
async def preview_importar_productos(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Vista previa de importación de productos desde Excel/CSV"""
    db = get_db()
    
    try:
        content = await file.read()
        
        # Detectar tipo de archivo y parsear
        productos_preview = []
        errors = []
        
        if file.filename.endswith('.csv'):
            # Parsear CSV
            decoded = content.decode('utf-8-sig')  # UTF-8 con BOM
            reader = csv.DictReader(io.StringIO(decoded))
            for idx, row in enumerate(reader, start=2):
                try:
                    producto = parse_import_row(row, idx)
                    if producto:
                        productos_preview.append(producto)
                except ValueError as e:
                    errors.append({"row": idx, "message": str(e)})
        else:
            # Parsear Excel (xlsx/xls)
            try:
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
                ws = wb.active
                
                # Obtener headers de la primera fila
                headers = [cell.value.lower().strip() if cell.value else f"col_{i}" 
                          for i, cell in enumerate(ws[1])]
                
                for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if not any(row):  # Fila vacía
                        continue
                    try:
                        row_dict = dict(zip(headers, row))
                        producto = parse_import_row(row_dict, idx)
                        if producto:
                            productos_preview.append(producto)
                    except ValueError as e:
                        errors.append({"row": idx, "message": str(e)})
            except ImportError:
                # Fallback sin openpyxl - solo CSV
                raise HTTPException(
                    status_code=400, 
                    detail="Para archivos Excel, use formato CSV. O contacte soporte para habilitar xlsx."
                )
        
        return {
            "preview": productos_preview[:50],  # Max 50 para preview
            "total": len(productos_preview),
            "errors": errors[:20]  # Max 20 errores
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en preview importación: {e}")
        raise HTTPException(status_code=400, detail=f"Error al procesar archivo: {str(e)}")


@router.post("/productos/importar")
async def importar_productos(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Importar productos desde Excel/CSV"""
    db = get_db()
    
    try:
        content = await file.read()
        
        productos_to_import = []
        errors = []
        
        # Parsear archivo
        if file.filename.endswith('.csv'):
            decoded = content.decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
            for idx, row in enumerate(reader, start=2):
                try:
                    producto = parse_import_row(row, idx)
                    if producto:
                        productos_to_import.append(producto)
                except ValueError as e:
                    errors.append({"row": idx, "message": str(e)})
        else:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
                ws = wb.active
                
                headers = [cell.value.lower().strip() if cell.value else f"col_{i}" 
                          for i, cell in enumerate(ws[1])]
                
                for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if not any(row):
                        continue
                    try:
                        row_dict = dict(zip(headers, row))
                        producto = parse_import_row(row_dict, idx)
                        if producto:
                            productos_to_import.append(producto)
                    except ValueError as e:
                        errors.append({"row": idx, "message": str(e)})
            except ImportError:
                raise HTTPException(
                    status_code=400, 
                    detail="Para archivos Excel, use formato CSV."
                )
        
        # Obtener categorías existentes para mapeo
        categorias = {c["nombre"].lower(): c["id"] 
                     for c in await db.categorias_inventario.find({"origen": "clinica"}).to_list(100)}
        
        # Insertar productos
        imported = 0
        skipped = 0
        now = datetime.now(timezone.utc).isoformat()
        
        for prod in productos_to_import:
            # Verificar si ya existe por código
            if prod.get("codigo"):
                existing = await db.productos_inventario.find_one({
                    "codigo": prod["codigo"],
                    "origen": "clinica"
                })
                if existing:
                    skipped += 1
                    continue
            
            # Mapear categoría
            if prod.get("categoria"):
                cat_name = prod["categoria"].lower()
                prod["categoria_id"] = categorias.get(cat_name, None)
            if "categoria" in prod:
                del prod["categoria"]
            
            # Generar ID y código si no existe
            prod["id"] = str(uuid.uuid4())
            if not prod.get("codigo"):
                # Generar código automático
                last = await db.productos_inventario.find_one(
                    {"origen": "clinica"}, 
                    sort=[("codigo", -1)]
                )
                last_num = 0
                if last and last.get("codigo", "").startswith("PROD-"):
                    try:
                        last_num = int(last["codigo"].split("-")[1])
                    except:
                        pass
                prod["codigo"] = f"PROD-{last_num + 1:04d}"
            
            prod["origen"] = "clinica"
            prod["created_at"] = now
            prod["updated_at"] = now
            prod["created_by"] = current_user["id"]
            
            await db.productos_inventario.insert_one(prod)
            imported += 1
        
        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:20],
            "message": f"Se importaron {imported} productos, {skipped} omitidos por duplicado"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en importación: {e}")
        raise HTTPException(status_code=400, detail=f"Error al importar: {str(e)}")


def parse_import_row(row: dict, row_num: int) -> Optional[dict]:
    """Parsea una fila de importación y retorna el producto"""
    # Normalizar keys a lowercase
    row = {k.lower().strip(): v for k, v in row.items() if k}
    
    # Campo obligatorio: nombre
    nombre = row.get("nombre", "").strip() if row.get("nombre") else ""
    if not nombre:
        raise ValueError("El nombre es obligatorio")
    
    # Parsear booleanos
    def parse_bool(val, default=True):
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        val_str = str(val).lower().strip()
        return val_str in ["true", "1", "si", "sí", "yes", "verdadero"]
    
    # Parsear números
    def parse_float(val, default=0.0):
        if val is None:
            return default
        try:
            # Remover símbolos de moneda y comas
            val_str = str(val).replace("Q", "").replace(",", "").strip()
            return float(val_str) if val_str else default
        except:
            return default
    
    def parse_int(val, default=0):
        if val is None:
            return default
        try:
            return int(float(str(val).strip()))
        except:
            return default
    
    # Validar tipo
    tipo = (row.get("tipo", "") or "producto").lower().strip()
    if tipo not in ["producto", "servicio", "insumo"]:
        tipo = "producto"
    
    return {
        "codigo": (row.get("codigo", "") or "").strip(),
        "codigo_barras": (row.get("codigo_barras", "") or "").strip(),
        "nombre": nombre,
        "nombre_generico": (row.get("nombre_generico", "") or "").strip(),
        "descripcion": (row.get("descripcion", "") or "").strip(),
        "categoria": (row.get("categoria", "") or "").strip(),
        "tipo": tipo,
        "presentacion": (row.get("presentacion", "") or "").strip(),
        "unidad_medida": (row.get("unidad_medida", "") or "unidad").strip(),
        "unidad_compra": (row.get("unidad_compra", "") or "").strip(),
        "factor_conversion": parse_int(row.get("factor_conversion"), 1),
        "controla_inventario": parse_bool(row.get("controla_inventario"), True),
        "controla_lotes": parse_bool(row.get("controla_lotes"), False),
        "requiere_receta": parse_bool(row.get("requiere_receta"), False),
        "precio_compra": parse_float(row.get("precio_compra")),
        "precio_venta": parse_float(row.get("precio_venta")),
        "afecto_iva": parse_bool(row.get("afecto_iva"), True),
        "existencia_minima": parse_int(row.get("existencia_minima")),
        "existencia_maxima": parse_int(row.get("existencia_maxima")),
        "activo": True
    }


# ==================== ENDPOINTS DE EXISTENCIAS ====================

@router.get("/existencias")
async def listar_existencias(
    bodega_id: Optional[str] = None,
    producto_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista existencias por bodega/producto"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    if bodega_id:
        filtro["bodega_id"] = bodega_id
    if producto_id:
        filtro["producto_id"] = producto_id
    
    existencias = await db.existencias_inventario.find(filtro).to_list(1000)
    
    # Obtener nombres de productos y bodegas
    productos = {p["id"]: p for p in await db.productos_inventario.find({"origen": "clinica"}).to_list(1000)}
    bodegas = {b["id"]: b for b in await db.bodegas_inventario.find({"origen": "clinica"}).to_list(100)}
    
    data = []
    for e in existencias:
        prod = productos.get(e["producto_id"], {})
        bod = bodegas.get(e["bodega_id"], {})
        
        data.append({
            "id": e.get("id", str(uuid.uuid4())),
            "producto_id": e["producto_id"],
            "producto_nombre": prod.get("nombre", ""),
            "producto_codigo": prod.get("codigo", ""),
            "bodega_id": e["bodega_id"],
            "bodega_nombre": bod.get("nombre", ""),
            "cantidad": e.get("cantidad", 0),
            "cantidad_reservada": e.get("cantidad_reservada", 0),
            "cantidad_disponible": e.get("cantidad", 0) - e.get("cantidad_reservada", 0),
            "ultima_actualizacion": e.get("ultima_actualizacion")
        })
    
    return {"data": data, "total": len(data)}

@router.get("/existencias/matriz")
async def matriz_existencias(
    categoria_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Vista de matriz producto × bodega"""
    db = get_db()
    
    # Filtro de productos
    filtro_prod = {"origen": "clinica", "controla_inventario": True, "activo": True}
    if categoria_id:
        filtro_prod["categoria_id"] = categoria_id
    if search:
        filtro_prod["$or"] = [
            {"nombre": {"$regex": search, "$options": "i"}},
            {"codigo": {"$regex": search, "$options": "i"}}
        ]
    
    productos = await db.productos_inventario.find(filtro_prod).sort("nombre", 1).to_list(500)
    bodegas = await db.bodegas_inventario.find({"origen": "clinica", "activo": True}).to_list(100)
    categorias = {c["id"]: c["nombre"] for c in await db.categorias_inventario.find({"origen": "clinica"}).to_list(100)}
    
    # Obtener todas las existencias
    existencias = await db.existencias_inventario.find({"origen": "clinica"}).to_list(5000)
    exist_map = {}
    for e in existencias:
        key = f"{e['producto_id']}_{e['bodega_id']}"
        exist_map[key] = e.get("cantidad", 0)
    
    data = []
    for p in productos:
        existencias_por_bodega = {}
        total = 0
        for b in bodegas:
            key = f"{p['id']}_{b['id']}"
            cant = exist_map.get(key, 0)
            existencias_por_bodega[b["id"]] = {
                "bodega_nombre": b["nombre"],
                "cantidad": cant
            }
            total += cant
        
        data.append({
            "producto_id": p["id"],
            "producto_nombre": p["nombre"],
            "producto_codigo": p.get("codigo", ""),
            "categoria_nombre": categorias.get(p.get("categoria_id")),
            "costo_promedio": p.get("costo_promedio", 0),
            "precio_venta": p.get("precio_venta", 0),
            "existencias_por_bodega": existencias_por_bodega,
            "total": total,
            "existencia_minima": p.get("existencia_minima", 0),
            "bajo_minimo": total < p.get("existencia_minima", 0)
        })
    
    return {"data": data, "bodegas": [{"id": b["id"], "nombre": b["nombre"]} for b in bodegas]}

@router.get("/existencias/{producto_id}")
async def obtener_existencias_producto(
    producto_id: str,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene existencias de un producto en todas las bodegas"""
    db = get_db()
    
    producto = await db.productos_inventario.find_one({"id": producto_id, "origen": "clinica"})
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    existencias = await db.existencias_inventario.find({
        "producto_id": producto_id,
        "origen": "clinica"
    }).to_list(100)
    
    bodegas = {b["id"]: b for b in await db.bodegas_inventario.find({"origen": "clinica"}).to_list(100)}
    
    data = []
    total = 0
    for e in existencias:
        bod = bodegas.get(e["bodega_id"], {})
        cant = e.get("cantidad", 0)
        total += cant
        data.append({
            "bodega_id": e["bodega_id"],
            "bodega_nombre": bod.get("nombre", ""),
            "cantidad": cant,
            "cantidad_reservada": e.get("cantidad_reservada", 0),
            "cantidad_disponible": cant - e.get("cantidad_reservada", 0)
        })
    
    return {
        "producto_id": producto_id,
        "producto_nombre": producto["nombre"],
        "existencias": data,
        "total": total
    }


# ==================== ENDPOINTS DE LOTES ====================

@router.get("/lotes", response_model=LoteListResponse)
async def listar_lotes(
    producto_id: Optional[str] = None,
    bodega_id: Optional[str] = None,
    estado: Optional[str] = None,
    vencimiento_desde: Optional[str] = None,
    vencimiento_hasta: Optional[str] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista lotes con filtros"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    if producto_id:
        filtro["producto_id"] = producto_id
    if bodega_id:
        filtro["bodega_id"] = bodega_id
    if estado:
        filtro["estado"] = estado
    
    if vencimiento_desde or vencimiento_hasta:
        filtro["fecha_vencimiento"] = {}
        if vencimiento_desde:
            filtro["fecha_vencimiento"]["$gte"] = vencimiento_desde
        if vencimiento_hasta:
            filtro["fecha_vencimiento"]["$lte"] = vencimiento_hasta
    
    lotes = await db.lotes_inventario.find(filtro).sort("fecha_vencimiento", 1).to_list(1000)
    
    productos = {p["id"]: p for p in await db.productos_inventario.find({"origen": "clinica"}).to_list(1000)}
    bodegas = {b["id"]: b for b in await db.bodegas_inventario.find({"origen": "clinica"}).to_list(100)}
    
    hoy = datetime.now(timezone.utc).date()
    
    data = []
    for l in lotes:
        prod = productos.get(l["producto_id"], {})
        bod = bodegas.get(l["bodega_id"], {})
        
        # Calcular días para vencer
        try:
            fecha_venc = datetime.strptime(l["fecha_vencimiento"], "%Y-%m-%d").date()
            dias_para_vencer = (fecha_venc - hoy).days
        except Exception:
            dias_para_vencer = None
        
        data.append(LoteResponse(
            id=l["id"],
            producto_id=l["producto_id"],
            producto_nombre=prod.get("nombre"),
            bodega_id=l["bodega_id"],
            bodega_nombre=bod.get("nombre"),
            numero_lote=l["numero_lote"],
            fecha_vencimiento=l["fecha_vencimiento"],
            cantidad_inicial=l.get("cantidad_inicial", 0),
            cantidad_disponible=l.get("cantidad_disponible", 0),
            costo_unitario=l.get("costo_unitario", 0),
            proveedor_id=l.get("proveedor_id"),
            recepcion_id=l.get("recepcion_id"),
            estado=l.get("estado", "disponible"),
            origen=l.get("origen", "clinica"),
            dias_para_vencer=dias_para_vencer
        ))
    
    return LoteListResponse(data=data, total=len(data))

@router.post("/lotes/{lote_id}/baja")
async def dar_baja_lote(
    lote_id: str,
    baja: BajaLote,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Da de baja un lote con motivo obligatorio"""
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede dar de baja lotes")
    
    if not baja.motivo or len(baja.motivo.strip()) < 5:
        raise HTTPException(status_code=400, detail="El motivo es obligatorio (mínimo 5 caracteres)")
    
    lote = await db.lotes_inventario.find_one({"id": lote_id, "origen": "clinica"})
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    if lote.get("cantidad_disponible", 0) <= 0:
        raise HTTPException(status_code=400, detail="El lote no tiene existencias disponibles")
    
    cantidad = lote["cantidad_disponible"]
    
    # Crear movimiento de baja
    await crear_movimiento_kardex(
        db=db,
        producto_id=lote["producto_id"],
        bodega_id=lote["bodega_id"],
        tipo="baja",
        cantidad=cantidad,
        costo_unitario=lote.get("costo_unitario", 0),
        usuario_id=current_user["id"],
        lote_id=lote_id,
        referencia_tipo="baja_lote",
        referencia_id=lote_id,
        motivo=baja.motivo
    )
    
    # Actualizar lote
    await db.lotes_inventario.update_one(
        {"id": lote_id},
        {"$set": {"cantidad_disponible": 0, "estado": "agotado"}}
    )
    
    # Actualizar existencia
    await actualizar_existencia(db, lote["producto_id"], lote["bodega_id"], -cantidad)
    
    return {"message": f"Lote dado de baja. {cantidad} unidades afectadas."}


# ==================== ENDPOINTS DE MOVIMIENTOS (KARDEX) ====================

@router.get("/movimientos", response_model=MovimientoListResponse)
async def listar_movimientos(
    producto_id: Optional[str] = None,
    bodega_id: Optional[str] = None,
    tipo: Optional[str] = None,
    usuario_id: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Lista movimientos de kardex con filtros"""
    db = get_db()
    
    filtro = {"origen": "clinica"}
    if producto_id:
        filtro["producto_id"] = producto_id
    if bodega_id:
        filtro["bodega_id"] = bodega_id
    if tipo:
        filtro["tipo"] = tipo
    if usuario_id:
        filtro["usuario_id"] = usuario_id
    
    if fecha_desde or fecha_hasta:
        filtro["fecha"] = {}
        if fecha_desde:
            filtro["fecha"]["$gte"] = fecha_desde
        if fecha_hasta:
            filtro["fecha"]["$lte"] = fecha_hasta + "T23:59:59"
    
    total = await db.movimientos_inventario.count_documents(filtro)
    
    skip = (page - 1) * limit
    movimientos = await db.movimientos_inventario.find(filtro).sort("fecha", -1).skip(skip).limit(limit).to_list(limit)
    
    productos = {p["id"]: p for p in await db.productos_inventario.find({"origen": "clinica"}).to_list(1000)}
    bodegas = {b["id"]: b for b in await db.bodegas_inventario.find({"origen": "clinica"}).to_list(100)}
    usuarios = {u["id"]: u for u in await db.users.find({}).to_list(100)}
    
    data = []
    for m in movimientos:
        prod = productos.get(m["producto_id"], {})
        bod = bodegas.get(m["bodega_id"], {})
        user = usuarios.get(m.get("usuario_id"), {})
        
        data.append(MovimientoResponse(
            id=m["id"],
            fecha=m["fecha"],
            producto_id=m["producto_id"],
            producto_nombre=prod.get("nombre"),
            bodega_id=m["bodega_id"],
            bodega_nombre=bod.get("nombre"),
            lote_id=m.get("lote_id"),
            tipo=m["tipo"],
            cantidad=m["cantidad"],
            existencia_anterior=m.get("existencia_anterior", 0),
            existencia_nueva=m.get("existencia_nueva", 0),
            costo_unitario=m.get("costo_unitario", 0),
            costo_total=m.get("costo_total", 0),
            referencia_tipo=m.get("referencia_tipo"),
            referencia_id=m.get("referencia_id"),
            motivo=m.get("motivo"),
            usuario_id=m.get("usuario_id", ""),
            usuario_nombre=user.get("name"),
            origen=m.get("origen", "clinica")
        ))
    
    return MovimientoListResponse(data=data, total=total, page=page, limit=limit)

@router.get("/kardex/{producto_id}")
async def obtener_kardex_producto(
    producto_id: str,
    bodega_id: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Obtiene el kardex completo de un producto"""
    db = get_db()
    
    producto = await db.productos_inventario.find_one({"id": producto_id, "origen": "clinica"})
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    filtro = {"producto_id": producto_id, "origen": "clinica"}
    if bodega_id:
        filtro["bodega_id"] = bodega_id
    if fecha_desde:
        filtro["fecha"] = {"$gte": fecha_desde}
    if fecha_hasta:
        if "fecha" not in filtro:
            filtro["fecha"] = {}
        filtro["fecha"]["$lte"] = fecha_hasta + "T23:59:59"
    
    movimientos = await db.movimientos_inventario.find(filtro).sort("fecha", 1).to_list(1000)
    
    bodegas = {b["id"]: b for b in await db.bodegas_inventario.find({"origen": "clinica"}).to_list(100)}
    
    kardex = []
    for m in movimientos:
        bod = bodegas.get(m["bodega_id"], {})
        kardex.append({
            "id": m["id"],
            "fecha": m["fecha"],
            "bodega_nombre": bod.get("nombre", ""),
            "tipo": m["tipo"],
            "cantidad": m["cantidad"],
            "existencia_anterior": m.get("existencia_anterior", 0),
            "existencia_nueva": m.get("existencia_nueva", 0),
            "costo_unitario": m.get("costo_unitario", 0),
            "costo_total": m.get("costo_total", 0),
            "valor_inventario": m.get("existencia_nueva", 0) * producto.get("costo_promedio", 0),
            "referencia_tipo": m.get("referencia_tipo"),
            "motivo": m.get("motivo")
        })
    
    return {
        "producto": {
            "id": producto["id"],
            "codigo": producto.get("codigo"),
            "nombre": producto["nombre"],
            "costo_promedio": producto.get("costo_promedio", 0)
        },
        "kardex": kardex,
        "total_movimientos": len(kardex)
    }


# ==================== ENDPOINTS DE ENTRADA Y AJUSTES ====================

@router.post("/entrada")
async def registrar_entrada_rapida(
    entrada: EntradaRapida,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Registra una entrada rápida de inventario"""
    db = get_db()
    
    if current_user.get("role") not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos para registrar entradas")
    
    producto = await db.productos_inventario.find_one({"id": entrada.producto_id, "origen": "clinica"})
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    bodega = await db.bodegas_inventario.find_one({"id": entrada.bodega_id, "origen": "clinica"})
    if not bodega:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    
    # Si controla lotes, crear el lote
    lote_id = None
    if producto.get("controla_lotes", False):
        if not entrada.numero_lote or not entrada.fecha_vencimiento:
            raise HTTPException(status_code=400, detail="Este producto requiere número de lote y fecha de vencimiento")
        
        # Verificar lote único
        lote_existente = await db.lotes_inventario.find_one({
            "producto_id": entrada.producto_id,
            "numero_lote": entrada.numero_lote,
            "origen": "clinica"
        })
        if lote_existente:
            raise HTTPException(status_code=400, detail="Ya existe un lote con ese número para este producto")
        
        lote_id = str(uuid.uuid4())
        nuevo_lote = {
            "id": lote_id,
            "producto_id": entrada.producto_id,
            "bodega_id": entrada.bodega_id,
            "numero_lote": entrada.numero_lote,
            "fecha_vencimiento": entrada.fecha_vencimiento,
            "cantidad_inicial": entrada.cantidad,
            "cantidad_disponible": entrada.cantidad,
            "costo_unitario": entrada.costo_unitario,
            "estado": "disponible",
            "origen": "clinica"
        }
        await db.lotes_inventario.insert_one(nuevo_lote)
    
    # Crear movimiento
    await crear_movimiento_kardex(
        db=db,
        producto_id=entrada.producto_id,
        bodega_id=entrada.bodega_id,
        tipo="entrada",
        cantidad=entrada.cantidad,
        costo_unitario=entrada.costo_unitario,
        usuario_id=current_user["id"],
        lote_id=lote_id,
        referencia_tipo="manual",
        motivo=entrada.motivo
    )
    
    # Actualizar existencia
    await actualizar_existencia(db, entrada.producto_id, entrada.bodega_id, entrada.cantidad)
    
    # Recalcular costo promedio
    await recalcular_costo_promedio(db, entrada.producto_id, entrada.cantidad, entrada.costo_unitario)
    
    return {"message": f"Entrada registrada: {entrada.cantidad} unidades"}

@router.post("/ajuste")
async def registrar_ajuste(
    ajuste: AjusteInventario,
    current_user: dict = Depends(get_current_user_dependency())
):
    """Registra un ajuste de inventario"""
    db = get_db()
    
    if current_user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo SuperAdmin puede realizar ajustes")
    
    if not ajuste.motivo or len(ajuste.motivo.strip()) < 5:
        raise HTTPException(status_code=400, detail="El motivo es obligatorio (mínimo 5 caracteres)")
    
    producto = await db.productos_inventario.find_one({"id": ajuste.producto_id, "origen": "clinica"})
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    existencia_actual = await obtener_existencia(db, ajuste.producto_id, ajuste.bodega_id)
    diferencia = ajuste.cantidad_nueva - existencia_actual
    
    if diferencia == 0:
        return {"message": "No hay diferencia que ajustar"}
    
    tipo = "ajuste_positivo" if diferencia > 0 else "ajuste_negativo"
    cantidad = abs(diferencia)
    
    # Si tiene lote específico, ajustar ese lote
    if ajuste.lote_id:
        lote = await db.lotes_inventario.find_one({"id": ajuste.lote_id, "origen": "clinica"})
        if not lote:
            raise HTTPException(status_code=404, detail="Lote no encontrado")
        
        nueva_cantidad_lote = lote.get("cantidad_disponible", 0) + diferencia
        if nueva_cantidad_lote < 0:
            raise HTTPException(status_code=400, detail="El ajuste dejaría el lote con cantidad negativa")
        
        await db.lotes_inventario.update_one(
            {"id": ajuste.lote_id},
            {"$set": {"cantidad_disponible": nueva_cantidad_lote}}
        )
    
    # Crear movimiento
    await crear_movimiento_kardex(
        db=db,
        producto_id=ajuste.producto_id,
        bodega_id=ajuste.bodega_id,
        tipo=tipo,
        cantidad=cantidad,
        costo_unitario=producto.get("costo_promedio", 0),
        usuario_id=current_user["id"],
        lote_id=ajuste.lote_id,
        referencia_tipo="ajuste_manual",
        motivo=ajuste.motivo
    )
    
    # Actualizar existencia
    await actualizar_existencia(db, ajuste.producto_id, ajuste.bodega_id, diferencia)
    
    return {
        "message": f"Ajuste realizado: {'+'if diferencia > 0 else ''}{diferencia} unidades",
        "existencia_anterior": existencia_actual,
        "existencia_nueva": ajuste.cantidad_nueva
    }


# ==================== REPORTE DE RENTABILIDAD POR CATEGORÍA ====================

class RentabilidadCategoriaItem(BaseModel):
    categoria_id: Optional[str] = None
    categoria_nombre: str
    total_productos: int
    productos_con_precio: int
    margen_promedio: float
    margen_minimo: float
    margen_maximo: float
    ganancia_promedio: float
    valor_inventario_costo: float
    valor_inventario_venta: float
    ganancia_potencial: float

class RentabilidadCategoriaResponse(BaseModel):
    categorias: List[RentabilidadCategoriaItem]
    resumen: dict
    fecha_generacion: str

@router.get("/reportes/rentabilidad-categorias", response_model=RentabilidadCategoriaResponse)
async def reporte_rentabilidad_categorias(
    solo_con_stock: bool = Query(False, description="Solo mostrar productos con existencias"),
    current_user: dict = Depends(get_current_user_dependency())
):
    """
    Genera un reporte de rentabilidad promedio agrupado por categoría.
    Calcula margen promedio, mínimo, máximo y ganancia potencial por categoría.
    """
    db = get_db()
    
    # Obtener todas las categorías
    categorias = {c["id"]: c["nombre"] for c in await db.categorias_inventario.find({"origen": "clinica"}).to_list(100)}
    
    # Filtro base para productos
    filtro_productos = {
        "origen": "clinica",
        "activo": True,
        "tipo": {"$ne": "servicio"}  # Excluir servicios
    }
    
    productos = await db.productos_inventario.find(filtro_productos).to_list(5000)
    
    # Obtener existencias si se requiere filtrar por stock
    existencias_map = {}
    if solo_con_stock:
        existencias = await db.existencias_inventario.find({"origen": "clinica"}).to_list(10000)
        for e in existencias:
            pid = e["producto_id"]
            existencias_map[pid] = existencias_map.get(pid, 0) + e.get("cantidad", 0)
    
    # Agrupar productos por categoría
    datos_por_categoria = {}
    productos_sin_categoria = []
    
    for p in productos:
        # Si solo_con_stock, verificar existencias
        if solo_con_stock:
            stock = existencias_map.get(p["id"], 0)
            if stock <= 0:
                continue
        else:
            stock = await obtener_existencia_total(db, p["id"]) if not solo_con_stock else existencias_map.get(p["id"], 0)
        
        # Calcular margen
        precio_compra = p.get("precio_compra") or p.get("costo_promedio") or 0
        precio_venta = p.get("precio_venta") or 0
        
        if precio_venta > 0 and precio_compra > 0:
            margen = ((precio_venta - precio_compra) / precio_venta) * 100
            ganancia = precio_venta - precio_compra
        else:
            margen = 0
            ganancia = 0
        
        cat_id = p.get("categoria_id")
        cat_nombre = categorias.get(cat_id, "Sin Categoría") if cat_id else "Sin Categoría"
        
        if cat_id not in datos_por_categoria:
            datos_por_categoria[cat_id] = {
                "categoria_id": cat_id,
                "categoria_nombre": cat_nombre,
                "productos": [],
                "margenes": [],
                "ganancias": [],
                "valor_costo": 0,
                "valor_venta": 0
            }
        
        datos_por_categoria[cat_id]["productos"].append(p)
        
        if precio_venta > 0 and precio_compra > 0:
            datos_por_categoria[cat_id]["margenes"].append(margen)
            datos_por_categoria[cat_id]["ganancias"].append(ganancia)
        
        # Calcular valor de inventario
        if not solo_con_stock:
            stock = await obtener_existencia_total(db, p["id"])
        
        datos_por_categoria[cat_id]["valor_costo"] += stock * precio_compra
        datos_por_categoria[cat_id]["valor_venta"] += stock * precio_venta
    
    # Construir respuesta
    resultado_categorias = []
    total_productos = 0
    total_valor_costo = 0
    total_valor_venta = 0
    todos_margenes = []
    
    for cat_id, datos in datos_por_categoria.items():
        margenes = datos["margenes"]
        ganancias = datos["ganancias"]
        
        margen_promedio = sum(margenes) / len(margenes) if margenes else 0
        margen_minimo = min(margenes) if margenes else 0
        margen_maximo = max(margenes) if margenes else 0
        ganancia_promedio = sum(ganancias) / len(ganancias) if ganancias else 0
        
        item = RentabilidadCategoriaItem(
            categoria_id=cat_id,
            categoria_nombre=datos["categoria_nombre"],
            total_productos=len(datos["productos"]),
            productos_con_precio=len(margenes),
            margen_promedio=round(margen_promedio, 2),
            margen_minimo=round(margen_minimo, 2),
            margen_maximo=round(margen_maximo, 2),
            ganancia_promedio=round(ganancia_promedio, 2),
            valor_inventario_costo=round(datos["valor_costo"], 2),
            valor_inventario_venta=round(datos["valor_venta"], 2),
            ganancia_potencial=round(datos["valor_venta"] - datos["valor_costo"], 2)
        )
        resultado_categorias.append(item)
        
        total_productos += len(datos["productos"])
        total_valor_costo += datos["valor_costo"]
        total_valor_venta += datos["valor_venta"]
        todos_margenes.extend(margenes)
    
    # Ordenar por margen promedio descendente
    resultado_categorias.sort(key=lambda x: x.margen_promedio, reverse=True)
    
    # Resumen general
    margen_general = sum(todos_margenes) / len(todos_margenes) if todos_margenes else 0
    
    resumen = {
        "total_categorias": len(resultado_categorias),
        "total_productos": total_productos,
        "margen_promedio_general": round(margen_general, 2),
        "valor_total_costo": round(total_valor_costo, 2),
        "valor_total_venta": round(total_valor_venta, 2),
        "ganancia_potencial_total": round(total_valor_venta - total_valor_costo, 2)
    }
    
    return RentabilidadCategoriaResponse(
        categorias=resultado_categorias,
        resumen=resumen,
        fecha_generacion=datetime.now(timezone.utc).isoformat()
    )


# ==================== HISTÓRICO DE RENTABILIDAD MENSUAL ====================

class RentabilidadMensualItem(BaseModel):
    mes: str  # Formato: "2024-01"
    mes_nombre: str  # Formato: "Enero 2024"
    total_ventas: int
    ingresos_brutos: float
    costo_total: float
    ganancia_neta: float
    margen_promedio: float
    productos_vendidos: int

class RentabilidadHistoricoResponse(BaseModel):
    datos_mensuales: List[RentabilidadMensualItem]
    tendencia: str  # "creciente", "decreciente", "estable"
    variacion_ultimo_mes: float
    fecha_generacion: str

@router.get("/reportes/rentabilidad-historico", response_model=RentabilidadHistoricoResponse)
async def reporte_rentabilidad_historico(
    meses: int = Query(12, ge=1, le=24, description="Cantidad de meses a analizar"),
    current_user: dict = Depends(get_current_user_dependency())
):
    """
    Genera un reporte histórico de rentabilidad mes a mes basado en ventas realizadas.
    Calcula margen, ganancia y tendencia de los últimos N meses.
    """
    db = get_db()
    
    # Nombres de meses en español
    meses_nombres = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    
    # Calcular rango de fechas
    fecha_fin = datetime.now(timezone.utc)
    fecha_inicio = fecha_fin - timedelta(days=meses * 31)
    
    # Obtener productos para mapear precios de compra
    productos = await db.productos_inventario.find({"origen": "clinica"}).to_list(5000)
    productos_map = {p["id"]: p for p in productos}
    
    # Obtener ventas del período (desde movimientos de inventario tipo 'venta' o desde ventas_optica)
    # Primero intentamos con ventas_optica
    ventas = await db.ventas_optica.find({
        "origen": "clinica",
        "created_at": {"$gte": fecha_inicio.isoformat(), "$lte": fecha_fin.isoformat()}
    }).to_list(10000)
    
    # Agrupar por mes
    datos_por_mes = {}
    
    for venta in ventas:
        try:
            fecha_str = venta.get("created_at", "")
            if not fecha_str:
                continue
            
            # Parsear fecha
            if isinstance(fecha_str, str):
                fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
            else:
                fecha = fecha_str
            
            mes_key = fecha.strftime("%Y-%m")
            mes_num = fecha.month
            año = fecha.year
            mes_nombre = f"{meses_nombres[mes_num]} {año}"
            
            if mes_key not in datos_por_mes:
                datos_por_mes[mes_key] = {
                    "mes": mes_key,
                    "mes_nombre": mes_nombre,
                    "total_ventas": 0,
                    "ingresos_brutos": 0,
                    "costo_total": 0,
                    "productos_vendidos": 0,
                    "margenes": []
                }
            
            datos_por_mes[mes_key]["total_ventas"] += 1
            
            # Procesar items de la venta
            items = venta.get("items", [])
            for item in items:
                producto_id = item.get("producto_id")
                cantidad = item.get("cantidad", 0)
                precio_venta = item.get("precio_unitario", 0)
                subtotal = item.get("subtotal", precio_venta * cantidad)
                
                datos_por_mes[mes_key]["ingresos_brutos"] += subtotal
                datos_por_mes[mes_key]["productos_vendidos"] += cantidad
                
                # Obtener precio de compra del producto
                producto = productos_map.get(producto_id, {})
                precio_compra = producto.get("precio_compra") or producto.get("costo_promedio") or 0
                costo_item = precio_compra * cantidad
                
                datos_por_mes[mes_key]["costo_total"] += costo_item
                
                # Calcular margen si hay precios válidos
                if precio_venta > 0 and precio_compra > 0:
                    margen = ((precio_venta - precio_compra) / precio_venta) * 100
                    datos_por_mes[mes_key]["margenes"].append(margen)
        except Exception as e:
            continue
    
    # Si no hay ventas, intentar con movimientos de inventario tipo 'venta'
    if not datos_por_mes:
        movimientos = await db.movimientos_inventario.find({
            "origen": "clinica",
            "tipo": "venta",
            "fecha": {"$gte": fecha_inicio.isoformat(), "$lte": fecha_fin.isoformat()}
        }).to_list(10000)
        
        for mov in movimientos:
            try:
                fecha_str = mov.get("fecha", "")
                if not fecha_str:
                    continue
                
                if isinstance(fecha_str, str):
                    fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                else:
                    fecha = fecha_str
                
                mes_key = fecha.strftime("%Y-%m")
                mes_num = fecha.month
                año = fecha.year
                mes_nombre = f"{meses_nombres[mes_num]} {año}"
                
                if mes_key not in datos_por_mes:
                    datos_por_mes[mes_key] = {
                        "mes": mes_key,
                        "mes_nombre": mes_nombre,
                        "total_ventas": 0,
                        "ingresos_brutos": 0,
                        "costo_total": 0,
                        "productos_vendidos": 0,
                        "margenes": []
                    }
                
                producto_id = mov.get("producto_id")
                cantidad = abs(mov.get("cantidad", 0))
                
                producto = productos_map.get(producto_id, {})
                precio_venta = producto.get("precio_venta", 0)
                precio_compra = producto.get("precio_compra") or producto.get("costo_promedio") or 0
                
                datos_por_mes[mes_key]["total_ventas"] += 1
                datos_por_mes[mes_key]["ingresos_brutos"] += precio_venta * cantidad
                datos_por_mes[mes_key]["costo_total"] += precio_compra * cantidad
                datos_por_mes[mes_key]["productos_vendidos"] += cantidad
                
                if precio_venta > 0 and precio_compra > 0:
                    margen = ((precio_venta - precio_compra) / precio_venta) * 100
                    datos_por_mes[mes_key]["margenes"].append(margen)
            except Exception as e:
                continue
    
    # Construir respuesta ordenada por mes
    datos_mensuales = []
    meses_ordenados = sorted(datos_por_mes.keys())
    
    for mes_key in meses_ordenados:
        d = datos_por_mes[mes_key]
        margen_promedio = sum(d["margenes"]) / len(d["margenes"]) if d["margenes"] else 0
        ganancia_neta = d["ingresos_brutos"] - d["costo_total"]
        
        datos_mensuales.append(RentabilidadMensualItem(
            mes=d["mes"],
            mes_nombre=d["mes_nombre"],
            total_ventas=d["total_ventas"],
            ingresos_brutos=round(d["ingresos_brutos"], 2),
            costo_total=round(d["costo_total"], 2),
            ganancia_neta=round(ganancia_neta, 2),
            margen_promedio=round(margen_promedio, 2),
            productos_vendidos=d["productos_vendidos"]
        ))
    
    # Calcular tendencia
    tendencia = "estable"
    variacion = 0
    
    if len(datos_mensuales) >= 2:
        ultimo = datos_mensuales[-1].margen_promedio
        penultimo = datos_mensuales[-2].margen_promedio
        
        if penultimo > 0:
            variacion = ((ultimo - penultimo) / penultimo) * 100
        
        if variacion > 5:
            tendencia = "creciente"
        elif variacion < -5:
            tendencia = "decreciente"
    
    return RentabilidadHistoricoResponse(
        datos_mensuales=datos_mensuales,
        tendencia=tendencia,
        variacion_ultimo_mes=round(variacion, 2),
        fecha_generacion=datetime.now(timezone.utc).isoformat()
    )


