# /app/backend/routes/igss_nogs.py
# NOG por Unidad IGSS: catálogo de contratos de servicios, contador de
# acreditaciones (1 por atención/evaluación), avisos al 90% y bloqueo al 100%.

from fastapi import APIRouter, HTTPException, Depends, Body, Query
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
import io

from config.database import db
from routes.auth import get_current_user, require_permission

router = APIRouter(prefix="/igss-units", tags=["Unidades IGSS - NOG"])

TIPO_COMPRA_LABELS = {
    "compra_directa": "Compra Directa",
    "baja_cuantia": "Baja Cuantía",
    "contrato": "Contrato",
    "convenio": "Convenio",
}

UMBRAL_AVISO = 0.9  # 90%


# ==================== MODELOS ====================

class NogCreate(BaseModel):
    numero: str = Field(..., min_length=1, max_length=100)
    nombre_servicio: Optional[str] = ""
    tipo_compra: Optional[str] = ""
    cantidad: int = Field(..., ge=1)
    precio: float = Field(0, ge=0)


class NogUpdate(BaseModel):
    numero: Optional[str] = None
    nombre_servicio: Optional[str] = None
    tipo_compra: Optional[str] = None
    cantidad: Optional[int] = Field(None, ge=1)
    precio: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None


# ==================== HELPERS ====================

def _calcular_edad(birth_date: str) -> int:
    try:
        birth = datetime.strptime((birth_date or "")[:10], "%Y-%m-%d")
        today = datetime.now()
        return max(0, today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day)))
    except Exception:
        return 0


def _estado_nog(acreditados: int, cantidad: int, is_active: bool) -> str:
    if not is_active:
        return "inactivo"
    if cantidad <= 0:
        return "activo"
    if acreditados >= cantidad:
        return "completado"
    if acreditados >= cantidad * UMBRAL_AVISO:
        return "por_completarse"
    return "activo"


def _nog_con_derivados(nog: dict) -> dict:
    cantidad = int(nog.get("cantidad") or 0)
    acreditados = int(nog.get("acreditados") or 0)
    precio = float(nog.get("precio") or 0)
    disponibles = max(cantidad - acreditados, 0)
    is_active = nog.get("is_active", True)
    porcentaje = round((acreditados / cantidad) * 100, 1) if cantidad > 0 else 0
    return {
        "id": nog["id"],
        "unidad_id": nog.get("unidad_id", ""),
        "numero": nog.get("numero", ""),
        "nombre_servicio": nog.get("nombre_servicio", ""),
        "tipo_compra": nog.get("tipo_compra", ""),
        "tipo_compra_label": TIPO_COMPRA_LABELS.get(nog.get("tipo_compra", ""), nog.get("tipo_compra", "")),
        "cantidad": cantidad,
        "precio": precio,
        "acreditados": acreditados,
        "disponibles": disponibles,
        "porcentaje": porcentaje,
        "estado": _estado_nog(acreditados, cantidad, is_active),
        "is_active": is_active,
        "valor_total": round(cantidad * precio, 2),
        "valor_acreditado": round(acreditados * precio, 2),
        "valor_disponible": round(disponibles * precio, 2),
        "created_at": nog.get("created_at", ""),
        "updated_at": nog.get("updated_at", ""),
    }


async def _crear_acreditacion(nog: dict, paciente: dict, evaluacion: dict, origen: str, user: dict):
    """Crea una acreditación (1 servicio) de forma atómica y sin sobregiro.
    Devuelve (ok, motivo). Deduplica por (nog_id, evaluacion_id)."""
    eval_id = (evaluacion or {}).get("id")
    if eval_id:
        existe = await db.igss_nog_acreditaciones.find_one(
            {"nog_id": nog["id"], "evaluacion_id": eval_id}, {"_id": 0, "id": 1}
        )
        if existe:
            return False, "duplicada"

    cantidad = int(nog.get("cantidad") or 0)
    # Guarda atómica: solo incrementa si aún hay cupo (no hay sobregiro)
    res = await db.igss_nogs.update_one(
        {"id": nog["id"], "acreditados": {"$lt": cantidad}},
        {"$inc": {"acreditados": 1}}
    )
    if res.modified_count != 1:
        return False, "completado"

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "nog_id": nog["id"],
        "unidad_id": nog.get("unidad_id", ""),
        "numero_nog": nog.get("numero", ""),
        "paciente_id": (paciente or {}).get("id", ""),
        "paciente_expediente": (paciente or {}).get("record_number", ""),
        "paciente_nombre": f"{(paciente or {}).get('first_name', '')} {(paciente or {}).get('last_name', '')}".strip(),
        "evaluacion_id": eval_id or "",
        "fecha_acreditacion": now,
        "origen": origen,
        "anulada": False,
        "anulada_por": None,
        "anulada_por_nombre": None,
        "fecha_anulacion": None,
        "motivo_anulacion": None,
        "created_by": (user or {}).get("id", ""),
    }
    await db.igss_nog_acreditaciones.insert_one(doc)
    return True, "creada"


