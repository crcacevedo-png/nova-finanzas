# Restaurar un respaldo COMPLETO (solo superadmin). SOLO corre en una copia aislada de la BD
# (memory/comparacion_pruebas/restaurar.sh, PERMITIR_RESTAURAR=1): reemplaza TODA la base.
# respaldo → cambios en todos los módulos → revisión (impacto exacto + sesiones abiertas) → rechazos
# → restauración (todo igual al respaldo; audit_logs y la lista de respaldos sobreviven) → el
# respaldo previo devuelve el estado anterior a la restauración. En proceso: si el respaldo previo
# o la preparación fallan, no se toca nada.
import asyncio
import functools
import gzip
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from usuarios_prueba import par

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
pytestmark = pytest.mark.skipif(os.environ.get("PERMITIR_RESTAURAR") != "1",
                                reason="Solo en una copia aislada: restaura TODA la base")
API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
BK = f"{API}/backups"
TAG = uuid.uuid4().hex[:6]
ID = {k: f"TEST_rest_{k}_{TAG}" for k in ("pmod", "pborrar", "cborrar", "pnuevo", "eval", "cita", "pago", "pagoopt",
                                           "venta", "ventaopt", "orden")}
NUEVA = f"TEST_rest_nueva_{TAG}"
E, TIEMPOS = {}, {}
AHORA = datetime.now(timezone.utc).isoformat()


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
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p}, timeout=60)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _sa():
    return _login("superadmin")


async def _foto_async(db):
    from routes.backups_restaurar import _huellas, _restaurable
    out = {}
    for n in await db.list_collection_names():
        if _restaurable(n):
            docs = await db[n].find({}).to_list(None)
            if docs:
                out[n] = _huellas(docs)
    return out


def _foto():
    return _db_call(_foto_async)


def _foto_respaldo(rec):
    from routes.backups_restaurar import _huellas, _restaurable
    r = requests.get(f"{BK}/{rec['id']}/download", headers=_sa(), timeout=300)
    assert r.status_code == 200
    data = json.loads(gzip.decompress(r.content))["data"]
    return {n: _huellas(d) for n, d in data.items() if _restaurable(n) and d}


def _esperar(tarea_id, limite=900):
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        t = requests.get(f"{BK}/restauraciones/{tarea_id}", headers=_sa(), timeout=60).json()
        if t["estado"] != "en_curso":
            return t
        time.sleep(1)
    raise AssertionError("la tarea no terminó")


def _respaldo_completo():
    r = requests.post(f"{BK}/run", headers=_sa(), timeout=60)
    assert r.status_code == 200, r.text
    fin = time.monotonic() + 600
    while time.monotonic() < fin:
        rec = next(b for b in requests.get(BK, headers=_sa(), timeout=60).json()["data"] if b["id"] == r.json()["id"])
        if rec["status"] != "en_progreso":
            assert rec["status"] == "completado", rec
            return rec
        time.sleep(1)
    raise AssertionError("el respaldo no terminó")


def _revisar(rec):
    r = requests.post(f"{BK}/{rec['id']}/restaurar/revisar", headers=_sa(), timeout=60)
    assert r.status_code == 200, r.text
    t = _esperar(r.json()["id"])
    assert t["estado"] == "listo", t
    return t


def _restaurar(rev):
    r = requests.post(f"{BK}/restaurar", json={"revision_id": rev["id"], "palabra": "RESTAURAR"}, headers=_sa(), timeout=60)
    assert r.status_code == 200, r.text
    t = _esperar(r.json()["id"])
    assert t["estado"] == "listo", t
    return t


def _tiempos(t):
    return {**{p["paso"]: p["segundos"] for p in t["pasos"]}, "total": t["segundos"]}


def test_01_respaldo_inicial():
    async def sembrar(db):
        await db.patients.insert_many([
            {"id": ID[k], "record_number": f"TEST-REST-{k}-{TAG}", "first_name": "TEST_REST", "last_name": k,
             "is_active": True, "created_at": AHORA} for k in ("pmod", "pborrar")])
        await db.citas.insert_one({"id": ID["cborrar"], "paciente_id": ID["pmod"], "fecha": "2026-12-01", "estado": "programada"})
    _db_call(sembrar)
    _sa()
    t0 = time.monotonic()
    E["backup"] = _respaldo_completo()
    TIEMPOS["respaldo_manual"] = round(time.monotonic() - t0, 1)
    TIEMPOS["documentos"] = E["backup"]["documents_count"]
    TIEMPOS["tamano_mb"] = round(E["backup"]["size"] / 1048576, 1)


