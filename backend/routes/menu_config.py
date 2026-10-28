# /app/backend/routes/menu_config.py
# Configuración de menús por rol

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timezone
from .auth import get_current_user, require_permission
from config.database import db

router = APIRouter(prefix="/menu-config", tags=["Menu Configuration"])

# Roles de sistema para la configuración de menús.
# Los roles personalizados (p. ej. "administrador_igss") se leen dinámicamente de db.roles.
SYSTEM_ROLES_MENU = ["superadmin", "admin", "usuario", "optica", "medico"]


async def _get_configurable_roles():
    """Roles configurables en 'Menús por Rol': roles de sistema + personalizados (db.roles)."""
    roles = list(SYSTEM_ROLES_MENU)
    try:
        custom = await db.roles.find({"name": {"$nin": SYSTEM_ROLES_MENU}}, {"name": 1}).to_list(200)
        for r in custom:
            name = r.get("name")
            if name and name not in roles:
                roles.append(name)
    except Exception:
        pass
    return roles


# Estructura de menús disponibles en el sistema
AVAILABLE_MENUS = {
    "dashboard": {
        "id": "dashboard",
        "label": "Dashboard",
        "path": "/dashboard",
        "icon": "LayoutDashboard",
        "category": "principal",
        "description": "Panel principal del sistema con estadísticas"
    },
    "dashboard_financiero": {
        "id": "dashboard_financiero",
        "label": "Dashboard Financiero",
        "path": "/dashboard-financiero",
        "icon": "TrendingUp",
        "category": "principal",
        "description": "Panel financiero con análisis de gastos e ingresos"
    },
    "pacientes": {
        "id": "pacientes",
        "label": "Pacientes",
        "path": "/pacientes",
        "icon": "Users",
        "category": "clinica",
        "description": "Gestión de pacientes de la clínica"
    },
    "importar_pacientes": {
        "id": "importar_pacientes",
        "label": "Importar Pacientes",
        "path": "/importar-pacientes",
        "icon": "Upload",
        "category": "clinica",
        "description": "Importación masiva de pacientes"
    },
    "evaluacion_oftalmologica": {
        "id": "evaluacion_oftalmologica",
        "label": "Evaluación Oftalmológica",
        "path": "/evaluacion-oftalmologica",
        "icon": "Eye",
        "category": "clinica",
        "description": "Evaluaciones y consultas oftalmológicas"
    },
    "sala_operaciones": {
        "id": "sala_operaciones",
        "label": "Sala de Operaciones",
        "path": "/sala-operaciones",
        "icon": "Syringe",
        "category": "clinica",
        "description": "Programación y gestión de cirugías"
    },
    "crm_cirugias": {
        "id": "crm_cirugias",
        "label": "CRM Cirugías",
        "path": "/crm-cirugias",
        "icon": "ClipboardList",
        "category": "clinica",
        "description": "Seguimiento de pacientes de cirugía"
    },
    "agenda": {
        "id": "agenda",
        "label": "Agenda",
        "path": "/agenda",
        "icon": "CalendarDays",
        "category": "clinica",
        "description": "Calendario de citas y eventos"
    },
    "medicos": {
        "id": "medicos",
        "label": "Médicos",
        "path": "/medicos",
        "icon": "Stethoscope",
        "category": "clinica",
        "description": "Gestión de médicos y especialistas"
    },
    # Módulo Óptica
    "optica_dashboard": {
        "id": "optica_dashboard",
        "label": "Dashboard Óptica",
        "path": "/optica/dashboard",
        "icon": "LayoutDashboard",
        "category": "optica",
        "description": "Panel de estadísticas de óptica"
    },
    "optica_armazones": {
        "id": "optica_armazones",
        "label": "Armazones",
        "path": "/optica/inventario",
        "icon": "Package",
        "category": "optica",
        "description": "Inventario de armazones"
    },
    "optica_lentes_contacto": {
        "id": "optica_lentes_contacto",
        "label": "Lentes de Contacto",
        "path": "/optica/lentes-contacto",
        "icon": "CircleDot",
        "category": "optica",
        "description": "Inventario de lentes de contacto"
    },
    "optica_tipos_lente": {
        "id": "optica_tipos_lente",
        "label": "Lentes Oftálmicos",
        "path": "/optica/tipos-lente",
        "icon": "Eye",
        "category": "optica",
        "description": "Catálogo de tipos de lentes"
    },
    "optica_pos": {
        "id": "optica_pos",
        "label": "Punto de Venta",
        "path": "/optica/punto-venta",
        "icon": "ShoppingCart",
        "category": "optica",
        "description": "Punto de venta de óptica"
    },
    "optica_cxc": {
        "id": "optica_cxc",
        "label": "Cuentas por Cobrar",
        "path": "/optica/cuentas-cobrar",
        "icon": "CreditCard",
        "category": "optica",
        "description": "Cuentas por cobrar de óptica"
    },
    "optica_compras": {
        "id": "optica_compras",
        "label": "Compras Óptica",
        "path": "/optica/compras",
        "icon": "Receipt",
        "category": "optica",
        "description": "Registro de compras de óptica"
    },
    # Módulo Finanzas
    "finanzas_pos": {
        "id": "finanzas_pos",
        "label": "Punto de Venta",
        "path": "/punto-venta",
        "icon": "Store",
        "category": "finanzas",
        "description": "Punto de venta y facturación"
    },
    "finanzas_caja": {
        "id": "finanzas_caja",
        "label": "Caja",
        "path": "/caja",
        "icon": "Wallet",
        "category": "finanzas",
        "description": "Control de caja y efectivo"
    },
    "finanzas_cxc": {
        "id": "finanzas_cxc",
        "label": "Cuentas por Cobrar",
        "path": "/cuentas-cobrar-finanzas",
        "icon": "CreditCard",
        "category": "finanzas",
        "description": "Cuentas por cobrar general"
    },
    "finanzas_gastos": {
        "id": "finanzas_gastos",
        "label": "Gastos",
        "path": "/gastos",
        "icon": "Receipt",
        "category": "finanzas",
        "description": "Registro y gestión de gastos"
    },
    "finanzas_pagos": {
        "id": "finanzas_pagos",
        "label": "Historial de Pagos",
        "path": "/historial-pagos",
        "icon": "History",
        "category": "finanzas",
        "description": "Historial de pagos realizados"
    },
    "finanzas_proveedores": {
        "id": "finanzas_proveedores",
        "label": "Proveedores",
        "path": "/configuracion/proveedores",
        "icon": "Truck",
        "category": "finanzas",
        "description": "Gestión de proveedores"
    },
    "finanzas_gastos_fijos": {
        "id": "finanzas_gastos_fijos",
        "label": "Gastos Fijos",
        "path": "/configuracion/gastos-fijos",
        "icon": "CalendarClock",
        "category": "finanzas",
        "description": "Configuración de gastos fijos recurrentes"
    },
    "finanzas_autorizaciones": {
        "id": "finanzas_autorizaciones",
        "label": "Autorizaciones",
        "path": "/autorizaciones-pendientes",
        "icon": "ClipboardCheck",
        "category": "finanzas",
        "description": "Autorizaciones de pagos pendientes"
    },
    # Módulo Inventario
    "inventario_panel": {
        "id": "inventario_panel",
        "label": "Panel Inventario",
        "path": "/inventario",
        "icon": "LayoutDashboard",
        "category": "inventario",
        "description": "Panel principal de inventario"
    },
    "inventario_bodegas": {
        "id": "inventario_bodegas",
        "label": "Bodegas",
        "path": "/inventario/bodegas",
        "icon": "Warehouse",
        "category": "inventario",
        "description": "Gestión de bodegas/almacenes"
    },
    "inventario_productos": {
        "id": "inventario_productos",
        "label": "Productos",
        "path": "/inventario/productos",
        "icon": "Package",
        "category": "inventario",
        "description": "Catálogo de productos"
    },
    "inventario_lotes": {
        "id": "inventario_lotes",
        "label": "Lotes y Vencimientos",
        "path": "/inventario/lotes",
        "icon": "AlertTriangle",
        "category": "inventario",
        "description": "Control de lotes y fechas de vencimiento"
    },
    "inventario_kardex": {
        "id": "inventario_kardex",
        "label": "Kardex",
        "path": "/inventario/movimientos",
        "icon": "FileText",
        "category": "inventario",
        "description": "Movimientos de inventario"
    },
    "inventario_categorias": {
        "id": "inventario_categorias",
        "label": "Categorías",
        "path": "/inventario/categorias",
        "icon": "Tag",
        "category": "inventario",
        "description": "Categorías de productos"
    },
    "inventario_rentabilidad": {
        "id": "inventario_rentabilidad",
        "label": "Rentabilidad",
        "path": "/inventario/rentabilidad",
        "icon": "PieChart",
        "category": "inventario",
        "description": "Reporte de rentabilidad por categoría"
    },
    "inventario_sociedades": {
        "id": "inventario_sociedades",
        "label": "Sociedades",
        "path": "/sociedades",
        "icon": "Users",
        "category": "inventario",
        "description": "Control de consumos para sociedades médicas"
    },
    "inventario_pos": {
        "id": "inventario_pos",
        "label": "Punto de Venta",
        "path": "/punto-venta",
        "icon": "ShoppingCart",
        "category": "inventario",
        "description": "Punto de venta general"
    },
    # Módulo IGSS
    "unidades_igss": {
        "id": "unidades_igss",
        "label": "Unidades IGSS",
        "path": "/igss/unidades",
        "icon": "Building",
        "category": "igss",
        "description": "Catálogo de unidades del IGSS"
    },
    "gestion_nog": {
        "id": "gestion_nog",
        "label": "NOG",
        "path": "/igss/nog",
        "icon": "ClipboardList",
        "category": "igss",
        "description": "Ingreso y gestión central de todos los NOG del IGSS"
    },
    # Configuración
    "gestion_usuarios": {
        "id": "gestion_usuarios",
        "label": "Gestión de Usuarios",
        "path": "/usuarios",
        "icon": "Users",
        "category": "configuracion",
        "description": "Administración de usuarios del sistema"
    },
    "audit_logs": {
        "id": "audit_logs",
        "label": "Logs de Auditoría",
        "path": "/audit-logs",
        "icon": "FileText",
        "category": "configuracion",
        "description": "Registro de actividades del sistema"
    },
    "alertas_seguridad": {
        "id": "alertas_seguridad",
        "label": "Alertas de Seguridad",
        "path": "/alertas-seguridad",
        "icon": "Shield",
        "category": "configuracion",
        "description": "Panel de alertas de seguridad"
    }
}

