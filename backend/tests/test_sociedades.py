"""Tests for Sociedades Médicas module CRUD + product assignment flow."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
if not BASE_URL.startswith("http"):
    BASE_URL = "http://localhost:8001"

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def created_sociedad(headers):
    payload = {
        "nombre": "TEST_Sociedad_QA",
        "descripcion": "Sociedad de prueba QA",
        "nit": "123456-7",
        "telefono": "555-0001",
        "email": "qa@sociedad.test",
        "contacto": "QA Contact",
        "direccion": "Calle QA 123",
        "color": "blue",
    }
    r = requests.post(f"{API}/inventario/sociedades/catalogo", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "sociedad" in data
    soc = data["sociedad"]
    yield soc
    # cleanup - remove any product assignment first
    # attempt delete
    requests.delete(f"{API}/inventario/sociedades/catalogo/{soc['id']}", headers=headers)


class TestSociedadesCRUD:
    def test_list_sociedades(self, headers):
        r = requests.get(f"{API}/inventario/sociedades/catalogo", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_sociedad(self, created_sociedad):
        assert created_sociedad["nombre"] == "TEST_Sociedad_QA"
        assert created_sociedad["color"] == "blue"
        assert "id" in created_sociedad

    def test_duplicate_name_rejected(self, headers, created_sociedad):
        r = requests.post(
            f"{API}/inventario/sociedades/catalogo",
            json={"nombre": "test_sociedad_qa"},  # case-insensitive
            headers=headers,
        )
        assert r.status_code == 400

    def test_get_sociedad_detail(self, headers, created_sociedad):
        sid = created_sociedad["id"]
        r = requests.get(f"{API}/inventario/sociedades/catalogo/{sid}", headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == sid
        assert d["nombre"] == "TEST_Sociedad_QA"
        assert d["telefono"] == "555-0001"
        assert d["email"] == "qa@sociedad.test"

    def test_update_sociedad(self, headers, created_sociedad):
        sid = created_sociedad["id"]
        r = requests.put(
            f"{API}/inventario/sociedades/catalogo/{sid}",
            json={"descripcion": "Descripción actualizada", "color": "green"},
            headers=headers,
        )
        assert r.status_code == 200
        # verify
        r2 = requests.get(f"{API}/inventario/sociedades/catalogo/{sid}", headers=headers)
        assert r2.status_code == 200
        d = r2.json()
        assert d["descripcion"] == "Descripción actualizada"
        assert d["color"] == "green"

    def test_list_includes_created(self, headers, created_sociedad):
        r = requests.get(f"{API}/inventario/sociedades/catalogo", headers=headers)
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()]
        assert created_sociedad["id"] in ids


class TestProductoSociedadAssignment:
    """Verify that a product can be created marked as sociedad with sociedad_id."""

    @pytest.fixture(scope="class")
    def producto_asignado(self, headers, created_sociedad):
        # Need a category id
        cats = requests.get(f"{API}/inventario/categorias", headers=headers)
        assert cats.status_code == 200
        cat_data = cats.json()
        cat_list = cat_data.get("data", cat_data) if isinstance(cat_data, dict) else cat_data
        if not cat_list:
            pytest.skip("No hay categorías disponibles")
        cat_id = cat_list[0]["id"]

        payload = {
            "codigo": "TEST-SOC-001",
            "nombre": "TEST Producto Sociedad",
            "categoria_id": cat_id,
            "tipo": "producto",
            "unidad_medida": "unidad",
            "precio_venta": 100.0,
            "precio_compra": 50.0,
            "existencia_minima": 1,
            "existencia_maxima": 100,
            "es_sociedad": True,
            "sociedad_id": created_sociedad["id"],
        }
        r = requests.post(f"{API}/inventario/productos", json=payload, headers=headers)
        assert r.status_code in (200, 201), r.text
        prod = r.json()
        prod_id = prod.get("id") or prod.get("producto", {}).get("id")
        yield prod_id
        # cleanup product
        if prod_id:
            requests.delete(f"{API}/inventario/productos/{prod_id}", headers=headers)

    def test_producto_created_with_sociedad(self, headers, producto_asignado, created_sociedad):
        # fetch product
        r = requests.get(f"{API}/inventario/productos/{producto_asignado}", headers=headers)
        assert r.status_code == 200
        p = r.json()
        assert p.get("es_sociedad") is True
        assert p.get("sociedad_id") == created_sociedad["id"]

    def test_sociedad_productos_count_increments(self, headers, producto_asignado, created_sociedad):
        r = requests.get(
            f"{API}/inventario/sociedades/catalogo/{created_sociedad['id']}", headers=headers
        )
        assert r.status_code == 200
        assert r.json()["productos_count"] >= 1

    def test_list_productos_by_sociedad(self, headers, producto_asignado, created_sociedad):
        r = requests.get(
            f"{API}/inventario/sociedades/catalogo/{created_sociedad['id']}/productos",
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        # Endpoint might return list or dict
        productos = data if isinstance(data, list) else data.get("productos", [])
        ids = [p.get("id") for p in productos]
        assert producto_asignado in ids

    def test_cannot_delete_sociedad_with_products(self, headers, producto_asignado, created_sociedad):
        r = requests.delete(
            f"{API}/inventario/sociedades/catalogo/{created_sociedad['id']}", headers=headers
        )
        assert r.status_code == 400
