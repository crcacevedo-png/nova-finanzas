# Correlación venta ↔ cuenta por cobrar: número de orden en listados, detalle con la venta
# de origen, búsqueda por número de orden y vinculación/desvinculación manual.
import os
import uuid
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"

TAG = uuid.uuid4().hex[:6]
CUENTA_SIN_VENTA = f"TEST_cxc_sin_{TAG}"
CUENTA_CON_VENTA = f"TEST_cxc_con_{TAG}"
VENTA_OK = f"TEST_venta_ok_{TAG}"
VENTA_OTRA = f"TEST_venta_otra_{TAG}"
VENTA_ANULADA = f"TEST_venta_anul_{TAG}"
NUM_VENTA_OK = f"VTA-TEST{TAG}-0001"
NUM_VENTA_OTRA = f"VTA-TEST{TAG}-0002"
NUM_VENTA_ANULADA = f"VTA-TEST{TAG}-0003"
ORDEN_OPTICA = f"TEST_ord_opt_{TAG}"
ORDEN_CANCELADA = f"TEST_ord_canc_{TAG}"
NUM_ORDEN_OPTICA = f"ORD-TEST{TAG}-0001"
NUM_ORDEN_CANCELADA = f"ORD-TEST{TAG}-0002"
CUENTA_OPTICA = f"TEST_cxc_opt_{TAG}"


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
    return login("superadmin", "nova2024")


def _venta(vid, numero, total, credito, estado="completada"):
    formas = []
    if credito:
        formas.append({"metodo": "Cuenta por Cobrar", "monto": credito})
    if total - credito > 0:
        formas.append({"metodo": "Efectivo", "monto": total - credito})
    return {
        "id": vid, "numero_venta": numero, "fecha": "2026-06-10T15:00:00+00:00",
        "paciente_id": "TEST_pac", "paciente_nombre": f"TEST Paciente {TAG}",
        "vendedor_nombre": "TEST Vendedor", "medico_nombre": "TEST Dra. QA",
        "bodega_nombre": "TEST Bodega",
        "items": [
            {"codigo": "TST-1", "nombre": "TEST Armazón", "cantidad": 1,
             "precio_unitario": total - 50, "descuento": 0.0, "subtotal": total - 50},
            {"codigo": "TST-2", "nombre": "TEST Consulta", "cantidad": 1,
             "precio_unitario": 50, "descuento": 0.0, "subtotal": 50},
        ],
        "cantidad_items": 2, "subtotal": total, "descuento_total": 0.0, "iva": 0.0,
        "total": total, "formas_pago": formas, "estado": estado, "origen": "clinica",
    }


def _orden_optica(oid, numero, total, credito, status="pendiente"):
    return {
        "id": oid, "order_number": numero, "created_at": "2026-06-12T15:00:00+00:00",
        "patient_id": "TEST_pac", "patient_name": f"TEST Paciente {TAG}",
        "doctor_name": "TEST Dra. QA", "created_by_name": "TEST Vendedor Óptica",
        "items_v2": [{"type": "frame", "product_id": "TEST_frame", "name": "TEST Armazón Óptica",
                      "quantity": 1, "unit_price": total, "subtotal": total}],
        "subtotal": total, "discount_amount": 0.0, "iva": 0.0, "total": total,
        "total_paid": total - credito, "balance_due": credito, "monto_cxc": credito,
        "payment_method": "efectivo", "status": status, "tiene_cxc": credito > 0,
    }


def _cuenta(cid, numero, venta_id):
    return {
        "id": cid, "origen": "clinica", "numero_cuenta": numero,
        "paciente_id": "TEST_pac", "paciente_nombre": f"TEST Paciente {TAG}",
        "responsable_id": "TEST_resp", "responsable_nombre": "TEST Responsable",
        "tipo_responsable": "medico", "venta_id": venta_id,
        "monto_total": 300.0, "monto_pagado": 100.0, "saldo_pendiente": 200.0,
        "concepto": f"TEST concepto {TAG}", "estado": "Parcial",
        "fecha_emision": "2026-06-10T15:00:00+00:00", "fecha_vencimiento": None,
        "pagos": [{"id": "TEST_pago", "monto": 100.0, "metodo_pago": "Efectivo",
                   "fecha": "2026-06-11T15:00:00+00:00", "registrado_por_nombre": "QA"}],
    }


