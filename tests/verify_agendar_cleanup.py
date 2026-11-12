# Verification + cleanup for UI-created data (Agregar a Agenda IGSS)
import os, sys, requests
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
s = requests.Session()
tok = s.post(f"{BASE}/api/auth/login", json={"username": "superadmin", "password": "nova2024"}).json()
s.headers["Authorization"] = f"Bearer {tok.get('access_token') or tok.get('token')}"
PID = '4ceb89de-628f-4aa9-a545-fe6c4f4affc5'
meds = {d['name']: d['id'] for d in s.get(f"{BASE}/api/medicos-agenda").json()['data']}
for f in ['2026-12-15', '2026-12-16', '2026-12-17', '2026-12-18']:
    r = s.get(f"{BASE}/api/agenda/citas", params={"fecha": f}).json()
    items = r.get('data') or []
    mine = [(c['id'], c['medico_nombre'], c['hora_inicio'], c.get('notas'), c.get('referral_institution_label')) for c in items if c.get('paciente_id') == PID]
    print(f, mine)
if len(sys.argv) > 1 and sys.argv[1] == 'cleanup':
    surg = sys.argv[2].split(',') if len(sys.argv) > 2 and sys.argv[2] else []
    citas = sys.argv[3].split(',') if len(sys.argv) > 3 and sys.argv[3] else []
    for c in citas:
        print('del cita', c, s.delete(f"{BASE}/api/agenda/citas/{c}").status_code)
    for x in surg:
        print('del surgery', x, s.delete(f"{BASE}/api/surgeries/{x}").status_code)
