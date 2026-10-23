# Órdenes IGSS múltiples por paciente: acreditaciones por NOG, aplicar/anular manual, evaluación + PDF, citas
import os
import random
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"
UNIT_ZONA11 = "18801a0e-2eb9-425f-8848-b511022c9027"
NOG_A = "12345678"
NOG_B = "TEST-17800"

mongo = MongoClient("mongodb://localhost:27017")["test_database"]


def _login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    d = r.json()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {d.get('access_token') or d.get('token')}"})
    return s


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def igss_admin():
    return _login("igss.admin", "IgssAdmin2024$")


def _nog(numero):
    return mongo.igss_nogs.find_one({"unidad_id": UNIT_ZONA11, "numero": numero}, {"_id": 0})


def _vigentes(pid):
    return list(mongo.igss_nog_acreditaciones.find({"paciente_id": pid, "anulada": {"$ne": True}}, {"_id": 0}))


@pytest.fixture(scope="module")
def created(sa):
    ids = {"patients": [], "evals": [], "citas": []}
    yield ids
    for cid in ids["citas"]:
        sa.delete(f"{API}/agenda/citas/{cid}")
        mongo.citas.delete_one({"id": cid})
    for eid in ids["evals"]:
        mongo.evaluaciones_oftalmologicas.delete_one({"id": eid})
    for pid in ids["patients"]:
        sa.delete(f"{API}/patients/{pid}")  # libera cupos
        # anular cualquier remanente
        for a in _vigentes(pid):
            mongo.igss_nog_acreditaciones.update_one({"id": a["id"]}, {"$set": {"anulada": True}})
            mongo.igss_nogs.update_one({"id": a["nog_id"], "acreditados": {"$gt": 0}}, {"$inc": {"acreditados": -1}})
        mongo.igss_nog_acreditaciones.delete_many({"paciente_id": pid})
        mongo.patients.delete_one({"id": pid})
        mongo.audit_logs.delete_many({"entity_id": pid}) if "audit_logs" in mongo.list_collection_names() else None


def _payload(**kw):
    p = {
        "first_name": "TEST_Orden", "last_name": f"Multi{random.randint(1000,9999)}",
        "dpi": str(random.randint(10**12, 10**13 - 1)), "birth_date": "1980-01-01",
        "gender": "masculino", "phone": "55551234", "referral_institution": "igss",
        "igss_unit_id": UNIT_ZONA11,
        "igss_ordenes": [
            {"nog": NOG_A, "no_sps": "SPS-A1", "codigo": "C-A", "procedimiento": "Consulta"},
            {"nog": NOG_B, "no_sps": "SPS-B1", "codigo": "C-B", "procedimiento": "Catarata"},
        ],
    }
    p.update(kw)
    return p


