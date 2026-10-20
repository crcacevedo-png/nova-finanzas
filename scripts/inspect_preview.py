import asyncio, json
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    c = AsyncIOMotorClient("mongodb://localhost:27017")
    db = c["test_database"]
    pt = await db.patients.count_documents({})
    pa = await db.patients.count_documents({"is_active": True})
    ev = await db.evaluaciones_oftalmologicas.count_documents({})
    print("patients total=", pt, "active=", pa, "evaluaciones=", ev)
    print("\n--- sample patient (imported) ---")
    p = await db.patients.find_one({"imported": True}, {"_id": 0})
    print(json.dumps(p, ensure_ascii=False, default=str, indent=1))
    print("\n--- patient field keys union (sample 2000) ---")
    keys = set()
    async for d in db.patients.find({}, {"_id": 0}).limit(2000):
        keys.update(d.keys())
    print(sorted(keys))
    print("\n--- sample evaluacion ---")
    e = await db.evaluaciones_oftalmologicas.find_one({}, {"_id": 0})
    print("eval keys:", sorted(e.keys()) if e else None)
    if e:
        print("expediente/paciente_expediente=", e.get("paciente_expediente"), "| paciente_id=", e.get("paciente_id"), "| import_source_id=", e.get("import_source_id"), "| import_batch=", e.get("import_batch"))
    c.close()

asyncio.run(main())
