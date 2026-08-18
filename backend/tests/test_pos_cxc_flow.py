"""
Test POS → CxC end-to-end flow for both Finanzas and Óptica.
Verifies caja status mapping, sale creation with CxC, and CxC record persistence.
"""
import os
import pytest
import requests
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def paciente(headers):
    # Buscar cualquier paciente activo
    r = requests.get(f"{API}/pacientes/buscar?q=a", headers=headers)
    assert r.status_code == 200, r.text
    lista = r.json()
    assert isinstance(lista, list) and len(lista) > 0, "No hay pacientes"
    return lista[0]


# ============== 1. Caja Estado ==============
def test_caja_estado_returns_caja_abierta(headers):
    r = requests.get(f"{API}/caja/estado", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "caja_abierta" in data
    # La caja de prueba está abierta según el prompt
    print(f"Caja abierta: {data['caja_abierta']}")


# ============== 2. Responsables CxC ==============
def test_responsables_disponibles(headers):
    r = requests.get(f"{API}/cuentas-cobrar/responsables", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json().get("data", [])
    assert len(data) > 0, "Debe haber al menos un responsable"


# ============== 3. POS Finanzas: venta con CxC ==============
def test_venta_finanzas_con_cxc_crea_cuenta_cobrar(headers, paciente):
    # Get bodega POS
    r = requests.get(f"{API}/ventas/bodega-pos", headers=headers)
    assert r.status_code == 200, r.text
    bodega = r.json()
    bodega_id = bodega["bodega_id"]

    # Buscar productos con stock
    r = requests.get(f"{API}/ventas/productos?bodega_id={bodega_id}&limit=10", headers=headers)
    assert r.status_code == 200, r.text
    productos = r.json()
    productos_con_stock = [p for p in productos if p.get("existencia", 0) > 0 or p.get("existencia") == -1]
    if not productos_con_stock:
        pytest.skip("No hay productos con stock disponible en bodega POS")
    prod = productos_con_stock[0]

    # Obtener responsable
    r = requests.get(f"{API}/cuentas-cobrar/responsables", headers=headers)
    responsables = r.json().get("data", [])
    if not responsables:
        pytest.skip("No hay responsables configurados")
    responsable = responsables[0]

    # Crear venta con CxC
    venta_data = {
        "bodega_id": bodega_id,
        "paciente_id": paciente["id"],
        "paciente_nombre": paciente.get("nombre") or paciente.get("nombre_completo"),
        "items": [{
            "producto_id": prod["id"],
            "codigo": prod["codigo"],
            "nombre": prod["nombre"],
            "cantidad": 1,
            "precio_unitario": prod["precio_venta"],
            "descuento": 0,
            "subtotal": prod["precio_venta"],
            "afecto_iva": prod.get("afecto_iva", True)
        }],
        "formas_pago": [{
            "metodo": "Cuenta por Cobrar",
            "monto": prod["precio_venta"] * 1.12,  # con IVA
            "referencia": None,
            "tipo_pagador_id": responsable["id"],
            "tipo_pagador_nombre": responsable["nombre"]
        }],
        "observaciones": "TEST_POS_CXC"
    }
    r = requests.post(f"{API}/ventas", json=venta_data, headers=headers)
    assert r.status_code in (200, 201), f"Falló venta: {r.status_code} {r.text}"
    venta_resp = r.json()
    print(f"Venta creada: {venta_resp.get('numero_venta')}")
    numero = venta_resp.get("numero_venta")

    # Verificar CxC creada en clínica
    r = requests.get(f"{API}/cuentas-cobrar/clinica?search={numero}", headers=headers)
    assert r.status_code == 200, r.text
    cxcs = r.json().get("data", [])
    assert len(cxcs) > 0, f"No se encontró CxC para la venta {numero}"
    cxc = cxcs[0]
    assert cxc["origen"] == "clinica"
    assert cxc["paciente_id"] == paciente["id"]
    print(f"CxC creada: {cxc.get('numero_cuenta') or cxc.get('id')} monto={cxc['monto_total']}")


# ============== 4. POS Óptica ==============
def test_optica_pos_sale_payload_matches_backend(headers, paciente):
    """Verifica que el payload que envía OpticaPOS.js sea aceptado por el backend"""
    # Buscar frames disponibles
    r = requests.get(f"{API}/optica/frames?is_active=true", headers=headers)
    assert r.status_code == 200, r.text
    frames = r.json().get("data") or r.json()
    frames_con_stock = [f for f in frames if f.get("stock", 0) > 0]
    if not frames_con_stock:
        pytest.skip("No hay armazones con stock")
    frame = frames_con_stock[0]

    # Payload EXACTAMENTE como lo envía OpticaPOS.js
    venta_data = {
        "patient_id": paciente["id"],
        "patient_name": f"{paciente.get('primer_nombre','')} {paciente.get('primer_apellido','')}".strip(),
        "items": [{
            "type": "frame",
            "product_id": frame["id"],
            "quantity": 1,
            "unit_price": frame.get("sale_price", 0),
            "subtotal": frame.get("sale_price", 0)
        }],
        "subtotal": frame.get("sale_price", 0),
        "discount": 0,
        "total": frame.get("sale_price", 0),
        "payments": [],
        "notes": "TEST_OPTICA_POS",
        "prescription": None,
        "created_by": None,
        "created_by_name": None,
        "tiene_cxc": True,
        "monto_cxc": frame.get("sale_price", 0)
    }
    r = requests.post(f"{API}/optica/sales/v2", json=venta_data, headers=headers)
    print(f"OPTICA SALE V2 status={r.status_code} body={r.text[:400]}")
    assert r.status_code in (200, 201), f"OpticaPOS V2 payload rechazado por backend: {r.status_code} - {r.text}"


def test_cxc_optica_directly_created(headers, paciente):
    """Prueba directa del endpoint POST /cuentas-cobrar/optica"""
    payload = {
        "paciente_id": paciente["id"],
        "paciente_nombre": f"{paciente.get('primer_nombre','')} {paciente.get('primer_apellido','')}".strip() or "TEST",
        "monto_total": 500.0,
        "concepto": "TEST_CXC_OPTICA_direct",
        "venta_id": None,
        "notas": "Test directo"
    }
    r = requests.post(f"{API}/cuentas-cobrar/optica", json=payload, headers=headers)
    assert r.status_code in (200, 201), f"Falló CxC óptica: {r.status_code} {r.text}"
    data = r.json()
    assert data["origen"] == "optica"
    assert data["monto_total"] == 500.0
    assert data["paciente_id"] == paciente["id"]

    # Verificar que aparece en el listado
    r = requests.get(f"{API}/cuentas-cobrar/optica?search=TEST_CXC_OPTICA_direct", headers=headers)
    assert r.status_code == 200
    cuentas = r.json().get("data", [])
    assert any(c.get("concepto") == "TEST_CXC_OPTICA_direct" for c in cuentas), "CxC no aparece en listado"
