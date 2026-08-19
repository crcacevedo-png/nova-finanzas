# Tests for POS Óptica → CxC flow ensuring CxC amount = pendiente (not total)
# Bug: total Q550, pago Q200 → CxC should be Q350
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API = f"{BASE_URL}/api"

USER = {"username": "superadmin", "password": "nova2024"}


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json=USER, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def paciente(headers):
    """Buscar paciente 'Juan Pérez' o crear uno de prueba"""
    r = requests.get(f"{API}/pacientes/buscar?search=Juan", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    if data:
        return data[0]
    # Crear si no existe
    payload = {
        "first_name": "Juan",
        "last_name": "Pérez Morales",
        "gender": "masculino",
        "birth_date": "1990-01-15",
        "phone": "55551234",
        "referral_institution": "particular"
    }
    rc = requests.post(f"{API}/patients", json=payload, headers=headers, timeout=15)
    assert rc.status_code == 200, rc.text
    p = rc.json()
    return {
        "id": p["id"],
        "primer_nombre": p["first_name"],
        "primer_apellido": p["last_name"],
        "dpi": p.get("dpi", ""),
        "telefono": p["phone"],
    }


@pytest.fixture(scope="module")
def frame(headers):
    """Crear/obtener un armazón con precio Q550"""
    code = f"TEST-RB-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "brand": "Ray-Ban",
        "code": code,
        "model": "Wayfarer Q550",
        "color": "Negro",
        "cost_price": 300,
        "sale_price": 550,
        "stock": 10
    }
    r = requests.post(f"{API}/optica/frames", json=payload, headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


# Test 1: Búsqueda de pacientes retorna campos en español
def test_buscar_pacientes_returns_spanish_fields(headers):
    r = requests.get(f"{API}/pacientes/buscar?search=Juan", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    if data:
        p = data[0]
        # Campos requeridos para POS Óptica
        assert "primer_nombre" in p, f"Missing primer_nombre. Keys: {list(p.keys())}"
        assert "primer_apellido" in p
        assert "telefono" in p
        assert "dpi" in p
        assert "id" in p


# Test 2: Venta con pago parcial + CxC → monto_cxc correcto
def test_sale_with_partial_payment_creates_cxc_with_pending_amount(headers, paciente, frame):
    """Total Q550, Pago efectivo Q200, CxC debe ser Q350 (no Q550)"""
    total = 550.0
    pago_efectivo = 200.0
    pendiente_esperado = 350.0

    venta_payload = {
        "patient_id": paciente["id"],
        "patient_name": f"{paciente['primer_nombre']} {paciente['primer_apellido']}",
        "items": [{
            "type": "frame",
            "product_id": frame["id"],
            "quantity": 1,
            "unit_price": total,
            "subtotal": total
        }],
        "subtotal": total,
        "discount": 0,
        "total": total,
        "payments": [{
            "method": "Efectivo",
            "amount": pago_efectivo,
            "reference": None
        }],
        "notes": "Test P0 CxC monto correcto",
        "tiene_cxc": True,
        "monto_cxc": pendiente_esperado  # ← Debe ser 350, no 550
    }

    r = requests.post(f"{API}/optica/sales/v2", json=venta_payload, headers=headers, timeout=20)
    assert r.status_code == 200, r.text
    venta = r.json()

    # Validaciones de la venta
    assert venta["total"] == total
    assert venta["total_paid"] == pago_efectivo
    assert abs(venta["balance_due"] - pendiente_esperado) < 0.01, \
        f"balance_due esperado {pendiente_esperado}, obtenido {venta['balance_due']}"
    assert venta["status"] == "pendiente"
    assert venta["monto_cxc"] == pendiente_esperado

    # Crear la CxC como lo hace el frontend
    cxc_payload = {
        "origen": "optica",
        "paciente_id": paciente["id"],
        "paciente_nombre": f"{paciente['primer_nombre']} {paciente['primer_apellido']}",
        "monto_total": pendiente_esperado,  # ← Q350
        "concepto": f"Venta Óptica #{venta.get('sale_number')} - frame",
        "venta_id": venta["id"],
        "notas": "Test"
    }
    rc = requests.post(f"{API}/cuentas-cobrar/optica", json=cxc_payload, headers=headers, timeout=15)
    assert rc.status_code in (200, 201), rc.text
    cxc = rc.json()

    # Validar CxC creada con monto correcto
    assert abs(cxc["monto_total"] - pendiente_esperado) < 0.01, \
        f"CxC monto_total esperado {pendiente_esperado}, obtenido {cxc['monto_total']}"
    assert cxc["monto_total"] != total, "BUG: CxC tiene el TOTAL en lugar del PENDIENTE"
    assert cxc["paciente_id"] == paciente["id"]

    # Cleanup: cancelar venta para restaurar stock
    requests.put(f"{API}/optica/sales/{venta['id']}/cancel", headers=headers, timeout=10)


# Test 3: CxC full (sin pago parcial) → monto = total
def test_sale_full_cxc_no_partial(headers, paciente, frame):
    """Cuando no hay pago parcial, CxC = total completo"""
    total = 550.0
    venta_payload = {
        "patient_id": paciente["id"],
        "patient_name": f"{paciente['primer_nombre']} {paciente['primer_apellido']}",
        "items": [{
            "type": "frame", "product_id": frame["id"],
            "quantity": 1, "unit_price": total, "subtotal": total
        }],
        "subtotal": total, "discount": 0, "total": total,
        "payments": [],
        "tiene_cxc": True,
        "monto_cxc": total
    }
    r = requests.post(f"{API}/optica/sales/v2", json=venta_payload, headers=headers, timeout=20)
    assert r.status_code == 200, r.text
    venta = r.json()
    assert venta["total_paid"] == 0
    assert abs(venta["balance_due"] - total) < 0.01
    assert venta["monto_cxc"] == total

    requests.put(f"{API}/optica/sales/{venta['id']}/cancel", headers=headers, timeout=10)
