"""Tests for Caja module (Clinica área: Caja Diaria, CxC, Cierres Financieros)"""
import os
import pytest
import requests
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://novavision-finanzas.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


# ==================== CAJA ESTADO / APERTURA / MOVIMIENTOS ====================

class TestCajaEstado:
    def test_caja_estado(self, client):
        r = client.get(f"{API}/caja/estado")
        assert r.status_code == 200
        data = r.json()
        assert "caja_abierta" in data
        assert "totales_dia" in data
        assert "saldo_efectivo_vivo" in data

    def test_caja_movimientos_list(self, client):
        r = client.get(f"{API}/caja/movimientos")
        assert r.status_code == 200
        data = r.json()
        assert "data" in data and isinstance(data["data"], list)
        # ensure no _id leak
        for m in data["data"]:
            assert "_id" not in m
            assert m.get("origen") == "clinica"


class TestCajaMovimientos:
    created_id = None

    def test_create_ingreso(self, client):
        # ensure caja abierta first
        estado = client.get(f"{API}/caja/estado").json()
        if not estado.get("caja_abierta"):
            r = client.post(f"{API}/caja/apertura", json={"monto_apertura": 100})
            assert r.status_code == 200

        payload = {
            "tipo": "Ingreso",
            "categoria": "Consulta",
            "concepto": "TEST_consulta_general",
            "monto": 250.00,
            "metodo_pago": "Efectivo",
            "referencia": "TEST-001"
        }
        r = client.post(f"{API}/caja/movimientos", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["tipo"] == "Ingreso"
        assert data["monto"] == 250.00
        assert data["origen"] == "clinica"
        assert "id" in data
        TestCajaMovimientos.created_id = data["id"]

        # verify persistence
        list_r = client.get(f"{API}/caja/movimientos")
        ids = [m["id"] for m in list_r.json()["data"]]
        assert data["id"] in ids

    def test_totales_reflected(self, client):
        estado = client.get(f"{API}/caja/estado").json()
        totales = estado.get("totales_dia", {})
        # Should have total_ingresos > 0 after creating ingreso
        assert totales.get("total_ingresos", 0) >= 250.00

    def test_create_egreso(self, client):
        payload = {
            "tipo": "Egreso",
            "categoria": "Gasto menor",
            "concepto": "TEST_papeleria",
            "monto": 50.00,
            "metodo_pago": "Efectivo"
        }
        r = client.post(f"{API}/caja/movimientos", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["tipo"] == "Egreso"
        assert data["monto"] == 50.00

    def test_update_movimiento(self, client):
        assert TestCajaMovimientos.created_id
        r = client.put(f"{API}/caja/movimientos/{TestCajaMovimientos.created_id}",
                       json={"concepto": "TEST_consulta_editada", "monto": 275})
        assert r.status_code == 200, r.text
        assert r.json()["concepto"] == "TEST_consulta_editada"
        assert r.json()["monto"] == 275


# ==================== PAGADORES ====================

class TestPagadores:
    def test_list_pagadores(self, client):
        r = client.get(f"{API}/catalogos/pagadores")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        nombres = [p["nombre"] for p in data]
        # Should have some seed data as per context
        assert len(data) > 0

    def test_create_pagador(self, client):
        payload = {"nombre": f"TEST_Pagador_{datetime.now().strftime('%H%M%S')}"}
        r = client.post(f"{API}/catalogos/pagadores", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["nombre"] == payload["nombre"]
        assert data["activo"] is True
        # cleanup
        client.delete(f"{API}/catalogos/pagadores/{data['id']}")


# ==================== CUENTAS POR COBRAR ====================

class TestCxC:
    cuenta_id = None
    pagador_id = None

    def test_setup(self, client):
        # Get an active pagador
        pagadores = client.get(f"{API}/catalogos/pagadores").json()
        activos = [p for p in pagadores if p.get("activo")]
        assert len(activos) > 0
        TestCxC.pagador_id = activos[0]["id"]

    def test_create_cxc(self, client):
        payload = {
            "paciente_id": "test-pac-1",
            "paciente_nombre": "TEST Paciente Uno",
            "tipo_pagador_id": TestCxC.pagador_id,
            "tipo_pagador_nombre": "TEST",
            "concepto": "TEST_consulta_cxc",
            "monto_total": 1000.00,
        }
        r = client.post(f"{API}/cxc", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["monto_total"] == 1000.00
        assert data["saldo_pendiente"] == 1000.00
        assert data["estado"] == "Pendiente"
        assert data["origen"] == "clinica"
        TestCxC.cuenta_id = data["id"]

    def test_list_cxc(self, client):
        r = client.get(f"{API}/cxc")
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()["data"]]
        assert TestCxC.cuenta_id in ids

    def test_resumen_cxc(self, client):
        r = client.get(f"{API}/cxc/resumen")
        assert r.status_code == 200
        d = r.json()
        assert "total_emitido" in d
        assert "saldo_pendiente" in d

    def test_registrar_abono(self, client):
        # NOTE: Backend endpoint is /abono (singular). Frontend calls /abonos (plural) which is a bug.
        r = client.post(f"{API}/cxc/{TestCxC.cuenta_id}/abono", json={
            "monto": 300,
            "metodo_pago": "Efectivo",
            "referencia": "TEST-abono",
            "registrar_en_caja": False
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["monto_pagado"] == 300
        assert data["saldo_pendiente"] == 700
        assert data["estado"] == "Parcial"

    def test_abono_plural_endpoint_missing(self, client):
        """Confirms the /abonos (plural) frontend calls fails"""
        r = client.post(f"{API}/cxc/{TestCxC.cuenta_id}/abonos", json={
            "monto": 10, "metodo_pago": "Efectivo", "registrar_en_caja": False
        })
        # This should be a 404 or 405 if the plural version doesn't exist
        assert r.status_code in (404, 405, 422), f"Expected mismatch but got {r.status_code}"


# ==================== CIERRES FINANCIEROS ====================

class TestCierresFinancieros:
    def test_list_cierres_financieros(self, client):
        r = client.get(f"{API}/cierres-financieros")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_create_cierre_mensual(self, client):
        now = datetime.now()
        payload = {
            "tipo": "Mensual",
            "mes": now.month,
            "anio": now.year,
            "observaciones": "TEST_cierre_mensual"
        }
        r = client.post(f"{API}/cierres-financieros", json=payload)
        # Might already exist -> could be 400
        assert r.status_code in (200, 400), r.text
        if r.status_code == 200:
            data = r.json()
            assert data["tipo"] == "Mensual"
            assert data["origen"] == "clinica"
            assert "ingresos_caja" in data
            assert "egresos_caja" in data
            assert "cxc_por_tipo" in data
            # cleanup
            client.delete(f"{API}/cierres-financieros/{data['id']}")


# ==================== HISTORIAL CIERRES DIARIOS ====================

class TestCierresDiarios:
    def test_list_historial(self, client):
        r = client.get(f"{API}/caja/cierres?limit=10")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
