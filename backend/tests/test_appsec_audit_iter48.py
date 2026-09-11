"""
AppSec audit E2E tests for NovaVision - Iteration 48
Covers: SEC-002 (Laboratorio Pruebas), SEC-003 (Module authorization),
SEC-004 (Logout blacklist + revoke sessions), Custom Role RBAC.

IMPORTANT: Login rate limit = 5/min. Tokens are cached at module level
and reused across tests to avoid 429 responses.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://novavision-finanzas.preview.emergentagent.com').rstrip('/')

CREDS = {
    "superadmin": ("superadmin", "nova2024"),
    "admin": ("admin", "Admin2024Nuevo!"),
    "optica": ("optica", "optica2024"),
    "usuario": ("usuario", "user2024"),
}

_TOKEN_CACHE = {}


def _login(role):
    """Login and cache token to avoid rate limit."""
    if role in _TOKEN_CACHE:
        return _TOKEN_CACHE[role]
    username, password = CREDS[role]
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password}, timeout=30)
    if r.status_code == 429:
        # Wait and retry once
        time.sleep(62)
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login {role} failed: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data
    _TOKEN_CACHE[role] = data["access_token"]
    return data["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Session-scoped fixtures: pre-warm tokens sequentially with spacing ----------

@pytest.fixture(scope="session", autouse=True)
def prewarm_tokens():
    """Login all needed roles once at start with 13s spacing to stay under 5/min."""
    for role in ["superadmin", "admin", "optica"]:
        _login(role)
        time.sleep(13)  # 3 logins in ~26s well under 5/min
    yield


# ================= Login response validation =================

class TestLoginPermissionsShape:
    def test_superadmin_has_new_perms(self):
        token = _login("superadmin")
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(token), timeout=30)
        assert r.status_code == 200
        me = r.json()
        perms = me.get("permissions", {})
        for key in ["manage_sales", "manage_caja", "view_inventory", "manage_inventory"]:
            assert perms.get(key) is True, f"superadmin should have {key}=True, got {perms.get(key)}"

    def test_admin_has_new_perms(self):
        token = _login("admin")
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(token), timeout=30)
        assert r.status_code == 200
        perms = r.json().get("permissions", {})
        for key in ["manage_sales", "manage_caja", "view_inventory", "manage_inventory"]:
            assert perms.get(key) is True, f"admin should have {key}=True, got {perms.get(key)}"

    def test_optica_lacks_clinical_perms(self):
        token = _login("optica")
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(token), timeout=30)
        assert r.status_code == 200
        perms = r.json().get("permissions", {})
        # optica should NOT have manage_caja/manage_sales for clinical modules
        assert perms.get("manage_caja", False) is False, f"optica should not have manage_caja"
        assert perms.get("manage_sales", False) is False, f"optica should not have manage_sales"


# ================= SEC-002 Laboratorio Pruebas =================

class TestSEC002LaboratorioPruebas:
    def test_estado_no_token(self):
        r = requests.get(f"{BASE_URL}/api/laboratorio-pruebas/estado", timeout=30)
        assert r.status_code in (401, 403), f"Expected 401/403 without token, got {r.status_code}"

    def test_credenciales_no_token(self):
        r = requests.get(f"{BASE_URL}/api/laboratorio-pruebas/credenciales-prueba", timeout=30)
        assert r.status_code in (401, 403)

    def test_purgar_no_token(self):
        r = requests.delete(f"{BASE_URL}/api/laboratorio-pruebas/purgar", timeout=30)
        assert r.status_code in (401, 403)

    def test_estado_optica_forbidden(self):
        token = _login("optica")
        r = requests.get(f"{BASE_URL}/api/laboratorio-pruebas/estado", headers=_h(token), timeout=30)
        assert r.status_code == 403, f"optica should get 403, got {r.status_code}"

    def test_credenciales_optica_forbidden(self):
        token = _login("optica")
        r = requests.get(f"{BASE_URL}/api/laboratorio-pruebas/credenciales-prueba", headers=_h(token), timeout=30)
        assert r.status_code == 403

    def test_estado_superadmin_ok(self):
        token = _login("superadmin")
        r = requests.get(f"{BASE_URL}/api/laboratorio-pruebas/estado", headers=_h(token), timeout=30)
        assert r.status_code == 200, f"superadmin should get 200, got {r.status_code} {r.text[:200]}"

    def test_credenciales_superadmin_ok(self):
        token = _login("superadmin")
        r = requests.get(f"{BASE_URL}/api/laboratorio-pruebas/credenciales-prueba", headers=_h(token), timeout=30)
        assert r.status_code == 200


# ================= SEC-003 Module authorization =================

class TestSEC003ModuleAuth:
    def test_optica_denied_inventario(self):
        token = _login("optica")
        r = requests.get(f"{BASE_URL}/api/inventario/productos", headers=_h(token), timeout=30)
        assert r.status_code == 403, f"optica denied inventario expected 403, got {r.status_code}"

    def test_optica_denied_ventas_productos(self):
        token = _login("optica")
        r = requests.get(f"{BASE_URL}/api/ventas/productos", headers=_h(token), timeout=30)
        assert r.status_code == 403

    def test_optica_denied_caja(self):
        token = _login("optica")
        r = requests.get(f"{BASE_URL}/api/caja/estado", headers=_h(token), timeout=30)
        assert r.status_code == 403

    def test_optica_denied_post_ventas(self):
        token = _login("optica")
        r = requests.post(f"{BASE_URL}/api/ventas", headers=_h(token), json={"items": []}, timeout=30)
        assert r.status_code == 403, f"optica POST /api/ventas expected 403, got {r.status_code}"

    def test_superadmin_allowed_inventario(self):
        token = _login("superadmin")
        r = requests.get(f"{BASE_URL}/api/inventario/productos", headers=_h(token), timeout=30)
        assert r.status_code == 200

    def test_superadmin_allowed_ventas(self):
        token = _login("superadmin")
        r = requests.get(f"{BASE_URL}/api/ventas/productos", headers=_h(token), timeout=30)
        assert r.status_code == 200

    def test_superadmin_allowed_caja(self):
        token = _login("superadmin")
        r = requests.get(f"{BASE_URL}/api/caja/estado", headers=_h(token), timeout=30)
        assert r.status_code == 200

    def test_admin_allowed_inventario(self):
        token = _login("admin")
        r = requests.get(f"{BASE_URL}/api/inventario/productos", headers=_h(token), timeout=30)
        assert r.status_code == 200

    def test_admin_allowed_ventas(self):
        token = _login("admin")
        r = requests.get(f"{BASE_URL}/api/ventas/productos", headers=_h(token), timeout=30)
        assert r.status_code == 200

    def test_admin_allowed_caja(self):
        token = _login("admin")
        r = requests.get(f"{BASE_URL}/api/caja/estado", headers=_h(token), timeout=30)
        assert r.status_code == 200


# ================= SEC-004 Logout blacklist unified =================

class TestSEC004LogoutBlacklist:
    def test_logout_blacklists_token_across_routers(self):
        # Wait to avoid rate limit before this dedicated login
        time.sleep(62)
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": "admin", "password": "Admin2024Nuevo!"}, timeout=30)
        assert r.status_code == 200, f"login failed: {r.status_code}"
        token = r.json()["access_token"]

        # Verify token works on both endpoints
        assert requests.get(f"{BASE_URL}/api/auth/me", headers=_h(token), timeout=30).status_code == 200
        assert requests.get(f"{BASE_URL}/api/caja/estado", headers=_h(token), timeout=30).status_code == 200

        # Logout
        r = requests.post(f"{BASE_URL}/api/auth/logout", headers=_h(token), timeout=30)
        assert r.status_code in (200, 204), f"logout failed: {r.status_code}"

        # Both endpoints must now reject
        r1 = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(token), timeout=30)
        r2 = requests.get(f"{BASE_URL}/api/caja/estado", headers=_h(token), timeout=30)
        assert r1.status_code == 401, f"/api/auth/me after logout expected 401, got {r1.status_code}"
        assert r2.status_code == 401, f"/api/caja/estado after logout expected 401, got {r2.status_code}"


# ================= SEC-004 Revoke sessions (token_version) =================

class TestSEC004RevokeSessions:
    def test_revoke_my_sessions_invalidates_token(self):
        # Wait to avoid rate limit
        time.sleep(62)
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": "admin", "password": "Admin2024Nuevo!"}, timeout=30)
        assert r.status_code == 200
        token = r.json()["access_token"]

        # Verify token works
        assert requests.get(f"{BASE_URL}/api/auth/me", headers=_h(token), timeout=30).status_code == 200

        # Revoke
        r = requests.post(f"{BASE_URL}/api/security/revoke-my-sessions", headers=_h(token), timeout=30)
        assert r.status_code in (200, 204), f"revoke failed: {r.status_code} {r.text[:200]}"

        # Old token rejected
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(token), timeout=30)
        assert r.status_code == 401, f"old token should be 401, got {r.status_code}"

        # Fresh login works
        time.sleep(62)
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": "admin", "password": "Admin2024Nuevo!"}, timeout=30)
        assert r.status_code == 200
        new_token = r.json()["access_token"]
        # Refresh cached admin token to keep suite consistent
        _TOKEN_CACHE["admin"] = new_token
        assert requests.get(f"{BASE_URL}/api/auth/me", headers=_h(new_token), timeout=30).status_code == 200


# ================= Custom role RBAC =================

class TestCustomRoleRBAC:
    ROLE_NAME = f"test_qa_role_iter48_v2"
    USER_NAME = "TEST_qa_user_iter48_v2"
    USER_PASS = "TestQa2024!"
    _created_role_id = None
    _created_user_id = None

    def test_create_custom_role_and_user(self):
        admin = _login("superadmin")

        # Pre-cleanup: delete role if leftover from previous run
        requests.delete(f"{BASE_URL}/api/roles/{self.__class__.ROLE_NAME}", headers=_h(admin), timeout=30)

        # Create custom role with view_inventory only
        payload = {
            "name": self.__class__.ROLE_NAME,
            "display_name": "QA Iter48",
            "description": "Test role for RBAC",
            "permissions": {"view_inventory": True, "manage_caja": False},
        }
        r = requests.post(f"{BASE_URL}/api/roles/", headers=_h(admin), json=payload, timeout=30)
        assert r.status_code in (200, 201), f"create role failed: {r.status_code} {r.text[:300]}"
        role_data = r.json()
        self.__class__._created_role_id = role_data.get("id") or role_data.get("_id") or self.__class__.ROLE_NAME

        # Create user with that role
        # Create user with valid built-in role first, then update to custom role
        # (UserCreate schema restricts role to built-ins; UserUpdate allows any)
        upayload = {
            "username": self.__class__.USER_NAME,
            "password": self.__class__.USER_PASS,
            "role": "usuario",
            "name": "QA Iter48 User",
            "full_name": "QA Iter48 User",
            "email": "qa_iter48@test.local",
        }
        r = requests.post(f"{BASE_URL}/api/users", headers=_h(admin), json=upayload, timeout=30)
        assert r.status_code in (200, 201), f"create user failed: {r.status_code} {r.text[:300]}"
        udata = r.json()
        self.__class__._created_user_id = udata.get("id") or udata.get("_id") or udata.get("user", {}).get("id")
        # Now update to assign custom role
        assert self.__class__._created_user_id, "no user id returned"
        r = requests.put(f"{BASE_URL}/api/users/{self.__class__._created_user_id}",
                         headers=_h(admin), json={"role": self.__class__.ROLE_NAME}, timeout=30)
        assert r.status_code in (200, 201), f"assign custom role failed: {r.status_code} {r.text[:300]}"

    def test_custom_role_permissions(self):
        # Wait to avoid rate limit
        time.sleep(62)
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": self.__class__.USER_NAME, "password": self.__class__.USER_PASS},
                          timeout=30)
        assert r.status_code == 200, f"custom user login failed: {r.status_code} {r.text[:200]}"
        token = r.json()["access_token"]

        # Should be able to GET inventario/productos
        r = requests.get(f"{BASE_URL}/api/inventario/productos", headers=_h(token), timeout=30)
        assert r.status_code == 200, f"expected 200 on inventario, got {r.status_code}"

        # Should NOT be able to GET caja/estado
        r = requests.get(f"{BASE_URL}/api/caja/estado", headers=_h(token), timeout=30)
        assert r.status_code == 403, f"expected 403 on caja, got {r.status_code}"

    def test_zzz_cleanup(self):
        """Cleanup created role and user."""
        admin = _login("superadmin")
        if self.__class__._created_user_id:
            r = requests.delete(f"{BASE_URL}/api/users/{self.__class__._created_user_id}",
                                headers=_h(admin), timeout=30)
            print(f"delete user status: {r.status_code}")
        if self.__class__._created_role_id:
            # Try delete by role name (route may accept name)
            r = requests.delete(f"{BASE_URL}/api/roles/{self.__class__.ROLE_NAME}",
                                headers=_h(admin), timeout=30)
            print(f"delete role status: {r.status_code}")
