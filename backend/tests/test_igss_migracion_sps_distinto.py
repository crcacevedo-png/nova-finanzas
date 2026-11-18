# Libro IGSS — Fase 4: la simulación deja fuera las órdenes con No. SPS distinto entre la
# cirugía y la ficha del paciente (ajuste aprobado del Bloque 2). Prefijo TEST_, se borra al final.
import asyncio
import os
import uuid

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from usuarios_prueba import par

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
SIM = f"{API}/igss-units/migracion/simular"
TAG = uuid.uuid4().hex[:6]
U, N = f"TEST_spsd_unit_{TAG}", f"TEST_spsd_nog_{TAG}"
NUM = f"TSPSD{TAG}"
P = {k: f"TEST_spsd_p{k}_{TAG}" for k in "ABC"}
X, Y, B, C = (f"TSPSD-{k}-{TAG}".upper() for k in "XYBC")
CX = {k: f"TEST_spsd_cx{k}_{TAG}" for k in "ABC"}


def _db_call(fn):
    async def runner():
        client = AsyncIOMotorClient(os.environ['MONGO_URL'])
        try:
            return await fn(client[os.environ['DB_NAME']])
        finally:
            client.close()
    return asyncio.run(runner())


def _pac(k, sps=None):
    ordenes = [{"id": str(uuid.uuid4()), "nog": NUM, "no_sps": sps, "codigo": "", "procedimiento": "Avastin"}] if sps else []
    return {"id": P[k], "record_number": f"TEST-SPSD-{k}-{TAG}", "first_name": "TEST_SPSD", "last_name": k,
            "referral_institution": "igss", "igss_unit_id": U, "is_active": True, "igss_ordenes": ordenes,
            "created_at": "2025-01-01T12:00:00+00:00"}


def _cx(k, sps):
    return {"id": CX[k], "patient_id": P[k], "patient_name": f"TEST_SPSD {k}", "date": "2099-01-10", "status": "activo",
            "institution": "IGSS", "procedure": "Inyección intravítrea Avastin", "surgeon": "Dr. Test",
            "igss_data": {"unit_id": U, "nog_id": N, "sps": sps}}


@pytest.fixture(scope="module", autouse=True)
def seed():
    async def ins(db):
        await db.igss_units.insert_one({"id": U, "name": f"TEST_SPSD Unidad {TAG}", "is_active": True,
                                        "created_at": "2025-01-01T00:00:00+00:00"})
        await db.igss_nogs.insert_one({"id": N, "unidad_id": U, "numero": NUM, "nombre_servicio": "Inyección",
                                       "nombre_servicio_norm": "inyeccion", "tipo_compra": "contrato", "cantidad": 10,
                                       "precio": 100.0, "acreditados": 0, "is_active": True, "fecha_asignacion": "",
                                       "sin_tope": False})
        await db.patients.insert_many([_pac("A", Y), _pac("B", B), _pac("C")])
        await db.surgeries.insert_many([_cx("A", X.lower()), _cx("B", B), _cx("C", C)])
    _db_call(ins)
    yield

    async def clean(db):
        await db.igss_units.delete_one({"id": U})
        await db.igss_nogs.delete_one({"id": N})
        await db.patients.delete_many({"id": {"$in": list(P.values())}})
        await db.surgeries.delete_many({"id": {"$in": list(CX.values())}})
    _db_call(clean)


@pytest.fixture(scope="module")
def sa():
    u, p = par("superadmin")
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _simular(sa):
    r = requests.get(SIM, params={"unidad_id": U}, headers=sa, timeout=180)
    assert r.status_code == 200, r.text
    return r.json()


def test_sps_distinto_no_se_migra_y_va_a_no_migrables(sa):
    s = _simular(sa)
    migran = {o["no_sps"] for o in s["ordenes"]}
    assert migran == {B, C}  # la ficha coincide (B) o no tiene No. SPS (C): entran normal
    filas = [x for x in s["no_migrables"] if x["motivo_agrupado"] == "No. SPS distinto entre la cirugía y la ficha"]
    assert len(filas) == 1
    f = filas[0]
    assert f["motivo"] == f"No. SPS distinto entre la cirugía y la ficha (cirugía: {X} · ficha: {Y})"
    assert (f["sps_cirugia"], f["sps_ficha"], f["no_sps"]) == (X, Y, f"{X} / {Y}")
    assert f["expediente"] == f"TEST-SPSD-A-{TAG}" and "Corregir" in f["falta"]
    assert _db_call(lambda db: db.igss_ordenes_libro.count_documents({"unidad_id": U})) == 0  # solo lectura


def test_corregido_entra_normal(sa):
    _db_call(lambda db: db.surgeries.update_one({"id": CX["A"]}, {"$set": {"igss_data.sps": Y}}))
    s = _simular(sa)
    assert {o["no_sps"] for o in s["ordenes"]} == {B, C, Y}
    assert not [x for x in s["no_migrables"] if x["motivo_agrupado"] == "No. SPS distinto entre la cirugía y la ficha"]
