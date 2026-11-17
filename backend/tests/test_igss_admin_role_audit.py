# Audit of role administrador_igss (igss.admin): permissions, menus, endpoint access boundaries
import os
import uuid
import pytest
import requests
from usuarios_prueba import cred, par  # usuarios sembrados solo para pruebas

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
USER, PWD = par("igss")

RESULTS = {}


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": USER, "password": PWD})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    s.login_data = data
    return s


# --- Login / identity
def test_login_and_me(client):
    d = client.login_data
    user = d.get("user", {})
    print("LOGIN user:", {k: user.get(k) for k in ("username", "role", "must_change_password")})
    print("LOGIN permissions true:", sorted([k for k, v in (user.get("permissions") or {}).items() if v]))
    assert user.get("role") == "administrador_igss"


# --- Menus
def test_my_menus(client):
    r = client.get(f"{BASE_URL}/api/menu-config/my-menus")
    print("MY MENUS", r.status_code, r.text[:800])
    assert r.status_code == 200


# --- Endpoints that SHOULD work
ALLOWED = [
    "/api/patients?page=1&limit=5",
    "/api/igss-units",
    "/api/igss-units/reporte",
    "/api/igss-units/nogs/all",
    "/api/igss-units/nogs/resumen",
    "/api/igss-units/nogs/alertas",
    "/api/evaluaciones?page=1&limit=5",
    "/api/patients/export/excel",
    "/api/patients/export/pdf",
    "/api/patients/export/template",
    "/api/patients/import/template",
]


@pytest.mark.parametrize("path", ALLOWED)
def test_allowed_endpoints(client, path):
    r = client.get(f"{BASE_URL}{path}")
    print(f"ALLOWED {path} -> {r.status_code} {r.text[:150] if r.status_code != 200 else ''}")
    assert r.status_code == 200


# --- Endpoints behind menus shown but possibly unauthorized (just record)
MENU_SHOWN = [
    "/api/surgeries?page=1&limit=5",
    "/api/surgeries/options",
    "/api/surgeries/template",
    "/api/quirofano/catalog",
    "/api/quirofano/anesthesia/types",
    "/api/quirofano/anesthesia/records",
    "/api/quirofano/anesthesia/closure",
    "/api/quirofano/anesthesia/closure/filtros",
    "/api/agenda/citas",
]


@pytest.mark.parametrize("path", MENU_SHOWN)
def test_menu_shown_endpoints_record(client, path):
    r = client.get(f"{BASE_URL}{path}")
    print(f"MENU_SHOWN {path} -> {r.status_code} {r.text[:200]}")
    assert r.status_code in (200, 403, 404, 422)


# --- Endpoints that MUST be blocked
BLOCKED = [
    "/api/dashboard/financiero",
    "/api/users",
    "/api/caja-chica/movimientos",
    "/api/optica/frames",
    "/api/cuentas-cobrar/clinica",
    "/api/cuentas-cobrar/optica",
    "/api/surgery-crm",
]


@pytest.mark.parametrize("path", BLOCKED)
def test_blocked_endpoints(client, path):
    r = client.get(f"{BASE_URL}{path}")
    print(f"BLOCKED {path} -> {r.status_code} {r.text[:200]}")
    assert r.status_code in (401, 403, 404, 405), f"{path} returned {r.status_code}"


# --- IGSS unit CRUD
def test_igss_unit_create_update_delete(client):
    name = f"TEST_UNIDAD_{uuid.uuid4().hex[:6]}"
    r = client.post(f"{BASE_URL}/api/igss-units", json={"name": name})
    print("CREATE UNIT", r.status_code, r.text[:300])
    assert r.status_code in (200, 201)
    uid = r.json()["id"]
    try:
        r2 = client.put(f"{BASE_URL}/api/igss-units/{uid}", json={"name": name + "_E"})
        print("UPDATE UNIT", r2.status_code, r2.text[:200])
        assert r2.status_code == 200
        g = client.get(f"{BASE_URL}/api/igss-units/{uid}")
        assert g.json()["name"] == name + "_E"
        rn = client.get(f"{BASE_URL}/api/igss-units/{uid}/nogs")
        print("UNIT NOGS", rn.status_code, rn.text[:200])
        assert rn.status_code == 200
    finally:
        d = client.delete(f"{BASE_URL}/api/igss-units/{uid}")
        print("DELETE UNIT", d.status_code, d.text[:200])


# --- IGSS patient flow: create -> edit -> verify (cleanup via superadmin soft-delete)
def test_patient_create_edit_flow(client):
    units = client.get(f"{BASE_URL}/api/igss-units").json()["data"]
    unit_id = units[0]["id"] if units else None
    payload = {"first_name": "TEST_Igss", "last_name": f"Audit{uuid.uuid4().hex[:5]}", "gender": "femenino",
               "birth_date": "1980-05-05", "phone": "55550000", "referral_institution": "igss",
               "igss_unit_id": unit_id, "igss_affiliation_number": "123456789",
               "dpi": str(uuid.uuid4().int)[:13]}
    r = client.post(f"{BASE_URL}/api/patients", json=payload)
    print("CREATE PATIENT", r.status_code, r.text[:250])
    assert r.status_code in (200, 201)
    pid = r.json()["id"]
    try:
        u = client.put(f"{BASE_URL}/api/patients/{pid}", json={"phone": "55551111"})
        print("EDIT PATIENT", u.status_code, u.text[:200])
        assert u.status_code == 200
        g = client.get(f"{BASE_URL}/api/patients/{pid}")
        assert g.status_code == 200 and g.json()["phone"] == "55551111"
        assert g.json().get("igss_unit_id") == unit_id
        s = client.get(f"{BASE_URL}/api/patients", params={"search": payload["last_name"]})
        print("SEARCH", s.status_code, s.json().get("total"))
        assert any(p["id"] == pid for p in s.json()["data"])
        d = client.delete(f"{BASE_URL}/api/patients/{pid}")
        print("IGSS DELETE PATIENT (expected 403)", d.status_code)
    finally:
        sa = requests.Session()
        lr = sa.post(f"{BASE_URL}/api/auth/login", json=cred("superadmin"))
        if lr.status_code == 200:
            tok = lr.json().get("access_token") or lr.json().get("token")
            if tok:
                sa.headers.update({"Authorization": f"Bearer {tok}"})
            print("CLEANUP PATIENT", sa.delete(f"{BASE_URL}/api/patients/{pid}").status_code)


# --- Write actions exposed by buttons on menu-shown screens (record status)
def test_write_actions_from_visible_buttons(client):
    r = client.post(f"{BASE_URL}/api/quirofano/catalog", json={"tipo": "insumo", "name": "TEST_igss_should_fail"})
    print("INSUMO AGREGAR", r.status_code, r.text[:150])
    r2 = client.get(f"{BASE_URL}/api/igss-units/mantenimiento/borradores-vacios")
    print("MANTENIMIENTO GET", r2.status_code, r2.text[:150])
    assert r.status_code == 403
