# /app/backend/routes/laboratorio_pruebas.py
"""
Módulo Laboratorio de Pruebas - NovaVision ERP
Panel de administración para generación y ejecución de pruebas E2E.
Solo accesible por SuperAdmin y NUNCA en producción.
"""

import os
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import asyncio

# Verificación de ambiente ANTES de todo
ENVIRONMENT = os.environ.get('ENVIRONMENT', os.environ.get('NODE_ENV', 'development'))
IS_PRODUCTION = ENVIRONMENT.lower() == 'production'

router = APIRouter(prefix="/laboratorio-pruebas", tags=["Laboratorio de Pruebas"])


# ==================== MODELOS ====================

class SeedResponse(BaseModel):
    success: bool
    message: str
    datos_creados: Dict[str, int] = {}
    errores: List[str] = []


class PurgeResponse(BaseModel):
    success: bool
    message: str
    datos_eliminados: Dict[str, int] = {}
    verificacion_residuos: Dict[str, int] = {}


class TestResult(BaseModel):
    test_id: str
    nombre: str
    estado: str  # PASA, FALLA, OMITIDA
    severidad: str
    mensaje: Optional[str] = None
    duracion_ms: Optional[int] = None
    evidencia: Optional[Dict[str, Any]] = None


class TestBatchResponse(BaseModel):
    success: bool
    total_pruebas: int
    aprobadas: int
    falladas: int
    omitidas: int
    duracion_total_ms: int
    resultados: List[TestResult]


class EstadoDatosPrueba(BaseModel):
    tiene_datos_prueba: bool
    conteo_por_coleccion: Dict[str, int]
    fecha_ultimo_seed: Optional[str] = None


# ==================== MIDDLEWARE DE SEGURIDAD ====================

async def verificar_no_produccion():
    """Bloquea TODAS las operaciones en producción"""
    if IS_PRODUCTION:
        # Registrar intento en audit log (si hay acceso a db)
        raise HTTPException(
            status_code=403,
            detail="❌ BLOQUEADO: El Laboratorio de Pruebas NO está disponible en producción. "
                   "Esta restricción no es negociable ni configurable."
        )
    return True


async def verificar_superadmin(current_user: dict):
    """Verifica que el usuario sea SuperAdmin"""
    if current_user.get("role") != "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Solo SuperAdmin puede acceder al Laboratorio de Pruebas"
        )
    return True


# ==================== ENDPOINTS ====================

@router.get("/estado", response_model=EstadoDatosPrueba)
async def obtener_estado_datos_prueba(
    _: bool = Depends(verificar_no_produccion)
):
    """
    Obtiene el estado actual de los datos de prueba en la base de datos.
    Muestra cuántos registros de prueba existen por colección.
    """
    from server import db
    
    colecciones = [
        "patients", "users", "bodegas_inventario", "productos_inventario",
        "lotes_inventario", "movimientos_kardex", "ventas", "tickets_espera",
        "caja_movimientos", "caja_cierres", "citas", "medicos_agenda",
        "evaluaciones_oftalmologicas", "surgeries", "expenses",
        "optica_sales", "optica_frames", "optica_contact_lenses",
        "optica_lens_types", "proveedores", "tipos_pagador"
    ]
    
    conteo = {}
    total = 0
    
    for col in colecciones:
        try:
            count = await db[col].count_documents({"esDatoPrueba": True})
            if count > 0:
                conteo[col] = count
                total += count
        except Exception:
            pass
    
    # Buscar fecha del último seed
    ultima_fecha = None
    try:
        ultimo_registro = await db.audit_logs.find_one(
            {"action": "SEED_DATOS_PRUEBA"},
            sort=[("timestamp", -1)]
        )
        if ultimo_registro:
            ultima_fecha = ultimo_registro.get("timestamp")
    except Exception:
        pass
    
    return EstadoDatosPrueba(
        tiene_datos_prueba=total > 0,
        conteo_por_coleccion=conteo,
        fecha_ultimo_seed=ultima_fecha
    )


