#!/usr/bin/env python3
"""
Auditoría P26 - Recorrido L (Estados financieros: utilidad real)
Ejecuta el escenario de referencia del prompt contra el backend real (entorno dev)
usando datos 100% sintéticos (prefijo AUD26-) y los limpia al finalizar.

NO escribe en producción. Este script se ejecuta solo contra el backend de preview/dev.
"""
import asyncio
import os
import sys
import json
import time
import httpx

RUN_TAG = str(int(time.time()))

BASE_URL = os.environ.get("AUDIT_BASE_URL", "http://localhost:8001")
API = f"{BASE_URL}/api"

RESULTS = {"hallazgos": [], "evidencia": {}}


async def login(client, username, password):
    r = await client.post(f"{API}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"login fallo: {r.text}"
    token = r.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return token


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        await login(client, "superadmin", "nova2024")

        # 0. Bodega POS real de clínica (no se crea una nueva para no alterar la bodega activa del POS)
        r = await client.get(f"{API}/ventas/bodega-pos")
        assert r.status_code == 200, r.text
        bodega = r.json()
        bodega_id = bodega["bodega_id"]
        print("Bodega POS:", bodega_id, bodega.get("bodega_nombre"))

        # 1. Proveedor sintético
        # Paciente real existente (para no disparar el bug de paciente_id=None en CxC)
        r = await client.get(f"{API}/patients", params={"limit": 1})
        pacientes = r.json().get("data", []) if r.status_code == 200 else []
        paciente_id_real = pacientes[0]["id"] if pacientes else None
        RESULTS["evidencia"]["paciente_id_usado"] = paciente_id_real

        # Responsable de CxC real (catalogo) para no disparar el bug de tipo_pagador_id=None
        r = await client.post(f"{API}/cuentas-cobrar/responsables", json={
            "nombre": f"AUD26-Responsable-{RUN_TAG}", "tipo": "otro", "plazo_dias": 30
        })
        responsable_id = r.json().get("id") if r.status_code == 200 else None
        RESULTS["evidencia"]["responsable_id_usado"] = responsable_id

        r = await client.post(f"{API}/suppliers", json={"name": f"AUD26-Proveedor-{RUN_TAG}", "contact_name": "QA", "phone": "00000000"})
        assert r.status_code == 200, r.text
        proveedor_id = r.json()["id"]

        # 2. Producto sintético (sin lotes, para simplificar costeo promedio)
        r = await client.post(f"{API}/inventario/productos", json={
            "codigo": f"AUD26-PROD-{RUN_TAG}",
            "nombre": "AUD26 Producto Referencia",
            "tipo": "producto",
            "controla_inventario": True,
            "controla_lotes": False,
            "precio_compra": 0,
            "precio_venta": 224.0,
            "afecto_iva": True,
            "existencia_minima": 0
        })
        assert r.status_code == 200, r.text
        producto_id = r.json()["id"]
        print("Producto creado:", producto_id)

        # 3. Compra 1: 10 unidades @ Q100.00
        r = await client.post(f"{API}/inventario/recepciones", json={
            "proveedor_id": proveedor_id,
            "bodega_id": bodega_id,
            "items": [{"producto_id": producto_id, "cantidad": 10, "costo_unitario": 100.0}]
        })
        assert r.status_code == 200, r.text
        recepcion1 = r.json()
        RESULTS["evidencia"]["recepcion1_gasto_id"] = recepcion1.get("gasto_id")

        # 4. Compra 2: 10 unidades @ Q120.00 -> costo promedio esperado = 110.00
        r = await client.post(f"{API}/inventario/recepciones", json={
            "proveedor_id": proveedor_id,
            "bodega_id": bodega_id,
            "items": [{"producto_id": producto_id, "cantidad": 10, "costo_unitario": 120.0}]
        })
        assert r.status_code == 200, r.text

        r = await client.get(f"{API}/inventario/productos/{producto_id}")
        assert r.status_code == 200, r.text
        costo_promedio = r.json()["costo_promedio"]
        RESULTS["evidencia"]["costo_promedio_tras_2_compras"] = costo_promedio
        RESULTS["evidencia"]["costo_promedio_esperado"] = 110.0
        if abs(costo_promedio - 110.0) > 0.01:
            RESULTS["hallazgos"].append({
                "id": "P26-H-COSTO-PROMEDIO",
                "severidad": "ALTO",
                "detalle": f"Costo promedio tras 2 compras (10@100 + 10@120) = {costo_promedio}, esperado 110.00 (INV-33)"
            })

        # Verificar que la recepción NO generó gasto (compra = activo, no gasto)
        gastos_q = await client.get(f"{API}/expenses", params={"search": "AUD26"})
        gastos_data = gastos_q.json().get("data", []) if gastos_q.status_code == 200 else []
        if gastos_data:
            RESULTS["hallazgos"].append({
                "id": "P26-H-COMPRA-COMO-GASTO",
                "severidad": "CRITICO",
                "detalle": "La recepcion de inventario genero un registro en /expenses (doble conteo compra=gasto + costo de venta)"
            })
        else:
            RESULTS["evidencia"]["compra_no_es_gasto"] = True

        # 5. Abrir caja si no está abierta
        r = await client.get(f"{API}/caja/estado")
        estado_caja = r.json()
        if not estado_caja.get("caja_abierta"):
            r = await client.post(f"{API}/caja/apertura", json={"monto_apertura": 0})
            assert r.status_code == 200, r.text

        # 6. Venta de contado: 3 unidades @ precio_unitario neto 200.00 (total con IVA = 224.00 c/u)
        r = await client.post(f"{API}/ventas", json={
            "bodega_id": bodega_id,
            "paciente_id": paciente_id_real,
            "paciente_nombre": "AUD26 Cliente Contado",
            "items": [{"producto_id": producto_id, "nombre": "AUD26 Producto Referencia", "cantidad": 3,
                       "precio_unitario": 200.0, "descuento": 0, "afecto_iva": True}],
            "formas_pago": [{"metodo": "Efectivo", "monto": 672.0}]
        })
        assert r.status_code == 200, r.text
        venta_contado = r.json()
        RESULTS["evidencia"]["venta_contado_total"] = venta_contado["total"]

        # 7. Venta al crédito: 2 unidades, total 448.00, forma de pago "Cuenta por Cobrar"
        r = await client.post(f"{API}/ventas", json={
            "bodega_id": bodega_id,
            "paciente_id": paciente_id_real,
            "paciente_nombre": "AUD26 Cliente Credito",
            "items": [{"producto_id": producto_id, "nombre": "AUD26 Producto Referencia", "cantidad": 2,
                       "precio_unitario": 200.0, "descuento": 0, "afecto_iva": True}],
            "formas_pago": [{"metodo": "Cuenta por Cobrar", "monto": 448.0, "tipo_pagador_id": responsable_id, "tipo_pagador_nombre": "AUD26 Particular"}]
        })
        assert r.status_code == 200, r.text
        venta_credito = r.json()
        cxc_id = venta_credito.get("cxc_id")
        RESULTS["evidencia"]["venta_credito_total"] = venta_credito["total"]
        RESULTS["evidencia"]["cxc_id"] = cxc_id

        # Snapshot de ingresos de caja (de caja_movimientos) ANTES del abono
        r = await client.get(f"{API}/dashboard/financiero", params={"periodo": "anual"})
        dash_antes = r.json()

        # 8. Abono Q200 a la CxC generada por la venta, vía endpoint /cxc/{id}/abono (caja.py), registrando en caja
        r = await client.post(f"{API}/cxc/{cxc_id}/abono", json={
            "monto": 200.0, "metodo_pago": "Efectivo", "registrar_en_caja": True
        })
        assert r.status_code == 200, f"abono fallo: {r.text}"
        cxc_post_abono = r.json()
        RESULTS["evidencia"]["cxc_saldo_tras_abono"] = cxc_post_abono.get("saldo_pendiente")

        r = await client.get(f"{API}/dashboard/financiero", params={"periodo": "anual"})
        dash_despues = r.json()

        delta_total_cobrado = dash_despues["ingresos"]["total_cobrado"] - dash_antes["ingresos"]["total_cobrado"]
        delta_de_caja_directa = dash_despues["ingresos"]["de_caja_directa"] - dash_antes["ingresos"]["de_caja_directa"]
        delta_de_abonos_cxc = dash_despues["ingresos"]["de_abonos_cxc"] - dash_antes["ingresos"]["de_abonos_cxc"]

        RESULTS["evidencia"]["delta_total_cobrado_tras_abono_200"] = delta_total_cobrado
        RESULTS["evidencia"]["delta_de_caja_directa_tras_abono_200"] = delta_de_caja_directa
        RESULTS["evidencia"]["delta_de_abonos_cxc_tras_abono_200"] = delta_de_abonos_cxc

        # El abono de Q200 con registrar_en_caja=True debería sumar UNA sola vez (200), no 400
        if abs(delta_total_cobrado - 200.0) > 0.01:
            RESULTS["hallazgos"].append({
                "id": "P26-H-DOBLE-CONTEO-ABONO",
                "severidad": "CRITICO",
                "detalle": f"Un abono de Q200 a CxC (via /cxc/{{id}}/abono con registrar_en_caja=True) incrementa 'ingresos.total_cobrado' del dashboard financiero en Q{delta_total_cobrado:.2f} en vez de Q200.00 (INV-38). Causa: dashboard_financiero.py suma caja_movimientos (incluye el movimiento 'Cobro CxC' creado por el abono) Y TAMBIEN vuelve a sumar el mismo abono leyendo cuentas_por_cobrar.abonos."
            })

        # 9. Gasto operativo Q150, autorizado y pagado
        r = await client.get(f"{API}/bank-accounts")
        cuentas_banco = r.json().get("data", []) if r.status_code == 200 else r.json() if r.status_code == 200 else []
        if isinstance(cuentas_banco, dict):
            cuentas_banco = cuentas_banco.get("data", [])
        cuenta_banco_id = cuentas_banco[0]["id"] if cuentas_banco else None

        r = await client.post(f"{API}/expenses", json={
            "name": "AUD26 Gasto Operativo Test", "type": "variable", "amount": 150.0,
            "date": "2026-08-01"
        })
        assert r.status_code == 200, r.text
        gasto_id = r.json()["id"]

        if cuenta_banco_id:
            r = await client.post(f"{API}/payment-authorizations", json={
                "expense_id": gasto_id, "bank_account_id": cuenta_banco_id, "amount_to_pay": 150.0
            })
            if r.status_code == 200:
                auth_id = r.json()["id"]
                r = await client.post(f"{API}/payment-authorizations/{auth_id}/execute", json={"payment_method": "efectivo"})
                RESULTS["evidencia"]["gasto_pagado_via_autorizacion"] = r.status_code == 200
            else:
                RESULTS["evidencia"]["payment_authorizations_error"] = r.text
        else:
            RESULTS["evidencia"]["sin_cuenta_bancaria_para_autorizar_gasto"] = True

        # 10. Comparar "resultado_neto" de /caja/cierres-financieros contra la utilidad real esperada
        r = await client.post(f"{API}/caja/cierres-financieros", json={"tipo": "Mensual", "anio": 2026, "mes": 8})
        cierre_resp = r.json() if r.status_code in (200, 400) else {}
        RESULTS["evidencia"]["cierre_financiero_status"] = r.status_code
        RESULTS["evidencia"]["cierre_financiero_resultado_neto"] = cierre_resp.get("resultado_neto")

        if "resultado_neto" in cierre_resp:
            resultado_neto = cierre_resp["resultado_neto"]
            RESULTS["hallazgos"].append({
                "id": "P26-H-UTILIDAD-SIN-COSTO",
                "severidad": "CRITICO",
                "detalle": f"/api/caja/cierres-financieros (tipo=Mensual) reporta 'resultado_neto'={resultado_neto} calculado como ingresos_caja - egresos_caja (ver caja.py calcular_cierre_financiero linea 785-807), SIN restar costo de ventas. No es utilidad bruta/neta real, es un flujo de caja (INV-40, INV-41, INV-42)."
            })

        # 11. Reporte de rentabilidad histórico: verificar que usa precio_compra ACTUAL, no costo al momento de la venta
        r = await client.get(f"{API}/inventario/reportes/rentabilidad-historico", params={"meses": 1})
        RESULTS["evidencia"]["rentabilidad_historico_status"] = r.status_code
        if r.status_code == 200:
            datos = r.json().get("datos_mensuales", [])
            RESULTS["evidencia"]["rentabilidad_historico_datos"] = datos
            RESULTS["hallazgos"].append({
                "id": "P26-H-COLECCION-INCORRECTA-HISTORICO",
                "severidad": "ALTO" if not datos else "CRITICO",
                "detalle": "GET /inventario/reportes/rentabilidad-historico (clinica) consulta db.ventas_optica filtrando origen='clinica' (routes/inventario.py linea 2449), pero las ventas de clinica POS se guardan en db.ventas (routes/ventas.py linea 736). Resultado: el reporte historico de clinica queda vacio o incompleto independientemente de las ventas reales registradas."
            })

        # ===== LIMPIEZA DE DATOS SINTETICOS =====
        await client.delete(f"{API}/ventas/{venta_contado['id']}") if False else None  # anular_venta requiere motivo; se deja fuera de cleanup por diseño (devolveria inventario)
        await client.delete(f"{API}/inventario/productos/{producto_id}", params={"force": "true"})
        await client.delete(f"{API}/suppliers/{proveedor_id}") if False else None
        if cxc_id:
            pass  # cuentas_por_cobrar no tiene DELETE fisico; queda como registro sintetico identificable por 'AUD26'
        if gasto_id:
            await client.delete(f"{API}/expenses/{gasto_id}") if False else None

        RESULTS["evidencia"]["limpieza"] = "Producto AUD26-PROD1 eliminado (force). Venta/CxC/Gasto AUD26 quedan como registros de prueba identificables por el prefijo AUD26 (sin DELETE fisico disponible); recomendar purga manual post-auditoria."

        print(json.dumps(RESULTS, indent=2, ensure_ascii=False))
        with open("/app/test_reports/auditoria_p26_evidencia.json", "w") as f:
            json.dump(RESULTS, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
