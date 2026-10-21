"""Genera un PDF con el informe de seguridad de NovaVisión ERP."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable
)
from datetime import datetime

OUT = "/app/frontend/public/seguridad-novavision.pdf"
TEAL = colors.HexColor("#0F6E56")
GRAY = colors.HexColor("#4b5563")

styles = getSampleStyleSheet()
h_title = ParagraphStyle("t", parent=styles["Title"], textColor=TEAL, fontSize=22, spaceAfter=4)
h_sub = ParagraphStyle("s", parent=styles["Normal"], textColor=GRAY, fontSize=10, spaceAfter=2)
h_sec = ParagraphStyle("sec", parent=styles["Heading2"], textColor=TEAL, fontSize=13, spaceBefore=14, spaceAfter=6)
body = ParagraphStyle("b", parent=styles["Normal"], fontSize=10, leading=15, textColor=colors.HexColor("#1f2937"))
intro = ParagraphStyle("i", parent=body, spaceAfter=8)

doc = SimpleDocTemplate(OUT, pagesize=letter, topMargin=0.8*inch, bottomMargin=0.8*inch,
                        leftMargin=0.9*inch, rightMargin=0.9*inch,
                        title="Informe de Seguridad - NovaVisión ERP")

def bullets(items):
    lis = [ListItem(Paragraph(x, body), leftIndent=6, value="•") for x in items]
    return ListFlowable(lis, bulletType="bullet", bulletColor=TEAL, bulletFontSize=9,
                        leftIndent=14, spaceBefore=2, spaceAfter=6)

story = []
story.append(Paragraph("Informe de Seguridad", h_title))
story.append(Paragraph("NovaVisión ERP — Sistema de gestión clínica", h_sub))
story.append(Paragraph("Generado el " + datetime.now().strftime("%d/%m/%Y"), h_sub))
story.append(Spacer(1, 6))
story.append(HRFlowable(width="100%", thickness=1.2, color=TEAL))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "Este documento resume las medidas de seguridad implementadas y verificadas en el código "
    "del sistema para prevenir vulnerabilidades. El sistema cuenta con una base de seguridad de "
    "nivel producción que cubre las principales categorías del OWASP Top 10.", intro))

sections = [
    ("Autenticación y sesiones", [
        "Contraseñas cifradas con <b>bcrypt</b> (salt único por usuario, nunca en texto plano).",
        "Tokens <b>JWT firmados (HS256)</b> con secreto tomado del entorno, no embebido en el código; expiración de 8 horas.",
        "Revocación de sesiones: blacklist de tokens persistente en MongoDB más <b>token_version</b> para cerrar todas las sesiones de un usuario a la vez.",
        "Tokens con algoritmo <b>none</b>, firma inválida o expirados son rechazados (con pruebas automatizadas).",
    ]),
    ("Protección contra ataques de acceso", [
        "<b>Rate limiting</b> en login: máximo 5 intentos por minuto (y 200/min global).",
        "<b>Bloqueo de cuenta</b> tras 5 intentos fallidos durante 15 minutos.",
        "Protección contra <b>inyección NoSQL</b> (operadores $gt, $regex en el login), con pruebas.",
        "Protección contra <b>mass assignment</b> (un usuario no puede auto-asignarse el rol administrador).",
    ]),
    ("Control de acceso", [
        "Permisos por <b>rol</b> evaluados en cada petición (require_permission / require_roles).",
        "Las respuestas de usuario <b>nunca</b> incluyen el campo de contraseña.",
        "Cuentas inactivas rechazadas automáticamente.",
    ]),
    ("Cabeceras y transporte", [
        "<b>X-Frame-Options: DENY</b> y CSP frame-ancestors 'none' (anti-clickjacking).",
        "X-Content-Type-Options: nosniff, X-XSS-Protection, Referrer-Policy y Permissions-Policy.",
        "<b>HSTS</b> forzado en producción (HTTPS obligatorio).",
        "<b>CORS restringido</b> a orígenes concretos (preview y dominio de producción), no comodín.",
    ]),
    ("Auditoría y trazabilidad", [
        "<b>Log de auditoría</b> persistente de acciones sensibles (quién, qué y cuándo).",
        "Panel de seguridad con conteo de inicios de sesión fallidos en 24 horas.",
        "Los errores no exponen trazas internas (stack traces) al cliente.",
    ]),
    ("Integridad de datos críticos (ERP)", [
        "Kárdex de inventario <b>sin endpoints de borrado ni edición</b> (inmutable por diseño).",
        "Expedientes de evaluación con <b>sellado</b> automático (no editables tras su cierre).",
    ]),
]

for title, items in sections:
    story.append(Paragraph(title, h_sec))
    story.append(bullets(items))

story.append(Spacer(1, 8))
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d1d5db")))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "<b>Resumen:</b> el sistema tiene una base de seguridad sólida y de nivel producción para un ERP "
    "clínico, con una suite de pruebas de seguridad automatizadas (tests/test_security.py). Para mayor "
    "profundidad puede realizarse una auditoría de seguridad formal y exhaustiva de todos los endpoints.",
    body))

doc.build(story)
print("PDF generado:", OUT)
