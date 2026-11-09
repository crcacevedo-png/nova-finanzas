# Helper for UI tests of persistent diagnoses: setup/inspect/cleanup TEST data via API
import os, sys, json, requests, datetime
BASE = open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0].rstrip('/') + '/api'
STATE = '/tmp/dx_state.json'

def tok():
    r = requests.post(f"{BASE}/auth/login", json={"username": "superadmin", "password": "nova2024"})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

def days_ago(n):
    return (datetime.date.today() - datetime.timedelta(days=n)).isoformat()

cmd = sys.argv[1]
H = tok()
if cmd == 'setup':
    p = requests.post(f"{BASE}/patients/quick", json={"name": "TEST_DxPersist Paciente"}, headers=H)
    print(p.status_code, p.text[:200]); p = p.json()
    e = requests.post(f"{BASE}/evaluaciones", json={
        "paciente_id": p["id"], "fecha": days_ago(3), "motivo_consulta": "TEST_motivo previo",
        "diagnosticos": [
            {"descripcion": "TEST_Glaucoma primario", "codigo_cie10": "", "ojo": "OD"},
            {"descripcion": "TEST_Catarata senil", "codigo_cie10": "", "ojo": "OS"}]}, headers=H)
    print(e.status_code, e.text[:200])
    json.dump({"patient_id": p["id"], "name": p.get("first_name", "") + " " + p.get("last_name", ""), "evals": [e.json()["id"]]}, open(STATE, 'w'))
elif cmd == 'list':
    st = json.load(open(STATE))
    r = requests.get(f"{BASE}/evaluaciones", params={"paciente_id": st["patient_id"]}, headers=H)
    data = r.json(); items = data if isinstance(data, list) else data.get("data", [])
    for ev in items:
        print(ev["id"], ev.get("fecha"), ev.get("lectura_examenes"), ev.get("motivo_consulta"), json.dumps(ev.get("diagnosticos")))
    h = requests.get(f"{BASE}/evaluaciones/paciente/{st['patient_id']}/historial-medico", headers=H).json()
    print("ACTIVOS:", h.get("diagnosticos_activos"))
elif cmd == 'shift':
    # move today's eval to N days ago to simulate another day
    st = json.load(open(STATE)); eid = sys.argv[2]; n = int(sys.argv[3])
    r = requests.patch(f"{BASE}/evaluaciones/{eid}/autoguardar", json={"fecha": days_ago(n)}, headers=H)
    print(r.status_code, r.json().get("fecha"))
elif cmd == 'cleanup':
    st = json.load(open(STATE))
    r = requests.get(f"{BASE}/evaluaciones", params={"paciente_id": st["patient_id"]}, headers=H)
    data = r.json(); items = data if isinstance(data, list) else data.get("data", [])
    for ev in items:
        if ev.get("paciente_id") == st["patient_id"]:
            print("del eval", requests.delete(f"{BASE}/evaluaciones/{ev['id']}", headers=H).status_code)
    print("del patient", requests.delete(f"{BASE}/patients/{st['patient_id']}", headers=H).status_code)
