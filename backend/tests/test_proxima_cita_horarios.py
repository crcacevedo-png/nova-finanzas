# Tests: Próxima Cita desde Evaluación -> horarios-disponibles + proxima-cita (409/400)
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
MEDICO_ID = "a8bb541a-7fcb-49ab-bd20-32788f57acb5"
LABORABLE = "2026-06-15"
DOMINGO = "2026-06-14"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token") or r.json().get("token")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def created(client):
    ids = []
    yield ids
    for cid in ids:
        client.delete(f"{BASE_URL}/api/agenda/citas/{cid}")


@pytest.fixture(scope="module")
def medico_horario(client):
    r = client.get(f"{BASE_URL}/api/medicos-agenda")
    meds = r.json() if r.status_code == 200 else []
    if isinstance(meds, dict):
        meds = meds.get("medicos", [])
    m = next((x for x in meds if x.get("id") == MEDICO_ID), None)
    return (m or {}).get("horario_semanal")


# ---- horarios-disponibles ----
class TestHorarios:
    def test_laborable_returns_slots(self, client):
        r = client.get(f"{BASE_URL}/api/agenda/horarios-disponibles",
                       params={"medico_id": MEDICO_ID, "fecha": LABORABLE, "duracion": 20})
        assert r.status_code == 200, r.text
        d = r.json()
        assert set(["disponible", "motivo", "slots", "duracion"]) <= set(d.keys())
        assert d["disponible"] is True
        assert d["duracion"] == 20
        assert isinstance(d["slots"], list) and len(d["slots"]) > 0
        for s in d["slots"]:
            assert len(s) == 5 and s[2] == ":"
        assert d["slots"] == sorted(d["slots"])
        print("slots:", d["slots"][:5], "...", d["slots"][-3:], len(d["slots"]))

    def test_domingo_no_disponible(self, client):
        r = client.get(f"{BASE_URL}/api/agenda/horarios-disponibles",
                       params={"medico_id": MEDICO_ID, "fecha": DOMINGO, "duracion": 20})
        assert r.status_code == 200
        d = r.json()
        assert d["disponible"] is False
        assert d["slots"] == []
        assert d["motivo"] == "El médico no atiende ese día"

    def test_fecha_invalida_400(self, client):
        r = client.get(f"{BASE_URL}/api/agenda/horarios-disponibles",
                       params={"medico_id": MEDICO_ID, "fecha": "2026-13-45"})
        assert r.status_code == 400

    def test_sin_auth(self):
        r = requests.get(f"{BASE_URL}/api/agenda/horarios-disponibles",
                         params={"medico_id": MEDICO_ID, "fecha": LABORABLE})
        assert r.status_code in (401, 403)

    def test_slots_within_horario(self, client, medico_horario):
        if not medico_horario:
            pytest.skip("medico sin horario_semanal")
        cfg = medico_horario.get("1")
        r = client.get(f"{BASE_URL}/api/agenda/horarios-disponibles",
                       params={"medico_id": MEDICO_ID, "fecha": LABORABLE, "duracion": 20})
        slots = r.json()["slots"]
        print("horario lunes:", cfg)
        assert slots[0] >= cfg["hora_inicio"]


