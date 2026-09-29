"""Verificación independiente iter59: POS anti-sobreventa + numero_venta único.

Tres pruebas:
 1. Sin lotes: existencia=3, 6 ventas concurrentes => 3 OK / 3 400 / existencia=0.
 2. Con lotes/FEFO: lote=2, 5 ventas concurrentes => 2 OK / 3 400 / lote=0 / existencia=0.
 3. numero_venta único bajo concurrencia (formato VTA-YYYYMMDD-####).
"""
import os
import uuid
import re
import pytest
import requests
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
API = f"{BASE}/api"
_mc = MongoClient(os.environ["MONGO_URL"])
_db = _mc[os.environ["DB_NAME"]]

VTA_RE = re.compile(r"^VTA-\d{8}-\d{4}$")


def _login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p}, timeout=30)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


@pytest.fixture(scope="module")
def tokens():
    return [_login("superadmin", "nova2024"), _login("admin", "Admin2024Nuevo!")]


@pytest.fixture(scope="module")
def bodega_id():
    b = _db.bodegas_inventario.find_one({"origen": "clinica"})
    assert b, "Se requiere una bodega clínica"
    return b["id"]


@pytest.fixture()
def caja_abierta():
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existente = _db.caja_cierres.find_one({"fecha": hoy, "origen": "clinica", "estado": "Abierto"})
    caja_id = None
    if not existente:
        caja_id = str(uuid.uuid4())
        _db.caja_cierres.insert_one({
            "id": caja_id, "fecha": hoy, "origen": "clinica", "estado": "Abierto",
            "monto_apertura": 0.0, "abierto_por": "test", "abierto_por_nombre": "iter59",
            "fecha_apertura": datetime.now(timezone.utc).isoformat(),
            "total_ingresos": 0.0, "total_egresos": 0.0,
            "ingresos_por_metodo": {}, "egresos_por_metodo": {},
            "saldo_esperado_efectivo": 0.0,
        })
    yield
    if caja_id:
        _db.caja_cierres.delete_one({"id": caja_id})


def _seed_producto(existencia, bodega_id, con_lotes=False):
    prod = {
        "id": str(uuid.uuid4()),
        "nombre": f"TEST-iter59-{uuid.uuid4().hex[:6]}",
        "codigo": f"T59-{uuid.uuid4().hex[:6]}",
        "origen": "clinica", "activo": True, "afecto_iva": False,
        "controla_inventario": True, "controla_lotes": con_lotes,
        "costo_promedio": 0.5, "ultimo_costo": 0.5, "precio_venta": 1.0,
        "tipo": "producto", "unidad_medida": "unidad", "categoria_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _db.productos_inventario.insert_one(prod)
    lote_id = None
    if con_lotes:
        lote_id = str(uuid.uuid4())
        _db.lotes_inventario.insert_one({
            "id": lote_id, "producto_id": prod["id"], "bodega_id": bodega_id,
            "origen": "clinica", "numero_lote": f"L-{uuid.uuid4().hex[:5]}",
            "cantidad_inicial": existencia, "cantidad_disponible": existencia,
            "costo_unitario": 0.5, "estado": "disponible",
            "fecha_vencimiento": "2027-12-31", "proveedor_id": None,
        })
    _db.existencias_inventario.insert_one({
        "id": str(uuid.uuid4()), "producto_id": prod["id"], "bodega_id": bodega_id,
        "origen": "clinica", "cantidad": existencia, "cantidad_reservada": 0,
        "ultima_actualizacion": datetime.now(timezone.utc).isoformat(),
    })
    return prod, lote_id


def _cleanup(prod_id):
    _db.ventas.delete_many({"items.producto_id": prod_id})
    _db.movimientos_inventario.delete_many({"producto_id": prod_id})
    _db.lotes_inventario.delete_many({"producto_id": prod_id})
    _db.existencias_inventario.delete_many({"producto_id": prod_id})
    _db.productos_inventario.delete_one({"id": prod_id})


def _vender(token, bodega_id, prod):
    payload = {
        "bodega_id": bodega_id,
        "items": [{"producto_id": prod["id"], "nombre": prod["nombre"], "cantidad": 1,
                   "precio_unitario": 1.0, "descuento": 0, "afecto_iva": False}],
        "formas_pago": [{"metodo": "Efectivo", "monto": 1.0}],
    }
    r = requests.post(f"{API}/ventas", json=payload,
                      headers={"Authorization": f"Bearer {token}"}, timeout=60)
    body = {}
    try:
        body = r.json()
    except Exception:
        pass
    return r.status_code, body


def test_anti_sobreventa_sin_lotes(tokens, bodega_id, caja_abierta):
    prod, _ = _seed_producto(3, bodega_id, con_lotes=False)
    try:
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = [ex.submit(_vender, tokens[i % 2], bodega_id, prod) for i in range(6)]
            results = [f.result() for f in as_completed(futs)]
        ok = sum(1 for c, _ in results if c == 200)
        fail = sum(1 for c, _ in results if c == 400)
        ex_final = _db.existencias_inventario.find_one(
            {"producto_id": prod["id"], "bodega_id": bodega_id})["cantidad"]
        assert ok == 3, f"Se esperaban 3 ventas OK, hubo {ok}: {results}"
        assert fail == 3, f"Se esperaban 3 rechazos 400, hubo {fail}: {results}"
        assert ex_final == 0, f"Existencia final debe ser 0, es {ex_final} (posible sobreventa)"
        assert ex_final >= 0, f"Existencia NEGATIVA: {ex_final}"
    finally:
        _cleanup(prod["id"])


def test_anti_sobreventa_con_lotes_fefo(tokens, bodega_id, caja_abierta):
    prod, lote_id = _seed_producto(2, bodega_id, con_lotes=True)
    try:
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = [ex.submit(_vender, tokens[i % 2], bodega_id, prod) for i in range(5)]
            results = [f.result() for f in as_completed(futs)]
        ok = sum(1 for c, _ in results if c == 200)
        fail = sum(1 for c, _ in results if c == 400)
        lote_final = _db.lotes_inventario.find_one({"id": lote_id})["cantidad_disponible"]
        ex_final = _db.existencias_inventario.find_one(
            {"producto_id": prod["id"], "bodega_id": bodega_id})["cantidad"]
        assert ok == 2, f"OK esperado 2, obtuvo {ok}"
        assert fail == 3, f"400 esperado 3, obtuvo {fail}"
        assert lote_final == 0 and lote_final >= 0
        assert ex_final == 0 and ex_final >= 0
    finally:
        _cleanup(prod["id"])


def test_numero_venta_unico_bajo_concurrencia(tokens, bodega_id, caja_abierta):
    """10 ventas concurrentes con stock suficiente => 10 números únicos y con formato."""
    prod, _ = _seed_producto(10, bodega_id, con_lotes=False)
    try:
        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = [ex.submit(_vender, tokens[i % 2], bodega_id, prod) for i in range(10)]
            results = [f.result() for f in as_completed(futs)]
        exitos = [b for c, b in results if c == 200]
        assert len(exitos) == 10, f"Se esperaban 10 ventas OK, hubo {len(exitos)}: {results}"
        numeros = [v.get("numero_venta") for v in exitos]
        assert all(numeros), f"Alguna venta sin numero_venta: {numeros}"
        for n in numeros:
            assert VTA_RE.match(n), f"Formato inválido: {n}"
        assert len(set(numeros)) == 10, f"numero_venta DUPLICADO bajo concurrencia: {numeros}"
    finally:
        _cleanup(prod["id"])
