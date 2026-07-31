"""Backend tests for Dashboard Financiero + Admin Integridad (iteration 25)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")

SUPERADMIN = {"username": "superadmin", "password": "nova2024"}
ADMIN = {"username": "admin", "password": "Admin2024Nuevo!"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['username']}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPERADMIN)


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


def H(t):
    return {"Authorization": f"Bearer {t}"}


# ============ Dashboard Financiero ============
class TestDashboardFinanciero:
    def test_mes_actual_superadmin(self, super_token):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero", headers=H(super_token), timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        # Schema keys
        for k in ("periodo", "ingresos", "gastos", "balance", "cuentas_por_cobrar",
                  "ingresos_por_pagador", "gastos_por_categoria", "evolucion_mensual"):
            assert k in d, f"missing key {k}"
        assert "total_cobrado" in d["ingresos"]
        assert "total" in d["gastos"] and "pagado" in d["gastos"] and "pendiente" in d["gastos"]
        assert "neto" in d["balance"] and "positivo" in d["balance"]
        assert "total_pendiente" in d["cuentas_por_cobrar"]
        assert isinstance(d["evolucion_mensual"], list) and len(d["evolucion_mensual"]) == 12
        for row in d["evolucion_mensual"]:
            for k in ("mes", "mes_nombre", "ingresos", "gastos", "balance"):
                assert k in row
        # Balance neto correctness
        assert abs(d["balance"]["neto"] - (d["ingresos"]["total_cobrado"] - d["gastos"]["pagado"])) < 0.01
        assert d["balance"]["positivo"] == (d["balance"]["neto"] >= 0)

    def test_semestre(self, super_token):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero?periodo=semestre", headers=H(super_token), timeout=60)
        assert r.status_code == 200
        assert "6 meses" in r.json()["periodo"]["nombre"]

    def test_anual(self, super_token):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero?periodo=anual", headers=H(super_token), timeout=60)
        assert r.status_code == 200
        assert "Año" in r.json()["periodo"]["nombre"] or "Ano" in r.json()["periodo"]["nombre"]

    def test_personalizado(self, super_token):
        r = requests.get(
            f"{BASE_URL}/api/dashboard/financiero?periodo=personalizado&fecha_inicio=2026-01-01&fecha_fin=2026-01-31",
            headers=H(super_token), timeout=60)
        assert r.status_code == 200
        p = r.json()["periodo"]
        assert p["fecha_inicio"] == "2026-01-01"
        assert p["fecha_fin"] == "2026-01-31"

    def test_forbidden_admin(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero", headers=H(admin_token), timeout=30)
        assert r.status_code == 403, f"Expected 403 for admin, got {r.status_code}"

    def test_unauthorized_no_token(self):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero", timeout=30)
        assert r.status_code in (401, 403)

    def test_export_excel(self, super_token):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero/exportar?formato=excel",
                         headers=H(super_token), timeout=60)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "spreadsheet" in ct or "excel" in ct or "octet-stream" in ct, ct
        assert len(r.content) > 500

    def test_export_pdf(self, super_token):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero/exportar?formato=pdf",
                         headers=H(super_token), timeout=60)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF", "Should be a PDF file"

    def test_export_forbidden_admin(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/dashboard/financiero/exportar?formato=excel",
                         headers=H(admin_token), timeout=30)
        assert r.status_code == 403


# ============ Integridad Pacientes / Datos ============
class TestIntegridad:
    def test_integridad_pacientes_super(self, super_token):
        r = requests.get(f"{BASE_URL}/api/admin/integridad-pacientes", headers=H(super_token), timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("pacientes_sin_referencias", "referencias_huerfanas", "posibles_duplicados", "estadisticas"):
            assert k in d
        for k in ("citas", "evaluaciones", "cirugias", "movimientos_caja", "cuentas_por_cobrar"):
            assert k in d["referencias_huerfanas"]
        for k in ("total_pacientes", "pacientes_con_referencias", "pacientes_sin_referencias",
                  "citas_huerfanas", "evaluaciones_huerfanas", "cirugias_huerfanas", "posibles_duplicados"):
            assert k in d["estadisticas"]

    def test_integridad_pacientes_forbidden_admin(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/admin/integridad-pacientes", headers=H(admin_token), timeout=30)
        assert r.status_code == 403

    def test_integridad_datos_super(self, super_token):
        r = requests.get(f"{BASE_URL}/api/admin/integridad-datos", headers=H(super_token), timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("documentos_sin_origen", "catalogos_duplicados", "estadisticas"):
            assert k in d
        for k in ("caja_movimientos", "caja_cierres", "cuentas_por_cobrar"):
            assert k in d["documentos_sin_origen"]
        for k in ("medicamentos", "estudios", "diagnosticos"):
            assert k in d["catalogos_duplicados"]

    def test_integridad_datos_forbidden_admin(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/admin/integridad-datos", headers=H(admin_token), timeout=30)
        assert r.status_code == 403


# ============ Modelos: cita_id en evaluaciones, paciente_id/evaluacion_id en surgeries ============
class TestReferenceFields:
    def test_evaluacion_accepts_cita_id(self, super_token):
        # Create a patient first
        import uuid
        dpi_unique = str(uuid.uuid4().int)[:13]
        p = requests.post(f"{BASE_URL}/api/patients", headers=H(super_token), json={
            "first_name": "TEST_REF", "last_name": "CITA",
            "gender": "masculino", "sex": "masculino",
            "birth_date": "1990-01-01",
            "phone": "55555555",
            "dpi": dpi_unique,
            "referral_institution": "particular"
        }, timeout=30)
        assert p.status_code in (200, 201), p.text
        patient = p.json()
        pid = patient["id"]
        try:
            payload = {
                "paciente_id": pid,
                "paciente_nombre": "TEST_REF CITA",
                "cita_id": "TEST-CITA-REF-123",
                "fecha": "2026-01-15",
                "motivo_consulta": "Test",
            }
            r = requests.post(f"{BASE_URL}/api/evaluaciones", headers=H(super_token), json=payload, timeout=30)
            assert r.status_code in (200, 201), r.text
            ev = r.json()
            assert ev.get("cita_id") == "TEST-CITA-REF-123"
            eid = ev["id"]
            # GET it back
            g = requests.get(f"{BASE_URL}/api/evaluaciones/{eid}", headers=H(super_token), timeout=30)
            assert g.status_code == 200
            assert g.json().get("cita_id") == "TEST-CITA-REF-123"
            requests.delete(f"{BASE_URL}/api/evaluaciones/{eid}", headers=H(super_token), timeout=30)
        finally:
            requests.delete(f"{BASE_URL}/api/patients/{pid}", headers=H(super_token), timeout=30)

    def test_surgery_accepts_paciente_id_and_evaluacion_id(self, super_token):
        payload = {
            "date": "2026-02-01",
            "time": "10:00",
            "paciente_id": "TEST-PAC-REF-999",
            "patient_name": "TEST_REF SURGERY",
            "evaluacion_id": "TEST-EVA-REF-999",
            "procedure": "Facoemulsificación",
            "surgeon": "Dr. Test",
            "eye": "OD",
            "anesthesia_type": "topica",
            "anesthesiologist": "Dr. Anest",
            "institution": "Clínica",
            "observations": "TEST"
        }
        r = requests.post(f"{BASE_URL}/api/surgeries", headers=H(super_token), json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text
        s = r.json()
        assert s.get("paciente_id") == "TEST-PAC-REF-999"
        assert s.get("evaluacion_id") == "TEST-EVA-REF-999"
        sid = s["id"]
        g = requests.get(f"{BASE_URL}/api/surgeries/{sid}", headers=H(super_token), timeout=30)
        assert g.status_code == 200
        assert g.json().get("paciente_id") == "TEST-PAC-REF-999"
        assert g.json().get("evaluacion_id") == "TEST-EVA-REF-999"
        requests.delete(f"{BASE_URL}/api/surgeries/{sid}", headers=H(super_token), timeout=30)
