"""Prueba: Sala de Operaciones — Seguro Privado + nombre del seguro, anestesia local_asistida."""
import os, sys, requests

API = os.environ["API_URL"].rstrip("/") + "/api"


def main():
    s = requests.Session()
    tk = s.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30).json()["access_token"]
    H = {"Authorization": f"Bearer {tk}"}

    base = {
        "date": "2026-12-20", "time": "10:00", "patient_name": "Paciente SalaOp Test",
        "procedure": "Facoemulsificación", "surgeon": "Dr. Prueba", "eye": "OD",
        "anesthesia_type": "local_asistida", "anesthesiologist": "Dr. Anest",
    }
    ok = True
    creadas = []

    # 1) Seguro Privado SIN nombre => 400
    r = s.post(f"{API}/surgeries", headers=H, json={**base, "institution": "Seguro Privado"}, timeout=30)
    print(f"  Seguro Privado sin nombre (esperado 400): {r.status_code} -> {r.json().get('detail')}")
    ok = ok and r.status_code == 400

    # 2) Seguro Privado CON nombre => 200 y persiste insurance_name + anestesia
    r = s.post(f"{API}/surgeries", headers=H, json={**base, "institution": "Seguro Privado", "insurance_name": "Seguros G&T"}, timeout=30)
    print(f"  Seguro Privado con nombre (esperado 200): {r.status_code}")
    ok = ok and r.status_code == 200
    if r.status_code == 200:
        d = r.json()
        creadas.append(d["id"])
        print(f"    insurance_name={d.get('insurance_name')} anestesia={d.get('anesthesia_type')}")
        ok = ok and d.get("insurance_name") == "Seguros G&T" and d.get("anesthesia_type") == "local_asistida"

    # 3) Novavision => 200 (sin requerir seguro)
    r = s.post(f"{API}/surgeries", headers=H, json={**base, "institution": "Novavision"}, timeout=30)
    print(f"  Novavision (esperado 200): {r.status_code}")
    ok = ok and r.status_code == 200
    if r.status_code == 200:
        creadas.append(r.json()["id"])

    # Limpieza
    for cid in creadas:
        s.delete(f"{API}/surgeries/{cid}", headers=H, timeout=30)
    print(f"  {len(creadas)} cirugías de prueba eliminadas")

    print("\nRESULTADO:", "✅ OK" if ok else "❌ FALLO")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
