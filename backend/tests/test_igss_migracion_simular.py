# Libro IGSS — Fase 4 paso (a): simulación de migración (solo lectura, solo superadmin).
# Clasificación de órdenes, no migrables, pendientes de SPS, historial ignorado; unidades
# duplicadas (advertencia) y mismo No. SPS en dos unidades duplicadas (bloqueo); filtro por
# unidad; reubicación del par duplicado; Excel de 6 hojas; invariancia total de datos (dbHash). Prefijo TEST_, se borra al final.
import asyncio
import io
import os
import uuid

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from openpyxl import load_workbook

from usuarios_prueba import par  # usuarios sembrados solo para pruebas

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
SIM = f"{API}/igss-units/migracion/simular"

TAG = uuid.uuid4().hex[:6]
U, DU1, DU2, U2, DA1, DA2 = (f"TEST_mig_{k}_{TAG}" for k in ("unit", "dup1", "dup2", "u2", "da1", "da2"))
UNIDADES = [U, DU1, DU2, U2, DA1, DA2]
N1, N2, NBC, N3, ND1, ND2, N4, ND3, NA1, NA2 = (f"TEST_mig_{k}_{TAG}" for k in (
    "n1", "n2", "bc", "n3", "nd1", "nd2", "n4", "nd3", "na1", "na2"))
NUM1, NUM2, NUM3, NUMD = f"TMIG1{TAG}", f"TMIG2{TAG}", f"TMIG3{TAG}", f"TMIGD{TAG}"
NUM4, NUMD2, NUMA = f"TMIG4{TAG}", f"TMIGE{TAG}", f"TMIGA{TAG}"
P = {k: f"TEST_mig_p{k}_{TAG}" for k in range(1, 20)}
SPS = {k: f"{ord(k)}-{int(TAG, 16)}" for k in "ABCDEFGHIJKLXYZ"}  # solo números y guiones
LIBRO_ID, LEG1 = f"TEST_mig_libro_{TAG}", f"TEST_mig_leg1_{TAG}"
COLECCIONES = ["igss_nogs", "igss_nog_acreditaciones", "igss_produccion", "igss_ordenes_libro", "igss_atenciones_sin_orden",
               "patients", "evaluaciones_oftalmologicas", "surgeries", "igss_units", "audit_logs", "igss_libro_config"]


def _db_call(fn):
    async def runner():
        client = AsyncIOMotorClient(os.environ['MONGO_URL'])
        try:
            return await fn(client[os.environ['DB_NAME']])
        finally:
            client.close()
    return asyncio.run(runner())


def _login(clave):
    u, p = par(clave)
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _nog(nid, numero, unidad=U, **kw):
    return {"id": nid, "unidad_id": unidad, "numero": numero, "nombre_servicio": kw.pop("servicio", "Consulta"),
            "nombre_servicio_norm": "consulta", "tipo_compra": "contrato", "cantidad": 10, "precio": 100.0,
            "acreditados": 0, "is_active": True, "fecha_asignacion": "", "sin_tope": False, **kw}


def _pac(k, ordenes=None, unidad=U, **kw):
    return {"id": P[k], "record_number": f"TEST-MIG-{k}-{TAG}", "first_name": "TEST_MIG", "last_name": f"P{k}",
            "referral_institution": "igss", "igss_unit_id": unidad, "is_active": True, "igss_afiliacion": f"AF{k}",
            "igss_ordenes": ordenes or [], "created_at": "2025-01-01T12:00:00+00:00", **kw}


def _ord(nog, sps, oid=None, proc=""):
    return {"id": oid or str(uuid.uuid4()), "nog": nog, "no_sps": sps, "codigo": "", "procedimiento": proc}


def _ev(k, pid, fecha, **kw):
    return {"id": f"TEST_mig_ev{k}_{TAG}", "paciente_id": pid, "fecha": fecha, "medico_nombre": "Dr. Test",
            "motivo_consulta": "Control", **kw}


def _acr(k, pid, nog_id, sps, fecha, unidad=U, **kw):
    return {"id": f"TEST_mig_acr{k}_{TAG}", "nog_id": nog_id, "unidad_id": unidad, "paciente_id": pid, "no_sps": sps,
            "fecha_acreditacion": fecha, "origen": "asignacion", "anulada": False, **kw}


