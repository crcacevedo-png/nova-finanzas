# Libro IGSS — Fase 4 paso (b): APLICAR la migración y DESHACERLA (solo superadmin).
# Rechazos (sin respaldo, con bloqueo, palabra, token vencido / de otro usuario, datos cambiados),
# una sola ejecución a la vez, órdenes vivas e históricas, constancias exactas, "Revisar SPS",
# cupos sin SPS, idempotencia, deshacer que deja el libro igual y deshacer negado con cambios.
# La migración es global (toda la BD de prueba): al final se limpia todo lo de los lotes creados.
import asyncio
import functools
import os
import threading
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import jwt
import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from usuarios_prueba import par  # usuarios sembrados solo para pruebas

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
MIG = f"{API}/igss-units/migracion"
LIBRO = f"{API}/igss-units/libro"
CLAVE = f"{os.environ['JWT_SECRET']}:migracion-libro"

TAG = uuid.uuid4().hex[:6]
NUM = int(TAG, 16) % 100000
U, B1, B2 = (f"TEST_apl_{k}_{TAG}" for k in ("unit", "b1", "b2"))
N1, N2, NB1, NB2 = (f"TEST_apl_{k}_{TAG}" for k in ("n1", "n2", "nb1", "nb2"))
NUM1, NUM2, NUMB = f"TAPL1{TAG}", f"TAPL2{TAG}", f"TAPLB{TAG}"
P = {k: f"TEST_apl_p{k}_{TAG}" for k in range(1, 9)}
SPS = {k: f"01-{NUM:05d}-2026-{i:06d}" for i, k in enumerate("ABCDEF", 1)}
RARO = "9-8-7-6-5-4-3-2-1"  # forma 1-1-1-1-1-1-1-1-1: única
RARO2 = "1-23-4-56-7-89-0"  # forma 1-2-1-2-1-2-1: única
LEG1 = f"TEST_apl_leg1_{TAG}"
CX = {k: f"TEST_apl_cx{k}_{TAG}" for k in ("1", "2a", "2b", "3")}
BACKUP = f"TEST_apl_bk_{TAG}"
LOTES = []
HOY = datetime.now(ZoneInfo("America/Guatemala")).date()
PASADA, FUTURA = (HOY - timedelta(days=6)).isoformat(), (HOY + timedelta(days=3)).isoformat()


def _db_call(fn):
    async def runner():
        client = AsyncIOMotorClient(os.environ['MONGO_URL'])
        try:
            return await fn(client[os.environ['DB_NAME']])
        finally:
            client.close()
    return asyncio.run(runner())


@functools.lru_cache(maxsize=None)
def _login(clave):
    u, p = par(clave)
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _nog(nid, numero, unidad=U, **kw):
    return {"id": nid, "unidad_id": unidad, "numero": numero, "nombre_servicio": "Procedimiento TEST",
            "nombre_servicio_norm": "procedimiento test", "tipo_compra": "contrato", "cantidad": 10, "precio": 100.0,
            "acreditados": 0, "is_active": True, "fecha_asignacion": "2025-01-01", "sin_tope": False, "libro_ocupados": 0, **kw}


def _pac(k, ordenes=None, unidad=U):
    return {"id": P[k], "record_number": f"TEST-APL-{k}-{TAG}", "first_name": "TEST_APL", "last_name": f"P{k}",
            "referral_institution": "igss", "igss_unit_id": unidad, "is_active": True, "igss_afiliacion": f"AF{k}",
            "igss_ordenes": ordenes or [], "created_at": "2025-01-01T12:00:00+00:00"}


def _ord(sps, oid=None, proc="", nog=NUM1):
    return {"id": oid or str(uuid.uuid4()), "nog": nog, "no_sps": sps, "codigo": "", "procedimiento": proc}


