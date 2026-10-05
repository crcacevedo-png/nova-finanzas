"""Prueba: nota de cirugía en historial clínico (crear, editar, cerrar, bloqueo)."""
import os, sys, requests

API = os.environ["API_URL"].rstrip("/") + "/api"


def main():
    s = requests.Session()
    tk = s.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30).json()["access_token"]
    H = {"Authorization": f"Bearer {tk}"}
    # token usuario (no superadmin)
    tu = s.post(f"{API}/auth/login", json={"username": "usuario", "password": "user2024"}, timeout=30).json().get("access_token")
    HU = {"Authorization": f"Bearer {tu}"}

    pac = s.get(f"{API}/patients?limit=1", headers=H, timeout=30).json()["data"][0]
    PAC = pac["id"]
    ok = True
    creadas = []

    # 1) Crear cirugía CON patient_id => crea nota
    r = s.post(f"{API}/surgeries", headers=H, json={
        "date": "2026-12-22", "time": "10:00", "patient_name": "Nota Test",
        "patient_id": PAC, "procedure": "Vitrectomía", "surgeon": "Dr. X", "eye": "OD",
        "anesthesia_type": "general", "anesthesiologist": "Dr. A", "institution": "Novavision"
    }, timeout=30)
    assert r.status_code == 200, f"crear cirugia {r.status_code}: {r.text}"
    SID = r.json()["id"]; creadas.append(SID)
    print(f"  cirugía creada con paciente: {r.status_code}")

    # 2) Listar notas del paciente => debe existir 1 con el procedimiento
    r = s.get(f"{API}/surgery-notes?patient_id={PAC}", headers=H, timeout=30)
    notas = [n for n in r.json()["data"] if n["surgery_id"] == SID]
    print(f"  notas del paciente para esta cirugía: {len(notas)}")
    ok = ok and len(notas) == 1 and notas[0]["procedure"] == "Vitrectomía" and notas[0]["estado"] == "abierta"
    NID = notas[0]["id"]

    # 3) Editar la nota (abierta) => 200
    r = s.put(f"{API}/surgery-notes/{NID}", headers=H, json={"contenido": "<b>Procedimiento</b> sin complicaciones"}, timeout=30)
    print(f"  editar nota abierta: {r.status_code} editable={r.json().get('editable')}")
    ok = ok and r.status_code == 200 and "Procedimiento" in r.json().get("contenido", "")

    # 4) Cirugía SIN patient_id => NO crea nota
    r = s.post(f"{API}/surgeries", headers=H, json={
        "date": "2026-12-22", "time": "11:00", "patient_name": "Sin Registro",
        "procedure": "Faco", "surgeon": "Dr. X", "eye": "OD",
        "anesthesia_type": "local", "anesthesiologist": "Dr. A", "institution": "Novavision"
    }, timeout=30)
    SID2 = r.json()["id"]; creadas.append(SID2)
    r2 = s.get(f"{API}/surgery-notes?surgery_id={SID2}", headers=H, timeout=30)
    print(f"  cirugía sin paciente -> notas creadas: {r2.json().get('total')} (esperado 0)")
    ok = ok and r2.json().get("total") == 0

    # 5) Cerrar la nota => queda cerrada/bloqueada
    r = s.post(f"{API}/surgery-notes/{NID}/close", headers=H, timeout=30)
    print(f"  cerrar nota: {r.status_code} estado={r.json().get('estado')} bloqueada={r.json().get('bloqueada')}")
    ok = ok and r.status_code == 200 and r.json().get("estado") == "cerrada"

    # 6) Editar nota cerrada como 'usuario' => 403
    if tu:
        r = s.put(f"{API}/surgery-notes/{NID}", headers=HU, json={"contenido": "hack"}, timeout=30)
        print(f"  editar cerrada como usuario (esperado 403): {r.status_code}")
        ok = ok and r.status_code == 403

    # 7) Editar nota cerrada como superadmin => 200 (excepción)
    r = s.put(f"{API}/surgery-notes/{NID}", headers=H, json={"contenido": "<b>Corrección</b> del superadmin"}, timeout=30)
    print(f"  editar cerrada como superadmin (esperado 200): {r.status_code}")
    ok = ok and r.status_code == 200

    # Limpieza
    for cid in creadas:
        s.delete(f"{API}/surgeries/{cid}", headers=H, timeout=30)
    # borrar notas directamente
    import os as _os
    from pymongo import MongoClient
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    mc = MongoClient(_os.environ["MONGO_URL"]); mdb = mc[_os.environ["DB_NAME"]]
    mdb.notas_cirugia.delete_many({"surgery_id": {"$in": creadas}})
    print(f"  limpieza: {len(creadas)} cirugías + notas eliminadas")

    print("\nRESULTADO:", "✅ OK" if ok else "❌ FALLO")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
