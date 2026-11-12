# Independent verification: Cierre de Producción Diario — Dra. Mariamercedes Palma (cron + PDF + auth)
import os, io, time, hmac, hashlib, base64, uuid
from datetime import datetime, timezone, timedelta
import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient
from pypdf import PdfReader

FE = dotenv_values('/app/frontend/.env')
BE = dotenv_values('/app/backend/.env')
BASE_URL = FE['REACT_APP_BACKEND_URL'].rstrip('/')
SECRET = BE['WEBHOOK_CRON_SECRET']
db = MongoClient(BE['MONGO_URL'])[BE['DB_NAME']]
GT = timezone(timedelta(hours=-6))


def make_token(fecha, nombre, exp_delta=21 * 86400, secret=SECRET):
    exp = int(time.time()) + exp_delta
    payload = f"prodmedico|{fecha}|{nombre}|{exp}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode().rstrip("=")


def pdf_text(content):
    r = PdfReader(io.BytesIO(content))
    return "".join(p.extract_text() or "" for p in r.pages).replace("\n", "")


def get_pdf(token):
    return requests.get(f"{BASE_URL}/api/ventas/produccion-medico/daily-report/pdf", params={"token": token}, timeout=60)


@pytest.fixture(scope="module")
def palma():
    d = db.doctors.find_one({"name": {"$regex": "mariamercedes", "$options": "i"}}, {"_id": 0})
    assert d, "Dra. Palma not found in db.doctors"
    return d


@pytest.fixture(scope="module")
def today():
    return datetime.now(GT).strftime("%Y-%m-%d")


# --- Doctor resolution ---
def test_doctor_exists(palma):
    assert "Palma" in palma["name"] and palma.get("is_active") is True


# --- Cron webhook auth ---
class TestCronAuth:
    url = f"{BASE_URL}/api/cron/produccion-medico-diario"

    def test_no_auth(self):
        assert requests.post(self.url, timeout=30).status_code == 401

    def test_wrong_bearer(self):
        assert requests.post(self.url, headers={"Authorization": "Bearer wrong"}, timeout=30).status_code == 401

    def test_raw_secret_no_bearer(self):
        assert requests.post(self.url, headers={"Authorization": SECRET}, timeout=30).status_code == 401


# --- PDF token security ---
class TestPdfToken:
    def test_garbage_token(self):
        assert get_pdf("garbage").status_code == 404

    def test_tampered_date(self, today):
        t = make_token(today, "Dra. Mariamercedes Palma")
        raw = base64.urlsafe_b64decode(t + "=" * (-len(t) % 4)).decode()
        raw = raw.replace(today, "2020-01-02", 1)
        bad = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
        assert get_pdf(bad).status_code == 404

    def test_wrong_secret(self, today):
        assert get_pdf(make_token(today, "Dra. Mariamercedes Palma", secret="x")).status_code == 404

    def test_expired(self, today):
        assert get_pdf(make_token(today, "Dra. Mariamercedes Palma", exp_delta=-10)).status_code == 404

    def test_missing_token(self):
        assert get_pdf.__call__ and requests.get(f"{BASE_URL}/api/ventas/produccion-medico/daily-report/pdf", timeout=30).status_code == 422

    def test_empty_day(self):
        r = get_pdf(make_token("2020-01-01", "Dra. Mariamercedes Palma"))
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        txt = pdf_text(r.content)
        assert "Sin producción registrada" in txt
        assert "Q 0.00" in txt

    def test_name_tolerance(self):
        # lowercase w/o prefix should still resolve to the canonical doctor name
        r = get_pdf(make_token("2020-01-01", "mariamercedes palma"))
        assert r.status_code == 200
        assert "Dra. Mariamercedes Palma" in pdf_text(r.content)


