# Sociedades Médicas: consumos from POS sales (valued at sale price), resumen, exports, role access
import io
import os
import uuid
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"

TAG = uuid.uuid4().hex[:6]
PROD_ID = f"TEST_prod_{TAG}"
VENTA_OK = f"TEST_venta_ok_{TAG}"
VENTA_OK2 = f"TEST_venta_ok2_{TAG}"
VENTA_ANUL = f"TEST_venta_anul_{TAG}"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


async def _db_op(fn):
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    try:
        return await fn(client[os.environ['DB_NAME']])
    finally:
        client.close()


def login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def sa():
    return login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def seed(sa):
    # TEST_ sociedad via API
    r = requests.post(f"{API}/inventario/sociedades/catalogo", headers=sa,
                      json={"nombre": f"TEST_Soc_{TAG}", "color": "blue"})
    assert r.status_code == 200, r.text
    soc_id = r.json()["sociedad"]["id"]

    async def ins(db):
        await db.productos_inventario.insert_one({
            "id": PROD_ID, "codigo": f"TST-{TAG}", "nombre": f"TEST_SocProd_{TAG}",
            "es_sociedad": True, "sociedad_id": soc_id, "origen": "clinica",
            "controla_inventario": False, "activo": True, "precio_venta": 500.0, "precio_compra": 100.0,
            "tipo": "producto"})
        base = {"origen": "clinica", "bodega_id": "", "vendedor_nombre": "QA"}
        await db.ventas.insert_many([
            {**base, "numero_venta": VENTA_OK, "id": VENTA_OK, "fecha": "2019-03-10T15:00:00+00:00", "estado": "completada",
             "items": [{"producto_id": PROD_ID, "cantidad": 2, "precio_unitario": 500.0, "subtotal": 1000.0}]},
            {**base, "numero_venta": VENTA_OK2, "id": VENTA_OK2, "fecha": "2019-03-20T15:00:00+00:00", "estado": "completada",
             "items": [{"producto_id": PROD_ID, "cantidad": 1, "precio_unitario": 450.0, "subtotal": 450.0}]},
            {**base, "numero_venta": VENTA_ANUL, "id": VENTA_ANUL, "fecha": "2019-03-15T15:00:00+00:00", "estado": "anulada",
             "items": [{"producto_id": PROD_ID, "cantidad": 7, "precio_unitario": 500.0, "subtotal": 3500.0}]},
        ])
    asyncio.run(_db_op(ins))
    yield {"soc_id": soc_id}

    async def cleanup(db):
        await db.ventas.delete_many({"id": {"$in": [VENTA_OK, VENTA_OK2, VENTA_ANUL]}})
        await db.productos_inventario.delete_one({"id": PROD_ID})
    asyncio.run(_db_op(cleanup))
    requests.delete(f"{API}/inventario/sociedades/catalogo/{soc_id}", headers=sa)


@pytest.fixture(scope="module")
def admin_headers(sa):
    uname = f"TEST_adm_{TAG}"
    r = requests.post(f"{API}/users", headers=sa,
                      json={"username": uname, "name": "TEST Admin", "password": "TestAdm2024$", "role": "admin"})
    assert r.status_code in (200, 201), r.text
    uid = r.json()["id"]
    h = login(uname, "TestAdm2024$")
    yield h
    d = requests.delete(f"{API}/users/{uid}", headers=sa)
    assert d.status_code in (200, 204), d.text


