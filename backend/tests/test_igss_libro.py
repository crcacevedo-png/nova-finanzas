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

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
LIBRO = f"{API}/igss-units/libro"

TAG = uuid.uuid4().hex[:6]
UNIT = f"TEST_libro_u1_{TAG}"
UNIT2 = f"TEST_libro_u2_{TAG}"
PAC1 = f"TEST_libro_p1_{TAG}"
PAC2 = f"TEST_libro_p2_{TAG}"
CREDS = {
    "superadmin": ("superadmin", "nova2024"),
    "admin": ("admin", "Admin2024$"),
    "administrador_igss": ("igss.admin", "IgssAdmin2024$"),
    "usuario": ("usuario", "user2024"),
    "medico": ("medico_test", "medico2024"),
}
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
        ])
        await db.patients.insert_many([
            {"id": pid, "record_number": f"TEST-LIB-{i}-{TAG}", "first_name": "TEST_LIBRO", "last_name": f"Paciente {i}",
             "referral_institution": "igss", "igss_unit_id": UNIT, "is_active": True, "igss_afiliacion": f"AF-{i}",
             "igss_ordenes": []}
            for i, pid in ((1, PAC1), (2, PAC2))
        ])
    _db_call(ins)
    yield

    async def clean(db):
        units = [UNIT, UNIT2]
        nog_ids = await db.igss_nogs.distinct("id", {"unidad_id": {"$in": units}})
        orden_ids = await db.igss_ordenes_libro.distinct("id", {"unidad_id": {"$in": units}})
        await db.igss_ordenes_libro.delete_many({"unidad_id": {"$in": units}})
        await db.igss_nog_acreditaciones.delete_many({"nog_id": {"$in": nog_ids}})
        await db.igss_nogs.delete_many({"unidad_id": {"$in": units}})
        await db.patients.delete_many({"id": {"$in": [PAC1, PAC2]}})
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