def _cx(k, pid, fecha, sps, proc="Avastin OD"):
    now = datetime.now(timezone.utc).isoformat()
    return {"id": CX[k], "date": fecha, "time": "08:00", "patient_name": "TEST_APL", "patient_id": pid, "procedure": proc,
            "surgeon": "Dr. TEST", "eye": "OD", "anesthesia_type": "topica", "anesthesiologist": "Dr. TEST Anest",
            "institution": "IGSS", "status": "activo", "equipment": [], "supplies": [], "created_by": "test",
            "created_at": now, "updated_at": now,
            "igss_data": {"unit": "TEST", "unit_id": U, "sps": sps, "affiliation_number": "AF", "code": "C-1",
                          "procedure_cost": 100, "nog_id": N1, "nog_number": NUM1}}


@pytest.fixture(scope="module", autouse=True)
def seed():
    async def ins(db):
        await db.igss_units.insert_one({"id": U, "name": f"TEST_APL Unidad {TAG}", "is_active": True,
                                        "created_at": "2025-01-01T00:00:00+00:00"})
        await db.igss_nogs.insert_many([_nog(N1, NUM1), _nog(N2, NUM2)])
        await db.patients.insert_many([
            _pac(1, [_ord(SPS["A"], LEG1)]), _pac(2, [_ord(SPS["B"], proc="Avastin")]),
            _pac(3, [_ord(SPS["C"], proc="Subciclofotocoagulación")]), _pac(4, [_ord(RARO)]), _pac(5)])
        await db.evaluaciones_oftalmologicas.insert_many([
            {"id": f"TEST_apl_ev1a_{TAG}", "paciente_id": P[1], "fecha": "2026-03-01", "medico_nombre": "Dr. TEST",
             "motivo_consulta": "Control", "igss_no_sps": SPS["A"]},
            {"id": f"TEST_apl_ev1b_{TAG}", "paciente_id": P[1], "fecha": "2026-04-01", "medico_nombre": "Dr. TEST",
             "motivo_consulta": "Control", "igss_orden_id": LEG1},
            {"id": f"TEST_apl_ev4_{TAG}", "paciente_id": P[4], "fecha": "2026-03-10", "medico_nombre": "Dr. TEST",
             "motivo_consulta": "Control", "igss_no_sps": RARO}])
        await db.surgeries.insert_many([
            _cx("1", P[1], "2026-05-01", SPS["A"]), _cx("2a", P[2], PASADA, SPS["B"]), _cx("2b", P[2], FUTURA, SPS["B"]),
            _cx("3", P[3], FUTURA, SPS["C"], proc="Subciclofotocoagulación")])
        await db.igss_nog_acreditaciones.insert_one({
            "id": f"TEST_apl_acr5_{TAG}", "nog_id": N1, "unidad_id": U, "paciente_id": P[5], "no_sps": "",
            "fecha_acreditacion": "2026-02-01T15:00:00+00:00", "origen": "asignacion", "anulada": False})
    _db_call(ins)
    yield

    async def clean(db):
        cupos = Counter()
        async for o in db.igss_ordenes_libro.find({"lote_migracion": {"$in": LOTES}}, {"_id": 0, "nog_id": 1, "estado": 1}):
            if o.get("estado") in ("reservada", "en_curso", "completa", "historica"):
                cupos[o["nog_id"]] += 1
        async for a in db.igss_libro_ajustes_cupo.find({"lote_migracion": {"$in": LOTES}, "activo": True}, {"_id": 0, "nog_id": 1}):
            cupos[a["nog_id"]] += 1
        for nog_id, n in cupos.items():
            await db.igss_nogs.update_one({"id": nog_id}, {"$inc": {"libro_ocupados": -n}})
        await db.igss_ordenes_libro.delete_many({"lote_migracion": {"$in": LOTES}})
        await db.igss_libro_ajustes_cupo.delete_many({"lote_migracion": {"$in": LOTES}})
        await db.igss_migracion_lotes.delete_many({"id": {"$in": LOTES}})
        await db.igss_migracion_fotos.delete_many({"lote_id": {"$in": LOTES}})
        await db.igss_ordenes_libro.delete_many({"id": {"$regex": f"^TEST_apl_.*_{TAG}$"}})
        await db.igss_units.delete_many({"id": {"$in": [U, B1, B2]}})
        await db.igss_nogs.delete_many({"id": {"$in": [N1, N2, NB1, NB2]}})
        await db.patients.delete_many({"id": {"$in": list(P.values())}})
        await db.evaluaciones_oftalmologicas.delete_many({"id": {"$regex": f"^TEST_apl_ev.*_{TAG}$"}})
        await db.surgeries.delete_many({"id": {"$in": list(CX.values())}})
        await db.igss_nog_acreditaciones.delete_many({"id": {"$regex": f"^TEST_apl_acr.*_{TAG}$"}})
        await db.igss_atenciones_sin_orden.delete_many({"ref_id": {"$in": list(CX.values())}})
        await db.backups.delete_many({"id": BACKUP})
    _db_call(clean)


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin")


