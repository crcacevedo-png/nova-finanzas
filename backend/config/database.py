# /app/backend/config/database.py
# Configuración de la base de datos MongoDB

import os
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "novavision")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
