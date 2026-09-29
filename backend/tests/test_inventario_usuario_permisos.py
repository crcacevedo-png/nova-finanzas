"""Tests for 'usuario' role permissions on inventario:
- Entrada rápida (POST /api/inventario/entrada) allowed
- PUT /api/inventario/productos/{id} min/max allowed
- PUT precio_venta by usuario rejected (400)
- Admin regression: not broken
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://novavision-finanzas.preview.emergentagent.com').rstrip('/')


def login(username, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed for {username}: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def admin_session():
    return login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def user_session():
    # small delay to avoid rate limit collision with admin login
    time.sleep(1)
    return login("usuario", "user2024")


@pytest.fixture(scope="module")
def product_and_bodega(admin_session):
    # Fetch first product controlling inventario
    r = admin_session.get(f"{BASE_URL}/api/inventario/productos?limit=100")
    assert r.status_code == 200, r.text
    payload = r.json()
    productos = payload.get("data") or payload.get("productos") or payload.get("items") if isinstance(payload, dict) else payload
    prod = None
    for p in productos:
        controla = p.get("controla_inventario") or p.get("controlaInventario")
        maneja_lotes = p.get("controla_lotes") or p.get("maneja_lotes") or p.get("manejaLotes")
        if controla and not maneja_lotes:
            prod = p
            break
    if not prod:
        for p in productos:
            if p.get("controla_inventario") or p.get("controlaInventario"):
                prod = p
                break
    if not prod and productos:
        prod = productos[0]
    assert prod, "No product found"

    rb = admin_session.get(f"{BASE_URL}/api/inventario/bodegas")
    assert rb.status_code == 200
    bod_payload = rb.json()
    bodegas = bod_payload.get("data") or bod_payload.get("bodegas") or bod_payload.get("items") if isinstance(bod_payload, dict) else bod_payload
    assert bodegas, "No bodegas"
    return prod, bodegas[0]


class TestUsuarioPermissions:
    def test_usuario_can_update_min_max(self, user_session, product_and_bodega):
        prod, _ = product_and_bodega
        pid = prod.get("id") or prod.get("_id")
        payload = {"existencia_minima": 7, "existencia_maxima": 150}
        r = user_session.put(f"{BASE_URL}/api/inventario/productos/{pid}", json=payload)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        # Verify persistence
        g = user_session.get(f"{BASE_URL}/api/inventario/productos/{pid}")
        assert g.status_code == 200
        data = g.json()
        assert data.get("existencia_minima") == 7
        assert data.get("existencia_maxima") == 150

    def test_usuario_cannot_change_precio(self, user_session, product_and_bodega, admin_session):
        prod, _ = product_and_bodega
        pid = prod.get("id") or prod.get("_id")
        # Get current price via admin
        g = admin_session.get(f"{BASE_URL}/api/inventario/productos/{pid}")
        original_price = g.json().get("precio_venta")

        r = user_session.put(f"{BASE_URL}/api/inventario/productos/{pid}", json={"precio_venta": 99999})
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

        # Confirm price unchanged
        g2 = admin_session.get(f"{BASE_URL}/api/inventario/productos/{pid}")
        assert g2.json().get("precio_venta") == original_price

    def test_usuario_can_register_entrada(self, user_session, product_and_bodega):
        prod, bodega = product_and_bodega
        pid = prod.get("id") or prod.get("_id")
        bid = bodega.get("id") or bodega.get("_id")
        payload = {
            "producto_id": pid,
            "bodega_id": bid,
            "cantidad": 3,
            "costo_unitario": 1.0,
            "motivo": "TEST_entrada_usuario"
        }
        r = user_session.post(f"{BASE_URL}/api/inventario/entrada", json=payload)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


class TestAdminRegression:
    def test_admin_entrada(self, admin_session, product_and_bodega):
        prod, bodega = product_and_bodega
        pid = prod.get("id") or prod.get("_id")
        bid = bodega.get("id") or bodega.get("_id")
        payload = {"producto_id": pid, "bodega_id": bid, "cantidad": 1, "costo_unitario": 1.0, "motivo": "TEST_admin"}
        r = admin_session.post(f"{BASE_URL}/api/inventario/entrada", json=payload)
        assert r.status_code == 200, r.text

    def test_admin_can_update_precio(self, admin_session, product_and_bodega):
        prod, _ = product_and_bodega
        pid = prod.get("id") or prod.get("_id")
        g = admin_session.get(f"{BASE_URL}/api/inventario/productos/{pid}")
        orig = g.json().get("precio_venta")
        new_price = (orig or 10) + 0  # no-op price to avoid disruption; just verify allowed
        r = admin_session.put(f"{BASE_URL}/api/inventario/productos/{pid}", json={"precio_venta": new_price})
        assert r.status_code == 200, r.text
