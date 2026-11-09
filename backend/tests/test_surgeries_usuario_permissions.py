# Regression: rol 'usuario' gestiona cirugías (view_sala_operaciones) sin afectar Gastos ni cancelar/eliminar
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


def _login(u, p):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login failed {u}: {r.status_code} {r.text[:200]}")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token' if 'access_token' in r.json() else 'token']}"})
    return s


@pytest.fixture(scope="module")
def usuario():
    return _login("usuario", "user2024")


@pytest.fixture(scope="module")
def superadmin():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def created(superadmin):
    ids = []
    yield ids
    for sid in ids:
        superadmin.delete(f"{BASE_URL}/api/surgeries/{sid}")


def _payload(name):
    return {"date": "2026-02-15", "time": "08:30", "patient_name": name, "procedure": "Facoemulsificación",
            "surgeon": "Dr. Carlos Méndez", "eye": "OD", "anesthesia_type": "local",
            "anesthesiologist": "TEST_Anest", "institution": "Privado", "observations": "obs1"}


# auth/me exposes permission
def test_me_permissions(usuario):
    r = usuario.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    perms = r.json().get("permissions", {})
    assert perms.get("view_sala_operaciones") is True
    assert not perms.get("create_expenses")
    assert not perms.get("edit_expenses")


# full surgery lifecycle as usuario
def test_usuario_crud_surgery(usuario, superadmin, created):
    r = usuario.post(f"{BASE_URL}/api/surgeries", json=_payload("TEST_PermUsuario"))
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    created.append(sid)
    r = usuario.put(f"{BASE_URL}/api/surgeries/{sid}", json={"observations": "obs2"})
    assert r.status_code == 200, r.text
    g = usuario.get(f"{BASE_URL}/api/surgeries/{sid}").json()
    assert g["observations"] == "obs2"
    r = usuario.post(f"{BASE_URL}/api/surgeries/{sid}/equipment", json={"name": "TEST_Equipo", "quantity": 1})
    assert r.status_code == 200, r.text
    r = usuario.post(f"{BASE_URL}/api/surgeries/{sid}/supplies", json={"name": "TEST_Insumo", "quantity": 2, "category": "otro"})
    assert r.status_code == 200, r.text
    g = usuario.get(f"{BASE_URL}/api/surgeries/{sid}").json()
    assert len(g["equipment"]) == 1 and len(g["supplies"]) == 1
    r = usuario.delete(f"{BASE_URL}/api/surgeries/{sid}/equipment/{g['equipment'][0]['id']}")
    assert r.status_code == 200, r.text
    r = usuario.delete(f"{BASE_URL}/api/surgeries/{sid}/supplies/{g['supplies'][0]['id']}")
    assert r.status_code == 200, r.text
    r = usuario.patch(f"{BASE_URL}/api/surgeries/{sid}/preop-status", json={"estado": "completo"})
    assert r.status_code == 200, r.text
    # iter128: usuario now CAN cancel/delete (previously 403)
    r = usuario.post(f"{BASE_URL}/api/surgeries/{sid}/cancel", json={"reason": "TEST"})
    assert r.status_code == 200
    r = usuario.delete(f"{BASE_URL}/api/surgeries/{sid}")
    assert r.status_code == 200


# cancel bypass via PUT status (should be blocked for non-superadmin)
def test_usuario_cannot_cancel_via_put(usuario, created):
    r = usuario.post(f"{BASE_URL}/api/surgeries", json=_payload("TEST_PermBypass"))
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    created.append(sid)
    r = usuario.put(f"{BASE_URL}/api/surgeries/{sid}", json={"status": "cancelado", "cancellation_reason": "TEST bypass"})
    g = usuario.get(f"{BASE_URL}/api/surgeries/{sid}").json()
    assert g.get("status") != "cancelado", f"PUT allowed cancel bypass: {r.status_code}"


# expenses still forbidden
def test_usuario_cannot_create_expense(usuario):
    r = usuario.post(f"{BASE_URL}/api/expenses", json={"description": "TEST_x", "amount": 1, "category": "otros", "date": "2026-01-10"})
    assert r.status_code == 403, r.text


# superadmin regression
def test_superadmin_create_edit(superadmin, created):
    r = superadmin.post(f"{BASE_URL}/api/surgeries", json=_payload("TEST_PermSA"))
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    created.append(sid)
    r = superadmin.put(f"{BASE_URL}/api/surgeries/{sid}", json={"observations": "sa2"})
    assert r.status_code == 200 and r.json()["observations"] == "sa2"
