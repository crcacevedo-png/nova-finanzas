"""Migración única: poblar igss_ordenes en pacientes IGSS a partir de los
campos legacy (igss_nog / igss_no_sps / igss_codigo). Idempotente."""
import asyncio, os, sys, uuid
sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient


async def run():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    cursor = db.patients.find({"referral_institution": "igss"}, {"_id": 0})
    total = migrados = 0
    async for p in cursor:
        total += 1
        if p.get("igss_ordenes"):
            continue
        nog = (p.get("igss_nog") or "").strip()
        sps = (p.get("igss_no_sps") or "").strip()
        cod = (p.get("igss_codigo") or "").strip()
        if not (nog or sps or cod):
            continue
        orden = {"id": str(uuid.uuid4()), "nog": nog, "no_sps": sps, "codigo": cod, "procedimiento": ""}
        await db.patients.update_one({"id": p["id"]}, {"$set": {"igss_ordenes": [orden]}})
        migrados += 1
    print(f"Pacientes IGSS revisados: {total} | migrados a órdenes: {migrados}")


if __name__ == "__main__":
    asyncio.run(run())
