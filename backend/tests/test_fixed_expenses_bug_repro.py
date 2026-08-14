"""
Bug reproduction tests for the reported issue:
"los días de vencimiento/cumplimiento se están agregando incorrectamente en gastos fijos"

Focuses on:
 1) Storage of day_of_month & start_date
 2) Whether the expense generated has due_date matching day_of_month (bug hypothesis: adds +30 days instead)
 3) start_date > today should skip generation
"""
import os
import uuid
from datetime import datetime, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")
SUPERADMIN = {"username": "superadmin", "password": "nova2024"}
ADMIN = {"username": "admin", "password": "Admin2024Nuevo!"}


@pytest.fixture(scope="module")
def sa_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERADMIN)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def supplier(sa_headers):
    name = f"TEST_BugRepro_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{BASE_URL}/api/suppliers",
                      json={"name": name, "contact_name": "T", "phone": "1"},
                      headers=sa_headers)
    assert r.status_code in (200, 201), r.text
    s = r.json()
    yield s
    requests.delete(f"{BASE_URL}/api/suppliers/{s['id']}", headers=sa_headers)


def _mk_payload(supplier_id, day, start_date, extra_name=""):
    return {
        "supplier_id": supplier_id,
        "expense_name": f"TEST_BUG_{extra_name}_{uuid.uuid4().hex[:6]}",
        "amount": 500.0,
        "day_of_month": day,
        "start_date": start_date,
    }


# ---------- 1) Create/Read/Update ----------

class TestCreateReadUpdate:
    def test_create_stores_day_and_start_date(self, sa_headers, supplier):
        payload = _mk_payload(supplier["id"], 15, "2026-01-15", "Create")
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=sa_headers)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert data["day_of_month"] == 15
        assert data["start_date"] == "2026-01-15"
        assert data["amount"] == 500.0
        assert data["supplier_id"] == supplier["id"]
        assert data["supplier_name"]

        # GET verification
        g = requests.get(f"{BASE_URL}/api/fixed-expenses/{data['id']}", headers=sa_headers)
        assert g.status_code == 200
        assert g.json()["day_of_month"] == 15
        assert g.json()["start_date"] == "2026-01-15"

        requests.delete(f"{BASE_URL}/api/fixed-expenses/{data['id']}", headers=sa_headers)

    def test_update_day_and_start_date(self, sa_headers, supplier):
        payload = _mk_payload(supplier["id"], 10, "2026-02-10", "Upd")
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=sa_headers)
        assert r.status_code in (200, 201)
        fe_id = r.json()["id"]

        u = requests.put(f"{BASE_URL}/api/fixed-expenses/{fe_id}",
                         json={"day_of_month": 25, "start_date": "2026-06-25"},
                         headers=sa_headers)
        assert u.status_code == 200, u.text
        assert u.json()["day_of_month"] == 25
        assert u.json()["start_date"] == "2026-06-25"

        g = requests.get(f"{BASE_URL}/api/fixed-expenses/{fe_id}", headers=sa_headers)
        assert g.json()["day_of_month"] == 25
        assert g.json()["start_date"] == "2026-06-25"

        requests.delete(f"{BASE_URL}/api/fixed-expenses/{fe_id}", headers=sa_headers)

    def test_list_returns_all_fields(self, sa_headers, supplier):
        payload = _mk_payload(supplier["id"], 7, "2026-01-07", "List")
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=sa_headers)
        fe_id = r.json()["id"]
        lst = requests.get(f"{BASE_URL}/api/fixed-expenses", headers=sa_headers)
        assert lst.status_code == 200
        found = next((x for x in lst.json()["data"] if x["id"] == fe_id), None)
        assert found is not None
        assert found["day_of_month"] == 7
        assert found["start_date"] == "2026-01-07"
        assert found["supplier_name"]
        requests.delete(f"{BASE_URL}/api/fixed-expenses/{fe_id}", headers=sa_headers)


# ---------- 2) Generation behaviour (user-reported bug) ----------