async def _sincronizar_acreditaciones(nog: dict, user: dict, origen: str = "retroactivo") -> int:
    """Acredita retroactivamente las evaluaciones existentes de pacientes activos
    de la unidad cuyo NOG coincide, hasta llenar el cupo. Idempotente (dedup)."""
    unidad_id = nog.get("unidad_id")
    numero = (nog.get("numero") or "").strip()
    cantidad = int(nog.get("cantidad") or 0)
    if not unidad_id or not numero or cantidad <= 0:
        return 0

    actual = await db.igss_nogs.find_one({"id": nog["id"]}, {"_id": 0, "acreditados": 1})
    acreditados = int((actual or {}).get("acreditados") or 0)
    if acreditados >= cantidad:
        return 0

    pacientes = await db.patients.find(
        {"is_active": True, "igss_unit_id": unidad_id, "igss_nog": numero},
        {"_id": 0}
    ).to_list(None)

    creadas = 0
    for pac in pacientes:
        if acreditados >= cantidad:
            break
        evs = await db.evaluaciones_oftalmologicas.find(
            {"paciente_id": pac["id"]}, {"_id": 0, "id": 1}
        ).sort("fecha_creacion", 1).to_list(None)
        for ev in evs:
            if acreditados >= cantidad:
                break
            ok, _ = await _crear_acreditacion(nog, pac, ev, origen, user)
            if ok:
                creadas += 1
                acreditados += 1
    return creadas


async def _acreditar_evaluacion(paciente: dict, evaluacion: dict, user: dict):
    """Hook llamado al crear una Evaluación Oftalmológica.
    Acredita 1 servicio si el paciente tiene un NOG del catálogo con cupo."""
    if not paciente:
        return
    if paciente.get("referral_institution") != "igss":
        return
    unidad_id = paciente.get("igss_unit_id")
    numero = (paciente.get("igss_nog") or "").strip()
    if not unidad_id or not numero:
        return
    nog = await db.igss_nogs.find_one(
        {"unidad_id": unidad_id, "numero": numero, "is_active": True}, {"_id": 0}
    )
    if not nog:
        return
    await _crear_acreditacion(nog, paciente, evaluacion, "evaluacion", user)


async def _get_nog_or_404(nog_id: str) -> dict:
    nog = await db.igss_nogs.find_one({"id": nog_id}, {"_id": 0})
    if not nog:
        raise HTTPException(status_code=404, detail="NOG no encontrado")
    return nog


