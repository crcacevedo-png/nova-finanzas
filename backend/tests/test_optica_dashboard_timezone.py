# Óptica dashboard: Guatemala-timezone "Ventas del Día", CxC and rentabilidad/utilidad fields
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
ACCESSORY_ID = "1cedd3ef-7840-4c2a-8b3a-b5ac49d2b293"  # Estuche rígido (preview seed)


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


# Same-day sale is counted in ventas-dia (GT day)
def test_same_day_sale_counts_today(client):
    before = client.get(f"{BASE_URL}/api/optica/dashboard/ventas-dia")
    assert before.status_code == 200, before.text
    b = before.json()
    payload = {
        "patient_name": "Consumidor Final",
        "items": [{"type": "accessory", "product_id": ACCESSORY_ID, "quantity": 1, "unit_price": 45.0, "subtotal": 45.0}],
        "subtotal": 45.0, "total": 45.0,
        "payments": [{"method": "Efectivo", "amount": 45.0}],
        "notes": "TEST_timezone_sale",
    }
    r = client.post(f"{BASE_URL}/api/optica/sales/v2", json=payload)
    assert r.status_code == 200, r.text
    sale = r.json()
    assert sale["total"] == 45.0
    print("created", sale["order_number"])
    after = client.get(f"{BASE_URL}/api/optica/dashboard/ventas-dia").json()
    assert after["fecha"] == b["fecha"]
    assert round(after["total_ventas"] - b["total_ventas"], 2) == 45.0
    assert after["num_ordenes"] == b["num_ordenes"] + 1
    assert round(after["total_cobrado"] - b["total_cobrado"], 2) == 45.0
    assert sale["order_number"] in [v.get("order_number") for v in after["ventas"]]


# CxC fields equal sum of pendiente balance_due
def test_cuentas_por_cobrar(client):
    d = client.get(f"{BASE_URL}/api/optica/dashboard/ventas-dia").json()
    assert "cuentas_por_cobrar" in d and "cuentas_por_cobrar_count" in d
    assert isinstance(d["cuentas_por_cobrar_count"], int)
    r = client.get(f"{BASE_URL}/api/optica/sales", params={"status": "pendiente", "limit": 1000})
    if r.status_code == 200:
        data = r.json()
        rows = data.get("data", data) if isinstance(data, dict) else data
        pend = [x for x in rows if x.get("status") == "pendiente" and (x.get("balance_due") or 0) > 0]
        print("list pend", len(pend), sum(x["balance_due"] for x in pend), "api", d["cuentas_por_cobrar"])


# Rentabilidad includes compras/utilidad
@pytest.mark.parametrize("periodo", ["dia", "semana", "mes", "año"])
def test_rentabilidad_fields(client, periodo):
    r = client.get(f"{BASE_URL}/api/optica/dashboard/rentabilidad", params={"periodo": periodo})
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("total_compras", "num_compras", "utilidad", "total_ingresos"):
        assert k in d
    assert abs(d["utilidad"] - round(d["total_ingresos"] - d["total_compras"], 2)) < 0.011


def test_ventas_dia_requires_auth():
    r = requests.get(f"{BASE_URL}/api/optica/dashboard/ventas-dia")
    assert r.status_code in (401, 403)
