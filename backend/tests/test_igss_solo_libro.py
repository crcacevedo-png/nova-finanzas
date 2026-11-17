# Interruptor "Usar solo el libro" (solo superadmin, apagado por defecto, auditado).
# Encendido: las acciones principales siguen funcionando y el libro se sigue actualizando,
# pero NADA cambia en el sistema anterior (igss_nog_acreditaciones, igss_produccion,
# igss_nogs.acreditados) y sus endpoints de recalcular/reconciliar/aplicar/anular -> 409.
# Siembra con prefijo TEST_ y lo borra al final; restaura el interruptor como estaba.
import asyncio
import hashlib
import json
import os
import random
import unicodedata
import re
import uuid

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from usuarios_prueba import par  # usuarios sembrados solo para pruebas

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
API = f"{os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')}/api"
LIBRO = f"{API}/igss-units/libro"

TAG = uuid.uuid4().hex[:6]
U = f"TEST_solo_unit_{TAG}"
N, N3 = f"TEST_solo_nog_{TAG}", f"TEST_solo_nog3_{TAG}"
NUM, NUM3 = f"TSOLO{TAG}", f"TSOLO3{TAG}"
P1 = f"TEST_solo_p1_{TAG}"
O1, S1 = f"TEST_solo_orden_{TAG}", f"TSOLO-{TAG}".upper()
A1, A3, AD = (f"TEST_solo_acr{k}_{TAG}" for k in ("1", "3", "d"))
E0 = f"TEST_solo_borrador_{TAG}"
DUP_U, DUP_N = f"TEST_solo_dupunit_{TAG}", f"TEST_solo_dupnog_{TAG}"
PREVIA = {}


def _db_call(fn):
    async def runner():
        client = AsyncIOMotorClient(os.environ['MONGO_URL'])
        try:
            return await fn(client[os.environ['DB_NAME']])
        finally:
            client.close()
    return asyncio.run(runner())


def _login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def sa():
    return _login(*par("superadmin"))


@pytest.fixture(scope="module")
def igss():
    return _login(*par("igss"))


def _acr(aid, nog_id, unidad, pid="", sps=""):
    return {"id": aid, "nog_id": nog_id, "unidad_id": unidad, "paciente_id": pid, "no_sps": sps, "anulada": False,
            "origen": "asignacion", "fecha_acreditacion": "2026-11-01T12:00:00+00:00"}


