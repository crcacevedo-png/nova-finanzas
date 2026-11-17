# Libro IGSS — Fase 4 paso (a): simulación de migración (solo lectura). Clasificación de
# órdenes, atenciones, revisión manual e historial ignorado; invariancia total de datos;
# Excel; permisos. Los documentos sembrados usan el prefijo TEST_ y se borran al final.
import asyncio
import hashlib
import io
import json
import os
import uuid

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from openpyxl import load_workbook

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
API = f"{os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')}/api"

TAG = uuid.uuid4().hex[:6]
U = f"TEST_mig_unit_{TAG}"
N1, N2, NBC, N3 = (f"TEST_mig_{k}_{TAG}" for k in ("n1", "n2", "bc", "n3"))
NUM1, NUM2, NUM3 = f"TMIG1{TAG}", f"TMIG2{TAG}", f"TMIG3{TAG}"
P = {k: f"TEST_mig_p{k}_{TAG}" for k in range(1, 11)}
SPS = {k: f"TMIG-{k}-{TAG}".upper() for k in "ABCDEFGH"}
LIBRO_ID = f"TEST_mig_libro_{TAG}"
LEG1 = f"TEST_mig_leg1_{TAG}"
COLECCIONES = ["igss_nogs", "igss_nog_acreditaciones", "igss_produccion", "igss_ordenes_libro",
               "igss_atenciones_sin_orden", "patients", "evaluaciones_oftalmologicas", "surgeries", "igss_units"]


def _db_call(fn):
    async def runner():
        client = AsyncIOMotorClient(os.environ['MONGO_URL'])
        try:
            return await fn(client[os.environ['DB_NAME']])
        finally:
            client.close()
    return asyncio.run(runner())


def login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _nog(nid, numero, **kw):
    return {"id": nid, "unidad_id": U, "numero": numero, "nombre_servicio": kw.pop("servicio", "Consulta"),
            "nombre_servicio_norm": "consulta", "tipo_compra": "contrato", "cantidad": 10, "precio": 100.0,
            "acreditados": 0, "is_active": True, "fecha_asignacion": "", "sin_tope": False, **kw}


def _pac(k, ordenes=None, **kw):
    return {"id": P[k], "record_number": f"TEST-MIG-{k}-{TAG}", "first_name": "TEST_MIG", "last_name": f"P{k}",
            "referral_institution": "igss", "igss_unit_id": U, "is_active": True, "igss_afiliacion": "",
            "igss_ordenes": ordenes or [], "created_at": "2025-01-01T12:00:00+00:00", **kw}


def _ord(nog, sps, oid=None, proc=""):
    return {"id": oid or str(uuid.uuid4()), "nog": nog, "no_sps": sps, "codigo": "", "procedimiento": proc}


def _ev(k, pid, fecha, **kw):
    return {"id": f"TEST_mig_ev{k}_{TAG}", "paciente_id": pid, "fecha": fecha, "medico_nombre": "Dr. Test",
            "motivo_consulta": "Control", **kw}


def _acr(k, pid, nog_id, sps, fecha, **kw):
    return {"id": f"TEST_mig_acr{k}_{TAG}", "nog_id": nog_id, "unidad_id": U, "paciente_id": pid, "no_sps": sps,
            "fecha_acreditacion": fecha, "origen": "asignacion", "anulada": False, **kw}


def _cx(k, pid, fecha, sps, status="realizado", nog_id=N1):
    return {"id": f"TEST_mig_cx{k}_{TAG}", "patient_id": pid, "patient_name": "TEST_MIG", "date": fecha,
            "status": status, "institution": "IGSS", "procedure": "Catarata", "surgeon": "Dr. Cx",
            "igss_data": {"unit_id": U, "nog_id": nog_id, "sps": sps}}


