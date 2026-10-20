"""Migración preview -> producción vía API HTTPS.
Uso: python migrate_to_prod.py [deldemo|patients|evals|verify]
"""
import sys, re, json, time, requests
from pymongo import MongoClient

PROD = "https://novavision-finanzas.emergent.host"
USER = "superadmin"
PWD = "Cristian1980$"

mc = MongoClient("mongodb://localhost:27017")
db = mc["test_database"]

NUM_Q = {"record_number": re.compile(r"^\d+$")}


def login():
    r = requests.post(f"{PROD}/api/auth/login", json={"username": USER, "password": PWD}, timeout=60)
    r.raise_for_status()
    return r.json()["access_token"]


def headers(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def del_demo(tok):
    r = requests.get(f"{PROD}/api/patients?page=1&limit=100", headers=headers(tok), timeout=60)
    data = r.json().get("data", [])
    print(f"Pacientes demo actuales: {len(data)}")
    for p in data:
        if re.match(r"^EXP-", p.get("record_number", "")):
            dr = requests.delete(f"{PROD}/api/patients/{p['id']}", headers=headers(tok), timeout=60)
            print(f"  delete {p['record_number']} -> {dr.status_code}")


def pat_payload(p):
    inst = p.get("referral_institution") or "particular"
    item = {
        "record_number": p["record_number"],
        "first_name": p.get("first_name", ""),
        "last_name": p.get("last_name", ""),
        "gender": p.get("gender", ""),
        "birth_date": p.get("birth_date", ""),
        "phone": p.get("phone", ""),
        "email": p.get("email", ""),
        "dpi": p.get("dpi", ""),
        "profession": p.get("profession", ""),
        "referral_institution": inst,
        "insurance_name": p.get("insurance_name", ""),
        "otra_institucion": p.get("other_institution_name", ""),
        "comments": p.get("comments", ""),
        "direccion": p.get("address", "") or p.get("direccion", ""),
        "emergency_phone": p.get("emergency_phone", ""),
        "emergency_contact_name": p.get("emergency_contact_name", ""),
        "emergency_contact_relationship": p.get("emergency_contact_relationship", ""),
    }
    if inst == "igss":
        item.update({
            "igss_unidad": p.get("igss_unidad", ""),
            "igss_afiliacion": p.get("igss_afiliacion", ""),
            "igss_no_sps": p.get("igss_no_sps", ""),
            "igss_codigo": p.get("igss_codigo", ""),
            "igss_nog": p.get("igss_nog", ""),
            "igss_tipo_compra": p.get("igss_tipo_compra", ""),
        })
    return item


def migrate_patients(tok):
    total = db.patients.count_documents(NUM_Q)
    print(f"Total pacientes a migrar: {total}")
    CHUNK = 500
    batch, inserted, dups, errs = [], 0, 0, 0
    bn = 0
    cur = db.patients.find(NUM_Q, {"_id": 0})
    processed = 0
    for p in cur:
        batch.append(pat_payload(p))
        if len(batch) >= CHUNK:
            bn += 1
            i, d, e = post_patients(tok, batch, bn)
            inserted += i; dups += d; errs += e
            processed += len(batch)
            print(f"  lote {bn}: +{i} ins, {d} dup, {e} err | acumulado ins={inserted} ({processed}/{total})")
            batch = []
    if batch:
        bn += 1
        i, d, e = post_patients(tok, batch, bn)
        inserted += i; dups += d; errs += e
        processed += len(batch)
        print(f"  lote {bn}: +{i} ins, {d} dup, {e} err | acumulado ins={inserted} ({processed}/{total})")
    print(f"PACIENTES -> insertados={inserted} duplicados={dups} errores={errs}")


def post_patients(tok, batch, bn, retries=3):
    body = {"patients": batch, "batch_number": bn, "total_batches": 0,
            "skip_duplicates": False, "preserve_record_numbers": True}
    for a in range(retries):
        try:
            r = requests.post(f"{PROD}/api/patients/import/batch", headers=headers(tok),
                              data=json.dumps(body), timeout=180)
            if r.status_code == 200:
                j = r.json()
                return j.get("inserted", 0), j.get("duplicates", 0), j.get("errors", 0)
            print(f"    HTTP {r.status_code}: {r.text[:200]}")
        except Exception as ex:
            print(f"    intento {a+1} falló: {ex}")
        time.sleep(3)
    return 0, 0, len(batch)


EVAL_Q = {"import_source_id": {"$ne": None}}


def eval_payload(e):
    d = {k: v for k, v in e.items() if k != "_id"}
    d["expediente"] = str(e.get("paciente_expediente") or "")
    d["id_origen"] = str(e.get("import_source_id") or "")
    return d


def post_evals(tok, batch, bn, retries=3):
    body = {"items": batch, "batch_number": bn, "skip_duplicates": True}
    for a in range(retries):
        try:
            r = requests.post(f"{PROD}/api/evaluaciones/import/batch", headers=headers(tok),
                              data=json.dumps(body, default=str), timeout=240)
            if r.status_code == 200:
                j = r.json()
                return j.get("inserted", 0), j.get("duplicates", 0), j.get("orphaned", 0), j.get("sin_clave", 0)
            print(f"    HTTP {r.status_code}: {r.text[:200]}")
        except Exception as ex:
            print(f"    intento {a+1} falló: {ex}")
        time.sleep(3)
    return 0, 0, 0, len(batch)


def migrate_evals(tok):
    total = db.evaluaciones_oftalmologicas.count_documents(EVAL_Q)
    print(f"Total evaluaciones a migrar: {total}")
    CHUNK = 200
    batch, ins, dup, orf, sc = [], 0, 0, 0, 0
    bn = 0
    processed = 0
    for e in db.evaluaciones_oftalmologicas.find(EVAL_Q, {"_id": 0}):
        batch.append(eval_payload(e))
        if len(batch) >= CHUNK:
            bn += 1
            i, d, o, s = post_evals(tok, batch, bn)
            ins += i; dup += d; orf += o; sc += s
            processed += len(batch)
            print(f"  lote {bn}: +{i} ins, {d} dup, {o} huerf, {s} sinclave | ins={ins} ({processed}/{total})")
            batch = []
    if batch:
        bn += 1
        i, d, o, s = post_evals(tok, batch, bn)
        ins += i; dup += d; orf += o; sc += s
        processed += len(batch)
        print(f"  lote {bn}: +{i} ins, {d} dup, {o} huerf, {s} sinclave | ins={ins} ({processed}/{total})")
    print(f"EVALUACIONES -> insertadas={ins} duplicadas={dup} huerfanas={orf} sinclave={sc}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    tok = login()
    print("login OK")
    if mode == "deldemo":
        del_demo(tok)
    elif mode == "patients":
        migrate_patients(tok)
    elif mode == "evals":
        migrate_evals(tok)
    elif mode == "verify":
        r = requests.get(f"{PROD}/api/patients?page=1&limit=1", headers=headers(tok), timeout=60)
        print("prod patients total:", r.json().get("total"))
