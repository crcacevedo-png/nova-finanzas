"""Genera el Manual Operativo del Superadministrador de NovaVisión ERP en PDF.

Uso: python3 generate_manual_superadmin.py
Salida: /app/frontend/public/manual-superadmin-novavision.pdf

Este script es un generador de documentación (no forma parte de la API en
ejecución). Se puede volver a correr para regenerar el manual si cambia el
contenido (ej. Fase 2: agregar capturas de pantalla).
"""
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, NextPageTemplate, PageBreak, KeepTogether, ListFlowable, ListItem,
)
from reportlab.platypus.tableofcontents import TableOfContents

OUTPUT_PATH = "/app/frontend/public/manual-superadmin-novavision.pdf"

NAVY = colors.HexColor("#0f172a")
INDIGO = colors.HexColor("#4F46E5")
SLATE = colors.HexColor("#374151")
LIGHT_GREY = colors.HexColor("#f1f5f9")
AMBER_BG = colors.HexColor("#fff7ed")
AMBER_BORDER = colors.HexColor("#d97706")
GREY_LINE = colors.HexColor("#e2e8f0")

FECHA_EMISION = "09 de noviembre de 2026"

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name="H1", fontName="Helvetica-Bold", fontSize=16, leading=20,
    spaceBefore=18, spaceAfter=10, textColor=NAVY,
))
styles.add(ParagraphStyle(
    name="H2", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
    spaceBefore=12, spaceAfter=6, textColor=INDIGO,
))
styles.add(ParagraphStyle(
    name="BodyText2", fontName="Helvetica", fontSize=10, leading=14,
    spaceAfter=6, textColor=SLATE, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="BulletText", fontName="Helvetica", fontSize=10, leading=14,
    textColor=SLATE, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="WarnTitle", fontName="Helvetica-Bold", fontSize=10, leading=13,
    textColor=AMBER_BORDER,
))
styles.add(ParagraphStyle(
    name="WarnBody", fontName="Helvetica", fontSize=10, leading=13.5,
    textColor=colors.HexColor("#78350f"),
))
styles.add(ParagraphStyle(
    name="FaqQ", fontName="Helvetica-Bold", fontSize=10.5, leading=14,
    textColor=NAVY, spaceBefore=10,
))
styles.add(ParagraphStyle(
    name="FaqLabel", fontName="Helvetica-Bold", fontSize=9.5, leading=13,
    textColor=INDIGO,
))
styles.add(ParagraphStyle(
    name="FaqBody", fontName="Helvetica", fontSize=9.5, leading=13,
    textColor=SLATE,
))
styles.add(ParagraphStyle(
    name="CoverTitle", fontName="Helvetica-Bold", fontSize=30, leading=36,
    alignment=TA_CENTER, textColor=colors.white,
))
styles.add(ParagraphStyle(
    name="CoverSubtitle", fontName="Helvetica", fontSize=15, leading=20,
    alignment=TA_CENTER, textColor=colors.HexColor("#c7d2fe"),
))
styles.add(ParagraphStyle(
    name="CoverMeta", fontName="Helvetica", fontSize=10.5, leading=15,
    alignment=TA_CENTER, textColor=colors.HexColor("#94a3b8"),
))
styles.add(ParagraphStyle(
    name="TOCHeading1", fontName="Helvetica-Bold", fontSize=11, leading=16,
    textColor=NAVY, leftIndent=0,
))


def p(text):
    return Paragraph(text, styles["BodyText2"])


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(t, styles["BulletText"]), spaceBefore=3) for t in items],
        bulletType="bullet", bulletColor=INDIGO, leftIndent=16, bulletFontSize=8,
    )


def numbered(items):
    return ListFlowable(
        [ListItem(Paragraph(t, styles["BulletText"]), spaceBefore=3) for t in items],
        bulletType="1", leftIndent=18, bulletColor=INDIGO,
    )


