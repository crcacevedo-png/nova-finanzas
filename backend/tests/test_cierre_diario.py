# Backend tests: Cierre del Día (diagnóstico consolidado), cron/email webhook, CxC descripcion
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


def _read_env(key):
    with open("/app/backend/.env") as f:
        for line in f:
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"')
    return None


@pytest.fixture(scope="module")
def headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    d = r.json()
    tk = d.get("access_token") or d.get("token")
    return {"Authorization": f"Bearer {tk}", "Content-Type": "application/json"}


def _cierre(headers, fecha=None):
    r = requests.get(f"{BASE_URL}/api/caja/cierre-diario", params={"fecha": fecha} if fecha else None, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Cierre del día: structure & invariants ----------
class TestCierreDiario:
    def test_structure(self, headers):
        d = _cierre(headers)
        for k in ("fecha", "resumen", "cobrado_por_metodo", "por_usuario", "conciliacion_cajas", "ventas"):
            assert k in d
        for k in ("ingreso_facturado", "total_cobrado", "cxc_generada_hoy", "cobrado_de_ventas_hoy",
                  "abonos_cuentas_previas", "egresos", "num_ventas"):
            assert k in d["resumen"]
            assert isinstance(d["resumen"][k], (int, float))
        for m in ("efectivo", "tarjeta", "transferencia", "cheque", "otro"):
            assert m in d["cobrado_por_metodo"]

    def test_devengado_invariant(self, headers):
        d = _cierre(headers)
        r = d["resumen"]
        assert abs(r["ingreso_facturado"] - (r["cobrado_de_ventas_hoy"] + r["cxc_generada_hoy"])) < 0.02, r
        assert abs(r["total_cobrado"] - sum(d["cobrado_por_metodo"].values())) < 0.02
        assert r["num_ventas"] == len(d["ventas"])
        assert abs(sum(u["facturado"] for u in d["por_usuario"]) - r["ingreso_facturado"]) < 0.05

    def test_specific_date(self, headers):
        d = _cierre(headers, "2026-11-02")
        assert d["fecha"] == "2026-11-02"

    def test_empty_past_date(self, headers):
        d = _cierre(headers, "2001-01-01")
        assert d["resumen"]["ingreso_facturado"] == 0
        assert d["ventas"] == []

    def test_invalid_date_returns_4xx(self, headers):
        r = requests.get(f"{BASE_URL}/api/caja/cierre-diario", params={"fecha": "not-a-date"}, headers=headers)
        assert 400 <= r.status_code < 500, f"Expected 4xx got {r.status_code}"

    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/caja/cierre-diario")
        assert r.status_code in (401, 403)

    def test_non_admin_forbidden(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "usuario", "password": "user2024"})
        if r.status_code != 200:
            pytest.skip("usuario login failed")
        tk = r.json().get("access_token") or r.json().get("token")
        r2 = requests.get(f"{BASE_URL}/api/caja/cierre-diario", headers={"Authorization": f"Bearer {tk}"})
        assert r2.status_code == 403
        r3 = requests.post(f"{BASE_URL}/api/caja/cierre-diario/enviar", headers={"Authorization": f"Bearer {tk}"})
        assert r3.status_code == 403


