# /app/backend/routes/igss_libro_lecturas.py
# Libro de órdenes IGSS — Fase 3: las lecturas salen del libro y cuentan ÓRDENES (No. SPS),
# nunca dosis ni atenciones: consumidos = atendidas, reservados = pendientes. Contadores y
# alertas del catálogo, Producción y listado oficial en Excel (1 fila por orden atendida).
# Exclusivo de LIBRO_IGSS_ROLES, salvo el selector ligero `nogs-activos`.

import io
import re
import unicodedata
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from config.database import db
from config.permissions import LIBRO_IGSS_ROLES
from routes.auth import get_current_user, require_role
from routes.igss_nogs import (TIPO_COMPRA_LABELS, UMBRAL_AVISO, _calcular_edad, _get_nog_or_404,
                              _produccion_totales, _unidad_or_404, etiqueta_catalogo, norm_txt)
from utils.timezone import now_gt, today_str_gt

router = APIRouter(prefix="/igss-units", tags=["IGSS - Libro (lecturas)"])

COSTO = {"$ifNull": ["$costo_override", {"$ifNull": ["$precio", 0]}]}
ESTADOS_PROD = ("impreso", "enviado", "facturado", "pagado")
FECHA = r"^\d{4}-\d{2}-\d{2}$"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ==================== CONTADORES ====================

def _modalidad(nog: dict) -> str:
    t = (nog or {}).get("tipo_compra", "")
    return TIPO_COMPRA_LABELS.get(t, t)


def costo_orden(o: dict) -> float:
    v = o.get("costo_override")
    return round(float(v if v is not None else (o.get("precio") or 0)), 2)


async def contadores_libro(match: Optional[dict] = None) -> dict:
    """{nog_id: {consumidos, reservados, monto_consumido}} contando órdenes vigentes."""
    out = {}
    pipeline = [{"$match": {"estado": {"$in": ["pendiente", "atendida"]}, **(match or {})}},
                {"$group": {"_id": {"nog": "$nog_id", "estado": "$estado"}, "n": {"$sum": 1}, "monto": {"$sum": COSTO}}}]
    async for g in db.igss_ordenes_libro.aggregate(pipeline):
        c = out.setdefault(g["_id"]["nog"], {"consumidos": 0, "reservados": 0, "monto_consumido": 0.0})
        if g["_id"]["estado"] == "atendida":
            c["consumidos"], c["monto_consumido"] = g["n"], round(float(g["monto"]), 2)
        else:
            c["reservados"] = g["n"]
    return out


def nog_libro(nog: dict, c: Optional[dict] = None) -> dict:
    """Entrada del catálogo con sus contadores del libro; aviso 90 % / bloqueo 100 % solo con tope."""
    c = c or {}
    cantidad = int(nog.get("cantidad") or 0)
    precio = float(nog.get("precio") or 0)
    sin_tope = bool(nog.get("sin_tope"))
    tope = not sin_tope and cantidad > 0
    consumidos, reservados = int(c.get("consumidos", 0)), int(c.get("reservados", 0))
    usados = consumidos + reservados
    activo = nog.get("is_active", True) is not False
    aviso, bloqueado = tope and usados >= cantidad * UMBRAL_AVISO, tope and usados >= cantidad
    estado = "inactivo" if not activo else "completado" if bloqueado else "por_completarse" if aviso else "activo"
    monto_total = nog.get("monto_total")
    monto_total = round(float(monto_total), 2) if monto_total is not None else round(cantidad * precio, 2)
    return {
        "id": nog["id"], "unidad_id": nog.get("unidad_id", ""), "numero": nog.get("numero", ""),
        "nombre_servicio": nog.get("nombre_servicio", ""), "tipo_compra": nog.get("tipo_compra", ""),
        "tipo_compra_label": _modalidad(nog), "modalidad": _modalidad(nog), "etiqueta": etiqueta_catalogo(nog),
        "sin_tope": sin_tope, "fecha_asignacion": nog.get("fecha_asignacion", ""),
        "cantidad": cantidad, "precio": precio, "monto_total": monto_total, "valor_total": monto_total,
        "consumidos": consumidos, "reservados": reservados, "usados": usados,
        "disponibles": max(cantidad - usados, 0) if tope else None,
        "porcentaje": round(usados / cantidad * 100, 1) if tope else None,
        "aviso_90": aviso, "bloqueado": bloqueado,
        "monto_consumido": float(c.get("monto_consumido", 0.0)),
        "estado": estado, "is_active": activo,
        "created_at": nog.get("created_at", ""), "updated_at": nog.get("updated_at", ""),
    }


