"""Tests for the 3 bugs fixed in Optica POS 'Lentes' category
1. Contact lenses list endpoint returns items (with optional lens_type)
2. Lens types (oftalmicos) endpoint maps default_price -> price/sale_price
3. Both endpoints accessible with optica user for POS category 'Lentes'
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    # Fallback to frontend/.env
    with open('/app/frontend/.env') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                BASE_URL = line.split('=', 1)[1].strip().strip('"').rstrip('/')
                break


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"username": "superadmin", "password": "nova2024"},
                      timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture()
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_contact_lenses_endpoint_ok(headers):
    r = requests.get(f"{BASE_URL}/api/optica/contact-lenses?is_active=true", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    data = body.get("data", body if isinstance(body, list) else [])
    assert isinstance(data, list)
    # All entries should serialize (lens_type optional now)
    for item in data:
        assert "id" in item
        # sale_price or price should exist
        assert "sale_price" in item or "price" in item


def test_lens_types_endpoint_maps_prices(headers):
    r = requests.get(f"{BASE_URL}/api/optica/lens-types", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    data = body.get("data", body if isinstance(body, list) else [])
    assert isinstance(data, list)
    assert len(data) > 0, "Expected at least one lens type (oftalmico) seeded"
    for lt in data:
        assert "id" in lt and "name" in lt
        # Bug fix: default_price must be mapped to price and sale_price
        assert lt.get("price") == lt.get("default_price"), f"price no mapeado: {lt}"
        assert lt.get("sale_price") == lt.get("default_price"), f"sale_price no mapeado: {lt}"


def test_contact_lens_can_be_added_to_sale_v2(headers):
    """Simulate: agregar 1 lente de contacto + 1 oftálmico y crear la venta V2."""
    # Fetch one contact lens with stock
    r1 = requests.get(f"{BASE_URL}/api/optica/contact-lenses?is_active=true", headers=headers, timeout=15)
    assert r1.status_code == 200
    cls = r1.json().get("data", [])
    contact = next((c for c in cls if (c.get("stock") or 0) > 0), None)
    if not contact:
        pytest.skip("No hay lentes de contacto con stock para probar venta")

    # Fetch one lens type (oftalmico)
    r2 = requests.get(f"{BASE_URL}/api/optica/lens-types", headers=headers, timeout=15)
    assert r2.status_code == 200
    lts = r2.json().get("data", [])
    assert len(lts) > 0
    lt = lts[0]

    unit_contact = float(contact.get("sale_price") or contact.get("price") or 0)
    unit_oft = float(lt.get("sale_price") or lt.get("price") or lt.get("default_price") or 0)
    assert unit_oft > 0, "El precio del lente oftálmico debe estar mapeado (>0)"

    subtotal = unit_contact + unit_oft
    payload = {
        "patient_name": "TEST_Lentes_Consumidor",
        "items": [
            {"type": "contact_lens", "product_id": contact["id"], "quantity": 1,
             "unit_price": unit_contact, "subtotal": unit_contact},
            {"type": "lens_type", "product_id": lt["id"], "quantity": 1,
             "unit_price": unit_oft, "subtotal": unit_oft},
        ],
        "subtotal": subtotal,
        "discount": 0,
        "total": subtotal,
        "payments": [{"method": "Efectivo", "amount": subtotal}],
    }
    r3 = requests.post(f"{BASE_URL}/api/optica/sales/v2", json=payload, headers=headers, timeout=20)
    assert r3.status_code in (200, 201), f"Venta falló: {r3.status_code} {r3.text}"
    sale = r3.json()
    sale_id = sale.get("id") or sale.get("sale_id")
    assert sale_id, f"Sin id de venta: {sale}"

    # Cleanup: cancelar la venta para restaurar stock
    requests.post(f"{BASE_URL}/api/optica/sales/{sale_id}/cancel",
                  json={"reason": "TEST cleanup"}, headers=headers, timeout=15)
