# NOG Fase 1: consumo de cupo por AUTORIZACIÓN (No. SPS) y listado de producción agrupado por autorización.
# Todos los datos se crean en una UNIDAD/NOG de PRUEBA (TEST_) y se limpian al final.
import os
import random
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"
mongo = MongoClient("mongodb://localhost:27017")["test_database"]
D1, D2, D3 = "2025-11-10", "2025-11-12", "2025-11-14"
RANGE = {"desde": "2025-11-01", "hasta": "2025-11-30"}


def _login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    d = r.json()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {d.get('access_token') or d.get('token')}"})
    return s


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin", "nova2024")


@pytest.fixture(scope="module")
def ia():
    return _login("igss.admin", "IgssAdmin2024$")


@pytest.fixture(scope="module")
def env(sa):
    tag = uuid.uuid4().hex[:6]
    r = sa.post(f"{API}/igss-units", json={"name": f"TEST_Unidad_SPS_{tag}", "code": f"T{tag}"})
    assert r.status_code == 200, r.text
    uid = r.json()["id"]
    nogs = {}
    for key, cant in (("main", 50), ("cap", 2), ("aviso", 10)):
        rn = sa.post(f"{API}/igss-units/{uid}/nogs", json={
            "numero": f"TEST-{key}-{tag}", "nombre_servicio": "TEST", "cantidad": cant, "precio": 100})
        assert rn.status_code == 200, rn.text
        nogs[key] = rn.json()
    data = {"uid": uid, "nogs": nogs, "patients": [], "evals": []}
    yield data
    for eid in data["evals"]:
        mongo.evaluaciones_oftalmologicas.delete_one({"id": eid})
        mongo.igss_produccion.delete_many({"evaluacion_id": eid})
    for pid in data["patients"]:
        mongo.patients.delete_one({"id": pid})
        mongo.igss_nog_acreditaciones.delete_many({"paciente_id": pid})
    for n in nogs.values():
        mongo.igss_nog_acreditaciones.delete_many({"nog_id": n["id"]})
        mongo.igss_nogs.delete_one({"id": n["id"]})
    mongo.igss_units.delete_one({"id": uid})


def _nog(env, key, client):
    r = client.get(f"{API}/igss-units/{env['uid']}/nogs")
    assert r.status_code == 200, r.text
    return next(n for n in r.json()["nogs"] if n["id"] == env["nogs"][key]["id"])


def _patient(sa, env, ordenes):
    p = {"first_name": "TEST_SPS", "last_name": f"Pac{random.randint(1000, 9999)}",
         "dpi": str(random.randint(10**12, 10**13 - 1)), "birth_date": "1980-01-01",
         "gender": "masculino", "phone": "55551234", "referral_institution": "igss",
         "igss_unit_id": env["uid"], "igss_ordenes": ordenes}
    r = sa.post(f"{API}/patients", json=p)
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]
    env["patients"].append(pid)
    return r.json()


def _eval(sa, env, pid, fecha, nog_num, sps):
    body = {"paciente_id": pid, "fecha": fecha, "motivo_consulta": "TEST consulta",
            "igss_nog": nog_num, "igss_no_sps": sps}
    r = sa.post(f"{API}/evaluaciones-oftalmologicas", json=body)
    if r.status_code == 404:
        r = sa.post(f"{API}/evaluaciones", json=body)
    assert r.status_code in (200, 201), r.text
    env["evals"].append(r.json()["id"])
    return r.json()


def _prod(sa, env, params=None):
    r = sa.get(f"{API}/igss-units/produccion", params={**(params or RANGE), "unidad_id": env["uid"]})
    assert r.status_code == 200, r.text
    return r.json()["data"]


