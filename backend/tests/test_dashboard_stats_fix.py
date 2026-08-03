"""Regression tests: Dashboard stats/summary/chart-data must reflect real expense data.

Bug context (iter 27): Filters used isoformat() which produced dates like
'2026-08-01T00:00:00+00:00' while expenses.date is stored as 'YYYY-MM-DD',
so the $gte comparison excluded all rows and dashboard showed Q 0.00 in every field.
Fix: use strftime('%Y-%m-%d') for month_start.
"""
import os
from datetime import datetime, timezone
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://novavision-finanzas.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def _month_start_str():
    return datetime.now(timezone.utc).replace(day=1).strftime("%Y-%m-%d")


def test_expenses_list_ok(headers):
    r = requests.get(f"{API}/expenses", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    # Support both list and paginated envelope
    items = data if isinstance(data, list) else (data.get("data") or data.get("items") or [])
    assert isinstance(items, list)
    print(f"[expenses] total items returned: {len(items)}")


def test_dashboard_stats_returns_numbers(headers):
    r = requests.get(f"{API}/dashboard/stats", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    stats = r.json()
    required = [
        "total_gastos", "gastos_pendientes", "gastos_pagados",
        "gastos_parciales", "gastos_vencidos",
        "total_fijos", "total_proveedores", "total_variables",
        "alertas_30_dias", "alertas_60_dias",
    ]
    for k in required:
        assert k in stats, f"Missing key {k} in stats"
        assert isinstance(stats[k], (int, float)), f"{k} is not numeric: {stats[k]}"
    print(f"[stats] {stats}")


def test_dashboard_stats_matches_current_month_expenses(headers):
    """Core bug: total_gastos must equal sum(amount) of expenses with date >= YYYY-MM-01 (current month)."""
    month_start = _month_start_str()

    r_exp = requests.get(f"{API}/expenses", headers=headers, timeout=30)
    assert r_exp.status_code == 200
    payload = r_exp.json()
    all_expenses = payload if isinstance(payload, list) else (payload.get("data") or payload.get("items") or [])

    # Filter to current month by string comparison (dates are stored YYYY-MM-DD)
    current = [e for e in all_expenses if isinstance(e.get("date"), str) and e["date"] >= month_start]
    expected_total = round(sum(float(e.get("amount", 0)) for e in current), 2)
    expected_paid = round(sum(float(e.get("paid_amount", 0)) for e in current), 2)

    r = requests.get(f"{API}/dashboard/stats", headers=headers, timeout=30)
    assert r.status_code == 200
    stats = r.json()
    actual_total = round(float(stats["total_gastos"]), 2)
    actual_paid = round(float(stats["gastos_pagados"]), 2)

    print(f"[compare] month_start={month_start} expenses_in_month={len(current)} "
          f"expected_total={expected_total} actual_total={actual_total} "
          f"expected_paid={expected_paid} actual_paid={actual_paid}")

    assert actual_total == expected_total, (
        f"total_gastos mismatch: dashboard={actual_total} vs sum(expenses.amount for current month)={expected_total}. "
        f"If both are 0 but there are month expenses, the date filter is still broken."
    )
    assert actual_paid == expected_paid, f"gastos_pagados mismatch: {actual_paid} vs {expected_paid}"

    # If there are month expenses at all, total should be > 0 (validates bug fix)
    if len(current) > 0:
        assert actual_total > 0, (
            "BUG REGRESSION: current-month expenses exist but dashboard/stats.total_gastos is 0. "
            "Date filter format likely broken again."
        )


def test_dashboard_chart_data(headers):
    r = requests.get(f"{API}/dashboard/chart-data", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    for item in data:
        assert "mes" in item
        for k in ("fijo", "proveedor", "variable"):
            assert k in item
            assert isinstance(item[k], (int, float))
    print(f"[chart-data] months returned: {len(data)}")


def test_dashboard_summary(headers):
    r = requests.get(f"{API}/dashboard/summary", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ("total_month", "total_paid", "total_pending", "overdue_count", "by_type"):
        assert k in data, f"Missing key {k}"
    print(f"[summary] total_month={data['total_month']} paid={data['total_paid']} pending={data['total_pending']}")
