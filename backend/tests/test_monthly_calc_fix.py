"""
Tests for monthly calculation fix in:
- GET /api/dashboard/monthly-chart (6 consecutive months)
- GET /api/dashboard/financiero (12 consecutive months in evolucion_mensual)

Verifies:
- Exact count of months
- Consecutive/chronological order (oldest to newest)
- Uniqueness of month names
- Cross-year boundary handling
"""
import os
import requests
import pytest
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def _expected_months(count):
    """Return list of expected 'YYYY-MM' keys from oldest to newest."""
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month
    keys = []
    for i in range(count - 1, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        keys.append(f"{y}-{m:02d}")
    return keys


class TestMonthlyChart:
    """GET /api/dashboard/monthly-chart -> exactly 6 consecutive months"""

    def test_returns_6_months(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/monthly-chart", headers=headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 6, f"Expected 6 months, got {len(data)}: {data}"

    def test_month_names_unique(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/monthly-chart", headers=headers)
        data = r.json()
        names = [d["month"] for d in data]
        assert len(set(names)) == 6, f"Duplicate month names found: {names}"

    def test_months_consecutive_chronological(self, headers):
        """Since MonthlyChartItem only has month name (no year), verify names match
        expected last 6 months in oldest->newest order."""
        r = requests.get(f"{BASE_URL}/api/dashboard/monthly-chart", headers=headers)
        data = r.json()
        expected_keys = _expected_months(6)
        expected_names = [datetime(int(k.split("-")[0]), int(k.split("-")[1]), 1).strftime("%b")
                          for k in expected_keys]
        actual_names = [d["month"] for d in data]
        assert actual_names == expected_names, (
            f"Months not consecutive/ordered. Expected {expected_names}, got {actual_names}"
        )


class TestFinancieroEvolucion:
    """GET /api/dashboard/financiero -> exactly 12 consecutive months in evolucion_mensual"""

    def test_endpoint_ok(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero", headers=headers)
        assert r.status_code == 200, r.text

    def test_returns_12_months(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero", headers=headers)
        evol = r.json()["evolucion_mensual"]
        assert len(evol) == 12, f"Expected 12 months, got {len(evol)}"

    def test_months_are_consecutive_and_chronological(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero", headers=headers)
        evol = r.json()["evolucion_mensual"]
        keys = [e["mes"] for e in evol]
        expected = _expected_months(12)
        assert keys == expected, f"Expected {expected}, got {keys}"

    def test_no_month_skipped(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero", headers=headers)
        evol = r.json()["evolucion_mensual"]
        keys = [e["mes"] for e in evol]
        # Verify each consecutive pair differs by exactly one month
        for a, b in zip(keys, keys[1:]):
            ya, ma = map(int, a.split("-"))
            yb, mb = map(int, b.split("-"))
            diff = (yb - ya) * 12 + (mb - ma)
            assert diff == 1, f"Non-consecutive months detected: {a} -> {b}"

    def test_mes_nombre_unique(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero", headers=headers)
        evol = r.json()["evolucion_mensual"]
        names = [e["mes_nombre"] for e in evol]
        assert len(set(names)) == 12, f"Duplicate mes_nombre found: {names}"

    def test_cross_year_boundary(self, headers):
        """12 months back must cross into previous year (unless current month is Dec).
        Verify at least one month has a different year than the current year."""
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero", headers=headers)
        evol = r.json()["evolucion_mensual"]
        current_year = datetime.now(timezone.utc).year
        years = {e["mes"].split("-")[0] for e in evol}
        # 12-month window necessarily includes at least 2 different years
        assert len(years) >= 2, f"Expected multiple years across 12 months, got {years}"
        assert str(current_year) in years
        assert str(current_year - 1) in years

    def test_fields_present(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero", headers=headers)
        evol = r.json()["evolucion_mensual"]
        for item in evol:
            for f in ("mes", "mes_nombre", "ingresos", "gastos", "balance"):
                assert f in item, f"Missing field {f} in {item}"
