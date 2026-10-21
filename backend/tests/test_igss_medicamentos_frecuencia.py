# IGSS medicamentos with frecuencia: create/get/put round-trip + legacy string compatibility
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')


def _login(u, p):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
    return r


@pytest.fixture(scope="module")
def sa():
    r = _login("superadmin", "nova2024")
    if r.status_code != 200:
        pytest.skip("superadmin login failed")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


@pytest.fixture(scope="module")
def patient_id(sa):
    r = sa.get(f"{BASE_URL}/api/patients", params={"limit": 5})
    assert r.status_code == 200
    d = r.json()
    items = d.get("data", d) if isinstance(d, dict) else d
    assert items
    return items[0]["id"]


@pytest.fixture(scope="module")
def created_ids():
    ids = []
    yield ids
    db = MongoClient(MONGO_URL)[DB_NAME]
    db.evaluaciones_oftalmologicas.delete_many({"id": {"$in": ids}})


def test_igss_admin_login():
    r = _login("igss.admin", "IgssAdmin2024$")
    assert r.status_code == 200
    assert r.json().get("access_token")


def test_create_with_frecuencia_and_get(sa, patient_id, created_ids):
    payload = {"paciente_id": patient_id, "motivo_consulta": "TEST_igss_freq",
               "igss_med_proc": {"medicamentos": [
                   {"nombre": "TEST_Timolol 0.5%", "frecuencia": "1 gota cada 8 horas"},
                   "TEST_Legacy string med",
                   {"nombre": "  ", "frecuencia": "x"}],
                   "estudios_procedimientos": ["TEST_OCT"]}}
    r = sa.post(f"{BASE_URL}/api/evaluaciones", json=payload)
    assert r.status_code == 200, r.text
    ev = r.json()
    created_ids.append(ev["id"])
    meds = ev["igss_med_proc"]["medicamentos"]
    assert meds == [{"nombre": "TEST_Timolol 0.5%", "frecuencia": "1 gota cada 8 horas"},
                    {"nombre": "TEST_Legacy string med", "frecuencia": ""}]
    g = sa.get(f"{BASE_URL}/api/evaluaciones/{ev['id']}")
    assert g.status_code == 200
    assert g.json()["igss_med_proc"]["medicamentos"][0]["frecuencia"] == "1 gota cada 8 horas"


def test_put_updates_frecuencia(sa, created_ids):
    eid = created_ids[0]
    r = sa.put(f"{BASE_URL}/api/evaluaciones/{eid}", json={"igss_med_proc": {
        "medicamentos": [{"nombre": "TEST_Latanoprost", "frecuencia": "1 gota por la noche"}],
        "estudios_procedimientos": []}})
    assert r.status_code == 200, r.text
    g = sa.get(f"{BASE_URL}/api/evaluaciones/{eid}").json()
    assert g["igss_med_proc"]["medicamentos"] == [{"nombre": "TEST_Latanoprost", "frecuencia": "1 gota por la noche"}]


def test_legacy_string_in_db_loads(sa, patient_id, created_ids):
    db = MongoClient(MONGO_URL)[DB_NAME]
    eid = str(uuid.uuid4())
    db.evaluaciones_oftalmologicas.insert_one({
        "id": eid, "paciente_id": patient_id, "fecha": "2026-01-10", "motivo_consulta": "TEST_legacy",
        "fecha_creacion": "2026-01-10T10:00:00+00:00", "sellado": False,
        "igss_med_proc": {"medicamentos": ["TEST_Old A", "TEST_Old B"], "estudios_procedimientos": []}})
    created_ids.append(eid)
    g = sa.get(f"{BASE_URL}/api/evaluaciones/{eid}")
    assert g.status_code == 200, g.text
    assert g.json()["igss_med_proc"]["medicamentos"] == [
        {"nombre": "TEST_Old A", "frecuencia": ""}, {"nombre": "TEST_Old B", "frecuencia": ""}]
    lst = sa.get(f"{BASE_URL}/api/evaluaciones", params={"paciente_id": patient_id, "limit": 100})
    assert lst.status_code == 200, lst.text


def test_autoguardar_persists_igss(sa, created_ids):
    """Autosave (PATCH) - check whether igss_med_proc is persisted"""
    eid = created_ids[0]
    r = sa.patch(f"{BASE_URL}/api/evaluaciones/{eid}/autoguardar", json={"igss_med_proc": {
        "medicamentos": [{"nombre": "TEST_Autosave med", "frecuencia": "c/12h"}], "estudios_procedimientos": []}})
    assert r.status_code == 200
    g = sa.get(f"{BASE_URL}/api/evaluaciones/{eid}").json()
    assert g["igss_med_proc"]["medicamentos"][0]["nombre"] == "TEST_Autosave med"
