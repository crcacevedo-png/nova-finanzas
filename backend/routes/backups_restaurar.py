# /app/backend/routes/backups_restaurar.py
# Restaurar un respaldo COMPLETO (solo superadmin), en dos pasos:
# 1) Revisión (solo lectura): compara el respaldo con los datos actuales en todos los módulos y
#    lista quién tiene sesión abierta. Vale 15 minutos y solo para quien la hizo.
# 2) Con la palabra RESTAURAR: respaldo previo OBLIGATORIO (si falla no se toca nada) → copia de
#    cada colección del respaldo en una temporal con los mismos índices (si falla, no se toca nada)
#    → reemplazo colección por colección.
# Nunca se tocan: audit_logs, la lista de respaldos, las restauraciones, la actividad de sesiones
# y los tokens cerrados. Todo queda en audit_logs.
import asyncio
import gzip
import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from bson import ObjectId, SON
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from config.database import db
from routes import backups as respaldos
from routes.auth import require_role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backups", tags=["Respaldos"])
SUPER = require_role("superadmin")

PALABRA = "RESTAURAR"
VIGENCIA_MIN = 15
SESION_ABIERTA_MIN = 30
TMP = "__rest_tmp_"
CANDADO = "candado"
LOTE = 500
NO_SE_TOCAN = ("audit_logs", "backups", "restauraciones", "sesiones_actividad", "token_blacklist")
GRUPOS = (
    ("Pacientes", ("patients",)),
    ("Evaluaciones", ("evaluaciones_oftalmologicas",)),
    ("Citas", ("citas",)),
    ("Pagos", ("payments", "optica_sale_payments", "caja_movimientos", "caja_chica_movimientos")),
    ("Ventas", ("ventas", "optica_sales")),
    ("Órdenes IGSS", ("igss_ordenes_libro",)),
)
NOMBRES = {
    "patients": "Pacientes", "evaluaciones_oftalmologicas": "Evaluaciones", "citas": "Citas",
    "payments": "Pagos de gastos", "optica_sale_payments": "Pagos de ventas de óptica",
    "caja_movimientos": "Movimientos de caja", "caja_chica_movimientos": "Caja chica",
    "ventas": "Ventas de clínica", "optica_sales": "Ventas de óptica", "igss_ordenes_libro": "Órdenes IGSS (libro)",
    "surgeries": "Cirugías", "users": "Usuarios", "expenses": "Gastos", "cuentas_por_cobrar": "Cuentas por cobrar",
    "igss_nogs": "NOG IGSS", "igss_nog_acreditaciones": "Cupos IGSS (acreditaciones)", "igss_units": "Unidades IGSS",
    "igss_libro_ajustes_cupo": "Cupos IGSS sin SPS", "igss_migracion_lotes": "Lotes de migración IGSS",
    "anesthesia_records": "Registros de anestesia", "notas_cirugia": "Notas de cirugía", "caja_cierres": "Cierres de caja",
    "security_alerts": "Alertas de seguridad", "system_flags": "Pasos únicos del sistema", "roles": "Roles",
}
_tareas = set()


class _Cancelada(Exception):
    """Se detuvo antes de tocar los datos: no se restauró nada."""


class Restaurar(BaseModel):
    revision_id: str
    palabra: str


def _ahora():
    return datetime.now(timezone.utc)


def _restaurable(nombre: str) -> bool:
    return nombre not in NO_SE_TOCAN and not nombre.startswith(("system.", TMP))


def _huella(doc: dict) -> bytes:
    return hashlib.blake2b(json.dumps(doc, sort_keys=True, ensure_ascii=False, default=str).encode(), digest_size=16).digest()


def _huellas(docs: list) -> dict:
    return {str(d.get("_id")): _huella(d) for d in docs}


def _oid(v):
    """El respaldo guarda el _id como texto: vuelve a ObjectId."""
    return ObjectId(v) if isinstance(v, str) and len(v) == 24 and ObjectId.is_valid(v) else v


def _nombre(user: dict) -> str:
    return user.get("name") or user.get("username", "")


def _lanzar(coro):
    t = asyncio.create_task(coro)
    _tareas.add(t)
    t.add_done_callback(_tareas.discard)


async def _audit(accion: str, user: dict, detalles: dict):
    await db.audit_logs.insert_one({"id": str(uuid.uuid4()), "action": accion, "user_id": user.get("id", ""),
                                    "user_name": _nombre(user), "timestamp": _ahora().isoformat(), "details": detalles})


