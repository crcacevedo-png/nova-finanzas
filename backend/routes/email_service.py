"""Servicio de correo (integración de email gestionada por Emergent / Resend).

Envía el reporte de Cierre Diario de NovaVisión a destinatarios fijos definidos
en el servidor. El cuerpo HTML se construye SIEMPRE en el servidor a partir del
diagnóstico de cierre (nunca se acepta HTML ni destinatarios del cliente).
"""
import os
import re
import ipaddress
import logging
import hmac
import asyncio
import httpx
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from dotenv import load_dotenv

from utils.timezone import today_str_gt, now_gt
from routes.auth import require_role

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter()

# Proxy de email gestionado por Emergent. Es una CONSTANTE — nunca leer de env.
EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "NovaVisión")
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")
WEBHOOK_CRON_SECRET = os.environ.get("WEBHOOK_CRON_SECRET")


def _destinatarios():
    raw = os.environ.get("CIERRE_DIARIO_EMAILS", "")
    return [e.strip() for e in raw.split(",") if e.strip()]


# ==================== GUARDRAIL GATE (copiar tal cual; llamar en cada envío) ====================
_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan(); scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str, reply_to: Optional[str] = None) -> Optional[str]:
    _assert_safe_email(subject, html)
    if not EMAIL_KEY:
        raise HTTPException(status_code=503, detail="Email no configurado (falta EMERGENT_EMAIL_KEY)")
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    if reply_to or EMAIL_REPLY_TO:
        payload["contact_email"] = reply_to or EMAIL_REPLY_TO
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": EMAIL_KEY},
                json=payload,
            )
        resp.raise_for_status()
        return resp.json().get("id")
    except httpx.HTTPStatusError as e:
        try:
            code = e.response.json().get("code", "")
        except ValueError:
            code = ""
        if code in ("insufficient_credits", "integration_disabled", "daily_limit_reached"):
            logger.warning(f"Email pausado: {code} ({e.response.status_code}): {e.response.json().get('message', '')}")
            raise HTTPException(status_code=503, detail="El envío de correo está temporalmente no disponible")
        logger.error(f"Email send failed: {e.response.status_code} {e.response.text}")
        try:
            msg = e.response.json().get("message", "")
        except ValueError:
            msg = ""
        raise HTTPException(status_code=502, detail=f"No se pudo enviar el correo{': ' + msg if msg else ''}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email send error: {str(e)}")
        raise HTTPException(status_code=500, detail="No se pudo enviar el correo")


# ==================== PLANTILLA HTML DEL CIERRE DIARIO ====================
def _q(n) -> str:
    try:
        return f"Q{float(n):,.2f}"
    except (TypeError, ValueError):
        return "Q0.00"


_METODO_LABEL = {"efectivo": "Efectivo", "tarjeta": "Tarjeta", "transferencia": "Transferencia",
                 "cheque": "Cheque", "otro": "Otro"}


def _cards_row(resumen: dict, with_egresos: bool = True) -> str:
    cards = [
        ("Ingreso facturado", _q(resumen.get("ingreso_facturado")), "#1e3a8a", "Incluye cuentas por cobrar"),
        ("Cobrado", _q(resumen.get("total_cobrado")), "#047857", "Dinero recibido"),
        ("Cuentas por cobrar", _q(resumen.get("cxc_generada_hoy")), "#b45309", "Pendiente de hoy"),
        ("Abonos previos", _q(resumen.get("abonos_cuentas_previas")), "#6d28d9", "Cuentas anteriores"),
    ]
    if with_egresos:
        cards.append(("Egresos", _q(resumen.get("egresos")), "#b91c1c", "Salidas de caja"))
    out = ""
    for titulo, valor, color, sub in cards:
        out += (
            f'<td style="padding:6px;" valign="top"><div style="border:1px solid #e5e7eb;border-radius:10px;'
            f'padding:12px 14px;background:#ffffff">'
            f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em">{escape(titulo)}</div>'
            f'<div style="font-size:19px;font-weight:700;color:{color};margin-top:3px">{escape(valor)}</div>'
            f'<div style="font-size:10px;color:#9ca3af;margin-top:3px">{escape(sub)}</div></div></td>'
        )
    return out


def _metodos_rows(metodos: dict) -> str:
    rows = ""
    for k in ("efectivo", "tarjeta", "transferencia", "cheque", "otro"):
        val = (metodos or {}).get(k, 0) or 0
        if val == 0 and k == "otro":
            continue
        rows += (
            f'<tr><td style="padding:6px 12px;border-bottom:1px solid #f1f5f9">{escape(_METODO_LABEL.get(k, k))}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #f1f5f9;text-align:right;font-weight:600">{escape(_q(val))}</td></tr>'
        )
    return rows or '<tr><td colspan="2" style="padding:10px;text-align:center;color:#9ca3af">Sin cobros</td></tr>'


