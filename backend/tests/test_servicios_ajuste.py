"""
E2E backend tests for:
- Creating a producto tipo='servicio' → controla_inventario forced false, es_sociedad + sociedad_id round-trip
- POS should list services without stock verification (implicit via controla_inventario=false)
- Servicio marked as Sociedad appears in /inventario/sociedades/productos aggregate
- Ajuste de inventario CRUD (positive/negative)
"""
import os
import requests
import pytest
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def categoria_id(client):
    r = client.get(f"{API}/inventario/categorias")
    assert r.status_code == 200, r.text
    data = r.json()
    cats = data.get("data", data) if isinstance(data, dict) else data
    assert len(cats) > 0
    return cats[0]["id"]


@pytest.fixture(scope="module")
def bodega_id(client):
    r = client.get(f"{API}/inventario/bodegas")
    assert r.status_code == 200, r.text
    data = r.json()
    bods = data.get("data", data) if isinstance(data, dict) else data
    assert len(bods) > 0
    return bods[0]["id"]


@pytest.fixture(scope="module")
def sociedad_id(client):
    r = client.get(f"{API}/inventario/sociedades/catalogo")
    assert r.status_code == 200, r.text
    data = r.json()
    socs = data.get("data", data) if isinstance(data, dict) else data
    if not socs:
        # create one
        r = client.post(f"{API}/inventario/sociedades/catalogo", json={"nombre": "TEST_SOC_QA"})
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]
    return socs[0]["id"]


created_products = []


@pytest.fixture(scope="module", autouse=True)
def cleanup(client):
    yield
    for pid in created_products:
        try:
            client.delete(f"{API}/inventario/productos/{pid}")
        except Exception:
            pass


# ---------- Servicios ----------

class TestServicio:
    def test_create_servicio_forces_controla_inventario_false(self, client, categoria_id):
        payload = {
            "codigo": f"TSVQ-{uuid.uuid4().hex[:8]}",
            "nombre": f"TEST_Servicio_QA_{uuid.uuid4().hex[:6]}",
            "categoria_id": categoria_id,
            "tipo": "servicio",
            "unidad_medida": "unidad",
            "precio_compra": 0,
            "precio_venta": 500,
            "controla_inventario": True,  # even if true, backend should force false
            "controla_lotes": False,
            "existencia_minima": 0,
            "existencia_maxima": 0,
            "afecto_iva": True,
        }
        r = client.post(f"{API}/inventario/productos", json=payload)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        created_products.append(body["id"])

        assert body["tipo"] == "servicio"
        assert body["controla_inventario"] is False, "Servicio debe forzar controla_inventario=false"

        # Verify by GET
        r2 = client.get(f"{API}/inventario/productos/{body['id']}")
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2["tipo"] == "servicio"
        assert b2["controla_inventario"] is False

    def test_create_servicio_sociedad_roundtrip(self, client, categoria_id, sociedad_id):
        payload = {
            "codigo": f"TSSQ-{uuid.uuid4().hex[:8]}",
            "nombre": f"TEST_ServSoc_QA_{uuid.uuid4().hex[:6]}",
            "categoria_id": categoria_id,
            "tipo": "servicio",
            "unidad_medida": "unidad",
            "precio_compra": 0,
            "precio_venta": 750,
            "controla_inventario": False,
            "controla_lotes": False,
            "es_sociedad": True,
            "sociedad_id": sociedad_id,
            "existencia_minima": 0,
            "existencia_maxima": 0,
            "afecto_iva": True,
        }
        r = client.post(f"{API}/inventario/productos", json=payload)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        created_products.append(body["id"])

        # GET must return es_sociedad + sociedad_id
        r2 = client.get(f"{API}/inventario/productos/{body['id']}")
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2["es_sociedad"] is True
        assert b2["sociedad_id"] == sociedad_id

    def test_servicio_sociedad_appears_in_sociedades_productos(self, client, sociedad_id):
        r = client.get(f"{API}/inventario/sociedades/productos")
        assert r.status_code == 200, r.text
        data = r.json()
        productos = data.get("data", data) if isinstance(data, dict) else data
        # At least one of our created TEST_ServSoc products must appear
        found = [p for p in productos if p.get("id") in created_products]
        assert len(found) >= 1, f"Servicio marcado como sociedad no aparece en /sociedades/productos. total={len(productos)}"
        # sociedad_id should be resolved
        assert any(p.get("sociedad_id") == sociedad_id for p in found)

    def test_servicio_visible_in_pos_listing(self, client):
        # POS uses /inventario/productos filter activo. Ensure our service is present.
        r = client.get(f"{API}/inventario/productos?limit=200")
        assert r.status_code == 200
        data = r.json()
        prods = data.get("data", data)
        ids = {p["id"] for p in prods}
        assert any(pid in ids for pid in created_products)


# ---------- Ajuste inventario ----------

class TestAjusteInventario:
    @pytest.fixture(scope="class")
    def producto_fisico_id(self, client, categoria_id):
        payload = {
            "codigo": f"TPAQ-{uuid.uuid4().hex[:8]}",
            "nombre": f"TEST_ProdAjuste_QA_{uuid.uuid4().hex[:6]}",
            "categoria_id": categoria_id,
            "tipo": "producto",
            "unidad_medida": "unidad",
            "precio_compra": 10,
            "precio_venta": 25,
            "controla_inventario": True,
            "controla_lotes": False,
            "existencia_minima": 1,
            "existencia_maxima": 100,
            "afecto_iva": True,
        }
        r = client.post(f"{API}/inventario/productos", json=payload)
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]
        created_products.append(pid)
        return pid

    def test_ajuste_motivo_muy_corto_rechazado(self, client, producto_fisico_id, bodega_id):
        r = client.post(f"{API}/inventario/ajuste", json={
            "producto_id": producto_fisico_id, "bodega_id": bodega_id,
            "cantidad_nueva": 10, "motivo": "x"
        })
        assert r.status_code == 400

    def test_ajuste_positivo(self, client, producto_fisico_id, bodega_id):
        r = client.post(f"{API}/inventario/ajuste", json={
            "producto_id": producto_fisico_id, "bodega_id": bodega_id,
            "cantidad_nueva": 25, "motivo": "Ajuste inicial de prueba QA"
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("existencia_nueva") == 25

    def test_ajuste_negativo(self, client, producto_fisico_id, bodega_id):
        r = client.post(f"{API}/inventario/ajuste", json={
            "producto_id": producto_fisico_id, "bodega_id": bodega_id,
            "cantidad_nueva": 10, "motivo": "Merma detectada en QA test"
        })
        assert r.status_code == 200, r.text
        assert r.json()["existencia_nueva"] == 10

    def test_producto_no_existe(self, client, bodega_id):
        r = client.post(f"{API}/inventario/ajuste", json={
            "producto_id": "no-existe-uuid", "bodega_id": bodega_id,
            "cantidad_nueva": 1, "motivo": "Prueba producto inexistente"
        })
        assert r.status_code == 404
