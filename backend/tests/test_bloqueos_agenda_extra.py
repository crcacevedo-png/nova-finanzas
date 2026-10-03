"""Pruebas extra Bloqueos de Agenda: rol 'usuario' + conflicto preserva cita."""
import os
import pytest
import requests

BASE = "https://novavision-finanzas.preview.emergentagent.com/api"
FECHA = "2026-12-18"


def _login(user, pwd):
    r = requests.post(f"{BASE}/auth/login", json={"username": user, "password": pwd}, timeout=30)
    assert r.status_code == 200, f"login {user} {r.status_code}: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login('superadmin', 'nova2024')}"}


@pytest.fixture(scope="module")
def user_h():
    return {"Authorization": f"Bearer {_login('usuario', 'user2024')}"}


@pytest.fixture(scope="module")
def ids(admin_h):
    med = requests.get(f"{BASE}/doctors?limit=1", headers=admin_h, timeout=30).json()
    pac = requests.get(f"{BASE}/patients?limit=1", headers=admin_h, timeout=30).json()
    ds = med.get("data") or med.get("doctors") or []
    ps = pac.get("data") or []
    return {"MED": ds[0]["id"], "MEDN": ds[0].get("name") or ds[0].get("nombre"), "PAC": ps[0]["id"]}


# Rol 'usuario' puede crear y eliminar bloqueo
def test_usuario_crea_y_elimina_bloqueo(user_h, ids):
    r = requests.post(f"{BASE}/agenda/bloqueos", headers=user_h, json={
        "tipo": "medico", "medico_id": ids["MED"], "medico_nombre": ids["MEDN"],
        "fecha_inicio": FECHA, "dia_completo": False,
        "hora_inicio": "08:00", "hora_fin": "09:00", "motivo": "Prueba rol usuario"
    }, timeout=30)
    assert r.status_code == 200, r.text
    bid = r.json()["bloqueo"]["id"]
    r2 = requests.delete(f"{BASE}/agenda/bloqueos/{bid}", headers=user_h, timeout=30)
    assert r2.status_code in (200, 204)


# Conflicto: crear bloqueo con cita existente la lista pero NO la elimina
def test_bloqueo_lista_conflictos_sin_eliminar(admin_h, ids):
    # 1. Crear una cita
    r = requests.post(f"{BASE}/agenda/citas", headers=admin_h, json={
        "paciente_id": ids["PAC"], "paciente_nombre": "Conflicto Test",
        "medico_id": ids["MED"], "medico_nombre": ids["MEDN"],
        "fecha": FECHA, "hora_inicio": "16:30", "duracion_minutos": 20,
        "tipo_cita": "Subsecuente"
    }, timeout=30)
    assert r.status_code == 200, r.text
    cita_id = r.json()["id"]

    # 2. Crear bloqueo que cubre esa cita
    rb = requests.post(f"{BASE}/agenda/bloqueos", headers=admin_h, json={
        "tipo": "medico", "medico_id": ids["MED"], "medico_nombre": ids["MEDN"],
        "fecha_inicio": FECHA, "dia_completo": False,
        "hora_inicio": "16:00", "hora_fin": "17:00", "motivo": "Overlap"
    }, timeout=30)
    assert rb.status_code == 200, rb.text
    body = rb.json()
    bid = body["bloqueo"]["id"]
    conflicts = body.get("citas_en_conflicto", [])
    assert any(c["id"] == cita_id for c in conflicts), f"cita no listada en conflictos: {conflicts}"

    # 3. La cita sigue existiendo
    rg = requests.get(f"{BASE}/agenda/citas/{cita_id}", headers=admin_h, timeout=30)
    assert rg.status_code == 200

    # cleanup
    requests.delete(f"{BASE}/agenda/bloqueos/{bid}", headers=admin_h, timeout=30)
    requests.delete(f"{BASE}/agenda/citas/{cita_id}", headers=admin_h, timeout=30)


# Reprogramar hacia bloqueo => 409
def test_reprogramar_hacia_bloqueo_409(admin_h, ids):
    # cita libre
    r = requests.post(f"{BASE}/agenda/citas", headers=admin_h, json={
        "paciente_id": ids["PAC"], "paciente_nombre": "Reprog Test",
        "medico_id": ids["MED"], "medico_nombre": ids["MEDN"],
        "fecha": FECHA, "hora_inicio": "18:00", "duracion_minutos": 20,
        "tipo_cita": "Subsecuente"
    }, timeout=30)
    assert r.status_code == 200
    cid = r.json()["id"]

    # bloqueo franja distinta
    rb = requests.post(f"{BASE}/agenda/bloqueos", headers=admin_h, json={
        "tipo": "medico", "medico_id": ids["MED"], "medico_nombre": ids["MEDN"],
        "fecha_inicio": FECHA, "dia_completo": False,
        "hora_inicio": "19:00", "hora_fin": "20:00", "motivo": "Reunión"
    }, timeout=30)
    assert rb.status_code == 200
    bid = rb.json()["bloqueo"]["id"]

    # intentar mover la cita a 19:30 => 409
    ru = requests.put(f"{BASE}/agenda/citas/{cid}", headers=admin_h, json={
        "fecha": FECHA, "hora_inicio": "19:30", "duracion_minutos": 20
    }, timeout=30)
    assert ru.status_code == 409, f"esperado 409, got {ru.status_code}: {ru.text}"
    assert "bloqueado" in ru.json().get("detail", "").lower() or "Reunión" in ru.json().get("detail", "")

    # cleanup
    requests.delete(f"{BASE}/agenda/bloqueos/{bid}", headers=admin_h, timeout=30)
    requests.delete(f"{BASE}/agenda/citas/{cid}", headers=admin_h, timeout=30)
