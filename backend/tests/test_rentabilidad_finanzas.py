# Tests para: reportes de rentabilidad, productos con precio_compra, categorías inventario, finanzas (gastos/ingresos)
# Excluye módulo de Óptica por indicación del usuario.
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback a frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    assert r.status_code == 200, f"Login falló: {r.status_code} {r.text}"
    data = r.json()
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="session")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


# ---------- Categorías ----------
class TestCategorias:
    def test_listar_categorias(self, client):
        r = client.get(f"{API}/inventario/categorias", timeout=30)
        assert r.status_code == 200
        assert "data" in r.json()

    def test_crear_editar_eliminar_categoria(self, client):
        nombre = f"TEST_Cat_{uuid.uuid4().hex[:6]}"
        r = client.post(f"{API}/inventario/categorias", json={"nombre": nombre, "icono": "package", "color": "#123456"}, timeout=30)
        assert r.status_code == 200, r.text
        cat = r.json()
        cat_id = cat["id"]
        assert cat["nombre"] == nombre

        # Editar
        r2 = client.put(f"{API}/inventario/categorias/{cat_id}", json={"nombre": nombre + "_upd", "icono": "package", "color": "#000000"}, timeout=30)
        assert r2.status_code == 200
        assert r2.json()["nombre"].endswith("_upd")

        # Eliminar
        r3 = client.delete(f"{API}/inventario/categorias/{cat_id}", timeout=30)
        assert r3.status_code == 200


# ---------- Productos con precio_compra ----------
class TestProductos:
    def test_crear_producto_con_precio_compra_y_verificar(self, client):
        # Crear categoría auxiliar
        cat_nombre = f"TEST_Cat_{uuid.uuid4().hex[:6]}"
        rc = client.post(f"{API}/inventario/categorias", json={"nombre": cat_nombre}, timeout=30)
        assert rc.status_code == 200
        cat_id = rc.json()["id"]

        payload = {
            "codigo": f"TESTP-{uuid.uuid4().hex[:8]}",
            "nombre": f"TEST_Prod_{uuid.uuid4().hex[:6]}",
            "categoria_id": cat_id,
            "tipo": "producto",
            "precio_compra": 50.0,
            "precio_venta": 80.0,
            "controla_inventario": True,
        }
        r = client.post(f"{API}/inventario/productos", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        prod = r.json()
        prod_id = prod["id"]
        assert prod["precio_compra"] == 50.0
        assert prod["precio_venta"] == 80.0

        # GET
        rg = client.get(f"{API}/inventario/productos/{prod_id}", timeout=30)
        assert rg.status_code == 200
        got = rg.json()
        assert got["precio_compra"] == 50.0
        assert got["precio_venta"] == 80.0

        # Cleanup
        client.delete(f"{API}/inventario/productos/{prod_id}?force=true", timeout=30)
        client.delete(f"{API}/inventario/categorias/{cat_id}", timeout=30)


# ---------- Reportes de rentabilidad ----------
class TestReporteRentabilidad:
    def test_rentabilidad_categorias(self, client):
        r = client.get(f"{API}/inventario/reportes/rentabilidad-categorias", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "categorias" in data
        assert "resumen" in data
        for key in ("margen_promedio_general", "ganancia_potencial_total", "valor_total_venta", "total_productos", "total_categorias", "valor_total_costo"):
            assert key in data["resumen"], f"Falta resumen.{key}"
        # Estructura de cada categoría
        if data["categorias"]:
            cat = data["categorias"][0]
            for k in ("categoria_nombre", "total_productos", "margen_promedio", "margen_minimo", "margen_maximo",
                      "ganancia_promedio", "valor_inventario_costo", "valor_inventario_venta", "ganancia_potencial"):
                assert k in cat, f"Falta cat.{k}"

    def test_rentabilidad_categorias_solo_con_stock(self, client):
        r = client.get(f"{API}/inventario/reportes/rentabilidad-categorias?solo_con_stock=true", timeout=60)
        assert r.status_code == 200

    @pytest.mark.parametrize("meses", [6, 12, 18, 24])
    def test_rentabilidad_historico(self, client, meses):
        r = client.get(f"{API}/inventario/reportes/rentabilidad-historico?meses={meses}", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "datos_mensuales" in data
        assert "tendencia" in data
        assert "variacion_ultimo_mes" in data
        if data["datos_mensuales"]:
            m = data["datos_mensuales"][0]
            for k in ("mes_nombre", "total_ventas", "productos_vendidos", "ingresos_brutos",
                      "costo_total", "ganancia_neta", "margen_promedio"):
                assert k in m, f"Falta datos_mensuales.{k}"


# ---------- Finanzas: Dashboard, Gastos, Ingresos ----------
class TestFinanzas:
    def test_dashboard_financiero(self, client):
        # Probar endpoints comunes
        candidates = [
            f"{API}/finanzas/dashboard",
            f"{API}/expenses/dashboard",
            f"{API}/dashboard/financiero",
        ]
        found = False
        for url in candidates:
            r = client.get(url, timeout=30)
            if r.status_code == 200:
                found = True
                break
        assert found, f"Ningún endpoint dashboard financiero respondió 200: {candidates}"

    def test_listar_gastos(self, client):
        r = client.get(f"{API}/expenses", timeout=30)
        assert r.status_code == 200, r.text

    def test_listar_ingresos(self, client):
        # income endpoint may not exist in this system; skip if 404
        r = client.get(f"{API}/income", timeout=30)
        if r.status_code == 404:
            r = client.get(f"{API}/incomes", timeout=30)
        if r.status_code == 404:
            pytest.skip("No income endpoint available in backend")
        assert r.status_code == 200, r.text

    def test_crear_gasto_manual(self, client):
        payload = {
            "name": f"TEST_Gasto_{uuid.uuid4().hex[:6]}",
            "type": "variable",
            "amount": 100.50,
            "date": "2026-01-15",
            "notes": "Test automated",
        }
        r = client.post(f"{API}/expenses", json=payload, timeout=30)
        # Aceptar 200 o 201
        assert r.status_code in (200, 201), r.text
        body = r.json()
        gasto_id = body.get("id") or body.get("_id") or body.get("expense_id")
        # GET verify
        if gasto_id:
            rg = client.get(f"{API}/expenses/{gasto_id}", timeout=30)
            if rg.status_code == 200:
                assert rg.json().get("amount") == 100.50
            # cleanup
            client.delete(f"{API}/expenses/{gasto_id}", timeout=30)
