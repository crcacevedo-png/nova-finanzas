import requests, json, math, random
PROD = "https://novavision-finanzas.emergent.host"
tok = requests.post(f"{PROD}/api/auth/login", json={"username": "superadmin", "password": "Cristian1980$"}, timeout=60).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
prod = json.load(open("/app/scripts/prod_patient_ids.json"))
ids = set(prod.keys())
te = requests.get(f"{PROD}/api/evaluaciones?page=1&limit=1", headers=H, timeout=60).json()["total"]
tp = math.ceil(te/100)
pages = random.sample(range(1, tp+1), min(50, tp))
linked=orphan=mismatch=n=0
oex=[]
for pg in pages:
    r = requests.get(f"{PROD}/api/evaluaciones?page={pg}&limit=100", headers=H, timeout=60).json()
    for e in r.get("data", []):
        n+=1
        pid=e["paciente_id"]; exp=str(e.get("paciente_expediente") or "")
        if pid not in ids:
            orphan+=1
            if len(oex)<15: oex.append(exp)
        elif str(prod[pid])!=exp: mismatch+=1
        else: linked+=1
print(f"evals_total={te} sampled={n} linked={linked} orphan={orphan} mismatch={mismatch}")
print(f"orphan_pct={100*orphan/max(n,1):.1f}% ejemplos={oex}")