def warning(text):
    t = Table(
        [[Paragraph("ADVERTENCIA", styles["WarnTitle"]), ""],
         [Paragraph(text, styles["WarnBody"]), ""]],
        colWidths=[6.5 * inch, 0],
    )
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)), ("SPAN", (0, 1), (1, 1)),
        ("BACKGROUND", (0, 0), (-1, -1), AMBER_BG),
        ("BOX", (0, 0), (-1, -1), 1, AMBER_BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, AMBER_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    return KeepTogether([Spacer(1, 4), t, Spacer(1, 8)])


def faq(pregunta, causa, accion):
    t = Table(
        [[Paragraph(f"P: {pregunta}", styles["FaqQ"])],
         [Paragraph("Causa probable:", styles["FaqLabel"])],
         [Paragraph(causa, styles["FaqBody"])],
         [Paragraph("Qué hacer:", styles["FaqLabel"])],
         [Paragraph(accion, styles["FaqBody"])]],
        colWidths=[6.5 * inch],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
        ("BOX", (0, 0), (-1, -1), 0.75, GREY_LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
    ]))
    return KeepTogether([t, Spacer(1, 6)])


def section_title(num, title):
    return Paragraph(f'<a name="sec{num}"/>{num}. {title}', styles["H1"])


def sub(title):
    return Paragraph(title, styles["H2"])


# ==================== DOCUMENTO ====================
class ManualDocTemplate(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            text = flowable.getPlainText()
            if style_name == "H1" and text.strip() and text[0].isdigit():
                self.notify("TOCEntry", (0, text, self.page))
                key = f"h1-{text}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=0)
            elif style_name == "H2" and text.strip():
                self.notify("TOCEntry", (1, text, self.page))


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawString(0.6 * inch, 0.45 * inch,
                       "NovaVisión ERP — Manual Operativo del Superadministrador")
    canvas.drawRightString(letter[0] - 0.6 * inch, 0.45 * inch, f"Página {doc.page}")
    canvas.setStrokeColor(GREY_LINE)
    canvas.line(0.6 * inch, 0.62 * inch, letter[0] - 0.6 * inch, 0.62 * inch)
    canvas.restoreState()


def _cover_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, letter[0], letter[1], fill=1, stroke=0)
    canvas.setFillColor(INDIGO)
    canvas.rect(0, letter[1] - 0.18 * inch, letter[0], 0.18 * inch, fill=1, stroke=0)
    canvas.restoreState()


