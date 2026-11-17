# Conciliación IGSS/NOG (solo lectura): detección de discrepancias D01-D15, invariancia
# de datos y control de acceso. Los documentos sembrados usan el prefijo TEST_ y se borran
# al terminar el módulo.
import os
import uuid
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from usuarios_prueba import par  # usuarios sembrados solo para pruebas

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"

TAG = uuid.uuid4().hex[:6]
UNIT_ID = f"TEST_unit_{TAG}"
N1 = f"TEST_nog1_{TAG}"      # NOG con contador inflado
N2 = f"TEST_nog2_{TAG}"      # NOG limpio
NUM1 = f"TESTN1{TAG}"
NUM2 = f"TESTN2{TAG}"
NUM_FANTASMA = f"TESTNX{TAG}"
EV_FANTASMA = f"TEST_eval_inexistente_{TAG}"
EV_PROD_FANTASMA = f"TEST_eval_prod_inexistente_{TAG}"
DPI_DUP = f"TESTDPI{TAG}"

COLECCIONES = ["igss_nogs", "igss_nog_acreditaciones", "patients",
               "evaluaciones_oftalmologicas", "igss_produccion", "surgeries", "igss_units"]


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


@pytest.fixture(scope="module")
def sa():
    return login(*par("superadmin"))


def _pac(pid, nombre, **kw):
    doc = {
        "id": pid, "record_number": f"TEST-{nombre}", "first_name": "TEST_PAC", "last_name": nombre,
        "referral_institution": "igss", "igss_unit_id": UNIT_ID, "is_active": True,
        "dpi": "", "igss_afiliacion": f"AF-{nombre}", "igss_ordenes": [],
    }
    doc.update(kw)
    return doc


def _acred(nog_id, numero, pac_id, sps, **kw):
    doc = {
        "id": f"TEST_acred_{uuid.uuid4().hex[:8]}", "nog_id": nog_id, "unidad_id": UNIT_ID,
        "numero_nog": numero, "paciente_id": pac_id, "paciente_expediente": "",
        "paciente_nombre": "", "evaluacion_id": "", "no_sps": sps,
        "fecha_acreditacion": "2026-06-01T12:00:00+00:00", "origen": "evaluacion", "anulada": False,
    }
    doc.update(kw)
    return doc


def _eval(ev_id, pac_id, numero, sps):
    return {
        "id": ev_id, "paciente_id": pac_id, "fecha": "2026-06-01",
        "medico_id": "TEST_med", "medico_nombre": "TEST Dra. QA",
        "motivo_consulta": "Control de conciliación QA",
        "igss_nog": numero, "igss_no_sps": sps, "igss_codigo": "QA", "igss_procedimiento": "QA proc",
        "fecha_creacion": "2026-06-01T12:00:00+00:00",
    }