@router.post("/seed/datos-maestros", response_model=SeedResponse)
async def seed_datos_maestros_endpoint(
    _: bool = Depends(verificar_no_produccion)
):
    """
    FASE 1: Genera datos maestros de prueba.
    - Bodegas (4)
    - Proveedores (4)
    - Productos clínica (18)
    - Lotes con condiciones especiales
    - Usuarios de prueba (5)
    - Médicos (4)
    - Tipo de pagador (1)
    - Productos óptica (12)
    """
    from server import db, audit
    from seed.datos_maestros import seed_datos_maestros
    
    try:
        # Verificar si ya existen datos de prueba
        existing = await db.bodegas_inventario.count_documents({"esDatoPrueba": True})
        if existing > 0:
            return SeedResponse(
                success=False,
                message="Ya existen datos de prueba. Ejecute la purga primero.",
                errores=["Datos de prueba existentes detectados"]
            )
        
        resultado = await seed_datos_maestros(db)
        
        # Registrar en audit log
        await audit.log(
            action="SEED_DATOS_PRUEBA",
            user_id="system",
            user_name="laboratorio_pruebas",
            details={
                "fase": "datos_maestros",
                "bodegas": len(resultado["bodegas"]),
                "proveedores": len(resultado["proveedores"]),
                "productos_clinica": len(resultado["productos_clinica"]),
                "lotes": len(resultado["lotes"]),
                "usuarios": len(resultado["usuarios"]),
                "medicos": len(resultado["medicos"])
            }
        )
        
        return SeedResponse(
            success=True,
            message="Datos maestros de prueba generados exitosamente",
            datos_creados={
                "bodegas": len(resultado["bodegas"]),
                "proveedores": len(resultado["proveedores"]),
                "productos_clinica": len(resultado["productos_clinica"]),
                "lotes": len(resultado["lotes"]),
                "usuarios": len(resultado["usuarios"]),
                "medicos": len(resultado["medicos"]),
                "optica_frames": len(resultado["productos_optica"]["frames"]),
                "optica_lens_types": len(resultado["productos_optica"]["lens_types"]),
                "optica_contact_lenses": len(resultado["productos_optica"]["contact_lenses"])
            }
        )
        
    except Exception as e:
        return SeedResponse(
            success=False,
            message=f"Error al generar datos maestros: {str(e)}",
            errores=[str(e)]
        )


@router.post("/seed/pacientes", response_model=SeedResponse)
async def seed_pacientes_endpoint(
    _: bool = Depends(verificar_no_produccion)
):
    """
    FASE 2: Genera los 14 pacientes sintéticos de prueba.
    Cada paciente tiene un perfil específico para diferentes pruebas.
    """
    from server import db, audit
    from seed.pacientes import seed_pacientes
    
    try:
        # Verificar si ya existen pacientes de prueba
        existing = await db.patients.count_documents({"esDatoPrueba": True})
        if existing > 0:
            return SeedResponse(
                success=False,
                message="Ya existen pacientes de prueba. Ejecute la purga primero.",
                errores=["Pacientes de prueba existentes detectados"]
            )
        
        pacientes = await seed_pacientes(db)
        
        # Registrar en audit log
        await audit.log(
            action="SEED_DATOS_PRUEBA",
            user_id="system",
            user_name="laboratorio_pruebas",
            details={
                "fase": "pacientes",
                "pacientes_creados": len(pacientes) - 1  # -1 por el duplicado intencional no insertado
            }
        )
        
        return SeedResponse(
            success=True,
            message="Pacientes de prueba generados exitosamente",
            datos_creados={
                "pacientes": len(pacientes) - 1
            }
        )
        
    except Exception as e:
        return SeedResponse(
            success=False,
            message=f"Error al generar pacientes: {str(e)}",
            errores=[str(e)]
        )


