# /app/backend/tests/test_auditoria_p26_invariantes.py
"""
Auditoria Prompt 26 - Invariantes financieros (INV-31 a INV-47).
Ejecuta contra el backend real con datos sinteticos (prefijo AUD26-TEST-),
purgados automaticamente en el fixture de limpieza.

IMPORTANTE: Varios de estos tests documentan el estado ACTUAL del sistema
(algunos fallan a proposito, marcados con @pytest.mark.xfail) porque la
auditoria P26 detecta hallazgos pendientes de aprobacion/correccion por el
SuperAdmin (ver /app/docs/auditoria/P26_informe.md). NO modificar estos
xfail a pasar sin haber aplicado la correccion correspondiente primero.
"""
import pytest
import uuid


RUN_TAG = uuid.uuid4().hex[:8]


@pytest.fixture
async def auditoria_setup(auth_client):
    """Crea bodega POS real + proveedor + producto sinteticos y limpia al final."""
    r = await auth_client.get("/api/ventas/bodega-pos")
    assert r.status_code == 200
    bodega_id = r.json()["bodega_id"]

    r = await auth_client.post("/api/suppliers", json={
        "name": f"AUD26-TEST-Proveedor-{RUN_TAG}", "contact_name": "QA", "phone": "00000000"
    })
    assert r.status_code == 200
    proveedor_id = r.json()["id"]

    r = await auth_client.post("/api/inventario/productos", json={
        "codigo": f"AUD26-TEST-PROD-{RUN_TAG}",
        "nombre": f"AUD26 TEST Producto {RUN_TAG}",
        "tipo": "producto",
        "controla_inventario": True,
        "controla_lotes": False,
        "precio_compra": 0,
        "precio_venta": 224.0,
        "afecto_iva": True
    })
    assert r.status_code == 200
    producto_id = r.json()["id"]

    yield {"bodega_id": bodega_id, "proveedor_id": proveedor_id, "producto_id": producto_id}

    await auth_client.delete(f"/api/inventario/productos/{producto_id}", params={"force": "true"})


@pytest.mark.asyncio
@pytest.mark.xfail(reason="H-02: recalcular_costo_promedio cuenta la cantidad nueva 2 veces (ver P26_informe.md)")
async def test_inv33_costo_promedio_ponderado(auth_client, auditoria_setup):
    """INV-33: el costo promedio tras cada entrada = recalculado desde el kardex completo."""
    producto_id = auditoria_setup["producto_id"]
    bodega_id = auditoria_setup["bodega_id"]
    proveedor_id = auditoria_setup["proveedor_id"]

    for cantidad, costo in [(10, 100.0), (10, 120.0)]:
        r = await auth_client.post("/api/inventario/recepciones", json={
            "proveedor_id": proveedor_id, "bodega_id": bodega_id,
            "items": [{"producto_id": producto_id, "cantidad": cantidad, "costo_unitario": costo}]
        })
        assert r.status_code == 200, r.text

    r = await auth_client.get(f"/api/inventario/productos/{producto_id}")
    assert r.status_code == 200
    costo_promedio = r.json()["costo_promedio"]
    assert abs(costo_promedio - 110.0) < 0.01, f"Costo promedio esperado 110.00, obtenido {costo_promedio}"


@pytest.mark.asyncio
async def test_inv42_compra_no_es_gasto(auth_client, auditoria_setup):
    """INV-42: las compras de inventario NO aparecen como gasto del periodo (hallazgo positivo H-11)."""
    producto_id = auditoria_setup["producto_id"]
    bodega_id = auditoria_setup["bodega_id"]
    proveedor_id = auditoria_setup["proveedor_id"]

    r = await auth_client.post("/api/inventario/recepciones", json={
        "proveedor_id": proveedor_id, "bodega_id": bodega_id,
        "items": [{"producto_id": producto_id, "cantidad": 5, "costo_unitario": 50.0}]
    })
    assert r.status_code == 200, r.text
    assert r.json().get("gasto_id") is None

    r = await auth_client.get("/api/expenses", params={"search": f"AUD26-TEST-{RUN_TAG}"})
    if r.status_code == 200:
        assert r.json().get("data", []) == [], "La recepcion de inventario NO debe generar un gasto"


