# Tests para Fase 2: Mi Agenda Semanal del médico
# Endpoints: GET /api/agenda/mi-dia, GET /api/agenda/mi-semana
import os
import time
import pytest
import requests
from datetime import datetime, timedelta

def _load_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        v = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL missing"
    return v.rstrip("/")

BASE_URL = _load_url()
API = f"{BASE_URL}/api"

MEDICO_ID = "a8bb541a-7fcb-49ab-bd20-32788f57acb5"  # Dr. Carlos Méndez
MEDICO_NOMBRE = "Dr. Carlos Méndez"
PACIENTE_ID = "93d83ba3-b447-4950-8a97-1e3df0a5a165"
PACIENTE_NOMBRE = "Carlos Mendoza Flores"


def _login(username, password):
    r = requests.post(f"{API}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"login {username} fail: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _next_monday_str():
    today = datetime.utcnow().date()
    # Encontrar próximo lunes al menos 7 días adelante para no chocar con existentes
    days_ahead = (0 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    monday = today + timedelta(days=days_ahead + 7)  # Lunes de la próxima próxima semana
    return monday.strftime("%Y-%m-%d")


@pytest.fixture(scope="module")
def admin_token():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def medico_token():
    return _login("medico_test", "medico2024")


@pytest.fixture(scope="module")
def seed_citas(admin_token):
    """Siembra 3 citas en LUNES 08:30/09:30/10:30 y limpia al terminar"""
    monday = _next_monday_str()
    created = []
    for hora in ["08:30", "09:30", "10:30"]:
        payload = {
            "paciente_id": PACIENTE_ID,
            "paciente_nombre": PACIENTE_NOMBRE,
            "medico_id": MEDICO_ID,
            "medico_nombre": MEDICO_NOMBRE,
            "fecha": monday,
            "hora_inicio": hora,
            "tipo_cita": "primera_vez",
            "duracion_minutos": 30,
        }
        r = requests.post(f"{API}/agenda/citas", json=payload, headers=_h(admin_token))
        assert r.status_code == 200, f"seed cita {hora}: {r.status_code} {r.text}"
        created.append(r.json()["id"])

    yield {"lunes": monday, "ids": created}

    # Cleanup: cancelar
    for cid in created:
        requests.patch(f"{API}/agenda/citas/{cid}/estado",
                       json={"estado": "Cancelada"}, headers=_h(admin_token))


# ---- Backend tests ----

class TestMiSemana:
    def test_mi_semana_devuelve_citas_del_rango(self, medico_token, seed_citas):
        lunes = seed_citas["lunes"]
        domingo = (datetime.strptime(lunes, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")

        r = requests.get(f"{API}/agenda/mi-semana",
                         params={"desde": lunes, "hasta": domingo},
                         headers=_h(medico_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["medico_nombre"] == MEDICO_NOMBRE
        assert data["medico_id"] == MEDICO_ID
        assert data["desde"] == lunes
        assert data["hasta"] == domingo
        assert data["total"] >= 3
        # Todas las citas del rango deben pertenecer al médico
        for c in data["citas"]:
            assert c["medico_id"] == MEDICO_ID or c.get("asignado_a_medico_id") == MEDICO_ID
            assert c["estado"] != "Cancelada"
            assert lunes <= c["fecha"] <= domingo

    def test_mi_semana_excluye_canceladas(self, medico_token, admin_token, seed_citas):
        lunes = seed_citas["lunes"]
        domingo = (datetime.strptime(lunes, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
        # Cancelar la primera
        cid = seed_citas["ids"][0]
        requests.patch(f"{API}/agenda/citas/{cid}/estado",
                       json={"estado": "Cancelada"}, headers=_h(admin_token))
        time.sleep(0.3)
        r = requests.get(f"{API}/agenda/mi-semana",
                         params={"desde": lunes, "hasta": domingo},
                         headers=_h(medico_token))
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()["citas"]]
        assert cid not in ids

    def test_mi_semana_403_si_no_vinculado(self, admin_token):
        # Crear usuario médico sin ficha
        ts = int(time.time())
        username = f"TEST_med_sin_vinc_{ts}"
        payload = {"username": username, "password": "test12345",
                   "name": "Médico Sin Vínculo", "role": "medico", "email": f"{username}@test.com"}
        r = requests.post(f"{API}/users", json=payload, headers=_h(admin_token))
        assert r.status_code in (200, 201), r.text
        uid = r.json().get("id")
        try:
            tok = _login(username, "test12345")
            lunes = _next_monday_str()
            domingo = (datetime.strptime(lunes, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
            r = requests.get(f"{API}/agenda/mi-semana",
                             params={"desde": lunes, "hasta": domingo}, headers=_h(tok))
            assert r.status_code == 403
            assert "vinculado" in r.json().get("detail", "").lower()
        finally:
            if uid:
                requests.delete(f"{API}/users/{uid}", headers=_h(admin_token))


class TestMiDia:
    def test_mi_dia_respeta_fecha(self, medico_token, seed_citas):
        lunes = seed_citas["lunes"]
        r = requests.get(f"{API}/agenda/mi-dia", params={"fecha": lunes}, headers=_h(medico_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["fecha"] == lunes
        assert data["medico_id"] == MEDICO_ID
        assert data["medico_nombre"] == MEDICO_NOMBRE
        assert data["contadores"]["total"] >= 2  # al menos 2 (una fue cancelada)
        for c in data["citas_del_dia"]:
            assert c["fecha"] == lunes
            assert c["estado"] != "Cancelada"


class TestRegresionAdmin:
    def test_mi_semana_admin_sin_vinculo_ok(self, admin_token, seed_citas):
        lunes = seed_citas["lunes"]
        domingo = (datetime.strptime(lunes, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
        r = requests.get(f"{API}/agenda/mi-semana",
                         params={"desde": lunes, "hasta": domingo}, headers=_h(admin_token))
        assert r.status_code == 200
        assert r.json()["total"] >= 2