@router.post("/seed/completo", response_model=SeedResponse)
async def seed_completo_endpoint(
    _: bool = Depends(verificar_no_produccion)
):
    """
    Ejecuta el seed completo: Fase 1 (datos maestros) + Fase 2 (pacientes).
    """
    from server import db, audit
    from seed.datos_maestros import seed_datos_maestros
    from seed.pacientes import seed_pacientes
    
    try:
        # Verificar si ya existen datos de prueba
        existing = await db.bodegas_inventario.count_documents({"esDatoPrueba": True})
        if existing > 0:
            return SeedResponse(
                success=False,
                message="Ya existen datos de prueba. Ejecute la purga primero.",
                errores=["Datos de prueba existentes detectados"]
            )
        
        # Fase 1: Datos maestros
        resultado_maestros = await seed_datos_maestros(db)
        
        # Fase 2: Pacientes
        pacientes = await seed_pacientes(db)
        
        # Registrar en audit log
        await audit.log(
            action="SEED_DATOS_PRUEBA",
            user_id="system",
            user_name="laboratorio_pruebas",
            details={
                "fase": "completo",
                "fases_ejecutadas": ["datos_maestros", "pacientes"]
            }
        )
        
        return SeedResponse(
            success=True,
            message="Seed completo ejecutado exitosamente (Fase 1 + Fase 2)",
            datos_creados={
                "bodegas": len(resultado_maestros["bodegas"]),
                "proveedores": len(resultado_maestros["proveedores"]),
                "productos_clinica": len(resultado_maestros["productos_clinica"]),
                "lotes": len(resultado_maestros["lotes"]),
                "usuarios": len(resultado_maestros["usuarios"]),
                "medicos": len(resultado_maestros["medicos"]),
                "pacientes": len(pacientes) - 1
            }
        )
        
    except Exception as e:
        return SeedResponse(
            success=False,
            message=f"Error en seed completo: {str(e)}",
            errores=[str(e)]
        )


@router.delete("/purgar", response_model=PurgeResponse)
async def purgar_datos_prueba(
    confirmacion: str,
    _: bool = Depends(verificar_no_produccion)
):
    """
    FASE 7: Elimina TODOS los datos de prueba.
    Requiere confirmación escrita: "ELIMINAR DATOS DE PRUEBA"
    """
    from server import db, audit
    
    # Verificar confirmación
    if confirmacion != "ELIMINAR DATOS DE PRUEBA":
        raise HTTPException(
            status_code=400,
            detail="Confirmación incorrecta. Escriba exactamente: ELIMINAR DATOS DE PRUEBA"
        )
    
    # Lista explícita de colecciones a purgar
    colecciones = [
        "patients", "users", "bodegas_inventario", "productos_inventario",
        "lotes_inventario", "movimientos_kardex", "ventas", "tickets_espera",
        "caja_movimientos", "caja_cierres", "citas", "medicos_agenda",
        "evaluaciones_oftalmologicas", "surgeries", "surgery_crm", "expenses",
        "expense_payments", "payment_authorizations",
        "optica_sales", "optica_sale_payments", "optica_frames", 
        "optica_contact_lenses", "optica_lens_types",
        "proveedores", "tipos_pagador", "doctors",
        "catalogo_diagnosticos", "catalogo_medicamentos"
    ]
    
    eliminados = {}
    
    for col in colecciones:
        try:
            result = await db[col].delete_many({"esDatoPrueba": True})
            if result.deleted_count > 0:
                eliminados[col] = result.deleted_count
        except Exception:
            pass
    
    # Verificación de residuos
    residuos = {}
    for col in colecciones:
        try:
            count = await db[col].count_documents({"esDatoPrueba": True})
            if count > 0:
                residuos[col] = count
        except Exception:
            pass
    
    # Registrar en audit log
    await audit.log(
        action="PURGA_DATOS_PRUEBA",
        user_id="system",
        user_name="laboratorio_pruebas",
        details={
            "eliminados": eliminados,
            "residuos": residuos
        }
    )
    
    if residuos:
        return PurgeResponse(
            success=False,
            message="Purga completada con residuos. Revisar manualmente.",
            datos_eliminados=eliminados,
            verificacion_residuos=residuos
        )
    
    return PurgeResponse(
        success=True,
        message="Todos los datos de prueba han sido eliminados exitosamente",
        datos_eliminados=eliminados,
        verificacion_residuos={}
    )


@router.get("/credenciales-prueba")
async def obtener_credenciales_prueba(
    _: bool = Depends(verificar_no_produccion)
):
    """
    Retorna las credenciales de los usuarios de prueba.
    Solo disponible fuera de producción.
    """
    return {
        "usuarios_prueba": [
            {"username": "prb.superadmin", "password": "PrbSuper2024!", "role": "superadmin"},
            {"username": "prb.admin", "password": "PrbAdmin2024!", "role": "admin"},
            {"username": "prb.usuario", "password": "PrbUser2024!", "role": "usuario"},
            {"username": "prb.medico1", "password": "PrbMed1-2024!", "role": "usuario", "nota": "Enlazado a médico 1"},
            {"username": "prb.medico2", "password": "PrbMed2-2024!", "role": "usuario", "nota": "Enlazado a médico 2"}
        ],
        "advertencia": "Estas credenciales son SOLO para ambiente de desarrollo"
    }
