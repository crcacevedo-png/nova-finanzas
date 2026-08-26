# Tests for CRUD de Roles (/api/roles)
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

TEST_ROLE_NAME = "test_rol"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module", autouse=True)
def cleanup(headers):
    # Pre-cleanup
    requests.delete(f"{API}/roles/{TEST_ROLE_NAME}", headers=headers)
    yield
    requests.delete(f"{API}/roles/{TEST_ROLE_NAME}", headers=headers)


def test_available_permissions(headers):
    r = requests.get(f"{API}/roles/available-permissions", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "categories" in data
    assert "total_permissions" in data
    assert data["total_permissions"] > 0
    # Check that expected categories exist
    for cat in ["dashboard", "finanzas", "pacientes", "administracion", "optica", "inventario", "proveedores"]:
        assert cat in data["categories"], f"Missing category: {cat}"


def test_get_all_roles(headers):
    r = requests.get(f"{API}/roles/", headers=headers)
    assert r.status_code == 200
    roles = r.json()
    assert isinstance(roles, list)
    names = [role["name"] for role in roles]
    for sys_role in ["superadmin", "admin", "usuario", "optica"]:
        assert sys_role in names, f"Missing system role {sys_role}"
    # Verify structure
    for role in roles:
        assert "name" in role and "display_name" in role and "permissions" in role
        assert "is_system" in role and "user_count" in role and "color" in role


def test_create_role(headers):
    payload = {
        "name": TEST_ROLE_NAME,
        "display_name": "Rol de Prueba",
        "description": "Rol de prueba creado por test suite",
        "color": "green",
        "permissions": {
            "view_dashboard": True,
            "view_patients": True,
            "view_expenses": True,
        }
    }
    r = requests.post(f"{API}/roles/", headers=headers, json=payload)
    assert r.status_code == 200, f"Create failed: {r.status_code} {r.text}"
    data = r.json()
    assert "role" in data
    assert data["role"]["name"] == TEST_ROLE_NAME
    assert data["role"]["color"] == "green"

    # Verify persistence via GET all
    r2 = requests.get(f"{API}/roles/", headers=headers)
    names = [role["name"] for role in r2.json()]
    assert TEST_ROLE_NAME in names


def test_create_role_duplicate_fails(headers):
    payload = {"name": TEST_ROLE_NAME, "display_name": "Duplicate", "permissions": {}}
    r = requests.post(f"{API}/roles/", headers=headers, json=payload)
    assert r.status_code == 400


def test_create_role_system_name_fails(headers):
    payload = {"name": "admin", "display_name": "Fake Admin", "permissions": {}}
    r = requests.post(f"{API}/roles/", headers=headers, json=payload)
    assert r.status_code == 400


def test_get_single_role(headers):
    r = requests.get(f"{API}/roles/{TEST_ROLE_NAME}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == TEST_ROLE_NAME
    assert data["is_system"] is False


def test_update_role_permissions(headers):
    payload = {
        "permissions": {
            "view_dashboard": True,
            "view_patients": True,
            "create_patients": True,
            "view_expenses": False,
        },
        "description": "Actualizada"
    }
    r = requests.put(f"{API}/roles/{TEST_ROLE_NAME}", headers=headers, json=payload)
    assert r.status_code == 200, f"Update failed: {r.text}"

    # Verify persistence
    r2 = requests.get(f"{API}/roles/{TEST_ROLE_NAME}", headers=headers)
    assert r2.status_code == 200
    data = r2.json()
    assert data["permissions"].get("create_patients") is True
    assert data["permissions"].get("view_expenses") is False
    assert data["description"] == "Actualizada"


def test_update_system_role_admin(headers):
    # Get current admin perms
    r = requests.get(f"{API}/roles/admin", headers=headers)
    assert r.status_code == 200
    current_perms = r.json()["permissions"]
    # Toggle one permission
    modified = dict(current_perms)
    modified["view_expenses"] = not modified.get("view_expenses", False)

    r = requests.put(f"{API}/roles/admin", headers=headers, json={"permissions": modified})
    assert r.status_code == 200

    # Verify saved
    r2 = requests.get(f"{API}/roles/admin", headers=headers)
    assert r2.json()["permissions"]["view_expenses"] == modified["view_expenses"]


def test_reset_system_role_permissions(headers):
    r = requests.post(f"{API}/roles/admin/reset-permissions", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "default_permissions" in data


def test_reset_custom_role_fails(headers):
    r = requests.post(f"{API}/roles/{TEST_ROLE_NAME}/reset-permissions", headers=headers)
    assert r.status_code == 400


def test_delete_system_role_fails(headers):
    r = requests.delete(f"{API}/roles/admin", headers=headers)
    assert r.status_code == 400


def test_delete_custom_role(headers):
    r = requests.delete(f"{API}/roles/{TEST_ROLE_NAME}", headers=headers)
    assert r.status_code == 200

    # Verify gone
    r2 = requests.get(f"{API}/roles/{TEST_ROLE_NAME}", headers=headers)
    assert r2.status_code == 404


def test_delete_nonexistent_role(headers):
    r = requests.delete(f"{API}/roles/does_not_exist_xyz", headers=headers)
    assert r.status_code == 404
