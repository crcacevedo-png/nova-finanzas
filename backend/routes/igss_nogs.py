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
from routes.auth import get_current_user, require_permission, require_role
from utils.timezone import today_str_gt

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
    monto_total: Optional[float] = Field(None, ge=0)
    fecha_asignacion: Optional[str] = ""


class NogUpdate(BaseModel):
    numero: Optional[str] = None
    nombre_servicio: Optional[str] = None
    tipo_compra: Optional[str] = None
    cantidad: Optional[int] = Field(None, ge=1)
    precio: Optional[float] = Field(None, ge=0)
    monto_total: Optional[float] = Field(None, ge=0)
    fecha_asignacion: Optional[str] = None
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
    monto_total = nog.get("monto_total")
    if monto_total is None:
        monto_total = round(cantidad * precio, 2)
    else:
        monto_total = round(float(monto_total), 2)
    return {
        "id": nog["id"],
        "unidad_id": nog.get("unidad_id", ""),
        "numero": nog.get("numero", ""),
        "nombre_servicio": nog.get("nombre_servicio", ""),
        "tipo_compra": nog.get("tipo_compra", ""),
        "tipo_compra_label": TIPO_COMPRA_LABELS.get(nog.get("tipo_compra", ""), nog.get("tipo_compra", "")),
        "fecha_asignacion": nog.get("fecha_asignacion", ""),
        "cantidad": cantidad,
        "precio": precio,
        "monto_total": monto_total,
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


async def _crear_acreditacion(nog: dict, paciente: dict, evaluacion: dict, origen: str, user: dict, no_sps: str = None):
    """Crea una acreditación (1 servicio) de forma atómica y sin sobregiro.
    Devuelve (ok, motivo). La unidad facturable es la AUTORIZACIÓN (No. SPS):
    se deduplica por (nog_id, paciente_id, no_sps). Autorizaciones distintas
    (otro No. SPS) bajo el mismo NOG cuentan por separado.
    Reglas de bloqueo para no duplicar descuentos ni afectar lo histórico:
      - Si la nueva consulta NO trae No. SPS => 1 descuento por paciente/NOG
        (cualquier acreditación vigente del paciente en ese NOG lo bloquea).
      - Una acreditación vigente SIN No. SPS (legada/pre-regla) actúa como
        comodín y bloquea nuevos descuentos del paciente en ese NOG.
      - Misma autorización (mismo No. SPS) ya acreditada => no descuenta de nuevo."""
    pac_id = (paciente or {}).get("id")
    eval_id = (evaluacion or {}).get("id")
    sps = (no_sps or "").strip()
    # Deduplicar por (paciente, NOG, autorización)
    if pac_id:
        existentes = await db.igss_nog_acreditaciones.find(
            {"nog_id": nog["id"], "paciente_id": pac_id, "anulada": {"$ne": True}},
            {"_id": 0, "no_sps": 1}
        ).to_list(None)
        for e in existentes:
            e_sps = (e.get("no_sps") or "").strip()
            if sps == "" or e_sps == "" or e_sps == sps:
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
        "no_sps": sps,
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
        {"is_active": True, "igss_unit_id": unidad_id,
         "$or": [{"igss_nog": numero}, {"igss_ordenes.nog": numero}]},
        {"_id": 0}
    ).to_list(None)

    creadas = 0
    for pac in pacientes:
        if acreditados >= cantidad:
            break
        # Vincular una evaluación existente si la hay (solo informativo); se acredita 1 por paciente
        ev = await db.evaluaciones_oftalmologicas.find_one(
            {"paciente_id": pac["id"]}, {"_id": 0, "id": 1}, sort=[("fecha_creacion", 1)]
        )
        ok, _ = await _crear_acreditacion(nog, pac, ev, origen, user)
        if ok:
            creadas += 1
            acreditados += 1
    return creadas


async def _anular_acreditacion_interna(acred: dict, user: dict, motivo: str):
    """Anula una acreditación y libera el cupo del NOG (uso interno)."""
    now = datetime.now(timezone.utc).isoformat()
    await db.igss_nog_acreditaciones.update_one(
        {"id": acred["id"]},
        {"$set": {
            "anulada": True,
            "anulada_por": (user or {}).get("id"),
            "anulada_por_nombre": (user or {}).get("name", (user or {}).get("username", "")),
            "fecha_anulacion": now,
            "motivo_anulacion": motivo,
        }}
    )
    await db.igss_nogs.update_one(
        {"id": acred["nog_id"], "acreditados": {"$gt": 0}},
        {"$inc": {"acreditados": -1}}
    )


