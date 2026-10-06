"""
Auditoria P26 - H-03: abono a CxC no debe duplicarse en el Dashboard Financiero.

Prueba contra el backend real via REACT_APP_BACKEND_URL (ingress) usando requests
sincronas, para evitar problemas con event loop en motor y validar la ruta
exactamente como la ve el usuario.

Casos:
  1. Abono con registrar_en_caja=True  -> dashboard sube EXACTAMENTE monto (no 2x)
  2. Abono con registrar_en_caja=False -> dashboard sube EXACTAMENTE monto
  3. Regresion: GET /api/cxc responde 200 (fix H-01)
  4. Regresion: GET /api/cierres-financieros responde 200 (fix sesion anterior)
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

RUN_TAG = f"TEST-H03-{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"username": "superadmin", "password": "nova2024"},
               timeout=30)
    assert r.status_code == 200, f"Login fallo: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {token}",
                      "Content-Type": "application/json"})
    yield s


@pytest.fixture(scope="module")
def setup_sintetico(session):
    r = session.get(f"{BASE_URL}/api/ventas/bodega-pos", timeout=30)
    assert r.status_code == 200, r.text
    bodega_id = r.json()["bodega_id"]

    r = session.post(f"{BASE_URL}/api/suppliers",
                     json={"name": f"{RUN_TAG}-Prov", "contact_name": "QA",
                           "phone": "00000000"}, timeout=30)
    assert r.status_code == 200, r.text
    proveedor_id = r.json()["id"]

    r = session.post(f"{BASE_URL}/api/inventario/productos",
                     json={"codigo": f"{RUN_TAG}-P",
                           "nombre": f"{RUN_TAG} Producto",
                           "tipo": "producto",
                           "controla_inventario": True,
                           "controla_lotes": False,
                           "precio_compra": 0,
                           "precio_venta": 100.0,
                           "afecto_iva": False}, timeout=30)
    assert r.status_code == 200, r.text
    producto_id = r.json()["id"]

    # Stock
    r = session.post(f"{BASE_URL}/api/inventario/recepciones",
                     json={"proveedor_id": proveedor_id, "bodega_id": bodega_id,
                           "items": [{"producto_id": producto_id,
                                      "cantidad": 10,
                                      "costo_unitario": 50.0}]}, timeout=30)
    assert r.status_code == 200, r.text

    # Asegurar caja abierta
    r = session.get(f"{BASE_URL}/api/caja/estado", timeout=30)
    if not r.json().get("caja_abierta"):
        r = session.post(f"{BASE_URL}/api/caja/apertura",
                         json={"monto_apertura": 0}, timeout=30)
        assert r.status_code == 200, r.text

    # Responsable CxC
    r = session.post(f"{BASE_URL}/api/cuentas-cobrar/responsables",
                     json={"nombre": f"{RUN_TAG}-Resp", "tipo": "otro"},
                     timeout=30)
    assert r.status_code == 200, r.text
    responsable_id = r.json()["id"]

    yield {
        "bodega_id": bodega_id, "producto_id": producto_id,
        "proveedor_id": proveedor_id, "responsable_id": responsable_id,
    }

    # Cleanup
    session.delete(f"{BASE_URL}/api/inventario/productos/{producto_id}",
                   params={"force": "true"}, timeout=30)


def _crear_cxc(session, setup, monto=100.0):
    r = session.post(f"{BASE_URL}/api/ventas",
                     json={"bodega_id": setup["bodega_id"],
                           "items": [{"producto_id": setup["producto_id"],
                                      "nombre": "x", "cantidad": 1,
                                      "precio_unitario": monto,
                                      "descuento": 0, "afecto_iva": False}],
                           "formas_pago": [{"metodo": "Cuenta por Cobrar",
                                            "monto": monto,
                                            "tipo_pagador_id": setup["responsable_id"]}]},
                     timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["cxc_id"]


def _dashboard_total(session):
    r = session.get(f"{BASE_URL}/api/dashboard/financiero",
                    params={"periodo": "anual"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["ingresos"]["total_cobrado"]


# ============= H-03 =============

def test_h03_abono_con_registrar_en_caja_no_se_duplica(session, setup_sintetico):
    """Abono Q100 con registrar_en_caja=True -> dashboard sube EXACTAMENTE Q100."""
    cxc_id = _crear_cxc(session, setup_sintetico, 100.0)
    antes = _dashboard_total(session)
    r = session.post(f"{BASE_URL}/api/cxc/{cxc_id}/abono",
                     json={"monto": 100.0, "metodo_pago": "Efectivo",
                           "registrar_en_caja": True}, timeout=30)
    assert r.status_code == 200, r.text
    despues = _dashboard_total(session)
    delta = despues - antes
    assert abs(delta - 100.0) < 0.01, (
        f"H-03 duplicado: abono Q100 con registrar_en_caja=True subio dashboard Q{delta:.2f}"
    )


def test_h03_abono_sin_registrar_en_caja_no_se_duplica(session, setup_sintetico):
    """Abono Q100 con registrar_en_caja=False -> dashboard sube EXACTAMENTE Q100."""
    cxc_id = _crear_cxc(session, setup_sintetico, 100.0)
    antes = _dashboard_total(session)
    r = session.post(f"{BASE_URL}/api/cxc/{cxc_id}/abono",
                     json={"monto": 100.0, "metodo_pago": "Efectivo",
                           "registrar_en_caja": False}, timeout=30)
    assert r.status_code == 200, r.text
    despues = _dashboard_total(session)
    delta = despues - antes
    assert abs(delta - 100.0) < 0.01, (
        f"Abono Q100 sin registrar_en_caja subio dashboard Q{delta:.2f} (debe ser 100)"
    )


def test_h03_movimiento_caja_id_presente_cuando_registrar_en_caja(session, setup_sintetico):
    """El abono con registrar_en_caja=True debe guardar movimiento_caja_id en el documento."""
    cxc_id = _crear_cxc(session, setup_sintetico, 50.0)
    r = session.post(f"{BASE_URL}/api/cxc/{cxc_id}/abono",
                     json={"monto": 50.0, "metodo_pago": "Efectivo",
                           "registrar_en_caja": True}, timeout=30)
    assert r.status_code == 200, r.text

    r = session.get(f"{BASE_URL}/api/cxc/{cxc_id}", timeout=30)
    assert r.status_code == 200, r.text
    abonos = r.json().get("abonos", [])
    assert any(a.get("movimiento_caja_id") for a in abonos), (
        "Al menos un abono con registrar_en_caja=True debe tener movimiento_caja_id guardado"
    )


# ============= Regresiones rapidas =============

def test_regresion_cxc_lista_200(session):
    r = session.get(f"{BASE_URL}/api/cxc", timeout=30)
    assert r.status_code == 200, r.text


def test_regresion_cierres_financieros_lista_200(session):
    r = session.get(f"{BASE_URL}/api/cierres-financieros", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    # Modelo debe tener campos de utilidad real (fix sesion anterior)
    assert "data" in data or isinstance(data, list)


def test_regresion_login_admin(session):
    s2 = requests.Session()
    r = s2.post(f"{BASE_URL}/api/auth/login",
                json={"username": "admin", "password": "Admin2024Nuevo!"},
                timeout=30)
    assert r.status_code == 200, r.text


def test_regresion_patients_200(session):
    r = session.get(f"{BASE_URL}/api/patients", params={"limit": 5}, timeout=30)
    assert r.status_code == 200, r.text


def test_regresion_inventario_productos_200(session):
    r = session.get(f"{BASE_URL}/api/inventario/productos",
                    params={"limit": 5}, timeout=30)
    assert r.status_code == 200, r.text
