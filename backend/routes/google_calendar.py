# /app/backend/routes/google_calendar.py
# Integración con Google Calendar: OAuth por médico (conectado por SuperAdmin),
# sincronización bidireccional (push de citas del sistema -> Google, y pull de
# Google -> citas del sistema mediante syncToken). Un calendario dedicado por médico.
import os
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

from config.database import db
from routes.auth import get_current_user, require_role

router = APIRouter(tags=["Google Calendar"])

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI")
APP_PUBLIC_URL = os.environ.get("APP_PUBLIC_URL", "")
SCOPES = "https://www.googleapis.com/auth/calendar"
TOKEN_URI = "https://oauth2.googleapis.com/token"
TZ_NAME = "America/Guatemala"
TZ = ZoneInfo(TZ_NAME)
CAL_SUMMARY = "NovaVision - Citas"


# ==================== HELPERS OAUTH (bloqueantes -> usar en to_thread) ====================

def _exchange_code(code: str) -> dict:
    r = requests.post(TOKEN_URI, data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=20).json()
    if r.get("expires_in"):
        r["expiry"] = (datetime.now(timezone.utc) + timedelta(seconds=int(r["expires_in"]) - 60)).isoformat()
    return r


def _get_userinfo(access_token: str) -> dict:
    return requests.get("https://www.googleapis.com/oauth2/v2/userinfo",
                        headers={"Authorization": f"Bearer {access_token}"}, timeout=20).json()


def _creds_from_tokens(tokens: dict) -> Credentials:
    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=[SCOPES],
    )
    exp = tokens.get("expiry")
    if exp:
        try:
            dt = datetime.fromisoformat(exp)
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            creds.expiry = dt
        except Exception:
            pass
    return creds


async def _get_service(doctor: dict):
    """Construye el servicio de Calendar para un médico, refrescando el token si es necesario."""
    gc = doctor.get("google_calendar") or {}
    tokens = gc.get("tokens") or {}
    creds = _creds_from_tokens(tokens)

    def _refresh(c):
        if c.expired and c.refresh_token:
            c.refresh(GoogleRequest())
            return True
        return False

    try:
        refreshed = await asyncio.to_thread(_refresh, creds)
    except Exception:
        refreshed = False
    if refreshed:
        await db.doctors.update_one({"id": doctor["id"]}, {"$set": {
            "google_calendar.tokens.access_token": creds.token,
            "google_calendar.tokens.expiry": creds.expiry.replace(tzinfo=timezone.utc).isoformat() if creds.expiry else None,
        }})
    service = await asyncio.to_thread(lambda: build("calendar", "v3", credentials=creds, cache_discovery=False))
    return service


async def _ensure_calendar(doctor: dict) -> str:
    """Devuelve el id del calendario dedicado del médico, creándolo si no existe."""
    gc = doctor.get("google_calendar") or {}
    if gc.get("calendar_id"):
        return gc["calendar_id"]
    service = await _get_service(doctor)

    def _find_or_create():
        page = None
        while True:
            cl = service.calendarList().list(pageToken=page).execute()
            for c in cl.get("items", []):
                if c.get("summary") == CAL_SUMMARY:
                    return c["id"]
            page = cl.get("nextPageToken")
            if not page:
                break
        created = service.calendars().insert(body={"summary": CAL_SUMMARY, "timeZone": TZ_NAME}).execute()
        return created["id"]

    cal_id = await asyncio.to_thread(_find_or_create)
    await db.doctors.update_one({"id": doctor["id"]}, {"$set": {"google_calendar.calendar_id": cal_id}})
    return cal_id


# ==================== HELPERS DE CONVERSIÓN CITA <-> EVENTO ====================

def _event_body(cita: dict) -> dict:
    fecha = cita.get("fecha")
    hi = cita.get("hora_inicio")
    hf = cita.get("hora_fin") or hi
    summary = cita.get("paciente_nombre") or "Cita"
    return {
        "summary": summary,
        "description": (
            f"Cita NovaVision\n"
            f"Tipo: {cita.get('tipo_cita', '')}\n"
            f"Estado: {cita.get('estado', '')}\n"
            f"Notas: {cita.get('notas', '') or ''}"
        ),
        "start": {"dateTime": f"{fecha}T{hi}:00", "timeZone": TZ_NAME},
        "end": {"dateTime": f"{fecha}T{hf}:00", "timeZone": TZ_NAME},
        "extendedProperties": {"private": {"nova_cita_id": cita["id"]}},
    }


