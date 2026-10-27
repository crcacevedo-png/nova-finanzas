# IGSS Fase 2/3: mantenimiento de borradores vacíos, recálculo por evaluaciones y guard de creación vacía
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
IGSS = f"{BASE_URL}/api/igss-units"


def _login(u, p):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login failed {u}: {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token") or r.json().get("token")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def igss_admin():
    return _login("igss.admin", "IgssAdmin2024$")


@pytest.fixture(scope="module")
def std():
    return _login("usuario", "user2024")


@pytest.fixture(scope="module")
def patient_id(sa):
    r = sa.get(f"{BASE_URL}/api/patients", params={"limit": 50})
    assert r.status_code == 200
    data = r.json()
    items = data if isinstance(data, list) else (data.get("items") or data.get("patients") or data.get("data") or [])
    non_igss = [p for p in items if p.get("referral_institution") != "igss"]
    assert items, "no patients"
    return (non_igss or items)[0]["id"]


@pytest.fixture(scope="module")
def created_ids(sa):
    ids = []
    yield ids
    for i in ids:
        sa.delete(f"{BASE_URL}/api/evaluaciones/{i}")


# Roles
class TestRoles:
    def test_std_preview_403(self, std):
        assert std.get(f"{IGSS}/mantenimiento/borradores-vacios").status_code == 403

    def test_std_limpiar_403(self, std):
        r = std.post(f"{IGSS}/mantenimiento/borradores-vacios/limpiar", json={"confirmar": True})
        assert r.status_code == 403

    def test_std_recalculo_403(self, std):
        assert std.post(f"{IGSS}/nogs/recalcular-por-evaluaciones").status_code == 403

    def test_igss_admin_preview_200(self, igss_admin):
        r = igss_admin.get(f"{IGSS}/mantenimiento/borradores-vacios")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["total_evaluaciones"], int) and isinstance(d["total_vacios"], int)
        assert isinstance(d["muestra"], list) and len(d["muestra"]) <= 50
        for m in d["muestra"]:
            assert set(m.keys()) == {"id", "paciente_nombre", "expediente", "fecha"}

    def test_limpiar_without_confirm_400(self, sa):
        r = sa.post(f"{IGSS}/mantenimiento/borradores-vacios/limpiar", json={})
        assert r.status_code == 400

    def test_igss_admin_limpiar_200(self, igss_admin):
        r = igss_admin.post(f"{IGSS}/mantenimiento/borradores-vacios/limpiar", json={"confirmar": True})
        assert r.status_code == 200
        assert isinstance(r.json()["eliminados"], int)
        after = igss_admin.get(f"{IGSS}/mantenimiento/borradores-vacios").json()
        assert after["total_vacios"] == 0


# Recálculo
class TestRecalculo:
    def test_recalculo_idempotent_no_overdraft(self, sa):
        r1 = sa.post(f"{IGSS}/nogs/recalcular-por-evaluaciones")
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert {"pacientes_procesados", "acreditaciones_vigentes", "nogs"} <= set(d1)
        r2 = sa.post(f"{IGSS}/nogs/recalcular-por-evaluaciones")
        assert r2.status_code == 200
        assert r2.json()["acreditaciones_vigentes"] == d1["acreditaciones_vigentes"]
        res = sa.get(f"{IGSS}/nogs/resumen").json()
        assert res["servicios_acreditados"] >= 0
        assert res["servicios_disponibles"] >= 0

    def test_igss_admin_recalculo_200(self, igss_admin):
        assert igss_admin.post(f"{IGSS}/nogs/recalcular-por-evaluaciones").status_code == 200


# Fase 3: guard de creación vacía
class TestCreateGuard:
    def test_empty_422(self, sa, patient_id):
        r = sa.post(f"{BASE_URL}/api/evaluaciones", json={"paciente_id": patient_id})
        assert r.status_code == 422, r.text

    def test_motivo_200(self, sa, patient_id, created_ids):
        r = sa.post(f"{BASE_URL}/api/evaluaciones",
                    json={"paciente_id": patient_id, "motivo_consulta": "TEST_motivo"})
        assert r.status_code == 200, r.text
        created_ids.append(r.json()["id"])
        assert r.json()["motivo_consulta"] == "TEST_motivo"

    def test_medico_200(self, sa, patient_id, created_ids):
        r = sa.post(f"{BASE_URL}/api/evaluaciones",
                    json={"paciente_id": patient_id, "medico_nombre": "TEST Dr"})
        assert r.status_code == 200, r.text
        created_ids.append(r.json()["id"])

    # Consistency frontend tieneDatosClinicos vs backend: frontend counts these as data
    def test_lectura_examenes_only(self, sa, patient_id, created_ids):
        r = sa.post(f"{BASE_URL}/api/evaluaciones",
                    json={"paciente_id": patient_id, "lectura_examenes": "TEST lectura"})
        if r.status_code == 200:
            created_ids.append(r.json()["id"])
        assert r.status_code == 200, f"frontend autosaves but backend rejects: {r.status_code} {r.text[:200]}"

    def test_antecedentes_only(self, sa, patient_id, created_ids):
        r = sa.get(f"{BASE_URL}/openapi.json")
        r = sa.post(f"{BASE_URL}/api/evaluaciones",
                    json={"paciente_id": patient_id, "antecedentes": {"oftalmologicos": "TEST glaucoma"}})
        if r.status_code == 200:
            created_ids.append(r.json()["id"])
        assert r.status_code == 200, f"frontend autosaves but backend rejects: {r.status_code} {r.text[:200]}"