def _simular(h, **params):
    r = requests.get(f"{MIG}/simular", params=params, headers=h, timeout=180)
    assert r.status_code == 200, r.text
    return r.json()


def _aplicar(h, token, palabra="MIGRAR"):
    r = requests.post(f"{MIG}/aplicar", json={"token": token, "palabra": palabra}, headers=h, timeout=300)
    if r.status_code == 200:
        LOTES.append(r.json()["lote_id"])
    return r


def _foto_libro():
    async def f(db):
        libro = sorted([o async for o in db.igss_ordenes_libro.find({}, {"_id": 0})], key=lambda o: o["id"])
        cupos = {n["id"]: n.get("libro_ocupados", 0) async for n in db.igss_nogs.find({}, {"_id": 0, "id": 1, "libro_ocupados": 1})}
        ajustes = await db.igss_libro_ajustes_cupo.count_documents({})
        return {"libro": libro, "cupos": cupos, "ajustes": ajustes}
    return _db_call(f)


def _ordenes_test():
    async def f(db):
        return {o["paciente_id"]: o async for o in db.igss_ordenes_libro.find(
            {"paciente_id": {"$in": list(P.values())}, "lote_migracion": {"$exists": True}}, {"_id": 0})}
    return _db_call(f)


def _respaldo(presente=True):
    async def f(db):
        if presente:
            now = datetime.now(timezone.utc).isoformat()
            await db.backups.update_one({"id": BACKUP}, {"$set": {
                "id": BACKUP, "status": "completado", "completed_at": now, "created_at": now, "is_deleted": False}}, upsert=True)
        else:
            await db.backups.delete_many({"id": BACKUP})
    _db_call(f)


def _token(tipo="aplicar", usuario="otro", minutos=30, huella="x"):
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    return jwt.encode({"tipo": tipo, "usuario": usuario, "huella": huella, "exp": exp}, CLAVE, algorithm="HS256")


def test_01_simulacion_clasifica_vivas_historicas_constancias_y_patrones(sa):
    sim = _simular(sa)
    assert sim["token_aplicar"] and sim["vence"] and sim["huella"]
    o = {x["paciente_id"]: x for x in sim["ordenes"] if x["paciente_id"] in P.values()}
    assert set(o) == {P[1], P[2], P[3], P[4]}
    assert o[P[1]]["estado_libro"] == "historica" and not o[P[1]]["viva"]
    assert {(c["tipo"], c["ref_id"]) for c in o[P[1]]["constancias"]} == {
        ("evaluacion", f"TEST_apl_ev1a_{TAG}"), ("cirugia", CX["1"])}  # la evaluación deducida (ev1b) no es constancia
    assert o[P[2]]["viva"] and o[P[2]]["estado_libro"] == "reservada" and o[P[2]]["dosis_autorizadas"] == 2
    assert o[P[2]]["inyectable"] is True and o[P[2]]["dosis_registradas"] == [] and o[P[2]]["cirugias_programadas"] == 2
    assert o[P[3]]["viva"] and o[P[3]]["estado_libro"] == "en_curso" and o[P[3]]["dosis_autorizadas"] == 1
    assert o[P[4]]["revisar_sps"] is True and o[P[4]]["sps_patron"] == "1-1-1-1-1-1-1-1-1"
    assert not any(o[k]["revisar_sps"] for k in (P[1], P[2], P[3]))
    pat = {p["patron"]: p for p in sim["patrones_sps"]}
    assert pat["1-1-1-1-1-1-1-1-1"]["ordenes"] == 1 and pat["1-1-1-1-1-1-1-1-1"]["comun"] is False
    assert pat["2-5-4-6"]["comun"] is True
    aj = next(p for p in sim["pendientes_sps"] if p["ref_id"] == f"TEST_apl_acr5_{TAG}")
    assert aj["tipo"] == "cupo_sin_sps" and aj["ajuste_existente"] is False
    claves = [c["clave"] for c in sim["cifras_lote"]]
    assert {"ordenes_vivas", "ordenes_historicas", "no_migrables", "pendientes_sps"} <= set(claves)
    # Filtrada por unidad: sin token (solo se aplica la simulación de todas las unidades)
    assert "token_aplicar" not in _simular(sa, unidad_id=U, detalle="false")


