# Tests: Análisis de Producción - Desglose por médico que refiere (medico-detalle + excel)
import io
import os
import pytest
import requests
from openpyxl import load_workbook

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
MEDICO_ID = "a8bb541a-7fcb-49ab-bd20-32788f57acb5"
DESDE, HASTA = "2026-01-01", "2026-12-31"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _login(u, p):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login {u} failed {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin", "nova2024")


def _analisis(sa, desde, hasta):
    r = sa.get(f"{API}/ventas/analisis", params={"periodo": "rango", "desde": desde, "hasta": hasta})
    assert r.status_code == 200
    return r.json()


def _detalle(sa, mid, desde, hasta):
    r = sa.get(f"{API}/ventas/analisis/medico-detalle", params={"medico_id": mid, "desde": desde, "hasta": hasta})
    assert r.status_code == 200, r.text
    return r.json()


# Detalle: totals match main analysis por_medico for every medico in the range
@pytest.mark.parametrize("desde,hasta", [(DESDE, HASTA), ("2026-10-01", "2026-10-31"), ("2026-11-01", "2026-11-30")])
def test_detalle_matches_analisis(sa, desde, hasta):
    a = _analisis(sa, desde, hasta)
    for m in a["por_medico"]:
        d = _detalle(sa, m["medico_id"], desde, hasta)
        assert d["total_monto"] == m["monto"], (m, d["total_monto"])
        assert d["num_ventas"] == m["num_ventas"]
        assert d["medico_nombre"] == m["medico_nombre"]
        assert d["desde"] == desde and d["hasta"] == hasta


def test_detalle_rows_structure(sa):
    d = _detalle(sa, MEDICO_ID, DESDE, HASTA)
    assert d["medico_nombre"] == "Dr. Carlos Méndez"
    assert len(d["items"]) > 0
    for it in d["items"]:
        for k in ("fecha", "numero_venta", "paciente_nombre", "nombre", "cantidad", "monto"):
            assert k in it
    assert d["total_items"] == sum(i["cantidad"] for i in d["items"])
    assert "_id" not in d


def test_detalle_sin_medico(sa):
    d = _detalle(sa, "sin", DESDE, HASTA)
    assert d["medico_nombre"] == "Sin médico"
    assert d["num_ventas"] > 0
    assert len(d["items"]) > 0


def test_detalle_empty_range(sa):
    d = _detalle(sa, MEDICO_ID, "2020-01-01", "2020-01-31")
    assert d["items"] == [] and d["total_monto"] == 0 and d["num_ventas"] == 0


def test_detalle_swapped_dates(sa):
    d = _detalle(sa, MEDICO_ID, HASTA, DESDE)
    assert d["desde"] == DESDE and d["hasta"] == HASTA


def test_detalle_invalid_dates(sa):
    r = sa.get(f"{API}/ventas/analisis/medico-detalle", params={"medico_id": MEDICO_ID, "desde": "abc", "hasta": "xyz"})
    assert r.status_code == 400


def test_detalle_missing_params(sa):
    r = sa.get(f"{API}/ventas/analisis/medico-detalle", params={"medico_id": MEDICO_ID})
    assert r.status_code == 422


def test_detalle_unknown_medico(sa):
    d = _detalle(sa, "no-existe-xyz", DESDE, HASTA)
    assert d["num_ventas"] == 0 and d["items"] == []


@pytest.mark.parametrize("mid", [MEDICO_ID, "sin"])
def test_excel(sa, mid):
    r = sa.get(f"{API}/ventas/analisis/medico-detalle/excel", params={"medico_id": mid, "desde": DESDE, "hasta": HASTA})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(XLSX)
    assert "attachment" in r.headers.get("content-disposition", "")
    wb = load_workbook(io.BytesIO(r.content))
    ws = wb.active
    d = _detalle(sa, mid, DESDE, HASTA)
    # 4 header rows + items + blank + total
    assert ws.max_row == 4 + len(d["items"]) + 2
    assert ws.cell(row=ws.max_row, column=6).value == d["total_monto"]


def test_excel_empty_range(sa):
    r = sa.get(f"{API}/ventas/analisis/medico-detalle/excel", params={"medico_id": MEDICO_ID, "desde": "2020-01-01", "hasta": "2020-01-02"})
    assert r.status_code == 200
    load_workbook(io.BytesIO(r.content))


@pytest.mark.parametrize("u,p", [("admin", "Admin2024$"), ("usuario", "user2024")])
@pytest.mark.parametrize("path", ["/ventas/analisis/medico-detalle", "/ventas/analisis/medico-detalle/excel"])
def test_forbidden_non_superadmin(u, p, path):
    s = _login(u, p)
    r = s.get(f"{API}{path}", params={"medico_id": "sin", "desde": DESDE, "hasta": HASTA})
    assert r.status_code == 403


@pytest.mark.parametrize("path", ["/ventas/analisis/medico-detalle", "/ventas/analisis/medico-detalle/excel"])
def test_unauthenticated(path):
    r = requests.get(f"{API}{path}", params={"medico_id": "sin", "desde": DESDE, "hasta": HASTA})
    assert r.status_code in (401, 403)


def test_analisis_still_works(sa):
    r = sa.get(f"{API}/ventas/analisis", params={"periodo": "mes"})
    assert r.status_code == 200
    j = r.json()
    for k in ("kpis", "top_productos_ingresos", "top_productos_unidades", "por_cajero", "por_medico", "por_categoria", "tendencia"):
        assert k in j
