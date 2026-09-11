# /app/backend/config/database.py
# Configuración de base de datos MongoDB

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings (SEC-001: sin fallback embebido; debe venir del entorno)
JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8

# Blacklisted tokens (for logout)
blacklisted_tokens = set()
