# Backend tests for POS Médico/Doctor requirement
# Verifies:
#  - /api/doctors/search returns results for autocomplete
#  - /api/ventas (Clinica POS) persists medico_id/medico_nombre
#  - /api/optica/sales/v2 persists doctor_id/doctor_name
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    tk = r.json().get("access_token") or r.json().get("token")
    assert tk
    return tk


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def ensure_caja_open(headers):
    # Ensure clinic caja is open (per request guidance)
    try:
        requests.post(f"{BASE_URL}/api/caja/apertura", json={"origen": "clinica", "monto_inicial": 0}, headers=headers)
    except Exception:
        pass
    yield


# ---------- Doctors autocomplete ----------

def test_doctors_search_endpoint(headers):
    r = requests.get(f"{BASE_URL}/api/doctors/search", params={"q": "ca"}, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    # Expect at least one doctor matching 'ca' (Dr. Carlos Méndez)
    assert any("carlos" in (d.get("name", "").lower()) for d in data), f"No Dr. Carlos found: {data}"


def test_doctors_search_min_chars(headers):
    # q with 2 letters should still return list
    r = requests.get(f"{BASE_URL}/api/doctors/search", params={"q": "me"}, headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------- Clinic POS: medico_id/medico_nombre persistence ----------

def _get_doctor_carlos(headers):
    r = requests.get(f"{BASE_URL}/api/doctors/search", params={"q": "carlos"}, headers=headers)
    assert r.status_code == 200
    doctors = r.json()
    doc = next((d for d in doctors if "carlos" in d.get("name", "").lower()), None)
    assert doc is not None, "No Dr. Carlos encontrado"
    return doc


def _get_patient_carlos(headers):
    r = requests.get(f"{BASE_URL}/api/patients", params={"search": "carlos", "limit": 10}, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    patients = data if isinstance(data, list) else data.get("data", [])
    p = next((pt for pt in patients if "carlos" in (pt.get("full_name") or (pt.get("first_name","")+" "+pt.get("last_name",""))).lower()), None)
    assert p is not None, f"No patient Carlos found in {len(patients)} results"
    return p


def test_crear_venta_clinica_con_medico(headers, ensure_caja_open):
    doctor = _get_doctor_carlos(headers)
    patient = _get_patient_carlos(headers)
    patient_nombre = patient.get("full_name") or (patient.get("first_name","")+" "+patient.get("last_name","")).strip()

    bod_res = requests.get(f"{BASE_URL}/api/ventas/bodega-pos", headers=headers)
    assert bod_res.status_code == 200, bod_res.text
    bodega_id = bod_res.json()["bodega_id"]

    prod_res = requests.get(
        f"{BASE_URL}/api/ventas/productos",
        params={"bodega_id": bodega_id, "limit": 50},
        headers=headers,
    )
    productos = prod_res.json()
    producto = next((p for p in productos if p["existencia"] > 0 and p["precio_venta"] > 0), None)
    if not producto:
        pytest.skip("Sin producto con stock para probar")

    precio = producto["precio_venta"]
    afecto_iva = producto["afecto_iva"]
    subtotal = precio
    total = round(subtotal + (subtotal * 0.12 if afecto_iva else 0), 2)

    payload = {
        "bodega_id": bodega_id,
        "paciente_id": patient["id"],
        "paciente_nombre": patient_nombre,
        "medico_id": doctor["id"],
        "medico_nombre": doctor["name"],
        "items": [{
            "producto_id": producto["id"],
            "codigo": producto["codigo"],
            "nombre": producto["nombre"],
            "cantidad": 1,
            "precio_unitario": precio,
            "descuento": 0,
            "subtotal": subtotal,
            "afecto_iva": afecto_iva,
        }],
        "formas_pago": [{"metodo": "Efectivo", "monto": total, "referencia": None}],
        "observaciones": "TEST_medico_clinica",
    }
    r = requests.post(f"{BASE_URL}/api/ventas", json=payload, headers=headers)
    assert r.status_code == 200, f"Crear venta falló: {r.status_code} {r.text}"
    venta = r.json()
    venta_id = venta["id"]

    # Response assertion
    assert venta.get("medico_id") == doctor["id"], f"medico_id mismatch: {venta.get('medico_id')} vs {doctor['id']}"
    assert venta.get("medico_nombre") == doctor["name"]

    # GET to confirm persistence
    r2 = requests.get(f"{BASE_URL}/api/ventas/{venta_id}", headers=headers)
    assert r2.status_code == 200
    v2 = r2.json()
    assert v2.get("medico_id") == doctor["id"]
    assert v2.get("medico_nombre") == doctor["name"]


def test_crear_venta_clinica_sin_paciente_sin_medico(headers, ensure_caja_open):
    # Cliente General: sin paciente, sin médico, debe permitirse
    bod_res = requests.get(f"{BASE_URL}/api/ventas/bodega-pos", headers=headers)
    bodega_id = bod_res.json()["bodega_id"]
    prod_res = requests.get(
        f"{BASE_URL}/api/ventas/productos",
        params={"bodega_id": bodega_id, "limit": 50},
        headers=headers,
    )
    producto = next((p for p in prod_res.json() if p["existencia"] > 0 and p["precio_venta"] > 0), None)
    if not producto:
        pytest.skip("Sin producto con stock")
    precio = producto["precio_venta"]
    afecto_iva = producto["afecto_iva"]
    total = round(precio + (precio * 0.12 if afecto_iva else 0), 2)
    payload = {
        "bodega_id": bodega_id,
        "paciente_id": None,
        "paciente_nombre": None,
        "items": [{
            "producto_id": producto["id"],
            "codigo": producto["codigo"],
            "nombre": producto["nombre"],
            "cantidad": 1,
            "precio_unitario": precio,
            "descuento": 0,
            "subtotal": precio,
            "afecto_iva": afecto_iva,
        }],
        "formas_pago": [{"metodo": "Efectivo", "monto": total, "referencia": None}],
        "observaciones": "TEST_sin_medico_cliente_general",
    }
    r = requests.post(f"{BASE_URL}/api/ventas", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    v = r.json()
    assert v.get("medico_id") in (None, "")
    assert v.get("medico_nombre") in (None, "")


# ---------- Óptica POS /sales/v2: doctor_id/doctor_name persistence ----------

def test_crear_venta_optica_v2_con_doctor(headers):
    doctor = _get_doctor_carlos(headers)
    patient = _get_patient_carlos(headers)

    # Get an optica frame with stock
    frames_res = requests.get(f"{BASE_URL}/api/optica/frames", headers=headers)
    assert frames_res.status_code == 200
    frames_data = frames_res.json()
    frames = frames_data if isinstance(frames_data, list) else frames_data.get("data", [])
    frame = next((f for f in frames if f.get("stock", 0) > 0 and f.get("is_active", True)), None)
    if not frame:
        pytest.skip("Sin armazones de óptica con stock")

    price = frame.get("sale_price", 0)
    if price <= 0:
        pytest.skip("Armazón sin precio de venta")

    subtotal = price
    total = subtotal
    payload = {
        "patient_id": patient["id"],
        "patient_name": patient.get("full_name") or (patient.get("first_name","")+" "+patient.get("last_name","")).strip(),
        "doctor_id": doctor["id"],
        "doctor_name": doctor["name"],
        "items": [{
            "type": "frame",
            "product_id": frame["id"],
            "name": f"{frame.get('brand','')} {frame.get('model','')}".strip(),
            "quantity": 1,
            "unit_price": price,
            "subtotal": subtotal,
        }],
        "subtotal": subtotal,
        "discount": 0,
        "total": total,
        "payments": [{"method": "Efectivo", "amount": total, "reference": ""}],
        "notes": "TEST_medico_optica",
        "tiene_cxc": False,
        "monto_cxc": 0,
    }
    r = requests.post(f"{BASE_URL}/api/optica/sales/v2", json=payload, headers=headers)
    assert r.status_code in (200, 201), f"Crear venta óptica v2 falló: {r.status_code} {r.text}"
    sale = r.json()
    sale_id = sale.get("id") or sale.get("sale_id")
    # Create response may be minimal; verify persistence via GET
    r2 = requests.get(f"{BASE_URL}/api/optica/sales/{sale_id}", headers=headers)
    assert r2.status_code == 200, f"GET sale falló: {r2.status_code} {r2.text}"
    s2 = r2.json()
    assert s2.get("doctor_id") == doctor["id"], f"doctor_id persistido: {s2.get('doctor_id')} esperado {doctor['id']}"
    assert s2.get("doctor_name") == doctor["name"]