async def _respaldo_ok(backup_id: str) -> dict:
    rec = await db.backups.find_one({"id": backup_id, "is_deleted": {"$ne": True}}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Respaldo no encontrado")
    if rec.get("status") != "completado" or not rec.get("storage_path"):
        raise HTTPException(status_code=409, detail="El respaldo no está completo")
    return rec


async def _cargar_respaldo(rec: dict) -> dict:
    gz = await asyncio.to_thread(respaldos.get_object, rec["storage_path"])
    return (await asyncio.to_thread(lambda: json.loads(gzip.decompress(gz))))["data"]


async def _nueva_tarea(tipo: str, rec: dict, user: dict, **extra) -> dict:
    doc = {"id": str(uuid.uuid4()), "tipo": tipo, "backup_id": rec["id"],
           "respaldo": {k: rec.get(k) for k in ("id", "filename", "tipo", "created_at", "completed_at", "documents_count")},
           "estado": "en_curso", "paso_actual": None, "pasos": [], "created_by": user["id"],
           "created_by_nombre": _nombre(user), "created_at": _ahora().isoformat(), **extra}
    await db.restauraciones.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def _iniciar_paso(tarea_id: str, paso: str):
    await db.restauraciones.update_one({"id": tarea_id}, {"$set": {"paso_actual": paso}})
    return _ahora()


async def _fin_paso(tarea_id: str, paso: str, inicio, **extra):
    await db.restauraciones.update_one({"id": tarea_id}, {"$push": {"pasos": {
        "paso": paso, "segundos": round((_ahora() - inicio).total_seconds(), 1), **extra}}})


async def _terminar(tarea_id: str, estado: str, inicio, **campos):
    await db.restauraciones.update_one({"id": tarea_id}, {"$set": {
        "estado": estado, "paso_actual": None, "terminado_en": _ahora().isoformat(),
        "segundos": round((_ahora() - inicio).total_seconds(), 1), **campos}})


# ==================== REVISIÓN (solo lectura) ====================

async def _comparar(nombre: str, en_respaldo: dict, existe: bool) -> dict:
    creados = cambiados = vistos = ahora = 0
    if existe:
        cursor = db[nombre].find({})
        while lote := await cursor.to_list(1000):
            for k, h in (await asyncio.to_thread(_huellas, lote)).items():
                ahora += 1
                previo = en_respaldo.get(k)
                if previo is None:
                    creados += 1
                else:
                    vistos += 1
                    cambiados += previo != h
    return {"coleccion": nombre, "nombre": NOMBRES.get(nombre, nombre), "en_respaldo": len(en_respaldo), "ahora": ahora,
            "creados": creados, "cambiados": cambiados, "borrados": len(en_respaldo) - vistos}


async def _impacto(data: dict) -> dict:
    actuales = {n for n in await db.list_collection_names() if _restaurable(n)}
    cols = []
    for nombre in sorted(actuales | {n for n in data if _restaurable(n)}):
        huellas = await asyncio.to_thread(_huellas, data.get(nombre, []))
        cols.append(await _comparar(nombre, huellas, nombre in actuales))
    por = {c["coleccion"]: c for c in cols}
    claves = ("creados", "cambiados", "borrados")
    grupos = [{"nombre": g, "colecciones": list(cs), **{k: sum(por.get(c, {}).get(k, 0) for c in cs) for k in claves}}
              for g, cs in GRUPOS]
    con_cambios = [c for c in cols if c["creados"] or c["cambiados"] or c["borrados"]]
    return {"grupos": grupos, "colecciones": con_cambios, "colecciones_sin_cambios": len(cols) - len(con_cambios),
            "total": {k: sum(c[k] for c in cols) for k in claves}, "no_se_tocan": list(NO_SE_TOCAN)}


async def _sesiones_abiertas(user_id: str) -> list:
    desde = (_ahora() - timedelta(minutes=SESION_ABIERTA_MIN)).isoformat()
    return await db.sesiones_actividad.find({"ultima_actividad": {"$gte": desde}, "user_id": {"$ne": user_id}},
                                            {"_id": 0}).sort("ultima_actividad", -1).to_list(200)


async def _revisar(tarea_id: str, rec: dict, user: dict):
    inicio = await _iniciar_paso(tarea_id, "revision")
    try:
        data = await _cargar_respaldo(rec)
        impacto = await _impacto(data)
        del data
        sesiones = await _sesiones_abiertas(user["id"])
        await _fin_paso(tarea_id, "revision", inicio)
        await _terminar(tarea_id, "listo", inicio, resultado={
            **impacto, "sesiones": sesiones, "vence": (_ahora() + timedelta(minutes=VIGENCIA_MIN)).isoformat()})
        await _audit("RESPALDO_RESTAURACION_REVISADA", user, {
            "revision_id": tarea_id, "backup_id": rec["id"], "respaldo_fecha": rec.get("created_at"),
            "grupos": {g["nombre"]: {k: g[k] for k in ("creados", "cambiados", "borrados")} for g in impacto["grupos"]},
            "total": impacto["total"], "sesiones_abiertas": [s.get("nombre") for s in sesiones]})
    except Exception as e:
        logger.exception("Revisión de restauración falló")
        await _terminar(tarea_id, "error", inicio, error=f"No se pudo leer el respaldo: {str(e)[:300]}")


# ==================== RESTAURACIÓN ====================

async def _tomar_candado(user: dict) -> bool:
    now = _ahora()
    try:
        await db.restauraciones.find_one_and_update(
            {"_id": CANDADO, "$or": [{"activo": False}, {"expira": {"$lt": now.isoformat()}}]},
            {"$set": {"activo": True, "por": user.get("id"), "expira": (now + timedelta(hours=1)).isoformat()}}, upsert=True)
        return True
    except DuplicateKeyError:
        return False


async def _limpiar_temporales():
    for n in await db.list_collection_names():
        if n.startswith(TMP):
            await db.drop_collection(n)


async def _probar_renombrar():
    a, b = f"{TMP}prueba_a", f"{TMP}prueba_b"
    await db[a].insert_one({"prueba": True})
    await db[a].rename(b, dropTarget=True)
    await db.drop_collection(b)


async def _preparar(data: dict) -> tuple:
    """Copia cada colección del respaldo en una temporal con los índices actuales. No toca datos reales."""
    await _limpiar_temporales()
    await _probar_renombrar()
    actuales = set(await db.list_collection_names())
    tv = {u["id"]: u.get("token_version") or 1 async for u in db.users.find({}, {"_id": 0, "id": 1, "token_version": 1}) if u.get("id")}
    preparadas = []
    for nombre in sorted(n for n in data if _restaurable(n)):
        tmp, docs = TMP + nombre, data[nombre]
        await db.create_collection(tmp)
        for d in docs:
            if "_id" in d:
                d["_id"] = _oid(d["_id"])
            if nombre == "users" and d.get("id") in tv:  # las sesiones cerradas después del respaldo siguen cerradas
                d["token_version"] = max(int(d.get("token_version") or 1), int(tv[d["id"]]))
        for i in range(0, len(docs), LOTE):
            await db[tmp].insert_many(docs[i:i + LOTE], ordered=True)
        if nombre in actuales:
            specs = [SON((k, v) for k, v in s.items() if k != "ns") async for s in db[nombre].list_indexes() if s["name"] != "_id_"]
            if specs:
                await db.command(SON([("createIndexes", tmp), ("indexes", specs)]))
        preparadas.append(nombre)
    vaciar = sorted(n for n in actuales if _restaurable(n) and n not in data)
    return preparadas, vaciar


async def _ejecutar(tarea_id: str, rec: dict, rev: dict, user: dict):
    inicio, tocado, previo_id = _ahora(), False, None
    base = {"tarea_id": tarea_id, "backup_id": rec["id"], "respaldo_fecha": rec.get("created_at"), "archivo": rec.get("filename")}
    try:
        res = rev.get("resultado") or {}
        await _audit("RESPALDO_RESTAURACION_INICIADA", user, {
            **base, "total": res.get("total"), "sesiones_abiertas": [s.get("nombre") for s in res.get("sesiones", [])],
            "grupos": {g["nombre"]: {k: g[k] for k in ("creados", "cambiados", "borrados")} for g in res.get("grupos", [])}})
        t = await _iniciar_paso(tarea_id, "respaldo_previo")
        previo = await respaldos.registrar_backup("previo_restauracion", user.get("username", ""))
        previo_id = previo["id"]
        await db.restauraciones.update_one({"id": tarea_id}, {"$set": {"respaldo_previo_id": previo_id, "respaldo_previo_archivo": previo["filename"]}})
        await respaldos._run_backup(previo_id)
        hecho = await db.backups.find_one({"id": previo_id}, {"_id": 0, "status": 1, "error": 1, "documents_count": 1})
        if (hecho or {}).get("status") != "completado":
            raise _Cancelada(f"El respaldo previo falló ({(hecho or {}).get('error') or 'sin detalle'}). No se restauró nada.")
        await _fin_paso(tarea_id, "respaldo_previo", t, backup_id=previo_id, documentos=hecho.get("documents_count"))

        t = await _iniciar_paso(tarea_id, "lectura")
        data = await _cargar_respaldo(rec)
        await _fin_paso(tarea_id, "lectura", t, documentos=sum(len(v) for v in data.values()))

        t = await _iniciar_paso(tarea_id, "preparacion")
        preparadas, vaciar = await _preparar(data)
        del data
        await _fin_paso(tarea_id, "preparacion", t, colecciones=len(preparadas))

        t = await _iniciar_paso(tarea_id, "reemplazo")
        tocado = True
        for nombre in preparadas:
            await db[TMP + nombre].rename(nombre, dropTarget=True)
        for nombre in vaciar:  # no existían al hacer el respaldo: quedan vacías (conservan sus índices)
            await db[nombre].delete_many({})
        await _fin_paso(tarea_id, "reemplazo", t, colecciones=len(preparadas), vaciadas=vaciar)

        await _terminar(tarea_id, "listo", inicio)
        hecha = await db.restauraciones.find_one({"id": tarea_id}, {"_id": 0, "pasos": 1, "segundos": 1})
        await _audit("RESPALDO_RESTAURACION_COMPLETADA", user, {**base, "respaldo_previo_id": previo_id, **hecha})
    except Exception as e:
        if not tocado:
            await _limpiar_temporales()
            msg = str(e) if isinstance(e, _Cancelada) else f"Se detuvo antes de tocar los datos ({str(e)[:300]}). No se restauró nada."
            await _terminar(tarea_id, "cancelada", inicio, error=msg)
            await _audit("RESPALDO_RESTAURACION_CANCELADA", user, {**base, "respaldo_previo_id": previo_id, "motivo": msg})
        else:
            logger.exception("Restauración falló a medias")
            msg = (f"La restauración se detuvo a medias ({str(e)[:300]}). Para volver al estado anterior, "
                   f"restaure el respaldo previo ({previo_id}).")
            await _terminar(tarea_id, "error", inicio, error=msg, parcial=True)
            await _audit("RESPALDO_RESTAURACION_FALLIDA", user, {**base, "respaldo_previo_id": previo_id, "motivo": msg})
    finally:
        await db.restauraciones.update_one({"_id": CANDADO}, {"$set": {"activo": False}})


# ==================== ENDPOINTS ====================

@router.post("/{backup_id}/restaurar/revisar")
async def revisar_restauracion(backup_id: str, current_user: dict = Depends(SUPER)):
    rec = await _respaldo_ok(backup_id)
    tarea = await _nueva_tarea("revision", rec, current_user)
    _lanzar(_revisar(tarea["id"], rec, current_user))
    return tarea


@router.post("/restaurar")
async def restaurar(body: Restaurar, current_user: dict = Depends(SUPER)):
    if body.palabra != PALABRA:
        raise HTTPException(status_code=400, detail=f"Escriba {PALABRA} para confirmar")
    rev = await db.restauraciones.find_one({"id": body.revision_id, "tipo": "revision"}, {"_id": 0})
    if not rev or rev.get("estado") != "listo":
        raise HTTPException(status_code=409, detail="Primero revise el respaldo")
    if rev.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Esta revisión la hizo otro usuario: revise usted el respaldo")
    if (rev.get("resultado") or {}).get("vence", "") < _ahora().isoformat():
        raise HTTPException(status_code=409, detail=f"La revisión venció ({VIGENCIA_MIN} min): vuelva a revisar el respaldo")
    rec = await _respaldo_ok(rev["backup_id"])
    if not await _tomar_candado(current_user):
        raise HTTPException(status_code=409, detail="Ya hay una restauración en curso")
    usada = await db.restauraciones.update_one({"id": rev["id"], "usada": {"$ne": True}}, {"$set": {"usada": True}})
    if not usada.modified_count:
        await db.restauraciones.update_one({"_id": CANDADO}, {"$set": {"activo": False}})
        raise HTTPException(status_code=409, detail="Esta revisión ya se usó: vuelva a revisar el respaldo")
    tarea = await _nueva_tarea("restauracion", rec, current_user, revision_id=rev["id"])
    _lanzar(_ejecutar(tarea["id"], rec, rev, current_user))
    return tarea


@router.get("/restauraciones")
async def listar_restauraciones(current_user: dict = Depends(SUPER)):
    docs = await db.restauraciones.find({"tipo": "restauracion"}, {"_id": 0}).sort("created_at", -1).to_list(10)
    return {"data": docs}


@router.get("/restauraciones/{tarea_id}")
async def ver_tarea(tarea_id: str, current_user: dict = Depends(SUPER)):
    doc = await db.restauraciones.find_one({"id": tarea_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="No encontrada")
    return doc