async def _reconciliar_nog_paciente(paciente: dict, user: dict, origen: str = "asignacion", solo_numeros=None):
    """Asegura que el paciente consuma 1 servicio por cada AUTORIZACIÓN distinta
    (par NOG + No. SPS) de sus órdenes IGSS (unidad activa + NOG del catálogo
    activo). Dos órdenes del mismo NOG con distinto No. SPS consumen 2 cupos.
    Libera las acreditaciones que ya no correspondan. Soporta múltiples órdenes.
    Hook llamado al crear/editar/desactivar/reactivar un paciente.
    Si se pasa `solo_numeros` (set), solo se consideran objetivo los NOG cuyo número
    esté en ese conjunto (usado por el recálculo basado en evaluaciones reales)."""
    if not paciente:
        return
    pac_id = paciente.get("id")
    if not pac_id:
        return

    # Órdenes objetivo a partir de las órdenes del paciente (o legacy igss_nog).
    # La unidad objetivo es la AUTORIZACIÓN: (nog_id, no_sps).
    target_orders = {}  # (nog_id, sps) -> (nog_doc, sps)
    if (paciente.get("is_active", True)
            and paciente.get("referral_institution") == "igss"
            and paciente.get("igss_unit_id")):
        ordenes = paciente.get("igss_ordenes") or []
        pares = [(str(o.get("nog", "") or "").strip(), str(o.get("no_sps", "") or "").strip())
                 for o in ordenes if str(o.get("nog", "") or "").strip()]
        if not pares:
            leg = (paciente.get("igss_nog") or "").strip()
            if leg:
                pares = [(leg, (paciente.get("igss_no_sps") or "").strip())]
        if solo_numeros is not None:
            pares = [(n, s) for (n, s) in pares if n in solo_numeros]
        # Autorizaciones derivadas de evaluaciones REALES del paciente: una
        # evaluación con un No. SPS nuevo (no presente en las órdenes) también es
        # una autorización facturable y su cupo no debe liberarse al editar al
        # paciente. Se ignoran los borradores vacíos y los SPS en blanco.
        evs = await db.evaluaciones_oftalmologicas.find(
            {"paciente_id": pac_id}, {"_id": 0}
        ).to_list(None)
        for ev in evs:
            if eval_es_borrador_vacio(ev):
                continue
            n = (ev.get("igss_nog") or "").strip()
            s = (ev.get("igss_no_sps") or "").strip()
            if not n or not s:
                continue
            if solo_numeros is not None and n not in solo_numeros:
                continue
            pares.append((n, s))
        for numero, sps in set(pares):
            nog = await db.igss_nogs.find_one(
                {"unidad_id": paciente["igss_unit_id"], "numero": numero, "is_active": True},
                {"_id": 0}
            )
            if nog:
                target_orders[(nog["id"], sps)] = (nog, sps)
    target_keys = set(target_orders.keys())

    # Acreditaciones vigentes del paciente
    vigentes = await db.igss_nog_acreditaciones.find(
        {"paciente_id": pac_id, "anulada": {"$ne": True}}, {"_id": 0}
    ).to_list(None)

    ya_tiene = set()
    for a in vigentes:
        nid = a.get("nog_id")
        a_sps = (a.get("no_sps") or "").strip()
        matched = None
        if (nid, a_sps) in target_keys and (nid, a_sps) not in ya_tiene:
            matched = (nid, a_sps)
        elif a_sps == "":
            # Legada sin SPS: cubre cualquier autorización pendiente de ese NOG
            cand = [k for k in target_keys if k[0] == nid and k not in ya_tiene]
            if cand:
                matched = cand[0]
        if matched:
            ya_tiene.add(matched)  # conservar exactamente una por autorización objetivo
        elif a.get("origen") == "manual":
            continue  # conservar descuentos aplicados manualmente (corrección puntual)
        else:
            motivo = "reasignacion_nog" if target_keys else "sin_nog"
            await _anular_acreditacion_interna(a, user, motivo)

    # Crear las acreditaciones objetivo que falten
    for key, (nog, sps) in target_orders.items():
        if key not in ya_tiene:
            await _crear_acreditacion(nog, paciente, None, origen, user, no_sps=sps)


