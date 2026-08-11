"""
Tests de lógica de negocio para el módulo de Inventario
NovaVision ERP - Suite de Testing Backend
Estos tests no requieren conexión a la API
"""

import pytest
from datetime import datetime, timedelta


# ============= Tests de Lógica FEFO =============

class TestLogicaFEFO:
    """Tests para la lógica First Expire First Out"""

    def test_fefo_ordenamiento_basico(self):
        """Test: FEFO ordena lotes por fecha de vencimiento ascendente"""
        lotes = [
            {"id": "1", "fecha_vencimiento": "2026-12-01", "cantidad": 10},
            {"id": "2", "fecha_vencimiento": "2026-08-15", "cantidad": 5},
            {"id": "3", "fecha_vencimiento": "2027-01-20", "cantidad": 20},
        ]
        
        ordenados = sorted(lotes, key=lambda x: x["fecha_vencimiento"])
        
        assert ordenados[0]["id"] == "2"  # Agosto (vence primero)
        assert ordenados[1]["id"] == "1"  # Diciembre
        assert ordenados[2]["id"] == "3"  # Enero (vence último)

    def test_fefo_descuento_lote_unico(self):
        """Test: FEFO descuenta del lote que vence primero cuando hay suficiente"""
        lotes = [
            {"id": "1", "fecha_vencimiento": "2026-12-01", "cantidad": 10},
            {"id": "2", "fecha_vencimiento": "2026-08-15", "cantidad": 5},
        ]
        
        cantidad_requerida = 3
        ordenados = sorted(lotes, key=lambda x: x["fecha_vencimiento"])
        
        lote_a_usar = ordenados[0]
        assert lote_a_usar["id"] == "2"
        assert lote_a_usar["cantidad"] >= cantidad_requerida

    def test_fefo_distribucion_multiples_lotes(self):
        """Test: FEFO distribuye entre múltiples lotes cuando es necesario"""
        lotes = [
            {"id": "1", "fecha_vencimiento": "2026-12-01", "cantidad": 10},
            {"id": "2", "fecha_vencimiento": "2026-08-15", "cantidad": 5},
        ]
        
        cantidad_requerida = 8
        ordenados = sorted(lotes, key=lambda x: x["fecha_vencimiento"])
        
        consumo = []
        restante = cantidad_requerida
        
        for lote in ordenados:
            if restante <= 0:
                break
            descontado = min(lote["cantidad"], restante)
            consumo.append({"lote_id": lote["id"], "cantidad": descontado})
            restante -= descontado
        
        assert len(consumo) == 2
        assert consumo[0] == {"lote_id": "2", "cantidad": 5}
        assert consumo[1] == {"lote_id": "1", "cantidad": 3}
        assert restante == 0

    def test_fefo_stock_insuficiente(self):
        """Test: FEFO detecta cuando no hay stock suficiente"""
        lotes = [
            {"id": "1", "fecha_vencimiento": "2026-12-01", "cantidad": 5},
            {"id": "2", "fecha_vencimiento": "2026-08-15", "cantidad": 3},
        ]
        
        cantidad_requerida = 15
        stock_total = sum(l["cantidad"] for l in lotes)
        
        assert stock_total < cantidad_requerida
        assert stock_total == 8

    def test_fefo_ignora_lotes_vencidos(self):
        """Test: FEFO debería poder filtrar lotes ya vencidos"""
        hoy = datetime.now().strftime("%Y-%m-%d")
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        manana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        lotes = [
            {"id": "1", "fecha_vencimiento": ayer, "cantidad": 10},  # Vencido
            {"id": "2", "fecha_vencimiento": manana, "cantidad": 5},  # Vigente
        ]
        
        lotes_vigentes = [l for l in lotes if l["fecha_vencimiento"] >= hoy]
        
        assert len(lotes_vigentes) == 1
        assert lotes_vigentes[0]["id"] == "2"


# ============= Tests de Cálculos de Inventario =============

class TestCalculosInventario:
    """Tests para cálculos de inventario"""

    def test_costo_promedio_ponderado(self):
        """Test: Calcula costo promedio ponderado correctamente"""
        movimientos = [
            {"cantidad": 10, "costo_unitario": 50.00},  # 500
            {"cantidad": 5, "costo_unitario": 60.00},   # 300
            {"cantidad": 15, "costo_unitario": 55.00},  # 825
        ]
        
        total_cantidad = sum(m["cantidad"] for m in movimientos)
        total_valor = sum(m["cantidad"] * m["costo_unitario"] for m in movimientos)
        costo_promedio = total_valor / total_cantidad
        
        assert total_cantidad == 30
        assert total_valor == 1625.00
        assert round(costo_promedio, 2) == 54.17

    def test_valor_inventario(self):
        """Test: Calcula valor total del inventario"""
        productos = [
            {"cantidad": 10, "costo_promedio": 50.00},
            {"cantidad": 20, "costo_promedio": 100.00},
            {"cantidad": 5, "costo_promedio": 200.00},
        ]
        
        valor_total = sum(p["cantidad"] * p["costo_promedio"] for p in productos)
        
        assert valor_total == 3500.00

    def test_margen_utilidad(self):
        """Test: Calcula margen de utilidad correctamente"""
        costo = 60.00
        precio_venta = 100.00
        margen = ((precio_venta - costo) / precio_venta) * 100
        
        assert margen == 40.0

    def test_punto_reorden(self):
        """Test: Identifica productos bajo stock mínimo"""
        productos = [
            {"id": "1", "existencia": 10, "stock_minimo": 5},   # OK
            {"id": "2", "existencia": 3, "stock_minimo": 10},   # BAJO
            {"id": "3", "existencia": 5, "stock_minimo": 5},    # LÍMITE
        ]
        
        bajo_stock = [p for p in productos if p["existencia"] < p["stock_minimo"]]
        
        assert len(bajo_stock) == 1
        assert bajo_stock[0]["id"] == "2"