@pytest.fixture(scope="module", autouse=True)
def seed():
    async def ins(db):
        PREVIA["config"] = await db.igss_libro_config.find_one({"id": "libro_igss"}, {"_id": 0})
        PREVIA["flag"] = await db.system_flags.find_one({"key": "nog_dedup_cleanup_v1"}, {"_id": 0})
        await db.igss_units.insert_one({"id": U, "name": f"TEST Solo Libro {TAG}", "is_active": True})
        base = {"unidad_id": U, "nombre_servicio": "Consulta", "nombre_servicio_norm": "consulta", "tipo_compra": "contrato",
                "cantidad": 10, "precio": 100.0, "is_active": True, "sin_tope": False, "fecha_asignacion": ""}
        await db.igss_nogs.insert_many([{**base, "id": N, "numero": NUM, "acreditados": 4},
                                        {**base, "id": N3, "numero": NUM3, "acreditados": 1}])
        await db.patients.insert_one({
            "id": P1, "record_number": f"TEST-SOLO-{TAG}", "first_name": "TEST_SOLO", "last_name": "Paciente",
            "referral_institution": "igss", "igss_unit_id": U, "is_active": True, "gender": "femenino",
            "birth_date": "1970-01-01", "phone": "55551234", "dpi": str(random.randint(10**12, 10**13 - 1)),
            "igss_ordenes": [{"id": f"leg-{TAG}", "nog": NUM, "no_sps": S1, "codigo": "", "procedimiento": ""}]})
        await db.igss_nog_acreditaciones.insert_many([_acr(A1, N, U, P1, S1), _acr(A3, N3, U)])
        await db.igss_ordenes_libro.insert_one({
            "id": O1, "unidad_id": U, "nog_id": N, "numero_nog": NUM, "no_sps": S1, "paciente_id": P1,
            "paciente_nombre": "TEST_SOLO Paciente", "estado": "pendiente", "vigente": True, "tipo": "consulta",
            "dosis_autorizadas": 1, "fecha_ingreso": "2026-11-01", "atenciones": []})
        await db.evaluaciones_oftalmologicas.insert_one({"id": E0, "paciente_id": P1, "fecha": "2026-11-02"})
        await db.igss_produccion.insert_one({"evaluacion_id": E0, "pagado": True})
    _db_call(ins)
    yield

    async def clean(db):
        await db.igss_libro_config.update_one({"id": "libro_igss"}, {"$set": {
            "usar_solo_libro": bool((PREVIA["config"] or {}).get("usar_solo_libro")),
            "exigir_orden": bool((PREVIA["config"] or {}).get("exigir_orden"))}}, upsert=True)
        if PREVIA["flag"]:
            await db.system_flags.replace_one({"key": "nog_dedup_cleanup_v1"}, PREVIA["flag"], upsert=True)
        pacs = [P1] + await db.patients.distinct("id", {"first_name": f"TEST_SOLO_NUEVO_{TAG}"})
        await db.evaluaciones_oftalmologicas.delete_many({"paciente_id": {"$in": pacs}})
        await db.igss_atenciones_sin_orden.delete_many({"paciente_id": {"$in": pacs}})
        await db.igss_ordenes_libro.delete_many({"unidad_id": U})
        await db.igss_nog_acreditaciones.delete_many({"$or": [{"id": {"$in": [A1, A3, AD]}}, {"paciente_id": {"$in": pacs}},
                                                              {"unidad_id": {"$in": [U, DUP_U]}}]})
        await db.igss_produccion.delete_many({"evaluacion_id": E0})
        await db.igss_nogs.delete_many({"unidad_id": {"$in": [U, DUP_U]}})
        await db.igss_nogs.delete_many({"id": DUP_N})
        await db.igss_units.delete_many({"id": {"$in": [U, DUP_U]}})
        await db.patients.delete_many({"id": {"$in": pacs}})
    _db_call(clean)


def _huella():
    """Estado completo del sistema anterior: cada acreditación, cada estado de producción y
    el contador `acreditados` de cada entrada del catálogo."""
    async def snap(db):
        acr = await db.igss_nog_acreditaciones.find({}, {"_id": 0}).to_list(None)
        prod = await db.igss_produccion.find({}, {"_id": 0}).to_list(None)
        cont = {n["id"]: n.get("acreditados") for n in await db.igss_nogs.find({}, {"_id": 0, "id": 1, "acreditados": 1}).to_list(None)}
        h = lambda docs: hashlib.md5(json.dumps(sorted(json.dumps(d, sort_keys=True, default=str) for d in docs)).encode()).hexdigest()
        return {"acreditaciones": (len(acr), h(acr)), "produccion": (len(prod), h(prod)), "acreditados": cont}
    return _db_call(snap)


def _mismo_sistema_anterior(antes, despues):
    assert despues["acreditaciones"] == antes["acreditaciones"], "cambió igss_nog_acreditaciones"
    assert despues["produccion"] == antes["produccion"], "cambió igss_produccion"
    comunes = set(antes["acreditados"]) & set(despues["acreditados"])
    cambiados = {k for k in comunes if antes["acreditados"][k] != despues["acreditados"][k]}
    assert not cambiados, f"cambió igss_nogs.acreditados en {cambiados}"


def _orden(sa):
    r = requests.get(f"{LIBRO}/ordenes/{O1}", headers=sa)
    assert r.status_code == 200, r.text
    return r.json()


