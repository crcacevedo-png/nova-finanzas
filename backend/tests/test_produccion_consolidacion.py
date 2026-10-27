# Producción IGSS consolidation tests: one row per patient+No.SPS, totals consistency, state toggle, Excel
import os
import io
import pytest
import requests
from collections import Counter

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api/igss-units/produccion"
OCT = {"desde": "2026-10-01", "hasta": "2026-10-31"}
# Group with several evals on same order (SPS-110): representative + non-representative member
REP_ID = "a0c71e69-9e39-4a43-a5a9-d4900ba1d333"
MEMBER_ID = "7f68a258-5206-49cb-b530-fd09bac8f088"


@pytest.fixture(scope="module")
def sa():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"})
    if r.status_code != 200:
        pytest.skip("login failed")
    tok = r.json().get("access_token") or r.json().get("token")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def data(sa):
    r = sa.get(API, params=OCT)
    assert r.status_code == 200
    return r.json()


# Consolidation / no duplicates
class TestConsolidacion:
    def test_rows_equal_servicios(self, data):
        assert data["totales"]["servicios"] == len(data["data"]) > 0

    def test_no_dup_patient_sps(self, data):
        c = Counter((r["paciente_id"], r["no_sps"]) for r in data["data"] if r["no_sps"])
        assert [k for k, v in c.items() if v > 1] == []

    def test_unique_eval_ids(self, data):
        ids = [r["evaluacion_id"] for r in data["data"]]
        assert len(ids) == len(set(ids))

    def test_por_nog_sum_equals_total(self, data):
        t = data["totales"]
        assert abs(sum(n["monto"] for n in t["por_nog"]) - t["total_costo"]) < 0.01
        assert sum(n["cantidad"] for n in t["por_nog"]) == t["servicios"]

    def test_pagado_pendiente(self, data):
        t = data["totales"]
        assert abs(t["total_pagado"] + t["total_pendiente"] - t["total_costo"]) < 0.01

    def test_member_eval_not_listed(self, data):
        ids = {r["evaluacion_id"] for r in data["data"]}
        assert MEMBER_ID not in ids


# Toggle state on consolidated row
class TestEstado:
    def test_toggle_facturado_persists(self, sa, data):
        row = data["data"][0]
        orig = row["facturado"]
        before = data["totales"]["por_estado"]["facturado"]["cantidad"]
        r = sa.patch(f"{API}/{row['evaluacion_id']}", json={"facturado": not orig})
        assert r.status_code == 200
        d2 = sa.get(API, params=OCT).json()
        row2 = next(x for x in d2["data"] if x["evaluacion_id"] == row["evaluacion_id"])
        assert row2["facturado"] == (not orig)
        assert d2["totales"]["por_estado"]["facturado"]["cantidad"] == before + (1 if not orig else -1)
        sa.patch(f"{API}/{row['evaluacion_id']}", json={"facturado": orig})

    def test_uncheck_when_state_on_member_eval(self, sa):
        """If a non-representative eval in the group has pagado=true (e.g. marked before
        consolidation), unchecking on the consolidated row must clear it."""
        sa.patch(f"{API}/{MEMBER_ID}", json={"pagado": True})
        try:
            d = sa.get(API, params=OCT).json()
            row = next(x for x in d["data"] if x["evaluacion_id"] == REP_ID)
            assert row["pagado"] is True
            sa.patch(f"{API}/{REP_ID}", json={"pagado": False})
            d2 = sa.get(API, params=OCT).json()
            row2 = next(x for x in d2["data"] if x["evaluacion_id"] == REP_ID)
            assert row2["pagado"] is False, "pagado sticky: cannot uncheck consolidated row"
        finally:
            sa.patch(f"{API}/{MEMBER_ID}", json={"pagado": False})
            sa.patch(f"{API}/{REP_ID}", json={"pagado": False})


# Excel export
class TestExcel:
    def test_excel(self, sa, data):
        r = sa.get(f"{API}/reporte/excel", params=OCT)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        ws = wb.active
        detail = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or row[0] in (None, "TOTALES"):
                break
            detail += 1
        assert detail == data["totales"]["servicios"]
