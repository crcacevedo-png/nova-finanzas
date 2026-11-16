# Regresión: resolución del valor (honorario) de un tipo de anestesia cuyo
# nombre contiene caracteres especiales de regex (p. ej. "+", ".", "(", ")").
#
# Bug real reportado en producción: la cirugía de "Mario Reyes Gomez" tenía el
# tipo de anestesia "Sedación Faco + Vitrecto" (Q1,200.00 en el catálogo), pero
# en "Procedimientos de Anestesia" el honorario aparecía en Q0.00. Causa raíz:
# routes/quirofano.py::_resolve_type_value armaba una regex `^{label}$` sin
# escapar el nombre; el "+" se interpretaba como cuantificador regex en vez de
# carácter literal, por lo que nunca encontraba el tipo en el catálogo y caía
# al fallback value=0. Fix: envolver el nombre con re.escape() antes de usarlo
# en la regex.
import os
import requests
from dotenv import dotenv_values

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")


def _login():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    assert r.status_code == 200, f"Login falló: {r.status_code} {r.text}"
    return r.json()["access_token"]


def test_anesthesia_type_con_caracteres_especiales_resuelve_valor_correcto():
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}
    type_name = "Sedación Faco + Vitrecto (TEST)"
    type_id = None
    surgery_id = None
    try:
        # 1) Crear un tipo de anestesia con "+" y paréntesis en el nombre
        r = requests.post(
            f"{BASE_URL}/api/quirofano/anesthesia/types",
            json={"name": type_name, "value": 1200},
            headers=headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        type_id = r.json()["id"]

        # 2) Crear una cirugía con ese tipo de anestesia y un anestesiólogo
        today = requests.get(f"{BASE_URL}/api/surgeries/options", headers=headers, timeout=30).json()
        import datetime as _dt
        today_str = _dt.datetime.now().strftime("%Y-%m-%d")
        r = requests.post(
            f"{BASE_URL}/api/surgeries",
            json={
                "date": today_str, "time": "09:00", "patient_name": "TEST REGEX PLUS PACIENTE",
                "procedure": "Faco VT", "surgeon": "Dr. Test Regex", "eye": "OD",
                "anesthesia_type": type_name, "anesthesiologist": "Dr. Test Anestesiologo Regex",
                "institution": "Alquiler",
            },
            headers=headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        surgery_id = r.json()["id"]

        # 3) El cierre mensual debe reflejar el valor REAL del catálogo (1200), no 0
        month = today_str[:7]
        r = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/closure", params={"month": month}, headers=headers, timeout=30)
        assert r.status_code == 200, r.text
        detalle = [
            det for g in r.json()["por_anestesiologo"] for det in g["detalle"]
            if det["patient_name"] == "TEST REGEX PLUS PACIENTE"
        ]
        assert len(detalle) == 1, "El procedimiento debe aparecer exactamente una vez en el cierre"
        assert detalle[0]["value"] == 1200.0, f"El honorario debía ser 1200.0, llegó {detalle[0]['value']} (bug de regex no escapada)"
        assert detalle[0]["tipo"] == type_name

        # 4) Editar la cirugía (p. ej. reafirmar el mismo tipo) debe seguir resolviendo bien
        r = requests.put(
            f"{BASE_URL}/api/surgeries/{surgery_id}",
            json={"anesthesia_type": type_name},
            headers=headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        r = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/closure", params={"month": month}, headers=headers, timeout=30)
        detalle = [
            det for g in r.json()["por_anestesiologo"] for det in g["detalle"]
            if det["patient_name"] == "TEST REGEX PLUS PACIENTE"
        ]
        assert detalle[0]["value"] == 1200.0
    finally:
        if surgery_id:
            requests.delete(f"{BASE_URL}/api/surgeries/{surgery_id}", headers=headers, timeout=30)
        if type_id:
            requests.delete(f"{BASE_URL}/api/quirofano/anesthesia/types/{type_id}", headers=headers, timeout=30)


def test_anesthesia_type_sin_caracteres_especiales_sigue_funcionando():
    """No-regresión: nombres de tipo normales (sin regex especiales) deben
    seguir resolviendo su valor igual que antes del fix."""
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}
    type_name = "Sedacion Local TEST Regresion"
    type_id = None
    try:
        r = requests.post(
            f"{BASE_URL}/api/quirofano/anesthesia/types",
            json={"name": type_name, "value": 500},
            headers=headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        type_id = r.json()["id"]

        r = requests.get(f"{BASE_URL}/api/quirofano/anesthesia/types", headers=headers, timeout=30)
        found = [t for t in r.json()["data"] if t["name"] == type_name and t["active"]]
        assert len(found) == 1
        assert found[0]["value"] == 500
    finally:
        if type_id:
            requests.delete(f"{BASE_URL}/api/quirofano/anesthesia/types/{type_id}", headers=headers, timeout=30)