def test_01_interruptor_apagado_por_defecto_y_solo_superadmin(sa, igss):
    async def borrar(db):
        await db.igss_libro_config.update_one({"id": "libro_igss"}, {"$unset": {"usar_solo_libro": ""}}, upsert=True)
    _db_call(borrar)
    assert requests.get(f"{LIBRO}/config", headers=sa).json()["usar_solo_libro"] is False
    assert requests.put(f"{LIBRO}/config", json={"usar_solo_libro": True}, headers=igss).status_code == 403
    r = requests.put(f"{LIBRO}/config", json={"usar_solo_libro": True}, headers=sa)
    assert r.status_code == 200 and r.json()["usar_solo_libro"] is True and r.json()["solo_libro_actualizado_en"]

    async def audit(db):
        return await db.audit_logs.find_one({"action": "LIBRO_SOLO_LIBRO_CAMBIADO"}, {"_id": 0}, sort=[("timestamp", -1)])
    a = _db_call(audit)
    assert a["details"] == {"antes": False, "despues": True}


def test_02_endpoints_antiguos_deshabilitados(sa):
    llamadas = [("post", f"{API}/igss-units/nogs/reconciliar-todo", None),
                ("post", f"{API}/igss-units/nogs/{N}/recalcular", None),
                ("post", f"{API}/igss-units/nogs/recalcular-por-evaluaciones", None),
                ("post", f"{API}/igss-units/nogs/{N}/acreditaciones/{A1}/anular", {"motivo": "x"}),
                ("post", f"{API}/igss-units/nogs/{N}/acreditaciones/aplicar", {"paciente_id": P1})]
    antes = _huella()
    for metodo, url, body in llamadas:
        r = getattr(requests, metodo)(url, json=body, headers=sa)
        assert r.status_code == 409, (url, r.status_code, r.text)
        assert "Usar solo el libro" in r.json()["detail"]
    _mismo_sistema_anterior(antes, _huella())


def test_03_paciente_crear_editar_desactivar_reactivar(sa):
    antes = _huella()
    body = {"first_name": f"TEST_SOLO_NUEVO_{TAG}", "last_name": "Paciente", "gender": "masculino",
            "birth_date": "1980-01-01", "phone": "55551234", "dpi": str(random.randint(10**12, 10**13 - 1)),
            "referral_institution": "igss", "igss_unit_id": U,
            "igss_ordenes": [{"nog": NUM, "no_sps": f"N1-{TAG}", "codigo": "", "procedimiento": "Consulta"}]}
    r = requests.post(f"{API}/patients", json=body, headers=sa)
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]
    r = requests.put(f"{API}/patients/{pid}", json={"igss_ordenes": [
        {"nog": NUM, "no_sps": f"N2-{TAG}", "codigo": "", "procedimiento": "Consulta"},
        {"nog": NUM3, "no_sps": f"N3-{TAG}", "codigo": "", "procedimiento": "Consulta"}]}, headers=sa)
    assert r.status_code == 200, r.text
    assert len(r.json()["igss_ordenes"]) == 2
    assert requests.delete(f"{API}/patients/{pid}", headers=sa).status_code == 200
    r = requests.post(f"{API}/patients/{pid}/reactivate", headers=sa)
    assert r.status_code == 200 and r.json()["is_active"] is True
    _mismo_sistema_anterior(antes, _huella())


def test_04_evaluacion_guardar_editar_eliminar_actualiza_el_libro(sa):
    antes = _huella()
    r = requests.post(f"{API}/evaluaciones", json={"paciente_id": P1, "medico_nombre": "Dr. TEST Solo",
                                                   "motivo_consulta": "Control TEST", "fecha": "2026-11-10",
                                                   "igss_orden_id": O1}, headers=sa)
    assert r.status_code == 200, r.text
    ev_id = r.json()["id"]
    assert _orden(sa)["estado"] == "atendida"
    r = requests.put(f"{API}/evaluaciones/{ev_id}", json={"plan": "Plan TEST"}, headers=sa)
    assert r.status_code == 200, r.text
    assert requests.delete(f"{API}/evaluaciones/{ev_id}", headers=sa).status_code == 200
    o = _orden(sa)
    assert o["estado"] == "pendiente" and o["total_atenciones"] == 0
    _mismo_sistema_anterior(antes, _huella())


