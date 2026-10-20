import requests, random
from pymongo import MongoClient

PROD = "https://novavision-finanzas.emergent.host"
tok = requests.post(f"{PROD}/api/auth/login", json={"username": "superadmin", "password": "Cristian1980$"}, timeout=60).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

# 1) Cargar TODOS los ids y record_numbers de pacientes de produccion
print("Cargando ids de pacientes de produccion...")
prod_ids = {}
page = 1
while True:
    r = requests.get(f"{PROD}/api/patients?page={page}&limit=100", headers=H, timeout=60).json()
    for p in r.get("data", []):
        prod_ids[p["id"]] = p.get("record_number")
    if page >= r.get("total_pages", 1):
        break
    page += 1
print(f"  pacientes cargados: {len(prod_ids)}")

# 2) Muestrear evaluaciones y medir huerfanas localmente
te = requests.get(f"{PROD}/api/evaluaciones?page=1&limit=1", headers=H, timeout=60).json()["total"]
import math
total_pages = math.ceil(te / 100)
sample_pages = random.sample(range(1, total_pages + 1), min(40, total_pages))
linked = orphan = mismatch = total_sampled = 0
orphan_exps = []
for pg in sample_pages:
    r = requests.get(f"{PROD}/api/evaluaciones?page={pg}&limit=100", headers=H, timeout=60).json()
    for e in r.get("data", []):
        total_sampled += 1
        pid = e["paciente_id"]
        exp = str(e.get("paciente_expediente") or "")
        if pid not in prod_ids:
            orphan += 1
            if len(orphan_exps) < 10:
                orphan_exps.append(exp)
        elif str(prod_ids[pid]) != exp:
            mismatch += 1
        else:
            linked += 1
print(f"\nEvals total prod={te}")
print(f"Muestreadas={total_sampled}  linked={linked}  orphan={orphan}  mismatch={mismatch}")
print(f"% huerfanas ~ {100*orphan/max(total_sampled,1):.1f}%")
print("ejemplos exp huerfanas:", orphan_exps)