def test_02_rechazos_sin_ejecutar_nada(sa):
    antes = _foto_libro()
    sim = _simular(sa)
    # Palabra incorrecta
    assert _aplicar(sa, sim["token_aplicar"], "migrar").status_code == 422
    # Token vencido, de otro usuario o de otra acción
    r = _aplicar(sa, _token(minutos=-1))
    assert r.status_code == 409 and "30 minutos" in r.json()["detail"]
    assert _aplicar(sa, _token(usuario="otro")).status_code == 409
    assert _aplicar(sa, _token(tipo="deshacer")).status_code == 409
    # Sin respaldo de menos de 24 h
    if not sim["respaldo"]["vigente"]:
        r = _aplicar(sa, sim["token_aplicar"])
        assert r.status_code == 409 and "respaldo" in r.json()["detail"]
    _respaldo(True)
    # Los datos cambiaron desde la simulación
    async def toca(db):
        await db.evaluaciones_oftalmologicas.update_one({"id": f"TEST_apl_ev4_{TAG}"}, {"$set": {"motivo_consulta": "Cambio"}})
    _db_call(toca)
    r = _aplicar(sa, sim["token_aplicar"])
    assert r.status_code == 409 and "cambiaron" in r.json()["detail"]
    assert _foto_libro() == antes


def test_03_rechazo_con_bloqueo(sa):
    async def ins(db):
        await db.igss_units.insert_many([
            {"id": B1, "name": f"TEST_APL Clínica {TAG}", "is_active": False, "created_at": "2026-01-01T00:00:00+00:00"},
            {"id": B2, "name": f"TEST_APL Clinica {TAG}", "is_active": True, "created_at": "2026-02-01T00:00:00+00:00"}])
        await db.igss_nogs.insert_many([_nog(NB1, NUMB, unidad=B1), _nog(NB2, NUMB, unidad=B2)])
        await db.patients.insert_one(_pac(6, [_ord(SPS["F"], nog=NUMB)], unidad=B1))
        await db.igss_nog_acreditaciones.insert_one({
            "id": f"TEST_apl_acr6_{TAG}", "nog_id": NB2, "unidad_id": B2, "paciente_id": P[6], "no_sps": SPS["F"],
            "fecha_acreditacion": "2026-03-01T15:00:00+00:00", "origen": "asignacion", "anulada": False})

    async def quita(db):
        await db.igss_units.delete_many({"id": {"$in": [B1, B2]}})
        await db.igss_nogs.delete_many({"id": {"$in": [NB1, NB2]}})
        await db.patients.delete_many({"id": P[6]})
        await db.igss_nog_acreditaciones.delete_many({"id": f"TEST_apl_acr6_{TAG}"})
    _db_call(ins)
    try:
        antes = _foto_libro()
        sim = _simular(sa)
        assert sim["aplicacion_permitida"] is False
        r = _aplicar(sa, sim["token_aplicar"])
        assert r.status_code == 409 and "bloqueo" in r.json()["detail"]
        assert _foto_libro() == antes
    finally:
        _db_call(quita)


@pytest.fixture(scope="module")
def aplicado(sa):
    _respaldo(True)
    antes = _foto_libro()
    sim = _simular(sa)
    res = []

    def correr():
        res.append(_aplicar(sa, sim["token_aplicar"]))
    hilos = [threading.Thread(target=correr) for _ in range(2)]
    for t in hilos:
        t.start()
    for t in hilos:
        t.join()
    return {"antes": antes, "sim": sim, "res": res}