@pytest.fixture(scope="module", autouse=True)
def seed():
    async def ins(db):
        await db.igss_units.insert_one({"id": U, "name": f"TEST_MIG Unidad {TAG}", "is_active": True})
        await db.igss_nogs.insert_many([
            _nog(N1, NUM1, fecha_asignacion="2026-01-01"), _nog(N2, NUM2, cantidad=5),
            _nog(NBC, "", servicio="Servicio BC", tipo_compra="baja_cuantia", sin_tope=True, fecha_asignacion="2026-01-01"),
            _nog(N3, NUM3, is_active=False, cantidad=1, fecha_asignacion="2025-01-01")])
        await db.patients.insert_many([
            _pac(1, [_ord(NUM1, SPS["A"], LEG1)]), _pac(2, [_ord(NUM2, SPS["B"])]),
            _pac(3, [_ord("BAJA CUANTIA", SPS["C"], proc="Servicio BC")]), _pac(4, [_ord("NOEXISTE99", SPS["D"])]),
            _pac(5, [_ord(NUM1, SPS["E"])]), _pac(6, [_ord(NUM1, SPS["E"])]), _pac(7, [_ord(NUM1, "")]),
            _pac(8, created_at="2026-01-01T12:00:00+00:00"), _pac(9), _pac(10)])
        await db.igss_nog_acreditaciones.insert_many([
            _acr(1, P[1], N1, SPS["A"], "2026-02-01T15:00:00+00:00"),
            _acr(7, P[7], N1, "", "2026-02-10T15:00:00+00:00"),
            _acr(8, P[8], N2, "", "2026-04-01T15:00:00+00:00", anulada=True)])
        await db.evaluaciones_oftalmologicas.insert_many([
            _ev("1a", P[1], "2025-12-15", igss_no_sps=SPS["A"]), _ev("1b", P[1], "2026-03-01", igss_orden_id=LEG1),
            _ev("2", P[2], "2025-06-01", igss_nog=NUM2), _ev("3", P[3], "2026-04-01", igss_no_sps=SPS["C"]),
            _ev("4", P[4], "2026-05-01", igss_no_sps=SPS["D"]), _ev("7a", P[7], "2025-11-01"),
            _ev("7b", P[7], "2026-06-01"), _ev("8", P[8], "2026-03-15"),
            _ev("10", P[10], "2026-09-01", igss_no_sps=SPS["H"])])
        await db.igss_produccion.insert_one({"evaluacion_id": f"TEST_mig_ev3_{TAG}", "pagado": True, "costo_override": 75.0})
        await db.surgeries.insert_many([
            _cx(1, P[9], "2026-07-01", SPS["F"]), _cx(2, P[9], "2026-08-01", SPS["F"]),
            _cx(3, P[9], "2026-07-05", SPS["G"], status="cancelado"), _cx(4, P[9], "2026-07-15", "")])
        await db.igss_ordenes_libro.insert_one({
            "id": LIBRO_ID, "unidad_id": U, "nog_id": N1, "numero_nog": NUM1, "no_sps": SPS["H"], "paciente_id": P[10],
            "paciente_nombre": "TEST_MIG P10", "estado": "pendiente", "vigente": True, "tipo": "consulta",
            "dosis_autorizadas": 1, "fecha_ingreso": "2026-08-01", "atenciones": []})
    _db_call(ins)
    yield

    async def clean(db):
        await db.igss_units.delete_many({"id": U})
        await db.igss_nogs.delete_many({"unidad_id": U})
        await db.patients.delete_many({"id": {"$in": list(P.values())}})
        await db.igss_nog_acreditaciones.delete_many({"unidad_id": U})
        await db.evaluaciones_oftalmologicas.delete_many({"id": {"$regex": f"^TEST_mig_ev.*_{TAG}$"}})
        await db.igss_produccion.delete_many({"evaluacion_id": {"$regex": f"^TEST_mig_ev.*_{TAG}$"}})
        await db.surgeries.delete_many({"id": {"$regex": f"^TEST_mig_cx.*_{TAG}$"}})
        await db.igss_ordenes_libro.delete_many({"id": LIBRO_ID})
    _db_call(clean)


def _snapshot():
    async def snap(db):
        out = {}
        for c in COLECCIONES:
            docs = await db[c].find({}, {"_id": 0}).to_list(None)
            txt = json.dumps(sorted(json.dumps(d, sort_keys=True, default=str) for d in docs))
            out[c] = (len(docs), hashlib.md5(txt.encode()).hexdigest())
        out["audit_simulada"] = await db.audit_logs.count_documents({"action": "LIBRO_MIGRACION_SIMULADA"})
        return out
    return _db_call(snap)


@pytest.fixture(scope="module")
def sa():
    return login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def sim(sa):
    antes = _snapshot()
    r = requests.get(f"{API}/igss-units/migracion/simular", headers=sa, timeout=120)
    assert r.status_code == 200, r.text
    x = requests.get(f"{API}/igss-units/migracion/simular/excel", headers=sa, timeout=120)
    assert x.status_code == 200, x.text
    despues = _snapshot()
    return {"data": r.json(), "excel": x.content, "antes": antes, "despues": despues}


def _orden(sim, sps):
    return next((o for o in sim["data"]["ordenes"] if o["no_sps"] == sps), None)


def _manual(sim):
    return [i for i in sim["data"]["revision_manual"] if (i["paciente_id"] or "").endswith(TAG)]


def test_solo_lectura_invariancia_total(sim):
    for c in COLECCIONES:
        assert sim["antes"][c] == sim["despues"][c], f"La simulación modificó {c}"
    assert sim["despues"]["audit_simulada"] == sim["antes"]["audit_simulada"] + 2
    assert sim["data"]["solo_lectura"] is True


def test_orden_con_fecha_asignacion_excluye_anteriores(sim):
    o = _orden(sim, SPS["A"])
    assert o and o["estado"] == "atendida" and o["nog_id"] == N1
    assert o["evaluaciones"] == 1 and o["excluidas_anteriores"] == 1
    assert o["fecha_primera_atencion"] == "2026-03-01" and o["fecha_referencia"] == "2026-01-01"
    assert o["fuente_referencia"] == "Asignación del NOG" and o["revisar_fecha"] is False
    assert o["fecha_ingreso"] == "2026-02-01"


