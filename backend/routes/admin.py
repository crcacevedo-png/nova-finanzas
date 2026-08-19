# /app/backend/routes/admin.py
# Módulo de Administración - Integridad de datos y vinculación de cirugías
# Solo SuperAdmin

from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Optional
from datetime import datetime, timezone
import unicodedata

from config.database import db
from routes.auth import require_role

router = APIRouter(prefix="/admin", tags=["Administración"])


def normalizar_nombre(nombre: str) -> str:
    """Normaliza un nombre para comparación (sin acentos, minúsculas)"""
    if not nombre:
        return ""
    nombre = unicodedata.normalize('NFD', nombre.lower())
    nombre = ''.join(c for c in nombre if unicodedata.category(c) != 'Mn')
    return ' '.join(nombre.split())


@router.get("/integridad-pacientes")
async def get_integridad_pacientes(current_user: dict = Depends(require_role("superadmin"))):
    """
    Diagnóstico de integridad de pacientes (solo SuperAdmin)
    Detecta: pacientes sin referencias, referencias huérfanas, posibles duplicados
    """
    resultado = {
        "pacientes_sin_referencias": [],
        "referencias_huerfanas": {
            "citas": [],
            "evaluaciones": [],
            "cirugias": [],
            "movimientos_caja": [],
            "cuentas_por_cobrar": []
        },
        "posibles_duplicados": [],
        "estadisticas": {}
    }
    
    # 1. Obtener todos los IDs de pacientes activos
    pacientes = await db.patients.find({"is_active": True}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "dpi": 1, "record_number": 1}).to_list(10000)
    pacientes_ids = {p["id"] for p in pacientes}
    pacientes_por_dpi = {}
    
    # Detectar duplicados por DPI
    for p in pacientes:
        dpi = p.get("dpi", "").strip()
        if dpi and dpi != "":
            if dpi not in pacientes_por_dpi:
                pacientes_por_dpi[dpi] = []
            pacientes_por_dpi[dpi].append({
                "id": p["id"],
                "nombre": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                "expediente": p.get("record_number", "")
            })
    
    for dpi, lista in pacientes_por_dpi.items():
        if len(lista) > 1:
            resultado["posibles_duplicados"].append({"dpi": dpi, "pacientes": lista})
    
    # 2. Verificar citas huérfanas
    citas = await db.citas.find({"tipo_agenda": "pacientes", "paciente_id": {"$exists": True}}, {"_id": 0, "id": 1, "paciente_id": 1, "paciente_nombre": 1, "fecha": 1}).to_list(10000)
    for cita in citas:
        if cita.get("paciente_id") and cita["paciente_id"] not in pacientes_ids:
            resultado["referencias_huerfanas"]["citas"].append({
                "cita_id": cita["id"],
                "paciente_id_invalido": cita["paciente_id"],
                "paciente_nombre": cita.get("paciente_nombre", ""),
                "fecha": cita.get("fecha", "")
            })
    
    # 3. Verificar evaluaciones huérfanas
    evaluaciones = await db.evaluaciones_oftalmologicas.find({"paciente_id": {"$exists": True}}, {"_id": 0, "id": 1, "paciente_id": 1, "paciente_nombre": 1, "fecha": 1}).to_list(10000)
    for eva in evaluaciones:
        if eva.get("paciente_id") and eva["paciente_id"] not in pacientes_ids:
            resultado["referencias_huerfanas"]["evaluaciones"].append({
                "evaluacion_id": eva["id"],
                "paciente_id_invalido": eva["paciente_id"],
                "paciente_nombre": eva.get("paciente_nombre", ""),
                "fecha": eva.get("fecha", "")
            })
    
    # 4. Verificar cirugías huérfanas
    cirugias = await db.surgeries.find({"paciente_id": {"$exists": True, "$ne": None}}, {"_id": 0, "id": 1, "paciente_id": 1, "patient_name": 1, "date": 1}).to_list(10000)
    for cirugia in cirugias:
        if cirugia.get("paciente_id") and cirugia["paciente_id"] not in pacientes_ids:
            resultado["referencias_huerfanas"]["cirugias"].append({
                "cirugia_id": cirugia["id"],
                "paciente_id_invalido": cirugia["paciente_id"],
                "patient_name": cirugia.get("patient_name", ""),
                "fecha": cirugia.get("date", "")
            })
    
    # 5. Verificar movimientos de caja huérfanos
    movimientos = await db.caja_movimientos.find({"paciente_id": {"$exists": True, "$ne": None}}, {"_id": 0, "id": 1, "paciente_id": 1, "paciente_nombre": 1, "fecha": 1}).to_list(10000)
    for mov in movimientos:
        if mov.get("paciente_id") and mov["paciente_id"] not in pacientes_ids:
            resultado["referencias_huerfanas"]["movimientos_caja"].append({
                "movimiento_id": mov["id"],
                "paciente_id_invalido": mov["paciente_id"],
                "paciente_nombre": mov.get("paciente_nombre", ""),
                "fecha": mov.get("fecha", "")
            })
    
    # 6. Verificar CxC huérfanas
    cxc = await db.cuentas_por_cobrar.find({"paciente_id": {"$exists": True}}, {"_id": 0, "id": 1, "paciente_id": 1, "paciente_nombre": 1}).to_list(10000)
    for cuenta in cxc:
        if cuenta.get("paciente_id") and cuenta["paciente_id"] not in pacientes_ids:
            resultado["referencias_huerfanas"]["cuentas_por_cobrar"].append({
                "cxc_id": cuenta["id"],
                "paciente_id_invalido": cuenta["paciente_id"],
                "paciente_nombre": cuenta.get("paciente_nombre", "")
            })
    
    # 7. Pacientes sin ninguna referencia
    pacientes_referenciados = set()
    for cita in citas:
        if cita.get("paciente_id"):
            pacientes_referenciados.add(cita["paciente_id"])
    for eva in evaluaciones:
        if eva.get("paciente_id"):
            pacientes_referenciados.add(eva["paciente_id"])
    for mov in movimientos:
        if mov.get("paciente_id"):
            pacientes_referenciados.add(mov["paciente_id"])
    
    for p in pacientes:
        if p["id"] not in pacientes_referenciados:
            resultado["pacientes_sin_referencias"].append({
                "id": p["id"],
                "nombre": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                "expediente": p.get("record_number", ""),
                "dpi": p.get("dpi", "")
            })
    
    resultado["estadisticas"] = {
        "total_pacientes": len(pacientes),
        "pacientes_con_referencias": len(pacientes_referenciados),
        "pacientes_sin_referencias": len(resultado["pacientes_sin_referencias"]),
        "citas_huerfanas": len(resultado["referencias_huerfanas"]["citas"]),
        "evaluaciones_huerfanas": len(resultado["referencias_huerfanas"]["evaluaciones"]),
        "cirugias_huerfanas": len(resultado["referencias_huerfanas"]["cirugias"]),
        "posibles_duplicados": len(resultado["posibles_duplicados"])
    }
    
    return resultado


