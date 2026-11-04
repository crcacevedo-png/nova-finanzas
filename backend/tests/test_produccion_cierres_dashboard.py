# Tests: Dashboard ventas clinica/optica, Historial de cierres (superadmin vs cajero), Análisis de Producción
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


def _login(u, p):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login {u} failed {r.status_code}")
    d = r.json()
    return {"Authorization": f"Bearer {d.get('access_token') or d.get('token')}"}


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def optica():
    return _login("optica", "Optica2024$")


@pytest.fixture(scope="module")
def usuario():
    return _login("usuario", "user2024")


def _me(h):
    return requests.get(f"{BASE_URL}/api/auth/me", headers=h).json()


# --- Dashboard resumen-dia
def test_resumen_dia_split(sa):
    r = requests.get(f"{BASE_URL}/api/dashboard/resumen-dia", headers=sa)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("ventas", "ventas_clinica", "ventas_optica"):
        assert k in d
        for f in ("cantidad", "total", "cobrado"):
            assert f in d[k]
    assert abs(d["ventas"]["total"] - (d["ventas_clinica"]["total"] + d["ventas_optica"]["total"])) < 0.02
    assert d["ventas"]["cantidad"] == d["ventas_clinica"]["cantidad"] + d["ventas_optica"]["cantidad"]
    assert abs(d["ventas"]["cobrado"] - (d["ventas_clinica"]["cobrado"] + d["ventas_optica"]["cobrado"])) < 0.02


# --- Historial de cierres
def test_cierres_superadmin(sa):
    r = requests.get(f"{BASE_URL}/api/caja/cierres", headers=sa)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["is_superadmin"] is True
    assert isinstance(d["resumen_cajeros"], list)
    for c in d["data"]:
        for f in ("total_ingresos", "total_egresos", "ingresos_efectivo", "ingresos_otros", "num_ventas", "cajero_nombre"):
            assert f in c
        assert abs(c["total_ingresos"] - (c["ingresos_efectivo"] + c["ingresos_otros"])) < 0.02
    for rc in d["resumen_cajeros"]:
        for f in ("total_ingresos", "num_ventas", "num_cierres", "diferencia_acumulada"):
            assert f in rc
    print("cierres:", d["total"], "cajeros:", len(d["resumen_cajeros"]),
          "distinct abierto_por:", len({c.get("abierto_por") for c in d["data"]}))


def test_cierres_optica_only_own(optica):
    me = _me(optica)
    r = requests.get(f"{BASE_URL}/api/caja/cierres", headers=optica)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["is_superadmin"] is False
    for c in d["data"]:
        assert c["abierto_por"] == me["id"]


def test_cierres_usuario(usuario):
    r = requests.get(f"{BASE_URL}/api/caja/cierres", headers=usuario)
    print("usuario cierres status", r.status_code)
    assert r.status_code in (200, 403)
    if r.status_code == 200:
        me = _me(usuario)
        assert r.json()["is_superadmin"] is False
        assert all(c["abierto_por"] == me["id"] for c in r.json()["data"])


def test_cierre_detalle(sa):
    lst = requests.get(f"{BASE_URL}/api/caja/cierres", headers=sa).json()["data"]
    if not lst:
        pytest.skip("no cierres")
    r = requests.get(f"{BASE_URL}/api/caja/cierres/{lst[0]['id']}", headers=sa)
    assert r.status_code == 200, r.text
    d = r.json()
    for f in ("ingresos_efectivo", "ingresos_otros", "num_ventas", "desglose_por_metodo", "total_ingresos"):
        assert f in d
    assert abs(sum(d["desglose_por_metodo"].values()) - d["total_ingresos"]) < 0.05


def test_cierre_detalle_404(sa):
    r = requests.get(f"{BASE_URL}/api/caja/cierres/nonexistent-xyz", headers=sa)
    assert r.status_code == 404


def test_cierre_detalle_idor_non_superadmin(sa, usuario):
    """Non-superadmin should not see other cashiers' cierres detail."""
    me = _me(usuario)
    lst = requests.get(f"{BASE_URL}/api/caja/cierres?limit=100", headers=sa).json()["data"]
    other = [c for c in lst if c.get("abierto_por") != me["id"]]
    if not other:
        pytest.skip("no other cashier cierres")
    r = requests.get(f"{BASE_URL}/api/caja/cierres/{other[0]['id']}", headers=usuario)
    assert r.status_code in (403, 404), f"IDOR: usuario can read other cashier cierre ({r.status_code})"


# --- Análisis de producción
@pytest.mark.parametrize("params", [
    {"periodo": "hoy"}, {"periodo": "semana"}, {"periodo": "mes"},
    {"periodo": "rango", "desde": "2025-01-01", "hasta": "2026-12-31"},
])
def test_analisis_periodos(sa, params):
    r = requests.get(f"{BASE_URL}/api/ventas/analisis", headers=sa, params=params)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("kpis", "top_productos_ingresos", "top_productos_unidades", "por_cajero", "por_medico", "por_categoria", "tendencia"):
        assert k in d
    k = d["kpis"]
    if k["num_ventas"]:
        assert abs(k["ticket_promedio"] - k["total_vendido"] / k["num_ventas"]) < 0.02
        assert abs(sum(t["monto"] for t in d["tendencia"]) - k["total_vendido"]) < 0.1
        assert sum(c["num_ventas"] for c in d["por_cajero"]) == k["num_ventas"]
        assert sum(m["num_ventas"] for m in d["por_medico"]) == k["num_ventas"]
    print(params, k)


def test_analisis_rango_invalido(sa):
    r = requests.get(f"{BASE_URL}/api/ventas/analisis", headers=sa,
                     params={"periodo": "rango", "desde": "bad", "hasta": "2026-01-01"})
    assert r.status_code in (400, 422), f"got {r.status_code}"


def test_analisis_forbidden_optica(optica):
    r = requests.get(f"{BASE_URL}/api/ventas/analisis?periodo=mes", headers=optica)
    assert r.status_code == 403


def test_analisis_forbidden_usuario(usuario):
    r = requests.get(f"{BASE_URL}/api/ventas/analisis?periodo=mes", headers=usuario)
    assert r.status_code == 403


def test_analisis_unauth():
    r = requests.get(f"{BASE_URL}/api/ventas/analisis?periodo=mes")
    assert r.status_code in (401, 403)
