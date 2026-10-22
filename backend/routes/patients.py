# /app/backend/routes/patients.py
# Módulo de Pacientes - CRUD completo y exportación

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import StreamingResponse
from typing import Optional, List, Literal
from datetime import datetime, timezone
from utils.timezone import now_gt
from routes.evaluaciones import audit
from pydantic import BaseModel, Field, ConfigDict
import uuid
import io

from config.database import db
from routes.auth import get_current_user, require_role, require_permission
from pymongo import ReturnDocument

router = APIRouter(prefix="/patients", tags=["Pacientes"])
pacientes_router = APIRouter(prefix="/pacientes", tags=["Pacientes - Búsqueda rápida"])


# ==================== MODELS ====================

class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    gender: Literal["masculino", "femenino", "otro"]
    birth_date: str  # YYYY-MM-DD
    profession: Optional[str] = ""
    phone: str = Field(..., min_length=8, max_length=20)
    email: Optional[str] = ""
    dpi: Optional[str] = Field(None, min_length=13, max_length=13)
    emergency_phone: Optional[str] = ""
    emergency_contact_name: Optional[str] = ""
    emergency_contact_relationship: Optional[str] = ""
    referral_institution: Literal["particular", "igss", "seguro_privado", "otra"]
    insurance_name: Optional[str] = ""
    other_institution_name: Optional[str] = ""
    igss_unit_id: Optional[str] = None
    igss_afiliacion: Optional[str] = ""
    igss_no_sps: Optional[str] = ""
    igss_codigo: Optional[str] = ""
    igss_tipo_compra: Optional[str] = ""
    igss_nog: Optional[str] = ""
    igss_tipo_paciente: Optional[str] = ""
    address: Optional[str] = ""
    comments: Optional[str] = ""


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[Literal["masculino", "femenino", "otro"]] = None
    birth_date: Optional[str] = None
    profession: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    dpi: Optional[str] = None
    emergency_phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    referral_institution: Optional[Literal["particular", "igss", "seguro_privado", "otra"]] = None
    insurance_name: Optional[str] = None
    other_institution_name: Optional[str] = None
    igss_unit_id: Optional[str] = None
    igss_afiliacion: Optional[str] = None
    igss_no_sps: Optional[str] = None
    igss_codigo: Optional[str] = None
    igss_tipo_compra: Optional[str] = None
    igss_nog: Optional[str] = None
    igss_tipo_paciente: Optional[str] = None
    address: Optional[str] = None
    comments: Optional[str] = None
    is_active: Optional[bool] = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    record_number: Optional[str] = ""
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    full_name: Optional[str] = ""
    gender: Optional[str] = ""
    birth_date: Optional[str] = ""
    age: Optional[int] = 0
    profession: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    dpi: Optional[str] = ""
    emergency_phone: Optional[str] = ""
    emergency_contact_name: Optional[str] = ""
    emergency_contact_relationship: Optional[str] = ""
    referral_institution: Optional[str] = ""
    referral_institution_label: Optional[str] = ""
    insurance_name: Optional[str] = ""
    other_institution_name: Optional[str] = ""
    igss_unit_id: Optional[str] = ""
    igss_unit_name: Optional[str] = ""
    igss_afiliacion: Optional[str] = ""
    igss_no_sps: Optional[str] = ""
    igss_codigo: Optional[str] = ""
    igss_tipo_compra: Optional[str] = ""
    igss_nog: Optional[str] = ""
    igss_tipo_paciente: Optional[str] = ""
    address: Optional[str] = ""
    comments: Optional[str] = ""
    is_active: bool = True
    created_by: Optional[str] = ""
    created_by_name: Optional[str] = ""
    created_at: Optional[str] = ""
    updated_by: Optional[str] = ""
    updated_by_name: Optional[str] = ""
    updated_at: Optional[str] = None


