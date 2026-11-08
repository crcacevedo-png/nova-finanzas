"""
Script de una sola ejecución: borra las cirugías de ejemplo en preview y carga las
cirugías reales del archivo Excel subido por el usuario
(cirugias_novavision_oct2026_ene2027.xlsx).

Ejecutar desde /app/backend: python3 scripts/import_surgeries_from_excel.py <ruta_xlsx>
"""
import asyncio
import os
import re
import sys
import uuid
from datetime import datetime, timezone

import openpyxl
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

VALID_EYE = {"OD", "OS", "AO"}
VALID_ANESTHESIA = {"topica", "local", "local_asistida", "general", "retrobulbar", "peribulbar", "sedacion"}
VALID_INSTITUTION = {"Novavision", "Alquiler", "Seguro Privado", "IGSS"}
INST_IN_OBS_RE = re.compile(r"Instituci[oó]n:\s*([^|]+)", re.IGNORECASE)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_rows(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Cirugías"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    parsed = []
    warnings = []
    for i, r in enumerate(rows, start=2):
        (fecha, hora, paciente, procedimiento, lio, cirujano, ayudante, ojo,
         tipo_anestesia, anestesiologo, institucion, nombre_seguro,
         unidad_igss, sps, afiliacion, codigo, costo, preop, observaciones) = (list(r) + [None] * 19)[:19]

        if not (fecha and hora and paciente and procedimiento and cirujano and tipo_anestesia):
            warnings.append(f"Fila {i}: faltan campos obligatorios, se omite")
            continue

        observaciones = (observaciones or "").strip()
        institucion = (institucion or "").strip()
        insurance_name = (nombre_seguro or "").strip()

        if not institucion:
            m = INST_IN_OBS_RE.search(observaciones)
            if m:
                insurance_name = m.group(1).strip()
                institucion = "Seguro Privado"
                observaciones = INST_IN_OBS_RE.sub("", observaciones).strip(" |")
            else:
                warnings.append(f"Fila {i} ({paciente}): sin institución, se asigna 'Seguro Privado' por defecto")
                institucion = "Seguro Privado"

        if institucion not in VALID_INSTITUTION:
            warnings.append(f"Fila {i} ({paciente}): institución '{institucion}' no reconocida, se asigna 'Seguro Privado'")
            institucion = "Seguro Privado"

        ojo = (ojo or "").strip().upper()
        if ojo and ojo not in VALID_EYE:
            warnings.append(f"Fila {i} ({paciente}): ojo '{ojo}' no válido, se deja vacío")
            ojo = ""
        if not ojo:
            warnings.append(f"Fila {i} ({paciente}): sin ojo especificado")

        tipo_anestesia = (tipo_anestesia or "").strip()
        if tipo_anestesia not in VALID_ANESTHESIA:
            warnings.append(f"Fila {i} ({paciente}): tipo de anestesia '{tipo_anestesia}' no válido, se omite")
            continue

        anestesiologo = (anestesiologo or "").strip() or "N/A"

        igss_data = None
        if institucion == "IGSS":
            if unidad_igss or sps or afiliacion or codigo or costo:
                igss_data = {
                    "unit": (unidad_igss or "").strip() or None,
                    "unit_id": None,
                    "nog_id": None,
                    "nog_number": None,
                    "sps": (str(sps).strip() if sps else None),
                    "affiliation_number": (str(afiliacion).strip() if afiliacion else None),
                    "code": (str(codigo).strip() if codigo else None),
                    "procedure_cost": float(costo) if costo else None,
                }
            else:
                warnings.append(f"Fila {i} ({paciente}): IGSS sin SPS/afiliación/código/costo, pendiente de completar")

        preop_status = "incompleto"
        if preop:
            p = str(preop).strip().lower()
            if p == "completo":
                preop_status = "completo"
            elif p == "incompleto":
                preop_status = "incompleto"

        doc = {
            "id": str(uuid.uuid4()),
            "date": str(fecha).strip(),
            "time": str(hora).strip(),
            "patient_name": str(paciente).strip(),
            "patient_id": None,
            "procedure": str(procedimiento).strip(),
            "surgeon": str(cirujano).strip(),
            "assistant_surgeon": (str(ayudante).strip() if ayudante else None),
            "eye": ojo,
            "lio": (str(lio).strip() if lio else ""),
            "anesthesia_type": tipo_anestesia,
            "anesthesiologist": anestesiologo,
            "institution": institucion,
            "igss_data": igss_data,
            "insurance_name": insurance_name,
            "observations": observaciones,
            "equipment": [],
            "supplies": [],
            "supplies_status": "pendiente" if institucion == "Alquiler" else None,
            "preop_status": preop_status,
            "status": "activo",
            "cancellation_reason": None,
            "rescheduled_to": None,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        parsed.append(doc)
    return parsed, warnings


async def main():
    if len(sys.argv) < 2:
        print("Uso: python3 import_surgeries_from_excel.py <ruta_xlsx>")
        sys.exit(1)
    path = sys.argv[1]

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    from routes.quirofano import upsert_anesthesia_from_surgery

    superadmin = await db.users.find_one({"role": "superadmin"}, {"_id": 0, "id": 1})
    created_by = superadmin["id"] if superadmin else "system"

    old_surgeries = await db.surgeries.find({}, {"_id": 0, "id": 1}).to_list(10000)
    old_ids = [s["id"] for s in old_surgeries]
    print(f"Cirugías existentes a eliminar: {len(old_ids)}")

    if old_ids:
        r1 = await db.anesthesia_records.delete_many({"surgery_id": {"$in": old_ids}})
        r2 = await db.notas_cirugia.delete_many({"surgery_id": {"$in": old_ids}})
        print(f"  anesthesia_records eliminados: {r1.deleted_count}")
        print(f"  notas_cirugia eliminadas: {r2.deleted_count}")
    r3 = await db.surgeries.delete_many({})
    print(f"  surgeries eliminadas: {r3.deleted_count}")

    docs, warnings = parse_rows(path)
    for d in docs:
        d["created_by"] = created_by

    if docs:
        await db.surgeries.insert_many(docs)
    print(f"\nCirugías insertadas: {len(docs)}")

    for d in docs:
        try:
            await upsert_anesthesia_from_surgery(d)
        except Exception as e:
            print(f"  (!) No se pudo crear registro de anestesia para {d['id']}: {e}")

    print(f"\nAdvertencias ({len(warnings)}):")
    for w in warnings:
        print(" -", w)

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
