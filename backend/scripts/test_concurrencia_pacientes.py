"""Prueba de carga: creación simultánea de pacientes por varios usuarios.

Verifica que NO se generen números de expediente duplicados bajo concurrencia
(el bug de condición de carrera en get_next_record_number). Limpia los datos
de prueba al final (hard delete por id).
"""
import os
import sys
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

API = os.environ["API_URL"] + "/api"

USERS = [
    ("superadmin", "nova2024"),
    ("admin", "Admin2024Nuevo!"),
    ("usuario", "user2024"),
]

N_POR_USUARIO = 8  # 3 usuarios x 8 = 24 pacientes concurrentes


def login(username, password):
    r = requests.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=30)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


def crear_paciente(token, i, uname):
    payload = {
        "first_name": f"ConcurTest{uname}",
        "last_name": f"Paciente{i}",
        "gender": "masculino",
        "birth_date": "1990-01-01",
        "phone": "55551234",
        "referral_institution": "particular",
    }
    r = requests.post(f"{API}/patients", json=payload,
                      headers={"Authorization": f"Bearer {token}"}, timeout=30)
    return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else {}


def main():
    print(f"API: {API}")
    tokens = {}
    for u, p in USERS:
        try:
            tokens[u] = login(u, p)
            print(f"  login OK: {u}")
        except Exception as e:
            print(f"  login FAIL {u}: {e}")
    if not tokens:
        print("Sin tokens, abortando")
        sys.exit(1)

    tasks = []
    for u in tokens:
        for i in range(N_POR_USUARIO):
            tasks.append((tokens[u], i, u))

    results = []
    created_ids = []
    record_numbers = []
    t0 = time.time()
    # Todos en paralelo para maximizar la colisión
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futs = [ex.submit(crear_paciente, tk, i, u) for (tk, i, u) in tasks]
        for f in as_completed(futs):
            try:
                code, body = f.result()
                results.append(code)
                if code == 200 and body.get("id"):
                    created_ids.append(body["id"])
                    record_numbers.append(body.get("record_number"))
            except Exception as e:
                results.append(f"ERR {e}")
    dt = time.time() - t0

    ok = sum(1 for c in results if c == 200)
    print(f"\n--- Resultados ({len(tasks)} solicitudes en {dt:.2f}s) ---")
    print(f"  200 OK: {ok}")
    codes = {}
    for c in results:
        codes[c] = codes.get(c, 0) + 1
    print(f"  Códigos: {codes}")

    dups = [r for r in record_numbers if record_numbers.count(r) > 1]
    unique_dups = sorted(set(dups))
    print(f"  Expedientes creados: {len(record_numbers)}")
    print(f"  Expedientes ÚNICOS: {len(set(record_numbers))}")
    if unique_dups:
        print(f"  ❌ DUPLICADOS DETECTADOS: {unique_dups}")
    else:
        print(f"  ✅ Sin duplicados de expediente")

    # Limpieza: hard delete directo en Mongo de los pacientes de prueba
    print("\n--- Limpieza ---")
    try:
        from pymongo import MongoClient
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        mc = MongoClient(os.environ["MONGO_URL"])
        mdb = mc[os.environ["DB_NAME"]]
        res = mdb.patients.delete_many({"first_name": {"$regex": "^ConcurTest"}})
        print(f"  Eliminados (hard, Mongo): {res.deleted_count}")
    except Exception as e:
        print(f"  Limpieza FAIL: {e}")

    if unique_dups:
        sys.exit(2)


if __name__ == "__main__":
    main()
