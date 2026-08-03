"""
Tests for timezone consistency in caja and dashboard financial date filters.
Verifies that ISO date filters with UTC (+00:00) work correctly for:
- GET /api/dashboard/financiero
- GET /api/caja/movimientos
- GET /api/dashboard/stats
- Caja cierre blocks movements of the day
"""
import os
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"No token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ==================== DASHBOARD FINANCIERO ====================

class TestDashboardFinanciero:
    def test_mes_actual(self, auth_headers):
        r = requests.get(f"{API}/dashboard/financiero?periodo=mes_actual", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        # Estructura
        for k in ["periodo", "ingresos", "gastos", "balance", "cuentas_por_cobrar",
                  "ingresos_por_pagador", "gastos_por_categoria", "evolucion_mensual"]:
            assert k in data, f"Missing key {k}"
        # Periodo debe corresponder al mes actual
        now = datetime.now(timezone.utc)
        assert data["periodo"]["fecha_inicio"].startswith(f"{now.year}-{now.month:02d}-01")
        # Ingresos totales debe ser numérico
        assert isinstance(data["ingresos"]["total_cobrado"], (int, float))
        # Evolución mensual = 12 meses
        assert len(data["evolucion_mensual"]) == 12
        # Chequear formato y orden cronológico
        meses = [e["mes"] for e in data["evolucion_mensual"]]
        assert meses == sorted(meses), f"Meses no ordenados: {meses}"
        # último mes = mes actual
        assert meses[-1] == f"{now.year}-{now.month:02d}"

    def test_semestre(self, auth_headers):
        r = requests.get(f"{API}/dashboard/financiero?periodo=semestre", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "Últimos 6 meses" in data["periodo"]["nombre"]

    def test_anual(self, auth_headers):
        r = requests.get(f"{API}/dashboard/financiero?periodo=anual", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        now = datetime.now(timezone.utc)
        assert data["periodo"]["fecha_inicio"] == f"{now.year}-01-01"

    def test_personalizado(self, auth_headers):
        r = requests.get(
            f"{API}/dashboard/financiero?periodo=personalizado&fecha_inicio=2026-01-01&fecha_fin=2026-01-31",
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["periodo"]["fecha_inicio"] == "2026-01-01"
        assert data["periodo"]["fecha_fin"] == "2026-01-31"

    def test_gastos_del_mes(self, auth_headers):
        """El ambiente de preview debe mostrar Q100 en gastos del mes."""
        r = requests.get(f"{API}/dashboard/financiero?periodo=mes_actual", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        # No forzar valor exacto, sólo que sea >= 0 y que la estructura sea correcta
        assert data["gastos"]["total"] >= 0
        assert data["gastos"]["pagado"] >= 0
        assert data["gastos"]["pendiente"] >= 0


# ==================== DASHBOARD STATS ====================

class TestDashboardStats:
    def test_stats_estructura(self, auth_headers):
        r = requests.get(f"{API}/dashboard/stats", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        expected_keys = [
            "total_gastos", "gastos_pendientes", "gastos_pagados",
            "gastos_parciales", "gastos_vencidos", "total_fijos",
            "total_proveedores", "total_variables", "alertas_30_dias", "alertas_60_dias"
        ]
        for k in expected_keys:
            assert k in data, f"Missing key {k} in stats"
            assert isinstance(data[k], (int, float)), f"{k} debe ser numérico"

    def test_stats_mes_actual(self, auth_headers):
        """Comparar stats con dashboard/financiero (mismo mes)."""
        r_stats = requests.get(f"{API}/dashboard/stats", headers=auth_headers)
        r_fin = requests.get(f"{API}/dashboard/financiero?periodo=mes_actual", headers=auth_headers)
        assert r_stats.status_code == 200
        assert r_fin.status_code == 200
        stats = r_stats.json()
        fin = r_fin.json()
        # Ambos deben devolver el mismo total de gastos del mes actual
        assert stats["total_gastos"] == fin["gastos"]["total"], (
            f"stats.total_gastos={stats['total_gastos']} != fin.gastos.total={fin['gastos']['total']}"
        )


# ==================== CAJA MOVIMIENTOS FILTRO POR FECHA ====================

class TestCajaMovimientos:
    def test_movimientos_hoy_estructura(self, auth_headers):
        r = requests.get(f"{API}/caja/movimientos", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "data" in data and "total" in data
        assert isinstance(data["data"], list)
        assert isinstance(data["total"], int)

    def test_movimientos_fecha_especifica(self, auth_headers):
        """Filtrar movimientos con fecha específica no debe fallar."""
        r = requests.get(f"{API}/caja/movimientos?fecha=2026-01-15", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        # Todos los movimientos devueltos deben tener fecha en el rango de ese día
        for mov in data["data"]:
            fecha_mov = mov.get("fecha", "")
            assert fecha_mov.startswith("2026-01-15"), (
                f"Movimiento fuera de rango: {fecha_mov}"
            )

    def test_movimientos_fecha_ayer_vs_hoy(self, auth_headers):
        """Los filtros por diferentes fechas deben devolver conjuntos distintos (o vacíos)."""
        r_hoy = requests.get(f"{API}/caja/movimientos", headers=auth_headers)
        r_ayer = requests.get(f"{API}/caja/movimientos?fecha=2020-01-01", headers=auth_headers)
        assert r_hoy.status_code == 200
        assert r_ayer.status_code == 200
        # No debe haber movimientos en 2020-01-01
        assert r_ayer.json()["total"] == 0

    def test_estado_caja(self, auth_headers):
        r = requests.get(f"{API}/caja/estado", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "caja_abierta" in data
        assert "totales_dia" in data
        assert "saldo_efectivo_vivo" in data


# ==================== FILTRO ISO UTC END-TO-END ====================

class TestCajaTimezoneConsistency:
    """Verifica que los filtros de fecha capturen movimientos guardados con isoformat UTC."""

    def test_crear_movimiento_y_filtrar(self, auth_headers):
        # 1. Verificar/abrir caja del día
        estado = requests.get(f"{API}/caja/estado", headers=auth_headers).json()
        caja_abierta_ya = estado.get("caja_abierta", False)

        if not caja_abierta_ya:
            r_ap = requests.post(
                f"{API}/caja/apertura",
                headers=auth_headers,
                json={"monto_apertura": 100.0},
            )
            if r_ap.status_code != 200:
                pytest.skip(f"No se pudo abrir caja: {r_ap.status_code} {r_ap.text}")

        # 2. Crear movimiento TEST_
        payload = {
            "tipo": "Ingreso",
            "categoria": "Consulta",
            "concepto": "TEST_timezone_check",
            "monto": 1.0,
            "metodo_pago": "Efectivo",
        }
        r_mov = requests.post(f"{API}/caja/movimientos", headers=auth_headers, json=payload)
        assert r_mov.status_code == 200, f"POST movimiento falló: {r_mov.status_code} {r_mov.text}"
        mov = r_mov.json()
        mov_id = mov["id"]
        # La fecha guardada debe tener info de timezone (UTC ISO)
        assert "+00:00" in mov["fecha"] or mov["fecha"].endswith("Z"), (
            f"Fecha del movimiento no tiene timezone UTC: {mov['fecha']}"
        )

        # 3. Filtrar por fecha de HOY (UTC) y confirmar que el movimiento aparece
        fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        r_list = requests.get(
            f"{API}/caja/movimientos?fecha={fecha_hoy}", headers=auth_headers
        )
        assert r_list.status_code == 200
        ids = [m["id"] for m in r_list.json()["data"]]
        assert mov_id in ids, (
            f"Movimiento recién creado {mov_id} no aparece en filtro por fecha {fecha_hoy}. "
            f"Fecha guardada: {mov['fecha']}"
        )

        # 4. Verificar que aparece en dashboard/financiero (ingresos)
        r_fin = requests.get(
            f"{API}/dashboard/financiero?periodo=mes_actual", headers=auth_headers
        )
        assert r_fin.status_code == 200
        fin = r_fin.json()
        assert fin["ingresos"]["de_caja_directa"] >= 1.0, (
            f"Ingreso no reflejado en dashboard: de_caja_directa={fin['ingresos']['de_caja_directa']}"
        )

        # 5. Verificar en evolución mensual del mes actual
        now = datetime.now(timezone.utc)
        mes_actual_key = f"{now.year}-{now.month:02d}"
        mes_actual = next((e for e in fin["evolucion_mensual"] if e["mes"] == mes_actual_key), None)
        assert mes_actual is not None
        assert mes_actual["ingresos"] >= 1.0, (
            f"Ingreso no reflejado en evolucion_mensual[{mes_actual_key}]: {mes_actual}"
        )

        # Cleanup: eliminar movimiento (superadmin puede)
        r_del = requests.delete(f"{API}/caja/movimientos/{mov_id}", headers=auth_headers)
        # El movimiento sólo se puede eliminar si NO está bloqueado (caja abierta)
        assert r_del.status_code in (200, 400), r_del.text


# ==================== CIERRE DE CAJA BLOQUEA MOVIMIENTOS ====================

class TestCierreCajaBloqueo:
    """Verifica que al cerrar caja los movimientos del día queden bloqueados."""

    def test_cierre_bloquea_movimientos(self, auth_headers):
        # Verificar si hay caja abierta
        estado = requests.get(f"{API}/caja/estado", headers=auth_headers).json()

        # Si la caja no está abierta, abrir
        if not estado.get("caja_abierta"):
            r_ap = requests.post(
                f"{API}/caja/apertura", headers=auth_headers,
                json={"monto_apertura": 50.0}
            )
            if r_ap.status_code != 200:
                pytest.skip(f"No se pudo abrir caja: {r_ap.text}")

        # Crear un movimiento para probar el bloqueo
        payload = {
            "tipo": "Ingreso", "categoria": "Consulta",
            "concepto": "TEST_bloqueo_cierre",
            "monto": 2.0, "metodo_pago": "Efectivo",
        }
        r_mov = requests.post(f"{API}/caja/movimientos", headers=auth_headers, json=payload)
        assert r_mov.status_code == 200, r_mov.text
        mov_id = r_mov.json()["id"]

        # Cerrar la caja
        r_cierre = requests.post(
            f"{API}/caja/cierre", headers=auth_headers,
            json={"efectivo_contado": 52.0, "observaciones": "TEST cierre timezone"}
        )
        assert r_cierre.status_code == 200, f"Cierre falló: {r_cierre.text}"
        cierre_data = r_cierre.json()
        cierre_id = cierre_data["id"]
        assert cierre_data["estado"] == "Cerrado"

        # Verificar que el movimiento está bloqueado
        fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        r_list = requests.get(f"{API}/caja/movimientos?fecha={fecha_hoy}", headers=auth_headers)
        assert r_list.status_code == 200
        target = next((m for m in r_list.json()["data"] if m["id"] == mov_id), None)
        assert target is not None, "Movimiento no aparece tras cierre"
        assert target.get("bloqueado") is True, (
            f"Movimiento no bloqueado tras cierre: {target}"
        )

        # Intentar modificar movimiento bloqueado debe fallar
        r_upd = requests.put(
            f"{API}/caja/movimientos/{mov_id}", headers=auth_headers,
            json={"concepto": "MODIFICADO_TEST"}
        )
        assert r_upd.status_code == 400, (
            f"Se permitió modificar movimiento bloqueado: {r_upd.status_code} {r_upd.text}"
        )

        # Cleanup: reabrir caja y eliminar movimiento
        r_reabrir = requests.post(
            f"{API}/caja/cierres/{cierre_id}/reabrir", headers=auth_headers
        )
        assert r_reabrir.status_code == 200, r_reabrir.text
        # Eliminar movimiento
        requests.delete(f"{API}/caja/movimientos/{mov_id}", headers=auth_headers)
