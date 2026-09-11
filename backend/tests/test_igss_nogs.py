"""
Tests para NOG por Unidad IGSS (feature nueva).
Cubre: catálogo NOG, acreditación automática al crear evaluación, bloqueo al 100%,
recalcular, anular, retroactivo, exportación Excel, permisos.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPERADMIN = {"username": "superadmin", "password": "nova2024"}
IGSS_ADMIN = {"username": "igss.admin", "password": "IgssAdmin2024"}
OPTICA = {"username": "optica", "password": "optica2024"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['username']}: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# -------------------- Fixtures --------------------

@pytest.fixture(scope="module")
def super_token():
    return _login(SUPERADMIN)


@pytest.fixture(scope="module")
def igss_token():
    try:
        return _login(IGSS_ADMIN)
    except AssertionError:
        pytest.skip("igss.admin user not available")


@pytest.fixture(scope="module")
def optica_token():
    return _login(OPTICA)


@pytest.fixture(scope="module")
def unidad_id(super_token):
    """Crear una unidad IGSS para las pruebas (o usar demo)."""
    name = f"TEST_UNIDAD_NOG_{uuid.uuid4().hex[:6]}"
    r = requests.post(
        f"{API}/igss-units",
        json={"name": name, "code": name[:15], "address": "Test", "phone": "12345678"},
        headers=_hdr(super_token), timeout=30
    )
    assert r.status_code in (200, 201), f"Crear unidad: {r.status_code} {r.text}"
    uid = r.json().get("id")
    yield uid
    # cleanup
    try:
        requests.delete(f"{API}/igss-units/{uid}", headers=_hdr(super_token), timeout=15)
    except Exception:
        pass


def _crear_paciente(token, unidad, nog_numero, sufijo=""):
    dpi = f"29{int(time.time()*1000) % 10**11:011d}"[:13]
    payload = {
        "first_name": f"TESTNOG{sufijo}",
        "last_name": f"Apellido{uuid.uuid4().hex[:4]}",
        "gender": "masculino",
        "birth_date": "1990-01-15",
        "phone": "55550001",
        "dpi": dpi,
        "referral_institution": "igss",
        "igss_unit_id": unidad,
        "igss_afiliacion": f"AF-{uuid.uuid4().hex[:6]}",
        "igss_nog": nog_numero,
    }
    r = requests.post(f"{API}/patients", json=payload, headers=_hdr(token), timeout=30)
    assert r.status_code in (200, 201), f"Crear paciente: {r.status_code} {r.text}"
    return r.json()


def _crear_evaluacion(token, paciente_id):
    r = requests.post(
        f"{API}/evaluaciones",
        json={"paciente_id": paciente_id, "motivo_consulta": "Test acreditación NOG"},
        headers=_hdr(token), timeout=30
    )
    return r


# -------------------- Backend tests --------------------

class TestCatalogoNOG:
    def test_crear_nog_devuelve_derivados(self, super_token, unidad_id):
        numero = f"NOG-TEST-{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{API}/igss-units/{unidad_id}/nogs",
            json={"numero": numero, "nombre_servicio": "Consulta", "tipo_compra": "contrato",
                  "cantidad": 5, "precio": 100.0},
            headers=_hdr(super_token), timeout=30
        )
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        d = r.json()
        assert d["numero"] == numero
        assert d["cantidad"] == 5
        assert d["acreditados"] == 0
        assert d["disponibles"] == 5
        assert d["estado"] == "activo"
        assert d["valor_total"] == 500.0
        assert d.get("acreditaciones_retroactivas") == 0
        pytest.nog_created_id = d["id"]

    def test_nog_duplicado_falla(self, super_token, unidad_id):
        numero = f"NOG-DUP-{uuid.uuid4().hex[:6]}"
        p = {"numero": numero, "cantidad": 2, "precio": 10}
        r1 = requests.post(f"{API}/igss-units/{unidad_id}/nogs", json=p,
                           headers=_hdr(super_token), timeout=30)
        assert r1.status_code == 200
        r2 = requests.post(f"{API}/igss-units/{unidad_id}/nogs", json=p,
                           headers=_hdr(super_token), timeout=30)
        assert r2.status_code == 400, f"Se esperaba 400 duplicado, got {r2.status_code}: {r2.text}"

    def test_nogs_activos_selector(self, super_token, unidad_id):
        r = requests.get(f"{API}/igss-units/{unidad_id}/nogs-activos",
                         headers=_hdr(super_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all("numero" in x and "disponibles" in x and "estado" in x for x in data)


class TestAcreditacionYBloqueo:
    """Crear NOG cantidad=3, paciente con ese NOG, 4 evaluaciones -> acreditados=3."""

    def test_flujo_completo(self, super_token, unidad_id):
        numero = f"NOG-BLOQ-{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{API}/igss-units/{unidad_id}/nogs",
            json={"numero": numero, "nombre_servicio": "Cx", "cantidad": 3, "precio": 50},
            headers=_hdr(super_token), timeout=30
        )
        assert r.status_code == 200, r.text
        nog = r.json()
        nog_id = nog["id"]

        pac = _crear_paciente(super_token, unidad_id, numero)
        pac_id = pac["id"]

        # 4 evaluaciones - todas exitosas, pero 4a NO acredita (bloqueo 100%)
        for i in range(4):
            re = _crear_evaluacion(super_token, pac_id)
            assert re.status_code == 200, f"Eval {i} falló: {re.status_code} {re.text}"

        # Estado del NOG
        r = requests.get(f"{API}/igss-units/{unidad_id}/nogs",
                         headers=_hdr(super_token), timeout=30)
        assert r.status_code == 200
        nogs = {n["id"]: n for n in r.json()["nogs"]}
        n = nogs[nog_id]
        assert n["acreditados"] == 3, f"Esperado 3, got {n['acreditados']}"
        assert n["disponibles"] == 0
        assert n["estado"] == "completado"

        # Listado pacientes del NOG
        r = requests.get(f"{API}/igss-units/nogs/{nog_id}/pacientes",
                         headers=_hdr(super_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        for row in data["acreditaciones"]:
            for f in ("record_number", "full_name", "dpi", "igss_afiliacion", "fecha_acreditacion"):
                assert f in row, f"Falta campo {f}"

        # Guardar contexto para siguientes tests
        pytest.bloq_nog_id = nog_id
        pytest.bloq_pac_id = pac_id
        pytest.bloq_acred_ids = [x["acreditacion_id"] for x in data["acreditaciones"]]

    def test_anular_libera_cupo(self, super_token, unidad_id):
        nog_id = getattr(pytest, "bloq_nog_id", None)
        acred_ids = getattr(pytest, "bloq_acred_ids", [])
        if not nog_id or not acred_ids:
            pytest.skip("Depende de test_flujo_completo")
        acred_id = acred_ids[0]
        r = requests.post(
            f"{API}/igss-units/nogs/{nog_id}/acreditaciones/{acred_id}/anular",
            json={"motivo": "Prueba anular"}, headers=_hdr(super_token), timeout=30
        )
        assert r.status_code == 200, r.text
        nog = r.json()["nog"]
        assert nog["acreditados"] == 2
        assert nog["disponibles"] == 1
        assert nog["estado"] == "activo"

        # La fila desaparece del listado
        r = requests.get(f"{API}/igss-units/nogs/{nog_id}/pacientes",
                         headers=_hdr(super_token), timeout=30)
        ids = [x["acreditacion_id"] for x in r.json()["acreditaciones"]]
        assert acred_id not in ids

    def test_recalcular_respeta_anulacion(self, super_token, unidad_id):
        nog_id = getattr(pytest, "bloq_nog_id", None)
        if not nog_id:
            pytest.skip("Depende de test_flujo_completo")
        # Recalcular: debe volver a acreditar la 4a que estaba bloqueada
        r = requests.post(f"{API}/igss-units/nogs/{nog_id}/recalcular",
                          headers=_hdr(super_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["acreditados"] == 3
        assert d["disponibles"] == 0
        # No recrea la anulada
        r = requests.get(f"{API}/igss-units/nogs/{nog_id}/pacientes",
                         headers=_hdr(super_token), timeout=30)
        anulada = getattr(pytest, "bloq_acred_ids", [])[0] if getattr(pytest, "bloq_acred_ids", None) else None
        ids = [x["acreditacion_id"] for x in r.json()["acreditaciones"]]
        assert anulada not in ids

        # Idempotente: 2a llamada no crea nuevas
        r2 = requests.post(f"{API}/igss-units/nogs/{nog_id}/recalcular",
                           headers=_hdr(super_token), timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("acreditaciones_nuevas", 0) == 0


class TestRetroactivo:
    def test_conteo_retroactivo_al_crear_nog(self, super_token, unidad_id):
        numero = f"NOG-RETRO-{uuid.uuid4().hex[:6]}"
        # Crear paciente con ese NOG ANTES
        pac = _crear_paciente(super_token, unidad_id, numero, sufijo="R")
        # 2 evaluaciones ANTES de que exista el NOG
        for _ in range(2):
            re = _crear_evaluacion(super_token, pac["id"])
            assert re.status_code == 200, re.text

        # Ahora crear el NOG
        r = requests.post(
            f"{API}/igss-units/{unidad_id}/nogs",
            json={"numero": numero, "cantidad": 5, "precio": 10},
            headers=_hdr(super_token), timeout=30
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("acreditaciones_retroactivas") == 2, f"retro esperado 2, got {d}"
        assert d["acreditados"] == 2


class TestExportaciones:
    def test_export_nog_excel(self, super_token, unidad_id):
        nog_id = getattr(pytest, "bloq_nog_id", None) or getattr(pytest, "nog_created_id", None)
        if not nog_id:
            pytest.skip("No hay NOG previo")
        r = requests.get(f"{API}/igss-units/nogs/{nog_id}/export/excel",
                         headers=_hdr(super_token), timeout=30)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "spreadsheetml" in ct, f"content-type inesperado: {ct}"
        assert len(r.content) > 500

    def test_export_unidad_excel(self, super_token, unidad_id):
        r = requests.get(f"{API}/igss-units/{unidad_id}/nogs/export/excel",
                         headers=_hdr(super_token), timeout=30)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        assert len(r.content) > 500


class TestPermisos:
    def test_igss_admin_puede_crear(self, igss_token, unidad_id):
        numero = f"NOG-IGSSADM-{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{API}/igss-units/{unidad_id}/nogs",
            json={"numero": numero, "cantidad": 2, "precio": 5},
            headers=_hdr(igss_token), timeout=30
        )
        assert r.status_code == 200, f"igss.admin debe poder crear: {r.status_code} {r.text}"

    def test_igss_admin_puede_listar(self, igss_token, unidad_id):
        r = requests.get(f"{API}/igss-units/{unidad_id}/nogs",
                         headers=_hdr(igss_token), timeout=30)
        assert r.status_code == 200

    def test_optica_sin_permiso_403(self, optica_token, unidad_id):
        numero = f"NOG-OPT-{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{API}/igss-units/{unidad_id}/nogs",
            json={"numero": numero, "cantidad": 2, "precio": 5},
            headers=_hdr(optica_token), timeout=30
        )
        assert r.status_code == 403, f"optica debe recibir 403, got {r.status_code}: {r.text}"