def _cx(k, pid, fecha, sps, status="realizado", nog_id=N1):
    return {"id": f"TEST_mig_cx{k}_{TAG}", "patient_id": pid, "patient_name": "TEST_MIG", "date": fecha,
            "status": status, "institution": "IGSS", "procedure": "Catarata", "surgeon": "Dr. Cx",
            "igss_data": {"unit_id": U, "nog_id": nog_id, "sps": sps}}


@pytest.fixture(scope="module", autouse=True)
def seed():
    async def ins(db):
        await db.igss_units.insert_many([
            {"id": U, "name": f"TEST_MIG Unidad {TAG}", "is_active": True, "created_at": "2025-01-01T00:00:00+00:00"},
            {"id": DU1, "name": f"TEST_MIG Duplicada {TAG}", "is_active": False, "created_at": "2026-01-01T00:00:00+00:00"},
            {"id": DU2, "name": f"TEST_MIG  duplicada  {TAG}", "is_active": True, "created_at": "2026-02-01T00:00:00+00:00"},
            {"id": U2, "name": f"TEST_MIG Fechas {TAG}", "is_active": True, "created_at": "2025-01-01T00:00:00+00:00"},
            # Mismo nombre solo al quitar tildes: advertencia, pero NO se reubica (solo espacios y mayúsculas)
            {"id": DA1, "name": f"TEST_MIG Clínica {TAG}", "is_active": False, "created_at": "2026-01-01T00:00:00+00:00"},
            {"id": DA2, "name": f"TEST_MIG Clinica {TAG}", "is_active": True, "created_at": "2026-02-01T00:00:00+00:00"}])
        await db.igss_nogs.insert_many([
            _nog(N1, NUM1, fecha_asignacion="2026-01-01"), _nog(N2, NUM2, cantidad=5),
            _nog(NBC, "", servicio="Servicio BC", tipo_compra="baja_cuantia", sin_tope=True, fecha_asignacion="2026-01-01"),
            _nog(N3, NUM3, is_active=False, cantidad=1, fecha_asignacion="2025-01-01"),
            _nog(ND1, NUMD, unidad=DU1, fecha_asignacion="2026-01-01"), _nog(ND2, NUMD, unidad=DU2, fecha_asignacion="2026-01-01"),
            _nog(N4, NUM4, unidad=U2, created_at="2026-06-01T12:00:00+00:00"),
            _nog(ND3, NUMD2, unidad=DU1, fecha_asignacion="2026-01-01"),
            _nog(NA1, NUMA, unidad=DA1, fecha_asignacion="2026-01-01"), _nog(NA2, NUMA, unidad=DA2, fecha_asignacion="2026-01-01")])
        await db.patients.insert_many([
            _pac(1, [_ord(NUM1, SPS["A"], LEG1)]), _pac(2, [_ord(NUM2, SPS["B"])]),
            _pac(3, [_ord("BAJA CUANTIA", SPS["C"], proc="Servicio BC")]), _pac(4, [_ord("NOEXISTE99", SPS["D"])]),
            _pac(5, [_ord(NUM1, SPS["E"])]), _pac(6, [_ord(NUM1, SPS["E"])]), _pac(7, [_ord(NUM1, "")]),
            _pac(8, created_at="2026-01-01T12:00:00+00:00"), _pac(9), _pac(10),
            _pac(11, [_ord(NUMD, SPS["X"])], unidad=DU1), _pac(12, [_ord(NUMD, SPS["X"])], unidad=DU2),
            _pac(13, [_ord(NUMD, SPS["Y"])], unidad=DU2), _pac(14, [_ord(NUMD, SPS["Z"])], unidad=DU1),
            _pac(15, [_ord(NUM4, SPS["I"])], unidad=U2), _pac(16, [_ord(NUM4, SPS["J"])], unidad=U2),
            _pac(17, [_ord(NUMD2, SPS["K"])], unidad=DU1), _pac(19, [_ord(NUMA, SPS["L"])], unidad=DA1)])
        await db.igss_nog_acreditaciones.insert_many([
            _acr(1, P[1], N1, SPS["A"], "2026-02-01T15:00:00+00:00"),
            _acr(7, P[7], N1, "", "2026-02-10T15:00:00+00:00"),
            _acr(8, P[8], N2, "", "2026-04-01T15:00:00+00:00", anulada=True),
            # Mismo patrón que producción: orden en una unidad y acreditación en el NOG de su duplicada
            _acr(14, P[14], ND2, SPS["Z"], "2026-03-01T15:00:00+00:00", unidad=DU2),
            _acr(15, P[15], N4, "", "2026-05-01T15:00:00+00:00", unidad=U2),
            # Cupo en la activa y orden en la inactiva con un NOG que la activa no tiene: no se migra
            _acr(17, P[17], ND2, SPS["K"], "2026-03-01T15:00:00+00:00", unidad=DU2),
            _acr(19, P[19], NA2, SPS["L"], "2026-03-01T15:00:00+00:00", unidad=DA2)])
        await db.evaluaciones_oftalmologicas.insert_many([
            _ev("1a", P[1], "2025-12-15", igss_no_sps=SPS["A"]), _ev("1b", P[1], "2026-03-01", igss_orden_id=LEG1),
            _ev("2", P[2], "2025-06-01", igss_nog=NUM2), _ev("3", P[3], "2026-04-01", igss_no_sps=SPS["C"]),
            _ev("4", P[4], "2026-05-01", igss_no_sps=SPS["D"]), _ev("7a", P[7], "2025-11-01"),
            _ev("7b", P[7], "2026-06-01"), _ev("8", P[8], "2026-03-15"),
            _ev("10", P[10], "2026-09-01", igss_no_sps=SPS["H"]),
            _ev("15", P[15], "2026-04-15", igss_no_sps=SPS["I"]), _ev("16", P[16], "2026-01-10", igss_no_sps=SPS["J"])])
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
        await db.igss_units.delete_many({"id": {"$in": UNIDADES}})
        await db.igss_nogs.delete_many({"unidad_id": {"$in": UNIDADES}})
        await db.patients.delete_many({"id": {"$in": list(P.values())}})
        await db.igss_nog_acreditaciones.delete_many({"id": {"$regex": f"^TEST_mig_acr.*_{TAG}$"}})
        await db.evaluaciones_oftalmologicas.delete_many({"id": {"$regex": f"^TEST_mig_ev.*_{TAG}$"}})
        await db.igss_produccion.delete_many({"evaluacion_id": {"$regex": f"^TEST_mig_ev.*_{TAG}$"}})
        await db.surgeries.delete_many({"id": {"$regex": f"^TEST_mig_cx.*_{TAG}$"}})
        await db.igss_ordenes_libro.delete_many({"id": LIBRO_ID})
    _db_call(clean)