class TestAutorizacion:
    # Dos órdenes mismo NOG, SPS distintos => 2 cupos
    def test_two_sps_two_cupos(self, sa, env):
        num = env["nogs"]["main"]["numero"]
        before = _nog(env, "main", sa)["acreditados"]
        p = _patient(sa, env, [{"nog": num, "no_sps": "SPS-A1"}, {"nog": num, "no_sps": "SPS-A2"}])
        env["pA"] = p["id"]
        after = _nog(env, "main", sa)["acreditados"]
        assert after - before == 2
        acr = sa.get(f"{API}/igss-units/nogs/{env['nogs']['main']['id']}/pacientes").json()["acreditaciones"]
        mine = [a for a in acr if a["paciente_id"] == p["id"]]
        assert len(mine) == 2
        vig = list(mongo.igss_nog_acreditaciones.find({"paciente_id": p["id"], "anulada": {"$ne": True}}))
        assert sorted(a["no_sps"] for a in vig) == ["SPS-A1", "SPS-A2"]

    # Evaluaciones bajo los SPS existentes no descuentan
    def test_evals_existing_sps_no_extra(self, sa, env):
        num = env["nogs"]["main"]["numero"]
        before = _nog(env, "main", sa)["acreditados"]
        _eval(sa, env, env["pA"], D2, num, "SPS-A1")
        _eval(sa, env, env["pA"], D1, num, "SPS-A1")  # creada después pero fecha anterior
        _eval(sa, env, env["pA"], D3, num, "SPS-A2")
        assert _nog(env, "main", sa)["acreditados"] == before

    # 1 SPS + varias evaluaciones => 1 cupo
    def test_one_sps_many_evals(self, sa, env):
        num = env["nogs"]["main"]["numero"]
        before = _nog(env, "main", sa)["acreditados"]
        p = _patient(sa, env, [{"nog": num, "no_sps": "SPS-B1"}])
        env["pB"] = p["id"]
        for f in (D3, D1, D2):
            _eval(sa, env, p["id"], f, num, "SPS-B1")
        assert _nog(env, "main", sa)["acreditados"] - before == 1

    # Sin SPS => 1 cupo por paciente (legado)
    def test_no_sps_legacy(self, sa, env):
        num = env["nogs"]["main"]["numero"]
        before = _nog(env, "main", sa)["acreditados"]
        p = _patient(sa, env, [{"nog": num, "no_sps": "", "codigo": "C1"}])
        env["pC"] = p["id"]
        _eval(sa, env, p["id"], D1, num, "")
        _eval(sa, env, p["id"], D2, num, "")
        assert _nog(env, "main", sa)["acreditados"] - before == 1

    # Evaluación con nueva autorización (SPS no presente en órdenes) => descuenta
    def test_eval_new_sps_discounts(self, sa, env):
        num = env["nogs"]["main"]["numero"]
        before = _nog(env, "main", sa)["acreditados"]
        _eval(sa, env, env["pB"], D2, num, "SPS-B2")
        assert _nog(env, "main", sa)["acreditados"] - before == 1
        _eval(sa, env, env["pB"], D3, num, "SPS-B2")
        assert _nog(env, "main", sa)["acreditados"] - before == 1

    # Paciente sin SPS: una evaluación con SPS no descuenta (acreditación legada actúa como comodín)
    def test_legacy_wildcard_blocks(self, sa, env):
        num = env["nogs"]["main"]["numero"]
        before = _nog(env, "main", sa)["acreditados"]
        _eval(sa, env, env["pC"], D3, num, "SPS-C9")
        assert _nog(env, "main", sa)["acreditados"] == before

    # PUT paciente: idempotente; quitar/añadir SPS libera/descuenta
    def test_put_reconcile(self, sa, env):
        num = env["nogs"]["main"]["numero"]
        before = _nog(env, "main", sa)["acreditados"]
        r = sa.put(f"{API}/patients/{env['pA']}", json={"igss_ordenes": [
            {"nog": num, "no_sps": "SPS-A1"}, {"nog": num, "no_sps": "SPS-A2"}]})
        assert r.status_code == 200, r.text
        assert _nog(env, "main", sa)["acreditados"] == before
        r = sa.put(f"{API}/patients/{env['pA']}", json={"igss_ordenes": [
            {"nog": num, "no_sps": "SPS-A1"}, {"nog": num, "no_sps": "SPS-A2"}, {"nog": num, "no_sps": "SPS-A3"}]})
        assert r.status_code == 200
        assert _nog(env, "main", sa)["acreditados"] == before + 1
        r = sa.put(f"{API}/patients/{env['pA']}", json={"igss_ordenes": [
            {"nog": num, "no_sps": "SPS-A1"}, {"nog": num, "no_sps": "SPS-A2"}]})
        assert _nog(env, "main", sa)["acreditados"] == before

    # Contador del NOG coincide con acreditaciones vigentes
    def test_counter_consistency(self, sa, env):
        n = _nog(env, "main", sa)
        vig = mongo.igss_nog_acreditaciones.count_documents({"nog_id": n["id"], "anulada": {"$ne": True}})
        assert n["acreditados"] == vig


