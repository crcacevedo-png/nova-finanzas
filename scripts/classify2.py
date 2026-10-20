import asyncio, re
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    c = AsyncIOMotorClient("mongodb://localhost:27017")
    db = c["test_database"]

    num_q = {"record_number": re.compile(r"^\d+$")}
    print("Pacientes con expediente NUMERICO (reales):", await db.patients.count_documents(num_q))
    print("  activos:", await db.patients.count_documents({**num_q, "is_active": True}))
    print("  con esDatoPrueba=True:", await db.patients.count_documents({**num_q, "esDatoPrueba": True}))
    print("Pacientes esDatoPrueba=True (total):", await db.patients.count_documents({"esDatoPrueba": True}))
    print("Pacientes record_number=None:", await db.patients.count_documents({"record_number": None}))

    # Expedientes referenciados por las evaluaciones historicas
    exps = await db.evaluaciones_oftalmologicas.distinct("paciente_expediente", {"import_source_id": {"$ne": None}})
    exps = [str(e) for e in exps if e]
    print("\nEvaluaciones historicas: expedientes distintos =", len(exps))
    # cuantos de esos expedientes existen entre pacientes numericos
    existing = set()
    async for p in db.patients.find({"record_number": {"$in": exps}}, {"_id":0,"record_number":1}):
        existing.add(p["record_number"])
    faltan = [e for e in exps if e not in existing]
    print("  expedientes con paciente existente:", len(existing))
    print("  expedientes SIN paciente:", len(faltan), faltan[:10])

    # Distribucion institucion en pacientes numericos
    print("\nDistribucion referral_institution (numericos):")
    pipe = [{"$match": num_q}, {"$group": {"_id": "$referral_institution", "n": {"$sum": 1}}}]
    async for r in db.patients.aggregate(pipe):
        print("  ", r["_id"], r["n"])
    c.close()

asyncio.run(main())
