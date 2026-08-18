"""Tests para módulo Cuentas por Cobrar (CxC) Óptica y Clínica."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://novavision-finanzas.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- Responsables ----------
class TestResponsables:
    responsable_id = None

    def test_listar_responsables(self, headers):
        r = requests.get(f"{API}/cuentas-cobrar/responsables", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "data" in body and "total" in body
        assert isinstance(body["data"], list)

    def test_crear_responsable(self, headers):
        payload = {
            "nombre": "TEST_Responsable QA",
            "tipo": "medico",
            "nit": "12345678",
            "telefono": "5555-5555",
            "plazo_dias": 30
        }
        r = requests.post(f"{API}/cuentas-cobrar/responsables", headers=headers, json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["nombre"] == payload["nombre"]
        assert data["tipo"] == "medico"
        assert data["is_active"] is True
        assert "id" in data
        TestResponsables.responsable_id = data["id"]

        # Verify GET
        r2 = requests.get(f"{API}/cuentas-cobrar/responsables", headers=headers)
        ids = [x["id"] for x in r2.json()["data"]]
        assert data["id"] in ids

    def test_actualizar_responsable(self, headers):
        assert TestResponsables.responsable_id
        r = requests.put(
            f"{API}/cuentas-cobrar/responsables/{TestResponsables.responsable_id}",
            headers=headers,
            json={"telefono": "9999-0000", "nombre": "TEST_Responsable QA Updated"}
        )
        assert r.status_code == 200, r.text
        assert r.json().get("success") is True

    def test_tipos_responsable(self, headers):
        r = requests.get(f"{API}/cuentas-cobrar/tipos-responsable/lista", headers=headers)
        assert r.status_code == 200
        tipos = r.json().get("tipos", [])
        assert len(tipos) >= 5
        assert any(t["value"] == "igss" for t in tipos)

    def test_desactivar_responsable(self, headers):
        assert TestResponsables.responsable_id
        r = requests.delete(
            f"{API}/cuentas-cobrar/responsables/{TestResponsables.responsable_id}",
            headers=headers
        )
        assert r.status_code == 200, r.text
        # Verify no longer in active list
        r2 = requests.get(f"{API}/cuentas-cobrar/responsables?is_active=true", headers=headers)
        ids = [x["id"] for x in r2.json()["data"]]
        assert TestResponsables.responsable_id not in ids


# ---------- CxC Óptica ----------
class TestCxCOptica:
    cuenta_id = None

    def test_listar_optica(self, headers):
        r = requests.get(f"{API}/cuentas-cobrar/optica", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "data" in body and "total" in body
        assert isinstance(body["data"], list)

    def test_resumen_optica(self, headers):
        r = requests.get(f"{API}/cuentas-cobrar/optica/resumen", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ["total_emitido", "total_cobrado", "saldo_pendiente", "cantidad_cuentas", "por_estado"]:
            assert k in body

    def test_crear_optica_y_abono(self, headers):
        payload = {
            "venta_id": "TEST-VENTA-001",
            "paciente_id": "TEST-PAC-001",
            "paciente_nombre": "TEST_Paciente Optica",
            "monto_total": 500.0,
            "monto_pagado": 100.0,
            "concepto": "TEST_Lentes",
            "notas": "test"
        }
        r = requests.post(f"{API}/cuentas-cobrar/optica", headers=headers, json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["origen"] == "optica"
        assert data["monto_total"] == 500.0
        assert data["saldo_pendiente"] == 400.0
        assert data["estado"] == "Parcial"
        TestCxCOptica.cuenta_id = data["id"]

        # Abono
        r2 = requests.post(
            f"{API}/cuentas-cobrar/{data['id']}/abono",
            headers=headers,
            json={"monto": 400.0, "metodo_pago": "Efectivo"}
        )
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["nuevo_saldo"] == 0
        assert body["nuevo_estado"] == "Pagado"

        # Abono excede saldo
        r3 = requests.post(
            f"{API}/cuentas-cobrar/{data['id']}/abono",
            headers=headers,
            json={"monto": 10.0}
        )
        assert r3.status_code == 400


# ---------- CxC Clínica ----------
class TestCxCClinica:
    def test_listar_clinica(self, headers):
        r = requests.get(f"{API}/cuentas-cobrar/clinica", headers=headers)
        assert r.status_code == 200, r.text
        assert "data" in r.json()

    def test_resumen_clinica(self, headers):
        r = requests.get(f"{API}/cuentas-cobrar/clinica/resumen", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ["total_emitido", "total_cobrado", "saldo_pendiente", "por_tipo", "por_estado"]:
            assert k in body

    def test_crear_clinica_con_responsable(self, headers):
        # Crear responsable
        resp = requests.post(f"{API}/cuentas-cobrar/responsables", headers=headers, json={
            "nombre": "TEST_Institucion QA",
            "tipo": "institucion"
        }).json()

        payload = {
            "responsable_id": resp["id"],
            "monto_total": 1000.0,
            "concepto": "TEST_Servicio médico",
            "paciente_nombre": "TEST_Paciente Clinica"
        }
        r = requests.post(f"{API}/cuentas-cobrar/clinica", headers=headers, json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["origen"] == "clinica"
        assert data["responsable_id"] == resp["id"]
        assert data["responsable_nombre"] == "TEST_Institucion QA"
        assert data["tipo_responsable"] == "institucion"
        assert data["estado"] == "Pendiente"

        # Filtrar por responsable
        r2 = requests.get(
            f"{API}/cuentas-cobrar/clinica?responsable_id={resp['id']}",
            headers=headers
        )
        assert r2.status_code == 200
        assert r2.json()["total"] >= 1

        # Cleanup soft
        requests.delete(f"{API}/cuentas-cobrar/responsables/{resp['id']}", headers=headers)
