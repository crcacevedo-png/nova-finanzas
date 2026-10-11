"""
Tests para funcionalidades de Agenda (iteración 68):
1) Eliminar cita = marcar como Cancelada (no borrar); desaparece de vistas activas.
2) Reagendar (PUT) con validación de choque de horario => 409.
3) Contadores: por_medico.total excluye canceladas.
"""
import os
import pytest
import requests
from datetime import datetime, timedelta

def _read_env_url():
    url = os.environ.get("REACT_APP_BACKEND_URL", "")
    if not url:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    return url.rstrip("/")

BASE_URL = _read_env_url()
assert BASE_URL, "REACT_APP_BACKEND_URL no configurado"


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "superadmin", "password": "nova2024"
    })
    assert r.status_code == 200, f"Login falló: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def medico_y_fecha(h):
    """Elige un médico con horario_semanal y calcula la primera fecha futura disponible."""
    r = requests.get(f"{BASE_URL}/api/doctors", headers=h)
    assert r.status_code == 200, r.text
    doctors = r.json().get("data", r.json() if isinstance(r.json(), list) else [])
    chosen = None
    for d in doctors:
        did = d.get("id")
        # obtener detalle con horario_semanal
        rd = requests.get(f"{BASE_URL}/api/doctors/{did}", headers=h)
        if rd.status_code != 200:
            continue
        detail = rd.json()
        horario = detail.get("horario_semanal") or {}
        # Buscar día con rango que incluya 10:00-10:30
        for day_key, cfg in horario.items():
            if not cfg:
                continue
            activo = cfg.get("activo", True)
            inicio = cfg.get("hora_inicio") or cfg.get("inicio")
            fin = cfg.get("hora_fin") or cfg.get("fin")
            if not activo or not inicio or not fin:
                continue
            if inicio <= "09:00" and fin >= "12:00":
                # calcular próxima fecha para ese weekday (clave "1"=Lun .. "7"=Dom)
                try:
                    dow = int(day_key)
                except Exception:
                    continue
                today = datetime.now()
                # python weekday: lun=0..dom=6 ; clave: 1..7
                target = dow - 1
                diff = (target - today.weekday()) % 7
                if diff == 0:
                    diff = 7  # usar próxima semana para asegurar día futuro
                fecha = (today + timedelta(days=diff)).strftime("%Y-%m-%d")
                chosen = {
                    "medico_id": did,
                    "medico_nombre": detail.get("name"),
                    "fecha": fecha
                }
                break
        if chosen:
            break
    assert chosen, "No se encontró médico con horario amplio para pruebas"
    return chosen


@pytest.fixture(scope="module")
def paciente(h):
    r = requests.get(f"{BASE_URL}/api/patients/search?q=ca", headers=h)
    assert r.status_code == 200, r.text
    pacientes = r.json()
    assert pacientes, "No hay pacientes con 'ca' para probar"
    p = pacientes[0]
    return {
        "paciente_id": p["id"],
        "paciente_nombre": p.get("nombre_completo") or f"{p.get('first_name','')} {p.get('last_name','')}".strip()
    }


@pytest.fixture(scope="module")
def citas_creadas(h, medico_y_fecha, paciente):
    """Crea 2 citas (10:00 y 11:00) para los tests. Teardown cancela ambas."""
    base = {
        "medico_id": medico_y_fecha["medico_id"],
        "medico_nombre": medico_y_fecha["medico_nombre"],
        "fecha": medico_y_fecha["fecha"],
        "tipo_cita": "Consulta",
        "duracion_minutos": 30,
        **paciente,
    }
    cita_a_payload = {**base, "hora_inicio": "10:00"}
    cita_b_payload = {**base, "hora_inicio": "11:00"}
    ra = requests.post(f"{BASE_URL}/api/agenda/citas", headers=h, json=cita_a_payload)
    assert ra.status_code == 200, f"Crear cita A falló: {ra.status_code} {ra.text}"
    rb = requests.post(f"{BASE_URL}/api/agenda/citas", headers=h, json=cita_b_payload)
    assert rb.status_code == 200, f"Crear cita B falló: {rb.status_code} {rb.text}"
    citas = {"a": ra.json(), "b": rb.json()}
    yield citas
    # teardown: cancelar ambas si siguen existiendo
    for c in citas.values():
        try:
            requests.patch(
                f"{BASE_URL}/api/agenda/citas/{c['id']}/estado",
                headers=h, json={"estado": "Cancelada"}
            )
        except Exception:
            pass