async def _unidad_or_404(unit_id: str) -> dict:
    unit = await db.igss_units.find_one({"id": unit_id}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad IGSS no encontrada")
    return unit


# ==================== ENDPOINTS - CATÁLOGO DE NOG ====================

@router.get("/{unit_id}/nogs")
async def listar_nogs_unidad(
    unit_id: str,
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Lista los NOG de una unidad con contadores derivados, más los pacientes
    de la unidad con NOG fuera del catálogo y los que no tienen NOG (solo activos)."""
    unit = await _unidad_or_404(unit_id)

    nogs_docs = await db.igss_nogs.find({"unidad_id": unit_id}, {"_id": 0}).sort("numero", 1).to_list(1000)
    nogs = [_nog_con_derivados(n) for n in nogs_docs]
    numeros_catalogo = {(n.get("numero") or "").strip() for n in nogs_docs}

    pacientes = await db.patients.find(
        {"is_active": True, "igss_unit_id": unit_id},
        {"_id": 0, "id": 1, "record_number": 1, "first_name": 1, "last_name": 1,
         "dpi": 1, "phone": 1, "birth_date": 1, "igss_nog": 1, "igss_afiliacion": 1}
    ).to_list(None)

    sin_nog, fuera_catalogo = [], []
    for p in pacientes:
        numero = (p.get("igss_nog") or "").strip()
        fila = {
            "id": p["id"],
            "record_number": p.get("record_number", ""),
            "full_name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "dpi": p.get("dpi", ""),
            "phone": p.get("phone", ""),
            "edad": _calcular_edad(p.get("birth_date", "")),
            "igss_nog": numero,
            "igss_afiliacion": p.get("igss_afiliacion", ""),
        }
        if not numero:
            sin_nog.append(fila)
        elif numero not in numeros_catalogo:
            fuera_catalogo.append(fila)

    return {
        "unidad": {"id": unit["id"], "name": unit.get("name", ""), "code": unit.get("code", "")},
        "nogs": nogs,
        "pacientes_nog_no_catalogado": fuera_catalogo,
        "pacientes_sin_nog": sin_nog,
        "totales": {
            "nogs": len(nogs),
            "servicios_contratados": sum(n["cantidad"] for n in nogs),
            "servicios_acreditados": sum(n["acreditados"] for n in nogs),
            "servicios_disponibles": sum(n["disponibles"] for n in nogs),
            "valor_total": round(sum(n["valor_total"] for n in nogs), 2),
        },
    }


@router.get("/{unit_id}/nogs-activos")
async def listar_nogs_activos(
    unit_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Lista ligera para el selector de NOG en la ficha del paciente.
    Devuelve los NOG activos con su estado y disponibilidad."""
    nogs_docs = await db.igss_nogs.find(
        {"unidad_id": unit_id, "is_active": True}, {"_id": 0}
    ).sort("numero", 1).to_list(1000)
    return [
        {
            "id": n["id"],
            "numero": n.get("numero", ""),
            "nombre_servicio": n.get("nombre_servicio", ""),
            "disponibles": max(int(n.get("cantidad") or 0) - int(n.get("acreditados") or 0), 0),
            "cantidad": int(n.get("cantidad") or 0),
            "estado": _estado_nog(int(n.get("acreditados") or 0), int(n.get("cantidad") or 0), True),
        }
        for n in nogs_docs
    ]


@router.post("/{unit_id}/nogs")
async def crear_nog(
    unit_id: str,
    data: NogCreate,
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Crea un NOG (contrato) en la unidad y acredita retroactivamente lo existente."""
    await _unidad_or_404(unit_id)
    numero = data.numero.strip()

    existing = await db.igss_nogs.find_one({"unidad_id": unit_id, "numero": numero})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un NOG con este número en la unidad")

    now = datetime.now(timezone.utc).isoformat()
    nog_doc = {
        "id": str(uuid.uuid4()),
        "unidad_id": unit_id,
        "numero": numero,
        "nombre_servicio": (data.nombre_servicio or "").strip(),
        "tipo_compra": data.tipo_compra or "",
        "cantidad": int(data.cantidad),
        "precio": float(data.precio or 0),
        "acreditados": 0,
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.igss_nogs.insert_one(nog_doc)
    if "_id" in nog_doc:
        del nog_doc["_id"]

    # Conteo retroactivo de lo ya existente
    creadas = await _sincronizar_acreditaciones(nog_doc, current_user, origen="retroactivo")

    fresh = await db.igss_nogs.find_one({"id": nog_doc["id"]}, {"_id": 0})
    result = _nog_con_derivados(fresh)
    result["acreditaciones_retroactivas"] = creadas
    return result


@router.put("/nogs/{nog_id}")
async def actualizar_nog(
    nog_id: str,
    data: NogUpdate,
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Actualiza un NOG. No modifica el contador de acreditaciones."""
    nog = await _get_nog_or_404(nog_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")

    if "numero" in update_data:
        nuevo = update_data["numero"].strip()
        update_data["numero"] = nuevo
        if nuevo.lower() != (nog.get("numero") or "").lower():
            dup = await db.igss_nogs.find_one(
                {"unidad_id": nog["unidad_id"], "numero": nuevo, "id": {"$ne": nog_id}}
            )
            if dup:
                raise HTTPException(status_code=400, detail="Ya existe un NOG con este número en la unidad")

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.igss_nogs.update_one({"id": nog_id}, {"$set": update_data})
    fresh = await db.igss_nogs.find_one({"id": nog_id}, {"_id": 0})
    return _nog_con_derivados(fresh)


@router.delete("/nogs/{nog_id}")
async def eliminar_nog(
    nog_id: str,
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Elimina un NOG y todas sus acreditaciones."""
    await _get_nog_or_404(nog_id)
    await db.igss_nog_acreditaciones.delete_many({"nog_id": nog_id})
    await db.igss_nogs.delete_one({"id": nog_id})
    return {"message": "NOG eliminado correctamente"}


@router.post("/nogs/{nog_id}/recalcular")
async def recalcular_nog(
    nog_id: str,
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Re-sincroniza el contador con las evaluaciones existentes (idempotente).
    Útil tras importar evaluaciones o pacientes. Respeta las anulaciones."""
    nog = await _get_nog_or_404(nog_id)
    creadas = await _sincronizar_acreditaciones(nog, current_user, origen="recalculo")
    fresh = await db.igss_nogs.find_one({"id": nog_id}, {"_id": 0})
    result = _nog_con_derivados(fresh)
    result["acreditaciones_nuevas"] = creadas
    return result


# ==================== ENDPOINTS - ACREDITACIONES / PACIENTES ====================

@router.get("/nogs/alertas")
async def alertas_nogs(
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Alertas de límite: NOG activos que alcanzaron el 90% (por completarse) o el
    100% (completados/bloqueados). Sirve para renovar el contrato a tiempo."""
    nogs = await db.igss_nogs.find({"is_active": True}, {"_id": 0}).to_list(None)
    units = {u["id"]: u for u in await db.igss_units.find(
        {}, {"_id": 0, "id": 1, "name": 1, "code": 1}).to_list(1000)}

    alertas = []
    for n in nogs:
        d = _nog_con_derivados(n)
        if d["estado"] in ("por_completarse", "completado"):
            u = units.get(n.get("unidad_id"), {})
            alertas.append({
                "unidad_id": n.get("unidad_id", ""),
                "unidad_nombre": u.get("name", ""),
                "unidad_codigo": u.get("code", ""),
                "nog_id": d["id"],
                "numero": d["numero"],
                "nombre_servicio": d["nombre_servicio"],
                "acreditados": d["acreditados"],
                "cantidad": d["cantidad"],
                "disponibles": d["disponibles"],
                "porcentaje": d["porcentaje"],
                "estado": d["estado"],
            })

    # Completados primero, luego por porcentaje descendente
    alertas.sort(key=lambda a: (0 if a["estado"] == "completado" else 1, -a["porcentaje"]))
    return {
        "alertas": alertas,
        "total": len(alertas),
        "completados": sum(1 for a in alertas if a["estado"] == "completado"),
        "por_completarse": sum(1 for a in alertas if a["estado"] == "por_completarse"),
        "umbral_aviso": int(UMBRAL_AVISO * 100),
    }


@router.get("/nogs/{nog_id}/pacientes")
async def listar_pacientes_nog(
    nog_id: str,
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Lista las acreditaciones (pacientes atendidos) del NOG. Solo pacientes activos."""
    nog = await _get_nog_or_404(nog_id)
    acreds = await db.igss_nog_acreditaciones.find(
        {"nog_id": nog_id, "anulada": {"$ne": True}}, {"_id": 0}
    ).sort("fecha_acreditacion", 1).to_list(None)

    pac_ids = list({a["paciente_id"] for a in acreds if a.get("paciente_id")})
    pacientes = {}
    if pac_ids:
        cursor = db.patients.find(
            {"id": {"$in": pac_ids}, "is_active": True}, {"_id": 0}
        )
        async for p in cursor:
            pacientes[p["id"]] = p

    filas = []
    for a in acreds:
        p = pacientes.get(a.get("paciente_id"))
        if not p:
            continue  # paciente inactivo o eliminado -> no se lista
        filas.append({
            "acreditacion_id": a["id"],
            "evaluacion_id": a.get("evaluacion_id", ""),
            "fecha_acreditacion": a.get("fecha_acreditacion", ""),
            "origen": a.get("origen", ""),
            "paciente_id": p["id"],
            "record_number": p.get("record_number", ""),
            "full_name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "dpi": p.get("dpi", ""),
            "igss_afiliacion": p.get("igss_afiliacion", ""),
            "igss_no_sps": p.get("igss_no_sps", ""),
            "igss_codigo": p.get("igss_codigo", ""),
            "igss_tipo_compra": p.get("igss_tipo_compra", ""),
            "phone": p.get("phone", ""),
            "edad": _calcular_edad(p.get("birth_date", "")),
            "numero_nog": a.get("numero_nog", ""),
        })

    return {"nog": _nog_con_derivados(nog), "acreditaciones": filas, "total": len(filas)}


@router.post("/nogs/{nog_id}/acreditaciones/{acred_id}/anular")
async def anular_acreditacion(
    nog_id: str,
    acred_id: str,
    motivo: str = Body("", embed=True),
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Anula una acreditación hecha por error; libera el servicio (queda disponible)."""
    acred = await db.igss_nog_acreditaciones.find_one({"id": acred_id, "nog_id": nog_id}, {"_id": 0})
    if not acred:
        raise HTTPException(status_code=404, detail="Acreditación no encontrada")
    if acred.get("anulada"):
        raise HTTPException(status_code=400, detail="La acreditación ya está anulada")

    now = datetime.now(timezone.utc).isoformat()
    await db.igss_nog_acreditaciones.update_one(
        {"id": acred_id},
        {"$set": {
            "anulada": True,
            "anulada_por": current_user["id"],
            "anulada_por_nombre": current_user.get("name", current_user.get("username", "")),
            "fecha_anulacion": now,
            "motivo_anulacion": motivo or "",
        }}
    )
    # Liberar cupo (no baja de 0)
    await db.igss_nogs.update_one(
        {"id": nog_id, "acreditados": {"$gt": 0}},
        {"$inc": {"acreditados": -1}}
    )
    fresh = await db.igss_nogs.find_one({"id": nog_id}, {"_id": 0})
    return {"message": "Acreditación anulada", "nog": _nog_con_derivados(fresh)}


# ==================== EXPORTACIÓN A EXCEL ====================

def _hoja_pacientes(ws, nog: dict, filas: list):
    from openpyxl.styles import Font, PatternFill, Alignment
    header_fill = PatternFill(start_color="0F6E56", end_color="0F6E56", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    label_font = Font(bold=True)

    # Encabezado del NOG
    d = _nog_con_derivados(nog)
    info = [
        ("NOG", d["numero"]),
        ("Servicio", d["nombre_servicio"]),
        ("Tipo de compra", d["tipo_compra_label"]),
        ("Cantidad contratada", d["cantidad"]),
        ("Precio unitario (Q)", d["precio"]),
        ("Acreditados", d["acreditados"]),
        ("Disponibles", d["disponibles"]),
        ("Valor total (Q)", d["valor_total"]),
        ("Valor acreditado (Q)", d["valor_acreditado"]),
        ("Valor disponible (Q)", d["valor_disponible"]),
    ]
    r = 1
    for label, value in info:
        ws.cell(row=r, column=1, value=label).font = label_font
        ws.cell(row=r, column=2, value=value)
        r += 1
    r += 1

    headers = ["Expediente", "Nombre y Apellido", "DPI", "Afiliación IGSS", "No. SPS",
               "Código", "Tipo de Compra", "Teléfono", "Edad", "NOG", "Fecha de Acreditación"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=r, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    header_row = r
    r += 1

    for f in filas:
        fecha = f.get("fecha_acreditacion", "")
        try:
            fecha = datetime.fromisoformat(fecha.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except Exception:
            pass
        valores = [
            f.get("record_number", ""), f.get("full_name", ""), f.get("dpi", ""),
            f.get("igss_afiliacion", ""), f.get("igss_no_sps", ""), f.get("igss_codigo", ""),
            TIPO_COMPRA_LABELS.get(f.get("igss_tipo_compra", ""), f.get("igss_tipo_compra", "")),
            f.get("phone", ""), f.get("edad", ""), f.get("numero_nog", ""), fecha,
        ]
        for col, v in enumerate(valores, 1):
            ws.cell(row=r, column=col, value=v)
        r += 1

    import openpyxl
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20
    return header_row


async def _filas_export_nog(nog_id: str) -> list:
    acreds = await db.igss_nog_acreditaciones.find(
        {"nog_id": nog_id, "anulada": {"$ne": True}}, {"_id": 0}
    ).sort("fecha_acreditacion", 1).to_list(None)
    pac_ids = list({a["paciente_id"] for a in acreds if a.get("paciente_id")})
    pacientes = {}
    if pac_ids:
        cursor = db.patients.find({"id": {"$in": pac_ids}, "is_active": True}, {"_id": 0})
        async for p in cursor:
            pacientes[p["id"]] = p
    filas = []
    for a in acreds:
        p = pacientes.get(a.get("paciente_id"))
        if not p:
            continue
        filas.append({
            "record_number": p.get("record_number", ""),
            "full_name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "dpi": p.get("dpi", ""),
            "igss_afiliacion": p.get("igss_afiliacion", ""),
            "igss_no_sps": p.get("igss_no_sps", ""),
            "igss_codigo": p.get("igss_codigo", ""),
            "igss_tipo_compra": p.get("igss_tipo_compra", ""),
            "phone": p.get("phone", ""),
            "edad": _calcular_edad(p.get("birth_date", "")),
            "numero_nog": a.get("numero_nog", ""),
            "fecha_acreditacion": a.get("fecha_acreditacion", ""),
        })
    return filas


def _safe_sheet_title(text: str) -> str:
    invalid = set('[]:*?/\\')
    clean = "".join(c for c in str(text) if c not in invalid).strip()
    return (clean or "NOG")[:31]


@router.get("/nogs/{nog_id}/export/excel")
async def export_nog_excel(
    nog_id: str,
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Exporta a Excel el listado de pacientes acreditados de un NOG."""
    nog = await _get_nog_or_404(nog_id)
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = _safe_sheet_title(f"NOG {nog.get('numero', '')}")
    filas = await _filas_export_nog(nog_id)
    _hoja_pacientes(ws, nog, filas)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"NOG_{(nog.get('numero') or 'export')}.xlsx".replace("/", "-").replace(" ", "_")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{unit_id}/nogs/export/excel")
async def export_unidad_excel(
    unit_id: str,
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Exporta a Excel todos los NOG de la unidad (una hoja por NOG)."""
    unit = await _unidad_or_404(unit_id)
    nogs = await db.igss_nogs.find({"unidad_id": unit_id}, {"_id": 0}).sort("numero", 1).to_list(1000)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = openpyxl.Workbook()

    # Hoja resumen
    ws = wb.active
    ws.title = "Resumen"
    header_fill = PatternFill(start_color="0F6E56", end_color="0F6E56", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    ws.cell(row=1, column=1, value=f"Unidad IGSS: {unit.get('name', '')}").font = Font(bold=True, size=12)
    headers = ["NOG", "Servicio", "Tipo de compra", "Cantidad", "Precio (Q)",
               "Acreditados", "Disponibles", "Valor total (Q)", "Estado"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    r = 4
    for n in nogs:
        d = _nog_con_derivados(n)
        for col, v in enumerate([
            d["numero"], d["nombre_servicio"], d["tipo_compra_label"], d["cantidad"],
            d["precio"], d["acreditados"], d["disponibles"], d["valor_total"], d["estado"],
        ], 1):
            ws.cell(row=r, column=col, value=v)
        r += 1
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18

    # Una hoja por NOG
    for n in nogs:
        hoja = wb.create_sheet(title=_safe_sheet_title(f"NOG {n.get('numero', '')}"))
        filas = await _filas_export_nog(n["id"])
        _hoja_pacientes(hoja, n, filas)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"Unidad_{(unit.get('name') or 'IGSS')}_NOGs.xlsx".replace("/", "-").replace(" ", "_")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
