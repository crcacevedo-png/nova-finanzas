"""Pruebas de concurrencia y permisos para POST /api/patients.

Valida:
- No se generan record_number duplicados al crear pacientes en paralelo desde
  múltiples sesiones (superadmin + admin + usuario).
- Formato EXP-YYYYMM-####.
- DPI duplicado concurrente => solo un 200; los otros deben ser 400.
- Permisos: superadmin/admin -> 200; usuario -> 403.
- Limpieza hard-delete en Mongo por prefijo de first_name.
"""
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://novavision-finanzas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

USERS = {
    "superadmin": "nova2024",
    "admin": "Admin2024Nuevo!",
    "usuario": "user2024",
}

TAG = f"LoadTest{uuid.uuid4().hex[:6]}"  # first_name prefix to identify test data
RECORD_RE = re.compile(r"^EXP-\d{6}-\d{4}$")


# -------- fixtures --------

@pytest.fixture(scope="session")
def tokens():
    """Login one time per user, reuse token (login rate-limit is 5/min/IP)."""
    result = {}
    for u, p in USERS.items():
        r = requests.post(f"{API}/auth/login", json={"username": u, "password": p}, timeout=30)
        assert r.status_code == 200, f"login {u} failed: {r.status_code} {r.text}"
        data = r.json()
        tk = data.get("access_token") or data.get("token")
        assert tk, f"no token in login response for {u}"
        result[u] = tk
    return result


@pytest.fixture(scope="session")
def mongo_db():
    load_dotenv("/app/backend/.env")
    mc = MongoClient(os.environ["MONGO_URL"])
    return mc[os.environ["DB_NAME"]]


@pytest.fixture(scope="session", autouse=True)
def _cleanup(mongo_db):
    yield
    try:
        res = mongo_db.patients.delete_many({"first_name": {"$regex": f"^{TAG}"}})
        print(f"\n[cleanup] hard-deleted {res.deleted_count} test patients (tag={TAG})")
    except Exception as e:
        print(f"\n[cleanup] failed: {e}")


# -------- helpers --------

def _payload(uname, i, dpi=None):
    p = {
        "first_name": f"{TAG}{uname}",
        "last_name": f"Paciente{i}",
        "gender": "masculino",
        "birth_date": "1990-01-01",
        "phone": "55551234",
        "referral_institution": "particular",
    }
    if dpi is not None:
        p["dpi"] = dpi
    return p


def _post(token, payload):
    r = requests.post(
        f"{API}/patients",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    try:
        body = r.json()
    except Exception:
        body = {}
    return r.status_code, body


# -------- tests --------

def test_permissions_matrix(tokens):
    """superadmin y admin => 200 ; usuario => 403."""
    codes = {}
    for u in ("superadmin", "admin", "usuario"):
        code, body = _post(tokens[u], _payload(u, 0))
        codes[u] = code
    assert codes["superadmin"] == 200, f"superadmin expected 200 got {codes['superadmin']}"
    assert codes["admin"] == 200, f"admin expected 200 got {codes['admin']}"
    assert codes["usuario"] == 403, f"usuario expected 403 got {codes['usuario']}"


def test_concurrent_creation_no_duplicate_record_numbers(tokens):
    """30 POSTs concurrentes (10 superadmin + 10 admin + 10 usuario).

    Espera: 20 x 200 con record_number único, 10 x 403 para 'usuario'.
    """
    tasks = []
    for u in ("superadmin", "admin", "usuario"):
        for i in range(10):
            tasks.append((u, tokens[u], _payload(u, i)))

    results = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futs = [ex.submit(_post, tk, pl) for (_u, tk, pl) in tasks]
        for f, (u, _tk, _pl) in zip(as_completed(futs), tasks):
            code, body = f.result()
            results.append((u, code, body))

    ok = [b for (_u, c, b) in results if c == 200]
    forbidden = [(u, c) for (u, c, _b) in results if c == 403]
    others = [(u, c) for (u, c, _b) in results if c not in (200, 403)]

    print(f"\n[concurrent] total={len(results)} ok={len(ok)} 403={len(forbidden)} otros={others}")

    assert not others, f"Códigos inesperados: {others}"
    assert len(forbidden) == 10, f"Se esperaban 10 x 403 (usuario), hubo {len(forbidden)}"
    assert len(ok) == 20, f"Se esperaban 20 x 200 (superadmin+admin), hubo {len(ok)}"

    record_numbers = [b.get("record_number") for b in ok]
    # Formato
    bad_fmt = [r for r in record_numbers if not (r and RECORD_RE.match(r))]
    assert not bad_fmt, f"Formatos inválidos: {bad_fmt}"
    # Unicidad
    dups = sorted({r for r in record_numbers if record_numbers.count(r) > 1})
    assert not dups, f"❌ Expedientes duplicados: {dups} | todos={record_numbers}"

    # IDs únicos también
    ids = [b.get("id") for b in ok]
    assert len(set(ids)) == len(ids), "IDs de paciente duplicados"


def test_concurrent_duplicate_dpi_only_one_succeeds(tokens):
    """Mismo DPI concurrentemente => 1 x 200, resto 400. No duplicados en DB."""
    dpi = f"9{uuid.uuid4().int % 10**12:012d}"  # DPI numérico único de 13 dígitos
    tasks = []
    for u in ("superadmin", "admin"):
        for i in range(5):
            tasks.append((u, tokens[u], _payload(u, 100 + i, dpi=dpi)))

    results = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futs = [ex.submit(_post, tk, pl) for (_u, tk, pl) in tasks]
        for f in as_completed(futs):
            results.append(f.result())

    codes = [c for (c, _b) in results]
    ok = [b for (c, b) in results if c == 200]
    bad = [c for c in codes if c == 400]
    print(f"\n[dup DPI] codes={codes} ok={len(ok)} 400={len(bad)}")

    # Al menos uno debe fallar con 400, y solo puede haber 1 exitoso.
    assert len(ok) == 1, f"Se esperaba exactamente 1 x 200, hubo {len(ok)} (codes={codes})"
    # El resto debe ser 400 (duplicado). Toleramos 500 solo para reportar y fallar.
    assert all(c in (200, 400) for c in codes), f"Códigos inesperados con DPI duplicado: {codes}"


def test_get_patients_returns_created(tokens):
    """Sanity: GET /api/patients responde 200."""
    r = requests.get(f"{API}/patients", headers={"Authorization": f"Bearer {tokens['superadmin']}"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) or isinstance(data, dict)
