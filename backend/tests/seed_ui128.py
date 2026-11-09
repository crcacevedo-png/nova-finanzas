# helper: create TEST_UI128 surgeries for UI tests (prints ids)
import os, sys, requests
B = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
t = requests.post(f"{B}/api/auth/login", json={"username": "usuario", "password": "user2024"}).json()
h = {"Authorization": f"Bearer {t.get('access_token') or t.get('token')}"}
if sys.argv[1:] and sys.argv[1] == 'list':
    r = requests.get(f"{B}/api/surgeries", params={"search": "TEST_UI128", "limit": 100}, headers=h).json()
    for s in r["data"]:
        print(s["id"], s["patient_name"], s["date"], s["time"], s["status"], s.get("new_surgery_id"), s.get("rescheduled_from_surgery_id", ""))
elif sys.argv[1:] and sys.argv[1] == 'cleanup':
    for sid in sys.argv[2:]:
        print(sid, requests.delete(f"{B}/api/surgeries/{sid}", headers=h).status_code)
else:
    for n in ["A", "B", "C", "D"]:
        r = requests.post(f"{B}/api/surgeries", headers=h, json={"date": "2026-01-20", "time": "09:00", "patient_name": f"TEST_UI128_{n}",
            "procedure": "Facoemulsificación", "surgeon": "Dr. Carlos Méndez", "eye": "OD", "anesthesia_type": "local", "lio": "TEST_LIO",
            "anesthesiologist": "TEST_Anest", "institution": "Novavision", "observations": "TEST_obs"})
        print(n, r.status_code, r.json().get("id"))
