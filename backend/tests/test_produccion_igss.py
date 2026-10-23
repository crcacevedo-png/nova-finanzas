# Producción IGSS module tests: listing, totals, PATCH estados/costo, Excel export, role access
import os
import io
import pytest
import requests

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
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def rows(sa):
    r = sa.get(API, params=RANGE)
    assert r.status_code == 200
    return r.json()["data"]


@pytest.fixture(scope="module")
def target(sa, rows):
    if not rows:
        pytest.skip("no rows in 2026")
    row = rows[0]
    yield row
    # restore original state
    restore = {k: row[k] for k in ["impreso", "enviado", "facturado", "pagado"]}
    sa.patch(f"{API}/{row['evaluacion_id']}", json=restore)


# Listing & totals
class TestListado:
    def test_list_structure(self, sa, rows):
        r = sa.get(API, params=RANGE).json()
        assert "totales" in r and r["totales"]["servicios"] == len(rows)
        assert len(rows) >= 1
        for k in ["evaluacion_id", "paciente_id", "paciente_nombre", "unidad_nombre", "nog", "costo", "impreso", "pagado"]:
            assert k in rows[0]
        assert abs(r["totales"]["total_costo"] - sum(x["costo"] for x in rows)) < 0.01

    def test_default_today(self, sa):
        r = sa.get(API)
        assert r.status_code == 200
        assert r.json()["filtro"]["fecha"]

    def test_filter_nog(self, sa, rows):
        nog = next((x["nog"] for x in rows if x["nog"]), None)
        if not nog:
            pytest.skip("no nog")
        r = sa.get(API, params={**RANGE, "nog": nog}).json()
        assert r["data"] and all(x["nog"] == nog for x in r["data"])
        r2 = sa.get(API, params={**RANGE, "nog": "00000000999"}).json()
        assert r2["data"] == []

    def test_filter_unidad(self, sa, rows):
        uid = next((x["unidad_id"] for x in rows if x["unidad_id"]), None)
        if not uid:
            pytest.skip("no unidad")
        r = sa.get(API, params={**RANGE, "unidad_id": uid}).json()
        assert r["data"] and all(x["unidad_id"] == uid for x in r["data"])


# PATCH estados and costo
class TestPatch:
    def test_toggle_pagado_updates_totals(self, sa, target):
        eid = target["evaluacion_id"]
        before = sa.get(API, params=RANGE).json()["totales"]
        new_val = not target["pagado"]
        r = sa.patch(f"{API}/{eid}", json={"pagado": new_val})
        assert r.status_code == 200 and r.json()["pagado"] is new_val
        after = sa.get(API, params=RANGE).json()
        row = next(x for x in after["data"] if x["evaluacion_id"] == eid)
        assert row["pagado"] is new_val
        delta = row["costo"] if new_val else -row["costo"]
        assert abs(after["totales"]["total_pagado"] - (before["total_pagado"] + delta)) < 0.01
        sa.patch(f"{API}/{eid}", json={"pagado": target["pagado"]})

    def test_costo_override(self, sa, target):
        eid = target["evaluacion_id"]
        r = sa.patch(f"{API}/{eid}", json={"costo_override": 123.45})
        assert r.status_code == 200
        row = next(x for x in sa.get(API, params=RANGE).json()["data"] if x["evaluacion_id"] == eid)
        assert row["costo"] == 123.45 and row["costo_editado"] is True

    def test_patch_404(self, sa):
        r = sa.patch(f"{API}/nonexistent-id", json={"pagado": True})
        assert r.status_code == 404

    def test_patch_empty_400(self, sa, target):
        r = sa.patch(f"{API}/{target['evaluacion_id']}", json={})
        assert r.status_code == 400

    def test_negative_cost_rejected(self, sa, target):
        r = sa.patch(f"{API}/{target['evaluacion_id']}", json={"costo_override": -50})
        # restore
        sa.patch(f"{API}/{target['evaluacion_id']}", json={"costo_override": 123.45})
        assert r.status_code in (400, 422), f"negative cost accepted: {r.status_code}"


# Excel export
class TestExcel:
    def test_excel(self, sa):
        r = sa.get(f"{API}/reporte/excel", params=RANGE)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        assert wb.active["A1"].value == "Fecha"


# Role access
class TestAccess:
    def test_medico_403(self):
        s = _login("medico_test", "medico2024")
        assert s.get(API, params=RANGE).status_code == 403
        assert s.get(f"{API}/reporte/excel", params=RANGE).status_code == 403
        assert s.patch(f"{API}/x", json={"pagado": True}).status_code == 403

    def test_igss_admin_allowed(self):
        s = _login("igss.admin", "IgssAdmin2024$")
        assert s.get(API, params=RANGE).status_code == 200

    def test_unauth(self):
        assert requests.get(API, params=RANGE).status_code in (401, 403)