def test_04_una_sola_ejecucion_y_cifras_iguales(aplicado):
    estados = sorted(r.status_code for r in aplicado["res"])
    assert estados == [200, 409], [r.text for r in aplicado["res"]]
    ok = next(r.json() for r in aplicado["res"] if r.status_code == 200)
    assert ok["diferencias"] == [] and all(c["igual"] for c in ok["comparacion"])
    simuladas = {c["clave"]: c["valor"] for c in aplicado["sim"]["cifras_lote"]}
    assert {c["clave"]: c["simulado"] for c in ok["comparacion"]} == simuladas
    assert len([x for x in LOTES]) == 1


def test_05_ordenes_creadas_como_se_simulo(sa, aplicado):
    o = _ordenes_test()
    assert set(o) == {P[1], P[2], P[3], P[4]}
    h = o[P[1]]
    assert h["estado"] == "historica" and h["atenciones"] == [] and h["dosis_por_confirmar"] is False
    assert {c["ref_id"] for c in h["constancias"]} == {f"TEST_apl_ev1a_{TAG}", CX["1"]}
    v = o[P[2]]
    assert v["estado"] == "reservada" and v["dosis_por_confirmar"] is True and v["inyectable"] is True
    assert v["dosis_autorizadas"] == 2 and v["atenciones"] == []
    assert {p["ref_id"] for p in v["cirugias_programadas"]} == {CX["2a"], CX["2b"]}
    assert o[P[3]]["estado"] == "en_curso" and [p["ref_id"] for p in o[P[3]]["cirugias_programadas"]] == [CX["3"]]
    assert o[P[4]]["estado"] == "historica" and o[P[4]]["sps_por_revisar"] is True
    assert all(x["lote_migracion"] == LOTES[0] and x["numero_libro"].startswith("ORD-") for x in o.values())
    c = requests.get(f"{LIBRO}/nogs/{N1}/contador", headers=sa, timeout=60).json()
    assert (c["historicas"], c["reservadas"], c["en_curso"], c["sin_sps"], c["ocupados"]) == (2, 1, 1, 1, 5)
    # La cirugía pasada de la orden viva sale en "sin marcar"; la de la histórica no
    cx = {x["id"] for x in requests.get(f"{LIBRO}/cirugias-por-marcar", headers=sa, timeout=60).json()["data"]}
    assert CX["2a"] in cx and CX["1"] not in cx
    sps = {x["id"] for x in requests.get(f"{LIBRO}/sps-por-revisar", headers=sa, timeout=60).json()["data"]}
    assert o[P[4]]["id"] in sps
    aj = [a for a in requests.get(f"{LIBRO}/ajustes-cupo", headers=sa, timeout=60).json()["data"] if a["paciente_id"] == P[5]]
    assert len(aj) == 1 and aj[0]["nog_id"] == N1


def test_06_idempotente_segunda_corrida_no_crea_nada(sa, aplicado):
    antes = _foto_libro()
    sim = _simular(sa)
    assert not [x for x in sim["ordenes"] if x["paciente_id"] in P.values()]
    assert next(p for p in sim["pendientes_sps"] if p["ref_id"] == f"TEST_apl_acr5_{TAG}")["ajuste_existente"] is True
    r = _aplicar(sa, sim["token_aplicar"])
    assert r.status_code == 409 and "nada que migrar" in r.json()["detail"]
    assert _foto_libro() == antes


def test_07_deshacer_deja_el_libro_igual(sa, aplicado):
    lote = LOTES[0]
    rev = requests.post(f"{MIG}/deshacer/simular", json={"lote_id": lote}, headers=sa, timeout=120).json()
    assert rev["puede_deshacer"] is True and rev["cambios"] == [] and rev["ordenes"] >= 4 and rev["ajustes"] >= 1
    r = requests.post(f"{MIG}/deshacer", json={"token": rev["token_deshacer"], "palabra": "MIGRAR"}, headers=sa, timeout=120)
    assert r.status_code == 422  # la palabra del deshacer es otra
    r = requests.post(f"{MIG}/deshacer", json={"token": aplicado["sim"]["token_aplicar"], "palabra": "DESHACER"}, headers=sa, timeout=120)
    assert r.status_code == 409  # un token de aplicar no sirve para deshacer
    r = requests.post(f"{MIG}/deshacer", json={"token": rev["token_deshacer"], "palabra": "DESHACER"}, headers=sa, timeout=300)
    assert r.status_code == 200, r.text
    assert _foto_libro() == aplicado["antes"]
    otra = requests.post(f"{MIG}/deshacer/simular", json={"lote_id": lote}, headers=sa, timeout=120).json()
    assert otra["puede_deshacer"] is False and "ya se deshizo" in otra["motivo"]