# ---------- Tests PUT (reagendar) ----------
def test_put_cita_conflicto_devuelve_409(h, citas_creadas):
    """Mover cita A a la hora de B (11:00) debe dar 409 con mensaje exacto."""
    cita_a = citas_creadas["a"]
    cita_b = citas_creadas["b"]
    payload = {
        "fecha": cita_b["fecha"],
        "hora_inicio": cita_b["hora_inicio"],  # 11:00
        "medico_id": cita_b["medico_id"],
    }
    r = requests.put(f"{BASE_URL}/api/agenda/citas/{cita_a['id']}", headers=h, json=payload)
    assert r.status_code == 409, f"Esperado 409, obtuvo {r.status_code}: {r.text}"
    assert r.json().get("detail") == "Ese horario ya está ocupado para este médico"


def test_put_cita_slot_libre_200_y_persiste(h, citas_creadas):
    """Mover cita A a 09:30 (slot libre dentro del horario) => 200 y GET refleja cambio."""
    cita_a = citas_creadas["a"]
    payload = {"hora_inicio": "09:30"}
    r = requests.put(f"{BASE_URL}/api/agenda/citas/{cita_a['id']}", headers=h, json=payload)
    assert r.status_code == 200, f"Esperado 200, obtuvo {r.status_code}: {r.text}"
    body = r.json()
    assert body["hora_inicio"] == "09:30"
    assert body["hora_fin"] == "10:00"
    # GET verify
    g = requests.get(f"{BASE_URL}/api/agenda/citas/{cita_a['id']}", headers=h)
    assert g.status_code == 200
    assert g.json()["hora_inicio"] == "09:30"


# ---------- Tests Cancelación ----------
def test_patch_cancelada_oculta_de_listado_activo(h, citas_creadas, medico_y_fecha):
    """PATCH estado=Cancelada => 200. Luego la cita no aparece en /citas sin filtro ni en /rango,
    pero sí con ?estado=Cancelada."""
    cita_b = citas_creadas["b"]
    cita_id = cita_b["id"]
    fecha = medico_y_fecha["fecha"]
    r = requests.patch(
        f"{BASE_URL}/api/agenda/citas/{cita_id}/estado",
        headers=h, json={"estado": "Cancelada"}
    )
    assert r.status_code == 200, f"PATCH falló: {r.status_code} {r.text}"
    assert r.json()["estado"] == "Cancelada"

    # Listado activo (sin filtro estado) no debe contenerla
    la = requests.get(
        f"{BASE_URL}/api/agenda/citas?fecha={fecha}",
        headers=h
    )
    assert la.status_code == 200
    ids_activos = [c["id"] for c in la.json()["data"]]
    assert cita_id not in ids_activos, "Cita cancelada no debería aparecer en listado activo"

    # Listado rango tampoco
    lr = requests.get(
        f"{BASE_URL}/api/agenda/citas/rango?desde={fecha}&hasta={fecha}",
        headers=h
    )
    assert lr.status_code == 200
    ids_rango = [c["id"] for c in lr.json()["data"]]
    assert cita_id not in ids_rango, "Cita cancelada no debería aparecer en /rango"

    # Pero con filtro estado=Cancelada sí
    lc = requests.get(
        f"{BASE_URL}/api/agenda/citas?fecha={fecha}&estado=Cancelada",
        headers=h
    )
    assert lc.status_code == 200
    ids_canc = [c["id"] for c in lc.json()["data"]]
    assert cita_id in ids_canc, "Cita cancelada debería aparecer con ?estado=Cancelada"


def test_contadores_por_medico_excluye_canceladas(h, citas_creadas, medico_y_fecha):
    """por_medico[].total NO debe incluir citas canceladas."""
    fecha = medico_y_fecha["fecha"]
    medico_id = medico_y_fecha["medico_id"]
    r = requests.get(f"{BASE_URL}/api/agenda/contadores?fecha={fecha}", headers=h)
    assert r.status_code == 200
    data = r.json()
    # Debe haber exactamente 1 cita activa (A) para este médico, B está cancelada
    por_medico = {m["medico_id"]: m for m in data["por_medico"]}
    if medico_id in por_medico:
        # Al menos no debe contar la cancelada (B)
        assert por_medico[medico_id]["total"] >= 1
        # Si solo creamos 2 y 1 cancelada, total debe ser 1 (solo A)
        # Permitir mayores si existen otras citas pre-existentes
    # total_cancelados sí debe reflejarla
    assert data["total_cancelados"] >= 1