# Configuración por defecto de menús por rol
DEFAULT_MENU_CONFIG = {
    "superadmin": list(AVAILABLE_MENUS.keys()),  # Todos los menús
    "admin": [
        "pacientes", "importar_pacientes", "evaluacion_oftalmologica",
        "sala_operaciones", "crm_cirugias", "agenda", "medicos",
        "finanzas_pos", "finanzas_caja", "finanzas_cxc", "finanzas_gastos", 
        "finanzas_pagos", "finanzas_proveedores", "finanzas_gastos_fijos", "finanzas_autorizaciones",
        "inventario_panel", "inventario_bodegas", "inventario_productos",
        "inventario_lotes", "inventario_kardex", "inventario_categorias", "inventario_pos",
        "inventario_sociedades", "gestion_nog"
    ],
    "usuario": [
        "pacientes", "evaluacion_oftalmologica", "agenda",
        "inventario_panel", "inventario_productos", "inventario_lotes"
    ],
    "optica": [
        "pacientes", "optica_armazones", "optica_lentes_contacto",
        "optica_tipos_lente", "optica_pos", "optica_cxc", "optica_compras"
    ],
    "administrador_igss": [
        "pacientes", "unidades_igss", "gestion_nog"
    ],
    "medico": [
        "pacientes", "agenda", "evaluacion_oftalmologica"
    ]
}

