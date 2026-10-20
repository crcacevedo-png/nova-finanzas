import requests, json
PROD = "https://novavision-finanzas.emergent.host"
tok = requests.post(f"{PROD}/api/auth/login", json={"username": "superadmin", "password": "Cristian1980$"}, timeout=60).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
ids = {}
page = 1
while True:
    r = requests.get(f"{PROD}/api/patients?page={page}&limit=100", headers=H, timeout=60).json()
    for p in r.get("data", []):
        ids[p["id"]] = p.get("record_number")
    tp = r.get("total_pages", 1)
    if page % 20 == 0:
        print(f"page {page}/{tp} ids={len(ids)}", flush=True)
    if page >= tp:
        break
    page += 1
json.dump(ids, open("/app/scripts/prod_patient_ids.json", "w"))
print("DONE ids=", len(ids))