@pytest.fixture(scope="module", autouse=True)
def seed(sa):
    async def ins(db):
        await db.igss_units.insert_one({"id": UNIT_ID, "name": f"TEST Unidad {TAG}", "is_active": True})
        await db.igss_nogs.insert_many([
            {"id": N1, "unidad_id": UNIT_ID, "numero": NUM1, "nombre_servicio": "TEST Servicio 1",
             "tipo_compra": "contrato", "cantidad": 20, "precio": 100.0, "acreditados": 9,
             "is_active": True},
            {"id": N2, "unidad_id": UNIT_ID, "numero": NUM2, "nombre_servicio": "TEST Servicio limpio",
             "tipo_compra": "contrato", "cantidad": 5, "precio": 50.0, "acreditados": 1,
             "is_active": True},
        ])
        await db.patients.insert_many([
            # D02 + D08: acreditación sin evaluación real y con evaluacion_id inexistente
            _pac("TEST_p1_" + TAG, "P1", igss_ordenes=[{"nog": NUM1, "no_sps": "SPS1"}]),
            # D03 + D14 + D15: evaluación real sin acreditación y sin SPS
            _pac("TEST_p2_" + TAG, "P2", igss_ordenes=[{"nog": NUM1, "no_sps": ""}]),
            # D05: dos acreditaciones vigentes para la misma terna
            _pac("TEST_p3_" + TAG, "P3", igss_ordenes=[{"nog": NUM1, "no_sps": "SPS3"}]),
            # D07: paciente inactivo con acreditación vigente
            _pac("TEST_p4_" + TAG, "P4", is_active=False, igss_ordenes=[{"nog": NUM1, "no_sps": "SPS4"}]),
            # D04: acreditación vigente sin No. SPS
            _pac("TEST_p5_" + TAG, "P5", igss_ordenes=[{"nog": NUM1, "no_sps": "SPS5"}]),
            # D11: NOG que no existe en el catálogo de la unidad
            _pac("TEST_p6_" + TAG, "P6", igss_ordenes=[{"nog": NUM_FANTASMA, "no_sps": "SPS6"}]),
            # D06: mismo No. SPS en dos pacientes
            _pac("TEST_p7_" + TAG, "P7", igss_ordenes=[{"nog": NUM1, "no_sps": "SPSDUP"}]),
            _pac("TEST_p8_" + TAG, "P8", igss_ordenes=[{"nog": NUM1, "no_sps": "SPSDUP"}]),
            # D09: cirugía IGSS sin acreditación
            _pac("TEST_p9_" + TAG, "P9", igss_ordenes=[{"nog": NUM1, "no_sps": "SPS9"}]),
            # D10: paciente IGSS con NOG/SPS pero sin unidad
            _pac("TEST_p10_" + TAG, "P10", igss_unit_id="", igss_nog=NUM1, igss_no_sps="SPS10"),
            # D12: mismo DPI en dos expedientes
            _pac("TEST_p11_" + TAG, "P11", dpi=DPI_DUP),
            _pac("TEST_p12_" + TAG, "P12", dpi=DPI_DUP),
            # NOG limpio: acreditada + atendida
            _pac("TEST_pc_" + TAG, "PC", igss_ordenes=[{"nog": NUM2, "no_sps": "SPSC"}]),
        ])
        await db.evaluaciones_oftalmologicas.insert_many([
            _eval(f"TEST_ev2_{TAG}", f"TEST_p2_{TAG}", NUM1, ""),
            _eval(f"TEST_evc_{TAG}", f"TEST_pc_{TAG}", NUM2, "SPSC"),
        ])
        await db.igss_nog_acreditaciones.insert_many([
            _acred(N1, NUM1, f"TEST_p1_{TAG}", "SPS1", evaluacion_id=EV_FANTASMA),
            _acred(N1, NUM1, f"TEST_p3_{TAG}", "SPS3"),
            _acred(N1, NUM1, f"TEST_p3_{TAG}", "SPS3"),
            _acred(N1, NUM1, f"TEST_p4_{TAG}", "SPS4"),
            _acred(N1, NUM1, f"TEST_p5_{TAG}", ""),
            _acred(N1, NUM1, f"TEST_p7_{TAG}", "SPSDUP"),
            _acred(N1, NUM1, f"TEST_p8_{TAG}", "SPSDUP"),
            _acred(N1, NUM1, f"TEST_p1_{TAG}", "ANULADA", anulada=True),
            _acred(N2, NUM2, f"TEST_pc_{TAG}", "SPSC", evaluacion_id=f"TEST_evc_{TAG}"),
        ])
        await db.surgeries.insert_one({
            "id": f"TEST_surg_{TAG}", "date": "2026-06-02", "patient_id": f"TEST_p9_{TAG}",
            "patient_name": "TEST_PAC P9", "procedure": "TEST cirugía", "institution": "IGSS",
            "status": "activo",
            "igss_data": {"unit_id": UNIT_ID, "nog_number": NUM1, "sps": "SPS9",
                          "procedure_cost": 250.0},
        })
        await db.igss_produccion.insert_one({"evaluacion_id": EV_PROD_FANTASMA, "impreso": False})

    _db_call(ins)
    yield

    async def clean(db):
        await db.igss_units.delete_many({"id": UNIT_ID})
        await db.igss_nogs.delete_many({"id": {"$in": [N1, N2]}})
        await db.igss_nog_acreditaciones.delete_many({"unidad_id": UNIT_ID})
        await db.patients.delete_many({"id": {"$regex": f"^TEST_p.*_{TAG}$"}})
        await db.evaluaciones_oftalmologicas.delete_many({"id": {"$regex": f"^TEST_ev.*_{TAG}$"}})
        await db.surgeries.delete_many({"id": f"TEST_surg_{TAG}"})
        await db.igss_produccion.delete_many({"evaluacion_id": EV_PROD_FANTASMA})
    _db_call(clean)