async def _acreditar_evaluacion(paciente: dict, evaluacion: dict, user: dict):
    """Hook llamado al crear una Evaluación Oftalmológica.
    Acredita 1 servicio al NOG de la orden (autorización/No. SPS) de la evaluación
    si tiene cupo. La primera consulta por autorización descuenta; las siguientes
    bajo el mismo No. SPS no vuelven a descontar (dedup por nog/paciente/No. SPS)."""
    if not paciente:
        return
    if paciente.get("referral_institution") != "igss":
        return
    unidad_id = paciente.get("igss_unit_id")
    # Preferir el NOG de la orden vinculada a la evaluación; si no, el legacy del paciente
    numero = (((evaluacion or {}).get("igss_nog") or "").strip()
              or (paciente.get("igss_nog") or "").strip())
    if not unidad_id or not numero:
        return
    # Autorización (No. SPS): de la evaluación; respaldo en la orden del paciente que coincide
    sps = ((evaluacion or {}).get("igss_no_sps") or "").strip()
    if not sps:
        for o in (paciente.get("igss_ordenes") or []):
            if str(o.get("nog", "") or "").strip() == numero:
                sps = str(o.get("no_sps", "") or "").strip()
                break
        if not sps:
            sps = (paciente.get("igss_no_sps") or "").strip()
    nog = await db.igss_nogs.find_one(
        {"unidad_id": unidad_id, "numero": numero, "is_active": True}, {"_id": 0}
    )
    if not nog:
        return
    await _crear_acreditacion(nog, paciente, evaluacion, "evaluacion", user, no_sps=sps)


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
    # Conteo de pacientes activos asignados a cada NOG de esta unidad (una sola agregación)
    conteo_docs = await db.patients.aggregate([
        {"$match": {"igss_unit_id": unit_id, "is_active": True, "igss_nog": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$igss_nog", "total": {"$sum": 1}}},
    ]).to_list(2000)
    conteo_por_nog = {c["_id"]: c["total"] for c in conteo_docs}
    return [
        {
            "id": n["id"],
            "numero": n.get("numero", ""),
            "nombre_servicio": n.get("nombre_servicio", ""),
            "disponibles": max(int(n.get("cantidad") or 0) - int(n.get("acreditados") or 0), 0),
            "cantidad": int(n.get("cantidad") or 0),
            "acreditados": int(n.get("acreditados") or 0),
            "pacientes_asignados": conteo_por_nog.get(n.get("numero", ""), 0),
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
        "monto_total": (round(float(data.monto_total), 2) if data.monto_total is not None
                        else round(float(data.precio or 0) * int(data.cantidad), 2)),
        "fecha_asignacion": (data.fecha_asignacion or "").strip(),
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


@router.post("/nogs/reconciliar-todo")
async def reconciliar_todo(
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Backfill idempotente: recalcula el consumo de TODOS los NOG a partir de los
    pacientes activos asignados (1 servicio por paciente). Corrige NOG de pacientes
    ingresados antes de que la asignación descontara el cupo y elimina duplicados."""
    pacientes = await db.patients.find({"is_active": True}, {"_id": 0}).to_list(None)
    reconciliados = 0
    for pac in pacientes:
        await _reconciliar_nog_paciente(pac, current_user, origen="backfill")
        reconciliados += 1
    return {"pacientes_reconciliados": reconciliados}


@router.post("/nogs/{nog_id}/recalcular")
async def recalcular_nog(
    nog_id: str,
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Re-sincroniza el contador con las evaluaciones existentes (idempotente).
    Útil tras importar evaluaciones o pacientes. Respeta las anulaciones."""
    nog = await _get_nog_or_404(nog_id)
    creadas = await _sincronizar_acreditaciones(nog, current_user, origen="recalculo")
    # Corregir cualquier desajuste del contador: acreditados = acreditaciones vigentes
    activos = await db.igss_nog_acreditaciones.count_documents(
        {"nog_id": nog_id, "anulada": {"$ne": True}}
    )
    await db.igss_nogs.update_one({"id": nog_id}, {"$set": {"acreditados": activos}})
    fresh = await db.igss_nogs.find_one({"id": nog_id}, {"_id": 0})
    result = _nog_con_derivados(fresh)
    result["acreditaciones_nuevas"] = creadas
    return result


# ==================== MANTENIMIENTO: BORRADORES VACÍOS Y RECÁLCULO ====================

MANTENIMIENTO_ROLES = ["superadmin", "administrador_igss"]

# Proyección mínima para evaluar si una evaluación es un borrador vacío
_BORRADOR_PROJ = {
    "_id": 0, "id": 1, "paciente_id": 1, "paciente_nombre": 1, "paciente_expediente": 1,
    "fecha": 1, "medico_id": 1, "medico_nombre": 1, "igss_procedimiento": 1, "igss_nog": 1,
    "motivo_consulta": 1, "padecimiento_actual": 1, "plan": 1, "diagnosticos": 1,
    "examen": 1, "igss_med_proc": 1, "procedimientos": 1, "recetas": 1, "recomendaciones": 1,
}


class LimpiarBorradoresBody(BaseModel):
    confirmar: bool = False


@router.get("/mantenimiento/borradores-vacios")
async def preview_borradores_vacios(
    current_user: dict = Depends(require_role(MANTENIMIENTO_ROLES))
):
    """Previsualiza las evaluaciones que son borradores vacíos (sin médico y sin datos
    clínicos). No elimina nada: devuelve total y una muestra para revisión."""
    total_evals = 0
    vacios = []
    cursor = db.evaluaciones_oftalmologicas.find({}, _BORRADOR_PROJ)
    async for ev in cursor:
        total_evals += 1
        if eval_es_borrador_vacio(ev):
            vacios.append(ev)
    muestra = sorted(vacios, key=lambda e: e.get("fecha", ""), reverse=True)[:50]
    return {
        "total_evaluaciones": total_evals,
        "total_vacios": len(vacios),
        "muestra": [{
            "id": e["id"],
            "paciente_nombre": e.get("paciente_nombre", ""),
            "expediente": e.get("paciente_expediente", ""),
            "fecha": e.get("fecha", ""),
        } for e in muestra],
    }


@router.post("/mantenimiento/borradores-vacios/limpiar")
async def limpiar_borradores_vacios(
    body: LimpiarBorradoresBody,
    current_user: dict = Depends(require_role(MANTENIMIENTO_ROLES))
):
    """Elimina todas las evaluaciones que son borradores vacíos. Requiere confirmación."""
    if not body.confirmar:
        raise HTTPException(status_code=400, detail="Debe confirmar la eliminación")
    ids = []
    cursor = db.evaluaciones_oftalmologicas.find({}, _BORRADOR_PROJ)
    async for ev in cursor:
        if eval_es_borrador_vacio(ev):
            ids.append(ev["id"])
    eliminados = 0
    for i in range(0, len(ids), 500):
        res = await db.evaluaciones_oftalmologicas.delete_many({"id": {"$in": ids[i:i + 500]}})
        eliminados += res.deleted_count
    # Limpiar estados de producción huérfanos de las evaluaciones eliminadas
    for i in range(0, len(ids), 500):
        await db.igss_produccion.delete_many({"evaluacion_id": {"$in": ids[i:i + 500]}})
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "LIMPIEZA_BORRADORES_VACIOS",
        "user_id": current_user.get("id", ""),
        "user_name": current_user.get("username", current_user.get("name", "")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {"eliminados": eliminados},
    })
    return {"eliminados": eliminados}


async def _recalcular_consumo_por_evaluaciones(user: dict):
    """Recalcula el consumo (acreditaciones) de cada NOG exigiendo que el paciente
    tenga al menos una evaluación REAL (con datos clínicos) de ese NOG. Los pacientes
    con solo borradores vacíos o sin evaluación dejan de consumir cupo. Conserva las
    acreditaciones marcadas manualmente."""
    # Pacientes IGSS (para fallback de orden y datos del paciente)
    pac_igss = await db.patients.find(
        {"referral_institution": "igss"}, {"_id": 0}
    ).to_list(None)
    pac_map = {p["id"]: p for p in pac_igss}
    # Mapa paciente -> set de números de NOG con evaluación REAL
    real = {}
    cursor = db.evaluaciones_oftalmologicas.find({}, _BORRADOR_PROJ)
    async for ev in cursor:
        if eval_es_borrador_vacio(ev):
            continue
        pac = pac_map.get(ev.get("paciente_id"))
        if not pac:
            continue  # evaluación de paciente no IGSS: no afecta consumo
        numero, _, _, _ = _resolver_orden(ev, pac)
        if numero:
            real.setdefault(ev["paciente_id"], set()).add(numero)
    # Pacientes a reconciliar: activos IGSS con unidad + cualquiera con acreditación vigente
    acred_ids = await db.igss_nog_acreditaciones.distinct("paciente_id", {"anulada": {"$ne": True}})
    ids = set(acred_ids) | {p["id"] for p in pac_igss if p.get("is_active", True) and p.get("igss_unit_id")}
    faltan = [pid for pid in ids if pid not in pac_map]
    if faltan:
        for i in range(0, len(faltan), 500):
            extra = await db.patients.find({"id": {"$in": faltan[i:i + 500]}}, {"_id": 0}).to_list(None)
            for p in extra:
                pac_map[p["id"]] = p
    procesados = 0
    for pid in ids:
        pac = pac_map.get(pid)
        if not pac:
            continue
        await _reconciliar_nog_paciente(pac, user, origen="recalculo_eval", solo_numeros=real.get(pid, set()))
        procesados += 1
    # Resincronizar contadores de todos los NOG
    nogs = await db.igss_nogs.find({}, {"_id": 0, "id": 1}).to_list(None)
    for n in nogs:
        activos = await db.igss_nog_acreditaciones.count_documents(
            {"nog_id": n["id"], "anulada": {"$ne": True}})
        await db.igss_nogs.update_one({"id": n["id"]}, {"$set": {"acreditados": activos}})
    vigentes = await db.igss_nog_acreditaciones.count_documents({"anulada": {"$ne": True}})
    return {"pacientes_procesados": procesados, "acreditaciones_vigentes": vigentes, "nogs": len(nogs)}


@router.post("/nogs/recalcular-por-evaluaciones")
async def recalcular_por_evaluaciones(
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Recalcula el consumo de TODOS los NOG contando solo a los pacientes con una
    evaluación real (con datos clínicos). Útil tras limpiar borradores vacíos."""
    res = await _recalcular_consumo_por_evaluaciones(current_user)
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "RECALCULO_NOG_POR_EVALUACIONES",
        "user_id": current_user.get("id", ""),
        "user_name": current_user.get("username", current_user.get("name", "")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": res,
    })
    return res


# ==================== ENDPOINTS - ACREDITACIONES / PACIENTES ====================

@router.get("/nogs/all")
async def listar_todos_nogs(
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Lista TODOS los NOG de TODAS las unidades (para el menú central de NOG),
    con el nombre de la unidad y los contadores derivados. El filtrado por unidad,
    estado y la búsqueda se hacen en el cliente."""
    units = {u["id"]: u for u in await db.igss_units.find(
        {}, {"_id": 0, "id": 1, "name": 1, "code": 1}).to_list(2000)}
    nogs_docs = await db.igss_nogs.find({}, {"_id": 0}).to_list(None)
    data = []
    for n in nogs_docs:
        d = _nog_con_derivados(n)
        u = units.get(n.get("unidad_id"), {})
        d["unidad_nombre"] = u.get("name", "")
        d["unidad_codigo"] = u.get("code", "")
        data.append(d)
    data.sort(key=lambda x: (x.get("unidad_nombre", ""), x.get("numero", "")))
    unidades = [{"id": u["id"], "name": u.get("name", ""), "code": u.get("code", "")}
                for u in units.values()]
    unidades.sort(key=lambda x: x["name"])
    return {"data": data, "unidades": unidades, "total": len(data)}


@router.get("/nogs/resumen")
async def resumen_nogs(
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Resumen global de NOG para tarjetas del catálogo: cuántos NOG están
    disponibles (activos y no completados) y el total de servicios disponibles."""
    nogs = await db.igss_nogs.find({}, {"_id": 0}).to_list(None)
    total_nogs = len(nogs)
    nogs_disponibles = 0
    nogs_completados = 0
    servicios_contratados = 0
    servicios_acreditados = 0
    servicios_disponibles = 0
    valor_total = 0.0
    for n in nogs:
        d = _nog_con_derivados(n)
        servicios_contratados += d["cantidad"]
        servicios_acreditados += d["acreditados"]
        valor_total += d["valor_total"]
        if d["is_active"]:
            servicios_disponibles += d["disponibles"]
            if d["estado"] == "completado":
                nogs_completados += 1
            else:
                nogs_disponibles += 1
    return {
        "total_nogs": total_nogs,
        "nogs_disponibles": nogs_disponibles,
        "nogs_completados": nogs_completados,
        "servicios_contratados": servicios_contratados,
        "servicios_acreditados": servicios_acreditados,
        "servicios_disponibles": servicios_disponibles,
        "valor_total": round(valor_total, 2),
    }


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
        # Mostrar el SPS/código de la orden que corresponde a ESTE NOG (no el legacy)
        _ordenes = p.get("igss_ordenes") or []
        _match = next((o for o in _ordenes if str(o.get("nog", "") or "").strip() == a.get("numero_nog", "")), None)
        _sps = (_match or {}).get("no_sps") if _match else p.get("igss_no_sps", "")
        _cod = (_match or {}).get("codigo") if _match else p.get("igss_codigo", "")
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
            "igss_no_sps": _sps or "",
            "igss_codigo": _cod or "",
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


@router.post("/nogs/{nog_id}/acreditaciones/aplicar")
async def aplicar_acreditacion_manual(
    nog_id: str,
    paciente_id: str = Body(..., embed=True),
    current_user: dict = Depends(require_permission("manage_igss_units"))
):
    """Aplica manualmente 1 descuento de este NOG a un paciente (corrección puntual).
    Respeta el cupo y evita duplicar el mismo NOG para el mismo paciente."""
    nog = await _get_nog_or_404(nog_id)
    paciente = await db.patients.find_one({"id": paciente_id, "is_active": True}, {"_id": 0})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o inactivo")
    if paciente.get("referral_institution") != "igss" or paciente.get("igss_unit_id") != nog.get("unidad_id"):
        raise HTTPException(status_code=400, detail="El paciente no pertenece a la unidad de este NOG")
    ok, motivo = await _crear_acreditacion(nog, paciente, None, "manual", current_user)
    if not ok:
        if motivo == "duplicada":
            raise HTTPException(status_code=400, detail="Este paciente ya tiene este NOG descontado")
        raise HTTPException(status_code=400, detail="El NOG ya no tiene cupo disponible")
    fresh = await db.igss_nogs.find_one({"id": nog_id}, {"_id": 0})
    return {"message": "Descuento aplicado", "nog": _nog_con_derivados(fresh)}


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


# ==================== MÓDULO DE PRODUCCIÓN IGSS ====================

PRODUCCION_ROLES = ["superadmin", "admin", "administrador_igss"]


class ProduccionUpdate(BaseModel):
    impreso: Optional[bool] = None
    enviado: Optional[bool] = None
    facturado: Optional[bool] = None
    pagado: Optional[bool] = None
    costo_override: Optional[float] = Field(None, ge=0)


def _txt(v):
    return bool(v.strip()) if isinstance(v, str) else bool(v)


def _refraccion_tiene_datos(r):
    if not isinstance(r, dict):
        return False
    return any(_txt(r.get(k)) for k in ("esfera", "cilindro", "eje", "adicion"))


def _examen_tiene_datos(ex):
    if not isinstance(ex, dict):
        return False
    campos = ["avsc_od", "avsc_os", "avcc_od", "avcc_os", "av_binocular", "av_cerca",
              "queratometria_od", "queratometria_os", "pio_od", "pio_os", "pio_metodo",
              "segmento_anterior", "segmento_posterior", "motilidad_ocular", "pupilas_reflejos"]
    if any(_txt(ex.get(c)) for c in campos):
        return True
    return any(_refraccion_tiene_datos(ex.get(rk))
               for rk in ("refraccion_od", "refraccion_os", "lensometria_od", "lensometria_os"))


def _eval_tiene_contenido(ev):
    """True si la evaluación tiene algún dato clínico real (no es borrador vacío)."""
    if _txt(ev.get("igss_procedimiento")):
        return True
    if any(_txt(ev.get(k)) for k in ("motivo_consulta", "padecimiento_actual", "plan", "lectura_examenes")):
        return True
    diags = ev.get("diagnosticos") or []
    if any(isinstance(d, dict) and (_txt(d.get("descripcion")) or _txt(d.get("codigo_cie10"))) for d in diags):
        return True
    if _examen_tiene_datos(ev.get("examen")):
        return True
    imp = ev.get("igss_med_proc") or {}
    if imp.get("medicamentos") or imp.get("estudios_procedimientos"):
        return True
    procs = ev.get("procedimientos") or []
    if any(isinstance(p, dict) and (_txt(p.get("tipo_nombre")) or _txt(p.get("descripcion"))) for p in procs):
        return True
    rec = ev.get("recetas") or {}
    if (rec.get("medicamentos") or {}).get("items"):
        return True
    if rec.get("anteojos_lista") or rec.get("lentes_contacto_lista"):
        return True
    recom = ev.get("recomendaciones") or {}
    if recom.get("estudios_a_realizar") or _txt(recom.get("recomendaciones_generales")):
        return True
    return False


def _eval_tiene_medico(ev):
    return _txt(ev.get("medico_id")) or _txt(ev.get("medico_nombre"))


def eval_es_borrador_vacio(ev):
    """Borrador vacío = sin médico asignado Y sin ningún dato clínico."""
    return not _eval_tiene_medico(ev) and not _eval_tiene_contenido(ev)


def _eval_recencia(ev):
    return (ev.get("fecha") or "", ev.get("fecha_actualizacion") or ev.get("ultimo_autoguardado") or "", ev.get("fecha_creacion") or "")


def _resolver_orden(ev, pac):
    """Resuelve (numero NOG, No. SPS, código, procedimiento) de una evaluación,
    con respaldo en la primera orden IGSS del paciente."""
    numero = (ev.get("igss_nog") or "").strip()
    no_sps = ev.get("igss_no_sps") or ""
    codigo = ev.get("igss_codigo") or ""
    proc = ev.get("igss_procedimiento") or ""
    if not numero:
        ords = (pac or {}).get("igss_ordenes") or []
        if ords:
            numero = (ords[0].get("nog") or "").strip()
            no_sps = no_sps or ords[0].get("no_sps", "")
            codigo = codigo or ords[0].get("codigo", "")
            proc = proc or ords[0].get("procedimiento", "")
    return numero, no_sps, codigo, proc


def _order_key(no_sps, numero, fecha):
    """Clave de agrupación por orden: No. SPS; respaldo NOG; respaldo paciente/fecha."""
    if (no_sps or "").strip():
        return ("sps", no_sps.strip())
    if numero:
        return ("nog", numero)
    return ("pac", fecha or "")


def _en_ventana(fecha_dia, fecha, desde, hasta):
    """True si `fecha_dia` (YYYY-MM-DD) cae dentro del filtro solicitado."""
    d = (fecha_dia or "")[:10]
    if not d:
        return False
    if fecha:
        return d == fecha[:10]
    if desde and d < desde[:10]:
        return False
    if hasta and d > hasta[:10]:
        return False
    return True


async def _build_produccion_rows(fecha, desde, hasta, unidad_id, nog):
    # 1) Ventana: evaluaciones del periodo solo para ubicar a los pacientes afectados.
    q = {}
    if fecha:
        q["fecha"] = fecha
    else:
        rango = {}
        if desde:
            rango["$gte"] = desde
        if hasta:
            rango["$lte"] = hasta
        if rango:
            q["fecha"] = rango
    evals_win = await db.evaluaciones_oftalmologicas.find(q, {"_id": 0, "paciente_id": 1}).to_list(None)
    if not evals_win:
        return []
    pac_ids = list({e.get("paciente_id") for e in evals_win if e.get("paciente_id")})
    pac_list = await db.patients.find({"id": {"$in": pac_ids}, "referral_institution": "igss"}, {"_id": 0}).to_list(None)
    pac_map = {p["id"]: p for p in pac_list}
    if not pac_map:
        return []
    # 2) TODAS las evaluaciones de esos pacientes (todas las fechas) para calcular la
    #    PRIMERA consulta de cada autorización y consolidar seguimientos de cualquier día.
    igss_pac_ids = list(pac_map.keys())
    evals = await db.evaluaciones_oftalmologicas.find(
        {"paciente_id": {"$in": igss_pac_ids}}, {"_id": 0}).to_list(None)
    if not evals:
        return []
    ev_ids = [e["id"] for e in evals]
    prod_list = await db.igss_produccion.find({"evaluacion_id": {"$in": ev_ids}}, {"_id": 0}).to_list(None)
    prod_map = {p["evaluacion_id"]: p for p in prod_list}
    # Acreditaciones vigentes de los pacientes: para ocultar autorizaciones que un
    # comodín legado (sin SPS) ya absorbió (no descontaron su propio cupo).
    acred_list = await db.igss_nog_acreditaciones.find(
        {"paciente_id": {"$in": igss_pac_ids}, "anulada": {"$ne": True}},
        {"_id": 0, "paciente_id": 1, "numero_nog": 1, "no_sps": 1}).to_list(None)
    acred_idx = {}
    for a in acred_list:
        acred_idx.setdefault(a.get("paciente_id"), set()).add(
            (a.get("numero_nog", ""), (a.get("no_sps") or "").strip()))
    unit_ids = list({p.get("igss_unit_id") for p in pac_list if p.get("igss_unit_id")})
    unit_list = await db.igss_units.find({"id": {"$in": unit_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(None)
    unit_map = {u["id"]: u for u in unit_list}
    nog_list = await db.igss_nogs.find({"unidad_id": {"$in": unit_ids}}, {"_id": 0, "unidad_id": 1, "numero": 1, "precio": 1}).to_list(None)
    nog_map = {(n["unidad_id"], n["numero"]): n for n in nog_list}
    # 1) Candidatos: resolver orden, excluir no-IGSS y ocultar borradores vacíos
    candidatos = []
    for ev in evals:
        pac = pac_map.get(ev.get("paciente_id"))
        if not pac:
            continue  # no IGSS o inexistente
        uid = pac.get("igss_unit_id")
        if unidad_id and uid != unidad_id:
            continue
        numero, no_sps, codigo, proc = _resolver_orden(ev, pac)
        if nog and numero != nog:
            continue
        # Ocultar evaluaciones en blanco: sin médico asignado y sin datos clínicos
        tiene_contenido = _eval_tiene_contenido(ev)
        if not _eval_tiene_medico(ev) and not tiene_contenido:
            continue
        unit = unit_map.get(uid)
        precio = float((nog_map.get((uid, numero)) or {}).get("precio") or 0)
        candidatos.append({
            "ev": ev, "pac": pac, "uid": uid, "unit": unit,
            "numero": numero, "no_sps": no_sps, "codigo": codigo, "proc": proc,
            "precio": precio, "tiene_contenido": tiene_contenido,
        })

    # 2) Agrupar por paciente + orden (No. SPS; respaldo NOG; respaldo paciente/día)
    grupos = {}
    for c in candidatos:
        ev = c["ev"]
        okey = _order_key(c["no_sps"], c["numero"], ev.get("fecha"))
        grupos.setdefault((ev.get("paciente_id"), okey), []).append(c)

    # 3) Una fila consolidada por grupo (representante = más reciente con contenido);
    #    la fecha mostrada es la de la PRIMERA consulta de la autorización.
    rows = []
    for (pid, okey), items in grupos.items():
        con_contenido = [c for c in items if c["tiene_contenido"]]
        rep = max(con_contenido or items, key=lambda c: _eval_recencia(c["ev"]))
        primera = min(items, key=lambda c: (c["ev"].get("fecha") or "", c["ev"].get("fecha_creacion") or ""))
        fecha_primera = primera["ev"].get("fecha", "")
        # Incluir la autorización SOLO si su PRIMERA consulta cae en el filtro pedido.
        # Así un seguimiento (mismo No. SPS) en otro día/mes no genera una fila nueva.
        if not _en_ventana(fecha_primera, fecha, desde, hasta):
            continue
        # Ocultar autorizaciones por SPS que no descontaron su propio cupo porque un
        # comodín legado (acreditación sin SPS) del mismo paciente/NOG ya las absorbió.
        _sps = (rep["no_sps"] or "").strip()
        if _sps:
            _pac_acr = acred_idx.get(pid, set())
            if (rep["numero"], _sps) not in _pac_acr and (rep["numero"], "") in _pac_acr:
                continue
        ev = rep["ev"]
        pac = rep["pac"]
        unit = rep["unit"]
        # Combinar estados de todas las evaluaciones de la orden; costo del representante
        impreso = enviado = facturado = pagado = False
        rep_est = prod_map.get(ev["id"])
        costo_override = rep_est.get("costo_override") if (rep_est and rep_est.get("costo_override") is not None) else None
        for c in items:
            est = prod_map.get(c["ev"]["id"])
            if not est:
                continue
            impreso = impreso or bool(est.get("impreso"))
            enviado = enviado or bool(est.get("enviado"))
            facturado = facturado or bool(est.get("facturado"))
            pagado = pagado or bool(est.get("pagado"))
            if costo_override is None and est.get("costo_override") is not None:
                costo_override = est.get("costo_override")
        precio = rep["precio"]
        costo = costo_override if costo_override is not None else precio
        rows.append({
            "evaluacion_id": ev["id"],
            "paciente_id": ev.get("paciente_id"),
            "paciente_nombre": ev.get("paciente_nombre") or f"{(pac.get('first_name') or '')} {(pac.get('last_name') or '')}".strip(),
            "expediente": ev.get("paciente_expediente") or pac.get("record_number", ""),
            "unidad_id": rep["uid"] or "",
            "unidad_nombre": (unit or {}).get("name", ""),
            "nog": rep["numero"], "no_sps": rep["no_sps"], "codigo": rep["codigo"], "procedimiento": rep["proc"],
            "medico_nombre": ev.get("medico_nombre", ""),
            "fecha": fecha_primera,
            "precio_nog": precio,
            "costo": float(costo or 0),
            "costo_editado": costo_override is not None,
            "impreso": impreso,
            "enviado": enviado,
            "facturado": facturado,
            "pagado": pagado,
        })
    rows.sort(key=lambda r: (r["unidad_nombre"], r["nog"], r["paciente_nombre"]))
    return rows


def _produccion_totales(rows):
    tot_costo = sum(r["costo"] for r in rows)
    por_estado = {e: {"cantidad": 0, "monto": 0.0} for e in ["impreso", "enviado", "facturado", "pagado"]}
    por_nog = {}
    for r in rows:
        for e in por_estado:
            if r[e]:
                por_estado[e]["cantidad"] += 1
                por_estado[e]["monto"] = round(por_estado[e]["monto"] + r["costo"], 2)
        k = r["nog"] or "—"
        pn = por_nog.setdefault(k, {"nog": k, "unidad_nombre": r["unidad_nombre"], "cantidad": 0, "monto": 0.0})
        pn["cantidad"] += 1
        pn["monto"] = round(pn["monto"] + r["costo"], 2)
    pagado = por_estado["pagado"]["monto"]
    return {
        "servicios": len(rows),
        "total_costo": round(tot_costo, 2),
        "por_estado": por_estado,
        "por_nog": sorted(por_nog.values(), key=lambda x: (x["unidad_nombre"], x["nog"])),
        "total_pagado": round(pagado, 2),
        "total_pendiente": round(tot_costo - pagado, 2),
    }


@router.get("/produccion")
async def listar_produccion(
    fecha: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    unidad_id: Optional[str] = None,
    nog: Optional[str] = None,
    current_user: dict = Depends(require_role(PRODUCCION_ROLES))
):
    """Listado de producción IGSS: una línea por evaluación (orden) con costo y estados."""
    if not (fecha or desde or hasta):
        fecha = today_str_gt()
    rows = await _build_produccion_rows(fecha, desde, hasta, unidad_id, nog)
    return {
        "data": rows,
        "totales": _produccion_totales(rows),
        "filtro": {"fecha": fecha, "desde": desde, "hasta": hasta, "unidad_id": unidad_id, "nog": nog},
    }


@router.patch("/produccion/{evaluacion_id}")
async def actualizar_produccion(
    evaluacion_id: str,
    data: ProduccionUpdate,
    current_user: dict = Depends(require_role(PRODUCCION_ROLES))
):
    """Marca estados (impreso/enviado/facturado/pagado) y/o ajusta el costo de un registro.
    Los estados se aplican a TODAS las evaluaciones de la misma orden (fila consolidada),
    para que marcar/desmarcar sea consistente. El costo se ajusta solo en el representante.
    Enviar costo_override=null restablece el costo al precio del NOG."""
    ev = await db.evaluaciones_oftalmologicas.find_one({"id": evaluacion_id}, {"_id": 0})
    if not ev:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    pac = await db.patients.find_one({"id": ev.get("paciente_id")}, {"_id": 0})
    if not pac or pac.get("referral_institution") != "igss":
        raise HTTPException(status_code=400, detail="La evaluación no pertenece a un paciente IGSS")
    provided = data.model_dump(exclude_unset=True)
    if not provided:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    now = datetime.now(timezone.utc).isoformat()
    uid = current_user["id"]

    # Estados booleanos: se aplican a toda la orden (todas las evaluaciones del grupo)
    bool_fields = {k: v for k, v in provided.items()
                   if k in ("impreso", "enviado", "facturado", "pagado") and v is not None}
    if bool_fields:
        numero, no_sps, _, _ = _resolver_orden(ev, pac)
        okey = _order_key(no_sps, numero, ev.get("fecha"))
        sibs = await db.evaluaciones_oftalmologicas.find(
            {"paciente_id": ev.get("paciente_id")}, {"_id": 0}).to_list(None)
        target_ids = {evaluacion_id}
        for s in sibs:
            sn, sp, _, _ = _resolver_orden(s, pac)
            if _order_key(sp, sn, s.get("fecha")) == okey:
                target_ids.add(s["id"])
        for tid in target_ids:
            await db.igss_produccion.update_one(
                {"evaluacion_id": tid},
                {"$set": {**bool_fields, "updated_at": now, "updated_by": uid},
                 "$setOnInsert": {"evaluacion_id": tid}},
                upsert=True,
            )

    # Costo: solo en el representante (la evaluación de la fila)
    if "costo_override" in provided:
        v = provided["costo_override"]
        doc = {"$set": {"updated_at": now, "updated_by": uid},
               "$setOnInsert": {"evaluacion_id": evaluacion_id}}
        if v is None:
            doc["$unset"] = {"costo_override": ""}
        else:
            doc["$set"]["costo_override"] = v
        await db.igss_produccion.update_one({"evaluacion_id": evaluacion_id}, doc, upsert=True)

    fresh = await db.igss_produccion.find_one({"evaluacion_id": evaluacion_id}, {"_id": 0})
    return fresh


@router.get("/produccion/reporte/excel")
async def exportar_produccion_excel(
    fecha: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    unidad_id: Optional[str] = None,
    nog: Optional[str] = None,
    current_user: dict = Depends(require_role(PRODUCCION_ROLES))
):
    """Exporta el reporte de producción (detalle + totales) a Excel."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    if not (fecha or desde or hasta):
        fecha = today_str_gt()
    rows = await _build_produccion_rows(fecha, desde, hasta, unidad_id, nog)
    tot = _produccion_totales(rows)
    wb = Workbook()
    ws = wb.active
    ws.title = "Produccion"
    hf = PatternFill(start_color="0F6E56", end_color="0F6E56", fill_type="solid")
    bold = Font(color="FFFFFF", bold=True)
    headers = ["Fecha", "Unidad", "NOG", "No. SPS", "Paciente", "Expediente", "Procedimiento", "Médico", "Costo (Q)", "Impreso", "Enviado", "Facturado", "Pagado"]
    ws.append(headers)
    for c in ws[1]:
        c.fill = hf
        c.font = bold
    si = lambda b: "Sí" if b else "No"
    for r in rows:
        ws.append([r["fecha"], r["unidad_nombre"], r["nog"], r["no_sps"], r["paciente_nombre"], r["expediente"], r["procedimiento"], r["medico_nombre"], r["costo"], si(r["impreso"]), si(r["enviado"]), si(r["facturado"]), si(r["pagado"])])
    ws.append([])
    ws.append(["TOTALES", "", "", "", "", "", "", "", tot["total_costo"]])
    ws.append(["Servicios", tot["servicios"]])
    ws.append(["Total pagado (Q)", tot["total_pagado"]])
    ws.append(["Total pendiente (Q)", tot["total_pendiente"]])
    ws.append([])
    ws.append(["Por estado", "Cantidad", "Monto (Q)"])
    for e in ["impreso", "enviado", "facturado", "pagado"]:
        ws.append([e.capitalize(), tot["por_estado"][e]["cantidad"], tot["por_estado"][e]["monto"]])
    ws.append([])
    ws.append(["Por NOG", "Unidad", "Cantidad", "Monto (Q)"])
    for pn in tot["por_nog"]:
        ws.append([pn["nog"], pn["unidad_nombre"], pn["cantidad"], pn["monto"]])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    periodo = fecha or f"{desde or ''}_{hasta or ''}"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="produccion_igss_{periodo}.xlsx"'}
    )