def _parse_dt(value: str):
    """Convierte un start/end de Google a (fecha 'YYYY-MM-DD', hora 'HH:MM') en hora de Guatemala."""
    if not value:
        return None, None
    if "T" not in value:  # evento de día completo
        return value, "00:00"
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        local = dt.astimezone(TZ)
        return local.strftime("%Y-%m-%d"), local.strftime("%H:%M")
    except Exception:
        return None, None


def _dur_min(f1, h1, f2, h2):
    try:
        a = datetime.strptime(f"{f1} {h1}", "%Y-%m-%d %H:%M")
        b = datetime.strptime(f"{f2} {h2}", "%Y-%m-%d %H:%M")
        d = int((b - a).total_seconds() / 60)
        return d if d > 0 else 30
    except Exception:
        return 30


# ==================== PUSH (sistema -> Google) ====================

async def push_cita(cita: dict):
    """Crea/actualiza el evento de Google para una cita. Nunca lanza excepción."""
    try:
        if not (CLIENT_ID and CLIENT_SECRET):
            return
        medico_id = cita.get("medico_id")
        if not medico_id:
            return
        doctor = await db.doctors.find_one({"id": medico_id})
        gc = (doctor or {}).get("google_calendar") or {}
        if not gc.get("connected"):
            return
        cal_id = gc.get("calendar_id") or "primary"
        service = await _get_service(doctor)
        body = _event_body(cita)
        ev_id = cita.get("google_event_id")

        def _do():
            if ev_id:
                try:
                    return service.events().update(calendarId=cal_id, eventId=ev_id, body=body).execute()
                except Exception:
                    return service.events().insert(calendarId=cal_id, body=body).execute()
            return service.events().insert(calendarId=cal_id, body=body).execute()

        ev = await asyncio.to_thread(_do)
        if ev and ev.get("id") and ev.get("id") != ev_id:
            await db.citas.update_one({"id": cita["id"]}, {"$set": {"google_event_id": ev["id"]}})
    except Exception as e:
        print("push_cita error:", e)


async def delete_cita_event(cita: dict):
    """Elimina el evento de Google asociado a una cita. Nunca lanza excepción."""
    try:
        medico_id = cita.get("medico_id")
        ev_id = cita.get("google_event_id")
        if not (medico_id and ev_id):
            return
        doctor = await db.doctors.find_one({"id": medico_id})
        gc = (doctor or {}).get("google_calendar") or {}
        if not gc.get("connected") or not gc.get("calendar_id"):
            return
        service = await _get_service(doctor)

        def _do():
            try:
                service.events().delete(calendarId=gc["calendar_id"], eventId=ev_id).execute()
            except Exception:
                pass

        await asyncio.to_thread(_do)
    except Exception as e:
        print("delete_cita_event error:", e)


# ==================== PULL (Google -> sistema) ====================

async def _apply_event(doctor, service, cal_id, ev, res):
    now = datetime.now(timezone.utc).isoformat()
    nova_id = (ev.get("extendedProperties", {}).get("private", {}) or {}).get("nova_cita_id")
    status = ev.get("status")

    if status == "cancelled":
        if nova_id:
            c = await db.citas.find_one({"id": nova_id})
            if c and c.get("estado") not in ["Atendida", "No asistió", "Cancelada"]:
                await db.citas.update_one({"id": nova_id}, {"$set": {"estado": "Cancelada", "fecha_actualizacion": now}})
                res["cancel"] += 1
        return

    start = ev.get("start", {})
    fecha, hora = _parse_dt(start.get("dateTime") or start.get("date"))
    if not fecha:
        return
    end = ev.get("end", {})
    fecha_f, hora_f = _parse_dt(end.get("dateTime") or end.get("date"))
    if not fecha_f:
        fecha_f, hora_f = fecha, hora
    dur = _dur_min(fecha, hora, fecha_f, hora_f)

    if nova_id:
        c = await db.citas.find_one({"id": nova_id})
        if c and c.get("estado") not in ["Atendida", "No asistió"]:
            changed = {}
            if c.get("fecha") != fecha:
                changed["fecha"] = fecha
            if c.get("hora_inicio") != hora:
                changed["hora_inicio"] = hora
                changed["hora_fin"] = hora_f
            if changed:
                changed["fecha_actualizacion"] = now
                await db.citas.update_one({"id": nova_id}, {"$set": changed})
                res["update"] += 1
        return

    # Evento nuevo creado directamente en Google -> crear cita externa
    new_id = str(uuid.uuid4())
    cita_doc = {
        "id": new_id,
        "paciente_id": "",
        "paciente_nombre": ev.get("summary") or "(Evento de Google Calendar)",
        "medico_id": doctor["id"],
        "medico_nombre": doctor.get("name", ""),
        "fecha": fecha,
        "hora_inicio": hora,
        "hora_fin": hora_f,
        "duracion_minutos": dur,
        "tipo_cita": "otro",
        "estado": "Agendada",
        "asistio": None,
        "hora_llegada": None,
        "hora_inicio_consulta": None,
        "hora_fin_consulta": None,
        "asignado_a_medico_id": doctor["id"],
        "asignado_a_medico_nombre": doctor.get("name", ""),
        "notas": ev.get("description", "") or "",
        "tipo_agenda": "pacientes",
        "google_event_id": ev.get("id"),
        "origen_google": True,
        "creado_por": "google",
        "creado_por_nombre": "Google Calendar",
        "fecha_creacion": now,
        "actualizado_por": None,
        "fecha_actualizacion": None,
    }
    await db.citas.insert_one(cita_doc)
    res["import"] += 1

    def _patch():
        try:
            service.events().patch(calendarId=cal_id, eventId=ev["id"],
                                   body={"extendedProperties": {"private": {"nova_cita_id": new_id}}}).execute()
        except Exception:
            pass

    await asyncio.to_thread(_patch)


