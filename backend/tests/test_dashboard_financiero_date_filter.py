"""
Verifies Dashboard Financiero (SuperAdmin) does NOT have the same date-format bug
as previously fixed in /api/dashboard/stats.

Focus: gastos.total must match the sum of expenses within the requested date range,
and be consistent with /api/dashboard/stats.total_gastos for the current month.
"""
import os
from datetime import datetime, timezone, date
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def sa():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


def _cm_bounds():
    now = datetime.now(timezone.utc)
    return date(now.year, now.month, 1).isoformat(), date(now.year, now.month, now.day).isoformat()


def _sum_expenses_in_range(expenses, start, end):
    # /api/expenses returns {data: [...], total, page, ...}
    if isinstance(expenses, dict):
        expenses = expenses.get("data", [])
    return round(sum(e.get("amount", 0) for e in expenses
                     if isinstance(e.get("date"), str)
                     and start <= e["date"][:10] <= end), 2)


def _fetch_all_expenses(sa):
    """Fetch all expenses via paginated /api/expenses (limit large)."""
    r = sa.get(f"{BASE_URL}/api/expenses?limit=100", timeout=30).json()
    if isinstance(r, dict):
        return r.get("data", [])
    return r


def test_mes_actual_gastos_total_matches_expenses(sa):
    start, end = _cm_bounds()
    all_exp = _fetch_all_expenses(sa)
    expected = _sum_expenses_in_range(all_exp, start, end)

    r = sa.get(f"{BASE_URL}/api/dashboard/financiero?periodo=mes_actual", timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    got = round(d["gastos"]["total"], 2)
    print(f"[mes_actual] range={start}..{end} expected_total={expected} got={got}")
    assert d["periodo"]["fecha_inicio"] == start
    assert d["periodo"]["fecha_fin"] == end
    assert got == expected, f"gastos.total mismatch: {got} != {expected}"


def test_dashboard_stats_and_financiero_consistent(sa):
    r_fin = sa.get(f"{BASE_URL}/api/dashboard/financiero?periodo=mes_actual", timeout=60)
    r_st = sa.get(f"{BASE_URL}/api/dashboard/stats", timeout=30)
    assert r_fin.status_code == 200 and r_st.status_code == 200
    fin = round(r_fin.json()["gastos"]["total"], 2)
    st = round(r_st.json().get("total_gastos", 0), 2)
    print(f"[consistency] financiero={fin} stats={st}")
    assert fin == st, f"financiero.gastos.total ({fin}) != stats.total_gastos ({st})"


def test_dashboard_stats_positive_when_month_has_expenses(sa):
    start, end = _cm_bounds()
    all_exp = _fetch_all_expenses(sa)
    expected = _sum_expenses_in_range(all_exp, start, end)
    if expected <= 0:
        pytest.skip("No expenses in current month to validate")
    total = sa.get(f"{BASE_URL}/api/dashboard/stats", timeout=30).json().get("total_gastos", 0)
    assert total > 0, "total_gastos returned 0 while expenses exist (date-filter bug)"


def test_semestre_period(sa):
    r = sa.get(f"{BASE_URL}/api/dashboard/financiero?periodo=semestre", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert d["periodo"]["nombre"] == "Últimos 6 meses"
    # semester total must be >= current month total (superset range)
    r_m = sa.get(f"{BASE_URL}/api/dashboard/financiero?periodo=mes_actual", timeout=60).json()
    assert d["gastos"]["total"] >= r_m["gastos"]["total"] - 0.01


def test_anual_period(sa):
    now = datetime.now(timezone.utc)
    r = sa.get(f"{BASE_URL}/api/dashboard/financiero?periodo=anual", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert d["periodo"]["fecha_inicio"] == date(now.year, 1, 1).isoformat()
    # annual gastos should match sum of expenses in year-to-date
    all_exp = _fetch_all_expenses(sa)
    expected = _sum_expenses_in_range(all_exp, d["periodo"]["fecha_inicio"], d["periodo"]["fecha_fin"])
    got = round(d["gastos"]["total"], 2)
    print(f"[anual] expected={expected} got={got}")
    assert got == expected


def test_personalizado_aug_2026(sa):
    fi, ff = "2026-08-01", "2026-08-31"
    r = sa.get(
        f"{BASE_URL}/api/dashboard/financiero?periodo=personalizado&fecha_inicio={fi}&fecha_fin={ff}",
        timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["periodo"]["fecha_inicio"] == fi
    assert d["periodo"]["fecha_fin"] == ff
    all_exp = _fetch_all_expenses(sa)
    expected = _sum_expenses_in_range(all_exp, fi, ff)
    got = round(d["gastos"]["total"], 2)
    print(f"[aug2026] expected={expected} got={got}")
    assert got == expected


def test_personalizado_full_year(sa):
    now = datetime.now(timezone.utc)
    fi = date(now.year, 1, 1).isoformat()
    ff = date(now.year, 12, 31).isoformat()
    r = sa.get(
        f"{BASE_URL}/api/dashboard/financiero?periodo=personalizado&fecha_inicio={fi}&fecha_fin={ff}",
        timeout=60)
    assert r.status_code == 200
    d = r.json()
    all_exp = _fetch_all_expenses(sa)
    expected = _sum_expenses_in_range(all_exp, fi, ff)
    got = round(d["gastos"]["total"], 2)
    assert got == expected


def test_evolucion_mensual_current_month_matches(sa):
    """Last evolution entry (current month) should match gastos.pagado of mes_actual view."""
    r = sa.get(f"{BASE_URL}/api/dashboard/financiero?periodo=mes_actual", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert len(d["evolucion_mensual"]) == 12
    last = d["evolucion_mensual"][-1]
    now = datetime.now(timezone.utc)
    assert last["mes"] == f"{now.year:04d}-{now.month:02d}"
    # gastos in evolution = paid_amount (see route). Compare with d.gastos.pagado.
    assert round(last["gastos"], 2) == round(d["gastos"]["pagado"], 2)