async def _unidades() -> dict:
    docs = await db.igss_units.find({}, {"_id": 0, "id": 1, "name": 1, "code": 1}).to_list(None)
    return {u["id"]: u for u in docs}


async def _nogs_libro(filtro: dict) -> list:
    docs = await db.igss_nogs.find(filtro, {"_id": 0}).to_list(None)
    match = {"unidad_id": filtro["unidad_id"]} if "unidad_id" in filtro else None
    cont = await contadores_libro(match)
    return [nog_libro(n, cont.get(n["id"])) for n in docs]


# ==================== FILAS POR ORDEN ====================

def fmt_fecha(f) -> str:
    f = str(f or "")[:10]
    return "/".join(reversed(f.split("-"))) if re.match(FECHA, f) else f


def fila_orden(o: dict, nog: Optional[dict], pac: Optional[dict]) -> dict:
    """Una fila por orden (No. SPS) con sus dosis aplicadas y fechas."""
    ats = sorted(o.get("atenciones") or [], key=lambda a: (a.get("fecha") or "", a.get("registrado_en") or ""))
    autorizadas = int(o.get("dosis_autorizadas") or 1)
    if o.get("tipo") == "procedimiento":
        cx = [a for a in ats if a.get("tipo") == "cirugia"]
        aplicadas, fechas = len(cx), [a.get("fecha") for a in cx]
    else:
        aplicadas, fechas = (1, [o.get("fecha_primera_atencion")]) if ats else (0, [])
    pac = pac or {}
    nombre = f"{pac.get('first_name', '')} {pac.get('last_name', '')}".strip()
    ev = next((a for a in ats if a.get("tipo") == "evaluacion"), None)
    return {
        "orden_id": o["id"], "estado": o.get("estado", ""), "no_sps": o.get("no_sps", ""),
        "modalidad": _modalidad(nog or o), "nog_id": o.get("nog_id", ""), "numero_nog": o.get("numero_nog", ""),
        "nog": etiqueta_catalogo(nog) if nog else o.get("numero_nog", ""), "unidad_id": o.get("unidad_id", ""),
        "paciente_id": o.get("paciente_id", ""), "paciente_nombre": nombre or o.get("paciente_nombre", ""),
        "expediente": pac.get("record_number") or o.get("paciente_expediente", ""),
        "igss_afiliacion": pac.get("igss_afiliacion") or o.get("igss_afiliacion", ""),
        "paciente_activo": pac.get("is_active", True) is not False,
        "codigo": o.get("codigo", ""), "procedimiento": o.get("procedimiento") or (nog or {}).get("nombre_servicio", ""),
        "tipo": o.get("tipo", ""), "fecha_ingreso": o.get("fecha_ingreso", ""),
        "fecha_primera_atencion": o.get("fecha_primera_atencion") or "",
        "medico_nombre": next((a.get("medico") for a in ats if a.get("medico")), ""),
        "dosis_aplicadas": aplicadas, "dosis_autorizadas": autorizadas, "fechas_dosis": [f for f in fechas if f],
        "evaluacion_id": ev.get("ref_id") if ev else None,
        "precio_nog": float(o.get("precio") or 0), "costo": costo_orden(o),
        "costo_editado": o.get("costo_override") is not None,
        **{k: bool(o.get(k)) for k in ESTADOS_PROD},
    }


def _orden_fecha_sps(o: dict):
    return (o.get("fecha_primera_atencion") or "", o.get("no_sps") or "")


async def ordenes_atendidas(filtro: dict, desde=None, hasta=None) -> list:
    """Órdenes ATENDIDAS (pendientes y anuladas fuera) cuya PRIMERA atención cae en el
    rango; incluye pacientes inactivos. Orden: fecha de primera atención y No. SPS."""
    q = {"estado": "atendida", **filtro}
    rango = {k: v[:10] for k, v in (("$gte", desde), ("$lte", hasta)) if v}
    if rango:
        q["fecha_primera_atencion"] = rango
    docs = await db.igss_ordenes_libro.find(q, {"_id": 0}).to_list(None)
    return sorted(docs, key=_orden_fecha_sps)


