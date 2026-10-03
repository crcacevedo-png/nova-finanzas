"""Prueba del horario de disponibilidad por médico (enforcement interno + API externa)."""
import os, sys, requests

API = os.environ["API_URL"].rstrip("/") + "/api"
KEY = os.environ["AGENDA_API_KEY"]


def main():
    s = requests.Session()
    tk = s.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30).json()["access_token"]
    H = {"Authorization": f"Bearer {tk}"}

    ds = s.get(f"{API}/doctors?limit=1", headers=H, timeout=30).json()
    d = (ds.get("data") or ds.get("doctors"))[0]
    MED, MEDN = d["id"], d.get("name") or d.get("nombre") or "Dr"
    horario_original = d.get("horario_semanal")
    pac = s.get(f"{API}/patients?limit=1", headers=H, timeout=30).json()["data"][0]
    PAC = pac["id"]
    print(f"MED={MED}")

    # 2026-12-14 es LUNES (isoweekday=1), 2026-12-15 MARTES (=2).
    # Config: Lunes 08:00-12:00 activo; Martes inactivo.
    horario = {
        "1": {"activo": True, "hora_inicio": "08:00", "hora_fin": "12:00"},
        "2": {"activo": False, "hora_inicio": "", "hora_fin": ""},
    }
    r = s.put(f"{API}/doctors/{MED}", headers=H, json={"horario_semanal": horario}, timeout=30)
    assert r.status_code == 200, f"update horario {r.status_code}: {r.text}"
    print("  horario configurado (Lun 08-12, Mar libre)")

    ok = True
    creadas = []
    HK = {"X-API-Key": KEY}
    LUN = "2026-12-14"
    MAR = "2026-12-15"

    # Dentro de horario (Lunes 09:00) => 200
    r = s.post(f"{API}/agenda/citas", headers=H, json={
        "paciente_id": PAC, "paciente_nombre": "Dentro Horario", "medico_id": MED,
        "medico_nombre": MEDN, "fecha": LUN, "hora_inicio": "09:00",
        "duracion_minutos": 20, "tipo_cita": "Subsecuente"}, timeout=30)
    print(f"  cita Lun 09:00 dentro (esperado 200): {r.status_code}")
    ok = ok and r.status_code == 200
    if r.status_code == 200: creadas.append(r.json()["id"])

    # Fuera de horario (Lunes 13:00) => 409
    r = s.post(f"{API}/agenda/citas", headers=H, json={
        "paciente_id": PAC, "paciente_nombre": "Fuera Horario", "medico_id": MED,
        "medico_nombre": MEDN, "fecha": LUN, "hora_inicio": "13:00",
        "duracion_minutos": 20, "tipo_cita": "Subsecuente"}, timeout=30)
    print(f"  cita Lun 13:00 fuera (esperado 409): {r.status_code} -> {r.json().get('detail')}")
    ok = ok and r.status_code == 409

    # Día que no atiende (Martes 09:00) => 409
    r = s.post(f"{API}/agenda/citas", headers=H, json={
        "paciente_id": PAC, "paciente_nombre": "Martes Libre", "medico_id": MED,
        "medico_nombre": MEDN, "fecha": MAR, "hora_inicio": "09:00",
        "duracion_minutos": 20, "tipo_cita": "Subsecuente"}, timeout=30)
    print(f"  cita Mar (no atiende, esperado 409): {r.status_code} -> {r.json().get('detail')}")
    ok = ok and r.status_code == 409

    # API externa disponibilidad fuera de horario => disponible False
    r = requests.get(f"{API}/agenda/external/disponibilidad", headers=HK,
                     params={"medico_id": MED, "fecha": LUN, "hora_inicio": "13:00", "hora_fin": "13:20"}, timeout=30)
    jd = r.json()
    print(f"  externa fuera horario: disponible={jd.get('disponible')} motivo={jd.get('motivo')}")
    ok = ok and jd.get("disponible") is False

    # API externa disponibilidad dentro de horario (10:00) => True
    r = requests.get(f"{API}/agenda/external/disponibilidad", headers=HK,
                     params={"medico_id": MED, "fecha": LUN, "hora_inicio": "10:00", "hora_fin": "10:20"}, timeout=30)
    jd = r.json()
    print(f"  externa dentro horario: disponible={jd.get('disponible')}")
    ok = ok and jd.get("disponible") is True

    # Limpieza
    print("--- Limpieza ---")
    for cid in creadas:
        s.delete(f"{API}/agenda/citas/{cid}", headers=H, timeout=30)
    # Restaurar horario original del médico
    s.put(f"{API}/doctors/{MED}", headers=H, json={"horario_semanal": horario_original}, timeout=30)
    print(f"  {len(creadas)} citas eliminadas, horario restaurado")

    print("\nRESULTADO:", "✅ OK" if ok else "❌ FALLO")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
