# Helper: print IGSS units and their active NOG counters (used to verify surgery IGSS capture doesn't consume NOG)
import os, json, requests
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"username": "superadmin", "password": "nova2024"})
print("login", r.status_code)
tok = r.json().get("access_token") or r.json().get("token")
if tok:
    s.headers["Authorization"] = f"Bearer {tok}"
units = s.get(f"{BASE}/api/igss-units").json()["data"]
for u in units:
    nogs = s.get(f"{BASE}/api/igss-units/{u['id']}/nogs-activos").json()
    print(u.get('name'), u['id'])
    for n in nogs:
        print("   ", json.dumps({k: n.get(k) for k in n if k not in ('servicios',)}, default=str)[:600])
surg = s.get(f"{BASE}/api/surgeries").json()
items = surg if isinstance(surg, list) else surg.get('items', surg)
print("surgeries:", len(items))
for x in items:
    print("  ", x.get('patient_name'), x.get('institution'), x.get('procedure'), x.get('igss_data'))