@router.get("/integridad-datos")
async def get_integridad_datos(current_user: dict = Depends(require_role("superadmin"))):
    """
    Verificación de integridad de datos (solo SuperAdmin)
    Detecta: documentos sin tag origen, catálogos duplicados
    """
    resultado = {
        "documentos_sin_origen": {
            "caja_movimientos": 0,
            "caja_cierres": 0,
            "cuentas_por_cobrar": 0
        },
        "catalogos_duplicados": {
            "medicamentos": [],
            "estudios": [],
            "diagnosticos": [],
            "pagadores": []
        },
        "referencias_rotas": [],
        "estadisticas": {}
    }
    
    # 1. Documentos sin tag origen
    resultado["documentos_sin_origen"]["caja_movimientos"] = await db.caja_movimientos.count_documents({
        "$or": [{"origen": {"$exists": False}}, {"origen": None}, {"origen": ""}]
    })
    resultado["documentos_sin_origen"]["caja_cierres"] = await db.caja_cierres.count_documents({
        "$or": [{"origen": {"$exists": False}}, {"origen": None}, {"origen": ""}]
    })
    resultado["documentos_sin_origen"]["cuentas_por_cobrar"] = await db.cuentas_por_cobrar.count_documents({
        "$or": [{"origen": {"$exists": False}}, {"origen": None}, {"origen": ""}]
    })
    
    # 2. Catálogos duplicados
    for coleccion, campo in [
        ("catalogo_medicamentos", "medicamentos"),
        ("catalogo_estudios", "estudios"),
        ("catalogo_diagnosticos", "diagnosticos"),
        ("caja_pagadores", "pagadores")
    ]:
        try:
            items = await db[coleccion].find({}, {"_id": 0, "nombre": 1}).to_list(10000)
            nombres = {}
            for item in items:
                nombre = item.get("nombre", "").lower().strip()
                if nombre:
                    nombres[nombre] = nombres.get(nombre, 0) + 1
            resultado["catalogos_duplicados"][campo] = [n for n, c in nombres.items() if c > 1]
        except Exception:
            pass
    
    resultado["estadisticas"] = {
        "total_sin_origen": sum(resultado["documentos_sin_origen"].values()),
        "total_catalogos_duplicados": sum(len(v) for v in resultado["catalogos_duplicados"].values())
    }
    
    return resultado


