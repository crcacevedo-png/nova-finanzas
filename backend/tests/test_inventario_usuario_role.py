"""Test for bug fix: rol 'usuario' should be able to create products in Inventario."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _login(username, password):
    r = requests.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text}"
    d = r.json()
    tok = d.get("access_token") or d.get("token")
    assert tok, f"no token: {d}"
    return tok


@pytest.fixture(scope="module")
def usuario_headers():
    return {"Authorization": f"Bearer {_login('usuario', 'user2024')}"}


@pytest.fixture(scope="module")
def super_headers():
    return {"Authorization": f"Bearer {_login('superadmin', 'nova2024')}"}


created_ids = []


def test_usuario_get_suppliers(usuario_headers):
    r = requests.get(f"{API}/suppliers", headers=usuario_headers, timeout=30)
    print("GET /suppliers ->", r.status_code)
    assert r.status_code == 200, r.text


def test_usuario_get_sociedades_catalogo(usuario_headers):
    r = requests.get(f"{API}/inventario/sociedades/catalogo", headers=usuario_headers, timeout=30)
    print("GET /inventario/sociedades/catalogo ->", r.status_code)
    assert r.status_code == 200, r.text


def test_usuario_get_bodegas(usuario_headers):
    r = requests.get(f"{API}/inventario/bodegas", headers=usuario_headers, timeout=30)
    print("GET /inventario/bodegas ->", r.status_code)
    assert r.status_code == 200, r.text


def test_usuario_create_producto(usuario_headers):
    payload = {"nombre": "QA Prod API Usuario", "tipo": "producto"}
    r = requests.post(f"{API}/inventario/productos", json=payload, headers=usuario_headers, timeout=30)
    print("POST /inventario/productos ->", r.status_code, r.text[:300])
    assert r.status_code in (200, 201), r.text
    body = r.json()
    pid = body.get("id") or body.get("_id") or (body.get("producto") or {}).get("id")
    if pid:
        created_ids.append(pid)
    assert body.get("nombre") == "QA Prod API Usuario" or "producto" in body or "id" in body


def test_usuario_delete_producto_forbidden(usuario_headers, super_headers):
    # Create a product first
    r = requests.post(f"{API}/inventario/productos", json={"nombre": "QA Prod Delete Test", "tipo": "producto"}, headers=usuario_headers, timeout=30)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    pid = body.get("id") or (body.get("producto") or {}).get("id")
    if not pid:
        # try to list and find
        lst = requests.get(f"{API}/inventario/productos", headers=usuario_headers, timeout=30).json()
        items = lst if isinstance(lst, list) else lst.get("items", [])
        for it in items:
            if it.get("nombre") == "QA Prod Delete Test":
                pid = it.get("id")
                break
    assert pid, "could not find product id"
    created_ids.append(pid)

    # usuario delete should be 403
    rd = requests.delete(f"{API}/inventario/productos/{pid}", headers=usuario_headers, timeout=30)
    print("DELETE as usuario ->", rd.status_code)
    assert rd.status_code == 403, f"expected 403, got {rd.status_code}: {rd.text}"


def test_cleanup(super_headers):
    # cleanup QA products
    r = requests.get(f"{API}/inventario/productos?search=QA", headers=super_headers, timeout=30)
    if r.status_code == 200:
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", [])
        for it in items:
            name = it.get("nombre", "")
            if name.startswith("QA "):
                pid = it.get("id")
                if pid:
                    dr = requests.delete(f"{API}/inventario/productos/{pid}", headers=super_headers, timeout=30)
                    print(f"cleanup {name} ({pid}) -> {dr.status_code}")
