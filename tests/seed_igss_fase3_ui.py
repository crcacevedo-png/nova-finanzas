# Siembra de datos TEST_ para pruebas UI Fase 3 (lecturas desde el libro IGSS). Guarda ids en /tmp/qa_seed.json
import os, json, time, uuid, requests
from dotenv import load_dotenv
load_dotenv('/app/frontend/.env')
API = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') + '/api'
TAG = uuid.uuid4().hex[:5]


def login(u, p):
    for _ in range(8):
        r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
        if r.status_code == 429:
            time.sleep(12); continue
        r.raise_for_status()
        return {"Authorization": f"Bearer {r.json()['access_token']}"}


def ok(r):
    assert r.status_code in (200, 201), f"{r.request.method} {r.url} -> {r.status_code} {r.text[:300]}"
    return r.json()


sa = login("superadmin", "nova2024")
out = {"tag": TAG}
u = ok(requests.post(f"{API}/igss-units", json={"name": f"TEST_QA Unidad {TAG}", "code": f"TQ{TAG[:3]}"}, headers=sa))
uid = u.get("id") or u.get("data", {}).get("id")
out["unit_id"] = uid; out["unit_name"] = f"TEST_QA Unidad {TAG}"
nog = ok(requests.post(f"{API}/igss-units/{uid}/nogs", json={"numero": f"TESTQA{TAG}", "nombre_servicio": "TEST consulta", "tipo_compra": "contrato", "cantidad": 10, "precio": 100}, headers=sa))
out["nog_id"] = nog["id"]
nog90 = ok(requests.post(f"{API}/igss-units/{uid}/nogs", json={"numero": f"TESTQA90{TAG}", "nombre_servicio": "TEST 90", "tipo_compra": "contrato", "cantidad": 10, "precio": 50}, headers=sa))
out["nog90_id"] = nog90["id"]
bc = ok(requests.post(f"{API}/igss-units/{uid}/nogs", json={"numero": "", "nombre_servicio": f"TEST campimetria {TAG}", "tipo_compra": "baja_cuantia", "precio": 80}, headers=sa))
out["bc_id"] = bc["id"]
pac = ok(requests.post(f"{API}/patients", json={"first_name": "TEST_QA", "last_name": f"Paciente {TAG}", "gender": "femenino", "birth_date": "1980-01-01", "phone": "55551234", "dpi": f"9{int(time.time())}"[:13].ljust(13, '0'), "referral_institution": "igss", "igss_unit_id": uid}, headers=sa))
pid = pac.get("id") or pac.get("data", {}).get("id")
out["pac_id"] = pid

def orden(nid, sps, **kw):
    b = {"nog_id": nid, "paciente_id": pid, "no_sps": sps, "tipo": "consulta"}; b.update(kw)
    return ok(requests.post(f"{API}/igss-units/libro/ordenes", json=b, headers=sa))

o_at = orden(out["nog_id"], f"QA1-{TAG}")
o_pen = orden(out["nog_id"], f"QA2-{TAG}")
o_an = orden(out["nog_id"], f"QA3-{TAG}")
o_proc = orden(out["nog_id"], f"QA4-{TAG}", tipo="procedimiento", dosis_autorizadas=3)
o_bc = orden(out["bc_id"], f"QA5-{TAG}")
out.update(orden_atendida=o_at["id"], orden_pendiente=o_pen["id"], orden_anulada=o_an["id"], orden_proc=o_proc["id"], orden_bc=o_bc["id"])
ok(requests.post(f"{API}/igss-units/libro/ordenes/{o_an['id']}/anular", json={"motivo": "prueba QA"}, headers=sa))
ev = ok(requests.post(f"{API}/evaluaciones", json={"paciente_id": pid, "medico_nombre": "Dr QA", "motivo_consulta": "control", "fecha": "2026-11-10", "igss_orden_id": o_at["id"]}, headers=sa))
out["eval_id"] = ev.get("id")
ev2 = ok(requests.post(f"{API}/evaluaciones", json={"paciente_id": pid, "medico_nombre": "Dr QA", "motivo_consulta": "control", "fecha": "2026-11-11", "igss_orden_id": o_bc["id"]}, headers=sa))
cx_ids = []
for i in range(3):
    cx = ok(requests.post(f"{API}/surgeries", json={"date": f"2026-11-1{2+i}", "time": "08:00", "patient_name": f"TEST_QA Paciente {TAG}", "patient_id": pid, "procedure": "Inyección", "surgeon": "Dr QA", "eye": "OD", "anesthesia_type": "topica", "anesthesiologist": "Dr A", "institution": "IGSS", "igss_data": {"unit": "X", "unit_id": uid, "sps": f"QA4-{TAG}", "affiliation_number": "AF", "code": "C1", "procedure_cost": 100}}, headers=sa))
    cx_ids.append(cx["id"])
    print("realizada", ok(requests.post(f"{API}/surgeries/{cx['id']}/realizada", json={"realizada": True}, headers=sa)).get("libro"))
out["cx_ids"] = cx_ids
# 8 órdenes pendientes en NOG90 (la 9ª se crea por UI para ver el toast de 90 %)
out["ordenes90"] = [orden(out["nog90_id"], f"Q90-{TAG}-{i}")["id"] for i in range(8)]
print(json.dumps(requests.get(f"{API}/igss-units/{uid}/nogs", headers=sa).json(), default=str)[:1500])
json.dump(out, open('/tmp/qa_seed.json', 'w'))
print(out)
