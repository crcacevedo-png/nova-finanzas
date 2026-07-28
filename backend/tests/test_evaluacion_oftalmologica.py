"""Tests for the Ophthalmological Evaluation module and its catalogs."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _login(username, password):
    r = requests.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {username}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def superadmin_token():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin", "Admin2024Nuevo!")


@pytest.fixture(scope="module")
def user_token():
    return _login("usuario", "user2024")


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# ==================== CATALOGOS ====================

class TestCatalogos:
    def test_medicamentos_returns_list(self, superadmin_token):
        r = requests.get(f"{API}/catalogos/medicamentos", headers=_h(superadmin_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected preloaded medicamentos"
        # Sorted by usos desc
        usos = [i.get("usos", 0) for i in data]
        assert usos == sorted(usos, reverse=True), f"Not sorted by usos desc: {usos}"
        # No _id
        for item in data:
            assert "_id" not in item
            assert "nombre" in item

    def test_medicamentos_search(self, superadmin_token):
        r = requests.get(f"{API}/catalogos/medicamentos?search=a", headers=_h(superadmin_token), timeout=30)
        assert r.status_code == 200
        for item in r.json():
            assert "a" in item["nombre"].lower()

    def test_estudios_returns_list(self, superadmin_token):
        r = requests.get(f"{API}/catalogos/estudios", headers=_h(superadmin_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0

    def test_diagnosticos_returns_list(self, superadmin_token):
        r = requests.get(f"{API}/catalogos/diagnosticos", headers=_h(superadmin_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0

    def test_catalogos_requires_auth(self):
        r = requests.get(f"{API}/catalogos/medicamentos", timeout=30)
        assert r.status_code in (401, 403)


# ==================== EVALUACIONES ====================

class TestEvaluacionesList:
    def test_list_evaluaciones(self, superadmin_token):
        r = requests.get(f"{API}/evaluaciones", headers=_h(superadmin_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "data" in data and "total" in data
        assert isinstance(data["data"], list)
        assert data["total"] >= 2, f"Expected >=2 sample evaluaciones, got {data['total']}"
        for ev in data["data"]:
            assert "_id" not in ev
            assert "id" in ev
            assert "paciente_id" in ev

    def test_list_as_user_readonly(self, user_token):
        # Usuario should be able to view
        r = requests.get(f"{API}/evaluaciones", headers=_h(user_token), timeout=30)
        assert r.status_code == 200


class TestEvaluacionSealed:
    """Test that a sealed evaluation returns 423 on updates."""

    def _get_sealed_id(self, token):
        r = requests.get(f"{API}/evaluaciones?limit=100", headers=_h(token), timeout=30)
        assert r.status_code == 200
        for ev in r.json()["data"]:
            if ev.get("sellado"):
                return ev["id"]
        return None

    def _get_unsealed_id(self, token):
        r = requests.get(f"{API}/evaluaciones?limit=100", headers=_h(token), timeout=30)
        assert r.status_code == 200
        for ev in r.json()["data"]:
            if not ev.get("sellado"):
                return ev["id"]
        return None

    def test_sample_sealed_exists(self, superadmin_token):
        sid = self._get_sealed_id(superadmin_token)
        assert sid is not None, "Expected at least 1 sealed sample evaluation"

    def test_put_on_sealed_returns_423(self, admin_token):
        sid = self._get_sealed_id(admin_token)
        if not sid:
            pytest.skip("No sealed evaluation")
        r = requests.put(
            f"{API}/evaluaciones/{sid}",
            headers=_h(admin_token),
            json={"plan": "intento de modificacion"},
            timeout=30,
        )
        assert r.status_code == 423, f"Expected 423 got {r.status_code}: {r.text}"

    def test_autoguardar_on_sealed_returns_423(self, admin_token):
        sid = self._get_sealed_id(admin_token)
        if not sid:
            pytest.skip("No sealed evaluation")
        r = requests.patch(
            f"{API}/evaluaciones/{sid}/autoguardar",
            headers=_h(admin_token),
            json={"plan": "test"},
            timeout=30,
        )
        assert r.status_code == 423

    def test_user_cannot_update(self, user_token, admin_token):
        eid = self._get_unsealed_id(admin_token)
        if not eid:
            pytest.skip("No unsealed evaluation")
        r = requests.put(
            f"{API}/evaluaciones/{eid}",
            headers=_h(user_token),
            json={"plan": "no debe permitir"},
            timeout=30,
        )
        assert r.status_code == 403


class TestEvaluacionCrud:
    """CRUD test with cleanup."""

    def test_create_update_get_delete(self, admin_token):
        # Get a patient id
        rp = requests.get(f"{API}/patients?limit=1", headers=_h(admin_token), timeout=30)
        assert rp.status_code == 200
        patients = rp.json()
        patients_data = patients if isinstance(patients, list) else patients.get("data", patients.get("patients", []))
        if not patients_data:
            pytest.skip("No patients available")
        paciente_id = patients_data[0]["id"]

        # CREATE
        payload = {
            "paciente_id": paciente_id,
            "motivo_consulta": "TEST_motivo",
            "plan": "TEST_plan_inicial",
        }
        rc = requests.post(f"{API}/evaluaciones", headers=_h(admin_token), json=payload, timeout=30)
        assert rc.status_code in (200, 201), rc.text
        created = rc.json()
        assert created["motivo_consulta"] == "TEST_motivo"
        assert created["sellado"] is False
        eid = created["id"]

        try:
            # GET
            rg = requests.get(f"{API}/evaluaciones/{eid}", headers=_h(admin_token), timeout=30)
            assert rg.status_code == 200
            assert rg.json()["motivo_consulta"] == "TEST_motivo"

            # UPDATE
            ru = requests.put(
                f"{API}/evaluaciones/{eid}",
                headers=_h(admin_token),
                json={"plan": "TEST_plan_actualizado"},
                timeout=30,
            )
            assert ru.status_code == 200, ru.text
            assert ru.json()["plan"] == "TEST_plan_actualizado"

            # AUTOGUARDAR
            ra = requests.patch(
                f"{API}/evaluaciones/{eid}/autoguardar",
                headers=_h(admin_token),
                json={"motivo_consulta": "TEST_autoguardado"},
                timeout=30,
            )
            assert ra.status_code == 200
            assert ra.json()["motivo_consulta"] == "TEST_autoguardado"
        finally:
            # Cleanup
            requests.delete(f"{API}/evaluaciones/{eid}", headers=_h(admin_token), timeout=30)
