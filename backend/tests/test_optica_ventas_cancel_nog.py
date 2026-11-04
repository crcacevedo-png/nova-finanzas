# Tests: Óptica Ventas cancel (role restriction + inventory revert) and NOG discount on patient create (optica role)
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
UNIT_ID = "37e430e9-4e82-43ce-ac98-28347b7c21e4"
NOG_NUM = "28017447"


def _env(key):
    with open("/app/backend/.env") as f:
        for line in f:
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"')


mdb = MongoClient(_env("MONGO_URL"))[_env("DB_NAME")]


def _login(u, p):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login {u} failed {r.status_code}")
    d = r.json()
    return {"Authorization": f"Bearer {d.get('access_token') or d.get('token')}"}


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def opt():
    return _login("optica", "Optica2024$")


@pytest.fixture(scope="module")
def usr():
    return _login("usuario", "user2024")


# ---- Cancel role restriction ----
class TestCancelRoles:
    def test_optica_forbidden(self, opt):
        r = requests.put(f"{BASE_URL}/api/optica/sales/fake-id/cancel", headers=opt)
        assert r.status_code == 403

    def test_usuario_forbidden(self, usr):
        r = requests.put(f"{BASE_URL}/api/optica/sales/fake-id/cancel", headers=usr)
        assert r.status_code == 403

    def test_superadmin_404(self, sa):
        r = requests.put(f"{BASE_URL}/api/optica/sales/{uuid.uuid4()}/cancel", headers=sa)
        assert r.status_code == 404


# ---- Cancel reverts inventory ----
class TestCancelRevertsStock:
    def test_v2_sale_then_cancel(self, opt, sa):
        frames = requests.get(f"{BASE_URL}/api/optica/frames", headers=sa).json()
        frames = frames.get("data", frames) if isinstance(frames, dict) else frames
        frame = next((f for f in frames if (f.get("stock") or 0) >= 3 and f.get("is_active", True)), None)
        if not frame:
            pytest.skip("No frame with stock")
        fid = frame["id"]
        before = mdb.optica_frames.find_one({"id": fid})["stock"]
        price = 100.0
        body = {"patient_name": "TEST_Consumidor", "items": [
            {"type": "frame", "product_id": fid, "quantity": 2, "unit_price": price, "subtotal": price * 2}],
            "subtotal": price * 2, "total": price * 2,
            "payments": [{"method": "Efectivo", "amount": price * 2}]}
        r = requests.post(f"{BASE_URL}/api/optica/sales/v2", json=body, headers=opt)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        sid = d.get("id") or (d.get("sale") or {}).get("id") or (d.get("data") or {}).get("id")
        assert sid, d
        try:
            mid = mdb.optica_frames.find_one({"id": fid})["stock"]
            assert mid == before - 2
            # optica cannot cancel
            r403 = requests.put(f"{BASE_URL}/api/optica/sales/{sid}/cancel", headers=opt)
            assert r403.status_code == 403
            rc = requests.put(f"{BASE_URL}/api/optica/sales/{sid}/cancel", headers=sa)
            assert rc.status_code == 200, rc.text
            after = mdb.optica_frames.find_one({"id": fid})["stock"]
            assert after == before
            s = mdb.optica_sales.find_one({"id": sid})
            assert s["status"] == "cancelado"
            # double cancel -> 400, no double restore
            r2 = requests.put(f"{BASE_URL}/api/optica/sales/{sid}/cancel", headers=sa)
            assert r2.status_code == 400
            assert mdb.optica_frames.find_one({"id": fid})["stock"] == before
            # sale list shows it cancelled
            g = requests.get(f"{BASE_URL}/api/optica/sales/{sid}", headers=opt)
            if g.status_code == 200:
                assert g.json().get("status") == "cancelado"
        finally:
            cur = mdb.optica_sales.find_one({"id": sid})
            if cur and cur.get("status") != "cancelado":
                mdb.optica_frames.update_one({"id": fid}, {"$inc": {"stock": 2}})
            mdb.optica_sales.delete_one({"id": sid})
            mdb.optica_sale_payments.delete_many({"sale_id": sid})


# ---- NOG discount on patient create by optica ----
class TestOpticaNog:
    def test_optica_create_igss_patient_discounts_nog(self, opt, sa):
        def nog():
            lst = requests.get(f"{BASE_URL}/api/igss-units/{UNIT_ID}/nogs-activos", headers=opt)
            assert lst.status_code == 200
            return next((n for n in lst.json() if n["numero"] == NOG_NUM), None)
        n0 = nog()
        if not n0:
            pytest.skip("NOG not found")
        body = {"first_name": "TEST_Nog", "last_name": "Optica", "gender": "otro", "birth_date": "1990-01-01",
                "phone": "55551234", "dpi": "9" + str(uuid.uuid4().int)[:12], "referral_institution": "igss", "igss_unit_id": UNIT_ID,
                "igss_ordenes": [{"id": str(uuid.uuid4()), "nog": NOG_NUM, "no_sps": "TESTSPS1",
                                  "codigo": "C1", "procedimiento": "TEST proc"}]}
        r = requests.post(f"{BASE_URL}/api/patients", json=body, headers=opt)
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]
        try:
            n1 = nog()
            assert n1["acreditados"] == n0["acreditados"] + 1
            assert n1["disponibles"] == n0["disponibles"] - 1
            # update by optica: add 2nd order with different SPS -> another discount
            body2 = {"igss_ordenes": body["igss_ordenes"] + [{"id": str(uuid.uuid4()), "nog": NOG_NUM,
                     "no_sps": "TESTSPS2", "codigo": "C2", "procedimiento": "P2"}]}
            u = requests.put(f"{BASE_URL}/api/patients/{pid}", json=body2, headers=opt)
            assert u.status_code == 200, u.text
            assert nog()["acreditados"] == n0["acreditados"] + 2
        finally:
            requests.delete(f"{BASE_URL}/api/patients/{pid}", headers=sa)
            assert nog()["acreditados"] == n0["acreditados"]
            mdb.patients.delete_one({"id": pid})
            mdb.igss_nog_acreditaciones.delete_many({"paciente_id": pid})
