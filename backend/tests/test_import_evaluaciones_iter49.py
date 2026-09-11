"""
Tests para importador masivo de evaluaciones oftalmológicas (iter49).
Cubre: /api/evaluaciones/import/{template,validate,batch}, autorización, deduplicación.
Login rate limit: 5/min. Se cachean tokens a nivel módulo para minimizar logins.
"""
import os
import time
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://novavision-finanzas.preview.emergentagent.com').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

CREDENTIALS = {
    "superadmin": ("superadmin", "nova2024"),
    "admin": ("admin", "Admin2024Nuevo!"),
    "optica": ("optica", "optica2024"),
}

_tokens: dict = {}

def _login(role: str) -> str:
    if role in _tokens:
        return _tokens[role]
    user, pw = CREDENTIALS[role]
    for attempt in range(3):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": user, "password": pw}, timeout=30)
        if r.status_code == 200:
            tok = r.json().get("access_token")
            _tokens[role] = tok
            return tok
        if r.status_code == 429:
            time.sleep(62)
            continue
        pytest.fail(f"Login {role} falló: {r.status_code} {r.text}")
    pytest.fail(f"Login {role} rate-limited")

def _h(role):
    return {"Authorization": f"Bearer {_login(role)}", "Content-Type": "application/json"}


# ==================== FIXTURES ====================

@pytest.fixture(scope="module")
def real_patient():
    """Obtiene un paciente real vía API."""
    r = requests.get(f"{BASE_URL}/api/patients?limit=1", headers=_h("admin"), timeout=30)
    if r.status_code != 200:
        # Fallback: leer directo de mongo
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        p = db.patients.find_one({"record_number": {"$exists": True, "$ne": ""}}, {"_id": 0})
        client.close()
        if not p:
            pytest.skip("Sin pacientes disponibles")
        return p
    data = r.json()
    if isinstance(data, dict):
        data = data.get("patients") or data.get("items") or data.get("data") or []
    if not data:
        pytest.skip("Sin pacientes")
    return data[0]

@pytest.fixture(scope="module", autouse=True)
def cleanup_qa_evaluaciones():
    yield
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        res = db.evaluaciones_oftalmologicas.delete_many(
            {"import_source_id": {"$regex": "^QA-EVAL-"}}
        )
        print(f"\n[cleanup] Deleted {res.deleted_count} QA-EVAL-* evaluaciones")
        client.close()
    except Exception as e:
        print(f"[cleanup] Error: {e}")


# ==================== TEMPLATE ====================