def _huella():
    async def h(db):
        r = await db.command({"dbHash": 1, "collections": COLECCIONES})
        return {c: r["collections"].get(c) for c in COLECCIONES}
    return _db_call(h)


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin")


@pytest.fixture(scope="module")
def sim(sa):
    antes = _huella()
    r = requests.get(SIM, headers=sa, timeout=180)
    assert r.status_code == 200, r.text
    ru = requests.get(SIM, params={"unidad_id": U}, headers=sa, timeout=180)
    rd = requests.get(SIM, params={"unidad_id": DU1}, headers=sa, timeout=180)
    x1 = requests.get(f"{SIM}/excel", params={"unidad_id": U}, headers=sa, timeout=180)
    x2 = requests.get(f"{SIM}/excel", params={"unidad_id": U}, headers=sa, timeout=180)
    for resp in (ru, rd, x1, x2):
        assert resp.status_code == 200, resp.text
    return {"todo": r.json(), "u": ru.json(), "dup": rd.json(), "excel": x1.content, "excel2": x2.content,
            "antes": antes, "despues": _huella()}


def _orden(data, sps):
    return next((o for o in data["ordenes"] if o["no_sps"] == sps), None)


def test_solo_lectura_invariancia_total(sim):
    assert sim["antes"] == sim["despues"], "La simulación o el Excel modificaron datos"
    assert sim["u"]["solo_lectura"] is True