def build():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    doc = ManualDocTemplate(OUTPUT_PATH, pagesize=letter,
                             rightMargin=0.6 * inch, leftMargin=0.6 * inch,
                             topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                             title="Manual Operativo del Superadministrador - NovaVisión ERP")

    frame_normal = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    frame_cover = Frame(0, 0, letter[0], letter[1], id="cover")
    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=frame_cover, onPage=_cover_page),
        PageTemplate(id="Normal", frames=frame_normal, onPage=_header_footer),
    ])

    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(name="TOCH1", fontName="Helvetica-Bold", fontSize=11, leading=18,
                        textColor=NAVY, leftIndent=0),
        ParagraphStyle(name="TOCH2", fontName="Helvetica", fontSize=9.5, leading=14,
                        textColor=SLATE, leftIndent=16),
    ]

    story = []

    # ---------- Portada ----------
    story.append(Spacer(1, 2.6 * inch))
    story.append(Paragraph("NovaVisión ERP", styles["CoverTitle"]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("Manual Operativo del Superadministrador", styles["CoverSubtitle"]))
    story.append(Spacer(1, 1.8 * inch))
    story.append(Paragraph(f"Fecha de emisión: {FECHA_EMISION}", styles["CoverMeta"]))
    story.append(Paragraph("Documento de uso interno — no incluye contraseñas ni llaves reales", styles["CoverMeta"]))
    story.append(NextPageTemplate("Normal"))
    story.append(PageBreak())

    # ---------- Índice ----------
    story.append(Paragraph("Índice", styles["H1"]))
    story.append(Spacer(1, 6))
    story.append(toc)
    story.append(PageBreak())

    # ---------- Convenciones ----------
    story.append(Paragraph("Cómo usar este manual", styles["H1"]))
    story.append(p("Este manual está organizado por módulo, en el mismo orden en que aparecen en el "
                    "menú lateral del sistema. Cada sección explica los pasos para usar el módulo "
                    "correctamente y qué cuidar para no generar datos inconsistentes."))
    story.append(bullets([
        "Los nombres de botones, pestañas y menús se citan tal como aparecen en el sistema, entre comillas (ej. clic en \u201cRegistrar cirugía\u201d).",
        "Los recuadros de <b>ADVERTENCIA</b> señalan acciones que pueden generar datos incorrectos o difíciles de revertir.",
        "La última sección (\u201cSolución de problemas comunes\u201d) está organizada como Pregunta → Causa probable → Qué hacer, para resolver rápido sin tener que leer el manual completo.",
        "Este documento no incluye capturas de pantalla ni contraseñas/llaves reales. Para credenciales y llaves de integraciones (correo, Google Calendar, FEL/Digifact), se indica dónde se gestionan, nunca su valor.",
    ]))
    story.append(PageBreak())

    # ==================== 1. INTRODUCCIÓN ====================
    story.append(section_title(1, "Introducción y primeros pasos"))
    story.append(p("NovaVisión ERP es el sistema integral de la clínica: expediente clínico, "
                    "sala de operaciones, anestesia, óptica, punto de venta, caja, facturación "
                    "electrónica (FEL) y administración de usuarios, todo en una sola aplicación "
                    "web."))
    story.append(sub("Iniciar y cerrar sesión"))
    story.append(numbered([
        "Ingresar a la dirección del sistema e introducir usuario y contraseña.",
        "El menú lateral se arma automáticamente según el rol de la cuenta: cada rol ve solo los módulos habilitados para él (ver sección 10, \u201cRoles y Permisos\u201d).",
        "Para cerrar sesión, usar la opción correspondiente en el menú de usuario (ícono/nombre en la esquina superior).",
    ]))
    story.append(warning(
        "La cuenta de superadmin tiene acceso total al sistema, incluyendo Gestión de Usuarios, "
        "Respaldos y configuración de FEL. No comparta el usuario ni la contraseña de superadmin; "
        "si varias personas necesitan administrar el sistema, crear una cuenta \u201cadmin\u201d para "
        "cada una (ver sección 10) en vez de compartir la de superadmin."
    ))
    story.append(sub("Contraseñas y llaves"))
    story.append(p("Las contraseñas de usuarios se gestionan desde \u201cGestión de Usuarios\u201d → pestaña "
                    "\u201cUsuarios\u201d. Las llaves de integraciones externas (correo, Google Calendar, "
                    "FEL/Digifact, respaldos) se gestionan a nivel de servidor por el equipo técnico; "
                    "el superadmin no necesita ni debe conocer su valor exacto para operar el sistema "
                    "del día a día."))

    # ==================== 2. PACIENTES ====================
    story.append(section_title(2, "Pacientes"))
    story.append(p("Expediente base de cada paciente: datos personales, contacto de emergencia, "
                    "institución referente y, si aplica, datos de seguro o de la unidad del IGSS."))
    story.append(sub("Alta de un paciente nuevo"))
    story.append(numbered([
        "Ir al menú \u201cPacientes\u201d y usar el botón para crear un paciente nuevo.",
        "Completar los datos personales (nombre, DPI, teléfono, dirección) y el contacto de emergencia.",
        "Si el paciente llega referido por una institución o tiene seguro, indicarlo en el campo de institución/seguro; si es paciente IGSS, vincular la unidad y el número de orden (NOG) correspondiente.",
        "Guardar. El paciente queda disponible para agendar citas, registrar cirugías o generar ventas de óptica.",
    ]))
    story.append(sub("Editar y buscar"))
    story.append(bullets([
        "La edición completa del paciente está disponible para superadmin, admin, médico y óptica desde el módulo \u201cPacientes\u201d.",
        "El rol \u201cusuario\u201d no tiene el botón de editar en el módulo general de Pacientes, pero sí puede editar todos los campos del paciente desde \u201cSala de Operaciones\u201d (en el detalle de una cirugía vinculada, o en \u201cEditar cirugía\u201d, con el enlace \u201cEditar paciente\u201d).",
        "La búsqueda admite nombre, DPI o teléfono. Si un paciente no aparece, revisar primero la sección 13 (\u201cUn paciente no aparece en el listado\u201d).",
        "Existen opciones de importación y exportación masiva de pacientes (Excel) para altas en lote.",
    ]))
    story.append(warning(
        "Verificar bien institución, seguro y datos de IGSS al dar de alta o editar un paciente: estos "
        "datos alimentan reportes financieros, el cierre de anestesia y los reportes del IGSS. Un dato "
        "mal cargado aquí se arrastra a todos esos reportes."
    ))

    # ==================== 3. AGENDA ====================
    story.append(section_title(3, "Agenda"))
    story.append(p("Calendario de citas de la clínica, con sincronización automática hacia Google "
                    "Calendar para los médicos configurados."))
    story.append(numbered([
        "Para programar una cita: elegir el médico, la fecha y hora, y vincular (o crear) el paciente.",
        "El sistema sincroniza automáticamente con Google Calendar cada pocos minutos; también se puede forzar una sincronización manual con el botón \u201cGoogle Calendar\u201d dentro de la Agenda.",
        "Si quedaron citas duplicadas por la sincronización, existe una opción para eliminar duplicados conservando la cita ya atendida o vinculada a un paciente.",
    ]))
    story.append(warning(
        "Un cambio hecho directamente en Google Calendar (fuera del sistema) puede tardar unos minutos "
        "en reflejarse en NovaVisión, o requerir una sincronización manual. Para evitar inconsistencias, "
        "siempre que sea posible, programar y mover citas desde la Agenda del sistema."
    ))

    # ==================== 4. SALA DE OPERACIONES ====================
    story.append(section_title(4, "Sala de Operaciones"))
    story.append(p("Programación y gestión de cirugías: datos clínicos, equipo e insumos, estado de "
                    "pre-operatorio (Pre-Ops) y reprogramaciones."))
    story.append(sub("Registrar una cirugía"))
    story.append(numbered([
        "Clic en \u201cRegistrar cirugía\u201d.",
        "Completar paciente, procedimiento, cirujano, ojo a operar y, si aplica, el campo de \u201cLIO\u201d (texto libre, justo después de \u201cOjo a operar\u201d) con el lente intraocular a usar.",
        "Indicar institución, tipo de anestesia y anestesiólogo responsable (esto crea automáticamente el registro correspondiente en \u201cProcedimientos de Anestesia\u201d, ver sección 5).",
        "Marcar el equipo e insumos necesarios del catálogo quirúrgico.",
        "Guardar. La cirugía queda activa en el listado, con su estado de \u201cPre-Ops\u201d en \u201cIncompletos\u201d por defecto.",
    ]))
    story.append(sub("Pre-Ops, edición, cancelación y reprogramación"))
    story.append(bullets([
        "La columna \u201cPre-Ops\u201d tiene un botón que alterna entre \u201cCompletos\u201d e \u201cIncompletos\u201d; úsese para marcar cuándo los exámenes/preparación previos a la cirugía ya están listos.",
        "\u201cEditar cirugía\u201d permite modificar cualquier dato antes de la fecha programada.",
        "\u201cCancelar cirugía\u201d pide un motivo; si además se indica fecha <b>y</b> hora en \u201cReagendar para\u201d, el sistema crea automáticamente una nueva cirugía activa en esa fecha/hora, con los mismos datos clínicos (paciente, procedimiento, cirujano, ojo, LIO, anestesia). El equipo/insumos y el estado de Pre-Ops de la nueva cirugía quedan en blanco/incompletos, porque es un registro nuevo.",
        "\u201cEliminar\u201d borra la cirugía de forma permanente (no queda historial). Úsese solo para registros creados por error.",
    ]))
    story.append(warning(
        "Si se cancela una cirugía SIN completar fecha y hora de reagendamiento, el sistema no crea "
        "ninguna cirugía nueva — solo queda marcada como cancelada. Para que la reprogramación "
        "aparezca en el listado del nuevo día, ambos campos (fecha y hora) deben llenarse al cancelar."
    ))
    story.append(p("Los roles superadmin, admin, médico y usuario tienen acceso completo para crear, "
                    "editar, cancelar/reprogramar y eliminar cirugías. El rol anestesia solo puede "
                    "ver el listado (sin crear ni modificar)."))

    # ==================== 5. PROCEDIMIENTOS DE ANESTESIA ====================
    story.append(section_title(5, "Procedimientos de Anestesia"))
    story.append(p("Registra automáticamente cada procedimiento con anestesia creado desde Sala de "
                    "Operaciones, calcula el honorario según el tipo de anestesia y arma el cierre "
                    "mensual por anestesiólogo."))
    story.append(sub("Registros automáticos y catálogo"))
    story.append(bullets([
        "Cada vez que se registra una cirugía con anestesiólogo asignado, se crea (o actualiza) automáticamente su registro de anestesia correspondiente — no es necesario capturarlo por separado.",
        "La pestaña \u201cTipos de anestesia\u201d es el catálogo de tipos (tópica, local, general, etc.) con su honorario fijo asociado; un cambio aquí solo afecta a los registros nuevos, no a los ya creados.",
    ]))
    story.append(sub("Cierre mensual y pago individual"))
    story.append(numbered([
        "En la pestaña \u201cCierre mensual\u201d se ve, por anestesiólogo, el total pendiente de pago del mes y el detalle de cada procedimiento (paciente, fecha, procedimiento, médico responsable, institución, tipo de anestesia, honorario).",
        "Para pagar un procedimiento individual sin esperar al cierre del mes completo, usar el botón \u201cMarcar pagado\u201d en esa fila; el total pendiente del mes se recalcula al instante.",
        "Cuando todos los pagos del mes están confirmados, usar \u201cCerrar mes y marcar pagado\u201d: esto marca TODO el mes como pagado y lo bloquea para edición.",
        "Las exportaciones a Excel y PDF incluyen la columna \u201cEstado\u201d (Pagado/Pendiente) y respetan los mismos totales que se ven en pantalla.",
    ]))
    story.append(warning(
        "No usar \u201cCerrar mes y marcar pagado\u201d hasta confirmar que todos los pagos individuales "
        "pendientes de ese mes son correctos. Una vez cerrado, el mes queda bloqueado para edición y "
        "solo la cuenta superadmin puede reabrirlo (botón \u201cReabrir\u201d); al reabrir, todos los pagos "
        "de ese mes vuelven a quedar pendientes y deben revisarse de nuevo."
    ))
    story.append(p("El rol anestesia puede ver el cierre mensual y exportarlo, pero no puede marcar "
                    "pagos ni cerrar/reabrir el mes (esas acciones son solo de admin/superadmin)."))

    # ==================== 6. EVALUACIONES OFTALMOLÓGICAS ====================
    story.append(section_title(6, "Evaluaciones Oftalmológicas"))
    story.append(p("Expediente clínico de cada consulta: lectura de exámenes, diagnósticos y recetas."))
    story.append(bullets([
        "La evaluación se guarda automáticamente mientras se está completando (autoguardado), incluyendo la \u201clectura de exámenes\u201d — no es necesario guardar manualmente cada campo, aunque también existe un botón \u201cGuardar\u201d para confirmar al terminar.",
        "Los diagnósticos marcados como activos en la última evaluación de un paciente se arrastran automáticamente a su siguiente consulta, para no perder seguimiento de condiciones crónicas.",
        "Cuando un diagnóstico ya no aplica, marcarlo como \u201cResuelto\u201d: deja de arrastrarse a futuras consultas, pero se conserva en el historial de la consulta donde se registró.",
        "Eliminar un diagnóstico (en vez de marcarlo resuelto) también detiene el arrastre, pero no deja registro de que existió.",
        "Las recetas generadas se pueden guardar e imprimir desde la misma evaluación.",
    ]))
    story.append(warning(
        "Preferir \u201cmarcar como Resuelto\u201d en vez de \u201celiminar\u201d un diagnóstico que ya no aplica: "
        "así se conserva el historial clínico completo del paciente."
    ))

    # ==================== 7. ÓPTICA Y PUNTO DE VENTA ====================
    story.append(section_title(7, "Óptica y Punto de Venta (POS)"))
    story.append(p("Inventario de armazones, lentes de contacto, lentes oftálmicos y accesorios, con "
                    "su propio punto de venta y facturación electrónica."))
    story.append(sub("Venta y cobro"))
    story.append(numbered([
        "Desde \u201cPunto de Venta\u201d (Óptica), armar la venta eligiendo los productos y, si aplica, vincular al paciente/cliente.",
        "Para cobrar, ingresar el monto y confirmar: si el monto ingresado cubre el total, la venta se confirma directamente (no es necesario un paso adicional de \u201cagregar\u201d el monto antes de confirmar).",
        "Al finalizar, se puede imprimir el ticket de la venta.",
    ]))
    story.append(sub("Facturación Electrónica (FEL) en Óptica"))
    story.append(bullets([
        "Desde la venta exitosa o desde \u201cVer Ventas del Día\u201d se puede \u201cCertificar factura\u201d (envía la venta al proveedor de FEL y genera el documento oficial).",
        "\u201cAnular factura\u201d requiere indicar un motivo; una factura certificada no puede editarse, solo anularse.",
        "El estado de la factura se puede consultar en cualquier momento desde el mismo detalle de la venta.",
    ]))
    story.append(warning(
        "Anular una venta de Óptica no cancela automáticamente la Cuenta por Cobrar asociada, si la "
        "venta generó una. Revisar manualmente la sección \u201cCuentas por Cobrar\u201d de Óptica después "
        "de anular una venta a crédito."
    ))

    # ==================== 8. CAJA ====================
    story.append(section_title(8, "Caja"))
    story.append(p("Control de efectivo por turno/cajero, con apertura, cierre y conciliación."))
    story.append(numbered([
        "Al iniciar el turno, usar \u201cAbrir Caja\u201d e indicar el monto inicial en efectivo.",
        "Durante el turno, los cobros de ventas/pagos quedan asociados automáticamente a la caja abierta.",
        "Al finalizar, usar \u201cCerrar Caja\u201d e ingresar el efectivo realmente contado; el sistema calcula la diferencia contra el efectivo esperado según los movimientos del turno.",
        "Un supervisor (admin/superadmin) puede cerrar la caja de otro usuario si quedó abierta.",
    ]))
    story.append(p("El módulo de \u201cCuentas por Cobrar\u201d (Finanzas) y los cierres consolidados "
                    "permiten revisar el panorama financiero general más allá de un solo turno de caja."))
    story.append(warning(
        "Cerrar la caja sin contar físicamente el efectivo genera una diferencia registrada (positiva "
        "o negativa) que queda en el historial del cierre. Contar el efectivo real antes de confirmar "
        "el cierre."
    ))

    # ==================== 9. FEL ====================
    story.append(section_title(9, "Facturación Electrónica (FEL)"))
    story.append(p("Integración con el proveedor certificador (Digifact) para emitir facturas "
                    "electrónicas válidas ante el SAT, compartida entre Clínica y Óptica (una sola "
                    "configuración para ambas)."))
    story.append(bullets([
        "La configuración general (NIT de la clínica, credenciales del certificador) la gestiona únicamente superadmin, y aplica por igual a las ventas de Clínica y de Óptica.",
        "Certificar una factura la envía al certificador y al SAT; el documento resultante queda disponible para descarga/impresión.",
        "Consultar estado permite verificar en cualquier momento si una factura quedó certificada, pendiente o anulada.",
        "Anular siempre requiere un motivo, y es la única forma de \u201ccorregir\u201d una factura ya certificada (no se puede editar directamente).",
    ]))
    story.append(warning(
        "Una factura certificada y enviada al SAT no se puede editar. Si el dato está mal, se debe "
        "anular (con motivo) y generar una nueva venta/factura con el dato corregido."
    ))

    # ==================== 10. ROLES Y PERMISOS ====================
    story.append(section_title(10, "Roles y Permisos"))
    story.append(p("Toda la administración de usuarios, roles y menús visibles vive en \u201cGestión de "
                    "Usuarios\u201d, con tres pestañas: \u201cUsuarios\u201d, \u201cRoles\u201d y \u201cMenús por Rol\u201d."))
    story.append(sub("Qué controla cada rol de sistema"))
    story.append(bullets([
        "<b>superadmin</b>: acceso total, incluyendo Gestión de Usuarios, Respaldos y configuración de FEL.",
        "<b>admin</b>: acceso operativo completo a Pacientes, Agenda, Sala de Operaciones, Anestesia, Finanzas e Inventario — sin Gestión de Usuarios ni Respaldos.",
        "<b>usuario</b>: acceso de solo lectura en Pacientes (salvo edición de datos del paciente desde Sala de Operaciones), acceso completo a Sala de Operaciones/Anestesia/Evaluaciones/Agenda; sin Finanzas ni Óptica.",
        "<b>médico</b>: Pacientes, Agenda y Evaluación Oftalmológica.",
        "<b>óptica</b>: todo el módulo de Óptica (inventario, punto de venta, cuentas por cobrar, compras) y Pacientes (para vincular clientes); sin Finanzas general.",
        "<b>anestesia</b>: solo lectura en Sala de Operaciones, Insumos/Equipos y Procedimientos de Anestesia (incluye el cierre mensual, sin poder marcar pagos).",
        "<b>administrador_igss</b>: Pacientes, Unidades IGSS y gestión de NOG.",
    ]))
    story.append(sub("Crear o ajustar un rol sin romper accesos"))
    story.append(numbered([
        "En la pestaña \u201cRoles\u201d, usar \u201cNuevo Rol\u201d para crear uno personalizado, o seleccionar uno existente para editarlo.",
        "Activar/desactivar los permisos específicos que ese rol debe tener (qué puede ver y qué puede modificar).",
        "Ir también a la pestaña \u201cMenús por Rol\u201d y habilitar los menús correspondientes a esos permisos. Un permiso activo sin su menú visible deja al usuario sin una forma de llegar a esa función desde la interfaz.",
        "Guardar y pedirle a un usuario de ese rol que vuelva a iniciar sesión para ver los cambios reflejados.",
    ]))
    story.append(warning(
        "Siempre que se cambie un permiso de un rol, revisar también \u201cMenús por Rol\u201d para ese "
        "mismo rol. Son dos configuraciones independientes: una controla qué puede HACER el rol "
        "(permisos) y otra qué puede VER en el menú (menús habilitados)."
    ))

    # ==================== 11. RESPALDOS ====================
    story.append(section_title(11, "Respaldos"))
    story.append(p("El sistema respalda automáticamente toda la base de datos una vez por semana, "
                    "sin necesidad de intervención manual."))
    story.append(bullets([
        "El respaldo automático corre todos los domingos a las 6:00 a.m., hora de Guatemala.",
        "El menú \u201cRespaldos\u201d (visible solo para superadmin) muestra el historial de respaldos con su fecha, estado, cantidad de documentos y tamaño.",
        "El botón \u201cEjecutar ahora\u201d genera un respaldo manual inmediato, útil antes de un cambio importante.",
        "Cada respaldo completado se puede descargar directamente desde la lista.",
    ]))
    story.append(warning(
        "Verificar periódicamente (ej. una vez al mes) que el respaldo automático del domingo aparece "
        "en la lista con estado \u201ccompletado\u201d. Si no aparece ninguno reciente, ejecutar uno manual "
        "y avisar al equipo técnico."
    ))

    # ==================== 12. CORREOS AUTOMÁTICOS ====================
    story.append(section_title(12, "Correos automáticos"))
    story.append(p("El sistema envía dos reportes por correo todos los días, sin acción manual, "
                    "usando el servicio de correo gestionado del sistema."))
    story.append(sub("Cierre del Día"))
    story.append(bullets([
        "Se envía todos los días a las 18:00, hora de Guatemala.",
        "Incluye el resumen financiero de Clínica y Óptica del día (facturado, cobrado, cuentas por cobrar generadas, egresos) y la conciliación de cajas abiertas ese día.",
        "Llega a los correos administrativos configurados en el sistema.",
    ]))
    story.append(sub("Informe diario de Anestesia"))
    story.append(bullets([
        "Se envía todos los días a las 17:00, hora de Guatemala, a la cuenta de correo del anestesiólogo configurada en el sistema.",
        "Incluye el detalle de los procedimientos de anestesia del día (paciente, procedimiento, médico responsable, tipo de anestesia, honorario, estado de pago) y un enlace para descargar el informe en PDF.",
        "Si un día no hubo procedimientos, el correo igual se envía mostrando el informe en cero — nunca se omite el envío.",
    ]))
    story.append(sub("Cambiar destinatarios"))
    story.append(p("Los correos de destino de ambos reportes se configuran a nivel de servidor "
                    "(no desde una pantalla del sistema). Para agregar, quitar o corregir un "
                    "destinatario, solicitarlo al equipo técnico indicando el reporte y el nuevo "
                    "correo."))
    story.append(warning(
        "Estos dos correos se envían automáticamente todos los días sin que nadie tenga que "
        "generarlos a mano. Si uno no llega, revisar primero la sección 13 (\u201cSolución de "
        "problemas comunes\u201d) antes de asumir que el sistema falló."
    ))

    # ==================== 13. SOLUCIÓN DE PROBLEMAS ====================
    story.append(section_title(13, "Solución de problemas comunes"))
    story.append(p("Preguntas frecuentes del día a día, organizadas como Pregunta → Causa probable "
                    "→ Qué hacer."))

    story.append(faq(
        "Un correo automático (Cierre del Día o Informe de Anestesia) no llegó.",
        "El proveedor de correo alcanzó un límite temporal de envíos, la dirección configurada tiene un error, o el correo cayó en la carpeta de spam del destinatario.",
        "Revisar primero la carpeta de spam/correo no deseado. Confirmar con el equipo técnico que el correo configurado es el correcto. El sistema no reenvía automáticamente el mismo día; el siguiente envío programado llegará normalmente al día siguiente."
    ))
    story.append(faq(
        "Un usuario no ve un menú que debería.",
        "El permiso correspondiente está activo para su rol, pero el menú no está habilitado en \u201cMenús por Rol\u201d (o al revés: el menú está habilitado pero el permiso de fondo está apagado).",
        "Ir a \u201cGestión de Usuarios\u201d y revisar, para ese rol, tanto la pestaña \u201cRoles\u201d (permisos) como \u201cMenús por Rol\u201d (menús visibles). Ajustar la que falte y pedir al usuario que vuelva a iniciar sesión."
    ))
    story.append(faq(
        "Una venta en el Punto de Venta no se deja confirmar.",
        "El monto ingresado no coincide con el total pendiente de la venta, o se está intentando confirmar sin haber ingresado ningún monto.",
        "Verificar que el monto escrito sea igual al total a cobrar. En la versión actual del sistema, un monto exacto se confirma directamente sin pasos adicionales; si el problema persiste, anotar el monto exacto mostrado en pantalla y reportarlo al equipo técnico."
    ))
    story.append(faq(
        "Un mes de Procedimientos de Anestesia aparece cerrado y no se puede editar.",
        "Alguien usó el botón \u201cCerrar mes y marcar pagado\u201d para ese mes.",
        "Solo la cuenta superadmin puede usar \u201cReabrir\u201d para ese mes. Al reabrir, todos los pagos individuales de ese mes vuelven a quedar pendientes y deben marcarse de nuevo uno por uno (o volver a cerrar el mes cuando estén confirmados)."
    ))
    story.append(faq(
        "Un paciente no aparece en el listado o en la búsqueda.",
        "Error de tipeo en el nombre/DPI buscado, o el dato real tiene un acento, guion u orden de nombres distinto al que se está buscando.",
        "Probar la búsqueda por teléfono o por institución en vez del nombre. Revisar en el módulo \u201cPacientes\u201d si existe con una grafía ligeramente distinta antes de crear un registro duplicado."
    ))
    story.append(faq(
        "Una cirugía cancelada y reagendada no aparece en la nueva fecha.",
        "Al cancelar la cirugía, el campo \u201cReagendar para\u201d es opcional: si no se completaron fecha Y hora, el sistema solo marca la cirugía como cancelada, sin crear ninguna cirugía nueva.",
        "Abrir la cirugía cancelada y, si aún corresponde reagendar, repetir el proceso de cancelación completando ambos campos (fecha y hora). Se creará una nueva cirugía activa con los mismos datos clínicos en esa fecha/hora."
    ))
    story.append(faq(
        "Una factura FEL no logra certificarse.",
        "El NIT u otro dato fiscal del cliente está incompleto o es inválido, o el servicio del certificador (Digifact) está temporalmente no disponible.",
        "Verificar el NIT y los datos fiscales del cliente en la venta. Reintentar certificar en unos minutos. Si el problema persiste, contactar al equipo técnico indicando el número de venta y el mensaje de error exacto."
    ))
    story.append(faq(
        "Un respaldo aparece en la lista pero el botón de descarga no funciona.",
        "El respaldo todavía está en proceso (su estado aún no es \u201ccompletado\u201d).",
        "Esperar unos minutos y refrescar la lista de \u201cRespaldos\u201d con el botón de actualizar. Si después de un tiempo prudente sigue sin completarse, ejecutar un respaldo manual nuevo y reportar el caso anterior al equipo técnico."
    ))
    story.append(faq(
        "Un reporte en PDF (por ejemplo, el cierre de Anestesia) se ve con texto cortado o fuera de su columna.",
        "El reporte se generó desde una versión anterior del sistema donde los nombres largos de procedimientos no se ajustaban bien a la columna.",
        "Confirmar que se está generando el reporte desde la versión actual del sistema (el ajuste de texto ya está corregido). Si el problema persiste en un reporte nuevo, reportarlo al equipo técnico indicando el nombre exacto del reporte y el mes consultado."
    ))

    doc.multiBuild(story)


if __name__ == "__main__":
    build()
    print(f"Manual generado en: {OUTPUT_PATH}")
