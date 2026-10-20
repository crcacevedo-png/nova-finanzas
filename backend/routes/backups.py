# /app/backend/routes/backups.py
# Respaldos automáticos de la base de datos -> almacenamiento de archivos de Emergent.
import os
import gzip
import json
import uuid
import hmac
import asyncio
import logging
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException, Header, Response

from config.database import db
from routes.auth import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backups", tags=["Respaldos"])
cron_router = APIRouter(prefix="/cron", tags=["Cron"])

APP_NAME = "novavision-finanzas"

# ==================== Almacenamiento de objetos ====================
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")

_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=180,
    )
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=180,
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> bytes:
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=120)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=120)
    resp.raise_for_status()
    return resp.content


# ==================== Lógica de respaldo ====================
async def _run_backup(backup_id: str):
    """Vuelca TODAS las colecciones a un JSON comprimido y lo sube al almacenamiento."""
    try:
        collection_names = await db.list_collection_names()
        dump = {}
        total_docs = 0
        for cname in collection_names:
            if cname == "backups":
                continue
            docs = []
            async for d in db[cname].find({}):
                if "_id" in d:
                    d["_id"] = str(d["_id"])
                docs.append(d)
            dump[cname] = docs
            total_docs += len(docs)

        payload = {
            "app": APP_NAME,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "collections": sorted(dump.keys()),
            "documents_count": total_docs,
            "data": dump,
        }
        raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        gz = gzip.compress(raw, compresslevel=6)

        path = f"{APP_NAME}/backups/{backup_id}.json.gz"
        result = put_object(path, gz, "application/gzip")

        await db.backups.update_one({"id": backup_id}, {"$set": {
            "status": "completado",
            "storage_path": result.get("path", path),
            "size": result.get("size", len(gz)),
            "size_uncompressed": len(raw),
            "collections_count": len(dump),
            "documents_count": total_docs,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }})
        logger.info(f"Backup {backup_id} completado: {len(dump)} colecciones, {total_docs} docs, {len(gz)} bytes")
    except Exception as e:
        logger.exception("Backup falló")
        await db.backups.update_one({"id": backup_id}, {"$set": {
            "status": "error",
            "error": str(e)[:500],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }})


async def _crear_backup(tipo: str, created_by: str) -> dict:
    now = datetime.now(timezone.utc)
    backup_id = str(uuid.uuid4())
    filename = f"respaldo-{now.strftime('%Y-%m-%d_%H%M%S')}.json.gz"
    doc = {
        "id": backup_id,
        "filename": filename,
        "tipo": tipo,                 # "automatico" | "manual"
        "status": "en_progreso",      # en_progreso | completado | error
        "storage_path": None,
        "size": 0,
        "documents_count": 0,
        "collections_count": 0,
        "created_by": created_by,
        "created_at": now.isoformat(),
        "completed_at": None,
        "is_deleted": False,
    }
    await db.backups.insert_one(doc)
    asyncio.create_task(_run_backup(backup_id))
    doc.pop("_id", None)
    return doc


# ==================== Endpoints de gestión (superadmin) ====================
@router.get("")
async def listar_backups(current_user: dict = Depends(require_role("superadmin"))):
    cursor = db.backups.find({"is_deleted": {"$ne": True}}, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(1000)
    return {"data": items, "total": len(items)}


@router.post("/run")
async def ejecutar_backup_manual(current_user: dict = Depends(require_role("superadmin"))):
    doc = await _crear_backup("manual", current_user.get("username", "manual"))
    return doc


@router.get("/{backup_id}/download")
async def descargar_backup(backup_id: str, current_user: dict = Depends(require_role("superadmin"))):
    rec = await db.backups.find_one({"id": backup_id, "is_deleted": {"$ne": True}}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Respaldo no encontrado")
    if rec.get("status") != "completado" or not rec.get("storage_path"):
        raise HTTPException(status_code=409, detail="El respaldo aún no está disponible")
    data = get_object(rec["storage_path"])
    return Response(
        content=data,
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="{rec["filename"]}"'},
    )


@router.delete("/{backup_id}")
async def eliminar_backup(backup_id: str, current_user: dict = Depends(require_role("superadmin"))):
    rec = await db.backups.find_one({"id": backup_id})
    if not rec:
        raise HTTPException(status_code=404, detail="Respaldo no encontrado")
    await db.backups.update_one({"id": backup_id}, {"$set": {"is_deleted": True}})
    return {"message": "Respaldo eliminado"}


# ==================== Cron webhook ====================
@cron_router.post("/backup")
async def cron_backup(authorization: str = Header(None)):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    expected = f"Bearer {secret}"
    if not secret or not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="No autorizado")
    doc = await _crear_backup("automatico", "cron")
    return {"accepted": True, "backup_id": doc["id"]}