def test_08_deshacer_negado_si_una_orden_cambio(sa):
    _respaldo(True)
    sim = _simular(sa)
    r = _aplicar(sa, sim["token_aplicar"])
    assert r.status_code == 200, r.text
    lote = r.json()["lote_id"]
    rev = requests.post(f"{MIG}/deshacer/simular", json={"lote_id": lote}, headers=sa, timeout=120).json()
    assert rev["puede_deshacer"] is True
    # Administración marca la cirugía pasada como realizada: cuenta como dosis 1 de 2, una sola vez
    for _ in range(2):
        m = requests.post(f"{API}/surgeries/{CX['2a']}/realizada", json={"realizada": True}, headers=sa, timeout=60)
        assert m.status_code == 200, m.text
    v = _ordenes_test()[P[2]]
    assert v["estado"] == "en_curso" and sum(1 for a in v["atenciones"] if a["tipo"] == "cirugia") == 1
    antes = _foto_libro()
    rev2 = requests.post(f"{MIG}/deshacer/simular", json={"lote_id": lote}, headers=sa, timeout=120).json()
    assert rev2["puede_deshacer"] is False and "token_deshacer" not in rev2
    cambio = next(c for c in rev2["cambios"] if c["id"] == v["id"])
    assert "dosis / atenciones registradas" in cambio["que_cambio"] and cambio["registros"]
    assert any(x["quien"] not in ("", "—") and x["cuando"] for x in cambio["registros"])
    r = requests.post(f"{MIG}/deshacer", json={"token": rev["token_deshacer"], "palabra": "DESHACER"}, headers=sa, timeout=120)
    assert r.status_code == 409 and r.json()["detail"]["cambios"]
    assert _foto_libro() == antes  # sin deshacer parcial


def test_08b_deshacer_negado_si_se_confirmo_un_sps(sa):
    """Confirmar un No. SPS ("Revisar SPS") después de migrar también impide deshacer el lote."""
    _db_call(lambda db: db.patients.insert_one(_pac(8, [_ord(RARO2)])))
    _respaldo(True)
    sim = _simular(sa)
    o8 = next(x for x in sim["ordenes"] if x["paciente_id"] == P[8])
    assert o8["revisar_sps"] is True
    r = _aplicar(sa, sim["token_aplicar"])
    assert r.status_code == 200, r.text
    lote = r.json()["lote_id"]
    orden = _ordenes_test()[P[8]]
    assert orden["sps_por_revisar"] is True and orden["lote_migracion"] == lote
    rev = requests.post(f"{MIG}/deshacer/simular", json={"lote_id": lote}, headers=sa, timeout=120).json()
    assert rev["puede_deshacer"] is True and rev["cambios"] == []
    # Un administrador IGSS confirma el No. SPS contra la hoja
    c = requests.post(f"{LIBRO}/ordenes/{orden['id']}/confirmar-sps", headers=_login("igss"), timeout=60)
    assert c.status_code == 200, c.text
    antes = _foto_libro()
    rev2 = requests.post(f"{MIG}/deshacer/simular", json={"lote_id": lote}, headers=sa, timeout=120).json()
    assert rev2["puede_deshacer"] is False and "token_deshacer" not in rev2
    cambio = next(x for x in rev2["cambios"] if x["id"] == orden["id"])
    assert cambio["que_cambio"] == ["No. SPS confirmado con la hoja"], cambio["que_cambio"]
    reg = [x for x in cambio["registros"] if x["accion"] == "No. SPS confirmado"]
    assert reg and reg[0]["quien"] == c.json()["sps_confirmado_por_nombre"] and reg[0]["cuando"]
    r = requests.post(f"{MIG}/deshacer", json={"token": rev["token_deshacer"], "palabra": "DESHACER"}, headers=sa, timeout=120)
    assert r.status_code == 409 and r.json()["detail"]["cambios"]
    assert _foto_libro() == antes  # no se borró nada del lote


