# Producción IGSS (Fase 3 del Libro IGSS): una fila por ORDEN atendida, estados y costo en la
# orden del libro, Excel y acceso por rol. El detalle con datos sembrados está en test_igss_libro.py.
import os
import io
import pytest
import requests
from usuarios_prueba import par  # usuarios sembrados solo para pruebas

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api/igss-units/produccion"
RANGE = {"desde": "2026-01-01", "hasta": "2026-12-31"}


def _login(u, p):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login failed {u}: {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token") or r.json().get("token")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def sa():
    return _login(*par("superadmin"))


class TestListado:
    def test_list_structure(self, sa):
        r = sa.get(API, params=RANGE).json()
        rows = r["data"]
        assert r["totales"]["servicios"] == len(rows)
        assert abs(r["totales"]["total_costo"] - sum(x["costo"] for x in rows)) < 0.01
        for x in rows:
            assert x["estado"] == "atendida" and x["orden_id"]
            assert len({y["orden_id"] for y in rows}) == len(rows)

    def test_default_today(self, sa):
        r = sa.get(API)
        assert r.status_code == 200
        assert r.json()["filtro"]["fecha"]

    def test_filter_nog_sin_coincidencias(self, sa):
        assert sa.get(API, params={**RANGE, "nog": "00000000999"}).json()["data"] == []

    def test_fecha_invalida_422(self, sa):
        assert sa.get(API, params={"fecha": "16-11-2026"}).status_code == 422

    def test_patch_legado_eliminado(self, sa):
        assert sa.patch(f"{API}/x", json={"pagado": True}).status_code in (404, 405)


class TestExcel:
    def test_excel(self, sa):
        r = sa.get(f"{API}/reporte/excel", params=RANGE)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        assert wb.active["A1"].value == "Fecha 1ª atención"


class TestAccess:
    def test_medico_403(self):
        s = _login(*par("medico"))
        assert s.get(API, params=RANGE).status_code == 403
        assert s.get(f"{API}/reporte/excel", params=RANGE).status_code == 403

    def test_igss_admin_allowed(self):
        s = _login(*par("igss"))
        assert s.get(API, params=RANGE).status_code == 200

    def test_unauth(self):
        assert requests.get(API, params=RANGE).status_code in (401, 403)