def test_02_cambios_en_todos_los_modulos():
    async def cambiar(db):
        await db.patients.insert_one({"id": ID["pnuevo"], "record_number": f"TEST-REST-pn-{TAG}", "first_name": "TEST_REST",
                                      "last_name": "nuevo", "is_active": True, "created_at": AHORA})
        await db.patients.update_one({"id": ID["pmod"]}, {"$set": {"first_name": "TEST_REST_CAMBIADO"}})
        await db.patients.delete_one({"id": ID["pborrar"]})
        await db.evaluaciones_oftalmologicas.insert_one({"id": ID["eval"], "paciente_id": ID["pnuevo"], "fecha": "2026-12-01"})
        await db.citas.insert_one({"id": ID["cita"], "paciente_id": ID["pnuevo"], "fecha": "2026-12-02", "estado": "programada"})
        await db.citas.delete_one({"id": ID["cborrar"]})
        await db.payments.insert_one({"id": ID["pago"], "amount": 10.0, "date": "2026-12-01"})
        await db.optica_sale_payments.insert_one({"id": ID["pagoopt"], "amount": 5.0})
        await db.ventas.insert_one({"id": ID["venta"], "numero_venta": f"TEST-REST-{TAG}", "total": 10.0})
        await db.optica_sales.insert_one({"id": ID["ventaopt"], "order_number": f"TEST-REST-{TAG}", "total": 5.0})
        await db.igss_ordenes_libro.insert_one({"id": ID["orden"], "numero_libro": f"ORD-TREST{TAG}", "estado": "reservada",
                                                "vigente": False, "paciente_id": ID["pnuevo"]})
        await db[NUEVA].insert_one({"id": "x"})
    _db_call(cambiar)
    assert requests.get(f"{API}/auth/me", headers=_login("admin"), timeout=60).status_code == 200


def test_03_revision_impacto_exacto_y_sesiones_abiertas():
    t = _revisar(E["backup"])
    E["revision"], TIEMPOS["revision"] = t, t["segundos"]
    res = t["resultado"]
    g = {x["nombre"]: (x["creados"], x["cambiados"], x["borrados"]) for x in res["grupos"]}
    assert g == {"Pacientes": (1, 1, 1), "Evaluaciones": (1, 0, 0), "Citas": (1, 0, 1), "Pagos": (2, 0, 0),
                 "Ventas": (2, 0, 0), "Órdenes IGSS": (1, 0, 0)}, g
    assert any(c["coleccion"] == NUEVA and c["creados"] == 1 for c in res["colecciones"])
    assert not any(c["coleccion"] in ("audit_logs", "backups", "sesiones_actividad") for c in res["colecciones"])
    usuarios = {s["usuario"] for s in res["sesiones"]}
    assert par("admin")[0] in usuarios and par("superadmin")[0] not in usuarios
    assert res["vence"] > datetime.now(timezone.utc).isoformat()
    log = _db_call(lambda db: db.audit_logs.find_one({"action": "RESPALDO_RESTAURACION_REVISADA", "details.revision_id": t["id"]}))
    assert log and log["details"]["grupos"]["Pacientes"] == {"creados": 1, "cambiados": 1, "borrados": 1}


def test_04_rechazos():
    rid = E["revision"]["id"]
    assert requests.post(f"{BK}/restaurar", json={"revision_id": rid, "palabra": "restaurar"}, headers=_sa(), timeout=60).status_code == 400
    for clave in ("admin", "igss", "usuario"):
        h = _login(clave)
        assert requests.post(f"{BK}/restaurar", json={"revision_id": rid, "palabra": "RESTAURAR"}, headers=h, timeout=60).status_code == 403
        assert requests.post(f"{BK}/{E['backup']['id']}/restaurar/revisar", headers=h, timeout=60).status_code == 403
        assert requests.get(f"{BK}/restauraciones", headers=h, timeout=60).status_code == 403
    yo = requests.get(f"{API}/auth/me", headers=_sa(), timeout=60).json()["id"]
    futuro = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    pasado = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    falsas = [{"id": f"TEST_rest_rev_{k}_{TAG}", "tipo": "revision", "estado": "listo", "backup_id": E["backup"]["id"],
               "created_by": quien, "resultado": {"vence": vence}} for k, quien, vence in (("otro", "otro-usuario", futuro), ("vencida", yo, pasado))]
    _db_call(lambda db: db.restauraciones.insert_many(falsas))
    r = requests.post(f"{BK}/restaurar", json={"revision_id": falsas[0]["id"], "palabra": "RESTAURAR"}, headers=_sa(), timeout=60)
    assert r.status_code == 403
    r = requests.post(f"{BK}/restaurar", json={"revision_id": falsas[1]["id"], "palabra": "RESTAURAR"}, headers=_sa(), timeout=60)
    assert r.status_code == 409 and "venció" in r.json()["detail"]
    assert requests.post(f"{BK}/restaurar", json={"revision_id": "no-existe", "palabra": "RESTAURAR"}, headers=_sa(), timeout=60).status_code == 409