class PatientListResponse(BaseModel):
    data: List[PatientResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class PatientSearchResponse(BaseModel):
    """Respuesta para autocompletado en otros módulos"""
    id: str
    record_number: str
    full_name: str
    dpi: Optional[str] = ""
    phone: str


class PatientDuplicateCheck(BaseModel):
    exists: bool
    match_type: Optional[str] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    patient_record_number: Optional[str] = None


# ==================== HELPERS ====================

INSTITUTION_LABELS = {
    "particular": "Particular",
    "igss": "IGSS",
    "seguro_privado": "Seguro Privado",
    "otra": "Otra Institución"
}


def validate_phone(phone: str) -> bool:
    """Validar formato de teléfono guatemalteco"""
    import re
    phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
    return len(phone_clean) >= 8 and phone_clean.isdigit()


def validate_email(email: str) -> bool:
    """Validar formato de email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_dpi(dpi: str) -> bool:
    """Validar DPI guatemalteco (13 dígitos)"""
    return len(dpi) == 13 and dpi.isdigit()


def calcular_edad(birth_date: str) -> int:
    """Calcular edad a partir de fecha de nacimiento"""
    try:
        birth = datetime.strptime(birth_date[:10], "%Y-%m-%d")
        today = datetime.now(timezone.utc).replace(tzinfo=None)
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return max(0, age)
    except (ValueError, TypeError):
        return 0


async def get_next_record_number() -> str:
    """Generar siguiente número de expediente correlativo de forma ATÓMICA.

    Con varios usuarios creando pacientes en simultáneo, el enfoque anterior
    (leer el último y sumar 1) generaba expedientes DUPLICADOS por condición de
    carrera. Ahora usamos un contador atómico por mes en la colección `counters`
    (`find_one_and_update` con `$inc`), inicializado una sola vez con el máximo
    existente del mes. Se reintenta si el número candidato ya existiera (drift
    por importaciones).
    """
    now = datetime.now(timezone.utc)
    ym = now.strftime('%Y%m')
    prefix = f"EXP-{ym}-"
    counter_key = f"patient_record_{ym}"

    # Inicialización idempotente del contador del mes (una sola vez).
    if await db.counters.find_one({"_id": counter_key}) is None:
        last = await db.patients.find_one(
            {"record_number": {"$regex": f"^{prefix}"}},
            sort=[("record_number", -1)]
        )
        start = 0
        if last:
            try:
                start = int(last["record_number"].split("-")[-1])
            except (ValueError, IndexError):
                start = 0
        # $setOnInsert evita pisar el contador si otro request lo creó primero.
        await db.counters.update_one(
            {"_id": counter_key},
            {"$setOnInsert": {"seq": start}},
            upsert=True
        )

    candidate = f"{prefix}0001"
    for _ in range(5):
        doc = await db.counters.find_one_and_update(
            {"_id": counter_key},
            {"$inc": {"seq": 1}},
            return_document=ReturnDocument.AFTER,
            upsert=True
        )
        next_num = doc.get("seq", 1)
        candidate = f"{prefix}{next_num:04d}"
        # Defensa ante drift: si el número ya existe, avanzar de nuevo.
        if not await db.patients.find_one({"record_number": candidate}):
            return candidate
    return candidate


async def enrich_patient(patient: dict) -> dict:
    """Enriquecer paciente con datos calculados y relaciones"""
    patient["full_name"] = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
    patient["age"] = calcular_edad(patient.get("birth_date", ""))
    patient["referral_institution_label"] = INSTITUTION_LABELS.get(patient.get("referral_institution", ""), "")
    
    # Obtener nombre de unidad IGSS
    if patient.get("igss_unit_id"):
        unit = await db.igss_units.find_one({"id": patient["igss_unit_id"]}, {"_id": 0, "name": 1})
        patient["igss_unit_name"] = unit["name"] if unit else ""
    else:
        patient["igss_unit_name"] = ""
    
    # Obtener nombres de usuarios
    if patient.get("created_by"):
        creator = await db.users.find_one({"id": patient["created_by"]}, {"_id": 0, "name": 1})
        patient["created_by_name"] = creator["name"] if creator else ""
    
    if patient.get("updated_by"):
        updater = await db.users.find_one({"id": patient["updated_by"]}, {"_id": 0, "name": 1})
        patient["updated_by_name"] = updater["name"] if updater else ""
    
    return patient


def generate_accent_regex(text: str) -> str:
    """Genera un patrón regex que ignora diacríticos en la búsqueda"""
    accent_map = {
        'a': '[aáàäâ]', 'e': '[eéèëê]', 'i': '[iíìïî]', 
        'o': '[oóòöô]', 'u': '[uúùüû]', 'n': '[nñ]',
        'A': '[AÁÀÄÂ]', 'E': '[EÉÈËÊ]', 'I': '[IÍÌÏÎ]',
        'O': '[OÓÒÖÔ]', 'U': '[UÚÙÜÛ]', 'N': '[NÑ]'
    }
    regex_pattern = ""
    for char in text:
        lower_char = char.lower()
        if lower_char in accent_map:
            regex_pattern += accent_map[lower_char]
        else:
            if char in r'\.^$*+?{}[]|()':
                regex_pattern += '\\' + char
            else:
                regex_pattern += char
    return regex_pattern


def build_patient_search_conditions(search: str) -> list:
    """Construye condiciones de búsqueda de pacientes.
    - Cada palabra del texto debe aparecer en el nombre O en el apellido (en cualquier orden),
      sin distinguir mayúsculas/minúsculas ni acentos.
    - Además permite coincidencia por número de expediente, DPI o teléfono con el texto completo.
    Devuelve una lista para usar en query["$or"] (coincide si cumple cualquiera de las alternativas)."""
    import re
    conditions = []
    tokens = [t for t in search.split() if t.strip()]
    if tokens:
        token_and = []
        for tok in tokens:
            rgx = {"$regex": generate_accent_regex(tok), "$options": "i"}
            token_and.append({"$or": [{"first_name": rgx}, {"last_name": rgx}]})
        conditions.append({"$and": token_and} if len(token_and) > 1 else token_and[0])
    full = search.strip()
    if full:
        ident = {"$regex": re.escape(full), "$options": "i"}
        conditions.append({"record_number": ident})
        conditions.append({"dpi": ident})
        conditions.append({"phone": ident})
    return conditions


# ==================== BÚSQUEDA RÁPIDA (para autocomplete) ====================

@pacientes_router.get("/buscar")
async def buscar_pacientes_rapido(
    search: str = Query("", min_length=0),
    q: str = Query("", min_length=0),
    limit: int = Query(50, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Búsqueda rápida de pacientes para autocomplete"""
    # Aceptar tanto ?search= como ?q= (frontend usa ?q=)
    search = search or q
    query = {"is_active": True}
    if search:
        conditions = build_patient_search_conditions(search)
        if conditions:
            query["$or"] = conditions
    
    pacientes = await db.patients.find(
        query, 
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "record_number": 1, "birth_date": 1, "gender": 1, "phone": 1, "dpi": 1}
    ).limit(limit).to_list(limit)
    
    for p in pacientes:
        p["nombre_completo"] = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        p["edad"] = calcular_edad(p.get("birth_date", "")) if p.get("birth_date") else 0
        # Agregar campos en español para compatibilidad con POS de Óptica
        p["primer_nombre"] = p.get("first_name", "")
        p["primer_apellido"] = p.get("last_name", "")
        p["segundo_nombre"] = ""
        p["segundo_apellido"] = ""
        p["telefono"] = p.get("phone", "")
    
    return pacientes


# ==================== CRUD ENDPOINTS ====================