class TestConsumosFromVentas:
    def test_consumos_global_nonzero(self, sa):
        r = requests.get(f"{API}/inventario/sociedades/consumos", headers=sa)
        assert r.status_code == 200
        d = r.json()
        assert d["total"] > 0 and d["resumen"]["total_costo"] > 0 and d["resumen"]["total_cantidad"] > 0
        row = d["data"][0]
        for k in ("fecha", "producto_nombre", "sociedad_nombre", "cantidad", "costo_total"):
            assert k in row

    def test_consumos_product_filter_sale_price_excludes_anulada(self, sa, seed):
        r = requests.get(f"{API}/inventario/sociedades/consumos", headers=sa, params={"producto_id": PROD_ID})
        assert r.status_code == 200
        d = r.json()
        assert d["total"] == 2
        assert d["resumen"]["total_cantidad"] == 3
        assert d["resumen"]["total_costo"] == 1450.0
        ids = {x["referencia_id"] for x in d["data"]}
        assert VENTA_ANUL not in ids
        assert all(x["sociedad_nombre"] == f"TEST_Soc_{TAG}" for x in d["data"])

    def test_consumos_date_filter(self, sa, seed):
        r = requests.get(f"{API}/inventario/sociedades/consumos", headers=sa,
                         params={"producto_id": PROD_ID, "fecha_inicio": "2019-03-01", "fecha_fin": "2019-03-10"})
        d = r.json()
        assert d["total"] == 1 and d["resumen"]["total_costo"] == 1000.0

    def test_consumos_sociedad_filter(self, sa, seed):
        r = requests.get(f"{API}/inventario/sociedades/consumos", headers=sa, params={"sociedad_id": seed["soc_id"]})
        d = r.json()
        assert d["total"] == 2 and d["resumen"]["total_costo"] == 1450.0

    def test_resumen_month(self, sa, seed):
        r = requests.get(f"{API}/inventario/sociedades/resumen", headers=sa,
                         params={"mes": 3, "anio": 2019, "sociedad_id": seed["soc_id"]})
        assert r.status_code == 200
        d = r.json()
        assert d["total_consumos"] == 3 and d["total_costo"] == 1450.0
        assert d["por_producto"][0]["producto_id"] == PROD_ID
        assert d["por_producto"][0]["costo_total"] == 1450.0

    def test_resumen_current_month(self, sa):
        r = requests.get(f"{API}/inventario/sociedades/resumen", headers=sa)
        assert r.status_code == 200 and "por_producto" in r.json()

    def test_excel_export(self, sa, seed):
        import openpyxl
        r = requests.get(f"{API}/inventario/sociedades/exportar/excel", headers=sa,
                         params={"mes": 3, "anio": 2019, "sociedad_id": seed["soc_id"]})
        assert r.status_code == 200
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        ws = wb.active
        hdr = [ws.cell(row=4, column=i).value for i in range(1, 8)]
        assert hdr == ["Fecha", "Código", "Producto", "Sociedad", "Cantidad", "Monto Unit.", "Monto Total"]
        assert ws.cell(row=7, column=1).value == "TOTALES"
        assert ws.cell(row=7, column=5).value == 3 and ws.cell(row=7, column=7).value == 1450.0

    def test_excel_export_range(self, sa, seed):
        import openpyxl
        r = requests.get(f"{API}/inventario/sociedades/exportar/excel", headers=sa,
                         params={"fecha_inicio": "2019-03-15", "fecha_fin": "2019-03-31", "sociedad_id": seed["soc_id"]})
        ws = openpyxl.load_workbook(io.BytesIO(r.content)).active
        assert ws.cell(row=6, column=1).value == "TOTALES" and ws.cell(row=6, column=7).value == 450.0

    def test_pdf_export(self, sa, seed):
        r = requests.get(f"{API}/inventario/sociedades/exportar/pdf", headers=sa,
                         params={"mes": 3, "anio": 2019, "sociedad_id": seed["soc_id"]})
        assert r.status_code == 200 and r.content[:4] == b"%PDF"
        from pypdf import PdfReader
        txt = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
        assert "Resumen por Producto" in txt and "Detalle de Consumos por Venta" in txt
        assert "1,450.00" in txt

    def test_productos_includes_no_inventory(self, sa, seed):
        r = requests.get(f"{API}/inventario/sociedades/productos", headers=sa)
        assert r.status_code == 200
        p = [x for x in r.json() if x["id"] == PROD_ID]
        assert p and p[0]["controla_inventario"] is False


class TestRoleAccess:
    def test_admin_can_access(self, admin_headers):
        for ep in ("consumos", "resumen", "productos", "catalogo"):
            r = requests.get(f"{API}/inventario/sociedades/{ep}", headers=admin_headers)
            assert r.status_code == 200, (ep, r.text)
        r = requests.get(f"{API}/inventario/sociedades/exportar/excel", headers=admin_headers)
        assert r.status_code == 200

    def test_usuario_blocked(self):
        h = login("usuario", "user2024")
        for ep in ("consumos", "resumen", "productos", "exportar/excel", "exportar/pdf"):
            r = requests.get(f"{API}/inventario/sociedades/{ep}", headers=h)
            assert r.status_code == 403, ep