# Categorías de menús
MENU_CATEGORIES = {
    "principal": {"label": "Principal", "order": 1},
    "clinica": {"label": "Clínica", "order": 2},
    "optica": {"label": "Óptica", "order": 3},
    "finanzas": {"label": "Finanzas", "order": 4},
    "inventario": {"label": "Inventario", "order": 5},
    "igss": {"label": "IGSS", "order": 6},
    "configuracion": {"label": "Configuración", "order": 7}
}


class MenuConfigUpdate(BaseModel):
    role: str
    enabled_menus: List[str]


class MenuConfigResponse(BaseModel):
    role: str
    enabled_menus: List[str]
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


@router.get("/available-menus")
async def get_available_menus(current_user: dict = Depends(require_permission("manage_users"))):
    """Obtener lista de todos los menús disponibles organizados por categoría"""
    menus_by_category = {}
    
    for menu_id, menu_data in AVAILABLE_MENUS.items():
        category = menu_data["category"]
        if category not in menus_by_category:
            menus_by_category[category] = {
                "category_id": category,
                "category_label": MENU_CATEGORIES.get(category, {}).get("label", category),
                "order": MENU_CATEGORIES.get(category, {}).get("order", 99),
                "menus": []
            }
        menus_by_category[category]["menus"].append({
            "id": menu_id,
            **menu_data
        })
    
    # Ordenar categorías
    sorted_categories = sorted(menus_by_category.values(), key=lambda x: x["order"])
    
    return {
        "categories": sorted_categories,
        "roles": await _get_configurable_roles()
    }