@router.get("", response_model=PatientListResponse)
async def get_patients(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    referral_institution: Optional[str] = None,
    igss_unit_id: Optional[str] = None,
    igss_nog: Optional[str] = None,
    gender: Optional[str] = None,
    age_from: Optional[int] = None,
    age_to: Optional[int] = None,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    is_active: bool = True,
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Listar pacientes con filtros y paginación"""
    query = {"is_active": is_active}
    
    if search:
        conditions = build_patient_search_conditions(search)
        if conditions:
            query["$or"] = conditions
    
    if referral_institution:
        query["referral_institution"] = referral_institution
    if igss_unit_id:
        query["igss_unit_id"] = igss_unit_id
    if igss_nog:
        import re as _re
        query["igss_nog"] = {"$regex": _re.escape(igss_nog.strip()), "$options": "i"}
    if gender:
        query["gender"] = gender
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["created_at"] = date_query
    
    total = await db.patients.count_documents(query)
    total_pages = (total + limit - 1) // limit
    
    skip = (page - 1) * limit
    patients = await db.patients.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    enriched_patients = []
    for patient in patients:
        enriched = await enrich_patient(patient)
        if age_from is not None and enriched["age"] < age_from:
            continue
        if age_to is not None and enriched["age"] > age_to:
            continue
        enriched_patients.append(enriched)
    
    return PatientListResponse(
        data=enriched_patients,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.get("/search", response_model=List[PatientSearchResponse])
async def search_patients(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Búsqueda de pacientes para autocompletado en otros módulos.
    Usa búsqueda multi-palabra en cualquier orden (nombre/apellido) + expediente/DPI/teléfono."""
    conditions = build_patient_search_conditions(q)
    query = {"is_active": True}
    if conditions:
        query["$or"] = conditions
    
    patients = await db.patients.find(query, {"_id": 0}).limit(limit).to_list(limit)
    
    results = []
    seen_ids = set()
    for p in patients:
        if p["id"] not in seen_ids:
            seen_ids.add(p["id"])
            results.append(PatientSearchResponse(
                id=p["id"],
                record_number=p.get("record_number", ""),
                full_name=f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                dpi=p.get("dpi", ""),
                phone=p.get("phone", "")
            ))
    
    return results


@router.get("/check-duplicate", response_model=PatientDuplicateCheck)
async def check_patient_duplicate(
    dpi: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    birth_date: Optional[str] = None,
    exclude_id: Optional[str] = None,
    current_user: dict = Depends(require_permission("view_patients"))
):
    """Verificar si existe un paciente duplicado"""
    if dpi and len(dpi) == 13:
        query = {"dpi": dpi, "is_active": True}
        if exclude_id:
            query["id"] = {"$ne": exclude_id}
        
        existing = await db.patients.find_one(query, {"_id": 0})
        if existing:
            return PatientDuplicateCheck(
                exists=True,
                match_type="dpi",
                patient_id=existing["id"],
                patient_name=f"{existing['first_name']} {existing['last_name']}",
                patient_record_number=existing["record_number"]
            )
    
    if first_name and last_name and birth_date:
        query = {
            "first_name": {"$regex": f"^{first_name}$", "$options": "i"},
            "last_name": {"$regex": f"^{last_name}$", "$options": "i"},
            "birth_date": birth_date,
            "is_active": True
        }
        if exclude_id:
            query["id"] = {"$ne": exclude_id}
        
        existing = await db.patients.find_one(query, {"_id": 0})
        if existing:
            return PatientDuplicateCheck(
                exists=True,
                match_type="name_birthdate",
                patient_id=existing["id"],
                patient_name=f"{existing['first_name']} {existing['last_name']}",
                patient_record_number=existing["record_number"]
            )
    
    return PatientDuplicateCheck(exists=False)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, current_user: dict = Depends(require_permission("view_patients"))):
    """Obtener detalle de un paciente"""
    patient = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    enriched = await enrich_patient(patient)
    return PatientResponse(**enriched)