def test_sin_fechas_incluye_todo_y_marca_revisar(sim):
    o = _orden(sim, SPS["B"])
    assert o and o["nog_id"] == N2 and o["estado"] == "atendida"
    assert o["revisar_fecha"] is True and o["fecha_primera_atencion"] == "2025-06-01"


def test_baja_cuantia_y_estados_heredados(sim):
    o = _orden(sim, SPS["C"])
    assert o and o["nog_id"] == NBC and o["modalidad"] == "Baja Cuantía"
    assert o["pagado"] is True and o["costo_override"] == 75.0


def test_procedimiento_con_dosis_por_cirugias(sim):
    o = _orden(sim, SPS["F"])
    assert o and o["tipo"] == "procedimiento" and o["cirugias"] == 2 and o["dosis_autorizadas"] == 2
    assert o["fechas_atenciones"] == ["2026-07-01", "2026-08-01"]
    assert _orden(sim, SPS["G"]) is None


def test_no_migrables(sim):
    nm = {n["no_sps"]: n for n in sim["data"]["no_migrables"] if n["unidad_id"] == U}
    assert "no está en el catálogo" in nm[SPS["D"]]["motivo"]
    assert "2 pacientes" in nm[SPS["E"]]["motivo"]
    assert any(n["motivo"] == "Orden del paciente sin No. SPS" and f"TEST-MIG-7-{TAG}" in n["expedientes"]
               for n in sim["data"]["no_migrables"])
    for sps in (SPS["D"], SPS["E"]):
        assert _orden(sim, sps) is None


def test_revision_manual(sim):
    m = _manual(sim)
    por_ref = {i["ref_id"]: i for i in m}
    cupo = por_ref[f"TEST_mig_acr7_{TAG}"]
    assert cupo["etiqueta"] == "Cupo descontado sin SPS" and cupo["nog_id"] == N1 and cupo["fecha"] == "2026-02-10"
    assert f"TEST_mig_ev4_{TAG}" in por_ref and "catálogo" in por_ref[f"TEST_mig_ev4_{TAG}"]["motivo"]
    assert por_ref[f"TEST_mig_ev7b_{TAG}"]["motivo"] == "Evaluación sin No. SPS"
    assert por_ref[f"TEST_mig_cx4_{TAG}"]["motivo"] == "Cirugía sin No. SPS"
    # Historial: anterior al contrato (7a) y paciente sin unidad IGSS en esa fecha (8) no se listan
    for ref in (f"TEST_mig_ev7a_{TAG}", f"TEST_mig_ev8_{TAG}", f"TEST_mig_ev1a_{TAG}"):
        assert ref not in por_ref
    t = sim["data"]["totales"]
    assert t["evaluaciones_anteriores_al_contrato"] >= 2 and t["evaluaciones_sin_unidad_igss_en_la_fecha"] >= 1


def test_ya_en_el_libro(sim):
    o = next(x for x in sim["data"]["ya_en_libro"] if x["orden_id"] == LIBRO_ID)
    assert o["evaluaciones_a_agregar"] == 1 and o["estado_resultante"] == "atendida"
    assert _orden(sim, SPS["H"]) is None


def test_resumen_nog_pendientes_sps_y_por_anio(sim):
    r = {f["nog_id"]: f for f in sim["data"]["resumen_nog"] if f["unidad_id"] == U}
    n1 = r[N1]
    assert n1["migrar_atendidas"] == 2 and n1["libro_reservados"] == 1
    assert n1["consumidos"] == n1["libro_consumidos"] + 3 and n1["reservados"] == 0
    assert n1["pendientes_sps"] == sum(1 for i in _manual(sim) if i["nog_id"] == N1) >= 1
    assert r[NBC]["sin_tope"] is True and r[NBC]["disponibles"] is None
    assert sum(a["ordenes"] for a in sim["data"]["por_anio"]) == len(sim["data"]["ordenes"])
    assert sim["data"]["totales"]["ordenes_a_migrar"] == len(sim["data"]["ordenes"])


def test_excel(sim):
    wb = load_workbook(io.BytesIO(sim["excel"]))
    assert wb.sheetnames == ["Resumen", "Por NOG", "Órdenes a migrar", "Ya en el libro", "Revisión manual", "No migrables"]
    assert "Pendientes de SPS" in [c.value for c in wb["Por NOG"][1]]
    sps_excel = {row[3] for row in wb["Órdenes a migrar"].iter_rows(min_row=2, values_only=True)}
    assert {SPS["A"], SPS["B"], SPS["C"], SPS["F"]} <= sps_excel
    resumen = [row[0] for row in wb["Resumen"].iter_rows(values_only=True) if row and row[0]]
    assert any(str(x).endswith("evaluaciones históricas ignoradas") for x in resumen)
    assert "Año de primera atención" in resumen


def test_permisos():
    for u, p, esperado in (("usuario", "user2024", 403), ("igss.admin", "IgssAdmin2024$", 200)):
        h = login(u, p)
        assert requests.get(f"{API}/igss-units/migracion/simular", headers=h, timeout=120).status_code == esperado
        assert requests.get(f"{API}/igss-units/migracion/simular/excel", headers=h, timeout=120).status_code == esperado
