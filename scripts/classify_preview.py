import asyncio, json, re
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    c = AsyncIOMotorClient("mongodb://localhost:27017")
    db = c["test_database"]

    # Pacientes historicos = record_number NO empieza con "EXP-"
    hist_q = {"record_number": {"$not": re.compile(r"^EXP-")}}
    demo_q = {"record_number": re.compile(r"^EXP-")}
    print("patients:")
    print("  historicos (no EXP):", await db.patients.count_documents(hist_q))
    print("    de esos activos:", await db.patients.count_documents({**hist_q, "is_active": True}))
    print("  demo (EXP-...):", await db.patients.count_documents(demo_q))
    print("  esDatoPrueba True:", await db.patients.count_documents({"esDatoPrueba": True}))
    print("  perfil_prueba True:", await db.patients.count_documents({"perfil_prueba": True}))

    # muestra de record_numbers historicos
    print("  sample hist record_numbers:")
    async for p in db.patients.find(hist_q, {"_id":0,"record_number":1,"first_name":1,"is_active":1}).sort("record_number",1).limit(3):
        print("   ", p.get("record_number"), p.get("first_name"), "active=",p.get("is_active"))

    # un paciente historico completo
    ph = await db.patients.find_one(hist_q, {"_id":0})
    print("\n--- sample HISTORIC patient doc ---")
    print(json.dumps(ph, ensure_ascii=False, default=str, indent=1))

    print("\nevaluaciones:")
    print("  con import_source_id:", await db.evaluaciones_oftalmologicas.count_documents({"import_source_id": {"$ne": None}}))
    print("  con import_batch:", await db.evaluaciones_oftalmologicas.count_documents({"import_batch": {"$ne": None}}))
    print("  paciente_expediente EXP- (demo):", await db.evaluaciones_oftalmologicas.count_documents({"paciente_expediente": re.compile(r"^EXP-")}))
    eh = await db.evaluaciones_oftalmologicas.find_one({"import_source_id": {"$ne": None}}, {"_id":0})
    print("\n--- sample HISTORIC evaluacion keys ---")
    if eh:
        print("exp=",eh.get("paciente_expediente"),"| src=",eh.get("import_source_id"),"| batch=",eh.get("import_batch"))
        print("keys:", sorted(eh.keys()))
    c.close()

asyncio.run(main())
