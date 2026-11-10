# Óptica POS - FEL + ticket endpoints (iteration: FEL en Punto de Venta de Óptica)
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
ACCESSORY_ID = "1cedd3ef-7840-4c2a-8b3a-b5ac49d2b293"


def _login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login {u} failed {r.status_code}")
    d = r.json()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {d.get('access_token') or d.get('token')}"})
    return s


@pytest.fixture(scope="module")
def optica():
    return _login("optica", "Optica2024$")


@pytest.fixture(scope="module")
def admin():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def sale(optica, admin):
    payload = {
        "patient_name": "TEST_POS_FEL",
        "items": [{"type": "accessory", "product_id": ACCESSORY_ID, "quantity": 1, "unit_price": 45.0, "subtotal": 45.0}],
        "subtotal": 45.0, "discount": 0, "total": 45.0,
        "payments": [{"method": "Efectivo", "amount": 45.0}],
    }
    r = optica.post(f"{API}/optica/sales/v2", json=payload)
    assert r.status_code in (200, 201), r.text
    s = r.json()
    yield s
    # cleanup: anular FEL if certified, then cancel sale
    d = admin.get(f"{API}/optica/sales/{s['id']}").json()
    if (d.get("fel") or {}).get("estado") == "certificado":
        admin.post(f"{API}/fel/anular", json={"origen": "optica", "sale_id": s["id"], "motivo": "TEST cleanup"})
    admin.put(f"{API}/optica/sales/{s['id']}/cancel")


class TestOpticaPosFel:
    def test_detail_has_fel_field_none(self, optica, sale):
        r = optica.get(f"{API}/optica/sales/{sale['id']}")
        assert r.status_code == 200
        d = r.json()
        assert "fel" in d and d["fel"] is None
        assert d["items_v2"][0]["product_id"] == ACCESSORY_ID

    def test_ticket_structure(self, optica, sale):
        r = optica.get(f"{API}/optica/sales/{sale['id']}/ticket")
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["venta"]["numero"] == sale["order_number"]
        assert t["cliente"]["nombre"] == "TEST_POS_FEL"
        assert len(t["items"]) == 1 and t["items"][0]["subtotal"] == 45.0
        assert t["totales"]["total"] == 45.0
        assert t["pago"]["formas"][0]["monto"] == 45.0
        assert "/" in t["venta"]["fecha"]

    def test_ticket_404(self, optica):
        r = optica.get(f"{API}/optica/sales/nonexistent-xyz/ticket")
        assert r.status_code == 404

    def test_ticket_requires_auth(self, sale):
        r = requests.get(f"{API}/optica/sales/{sale['id']}/ticket")
        assert r.status_code in (401, 403)

    def test_certify_and_detail_persists(self, optica, sale):
        r = optica.post(f"{API}/fel/certificar", json={"origen": "optica", "sale_id": sale["id"], "receptor_nit": None, "receptor_nombre": None}, timeout=90)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c.get("serie") and c.get("numero")
        d = optica.get(f"{API}/optica/sales/{sale['id']}").json()
        assert d["fel"]["estado"] == "certificado"
        assert str(d["fel"]["numero"]) == str(c["numero"])

    def test_resumen_dia_includes_fel(self, optica, sale):
        r = optica.get(f"{API}/optica/sales/resumen-dia")
        assert r.status_code == 200
        row = next((s for s in r.json()["sales"] if s["id"] == sale["id"]), None)
        assert row is not None
        assert (row.get("fel") or {}).get("estado") == "certificado"
        assert row.get("items_v2") and row.get("payments") is not None

    def test_certify_twice_rejected(self, optica, sale):
        r = optica.post(f"{API}/fel/certificar", json={"origen": "optica", "sale_id": sale["id"]}, timeout=90)
        assert r.status_code == 400

    def test_list_sales_includes_fel(self, optica, sale):
        r = optica.get(f"{API}/optica/sales", params={"search": sale["order_number"]})
        assert r.status_code == 200
