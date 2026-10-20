import requests, re, random
from pymongo import MongoClient

PROD = "https://novavision-finanzas.emergent.host"
tok = requests.post(f"{PROD}/api/auth/login", json={"username": "superadmin", "password": "Cristian1980$"}, timeout=60).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

mc = MongoClient("mongodb://localhost:27017")
db = mc["test_database"]

# Totales
tp = requests.get(f"{PROD}/api/patients?page=1&limit=1", headers=H, timeout=60).json()["total"]
te = requests.get(f"{PROD}/api/evaluaciones?page=1&limit=1", headers=H, timeout=60).json()["total"]
print(f"PROD patients={tp}  evaluaciones={te}")

# Muestra de evaluaciones de varias paginas
pids = {}
orphans = 0
mismatch = 0
checked = 0
pages = random.sample(range(1, 365), 25)  # ~36419/100
for pg in pages:
    r = requests.get(f"{PROD}/api/evaluaciones?page={pg}&limit=100", headers=H, timeout=60).json()
    for e in r.get("data", []):
        pids[e["paciente_id"]] = e.get("paciente_expediente")

print(f"paciente_ids unicos muestreados: {len(pids)}")
for pid, exp in list(pids.items()):
    rp = requests.get(f"{PROD}/api/patients/{pid}", headers=H, timeout=60)
    checked += 1
    if rp.status_code != 200:
        orphans += 1
        if orphans <= 5:
            print(f"  ORPHAN eval pid={pid} exp={exp} -> {rp.status_code}")
        continue
    rec = rp.json().get("record_number")
    if str(rec) != str(exp):
        mismatch += 1
        if mismatch <= 5:
            print(f"  MISMATCH pid={pid} exp_eval={exp} record_number={rec}")
print(f"Pacientes verificados={checked}  orphans={orphans}  mismatch={mismatch}")

# Comparar conteo de evaluaciones por expediente: preview vs prod (5 expedientes)
print("\n--- comparacion por expediente (preview historico vs prod) ---")
sample_exps = [exp for exp in list(pids.values())[:6] if exp and re.match(r"^\d+$", str(exp))]
# map exp -> prod pid
exp2pid = {v: k for k, v in pids.items()}
for exp in sample_exps:
    pre = db.evaluaciones_oftalmologicas.count_documents({"paciente_expediente": str(exp), "import_source_id": {"$ne": None}})
    pid = exp2pid[exp]
    prod = requests.get(f"{PROD}/api/evaluaciones?paciente_id={pid}&page=1&limit=1", headers=H, timeout=60).json()["total"]
    print(f"  exp {exp}: preview={pre}  prod={prod}  {'OK' if pre==prod else 'DIFERENCIA'}")
