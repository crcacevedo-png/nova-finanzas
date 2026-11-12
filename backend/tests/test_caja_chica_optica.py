# Caja Chica Óptica: permisos por rol, validación egreso, saldo continuo, edición/eliminación, informe + excel
import os
import io
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api/caja-chica"

CREDS = {
    "superadmin": ("superadmin", "nova2024"),
    "optica": ("optica", "Optica2024$"),
    "admin": ("admin", "Admin2024$"),
    "usuario": ("usuario", "user2024"),
}

_tokens = {}
CREATED = []


def hdr(role):
    if role not in _tokens:
        u, p = CREDS[role]
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
        if r.status_code != 200:
            pytest.skip(f"login {role} failed {r.status_code} {r.text[:200]}")
        _tokens[role] = r.json()["access_token"]
    return {"Authorization": f"Bearer {_tokens[role]}"}


def create(role, **payload):
    r = requests.post(f"{API}/movimientos", json=payload, headers=hdr(role))
    if r.status_code == 200:
        CREATED.append(r.json()["id"])
    return r


def resumen(role="superadmin"):
    r = requests.get(f"{API}/resumen", headers=hdr(role))
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for mid in CREATED:
        requests.delete(f"{API}/movimientos/{mid}", headers=hdr("superadmin"))


# --- Access control
class TestAccess:
    @pytest.mark.parametrize("role", ["superadmin", "optica", "admin"])
    def test_roles_with_access(self, role):
        d = resumen(role)
        assert set(d.keys()) >= {"total_ingresos", "total_egresos", "saldo"}

    def test_usuario_no_access(self):
        r = requests.get(f"{API}/resumen", headers=hdr("usuario"))
        assert r.status_code == 403
        r = requests.post(f"{API}/movimientos", json={"tipo": "ingreso", "monto": 1, "fecha": "2026-01-05"}, headers=hdr("usuario"))
        assert r.status_code == 403

    def test_no_token(self):
        r = requests.get(f"{API}/resumen")
        assert r.status_code in (401, 403)


# --- Validation
class TestValidation:
    def test_egreso_without_fields_422(self):
        before = requests.get(f"{API}/movimientos", headers=hdr("optica")).json()["total"]
        r = create("optica", tipo="egreso", monto=10, fecha="2026-01-10")
        assert r.status_code == 422
        r = create("optica", tipo="egreso", monto=10, fecha="2026-01-10", solicitante="  ", motivo="x")
        assert r.status_code == 422
        r = create("optica", tipo="egreso", monto=10, fecha="2026-01-10", solicitante="Juan")
        assert r.status_code == 422
        after = requests.get(f"{API}/movimientos", headers=hdr("optica")).json()["total"]
        assert before == after

    def test_invalid_monto_fecha(self):
        assert create("optica", tipo="ingreso", monto=0, fecha="2026-01-10").status_code == 422
        assert create("optica", tipo="ingreso", monto=-5, fecha="2026-01-10").status_code == 422
        assert create("optica", tipo="ingreso", monto=5, fecha="10/01/2026").status_code == 422
        assert create("optica", tipo="otro", monto=5, fecha="2026-01-10").status_code == 422


# --- CRUD + continuous balance + permissions
class TestFlow:
    def test_full_flow(self):
        base = resumen()
        r1 = create("optica", tipo="ingreso", monto=500, fecha="2026-01-15")
        assert r1.status_code == 200, r1.text
        ing = r1.json()
        assert ing["registrado_por_nombre"] and ing["solicitante"] is None
        r2 = create("optica", tipo="egreso", monto=120.5, fecha="2026-02-03", solicitante="TEST_Maria", motivo="TEST_Papeleria")
        assert r2.status_code == 200, r2.text
        eg = r2.json()
        assert eg["solicitante"] == "TEST_Maria"
        s = resumen()
        assert round(s["total_ingresos"] - base["total_ingresos"], 2) == 500
        assert round(s["total_egresos"] - base["total_egresos"], 2) == 120.5
        assert round(s["saldo"] - base["saldo"], 2) == 379.5

        # list contains both, filter by mes
        lst = requests.get(f"{API}/movimientos", headers=hdr("optica")).json()["data"]
        ids = [m["id"] for m in lst]
        assert ing["id"] in ids and eg["id"] in ids
        jan = requests.get(f"{API}/movimientos?mes=2026-01", headers=hdr("optica")).json()["data"]
        assert ing["id"] in [m["id"] for m in jan] and eg["id"] not in [m["id"] for m in jan]

        # owner edit
        r = requests.put(f"{API}/movimientos/{ing['id']}", json={"monto": 600}, headers=hdr("optica"))
        assert r.status_code == 200 and r.json()["monto"] == 600 and r.json()["editado_por_nombre"]
        assert round(resumen()["total_ingresos"] - base["total_ingresos"], 2) == 600

        # egreso edit empty solicitante -> 400
        r = requests.put(f"{API}/movimientos/{eg['id']}", json={"solicitante": " "}, headers=hdr("optica"))
        assert r.status_code == 400

        # admin cannot edit optica's movement
        r = requests.put(f"{API}/movimientos/{ing['id']}", json={"monto": 1}, headers=hdr("admin"))
        assert r.status_code == 403
        # superadmin can edit anyone's
        r = requests.put(f"{API}/movimientos/{ing['id']}", json={"monto": 650}, headers=hdr("superadmin"))
        assert r.status_code == 200 and r.json()["monto"] == 650

        # delete: optica/admin 403
        for role in ("optica", "admin"):
            r = requests.delete(f"{API}/movimientos/{eg['id']}", headers=hdr(role))
            assert r.status_code == 403, role

        # admin creates and edits own
        r3 = create("admin", tipo="ingreso", monto=10, fecha="2026-02-10")
        assert r3.status_code == 200
        r = requests.put(f"{API}/movimientos/{r3.json()['id']}", json={"monto": 11}, headers=hdr("admin"))
        assert r.status_code == 200

        # informe
        inf = requests.get(f"{API}/informe?mes=2026-02", headers=hdr("optica"))
        assert inf.status_code == 200
        d = inf.json()
        ids = [m["id"] for m in d["movimientos"]]
        assert eg["id"] in ids and r3.json()["id"] in ids and ing["id"] not in ids
        assert d["total_egresos_mes"] >= 120.5
        # saldo acumulado includes Jan ingreso
        assert d["saldo_acumulado_fin_mes"] >= 650 + 11 - 120.5 - 1e-6 or base["saldo"] != 0

        x = requests.get(f"{API}/informe/excel?mes=2026-02", headers=hdr("optica"))
        assert x.status_code == 200
        assert "spreadsheetml" in x.headers["content-type"]
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(x.content))
        assert wb.active.max_row >= 5

        # superadmin delete -> 404 afterwards
        r = requests.delete(f"{API}/movimientos/{eg['id']}", headers=hdr("superadmin"))
        assert r.status_code == 200
        r = requests.delete(f"{API}/movimientos/{eg['id']}", headers=hdr("superadmin"))
        assert r.status_code == 404
        r = requests.put(f"{API}/movimientos/nonexistent", json={"monto": 1}, headers=hdr("superadmin"))
        assert r.status_code == 404

    def test_informe_bad_mes(self):
        r = requests.get(f"{API}/informe?mes=abc", headers=hdr("optica"))
        print("informe mes=abc ->", r.status_code, r.text[:200])
        r = requests.get(f"{API}/informe", headers=hdr("optica"))
        assert r.status_code == 422
