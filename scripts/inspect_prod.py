import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

PROD_URL = "mongodb+srv://novavision-finanzas:d73fi7slqs2c73bqebfg@customer-apps.o48sbi.mongodb.net/?appName=novavision-finanzas&maxPoolSize=5&retryWrites=true&w=majority"


async def main():
    client = AsyncIOMotorClient(PROD_URL, serverSelectionTimeoutMS=60000, connectTimeoutMS=60000)
    dbs = await client.list_database_names()
    print("DATABASES:", dbs)
    for name in dbs:
        if name in ("admin", "local", "config"):
            continue
        db = client[name]
        cols = await db.list_collection_names()
        print(f"\n== DB: {name} ==")
        for c in sorted(cols):
            cnt = await db[c].count_documents({})
            print(f"  {c}: {cnt}")
    client.close()


asyncio.run(main())