# --- Combined aggregation clinica + optica ---
def test_combined_aggregation(palma, today):
    now = datetime.now(timezone.utc).isoformat()
    vid, oid = str(uuid.uuid4()), str(uuid.uuid4())
    db.ventas.insert_one({
        "id": vid, "numero_venta": "TEST_VTA_PALMA", "fecha": now, "origen": "clinica", "estado": "completada",
        "medico_id": palma["id"], "medico_nombre": palma["name"], "paciente_nombre": "TEST_Paciente Clinica",
        "items": [{"nombre": "TEST_ConsultaXYZ", "cantidad": 1, "subtotal": 111.0}], "total": 111.0, "created_at": now,
    })
    db.optica_sales.insert_one({
        "id": oid, "order_number": "TEST_ORD_PALMA", "created_at": now, "status": "pagado",
        "doctor_id": palma["id"], "doctor_name": palma["name"], "patient_name": "TEST_Paciente Optica",
        "items_v2": [
            {"type": "frame", "name": "TEST_ArmazonXYZ", "quantity": 1, "unit_price": 200.0, "subtotal": 200.0},
            {"type": "lens_type", "name": "TEST_LenteXYZ", "quantity": 2, "unit_price": 50.0, "subtotal": 100.0},
        ], "total": 300.0,
    })
    try:
        token = make_token(today, palma["name"])
        r = get_pdf(token)
        assert r.status_code == 200
        txt = pdf_text(r.content)
        for s in ["TEST_ConsultaXYZ", "TEST_ArmazonXYZ", "TEST_LenteXYZ", "TEST_VTA_PALMA", "TEST_ORD_PALMA"]:
            assert s in txt, f"{s} missing"
        # baseline: compute other real production of the day to make total check robust
        base = r.content
        db.optica_sales.update_one({"id": oid}, {"$set": {"status": "cancelado"}})
        r2 = get_pdf(token)
        assert r2.status_code == 200
        txt2 = pdf_text(r2.content)
        assert "TEST_ArmazonXYZ" not in txt2 and "TEST_LenteXYZ" not in txt2
        assert "TEST_ConsultaXYZ" in txt2
        # total check via direct import of aggregation numbers in text
        import re
        tot1 = float(re.search(r"TOTAL DEL D[ÍI]A: Q ([\d,\.]+)", txt).group(1).replace(",", ""))
        tot2 = float(re.search(r"TOTAL DEL D[ÍI]A: Q ([\d,\.]+)", txt2).group(1).replace(",", ""))
        assert round(tot1 - tot2, 2) == 300.0
        print(f"tot with optica={tot1}, without={tot2}")
    finally:
        db.ventas.delete_one({"id": vid})
        db.optica_sales.delete_one({"id": oid})


# --- Manual send requires admin ---
def test_manual_send_requires_auth():
    r = requests.post(f"{BASE_URL}/api/ventas/produccion-medico/daily-report/enviar", timeout=30)
    assert r.status_code in (401, 403)


def test_manual_send_forbidden_for_usuario():
    s = requests.Session()
    lr = s.post(f"{BASE_URL}/api/auth/login", json={"username": "usuario", "password": "user2024"}, timeout=30)
    if lr.status_code != 200:
        pytest.skip(f"usuario login failed {lr.status_code}")
    tok = lr.json().get("access_token") or lr.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    r = s.post(f"{BASE_URL}/api/ventas/produccion-medico/daily-report/enviar", timeout=30)
    assert r.status_code == 403


# --- Regression ---
def test_regression_analisis():
    s = requests.Session()
    lr = s.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    assert lr.status_code == 200
    tok = lr.json().get("access_token") or lr.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    r = s.get(f"{BASE_URL}/api/ventas/analisis", timeout=60)
    assert r.status_code == 200, r.text[:300]
    assert isinstance(r.json(), (dict, list))


def test_regression_anestesia_cron_auth():
    assert requests.post(f"{BASE_URL}/api/cron/informe-anestesia-diario", timeout=30).status_code == 401