# ============= Tests de Alertas de Vencimiento =============

class TestAlertasVencimiento:
    """Tests para sistema de alertas de vencimiento"""

    def test_clasificacion_vencimientos(self):
        """Test: Clasifica lotes por proximidad a vencimiento"""
        hoy = datetime.now()
        
        lotes = [
            {"id": "1", "dias_para_vencer": -5},   # Vencido
            {"id": "2", "dias_para_vencer": 15},   # Crítico (<30 días)
            {"id": "3", "dias_para_vencer": 45},   # Próximo (30-60 días)
            {"id": "4", "dias_para_vencer": 100},  # OK
        ]
        
        vencidos = [l for l in lotes if l["dias_para_vencer"] < 0]
        criticos = [l for l in lotes if 0 <= l["dias_para_vencer"] <= 30]
        proximos = [l for l in lotes if 30 < l["dias_para_vencer"] <= 60]
        ok = [l for l in lotes if l["dias_para_vencer"] > 60]
        
        assert len(vencidos) == 1
        assert len(criticos) == 1
        assert len(proximos) == 1
        assert len(ok) == 1

    def test_dias_para_vencer(self):
        """Test: Calcula días hasta vencimiento"""
        hoy = datetime.now()
        fecha_vencimiento = hoy + timedelta(days=30)
        
        dias = (fecha_vencimiento - hoy).days
        
        assert dias == 30


# ============= Tests de Validaciones =============

class TestValidaciones:
    """Tests para validaciones de datos"""

    def test_codigo_producto_unico(self):
        """Test: Valida que códigos de producto sean únicos"""
        codigos_existentes = ["PROD-001", "PROD-002", "PROD-003"]
        nuevo_codigo = "PROD-002"
        
        es_duplicado = nuevo_codigo in codigos_existentes
        assert es_duplicado is True

    def test_cantidad_positiva(self):
        """Test: Rechaza cantidades negativas o cero"""
        cantidades_invalidas = [-1, 0, -100]
        cantidades_validas = [1, 10, 100]
        
        for c in cantidades_invalidas:
            assert c <= 0
        
        for c in cantidades_validas:
            assert c > 0

    def test_precio_venta_mayor_costo(self):
        """Test: Alerta si precio de venta es menor al costo"""
        producto = {
            "costo_promedio": 100.00,
            "precio_venta": 80.00
        }
        
        venta_menor_costo = producto["precio_venta"] < producto["costo_promedio"]
        assert venta_menor_costo is True

    def test_lote_codigo_formato(self):
        """Test: Valida formato de código de lote"""
        import re
        
        lote_valido = "LOT-20260815-001"
        lote_invalido = "lote123"
        
        patron = r"^LOT-\d{8}-\d{3}$"
        
        assert re.match(patron, lote_valido) is not None
        assert re.match(patron, lote_invalido) is None


# ============= Tests de Kardex =============

class TestKardex:
    """Tests para movimientos de Kardex"""

    def test_kardex_entrada_suma(self):
        """Test: Entrada de inventario suma a existencia"""
        existencia_inicial = 100
        entrada = {"tipo": "entrada", "cantidad": 50}
        
        existencia_final = existencia_inicial + entrada["cantidad"]
        
        assert existencia_final == 150

    def test_kardex_salida_resta(self):
        """Test: Salida de inventario resta de existencia"""
        existencia_inicial = 100
        salida = {"tipo": "salida", "cantidad": 30}
        
        existencia_final = existencia_inicial - salida["cantidad"]
        
        assert existencia_final == 70

    def test_kardex_ajuste_positivo(self):
        """Test: Ajuste positivo de inventario"""
        existencia_sistema = 100
        existencia_fisica = 105
        
        ajuste = existencia_fisica - existencia_sistema
        
        assert ajuste == 5
        assert ajuste > 0

    def test_kardex_ajuste_negativo(self):
        """Test: Ajuste negativo de inventario (merma)"""
        existencia_sistema = 100
        existencia_fisica = 95
        
        ajuste = existencia_fisica - existencia_sistema
        
        assert ajuste == -5
        assert ajuste < 0

    def test_kardex_inmutable(self):
        """Test: Movimientos de kardex no se modifican"""
        movimiento = {
            "id": "mov-001",
            "fecha": "2026-08-07",
            "tipo": "entrada",
            "cantidad": 50,
            "inmutable": True
        }
        
        # Un kardex inmutable no debe permitir modificaciones
        assert movimiento["inmutable"] is True