async def _sync_doctor(doctor):
    gc = doctor.get("google_calendar") or {}
    cal_id = gc.get("calendar_id") or "primary"
    service = await _get_service(doctor)
    sync_token = gc.get("sync_token")
    res = {"import": 0, "update": 0, "cancel": 0}

    def _list(page_token, stoken):
        params = {"calendarId": cal_id, "singleEvents": True, "showDeleted": True, "maxResults": 250}
        if stoken:
            params["syncToken"] = stoken
        else:
            # Desde hoy en adelante (inicio del día en hora de Guatemala)
            hoy = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
            params["timeMin"] = hoy.isoformat()
        if page_token:
            params["pageToken"] = page_token
        return service.events().list(**params).execute()

    async def _collect(stoken):
        items = []
        next_sync = None
        page = None
        while True:
            resp = await asyncio.to_thread(_list, page, stoken)
            items.extend(resp.get("items", []))
            next_sync = resp.get("nextSyncToken") or next_sync
            page = resp.get("nextPageToken")
            if not page:
                break
        return items, next_sync

    try:
        events, next_sync = await _collect(sync_token)
    except Exception:
        # syncToken inválido (410 GONE) -> resincronización completa
        events, next_sync = await _collect(None)

    for ev in events:
        try:
            await _apply_event(doctor, service, cal_id, ev, res)
        except Exception as e:
            print("apply_event error:", e)

    if next_sync:
        await db.doctors.update_one({"id": doctor["id"]}, {"$set": {
            "google_calendar.sync_token": next_sync,
            "google_calendar.last_sync": datetime.now(timezone.utc).isoformat(),
        }})
    return res


# ==================== ENDPOINTS ====================

