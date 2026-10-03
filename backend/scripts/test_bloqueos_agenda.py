"""Prueba del flujo de Bloqueos de Agenda + API del agente externo."""
import os
import sys
import requests

API = os.environ["API_URL"].rstrip("/") + "/api"
KEY = os.environ["AGENDA_API_KEY"]
FECHA = "2026-12-15"


def main():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    tk = r.json().get("access_token")
    H = {"Authorization": f"Bearer {tk}"}
    print("login OK")

    med = s.get(f"{API}/doctors?limit=1", headers=H, timeout=30).json()
    ds = med.get("data") or med.get("doctors") or []
    MED = ds[0]["id"]
    MEDN = ds[0].get("name") or ds[0].get("nombre") or "Dr"
    pac = s.get(f"{API}/patients?limit=1", headers=H, timeout=30).json()
    ps = pac.get("data") or []
    PAC = ps[0]["id"]
    print(f"MED={MED} PAC={PAC}")

    ok = True
    creadas = []

    # 1) Crear bloqueo de médico (franja 10:00-12:00)
    r = s.post(f"{API}/agenda/bloqueos", headers=H, json={
        "tipo": "medico", "medico_id": MED, "medico_nombre": MEDN,
        "fecha_inicio": FECHA, "dia_completo": False,
        "hora_inicio": "10:00", "hora_fin": "12:00", "motivo": "Congreso"
    }, timeout=30)
    assert r.status_code == 200, f"crear bloqueo medico {r.status_code}: {r.text}"
    BID = r.json()["bloqueo"]["id"]
    print(f"  bloqueo medico creado id={BID} conflictos={len(r.json()['citas_en_conflicto'])}")

    # 2) Cita interna dentro de la franja (10:30) => 409
    r = s.post(f"{API}/agenda/citas", headers=H, json={
        "paciente_id": PAC, "paciente_nombre": "Test Bloqueo", "medico_id": MED,
        "medico_nombre": MEDN, "fecha": FECHA, "hora_inicio": "10:30",
        "duracion_minutos": 20, "tipo_cita": "Subsecuente"
    }, timeout=30)
    print(f"  cita bloqueada (esperado 409): {r.status_code}")
    ok = ok and r.status_code == 409

    # 3) Cita interna fuera de la franja (13:00) => 200
    r = s.post(f"{API}/agenda/citas", headers=H, json={
        "paciente_id": PAC, "paciente_nombre": "Test Libre", "medico_id": MED,
        "medico_nombre": MEDN, "fecha": FECHA, "hora_inicio": "13:00",
        "duracion_minutos": 20, "tipo_cita": "Subsecuente"
    }, timeout=30)
    print(f"  cita libre (esperado 200): {r.status_code}")
    ok = ok and r.status_code == 200
    if r.status_code == 200:
        creadas.append(r.json()["id"])

    # 4) API externa SIN clave => 401
    r = requests.get(f"{API}/agenda/external/disponibilidad",
                     params={"medico_id": MED, "fecha": FECHA, "hora_inicio": "10:30", "hora_fin": "10:50"}, timeout=30)
    print(f"  externa sin clave (esperado 401): {r.status_code}")
    ok = ok and r.status_code == 401

    # 5) API externa disponibilidad en franja bloqueada => disponible False
    HK = {"X-API-Key": KEY}
    r = requests.get(f"{API}/agenda/external/disponibilidad", headers=HK,
                     params={"medico_id": MED, "fecha": FECHA, "hora_inicio": "10:30", "hora_fin": "10:50"}, timeout=30)
    jd = r.json()
    print(f"  externa disponibilidad bloqueada: {r.status_code} disponible={jd.get('disponible')} motivo={jd.get('motivo')}")
    ok = ok and r.status_code == 200 and jd.get("disponible") is False

    # 6) API externa disponibilidad libre (14:00) => disponible True
    r = requests.get(f"{API}/agenda/external/disponibilidad", headers=HK,
                     params={"medico_id": MED, "fecha": FECHA, "hora_inicio": "14:00", "hora_fin": "14:20"}, timeout=30)
    jd = r.json()
    print(f"  externa disponibilidad libre: {r.status_code} disponible={jd.get('disponible')}")
    ok = ok and r.status_code == 200 and jd.get("disponible") is True

    # 7) API externa agendar en franja bloqueada => 409
    r = requests.post(f"{API}/agenda/external/citas", headers=HK, json={
        "paciente_id": PAC, "paciente_nombre": "Externo Bloqueo", "medico_id": MED,
        "medico_nombre": MEDN, "fecha": FECHA, "hora_inicio": "11:00",
        "duracion_minutos": 20, "tipo_cita": "Subsecuente"
    }, timeout=30)
    print(f"  externa agendar bloqueada (esperado 409): {r.status_code}")
    ok = ok and r.status_code == 409

    # 8) API externa agendar libre (15:00) => 200
    r = requests.post(f"{API}/agenda/external/citas", headers=HK, json={
        "paciente_id": PAC, "paciente_nombre": "Externo Libre", "medico_id": MED,
        "medico_nombre": MEDN, "fecha": FECHA, "hora_inicio": "15:00",
        "duracion_minutos": 20, "tipo_cita": "Subsecuente"
    }, timeout=30)
    print(f"  externa agendar libre (esperado 200): {r.status_code}")
    ok = ok and r.status_code == 200
    if r.status_code == 200:
        creadas.append(r.json()["id"])

    # 9) Bloqueo de clínica (rango) y verificar que afecta a todos
    r = s.post(f"{API}/agenda/bloqueos", headers=H, json={
        "tipo": "clinica", "fecha_inicio": "2026-12-24", "fecha_fin": "2026-12-26",
        "motivo": "Vacaciones de fin de año"
    }, timeout=30)
    assert r.status_code == 200, f"crear bloqueo clinica {r.status_code}: {r.text}"
    BID_CLIN = r.json()["bloqueo"]["id"]
    r = requests.get(f"{API}/agenda/external/disponibilidad", headers=HK,
                     params={"medico_id": MED, "fecha": "2026-12-25", "hora_inicio": "09:00", "hora_fin": "09:20"}, timeout=30)
    jd = r.json()
    print(f"  clinica bloquea 25-dic: disponible={jd.get('disponible')} motivo={jd.get('motivo')}")
    ok = ok and jd.get("disponible") is False

    # 10) Listar bloqueos
    r = s.get(f"{API}/agenda/bloqueos", headers=H, timeout=30)
    print(f"  listar bloqueos: total={r.json().get('total')}")

    # Limpieza
    print("--- Limpieza ---")
    s.delete(f"{API}/agenda/bloqueos/{BID}", headers=H, timeout=30)
    s.delete(f"{API}/agenda/bloqueos/{BID_CLIN}", headers=H, timeout=30)
    for cid in creadas:
        s.delete(f"{API}/agenda/citas/{cid}", headers=H, timeout=30)
    print(f"  bloqueos y {len(creadas)} citas de prueba eliminados")

    print("\nRESULTADO:", "✅ OK" if ok else "❌ FALLO")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
