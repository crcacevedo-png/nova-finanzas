import os, json, requests, sys
BASE = open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0].rstrip('/')
s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"username": "superadmin", "password": "nova2024"})
print("login", r.status_code, list(r.json().keys()))
tok = r.json().get("access_token") or r.json().get("token")
if tok:
    s.headers["Authorization"] = f"Bearer {tok}"
mode = sys.argv[1] if len(sys.argv) > 1 else "setup"
if mode == "setup":
    docs = s.get(f"{BASE}/api/agenda/medicos").json() if s.get(f"{BASE}/api/agenda/medicos").ok else s.get(f"{BASE}/api/doctors").json()
    docs = docs.get("data", docs) if isinstance(docs, dict) else docs
    print("doctors", len(docs), [(d.get("id"), d.get("nombre") or d.get("name")) for d in docs][:5])
    pts = s.get(f"{BASE}/api/patients", params={"limit": 3}).json()
    pts = pts.get("data", pts.get("items", pts)) if isinstance(pts, dict) else pts
    print("patients", [(p["id"], p.get("nombre_completo") or p.get("first_name")) for p in pts[:3]])
    prefs = s.get(f"{BASE}/api/agenda/preferencias-medicos").json()
    print("prefs", prefs)
    created = []
    for i, d in enumerate(docs):
        if len(created) >= 2:
            break
        p = pts[len(created)]
        body = {"paciente_id": p["id"], "paciente_nombre": "TEST_Fix" + str(i), "medico_id": d["id"],
                "medico_nombre": d.get("nombre") or d.get("name"), "fecha": "2026-11-07",
                "hora_inicio": f"1{5+i}:00", "tipo_cita": "Subsecuente"}
        r = s.post(f"{BASE}/api/agenda/citas", json=body)
        print("create", r.status_code, r.text[:200])
        if r.ok:
            created.append({"id": r.json()["id"], "medico_id": d["id"], "paciente_id": p["id"]})
    json.dump({"created": created, "prefs": prefs}, open("/tmp/agenda_fix_state.json", "w"))
    print(json.dumps(created))
elif mode == "hide":
    st = json.load(open("/tmp/agenda_fix_state.json"))
    hid = st["created"][1]["medico_id"]
    r = s.put(f"{BASE}/api/agenda/preferencias-medicos", json={"orden": st["prefs"]["orden"], "ocultos": list(set(st["prefs"]["ocultos"] + [hid]))})
    print("hide", r.status_code, r.text)
elif mode == "cleanup":
    st = json.load(open("/tmp/agenda_fix_state.json"))
    r = s.put(f"{BASE}/api/agenda/preferencias-medicos", json=st["prefs"])
    print("restore prefs", r.status_code, r.text)
    for c in st["created"]:
        r = s.delete(f"{BASE}/api/agenda/citas/{c['id']}")
        print("delete", c["id"], r.status_code)
elif mode == "get":
    st = json.load(open("/tmp/agenda_fix_state.json"))
    for c in st["created"]:
        r = s.get(f"{BASE}/api/agenda/citas/{c['id']}").json()
        print(c["id"], r.get("estado"), r.get("hora_llegada"), r.get("estado_previo"))
