"""Prueba de concurrencia del POS: evitar sobreventa (vender el mismo lote agotado).

Siembra un producto con existencia = 3 en una bodega clínica, dispara 6 ventas
concurrentes (qty 1) desde 2 usuarios y verifica que SOLO 3 tengan éxito, el
resto falle por stock insuficiente y la existencia final sea 0 (nunca negativa).
Limpia todo al final.
"""
import os
import sys
import uuid
import time
import requests
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
API = os.environ["API_URL"] + "/api"
mc = MongoClient(os.environ["MONGO_URL"])
db = mc[os.environ["DB_NAME"]]

STOCK_INICIAL = 3
N_VENTAS = 6


def login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p}, timeout=30)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


def vender(token, bodega_id, prod):
    payload = {
        "bodega_id": bodega_id,
        "items": [{
            "producto_id": prod["id"],
            "nombre": prod["nombre"],
            "cantidad": 1,
            "precio_unitario": 1.0,
            "descuento": 0,
            "afecto_iva": False,
        }],
        "formas_pago": [{"metodo": "Efectivo", "monto": 1.0}],
    }
    r = requests.post(f"{API}/ventas", json=payload,
                      headers={"Authorization": f"Bearer {token}"}, timeout=60)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})


def main():
    print(f"API: {API}")
    tokens = []
    for u, p in [("superadmin", "nova2024"), ("admin", "Admin2024Nuevo!")]:
        try:
            tokens.append(login(u, p))
            print(f"  login OK: {u}")
        except Exception as e:
            print(f"  login FAIL {u}: {e}")
    if not tokens:
        sys.exit(1)

    # Bodega clínica (cualquiera existente)
    bodega = db.bodegas_inventario.find_one({"origen": "clinica"})
    if not bodega:
        print("No hay bodega clínica; abortando")
        sys.exit(1)
    bodega_id = bodega["id"]
    print(f"  Bodega: {bodega.get('nombre')} ({bodega_id})")

    # Caja abierta hoy?
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    caja = db.caja_cierres.find_one({"fecha": hoy, "origen": "clinica", "estado": "Abierto"})
    caja_creada_id = None
    print(f"  Caja abierta {hoy}: {'SÍ' if caja else 'NO'}")
    if not caja:
        caja_creada_id = str(uuid.uuid4())
        db.caja_cierres.insert_one({
            "id": caja_creada_id,
            "fecha": hoy,
            "origen": "clinica",
            "estado": "Abierto",
            "monto_apertura": 0.0,
            "abierto_por": "test",
            "abierto_por_nombre": "Test Concurrencia",
            "fecha_apertura": datetime.now(timezone.utc).isoformat(),
            "total_ingresos": 0.0,
            "total_egresos": 0.0,
            "ingresos_por_metodo": {},
            "egresos_por_metodo": {},
            "saldo_esperado_efectivo": 0.0,
        })
        print("  Caja temporal abierta para la prueba")

    # Sembrar producto de prueba con existencia limitada
    prod = {
        "id": str(uuid.uuid4()),
        "nombre": f"POSConcurTest-{uuid.uuid4().hex[:6]}",
        "codigo": f"PCT-{uuid.uuid4().hex[:6]}",
        "origen": "clinica",
        "activo": True,
        "afecto_iva": False,
        "controla_inventario": True,
        "controla_lotes": False,
        "costo_promedio": 0.5,
        "ultimo_costo": 0.5,
        "precio_venta": 1.0,
        "tipo": "producto",
        "unidad_medida": "unidad",
        "categoria_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    db.productos_inventario.insert_one(prod)
    db.existencias_inventario.insert_one({
        "id": str(uuid.uuid4()),
        "producto_id": prod["id"],
        "bodega_id": bodega_id,
        "origen": "clinica",
        "cantidad": STOCK_INICIAL,
        "cantidad_reservada": 0,
        "ultima_actualizacion": datetime.now(timezone.utc).isoformat(),
    })
    print(f"  Producto sembrado con existencia={STOCK_INICIAL}")

    # Disparar ventas concurrentes
    tasks = [tokens[i % len(tokens)] for i in range(N_VENTAS)]
    results = []
    venta_ids = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=N_VENTAS) as ex:
        futs = [ex.submit(vender, tk, bodega_id, prod) for tk in tasks]
        for f in as_completed(futs):
            code, body = f.result()
            results.append((code, body.get("detail") if isinstance(body, dict) else None))
            if code == 200 and isinstance(body, dict) and body.get("id"):
                venta_ids.append(body["id"])
    dt = time.time() - t0

    ok = sum(1 for c, _ in results if c == 200)
    fail = sum(1 for c, _ in results if c == 400)
    print(f"\n--- Resultados ({N_VENTAS} ventas concurrentes en {dt:.2f}s) ---")
    print(f"  200 OK (ventas exitosas): {ok}  (esperado: {STOCK_INICIAL})")
    print(f"  400 (stock insuficiente): {fail}  (esperado: {N_VENTAS - STOCK_INICIAL})")
    for c, det in results:
        if c not in (200, 400):
            print(f"    inesperado: {c} {det}")

    ex_final = db.existencias_inventario.find_one({"producto_id": prod["id"], "bodega_id": bodega_id})
    cantidad_final = ex_final.get("cantidad") if ex_final else None
    print(f"  Existencia final: {cantidad_final}  (esperado: 0, NUNCA negativa)")

    exito = (ok == STOCK_INICIAL and cantidad_final == 0)
    print(f"\n  {'✅ SIN SOBREVENTA' if exito else '❌ FALLO (posible sobreventa o descuento incorrecto)'}")

    # Limpieza
    print("\n--- Limpieza ---")
    for vid in venta_ids:
        db.ventas.delete_one({"id": vid})
    d1 = db.movimientos_inventario.delete_many({"producto_id": prod["id"]}).deleted_count
    db.existencias_inventario.delete_many({"producto_id": prod["id"]})
    db.productos_inventario.delete_one({"id": prod["id"]})
    if caja_creada_id:
        db.caja_cierres.delete_one({"id": caja_creada_id})
        db.movimientos_caja.delete_many({"referencia_id": {"$in": venta_ids}}) if venta_ids else None
    print(f"  Ventas borradas: {len(venta_ids)}, movimientos: {d1}, producto+existencias eliminados"
          + (", caja temporal eliminada" if caja_creada_id else ""))

    sys.exit(0 if exito else 2)


if __name__ == "__main__":
    main()