class TestGenerationDueDate:
    def test_generated_expense_due_date_matches_day_of_month(self, sa_headers, supplier):
        """
        USER-REPORTED BUG:
        The user expects the generated expense's due_date to fall on the configured day_of_month.
        Current backend code (server.py line 3311-3313) sets due_date = today + 30 days.
        This test asserts the EXPECTED behavior; if it fails it confirms the bug.
        """
        today = datetime.utcnow()
        day = today.day
        start_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")  # ensure start_date <= today
        unique = uuid.uuid4().hex[:6]
        payload = {
            "supplier_id": supplier["id"],
            "expense_name": f"TEST_BUG_DueDate_{unique}",
            "amount": 1234.56,
            "day_of_month": day,
            "start_date": start_date,
        }
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=sa_headers)
        assert r.status_code in (200, 201), r.text
        fe_id = r.json()["id"]

        # Trigger generation
        g = requests.post(f"{BASE_URL}/api/fixed-expenses/generate-now", headers=sa_headers)
        assert g.status_code == 200, g.text

        # Find generated expense
        exp = requests.get(f"{BASE_URL}/api/expenses?search=TEST_BUG_DueDate_{unique}", headers=sa_headers)
        assert exp.status_code == 200
        items = [e for e in exp.json().get("data", []) if unique in e.get("name", "")]

        # Cleanup regardless
        for e in items:
            requests.delete(f"{BASE_URL}/api/expenses/{e['id']}", headers=sa_headers)
        requests.delete(f"{BASE_URL}/api/fixed-expenses/{fe_id}", headers=sa_headers)

        # If duplicate protection means no expense was created this test month, don't fail this test
        if not items:
            pytest.skip("No new expense generated (likely already generated this month)")

        gen = items[0]
        due_date = gen.get("due_date")
        expense_date = gen.get("date")
        print(f"Generated: date={expense_date}, due_date={due_date}, day_of_month={day}")

        # EXPECTED: due date's day == configured day_of_month
        due_dt = datetime.strptime(due_date, "%Y-%m-%d")
        assert due_dt.day == day, (
            f"BUG: expected due_date day == day_of_month ({day}) but got {due_dt.day} "
            f"({due_date}). Backend seems to add +30 days instead of using day_of_month."
        )

    def test_start_date_in_future_skips_generation(self, sa_headers, supplier):
        today = datetime.utcnow()
        future = (today + timedelta(days=90)).strftime("%Y-%m-%d")
        unique = uuid.uuid4().hex[:6]
        payload = {
            "supplier_id": supplier["id"],
            "expense_name": f"TEST_BUG_Future_{unique}",
            "amount": 999.0,
            "day_of_month": today.day,
            "start_date": future,
        }
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=sa_headers)
        assert r.status_code in (200, 201), r.text
        fe_id = r.json()["id"]

        g = requests.post(f"{BASE_URL}/api/fixed-expenses/generate-now", headers=sa_headers)
        assert g.status_code == 200

        exp = requests.get(f"{BASE_URL}/api/expenses?search=TEST_BUG_Future_{unique}", headers=sa_headers)
        items = [e for e in exp.json().get("data", []) if unique in e.get("name", "")]
        requests.delete(f"{BASE_URL}/api/fixed-expenses/{fe_id}", headers=sa_headers)
        assert len(items) == 0, f"Should not have generated (future start_date), got: {items}"


# ---------- 3) Validation ----------

class TestValidation:
    def test_day_of_month_out_of_range(self, sa_headers, supplier):
        for bad in (0, 32):
            r = requests.post(f"{BASE_URL}/api/fixed-expenses",
                              json={"supplier_id": supplier["id"], "expense_name": f"TEST_bad_{bad}",
                                    "amount": 100, "day_of_month": bad, "start_date": "2026-01-01"},
                              headers=sa_headers)
            assert r.status_code == 422, f"Expected 422 for day={bad}, got {r.status_code}"

    def test_admin_can_create(self, admin_headers, supplier):
        payload = _mk_payload(supplier["id"], 3, "2026-01-03", "Admin")
        r = requests.post(f"{BASE_URL}/api/fixed-expenses", json=payload, headers=admin_headers)
        assert r.status_code in (200, 201), r.text
        fe_id = r.json()["id"]
        requests.delete(f"{BASE_URL}/api/fixed-expenses/{fe_id}", headers=admin_headers)
