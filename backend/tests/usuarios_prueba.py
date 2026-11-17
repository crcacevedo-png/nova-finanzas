# Usuarios SOLO de prueba (uno por rol). conftest.py los siembra al iniciar pytest y los
# borra al terminar. Nunca se usan usuarios reales ni sus contraseñas.
# Contraseñas: variables de entorno TEST_PASSWORD_<CLAVE> (p. ej. TEST_PASSWORD_SUPERADMIN).
# Si no están definidas se genera una aleatoria para esa corrida; no se escribe en disco.
import os
import secrets
from datetime import datetime, timezone

import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv('/app/backend/.env')

# clave -> (username, rol, nombre)
USUARIOS = {
    "superadmin": ("prueba.superadmin", "superadmin", "Prueba Superadmin"),
    "admin": ("prueba.admin", "admin", "Prueba Admin"),
    "usuario": ("prueba.usuario", "usuario", "Prueba Usuario"),
    "optica": ("prueba.optica", "optica", "Prueba Optica"),
    "medico": ("prueba.medico", "medico", "Prueba Medico"),
    "igss": ("prueba.igss", "administrador_igss", "Prueba Admin IGSS"),
    "anestesia": ("prueba.anestesia", "anestesia", "Prueba Anestesia"),
}


def password(clave: str) -> str:
    var = f"TEST_PASSWORD_{clave.upper()}"
    if not os.environ.get(var):
        os.environ[var] = "Tp-" + secrets.token_urlsafe(18)
    return os.environ[var]


def usuario(clave: str) -> str:
    return USUARIOS[clave][0]


def par(clave: str) -> tuple:
    return usuario(clave), password(clave)


def cred(clave: str) -> dict:
    return {"username": usuario(clave), "password": password(clave)}


DOCTOR_PRUEBA = "TEST_DOC_medico"  # ficha de médico vinculada al usuario de prueba "medico"


def _db():
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def sembrar():
    now = datetime.now(timezone.utc).isoformat()
    db = _db()
    users = db.users
    for clave, (username, rol, nombre) in USUARIOS.items():
        pwd = bcrypt.hashpw(password(clave).encode(), bcrypt.gensalt()).decode()
        users.update_one({"username": username}, {
            "$set": {"name": nombre, "role": rol, "password": pwd, "is_active": True, "es_usuario_prueba": True,
                     "failed_login_attempts": 0, "locked_until": None, "must_change_password": False,
                     "token_version": 1, "updated_at": now},
            "$setOnInsert": {"id": f"TEST_USR_{clave}", "username": username, "created_at": now}}, upsert=True)
    medico_id = users.find_one({"username": usuario("medico")}, {"_id": 0, "id": 1})["id"]
    db.doctors.update_one({"id": DOCTOR_PRUEBA}, {"$set": {
        "name": USUARIOS["medico"][2], "specialty": "Oftalmología General", "is_active": True,
        "usuario_id": medico_id, "es_usuario_prueba": True},
        "$setOnInsert": {"created_by": "pruebas", "created_at": now}}, upsert=True)


def retirar():
    db = _db()
    db.users.delete_many({"es_usuario_prueba": True, "username": {"$in": [u for u, _, _ in USUARIOS.values()]}})
    db.doctors.delete_many({"id": DOCTOR_PRUEBA, "es_usuario_prueba": True})