@router.get("/role/{role}")
async def get_menu_config_for_role(
    role: str,
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Obtener configuración de menús para un rol específico"""
    if role not in await _get_configurable_roles():
        raise HTTPException(status_code=400, detail="Rol no válido")
    
    # Buscar configuración personalizada en la base de datos
    config = await db.menu_configurations.find_one({"role": role})
    
    if config:
        return MenuConfigResponse(
            role=role,
            enabled_menus=config.get("enabled_menus", []),
            updated_at=config.get("updated_at"),
            updated_by=config.get("updated_by")
        )
    
    # Si no hay configuración personalizada, usar la por defecto
    return MenuConfigResponse(
        role=role,
        enabled_menus=DEFAULT_MENU_CONFIG.get(role, []),
        updated_at=None,
        updated_by=None
    )


@router.get("/all-roles")
async def get_all_menu_configs(current_user: dict = Depends(require_permission("manage_users"))):
    """Obtener configuración de menús para todos los roles"""
    configs = {}
    
    for role in await _get_configurable_roles():
        # Buscar configuración personalizada
        config = await db.menu_configurations.find_one({"role": role})
        
        if config:
            configs[role] = {
                "enabled_menus": config.get("enabled_menus", []),
                "updated_at": config.get("updated_at"),
                "updated_by": config.get("updated_by"),
                "is_custom": True
            }
        else:
            configs[role] = {
                "enabled_menus": DEFAULT_MENU_CONFIG.get(role, []),
                "updated_at": None,
                "updated_by": None,
                "is_custom": False
            }
    
    return configs


@router.put("/role/{role}")
async def update_menu_config_for_role(
    role: str,
    config: MenuConfigUpdate,
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Actualizar configuración de menús para un rol"""
    if role not in await _get_configurable_roles():
        raise HTTPException(status_code=400, detail="Rol no válido")
    
    if role != config.role:
        raise HTTPException(status_code=400, detail="El rol en la URL no coincide con el del body")
    
    # Validar que los menús existan
    invalid_menus = [m for m in config.enabled_menus if m not in AVAILABLE_MENUS]
    if invalid_menus:
        raise HTTPException(status_code=400, detail=f"Menús no válidos: {invalid_menus}")
    
    # SuperAdmin siempre debe tener acceso a gestión de usuarios
    if role == "superadmin" and "gestion_usuarios" not in config.enabled_menus:
        config.enabled_menus.append("gestion_usuarios")
    
    # Actualizar o insertar configuración
    update_data = {
        "role": role,
        "enabled_menus": config.enabled_menus,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user.get("username", "system")
    }
    
    await db.menu_configurations.update_one(
        {"role": role},
        {"$set": update_data},
        upsert=True
    )
    
    return {
        "message": f"Configuración de menús actualizada para rol '{role}'",
        "config": update_data
    }


@router.post("/reset/{role}")
async def reset_menu_config_for_role(
    role: str,
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Restaurar configuración de menús por defecto para un rol"""
    if role not in await _get_configurable_roles():
        raise HTTPException(status_code=400, detail="Rol no válido")
    
    # Eliminar configuración personalizada
    await db.menu_configurations.delete_one({"role": role})
    
    return {
        "message": f"Configuración de menús restaurada a valores por defecto para rol '{role}'",
        "default_menus": DEFAULT_MENU_CONFIG.get(role, [])
    }


@router.get("/my-menus")
async def get_my_menus(current_user: dict = Depends(get_current_user)):
    """Obtener los menús habilitados para el usuario actual"""
    role = current_user.get("role", "usuario")
    
    # Buscar configuración personalizada
    config = await db.menu_configurations.find_one({"role": role})
    
    if config:
        enabled_menu_ids = config.get("enabled_menus", [])
    else:
        enabled_menu_ids = DEFAULT_MENU_CONFIG.get(role, [])
    
    # Obtener detalles de los menús habilitados
    enabled_menus = []
    for menu_id in enabled_menu_ids:
        if menu_id in AVAILABLE_MENUS:
            enabled_menus.append({
                "id": menu_id,
                **AVAILABLE_MENUS[menu_id]
            })
    
    # Organizar por categoría
    menus_by_category = {}
    for menu in enabled_menus:
        category = menu["category"]
        if category not in menus_by_category:
            menus_by_category[category] = {
                "category_id": category,
                "category_label": MENU_CATEGORIES.get(category, {}).get("label", category),
                "order": MENU_CATEGORIES.get(category, {}).get("order", 99),
                "menus": []
            }
        menus_by_category[category]["menus"].append(menu)
    
    sorted_categories = sorted(menus_by_category.values(), key=lambda x: x["order"])
    
    return {
        "role": role,
        "categories": sorted_categories,
        "menu_ids": enabled_menu_ids
    }
