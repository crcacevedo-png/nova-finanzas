"""Tests for accent-insensitive patient search (Issue P2)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def maria_patient(headers):
    """Ensure a patient named 'María García López' exists."""
    # Search first
    r = requests.get(f"{BASE_URL}/api/patients", params={"search": "García López"}, headers=headers)
    if r.status_code == 200:
        data = r.json()
        items = data if isinstance(data, list) else data.get("patients", data.get("items", []))
        for p in items:
            nombre = (p.get("nombre") or p.get("name") or p.get("first_name") or "").lower()
            apellido = (p.get("apellido") or p.get("last_name") or "").lower()
            full = f"{nombre} {apellido}".strip()
            if "maría" in full or "maria" in full:
                if "garcía" in full or "garcia" in full:
                    return p
    # Create one
    payload = {
        "first_name": "María",
        "last_name": "García López",
        "dni": "TEST99887766",
        "phone": "1122334455",
        "email": "test.maria@example.com",
        "birth_date": "1990-01-01",
        "gender": "femenino",
        "referral_institution": "particular",
    }
    r = requests.post(f"{BASE_URL}/api/patients", json=payload, headers=headers)
    assert r.status_code in (200, 201), f"Create patient failed: {r.status_code} {r.text}"
    return r.json()


def _extract_items(resp_json):
    if isinstance(resp_json, list):
        return resp_json
    for k in ("patients", "items", "results", "data"):
        if k in resp_json and isinstance(resp_json[k], list):
            return resp_json[k]
    return []


def _has_maria_garcia(items):
    for p in items:
        nombre = (p.get("nombre") or p.get("name") or p.get("first_name") or "").lower()
        apellido = (p.get("apellido") or p.get("last_name") or "").lower()
        full = f"{nombre} {apellido}"
        if ("maría" in full or "maria" in full) and ("garcía" in full or "garcia" in full):
            return True
    return False


# ---------- /api/patients ----------

@pytest.mark.parametrize("query", ["Maria", "María", "maria", "MARIA", "MARÍA"])
def test_patients_search_nombre_variants(headers, maria_patient, query):
    r = requests.get(f"{BASE_URL}/api/patients", params={"search": query}, headers=headers)
    assert r.status_code == 200, r.text
    items = _extract_items(r.json())
    assert _has_maria_garcia(items), f"'{query}' did not find María García López. Got {len(items)} items."


@pytest.mark.parametrize("query", ["Garcia", "García", "garcia", "GARCIA", "GARCÍA"])
def test_patients_search_apellido_variants(headers, maria_patient, query):
    r = requests.get(f"{BASE_URL}/api/patients", params={"search": query}, headers=headers)
    assert r.status_code == 200, r.text
    items = _extract_items(r.json())
    assert _has_maria_garcia(items), f"'{query}' did not find García. Got {len(items)} items."


# ---------- /api/pacientes/buscar ----------

@pytest.mark.parametrize("query", ["Maria", "María", "maria", "MARIA"])
def test_pacientes_buscar_nombre_variants(headers, maria_patient, query):
    r = requests.get(f"{BASE_URL}/api/pacientes/buscar", params={"search": query}, headers=headers)
    assert r.status_code == 200, r.text
    items = _extract_items(r.json())
    assert _has_maria_garcia(items), f"'{query}' did not find María. Got {len(items)} items."


@pytest.mark.parametrize("query", ["Garcia", "García", "garcia", "GARCÍA"])
def test_pacientes_buscar_apellido_variants(headers, maria_patient, query):
    r = requests.get(f"{BASE_URL}/api/pacientes/buscar", params={"search": query}, headers=headers)
    assert r.status_code == 200, r.text
    items = _extract_items(r.json())
    assert _has_maria_garcia(items), f"'{query}' did not find García. Got {len(items)} items."