@router.post("/vincular-cirugias")
async def vincular_cirugias(current_user: dict = Depends(require_role("superadmin"))):
    """
    Vincula cirugías existentes con pacientes basándose en coincidencia de nombres.
    """
    cirugias_sin_vincular = await db.surgeries.find({
        "$or": [{"paciente_id": {"$exists": False}}, {"paciente_id": None}, {"paciente_id": ""}]
    }, {"_id": 0}).to_list(1000)
    
    if not cirugias_sin_vincular:
        return {"message": "No hay cirugías sin vincular", "vinculadas": 0, "no_encontradas": 0, "detalles": []}
    
    pacientes = await db.patients.find({"is_active": True}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}).to_list(10000)
    
    pacientes_por_nombre = {}
    for p in pacientes:
        nombre_completo = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        nombre_normalizado = normalizar_nombre(nombre_completo)
        if nombre_normalizado:
            pacientes_por_nombre[nombre_normalizado] = p["id"]
    
    vinculadas = 0
    no_encontradas = 0
    detalles = []
    
    for cirugia in cirugias_sin_vincular:
        patient_name = cirugia.get("patient_name", "")
        nombre_normalizado = normalizar_nombre(patient_name)
        
        if nombre_normalizado in pacientes_por_nombre:
            paciente_id = pacientes_por_nombre[nombre_normalizado]
            await db.surgeries.update_one(
                {"id": cirugia["id"]},
                {"$set": {"paciente_id": paciente_id, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            vinculadas += 1
            detalles.append({"cirugia_id": cirugia["id"], "patient_name": patient_name, "paciente_id": paciente_id, "estado": "vinculada"})
        else:
            no_encontradas += 1
            detalles.append({"cirugia_id": cirugia["id"], "patient_name": patient_name, "paciente_id": None, "estado": "no_encontrada"})
    
    return {"message": f"Proceso completado: {vinculadas} vinculadas, {no_encontradas} sin coincidencia", "vinculadas": vinculadas, "no_encontradas": no_encontradas, "detalles": detalles}


@router.get("/cirugias-sin-vincular")
async def get_cirugias_sin_vincular(current_user: dict = Depends(require_role("superadmin"))):
    """Lista cirugías que no tienen paciente_id asignado."""
    cirugias = await db.surgeries.find({
        "$or": [{"paciente_id": {"$exists": False}}, {"paciente_id": None}, {"paciente_id": ""}]
    }, {"_id": 0, "id": 1, "patient_name": 1, "date": 1, "procedure": 1}).to_list(1000)
    
    pacientes = await db.patients.find({"is_active": True}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}).to_list(10000)
    
    resultado = []
    for cirugia in cirugias:
        patient_name = cirugia.get("patient_name", "").lower()
        posibles = []
        for p in pacientes:
            nombre = f"{p.get('first_name', '')} {p.get('last_name', '')}".lower()
            if patient_name in nombre or nombre in patient_name:
                posibles.append({"paciente_id": p["id"], "nombre": f"{p.get('first_name', '')} {p.get('last_name', '')}"})
        
        resultado.append({
            "cirugia_id": cirugia["id"],
            "patient_name": cirugia.get("patient_name", ""),
            "date": cirugia.get("date", ""),
            "procedure": cirugia.get("procedure", ""),
            "posibles_coincidencias": posibles[:5]
        })
    
    return {"total": len(resultado), "cirugias": resultado}


@router.put("/vincular-cirugia/{cirugia_id}")
async def vincular_cirugia_manual(
    cirugia_id: str,
    paciente_id: str = Body(..., embed=True),
    current_user: dict = Depends(require_role("superadmin"))
):
    """Vincula manualmente una cirugía específica con un paciente."""
    cirugia = await db.surgeries.find_one({"id": cirugia_id}, {"_id": 0})
    if not cirugia:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    
    paciente = await db.patients.find_one({"id": paciente_id}, {"_id": 0, "first_name": 1, "last_name": 1})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    await db.surgeries.update_one(
        {"id": cirugia_id},
        {"$set": {"paciente_id": paciente_id, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "message": "Cirugía vinculada exitosamente",
        "cirugia_id": cirugia_id,
        "paciente_id": paciente_id,
        "paciente_nombre": f"{paciente.get('first_name', '')} {paciente.get('last_name', '')}"
    }
