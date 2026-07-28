"""Tests for the Audit Log module - superadmin-only endpoints."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")

SUPERADMIN = {"username": "superadmin", "password": "nova2024"}
ADMIN = {"username": "admin", "password": "Admin2024Nuevo!"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['username']}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def superadmin_token():
    return _login(SUPERADMIN)


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


# ---------- GET /api/security/audit-logs ----------

class TestAuditLogs:
    def test_superadmin_can_list_audit_logs(self, superadmin_token):
        r = requests.get(
            f"{BASE_URL}/api/security/audit-logs",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # Structure check
        for k in ("data", "total", "page", "total_pages"):
            assert k in data, f"Missing '{k}' in response: {list(data.keys())}"
        assert isinstance(data["data"], list)
        assert isinstance(data["total"], int)
        assert data["page"] == 1
        assert data["total_pages"] >= 1
        # Ensure no mongo _id leaks
        for entry in data["data"]:
            assert "_id" not in entry

    def test_admin_cannot_list_audit_logs(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/security/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}: {r.text}"

    def test_no_auth_returns_401_or_403(self):
        r = requests.get(f"{BASE_URL}/api/security/audit-logs", timeout=30)
        assert r.status_code in (401, 403)

    def test_pagination_params(self, superadmin_token):
        r = requests.get(
            f"{BASE_URL}/api/security/audit-logs?page=1&limit=5",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["data"]) <= 5
        assert data["page"] == 1

    def test_filter_by_action(self, superadmin_token):
        # Generate a LOGIN_SUCCESS entry
        _login(SUPERADMIN)
        r = requests.get(
            f"{BASE_URL}/api/security/audit-logs?action=LOGIN_SUCCESS&limit=10",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        for entry in data["data"]:
            assert entry.get("action") == "LOGIN_SUCCESS"

    def test_filter_by_date_from(self, superadmin_token):
        r = requests.get(
            f"{BASE_URL}/api/security/audit-logs?date_from=2020-01-01",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            timeout=30,
        )
        assert r.status_code == 200

    def test_search_filter(self, superadmin_token):
        r = requests.get(
            f"{BASE_URL}/api/security/audit-logs?search=LOGIN",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            timeout=30,
        )
        assert r.status_code == 200


# ---------- GET /api/security/audit-actions ----------

class TestAuditActions:
    def test_superadmin_can_list_actions(self, superadmin_token):
        r = requests.get(
            f"{BASE_URL}/api/security/audit-actions",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert "actions" in data
        assert isinstance(data["actions"], list)

    def test_admin_cannot_list_actions(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/security/audit-actions",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code in (401, 403)


# ---------- GET /api/security/status ----------

class TestSecurityStatus:
    def test_superadmin_can_get_status(self, superadmin_token):
        r = requests.get(
            f"{BASE_URL}/api/security/status",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        for k in ("blacklisted_tokens", "failed_logins_24h", "active_users"):
            assert k in data, f"Missing key '{k}'"
            assert isinstance(data[k], int)

    def test_admin_cannot_get_status(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/security/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code in (401, 403)
