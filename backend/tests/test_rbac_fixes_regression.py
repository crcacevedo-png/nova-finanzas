# Regression for RBAC fixes after iteration_145 (igss admin audit): cuentas_cobrar, surgeries, surgery-crm, patient exports/import
import os
import pytest
import requests
from usuarios_prueba import par  # usuarios sembrados solo para pruebas

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

CREDS = {
    "igss": par("igss"),
    "superadmin": par("superadmin"),
    "admin": par("admin"),
    "usuario": par("usuario"),
    "optica": par("optica"),
    "anestesia": par("anestesia"),
    "medico": par("medico"),
}
_sessions = {}


def sess(role):
    if role in _sessions:
        return _sessions[role]
    u, p = CREDS[role]
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login {role} failed {r.status_code} {r.text[:150]}")
    d = r.json()
    tok = d.get("access_token") or d.get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    _sessions[role] = s
    return s


# --- Patient exports (previous 500 KeyError record_number)
@pytest.mark.parametrize("role", ["igss", "superadmin", "admin"])
@pytest.mark.parametrize("path,ctype", [("/api/patients/export/excel", "spreadsheet"), ("/api/patients/export/pdf", "pdf")])
def test_patient_exports(role, path, ctype):
    r = sess(role).get(f"{BASE_URL}{path}", timeout=110)
    print(role, path, r.status_code, r.headers.get("content-type"), len(r.content))
    assert r.status_code == 200, r.text[:300]
    assert ctype in r.headers.get("content-type", "")
    assert len(r.content) > 1000


# --- Patients import endpoints use import_patients permission
@pytest.mark.parametrize("role,expected", [("igss", 200), ("superadmin", 200), ("usuario", 403), ("optica", 403)])
def test_import_stats_permission(role, expected):
    r = sess(role).get(f"{BASE_URL}/api/patients/import/stats")
    print(role, r.status_code, r.text[:150])
    assert r.status_code == expected


# --- Surgeries list/options require view_sala_operaciones
@pytest.mark.parametrize("role,expected", [("igss", 403), ("optica", 403), ("superadmin", 200), ("admin", 200),
                                           ("usuario", 200), ("anestesia", 200), ("medico", 200)])
def test_surgeries_list(role, expected):
    s = sess(role)
    r = s.get(f"{BASE_URL}/api/surgeries?page=1&limit=5")
    r2 = s.get(f"{BASE_URL}/api/surgeries/options")
    print(role, r.status_code, r2.status_code, r.text[:120])
    assert r.status_code == expected
    assert r2.status_code == expected
    if expected == 200:
        d = r.json()
        assert isinstance(d, dict) and ("items" in d or "surgeries" in d or "data" in d or "total" in d)


# --- Surgery CRM requires view_patients
@pytest.mark.parametrize("role,expected", [("igss", 200), ("superadmin", 200), ("admin", 200), ("usuario", 200), ("medico", 200), ("optica", 200)])
def test_crm_list_stats(role, expected):
    s = sess(role)
    r = s.get(f"{BASE_URL}/api/surgery-crm?page=1&limit=5")
    r2 = s.get(f"{BASE_URL}/api/surgery-crm/stats")
    print(role, r.status_code, r2.status_code)
    assert r.status_code == expected and r2.status_code == expected


def test_crm_requires_auth():
    r = requests.get(f"{BASE_URL}/api/surgery-crm")
    assert r.status_code in (401, 403)


# --- Cuentas por cobrar (finanzas)
CXC_READ = ["/api/cuentas-cobrar/responsables", "/api/cuentas-cobrar/clinica", "/api/cuentas-cobrar/clinica/resumen"]


@pytest.mark.parametrize("role,expected", [("igss", 403), ("optica", 403), ("anestesia", 403), ("medico", 403),
                                           ("superadmin", 200), ("admin", 200), ("usuario", 200)])
@pytest.mark.parametrize("path", CXC_READ)
def test_cxc_read(role, expected, path):
    r = sess(role).get(f"{BASE_URL}{path}")
    print(role, path, r.status_code, r.text[:100])
    assert r.status_code == expected


