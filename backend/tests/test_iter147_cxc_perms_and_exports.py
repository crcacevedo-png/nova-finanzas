# Iteration 147: verifies CxC permission duplication fix (server.py vs config/permissions.py) and patient export endpoints
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

CREDS = {
    "superadmin": ("superadmin", "nova2024"),
    "admin": ("admin", "Admin2024$"),
    "usuario": ("usuario", "user2024"),
    "optica": ("optica", "Optica2024$"),
    "igss": ("igss.admin", "IgssAdmin2024$"),
}
_cache = {}


def login(key):
    if key in _cache:
        return _cache[key]
    u, p = CREDS[key]
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login {u} failed {r.status_code} {r.text[:200]}")
    _cache[key] = r.json()
    return _cache[key]


def hdr(key):
    d = login(key)
    tok = d.get("access_token") or d.get("token")
    return {"Authorization": f"Bearer {tok}"}


def perms(key):
    d = login(key)
    return (d.get("user") or {}).get("permissions") or d.get("permissions") or {}


# Login response now carries view/manage_cuentas_cobrar (server.py PERMISSIONS)
@pytest.mark.parametrize("role,view,manage", [
    ("superadmin", True, True), ("admin", True, True), ("usuario", True, False), ("optica", True, True),
])
def test_login_permissions_include_cxc(role, view, manage):
    p = perms(role)
    assert p.get("view_cuentas_cobrar") is view
    assert p.get("manage_cuentas_cobrar") is manage


def test_me_permissions_include_cxc():
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=hdr("usuario"), timeout=30)
    assert r.status_code == 200
    d = r.json()
    p = d.get("permissions") or (d.get("user") or {}).get("permissions") or {}
    assert p.get("view_cuentas_cobrar") is True
    assert p.get("manage_cuentas_cobrar") is False


def test_igss_has_no_cxc():
    p = perms("igss")
    assert not p.get("view_cuentas_cobrar")
    r = requests.get(f"{BASE_URL}/api/cuentas-cobrar/clinica", headers=hdr("igss"), timeout=30)
    assert r.status_code == 403


# CxC clinica list viewable by all 4 roles
@pytest.mark.parametrize("role", ["superadmin", "admin", "usuario", "optica"])
def test_cxc_clinica_view(role):
    for path in ["/api/cuentas-cobrar/clinica", "/api/cuentas-cobrar/clinica/resumen", "/api/cuentas-cobrar/responsables"]:
        r = requests.get(f"{BASE_URL}{path}", headers=hdr(role), timeout=30)
        assert r.status_code == 200, f"{role} {path} {r.status_code} {r.text[:200]}"


# usuario cannot manage
def test_usuario_cannot_manage_cxc():
    h = hdr("usuario")
    r = requests.post(f"{BASE_URL}/api/cuentas-cobrar/responsables", headers=h,
                      json={"nombre": "TEST_resp", "tipo": "otro"}, timeout=30)
    assert r.status_code == 403
    r = requests.put(f"{BASE_URL}/api/cuentas-cobrar/nonexistent/anular", headers=h, json={"motivo": "x"}, timeout=30)
    assert r.status_code == 403


def test_optica_own_cxc():
    r = requests.get(f"{BASE_URL}/api/cuentas-cobrar/optica", headers=hdr("optica"), timeout=30)
    assert r.status_code == 200


# Patient exports with Bearer token
@pytest.mark.parametrize("role", ["igss", "superadmin"])
def test_patient_exports(role):
    h = hdr(role)
    r = requests.get(f"{BASE_URL}/api/patients/export/excel", headers=h, timeout=60)
    assert r.status_code == 200 and r.content[:2] == b"PK"
    r = requests.get(f"{BASE_URL}/api/patients/export/pdf", headers=h, timeout=90)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_patient_template():
    r = requests.get(f"{BASE_URL}/api/patients/export/template", headers=hdr("superadmin"), timeout=60)
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_export_requires_auth():
    r = requests.get(f"{BASE_URL}/api/patients/export/excel", timeout=30)
    assert r.status_code in (401, 403)