@pytest.fixture(scope="module")
def reporte_unidad(sa):
    r = requests.get(f"{API}/igss-units/conciliacion", headers=sa, params={"unidad_id": UNIT_ID})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def reporte_global(sa):
    r = requests.get(f"{API}/igss-units/conciliacion", headers=sa)
    assert r.status_code == 200, r.text
    return r.json()


def _tipos(reporte, **filtros):
    """Tipos de discrepancia presentes para las filas que cumplen los filtros."""
    out = set()
    for d in reporte["discrepancias"]:
        if all(str(d.get(k, "")) == v or v in str(d.get("ids", {})) for k, v in filtros.items()):
            out.add(d["tipo"])
    return out


def _de_paciente(reporte, pac_id, tipo=None):
    res = [d for d in reporte["discrepancias"] if pac_id in str(d.get("ids", {}))]
    if tipo:
        res = [d for d in res if d["tipo"] == tipo]
    return res


# ---------- 1. Solo lectura ----------
class TestSoloLectura:
    def test_no_modifica_datos(self, sa):
        async def snapshot(db):
            counts = {c: await db[c].count_documents({}) for c in COLECCIONES}
            nogs = {n["id"]: n.get("acreditados") async for n in db.igss_nogs.find({}, {"id": 1, "acreditados": 1})}
            audits = await db.audit_logs.count_documents({"action": "CONCILIACION_IGSS_GENERADA"})
            return counts, nogs, audits

        antes_counts, antes_nogs, antes_audit = _db_call(snapshot)

        r1 = requests.get(f"{API}/igss-units/conciliacion", headers=sa)
        assert r1.status_code == 200, r1.text
        r2 = requests.get(f"{API}/igss-units/conciliacion/export/excel", headers=sa)
        assert r2.status_code == 200, r2.text
        assert r2.content[:2] == b"PK"

        despues_counts, despues_nogs, despues_audit = _db_call(snapshot)
        assert despues_counts == antes_counts
        assert despues_nogs == antes_nogs
        assert despues_audit == antes_audit + 2  # única escritura permitida


# ---------- 2. Un caso sembrado por cada tipo ----------
class TestDiscrepancias:
    def test_d01_contador_distinto(self, reporte_unidad):
        fila = next(f for f in reporte_unidad["resumen_por_nog"] if f["nog_id"] == N1)
        assert fila["contador_guardado"] == 9
        assert fila["acreditaciones_vigentes"] == 7
        assert fila["diferencia_contador"] == 2
        assert fila["acreditaciones_anuladas"] == 1
        assert any(d["tipo"] == "D01" and d["ids"].get("nog_id") == N1
                   for d in reporte_unidad["discrepancias"])

    def test_d02_acreditacion_sin_evaluacion(self, reporte_unidad):
        assert _de_paciente(reporte_unidad, f"TEST_p1_{TAG}", "D02")

    def test_d03_evaluacion_sin_acreditacion(self, reporte_unidad):
        d = _de_paciente(reporte_unidad, f"TEST_p2_{TAG}", "D03")
        assert d and "Causa probable" in d[0]["descripcion"]

    def test_d04_acreditacion_sin_sps(self, reporte_unidad):
        assert _de_paciente(reporte_unidad, f"TEST_p5_{TAG}", "D04")
        fila = next(f for f in reporte_unidad["resumen_por_nog"] if f["nog_id"] == N1)
        assert fila["vigentes_sin_sps"] == 1

    def test_d05_acreditaciones_duplicadas(self, reporte_unidad):
        assert _de_paciente(reporte_unidad, f"TEST_p3_{TAG}", "D05")

    def test_d06_sps_repetido(self, reporte_unidad):
        d = [x for x in reporte_unidad["discrepancias"]
             if x["tipo"] == "D06" and x["no_sps"] == "SPSDUP"]
        assert len(d) >= 2

    def test_d07_paciente_inactivo(self, reporte_unidad):
        assert _de_paciente(reporte_unidad, f"TEST_p4_{TAG}", "D07")
        fila = next(f for f in reporte_unidad["resumen_por_nog"] if f["nog_id"] == N1)
        assert fila["vigentes_paciente_inactivo_o_inexistente"] == 1

    def test_d08_evaluacion_inexistente(self, reporte_unidad):
        d = [x for x in reporte_unidad["discrepancias"]
             if x["tipo"] == "D08" and x["ids"].get("evaluacion_id") == EV_FANTASMA]
        assert d

    def test_d09_cirugia_sin_acreditacion(self, reporte_unidad):
        d = [x for x in reporte_unidad["discrepancias"]
             if x["tipo"] == "D09" and x["ids"].get("surgery_id") == f"TEST_surg_{TAG}"]
        assert d
        fila = next(f for f in reporte_unidad["resumen_por_nog"] if f["nog_id"] == N1)
        assert fila["cirugias_igss"] == 1
        assert fila["cirugias_igss_monto"] == 250.0

    def test_d10_paciente_sin_unidad(self, reporte_global):
        assert _de_paciente(reporte_global, f"TEST_p10_{TAG}", "D10")

    def test_d11_nog_fuera_de_catalogo(self, reporte_unidad):
        assert _de_paciente(reporte_unidad, f"TEST_p6_{TAG}", "D11")

    def test_d12_pacientes_duplicados(self, reporte_global):
        d = [x for x in reporte_global["discrepancias"]
             if x["tipo"] == "D12" and DPI_DUP.upper() in x["descripcion"].upper()]
        assert len(d) == 2

    def test_d13_produccion_huerfana(self, reporte_global):
        d = [x for x in reporte_global["discrepancias"]
             if x["tipo"] == "D13" and x["ids"].get("evaluacion_id") == EV_PROD_FANTASMA]
        assert d

    def test_d14_evaluacion_sin_sps(self, reporte_unidad):
        assert _de_paciente(reporte_unidad, f"TEST_p2_{TAG}", "D14")

    def test_d15_orden_sin_sps(self, reporte_unidad):
        assert _de_paciente(reporte_unidad, f"TEST_p2_{TAG}", "D15")

    def test_conteo_por_tipo_completo(self, reporte_unidad):
        esperados = {f"D{str(i).zfill(2)}" for i in range(1, 16)}
        assert esperados.issubset(set(reporte_unidad["conteo_por_tipo"].keys()))