@pytest.fixture(scope="module", autouse=True)
def seed():
    async def ins(db):
        await db.ventas.insert_many([
            _venta(VENTA_OK, NUM_VENTA_OK, 300.0, 300.0),
            _venta(VENTA_OTRA, NUM_VENTA_OTRA, 500.0, 200.0),
            _venta(VENTA_ANULADA, NUM_VENTA_ANULADA, 100.0, 100.0, estado="anulada"),
        ])
        await db.optica_sales.insert_many([
            _orden_optica(ORDEN_OPTICA, NUM_ORDEN_OPTICA, 500.0, 400.0),
            _orden_optica(ORDEN_CANCELADA, NUM_ORDEN_CANCELADA, 200.0, 200.0, status="cancelado"),
        ])
        await db.cuentas_por_cobrar.insert_many([
            _cuenta(CUENTA_SIN_VENTA, f"CXC-TEST-{TAG}-0001", None),
            _cuenta(CUENTA_CON_VENTA, f"CXC-TEST-{TAG}-0002", VENTA_OTRA),
            {**_cuenta(CUENTA_OPTICA, f"CXC-TEST-{TAG}-0003", None),
             "origen": "optica", "monto_total": 500.0, "monto_pagado": 100.0,
             "saldo_pendiente": 400.0, "concepto": f"TEST concepto optica {TAG}"},
        ])
    _db_call(ins)
    yield

    async def clean(db):
        await db.ventas.delete_many({"id": {"$in": [VENTA_OK, VENTA_OTRA, VENTA_ANULADA]}})
        await db.optica_sales.delete_many({"id": {"$in": [ORDEN_OPTICA, ORDEN_CANCELADA]}})
        await db.cuentas_por_cobrar.delete_many(
            {"id": {"$in": [CUENTA_SIN_VENTA, CUENTA_CON_VENTA, CUENTA_OPTICA]}})
    _db_call(clean)


def _get_cuenta(sa, cuenta_id):
    r = requests.get(f"{API}/cuentas-cobrar/{cuenta_id}", headers=sa)
    assert r.status_code == 200, r.text
    return r.json()


class TestOrigenVisible:
    def test_listado_incluye_numero_de_orden(self, sa):
        r = requests.get(f"{API}/cuentas-cobrar/clinica", headers=sa,
                         params={"search": f"TEST concepto {TAG}"})
        assert r.status_code == 200, r.text
        filas = {c["numero_cuenta"]: c for c in r.json()["data"]}
        assert filas[f"CXC-TEST-{TAG}-0002"]["venta_numero"] == NUM_VENTA_OTRA
        assert filas[f"CXC-TEST-{TAG}-0001"]["venta_numero"] == ""

    def test_busqueda_por_numero_de_orden(self, sa):
        r = requests.get(f"{API}/cuentas-cobrar/clinica", headers=sa,
                         params={"search": NUM_VENTA_OTRA})
        assert r.status_code == 200, r.text
        ids = [c["id"] for c in r.json()["data"]]
        assert CUENTA_CON_VENTA in ids

    def test_detalle_trae_venta_de_origen(self, sa):
        c = _get_cuenta(sa, CUENTA_CON_VENTA)
        v = c["venta"]
        assert v["numero_venta"] == NUM_VENTA_OTRA
        assert v["total"] == 500.0
        assert v["monto_credito"] == 200.0
        assert v["monto_en_caja"] == 300.0
        assert len(v["items"]) == 2
        assert v["vendedor_nombre"] == "TEST Vendedor"

    def test_detalle_sin_venta(self, sa):
        c = _get_cuenta(sa, CUENTA_SIN_VENTA)
        assert c["venta"] is None
        assert c["venta_numero"] == ""


