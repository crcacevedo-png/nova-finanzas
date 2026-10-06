#!/usr/bin/env python3
"""
Corrección histórica del costo promedio ponderado (hallazgo H-02, Auditoría P26).

IMPORTANTE: la primera versión de este script recalculaba TODO desde el kardex
asumiendo que el costo promedio solo cambia por movimientos tipo "entrada".
Eso resultó INCORRECTO para productos cuyo stock inicial se cargó directo en
la base (sin movimiento "entrada" en el kardex): el script los dejaba en
costo_promedio = 0. Esa corrección fue revertida inmediatamente.

Esta versión es CONSERVADORA: solo corrige un producto si TODAS sus entradas
de kardex ocurren con la existencia en cero al inicio (cadena limpia, sin
ediciones manuales de costo fuera del kardex) y tiene 2+ entradas (único
escenario donde el bug de orden de operaciones (actualizar_existencia antes
de recalcular_costo_promedio) pudo haberse manifestado). Todo lo demás se
reporta para revisión manual, NO se modifica automáticamente.
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    productos = await db.productos_inventario.find({"controla_inventario": True}).to_list(10000)

    for producto in productos:
        producto_id = producto["id"]
        entradas = await db.movimientos_inventario.find(
            {"producto_id": producto_id, "tipo": "entrada"}
        ).sort("fecha", 1).to_list(10000)

        if len(entradas) < 2:
            continue  # el bug requiere al menos 2 entradas para manifestarse

        if entradas[0].get("existencia_anterior", -1) != 0:
            print(f"[REVISION MANUAL] {producto.get('codigo')} {producto.get('nombre')}: "
                  f"la primera entrada no parte de existencia 0, no se puede recalcular con certeza desde el kardex.")
            continue

        # Verificar que no haya saltos de costo fuera de las entradas (indicio de edicion manual)
        costos_vistos = {e["costo_unitario"] for e in entradas}
        if len(costos_vistos) > 1:
            print(f"[REVISION MANUAL] {producto.get('codigo')} {producto.get('nombre')}: "
                  f"tiene entradas a distintos costos ({costos_vistos}); verificar historial completo antes de recalcular.")
            continue

        costo_uniforme = entradas[0]["costo_unitario"]
        costo_anterior = producto.get("costo_promedio", 0) or 0
        if abs(costo_uniforme - costo_anterior) > 0.01:
            await db.productos_inventario.update_one(
                {"id": producto_id},
                {"$set": {"costo_promedio": round(costo_uniforme, 4)}}
            )
            print(f"[CORREGIDO] {producto.get('codigo')} {producto.get('nombre')}: "
                  f"Q{costo_anterior:.2f} -> Q{costo_uniforme:.2f} (entradas uniformes, sin ambiguedad)")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
