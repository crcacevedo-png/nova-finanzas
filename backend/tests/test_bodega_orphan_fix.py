"""Tests for bodega deletion orphan fix and force-delete product collection fix."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://novavision-finanzas.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


def _login(username, password):
    r = requests.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed {username}: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in {data}"
    return tok


@pytest.fixture(scope="module")
def super_headers():
    return {"Authorization": f"Bearer {_login('superadmin', 'nova2024')}"}


@pytest.fixture(scope="module")
def user_headers():
    return {"Authorization": f"Bearer {_login('usuario', 'user2024')}"}


def test_1_non_superadmin_delete_forbidden(user_headers):
    r = requests.delete(f"{API}/inventario/bodegas/QA-BOD-ORPHAN", headers=user_headers, timeout=30)
    print(f"[NON-SUPER DELETE] status={r.status_code} body={r.text}")
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
    assert "SuperAdmin" in r.text or "superadmin" in r.text.lower()


def test_2_delete_bodega_real_stock_blocked(super_headers):
    """QA-BOD-REAL has real stock -> should return 400."""
    r = requests.delete(f"{API}/inventario/bodegas/QA-BOD-REAL", headers=super_headers, timeout=30)
    print(f"[DELETE REAL] status={r.status_code} body={r.text}")
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
    assert "No se puede eliminar una bodega con existencias" in r.text


def test_3_delete_bodega_orphan_allowed(super_headers):
    """QA-BOD-ORPHAN has orphan existencia only -> should now succeed (200)."""
    r = requests.delete(f"{API}/inventario/bodegas/QA-BOD-ORPHAN", headers=super_headers, timeout=30)
    print(f"[DELETE ORPHAN] status={r.status_code} body={r.text}")
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    # Verify the message
    msg = body.get("message") or body.get("detail") or str(body)
    assert "eliminada" in msg.lower() or "eliminado" in msg.lower(), f"unexpected msg: {msg}"

    # Verify bodega no longer listed
    r2 = requests.get(f"{API}/inventario/bodegas", headers=super_headers, timeout=30)
    assert r2.status_code == 200
    bodegas = r2.json()
    if isinstance(bodegas, dict):
        bodegas = bodegas.get("bodegas", bodegas.get("data", []))
    codes = [b.get("codigo") or b.get("id") for b in bodegas]
    names = [b.get("nombre", "") for b in bodegas]
    assert "QA-BOD-ORPHAN" not in codes, f"QA-BOD-ORPHAN still listed: {codes}"
    assert not any("Huerfana" in n or "Huérfana" in n for n in names), f"Huerfana bodega still listed: {names}"


def test_4_force_delete_product_cleans_existencias(super_headers):
    """Force delete QA-PROD-REAL, then QA-BOD-REAL should be deletable."""
    r = requests.delete(f"{API}/inventario/productos/QA-PROD-REAL?force=true", headers=super_headers, timeout=30)
    print(f"[FORCE DEL PROD] status={r.status_code} body={r.text}")
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"

    # Now delete the bodega, should succeed
    r2 = requests.delete(f"{API}/inventario/bodegas/QA-BOD-REAL", headers=super_headers, timeout=30)
    print(f"[DELETE REAL POST-FORCE] status={r2.status_code} body={r2.text}")
    assert r2.status_code == 200, f"expected 200 after force delete, got {r2.status_code}: {r2.text}"