class TestOrdenesIgss:
    state = {}

    def test_create_patient_two_orders_two_discounts(self, sa, created):
        a0, b0 = _nog(NOG_A)["acreditados"], _nog(NOG_B)["acreditados"]
        r = sa.post(f"{API}/patients", json=_payload())
        assert r.status_code in (200, 201), r.text
        d = r.json()
        created["patients"].append(d["id"])
        self.state["pid"] = d["id"]
        assert len(d["igss_ordenes"]) == 2
        assert d["igss_nog"] == NOG_A and d["igss_no_sps"] == "SPS-A1"
        assert _nog(NOG_A)["acreditados"] == a0 + 1
        assert _nog(NOG_B)["acreditados"] == b0 + 1
        assert len(_vigentes(d["id"])) == 2

    def test_get_patient_returns_ordenes(self, sa):
        r = sa.get(f"{API}/patients/{self.state['pid']}")
        assert r.status_code == 200
        ords = r.json()["igss_ordenes"]
        assert [o["nog"] for o in ords] == [NOG_A, NOG_B]
        assert all(o.get("id") for o in ords)
        self.state["ordenes"] = ords

    def test_same_nog_twice_single_discount(self, sa, created):
        a0 = _nog(NOG_A)["acreditados"]
        p = _payload(igss_ordenes=[{"nog": NOG_A, "no_sps": "X1"}, {"nog": NOG_A, "no_sps": "X2"}])
        r = sa.post(f"{API}/patients", json=p)
        assert r.status_code in (200, 201), r.text
        created["patients"].append(r.json()["id"])
        assert _nog(NOG_A)["acreditados"] == a0 + 1
        assert len(_vigentes(r.json()["id"])) == 1

    def test_put_remove_order_releases_one(self, sa):
        b0 = _nog(NOG_B)["acreditados"]
        ords = self.state["ordenes"]
        r = sa.put(f"{API}/patients/{self.state['pid']}", json={"igss_ordenes": [ords[0]]})
        assert r.status_code == 200, r.text
        assert len(r.json()["igss_ordenes"]) == 1
        assert _nog(NOG_B)["acreditados"] == b0 - 1
        assert len(_vigentes(self.state["pid"])) == 1

    def test_put_readd_order(self, sa):
        b0 = _nog(NOG_B)["acreditados"]
        ords = self.state["ordenes"]
        r = sa.put(f"{API}/patients/{self.state['pid']}", json={"igss_ordenes": ords})
        assert r.status_code == 200, r.text
        assert _nog(NOG_B)["acreditados"] == b0 + 1

    def test_put_remove_all_orders(self, sa):
        """Quitar TODAS las órdenes debería liberar los descuentos (no re-derivar del legacy)."""
        r = sa.put(f"{API}/patients/{self.state['pid']}", json={"igss_ordenes": []})
        assert r.status_code == 200, r.text
        n = len(r.json()["igss_ordenes"])
        vig = len(_vigentes(self.state["pid"]))
        # restaurar
        sa.put(f"{API}/patients/{self.state['pid']}", json={"igss_ordenes": self.state["ordenes"]})
        assert n == 0 and vig == 0, f"tras quitar todas: ordenes={n} acreditaciones vigentes={vig}"

    def test_aplicar_manual_and_duplicate(self, igss_admin, created):
        nog_id = _nog(NOG_B)["id"]
        # paciente IGSS con solo NOG_A
        sa = igss_admin
        r = sa.post(f"{API}/patients", json=_payload(igss_ordenes=[{"nog": NOG_A, "no_sps": "S"}]))
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]
        created["patients"].append(pid)
        self.state["pid_manual"] = pid
        b0 = _nog(NOG_B)["acreditados"]
        r = sa.post(f"{API}/igss-units/nogs/{nog_id}/acreditaciones/aplicar", json={"paciente_id": pid})
        assert r.status_code == 200, r.text
        assert r.json()["nog"]["acreditados"] == b0 + 1
        r2 = sa.post(f"{API}/igss-units/nogs/{nog_id}/acreditaciones/aplicar", json={"paciente_id": pid})
        assert r2.status_code == 400
        lst = sa.get(f"{API}/igss-units/nogs/{nog_id}/pacientes").json()
        assert any(f["paciente_id"] == pid for f in lst["acreditaciones"])

    def test_aplicar_404_patient(self, igss_admin):
        nog_id = _nog(NOG_B)["id"]
        r = igss_admin.post(f"{API}/igss-units/nogs/{nog_id}/acreditaciones/aplicar", json={"paciente_id": "nope"})
        assert r.status_code == 404

    def test_manual_discount_survives_patient_edit(self, igss_admin):
        """Un descuento aplicado manualmente no debería anularse al editar al paciente."""
        pid = self.state["pid_manual"]
        nog_id = _nog(NOG_B)["id"]
        r = igss_admin.put(f"{API}/patients/{pid}", json={"comments": "edit"})
        assert r.status_code == 200, r.text
        vig = [a for a in _vigentes(pid) if a["nog_id"] == nog_id]
        assert len(vig) == 1, "El descuento manual se anuló al editar el paciente (reconciliación)"

    def test_anular_releases(self, igss_admin):
        pid = self.state["pid_manual"]
        nog_id = _nog(NOG_B)["id"]
        vig = [a for a in _vigentes(pid) if a["nog_id"] == nog_id]
        if not vig:
            pytest.skip("no manual acred present")
        b0 = _nog(NOG_B)["acreditados"]
        r = igss_admin.post(f"{API}/igss-units/nogs/{nog_id}/acreditaciones/{vig[0]['id']}/anular", json={"motivo": "test"})
        assert r.status_code == 200, r.text
        assert _nog(NOG_B)["acreditados"] == b0 - 1

    def test_evaluacion_with_order_and_pdf(self, sa, created):
        ords = sa.get(f"{API}/patients/{self.state['pid']}").json()["igss_ordenes"]
        o = ords[1]
        a0 = _nog(NOG_B)["acreditados"]
        r = sa.post(f"{API}/evaluaciones", json={
            "paciente_id": self.state["pid"], "igss_orden_id": o["id"], "igss_nog": o["nog"],
            "igss_no_sps": o["no_sps"], "igss_codigo": o["codigo"], "igss_procedimiento": o["procedimiento"],
        })
        assert r.status_code in (200, 201), r.text
        ev = r.json()
        created["evals"].append(ev["id"])
        assert ev.get("igss_nog") == NOG_B and ev.get("igss_orden_id") == o["id"]
        assert _nog(NOG_B)["acreditados"] == a0  # no duplica
        # autoguardado cambiando la orden
        o0 = ords[0]
        r = sa.patch(f"{API}/evaluaciones/{ev['id']}/autoguardar", json={
            "igss_orden_id": o0["id"], "igss_nog": o0["nog"], "igss_no_sps": o0["no_sps"],
            "igss_codigo": o0["codigo"], "igss_procedimiento": o0["procedimiento"]})
        assert r.status_code == 200, r.text
        g = sa.get(f"{API}/evaluaciones/{ev['id']}").json()
        assert g["igss_orden_id"] == o0["id"] and g["igss_no_sps"] == "SPS-A1"
        pdf = sa.get(f"{API}/evaluaciones/{ev['id']}/pdf")
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

    def test_cita_with_order(self, sa, created):
        ords = sa.get(f"{API}/patients/{self.state['pid']}").json()["igss_ordenes"]
        docs = sa.get(f"{API}/doctors").json()
        docs = docs.get("data", docs) if isinstance(docs, dict) else docs
        import datetime as dt
        ok = None
        for doc in docs[:8]:
            for delta in range(1, 15):
                f = (dt.date.today() + dt.timedelta(days=delta)).isoformat()
                body = {"paciente_id": self.state["pid"], "paciente_nombre": "TEST_Orden",
                        "medico_id": doc["id"], "medico_nombre": doc.get("name", doc.get("nombre", "")),
                        "fecha": f, "hora_inicio": "10:00", "duracion_minutos": 20,
                        "igss_orden_id": ords[0]["id"], "igss_nog": ords[0]["nog"],
                        "igss_no_sps": ords[0]["no_sps"], "igss_procedimiento": ords[0]["procedimiento"]}
                r = sa.post(f"{API}/agenda/citas", json=body)
                if r.status_code in (200, 201):
                    ok = (r.json(), body)
                    break
            if ok:
                break
        assert ok, f"No se pudo crear cita: {r.status_code} {r.text[:200]}"
        c, body = ok
        created["citas"].append(c["id"])
        assert c.get("igss_orden_id") == ords[0]["id"] and c.get("igss_nog") == NOG_A
        body2 = dict(body, hora_inicio="11:00", igss_orden_id=ords[1]["id"], igss_nog=ords[1]["nog"],
                     igss_no_sps=ords[1]["no_sps"], igss_procedimiento=ords[1]["procedimiento"])
        r2 = sa.post(f"{API}/agenda/citas", json=body2)
        assert r2.status_code in (200, 201), r2.text
        created["citas"].append(r2.json()["id"])
        assert r2.json()["igss_nog"] == NOG_B

    def test_particular_patient_no_ordenes(self, sa, created):
        p = _payload(referral_institution="particular", igss_unit_id=None)
        r = sa.post(f"{API}/patients", json=p)
        assert r.status_code in (200, 201), r.text
        created["patients"].append(r.json()["id"])
        assert r.json()["igss_ordenes"] == []
        assert _vigentes(r.json()["id"]) == []

    def test_legacy_lazy_migration(self, sa):
        p = mongo.patients.find_one({"is_active": True, "referral_institution": "igss",
                                     "igss_nog": {"$nin": ["", None]},
                                     "$or": [{"igss_ordenes": {"$exists": False}}, {"igss_ordenes": []}]}, {"_id": 0, "id": 1, "igss_nog": 1})
        if not p:
            pytest.skip("No legacy patient without ordenes found")
        r = sa.get(f"{API}/patients/{p['id']}")
        assert r.status_code == 200
        assert r.json()["igss_ordenes"][0]["nog"] == p["igss_nog"]
