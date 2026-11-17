# Libro de órdenes IGSS — Fase 1 (modelo `igss_ordenes_libro`): No. SPS obligatorio y
# único por unidad, cupo atómico, anulación, catálogo Baja Cuantía / sin tope y permisos
# LIBRO_IGSS_ROLES. Todo se siembra con prefijo TEST_ y se borra al terminar el módulo.
import os
import time
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from usuarios_prueba import par  # usuarios sembrados solo para pruebas

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
LIBRO = f"{API}/igss-units/libro"

TAG = uuid.uuid4().hex[:6]
UNIT = f"TEST_libro_u1_{TAG}"
UNIT2 = f"TEST_libro_u2_{TAG}"
UNIT3 = f"TEST_libro_u3_{TAG}"
PAC1 = f"TEST_libro_p1_{TAG}"
PAC2 = f"TEST_libro_p2_{TAG}"
CREDS = {
    "superadmin": par("superadmin"),
    "admin": par("admin"),
    "administrador_igss": par("igss"),
    "usuario": par("usuario"),
    "medico": par("medico"),
}
CONFIG_PREVIA = []
AUTORIZADOS = ["superadmin", "admin", "administrador_igss"]
DENEGADOS = ["usuario", "medico"]


def _db_call(fn):
    async def runner():
        client = AsyncIOMotorClient(os.environ['MONGO_URL'])
        try:
            return await fn(client[os.environ['DB_NAME']])
        finally:
            client.close()
    return asyncio.run(runner())


def _login(u, p):
    for _ in range(8):
        r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
        if r.status_code == 429:
            time.sleep(12)
            continue
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    raise AssertionError("Login bloqueado por rate limit")


@pytest.fixture(scope="module")
def H():
    return {rol: _login(*c) for rol, c in CREDS.items()}


@pytest.fixture(scope="module", autouse=True)
def seed():
    async def ins(db):
        await db.igss_units.insert_many([
            {"id": UNIT, "name": f"TEST Libro U1 {TAG}", "code": "TL1", "is_active": True},
            {"id": UNIT2, "name": f"TEST Libro U2 {TAG}", "code": "TL2", "is_active": True},
            {"id": UNIT3, "name": f"TEST Libro U3 {TAG}", "code": "TL3", "is_active": True},
        ])
        await db.patients.insert_many([
            {"id": pid, "record_number": f"TEST-LIB-{i}-{TAG}", "first_name": "TEST_LIBRO", "last_name": f"Paciente {i}",
             "referral_institution": "igss", "igss_unit_id": UNIT, "is_active": True, "igss_afiliacion": f"AF-{i}",
             "gender": "femenino", "birth_date": "1970-01-01", "phone": "55551234", "dpi": f"{i}{'0' * 12}",
             "igss_ordenes": [{"id": f"legacy-{i}", "nog": "LEGACY", "no_sps": f"LEG-{i}", "codigo": "", "procedimiento": ""}],
             "igss_no_sps": f"LEG-{i}", "igss_nog": "LEGACY"}
            for i, pid in ((1, PAC1), (2, PAC2))
        ])
        prev = await db.igss_libro_config.find_one({"id": "libro_igss"}, {"_id": 0})
        CONFIG_PREVIA.append(prev)
        await db.igss_libro_config.update_one({"id": "libro_igss"}, {"$set": {"exigir_orden": False}}, upsert=True)
    _db_call(ins)
    yield

    async def clean(db):
        units = [UNIT, UNIT2, UNIT3]
        nog_ids = await db.igss_nogs.distinct("id", {"unidad_id": {"$in": units}})
        orden_ids = await db.igss_ordenes_libro.distinct("id", {"unidad_id": {"$in": units}})
        await db.igss_ordenes_libro.delete_many({"unidad_id": {"$in": units}})
        await db.igss_nog_acreditaciones.delete_many({"nog_id": {"$in": nog_ids}})
        await db.igss_nogs.delete_many({"unidad_id": {"$in": units}})
        pacs = [PAC1, PAC2] + await db.patients.distinct("id", {"first_name": f"TEST_LIBRO_NUEVO_{TAG}"})
        cx_ids = await db.surgeries.distinct("id", {"patient_id": {"$in": pacs}})
        ev_ids = await db.evaluaciones_oftalmologicas.distinct("id", {"paciente_id": {"$in": pacs}})
        await db.surgeries.delete_many({"id": {"$in": cx_ids}})
        await db.anesthesia_records.delete_many({"surgery_id": {"$in": cx_ids}})
        await db.notas_cirugia.delete_many({"surgery_id": {"$in": cx_ids}})
        await db.evaluaciones_oftalmologicas.delete_many({"id": {"$in": ev_ids}})
        await db.igss_atenciones_sin_orden.delete_many({"ref_id": {"$in": cx_ids + ev_ids}})
        await db.audit_logs.delete_many({"details.ref_id": {"$in": cx_ids + ev_ids}})
        await db.audit_logs.delete_many({"details.surgery_id": {"$in": cx_ids}})
        await db.patients.delete_many({"id": {"$in": pacs}})
        prev = CONFIG_PREVIA[0] if CONFIG_PREVIA else None
        await db.igss_libro_config.update_one({"id": "libro_igss"}, {"$set": {"exigir_orden": bool((prev or {}).get("exigir_orden"))}}, upsert=True)
        await db.igss_units.delete_many({"id": {"$in": units}})
        await db.audit_logs.delete_many({"action": {"$regex": "^LIBRO_"}, "$or": [
            {"details.unidad_id": {"$in": units}}, {"details.nog_id": {"$in": nog_ids}},
            {"details.orden_id": {"$in": orden_ids}}]})
    _db_call(clean)


_SPS_N = [0]


def sps():
    _SPS_N[0] += 1
    return f"sps-{TAG}-{_SPS_N[0]}"


def nueva_entrada(h, unit=UNIT, **kw):
    body = {"numero": f"TESTNOG{TAG}{uuid.uuid4().hex[:4]}", "nombre_servicio": "TEST servicio",
            "tipo_compra": "contrato", "cantidad": 10, "precio": 100}
    body.update(kw)
    return requests.post(f"{API}/igss-units/{unit}/nogs", json=body, headers=h)


def entrada(h, **kw):
    r = nueva_entrada(h, **kw)
    assert r.status_code == 200, r.text
    return r.json()


def nueva_orden(h, nog_id, no_sps=None, pac=PAC1, **kw):
    body = {"nog_id": nog_id, "paciente_id": pac, "no_sps": sps() if no_sps is None else no_sps}
    body.update(kw)
    return requests.post(f"{LIBRO}/ordenes", json=body, headers=h)


def orden(h, nog_id, **kw):
    r = nueva_orden(h, nog_id, **kw)
    assert r.status_code == 200, r.text
    return r.json()


