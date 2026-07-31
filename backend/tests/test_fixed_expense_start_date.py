"""
Tests for start_date field in Fixed Expenses (Gastos Fijos)
Verifies:
- POST /api/fixed-expenses accepts start_date
- GET /api/fixed-expenses returns start_date
- PUT /api/fixed-expenses updates start_date
- generate-now skips fixed expenses whose start_date > today
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SUPERADMIN_CREDS = {"username": "superadmin", "password": "nova2024"}


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERADMIN_CREDS)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def supplier(headers):
    name = f"TEST_SD_Supplier_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{BASE_URL}/api/suppliers",
                      json={"name": name, "contact_name": "T", "phone": "1"},
                      headers=headers)
    assert r.status_code in (200, 201), r.text
    s = r.json()
    yield s
    requests.delete(f"{BASE_URL}/api/suppliers/{s['id']}", headers=headers)


def _cleanup(headers, fe_id):
    try:
        requests.delete(f"{BASE_URL}/api/fixed-expenses/{fe_id}", headers=headers)
    except Exception:
        pass


class TestStartDateField:
    def test_create_accepts_start_date(self, headers, supplier):
        payload = {
            "supplier_id": supplier["id"],
            "expense_name": f"TEST_SD_Create_{uuid.uuid4().hex[:6]}",
            "amount": 1234.5,
            "day_of_month": 15,
            "start_date": "2026-01-15",
        }
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=headers)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert data["start_date"] == "2026-01-15"
        assert data["day_of_month"] == 15
        _cleanup(headers, data["id"])

    def test_get_list_includes_start_date(self, headers, supplier):
        payload = {
            "supplier_id": supplier["id"],
            "expense_name": f"TEST_SD_List_{uuid.uuid4().hex[:6]}",
            "amount": 100,
            "day_of_month": 10,
            "start_date": "2026-03-10",
        }
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=headers)
        assert r.status_code in (200, 201), r.text
        fe_id = r.json()["id"]

        list_r = requests.get(f"{BASE_URL}/api/fixed-expenses", headers=headers)
        assert list_r.status_code == 200
        found = next((x for x in list_r.json()["data"] if x["id"] == fe_id), None)
        assert found is not None
        assert found["start_date"] == "2026-03-10"
        _cleanup(headers, fe_id)

    def test_get_by_id_includes_start_date(self, headers, supplier):
        payload = {
            "supplier_id": supplier["id"],
            "expense_name": f"TEST_SD_ById_{uuid.uuid4().hex[:6]}",
            "amount": 50,
            "day_of_month": 5,
            "start_date": "2026-05-05",
        }
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=headers)
        fe_id = r.json()["id"]
        g = requests.get(f"{BASE_URL}/api/fixed-expenses/{fe_id}", headers=headers)
        assert g.status_code == 200
        assert g.json()["start_date"] == "2026-05-05"
        _cleanup(headers, fe_id)

    def test_update_start_date(self, headers, supplier):
        payload = {
            "supplier_id": supplier["id"],
            "expense_name": f"TEST_SD_Update_{uuid.uuid4().hex[:6]}",
            "amount": 100,
            "day_of_month": 20,
            "start_date": "2026-01-20",
        }
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=headers)
        fe_id = r.json()["id"]
        u = requests.put(f"{BASE_URL}/api/fixed-expenses/{fe_id}",
                         json={"start_date": "2026-07-20"}, headers=headers)
        assert u.status_code == 200
        assert u.json()["start_date"] == "2026-07-20"
        _cleanup(headers, fe_id)

    def test_create_without_start_date_allowed_optional(self, headers, supplier):
        """start_date is Optional in the backend model (frontend enforces required)."""
        payload = {
            "supplier_id": supplier["id"],
            "expense_name": f"TEST_SD_Null_{uuid.uuid4().hex[:6]}",
            "amount": 100,
            "day_of_month": 12,
        }
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=headers)
        assert r.status_code in (200, 201), r.text
        assert r.json().get("start_date") is None
        _cleanup(headers, r.json()["id"])

    def test_generate_now_skips_future_start_date(self, headers, supplier):
        """A fixed expense with day_of_month == today but start_date > today should NOT be generated."""
        today = datetime.utcnow()
        future_date = (today + timedelta(days=90)).strftime("%Y-%m-%d")
        unique = uuid.uuid4().hex[:6]
        payload = {
            "supplier_id": supplier["id"],
            "expense_name": f"TEST_SD_Future_{unique}",
            "amount": 321.0,
            "day_of_month": today.day,
            "start_date": future_date,
        }
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=headers)
        assert r.status_code in (200, 201), r.text
        fe_id = r.json()["id"]

        # Trigger generation
        g = requests.post(f"{BASE_URL}/api/fixed-expenses/generate-now", headers=headers)
        assert g.status_code == 200

        # Verify no expense was created for this fixed expense name
        exp_r = requests.get(
            f"{BASE_URL}/api/expenses?search=TEST_SD_Future_{unique}", headers=headers
        )
        assert exp_r.status_code == 200
        found_names = [e for e in exp_r.json().get("data", []) if unique in e.get("name", "")]
        assert len(found_names) == 0, f"Expense should NOT have been generated but got: {found_names}"
        _cleanup(headers, fe_id)