def test_09_sps_por_revisar_impide_facturar_hasta_confirmar(sa):
    now = datetime.now(timezone.utc).isoformat()
    oids = {k: f"TEST_apl_orden{k}_{TAG}" for k in ("igss", "admin")}

    async def ins(db):
        await db.igss_ordenes_libro.insert_many([{
            "id": oid, "unidad_id": U, "nog_id": N2, "numero_nog": NUM2, "no_sps": f"01-{NUM:05d}-2026-99999{i}",
            "paciente_id": P[7], "paciente_nombre": "TEST_APL P7", "estado": "completa", "vigente": True, "tipo": "consulta",
            "dosis_autorizadas": 1, "fecha_ingreso": "2026-11-01", "atenciones": [{"tipo": "evaluacion", "ref_id": "x", "fecha": "2026-11-02"}],
            "cirugias_programadas": [], "sps_por_revisar": True, "facturado": False, "pagado": False, "created_at": now, "updated_at": now}
            for i, oid in enumerate(oids.values())])
    _db_call(ins)
    for oid in oids.values():
        for campo in ("facturado", "pagado"):
            r = requests.put(f"{LIBRO}/ordenes/{oid}", json={campo: True}, headers=sa, timeout=60)
            assert r.status_code == 422 and "Confirme el No. SPS" in r.json()["detail"]
    # Quien ingresa el SPS (usuario, óptica) no puede confirmarlo: no sería una revisión
    for rol in ("usuario", "optica"):
        assert requests.post(f"{LIBRO}/ordenes/{oids['igss']}/confirmar-sps", headers=_login(rol), timeout=60).status_code == 403
    for rol, oid in oids.items():
        c = requests.post(f"{LIBRO}/ordenes/{oid}/confirmar-sps", headers=_login(rol), timeout=60)
        assert c.status_code == 200, c.text
        assert c.json()["sps_por_revisar"] is False and c.json()["sps_confirmado_por_nombre"] and c.json()["sps_confirmado_en"]
        assert requests.post(f"{LIBRO}/ordenes/{oid}/confirmar-sps", headers=sa, timeout=60).status_code == 400
        assert requests.put(f"{LIBRO}/ordenes/{oid}", json={"facturado": True}, headers=sa, timeout=60).status_code == 200
    # La ficha (también para quien ingresa) muestra quién confirmó y cuándo
    fichas = {o["id"]: o for o in requests.get(f"{API}/patients/{P[7]}/igss-ordenes", headers=_login("usuario"), timeout=60).json()}
    assert all(fichas[oid]["sps_confirmado_por_nombre"] and fichas[oid]["sps_confirmado_en"] for oid in oids.values())
    # Una orden anulada ya no se confirma
    async def anula(db):
        await db.igss_ordenes_libro.update_one({"id": oids["admin"]}, {"$set": {"estado": "anulada", "sps_por_revisar": True}})
    _db_call(anula)
    assert requests.post(f"{LIBRO}/ordenes/{oids['admin']}/confirmar-sps", headers=sa, timeout=60).status_code == 400


@pytest.mark.parametrize("rol", ["admin", "igss", "usuario"])
def test_10_solo_superadmin(rol):
    h = _login(rol)
    assert requests.post(f"{MIG}/aplicar", json={"token": "x" * 20, "palabra": "MIGRAR"}, headers=h, timeout=60).status_code == 403
    assert requests.get(f"{MIG}/lotes", headers=h, timeout=60).status_code == 403
    assert requests.post(f"{MIG}/deshacer/simular", json={"lote_id": "x"}, headers=h, timeout=60).status_code == 403
    assert requests.post(f"{MIG}/deshacer", json={"token": "x" * 20, "palabra": "DESHACER"}, headers=h, timeout=60).status_code == 403