# ---------- 3. NOG limpio ----------
class TestNogLimpio:
    def test_sin_discrepancias_y_estado_ok(self, reporte_unidad):
        fila = next(f for f in reporte_unidad["resumen_por_nog"] if f["nog_id"] == N2)
        assert fila["contador_guardado"] == 1
        assert fila["acreditaciones_vigentes"] == 1
        assert fila["autorizaciones_con_evaluacion_real"] == 1
        assert fila["diferencia_contador"] == 0
        assert fila["diferencia_atendidos"] == 0
        assert not [d for d in reporte_unidad["discrepancias"] if d["nog"] == NUM2]
        fila_cotejo = next(c for c in reporte_unidad["cotejo"]
                           if c["paciente_id"] == f"TEST_pc_{TAG}")
        assert fila_cotejo["estado_sugerido"] == "OK"
        assert fila_cotejo["acreditada"] is True
        assert fila_cotejo["evaluacion_real"] is True
        assert fila_cotejo["en_ordenes"] is True
        assert fila_cotejo["verificado_hoja_sps"] == ""
        assert fila_cotejo["observaciones"] == ""

    def test_estados_sugeridos_de_los_casos(self, reporte_unidad):
        por_pac = {c["paciente_id"]: c for c in reporte_unidad["cotejo"]}
        assert por_pac[f"TEST_p2_{TAG}"]["estado_sugerido"] == "ATENDIDO_SIN_CONTAR"
        assert por_pac[f"TEST_p1_{TAG}"]["estado_sugerido"] == "REVISAR"  # D08


# ---------- 4. Control de acceso ----------
class TestAcceso:
    def test_rol_sin_permiso_403(self):
        h = login(*par("usuario"))
        r = requests.get(f"{API}/igss-units/conciliacion", headers=h)
        assert r.status_code == 403
        r2 = requests.get(f"{API}/igss-units/conciliacion/export/excel", headers=h)
        assert r2.status_code == 403

    def test_administrador_igss_puede(self):
        h = login(*par("igss"))
        r = requests.get(f"{API}/igss-units/conciliacion", headers=h, params={"unidad_id": UNIT_ID})
        assert r.status_code == 200, r.text
        assert "resumen_por_nog" in r.json()
