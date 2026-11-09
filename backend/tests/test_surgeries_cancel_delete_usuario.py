# Iter128: rol 'usuario' puede cancelar/reprogramar/eliminar cirugías; anestesia sigue 403; superadmin regresión
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

CREDS = {"superadmin": ("superadmin", "nova2024"), "usuario": ("usuario", "user2024"),
         "anestesia": ("anestesia", "anest2024")}


def _login(u, p):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": u, "password": p})
    if r.status_code != 200:
        pytest.skip(f"login failed {u}: {r.status_code}")
    j = r.json()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {j.get('access_token') or j.get('token')}"})
    return s


@pytest.fixture(scope="module")
def sessions():
    return {k: _login(*v) for k, v in CREDS.items()}


@pytest.fixture(scope="module")
def created(sessions):
    ids = []
    yield ids
    for sid in ids:
        sessions["superadmin"].delete(f"{BASE_URL}/api/surgeries/{sid}")


def _payload(name):
    return {"date": "2026-02-15", "time": "08:30", "patient_name": name, "procedure": "Facoemulsificación",
            "surgeon": "Dr. Carlos Méndez", "eye": "OD", "anesthesia_type": "local", "lio": "TEST_LIO",
            "anesthesiologist": "TEST_Anest", "institution": "Novavision", "observations": "TEST_obs"}


def _create(s, created, name):
    r = s.post(f"{BASE_URL}/api/surgeries", json=_payload(name))
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    created.append(sid)
    return sid


# usuario cancel with reschedule -> clone
def test_usuario_cancel_reschedule(sessions, created):
    s = sessions["usuario"]
    sid = _create(s, created, "TEST_I128_resched")
    r = s.post(f"{BASE_URL}/api/surgeries/{sid}/cancel",
               json={"reason": "TEST motivo", "reschedule_date": "2026-02-22", "reschedule_time": "10:15"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "cancelado" and d["cancellation_reason"] == "TEST motivo"
    assert d["rescheduled_to"] == "2026-02-22" and d["rescheduled_to_time"] == "10:15"
    nid = d["new_surgery_id"]
    assert nid
    created.append(nid)
    n = s.get(f"{BASE_URL}/api/surgeries/{nid}").json()
    assert n["status"] == "activo" and n["date"] == "2026-02-22" and n["time"] == "10:15"
    for k in ("patient_name", "procedure", "surgeon", "eye", "lio", "anesthesia_type", "anesthesiologist", "institution", "observations"):
        assert n[k] == _payload("TEST_I128_resched")[k], k


# usuario cancel without reschedule -> no clone
def test_usuario_cancel_no_reschedule(sessions, created):
    s = sessions["usuario"]
    sid = _create(s, created, "TEST_I128_noresched")
    r = s.post(f"{BASE_URL}/api/surgeries/{sid}/cancel", json={"reason": "TEST solo motivo"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "cancelado" and d["new_surgery_id"] is None and d["rescheduled_to"] is None
    g = s.get(f"{BASE_URL}/api/surgeries/{sid}").json()
    assert g["status"] == "cancelado"


# usuario delete -> 404 after
def test_usuario_delete(sessions, created):
    s = sessions["usuario"]
    sid = _create(s, created, "TEST_I128_delete")
    r = s.delete(f"{BASE_URL}/api/surgeries/{sid}")
    assert r.status_code == 200, r.text
    assert s.get(f"{BASE_URL}/api/surgeries/{sid}").status_code == 404
    assert s.delete(f"{BASE_URL}/api/surgeries/{sid}").status_code == 404


# anestesia still 403
def test_anestesia_forbidden(sessions, created):
    sid = _create(sessions["superadmin"], created, "TEST_I128_anest")
    a = sessions["anestesia"]
    r = a.post(f"{BASE_URL}/api/surgeries/{sid}/cancel", json={"reason": "TEST"})
    assert r.status_code == 403
    r = a.delete(f"{BASE_URL}/api/surgeries/{sid}")
    assert r.status_code == 403
    assert a.get(f"{BASE_URL}/api/surgeries/{sid}").json()["status"] == "activo"


# superadmin regression
def test_superadmin_cancel_delete(sessions, created):
    s = sessions["superadmin"]
    sid = _create(s, created, "TEST_I128_sa")
    r = s.post(f"{BASE_URL}/api/surgeries/{sid}/cancel", json={"reason": "TEST sa", "reschedule_date": "2026-03-01"})
    assert r.status_code == 200
    nid = r.json()["new_surgery_id"]
    created.append(nid)
    assert s.get(f"{BASE_URL}/api/surgeries/{nid}").json()["time"] == "08:30"
    assert s.delete(f"{BASE_URL}/api/surgeries/{nid}").status_code == 200


# usuario still can edit / equipment / supplies
def test_usuario_manage_regression(sessions, created):
    s = sessions["usuario"]
    sid = _create(s, created, "TEST_I128_manage")
    assert s.put(f"{BASE_URL}/api/surgeries/{sid}", json={"observations": "obs2"}).status_code == 200
    assert s.post(f"{BASE_URL}/api/surgeries/{sid}/equipment", json={"name": "TEST_Eq", "quantity": 1}).status_code == 200
    assert s.post(f"{BASE_URL}/api/surgeries/{sid}/supplies", json={"name": "TEST_Ins", "quantity": 2}).status_code == 200
    g = s.get(f"{BASE_URL}/api/surgeries/{sid}").json()
    assert g["observations"] == "obs2" and len(g["equipment"]) == 1 and len(g["supplies"]) == 1


# cancel status bypass via PUT still blocked
def test_put_cannot_cancel(sessions, created):
    s = sessions["usuario"]
    sid = _create(s, created, "TEST_I128_put")
    s.put(f"{BASE_URL}/api/surgeries/{sid}", json={"status": "cancelado"})
    assert s.get(f"{BASE_URL}/api/surgeries/{sid}").json()["status"] == "activo"


# re-cancel of an already-cancelled surgery (edge): observe behaviour
def test_recancel_already_cancelled(sessions, created):
    s = sessions["usuario"]
    sid = _create(s, created, "TEST_I128_recancel")
    r1 = s.post(f"{BASE_URL}/api/surgeries/{sid}/cancel", json={"reason": "a", "reschedule_date": "2026-02-20"})
    created.append(r1.json()["new_surgery_id"])
    r2 = s.post(f"{BASE_URL}/api/surgeries/{sid}/cancel", json={"reason": "b", "reschedule_date": "2026-02-21"})
    if r2.status_code == 200 and r2.json().get("new_surgery_id"):
        created.append(r2.json()["new_surgery_id"])
    assert r2.status_code in (400, 409), f"Re-cancel allowed ({r2.status_code}) -> duplicates clone"
