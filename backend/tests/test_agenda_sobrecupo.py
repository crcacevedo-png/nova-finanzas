"""Sobrecupo de citas en Agenda: verificar-horario, sobrecupo permitido en POST /citas,
enforcement 409 (fuera de horario / bloqueo), walk-in Presente."""
import os
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") + "/api"
MED = "a8bb541a-7fcb-49ab-bd20-32788f57acb5"  # Dr. Carlos Méndez (Lunes 08:00-12:00)
MEDN = "Dr. Carlos Méndez"
LUNES = "2026-10-26"
DOMINGO = "2026-10-25"
HORA_LLENO = "09:40"
CREATED = []


def _login():
    r = requests.post(f"{BASE}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def h():
    hdr = {"Authorization": f"Bearer {_login()}"}
    yield hdr
    for cid in CREATED:
        requests.delete(f"{BASE}/agenda/citas/{cid}", headers=hdr, timeout=30)


@pytest.fixture(scope="module")
def pac(h):
    r = requests.get(f"{BASE}/patients?limit=1", headers=h, timeout=30).json()
    return (r.get("data") or r)[0]["id"]


def _verif(h, fecha, hora, dur=20, med=MED):
    r = requests.get(f"{BASE}/agenda/verificar-horario", headers=h, timeout=30,
                     params={"medico_id": med, "fecha": fecha, "hora": hora, "duracion": dur})
    assert r.status_code == 200, r.text
    return r.json()


def _crear(h, pac, fecha, hora):
    return requests.post(f"{BASE}/agenda/citas", headers=h, timeout=30, json={
        "paciente_id": pac, "paciente_nombre": "TEST_Sobrecupo", "medico_id": MED, "medico_nombre": MEDN,
        "fecha": fecha, "hora_inicio": hora, "duracion_minutos": 20, "tipo_cita": "Subsecuente"})


# verificar-horario: libre en lunes laborable
def test_verificar_libre(h):
    d = _verif(h, LUNES, "11:20")
    assert d["estado"] == "libre" and d["motivo"] is None and isinstance(d["ocupadas"], int)


# verificar-horario: domingo no atiende
def test_verificar_domingo_no_disponible(h):
    d = _verif(h, DOMINGO, "09:00")
    assert d["estado"] == "no_disponible" and "no atiende" in d["motivo"].lower()


# verificar-horario: fuera de horario (antes 08:00 / pasa de 12:00)
def test_verificar_fuera_horario(h):
    assert _verif(h, LUNES, "07:00")["estado"] == "no_disponible"
    d = _verif(h, LUNES, "11:50")
    assert d["estado"] == "no_disponible" and "Fuera del horario" in d["motivo"]


# verificar-horario: hora inválida -> 400; sin auth -> 401/403
def test_verificar_validaciones(h):
    r = requests.get(f"{BASE}/agenda/verificar-horario", headers=h, timeout=30,
                     params={"medico_id": MED, "fecha": LUNES, "hora": "xx"})
    assert r.status_code == 400
    r2 = requests.get(f"{BASE}/agenda/verificar-horario", timeout=30,
                      params={"medico_id": MED, "fecha": LUNES, "hora": "09:00"})
    assert r2.status_code in (401, 403)


# Llenar slot (max=3) -> lleno -> 4a cita se crea (sobrecupo permitido)
def test_lleno_y_sobrecupo_permitido(h, pac):
    cfg = requests.get(f"{BASE}/agenda/configuracion", headers=h, timeout=30).json()
    mx = int(cfg.get("max_citas_por_slot") or 1)
    base = _verif(h, LUNES, HORA_LLENO)["ocupadas"]
    for _ in range(max(0, mx - base)):
        r = _crear(h, pac, LUNES, HORA_LLENO)
        assert r.status_code == 200, r.text
        CREATED.append(r.json()["id"])
    d = _verif(h, LUNES, HORA_LLENO)
    assert d["estado"] == "lleno" and d["ocupadas"] >= mx
    r = _crear(h, pac, LUNES, HORA_LLENO)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    CREATED.append(cid)
    g = requests.get(f"{BASE}/agenda/citas/{cid}", headers=h, timeout=30)
    assert g.status_code == 200 and g.json()["hora_inicio"] == HORA_LLENO
    assert _verif(h, LUNES, HORA_LLENO)["ocupadas"] == d["ocupadas"] + 1


# horarios-disponibles (Próxima Cita) excluye el slot lleno; proxima-cita rechaza 409
def test_proxima_cita_sin_sobrecupo(h, pac):
    r = requests.get(f"{BASE}/agenda/horarios-disponibles", headers=h, timeout=30,
                     params={"medico_id": MED, "fecha": LUNES, "duracion": 20}).json()
    assert HORA_LLENO not in r["slots"]
    r2 = requests.post(f"{BASE}/agenda/proxima-cita", headers=h, timeout=30, json={
        "paciente_id": pac, "paciente_nombre": "TEST_Sobrecupo", "medico_id": MED, "medico_nombre": MEDN,
        "fecha": LUNES, "hora_inicio": HORA_LLENO, "tipo_cita": "Subsecuente"})
    if r2.status_code == 200:
        CREATED.append(r2.json()["id"])
    assert r2.status_code in (400, 409), r2.text


# POST /citas sigue 409 en domingo y fuera de horario
def test_crear_rechaza_no_disponible(h, pac):
    r = _crear(h, pac, DOMINGO, "09:00")
    if r.status_code == 200:
        CREATED.append(r.json()["id"])
    assert r.status_code == 409 and "no atiende" in r.json()["detail"].lower()
    r = _crear(h, pac, LUNES, "07:00")
    if r.status_code == 200:
        CREATED.append(r.json()["id"])
    assert r.status_code == 409


# Bloqueo de franja: verificar -> no_disponible con motivo; POST -> 409
def test_bloqueo_enforcement(h, pac):
    rb = requests.post(f"{BASE}/agenda/bloqueos", headers=h, timeout=30, json={
        "tipo": "medico", "medico_id": MED, "medico_nombre": MEDN, "fecha_inicio": LUNES,
        "dia_completo": False, "hora_inicio": "10:00", "hora_fin": "11:00", "motivo": "TEST_Bloqueo sobrecupo"})
    assert rb.status_code == 200, rb.text
    bid = rb.json()["bloqueo"]["id"]
    try:
        d = _verif(h, LUNES, "10:20")
        assert d["estado"] == "no_disponible" and d["motivo"] == "TEST_Bloqueo sobrecupo"
        r = _crear(h, pac, LUNES, "10:20")
        if r.status_code == 200:
            CREATED.append(r.json()["id"])
        assert r.status_code == 409 and "TEST_Bloqueo" in r.json()["detail"]
    finally:
        requests.delete(f"{BASE}/agenda/bloqueos/{bid}", headers=h, timeout=30)


# Walk-in crea como Presente
def test_walk_in_presente(h, pac):
    r = requests.post(f"{BASE}/agenda/walk-in", headers=h, timeout=30, json={
        "paciente_id": pac, "paciente_nombre": "TEST_WalkIn", "medico_id": MED, "medico_nombre": MEDN,
        "tipo_cita": "Subsecuente"})
    assert r.status_code == 200, r.text
    d = r.json()
    CREATED.append(d["id"])
    assert d["estado"] == "Presente" and d["hora_llegada"]
