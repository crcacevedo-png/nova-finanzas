"""Test evaluaciones role-based write permissions for user 'usuario' vs admin/superadmin."""
import os
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://novavision-finanzas.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


def login(username, password):
    r = requests.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login {username} failed: {r.status_code} {r.text}"
    data = r.json()
    return data.get("access_token") or data.get("token"), data


def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def tokens():
    return {
        "usuario": login("usuario", "user2024")[0],
        "admin": login("admin", "Admin2024Nuevo!")[0],
        "superadmin": login("superadmin", "nova2024")[0],
    }


@pytest.fixture(scope="module")
def paciente_id(tokens):
    r = requests.get(f"{API}/patients", headers=headers(tokens["admin"]), timeout=30)
    assert r.status_code == 200, f"GET /api/patients failed: {r.status_code} {r.text}"
    data = r.json()
    items = data if isinstance(data, list) else data.get("items") or data.get("patients") or data.get("pacientes") or data.get("data") or []
    assert items, "No hay pacientes"
    pid = items[0].get("id") or items[0].get("_id") or items[0].get("paciente_id")
    return pid


def _payload(paciente_id):
    return {
        "paciente_id": paciente_id,
        "motivo_consulta": "TEST_permisos evaluacion",
        "diagnosticos": [],
    }


class TestUsuarioNoPuedeEscribir:
    def test_usuario_POST_evaluacion_403(self, tokens, paciente_id):
        r = requests.post(f"{API}/evaluaciones", headers=headers(tokens["usuario"]), json=_payload(paciente_id), timeout=30)
        print(f"USUARIO POST => {r.status_code} : {r.text[:300]}")
        assert r.status_code == 403, f"Expected 403 for usuario, got {r.status_code}: {r.text}"

    def test_usuario_PUT_evaluacion_403(self, tokens, paciente_id):
        # First create with admin
        cr = requests.post(f"{API}/evaluaciones", headers=headers(tokens["admin"]), json=_payload(paciente_id), timeout=30)
        assert cr.status_code in (200, 201), f"admin create failed: {cr.status_code} {cr.text}"
        eid = cr.json().get("id") or cr.json().get("_id") or cr.json().get("evaluacion_id")
        assert eid, f"no id in {cr.json()}"

        try:
            r = requests.put(f"{API}/evaluaciones/{eid}", headers=headers(tokens["usuario"]),
                             json={"motivo_consulta": "TEST_edit intento usuario"}, timeout=30)
            print(f"USUARIO PUT => {r.status_code} : {r.text[:300]}")
            assert r.status_code == 403
        finally:
            requests.delete(f"{API}/evaluaciones/{eid}", headers=headers(tokens["superadmin"]), timeout=30)


class TestAdminYSuperadminSiPueden:
    def test_admin_POST_evaluacion_ok(self, tokens, paciente_id):
        r = requests.post(f"{API}/evaluaciones", headers=headers(tokens["admin"]), json=_payload(paciente_id), timeout=30)
        print(f"ADMIN POST => {r.status_code} : {r.text[:200]}")
        assert r.status_code in (200, 201)
        eid = r.json().get("id") or r.json().get("_id")
        if eid:
            requests.delete(f"{API}/evaluaciones/{eid}", headers=headers(tokens["superadmin"]), timeout=30)

    def test_superadmin_POST_evaluacion_ok(self, tokens, paciente_id):
        r = requests.post(f"{API}/evaluaciones", headers=headers(tokens["superadmin"]), json=_payload(paciente_id), timeout=30)
        print(f"SUPERADMIN POST => {r.status_code} : {r.text[:200]}")
        assert r.status_code in (200, 201)
        eid = r.json().get("id") or r.json().get("_id")
        if eid:
            requests.delete(f"{API}/evaluaciones/{eid}", headers=headers(tokens["superadmin"]), timeout=30)