class TestBuscadorDeVentas:
    def test_busca_por_numero(self, sa):
        r = requests.get(f"{API}/cuentas-cobrar/ventas/buscar", headers=sa,
                         params={"search": f"VTA-TEST{TAG}"})
        assert r.status_code == 200, r.text
        numeros = {v["numero_venta"]: v for v in r.json()["data"]}
        assert NUM_VENTA_OK in numeros and NUM_VENTA_OTRA in numeros
        assert NUM_VENTA_ANULADA not in numeros  # no se ofrecen ventas anuladas
        assert numeros[NUM_VENTA_OTRA]["cuentas_vinculadas"][0]["numero_cuenta"] == f"CXC-TEST-{TAG}-0002"
        assert numeros[NUM_VENTA_OK]["cuentas_vinculadas"] == []

    def test_busca_por_paciente(self, sa):
        r = requests.get(f"{API}/cuentas-cobrar/ventas/buscar", headers=sa,
                         params={"search": f"TEST Paciente {TAG}"})
        assert r.status_code == 200
        assert len(r.json()["data"]) >= 2


class TestVinculacion:
    def test_vincular_no_altera_montos(self, sa):
        antes = _get_cuenta(sa, CUENTA_SIN_VENTA)
        r = requests.put(f"{API}/cuentas-cobrar/{CUENTA_SIN_VENTA}/venta", headers=sa,
                         json={"venta_id": VENTA_OK})
        assert r.status_code == 200, r.text
        assert r.json()["advertencias"] == []
        despues = _get_cuenta(sa, CUENTA_SIN_VENTA)
        assert despues["venta"]["numero_venta"] == NUM_VENTA_OK
        assert despues["venta_vinculada_por_nombre"]
        for campo in ("monto_total", "monto_pagado", "saldo_pendiente", "estado"):
            assert despues[campo] == antes[campo]
        assert len(despues["pagos"]) == len(antes["pagos"])

    def test_venta_anulada_rechazada(self, sa):
        r = requests.put(f"{API}/cuentas-cobrar/{CUENTA_SIN_VENTA}/venta", headers=sa,
                         json={"venta_id": VENTA_ANULADA})
        assert r.status_code == 400
        assert "anulada" in r.json()["detail"].lower()

    def test_venta_ya_vinculada_pide_confirmacion(self, sa):
        r = requests.put(f"{API}/cuentas-cobrar/{CUENTA_SIN_VENTA}/venta", headers=sa,
                         json={"venta_id": VENTA_OTRA})
        assert r.status_code == 409, r.text
        assert f"CXC-TEST-{TAG}-0002" in r.json()["detail"]

    def test_confirmar_vinculo_duplicado_avisa_monto(self, sa):
        r = requests.put(f"{API}/cuentas-cobrar/{CUENTA_SIN_VENTA}/venta", headers=sa,
                         json={"venta_id": VENTA_OTRA, "confirmar": True})
        assert r.status_code == 200, r.text
        avisos = " ".join(r.json()["advertencias"])
        assert "también está vinculada" in avisos
        assert "no coincide" in avisos  # crédito 200 vs cuenta 300

    def test_desvincular_no_altera_montos(self, sa):
        antes = _get_cuenta(sa, CUENTA_SIN_VENTA)
        r = requests.delete(f"{API}/cuentas-cobrar/{CUENTA_SIN_VENTA}/venta", headers=sa)
        assert r.status_code == 200, r.text
        despues = _get_cuenta(sa, CUENTA_SIN_VENTA)
        assert despues["venta"] is None
        assert despues["venta_desvinculada_por_nombre"]
        for campo in ("monto_total", "monto_pagado", "saldo_pendiente", "estado"):
            assert despues[campo] == antes[campo]

    def test_desvincular_sin_venta_400(self, sa):
        r = requests.delete(f"{API}/cuentas-cobrar/{CUENTA_SIN_VENTA}/venta", headers=sa)
        assert r.status_code == 400

    def test_venta_inexistente_404(self, sa):
        r = requests.put(f"{API}/cuentas-cobrar/{CUENTA_SIN_VENTA}/venta", headers=sa,
                         json={"venta_id": "no-existe"})
        assert r.status_code == 404


