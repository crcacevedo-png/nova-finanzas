# Ventas del Día (rol usuario) - backend checks: /ventas/hoy, /ventas/resumen-dia, /ventas/{id}, menu config
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
PRODUCTO_ID = "605fc05e-8161-4f70-9689-6638b57ae34e"
BODEGA_ID = "e829c15c-f9bb-41a2-9ac7-38ce446f83a2"

STATE = {}


def login(username, password):
    r = requests.post(f"{API}/auth/login", json={"username": username, "password": password})
    if r.status_code != 200:
        pytest.skip(f"login {username} failed {r.status_code}")
    data = r.json()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    s.user = data["user"]
    return s


@pytest.fixture(scope="module")
def usuario():
    return login("usuario", "user2024")


@pytest.fixture(scope="module")
def adm():
    return login("admin", "Admin2024$")


@pytest.fixture(scope="module")
def sa():
    return login("superadmin", "nova2024")


class TestVentasDelDiaUsuario:
    # Usuario role: permissions + menu config
    def test_usuario_menu_includes_ventas_del_dia(self, usuario):
        r = usuario.get(f"{API}/auth/me")
        print("perms manage_sales:", (r.json().get("permissions") or {}).get("manage_sales"))
        r2 = usuario.get(f"{API}/menu-config/my-menus")
        print("my-menus status", r2.status_code, str(r2.text)[:400])
        assert "ventas_del_dia" in r2.text

    # Usuario: GET /ventas/hoy & /resumen-dia
    def test_usuario_ventas_hoy_200(self, usuario):
        r = usuario.get(f"{API}/ventas/hoy")
        print(r.status_code, r.text[:300])
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)
        STATE["count_before"] = r.json()["total"]

    def test_usuario_resumen_dia_200(self, usuario):
        r = usuario.get(f"{API}/ventas/resumen-dia")
        print(r.status_code, r.text[:300])
        assert r.status_code == 200
        assert "total_ventas" in r.json()
        STATE["resumen_before"] = r.json()

    # Superadmin: open caja (if needed) and create test sale
    def test_admin_create_venta(self, adm):
        sa = adm
        est = sa.get(f"{API}/caja/estado").json()
        print("caja estado superadmin:", est.get("caja_abierta"), (est.get("cierre") or {}).get("estado"))
        if not est.get("caja_abierta"):
            r = sa.post(f"{API}/caja/apertura", json={"monto_apertura": 100})
            print("apertura", r.status_code, r.text[:200])
            assert r.status_code == 200
            STATE["opened_caja"] = True
        body = {
            "bodega_id": BODEGA_ID,
            "paciente_nombre": "TEST_Cliente QA",
            "items": [{"producto_id": PRODUCTO_ID, "nombre": "Consulta Oftalmológica General",
                       "cantidad": 1, "precio_unitario": 300, "subtotal": 300}],
            "formas_pago": [{"metodo": "Efectivo", "monto": 300}],
            "observaciones": "TEST_QA ventas del dia",
        }
        r = sa.post(f"{API}/ventas", json=body)
        print("venta", r.status_code, r.text[:400])
        assert r.status_code == 200
        v = r.json()
        STATE["venta"] = v
        assert v["total"] == 300
        import json
        json.dump({"venta": v, "opened_caja": STATE.get("opened_caja")}, open("/tmp/vdd_state.json", "w"))

    def test_usuario_sees_new_venta(self, usuario):
        v = STATE.get("venta") or pytest.skip("no venta")
        r = usuario.get(f"{API}/ventas/hoy")
        assert r.status_code == 200
        found = [x for x in r.json()["data"] if x["id"] == v["id"]]
        assert found, "venta no aparece en /ventas/hoy"
        f = found[0]
        assert f["numero_venta"] == v["numero_venta"]
        assert f["total"] == 300
        assert f["paciente_nombre"] == "TEST_Cliente QA"
        assert f["vendedor_nombre"]
        res = usuario.get(f"{API}/ventas/resumen-dia").json()
        assert res["total_ventas"] == STATE["resumen_before"]["total_ventas"] + 1

    def test_usuario_get_detalle(self, usuario):
        v = STATE.get("venta") or pytest.skip("no venta")
        r = usuario.get(f"{API}/ventas/{v['id']}")
        assert r.status_code == 200
        d = r.json()
        assert d["items"][0]["nombre"] == "Consulta Oftalmológica General"
        assert d["subtotal"] == 300 and d["total"] == 300
        assert d["formas_pago"][0]["metodo"] == "Efectivo"

    # Read-only: usuario cannot anular
    def test_usuario_cannot_anular(self, usuario):
        v = STATE.get("venta") or pytest.skip("no venta")
        r = usuario.post(f"{API}/ventas/{v['id']}/anular", json={"motivo": "intento usuario"})
        assert r.status_code == 403

    def test_usuario_create_venta_permission(self, usuario):
        # informational: can usuario create sales via API? (UI is read-only)
        r = usuario.post(f"{API}/ventas", json={"bodega_id": BODEGA_ID, "items": [], "formas_pago": []})
        print("usuario POST /ventas ->", r.status_code, r.text[:200])

    # Cleanup
    def test_zz_cleanup(self, sa, adm):
        import json, os as _o
        if not STATE.get("venta") and _o.path.exists("/tmp/vdd_state.json"):
            STATE.update(json.load(open("/tmp/vdd_state.json")))
        v = STATE.get("venta")
        if v:
            r = sa.post(f"{API}/ventas/{v['id']}/anular", json={"motivo": "limpieza QA test", "devolver_inventario": True})
            print("anular", r.status_code, r.text[:200])
            assert r.status_code == 200
        if STATE.get("opened_caja"):
            r = adm.post(f"{API}/caja/cierre", json={"efectivo_contado": 100, "observaciones": "limpieza QA"})
            print("cierre", r.status_code, r.text[:200])
            assert r.status_code == 200
