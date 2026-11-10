# Informe diario de anestesia: envío manual, cron webhook, PDF firmado, seguridad del HTML y regresión cierre diario
import os
import sys
import io
import time
import hmac
import base64
import hashlib
import pytest
import requests
from dotenv import dotenv_values

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]
BASE_URL = BASE_URL.rstrip("/")
BENV = dotenv_values("/app/backend/.env")
CRON_SECRET = BENV["WEBHOOK_CRON_SECRET"]
DATA_DATE = "2026-11-09"
EMPTY_DATE = "2026-01-01"
EXPECTED_TO = "draherreranestesia@gmail.com"

sys.path.insert(0, "/app/backend")


def make_token(date_str, ttl=21 * 86400, secret=CRON_SECRET):
    exp = int(time.time()) + ttl
    payload = f"{date_str}|{exp}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode().rstrip("=")


def pdf_text(content):
    import pypdf
    r = pypdf.PdfReader(io.BytesIO(content))
    return "\n".join(p.extract_text() or "" for p in r.pages)


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# --- Manual send endpoint ---
class TestManualSend:
    def test_send_with_data(self, auth):
        t0 = time.time()
        r = requests.post(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/enviar", params={"fecha": DATA_DATE}, headers=auth, timeout=60)
        print("elapsed", time.time() - t0, r.text)
        assert r.status_code == 200
        d = r.json()
        assert d["destinatarios"] == [EXPECTED_TO]
        assert d["errores"] == []
        assert "1 destinatario" in d["message"]

    def test_send_empty_day(self, auth):
        r = requests.post(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/enviar", params={"fecha": EMPTY_DATE}, headers=auth, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["destinatarios"] == [EXPECTED_TO]

    def test_send_no_auth(self):
        r = requests.post(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/enviar", params={"fecha": EMPTY_DATE}, timeout=30)
        assert r.status_code in (401, 403)

    def test_send_bad_token(self):
        r = requests.post(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/enviar", params={"fecha": EMPTY_DATE},
                          headers={"Authorization": "Bearer xyz"}, timeout=30)
        assert r.status_code in (401, 403)


# --- Report data consistency vs records endpoint ---
class TestDataConsistency:
    def test_report_matches_records(self, auth):
        r = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/records", params={"month": "2026-11"}, headers=auth, timeout=30)
        assert r.status_code == 200
        day = [x for x in r.json()["data"] if x["date"] == DATA_DATE]
        assert len(day) > 0
        total = round(sum(x.get("value") or 0 for x in day), 2)
        pdf = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/pdf", params={"token": make_token(DATA_DATE)}, timeout=30)
        assert pdf.status_code == 200
        txt = pdf_text(pdf.content)
        print(txt[:600])
        assert f"Procedimientos: {len(day)}" in txt
        assert f"Q {total:,.2f}" in txt
        for x in day:
            if x.get("patient_name"):
                first = x["patient_name"].split()[0]
                assert first in txt, first


# --- Public PDF endpoint ---
class TestPdf:
    def test_pdf_valid_token(self):
        r = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/pdf", params={"token": make_token(DATA_DATE)}, timeout=30)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"

    def test_pdf_empty_day(self):
        r = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/pdf", params={"token": make_token(EMPTY_DATE)}, timeout=30)
        assert r.status_code == 200
        txt = pdf_text(r.content)
        assert "Procedimientos: 0" in txt
        assert "Q 0.00" in txt
        assert "Sin procedimientos" in txt

    @pytest.mark.parametrize("bad", [
        "basura_invalida",
        "",
        base64.urlsafe_b64encode(b"2026-11-09|9999999999|deadbeef").decode(),
        base64.urlsafe_b64encode("2026-11-09|9999999999|é".encode()).decode(),
        base64.urlsafe_b64encode(b"a|b|c|d").decode(),
        base64.urlsafe_b64encode(b"\xff\xfe\xfd").decode(),
    ])
    def test_pdf_invalid_token(self, bad):
        r = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/pdf", params={"token": bad}, timeout=30)
        print(repr(bad), r.status_code)
        assert r.status_code in (404, 422)
        assert not r.content.startswith(b"%PDF")

    def test_pdf_expired_token(self):
        r = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/pdf", params={"token": make_token(DATA_DATE, ttl=-10)}, timeout=30)
        assert r.status_code == 404

    def test_pdf_wrong_secret(self):
        r = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/pdf", params={"token": make_token(DATA_DATE, secret="other")}, timeout=30)
        assert r.status_code == 404

    def test_pdf_missing_token(self):
        r = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/daily-report/pdf", timeout=30)
        assert r.status_code == 422


# --- Cron webhook ---
class TestCron:
    def test_cron_no_auth(self):
        r = requests.post(f"{BASE_URL}/api/cron/informe-anestesia-diario", timeout=30)
        assert r.status_code == 401

    def test_cron_wrong_secret(self):
        r = requests.post(f"{BASE_URL}/api/cron/informe-anestesia-diario", headers={"Authorization": "Bearer wrong"}, timeout=30)
        assert r.status_code == 401

    def test_cron_ok_fast(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        t0 = time.time()
        r = requests.post(f"{BASE_URL}/api/cron/informe-anestesia-diario", headers={"Authorization": f"Bearer {CRON_SECRET}"}, timeout=30)
        el = time.time() - t0
        print("cron elapsed", el)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "accepted"
        assert d["fecha"] == datetime.now(ZoneInfo("America/Guatemala")).strftime("%Y-%m-%d")
        assert el < 5


# --- Email HTML guardrails (in-process) ---
class TestEmailHtml:
    def test_html_safe_with_rows(self):
        from routes.email_service import build_anesthesia_daily_html, _assert_safe_email, EMAIL_FROM_NAME
        data = {"rows": [{"patient_name": "<script>x</script>", "procedure": "Faco", "surgeon": "Dr", "tipo": "Local",
                          "anesthesiologist": "A", "value": 100.0, "paid": False}], "total_count": 1, "total_value": 100.0}
        html = build_anesthesia_daily_html(DATA_DATE, data, f"{BENV['APP_PUBLIC_URL']}/api/quirofano/anesthesia/daily-report/pdf?token=abc")
        _assert_safe_email("Informe", html)
        assert "<form" not in html and "<input" not in html
        assert "<script>" not in html
        assert "Q100.00" in html
        assert EMAIL_FROM_NAME == "NovaVisión"
        assert BENV["APP_PUBLIC_URL"].startswith("https://")

    def test_html_empty(self):
        from routes.email_service import build_anesthesia_daily_html, _assert_safe_email
        html = build_anesthesia_daily_html(EMPTY_DATE, {"rows": [], "total_count": 0, "total_value": 0}, "https://example.com/x")
        _assert_safe_email("Informe", html)
        assert "Sin procedimientos de anestesia registrados este día" in html
        assert "Q0.00" in html

    def test_no_attachments_in_payload(self):
        src = open("/app/backend/routes/email_service.py").read()
        assert "attachments" not in src


# --- Regression: Cierre del Día ---
class TestCierreRegression:
    def test_cierre_manual(self, auth):
        r = requests.post(f"{BASE_URL}/api/caja/cierre-diario/enviar", params={"fecha": EMPTY_DATE}, headers=auth, timeout=90)
        print(r.text)
        assert r.status_code == 200
        assert len(r.json()["destinatarios"]) >= 1

    def test_cierre_no_auth(self):
        r = requests.post(f"{BASE_URL}/api/caja/cierre-diario/enviar", timeout=30)
        assert r.status_code in (401, 403)

    def test_cierre_cron_no_auth(self):
        r = requests.post(f"{BASE_URL}/api/cron/cierre-diario", timeout=30)
        assert r.status_code == 401