class TestOpticaOrigen:
    """Las cuentas de Óptica se vinculan a órdenes de óptica (optica_sales)."""

    def test_buscar_ordenes_optica(self, sa):
        r = requests.get(f"{API}/cuentas-cobrar/ventas/buscar", headers=sa,
                         params={"search": NUM_ORDEN_OPTICA, "origen": "optica"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert len(data) == 1
        assert data[0]["numero_venta"] == NUM_ORDEN_OPTICA
        assert data[0]["origen"] == "optica"
        assert data[0]["monto_credito"] == 400.0
        assert data[0]["items"][0]["nombre"] == "TEST Armazón Óptica"

    def test_vincular_orden_optica(self, sa):
        r = requests.put(f"{API}/cuentas-cobrar/{CUENTA_OPTICA}/venta", headers=sa,
                         json={"venta_id": ORDEN_OPTICA})
        assert r.status_code == 200, r.text
        c = _get_cuenta(sa, CUENTA_OPTICA)
        assert c["venta"]["numero_venta"] == NUM_ORDEN_OPTICA
        assert c["venta"]["monto_en_caja"] == 100.0
        assert c["monto_total"] == 500.0 and c["saldo_pendiente"] == 400.0

    def test_listado_optica_muestra_orden(self, sa):
        r = requests.get(f"{API}/cuentas-cobrar/optica", headers=sa,
                         params={"search": f"TEST concepto optica {TAG}"})
        assert r.status_code == 200, r.text
        filas = {c["id"]: c for c in r.json()["data"]}
        assert filas[CUENTA_OPTICA]["venta_numero"] == NUM_ORDEN_OPTICA

    def test_orden_optica_cancelada_rechazada(self, sa):
        r = requests.put(f"{API}/cuentas-cobrar/{CUENTA_OPTICA}/venta", headers=sa,
                         json={"venta_id": ORDEN_CANCELADA})
        assert r.status_code == 400

    def test_pos_optica_guarda_venta_origen_id(self, sa):
        """El POS de Óptica envía venta_origen_id: debe quedar como venta vinculada."""
        r = requests.post(f"{API}/cuentas-cobrar/optica", headers=sa, json={
            "paciente_id": "TEST_pac", "paciente_nombre": f"TEST Paciente {TAG}",
            "monto_total": 400.0, "concepto": f"TEST pos optica {TAG}",
            "venta_origen_id": ORDEN_OPTICA, "venta_origen_tipo": "optica_sale",
        })
        assert r.status_code == 200, r.text
        creada = r.json()
        assert creada["venta_id"] == ORDEN_OPTICA
        detalle = _get_cuenta(sa, creada["id"])
        assert detalle["venta"]["numero_venta"] == NUM_ORDEN_OPTICA
        _db_call(lambda db: db.cuentas_por_cobrar.delete_one({"id": creada["id"]}))


class TestAcceso:
    def test_rol_sin_permiso_no_vincula(self):
        h = login("medico_test", "medico2024")
        r = requests.put(f"{API}/cuentas-cobrar/{CUENTA_CON_VENTA}/venta", headers=h,
                         json={"venta_id": VENTA_OK})
        assert r.status_code == 403
        r2 = requests.get(f"{API}/cuentas-cobrar/ventas/buscar", headers=h)
        assert r2.status_code == 403

    def test_usuario_con_abonos_si_vincula(self):
        h = login("usuario", "user2024")
        r = requests.get(f"{API}/cuentas-cobrar/ventas/buscar", headers=h,
                         params={"search": NUM_VENTA_OK})
        assert r.status_code == 200, r.text
