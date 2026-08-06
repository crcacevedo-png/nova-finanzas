# Backend tests for POS (Punto de Venta) module
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    tk = data.get("access_token") or data.get("token")
    assert tk, f"No token in response: {data}"
    return tk


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- POS endpoints ----------

def test_get_bodega_pos(headers):
    r = requests.get(f"{BASE_URL}/api/ventas/bodega-pos", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "bodega_id" in data and "bodega_nombre" in data
    return data


def test_buscar_productos_pos(headers):
    bod = requests.get(f"{BASE_URL}/api/ventas/bodega-pos", headers=headers).json()
    r = requests.get(
        f"{BASE_URL}/api/ventas/productos",
        params={"bodega_id": bod["bodega_id"], "limit": 50},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    productos = r.json()
    assert isinstance(productos, list)
    assert len(productos) > 0, "No hay productos disponibles en la bodega POS"
    for p in productos[:3]:
        for f in ["id", "codigo", "nombre", "precio_venta", "existencia", "afecto_iva"]:
            assert f in p, f"Falta campo {f} en producto"


def test_ventas_hoy(headers):
    r = requests.get(f"{BASE_URL}/api/ventas/hoy", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "data" in data and "total" in data


def test_resumen_dia(headers):
    r = requests.get(f"{BASE_URL}/api/ventas/resumen-dia", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "total_ventas" in data
    assert "por_metodo_pago" in data
    for m in ["Efectivo", "Tarjeta", "Transferencia", "Cheque", "Cuenta por Cobrar"]:
        assert m in data["por_metodo_pago"], f"Falta método {m}"


def test_listar_ventas(headers):
    r = requests.get(f"{BASE_URL}/api/ventas", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "data" in data and "total" in data


# ---------- Full sale flow: create sale, verify inventory decremented ----------

def test_crear_venta_y_descontar_inventario(headers):
    # 1. Get bodega POS
    bod_res = requests.get(f"{BASE_URL}/api/ventas/bodega-pos", headers=headers)
    assert bod_res.status_code == 200
    bodega_id = bod_res.json()["bodega_id"]

    # 2. Get a product with stock
    prod_res = requests.get(
        f"{BASE_URL}/api/ventas/productos",
        params={"bodega_id": bodega_id, "limit": 50},
        headers=headers,
    )
    productos = prod_res.json()
    producto = next((p for p in productos if p["existencia"] > 2 and p["precio_venta"] > 0), None)
    if not producto:
        pytest.skip("No hay producto con stock > 2 y precio > 0 para probar")

    stock_antes = producto["existencia"]
    precio = producto["precio_venta"]
    afecto_iva = producto["afecto_iva"]

    # 3. Verify stock endpoint
    vs = requests.post(
        f"{BASE_URL}/api/ventas/verificar-stock",
        json={"items": [{"producto_id": producto["id"], "cantidad": 1}], "bodega_id": bodega_id},
        headers=headers,
    )
    assert vs.status_code == 200, vs.text
    assert vs.json().get("puede_proceder") is True

    # 4. Create sale
    subtotal = precio * 1
    iva = subtotal * 0.12 if afecto_iva else 0
    total = round(subtotal + iva, 2)

    venta_payload = {
        "bodega_id": bodega_id,
        "paciente_id": None,
        "paciente_nombre": None,
        "items": [{
            "producto_id": producto["id"],
            "codigo": producto["codigo"],
            "nombre": producto["nombre"],
            "cantidad": 1,
            "precio_unitario": precio,
            "descuento": 0,
            "subtotal": subtotal,
            "afecto_iva": afecto_iva,
        }],
        "formas_pago": [{"metodo": "Efectivo", "monto": total, "referencia": None}],
        "observaciones": "TEST_venta automated",
    }
    r = requests.post(f"{BASE_URL}/api/ventas", json=venta_payload, headers=headers)
    assert r.status_code == 200, f"Crear venta falló: {r.status_code} {r.text}"
    venta = r.json()
    assert venta.get("numero_venta", "").startswith("VTA-")
    assert venta.get("total") == total
    assert venta.get("estado") == "completada"
    venta_id = venta["id"]

    # 5. Verify inventory decremented
    prod_res2 = requests.get(
        f"{BASE_URL}/api/ventas/productos",
        params={"bodega_id": bodega_id, "search": producto["codigo"], "limit": 5},
        headers=headers,
    )
    productos2 = prod_res2.json()
    match = next((p for p in productos2 if p["id"] == producto["id"]), None)
    assert match is not None, "Producto no encontrado tras venta"
    # if product controls inventory, stock should decrease by 1
    if not match.get("controla_lotes", False):
        # For products without lot control, existencia may still update
        assert match["existencia"] == stock_antes - 1, (
            f"Stock no decrementó. Antes: {stock_antes}, Ahora: {match['existencia']}"
        )

    # 6. Verify sale is retrievable
    r_get = requests.get(f"{BASE_URL}/api/ventas/{venta_id}", headers=headers)
    assert r_get.status_code == 200
    assert r_get.json()["numero_venta"] == venta["numero_venta"]

    # 7. Verify ticket generation
    r_ticket = requests.get(f"{BASE_URL}/api/ventas/{venta_id}/ticket", headers=headers)
    assert r_ticket.status_code == 200
    t = r_ticket.json()
    assert t["venta"]["numero"] == venta["numero_venta"]
    assert t["totales"]["total"] == total


def test_venta_sin_items_falla(headers):
    bod_res = requests.get(f"{BASE_URL}/api/ventas/bodega-pos", headers=headers)
    bodega_id = bod_res.json()["bodega_id"]
    r = requests.post(
        f"{BASE_URL}/api/ventas",
        json={"bodega_id": bodega_id, "items": [], "formas_pago": [{"metodo": "Efectivo", "monto": 10}]},
        headers=headers,
    )
    assert r.status_code == 400


def test_venta_pago_insuficiente(headers):
    bod_res = requests.get(f"{BASE_URL}/api/ventas/bodega-pos", headers=headers)
    bodega_id = bod_res.json()["bodega_id"]
    prods = requests.get(
        f"{BASE_URL}/api/ventas/productos",
        params={"bodega_id": bodega_id, "limit": 20},
        headers=headers,
    ).json()
    p = next((p for p in prods if p["existencia"] > 0 and p["precio_venta"] > 10), None)
    if not p:
        pytest.skip("no producto adecuado")
    payload = {
        "bodega_id": bodega_id,
        "items": [{
            "producto_id": p["id"], "codigo": p["codigo"], "nombre": p["nombre"],
            "cantidad": 1, "precio_unitario": p["precio_venta"], "descuento": 0,
            "subtotal": p["precio_venta"], "afecto_iva": p["afecto_iva"],
        }],
        "formas_pago": [{"metodo": "Efectivo", "monto": 0.01}],
    }
    r = requests.post(f"{BASE_URL}/api/ventas", json=payload, headers=headers)
    assert r.status_code == 400
