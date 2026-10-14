"""Tests for /api/agenda/preferencias-medicos (per-user doctor ordering/visibility prefs)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE_URL}/api"


def _login(username, password):
    r = requests.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed {username}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def super_token():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def medico_token():
    return _login("medico_test", "medico2024")


@pytest.fixture(scope="module")
def doctor_ids(super_token):
    r = requests.get(f"{API}/doctors", headers={"Authorization": f"Bearer {super_token}"}, timeout=20)
    assert r.status_code == 200
    data = r.json()
    if isinstance(data, dict):
        data = data.get("data", data.get("doctors", []))
    ids = [d["id"] for d in data]
    assert len(ids) >= 2, "necesitamos al menos 2 médicos para probar"
    return ids


def _reset(token):
    requests.put(
        f"{API}/agenda/preferencias-medicos",
        headers={"Authorization": f"Bearer {token}"},
        json={"orden": [], "ocultos": []},
        timeout=20,
    )


def test_get_default_empty(super_token):
    _reset(super_token)
    r = requests.get(f"{API}/agenda/preferencias-medicos",
                     headers={"Authorization": f"Bearer {super_token}"}, timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data == {"orden": [], "ocultos": []}


def test_put_and_get_persist(super_token, doctor_ids):
    orden = doctor_ids[:3][::-1]
    ocultos = doctor_ids[:1]
    r = requests.put(
        f"{API}/agenda/preferencias-medicos",
        headers={"Authorization": f"Bearer {super_token}"},
        json={"orden": orden, "ocultos": ocultos}, timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert body["orden"] == orden
    assert body["ocultos"] == ocultos

    r2 = requests.get(f"{API}/agenda/preferencias-medicos",
                      headers={"Authorization": f"Bearer {super_token}"}, timeout=20)
    assert r2.status_code == 200
    data = r2.json()
    assert data["orden"] == orden
    assert data["ocultos"] == ocultos


def test_per_user_isolation(super_token, medico_token, doctor_ids):
    # superadmin sets a specific preference
    orden = doctor_ids[::-1]
    ocultos = [doctor_ids[-1]]
    requests.put(f"{API}/agenda/preferencias-medicos",
                 headers={"Authorization": f"Bearer {super_token}"},
                 json={"orden": orden, "ocultos": ocultos}, timeout=20)
    # medico_test should NOT see the same preference
    r = requests.get(f"{API}/agenda/preferencias-medicos",
                     headers={"Authorization": f"Bearer {medico_token}"}, timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data["orden"] != orden or data["ocultos"] != ocultos, "preference leaked across users"


def test_reset_clears(super_token):
    _reset(super_token)
    r = requests.get(f"{API}/agenda/preferencias-medicos",
                     headers={"Authorization": f"Bearer {super_token}"}, timeout=20)
    assert r.json() == {"orden": [], "ocultos": []}


def test_unauthorized_rejected():
    r = requests.get(f"{API}/agenda/preferencias-medicos", timeout=20)
    assert r.status_code in (401, 403)
    r2 = requests.put(f"{API}/agenda/preferencias-medicos", json={"orden": [], "ocultos": []}, timeout=20)
    assert r2.status_code in (401, 403)


def test_cleanup_reset_superadmin(super_token):
    """Leave superadmin preference reset so other tests are not affected."""
    _reset(super_token)
    r = requests.get(f"{API}/agenda/preferencias-medicos",
                     headers={"Authorization": f"Bearer {super_token}"}, timeout=20)
    assert r.json() == {"orden": [], "ocultos": []}