def test_05_limpiar_borradores_y_crear_eliminar_nog(sa):
    antes = _huella()
    r = requests.post(f"{API}/igss-units/mantenimiento/borradores-vacios/limpiar", json={"confirmar": True}, headers=sa)
    assert r.status_code == 200 and r.json()["eliminados"] >= 1

    async def existe(db):
        return await db.evaluaciones_oftalmologicas.find_one({"id": E0}, {"_id": 1})
    assert _db_call(existe) is None  # la acción principal se ejecutó
    r = requests.post(f"{API}/igss-units/{U}/nogs", json={"numero": f"TSOLO4{TAG}", "nombre_servicio": "Consulta",
                                                          "tipo_compra": "contrato", "cantidad": 5, "precio": 10}, headers=sa)
    assert r.status_code == 200 and r.json()["acreditaciones_retroactivas"] == 0, r.text
    assert requests.delete(f"{API}/igss-units/nogs/{N3}", headers=sa).status_code == 200
    _mismo_sistema_anterior(antes, _huella())  # la acreditación A3 del NOG eliminado sigue intacta


def _norm(s):
    s = "".join(c for c in unicodedata.normalize("NFD", (s or "").strip()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).upper()


def test_06_fusion_de_unidades_duplicadas_no_toca_acreditaciones(sa):
    with open("/app/backend/data/igss_nogs_seed.json", encoding="utf-8") as fh:
        nombres = {_norm(i.get("unidad_nombre")) for i in json.load(fh)}

    async def preparar(db):
        for u in await db.igss_units.find({}, {"_id": 0}).sort("created_at", 1).to_list(None):
            n = await db.igss_nogs.find_one({"unidad_id": u["id"], "numero": {"$nin": ["", None]}}, {"_id": 0})
            if _norm(u.get("name")) in nombres and n:
                await db.igss_units.insert_one({"id": DUP_U, "name": u["name"], "created_at": "2099-01-01T00:00:00+00:00"})
                await db.igss_nogs.insert_one({**{k: v for k, v in n.items() if k != "id"}, "id": DUP_N, "unidad_id": DUP_U})
                await db.igss_nog_acreditaciones.insert_one(_acr(AD, DUP_N, DUP_U))
                await db.system_flags.update_one({"key": "nog_dedup_cleanup_v1"}, {"$set": {"done": False}}, upsert=True)
                return True
        return False
    if not _db_call(preparar):
        pytest.skip("No hay una unidad del listado oficial con NOG para simular el duplicado")
    antes = _huella()
    import server
    asyncio.run(server.cleanup_igss_nog_seed_duplicates())

    async def estado(db):
        return (await db.igss_units.find_one({"id": DUP_U}), await db.igss_nogs.find_one({"id": DUP_N}),
                await db.igss_nog_acreditaciones.find_one({"id": AD}, {"_id": 0}))
    unidad, nog, acr = _db_call(estado)
    assert unidad is None and nog is None  # la fusión se ejecutó
    assert acr["nog_id"] == DUP_N and acr["unidad_id"] == DUP_U  # la acreditación antigua no se tocó
    _mismo_sistema_anterior(antes, _huella())


def test_07_apagar_restaura_el_sistema_anterior(sa):
    assert requests.put(f"{LIBRO}/config", json={"usar_solo_libro": False}, headers=sa).json()["usar_solo_libro"] is False
    r = requests.post(f"{API}/igss-units/nogs/{N}/recalcular", headers=sa)
    assert r.status_code == 200, r.text
