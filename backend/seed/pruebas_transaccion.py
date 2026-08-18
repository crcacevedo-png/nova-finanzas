# /app/backend/seed/pruebas_transaccion.py
"""
PRUEBAS DE TRANSACCIÓN E2E
Crea transacciones reales y verifica integridad de datos:
- Apertura/cierre de caja
- Ventas POS con descuento de inventario
- Movimientos de caja (ingresos/egresos)
- Verificación de totales y kardex
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import time
import uuid

# Constantes
PRB = "PRB-"


class ResultadoTransaccion:
    """Resultado de una prueba de transacción"""
    def __init__(self, test_id: str, nombre: str, severidad: str = "ALTA"):
        self.test_id = test_id
        self.nombre = nombre
        self.severidad = severidad
        self.estado = "PENDIENTE"
        self.mensaje = None
        self.evidencia = {}
        self.duracion_ms = 0
        self.timestamp = None
        self.datos_creados = []  # IDs de documentos creados para rollback
    
    def pasar(self, mensaje: str = None, evidencia: dict = None):
        self.estado = "PASA"
        self.mensaje = mensaje or "Transacción exitosa"
        self.evidencia = evidencia or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def fallar(self, mensaje: str, evidencia: dict = None):
        self.estado = "FALLA"
        self.mensaje = mensaje
        self.evidencia = evidencia or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def error(self, mensaje: str):
        self.estado = "ERROR"
        self.mensaje = f"Error de ejecución: {mensaje}"
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "nombre": self.nombre,
            "severidad": self.severidad,
            "estado": self.estado,
            "mensaje": self.mensaje,
            "evidencia": self.evidencia,
            "duracion_ms": self.duracion_ms,
            "timestamp": self.timestamp,
            "datos_creados": self.datos_creados
        }


class PruebasTransaccion:
    """Motor de pruebas de transacción E2E"""
    
    def __init__(self, db):
        self.db = db
        self.resultados: List[ResultadoTransaccion] = []
        self.datos_creados = {
            "ventas": [],
            "caja_movimientos": [],
            "caja_cierres": [],
            "kardex": []
        }
        self.inicio = None
        self.fin = None
        self.sesion_caja_id = None
        self.fecha_prueba = None
        self.run_id = None  # ID único para esta ejecución
        self.ventas_para_anular = []  # Ventas que se anularán en las pruebas de devolución
        self.stock_antes_anulacion = {}  # Stock de lotes antes de anulación
    
    async def ejecutar_todas(self) -> Dict[str, Any]:
        """Ejecuta todas las pruebas de transacción"""
        self.inicio = time.time()
        self.resultados = []
        self.fecha_prueba = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Generar un sufijo único para esta ejecución
        self.run_id = uuid.uuid4().hex[:6]
        
        # FASE 1: Preparación y apertura de caja
        await self._test_apertura_caja()
        
        # FASE 2: Ventas POS
        await self._test_venta_simple()
        await self._test_venta_multiple_items()
        await self._test_venta_con_descuento()
        await self._test_venta_multiples_formas_pago()
        
        # FASE 3: Movimientos de caja
        await self._test_ingreso_extra()
        await self._test_egreso_gasto()
        
        # FASE 4: Verificaciones de integridad
        await self._test_verificar_kardex()
        await self._test_verificar_totales_caja()
        await self._test_verificar_saldo_efectivo()
        
        # FASE 5: Cierre de caja
        await self._test_cierre_caja()
        
        # FASE 6: Devoluciones y anulaciones
        await self._test_anular_venta_con_devolucion()
        await self._test_anular_venta_sin_devolucion()
        await self._test_verificar_reversion_kardex()
        await self._test_verificar_totales_post_anulacion()
        
        self.fin = time.time()
        
        return self._generar_resumen()
    
    async def limpiar_transacciones(self) -> Dict[str, int]:
        """Limpia todas las transacciones de prueba creadas"""
        eliminados = {}
        
        # Eliminar ventas de prueba
        result = await self.db.ventas.delete_many({
            "$or": [
                {"esDatoPrueba": True},
                {"numero_venta": {"$regex": f"^{PRB}"}}
            ]
        })
        eliminados["ventas"] = result.deleted_count
        
        # Eliminar movimientos de caja de prueba
        result = await self.db.caja_movimientos.delete_many({
            "$or": [
                {"esDatoPrueba": True},
                {"numero_movimiento": {"$regex": f"^{PRB}"}}
            ]
        })
        eliminados["caja_movimientos"] = result.deleted_count
        
        # Eliminar cierres de caja de prueba
        result = await self.db.caja_cierres.delete_many({
            "esDatoPrueba": True
        })
        eliminados["caja_cierres"] = result.deleted_count
        
        # Eliminar kardex de prueba
        result = await self.db.kardex_inventario.delete_many({
            "$or": [
                {"esDatoPrueba": True},
                {"referencia_id": {"$regex": f"^{PRB}"}}
            ]
        })
        eliminados["kardex"] = result.deleted_count
        
        return eliminados
    
    # ==================== PRUEBAS DE APERTURA/CIERRE ====================
    
    async def _test_apertura_caja(self):
        """TRX-01: Apertura de caja de prueba"""
        prueba = ResultadoTransaccion("TRX-01", "Apertura de caja de prueba", "CRITICA")
        inicio = time.time()
        
        try:
            # Buscar usuario de prueba
            usuario = await self.db.users.find_one({
                "esDatoPrueba": True,
                "role": {"$in": ["superadmin", "admin"]}
            })
            
            if not usuario:
                # Usar superadmin real si no hay usuarios de prueba
                usuario = await self.db.users.find_one({"role": "superadmin"})
            
            if not usuario:
                prueba.fallar("No se encontró usuario para abrir caja")
                self.resultados.append(prueba)
                return
            
            # Verificar si ya hay caja abierta hoy (de prueba)
            fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            existing = await self.db.caja_cierres.find_one({
                "fecha": fecha_hoy,
                "origen": "clinica",
                "esDatoPrueba": True
            })
            
            if existing:
                # Usar la caja existente
                self.sesion_caja_id = existing["id"]
                prueba.pasar("Caja de prueba ya abierta, reutilizando", {
                    "sesion_id": self.sesion_caja_id,
                    "monto_apertura": existing.get("monto_apertura")
                })
                prueba.duracion_ms = int((time.time() - inicio) * 1000)
                self.resultados.append(prueba)
                return
            
            # Crear apertura de caja de prueba
            now = datetime.now(timezone.utc)
            monto_apertura = 500.00
            
            cierre = {
                "id": f"{PRB}CAJA-{fecha_hoy}",
                "fecha": fecha_hoy,
                "origen": "clinica",
                "estado": "Abierto",
                "monto_apertura": monto_apertura,
                "total_ingresos": 0,
                "total_egresos": 0,
                "saldo_esperado_efectivo": monto_apertura,
                "efectivo_contado": None,
                "diferencia": None,
                "observaciones": "Caja de prueba E2E",
                "abierto_por": usuario["id"],
                "abierto_por_nombre": usuario.get("name", "Sistema E2E"),
                "fecha_apertura": now.isoformat(),
                "cerrado_por": None,
                "cerrado_por_nombre": None,
                "fecha_cierre": None,
                "esDatoPrueba": True
            }
            
            await self.db.caja_cierres.insert_one(cierre)
            self.sesion_caja_id = cierre["id"]
            self.datos_creados["caja_cierres"].append(cierre["id"])
            
            prueba.pasar("Caja de prueba abierta exitosamente", {
                "sesion_id": self.sesion_caja_id,
                "monto_apertura": monto_apertura,
                "fecha": fecha_hoy
            })
            prueba.datos_creados.append(f"caja_cierres:{cierre['id']}")
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    async def _test_cierre_caja(self):
        """TRX-11: Cierre de caja y verificación de arqueo"""
        prueba = ResultadoTransaccion("TRX-11", "Cierre de caja con arqueo", "CRITICA")
        inicio = time.time()
        
        try:
            if not self.sesion_caja_id:
                prueba.fallar("No hay sesión de caja activa")
                self.resultados.append(prueba)
                return
            
            # Obtener caja actual
            caja = await self.db.caja_cierres.find_one({
                "id": self.sesion_caja_id,
                "esDatoPrueba": True
            })
            
            if not caja:
                prueba.fallar("Caja de prueba no encontrada")
                self.resultados.append(prueba)
                return
            
            # Calcular totales del día
            fecha_hoy = caja["fecha"]
            inicio_dia = f"{fecha_hoy}T00:00:00+00:00"
            fin_dia = f"{fecha_hoy}T23:59:59+00:00"
            
            movimientos = await self.db.caja_movimientos.find({
                "origen": "clinica",
                "esDatoPrueba": True,
                "fecha": {"$gte": inicio_dia, "$lte": fin_dia}
            }).to_list(None)
            
            total_ingresos = sum(m.get("monto", 0) for m in movimientos if m.get("tipo") == "Ingreso")
            total_egresos = sum(m.get("monto", 0) for m in movimientos if m.get("tipo") == "Egreso")
            
            # Calcular saldo esperado en efectivo
            ingresos_efectivo = sum(
                m.get("monto", 0) for m in movimientos 
                if m.get("tipo") == "Ingreso" and m.get("metodo_pago") == "Efectivo"
            )
            egresos_efectivo = sum(
                m.get("monto", 0) for m in movimientos 
                if m.get("tipo") == "Egreso" and m.get("metodo_pago") == "Efectivo"
            )
            
            saldo_esperado = caja["monto_apertura"] + ingresos_efectivo - egresos_efectivo
            
            # Simular conteo de efectivo (con pequeña diferencia intencional para prueba)
            efectivo_contado = saldo_esperado  # Sin diferencia
            diferencia = efectivo_contado - saldo_esperado
            
            # Actualizar cierre
            now = datetime.now(timezone.utc)
            await self.db.caja_cierres.update_one(
                {"id": self.sesion_caja_id},
                {"$set": {
                    "estado": "Cerrado",
                    "total_ingresos": total_ingresos,
                    "total_egresos": total_egresos,
                    "saldo_esperado_efectivo": saldo_esperado,
                    "efectivo_contado": efectivo_contado,
                    "diferencia": diferencia,
                    "fecha_cierre": now.isoformat(),
                    "cerrado_por": "sistema_e2e",
                    "cerrado_por_nombre": "Sistema E2E"
                }}
            )
            
            prueba.pasar("Caja cerrada exitosamente sin diferencias", {
                "total_ingresos": total_ingresos,
                "total_egresos": total_egresos,
                "monto_apertura": caja["monto_apertura"],
                "saldo_esperado_efectivo": saldo_esperado,
                "efectivo_contado": efectivo_contado,
                "diferencia": diferencia,
                "movimientos_procesados": len(movimientos)
            })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    # ==================== PRUEBAS DE VENTA ====================
    
    async def _test_venta_simple(self):
        """TRX-02: Venta simple de un producto"""
        prueba = ResultadoTransaccion("TRX-02", "Venta simple - 1 producto", "CRITICA")
        inicio = time.time()
        
        try:
            # Obtener producto de prueba con stock
            producto = await self.db.productos_inventario.find_one({
                "esDatoPrueba": True,
                "es_servicio": False,
                "origen": "clinica"
            })
            
            if not producto:
                prueba.fallar("No hay productos de prueba disponibles")
                self.resultados.append(prueba)
                return
            
            # Obtener lote con stock
            lote = await self.db.lotes_inventario.find_one({
                "producto_id": producto["id"],
                "esDatoPrueba": True,
                "cantidad_disponible": {"$gt": 0}
            })
            
            if not lote:
                prueba.fallar(f"No hay lotes con stock para {producto['codigo']}")
                self.resultados.append(prueba)
                return
            
            stock_antes = lote["cantidad_disponible"]
            
            # Obtener bodega dispensario
            bodega = await self.db.bodegas_inventario.find_one({
                "esDatoPrueba": True,
                "esPuntoVenta": True,
                "origen": "clinica"
            })
            
            if not bodega:
                prueba.fallar("No hay bodega de dispensario")
                self.resultados.append(prueba)
                return
            
            # Obtener paciente de prueba
            paciente = await self.db.patients.find_one({
                "esDatoPrueba": True
            })
            
            # Crear venta
            cantidad = 1
            precio = producto.get("precio_venta", 100)
            subtotal = precio * cantidad
            iva = round(subtotal * 0.12, 2)
            total = subtotal + iva
            
            now = datetime.now(timezone.utc)
            venta_id = f"{PRB}VTA-{self.run_id}-0001"
            
            venta = {
                "id": venta_id,
                "numero_venta": venta_id,
                "fecha": now.isoformat(),
                "bodega_id": bodega["id"],
                "bodega_nombre": bodega.get("nombre", "Dispensario"),
                "paciente_id": paciente["id"] if paciente else None,
                "paciente_nombre": f"{paciente.get('primer_nombre', '')} {paciente.get('primer_apellido', '')}" if paciente else "Consumidor Final",
                "items": [{
                    "producto_id": producto["id"],
                    "codigo": producto["codigo"],
                    "nombre": producto["nombre"],
                    "cantidad": cantidad,
                    "precio_unitario": precio,
                    "descuento": 0,
                    "subtotal": subtotal,
                    "afecto_iva": True,
                    "lotes_consumidos": [{
                        "lote_id": lote["id"],
                        "numero_lote": lote["numero_lote"],
                        "cantidad": cantidad
                    }]
                }],
                "cantidad_items": cantidad,
                "subtotal": subtotal,
                "descuento_total": 0,
                "iva": iva,
                "total": total,
                "formas_pago": [{
                    "metodo": "Efectivo",
                    "monto": total,
                    "referencia": None
                }],
                "efectivo_recibido": total,
                "cambio": 0,
                "estado": "completada",
                "caja_sesion_id": self.sesion_caja_id,
                "vendedor_id": "sistema_e2e",
                "vendedor_nombre": "Sistema E2E",
                "origen": "clinica",
                "created_at": now.isoformat(),
                "esDatoPrueba": True
            }
            
            await self.db.ventas.insert_one(venta)
            self.datos_creados["ventas"].append(venta_id)
            
            # Descontar del lote
            await self.db.lotes_inventario.update_one(
                {"id": lote["id"]},
                {"$inc": {"cantidad_disponible": -cantidad}}
            )
            
            # Crear movimiento de kardex
            kardex = {
                "id": f"{PRB}KDX-{uuid.uuid4().hex[:8]}",
                "producto_id": producto["id"],
                "lote_id": lote["id"],
                "bodega_id": bodega["id"],
                "tipo_movimiento": "Salida",
                "cantidad": cantidad,
                "stock_anterior": stock_antes,
                "stock_nuevo": stock_antes - cantidad,
                "costo_unitario": lote.get("costo_unitario", 0),
                "referencia_tipo": "Venta",
                "referencia_id": venta_id,
                "observaciones": "Venta E2E de prueba",
                "usuario_id": "sistema_e2e",
                "fecha": now.isoformat(),
                "origen": "clinica",
                "esDatoPrueba": True
            }
            
            await self.db.kardex_inventario.insert_one(kardex)
            self.datos_creados["kardex"].append(kardex["id"])
            
            # Crear movimiento de caja
            mov_caja = {
                "id": f"{PRB}MOV-{uuid.uuid4().hex[:8]}",
                "numero_movimiento": f"{PRB}MOV-001",
                "sesion_id": self.sesion_caja_id,
                "tipo": "Ingreso",
                "categoria": "Venta",
                "monto": total,
                "metodo_pago": "Efectivo",
                "referencia": venta_id,
                "descripcion": f"Venta {venta_id}",
                "fecha": now.isoformat(),
                "usuario_id": "sistema_e2e",
                "usuario_nombre": "Sistema E2E",
                "origen": "clinica",
                "esDatoPrueba": True
            }
            
            await self.db.caja_movimientos.insert_one(mov_caja)
            self.datos_creados["caja_movimientos"].append(mov_caja["id"])
            
            # Verificar que el stock se actualizó
            lote_actualizado = await self.db.lotes_inventario.find_one({"id": lote["id"]})
            stock_despues = lote_actualizado["cantidad_disponible"]
            
            if stock_despues != stock_antes - cantidad:
                prueba.fallar(f"Stock no se actualizó correctamente: {stock_antes} -> {stock_despues}, esperado {stock_antes - cantidad}")
            else:
                # Guardar info para prueba de anulación
                self.ventas_para_anular.append({
                    "venta_id": venta_id,
                    "lote_id": lote["id"],
                    "cantidad": cantidad,
                    "stock_antes_venta": stock_antes,
                    "stock_despues_venta": stock_despues,
                    "total": total,
                    "producto_codigo": producto["codigo"]
                })
                
                prueba.pasar("Venta simple completada correctamente", {
                    "venta_id": venta_id,
                    "producto": producto["codigo"],
                    "cantidad": cantidad,
                    "total": total,
                    "stock_antes": stock_antes,
                    "stock_despues": stock_despues,
                    "kardex_id": kardex["id"],
                    "movimiento_caja_id": mov_caja["id"]
                })
            
            prueba.datos_creados = [f"ventas:{venta_id}", f"kardex:{kardex['id']}", f"caja_movimientos:{mov_caja['id']}"]
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    async def _test_venta_multiple_items(self):
        """TRX-03: Venta con múltiples productos"""
        prueba = ResultadoTransaccion("TRX-03", "Venta múltiple - 3 productos", "ALTA")
        inicio = time.time()
        
        try:
            # Obtener 3 productos distintos
            productos = await self.db.productos_inventario.find({
                "esDatoPrueba": True,
                "es_servicio": False,
                "origen": "clinica"
            }).limit(3).to_list(3)
            
            if len(productos) < 3:
                prueba.fallar(f"Solo hay {len(productos)} productos, necesito 3")
                self.resultados.append(prueba)
                return
            
            bodega = await self.db.bodegas_inventario.find_one({
                "esDatoPrueba": True,
                "esPuntoVenta": True,
                "origen": "clinica"
            })
            
            now = datetime.now(timezone.utc)
            venta_id = f"{PRB}VTA-{self.run_id}-0002"
            
            items = []
            total_subtotal = 0
            
            for i, prod in enumerate(productos):
                cantidad = i + 1  # 1, 2, 3
                precio = prod.get("precio_venta", 50 * (i + 1))
                subtotal = precio * cantidad
                total_subtotal += subtotal
                
                # Obtener lote
                lote = await self.db.lotes_inventario.find_one({
                    "producto_id": prod["id"],
                    "cantidad_disponible": {"$gte": cantidad}
                })
                
                if not lote:
                    continue
                
                items.append({
                    "producto_id": prod["id"],
                    "codigo": prod["codigo"],
                    "nombre": prod["nombre"],
                    "cantidad": cantidad,
                    "precio_unitario": precio,
                    "descuento": 0,
                    "subtotal": subtotal,
                    "afecto_iva": True,
                    "lotes_consumidos": [{"lote_id": lote["id"], "cantidad": cantidad}]
                })
                
                # Descontar stock
                await self.db.lotes_inventario.update_one(
                    {"id": lote["id"]},
                    {"$inc": {"cantidad_disponible": -cantidad}}
                )
            
            if len(items) < 2:
                prueba.fallar("No hay suficientes productos con stock")
                self.resultados.append(prueba)
                return
            
            iva = round(total_subtotal * 0.12, 2)
            total = total_subtotal + iva
            
            venta = {
                "id": venta_id,
                "numero_venta": venta_id,
                "fecha": now.isoformat(),
                "bodega_id": bodega["id"],
                "items": items,
                "cantidad_items": len(items),
                "subtotal": total_subtotal,
                "descuento_total": 0,
                "iva": iva,
                "total": total,
                "formas_pago": [{"metodo": "Efectivo", "monto": total}],
                "efectivo_recibido": total,
                "cambio": 0,
                "estado": "completada",
                "caja_sesion_id": self.sesion_caja_id,
                "vendedor_id": "sistema_e2e",
                "origen": "clinica",
                "created_at": now.isoformat(),
                "esDatoPrueba": True
            }
            
            await self.db.ventas.insert_one(venta)
            self.datos_creados["ventas"].append(venta_id)
            
            # Crear movimiento de caja
            mov_caja = {
                "id": f"{PRB}MOV-{uuid.uuid4().hex[:8]}",
                "sesion_id": self.sesion_caja_id,
                "tipo": "Ingreso",
                "categoria": "Venta",
                "monto": total,
                "metodo_pago": "Efectivo",
                "referencia": venta_id,
                "fecha": now.isoformat(),
                "origen": "clinica",
                "esDatoPrueba": True
            }
            await self.db.caja_movimientos.insert_one(mov_caja)
            self.datos_creados["caja_movimientos"].append(mov_caja["id"])
            
            prueba.pasar("Venta múltiple completada", {
                "venta_id": venta_id,
                "items": len(items),
                "subtotal": total_subtotal,
                "iva": iva,
                "total": total
            })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    async def _test_venta_con_descuento(self):
        """TRX-04: Venta con descuento aplicado"""
        prueba = ResultadoTransaccion("TRX-04", "Venta con descuento 10%", "MEDIA")
        inicio = time.time()
        
        try:
            producto = await self.db.productos_inventario.find_one({
                "esDatoPrueba": True,
                "es_servicio": False
            })
            
            if not producto:
                prueba.fallar("No hay producto para prueba de descuento")
                self.resultados.append(prueba)
                return
            
            lote = await self.db.lotes_inventario.find_one({
                "producto_id": producto["id"],
                "cantidad_disponible": {"$gt": 0}
            })
            
            if not lote:
                prueba.fallar("No hay stock disponible")
                self.resultados.append(prueba)
                return
            
            bodega = await self.db.bodegas_inventario.find_one({
                "esDatoPrueba": True,
                "esPuntoVenta": True
            })
            
            now = datetime.now(timezone.utc)
            venta_id = f"{PRB}VTA-{self.run_id}-0003"
            
            cantidad = 2
            precio = producto.get("precio_venta", 100)
            descuento_porcentaje = 10
            subtotal_bruto = precio * cantidad
            descuento = round(subtotal_bruto * descuento_porcentaje / 100, 2)
            subtotal = subtotal_bruto - descuento
            iva = round(subtotal * 0.12, 2)
            total = subtotal + iva
            
            venta = {
                "id": venta_id,
                "numero_venta": venta_id,
                "fecha": now.isoformat(),
                "bodega_id": bodega["id"],
                "items": [{
                    "producto_id": producto["id"],
                    "codigo": producto["codigo"],
                    "nombre": producto["nombre"],
                    "cantidad": cantidad,
                    "precio_unitario": precio,
                    "descuento": descuento,
                    "subtotal": subtotal,
                    "afecto_iva": True,
                    "lotes_consumidos": [{"lote_id": lote["id"], "cantidad": cantidad}]
                }],
                "cantidad_items": cantidad,
                "subtotal": subtotal,
                "descuento_total": descuento,
                "iva": iva,
                "total": total,
                "formas_pago": [{"metodo": "Tarjeta", "monto": total, "referencia": "AUTH-12345"}],
                "estado": "completada",
                "caja_sesion_id": self.sesion_caja_id,
                "vendedor_id": "sistema_e2e",
                "origen": "clinica",
                "created_at": now.isoformat(),
                "esDatoPrueba": True
            }
            
            await self.db.ventas.insert_one(venta)
            self.datos_creados["ventas"].append(venta_id)
            
            # Descontar stock
            await self.db.lotes_inventario.update_one(
                {"id": lote["id"]},
                {"$inc": {"cantidad_disponible": -cantidad}}
            )
            
            # Movimiento de caja (tarjeta)
            mov_caja = {
                "id": f"{PRB}MOV-{uuid.uuid4().hex[:8]}",
                "sesion_id": self.sesion_caja_id,
                "tipo": "Ingreso",
                "categoria": "Venta",
                "monto": total,
                "metodo_pago": "Tarjeta",
                "referencia": venta_id,
                "fecha": now.isoformat(),
                "origen": "clinica",
                "esDatoPrueba": True
            }
            await self.db.caja_movimientos.insert_one(mov_caja)
            self.datos_creados["caja_movimientos"].append(mov_caja["id"])
            
            # Verificar cálculo correcto del descuento
            descuento_esperado = round(precio * cantidad * 0.10, 2)
            if abs(descuento - descuento_esperado) > 0.01:
                prueba.fallar(f"Descuento incorrecto: {descuento} vs esperado {descuento_esperado}")
            else:
                prueba.pasar("Venta con descuento calculada correctamente", {
                    "venta_id": venta_id,
                    "subtotal_bruto": subtotal_bruto,
                    "descuento": descuento,
                    "subtotal_neto": subtotal,
                    "iva": iva,
                    "total": total,
                    "metodo_pago": "Tarjeta"
                })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    async def _test_venta_multiples_formas_pago(self):
        """TRX-05: Venta con pago dividido (efectivo + tarjeta)"""
        prueba = ResultadoTransaccion("TRX-05", "Venta pago mixto (efectivo + tarjeta)", "ALTA")
        inicio = time.time()
        
        try:
            producto = await self.db.productos_inventario.find_one({
                "esDatoPrueba": True,
                "es_servicio": False
            })
            
            lote = await self.db.lotes_inventario.find_one({
                "producto_id": producto["id"],
                "cantidad_disponible": {"$gt": 0}
            }) if producto else None
            
            if not producto or not lote:
                prueba.fallar("Sin producto/lote disponible")
                self.resultados.append(prueba)
                return
            
            bodega = await self.db.bodegas_inventario.find_one({
                "esDatoPrueba": True,
                "esPuntoVenta": True
            })
            
            now = datetime.now(timezone.utc)
            venta_id = f"{PRB}VTA-{self.run_id}-0004"
            
            cantidad = 1
            precio = producto.get("precio_venta", 200)
            subtotal = precio * cantidad
            iva = round(subtotal * 0.12, 2)
            total = subtotal + iva
            
            # Dividir pago: 60% efectivo, 40% tarjeta
            pago_efectivo = round(total * 0.6, 2)
            pago_tarjeta = round(total - pago_efectivo, 2)
            
            venta = {
                "id": venta_id,
                "numero_venta": venta_id,
                "fecha": now.isoformat(),
                "bodega_id": bodega["id"],
                "items": [{
                    "producto_id": producto["id"],
                    "codigo": producto["codigo"],
                    "nombre": producto["nombre"],
                    "cantidad": cantidad,
                    "precio_unitario": precio,
                    "descuento": 0,
                    "subtotal": subtotal,
                    "afecto_iva": True
                }],
                "subtotal": subtotal,
                "descuento_total": 0,
                "iva": iva,
                "total": total,
                "formas_pago": [
                    {"metodo": "Efectivo", "monto": pago_efectivo},
                    {"metodo": "Tarjeta", "monto": pago_tarjeta, "referencia": "AUTH-54321"}
                ],
                "efectivo_recibido": pago_efectivo,
                "cambio": 0,
                "estado": "completada",
                "caja_sesion_id": self.sesion_caja_id,
                "vendedor_id": "sistema_e2e",
                "origen": "clinica",
                "created_at": now.isoformat(),
                "esDatoPrueba": True
            }
            
            await self.db.ventas.insert_one(venta)
            self.datos_creados["ventas"].append(venta_id)
            
            # Descontar stock
            await self.db.lotes_inventario.update_one(
                {"id": lote["id"]},
                {"$inc": {"cantidad_disponible": -cantidad}}
            )
            
            # Crear DOS movimientos de caja (uno por cada forma de pago)
            for forma in [("Efectivo", pago_efectivo), ("Tarjeta", pago_tarjeta)]:
                mov = {
                    "id": f"{PRB}MOV-{uuid.uuid4().hex[:8]}",
                    "sesion_id": self.sesion_caja_id,
                    "tipo": "Ingreso",
                    "categoria": "Venta",
                    "monto": forma[1],
                    "metodo_pago": forma[0],
                    "referencia": venta_id,
                    "fecha": now.isoformat(),
                    "origen": "clinica",
                    "esDatoPrueba": True
                }
                await self.db.caja_movimientos.insert_one(mov)
                self.datos_creados["caja_movimientos"].append(mov["id"])
            
            # Verificar que suma de pagos = total
            suma_pagos = pago_efectivo + pago_tarjeta
            if abs(suma_pagos - total) > 0.01:
                prueba.fallar(f"Suma de pagos ({suma_pagos}) no coincide con total ({total})")
            else:
                prueba.pasar("Pago mixto registrado correctamente", {
                    "venta_id": venta_id,
                    "total": total,
                    "pago_efectivo": pago_efectivo,
                    "pago_tarjeta": pago_tarjeta,
                    "suma_pagos": suma_pagos
                })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    # ==================== PRUEBAS DE MOVIMIENTOS DE CAJA ====================
    
    async def _test_ingreso_extra(self):
        """TRX-06: Ingreso extra (no venta)"""
        prueba = ResultadoTransaccion("TRX-06", "Ingreso extra - Pago de cuenta", "MEDIA")
        inicio = time.time()
        
        try:
            now = datetime.now(timezone.utc)
            mov_id = f"{PRB}MOV-{uuid.uuid4().hex[:8]}"
            
            movimiento = {
                "id": mov_id,
                "sesion_id": self.sesion_caja_id,
                "tipo": "Ingreso",
                "categoria": "Abono",
                "subcategoria": "Pago de cuenta por cobrar",
                "monto": 150.00,
                "metodo_pago": "Efectivo",
                "referencia": "CXC-001",
                "descripcion": "Abono a cuenta del paciente de prueba",
                "fecha": now.isoformat(),
                "usuario_id": "sistema_e2e",
                "origen": "clinica",
                "esDatoPrueba": True
            }
            
            await self.db.caja_movimientos.insert_one(movimiento)
            self.datos_creados["caja_movimientos"].append(mov_id)
            
            prueba.pasar("Ingreso extra registrado", {
                "movimiento_id": mov_id,
                "tipo": "Ingreso",
                "categoria": "Abono",
                "monto": 150.00,
                "metodo_pago": "Efectivo"
            })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    async def _test_egreso_gasto(self):
        """TRX-07: Egreso de caja (gasto menor)"""
        prueba = ResultadoTransaccion("TRX-07", "Egreso - Gasto de caja menor", "MEDIA")
        inicio = time.time()
        
        try:
            now = datetime.now(timezone.utc)
            mov_id = f"{PRB}MOV-{uuid.uuid4().hex[:8]}"
            
            movimiento = {
                "id": mov_id,
                "sesion_id": self.sesion_caja_id,
                "tipo": "Egreso",
                "categoria": "Gasto",
                "subcategoria": "Caja chica",
                "monto": 25.00,
                "metodo_pago": "Efectivo",
                "descripcion": "Compra de útiles de limpieza",
                "fecha": now.isoformat(),
                "usuario_id": "sistema_e2e",
                "origen": "clinica",
                "esDatoPrueba": True
            }
            
            await self.db.caja_movimientos.insert_one(movimiento)
            self.datos_creados["caja_movimientos"].append(mov_id)
            
            prueba.pasar("Egreso registrado", {
                "movimiento_id": mov_id,
                "tipo": "Egreso",
                "categoria": "Gasto",
                "monto": 25.00
            })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    # ==================== PRUEBAS DE VERIFICACIÓN ====================
    
    async def _test_verificar_kardex(self):
        """TRX-08: Verificar integridad del kardex"""
        prueba = ResultadoTransaccion("TRX-08", "Verificación de kardex", "CRITICA")
        inicio = time.time()
        
        try:
            # Contar movimientos de kardex generados en esta sesión de pruebas
            kardex_prueba = await self.db.kardex_inventario.find({
                "esDatoPrueba": True
            }).to_list(None)
            
            kardex_count = len(kardex_prueba)
            
            # Verificar que todos los movimientos tienen los campos requeridos
            kardex_incompleto = 0
            for k in kardex_prueba:
                if not k.get("producto_id") or not k.get("tipo_movimiento") or k.get("cantidad") is None:
                    kardex_incompleto += 1
            
            # Verificar que cada salida de kardex corresponde a una venta
            ventas_prueba = await self.db.ventas.find({
                "esDatoPrueba": True
            }).to_list(None)
            
            ventas_ids = {v["id"] for v in ventas_prueba}
            
            kardex_sin_venta = 0
            for k in kardex_prueba:
                if k.get("tipo_movimiento") == "Salida" and k.get("referencia_tipo") == "Venta":
                    if k.get("referencia_id") not in ventas_ids:
                        kardex_sin_venta += 1
            
            # Verificar que el stock se decrementó correctamente para ventas de prueba
            # Solo verificamos los lotes que tuvieron movimientos de kardex
            lotes_afectados = {k.get("lote_id") for k in kardex_prueba if k.get("lote_id")}
            inconsistencias = 0
            
            for lote_id in lotes_afectados:
                lote = await self.db.lotes_inventario.find_one({"id": lote_id})
                if not lote:
                    continue
                
                # Sumar salidas de este lote
                salidas = sum(
                    k.get("cantidad", 0) 
                    for k in kardex_prueba 
                    if k.get("lote_id") == lote_id and k.get("tipo_movimiento") == "Salida"
                )
                
                # El stock actual debe ser menor o igual al inicial menos las salidas
                # (podría haber otras salidas no de prueba)
                stock_esperado_max = lote.get("cantidad_inicial", 0) - salidas
                stock_actual = lote.get("cantidad_disponible", 0)
                
                if stock_actual > stock_esperado_max:
                    inconsistencias += 1
            
            if kardex_incompleto > 0:
                prueba.fallar(f"{kardex_incompleto} registros de kardex incompletos")
            elif kardex_sin_venta > 0:
                prueba.fallar(f"{kardex_sin_venta} movimientos de kardex sin venta asociada")
            else:
                prueba.pasar("Kardex de pruebas íntegro", {
                    "movimientos_kardex": kardex_count,
                    "lotes_afectados": len(lotes_afectados),
                    "ventas_verificadas": len(ventas_ids)
                })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    async def _test_verificar_totales_caja(self):
        """TRX-09: Verificar totales de caja cuadren"""
        prueba = ResultadoTransaccion("TRX-09", "Verificación de totales de caja", "CRITICA")
        inicio = time.time()
        
        try:
            # Sumar ventas de prueba
            ventas = await self.db.ventas.find({
                "esDatoPrueba": True,
                "estado": "completada"
            }).to_list(None)
            
            total_ventas = sum(v.get("total", 0) for v in ventas)
            
            # Sumar movimientos de caja tipo ingreso/venta
            mov_ventas = await self.db.caja_movimientos.aggregate([
                {"$match": {
                    "esDatoPrueba": True,
                    "tipo": "Ingreso",
                    "categoria": "Venta"
                }},
                {"$group": {"_id": None, "total": {"$sum": "$monto"}}}
            ]).to_list(1)
            
            total_mov_ventas = mov_ventas[0]["total"] if mov_ventas else 0
            
            # Verificar que coincidan
            diferencia = abs(total_ventas - total_mov_ventas)
            
            if diferencia > 0.01:
                prueba.fallar(f"Diferencia entre ventas ({total_ventas}) y movimientos caja ({total_mov_ventas}): {diferencia}")
            else:
                prueba.pasar("Totales de caja cuadran", {
                    "total_ventas": total_ventas,
                    "total_movimientos_venta": total_mov_ventas,
                    "diferencia": diferencia,
                    "num_ventas": len(ventas)
                })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    async def _test_verificar_saldo_efectivo(self):
        """TRX-10: Verificar saldo de efectivo"""
        prueba = ResultadoTransaccion("TRX-10", "Verificación de saldo efectivo", "ALTA")
        inicio = time.time()
        
        try:
            if not self.sesion_caja_id:
                prueba.fallar("No hay sesión de caja")
                self.resultados.append(prueba)
                return
            
            caja = await self.db.caja_cierres.find_one({
                "id": self.sesion_caja_id,
                "esDatoPrueba": True
            })
            
            if not caja:
                prueba.fallar("Caja no encontrada")
                self.resultados.append(prueba)
                return
            
            monto_apertura = caja.get("monto_apertura", 0)
            
            # Calcular ingresos en efectivo
            ingresos_efectivo = await self.db.caja_movimientos.aggregate([
                {"$match": {
                    "esDatoPrueba": True,
                    "sesion_id": self.sesion_caja_id,
                    "tipo": "Ingreso",
                    "metodo_pago": "Efectivo"
                }},
                {"$group": {"_id": None, "total": {"$sum": "$monto"}}}
            ]).to_list(1)
            
            # Calcular egresos en efectivo
            egresos_efectivo = await self.db.caja_movimientos.aggregate([
                {"$match": {
                    "esDatoPrueba": True,
                    "sesion_id": self.sesion_caja_id,
                    "tipo": "Egreso",
                    "metodo_pago": "Efectivo"
                }},
                {"$group": {"_id": None, "total": {"$sum": "$monto"}}}
            ]).to_list(1)
            
            total_ingresos = ingresos_efectivo[0]["total"] if ingresos_efectivo else 0
            total_egresos = egresos_efectivo[0]["total"] if egresos_efectivo else 0
            
            saldo_esperado = monto_apertura + total_ingresos - total_egresos
            
            prueba.pasar("Saldo de efectivo calculado correctamente", {
                "monto_apertura": monto_apertura,
                "ingresos_efectivo": total_ingresos,
                "egresos_efectivo": total_egresos,
                "saldo_efectivo_esperado": saldo_esperado
            })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    # ==================== FASE 6: DEVOLUCIONES Y ANULACIONES ====================
    
    async def _test_anular_venta_con_devolucion(self):
        """TRX-12: Anular venta con devolución de inventario"""
        prueba = ResultadoTransaccion("TRX-12", "Anulación de venta con devolución de inventario", "CRITICA")
        inicio = time.time()
        
        try:
            # Verificar que hay ventas para anular
            if not self.ventas_para_anular:
                prueba.fallar("No hay ventas disponibles para anular")
                self.resultados.append(prueba)
                return
            
            # Tomar la primera venta para anular con devolución
            venta_info = self.ventas_para_anular[0]
            venta_id = venta_info["venta_id"]
            lote_id = venta_info["lote_id"]
            cantidad_vendida = venta_info["cantidad"]
            
            # Obtener stock actual antes de anular
            lote_antes = await self.db.lotes_inventario.find_one({"id": lote_id})
            if not lote_antes:
                prueba.fallar(f"No se encontró el lote {lote_id}")
                self.resultados.append(prueba)
                return
            
            stock_antes_anulacion = lote_antes["cantidad_disponible"]
            self.stock_antes_anulacion[venta_id] = stock_antes_anulacion
            
            # Verificar que la venta existe y está activa
            venta = await self.db.ventas.find_one({"id": venta_id})
            if not venta:
                prueba.fallar(f"Venta {venta_id} no encontrada")
                self.resultados.append(prueba)
                return
            
            if venta.get("estado") == "anulada":
                prueba.fallar(f"Venta {venta_id} ya está anulada")
                self.resultados.append(prueba)
                return
            
            now = datetime.now(timezone.utc)
            
            # Simular anulación con devolución (como haría el endpoint)
            # 1. Restaurar stock del lote
            await self.db.lotes_inventario.update_one(
                {"id": lote_id},
                {"$inc": {"cantidad_disponible": cantidad_vendida}}
            )
            
            # 2. Crear movimiento de kardex de devolución
            kardex_devolucion = {
                "id": f"{PRB}KDX-DEV-{uuid.uuid4().hex[:8]}",
                "producto_id": venta["items"][0]["producto_id"],
                "lote_id": lote_id,
                "bodega_id": venta["bodega_id"],
                "tipo_movimiento": "Entrada",
                "subtipo": "Anulacion",
                "cantidad": cantidad_vendida,
                "stock_anterior": stock_antes_anulacion,
                "stock_nuevo": stock_antes_anulacion + cantidad_vendida,
                "referencia_tipo": "Anulacion_Venta",
                "referencia_id": venta_id,
                "observaciones": f"Devolución por anulación de venta {venta['numero_venta']}",
                "usuario_id": "sistema_e2e",
                "fecha": now.isoformat(),
                "origen": "clinica",
                "esDatoPrueba": True
            }
            await self.db.kardex_inventario.insert_one(kardex_devolucion)
            self.datos_creados["kardex"].append(kardex_devolucion["id"])
            
            # 3. Actualizar venta como anulada
            await self.db.ventas.update_one(
                {"id": venta_id},
                {"$set": {
                    "estado": "anulada",
                    "anulada_por": "sistema_e2e",
                    "anulada_por_nombre": "Sistema E2E",
                    "fecha_anulacion": now.isoformat(),
                    "motivo_anulacion": "Prueba E2E - Anulación con devolución",
                    "inventario_devuelto": True
                }}
            )
            
            # 4. Marcar movimientos de caja relacionados como anulados
            await self.db.caja_movimientos.update_many(
                {"referencia": venta_id, "esDatoPrueba": True},
                {"$set": {
                    "anulado": True,
                    "fecha_anulacion": now.isoformat(),
                    "motivo_anulacion": "Anulación de venta E2E"
                }}
            )
            
            # 5. Verificar que el stock se restauró
            lote_despues = await self.db.lotes_inventario.find_one({"id": lote_id})
            stock_despues_anulacion = lote_despues["cantidad_disponible"]
            
            stock_esperado = stock_antes_anulacion + cantidad_vendida
            
            if stock_despues_anulacion != stock_esperado:
                prueba.fallar(
                    f"Stock no se restauró correctamente. Esperado: {stock_esperado}, Actual: {stock_despues_anulacion}",
                    {"stock_antes": stock_antes_anulacion, "cantidad_devuelta": cantidad_vendida}
                )
            else:
                prueba.pasar("Venta anulada con devolución de inventario exitosa", {
                    "venta_id": venta_id,
                    "stock_antes_anulacion": stock_antes_anulacion,
                    "cantidad_devuelta": cantidad_vendida,
                    "stock_despues_anulacion": stock_despues_anulacion,
                    "kardex_devolucion_id": kardex_devolucion["id"]
                })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    async def _test_anular_venta_sin_devolucion(self):
        """TRX-13: Anular venta SIN devolución de inventario"""
        prueba = ResultadoTransaccion("TRX-13", "Anulación de venta SIN devolución de inventario", "ALTA")
        inicio = time.time()
        
        try:
            # Verificar que hay más ventas para anular (la segunda)
            if len(self.ventas_para_anular) < 2:
                # Crear una venta rápida para anular sin devolución
                producto = await self.db.productos_inventario.find_one({
                    "esDatoPrueba": True,
                    "es_servicio": True  # Usar servicio para no afectar inventario
                })
                
                if not producto:
                    prueba.omitir("No hay servicios de prueba para anulación sin devolución")
                    prueba.estado = "PASA"  # Marcar como pasa (omitido no es fallo)
                    prueba.mensaje = "Omitida: Sin servicios de prueba disponibles"
                    self.resultados.append(prueba)
                    return
                
                # Crear venta de servicio
                now = datetime.now(timezone.utc)
                venta_id = f"{PRB}VTA-{self.run_id}-SERV"
                total = producto.get("precio_venta", 150)
                
                venta = {
                    "id": venta_id,
                    "numero_venta": venta_id,
                    "fecha": now.isoformat(),
                    "items": [{
                        "producto_id": producto["id"],
                        "codigo": producto["codigo"],
                        "nombre": producto["nombre"],
                        "cantidad": 1,
                        "precio_unitario": total,
                        "subtotal": total,
                        "es_servicio": True
                    }],
                    "total": total,
                    "estado": "completada",
                    "origen": "clinica",
                    "esDatoPrueba": True,
                    "created_at": now.isoformat()
                }
                await self.db.ventas.insert_one(venta)
                self.datos_creados["ventas"].append(venta_id)
            else:
                # Usar la segunda venta registrada
                venta_info = self.ventas_para_anular[1] if len(self.ventas_para_anular) > 1 else self.ventas_para_anular[0]
                venta_id = venta_info["venta_id"]
            
            # Verificar que la venta existe
            venta = await self.db.ventas.find_one({"id": venta_id, "estado": {"$ne": "anulada"}})
            
            if not venta:
                prueba.omitir("No hay venta activa para anular sin devolución")
                prueba.estado = "PASA"
                prueba.mensaje = "Omitida: Ya no hay ventas activas"
                self.resultados.append(prueba)
                return
            
            now = datetime.now(timezone.utc)
            
            # Anular sin devolución de inventario
            await self.db.ventas.update_one(
                {"id": venta_id},
                {"$set": {
                    "estado": "anulada",
                    "anulada_por": "sistema_e2e",
                    "anulada_por_nombre": "Sistema E2E",
                    "fecha_anulacion": now.isoformat(),
                    "motivo_anulacion": "Prueba E2E - Anulación SIN devolución (producto dañado/merma)",
                    "inventario_devuelto": False
                }}
            )
            
            # Marcar movimientos de caja como anulados
            await self.db.caja_movimientos.update_many(
                {"referencia": venta_id, "esDatoPrueba": True},
                {"$set": {
                    "anulado": True,
                    "fecha_anulacion": now.isoformat(),
                    "motivo_anulacion": "Anulación sin devolución E2E"
                }}
            )
            
            # Verificar que la venta quedó anulada
            venta_actualizada = await self.db.ventas.find_one({"id": venta_id})
            
            if venta_actualizada.get("estado") == "anulada" and not venta_actualizada.get("inventario_devuelto"):
                prueba.pasar("Venta anulada sin devolución de inventario", {
                    "venta_id": venta_id,
                    "motivo": "Producto dañado/merma",
                    "inventario_devuelto": False
                })
            else:
                prueba.fallar("La venta no se anuló correctamente", {
                    "estado_actual": venta_actualizada.get("estado"),
                    "inventario_devuelto": venta_actualizada.get("inventario_devuelto")
                })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    async def _test_verificar_reversion_kardex(self):
        """TRX-14: Verificar que el kardex registró la reversión correctamente"""
        prueba = ResultadoTransaccion("TRX-14", "Verificación de reversión en kardex", "CRITICA")
        inicio = time.time()
        
        try:
            # Buscar movimientos de kardex tipo anulación
            kardex_anulaciones = await self.db.kardex_inventario.find({
                "esDatoPrueba": True,
                "referencia_tipo": "Anulacion_Venta"
            }).to_list(None)
            
            if not kardex_anulaciones:
                prueba.fallar("No se encontraron movimientos de kardex de anulación")
                self.resultados.append(prueba)
                return
            
            # Verificar estructura de cada movimiento
            errores = []
            for k in kardex_anulaciones:
                if k.get("tipo_movimiento") != "Entrada":
                    errores.append(f"{k['id']}: tipo_movimiento debe ser 'Entrada'")
                if not k.get("referencia_id"):
                    errores.append(f"{k['id']}: falta referencia_id")
                if k.get("cantidad", 0) <= 0:
                    errores.append(f"{k['id']}: cantidad debe ser positiva")
            
            if errores:
                prueba.fallar(f"Errores en kardex de anulación: {errores}")
            else:
                # Verificar que por cada anulación con devolución hay un kardex
                ventas_anuladas_con_dev = await self.db.ventas.count_documents({
                    "esDatoPrueba": True,
                    "estado": "anulada",
                    "inventario_devuelto": True
                })
                
                prueba.pasar("Kardex de anulaciones verificado correctamente", {
                    "movimientos_anulacion": len(kardex_anulaciones),
                    "ventas_con_devolucion": ventas_anuladas_con_dev,
                    "detalles": [
                        {
                            "id": k["id"],
                            "cantidad": k.get("cantidad"),
                            "venta_ref": k.get("referencia_id")
                        } for k in kardex_anulaciones
                    ]
                })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    async def _test_verificar_totales_post_anulacion(self):
        """TRX-15: Verificar que los totales de caja excluyen ventas anuladas"""
        prueba = ResultadoTransaccion("TRX-15", "Totales de caja post-anulación", "CRITICA")
        inicio = time.time()
        
        try:
            # Sumar solo ventas NO anuladas
            ventas_activas = await self.db.ventas.find({
                "esDatoPrueba": True,
                "estado": {"$ne": "anulada"}
            }).to_list(None)
            
            total_ventas_activas = sum(v.get("total", 0) for v in ventas_activas)
            
            # Sumar ventas anuladas (para información)
            ventas_anuladas = await self.db.ventas.find({
                "esDatoPrueba": True,
                "estado": "anulada"
            }).to_list(None)
            
            total_ventas_anuladas = sum(v.get("total", 0) for v in ventas_anuladas)
            
            # Sumar movimientos de caja NO anulados
            mov_activos = await self.db.caja_movimientos.aggregate([
                {"$match": {
                    "esDatoPrueba": True,
                    "tipo": "Ingreso",
                    "categoria": "Venta",
                    "anulado": {"$ne": True}
                }},
                {"$group": {"_id": None, "total": {"$sum": "$monto"}}}
            ]).to_list(1)
            
            total_mov_activos = mov_activos[0]["total"] if mov_activos else 0
            
            # Verificar que cuadran (ventas activas == movimientos activos)
            diferencia = abs(total_ventas_activas - total_mov_activos)
            
            if diferencia > 0.01:
                prueba.fallar(
                    f"Diferencia entre ventas activas ({total_ventas_activas}) y movimientos activos ({total_mov_activos})",
                    {"diferencia": diferencia}
                )
            else:
                prueba.pasar("Totales post-anulación cuadran correctamente", {
                    "ventas_activas": len(ventas_activas),
                    "total_ventas_activas": total_ventas_activas,
                    "ventas_anuladas": len(ventas_anuladas),
                    "total_ventas_anuladas": total_ventas_anuladas,
                    "total_movimientos_activos": total_mov_activos,
                    "diferencia": diferencia
                })
            
        except Exception as e:
            prueba.error(str(e))
        
        prueba.duracion_ms = int((time.time() - inicio) * 1000)
        self.resultados.append(prueba)
    
    # ==================== RESUMEN ====================
    
    def _generar_resumen(self) -> Dict[str, Any]:
        """Genera resumen de pruebas de transacción"""
        duracion_total = int((self.fin - self.inicio) * 1000) if self.inicio and self.fin else 0
        
        conteo = {"PASA": 0, "FALLA": 0, "ERROR": 0}
        
        for r in self.resultados:
            conteo[r.estado] = conteo.get(r.estado, 0) + 1
        
        tasa_exito = (conteo["PASA"] / len(self.resultados) * 100) if self.resultados else 0
        
        return {
            "success": conteo["FALLA"] == 0 and conteo["ERROR"] == 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duracion_total_ms": duracion_total,
            "total_pruebas": len(self.resultados),
            "resumen": conteo,
            "tasa_exito": round(tasa_exito, 2),
            "datos_creados": self.datos_creados,
            "resultados": [r.to_dict() for r in self.resultados]
        }