async def _pacientes(ids) -> dict:
    ids = [i for i in set(ids) if i]
    docs = await db.patients.find({"id": {"$in": ids}}, {
        "_id": 0, "id": 1, "record_number": 1, "first_name": 1, "last_name": 1,
        "igss_afiliacion": 1, "is_active": 1}).to_list(None)
    return {p["id"]: p for p in docs}


async def _filas(ordenes: list, nogs: dict) -> list:
    pacs = await _pacientes(o.get("paciente_id") for o in ordenes)
    return [fila_orden(o, nogs.get(o.get("nog_id")), pacs.get(o.get("paciente_id"))) for o in ordenes]


# ==================== ENDPOINTS: CATÁLOGO Y CONTADORES ====================

@router.get("/{unit_id}/nogs")
async def listar_nogs_unidad(unit_id: str, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """NOG de la unidad con sus contadores del libro, más los pacientes de la unidad con
    NOG escrito fuera del catálogo o sin NOG (solo activos)."""
    unit = await _unidad_or_404(unit_id)
    nogs = sorted(await _nogs_libro({"unidad_id": unit_id}), key=lambda n: (n["numero"] == "", n["etiqueta"]))
    numeros = {(n["numero"] or "").strip() for n in nogs}
    pacientes = await db.patients.find(
        {"is_active": True, "igss_unit_id": unit_id},
        {"_id": 0, "id": 1, "record_number": 1, "first_name": 1, "last_name": 1,
         "dpi": 1, "phone": 1, "birth_date": 1, "igss_nog": 1, "igss_afiliacion": 1}).to_list(None)
    sin_nog, fuera = [], []
    for p in pacientes:
        numero = (p.get("igss_nog") or "").strip()
        fila = {"id": p["id"], "record_number": p.get("record_number", ""),
                "full_name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                "dpi": p.get("dpi", ""), "phone": p.get("phone", ""), "edad": _calcular_edad(p.get("birth_date", "")),
                "igss_nog": numero, "igss_afiliacion": p.get("igss_afiliacion", "")}
        if not numero:
            sin_nog.append(fila)
        elif numero not in numeros:
            fuera.append(fila)
    con_tope = [n for n in nogs if n["disponibles"] is not None]
    return {
        "unidad": {"id": unit["id"], "name": unit.get("name", ""), "code": unit.get("code", "")},
        "nogs": nogs, "pacientes_nog_no_catalogado": fuera, "pacientes_sin_nog": sin_nog,
        "totales": {
            "nogs": len(nogs),
            "servicios_contratados": sum(n["cantidad"] for n in con_tope),
            "consumidos": sum(n["consumidos"] for n in nogs),
            "reservados": sum(n["reservados"] for n in nogs),
            "servicios_disponibles": sum(n["disponibles"] for n in con_tope if n["is_active"]),
            "valor_total": round(sum(n["monto_total"] for n in nogs), 2),
        },
    }


@router.get("/{unit_id}/nogs-activos")
async def listar_nogs_activos(unit_id: str, current_user: dict = Depends(get_current_user)):
    """Selector ligero de NOG (ficha del paciente, cirugías). Los roles fuera del libro solo
    reciben número, servicio y si el NOG está completo; nunca contadores ni porcentajes."""
    nogs = await _nogs_libro({"unidad_id": unit_id, "is_active": True, "numero": {"$nin": [None, ""]}})
    nogs.sort(key=lambda n: n["numero"])
    if current_user.get("role") not in LIBRO_IGSS_ROLES:
        return [{"id": n["id"], "numero": n["numero"], "nombre_servicio": n["nombre_servicio"],
                 "estado": "completado" if n["bloqueado"] else "activo"} for n in nogs]
    conteo = {c["_id"]: c["total"] for c in await db.patients.aggregate([
        {"$match": {"igss_unit_id": unit_id, "is_active": True, "igss_nog": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$igss_nog", "total": {"$sum": 1}}}]).to_list(None)}
    return [{**n, "pacientes_asignados": conteo.get(n["numero"], 0)} for n in nogs]


@router.get("/nogs/all")
async def listar_todos_nogs(current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Todas las entradas del catálogo de todas las unidades con sus contadores del libro."""
    units = await _unidades()
    data = []
    for n in await _nogs_libro({}):
        u = units.get(n["unidad_id"], {})
        data.append({**n, "unidad_nombre": u.get("name", ""), "unidad_codigo": u.get("code", "")})
    data.sort(key=lambda x: (x["unidad_nombre"], x["numero"] == "", x["etiqueta"]))
    unidades = sorted(({"id": u["id"], "name": u.get("name", ""), "code": u.get("code", "")} for u in units.values()),
                      key=lambda x: x["name"])
    return {"data": data, "unidades": unidades, "total": len(data)}


@router.get("/nogs/resumen")
async def resumen_nogs(current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    nogs = await _nogs_libro({})
    activos = [n for n in nogs if n["is_active"]]
    con_tope = [n for n in nogs if n["disponibles"] is not None]
    return {
        "total_nogs": len(nogs),
        "nogs_disponibles": sum(1 for n in activos if n["estado"] != "completado"),
        "nogs_completados": sum(1 for n in activos if n["estado"] == "completado"),
        "servicios_contratados": sum(n["cantidad"] for n in con_tope),
        "servicios_consumidos": sum(n["consumidos"] for n in nogs),
        "servicios_reservados": sum(n["reservados"] for n in nogs),
        "servicios_disponibles": sum(n["disponibles"] for n in con_tope if n["is_active"]),
        "valor_total": round(sum(n["monto_total"] for n in nogs), 2),
    }


@router.get("/nogs/alertas")
async def alertas_nogs(current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Entradas activas con tope que llegaron al 90 % (por completarse) o al 100 % (bloqueadas)."""
    units = await _unidades()
    alertas = []
    for n in await _nogs_libro({"is_active": {"$ne": False}}):
        if not n["aviso_90"]:
            continue
        u = units.get(n["unidad_id"], {})
        alertas.append({
            "unidad_id": n["unidad_id"], "unidad_nombre": u.get("name", ""), "unidad_codigo": u.get("code", ""),
            "nog_id": n["id"], "numero": n["numero"], "etiqueta": n["etiqueta"], "nombre_servicio": n["nombre_servicio"],
            "consumidos": n["consumidos"], "reservados": n["reservados"], "usados": n["usados"],
            "cantidad": n["cantidad"], "disponibles": n["disponibles"], "porcentaje": n["porcentaje"], "estado": n["estado"]})
    alertas.sort(key=lambda a: (0 if a["estado"] == "completado" else 1, -a["porcentaje"]))
    return {
        "alertas": alertas, "total": len(alertas),
        "completados": sum(1 for a in alertas if a["estado"] == "completado"),
        "por_completarse": sum(1 for a in alertas if a["estado"] == "por_completarse"),
        "umbral_aviso": int(UMBRAL_AVISO * 100),
    }


@router.get("/nogs/{nog_id}/pacientes")
async def ordenes_de_nog(nog_id: str, current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES))):
    """Órdenes vigentes del NOG (atendidas y pendientes), una fila por orden."""
    nog = await _get_nog_or_404(nog_id)
    docs = await db.igss_ordenes_libro.find(
        {"nog_id": nog_id, "estado": {"$in": ["pendiente", "atendida"]}}, {"_id": 0}).to_list(None)
    docs.sort(key=lambda o: (o.get("estado") != "atendida", *_orden_fecha_sps(o)))
    cont = await contadores_libro({"nog_id": nog_id})
    filas = await _filas(docs, {nog_id: nog})
    return {"nog": nog_libro(nog, cont.get(nog_id)), "ordenes": filas, "total": len(filas)}


# ==================== LISTADO OFICIAL (EXCEL) ====================

COLUMNAS = ["No. SPS", "Modalidad", "NOG", "Expediente", "Paciente", "Afiliación", "Código", "Procedimiento",
            "Fecha 1ª atención", "Médico", "Dosis aplicadas / autorizadas", "Fechas de cada dosis", "Precio (Q)",
            "Impreso", "Enviado", "Facturado", "Pagado"]
COLUMNAS_RESUMEN = ["NOG / Entrada", "Servicio", "Modalidad", "Precio unitario (Q)", "Órdenes atendidas en el periodo",
                    "Monto del periodo (Q)", "Órdenes atendidas acumuladas", "Cupos contratados", "Avance acumulado",
                    "Monto acumulado (Q)", "Monto contratado (Q)", "Estado"]


def _si(v) -> str:
    return "Sí" if v else "No"


def _valores(f: dict) -> list:
    return [f["no_sps"], f["modalidad"], f["nog"], f["expediente"], f["paciente_nombre"], f["igss_afiliacion"],
            f["codigo"], f["procedimiento"], fmt_fecha(f["fecha_primera_atencion"]), f["medico_nombre"],
            f"{f['dosis_aplicadas']} / {f['dosis_autorizadas']}", ", ".join(fmt_fecha(x) for x in f["fechas_dosis"]),
            f["costo"], *(_si(f[k]) for k in ESTADOS_PROD)]


def _estilos():
    from openpyxl.styles import Alignment, Font, PatternFill
    return (PatternFill(start_color="0F6E56", end_color="0F6E56", fill_type="solid"),
            Font(color="FFFFFF", bold=True), Font(bold=True), Alignment(horizontal="center", vertical="center", wrap_text=True))


def _encabezado(ws, lineas: list) -> int:
    _, _, bold, _ = _estilos()
    for r, (k, v) in enumerate(lineas, 1):
        ws.cell(row=r, column=1, value=k).font = bold
        ws.cell(row=r, column=2, value=v)
    return len(lineas) + 2


def _fila_titulos(ws, r: int, titulos: list):
    fill, font, _, align = _estilos()
    for c, h in enumerate(titulos, 1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill, cell.font, cell.alignment = fill, font, align


def _anchos(ws, n: int, ancho: int = 18):
    from openpyxl.utils import get_column_letter
    for c in range(1, n + 1):
        ws.column_dimensions[get_column_letter(c)].width = ancho


def _hoja_ordenes(ws, lineas: list, filas: list):
    _, _, bold, _ = _estilos()
    r = _encabezado(ws, lineas)
    _fila_titulos(ws, r, COLUMNAS)
    for f in filas:
        r += 1
        for c, v in enumerate(_valores(f), 1):
            cell = ws.cell(row=r, column=c, value=v)
            if c == 13:
                cell.number_format = "#,##0.00"
    r += 2
    ws.cell(row=r, column=1, value="Total de órdenes").font = bold
    ws.cell(row=r, column=2, value=len(filas)).font = bold
    ws.cell(row=r + 1, column=1, value="Monto total (Q)").font = bold
    total = ws.cell(row=r + 1, column=2, value=round(sum(f["costo"] for f in filas), 2))
    total.font, total.number_format = bold, "#,##0.00"
    _anchos(ws, len(COLUMNAS))


def _titulo_hoja(wb, texto: str) -> str:
    base = ("".join(ch for ch in str(texto) if ch not in '[]:*?/\\').strip() or "Hoja")[:31]
    titulo, i = base, 2
    while titulo in wb.sheetnames:
        sufijo = f" ({i})"
        titulo, i = base[:31 - len(sufijo)] + sufijo, i + 1
    return titulo


def _periodo_texto(desde, hasta) -> str:
    if not (desde or hasta):
        return "Todo el historial"
    return f"{fmt_fecha(desde) if desde else 'inicio'} al {fmt_fecha(hasta) if hasta else 'hoy'} (fecha de primera atención)"


def _fila_resumen(n: dict, filas: list) -> list:
    tope = n["disponibles"] is not None
    avance = f"{round(n['consumidos'] / n['cantidad'] * 100, 1)} %" if tope else "Sin tope" if n["sin_tope"] else "—"
    return [n["etiqueta"], n["nombre_servicio"], n["modalidad"], n["precio"], len(filas),
            round(sum(f["costo"] for f in filas), 2), n["consumidos"],
            n["cantidad"] if tope else "Sin tope", avance, n["monto_consumido"],
            "Sin tope" if n["sin_tope"] else n["monto_total"], "Activo" if n["is_active"] else "Inactivo"]


async def libro_oficial_excel(unit: dict, nogs_docs: list, desde=None, hasta=None) -> io.BytesIO:
    """Hoja "Resumen" (1 fila por NOG y por entrada de baja cuantía), una hoja por NOG y una
    hoja aparte de Baja Cuantía. Cada fila es una orden atendida; al pie, total y monto."""
    from openpyxl import Workbook
    ids = [n["id"] for n in nogs_docs]
    cont = await contadores_libro({"nog_id": {"$in": ids}})
    nogs = [nog_libro(n, cont.get(n["id"])) for n in nogs_docs]
    docs = {n["id"]: n for n in nogs_docs}
    por_nog = {}
    for f in await _filas(await ordenes_atendidas({"nog_id": {"$in": ids}}, desde, hasta), docs):
        por_nog.setdefault(f["nog_id"], []).append(f)
    con_numero = sorted((n for n in nogs if n["numero"].strip()), key=lambda n: n["numero"])
    sin_numero = sorted((n for n in nogs if not n["numero"].strip()), key=lambda n: n["etiqueta"])
    periodo = _periodo_texto(desde, hasta)
    base = [("Unidad IGSS", unit.get("name", "")), ("Periodo", periodo)]

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    r = _encabezado(ws, base + [("Generado", now_gt().strftime("%d/%m/%Y %H:%M"))])
    _fila_titulos(ws, r, COLUMNAS_RESUMEN)
    for n in con_numero + sin_numero:
        r += 1
        for c, v in enumerate(_fila_resumen(n, por_nog.get(n["id"], [])), 1):
            ws.cell(row=r, column=c, value=v)
    todas = [f for fs in por_nog.values() for f in fs]
    r += 1
    _, _, bold, _ = _estilos()
    for c, v in ((1, "TOTAL"), (5, len(todas)), (6, round(sum(f["costo"] for f in todas), 2)),
                 (7, sum(n["consumidos"] for n in nogs)), (10, round(sum(n["monto_consumido"] for n in nogs), 2))):
        ws.cell(row=r, column=c, value=v).font = bold
    _anchos(ws, len(COLUMNAS_RESUMEN), 20)

    for n in con_numero:
        _hoja_ordenes(wb.create_sheet(_titulo_hoja(wb, f"NOG {n['numero']}")),
                      base + [("NOG", n["numero"]), ("Servicio", n["nombre_servicio"]), ("Modalidad", n["modalidad"])],
                      por_nog.get(n["id"], []))
    if sin_numero:
        filas = sorted((f for n in sin_numero for f in por_nog.get(n["id"], [])),
                       key=lambda f: (f["fecha_primera_atencion"], f["no_sps"]))
        _hoja_ordenes(wb.create_sheet(_titulo_hoja(wb, "Baja Cuantía")),
                      base + [("Modalidad", "Baja Cuantía (sin número de NOG)")], filas)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _nombre_archivo(*partes) -> str:
    txt = "_".join(str(p) for p in partes if p)
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9_-]+", "_", txt).strip("_") + ".xlsx"


def _validar_rango(desde, hasta):
    if desde and hasta and desde > hasta:
        raise HTTPException(status_code=400, detail="La fecha 'desde' no puede ser posterior a 'hasta'")


def _descarga(buf: io.BytesIO, nombre: str) -> StreamingResponse:
    return StreamingResponse(buf, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.get("/nogs/{nog_id}/export/excel")
async def export_nog_excel(
    nog_id: str,
    desde: Optional[str] = Query(None, pattern=FECHA),
    hasta: Optional[str] = Query(None, pattern=FECHA),
    current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES)),
):
    """Listado oficial de un solo NOG (mismo formato que el de la unidad)."""
    _validar_rango(desde, hasta)
    nog = await _get_nog_or_404(nog_id)
    unit = await db.igss_units.find_one({"id": nog.get("unidad_id")}, {"_id": 0}) or {}
    buf = await libro_oficial_excel(unit, [nog], desde, hasta)
    return _descarga(buf, _nombre_archivo("Listado_oficial", etiqueta_catalogo(nog), desde, hasta))


@router.get("/{unit_id}/nogs/export/excel")
async def export_unidad_excel(
    unit_id: str,
    desde: Optional[str] = Query(None, pattern=FECHA),
    hasta: Optional[str] = Query(None, pattern=FECHA),
    current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES)),
):
    """Listado oficial de la unidad: 1 fila por orden atendida; filtro sobre la fecha de
    la PRIMERA atención. Entradas activas o con órdenes atendidas."""
    _validar_rango(desde, hasta)
    unit = await _unidad_or_404(unit_id)
    docs = await db.igss_nogs.find({"unidad_id": unit_id}, {"_id": 0}).to_list(None)
    con_ordenes = set(await db.igss_ordenes_libro.distinct("nog_id", {"unidad_id": unit_id, "estado": "atendida"}))
    docs = [n for n in docs if n.get("is_active", True) is not False or n["id"] in con_ordenes]
    buf = await libro_oficial_excel(unit, docs, desde, hasta)
    return _descarga(buf, _nombre_archivo("Listado_oficial", unit.get("name") or "IGSS", desde, hasta))


# ==================== PRODUCCIÓN ====================

async def produccion_rows(fecha=None, desde=None, hasta=None, unidad_id=None, nog=None) -> list:
    """Producción leída del libro: 1 fila por orden atendida en la fecha de su primera atención."""
    if fecha:
        desde = hasta = fecha
    ordenes = await ordenes_atendidas({"unidad_id": unidad_id} if unidad_id else {}, desde, hasta)
    nogs = {n["id"]: n for n in await db.igss_nogs.find(
        {"id": {"$in": list({o.get("nog_id") for o in ordenes})}}, {"_id": 0}).to_list(None)}
    units = await _unidades()
    rows = []
    for f in await _filas(ordenes, nogs):
        if nog and norm_txt(nog) not in norm_txt(f["nog"]):
            continue
        rows.append({**f, "fecha": f["fecha_primera_atencion"],
                     "unidad_nombre": units.get(f["unidad_id"], {}).get("name", "")})
    rows.sort(key=lambda r: (r["unidad_nombre"], r["nog"], r["fecha"], r["no_sps"]))
    return rows


@router.get("/produccion")
async def listar_produccion(
    fecha: Optional[str] = Query(None, pattern=FECHA),
    desde: Optional[str] = Query(None, pattern=FECHA),
    hasta: Optional[str] = Query(None, pattern=FECHA),
    unidad_id: Optional[str] = None,
    nog: Optional[str] = None,
    current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES)),
):
    """Producción IGSS: una línea por ORDEN atendida, con costo y estados (se editan en la orden)."""
    if not (fecha or desde or hasta):
        fecha = today_str_gt()
    rows = await produccion_rows(fecha, desde, hasta, unidad_id, nog)
    return {"data": rows, "totales": _produccion_totales(rows),
            "filtro": {"fecha": fecha, "desde": desde, "hasta": hasta, "unidad_id": unidad_id, "nog": nog}}