@pytest.mark.parametrize("role,expected", [("igss", 403), ("superadmin", 200), ("admin", 200), ("usuario", 200), ("optica", 200)])
@pytest.mark.parametrize("path", ["/api/cuentas-cobrar/optica", "/api/cuentas-cobrar/optica/resumen"])
def test_cxc_optica_read(role, expected, path):
    r = sess(role).get(f"{BASE_URL}{path}")
    print(role, path, r.status_code)
    assert r.status_code == expected


@pytest.mark.parametrize("role", ["usuario", "igss", "optica"])
def test_cxc_write_blocked(role):
    s = sess(role)
    r = s.post(f"{BASE_URL}/api/cuentas-cobrar/responsables", json={"nombre": "TEST_blocked", "tipo": "otro"})
    r2 = s.put(f"{BASE_URL}/api/cuentas-cobrar/nonexistent-id/anular", json={"motivo": "TEST"})
    r3 = s.post(f"{BASE_URL}/api/cuentas-cobrar/clinica", json={})
    print(role, r.status_code, r2.status_code, r3.status_code)
    assert r.status_code == 403
    assert r2.status_code == 403
    assert r3.status_code in (403, 422)


def test_cxc_responsable_crud_admin():
    s = sess("admin")
    r = s.post(f"{BASE_URL}/api/cuentas-cobrar/responsables", json={"nombre": "TEST_resp_rbac", "tipo": "otro"})
    print("create", r.status_code, r.text[:300])
    assert r.status_code in (200, 201), r.text
    rid = r.json()["id"]
    try:
        lst = s.get(f"{BASE_URL}/api/cuentas-cobrar/responsables").json()
        items = lst if isinstance(lst, list) else lst.get("data", [])
        assert any(i.get("id") == rid for i in items)
    finally:
        d = s.delete(f"{BASE_URL}/api/cuentas-cobrar/responsables/{rid}")
        print("delete", d.status_code)
        assert d.status_code in (200, 204)


def test_cxc_optica_detail_optica_role():
    s = sess("optica")
    lst = s.get(f"{BASE_URL}/api/cuentas-cobrar/optica").json()
    items = lst if isinstance(lst, list) else lst.get("data", lst.get("items", []))
    if not items:
        pytest.skip("no optica cxc")
    r = s.get(f"{BASE_URL}/api/cuentas-cobrar/{items[0]['id']}")
    print(r.status_code)
    assert r.status_code == 200
    # abono with invalid amount -> must not be 403 (validation instead)
    r2 = s.post(f"{BASE_URL}/api/cuentas-cobrar/{items[0]['id']}/abono", json={"monto": -1, "metodo_pago": "efectivo"})
    print("abono invalid", r2.status_code, r2.text[:200])
    assert r2.status_code != 403


# --- Menus for igss admin
def test_igss_menus():
    r = sess("igss").get(f"{BASE_URL}/api/menu-config/my-menus")
    print(r.text[:500])
    assert r.status_code == 200
    txt = r.text
    for bad in ["sala_operaciones", "agenda", "quirofano_insumos", "quirofano_anestesia", "optica_accesorios"]:
        assert f'"{bad}"' not in txt, bad


# --- IGSS units/NOG still work
@pytest.mark.parametrize("path", ["/api/igss-units", "/api/igss-units/nogs/all", "/api/igss-units/nogs/resumen", "/api/patients?page=1&limit=5"])
def test_igss_allowed(path):
    r = sess("igss").get(f"{BASE_URL}{path}")
    assert r.status_code == 200


# --- Anestesia procedures still work
@pytest.mark.parametrize("path", ["/api/quirofano/catalog", "/api/quirofano/anesthesia/records", "/api/quirofano/anesthesia/closure?month=2026-11", "/api/quirofano/anesthesia/types"])
def test_anestesia_misc(path):
    r = sess("anestesia").get(f"{BASE_URL}{path}")
    print(path, r.status_code, r.text[:150])
    assert r.status_code in (200, 404)