def test_05_restaurar_deja_todo_igual_al_respaldo():
    esperado = _foto_respaldo(E["backup"])
    n_audit = _db_call(lambda db: db.audit_logs.count_documents({}))
    E["antes"] = _foto()
    t = _restaurar(E["revision"])
    E["restauracion"], TIEMPOS["restauracion"] = t, _tiempos(t)
    r = requests.post(f"{BK}/restaurar", json={"revision_id": E["revision"]["id"], "palabra": "RESTAURAR"}, headers=_sa(), timeout=60)
    assert r.status_code == 409  # la misma revisión no se usa dos veces
    despues = _foto()
    for col in ("patients", "igss_ordenes_libro", "evaluaciones_oftalmologicas", "citas", "users"):
        assert despues.get(col) == esperado.get(col), col
    assert sorted(c for c in set(despues) | set(esperado) if despues.get(c) != esperado.get(c)) == []
    # audit_logs sobrevive (no vuelve atrás) y registra la restauración
    assert _db_call(lambda db: db.audit_logs.count_documents({})) > n_audit
    for accion in ("RESPALDO_RESTAURACION_INICIADA", "RESPALDO_RESTAURACION_COMPLETADA"):
        assert _db_call(lambda db: db.audit_logs.find_one({"action": accion, "details.tarea_id": t["id"]})), accion
    lista = {b["id"]: b for b in requests.get(BK, headers=_sa(), timeout=60).json()["data"]}
    assert lista[t["respaldo_previo_id"]]["tipo"] == "previo_restauracion" and lista[t["respaldo_previo_id"]]["status"] == "completado"
    assert E["backup"]["id"] in lista
    assert requests.get(f"{API}/patients?limit=1", headers=_sa(), timeout=60).status_code == 200


def test_06_el_respaldo_previo_vuelve_al_estado_anterior():
    lista = {b["id"]: b for b in requests.get(BK, headers=_sa(), timeout=60).json()["data"]}
    previo = lista[E["restauracion"]["respaldo_previo_id"]]
    rev = _revisar(previo)
    g = {x["nombre"]: (x["creados"], x["cambiados"], x["borrados"]) for x in rev["resultado"]["grupos"]}
    assert g["Pacientes"] == (1, 1, 1) and g["Órdenes IGSS"] == (0, 0, 1)
    t = _restaurar(rev)
    TIEMPOS["vuelta_con_previo"] = _tiempos(t)
    assert _foto() == E["antes"]


def test_07_si_falla_el_respaldo_previo_o_la_preparacion_no_se_toca_nada():
    async def escenario():
        import routes.backups as B
        import routes.backups_restaurar as R
        db = R.db
        user = await db.users.find_one({"username": par("superadmin")[0]}, {"_id": 0})
        rev = {"resultado": {"sesiones": [], "grupos": [], "total": {}}}
        antes = await _foto_async(db)

        def caido(*a, **k):
            raise RuntimeError("almacenamiento caído (prueba)")
        original = B.put_object
        B.put_object = caido
        try:
            t1 = await R._nueva_tarea("restauracion", E["backup"], user)
            await R._ejecutar(t1["id"], E["backup"], rev, user)
        finally:
            B.put_object = original
        t1 = await db.restauraciones.find_one({"id": t1["id"]}, {"_id": 0})
        assert t1["estado"] == "cancelada" and "respaldo previo falló" in t1["error"], t1
        assert (await db.backups.find_one({"id": t1["respaldo_previo_id"]}))["status"] == "error"
        assert await db.audit_logs.find_one({"action": "RESPALDO_RESTAURACION_CANCELADA", "details.tarea_id": t1["id"]})
        assert await _foto_async(db) == antes

        async def roto(_rec):  # usuarios repetidos: rompe el índice único de username al preparar
            u = await db.users.find_one({}, {"_id": 0})
            return {"users": [dict(u), dict(u)], "patients": []}
        original_c = R._cargar_respaldo
        R._cargar_respaldo = roto
        try:
            t2 = await R._nueva_tarea("restauracion", E["backup"], user)
            await R._ejecutar(t2["id"], E["backup"], rev, user)
        finally:
            R._cargar_respaldo = original_c
        t2 = await db.restauraciones.find_one({"id": t2["id"]}, {"_id": 0})
        assert t2["estado"] == "cancelada" and "No se restauró nada" in t2["error"], t2
        assert await _foto_async(db) == antes
        assert not [n for n in await db.list_collection_names() if n.startswith(R.TMP)]
        assert (await db.restauraciones.find_one({"_id": R.CANDADO}))["activo"] is False
    asyncio.run(escenario())


def test_99_limpieza_y_tiempos():
    async def limpiar(db):
        for col in ("patients", "evaluaciones_oftalmologicas", "citas", "payments", "optica_sale_payments", "ventas",
                    "optica_sales", "igss_ordenes_libro", "restauraciones"):
            await db[col].delete_many({"id": {"$regex": f"^TEST_rest_.*_{TAG}$"}})
        await db.drop_collection(NUEVA)
    _db_call(limpiar)
    print("\nTIEMPOS_RESTAURACION " + json.dumps(TIEMPOS, ensure_ascii=False))
