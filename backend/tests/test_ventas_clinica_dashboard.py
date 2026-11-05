# Tests for Ventas de Clínica module: dashboard, rankings, list filters, detail(fel), monthly report, anular authz
import os
import uuid
import io
from datetime import datetime, timezone
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def _login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login {u} failed {r.status_code}")
    d = r.json()
    return {"Authorization": f"Bearer {d.get('access_token') or d.get('token')}"}


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def usr():
    return _login("usuario", "user2024")


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(os.environ["MONGO_URL"])
    yield c[os.environ["DB_NAME"]]
    c.close()


@pytest.fixture(scope="module")
def test_admin(sa):
    """Create a TEST_ admin user, delete at teardown."""
    uname = f"test_admin_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/users", headers=sa, json={"username": uname, "name": "TEST_Admin", "role": "admin", "password": "TestAdmin2024$"})
    assert r.status_code == 200, r.text
    uid = r.json()["id"]
    h = _login(uname, "TestAdmin2024$")
    yield h
    requests.delete(f"{API}/users/{uid}", headers=sa)


def _make_test_sale(mongo):
    vid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    mongo.ventas.insert_one({
        "id": vid, "numero_venta": f"TEST_VTA-{vid[:6]}", "fecha": now, "origen": "clinica",
        "estado": "completada", "paciente_nombre": "TEST_Paciente", "medico_nombre": "TEST_Medico",
        "bodega_id": "TEST_bodega", "items": [{"producto_id": "TEST_noexiste", "nombre": "TEST_Prod", "cantidad": 1, "precio_unitario": 1, "subtotal": 1}],
        "subtotal": 1, "total": 1, "formas_pago": [{"metodo": "Efectivo", "monto": 1}], "created_at": now,
    })
    return vid


# ---- Dashboard ----
class TestDashboard:
    def test_stats(self, sa):
        r = requests.get(f"{API}/ventas/dashboard/stats", headers=sa)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["ventas_mes", "ordenes_mes", "ticket_promedio", "ventas_hoy", "ordenes_hoy", "anuladas_mes"]:
            assert k in d
        if d["ordenes_mes"]:
            assert abs(d["ticket_promedio"] - d["ventas_mes"] / d["ordenes_mes"]) < 0.02

    def test_monthly_chart(self, sa):
        r = requests.get(f"{API}/ventas/dashboard/monthly-chart", headers=sa)
        assert r.status_code == 200
        d = r.json()
        assert len(d) == 6 and all({"mes", "ventas", "ordenes"} <= set(x) for x in d)

    @pytest.mark.parametrize("ep,key", [("top-medicos", "medico_nombre"), ("top-productos", "nombre"), ("top-categorias", "categoria")])
    def test_rankings(self, sa, ep, key):
        r = requests.get(f"{API}/ventas/dashboard/{ep}?limit=5", headers=sa)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d, list) and len(d) <= 5
        for x in d:
            assert key in x

    def test_usuario_can_access_dashboard(self, usr):
        r = requests.get(f"{API}/ventas/dashboard/stats", headers=usr)
        assert r.status_code == 200

    def test_unauth(self):
        r = requests.get(f"{API}/ventas/dashboard/stats")
        assert r.status_code in (401, 403)


# ---- List & filters ----
class TestList:
    def test_list_limit_200(self, sa):
        r = requests.get(f"{API}/ventas?limit=200", headers=sa)
        assert r.status_code == 200, r.text
        assert isinstance(r.json()["data"], list)

    def test_filter_estado(self, sa):
        for est in ["completada", "anulada"]:
            r = requests.get(f"{API}/ventas", params={"estado": est, "limit": 200}, headers=sa)
            assert r.status_code == 200
            assert all(v["estado"] == est for v in r.json()["data"])

    def test_filter_dates(self, sa):
        r = requests.get(f"{API}/ventas", params={"fecha_desde": "2026-11-01", "fecha_hasta": "2026-11-30", "limit": 200}, headers=sa)
        assert r.status_code == 200
        assert all("2026-11-01" <= v["fecha"][:10] <= "2026-12-01" for v in r.json()["data"])

    def test_search_special_chars(self, sa):
        r = requests.get(f"{API}/ventas", params={"search": "(", "limit": 50}, headers=sa)
        assert r.status_code in (200, 400), f"regex special char gives {r.status_code}"

    def test_detail_has_fel(self, sa):
        lst = requests.get(f"{API}/ventas?limit=5", headers=sa).json()["data"]
        assert lst
        r = requests.get(f"{API}/ventas/{lst[0]['id']}", headers=sa)
        assert r.status_code == 200
        assert "fel" in r.json()

    def test_detail_404(self, sa):
        r = requests.get(f"{API}/ventas/no-existe-xyz", headers=sa)
        assert r.status_code == 404

    def test_resumen_dia_regression(self, sa):
        r = requests.get(f"{API}/ventas/resumen-dia", headers=sa)
        assert r.status_code == 200


# ---- Monthly report ----
class TestReport:
    def test_excel(self, sa):
        r = requests.get(f"{API}/ventas/reports/monthly", params={"year": 2026, "month": 11, "format": "excel"}, headers=sa)
        assert r.status_code == 200
        assert r.content[:2] == b"PK"
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        assert "Ventas de Clínica" in str(wb.active["A1"].value)

    def test_pdf(self, sa):
        r = requests.get(f"{API}/ventas/reports/monthly", params={"year": 2026, "month": 11, "format": "pdf"}, headers=sa)
        assert r.status_code == 200 and r.content[:4] == b"%PDF"

    def test_invalid(self, sa):
        assert requests.get(f"{API}/ventas/reports/monthly", params={"year": 2026, "month": 13}, headers=sa).status_code == 400
        assert requests.get(f"{API}/ventas/reports/monthly", params={"year": 2026, "month": 11, "format": "csv"}, headers=sa).status_code == 400


# ---- Anular authorization ----
class TestAnular:
    def test_usuario_forbidden(self, usr, mongo):
        vid = _make_test_sale(mongo)
        try:
            r = requests.post(f"{API}/ventas/{vid}/anular", headers=usr, json={"motivo": "TEST motivo", "devolver_inventario": False})
            assert r.status_code == 403
            assert mongo.ventas.find_one({"id": vid})["estado"] == "completada"
        finally:
            mongo.ventas.delete_one({"id": vid})

    def test_motivo_min_length(self, sa, mongo):
        vid = _make_test_sale(mongo)
        try:
            r = requests.post(f"{API}/ventas/{vid}/anular", headers=sa, json={"motivo": "abc", "devolver_inventario": False})
            assert r.status_code == 422
        finally:
            mongo.ventas.delete_one({"id": vid})

    def test_admin_can_anular(self, test_admin, sa, mongo):
        vid = _make_test_sale(mongo)
        try:
            r = requests.post(f"{API}/ventas/{vid}/anular", headers=test_admin, json={"motivo": "TEST anulacion admin", "devolver_inventario": True})
            assert r.status_code == 200, r.text
            g = requests.get(f"{API}/ventas/{vid}", headers=sa).json()
            assert g["estado"] == "anulada" and g["motivo_anulacion"] == "TEST anulacion admin"
            r2 = requests.post(f"{API}/ventas/{vid}/anular", headers=sa, json={"motivo": "TEST again", "devolver_inventario": False})
            assert r2.status_code == 400
        finally:
            mongo.ventas.delete_one({"id": vid})
