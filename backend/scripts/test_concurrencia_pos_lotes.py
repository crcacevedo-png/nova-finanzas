"""Prueba de concurrencia del POS con LOTES (FEFO): evitar vender el mismo lote agotado.

Producto controla_lotes=True, 1 lote con cantidad_disponible=2, existencia=2.
Dispara 5 ventas concurrentes (qty 1); solo 2 deben tener éxito, el lote debe
quedar en 0 (nunca negativo) y la existencia total en 0. Limpia todo.
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

STOCK = 2
N = 5


def login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p}, timeout=30)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


def vender(token, bodega_id, prod):
    payload = {
        "bodega_id": bodega_id,
        "items": [{"producto_id": prod["id"], "nombre": prod["nombre"], "cantidad": 1,
                   "precio_unitario": 1.0, "descuento": 0, "afecto_iva": False}],
        "formas_pago": [{"metodo": "Efectivo", "monto": 1.0}],
    }
    r = requests.post(f"{API}/ventas", json=payload,
                      headers={"Authorization": f"Bearer {token}"}, timeout=60)
    return r.status_code


def main():
    print(f"API: {API}")
    tokens = [login("superadmin", "nova2024"), login("admin", "Admin2024Nuevo!")]
    print("  logins OK")

    bodega = db.bodegas_inventario.find_one({"origen": "clinica"})
    bodega_id = bodega["id"]

    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    caja = db.caja_cierres.find_one({"fecha": hoy, "origen": "clinica", "estado": "Abierto"})
    caja_creada_id = None
    if not caja:
        caja_creada_id = str(uuid.uuid4())
        db.caja_cierres.insert_one({
            "id": caja_creada_id, "fecha": hoy, "origen": "clinica", "estado": "Abierto",
            "monto_apertura": 0.0, "abierto_por": "test", "abierto_por_nombre": "Test",
            "fecha_apertura": datetime.now(timezone.utc).isoformat(),
            "total_ingresos": 0.0, "total_egresos": 0.0,
            "ingresos_por_metodo": {}, "egresos_por_metodo": {}, "saldo_esperado_efectivo": 0.0,
        })

    prod = {
        "id": str(uuid.uuid4()), "nombre": f"POSLoteTest-{uuid.uuid4().hex[:6]}",
        "codigo": f"PLT-{uuid.uuid4().hex[:6]}", "origen": "clinica", "activo": True,
        "afecto_iva": False, "controla_inventario": True, "controla_lotes": True,
        "costo_promedio": 0.5, "ultimo_costo": 0.5, "precio_venta": 1.0, "tipo": "producto",
        "unidad_medida": "unidad", "categoria_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    db.productos_inventario.insert_one(prod)
    lote_id = str(uuid.uuid4())
    db.lotes_inventario.insert_one({
        "id": lote_id, "producto_id": prod["id"], "bodega_id": bodega_id, "origen": "clinica",
        "numero_lote": f"LOTE-{uuid.uuid4().hex[:5]}", "cantidad_inicial": STOCK,
        "cantidad_disponible": STOCK, "costo_unitario": 0.5, "estado": "disponible",
        "fecha_vencimiento": "2027-12-31", "proveedor_id": None,
    })
    db.existencias_inventario.insert_one({
        "id": str(uuid.uuid4()), "producto_id": prod["id"], "bodega_id": bodega_id,
        "origen": "clinica", "cantidad": STOCK, "cantidad_reservada": 0,
        "ultima_actualizacion": datetime.now(timezone.utc).isoformat(),
    })
    print(f"  Producto con lote sembrado (disponible={STOCK})")

    results = []
    with ThreadPoolExecutor(max_workers=N) as ex:
        futs = [ex.submit(vender, tokens[i % 2], bodega_id, prod) for i in range(N)]
        for f in as_completed(futs):
            results.append(f.result())
    ok = sum(1 for c in results if c == 200)
    fail = sum(1 for c in results if c == 400)
    lote_final = db.lotes_inventario.find_one({"id": lote_id})["cantidad_disponible"]
    ex_final = db.existencias_inventario.find_one({"producto_id": prod["id"], "bodega_id": bodega_id})["cantidad"]

    print(f"\n--- Resultados ({N} ventas concurrentes) ---")
    print(f"  200 OK: {ok} (esperado {STOCK}) | 400: {fail} (esperado {N-STOCK})")
    print(f"  Lote disponible final: {lote_final} (esperado 0, nunca negativo)")
    print(f"  Existencia total final: {ex_final} (esperado 0)")
    exito = ok == STOCK and lote_final == 0 and ex_final == 0
    print(f"  {'✅ SIN SOBREVENTA DE LOTE' if exito else '❌ FALLO'}")

    # Limpieza
    db.ventas.delete_many({"items.producto_id": prod["id"]})
    db.movimientos_inventario.delete_many({"producto_id": prod["id"]})
    db.lotes_inventario.delete_many({"producto_id": prod["id"]})
    db.existencias_inventario.delete_many({"producto_id": prod["id"]})
    db.productos_inventario.delete_one({"id": prod["id"]})
    if caja_creada_id:
        db.caja_cierres.delete_one({"id": caja_creada_id})
    print("  Limpieza completada")
    sys.exit(0 if exito else 2)


if __name__ == "__main__":
    main()
