# Escenario de UI para Bloques 2-3 del libro IGSS (preview). Uso: python3 /app/tests/setup_bloque3_ui.py
import json
import os
import random

import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
s = requests.Session()
tok = s.post(f"{BASE}/auth/login", json={"username": "superadmin", "password": "nova2024"}).json()["access_token"]
s.headers["Authorization"] = f"Bearer {tok}"
units = s.get(f"{BASE}/igss-units").json()
unit = next(u for u in units.get("data", units) if u.get("is_active", True))
rnd = random.randint(10000, 99999)
out = {"unit_id": unit["id"], "unit_name": unit["name"]}
nog = s.post(f"{BASE}/igss-units/{unit['id']}/nogs", json={"numero": f"TESTB3{rnd}", "nombre_servicio": "TEST B3 Inyección",
                                                          "tipo_compra": "contrato", "cantidad": 10, "precio": 100}).json()
out["nog_id"], out["nog_numero"] = nog["id"], nog["numero"]
pac = s.post(f"{BASE}/patients", json={"first_name": "TEST_B3", "last_name": f"Paciente{rnd}", "phone": "55555555",
                                       "referral_institution": "igss", "igss_unit_id": unit["id"], "gender": "femenino",
                                       "dpi": f"{rnd}{rnd}{rnd}"[:13].ljust(13, "2"), "birth_date": "1965-01-01"}).json()
out["patient_id"], out["patient_name"], out["record_number"] = pac["id"], f"TEST_B3 Paciente{rnd}", pac.get("record_number")


def orden(sps, **kw):
    r = s.post(f"{BASE}/igss-units/libro/ordenes", json={"nog_id": nog["id"], "paciente_id": pac["id"], "no_sps": sps, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def cirugia(sps, fecha, realizar=True):
    c = s.post(f"{BASE}/surgeries", json={
        "institution": "IGSS", "patient_id": pac["id"], "patient_name": out["patient_name"], "date": fecha, "time": "08:00",
        "procedure": "Inyección intravítrea Avastin", "surgeon": "Dr Test", "eye": "OD", "anesthesia_type": "topica",
        "anesthesiologist": "Dr Anest", "igss_data": {"unit": unit["name"], "unit_id": unit["id"], "sps": sps, "affiliation_number": "123456789",
                      "code": "INY-01", "procedure_cost": 100}})
    assert c.status_code == 200, c.text
    c = c.json()
    if realizar:
        s.post(f"{BASE}/surgeries/{c['id']}/realizada", json={"realizada": True})
    return c["id"]


# 1) Migrada en curso: 2 dosis conocidas aplicadas, "Confirmar dosis" pendiente
o1 = orden(f"TESTB3A-{rnd}", tipo="procedimiento", dosis_autorizadas=2, procedimiento="Avastin OD", inyectable=True)
db.igss_ordenes_libro.update_one({"id": o1["id"]}, {"$set": {"dosis_por_confirmar": True}})
cirugia(o1["no_sps"], "2026-10-01")
cirugia(o1["no_sps"], "2026-10-15")
# 2) Consulta reservada; 3) procedimiento 3 dosis en curso (1 aplicada); 4) histórica (no la ve el médico)
o2 = orden(f"TESTB3B-{rnd}", tipo="consulta", procedimiento="Consulta control")
o3 = orden(f"TESTB3C-{rnd}", tipo="procedimiento", dosis_autorizadas=3, procedimiento="Eylea OI")
cirugia(o3["no_sps"], "2026-10-20")
o4 = orden(f"TESTB3D-{rnd}", tipo="consulta", procedimiento="Histórica")
db.igss_ordenes_libro.update_one({"id": o4["id"]}, {"$set": {"estado": "historica"}})
o5 = orden(f"TESTB3E-{rnd}", tipo="consulta", procedimiento="Completa (no la ve el médico)")
db.igss_ordenes_libro.update_one({"id": o5["id"]}, {"$set": {"estado": "completa", "fecha_completa": "2026-10-05"}})
for k, o in (("o1_por_confirmar", o1), ("o2_consulta", o2), ("o3_en_curso", o3), ("o4_historica", o4), ("o5_completa", o5)):
    d = s.get(f"{BASE}/igss-units/libro/ordenes/{o['id']}").json()
    out[k] = {"id": d["id"], "numero_libro": d["numero_libro"], "no_sps": d["no_sps"], "estado": d["estado"],
              "dosis": f"{d['dosis_aplicadas']}/{d['dosis_autorizadas']}"}
json.dump(out, open("/app/tests/setup_bloque3_ui.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