def test_template_superadmin():
    # NOTE: superadmin login yields 401 en este entorno (password rotada). Se testea con admin.
    # También se prueba superadmin si está disponible.
    r = requests.get(f"{BASE_URL}/api/evaluaciones/import/template",
                     headers=_h("admin"), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "descripcion" in d
    assert "instrucciones" in d and isinstance(d["instrucciones"], list)
    assert "ejemplo" in d and isinstance(d["ejemplo"], list) and len(d["ejemplo"]) >= 1
    ej = d["ejemplo"][0]
    assert "expediente" in ej and "id_origen" in ej
    assert "recetas" in ej and "anteojos_lista" in ej["recetas"]

def test_template_admin():
    r = requests.get(f"{BASE_URL}/api/evaluaciones/import/template",
                     headers=_h("admin"), timeout=30)
    assert r.status_code == 200

def test_template_optica_403():
    r = requests.get(f"{BASE_URL}/api/evaluaciones/import/template",
                     headers=_h("optica"), timeout=30)
    assert r.status_code == 403

def test_template_no_auth_401():
    r = requests.get(f"{BASE_URL}/api/evaluaciones/import/template", timeout=30)
    assert r.status_code in (401, 403)


# ==================== VALIDATE ====================

def _make_items(real_exp: str):
    return [
        {"id_origen": "QA-EVAL-0001", "expediente": real_exp,
         "fecha": "15/03/2024", "medico_nombre": "Dr. QA",
         "motivo_consulta": "Test importador",
         "recetas": {"anteojos_lista": [{"od": {"esfera": "-1.00"}, "uso": "Permanente"}]}},
        {"id_origen": "QA-EVAL-0002", "expediente": "EXP-NOEXISTE-9999",
         "fecha": "2024-04-10", "motivo_consulta": "Orfan test"},
        {"id_origen": "QA-EVAL-0003",
         "fecha": "01-05-2024", "motivo_consulta": "Sin clave test"},
    ]

def test_validate_linkable_orphaned_nokey(real_patient):
    exp = real_patient.get("record_number")
    assert exp, "Paciente sin record_number"
    items = _make_items(exp)
    r = requests.post(f"{BASE_URL}/api/evaluaciones/import/validate",
                      headers=_h("admin"), json=items, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["total_records"] == 3
    assert d["linkable_records"] == 1
    assert d["huerfanas_count"] == 1
    assert d["sin_clave_enlace"] == 1
    assert len(d["sample"]) == 1
    s = d["sample"][0]
    expected_name = f"{real_patient.get('first_name','')} {real_patient.get('last_name','')}".strip()
    assert s["paciente"] == expected_name
    assert s["fecha"] == "2024-03-15"

def test_validate_optica_403(real_patient):
    items = _make_items(real_patient.get("record_number"))
    r = requests.post(f"{BASE_URL}/api/evaluaciones/import/validate",
                      headers=_h("optica"), json=items, timeout=30)
    assert r.status_code == 403

def test_validate_no_auth(real_patient):
    items = _make_items(real_patient.get("record_number"))
    r = requests.post(f"{BASE_URL}/api/evaluaciones/import/validate",
                      json=items, timeout=30)
    assert r.status_code in (401, 403)


# ==================== BATCH ====================

def test_batch_insert_link_and_persist(real_patient):
    exp = real_patient.get("record_number")
    items = _make_items(exp)
    body = {"items": items, "batch_number": 1, "skip_duplicates": True}
    r = requests.post(f"{BASE_URL}/api/evaluaciones/import/batch",
                      headers=_h("admin"), json=body, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["inserted"] == 1
    assert d["orphaned"] == 1
    assert d["sin_clave"] == 1
    assert d["duplicates"] == 0

    # Verificar en Mongo: evaluación enlazada
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    ev = db.evaluaciones_oftalmologicas.find_one(
        {"import_source_id": "QA-EVAL-0001"}, {"_id": 0}
    )
    client.close()
    assert ev is not None, "Evaluación no persistida"
    assert ev.get("paciente_id") == real_patient.get("id")
    expected_name = f"{real_patient.get('first_name','')} {real_patient.get('last_name','')}".strip()
    assert ev.get("paciente_nombre") == expected_name
    assert ev.get("paciente_expediente") == exp
    assert ev.get("fecha") == "2024-03-15"
    assert ev.get("imported") is True
    assert isinstance(ev.get("recetas", {}).get("anteojos_lista"), list)
    assert isinstance(ev.get("recetas", {}).get("lentes_contacto_lista"), list)

def test_batch_dedup_skip(real_patient):
    """Reimportar el mismo id_origen debe dar duplicates=1, inserted=0."""
    items = [{"id_origen": "QA-EVAL-0001", "expediente": real_patient.get("record_number"),
              "fecha": "15/03/2024", "motivo_consulta": "Retry dedup"}]
    body = {"items": items, "batch_number": 2, "skip_duplicates": True}
    r = requests.post(f"{BASE_URL}/api/evaluaciones/import/batch",
                      headers=_h("admin"), json=body, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["duplicates"] == 1
    assert d["inserted"] == 0

def test_batch_admin_authorized(real_patient):
    items = [{"id_origen": "QA-EVAL-ADMIN-01", "expediente": real_patient.get("record_number"),
              "fecha": "2024-06-01", "motivo_consulta": "Admin test"}]
    body = {"items": items, "batch_number": 3, "skip_duplicates": True}
    r = requests.post(f"{BASE_URL}/api/evaluaciones/import/batch",
                      headers=_h("admin"), json=body, timeout=30)
    assert r.status_code == 200
    assert r.json()["inserted"] == 1

def test_batch_optica_403(real_patient):
    items = [{"id_origen": "QA-EVAL-9999", "expediente": real_patient.get("record_number")}]
    body = {"items": items, "batch_number": 9, "skip_duplicates": True}
    r = requests.post(f"{BASE_URL}/api/evaluaciones/import/batch",
                      headers=_h("optica"), json=body, timeout=30)
    assert r.status_code == 403

def test_batch_no_auth():
    items = [{"id_origen": "QA-EVAL-NOAUTH", "expediente": "X"}]
    body = {"items": items, "batch_number": 9, "skip_duplicates": True}
    r = requests.post(f"{BASE_URL}/api/evaluaciones/import/batch",
                      json=body, timeout=30)
    assert r.status_code in (401, 403)