def contador(h, nog_id):
    r = requests.get(f"{LIBRO}/nogs/{nog_id}/contador", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- 1 y 2: No. SPS ----------

def test_01_sps_repetido_en_la_misma_unidad_falla(H):
    sa = H["superadmin"]
    n1 = entrada(sa)
    o = orden(sa, n1["id"], no_sps=f"  abc-{TAG} ")
    assert o["no_sps"] == f"ABC-{TAG}".upper() and o["estado"] == "pendiente"
    r = nueva_orden(sa, n1["id"], no_sps=f"Abc-{TAG}", pac=PAC2)
    assert r.status_code == 409 and "No. SPS" in r.json()["detail"]
    # Otra entrada del catálogo de la MISMA unidad tampoco admite el SPS repetido
    n1b = entrada(sa)
    assert nueva_orden(sa, n1b["id"], no_sps=f"ABC-{TAG}").status_code == 409
    # El mismo SPS en OTRA unidad sí se permite
    n2 = entrada(sa, unit=UNIT2)
    assert nueva_orden(sa, n2["id"], no_sps=f"ABC-{TAG}").status_code == 200
    # Al anular la orden el SPS queda libre (índice único parcial solo para vigentes)
    assert requests.post(f"{LIBRO}/ordenes/{o['id']}/anular", json={"motivo": "SPS mal digitado"}, headers=sa).status_code == 200
    assert nueva_orden(sa, n1["id"], no_sps=f"abc-{TAG}").status_code == 200


def test_02_orden_sin_sps_rechazada(H):
    sa = H["superadmin"]
    n = entrada(sa)
    for valor in ("", "   "):
        r = nueva_orden(sa, n["id"], no_sps=valor)
        assert r.status_code == 422 and "No. SPS es obligatorio" in r.json()["detail"]
    r = requests.post(f"{LIBRO}/ordenes", json={"nog_id": n["id"], "paciente_id": PAC1}, headers=sa)
    assert r.status_code == 422
    assert contador(sa, n["id"])["reservados"] == 0


# ---------- 7: pendiente = reservado ----------

def test_07_orden_pendiente_cuenta_como_reservada(H):
    sa = H["superadmin"]
    n = entrada(sa, cantidad=3)
    orden(sa, n["id"])
    c = contador(sa, n["id"])
    assert c["reservados"] == 1 and c["consumidos"] == 0 and c["disponibles"] == 2
    assert c["monto_acumulado"] == 0


# ---------- 9: concurrencia ----------

def test_09_veinte_creaciones_simultaneas_con_cupo_para_cinco(H):
    sa = H["superadmin"]
    n = entrada(sa, cantidad=5)
    with ThreadPoolExecutor(max_workers=20) as ex:
        codigos = list(ex.map(lambda i: nueva_orden(sa, n["id"], no_sps=f"CONC-{TAG}-{i}").status_code, range(20)))
    assert codigos.count(200) == 5, codigos
    assert codigos.count(409) == 15, codigos
    vig = _db_call(lambda db: db.igss_ordenes_libro.count_documents({"nog_id": n["id"], "vigente": True}))
    assert vig == 5
    c = contador(sa, n["id"])
    assert c["reservados"] == 5 and c["bloqueado"] is True and c["disponibles"] == 0
    r = nueva_orden(sa, n["id"])
    assert r.status_code == 409 and "100 %" in r.json()["detail"]


def test_anular_libera_cupo_y_exige_motivo(H):
    sa = H["superadmin"]
    n = entrada(sa, cantidad=1)
    o = orden(sa, n["id"])
    assert nueva_orden(sa, n["id"]).status_code == 409
    assert requests.post(f"{LIBRO}/ordenes/{o['id']}/anular", json={}, headers=sa).status_code == 422
    r = requests.post(f"{LIBRO}/ordenes/{o['id']}/anular", json={"motivo": "Orden duplicada por error"}, headers=sa)
    assert r.status_code == 200
    a = r.json()
    assert a["estado"] == "anulada" and a["motivo_anulacion"] == "Orden duplicada por error"
    assert a["anulada_por"] and a["fecha_anulacion"]
    assert requests.post(f"{LIBRO}/ordenes/{o['id']}/anular", json={"motivo": "otra vez"}, headers=sa).status_code == 400
    assert requests.put(f"{LIBRO}/ordenes/{o['id']}", json={"codigo": "X"}, headers=sa).status_code == 400
    c = contador(sa, n["id"])
    assert c["reservados"] == 0 and c["anuladas"] == 1
    assert nueva_orden(sa, n["id"]).status_code == 200
    # La orden anulada sigue existiendo (nunca se elimina)
    assert requests.get(f"{LIBRO}/ordenes/{o['id']}", headers=sa).status_code == 200


def test_dosis_y_edicion_atomica(H):
    sa = H["superadmin"]
    n = entrada(sa)
    r = nueva_orden(sa, n["id"], tipo="consulta", dosis_autorizadas=3)
    assert r.status_code == 422
    o = orden(sa, n["id"], tipo="procedimiento", dosis_autorizadas=3, codigo="P01", procedimiento="Avastin")
    assert o["dosis_autorizadas"] == 3 and o["dosis_aplicadas"] == 0
    c = orden(sa, n["id"])
    assert requests.put(f"{LIBRO}/ordenes/{c['id']}", json={"dosis_autorizadas": 3}, headers=sa).status_code == 422
    # Simula 2 dosis aplicadas (el registro automático de atenciones llega en la Fase 2)
    _db_call(lambda db: db.igss_ordenes_libro.update_one({"id": o["id"]}, {"$set": {"atenciones": [
        {"tipo": "cirugia", "ref_id": "TEST_c1", "numero_dosis": 1},
        {"tipo": "cirugia", "ref_id": "TEST_c2", "numero_dosis": 2}], "estado": "atendida"}}))
    r = requests.put(f"{LIBRO}/ordenes/{o['id']}", json={"dosis_autorizadas": 1}, headers=sa)
    assert r.status_code == 422 and "2 dosis aplicadas" in r.json()["detail"]
    r = requests.put(f"{LIBRO}/ordenes/{o['id']}", json={"paciente_id": PAC2}, headers=sa)
    assert r.status_code == 422
    r = requests.put(f"{LIBRO}/ordenes/{o['id']}", json={"impreso": True, "precio": 250, "costo_override": 90}, headers=sa)
    assert r.status_code == 200 and r.json()["impreso"] is True and r.json()["precio"] == 250
    assert r.json()["dosis_aplicadas"] == 2
    r = requests.put(f"{LIBRO}/ordenes/{c['id']}", json={"no_sps": o["no_sps"].lower()}, headers=sa)
    assert r.status_code == 409
    logs = _db_call(lambda db: db.audit_logs.count_documents({"action": "LIBRO_ORDEN_EDITADA", "details.orden_id": o["id"]}))
    assert logs == 1


# ---------- 11: catálogo con órdenes ----------

def test_11_entrada_con_ordenes_no_se_puede_eliminar(H):
    sa = H["superadmin"]
    n = entrada(sa)
    orden(sa, n["id"])
    r = requests.delete(f"{API}/igss-units/nogs/{n['id']}", headers=sa)
    assert r.status_code == 400 and "Desactívela" in r.json()["detail"]
    r = requests.put(f"{API}/igss-units/nogs/{n['id']}", json={"is_active": False}, headers=sa)
    assert r.status_code == 200 and r.json()["estado"] == "inactivo"
    assert nueva_orden(sa, n["id"]).status_code == 400
    # Sin órdenes sí se puede eliminar
    vacia = entrada(sa)
    assert requests.delete(f"{API}/igss-units/nogs/{vacia['id']}", headers=sa).status_code == 200


# ---------- 13: permisos ----------

@pytest.mark.parametrize("rol", AUTORIZADOS)
def test_13_roles_autorizados_200(H, rol):
    h = H[rol]
    n = entrada(h)
    o = orden(h, n["id"])
    assert requests.get(f"{LIBRO}/ordenes", params={"nog_id": n["id"]}, headers=h).status_code == 200
    assert requests.get(f"{LIBRO}/ordenes/{o['id']}", headers=h).status_code == 200
    assert requests.put(f"{LIBRO}/ordenes/{o['id']}", json={"codigo": "C1"}, headers=h).status_code == 200
    assert requests.get(f"{LIBRO}/nogs/{n['id']}/contador", headers=h).status_code == 200
    assert requests.post(f"{LIBRO}/ordenes/{o['id']}/anular", json={"motivo": "prueba de rol"}, headers=h).status_code == 200
    assert requests.put(f"{API}/igss-units/nogs/{n['id']}", json={"precio": 120}, headers=h).status_code == 200
    vacia = entrada(h)
    assert requests.delete(f"{API}/igss-units/nogs/{vacia['id']}", headers=h).status_code == 200


@pytest.mark.parametrize("rol", DENEGADOS)
def test_13_roles_no_autorizados_403(H, rol):
    sa, h = H["superadmin"], H[rol]
    n = entrada(sa)
    o = orden(sa, n["id"])
    llamadas = [
        requests.get(f"{LIBRO}/ordenes", headers=h),
        requests.get(f"{LIBRO}/ordenes/{o['id']}", headers=h),
        nueva_orden(h, n["id"]),
        requests.put(f"{LIBRO}/ordenes/{o['id']}", json={"codigo": "X"}, headers=h),
        requests.post(f"{LIBRO}/ordenes/{o['id']}/anular", json={"motivo": "no autorizado"}, headers=h),
        requests.get(f"{LIBRO}/nogs/{n['id']}/contador", headers=h),
        nueva_entrada(h),
        requests.put(f"{API}/igss-units/nogs/{n['id']}", json={"precio": 1}, headers=h),
        requests.delete(f"{API}/igss-units/nogs/{n['id']}", headers=h),
    ]
    assert [r.status_code for r in llamadas] == [403] * len(llamadas)
    assert requests.get(f"{LIBRO}/ordenes/{o['id']}", headers=sa).json()["estado"] == "pendiente"


# ---------- 16-20: Baja Cuantía y sin tope ----------

def test_16_baja_cuantia_sin_numero_por_servicio(H):
    sa = H["superadmin"]
    a = entrada(sa, numero="", tipo_compra="baja_cuantia", nombre_servicio=f"Consulta Oftalmológica {TAG}", cantidad=None)
    b = entrada(sa, numero="", tipo_compra="baja_cuantia", nombre_servicio=f"Retina {TAG}", cantidad=None)
    assert a["numero"] == "" and b["numero"] == ""
    assert a["etiqueta"] == f"Baja cuantía — Consulta Oftalmológica {TAG}"
    r = nueva_entrada(sa, numero="", tipo_compra="baja_cuantia", nombre_servicio=f"  consulta   oftalmologica {TAG} ")
    assert r.status_code == 400
    # Sin servicio no se admite una entrada sin número
    assert nueva_entrada(sa, numero="", tipo_compra="baja_cuantia", nombre_servicio="").status_code == 422


def test_17_contrato_sin_numero_rechazado(H):
    sa = H["superadmin"]
    for tipo in ("contrato", "compra_directa", ""):
        r = nueva_entrada(sa, numero="", tipo_compra=tipo)
        assert r.status_code == 422 and "obligatorio" in r.json()["detail"]
    n = entrada(sa)
    assert requests.put(f"{API}/igss-units/nogs/{n['id']}", json={"numero": ""}, headers=sa).status_code == 422


def test_18_texto_baja_cuantia_como_numero_rechazado(H):
    sa = H["superadmin"]
    for txt in ("BAJA CUANTIA", "baja cuantía", " Baja  Cuantia 2026 "):
        r = nueva_entrada(sa, numero=txt, tipo_compra="baja_cuantia")
        assert r.status_code == 422
        assert r.json()["detail"] == "Deje el número vacío y elija tipo de compra Baja Cuantía"
    n = entrada(sa)
    r = requests.put(f"{API}/igss-units/nogs/{n['id']}", json={"numero": "BAJA CUANTIA"}, headers=sa)
    assert r.status_code == 422


def test_19_orden_baja_cuantia_con_sps(H):
    sa = H["superadmin"]
    bc = entrada(sa, numero="", tipo_compra="baja_cuantia", nombre_servicio=f"Glaucoma {TAG}", cantidad=None, precio=80)
    assert bc["sin_tope"] is True and bc["modalidad"] == "Baja Cuantía"
    r = nueva_orden(sa, bc["id"], no_sps="")
    assert r.status_code == 422
    o = orden(sa, bc["id"])
    assert o["modalidad"] == "Baja Cuantía" and o["numero_nog"] == ""
    assert o["etiqueta_nog"] == f"Baja cuantía — Glaucoma {TAG}" and o["precio"] == 80
    c = contador(sa, bc["id"])
    assert c["reservados"] == 1 and c["sin_tope"] is True
    lst = requests.get(f"{LIBRO}/ordenes", params={"nog_id": bc["id"]}, headers=sa).json()
    assert lst["total"] == 1 and lst["data"][0]["modalidad"] == "Baja Cuantía"


def test_20_entrada_sin_tope_nunca_bloquea(H):
    sa = H["superadmin"]
    st = entrada(sa, numero=f"TESTST{TAG}", tipo_compra="compra_directa", sin_tope=True, cantidad=0)
    assert st["sin_tope"] is True
    for _ in range(8):
        orden(sa, st["id"])
    c = contador(sa, st["id"])
    assert c["reservados"] == 8 and c["bloqueado"] is False and c["aviso_90"] is False
    assert c["disponibles"] is None and c["cantidad"] is None
    # Valores por defecto de sin_tope según el tipo de compra
    assert entrada(sa, numero="", tipo_compra="baja_cuantia", nombre_servicio=f"Default {TAG}", cantidad=None)["sin_tope"] is True
    assert entrada(sa, tipo_compra="contrato")["sin_tope"] is False
    # Con tope y sin cantidad no se admite
    assert nueva_entrada(sa, tipo_compra="contrato", cantidad=0).status_code == 422


def test_auditoria_de_creacion_y_anulacion(H):
    sa = H["superadmin"]
    n = entrada(sa)
    o = orden(sa, n["id"])
    requests.post(f"{LIBRO}/ordenes/{o['id']}/anular", json={"motivo": "auditoría"}, headers=sa)

    async def q(db):
        return (await db.audit_logs.find_one({"action": "LIBRO_ORDEN_CREADA", "details.orden_id": o["id"]}),
                await db.audit_logs.find_one({"action": "LIBRO_ORDEN_ANULADA", "details.orden_id": o["id"]}),
                await db.audit_logs.find_one({"action": "LIBRO_CATALOGO_CREADO", "details.nog_id": n["id"]}))
    creada, anulada, cat = _db_call(q)
    assert creada and creada["user_id"] and creada["timestamp"]
    assert anulada and anulada["details"]["motivo"] == "auditoría"
    assert cat


# ==================== FASE 2: REGISTRO DE ATENCIONES ====================

EVAL_API = f"{API}/evaluaciones"
CX_API = f"{API}/surgeries"
SIN_ORDEN = f"{LIBRO}/atenciones-sin-orden"


def switch(sa, valor):
    r = requests.put(f"{LIBRO}/config", json={"exigir_orden": valor}, headers=sa)
    assert r.status_code == 200, r.text


def crear_eval(h, pac=PAC1, orden_id="", **kw):
    body = {"paciente_id": pac, "medico_nombre": "Dr. TEST Libro", "motivo_consulta": "Control TEST",
            "fecha": "2026-11-10", "igss_orden_id": orden_id}
    body.update(kw)
    r = requests.post(EVAL_API, json=body, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def nueva_cx(h, pac=PAC1, no_sps="", **kw):
    body = {"date": "2026-11-12", "time": "08:00", "patient_name": "TEST_LIBRO Paciente", "patient_id": pac,
            "procedure": "Inyección intravítrea TEST", "surgeon": "Dr. TEST Cirujano", "eye": "OD",
            "anesthesia_type": "topica", "anesthesiologist": "Dr. TEST Anestesia", "institution": "IGSS",
            "igss_data": {"unit": "TEST", "unit_id": UNIT, "sps": no_sps, "affiliation_number": "AF-1",
                          "code": "C-01", "procedure_cost": 100}}
    body.update(kw)
    return requests.post(CX_API, json=body, headers=h)


def crear_cx(h, **kw):
    r = nueva_cx(h, **kw)
    assert r.status_code == 200, r.text
    return r.json()


def realizar(h, cx_id, valor=True):
    return requests.post(f"{CX_API}/{cx_id}/realizada", json={"realizada": valor}, headers=h)


def get_orden(h, oid):
    r = requests.get(f"{LIBRO}/ordenes/{oid}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def sin_orden_de(sa, ref_id, estado="pendiente"):
    r = requests.get(SIN_ORDEN, params={"estado": estado, "limit": 500}, headers=sa)
    assert r.status_code == 200, r.text
    return next((e for e in r.json()["data"] if e["ref_id"] == ref_id), None)


def test_03_tres_dosis_un_cupo_y_cuarta_rechazada(H):
    sa = H["superadmin"]
    n = entrada(sa, cantidad=5)
    o = orden(sa, n["id"], tipo="procedimiento", dosis_autorizadas=3, procedimiento="Avastin OD")
    switch(sa, True)
    try:
        cxs = [crear_cx(sa, no_sps=o["no_sps"]) for _ in range(4)]
        for i, cx in enumerate(cxs[:3], start=1):
            r = realizar(sa, cx["id"])
            assert r.status_code == 200, r.text
            assert r.json()["status"] == "realizado"
            assert r.json()["libro"]["dosis_aplicadas"] == i
        r = realizar(sa, cxs[3]["id"])
        assert r.status_code == 422
        assert r.json()["detail"] == "Esta orden ya completó sus 3 dosis. Se requiere una nueva orden (No. SPS)."
        assert requests.get(f"{CX_API}/{cxs[3]['id']}", headers=sa).json()["status"] == "activo"
        r = nueva_cx(sa, no_sps=o["no_sps"])
        assert r.status_code == 422 and "completó sus 3 dosis" in r.json()["detail"]
    finally:
        switch(sa, False)
    od = get_orden(sa, o["id"])
    assert od["estado"] == "atendida" and od["dosis_aplicadas"] == 3
    assert [a["numero_dosis"] for a in od["atenciones"]] == [1, 2, 3]
    c = contador(sa, n["id"])
    assert c["consumidos"] == 1 and c["reservados"] == 0


def test_04_una_dosis_segunda_cirugia(H):
    sa, us = H["superadmin"], H["usuario"]
    n = entrada(sa)
    o = orden(sa, n["id"], tipo="procedimiento", dosis_autorizadas=1)
    c1, c2, c3 = (crear_cx(sa, no_sps=o["no_sps"]) for _ in range(3))
    assert realizar(sa, c1["id"]).status_code == 200
    switch(sa, True)
    try:
        r = realizar(sa, c2["id"])
        assert r.status_code == 422 and "completó sus 1 dosis" in r.json()["detail"]
    finally:
        switch(sa, False)
    # Interruptor apagado: la cirugía se guarda, pero NO se anota en la orden completa:
    # queda en "atenciones sin orden" pidiendo otra orden (aviso genérico al usuario)
    r = realizar(us, c3["id"])
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo.get("aviso_igss") and cuerpo.get("libro") is None
    od = get_orden(sa, o["id"])
    assert od["dosis_aplicadas"] == 1
    e = sin_orden_de(sa, c3["id"])
    assert e and "completó sus 1 dosis" in e["motivo"]
    # Tampoco se puede asignar a mano a la orden completa
    r = requests.post(f"{SIN_ORDEN}/{e['id']}/asignar", json={"orden_id": o["id"]}, headers=sa)
    assert r.status_code == 422 and "completó sus 1 dosis" in r.json()["detail"]


def test_05_cirugia_programada_no_registra(H):
    sa = H["superadmin"]
    n = entrada(sa)
    o = orden(sa, n["id"], tipo="procedimiento", dosis_autorizadas=3)
    cx = crear_cx(sa, no_sps=o["no_sps"])
    od = get_orden(sa, o["id"])
    assert od["estado"] == "pendiente" and od["total_atenciones"] == 0
    assert sin_orden_de(sa, cx["id"]) is None
    # Al desmarcar "realizada" la dosis se quita
    assert realizar(sa, cx["id"]).status_code == 200
    assert get_orden(sa, o["id"])["dosis_aplicadas"] == 1
    assert realizar(sa, cx["id"], False).status_code == 200
    od = get_orden(sa, o["id"])
    assert od["estado"] == "pendiente" and od["dosis_aplicadas"] == 0


def test_06_consulta_seguimiento_no_consume_otro_cupo(H):
    sa = H["superadmin"]
    n = entrada(sa, cantidad=5)
    o = orden(sa, n["id"])
    crear_eval(sa, orden_id=o["id"])
    crear_eval(sa, orden_id=o["id"], fecha="2026-11-20")
    od = get_orden(sa, o["id"])
    assert od["estado"] == "atendida" and od["total_atenciones"] == 2
    assert od["fecha_primera_atencion"] == "2026-11-10"
    c = contador(sa, n["id"])
    assert c["consumidos"] == 1 and c["reservados"] == 0 and c["disponibles"] == 4


def test_10_eliminar_evaluacion_devuelve_a_pendiente(H):
    sa = H["superadmin"]
    n = entrada(sa)
    o = orden(sa, n["id"])
    ev = crear_eval(sa, orden_id=o["id"])
    assert get_orden(sa, o["id"])["estado"] == "atendida"
    assert requests.delete(f"{EVAL_API}/{ev['id']}", headers=sa).status_code == 200
    od = get_orden(sa, o["id"])
    assert od["estado"] == "pendiente" and od["total_atenciones"] == 0 and od["fecha_primera_atencion"] is None
    # Lo mismo al eliminar una cirugía realizada; las dosis restantes se renumeran
    p = orden(sa, n["id"], tipo="procedimiento", dosis_autorizadas=3)
    c1, c2 = crear_cx(sa, no_sps=p["no_sps"]), crear_cx(sa, no_sps=p["no_sps"])
    realizar(sa, c1["id"])
    realizar(sa, c2["id"])
    assert requests.delete(f"{CX_API}/{c1['id']}", headers=sa).status_code == 200
    pd = get_orden(sa, p["id"])
    assert pd["dosis_aplicadas"] == 1 and pd["atenciones"][0]["numero_dosis"] == 1


def test_14_medico_registra_atencion_sin_ver_libro(H):
    sa, med = H["superadmin"], H["medico"]
    n = entrada(sa)
    o = orden(sa, n["id"], procedimiento="Consulta retina")
    # Opciones del selector: solo procedimiento y fecha de ingreso
    r = requests.get(f"{API}/patients/{PAC1}/igss-ordenes-abiertas", headers=med)
    assert r.status_code == 200
    op = next(x for x in r.json() if x["id"] == o["id"])
    assert set(op) == {"id", "procedimiento", "fecha_ingreso", "motivo_sugerido"}
    assert op["procedimiento"] == "Consulta retina"
    ev = crear_eval(med, orden_id=o["id"])
    assert ev.get("aviso_igss") is None and "libro" not in ev
    texto = str(ev)
    assert o["no_sps"] not in texto and n["numero"] not in texto
    od = get_orden(sa, o["id"])
    assert od["estado"] == "atendida" and od["atenciones"][0]["ref_id"] == ev["id"]
    # El paciente que ve el médico no trae órdenes, No. SPS ni NOG
    pac = requests.get(f"{API}/patients/{PAC1}", headers=med).json()
    assert pac["igss_ordenes"] == [] and pac["igss_no_sps"] == "" and pac["igss_nog"] == ""
    pac_sa = requests.get(f"{API}/patients/{PAC1}", headers=sa).json()
    assert pac_sa["igss_ordenes"] and pac_sa["igss_no_sps"] == "LEG-1"


def test_15_roles_no_autorizados_no_modifican_ordenes_del_paciente(H):
    sa = H["superadmin"]
    cambios = {"comments": "TEST edición", "igss_no_sps": "HACK", "igss_nog": "HACK",
               "igss_ordenes": [{"nog": "HACK", "no_sps": "HACK-1", "codigo": "", "procedimiento": ""}]}
    for rol in DENEGADOS:
        r = requests.put(f"{API}/patients/{PAC2}", json=cambios, headers=H[rol])
        assert r.status_code in (200, 403), r.text
    p = _db_call(lambda db: db.patients.find_one({"id": PAC2}, {"_id": 0}))
    assert p["igss_no_sps"] == "LEG-2" and p["igss_nog"] == "LEGACY"
    assert [o["no_sps"] for o in p["igss_ordenes"]] == ["LEG-2"]
    # Alta de paciente por un médico: las órdenes enviadas se ignoran
    nuevo = {"first_name": f"TEST_LIBRO_NUEVO_{TAG}", "last_name": "Paciente", "gender": "masculino",
             "birth_date": "1980-05-05", "phone": "55559876", "referral_institution": "igss",
             "igss_unit_id": UNIT, "dpi": "9" * 13, "igss_no_sps": "HACK", "igss_nog": "HACK",
             "igss_ordenes": [{"nog": "HACK", "no_sps": "HACK-2"}]}
    r = requests.post(f"{API}/patients", json=nuevo, headers=H["medico"])
    assert r.status_code == 200, r.text
    creado = _db_call(lambda db: db.patients.find_one({"id": r.json()["id"]}, {"_id": 0}))
    assert creado["igss_ordenes"] == [] and creado["igss_no_sps"] == "" and creado["igss_nog"] == ""
    # Ningún rol sin acceso puede crear órdenes en el libro
    n = entrada(sa)
    for rol in DENEGADOS:
        assert nueva_orden(H[rol], n["id"], pac=PAC2).status_code == 403


def test_19_baja_cuantia_atendida_se_consume(H):
    sa = H["superadmin"]
    bc = entrada(sa, numero="", tipo_compra="baja_cuantia", nombre_servicio=f"Campimetría {TAG}", cantidad=None)
    o = orden(sa, bc["id"])
    crear_eval(sa, orden_id=o["id"])
    c = contador(sa, bc["id"])
    assert c["consumidos"] == 1 and c["reservados"] == 0
    lst = requests.get(f"{LIBRO}/ordenes", params={"nog_id": bc["id"], "estado": "atendida"}, headers=sa).json()
    assert lst["total"] == 1 and lst["data"][0]["modalidad"] == "Baja Cuantía"


def test_ninguna_y_asignacion_desde_sin_orden(H):
    sa, us = H["superadmin"], H["usuario"]
    n = entrada(sa)
    o = orden(sa, n["id"], pac=PAC2)
    # "Ninguna de estas" nunca vincula, aunque la evaluación traiga un No. SPS antiguo
    ev = crear_eval(sa, pac=PAC2, orden_id="ninguna", igss_no_sps=o["no_sps"])
    e = sin_orden_de(sa, ev["id"])
    assert e and e["tipo"] == "evaluacion" and "Ninguna" in e["motivo"]
    assert get_orden(sa, o["id"])["estado"] == "pendiente"
    assert requests.get(SIN_ORDEN, headers=us).status_code == 403
    assert requests.post(f"{SIN_ORDEN}/{e['id']}/asignar", json={"orden_id": o["id"]}, headers=us).status_code == 403
    r = requests.post(f"{SIN_ORDEN}/{e['id']}/asignar", json={"orden_id": o["id"]}, headers=sa)
    assert r.status_code == 200, r.text
    assert get_orden(sa, o["id"])["estado"] == "atendida"
    assert sin_orden_de(sa, ev["id"]) is None and sin_orden_de(sa, ev["id"], "resuelta")
    ev_db = _db_call(lambda db: db.evaluaciones_oftalmologicas.find_one({"id": ev["id"]}, {"_id": 0}))
    assert ev_db["igss_orden_id"] == o["id"]
    # Otra entrada: se descarta con motivo
    ev2 = crear_eval(sa, pac=PAC2, orden_id="ninguna", fecha="2026-11-11")
    e2 = sin_orden_de(sa, ev2["id"])
    r = requests.post(f"{SIN_ORDEN}/{e2['id']}/descartar", json={"motivo": "No es atención IGSS"}, headers=sa)
    assert r.status_code == 200 and r.json()["estado"] == "descartada"


def test_cirugia_sin_orden_con_interruptor_apagado(H):
    sa, us = H["superadmin"], H["usuario"]
    cx = crear_cx(us, no_sps=f"NOEXISTE-{TAG}")
    r = realizar(us, cx["id"])
    assert r.status_code == 200
    assert r.json().get("aviso_igss") and r.json().get("libro") is None
    e = sin_orden_de(sa, cx["id"])
    assert e and e["tipo"] == "cirugia" and f"NOEXISTE-{TAG}".upper() in e["motivo"]
    # Al crear después la orden en el libro se asigna desde la lista
    n = entrada(sa)
    o = orden(sa, n["id"], tipo="procedimiento", dosis_autorizadas=3)
    assert requests.post(f"{SIN_ORDEN}/{e['id']}/asignar", json={"orden_id": o["id"]}, headers=sa).status_code == 200
    od = get_orden(sa, o["id"])
    assert od["dosis_aplicadas"] == 1
    assert _db_call(lambda db: db.surgeries.find_one({"id": cx["id"]}, {"_id": 0}))["igss_orden_id"] == o["id"]
    # Una cirugía realizada no se puede cancelar sin desmarcarla
    r = requests.post(f"{CX_API}/{cx['id']}/cancel", json={"reason": "TEST"}, headers=sa)
    assert r.status_code == 400


def test_interruptor_solo_superadmin_y_exigencia(H):
    sa = H["superadmin"]
    for rol in ("admin", "administrador_igss", "usuario", "medico"):
        assert requests.put(f"{LIBRO}/config", json={"exigir_orden": True}, headers=H[rol]).status_code == 403
    for rol in AUTORIZADOS:
        r = requests.get(f"{LIBRO}/config", headers=H[rol])
        assert r.status_code == 200 and "atenciones_sin_orden_pendientes" in r.json()
    for rol in DENEGADOS:
        assert requests.get(f"{LIBRO}/config", headers=H[rol]).status_code == 403
    previa = crear_cx(sa, no_sps=f"PREVIA-{TAG}")
    r = requests.put(f"{LIBRO}/config", json={"exigir_orden": True}, headers=sa)
    assert r.status_code == 200 and r.json()["exigir_orden"] is True
    try:
        r = nueva_cx(sa, no_sps=f"NOEXISTE2-{TAG}")
        assert r.status_code == 422 and "no corresponde a una orden IGSS vigente" in r.json()["detail"]
        r = nueva_cx(sa, pac=None, no_sps=f"NOEXISTE2-{TAG}")
        assert r.status_code == 422 and "paciente registrado" in r.json()["detail"]
        # Las cirugías no IGSS no se afectan
        assert nueva_cx(sa, institution="Novavision", igss_data=None).status_code == 200
        # Una cirugía existente sin orden se puede seguir marcando realizada (queda sin orden)
        assert realizar(sa, previa["id"]).status_code == 200
        assert sin_orden_de(sa, previa["id"]) is not None
    finally:
        switch(sa, False)
    log = _db_call(lambda db: db.audit_logs.find_one({"action": "LIBRO_INTERRUPTOR_CAMBIADO", "details.despues": True},
                                                     sort=[("timestamp", -1)]))
    assert log and log["user_id"]


def test_reasignar_atencion_entre_ordenes(H):
    sa = H["superadmin"]
    n = entrada(sa)
    a, b = orden(sa, n["id"]), orden(sa, n["id"])
    otro = orden(sa, n["id"], pac=PAC2)
    ev = crear_eval(sa, orden_id=a["id"])
    body = {"tipo": "evaluacion", "ref_id": ev["id"], "orden_destino_id": otro["id"]}
    assert requests.post(f"{LIBRO}/atenciones/reasignar", json=body, headers=sa).status_code == 422
    body["orden_destino_id"] = b["id"]
    assert requests.post(f"{LIBRO}/atenciones/reasignar", json=body, headers=H["medico"]).status_code == 403
    r = requests.post(f"{LIBRO}/atenciones/reasignar", json=body, headers=sa)
    assert r.status_code == 200, r.text
    assert get_orden(sa, a["id"])["estado"] == "pendiente" and get_orden(sa, b["id"])["estado"] == "atendida"
    log = _db_call(lambda db: db.audit_logs.find_one({"action": "LIBRO_ATENCION_REASIGNADA", "details.ref_id": ev["id"]}))
    assert log and log["details"]["orden_anterior"] == a["id"]
    # Reasignar a "sin orden"
    body["orden_destino_id"] = None
    assert requests.post(f"{LIBRO}/atenciones/reasignar", json=body, headers=sa).status_code == 200
    assert get_orden(sa, b["id"])["estado"] == "pendiente" and sin_orden_de(sa, ev["id"]) is not None


def test_opciones_solo_ordenes_abiertas(H):
    sa = H["superadmin"]
    n = entrada(sa)
    abierta = orden(sa, n["id"], pac=PAC2, procedimiento="Abierta")
    anulada = orden(sa, n["id"], pac=PAC2, procedimiento="Anulada")
    requests.post(f"{LIBRO}/ordenes/{anulada['id']}/anular", json={"motivo": "prueba"}, headers=sa)
    completa = orden(sa, n["id"], pac=PAC2, tipo="procedimiento", dosis_autorizadas=1, procedimiento="Completa")
    cx = crear_cx(sa, pac=PAC2, no_sps=completa["no_sps"])
    realizar(sa, cx["id"])
    ids = [x["id"] for x in requests.get(f"{API}/patients/{PAC2}/igss-ordenes-abiertas", headers=H["usuario"]).json()]
    assert abierta["id"] in ids and anulada["id"] not in ids and completa["id"] not in ids


# ==================== FASE 3: LECTURAS DESDE EL LIBRO ====================

import io as _io
from openpyxl import load_workbook

UNITS_API = f"{API}/igss-units"


def nog_de(h, nog_id, unit=UNIT):
    r = requests.get(f"{UNITS_API}/{unit}/nogs", headers=h)
    assert r.status_code == 200, r.text
    return next(n for n in r.json()["nogs"] if n["id"] == nog_id), r.json()


def filas_hoja(ws):
    rows = list(ws.iter_rows(values_only=True))
    ini = next(i for i, r in enumerate(rows) if r[0] == "No. SPS")
    datos = []
    for r in rows[ini + 1:]:
        if r[0] in (None, ""):
            break
        datos.append(r)
    pie = {r[0]: r[1] for r in rows if r[0] in ("Total de órdenes", "Monto total (Q)")}
    return rows[ini], datos, pie


def excel(h, url, **params):
    r = requests.get(url, params=params, headers=h)
    assert r.status_code == 200, r.text
    return load_workbook(_io.BytesIO(r.content))


def test_fase3_contadores_cuentan_ordenes_no_dosis(H):
    sa = H["superadmin"]
    n = entrada(sa, cantidad=10)
    a = orden(sa, n["id"], tipo="procedimiento", dosis_autorizadas=3)
    for _ in range(3):
        assert realizar(sa, crear_cx(sa, no_sps=a["no_sps"])["id"]).status_code == 200
    b = orden(sa, n["id"], pac=PAC2)
    crear_eval(sa, pac=PAC2, orden_id=b["id"])
    crear_eval(sa, pac=PAC2, orden_id=b["id"], fecha="2026-11-21")
    orden(sa, n["id"])  # pendiente
    anulada = orden(sa, n["id"])
    requests.post(f"{LIBRO}/ordenes/{anulada['id']}/anular", json={"motivo": "prueba"}, headers=sa)
    d, _ = nog_de(sa, n["id"])
    assert (d["consumidos"], d["reservados"], d["usados"], d["disponibles"]) == (2, 1, 3, 7)
    todos = requests.get(f"{UNITS_API}/nogs/all", headers=sa).json()["data"]
    assert next(x for x in todos if x["id"] == n["id"])["consumidos"] == 2
    r = requests.get(f"{UNITS_API}/nogs/{n['id']}/pacientes", headers=sa)
    assert r.status_code == 200
    filas = r.json()["ordenes"]
    assert len(filas) == 3 and sorted(f["estado"] for f in filas) == ["atendida", "atendida", "pendiente"]
    fa = next(f for f in filas if f["orden_id"] == a["id"])
    assert (fa["dosis_aplicadas"], fa["dosis_autorizadas"], len(fa["fechas_dosis"])) == (3, 3, 3)
    assert contador(sa, n["id"])["consumidos"] == 2


def test_fase3_aviso_90_y_bloqueo_100(H):
    sa = H["superadmin"]
    n = entrada(sa, cantidad=10)
    for i in range(8):
        assert "aviso_cupo" not in orden(sa, n["id"])
    novena = orden(sa, n["id"])
    assert "9 de 10" in novena["aviso_cupo"]
    al = requests.get(f"{UNITS_API}/nogs/alertas", headers=sa).json()["alertas"]
    assert next(x for x in al if x["nog_id"] == n["id"])["estado"] == "por_completarse"
    orden(sa, n["id"])
    al = requests.get(f"{UNITS_API}/nogs/alertas", headers=sa).json()["alertas"]
    assert next(x for x in al if x["nog_id"] == n["id"])["estado"] == "completado"
    r = nueva_orden(sa, n["id"])
    assert r.status_code == 409 and "100 %" in r.json()["detail"]
    # Sin tope: nunca hay alerta
    bc = entrada(sa, numero="", tipo_compra="baja_cuantia", nombre_servicio=f"Sin tope {TAG}", cantidad=None)
    orden(sa, bc["id"])
    al = requests.get(f"{UNITS_API}/nogs/alertas", headers=sa).json()["alertas"]
    assert all(x["nog_id"] != bc["id"] for x in al)


def test_fase3_permisos_de_lecturas(H):
    sa = H["superadmin"]
    n = entrada(sa)
    urls = [f"{UNITS_API}/nogs/all", f"{UNITS_API}/nogs/resumen", f"{UNITS_API}/nogs/alertas",
            f"{UNITS_API}/{UNIT}/nogs", f"{UNITS_API}/nogs/{n['id']}/pacientes", f"{UNITS_API}/produccion",
            f"{UNITS_API}/produccion/reporte/excel", f"{UNITS_API}/nogs/{n['id']}/export/excel",
            f"{UNITS_API}/{UNIT}/nogs/export/excel"]
    for u in urls:
        for rol in AUTORIZADOS:
            assert requests.get(u, headers=H[rol]).status_code == 200, (u, rol)
        for rol in DENEGADOS:
            assert requests.get(u, headers=H[rol]).status_code == 403, (u, rol)
    # Selector nogs-activos: solo roles del libro (restringido 2026-11-17); los demás reciben 403
    for rol in DENEGADOS:
        assert requests.get(f"{UNITS_API}/{UNIT}/nogs-activos", headers=H[rol]).status_code == 403, rol
    full = requests.get(f"{UNITS_API}/{UNIT}/nogs-activos", headers=sa).json()
    assert "consumidos" in next(x for x in full if x["id"] == n["id"])


def _escenario_unidad2(sa):
    n = entrada(sa, unit=UNIT3, cantidad=5, precio=150)
    bc = entrada(sa, unit=UNIT3, numero="", tipo_compra="baja_cuantia", nombre_servicio=f"Campimetría U2 {TAG}",
                 cantidad=None, precio=80)
    c1 = orden(sa, n["id"], no_sps=f"B-{TAG}", procedimiento="Consulta U2")
    crear_eval(sa, orden_id=c1["id"], fecha="2026-08-05")
    crear_eval(sa, orden_id=c1["id"], fecha="2026-08-20")
    c2 = orden(sa, n["id"], no_sps=f"A-{TAG}", pac=PAC2)
    crear_eval(sa, pac=PAC2, orden_id=c2["id"], fecha="2026-08-05")
    p = orden(sa, n["id"], tipo="procedimiento", dosis_autorizadas=3, procedimiento="Avastin U2")
    for fecha in ("2026-08-12", "2026-09-15"):
        realizar(sa, crear_cx(sa, no_sps=p["no_sps"], date=fecha)["id"])
    orden(sa, n["id"])  # pendiente: no aparece
    an = orden(sa, n["id"])
    requests.post(f"{LIBRO}/ordenes/{an['id']}/anular", json={"motivo": "prueba"}, headers=sa)
    b = orden(sa, bc["id"], pac=PAC2)
    crear_eval(sa, pac=PAC2, orden_id=b["id"], fecha="2026-09-01")
    return n, bc, c1, c2, p, b


ESC = {}


def escenario(sa):
    if not ESC:
        ESC["v"] = _escenario_unidad2(sa)
    return ESC["v"]


def test_fase3_listado_oficial_unidad(H):
    sa = H["superadmin"]
    n, bc, c1, c2, p, b = escenario(sa)
    _db_call(lambda db: db.patients.update_one({"id": PAC2}, {"$set": {"is_active": False}}))
    try:
        wb = excel(sa, f"{UNITS_API}/{UNIT3}/nogs/export/excel")
    finally:
        _db_call(lambda db: db.patients.update_one({"id": PAC2}, {"$set": {"is_active": True}}))
    hoja_nog = f"NOG {n['numero']}"
    assert wb.sheetnames == ["Resumen", hoja_nog, "Baja Cuantía"]
    cab, filas, pie = filas_hoja(wb[hoja_nog])
    assert list(cab) == ["No. SPS", "Modalidad", "NOG", "Expediente", "Paciente", "Afiliación", "Código",
                         "Procedimiento", "Fecha 1ª atención", "Médico", "Dosis aplicadas / autorizadas",
                         "Fechas de cada dosis", "Precio (Q)", "Impreso", "Enviado", "Facturado", "Pagado"]
    # 1 fila por orden atendida == consumidos; orden: fecha de 1ª atención y luego No. SPS
    d, _ = nog_de(sa, n["id"], UNIT3)
    assert len(filas) == d["consumidos"] == 3 and pie["Total de órdenes"] == 3
    assert [f[0] for f in filas] == [c2["no_sps"], c1["no_sps"], p["no_sps"]]
    assert pie["Monto total (Q)"] == 450
    fp = filas[2]
    assert fp[10] == "2 / 3" and fp[11] == "12/08/2026, 15/09/2026" and fp[8] == "12/08/2026"
    f1 = filas[1]
    assert f1[10] == "1 / 1" and f1[11] == "05/08/2026" and f1[9] == "Dr. TEST Libro"
    assert filas[0][4] == "TEST_LIBRO Paciente 2"  # paciente inactivo incluido
    _, fb, pb = filas_hoja(wb["Baja Cuantía"])
    assert len(fb) == 1 and fb[0][1] == "Baja Cuantía" and fb[0][2].startswith("Baja cuantía —") and pb["Monto total (Q)"] == 80
    res = list(wb["Resumen"].iter_rows(values_only=True))
    fila_n = next(r for r in res if r[0] == n["numero"])
    assert fila_n[4] == 3 and fila_n[6] == 3 and fila_n[7] == 5 and fila_n[8] == "60.0 %"
    fila_b = next(r for r in res if str(r[0]).startswith("Baja cuantía"))
    assert fila_b[4] == 1 and fila_b[7] == "Sin tope"


def test_fase3_listado_oficial_filtro_fechas_y_un_nog(H):
    sa = H["superadmin"]
    n, bc, c1, c2, p, b = escenario(sa)
    # El filtro aplica sobre la fecha de la PRIMERA atención (seguimientos posteriores no cuentan)
    wb = excel(sa, f"{UNITS_API}/{UNIT3}/nogs/export/excel", desde="2026-08-10", hasta="2026-08-31")
    _, filas, _ = filas_hoja(wb[f"NOG {n['numero']}"])
    assert [f[0] for f in filas] == [p["no_sps"]]
    _, fb, _ = filas_hoja(wb["Baja Cuantía"])
    assert fb == []
    res = list(wb["Resumen"].iter_rows(values_only=True))
    fila_n = next(r for r in res if r[0] == n["numero"])
    assert fila_n[4] == 1 and fila_n[6] == 3  # periodo vs acumulado
    # Exportación de un solo NOG: mismo formato
    wb1 = excel(sa, f"{UNITS_API}/nogs/{n['id']}/export/excel")
    assert wb1.sheetnames == ["Resumen", f"NOG {n['numero']}"]
    assert len(filas_hoja(wb1[f"NOG {n['numero']}"])[1]) == 3
    assert requests.get(f"{UNITS_API}/{UNIT3}/nogs/export/excel", params={"desde": "2026-09-01", "hasta": "2026-08-01"},
                        headers=sa).status_code == 400


def test_fase3_produccion_y_dashboard_desde_libro(H):
    sa = H["superadmin"]
    n, bc, c1, c2, p, b = escenario(sa)
    q = {"desde": "2026-08-01", "hasta": "2026-09-30", "unidad_id": UNIT3}
    r = requests.get(f"{UNITS_API}/produccion", params=q, headers=sa)
    assert r.status_code == 200
    rows = r.json()["data"]
    assert sorted(x["orden_id"] for x in rows) == sorted([c1["id"], c2["id"], p["id"], b["id"]])
    assert r.json()["totales"]["servicios"] == 4
    # Los estados de facturación se guardan en la orden del libro
    assert requests.put(f"{LIBRO}/ordenes/{p['id']}", json={"pagado": True, "costo_override": 175}, headers=sa).status_code == 200
    tot = requests.get(f"{UNITS_API}/produccion", params=q, headers=sa).json()["totales"]
    assert tot["por_estado"]["pagado"] == {"cantidad": 1, "monto": 175.0}
    assert tot["total_costo"] == 150 + 150 + 175 + 80
    solo = requests.get(f"{UNITS_API}/produccion", params={**q, "nog": "campimetría u2"}, headers=sa).json()["data"]
    assert [x["orden_id"] for x in solo] == [b["id"]]
    dia = requests.get(f"{UNITS_API}/produccion", params={"fecha": "2026-08-05", "unidad_id": UNIT3}, headers=sa).json()
    assert dia["totales"]["servicios"] == 2
    # Dashboard: mismas órdenes que Producción (todas las unidades) en el mismo periodo
    dq = {"desde": "2026-08-01", "hasta": "2026-09-30"}
    dash = requests.get(f"{API}/dashboard/resumen-dia", params=dq, headers=sa).json()
    prod = requests.get(f"{UNITS_API}/produccion", params=dq, headers=sa).json()["totales"]
    assert dash["igss"]["servicios"] == dash["produccion_igss"]["servicios"] == prod["servicios"]
    assert dash["produccion_igss"]["total"] == prod["total_costo"]
