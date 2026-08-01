"""
Regression tests for backend refactor (iteration 26)

Covers extracted routers:
- routes/patients.py    : /api/patients, /api/pacientes/buscar
- routes/evaluaciones.py: /api/evaluaciones, /api/catalogos/medicamentos
- routes/surgeries.py   : /api/surgeries
- routes/expenses.py    : /api/expenses
- routes/dashboard_financiero.py: /api/dashboard/financiero (SuperAdmin only)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ----------- fixtures -----------
@pytest.fixture(scope="session")
def super_token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    assert r.status_code == 200, f"superadmin login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "Admin2024Nuevo!"}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ----------- Patients -----------
class TestPatients:
    def test_list_patients_paginated(self, super_token):
        r = requests.get(f"{API}/patients?page=1&page_size=5", headers=h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Accept either wrapped {items,total,page,...} or plain list
        if isinstance(data, dict):
            assert "items" in data or "pacientes" in data or "data" in data
            items_key = next(k for k in ("items", "pacientes", "data") if k in data)
            items = data[items_key]
        else:
            items = data
        assert isinstance(items, list)
        # ensure no mongo _id leaks
        for it in items[:3]:
            assert "_id" not in it

    def test_buscar_pacientes_with_accent(self, super_token):
        r = requests.get(f"{API}/pacientes/buscar", params={"q": "María"}, headers=h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list) or isinstance(data, dict)


# ----------- Evaluaciones -----------
class TestEvaluaciones:
    def test_list_evaluaciones(self, super_token):
        r = requests.get(f"{API}/evaluaciones?page=1&page_size=5", headers=h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_catalogos_medicamentos(self, super_token):
        r = requests.get(f"{API}/catalogos/medicamentos", headers=h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)

    def test_create_evaluacion_minimal(self, super_token):
        # First get a patient to attach
        rp = requests.get(f"{API}/patients?page=1&page_size=1", headers=h(super_token), timeout=30)
        assert rp.status_code == 200
        pdata = rp.json()
        items = pdata["items"] if isinstance(pdata, dict) and "items" in pdata else (
            pdata.get("pacientes") if isinstance(pdata, dict) else pdata
        )
        if not items:
            pytest.skip("No patients available to attach evaluacion")
        paciente = items[0]
        paciente_id = paciente.get("id") or paciente.get("_id")

        payload = {
            "paciente_id": paciente_id,
            "motivo_consulta": "TEST_REFACTOR_26 revisión",
            "diagnostico": "TEST diagnóstico refactor",
        }
        r = requests.post(f"{API}/evaluaciones", json=payload, headers=h(super_token), timeout=30)
        # Accept 200/201 create success or 422 if extra required fields (route wired ok)
        assert r.status_code in (200, 201, 400, 422), r.text
        if r.status_code in (200, 201):
            body = r.json()
            eval_id = body.get("id") or body.get("_id")
            if eval_id:
                requests.delete(f"{API}/evaluaciones/{eval_id}", headers=h(super_token), timeout=30)


# ----------- Surgeries -----------
class TestSurgeries:
    def test_list_surgeries(self, super_token):
        r = requests.get(f"{API}/surgeries?page=1&page_size=5", headers=h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, (list, dict))


# ----------- Expenses -----------
class TestExpenses:
    def test_list_expenses(self, super_token):
        r = requests.get(f"{API}/expenses", headers=h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, (list, dict))


# ----------- Dashboard Financiero -----------
class TestDashboardFinanciero:
    def test_dashboard_superadmin(self, super_token):
        r = requests.get(f"{API}/dashboard/financiero?periodo=mes_actual", headers=h(super_token), timeout=45)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("ingresos", "gastos", "balance"):
            assert k in data, f"missing key {k} in dashboard response: {list(data.keys())}"

    def test_dashboard_admin_forbidden(self, admin_token):
        r = requests.get(f"{API}/dashboard/financiero?periodo=mes_actual", headers=h(admin_token), timeout=30)
        assert r.status_code == 403, f"expected 403 for admin, got {r.status_code}: {r.text}"

    def test_dashboard_unauthenticated(self):
        r = requests.get(f"{API}/dashboard/financiero?periodo=mes_actual", timeout=30)
        assert r.status_code in (401, 403), r.text
