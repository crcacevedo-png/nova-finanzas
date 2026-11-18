# Última actividad de cada usuario con sesión (para avisar quién está conectado antes de restaurar).
# Se escribe como mucho una vez por minuto por usuario; al cerrar sesión se borra.
import time
from datetime import datetime, timezone

from config.database import db

_ULTIMA = {}


async def marcar_actividad(user: dict):
    uid = user.get("id")
    ahora = time.monotonic()
    if not uid or ahora - _ULTIMA.get(uid, -1e9) < 60:
        return
    _ULTIMA[uid] = ahora
    await db.sesiones_actividad.update_one({"user_id": uid}, {"$set": {
        "user_id": uid, "nombre": user.get("name") or user.get("username", ""), "usuario": user.get("username", ""),
        "rol": user.get("role", ""), "ultima_actividad": datetime.now(timezone.utc).isoformat()}}, upsert=True)


async def cerrar_actividad(user_id: str):
    _ULTIMA.pop(user_id, None)
    await db.sesiones_actividad.delete_one({"user_id": user_id})
