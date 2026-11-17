# Setup scenario for Libro IGSS UI test (detenidas / cerrar / programada)
import os, json, random, requests
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
s = requests.Session()
r = s.post(f"{BASE}/auth/login", json={"username": "superadmin", "password": "nova2024"})
print("login", r.status_code, list(r.json().keys()))
tok = r.json().get("access_token") or r.json().get("token")
if tok:
    s.headers["Authorization"] = f"Bearer {tok}"
out = {}
for path in ["igss-units/nogs/resumen", "igss-units/libro/config", "igss-units/libro/cirugias-por-marcar", "igss-units/libro/en-curso-sin-movimiento?dias=90"]:
    j = s.get(f"{BASE}/{path}").json()
    print(path, {k: v for k, v in j.items() if k != "data"} if isinstance(j, dict) else j)
units = s.get(f"{BASE}/igss-units").json()
units = units.get("data", units) if isinstance(units, dict) else units
unit = next(u for u in units if u.get("active", u.get("activo", True)))
uid = unit["id"]; out["unit_id"] = uid; out["unit_name"] = unit.get("name") or unit.get("nombre")
print("unit", uid, out["unit_name"])
rnd = random.randint(10000, 99999)
nog_id = os.environ.get("NOG_ID")
nog = None if nog_id else s.post(f"{BASE}/igss-units/{uid}/nogs", json={"numero": f"TESTUI{rnd}", "nombre_servicio": "TEST UI", "tipo_compra": "contrato", "cantidad": 10, "precio": 100})
nog_id = nog_id or nog.json()["id"]; out["nog_id"] = nog_id
pat = s.post(f"{BASE}/patients", json={"first_name": "TEST_UI", "last_name": f"Libro{rnd}", "nombre": f"TEST_UI Libro{rnd}", "phone": "55555555", "referral_institution": "igss", "igss_unit_id": uid, "gender": "masculino", "dpi": f"{rnd}{rnd}{rnd}"[:13].ljust(13,"1"), "birth_date": "1970-01-01"})
print("patient", pat.status_code, pat.text[:300]); pj = pat.json(); pid = pj["id"]; out["patient_id"] = pid
out["patient_name"] = f"TEST_UI Libro{rnd}"
sps = f"TESTUI-{rnd}"; out["sps"] = sps
o = s.post(f"{BASE}/igss-units/libro/ordenes", json={"nog_id": nog_id, "paciente_id": pid, "no_sps": sps, "tipo": "procedimiento", "dosis_autorizadas": 3})
print("orden", o.status_code, o.text[:300]); out["orden_id"] = o.json().get("id")
surg = {"institution": "IGSS", "patient_id": pid, "date": "2025-01-10", "time": "08:00", "patient_name": f"TEST_UI Libro{rnd}", "procedure": "TEST UI Proc", "surgeon": "Dr Test", "eye": "OD", "anesthesia_type": "topica", "anesthesiologist": "Dr Anest",
        "igss_data": {"unit": out["unit_name"], "unit_id": uid, "sps": sps, "affiliation_number": "AF", "code": "C1", "procedure_cost": 100}}
sr = s.post(f"{BASE}/surgeries", json=surg); print("surgery", sr.status_code, sr.text[:300]); out["surgery_id"] = sr.json().get("id")
rr = s.post(f"{BASE}/surgeries/{out['surgery_id']}/realizada", json={"realizada": True}); print("realizada", rr.status_code, rr.text[:200])
# 2nd order: 1-dose procedure with programmed future surgery
sps2 = f"TESTUI2-{rnd}"; out["sps2"] = sps2
o2 = s.post(f"{BASE}/igss-units/libro/ordenes", json={"nog_id": nog_id, "paciente_id": pid, "no_sps": sps2, "tipo": "procedimiento", "dosis_autorizadas": 1})
print("orden2", o2.status_code, o2.text[:200]); out["orden2_id"] = o2.json().get("id")
surg2 = dict(surg, date="2026-03-15", igss_data=dict(surg["igss_data"], sps=sps2))
sr2 = s.post(f"{BASE}/surgeries", json=surg2); print("surgery2", sr2.status_code, sr2.text[:200]); out["surgery2_id"] = sr2.json().get("id")
ords = s.get(f"{BASE}/igss-units/libro/ordenes", params={"paciente_id": pid}).json()
for x in ords.get("data", []):
    print("ORD", x["no_sps"], x["estado"], x.get("dosis_aplicadas"), x.get("cirugias_programadas"))
json.dump(out, open("/tmp/libro_ui.json", "w")); print(out)