# ---- proxima-cita ----
class TestProximaCita:
    def _payload(self, hora, fecha=LABORABLE, notas=None):
        return {
            "paciente_id": "TEST_pac_" + self.pid,
            "paciente_nombre": "TEST Paciente ProximaCita",
            "medico_id": MEDICO_ID,
            "medico_nombre": "Dr. Carlos Méndez",
            "fecha": fecha,
            "hora_inicio": hora,
            "tipo_cita": "Control Post Operatorio",
            "notas": notas or "TEST_nota proxima cita",
        }

    pid = uuid.uuid4().hex[:8]

    def test_create_and_appears_in_agenda(self, client, created):
        r = client.get(f"{BASE_URL}/api/agenda/horarios-disponibles",
                       params={"medico_id": MEDICO_ID, "fecha": LABORABLE, "duracion": 20})
        slots = r.json()["slots"]
        hora = slots[len(slots) // 2]
        TestProximaCita.hora = hora
        r = client.post(f"{BASE_URL}/api/agenda/proxima-cita", json=self._payload(hora))
        assert r.status_code == 200, r.text
        c = r.json()
        created.append(c["id"])
        assert c["estado"] == "Agendada"
        assert c["tipo_cita"] == "Control Post Operatorio"
        assert c["notas"] == "TEST_nota proxima cita"
        g = client.get(f"{BASE_URL}/api/agenda/citas", params={"fecha": LABORABLE, "medico_id": MEDICO_ID})
        assert g.status_code == 200
        data = g.json()
        lst = data if isinstance(data, list) else data.get("data", [])
        f = next((x for x in lst if x["id"] == c["id"]), None)
        assert f is not None
        assert f["tipo_cita"] == "Control Post Operatorio"
        assert f["notas"] == "TEST_nota proxima cita"
        assert f["hora_inicio"] == hora

    def test_duplicate_400(self, client):
        r = client.post(f"{BASE_URL}/api/agenda/proxima-cita", json=self._payload(TestProximaCita.hora))
        assert r.status_code == 400, r.text

    def test_domingo_409(self, client):
        r = client.post(f"{BASE_URL}/api/agenda/proxima-cita", json=self._payload("10:00", fecha=DOMINGO))
        assert r.status_code == 409, r.text
        assert "no atiende" in r.json()["detail"]

    def test_fuera_horario_409(self, client):
        r = client.post(f"{BASE_URL}/api/agenda/proxima-cita", json=self._payload("23:00"))
        assert r.status_code == 409, r.text
        print(r.json())

    def test_bloqueo_409(self, client):
        # crear bloqueo de franja horaria del médico en otra fecha laborable
        fecha = "2026-06-16"
        b = client.post(f"{BASE_URL}/api/agenda/bloqueos", json={
            "tipo": "medico", "medico_id": MEDICO_ID, "fecha_inicio": fecha, "fecha_fin": fecha,
            "dia_completo": False, "hora_inicio": "09:00", "hora_fin": "10:00", "motivo": "TEST_bloqueo"})
        if b.status_code not in (200, 201):
            pytest.skip(f"no se pudo crear bloqueo {b.status_code} {b.text[:200]}")
        bid = b.json().get("id") or b.json().get("bloqueo", {}).get("id")
        try:
            h = client.get(f"{BASE_URL}/api/agenda/horarios-disponibles",
                           params={"medico_id": MEDICO_ID, "fecha": fecha, "duracion": 20}).json()
            assert "09:00" not in h["slots"] and "09:15" not in h["slots"] and "08:45" not in h["slots"]
            r = client.post(f"{BASE_URL}/api/agenda/proxima-cita", json=self._payload("09:15", fecha=fecha))
            assert r.status_code == 409, r.text
            assert "TEST_bloqueo" in r.json()["detail"]
        finally:
            client.delete(f"{BASE_URL}/api/agenda/bloqueos/{bid}")

    def test_full_slot_hidden(self, client, created):
        # Llenar un slot hasta max_citas_por_slot y verificar que desaparece
        cfg = client.get(f"{BASE_URL}/api/agenda/configuracion").json()
        mx = int(cfg.get("max_citas_por_slot") or 1)
        fecha = "2026-06-22"
        slots = client.get(f"{BASE_URL}/api/agenda/horarios-disponibles",
                           params={"medico_id": MEDICO_ID, "fecha": fecha}).json()["slots"]
        hora = slots[0]
        for i in range(mx):
            p = self._payload(hora, fecha=fecha)
            p["paciente_id"] = f"TEST_full_{self.pid}_{i}"
            r = client.post(f"{BASE_URL}/api/agenda/proxima-cita", json=p)
            assert r.status_code == 200, r.text
            created.append(r.json()["id"])
        slots2 = client.get(f"{BASE_URL}/api/agenda/horarios-disponibles",
                            params={"medico_id": MEDICO_ID, "fecha": fecha}).json()["slots"]
        assert hora not in slots2
        # Backend still accepts an extra one beyond max? (report-only)
        p = self._payload(hora, fecha=fecha)
        p["paciente_id"] = f"TEST_full_{self.pid}_extra"
        r = client.post(f"{BASE_URL}/api/agenda/proxima-cita", json=p)
        print("extra beyond max status:", r.status_code)
        if r.status_code == 200:
            created.append(r.json()["id"])
