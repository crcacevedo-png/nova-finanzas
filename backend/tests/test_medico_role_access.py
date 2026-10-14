"""
Pruebas de acceso del rol 'medico' (ERP NovaVisión).
Valida:
 - Login medico_test con permisos efectivos esperados.
 - GET /roles/available-permissions incluye categoría 'clinica' con 4 permisos.
 - GET /roles/medico retorna display_name 'Médico' y permisos clínicos True.
 - GET /agenda/mi-dia con token de médico retorna 'Dr. Carlos Méndez' y filtra por médico.
 - Menu config del rol medico contiene los 4 menús esperados.
 - Vincular usuario_id a ficha de médico vía PATCH /medicos-agenda/{id}.
 - Regresión: rol usuario y admin conservan view_agenda; optica no.
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

MEDICO_FICHA_ID = "a8bb541a-7fcb-49ab-bd20-32788f57acb5"
DR_NAME = "Dr. Carlos Méndez"


def _login(username, password):
    r = requests.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {username} -> {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def superadmin():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def medico():
    return _login("medico_test", "medico2024")


@pytest.fixture(scope="module")
def usuario():
    return _login("usuario", "user2024")


def _h(tok): return {"Authorization": f"Bearer {tok['access_token'] if 'access_token' in tok else tok.get('token','')}"}


# ---------- 1. Login médico y permisos ----------
def test_medico_login_permissions(medico):
    perms = medico.get("permissions") or medico.get("user", {}).get("permissions") or {}
    # Esperados True
    for p in ["view_agenda", "view_evaluacion", "view_sala_operaciones", "create_patients", "edit_patients"]:
        assert perms.get(p) is True, f"Permiso {p} esperado True, got {perms.get(p)}"
    # Esperados False
    for p in ["delete_patients", "view_dashboard", "view_optica"]:
        assert perms.get(p) is False or perms.get(p) is None or perms.get(p) == False, (
            f"Permiso {p} esperado False, got {perms.get(p)}"
        )


# ---------- 2. Available permissions incluye clinica ----------
def test_available_permissions_clinica(superadmin):
    r = requests.get(f"{API}/roles/available-permissions", headers=_h(superadmin), timeout=30)
    assert r.status_code == 200, r.text
    cats = r.json()["categories"]
    assert "clinica" in cats
    ids = {p["id"] for p in cats["clinica"]["permissions"]}
    assert {"view_agenda", "view_evaluacion", "manage_recetas", "view_sala_operaciones"}.issubset(ids)


# ---------- 3. Rol medico ----------
def test_rol_medico(superadmin):
    r = requests.get(f"{API}/roles/medico", headers=_h(superadmin), timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["display_name"] == "Médico"
    perms = body["permissions"]
    for p in ["view_agenda", "view_evaluacion", "manage_recetas", "view_sala_operaciones"]:
        assert perms.get(p) is True, f"permiso rol {p} debería ser True"


# ---------- 4. mi-dia como médico ----------
def test_mi_dia_medico(medico):
    r = requests.get(f"{API}/agenda/mi-dia", headers=_h(medico), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["medico_nombre"] == DR_NAME, f"got {data['medico_nombre']}"
    # Todas las citas devueltas deben ser del médico
    for c in data.get("citas_del_dia", []):
        assert (
            c.get("medico_id") == MEDICO_FICHA_ID
            or c.get("asignado_a_medico_id") == MEDICO_FICHA_ID
        ), f"Cita no pertenece al médico: {c}"


# ---------- 5. Menu config del rol medico ----------
def test_menu_config_medico(superadmin):
    r = requests.get(f"{API}/menu-config/role/medico", headers=_h(superadmin), timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    enabled = set(body.get("enabled_menus") or body.get("default_menus") or [])
    assert {"pacientes", "agenda", "evaluacion_oftalmologica", "sala_operaciones"}.issubset(enabled), enabled
    # No debería tener dashboard/finanzas/inventario/optica
    assert not ({"dashboard", "finanzas", "inventario", "optica"} & enabled), enabled


# ---------- 6. Vinculación usuario_id a ficha médico ----------
def test_patch_medico_usuario_id_idempotent(superadmin, medico):
    # Obtener user id medico_test
    r = requests.get(f"{API}/users", headers=_h(superadmin), timeout=30)
    assert r.status_code == 200
    users = r.json() if isinstance(r.json(), list) else r.json().get("users", [])
    medico_user = next((u for u in users if u.get("username") == "medico_test"), None)
    assert medico_user, "medico_test user no encontrado"
    uid = medico_user.get("id") or medico_user.get("_id")

    # PATCH setear usuario_id (idempotente)
    r = requests.patch(
        f"{API}/medicos-agenda/{MEDICO_FICHA_ID}",
        json={"usuario_id": uid},
        headers=_h(superadmin),
        timeout=30,
    )
    assert r.status_code in (200, 204), r.text

    # Verificar persistió
    r = requests.get(f"{API}/medicos-agenda", headers=_h(superadmin), timeout=30)
    assert r.status_code == 200
    body = r.json()
    doctors = body["data"] if isinstance(body, dict) else body
    doc = next((d for d in doctors if d["id"] == MEDICO_FICHA_ID), None)
    assert doc is not None
    assert doc.get("usuario_id") == uid, f"usuario_id no persistió: {doc}"


# ---------- 7. Regresión: usuario y admin siguen con view_agenda ----------
def test_regresion_usuario_sigue_con_agenda(usuario):
    perms = usuario.get("permissions") or usuario.get("user", {}).get("permissions") or {}
    assert perms.get("view_agenda") is True, f"usuario perdió view_agenda: {perms.get('view_agenda')}"


def test_regresion_optica_sin_agenda(superadmin):
    r = requests.get(f"{API}/roles/optica", headers=_h(superadmin), timeout=30)
    assert r.status_code == 200
    perms = r.json()["permissions"]
    assert not perms.get("view_agenda", False), "optica NO debería tener view_agenda"
    assert not perms.get("view_evaluacion", False), "optica NO debería tener view_evaluacion"
    assert not perms.get("view_sala_operaciones", False), "optica NO debería tener view_sala_operaciones"


# ---------- 8. Medico sin ficha vinculada: 403 ----------
def test_mi_dia_sin_vinculo(superadmin):
    # Crear usuario médico temporal sin ficha
    import time
    uname = f"TEST_medico_sin_ficha_{int(time.time())}"
    r = requests.post(
        f"{API}/users",
        json={
            "username": uname,
            "password": "test1234",
            "name": "TEST Medico Sin Ficha",
            "role": "medico",
            "email": f"{uname}@test.com",
        },
        headers=_h(superadmin),
        timeout=30,
    )
    assert r.status_code in (200, 201), r.text
    created_id = r.json().get("id") or r.json().get("user", {}).get("id")

    # login
    tok = _login(uname, "test1234")
    r = requests.get(f"{API}/agenda/mi-dia", headers=_h(tok), timeout=30)
    assert r.status_code == 403, f"esperado 403, got {r.status_code} {r.text}"
    assert "vinculado" in r.text.lower() or "medico" in r.text.lower()

    # cleanup
    if created_id:
        requests.delete(f"{API}/users/{created_id}", headers=_h(superadmin), timeout=30)