def test_totales_de_la_unidad(sim):
    t = sim["u"]["totales"]
    assert (t["ordenes_a_migrar"], t["consumidas"], t["pendientes"]) == (4, 4, 0)
    assert (t["no_migrables"], t["pendientes_sps"], t["no_se_migra"]) == (3, 3, 6)
    assert t["evaluaciones_anteriores_al_contrato"] == 2 and t["evaluaciones_sin_unidad_igss_en_la_fecha"] == 1
    assert t["evaluaciones_historicas_ignoradas"] == 3
    assert t["ordenes_ya_en_libro_con_atenciones_nuevas"] == 1
    assert sum(m["casos"] for m in sim["u"]["por_motivo"]) == t["no_se_migra"]
    assert {a["anio"]: a["ordenes"] for a in sim["u"]["por_anio"]} == {"2025": 1, "2026": 3}
    assert sim["u"]["por_unidad"] == [{"unidad_id": U, "unidad": f"TEST_MIG Unidad {TAG}", "a_migrar": 4, "consumidas": 4,
                                       "pendientes": 0, "no_migrables": 3, "pendientes_sps": 3}]


def test_orden_con_fecha_asignacion_excluye_anteriores(sim):
    o = _orden(sim["u"], SPS["A"])
    assert o and o["estado"] == "atendida" and o["nog_id"] == N1 and o["igss_afiliacion"] == "AF1"
    assert o["evaluaciones"] == 1 and o["excluidas_anteriores"] == 1
    assert o["fecha_primera_atencion"] == "2026-03-01" and o["fecha_referencia"] == "2026-01-01"
    assert o["fecha_ingreso"] == "2026-02-01" and o["revisar_fecha"] is False
    assert set(o["origen"]) == {"orden del paciente", "acreditación", "evaluación"}


def test_sin_fechas_incluye_todo_y_marca_revisar(sim):
    o = _orden(sim["u"], SPS["B"])
    assert o and o["nog_id"] == N2 and o["estado"] == "atendida"
    assert o["revisar_fecha"] is True and o["fecha_primera_atencion"] == "2025-06-01"
    assert "Revisar fecha: sin ninguna fecha de referencia" in o["observaciones"]


def test_fecha_de_respaldo_no_excluye_y_marca_solo_mas_de_90_dias(sim):
    i, j = _orden(sim["todo"], SPS["I"]), _orden(sim["todo"], SPS["J"])
    # Respaldo = la más antigua entre la acreditación del mismo paciente y entrada y el registro de la entrada
    assert i["fecha_referencia"] == "2026-05-01" and i["fuente_referencia"] == "Acreditación de la orden"
    assert i["evaluaciones"] == 1 and i["excluidas_anteriores"] == 0 and i["revisar_fecha"] is False
    assert not any(x.startswith("Revisar fecha") for x in i["observaciones"])
    assert j["fecha_referencia"] == "2026-06-01" and j["fuente_referencia"] == "Registro de la entrada del catálogo"
    assert j["evaluaciones"] == 1 and j["excluidas_anteriores"] == 0 and j["revisar_fecha"] is True
    assert "Revisar fecha: 1 atención(es) de más de 90 días antes del 01/06/2026" in j["observaciones"]


def test_baja_cuantia_y_procedimiento(sim):
    c = _orden(sim["u"], SPS["C"])
    assert c and c["nog_id"] == NBC and c["modalidad"] == "Baja Cuantía" and c["pagado"] is True and c["costo_override"] == 75.0
    f = _orden(sim["u"], SPS["F"])
    assert f and f["tipo"] == "procedimiento" and f["dosis_autorizadas"] == 2 and f["fechas_atenciones"] == ["2026-07-01", "2026-08-01"]
    assert _orden(sim["u"], SPS["G"]) is None


def test_no_migrables_motivo_falta_y_orden(sim):
    nm = sim["u"]["no_migrables"]
    assert [x["motivo_agrupado"] for x in nm] == ["Orden sin No. SPS", "NOG no está en el catálogo de la unidad",
                                                  "No. SPS en varios pacientes"]  # por unidad y luego fecha (vacía al final)
    assert nm[0]["fecha"] == "2026-02-10" and nm[0]["expediente"] == f"TEST-MIG-7-{TAG}" and nm[0]["falta"]
    assert nm[1]["no_sps"] == SPS["D"] and nm[1]["atenciones"] == 1 and "Registrar el NOG" in nm[1]["falta"]
    assert nm[2]["no_sps"] == SPS["E"] and nm[2]["expediente"].count("TEST-MIG") == 2
    for sps in (SPS["D"], SPS["E"]):
        assert _orden(sim["u"], sps) is None


