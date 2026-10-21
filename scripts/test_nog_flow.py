import os, requests, sys, random

API = os.popen("grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d'=' -f2").read().strip()
API = API + "/api"
print("API:", API)

def login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    r.raise_for_status()
    return r.json()["access_token"] if "access_token" in r.json() else r.json().get("token")

tok = login("superadmin", "nova2024")
H = {"Authorization": f"Bearer {tok}"}

# 1. Find or create an active IGSS unit
units = requests.get(f"{API}/igss-units", headers=H).json()
if isinstance(units, dict):
    units = units.get("data") or units.get("items") or units.get("units") or []
active_units = [u for u in units if u.get("is_active", True)]
assert active_units, "No hay unidades IGSS activas"
unit = active_units[0]
uid = unit["id"]
print("Unidad:", unit.get("nombre") or unit.get("name"), uid)

# 2. Create a NOG with cantidad=3
num = f"TEST-{random.randint(10000,99999)}"
payload = {
    "numero": num,
    "nombre_servicio": "Servicio prueba automatizada",
    "tipo_compra": "evento",
    "cantidad": 3,
    "precio_unitario": 100.0,
}
r = requests.post(f"{API}/igss-units/{uid}/nogs", headers=H, json=payload)
print("crear NOG:", r.status_code, r.text[:200])
r.raise_for_status()
nog = r.json()
nid = nog["id"]

def nog_state():
    r = requests.get(f"{API}/igss-units/{uid}/nogs", headers=H)
    data = r.json()
    arr = data.get("nogs") if isinstance(data, dict) else data
    for n in arr:
        if n["id"] == nid:
            return n
    return None

s = nog_state()
print("Inicial -> cantidad:", s["cantidad"], "acreditados:", s["acreditados"], "disponibles:", s["disponibles"])
assert s["acreditados"] == 0 and s["disponibles"] == 3

# 3. Create patient IGSS assigned to this NOG
dpi = "".join([str(random.randint(0,9)) for _ in range(13)])
pat = {
    "first_name": "Paciente", "last_name": "NOGtest", "gender": "masculino",
    "birth_date": "1990-01-01", "phone": "12345678", "dpi": dpi,
    "referral_institution": "igss", "igss_unit_id": uid, "igss_nog": num,
    "igss_afiliacion": "A1", "igss_tipo_paciente": "afiliado",
}
r = requests.post(f"{API}/patients", headers=H, json=pat)
print("crear paciente:", r.status_code, r.text[:200])
r.raise_for_status()
p = r.json()
pid = p["id"]

s = nog_state()
print("Tras asignar NOG -> acreditados:", s["acreditados"], "disponibles:", s["disponibles"])
assert s["acreditados"] == 1 and s["disponibles"] == 2, "No descontó al asignar!"

# 3b. Update patient without changing NOG -> should stay at 1 (no double)
r = requests.put(f"{API}/patients/{pid}", headers=H, json={"phone": "87654321"})
r.raise_for_status()
s = nog_state()
print("Tras editar (mismo NOG) -> acreditados:", s["acreditados"], "disponibles:", s["disponibles"])
assert s["acreditados"] == 1, "Doble descuento al editar!"

# 4. Reassign to no NOG (remove NOG) -> should release
r = requests.put(f"{API}/patients/{pid}", headers=H, json={"referral_institution": "particular"})
print("reasignar a particular:", r.status_code, r.text[:150])
r.raise_for_status()
s = nog_state()
print("Tras quitar NOG -> acreditados:", s["acreditados"], "disponibles:", s["disponibles"])
assert s["acreditados"] == 0 and s["disponibles"] == 3, "No liberó al quitar NOG!"

# 5. Reassign back to IGSS + NOG -> consume again
r = requests.put(f"{API}/patients/{pid}", headers=H, json={
    "referral_institution": "igss", "igss_unit_id": uid, "igss_nog": num})
r.raise_for_status()
s = nog_state()
print("Tras reasignar NOG -> acreditados:", s["acreditados"], "disponibles:", s["disponibles"])
assert s["acreditados"] == 1, "No reconsumió al reasignar!"

# 6. Deactivate patient -> release
r = requests.delete(f"{API}/patients/{pid}", headers=H)
r.raise_for_status()
s = nog_state()
print("Tras desactivar -> acreditados:", s["acreditados"], "disponibles:", s["disponibles"])
assert s["acreditados"] == 0, "No liberó al desactivar!"

# 7. Reactivate -> consume
r = requests.post(f"{API}/patients/{pid}/reactivate", headers=H)
r.raise_for_status()
s = nog_state()
print("Tras reactivar -> acreditados:", s["acreditados"], "disponibles:", s["disponibles"])
assert s["acreditados"] == 1, "No reconsumió al reactivar!"

# cleanup: deactivate patient and delete NOG
requests.delete(f"{API}/patients/{pid}", headers=H)
requests.delete(f"{API}/igss-units/nogs/{nid}", headers=H)
print("\n✅ TODAS LAS ASERCIONES PASARON")
