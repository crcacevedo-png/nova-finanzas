#!/usr/bin/env python3
"""
Script de migración para convertir recetas de anteojos y lentes de contacto
del formato legacy (objeto único) al nuevo formato de arrays.

Uso:
    python migrar_recetas_legacy.py [--dry-run]
    
    --dry-run: Muestra qué cambios se harían sin ejecutarlos
"""

import asyncio
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "novavision_erp")


async def migrar_recetas():
    """Migra las recetas del formato legacy al nuevo formato de arrays."""
    
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("=" * 60)
        print("MODO DRY-RUN: No se realizarán cambios en la base de datos")
        print("=" * 60)
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Buscar evaluaciones que tienen recetas en formato legacy
    # (tienen recetas.anteojos o recetas.lentes_contacto pero no las listas)
    evaluaciones = await db.evaluaciones_oftalmologicas.find({
        "$or": [
            # Tiene receta de anteojos legacy pero no lista
            {
                "recetas.anteojos.od.esfera": {"$exists": True, "$ne": ""},
                "recetas.anteojos_lista": {"$exists": False}
            },
            {
                "recetas.anteojos.os.esfera": {"$exists": True, "$ne": ""},
                "recetas.anteojos_lista": {"$exists": False}
            },
            # Tiene receta de lentes legacy pero no lista
            {
                "recetas.lentes_contacto.od.poder": {"$exists": True, "$ne": ""},
                "recetas.lentes_contacto_lista": {"$exists": False}
            },
            {
                "recetas.lentes_contacto.os.poder": {"$exists": True, "$ne": ""},
                "recetas.lentes_contacto_lista": {"$exists": False}
            }
        ]
    }).to_list(None)
    
    print(f"\nEvaluaciones encontradas para migrar: {len(evaluaciones)}")
    
    migradas_anteojos = 0
    migradas_lentes = 0
    errores = 0
    
    for ev in evaluaciones:
        try:
            ev_id = ev.get("id") or str(ev.get("_id"))
            paciente = ev.get("paciente_nombre", "Desconocido")
            fecha_creacion = ev.get("fecha_creacion", datetime.now(timezone.utc).isoformat())
            
            recetas = ev.get("recetas", {})
            updates = {}
            
            # Migrar receta de anteojos
            anteojos = recetas.get("anteojos", {})
            od_ant = anteojos.get("od", {})
            os_ant = anteojos.get("os", {}) or anteojos.get("oi", {})  # Compatibilidad con oi legacy
            
            tiene_anteojos = bool(
                od_ant.get("esfera") or od_ant.get("cilindro") or
                os_ant.get("esfera") or os_ant.get("cilindro")
            )
            
            if tiene_anteojos and "anteojos_lista" not in recetas:
                nueva_receta_anteojos = {
                    "id": f"ant_migrated_{ev_id}",
                    "od": {
                        "esfera": od_ant.get("esfera", ""),
                        "cilindro": od_ant.get("cilindro", ""),
                        "eje": od_ant.get("eje", ""),
                        "adicion": od_ant.get("adicion", "")
                    },
                    "os": {
                        "esfera": os_ant.get("esfera", ""),
                        "cilindro": os_ant.get("cilindro", ""),
                        "eje": os_ant.get("eje", ""),
                        "adicion": os_ant.get("adicion", "")
                    },
                    "distancia_pupilar": anteojos.get("distancia_pupilar", ""),
                    "tipo_lente": anteojos.get("tipo_lente", ""),
                    "material": anteojos.get("material", ""),
                    "tratamientos": anteojos.get("tratamientos", ""),
                    "uso": anteojos.get("uso", ""),
                    "observaciones": anteojos.get("observaciones", ""),
                    "fecha_creacion": fecha_creacion,
                    "migrado_de_legacy": True
                }
                updates["recetas.anteojos_lista"] = [nueva_receta_anteojos]
                migradas_anteojos += 1
                print(f"  [ANTEOJOS] {paciente} - OD: {od_ant.get('esfera', '-')}, OS: {os_ant.get('esfera', '-')}")
            
            # Migrar receta de lentes de contacto
            lentes = recetas.get("lentes_contacto", {})
            od_lc = lentes.get("od", {})
            os_lc = lentes.get("os", {}) or lentes.get("oi", {})  # Compatibilidad con oi legacy
            
            tiene_lentes = bool(
                od_lc.get("poder") or od_lc.get("curva_base") or
                os_lc.get("poder") or os_lc.get("curva_base")
            )
            
            if tiene_lentes and "lentes_contacto_lista" not in recetas:
                nueva_receta_lentes = {
                    "id": f"lc_migrated_{ev_id}",
                    "od": {
                        "poder": od_lc.get("poder", ""),
                        "curva_base": od_lc.get("curva_base", ""),
                        "diametro": od_lc.get("diametro", ""),
                        "adicion": od_lc.get("adicion", "")
                    },
                    "os": {
                        "poder": os_lc.get("poder", ""),
                        "curva_base": os_lc.get("curva_base", ""),
                        "diametro": os_lc.get("diametro", ""),
                        "adicion": os_lc.get("adicion", "")
                    },
                    "marca": lentes.get("marca", ""),
                    "tipo": lentes.get("tipo", ""),
                    "regimen_reemplazo": lentes.get("regimen_reemplazo", ""),
                    "observaciones": lentes.get("observaciones", ""),
                    "fecha_creacion": fecha_creacion,
                    "migrado_de_legacy": True
                }
                updates["recetas.lentes_contacto_lista"] = [nueva_receta_lentes]
                migradas_lentes += 1
                print(f"  [LENTES]   {paciente} - OD: {od_lc.get('poder', '-')}, OS: {os_lc.get('poder', '-')}")
            
            # Aplicar actualizaciones
            if updates and not dry_run:
                await db.evaluaciones_oftalmologicas.update_one(
                    {"_id": ev["_id"]},
                    {"$set": updates}
                )
            
        except Exception as e:
            errores += 1
            print(f"  [ERROR] {ev.get('paciente_nombre', 'Unknown')}: {str(e)}")
    
    # También asegurar que evaluaciones sin recetas legacy tengan las listas vacías
    if not dry_run:
        result = await db.evaluaciones_oftalmologicas.update_many(
            {"recetas.anteojos_lista": {"$exists": False}},
            {"$set": {"recetas.anteojos_lista": []}}
        )
        print(f"\nEvaluaciones inicializadas con anteojos_lista vacía: {result.modified_count}")
        
        result = await db.evaluaciones_oftalmologicas.update_many(
            {"recetas.lentes_contacto_lista": {"$exists": False}},
            {"$set": {"recetas.lentes_contacto_lista": []}}
        )
        print(f"Evaluaciones inicializadas con lentes_contacto_lista vacía: {result.modified_count}")
    
    print("\n" + "=" * 60)
    print("RESUMEN DE MIGRACIÓN")
    print("=" * 60)
    print(f"Recetas de anteojos migradas:        {migradas_anteojos}")
    print(f"Recetas de lentes de contacto migradas: {migradas_lentes}")
    print(f"Errores:                             {errores}")
    
    if dry_run:
        print("\n[DRY-RUN] Ejecute sin --dry-run para aplicar los cambios.")
    else:
        print("\n[OK] Migración completada exitosamente.")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(migrar_recetas())