@pytest.mark.asyncio
@pytest.mark.xfail(reason="H-01: CuentaCobrarResponse exige paciente_id/tipo_pagador_id obligatorios; ventas.py permite None (ver P26_informe.md)")
async def test_inv37_cxc_sin_paciente_no_rompe_api(auth_client, auditoria_setup):
    """INV-37 (prerequisito): una CxC generada por venta sin paciente vinculado debe poder listarse y abonarse sin error 500."""
    bodega_id = auditoria_setup["bodega_id"]
    producto_id = auditoria_setup["producto_id"]

    r = await auth_client.get("/api/caja/estado")
    if not r.json().get("caja_abierta"):
        r = await auth_client.post("/api/caja/apertura", json={"monto_apertura": 0})
        assert r.status_code == 200, r.text

    r = await auth_client.post("/api/ventas", json={
        "bodega_id": bodega_id,
        "items": [{"producto_id": producto_id, "nombre": "x", "cantidad": 1,
                   "precio_unitario": 100.0, "descuento": 0, "afecto_iva": False}],
        "formas_pago": [{"metodo": "Cuenta por Cobrar", "monto": 100.0}]
    })
    assert r.status_code == 200, r.text
    cxc_id = r.json()["cxc_id"]

    r = await auth_client.get("/api/cxc")
    assert r.status_code == 200, f"GET /api/cxc no debe fallar con CxC sin paciente_id: {r.text}"

    r = await auth_client.post(f"/api/cxc/{cxc_id}/abono", json={"monto": 50.0, "metodo_pago": "Efectivo"})
    assert r.status_code == 200, f"Abono no debe fallar con CxC sin paciente_id: {r.text}"


@pytest.mark.asyncio
@pytest.mark.xfail(reason="H-03: dashboard_financiero.py suma el abono dos veces (caja_movimientos + cuentas_por_cobrar.abonos), ver P26_informe.md")
async def test_inv38_abono_no_se_duplica_en_dashboard(auth_client, auditoria_setup):
    """INV-38: ningun abono de CxC se suma dos veces en el estado de resultados."""
    bodega_id = auditoria_setup["bodega_id"]
    producto_id = auditoria_setup["producto_id"]

    r = await auth_client.get("/api/caja/estado")
    if not r.json().get("caja_abierta"):
        await auth_client.post("/api/caja/apertura", json={"monto_apertura": 0})

    r = await auth_client.get("/api/patients", params={"limit": 1})
    pacientes = r.json().get("data", [])
    paciente_id = pacientes[0]["id"] if pacientes else None

    r = await auth_client.post("/api/cuentas-cobrar/responsables", json={
        "nombre": f"AUD26-TEST-Resp-{RUN_TAG}", "tipo": "otro"
    })
    responsable_id = r.json()["id"]

    r = await auth_client.post("/api/ventas", json={
        "bodega_id": bodega_id,
        "paciente_id": paciente_id,
        "items": [{"producto_id": producto_id, "nombre": "x", "cantidad": 1,
                   "precio_unitario": 100.0, "descuento": 0, "afecto_iva": False}],
        "formas_pago": [{"metodo": "Cuenta por Cobrar", "monto": 100.0, "tipo_pagador_id": responsable_id}]
    })
    assert r.status_code == 200, r.text
    cxc_id = r.json()["cxc_id"]

    r = await auth_client.get("/api/dashboard/financiero", params={"periodo": "anual"})
    antes = r.json()["ingresos"]["total_cobrado"]

    r = await auth_client.post(f"/api/cxc/{cxc_id}/abono", json={
        "monto": 100.0, "metodo_pago": "Efectivo", "registrar_en_caja": True
    })
    assert r.status_code == 200, r.text

    r = await auth_client.get("/api/dashboard/financiero", params={"periodo": "anual"})
    despues = r.json()["ingresos"]["total_cobrado"]

    assert abs((despues - antes) - 100.0) < 0.01, (
        f"Un abono de Q100 debe aumentar 'ingresos.total_cobrado' en Q100, aumento en Q{despues - antes:.2f}"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(reason="H-06: POST /payments no verifica autorizacion previa (ver P26_informe.md)")
async def test_inv43_no_pagar_sin_autorizacion(auth_client):
    """INV-43: ningun gasto pasa a pagado sin autorizacion previa registrada."""
    r = await auth_client.post("/api/expenses", json={
        "name": f"AUD26-TEST-Gasto-{RUN_TAG}", "type": "variable", "amount": 50.0, "date": "2026-08-01"
    })
    assert r.status_code == 200, r.text
    expense_id = r.json()["id"]

    # Intento de pago DIRECTO sin ninguna autorizacion previa en payment_authorizations
    r = await auth_client.post("/api/payments", json={
        "expense_id": expense_id, "amount": 50.0, "date": "2026-08-01", "method": "Efectivo"
    })
    assert r.status_code != 200, "No deberia poder pagarse un gasto sin autorizacion previa"

    await auth_client.delete(f"/api/expenses/{expense_id}")
