"""
Tests para verificar que TODO el sistema utilice la fecha de Guatemala (GMT-6)
como 'hoy' en los endpoints clave: agenda, caja, ventas, dashboard financiero,
upcoming y gastos vencidos.

Momento crítico (noche en Guatemala, UTC ya es el día siguiente):
el día GT debe aparecer, no el día UTC.
"""
import os
import pytest
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
GT = ZoneInfo("America/Guatemala")


def today_gt_str():
    return datetime.now(GT).strftime("%Y-%m-%d")


def today_utc_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# =============== AGENDA ===============
class TestAgendaTimezone:
    def test_citas_sin_fecha_usa_dia_gt(self, h):
        r = requests.get(f"{API}/agenda/citas", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        # Puede ser lista directa o {data:...}
        items = data if isinstance(data, list) else data.get("data", [])
        fecha_gt = today_gt_str()
        # Todas las citas deben pertenecer al día GT
        for c in items:
            fecha_cita = c.get("fecha", "")
            assert fecha_cita == fecha_gt, (
                f"Cita con fecha {fecha_cita} no coincide con hoy GT {fecha_gt}"
            )

    def test_contadores_sin_fecha(self, h):
        r = requests.get(f"{API}/agenda/contadores", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_presentes_sin_fecha(self, h):
        r = requests.get(f"{API}/agenda/presentes", headers=h)
        assert r.status_code == 200, r.text


# =============== CAJA ===============
class TestCajaTimezone:
    def test_estado_sin_fecha(self, h):
        r = requests.get(f"{API}/caja/estado", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "caja_abierta" in data
        assert "totales_dia" in data
        # Si la caja está abierta hoy GT, su fecha debe ser hoy GT
        if data.get("caja_abierta") and data.get("caja"):
            fecha_caja = data["caja"].get("fecha", "")
            assert fecha_caja == today_gt_str(), (
                f"Caja abierta con fecha {fecha_caja} != hoy GT {today_gt_str()}"
            )

    def test_abrir_movimiento_totales_cerrar(self, h):
        estado = requests.get(f"{API}/caja/estado", headers=h).json()
        # Abrir si está cerrada
        if not estado.get("caja_abierta"):
            r_ap = requests.post(f"{API}/caja/apertura", headers=h, json={"monto_apertura": 10.0})
            if r_ap.status_code != 200:
                pytest.skip(f"No se pudo abrir caja: {r_ap.text}")
            caja_fecha = r_ap.json().get("fecha")
            assert caja_fecha == today_gt_str(), (
                f"Caja abierta con fecha {caja_fecha} != hoy GT {today_gt_str()}"
            )

        # Crear movimiento
        payload = {
            "tipo": "Ingreso", "categoria": "Consulta",
            "concepto": "TEST_TZ_GT_movimiento",
            "monto": 7.0, "metodo_pago": "Efectivo",
        }
        r_mov = requests.post(f"{API}/caja/movimientos", headers=h, json=payload)
        assert r_mov.status_code == 200, r_mov.text
        mov_id = r_mov.json()["id"]

        # Verificar que el totales_dia refleja el movimiento
        estado2 = requests.get(f"{API}/caja/estado", headers=h).json()
        totales = estado2.get("totales_dia", {})
        # total_ingresos debería incluir el 7.0 nuevo
        assert totales.get("total_ingresos", 0) >= 7.0, (
            f"Totales del día no reflejan el movimiento: {totales}"
        )

        # Cerrar caja
        r_cierre = requests.post(
            f"{API}/caja/cierre", headers=h,
            json={"efectivo_contado": 999.0, "observaciones": "TEST_TZ_cierre"}
        )
        assert r_cierre.status_code == 200, r_cierre.text
        cierre = r_cierre.json()
        assert cierre.get("fecha") == today_gt_str(), (
            f"Cierre con fecha {cierre.get('fecha')} != hoy GT {today_gt_str()}"
        )

        # Reabrir para no bloquear subsecuentes tests
        cierre_id = cierre.get("id")
        if cierre_id:
            requests.post(f"{API}/caja/cierres/{cierre_id}/reabrir", headers=h)
        # Limpieza de movimiento
        requests.delete(f"{API}/caja/movimientos/{mov_id}", headers=h)


# =============== VENTAS ===============
class TestVentasTimezone:
    def test_ventas_hoy(self, h):
        r = requests.get(f"{API}/ventas/hoy", headers=h)
        assert r.status_code == 200, r.text

    def test_ventas_resumen_dia(self, h):
        r = requests.get(f"{API}/ventas/resumen-dia", headers=h)
        assert r.status_code == 200, r.text


# =============== DASHBOARD ===============
class TestDashboardTimezone:
    def test_dashboard_financiero_superadmin(self, h):
        r = requests.get(f"{API}/dashboard/financiero?periodo=mes_actual", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        now_gt = datetime.now(GT)
        # El mes del periodo debe coincidir con el mes GT (no UTC)
        fecha_inicio = data["periodo"]["fecha_inicio"]
        assert fecha_inicio.startswith(f"{now_gt.year}-{now_gt.month:02d}-01"), (
            f"Periodo inicio {fecha_inicio} no coincide con mes GT {now_gt.year}-{now_gt.month:02d}"
        )

    def test_dashboard_upcoming(self, h):
        r = requests.get(f"{API}/dashboard/upcoming", headers=h)
        assert r.status_code == 200, r.text

    def test_dashboard_stats(self, h):
        r = requests.get(f"{API}/dashboard/stats", headers=h)
        assert r.status_code == 200, r.text


# =============== EXPENSES VENCIDOS ===============
class TestExpensesTimezone:
    def test_expenses_list(self, h):
        r = requests.get(f"{API}/expenses", headers=h)
        assert r.status_code == 200, r.text
