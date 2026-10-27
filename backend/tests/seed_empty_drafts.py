# Seed helper: insert TEST_ empty draft evaluations (legacy simulation) for Mantenimiento UI tests
import os, uuid, asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv('/app/backend/.env')


async def main(n=3):
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    for i in range(n):
        await db.evaluaciones_oftalmologicas.insert_one({
            "id": f"TEST_borrador_{uuid.uuid4()}", "paciente_id": "TEST_pac",
            "paciente_nombre": f"TEST_Borrador {i}", "paciente_expediente": f"TEST-{i}",
            "fecha": "2026-10-26", "medico_id": "", "medico_nombre": "", "motivo_consulta": "",
            "examen": {"tipo_lensometria": "Lensometria"},
        })
    print("seeded", n)

asyncio.run(main())