@router.get("/oauth/calendar/connect")
async def connect(doctor_id: str = Query(...), current_user: dict = Depends(require_role(["superadmin"]))):
    """Genera la URL de consentimiento de Google para conectar la cuenta de un médico."""
    if not (CLIENT_ID and CLIENT_SECRET and REDIRECT_URI):
        raise HTTPException(status_code=500, detail="Google Calendar no está configurado en el servidor")
    doctor = await db.doctors.find_one({"id": doctor_id})
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    state = uuid.uuid4().hex
    await db.gcal_oauth_state.insert_one({
        "state": state, "doctor_id": doctor_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return {"authorization_url": f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"}


@router.get("/oauth/calendar/callback")
async def callback(code: str = "", state: str = "", error: str = ""):
    """Callback de Google OAuth: intercambia el código, guarda tokens del médico y crea su calendario."""
    frontend = f"{APP_PUBLIC_URL}/agenda"
    if error or not code or not state:
        return RedirectResponse(f"{frontend}?gcal=error")
    st = await db.gcal_oauth_state.find_one({"state": state})
    if not st:
        return RedirectResponse(f"{frontend}?gcal=error")
    doctor_id = st["doctor_id"]
    await db.gcal_oauth_state.delete_one({"state": state})

    token = await asyncio.to_thread(_exchange_code, code)
    if not token.get("access_token"):
        return RedirectResponse(f"{frontend}?gcal=error")
    try:
        userinfo = await asyncio.to_thread(_get_userinfo, token["access_token"])
    except Exception:
        userinfo = {}

    await db.doctors.update_one({"id": doctor_id}, {"$set": {"google_calendar": {
        "connected": True,
        "email": userinfo.get("email", ""),
        "tokens": token,
        "calendar_id": "primary",
        "calendar_name": "Principal",
        "sync_token": None,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }}})

    return RedirectResponse(f"{frontend}?gcal=connected")


@router.get("/google-calendar/status")
async def status(current_user: dict = Depends(require_role(["superadmin"]))):
    """Lista médicos con su estado de conexión a Google Calendar."""
    doctors = await db.doctors.find({"is_active": True}, {"_id": 0}).sort("name", 1).to_list(200)
    out = []
    for d in doctors:
        gc = d.get("google_calendar") or {}
        out.append({
            "id": d["id"],
            "name": d.get("name"),
            "specialty": d.get("specialty", ""),
            "connected": bool(gc.get("connected")),
            "email": gc.get("email", ""),
            "calendar_id": gc.get("calendar_id"),
            "calendar_name": gc.get("calendar_name", ""),
            "last_sync": gc.get("last_sync"),
        })
    return {"data": out, "configured": bool(CLIENT_ID and CLIENT_SECRET)}


@router.get("/google-calendar/calendars")
async def list_calendars(doctor_id: str, current_user: dict = Depends(require_role(["superadmin"]))):
    """Lista TODOS los calendarios accesibles por la cuenta del médico (propios y compartidos)."""
    doctor = await db.doctors.find_one({"id": doctor_id})
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    gc = doctor.get("google_calendar") or {}
    if not gc.get("connected"):
        raise HTTPException(status_code=400, detail="El médico no tiene una cuenta de Google conectada")
    try:
        service = await _get_service(doctor)
        def _list():
            items = []
            page = None
            while True:
                resp = service.calendarList().list(pageToken=page, showHidden=False).execute()
                items.extend(resp.get("items", []))
                page = resp.get("nextPageToken")
                if not page:
                    break
            return items
        cals = await asyncio.to_thread(_list)
    except Exception as e:
        print("list_calendars error:", e)
        raise HTTPException(status_code=502, detail="No se pudieron obtener los calendarios de Google")
    data = [{
        "id": c.get("id"),
        "summary": c.get("summaryOverride") or c.get("summary", ""),
        "primary": bool(c.get("primary")),
        "access_role": c.get("accessRole", ""),
    } for c in cals]
    # Principal primero, luego alfabético
    data.sort(key=lambda x: (0 if x["primary"] else 1, x["summary"].lower()))
    return {"data": data, "selected": gc.get("calendar_id")}


@router.post("/google-calendar/select-calendar")
async def select_calendar(payload: dict, current_user: dict = Depends(require_role(["superadmin"]))):
    """Elige el calendario de origen/destino para un médico. Reinicia la sincronización
    (sync_token=None) para que la próxima lectura traiga todo desde hoy del nuevo calendario."""
    doctor_id = payload.get("doctor_id")
    calendar_id = payload.get("calendar_id")
    calendar_name = payload.get("calendar_name", "")
    if not doctor_id or not calendar_id:
        raise HTTPException(status_code=400, detail="doctor_id y calendar_id requeridos")
    doctor = await db.doctors.find_one({"id": doctor_id})
    if not doctor or not (doctor.get("google_calendar") or {}).get("connected"):
        raise HTTPException(status_code=400, detail="El médico no tiene una cuenta de Google conectada")
    await db.doctors.update_one({"id": doctor_id}, {"$set": {
        "google_calendar.calendar_id": calendar_id,
        "google_calendar.calendar_name": calendar_name,
        "google_calendar.sync_token": None,
    }})
    return {"message": "Calendario actualizado", "calendar_id": calendar_id}


@router.post("/google-calendar/disconnect")
async def disconnect(payload: dict, current_user: dict = Depends(require_role(["superadmin"]))):
    doctor_id = payload.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=400, detail="doctor_id requerido")
    await db.doctors.update_one({"id": doctor_id}, {"$unset": {"google_calendar": ""}})
    return {"message": "Cuenta de Google desconectada"}


@router.post("/google-calendar/sync")
async def sync(current_user: dict = Depends(get_current_user)):
    """Sincroniza (pull) los calendarios de todos los médicos conectados."""
    if not (CLIENT_ID and CLIENT_SECRET):
        return {"configured": False, "medicos_sincronizados": 0, "importadas": 0, "actualizadas": 0, "canceladas": 0}
    doctors = await db.doctors.find({"google_calendar.connected": True}).to_list(200)
    totals = {"import": 0, "update": 0, "cancel": 0}
    for doctor in doctors:
        try:
            r = await _sync_doctor(doctor)
            for k in totals:
                totals[k] += r[k]
        except Exception as e:
            print("sync_doctor error:", doctor.get("id"), e)
    return {
        "configured": True,
        "medicos_sincronizados": len(doctors),
        "importadas": totals["import"],
        "actualizadas": totals["update"],
        "canceladas": totals["cancel"],
    }