class TestCupo:
    # Bloqueo al 100%: 3 SPS distintos en NOG de cantidad 2 => acreditados 2 (completado)
    def test_cap_block(self, sa, env):
        num = env["nogs"]["cap"]["numero"]
        p = _patient(sa, env, [{"nog": num, "no_sps": f"SPS-K{i}"} for i in range(3)])
        n = _nog(env, "cap", sa)
        assert n["acreditados"] == 2 and n["estado"] == "completado" and n["disponibles"] == 0
        _eval(sa, env, p["id"], D1, num, "SPS-K9")
        assert _nog(env, "cap", sa)["acreditados"] == 2

    # Aviso 90%: 9 SPS distintos en NOG de cantidad 10 => por_completarse y aparece en alertas
    def test_aviso_90(self, sa, env, ia):
        num = env["nogs"]["aviso"]["numero"]
        _patient(sa, env, [{"nog": num, "no_sps": f"SPS-W{i}"} for i in range(9)])
        n = _nog(env, "aviso", sa)
        assert n["acreditados"] == 9 and n["estado"] == "por_completarse"
        al = ia.get(f"{API}/igss-units/nogs/alertas").json()["alertas"]
        ids = {a["nog_id"]: a["estado"] for a in al}
        assert ids.get(env["nogs"]["aviso"]["id"]) == "por_completarse"
        assert ids.get(env["nogs"]["cap"]["id"]) == "completado"


class TestProduccion:
    # Una fila por autorización; fecha = primera consulta
    def test_rows_by_authorization(self, sa, env):
        rows = _prod(sa, env)
        a = [r for r in rows if r["paciente_id"] == env["pA"]]
        assert sorted(r["no_sps"] for r in a) == ["SPS-A1", "SPS-A2"], a
        a1 = next(r for r in a if r["no_sps"] == "SPS-A1")
        assert a1["fecha"] == D1
        b = [r for r in rows if r["paciente_id"] == env["pB"]]
        assert sorted(r["no_sps"] for r in b) == ["SPS-B1", "SPS-B2"]
        assert next(r for r in b if r["no_sps"] == "SPS-B1")["fecha"] == D1
        assert next(r for r in b if r["no_sps"] == "SPS-B2")["fecha"] == D2

    # Sin SPS: una fila por paciente/NOG
    def test_rows_no_sps(self, sa, env):
        rows = [r for r in _prod(sa, env) if r["paciente_id"] == env["pC"]]
        # pC: 2 evals sin SPS (1 fila) + 1 eval con SPS-C9 (sin descuento)
        no_sps_rows = [r for r in rows if not r["no_sps"]]
        assert len(no_sps_rows) == 1 and no_sps_rows[0]["fecha"] == D1

    # Producción no debe mostrar filas de autorizaciones que no descontaron cupo (SPS-C9 bloqueado)
    def test_row_without_cupo_not_listed(self, sa, env):
        rows = [r for r in _prod(sa, env) if r["paciente_id"] == env["pC"]]
        assert not any(r["no_sps"] == "SPS-C9" for r in rows), rows

    # Filtro por día: consulta de seguimiento (mismo SPS) no debe crear una nueva línea en otro día
    def test_followup_day_not_new_row(self, sa, env):
        rows = [r for r in _prod(sa, env, {"fecha": D2}) if r["paciente_id"] == env["pB"] and r["no_sps"] == "SPS-B1"]
        assert rows == [], f"seguimiento del {D2} aparece como fila nueva: {rows}"

    # Acceso admin IGSS
    def test_igss_admin_access(self, ia, env):
        assert ia.get(f"{API}/igss-units/produccion", params={**RANGE, "unidad_id": env["uid"]}).status_code == 200
        r = ia.get(f"{API}/igss-units/nogs/all")
        assert r.status_code == 200
        assert any(n["id"] == env["nogs"]["main"]["id"] for n in r.json()["data"])


class TestEdicionPaciente:
    # Editar un dato no-IGSS del paciente no debe liberar cupo de una autorización acreditada por evaluación
    def test_put_phone_keeps_eval_sps(self, sa, env):
        before = _nog(env, "main", sa)["acreditados"]
        r = sa.put(f"{API}/patients/{env['pB']}", json={"phone": "55559999"})
        assert r.status_code == 200, r.text
        after = _nog(env, "main", sa)["acreditados"]
        assert after == before, f"PUT phone cambió acreditados {before}->{after} (SPS-B2 anulada por reconciliación)"
