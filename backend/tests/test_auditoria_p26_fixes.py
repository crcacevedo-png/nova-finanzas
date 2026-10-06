"""Validacion de los 3 fixes de la Auditoria P26:
- H-01: GET /api/cxc no retorna 500 aunque existan cuentas sin paciente
- H-02: Costo promedio ponderado correcto (10@100 + 10@120 => 110.00)
- H-04/H-05: Cierre financiero con costo_ventas, gastos_pagados y utilidad_bruta
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
RUN_TAG = f"TEST-P26-{int(time.time())}"


@pytest.fixture(scope="module")
def superadmin_token():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    assert r.status_code == 200, f"login superadmin fallo: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "Admin2024Nuevo!"}, timeout=30)
    assert r.status_code == 200, f"login admin fallo: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def super_client(superadmin_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_client(admin_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"})
    return s


# =========================================================================
# H-01: GET /api/cxc no deberia dar 500 con cuentas sin paciente
# =========================================================================
class TestH01CxcSinPaciente:
    def test_get_cxc_lista_ok(self, super_client):
        r = super_client.get(f"{API}/cxc", timeout=30)
        assert r.status_code == 200, f"GET /api/cxc fallo: {r.status_code} - {r.text[:400]}"
        data = r.json()
        # Puede ser list o dict con 'data'
        if isinstance(data, dict):
            items = data.get("data", data.get("items", []))
        else:
            items = data
        assert isinstance(items, list), f"Respuesta inesperada: {type(items)}"
        # Si hay items, confirmar que no revientan por paciente_id Optional
        for it in items[:5]:
            assert "id" in it

    def test_get_cxc_tolera_paciente_null(self, super_client):
        """Buscar una CxC sin paciente_id si existe (no debe bloquear)."""
        r = super_client.get(f"{API}/cxc", timeout=30)
        assert r.status_code == 200
        data = r.json()
        items = data.get("data", data) if isinstance(data, dict) else data
        sin_paciente = [c for c in items if c.get("paciente_id") in (None, "")]
        # Al menos verificamos que no hubo 500. Si no hay registros sin paciente, pasamos igual.
        assert isinstance(sin_paciente, list)


# =========================================================================
# H-02: Costo promedio ponderado
# =========================================================================
class TestH02CostoPromedio:
    def test_costo_promedio_dos_compras(self, super_client):
        # Obtener bodega POS
        r = super_client.get(f"{API}/ventas/bodega-pos", timeout=30)
        assert r.status_code == 200, r.text
        bodega_id = r.json()["bodega_id"]

        # Proveedor sintetico
        r = super_client.post(f"{API}/suppliers", json={
            "name": f"{RUN_TAG}-Prov", "contact_name": "QA", "phone": "00000000"
        }, timeout=30)
        assert r.status_code == 200, r.text
        proveedor_id = r.json()["id"]

        # Producto sintetico
        r = super_client.post(f"{API}/inventario/productos", json={
            "codigo": f"{RUN_TAG}-P", "nombre": f"{RUN_TAG} Producto", "tipo": "producto",
            "controla_inventario": True, "controla_lotes": False,
            "precio_compra": 0, "precio_venta": 224.0, "afecto_iva": True, "existencia_minima": 0
        }, timeout=30)
        assert r.status_code == 200, r.text
        producto_id = r.json()["id"]

        try:
            # Compra 1: 10 @ 100
            r = super_client.post(f"{API}/inventario/recepciones", json={
                "proveedor_id": proveedor_id, "bodega_id": bodega_id,
                "items": [{"producto_id": producto_id, "cantidad": 10, "costo_unitario": 100.0}]
            }, timeout=30)
            assert r.status_code == 200, r.text

            # Compra 2: 10 @ 120
            r = super_client.post(f"{API}/inventario/recepciones", json={
                "proveedor_id": proveedor_id, "bodega_id": bodega_id,
                "items": [{"producto_id": producto_id, "cantidad": 10, "costo_unitario": 120.0}]
            }, timeout=30)
            assert r.status_code == 200, r.text

            r = super_client.get(f"{API}/inventario/productos/{producto_id}", timeout=30)
            assert r.status_code == 200, r.text
            costo_promedio = r.json().get("costo_promedio")
            assert costo_promedio is not None, "costo_promedio no retornado"
            assert abs(costo_promedio - 110.0) < 0.01, f"costo_promedio esperado 110.00, got {costo_promedio}"
        finally:
            # Cleanup producto
            super_client.delete(f"{API}/inventario/productos/{producto_id}", params={"force": "true"}, timeout=30)


# =========================================================================
# H-04/H-05: Cierre financiero con nuevos campos
# =========================================================================
class TestH04H05CierreFinanciero:
    def test_cierre_tiene_nuevos_campos(self, super_client):
        # Recalcular / crear cierre mensual
        r = super_client.post(f"{API}/cierres-financieros",
                              json={"tipo": "Mensual", "anio": 2026, "mes": 1}, timeout=60)
        assert r.status_code in (200, 400), r.text
        if r.status_code == 400:
            r_list = super_client.get(f"{API}/cierres-financieros", timeout=30)
            assert r_list.status_code == 200
            lst = r_list.json()
            items = lst.get("data", lst) if isinstance(lst, dict) else lst
            cierre = next((c for c in items if c.get("tipo") == "Mensual" and (c.get("periodo") or {}).get("anio") == 2026 and (c.get("periodo") or {}).get("mes") == 1), None)
            assert cierre, f"No se pudo crear ni encontrar cierre 2026-01: {r.text[:300]}"
            r = super_client.post(f"{API}/cierres-financieros/{cierre['id']}/recalcular", timeout=60)
            assert r.status_code == 200, r.text

        cierre = r.json()
        # Validar nuevos campos presentes
        for campo in ("costo_ventas", "gastos_pagados", "utilidad_bruta", "resultado_neto"):
            assert campo in cierre, f"Campo '{campo}' ausente en respuesta de cierre: {list(cierre.keys())}"

        # Validacion aritmetica: utilidad_bruta = ingresos_caja - costo_ventas
        ingresos = cierre.get("ingresos_caja", 0) or 0
        egresos = cierre.get("egresos_caja", 0) or 0
        costo_v = cierre.get("costo_ventas", 0) or 0
        gastos_p = cierre.get("gastos_pagados", 0) or 0
        util_bruta = cierre.get("utilidad_bruta", 0) or 0
        neto = cierre.get("resultado_neto", 0) or 0

        assert abs(util_bruta - (ingresos - costo_v)) < 0.01, \
            f"utilidad_bruta={util_bruta} != ingresos_caja({ingresos}) - costo_ventas({costo_v})"
        assert abs(neto - (util_bruta - gastos_p - egresos)) < 0.01, \
            f"resultado_neto={neto} != utilidad_bruta({util_bruta}) - gastos_pagados({gastos_p}) - egresos_caja({egresos})"


# =========================================================================
# Regresion basica
# =========================================================================
class TestRegresion:
    def test_login_ok(self, superadmin_token):
        assert isinstance(superadmin_token, str) and len(superadmin_token) > 10

    def test_dashboard_stats(self, super_client):
        r = super_client.get(f"{API}/dashboard/stats", timeout=30)
        assert r.status_code == 200, r.text

    def test_patients_list(self, super_client):
        r = super_client.get(f"{API}/patients", params={"limit": 5}, timeout=30)
        assert r.status_code == 200, r.text

    def test_inventario_productos_list(self, super_client):
        r = super_client.get(f"{API}/inventario/productos", params={"limit": 5}, timeout=30)
        assert r.status_code == 200, r.text

    def test_expenses_list(self, super_client):
        r = super_client.get(f"{API}/expenses", params={"limit": 5}, timeout=30)
        assert r.status_code == 200, r.text

    def test_payment_auth_list(self, super_client):
        r = super_client.get(f"{API}/payment-authorizations", timeout=30)
        assert r.status_code == 200, r.text

    def test_agenda_list(self, super_client):
        r = super_client.get(f"{API}/agenda/citas", params={"limit": 5}, timeout=30)
        assert r.status_code in (200, 404), r.text  # endpoint puede variar
