"""Extended tests for horario_semanal: persistence, PUT reprogramar, external POST, compatibility."""
import os
import pytest
import requests

BASE = "https://novavision-finanzas.preview.emergentagent.com"
API = f"{BASE}/api"
KEY = "nova_agenda_1eH6M_ssw5iOnYeYVK_rGwnWUIh3_U1FXULX2AZB8jk"
LUN = "2026-12-14"
MAR = "2026-12-15"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def ctx(auth):
    ds = requests.get(f"{API}/doctors?limit=5", headers=auth, timeout=30).json()
    doctors = ds.get("data") or ds.get("doctors")
    assert len(doctors) >= 1
    d = doctors[0]
    pac = requests.get(f"{API}/patients?limit=1", headers=auth, timeout=30).json()["data"][0]
    original = d.get("horario_semanal")
    yield {"med_id": d["id"], "med_name": d.get("name") or d.get("nombre") or "Dr", "pac_id": pac["id"], "original": original, "doctors": doctors}
    # restore
    requests.put(f"{API}/doctors/{d['id']}", headers=auth, json={"horario_semanal": original}, timeout=30)


def test_persist_horario_and_get(auth, ctx):
    horario = {
        "1": {"activo": True, "hora_inicio": "08:00", "hora_fin": "12:00"},
        "2": {"activo": False, "hora_inicio": "", "hora_fin": ""},
        "3": {"activo": True, "hora_inicio": "14:00", "hora_fin": "18:00"},
    }
    r = requests.put(f"{API}/doctors/{ctx['med_id']}", headers=auth, json={"horario_semanal": horario}, timeout=30)
    assert r.status_code == 200
    # GET
    ds = requests.get(f"{API}/doctors?limit=50", headers=auth, timeout=30).json()
    doc = next(x for x in (ds.get("data") or ds.get("doctors")) if x["id"] == ctx["med_id"])
    hs = doc.get("horario_semanal")
    assert hs is not None
    assert hs["1"]["activo"] is True
    assert hs["1"]["hora_inicio"] == "08:00"
    assert hs["1"]["hora_fin"] == "12:00"
    assert hs["2"]["activo"] is False
    assert hs["3"]["hora_inicio"] == "14:00"


def test_reprogramar_fuera_de_horario(auth, ctx):
    # Create inside, then PUT to outside -> 409
    r = requests.post(f"{API}/agenda/citas", headers=auth, json={
        "paciente_id": ctx["pac_id"], "paciente_nombre": "Repro Test",
        "medico_id": ctx["med_id"], "medico_nombre": ctx["med_name"],
        "fecha": LUN, "hora_inicio": "10:00", "duracion_minutos": 20, "tipo_cita": "Subsecuente"}, timeout=30)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    try:
        # Reprogramar hacia fuera (13:00)
        r2 = requests.put(f"{API}/agenda/citas/{cid}", headers=auth, json={
            "fecha": LUN, "hora_inicio": "13:00", "duracion_minutos": 20}, timeout=30)
        assert r2.status_code == 409, f"expected 409, got {r2.status_code}: {r2.text}"
        assert "horario" in r2.json().get("detail", "").lower()
        # Reprogramar a Martes (no atiende)
        r3 = requests.put(f"{API}/agenda/citas/{cid}", headers=auth, json={
            "fecha": MAR, "hora_inicio": "10:00", "duracion_minutos": 20}, timeout=30)
        assert r3.status_code == 409
    finally:
        requests.delete(f"{API}/agenda/citas/{cid}", headers=auth, timeout=30)


def test_external_post_fuera_horario(auth, ctx):
    HK = {"X-API-Key": KEY}
    # Fuera de horario Lunes 13:00
    r = requests.post(f"{API}/agenda/external/citas", headers=HK, json={
        "paciente_id": ctx["pac_id"], "paciente_nombre": "Ext Fuera",
        "medico_id": ctx["med_id"], "medico_nombre": ctx["med_name"],
        "fecha": LUN, "hora_inicio": "13:00", "duracion_minutos": 20, "tipo_cita": "Subsecuente"}, timeout=30)
    assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text}"

    # Dentro -> 200 (si crea, limpiar)
    r2 = requests.post(f"{API}/agenda/external/citas", headers=HK, json={
        "paciente_id": ctx["pac_id"], "paciente_nombre": "Ext Dentro",
        "medico_id": ctx["med_id"], "medico_nombre": ctx["med_name"],
        "fecha": LUN, "hora_inicio": "11:00", "duracion_minutos": 20, "tipo_cita": "Subsecuente"}, timeout=30)
    assert r2.status_code in (200, 201), f"expected 200, got {r2.status_code}: {r2.text}"
    try:
        cid = r2.json().get("id")
        if cid:
            requests.delete(f"{API}/agenda/citas/{cid}", headers=auth, timeout=30)
    except Exception:
        pass


def test_compatibilidad_sin_horario(auth, ctx):
    """Un médico SIN horario_semanal (null) debe permitir agendar cualquier día/hora."""
    # Buscar o crear un médico sin horario: usar el segundo si existe, o resetear uno temporalmente
    doctors = ctx["doctors"]
    target = None
    for d in doctors:
        if d["id"] != ctx["med_id"] and not d.get("horario_semanal"):
            target = d
            break
    cleanup_restore = None
    if target is None:
        # Usar un segundo médico y resetear su horario a null
        if len(doctors) < 2:
            pytest.skip("Need at least 2 doctors")
        target = doctors[1]
        cleanup_restore = target.get("horario_semanal")
        r = requests.put(f"{API}/doctors/{target['id']}", headers=auth, json={"horario_semanal": None}, timeout=30)
        assert r.status_code == 200

    try:
        # Intentar crear cita Martes a las 22:00 (debería permitir)
        r = requests.post(f"{API}/agenda/citas", headers=auth, json={
            "paciente_id": ctx["pac_id"], "paciente_nombre": "Compat Sin Horario",
            "medico_id": target["id"], "medico_nombre": target.get("name") or target.get("nombre") or "Dr",
            "fecha": MAR, "hora_inicio": "22:00", "duracion_minutos": 20, "tipo_cita": "Subsecuente"}, timeout=30)
        assert r.status_code == 200, f"compat should allow any time, got {r.status_code}: {r.text}"
        cid = r.json()["id"]
        requests.delete(f"{API}/agenda/citas/{cid}", headers=auth, timeout=30)
    finally:
        if cleanup_restore is not None:
            requests.put(f"{API}/doctors/{target['id']}", headers=auth, json={"horario_semanal": cleanup_restore}, timeout=30)