def test_pendientes_de_sps(sim):
    ps = {i["ref_id"]: i for i in sim["u"]["pendientes_sps"]}
    assert set(ps) == {f"TEST_mig_acr7_{TAG}", f"TEST_mig_ev7b_{TAG}", f"TEST_mig_cx4_{TAG}"}
    assert ps[f"TEST_mig_acr7_{TAG}"]["etiqueta"] == "Cupo descontado sin SPS" and ps[f"TEST_mig_acr7_{TAG}"]["nog_id"] == N1
    assert ps[f"TEST_mig_ev7b_{TAG}"]["etiqueta"] == "Evaluación sin No. SPS"
    assert ps[f"TEST_mig_cx4_{TAG}"]["etiqueta"] == "Cirugía sin No. SPS"


def test_ya_en_el_libro(sim):
    o = next(x for x in sim["u"]["ya_en_libro"] if x["orden_id"] == LIBRO_ID)
    assert o["evaluaciones_a_agregar"] == 1 and o["estado_resultante"] == "atendida"
    assert _orden(sim["u"], SPS["H"]) is None


def test_resumen_por_nog(sim):
    r = {f["nog_id"]: f for f in sim["u"]["resumen_nog"]}
    assert set(r) == {N1, N2, NBC, N3}
    n1 = r[N1]
    assert (n1["a_migrar"], n1["consumidas"], n1["pendientes"], n1["pendientes_sps"]) == (2, 2, 0, 2)
    assert (n1["contador_actual"], n1["acreditaciones_vigentes"]) == (0, 2)
    assert r[N2]["acreditaciones_vigentes"] == 0 and r[NBC]["sin_tope"] is True


def test_unidades_duplicadas_advertencia_y_bloqueo_por_sps(sim):
    todo = sim["todo"]
    adv = next(a for a in todo["advertencias"] if {u["unidad_id"] for u in a["unidades"]} == {DU1, DU2})
    assert [u["unidad_id"] for u in adv["unidades"]] == [DU1, DU2]  # la más antigua primero
    # Par reubicable (solo difiere en espacios y mayúsculas): ya no bloquea
    assert not [b for b in todo["bloqueos"] if set(b["unidades_ids"]) == {DU1, DU2}]
    # Par que solo coincide al quitar tildes: no se reubica y el mismo No. SPS sigue bloqueando
    bloq = {b["no_sps"]: b for b in todo["bloqueos"] if set(b["unidades_ids"]) == {DA1, DA2}}
    assert set(bloq) == {SPS["L"]} and {u["unidad_id"] for u in bloq[SPS["L"]]["usos"]} == {DA1, DA2}
    assert todo["aplicacion_permitida"] is False
    assert sim["dup"]["bloqueos"] == [] and sim["dup"]["totales"]["unidades_duplicadas"] == 1
    assert all(o["unidad_id"] == DU1 for o in sim["dup"]["ordenes"])


