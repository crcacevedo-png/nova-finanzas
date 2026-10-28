# Gestión central de NOG (/api/igss-units/nogs/all, create, update, roles)
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/igss-units"


def _login(u, p):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login failed {u}: {r.status_code} {r.text[:200]}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def igss():
    return _login("igss.admin", "IgssAdmin2024$")


@pytest.fixture(scope="module")
def std():
    return _login("usuario", "user2024")


@pytest.fixture(scope="module")
def created(sa):
    ids = []
    yield ids
    for i in ids:
        sa.delete(f"{API}/nogs/{i}")


# Listado global
def test_list_all_superadmin(sa):
    r = sa.get(f"{API}/nogs/all")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] == len(d["data"]) and d["total"] > 0
    assert len(d["unidades"]) > 0
    n = d["data"][0]
    for k in ["id", "numero", "unidad_nombre", "fecha_asignacion", "estado", "disponibles", "acreditados", "cantidad", "precio"]:
        assert k in n
    assert "_id" not in n
    assert len({x["unidad_id"] for x in d["data"]}) > 1


def test_list_all_igss_admin(igss):
    r = igss.get(f"{API}/nogs/all")
    assert r.status_code == 200
    assert r.json()["total"] > 0


def test_list_all_standard_forbidden(std):
    assert std.get(f"{API}/nogs/all").status_code == 403
    assert std.post(f"{API}/x/nogs", json={"numero": "X", "cantidad": 1}).status_code == 403
    assert std.put(f"{API}/nogs/x", json={"is_active": False}).status_code == 403


def test_list_all_unauthenticated():
    assert requests.get(f"{API}/nogs/all").status_code in (401, 403)


# Crear / editar / toggle / borrar
def test_create_edit_toggle_flow(sa, created):
    unidades = sa.get(f"{API}/nogs/all").json()["unidades"]
    uid = unidades[0]["id"]
    payload = {"numero": "NOG-QA-PYT1", "nombre_servicio": "TEST_Servicio", "tipo_compra": "contrato",
               "cantidad": 10, "precio": 150.5, "fecha_asignacion": "2026-10-20"}
    r = sa.post(f"{API}/{uid}/nogs", json=payload)
    assert r.status_code == 200, r.text
    n = r.json()
    created.append(n["id"])
    assert n["fecha_asignacion"] == "2026-10-20"
    assert n["is_active"] is True and n["estado"] == "activo"
    assert n["tipo_compra_label"] == "Contrato"

    allr = sa.get(f"{API}/nogs/all").json()["data"]
    f = next(x for x in allr if x["id"] == n["id"])
    assert f["unidad_id"] == uid and f["unidad_nombre"] == unidades[0]["name"]

    # duplicado
    assert sa.post(f"{API}/{uid}/nogs", json=payload).status_code == 400

    # disponible para asignar (nogs-activos)
    act = sa.get(f"{API}/{uid}/nogs-activos")
    assert act.status_code == 200
    assert n["id"] in str(act.json())

    r = sa.put(f"{API}/nogs/{n['id']}", json={"fecha_asignacion": "2026-10-25", "nombre_servicio": "TEST_Edit"})
    assert r.status_code == 200
    assert r.json()["fecha_asignacion"] == "2026-10-25" and r.json()["nombre_servicio"] == "TEST_Edit"

    r = sa.put(f"{API}/nogs/{n['id']}", json={"is_active": False})
    assert r.json()["estado"] == "inactivo"
    act = sa.get(f"{API}/{uid}/nogs-activos")
    assert n["id"] not in str(act.json())
    r = sa.put(f"{API}/nogs/{n['id']}", json={"is_active": True})
    assert r.json()["estado"] == "activo"


def test_create_validation(sa):
    uid = sa.get(f"{API}/nogs/all").json()["unidades"][0]["id"]
    assert sa.post(f"{API}/{uid}/nogs", json={"numero": "", "cantidad": 1}).status_code == 422
    assert sa.post(f"{API}/{uid}/nogs", json={"numero": "NOG-QA-V", "cantidad": 0}).status_code == 422
    assert sa.post(f"{API}/no-existe/nogs", json={"numero": "NOG-QA-V", "cantidad": 1}).status_code == 404


def test_igss_admin_create_edit(igss, sa, created):
    uid = igss.get(f"{API}/nogs/all").json()["unidades"][0]["id"]
    r = igss.post(f"{API}/{uid}/nogs", json={"numero": "NOG-QA-PYT2", "cantidad": 5, "fecha_asignacion": "2026-10-01"})
    assert r.status_code == 200, r.text
    nid = r.json()["id"]
    created.append(nid)
    r = igss.put(f"{API}/nogs/{nid}", json={"fecha_asignacion": "2026-10-02"})
    assert r.status_code == 200 and r.json()["fecha_asignacion"] == "2026-10-02"
    assert igss.delete(f"{API}/nogs/{nid}").status_code == 200
    created.remove(nid)
    assert not any(x["id"] == nid for x in sa.get(f"{API}/nogs/all").json()["data"])