def _ventas_rows(ventas: list) -> str:
    rows = ""
    for v in (ventas or []):
        rows += (
            f'<tr><td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;white-space:nowrap">{escape(str(v.get("numero", "—")))}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #f1f5f9">{escape(str(v.get("usuario", "—")))}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #f1f5f9">{escape(str(v.get("cliente", "—")))}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;color:#6b7280">{escape(str(v.get("concepto", "—")))}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;white-space:nowrap">{escape(_q(v.get("total")))}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;color:#047857;white-space:nowrap">{escape(_q(v.get("cobrado")))}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;color:#b45309;white-space:nowrap">{escape(_q(v.get("pendiente")))}</td></tr>'
        )
    return rows or '<tr><td colspan="7" style="padding:12px;text-align:center;color:#9ca3af">Sin ventas este día</td></tr>'


def _usuarios_rows(usuarios: list) -> str:
    rows = ""
    for u in (usuarios or []):
        rows += (
            f'<tr><td style="padding:6px 10px;border-bottom:1px solid #f1f5f9">{escape(str(u.get("usuario_nombre", "—")))}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f1f5f9;text-align:center">{escape(str(u.get("num_ventas", 0)))}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f1f5f9;text-align:right">{escape(_q(u.get("facturado")))}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f1f5f9;text-align:right;color:#047857">{escape(_q(u.get("cobrado")))}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f1f5f9;text-align:right;color:#b45309">{escape(_q(u.get("cxc_generada")))}</td></tr>'
        )
    return rows or '<tr><td colspan="5" style="padding:12px;text-align:center;color:#9ca3af">Sin ventas registradas</td></tr>'


def _modulo_block(titulo: str, color: str, mod: dict, with_egresos: bool) -> str:
    resumen = (mod or {}).get("resumen", {})
    return (
        f'<tr><td style="padding:18px 24px 4px"><div style="font-size:16px;font-weight:700;color:{color};'
        f'border-left:4px solid {color};padding-left:10px">{escape(titulo)}</div></td></tr>'
        f'<tr><td style="padding:6px 18px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{_cards_row(resumen, with_egresos)}</tr></table></td></tr>'
        f'<tr><td style="padding:6px 24px 2px"><div style="font-size:13px;font-weight:700;color:#0f172a;margin-bottom:4px">Cobrado por método</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:12px;color:#374151;border:1px solid #e5e7eb;border-radius:8px">{_metodos_rows((mod or {}).get("cobrado_por_metodo", {}))}</table></td></tr>'
        f'<tr><td style="padding:10px 24px 2px"><div style="font-size:13px;font-weight:700;color:#0f172a;margin-bottom:4px">Ventas por usuario</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:12px;color:#374151;border:1px solid #e5e7eb;border-radius:8px">'
        f'<tr style="background:#f8fafc"><th style="padding:6px 10px;text-align:left">Usuario</th><th style="padding:6px 10px;text-align:center">Ventas</th>'
        f'<th style="padding:6px 10px;text-align:right">Facturado</th><th style="padding:6px 10px;text-align:right">Cobrado</th><th style="padding:6px 10px;text-align:right">CxC</th></tr>'
        f'{_usuarios_rows((mod or {}).get("por_usuario", []))}</table></td></tr>'
        f'<tr><td style="padding:10px 24px 6px"><div style="font-size:13px;font-weight:700;color:#0f172a;margin-bottom:4px">Ventas del día</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:11px;color:#374151;border:1px solid #e5e7eb;border-radius:8px">'
        f'<tr style="background:#f8fafc"><th style="padding:6px 8px;text-align:left">Documento</th><th style="padding:6px 8px;text-align:left">Usuario</th>'
        f'<th style="padding:6px 8px;text-align:left">Cliente</th><th style="padding:6px 8px;text-align:left">Concepto</th>'
        f'<th style="padding:6px 8px;text-align:right">Total</th><th style="padding:6px 8px;text-align:right">Cobrado</th><th style="padding:6px 8px;text-align:right">Pendiente</th></tr>'
        f'{_ventas_rows((mod or {}).get("ventas", []))}</table></td></tr>'
    )