def test_reubicacion_en_la_unidad_activa(sim):
    todo = sim["todo"]
    r = {f["no_sps"]: f for f in todo["reubicadas"] if f["unidad_origen_id"] == DU1}
    assert set(r) == {SPS["X"], SPS["Z"], SPS["K"]}  # Y y L no se reubican
    assert all(f["unidad_destino_id"] == DU2 for f in r.values())
    # Mismo paciente, cupo en la activa y orden en la inactiva: una sola orden en la activa
    z = _orden(todo, SPS["Z"])
    assert z["unidad_id"] == DU2 and z["nog_id"] == ND2 and z["paciente_id"] == P[14]
    assert r[SPS["Z"]]["resultado"] == "Se migra en la unidad activa"
    assert r[SPS["Z"]]["cupo_origen"].startswith(f"{NUMD} — sin cupo descontado")
    assert r[SPS["Z"]]["cupo_destino"].startswith(f"{NUMD} — cupo descontado")
    # Dos pacientes distintos con el mismo No. SPS: no se inventa a quién pertenece
    assert r[SPS["X"]]["resultado"].startswith("No se migra: El No. SPS") and _orden(todo, SPS["X"]) is None
    # El NOG de la hoja no existe en la unidad activa: ese caso no se migra
    assert r[SPS["K"]]["resultado"] == f"No se migra: Reubicación: el NOG {NUMD2} no existe en la unidad activa"
    nm = next(x for x in todo["no_migrables"] if x["no_sps"] == SPS["K"])
    assert nm["unidad_id"] == DU1 and nm["motivo_agrupado"] == "NOG no existe en la unidad activa (reubicación)"
    assert _orden(todo, SPS["K"])["unidad_id"] == DU2  # el cupo de la activa sí migra
    assert {f["no_sps"] for f in sim["dup"]["reubicadas"]} == set(r) and todo["totales"]["ordenes_reubicadas"] >= 3
    assert sim["u"]["bloqueos"] == [] and sim["u"]["advertencias"] == [] and sim["u"]["aplicacion_permitida"] is False


def test_excel_siete_hojas(sim):
    for contenido in (sim["excel"], sim["excel2"]):
        wb = load_workbook(io.BytesIO(contenido))
        assert wb.sheetnames == ["Resumen", "Por NOG", "Órdenes", "No migrables", "Pendientes de SPS", "Órdenes reubicadas",
                                 "Patrones de No. SPS"]
    wb = load_workbook(io.BytesIO(sim["excel"]))
    cab = {h: [c.value for c in wb[h][1]] for h in wb.sheetnames[1:]}
    assert cab["Por NOG"][-3:-1] == ["Contador actual (acreditados)", "Acreditaciones vigentes hoy"]
    assert cab["Órdenes"][:12] == ["Unidad", "Modalidad", "NOG", "No. SPS", "Expediente", "Paciente", "Afiliación",
                                   "Procedimiento", "Fecha 1ª atención", "Estado propuesto", "Dosis autorizadas", "Origen"]
    assert cab["Órdenes reubicadas"] == ["Unidad de origen", "Unidad de destino", "NOG", "No. SPS", "Expediente", "Paciente",
                                         "Cupo en la unidad de origen", "Cupo en la unidad de destino", "Resultado"]
    for h in ("No migrables", "Pendientes de SPS"):
        assert cab[h][-2:] == ["No. SPS correcto", "Revisado por"]
        filas = list(wb[h].iter_rows(min_row=2, values_only=True))
        assert filas and all(f[-1] is None and f[-2] is None for f in filas)
    assert {row[3] for row in wb["Órdenes"].iter_rows(min_row=2, values_only=True)} == {SPS[k] for k in "ABCF"}
    assert [row[1] or "" for row in wb["No migrables"].iter_rows(min_row=2, values_only=True)] == ["10/02/2026", "01/05/2026", ""]
    resumen = [row[0] for row in wb["Resumen"].iter_rows(values_only=True) if row and row[0]]
    assert "Total que NO se migra" in resumen and "Año de primera atención" in resumen
    assert "Motivo de no migración" in resumen
    assert any(x.startswith("  · anteriores a la primera actividad IGSS del paciente") for x in resumen)
    assert not any("sin unidad IGSS en esa fecha" in str(x) for x in resumen)


def test_detalle_false_y_unidad_inexistente(sa):
    r = requests.get(SIM, params={"unidad_id": U, "detalle": "false"}, headers=sa, timeout=180)
    assert r.status_code == 200 and "ordenes" not in r.json() and r.json()["totales"]["ordenes_a_migrar"] == 4
    assert requests.get(SIM, params={"unidad_id": "no-existe"}, headers=sa, timeout=180).status_code == 404


@pytest.mark.parametrize("rol", ["admin", "igss", "usuario"])
def test_solo_superadmin(rol):
    h = _login(rol)
    assert requests.get(SIM, headers=h, timeout=60).status_code == 403
    assert requests.get(f"{SIM}/excel", headers=h, timeout=60).status_code == 403