@router.get("/produccion/reporte/excel")
async def exportar_produccion_excel(
    fecha: Optional[str] = Query(None, pattern=FECHA),
    desde: Optional[str] = Query(None, pattern=FECHA),
    hasta: Optional[str] = Query(None, pattern=FECHA),
    unidad_id: Optional[str] = None,
    nog: Optional[str] = None,
    current_user: dict = Depends(require_role(LIBRO_IGSS_ROLES)),
):
    from openpyxl import Workbook
    if not (fecha or desde or hasta):
        fecha = today_str_gt()
    rows = await produccion_rows(fecha, desde, hasta, unidad_id, nog)
    tot = _produccion_totales(rows)
    wb = Workbook()
    ws = wb.active
    ws.title = "Produccion"
    titulos = ["Fecha 1ª atención", "Unidad", "NOG", "Modalidad", "No. SPS", "Paciente", "Expediente", "Procedimiento",
               "Médico", "Dosis", "Costo (Q)", "Impreso", "Enviado", "Facturado", "Pagado"]
    _fila_titulos(ws, 1, titulos)
    for r in rows:
        ws.append([fmt_fecha(r["fecha"]), r["unidad_nombre"], r["nog"], r["modalidad"], r["no_sps"], r["paciente_nombre"],
                   r["expediente"], r["procedimiento"], r["medico_nombre"], f"{r['dosis_aplicadas']} / {r['dosis_autorizadas']}",
                   r["costo"], *(_si(r[k]) for k in ESTADOS_PROD)])
    ws.append([])
    ws.append(["Órdenes", tot["servicios"]])
    ws.append(["Total producción (Q)", tot["total_costo"]])
    ws.append(["Total pagado (Q)", tot["total_pagado"]])
    ws.append(["Total pendiente (Q)", tot["total_pendiente"]])
    ws.append([])
    ws.append(["Por estado", "Cantidad", "Monto (Q)"])
    for e in ESTADOS_PROD:
        ws.append([e.capitalize(), tot["por_estado"][e]["cantidad"], tot["por_estado"][e]["monto"]])
    ws.append([])
    ws.append(["Por NOG", "Unidad", "Cantidad", "Monto (Q)"])
    for pn in tot["por_nog"]:
        ws.append([pn["nog"], pn["unidad_nombre"], pn["cantidad"], pn["monto"]])
    _anchos(ws, len(titulos))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return _descarga(buf, _nombre_archivo("produccion_igss", fecha or f"{desde or ''}_{hasta or ''}"))