# ---------- Cron webhook ----------
class TestCron:
    def test_cron_no_auth(self):
        r = requests.post(f"{BASE_URL}/api/cron/cierre-diario")
        assert r.status_code == 401

    def test_cron_wrong_secret(self):
        r = requests.post(f"{BASE_URL}/api/cron/cierre-diario", headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401

    def test_cron_ok(self):
        secret = _read_env("WEBHOOK_CRON_SECRET")
        assert secret
        r = requests.post(f"{BASE_URL}/api/cron/cierre-diario", headers={"Authorization": f"Bearer {secret}"})
        assert 200 <= r.status_code < 300, r.text
        assert r.json()["status"] == "accepted"


# ---------- Manual email send ----------
class TestEnvioManual:
    def test_enviar_manual(self, headers):
        r = requests.post(f"{BASE_URL}/api/caja/cierre-diario/enviar", headers=headers, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "message" in d and isinstance(d["destinatarios"], list) and len(d["destinatarios"]) >= 1
        print("ENVIO:", d)


# ---------- CxC descripcion ----------
class TestCxCDescripcion:
    def test_cxc_optica_descripcion(self, headers):
        desc = f"TEST_Lentes progresivos antirreflejo {uuid.uuid4().hex[:6]}"
        payload = {"paciente_id": "TEST_pac", "paciente_nombre": "TEST_Paciente CxC",
                   "monto_total": 100, "monto_pagado": 0, "concepto": "TEST_Concepto", "descripcion": desc}
        r = requests.post(f"{BASE_URL}/api/cuentas-cobrar/optica", json=payload, headers=headers)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c["descripcion"] == desc
        g = requests.get(f"{BASE_URL}/api/cuentas-cobrar/{c['id']}", headers=headers)
        assert g.status_code == 200 and g.json()["descripcion"] == desc
        s = requests.get(f"{BASE_URL}/api/cuentas-cobrar/optica", params={"search": desc[:30]}, headers=headers)
        assert s.status_code == 200
        body = s.json()
        items = body if isinstance(body, list) else (body.get("items") or body.get("cuentas") or body.get("data") or [])
        assert any(i["id"] == c["id"] for i in items), "CxC not found by descripcion search"
        requests.put(f"{BASE_URL}/api/cuentas-cobrar/{c['id']}/anular", params={"motivo": "TEST cleanup"}, headers=headers)

    def test_clinica_pos_cxc_autodescripcion_and_cierre(self, headers):
        bod = requests.get(f"{BASE_URL}/api/ventas/bodega-pos", headers=headers).json()
        prods = requests.get(f"{BASE_URL}/api/ventas/productos", params={"bodega_id": bod["bodega_id"], "limit": 50},
                             headers=headers).json()
        cands = [x for x in prods if x["existencia"] > 2 and x["precio_venta"] > 0]
        if not cands:
            pytest.skip("no product")
        resp = requests.get(f"{BASE_URL}/api/cuentas-cobrar/responsables", headers=headers).json()
        resp_list = resp if isinstance(resp, list) else (resp.get("data") or resp.get("items") or [])
        if not resp_list:
            cr = requests.post(f"{BASE_URL}/api/cuentas-cobrar/responsables",
                               json={"nombre": "TEST_Responsable Cierre", "tipo": "otro"}, headers=headers)
            assert cr.status_code == 200, cr.text
            resp_list = [cr.json()]
        before = _cierre(headers)["resumen"]
        r = None
        for p in cands:
            sub = p["precio_venta"]
            total = round(sub, 2)  # precio incluye IVA
            venta = {"bodega_id": bod["bodega_id"], "items": [{
                "producto_id": p["id"], "codigo": p["codigo"], "nombre": p["nombre"], "cantidad": 1,
                "precio_unitario": sub, "descuento": 0, "subtotal": sub, "afecto_iva": p["afecto_iva"]}],
                "formas_pago": [{"metodo": "Cuenta por Cobrar", "monto": total, "tipo_pagador_id": resp_list[0]["id"]}],
                "observaciones": "TEST_cierre_diario"}
            r = requests.post(f"{BASE_URL}/api/ventas", json=venta, headers=headers)
            if r.status_code == 400 and "caja" in r.text.lower() and "abierta" in r.text.lower():
                pytest.skip("caja no abierta")
            if r.status_code == 200:
                break
        assert r.status_code == 200, r.text
        v = r.json()
        full = requests.get(f"{BASE_URL}/api/ventas/{v['id']}", headers=headers).json()
        cxc_id = full.get("cxc_id") or v.get("cxc_id")
        print("VENTA:", full.get("numero_venta"), "cxc_id:", cxc_id, "total:", total)
        if cxc_id:
            c = requests.get(f"{BASE_URL}/api/cuentas-cobrar/{cxc_id}", headers=headers).json()
            print("CXC descripcion:", c.get("descripcion"))
            assert p["nombre"] in (c.get("descripcion") or ""), c
        after = _cierre(headers)["resumen"]
        assert abs(after["ingreso_facturado"] - before["ingreso_facturado"] - total) < 0.02
        assert abs(after["cxc_generada_hoy"] - before["cxc_generada_hoy"] - total) < 0.02
        # anular -> cierre should drop back
        a = requests.post(f"{BASE_URL}/api/ventas/{v['id']}/anular",
                          json={"motivo": "TEST anulacion cierre", "devolver_inventario": True}, headers=headers)
        assert a.status_code == 200, a.text
        final = _cierre(headers)["resumen"]
        assert abs(final["ingreso_facturado"] - before["ingreso_facturado"]) < 0.02, \
            f"Venta anulada sigue contando en cierre: before={before['ingreso_facturado']} final={final['ingreso_facturado']}"