def build_cierre_html(data: dict) -> str:
    fecha = escape(str(data.get("fecha", "")))
    general = data.get("general", {})
    conc = data.get("conciliacion_cajas", [])
    conc_rows = ""
    for c in conc:
        dif = c.get("diferencia")
        dif_txt = "—" if dif is None else _q(dif)
        dif_color = "#6b7280" if dif is None else ("#047857" if abs(dif) < 0.01 else "#b91c1c")
        contado = c.get("efectivo_contado")
        contado_txt = "Sin cerrar" if contado is None else _q(contado)
        conc_rows += (
            f'<tr><td style="padding:6px 10px;border-bottom:1px solid #f1f5f9">{escape(str(c.get("cajero", "—")))}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f1f5f9;text-align:center">{escape(str(c.get("estado", "—")))}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f1f5f9;text-align:right">{escape(_q(c.get("efectivo_esperado")))}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f1f5f9;text-align:right">{escape(contado_txt)}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f1f5f9;text-align:right;color:{dif_color};font-weight:600">{escape(dif_txt)}</td></tr>'
        )
    if not conc_rows:
        conc_rows = '<tr><td colspan="5" style="padding:12px;text-align:center;color:#9ca3af">Sin cajas abiertas este día</td></tr>'

    generado = escape(now_gt().strftime("%d/%m/%Y %H:%M"))

    return (
        f'<div style="background:#f3f4f6;padding:24px 0;font-family:Arial,Helvetica,sans-serif">'
        f'<table role="presentation" width="720" align="center" cellpadding="0" cellspacing="0" '
        f'style="max-width:720px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e5e7eb">'
        f'<tr><td style="background:#0f172a;padding:22px 28px">'
        f'<div style="color:#ffffff;font-size:20px;font-weight:700">NovaVisión — Cierre del Día</div>'
        f'<div style="color:#94a3b8;font-size:13px;margin-top:2px">Diagnóstico de cierre · {fecha}</div></td></tr>'
        f'<tr><td style="padding:16px 18px 2px"><div style="font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;padding-left:6px">Resumen general (Clínica + Óptica)</div></td></tr>'
        f'<tr><td style="padding:4px 18px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{_cards_row(general, True)}</tr></table></td></tr>'
        f'{_modulo_block("Clínica", "#2563eb", data.get("clinica", {}), True)}'
        f'{_modulo_block("Óptica", "#4f46e5", data.get("optica", {}), False)}'
        f'<tr><td style="padding:16px 24px 10px"><div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:6px">Conciliación de cajas (Clínica)</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:12px;color:#374151;border:1px solid #e5e7eb;border-radius:8px">'
        f'<tr style="background:#f8fafc"><th style="padding:7px 10px;text-align:left">Cajero</th>'
        f'<th style="padding:7px 10px;text-align:center">Estado</th>'
        f'<th style="padding:7px 10px;text-align:right">Efectivo esperado</th>'
        f'<th style="padding:7px 10px;text-align:right">Contado</th>'
        f'<th style="padding:7px 10px;text-align:right">Diferencia</th></tr>{conc_rows}</table></td></tr>'
        f'<tr><td style="padding:14px 28px 24px"><div style="font-size:11px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:12px">'
        f'Reporte generado automáticamente por NovaVisión ERP el {generado} (hora de Guatemala). '
        f'Nunca solicitamos contraseñas ni datos de tarjeta por correo.</div></td></tr>'
        f'</table></div>'
    )


async def enviar_cierre_diario(fecha_dia: str) -> dict:
    """Calcula el cierre del día y lo envía por correo a los destinatarios fijos."""
    from routes.caja import calcular_cierre_diario  # import diferido para evitar ciclo
    data = await calcular_cierre_diario(fecha_dia)
    html = build_cierre_html(data)
    subject = f"Cierre del día NovaVisión — {fecha_dia}"
    destinatarios = _destinatarios()
    enviados, errores = [], []
    for correo in destinatarios:
        try:
            email_id = await send_email(to=correo, subject=subject, html=html)
            enviados.append({"to": correo, "id": email_id})
        except HTTPException as e:
            errores.append({"to": correo, "error": e.detail})
        except Exception as e:
            errores.append({"to": correo, "error": str(e)})
    return {"fecha": fecha_dia, "enviados": enviados, "errores": errores, "resumen": data.get("general")}


# ==================== ENDPOINTS ====================
@router.post("/caja/cierre-diario/enviar")
async def enviar_cierre_diario_manual(
    fecha: Optional[str] = None,
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """Envío manual del cierre diario por correo (Admin/SuperAdmin)."""
    fecha_dia = fecha or today_str_gt()
    destinatarios = _destinatarios()
    if not destinatarios:
        raise HTTPException(status_code=400, detail="No hay destinatarios configurados")
    resultado = await enviar_cierre_diario(fecha_dia)
    if resultado["errores"] and not resultado["enviados"]:
        raise HTTPException(status_code=502, detail=f"No se pudo enviar el cierre: {resultado['errores'][0]['error']}")
    return {
        "message": f"Cierre enviado a {len(resultado['enviados'])} destinatario(s)",
        "destinatarios": [e["to"] for e in resultado["enviados"]],
        "errores": resultado["errores"],
    }


@router.post("/cron/cierre-diario")
async def cron_cierre_diario(request: Request, background_tasks: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not WEBHOOK_CRON_SECRET or not token or not hmac.compare_digest(token, WEBHOOK_CRON_SECRET):
        raise HTTPException(status_code=401, detail="No autorizado")
    fecha_dia = today_str_gt()
    background_tasks.add_task(_run_cron_cierre, fecha_dia)
    return {"status": "accepted", "fecha": fecha_dia}


async def _run_cron_cierre(fecha_dia: str):
    try:
        resultado = await enviar_cierre_diario(fecha_dia)
        logger.info(f"Cierre diario {fecha_dia} enviado: {len(resultado['enviados'])} ok, {len(resultado['errores'])} errores")
    except Exception as e:
        logger.error(f"Error enviando cierre diario {fecha_dia}: {e}")
