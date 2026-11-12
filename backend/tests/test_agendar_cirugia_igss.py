# Feature: "Agregar a Agenda" desde Registro de Cirugía IGSS (backend contract the UI relies on)
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
MEDICOS = ['Dr. Cristian Acevedo', 'Dra. Mariamercedes Palma', 'Dr. Manuel de la Cruz', 'Dra. Rocío Muñoz']
PATIENT_ID = '4ceb89de-628f-4aa9-a545-fe6c4f4affc5'


@pytest.fixture(scope='module')
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    tok = r.json().get('access_token') or r.json().get('token')
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope='module')
def created():
    return {"surgeries": [], "citas": []}


@pytest.fixture(scope='module', autouse=True)
def cleanup(client, created):
    yield
    for cid in created["citas"]:
        client.delete(f"{BASE_URL}/api/agenda/citas/{cid}")
    for sid in created["surgeries"]:
        client.delete(f"{BASE_URL}/api/surgeries/{sid}")


def _medicos(client):
    r = client.get(f"{BASE_URL}/api/medicos-agenda")
    assert r.status_code == 200
    return r.json()["data"]


# Medicos fijos existen con nombre exacto y únicos
def test_four_doctors_exist_exact_names(client):
    data = _medicos(client)
    for n in MEDICOS:
        matches = [d for d in data if d["name"] == n]
        assert len(matches) == 1, f"{n}: {len(matches)} matches"


# Paciente IGSS de prueba existe
def test_patient_is_igss(client):
    r = client.get(f"{BASE_URL}/api/patients/{PATIENT_ID}")
    assert r.status_code == 200
    assert (r.json().get('referral_institution') or '').lower() == 'igss'


# Flujo API: crear cirugía IGSS -> crear cita -> GET muestra IGSS + notas
def test_surgery_then_cita_enriched(client, created):
    pr = client.get(f"{BASE_URL}/api/patients/{PATIENT_ID}").json()
    name = pr.get('full_name') or f"{pr.get('first_name','')} {pr.get('last_name','')}".strip()
    payload = {
        "date": "2026-03-17", "time": "07:15", "patient_name": name, "patient_id": PATIENT_ID,
        "procedure": "TEST_Faco API", "surgeon": "TEST_Surg", "eye": "OD", "anesthesia_type": "Local",
        "anesthesiologist": "TEST_Anest", "institution": "IGSS",
        "igss_data": {"unit": "TEST_U", "sps": "1", "affiliation_number": "1", "code": "1", "procedure_cost": 100},
    }
    r = client.post(f"{BASE_URL}/api/surgeries", json=payload)
    assert r.status_code in (200, 201), r.text
    s = r.json()
    created["surgeries"].append(s["id"])
    assert s["patient_id"] == PATIENT_ID and s["time"] == "07:15"

    med = [d for d in _medicos(client) if d["name"] == MEDICOS[0]][0]
    r = client.post(f"{BASE_URL}/api/agenda/citas", json={
        "paciente_id": PATIENT_ID, "paciente_nombre": name, "medico_id": med["id"], "medico_nombre": med["name"],
        "fecha": s["date"], "hora_inicio": s["time"], "tipo_cita": "Cirugía", "notas": f"Procedimiento: {s['procedure']}"})
    assert r.status_code in (200, 201), r.text
    cita = r.json()
    created["citas"].append(cita["id"])

    r = client.get(f"{BASE_URL}/api/agenda/citas", params={"fecha": "2026-03-17", "medico_id": med["id"]})
    assert r.status_code == 200
    items = r.json().get("data") or r.json().get("citas") or []
    found = [c for c in items if c["id"] == cita["id"]]
    assert found, "cita not in list"
    c = found[0]
    assert c["hora_inicio"] == "07:15"
    assert c["notas"] == "Procedimiento: TEST_Faco API"
    print("enriched cita:", {k: c.get(k) for k in c if 'instit' in k.lower()})
    assert any('igss' in str(v).lower() for k, v in c.items() if 'instit' in k.lower())
