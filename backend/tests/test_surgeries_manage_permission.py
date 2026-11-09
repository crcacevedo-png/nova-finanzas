# Retest iter127: manage_sala_operaciones gating + PUT cancel bypass closed + anestesia read-only
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


def _login(u, p):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login failed {u}: {r.status_code}")
    d = r.json()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {d.get('access_token') or d.get('token')}"})
    return s


@pytest.fixture(scope="module")
def sessions():
    return {
        "superadmin": _login("superadmin", "nova2024"),
        "usuario": _login("usuario", "user2024"),
        "medico": _login("medico_test", "medico2024"),
        "anestesia": _login("anestesia", "anest2024"),
    }


@pytest.fixture(scope="module")
def created(sessions):
    ids = []
    yield ids
    for sid in ids:
        sessions["superadmin"].delete(f"{BASE_URL}/api/surgeries/{sid}")


def _payload(name):
    return {"date": "2026-02-16", "time": "09:00", "patient_name": name, "procedure": "Facoemulsificación",
            "surgeon": "Dr. Carlos Méndez", "eye": "OI", "anesthesia_type": "local",
            "anesthesiologist": "TEST_Anest", "institution": "Privado", "observations": "o1"}


# /auth/me permission flags per role
@pytest.mark.parametrize("role,expected", [("superadmin", True), ("usuario", True), ("medico", True), ("anestesia", False)])
def test_me_manage_flag(sessions, role, expected):
    p = sessions[role].get(f"{BASE_URL}/api/auth/me").json().get("permissions", {})
    assert bool(p.get("manage_sala_operaciones")) is expected
    assert p.get("view_sala_operaciones") is True


# Create+edit works for superadmin/usuario/medico
@pytest.mark.parametrize("role", ["superadmin", "usuario", "medico"])
def test_create_edit(sessions, created, role):
    s = sessions[role]
    r = s.post(f"{BASE_URL}/api/surgeries", json=_payload(f"TEST_Iter127_{role}"))
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    created.append(sid)
    r = s.put(f"{BASE_URL}/api/surgeries/{sid}", json={"observations": f"edit_{role}"})
    assert r.status_code == 200, r.text
    assert s.get(f"{BASE_URL}/api/surgeries/{sid}").json()["observations"] == f"edit_{role}"


# PUT cannot change status/cancellation fields, any role
@pytest.mark.parametrize("role", ["usuario", "medico", "superadmin"])
def test_put_cannot_cancel(sessions, created, role):
    sa = sessions["superadmin"]
    r = sa.post(f"{BASE_URL}/api/surgeries", json=_payload(f"TEST_Iter127_bypass_{role}"))
    sid = r.json()["id"]
    created.append(sid)
    r = sessions[role].put(f"{BASE_URL}/api/surgeries/{sid}",
                           json={"status": "cancelado", "cancellation_reason": "x", "rescheduled_to": "2026-03-01"})
    assert r.status_code == 200, r.text
    g = sa.get(f"{BASE_URL}/api/surgeries/{sid}").json()
    assert g["status"] == "activo"
    assert not g.get("cancellation_reason")
    assert not g.get("rescheduled_to")


# anestesia: read OK, all writes 403
def test_anestesia_read_only(sessions, created):
    an = sessions["anestesia"]
    assert an.get(f"{BASE_URL}/api/surgeries").status_code == 200
    r = an.post(f"{BASE_URL}/api/surgeries", json=_payload("TEST_Iter127_anest"))
    assert r.status_code == 403
    sa = sessions["superadmin"]
    sid = sa.post(f"{BASE_URL}/api/surgeries", json=_payload("TEST_Iter127_anest_target")).json()["id"]
    created.append(sid)
    sa.post(f"{BASE_URL}/api/surgeries/{sid}/equipment", json={"name": "TEST_Eq", "quantity": 1})
    sa.post(f"{BASE_URL}/api/surgeries/{sid}/supplies", json={"name": "TEST_Sup", "quantity": 1, "category": "otro"})
    g = sa.get(f"{BASE_URL}/api/surgeries/{sid}").json()
    eq, sup = g["equipment"][0]["id"], g["supplies"][0]["id"]
    assert an.get(f"{BASE_URL}/api/surgeries/{sid}").status_code == 200
    calls = [
        ("put", f"/api/surgeries/{sid}", {"observations": "hack"}),
        ("patch", f"/api/surgeries/{sid}/supplies-status", {"estado": "registrados"}),
        ("post", f"/api/surgeries/{sid}/equipment", {"name": "x", "quantity": 1}),
        ("delete", f"/api/surgeries/{sid}/equipment/{eq}", None),
        ("post", f"/api/surgeries/{sid}/supplies", {"name": "x", "quantity": 1, "category": "otro"}),
        ("put", f"/api/surgeries/{sid}/supplies/{sup}", {"quantity": 5}),
        ("delete", f"/api/surgeries/{sid}/supplies/{sup}", None),
        ("post", f"/api/surgeries/{sid}/cancel", {"reason": "x"}),
        ("delete", f"/api/surgeries/{sid}", None),
    ]
    for m, path, body in calls:
        r = getattr(an, m)(f"{BASE_URL}{path}", json=body) if body is not None else getattr(an, m)(f"{BASE_URL}{path}")
        assert r.status_code == 403, f"{m} {path} -> {r.status_code}"
    g2 = sa.get(f"{BASE_URL}/api/surgeries/{sid}").json()
    assert g2["observations"] == "o1" and len(g2["equipment"]) == 1 and len(g2["supplies"]) == 1


# superadmin real cancel still works; usuario cancel 403
def test_cancel_endpoint(sessions, created):
    sa = sessions["superadmin"]
    sid = sa.post(f"{BASE_URL}/api/surgeries", json=_payload("TEST_Iter127_cancel")).json()["id"]
    created.append(sid)
    assert sessions["usuario"].post(f"{BASE_URL}/api/surgeries/{sid}/cancel", json={"reason": "x"}).status_code == 200  # iter128: usuario allowed
    sa.put(f"{BASE_URL}/api/surgeries/{sid}", json={"observations": "noop"})
    r = sa.post(f"{BASE_URL}/api/surgeries/{sid}/cancel", json={"reason": "TEST motivo"})
    assert r.status_code == 200, r.text
    assert sa.get(f"{BASE_URL}/api/surgeries/{sid}").json()["status"] == "cancelado"