@router.post("", response_model=PatientResponse)
async def create_patient(patient_data: PatientCreate, current_user: dict = Depends(require_permission("create_patients"))):
    """Crear nuevo paciente"""
    if not validate_phone(patient_data.phone):
        raise HTTPException(status_code=400, detail="Formato de teléfono inválido")
    
    if patient_data.email and not validate_email(patient_data.email):
        raise HTTPException(status_code=400, detail="Formato de email inválido")
    
    if patient_data.dpi and not validate_dpi(patient_data.dpi):
        raise HTTPException(status_code=400, detail="DPI debe tener exactamente 13 dígitos numéricos")
    
    try:
        birth_date = datetime.strptime(patient_data.birth_date[:10], "%Y-%m-%d")
        if birth_date > datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(status_code=400, detail="La fecha de nacimiento no puede ser futura")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha de nacimiento inválido (YYYY-MM-DD)")
    
    if patient_data.referral_institution == "igss":
        if not patient_data.dpi:
            raise HTTPException(status_code=400, detail="El DPI es obligatorio para pacientes IGSS")
        if not patient_data.igss_unit_id:
            raise HTTPException(status_code=400, detail="Debe seleccionar una unidad IGSS")
        unit = await db.igss_units.find_one({"id": patient_data.igss_unit_id, "is_active": True})
        if not unit:
            raise HTTPException(status_code=400, detail="Unidad IGSS no encontrada")
    
    if patient_data.dpi:
        existing_dpi = await db.patients.find_one({"dpi": patient_data.dpi, "is_active": True})
        if existing_dpi:
            raise HTTPException(status_code=400, detail="Ya existe un paciente con este DPI")
    
    now = datetime.now(timezone.utc).isoformat()
    record_number = await get_next_record_number()
    
    patient_doc = {
        "id": str(uuid.uuid4()),
        "record_number": record_number,
        "first_name": patient_data.first_name.strip(),
        "last_name": patient_data.last_name.strip(),
        "gender": patient_data.gender,
        "birth_date": patient_data.birth_date[:10],
        "profession": patient_data.profession or "",
        "phone": patient_data.phone,
        "email": patient_data.email or "",
        "dpi": patient_data.dpi or "",
        "emergency_phone": patient_data.emergency_phone or "",
        "emergency_contact_name": patient_data.emergency_contact_name or "",
        "emergency_contact_relationship": patient_data.emergency_contact_relationship or "",
        "referral_institution": patient_data.referral_institution,
        "insurance_name": patient_data.insurance_name or "",
        "other_institution_name": patient_data.other_institution_name or "",
        "igss_unit_id": patient_data.igss_unit_id if patient_data.referral_institution == "igss" else "",
        "igss_afiliacion": patient_data.igss_afiliacion if patient_data.referral_institution == "igss" else "",
        "igss_no_sps": patient_data.igss_no_sps if patient_data.referral_institution == "igss" else "",
        "igss_codigo": patient_data.igss_codigo if patient_data.referral_institution == "igss" else "",
        "igss_tipo_compra": patient_data.igss_tipo_compra if patient_data.referral_institution == "igss" else "",
        "igss_nog": patient_data.igss_nog if patient_data.referral_institution == "igss" else "",
        "igss_tipo_paciente": patient_data.igss_tipo_paciente if patient_data.referral_institution == "igss" else "",
        "address": patient_data.address or "",
        "comments": patient_data.comments or "",
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_by": "",
        "updated_at": now
    }
    
    await db.patients.insert_one(patient_doc)
    if "_id" in patient_doc:
        del patient_doc["_id"]
    
    # Descontar 1 servicio del NOG asignado (si aplica)
    from routes.igss_nogs import _reconciliar_nog_paciente
    await _reconciliar_nog_paciente(patient_doc, current_user, origen="asignacion")
    
    enriched = await enrich_patient(patient_doc)
    return PatientResponse(**enriched)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: str, patient_data: PatientUpdate, current_user: dict = Depends(require_permission("edit_patients"))):
    """Actualizar paciente"""
    patient = await db.patients.find_one({"id": patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    update_data = {k: v for k, v in patient_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    if "phone" in update_data and not validate_phone(update_data["phone"]):
        raise HTTPException(status_code=400, detail="Formato de teléfono inválido")
    
    if "email" in update_data and update_data["email"] and not validate_email(update_data["email"]):
        raise HTTPException(status_code=400, detail="Formato de email inválido")
    
    if "dpi" in update_data and update_data["dpi"] and not validate_dpi(update_data["dpi"]):
        raise HTTPException(status_code=400, detail="DPI debe tener exactamente 13 dígitos numéricos")
    
    if "birth_date" in update_data:
        try:
            birth_date = datetime.strptime(update_data["birth_date"][:10], "%Y-%m-%d")
            if birth_date > datetime.now(timezone.utc).replace(tzinfo=None):
                raise HTTPException(status_code=400, detail="La fecha de nacimiento no puede ser futura")
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha de nacimiento inválido")
    
    if "dpi" in update_data and update_data["dpi"]:
        existing_dpi = await db.patients.find_one({
            "dpi": update_data["dpi"],
            "is_active": True,
            "id": {"$ne": patient_id}
        })
        if existing_dpi:
            raise HTTPException(status_code=400, detail="Ya existe un paciente con este DPI")
    
    referral = update_data.get("referral_institution", patient["referral_institution"])
    if referral == "igss":
        dpi_val = update_data.get("dpi", patient.get("dpi"))
        if not dpi_val:
            raise HTTPException(status_code=400, detail="El DPI es obligatorio para pacientes IGSS")
        igss_unit = update_data.get("igss_unit_id", patient.get("igss_unit_id"))
        if not igss_unit:
            raise HTTPException(status_code=400, detail="Debe seleccionar una unidad IGSS")
        unit = await db.igss_units.find_one({"id": igss_unit, "is_active": True})
        if not unit:
            raise HTTPException(status_code=400, detail="Unidad IGSS no encontrada")
    
    if "referral_institution" in update_data:
        if update_data["referral_institution"] != "igss":
            update_data["igss_unit_id"] = ""
        if update_data["referral_institution"] != "seguro_privado":
            update_data["insurance_name"] = ""
        if update_data["referral_institution"] != "otra":
            update_data["other_institution_name"] = ""
    
    update_data["updated_by"] = current_user["id"]
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.patients.update_one({"id": patient_id}, {"$set": update_data})
    updated = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    
    # Reconciliar consumo de NOG (reasignación / cambio de unidad / institución)
    from routes.igss_nogs import _reconciliar_nog_paciente
    await _reconciliar_nog_paciente(updated, current_user, origen="reasignacion")
    
    # Auditoría: registrar qué usuario editó el expediente y qué campos cambió
    await audit.log(
        action="PATIENT_UPDATED",
        user_id=current_user["id"],
        user_name=current_user.get("username", "unknown"),
        details={
            "patient_id": patient_id,
            "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
            "campos_modificados": [k for k in update_data.keys() if k not in ("updated_by", "updated_at")]
        }
    )
    
    enriched = await enrich_patient(updated)
    return PatientResponse(**enriched)


@router.delete("/{patient_id}")
async def delete_patient(patient_id: str, current_user: dict = Depends(require_permission("delete_patients"))):
    """Desactivar paciente (soft delete)"""
    patient = await db.patients.find_one({"id": patient_id, "is_active": True})
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    await db.patients.update_one(
        {"id": patient_id},
        {"$set": {
            "is_active": False,
            "updated_by": current_user["id"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    # Liberar el cupo del NOG al desactivar al paciente
    from routes.igss_nogs import _reconciliar_nog_paciente
    inactivo = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    await _reconciliar_nog_paciente(inactivo, current_user, origen="baja")
    return {"message": "Paciente desactivado correctamente"}


@router.post("/{patient_id}/reactivate", response_model=PatientResponse)
async def reactivate_patient(patient_id: str, current_user: dict = Depends(require_permission("delete_patients"))):
    """Reactivar un paciente desactivado"""
    patient = await db.patients.find_one({"id": patient_id, "is_active": False})
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o ya está activo")
    
    await db.patients.update_one(
        {"id": patient_id},
        {"$set": {
            "is_active": True,
            "updated_by": current_user["id"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    updated = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    # Reconsumir el cupo del NOG al reactivar al paciente
    from routes.igss_nogs import _reconciliar_nog_paciente
    await _reconciliar_nog_paciente(updated, current_user, origen="reactivacion")
    enriched = await enrich_patient(updated)
    return PatientResponse(**enriched)


# ==================== EXPORT ENDPOINTS ====================

@router.get("/export/template")
async def download_import_template(current_user: dict = Depends(require_permission("import_patients"))):
    """Descargar plantilla para importación de pacientes"""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Pacientes"
        
        headers = [
            "Nombre*", "Apellido*", "Género* (masculino/femenino/otro)",
            "Fecha Nacimiento* (YYYY-MM-DD)", "Profesión", "Teléfono*",
            "Email", "DPI (13 dígitos)", "Teléfono Emergencia",
            "Nombre Contacto Emergencia", "Parentesco",
            "Institución* (particular/igss/seguro_privado/otra)",
            "Nombre Aseguradora", "Otra Institución", "Código Unidad IGSS",
            "Comentarios"
        ]
        
        header_fill = PatternFill(start_color="0F6E56", end_color="0F6E56", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20
        
        example = [
            "Juan", "Pérez García", "masculino", "1985-03-15", "Ingeniero",
            "55551234", "juan@email.com", "1234567890123", "55559876",
            "María Pérez", "Esposa", "particular", "", "", "", "Paciente de ejemplo"
        ]
        for col, value in enumerate(example, 1):
            ws.cell(row=2, column=col, value=value)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=plantilla_pacientes.xlsx"}
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Librería Excel no disponible")


@router.post("/import")
async def import_patients(current_user: dict = Depends(require_permission("import_patients"))):
    """Importar pacientes desde Excel (placeholder)"""
    raise HTTPException(status_code=501, detail="Funcionalidad de importación en desarrollo")


@router.get("/export/excel")
async def export_patients_excel(
    search: Optional[str] = None,
    referral_institution: Optional[str] = None,
    igss_unit_id: Optional[str] = None,
    igss_nog: Optional[str] = None,
    gender: Optional[str] = None,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    current_user: dict = Depends(require_permission("export_patients"))
):
    """Exportar pacientes a Excel"""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        import re as _re
        
        query = {"is_active": True}
        if search:
            search_regex = {"$regex": search, "$options": "i"}
            query["$or"] = [{"first_name": search_regex}, {"last_name": search_regex}, {"dpi": search_regex}]
        if referral_institution:
            query["referral_institution"] = referral_institution
        if igss_unit_id:
            query["igss_unit_id"] = igss_unit_id
        if igss_nog:
            query["igss_nog"] = {"$regex": _re.escape(igss_nog.strip()), "$options": "i"}
        if gender:
            query["gender"] = gender
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            if date_query:
                query["created_at"] = date_query
        
        patients = await db.patients.find(query, {"_id": 0}).sort("record_number", 1).to_list(10000)
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Pacientes"
        
        headers = [
            "No. Expediente", "Nombre", "Apellido", "Género", "Fecha Nacimiento",
            "Edad", "Profesión", "Teléfono", "Email", "DPI", "Institución",
            "Unidad IGSS", "NOG", "Fecha Registro"
        ]
        
        header_fill = PatternFill(start_color="0F6E56", end_color="0F6E56", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        
        for row, patient in enumerate(patients, 2):
            enriched = await enrich_patient(patient)
            data = [
                enriched["record_number"], enriched["first_name"], enriched["last_name"],
                enriched["gender"].capitalize(), enriched["birth_date"], enriched["age"],
                enriched.get("profession", ""), enriched["phone"], enriched.get("email", ""),
                enriched.get("dpi", ""), enriched["referral_institution_label"],
                enriched.get("igss_unit_name", ""), enriched.get("igss_nog", ""), enriched["created_at"][:10]
            ]
            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = thin_border
        
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=pacientes_novavision.xlsx"}
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Librería Excel no disponible")


@router.get("/export/pdf")
async def export_patients_pdf(
    search: Optional[str] = None,
    referral_institution: Optional[str] = None,
    igss_unit_id: Optional[str] = None,
    igss_nog: Optional[str] = None,
    gender: Optional[str] = None,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    current_user: dict = Depends(require_permission("export_patients"))
):
    """Exportar pacientes a PDF"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER
        import re as _re
        
        query = {"is_active": True}
        if search:
            search_regex = {"$regex": search, "$options": "i"}
            query["$or"] = [{"first_name": search_regex}, {"last_name": search_regex}, {"dpi": search_regex}]
        if referral_institution:
            query["referral_institution"] = referral_institution
        if igss_unit_id:
            query["igss_unit_id"] = igss_unit_id
        if igss_nog:
            query["igss_nog"] = {"$regex": _re.escape(igss_nog.strip()), "$options": "i"}
        if gender:
            query["gender"] = gender
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            if date_query:
                query["created_at"] = date_query
        
        patients = await db.patients.find(query, {"_id": 0}).sort("record_number", 1).to_list(10000)
        
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(letter), rightMargin=0.5*inch,
                                leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16,
                                     alignment=TA_CENTER, spaceAfter=20, textColor=colors.HexColor('#0F6E56'))
        elements.append(Paragraph("Novavisión - Lista de Pacientes", title_style))
        elements.append(Paragraph(f"Generado: {now_gt().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        table_data = [["Expediente", "Nombre Completo", "Género", "Edad", "Teléfono", "DPI", "Institución", "Unidad IGSS", "NOG"]]
        
        for patient in patients:
            enriched = await enrich_patient(patient)
            table_data.append([
                enriched["record_number"], enriched["full_name"], enriched["gender"].capitalize(),
                str(enriched["age"]), enriched["phone"], enriched.get("dpi", "-"),
                enriched["referral_institution_label"],
                enriched.get("igss_unit_name", "") or "-", enriched.get("igss_nog", "") or "-"
            ])
        
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F6E56')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        
        elements.append(table)
        doc.build(elements)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=pacientes_novavision.pdf"}
        )
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Librería PDF no disponible: {str(e)}")


# ==================== IMPORTACIÓN MASIVA ====================

class ImportPatientItem(BaseModel):
    """Esquema flexible para importación - campos opcionales para mayor tolerancia"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    nombre: Optional[str] = None  # Alternativo: nombre completo
    nombres: Optional[str] = None  # Alternativo
    apellidos: Optional[str] = None  # Alternativo
    gender: Optional[str] = None
    sexo: Optional[str] = None  # Alternativo
    birth_date: Optional[str] = None
    fecha_nacimiento: Optional[str] = None  # Alternativo
    phone: Optional[str] = None
    telefono: Optional[str] = None  # Alternativo
    email: Optional[str] = None
    correo: Optional[str] = None  # Alternativo
    dpi: Optional[str] = None
    cui: Optional[str] = None  # Alternativo
    profession: Optional[str] = None
    profesion: Optional[str] = None  # Alternativo
    direccion: Optional[str] = None  # Dirección
    estado_civil: Optional[str] = None  # Estado civil
    referral_institution: Optional[str] = None
    institucion: Optional[str] = None  # Alternativo
    insurance_name: Optional[str] = None
    seguro: Optional[str] = None  # Alternativo
    nombre_seguro: Optional[str] = None  # Alternativo
    otra_institucion: Optional[str] = None  # Nombre de otra institución
    comments: Optional[str] = None
    observaciones: Optional[str] = None  # Alternativo
    record_number: Optional[str] = None  # Para mantener expediente existente
    expediente: Optional[str] = None  # Alternativo
    emergency_phone: Optional[str] = None
    emergencia_telefono: Optional[str] = None  # Alternativo
    emergency_contact_name: Optional[str] = None
    emergencia_nombre: Optional[str] = None  # Alternativo
    emergency_contact_relationship: Optional[str] = None
    emergencia_parentesco: Optional[str] = None  # Alternativo
    # Campos IGSS
    igss_unidad: Optional[str] = None
    igss_afiliacion: Optional[str] = None
    igss_no_sps: Optional[str] = None
    igss_codigo: Optional[str] = None
    igss_nog: Optional[str] = None  # Número de Orden de Gestión
    igss_tipo_compra: Optional[str] = None


class ImportBatchRequest(BaseModel):
    """Request para importación por lotes"""
    patients: List[ImportPatientItem]
    batch_number: int = 1
    total_batches: int = 1
    skip_duplicates: bool = True
    preserve_record_numbers: bool = False  # Mantener números de expediente existentes


class ImportResult(BaseModel):
    """Resultado de importación"""
    success: bool
    batch_number: int
    total_processed: int
    inserted: int
    duplicates: int
    errors: int
    error_details: List[dict] = []
    duplicate_details: List[dict] = []


class ImportValidationResult(BaseModel):
    """Resultado de validación previa"""
    valid: bool
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    errors: List[dict] = []
    duplicates: List[dict] = []
    field_mapping: dict = {}
    sample_data: List[dict] = []


def normalize_gender(value: str) -> str:
    """Normalizar valor de género"""
    if not value:
        return "otro"
    value_lower = value.lower().strip()
    if value_lower in ['m', 'masculino', 'male', 'hombre', 'h']:
        return "masculino"
    elif value_lower in ['f', 'femenino', 'female', 'mujer']:
        return "femenino"
    return "otro"


def normalize_institution(value: str) -> str:
    """Normalizar institución de referencia"""
    if not value:
        return "particular"
    value_lower = value.lower().strip()
    if 'igss' in value_lower:
        return "igss"
    elif 'seguro' in value_lower or 'privado' in value_lower:
        return "seguro_privado"
    elif 'particular' in value_lower or 'privado' in value_lower:
        return "particular"
    elif value_lower and value_lower != 'particular':
        return "otra"
    return "particular"


def normalize_date(value: str) -> Optional[str]:
    """Normalizar fecha a formato YYYY-MM-DD"""
    if not value:
        return None
    
    import re
    value = str(value).strip()
    
    # Formato ISO: 2024-01-15
    if re.match(r'^\d{4}-\d{2}-\d{2}', value):
        return value[:10]
    
    # Formato DD/MM/YYYY o DD-MM-YYYY
    match = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', value)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # Formato MM/DD/YYYY
    match = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', value)
    if match:
        part1, part2, year = match.groups()
        # Si part1 > 12, asumimos DD/MM/YYYY
        if int(part1) > 12:
            return f"{year}-{part2.zfill(2)}-{part1.zfill(2)}"
        # Si part2 > 12, asumimos MM/DD/YYYY
        elif int(part2) > 12:
            return f"{year}-{part1.zfill(2)}-{part2.zfill(2)}"
        # Ambiguo, asumimos DD/MM/YYYY (formato guatemalteco)
        return f"{year}-{part2.zfill(2)}-{part1.zfill(2)}"
    
    # Formato YYYY/MM/DD
    match = re.match(r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$', value)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    return None


def normalize_phone(value: str) -> str:
    """Normalizar teléfono"""
    if not value:
        return "00000000"
    import re
    # Remover todo excepto dígitos
    phone = re.sub(r'[^\d]', '', str(value))
    # Si tiene código de país, removerlo
    if phone.startswith('502') and len(phone) > 8:
        phone = phone[3:]
    # Asegurar al menos 8 dígitos
    if len(phone) < 8:
        phone = phone.zfill(8)
    return phone[:20]


def normalize_dpi(value: str) -> Optional[str]:
    """Normalizar DPI/CUI"""
    if not value:
        return None
    import re
    dpi = re.sub(r'[^\d]', '', str(value))
    if len(dpi) == 13:
        return dpi
    return None


def extract_patient_data(item: ImportPatientItem) -> dict:
    """Extraer y normalizar datos del paciente desde el item de importación"""
    # Nombre
    first_name = item.first_name or item.nombres or ""
    last_name = item.last_name or item.apellidos or ""
    
    # Si viene nombre completo, intentar separar
    if not first_name and not last_name and item.nombre:
        parts = item.nombre.strip().split()
        if len(parts) >= 2:
            # Asumimos primer nombre(s) y último apellido(s)
            mid = len(parts) // 2
            first_name = " ".join(parts[:mid])
            last_name = " ".join(parts[mid:])
        else:
            first_name = item.nombre
            last_name = ""
    
    # Género
    gender = normalize_gender(item.gender or item.sexo or "")
    
    # Fecha de nacimiento
    birth_date = normalize_date(item.birth_date or item.fecha_nacimiento or "")
    
    # Teléfono
    phone = normalize_phone(item.phone or item.telefono or "")
    
    # Email
    email = item.email or item.correo or ""
    
    # DPI
    dpi = normalize_dpi(item.dpi or item.cui or "")
    
    # Profesión
    profession = item.profession or item.profesion or ""
    
    # Institución
    referral_institution = normalize_institution(item.referral_institution or item.institucion or "")
    
    # Seguro
    insurance_name = item.insurance_name or item.seguro or item.nombre_seguro or ""
    
    # Otra institución
    other_institution_name = item.otra_institucion or ""
    
    # Comentarios
    comments = item.comments or item.observaciones or ""
    
    # Número de expediente (si se quiere preservar)
    record_number = item.record_number or item.expediente or None
    
    # Contacto de emergencia
    emergency_phone = item.emergency_phone or item.emergencia_telefono or ""
    emergency_contact_name = item.emergency_contact_name or item.emergencia_nombre or ""
    emergency_contact_relationship = item.emergency_contact_relationship or item.emergencia_parentesco or ""
    
    # Campos IGSS (solo si la institución es IGSS)
    is_igss = referral_institution == "igss"
    igss_afiliacion = (item.igss_afiliacion or "") if is_igss else ""
    igss_no_sps = (item.igss_no_sps or "") if is_igss else ""
    igss_codigo = (item.igss_codigo or "") if is_igss else ""
    igss_nog = (item.igss_nog or "") if is_igss else ""
    igss_tipo_compra = (item.igss_tipo_compra or "") if is_igss else ""
    igss_unidad = (item.igss_unidad or "") if is_igss else ""
    
    return {
        "first_name": first_name.strip()[:100] if first_name else "",
        "last_name": last_name.strip()[:100] if last_name else "",
        "gender": gender,
        "birth_date": birth_date or "1900-01-01",
        "phone": phone,
        "email": email[:100] if email else "",
        "dpi": dpi,
        "profession": profession[:100] if profession else "",
        "direccion": item.direccion or "",
        "estado_civil": item.estado_civil or "",
        "referral_institution": referral_institution,
        "insurance_name": insurance_name[:100] if insurance_name else "",
        "other_institution_name": other_institution_name[:100] if other_institution_name else "",
        "comments": comments[:500] if comments else "",
        "emergency_phone": emergency_phone,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_relationship": emergency_contact_relationship,
        "igss_unit_id": None,
        "igss_unit_name": igss_unidad,
        "igss_afiliacion": igss_afiliacion,
        "igss_no_sps": igss_no_sps,
        "igss_codigo": igss_codigo,
        "igss_nog": igss_nog,
        "igss_tipo_compra": igss_tipo_compra,
        "_original_record_number": record_number
    }


@router.post("/import/validate", response_model=ImportValidationResult)
async def validate_import_data(
    patients: List[ImportPatientItem] = Body(...),
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """
    Validar datos de importación antes de procesar.
    Detecta duplicados, errores y muestra mapeo de campos.
    """
    errors = []
    duplicates = []
    valid_count = 0
    
    # Detectar campos presentes en los datos
    field_mapping = {}
    if patients:
        sample = patients[0].model_dump()
        for key, value in sample.items():
            if value is not None and value != "":
                field_mapping[key] = "detectado"
    
    # Obtener DPIs y nombres existentes para verificar duplicados
    existing_dpis = set()
    existing_names = set()
    
    cursor = db.patients.find(
        {"is_active": True}, 
        {"_id": 0, "dpi": 1, "first_name": 1, "last_name": 1}
    )
    async for p in cursor:
        if p.get("dpi"):
            existing_dpis.add(p["dpi"])
        name_key = f"{p.get('first_name', '').lower()}|{p.get('last_name', '').lower()}"
        existing_names.add(name_key)
    
    # Validar cada registro
    for idx, item in enumerate(patients[:1000]):  # Limitar validación a primeros 1000
        try:
            data = extract_patient_data(item)
            
            # Validar campos requeridos
            if not data["first_name"]:
                errors.append({
                    "row": idx + 1,
                    "error": "Nombre vacío o no detectado",
                    "data": item.model_dump()
                })
                continue
            
            # Verificar duplicado por DPI
            if data["dpi"] and data["dpi"] in existing_dpis:
                duplicates.append({
                    "row": idx + 1,
                    "type": "DPI",
                    "value": data["dpi"],
                    "name": f"{data['first_name']} {data['last_name']}"
                })
                continue
            
            # Verificar duplicado por nombre
            name_key = f"{data['first_name'].lower()}|{data['last_name'].lower()}"
            if name_key in existing_names:
                duplicates.append({
                    "row": idx + 1,
                    "type": "Nombre",
                    "value": f"{data['first_name']} {data['last_name']}",
                    "name": f"{data['first_name']} {data['last_name']}"
                })
                continue
            
            valid_count += 1
            existing_names.add(name_key)
            if data["dpi"]:
                existing_dpis.add(data["dpi"])
                
        except Exception as e:
            errors.append({
                "row": idx + 1,
                "error": str(e),
                "data": item.model_dump() if hasattr(item, 'model_dump') else str(item)
            })
    
    # Muestra de datos normalizados
    sample_data = []
    for item in patients[:5]:
        try:
            sample_data.append(extract_patient_data(item))
        except Exception:
            pass
    
    return ImportValidationResult(
        valid=len(errors) == 0 and valid_count > 0,
        total_records=len(patients),
        valid_records=valid_count,
        invalid_records=len(errors),
        duplicate_records=len(duplicates),
        errors=errors[:50],  # Limitar errores mostrados
        duplicates=duplicates[:50],  # Limitar duplicados mostrados
        field_mapping=field_mapping,
        sample_data=sample_data
    )


@router.post("/import/batch", response_model=ImportResult)
async def import_patients_batch(
    request: ImportBatchRequest,
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """
    Importar un lote de pacientes.
    Diseñado para procesar ~500 registros por lote.
    """
    inserted = 0
    duplicates = 0
    errors_count = 0
    error_details = []
    duplicate_details = []
    
    now = datetime.now(timezone.utc)
    
    # Obtener DPIs existentes
    existing_dpis = set()
    if request.skip_duplicates:
        cursor = db.patients.find({"is_active": True, "dpi": {"$ne": None}}, {"_id": 0, "dpi": 1})
        async for p in cursor:
            if p.get("dpi"):
                existing_dpis.add(p["dpi"])
    
    # Obtener último número de expediente
    last_record = await db.patients.find_one(
        {"record_number": {"$regex": r"^EXP-\d{6}-"}},
        sort=[("record_number", -1)]
    )
    
    if last_record:
        try:
            last_num = int(last_record["record_number"].split("-")[-1])
        except (ValueError, IndexError):
            last_num = 0
    else:
        last_num = 0
    
    current_prefix = f"EXP-{now.strftime('%Y%m')}-"
    next_num = last_num + 1
    
    # Procesar pacientes en el lote
    patients_to_insert = []
    
    for idx, item in enumerate(request.patients):
        try:
            data = extract_patient_data(item)
            
            # Validar campos mínimos
            if not data["first_name"]:
                errors_count += 1
                error_details.append({
                    "row": idx + 1,
                    "error": "Nombre vacío"
                })
                continue
            
            # Verificar duplicado por DPI
            if data["dpi"] and data["dpi"] in existing_dpis:
                if request.skip_duplicates:
                    duplicates += 1
                    duplicate_details.append({
                        "row": idx + 1,
                        "dpi": data["dpi"],
                        "name": f"{data['first_name']} {data['last_name']}"
                    })
                    continue
            
            # Generar número de expediente
            if request.preserve_record_numbers and data.get("_original_record_number"):
                record_number = data["_original_record_number"]
            else:
                record_number = f"{current_prefix}{next_num:04d}"
                next_num += 1
            
            # Preparar documento
            patient_doc = {
                "id": str(uuid.uuid4()),
                "record_number": record_number,
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "gender": data["gender"],
                "birth_date": data["birth_date"],
                "phone": data["phone"],
                "email": data["email"],
                "dpi": data["dpi"],
                "profession": data["profession"],
                "referral_institution": data["referral_institution"],
                "insurance_name": data["insurance_name"],
                "other_institution_name": data["other_institution_name"],
                "igss_unit_id": data["igss_unit_id"],
                "igss_afiliacion": data.get("igss_afiliacion", ""),
                "igss_no_sps": data.get("igss_no_sps", ""),
                "igss_codigo": data.get("igss_codigo", ""),
                "igss_nog": data.get("igss_nog", ""),
                "igss_tipo_compra": data.get("igss_tipo_compra", ""),
                "comments": data["comments"],
                "emergency_phone": data["emergency_phone"],
                "emergency_contact_name": data["emergency_contact_name"],
                "emergency_contact_relationship": data["emergency_contact_relationship"],
                "direccion": data.get("direccion", ""),
                "estado_civil": data.get("estado_civil", ""),
                "is_active": True,
                "created_by": current_user["id"],
                "created_at": now.isoformat(),
                "updated_by": None,
                "updated_at": None,
                "imported": True,
                "import_date": now.isoformat(),
                "import_batch": request.batch_number
            }
            
            patients_to_insert.append(patient_doc)
            
            # Agregar DPI al set para evitar duplicados dentro del mismo lote
            if data["dpi"]:
                existing_dpis.add(data["dpi"])
                
        except Exception as e:
            errors_count += 1
            error_details.append({
                "row": idx + 1,
                "error": str(e)
            })
    
    # Insertar en lote
    if patients_to_insert:
        try:
            result = await db.patients.insert_many(patients_to_insert, ordered=False)
            inserted = len(result.inserted_ids)
        except Exception as e:
            # Algunos pueden haber fallado por duplicados de índice único
            error_str = str(e)
            if "duplicate key" in error_str.lower():
                # Contar cuántos se insertaron realmente
                inserted = patients_to_insert.__len__() - errors_count
            else:
                raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    
    return ImportResult(
        success=True,
        batch_number=request.batch_number,
        total_processed=len(request.patients),
        inserted=inserted,
        duplicates=duplicates,
        errors=errors_count,
        error_details=error_details[:20],
        duplicate_details=duplicate_details[:20]
    )


@router.get("/import/template")
async def get_import_template(
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """
    Obtener plantilla JSON para importación.
    """
    template = {
        "descripcion": "Plantilla para importación masiva de pacientes NovaVision",
        "instrucciones": [
            "El archivo debe ser un array JSON de objetos",
            "Puede usar nombres de campos en español o inglés",
            "Los campos obligatorios son: nombre (first_name o nombres) y apellido (last_name o apellidos)",
            "El formato de fecha puede ser: YYYY-MM-DD, DD/MM/YYYY, o DD-MM-YYYY",
            "El género puede ser: M, F, masculino, femenino, hombre, mujer",
            "El DPI debe tener exactamente 13 dígitos",
            "Se recomienda importar en lotes de 500 registros máximo"
        ],
        "campos_aceptados": {
            "nombre_completo": ["nombre", "name", "full_name"],
            "nombres": ["first_name", "nombres", "primer_nombre"],
            "apellidos": ["last_name", "apellidos", "apellido"],
            "genero": ["gender", "sexo", "genero"],
            "fecha_nacimiento": ["birth_date", "fecha_nacimiento", "nacimiento"],
            "telefono": ["phone", "telefono", "tel"],
            "email": ["email", "correo", "correo_electronico"],
            "dpi": ["dpi", "cui", "documento"],
            "profesion": ["profession", "profesion", "ocupacion"],
            "institucion": ["referral_institution", "institucion", "referido_por"],
            "seguro": ["insurance_name", "seguro", "aseguradora"],
            "observaciones": ["comments", "observaciones", "notas"],
            "expediente": ["record_number", "expediente", "numero_expediente"]
        },
        "ejemplo": [
            {
                "nombres": "María José",
                "apellidos": "García López",
                "sexo": "F",
                "fecha_nacimiento": "15/03/1985",
                "telefono": "5555-1234",
                "dpi": "1234567890123",
                "profesion": "Maestra",
                "institucion": "IGSS"
            },
            {
                "first_name": "Juan Carlos",
                "last_name": "Pérez Morales",
                "gender": "M",
                "birth_date": "1990-07-22",
                "phone": "4444-5678",
                "email": "juan@email.com",
                "profession": "Ingeniero",
                "referral_institution": "particular"
            }
        ]
    }
    
    return template


@router.get("/import/stats")
async def get_import_stats(
    current_user: dict = Depends(require_role(["admin", "superadmin"]))
):
    """
    Obtener estadísticas de importaciones realizadas.
    """
    total_patients = await db.patients.count_documents({})
    imported_patients = await db.patients.count_documents({"imported": True})
    manual_patients = total_patients - imported_patients
    
    # Estadísticas por lote de importación
    pipeline = [
        {"$match": {"imported": True}},
        {"$group": {
            "_id": "$import_batch",
            "count": {"$sum": 1},
            "date": {"$first": "$import_date"}
        }},
        {"$sort": {"_id": -1}},
        {"$limit": 10}
    ]
    
    batches = await db.patients.aggregate(pipeline).to_list(10)
    
    return {
        "total_patients": total_patients,
        "imported_patients": imported_patients,
        "manual_patients": manual_patients,
        "import_percentage": round(imported_patients / total_patients * 100, 2) if total_patients > 0 else 0,
        "recent_batches": batches
    }

