# /app/backend/routes/roles.py
# CRUD de roles personalizados con permisos dinámicos

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone
from bson import ObjectId

from config.database import db
from config.permissions import PERMISSIONS
from .auth import get_current_user, require_permission

router = APIRouter(prefix="/roles", tags=["Roles"])

# Roles del sistema que no pueden eliminarse
SYSTEM_ROLES = ["superadmin", "admin", "usuario", "optica"]

# Lista de todos los permisos disponibles organizados por categoría
AVAILABLE_PERMISSIONS = {
    "dashboard": {
        "label": "Dashboard",
        "permissions": [
            {"id": "view_dashboard", "label": "Ver Dashboard", "description": "Acceso al panel principal"},
        ]
    },
    "finanzas": {
        "label": "Finanzas",
        "permissions": [
            {"id": "view_expenses", "label": "Ver Gastos", "description": "Visualizar registro de gastos"},
            {"id": "create_expenses", "label": "Crear Gastos", "description": "Registrar nuevos gastos"},
            {"id": "edit_expenses", "label": "Editar Gastos", "description": "Modificar gastos existentes"},
            {"id": "delete_expenses", "label": "Eliminar Gastos", "description": "Eliminar registros de gastos"},
            {"id": "view_payment_history", "label": "Ver Historial de Pagos", "description": "Acceso al historial de pagos"},
            {"id": "view_due_payments", "label": "Ver Pagos Pendientes", "description": "Ver pagos por vencer"},
            {"id": "register_payments", "label": "Registrar Pagos", "description": "Registrar pagos a proveedores"},
            {"id": "delete_payments", "label": "Eliminar Pagos", "description": "Eliminar registros de pagos"},
            {"id": "authorize_payments", "label": "Autorizar Pagos", "description": "Aprobar pagos pendientes"},
            {"id": "view_payment_authorizations", "label": "Ver Autorizaciones", "description": "Ver solicitudes de autorización"},
            {"id": "execute_payment_authorizations", "label": "Ejecutar Autorizaciones", "description": "Procesar autorizaciones aprobadas"},
            {"id": "export_reports", "label": "Exportar Reportes", "description": "Descargar reportes financieros"},
        ]
    },
    "pacientes": {
        "label": "Pacientes",
        "permissions": [
            {"id": "view_patients", "label": "Ver Pacientes", "description": "Visualizar lista de pacientes"},
            {"id": "create_patients", "label": "Crear Pacientes", "description": "Registrar nuevos pacientes"},
            {"id": "edit_patients", "label": "Editar Pacientes", "description": "Modificar datos de pacientes"},
            {"id": "delete_patients", "label": "Eliminar Pacientes", "description": "Eliminar registros de pacientes"},
            {"id": "import_patients", "label": "Importar Pacientes", "description": "Importación masiva de pacientes"},
            {"id": "export_patients", "label": "Exportar Pacientes", "description": "Exportar datos de pacientes"},
        ]
    },
    "administracion": {
        "label": "Administración",
        "permissions": [
            {"id": "manage_users", "label": "Gestionar Usuarios", "description": "CRUD completo de usuarios"},
            {"id": "view_user_management", "label": "Ver Gestión de Usuarios", "description": "Acceso al módulo de usuarios"},
            {"id": "manage_igss_units", "label": "Gestionar Unidades IGSS", "description": "Administrar catálogo IGSS"},
            {"id": "manage_doctors", "label": "Gestionar Médicos", "description": "Administrar catálogo de médicos"},
            {"id": "manage_roles", "label": "Gestionar Roles", "description": "CRUD de roles y permisos"},
        ]
    },
    "optica": {
        "label": "Óptica",
        "permissions": [
            {"id": "view_optica", "label": "Ver Módulo Óptica", "description": "Acceso al módulo de óptica"},
            {"id": "manage_optica_inventory", "label": "Gestionar Inventario Óptica", "description": "CRUD de inventario óptico"},
            {"id": "manage_optica_sales", "label": "Gestionar Ventas Óptica", "description": "Registrar ventas de óptica"},
            {"id": "manage_optica_expenses", "label": "Gestionar Gastos Óptica", "description": "Registrar gastos de óptica"},
            {"id": "view_optica_reports", "label": "Ver Reportes Óptica", "description": "Acceso a reportes de óptica"},
            {"id": "manage_lens_catalog", "label": "Gestionar Catálogo Lentes", "description": "Administrar tipos de lentes"},
        ]
    },
    "inventario": {
        "label": "Inventario",
        "permissions": [
            {"id": "view_inventory", "label": "Ver Inventario", "description": "Acceso al módulo de inventario"},
            {"id": "manage_inventory", "label": "Gestionar Inventario", "description": "CRUD de productos"},
            {"id": "manage_warehouses", "label": "Gestionar Bodegas", "description": "Administrar almacenes"},
            {"id": "view_kardex", "label": "Ver Kardex", "description": "Acceso a movimientos de inventario"},
            {"id": "manage_categories", "label": "Gestionar Categorías", "description": "Administrar categorías de productos"},
            {"id": "view_profitability", "label": "Ver Rentabilidad", "description": "Acceso a reportes de rentabilidad"},
        ]
    },
    "proveedores": {
        "label": "Proveedores",
        "permissions": [
            {"id": "view_suppliers", "label": "Ver Proveedores", "description": "Visualizar lista de proveedores"},
            {"id": "create_suppliers", "label": "Crear Proveedores", "description": "Registrar nuevos proveedores"},
            {"id": "edit_suppliers", "label": "Editar Proveedores", "description": "Modificar datos de proveedores"},
            {"id": "delete_suppliers", "label": "Eliminar Proveedores", "description": "Eliminar registros de proveedores"},
        ]
    }
}


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    display_name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    permissions: Dict[str, bool] = Field(default_factory=dict)
    color: Optional[str] = "gray"  # Color para badge en UI


class RoleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: Dict[str, bool]
    color: str
    is_system: bool
    is_active: bool
    user_count: int = 0
    created_at: str
    updated_at: Optional[str] = None


@router.get("/available-permissions")
async def get_available_permissions(
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Obtener lista de todos los permisos disponibles organizados por categoría"""
    return {
        "categories": AVAILABLE_PERMISSIONS,
        "total_permissions": sum(len(cat["permissions"]) for cat in AVAILABLE_PERMISSIONS.values())
    }


@router.get("/")
async def get_all_roles(
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Obtener todos los roles (sistema + personalizados)"""
    roles = []
    
    # Obtener conteo de usuarios por rol en una sola query (optimización)
    user_counts_pipeline = [
        {"$group": {"_id": "$role", "count": {"$sum": 1}}}
    ]
    user_counts_cursor = db.users.aggregate(user_counts_pipeline)
    user_counts_list = await user_counts_cursor.to_list(100)
    user_counts = {item["_id"]: item["count"] for item in user_counts_list}
    
    # 1. Agregar roles del sistema (desde PERMISSIONS)
    for role_name in SYSTEM_ROLES:
        # Buscar si hay personalización en DB
        custom_config = await db.roles.find_one({"name": role_name})
        
        display_names = {
            "superadmin": "Super Administrador",
            "admin": "Administrador", 
            "usuario": "Usuario",
            "optica": "Óptica"
        }
        
        colors = {
            "superadmin": "red",
            "admin": "blue",
            "usuario": "gray",
            "optica": "purple"
        }
        
        roles.append({
            "id": role_name,
            "name": role_name,
            "display_name": custom_config.get("display_name") or display_names.get(role_name, role_name) if custom_config else display_names.get(role_name, role_name),
            "description": custom_config.get("description") or f"Rol de sistema: {role_name}" if custom_config else f"Rol de sistema: {role_name}",
            "permissions": custom_config.get("permissions") if custom_config else PERMISSIONS.get(role_name, {}),
            "color": custom_config.get("color") or colors.get(role_name, "gray") if custom_config else colors.get(role_name, "gray"),
            "is_system": True,
            "is_active": True,
            "user_count": user_counts.get(role_name, 0),
            "created_at": custom_config.get("created_at") if custom_config else None,
            "updated_at": custom_config.get("updated_at") if custom_config else None
        })
    
    # 2. Agregar roles personalizados desde la base de datos
    custom_roles = await db.roles.find({"name": {"$nin": SYSTEM_ROLES}}).to_list(100)
    
    for role in custom_roles:
        roles.append({
            "id": str(role["_id"]),
            "name": role["name"],
            "display_name": role.get("display_name", role["name"]),
            "description": role.get("description", ""),
            "permissions": role.get("permissions", {}),
            "color": role.get("color", "gray"),
            "is_system": False,
            "is_active": role.get("is_active", True),
            "user_count": user_counts.get(role["name"], 0),
            "created_at": role.get("created_at"),
            "updated_at": role.get("updated_at")
        })
    
    return roles


@router.get("/{role_name}")
async def get_role(
    role_name: str,
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Obtener detalle de un rol específico"""
    # Verificar si es un rol del sistema
    if role_name in SYSTEM_ROLES:
        custom_config = await db.roles.find_one({"name": role_name})
        user_count = await db.users.count_documents({"role": role_name})
        
        display_names = {
            "superadmin": "Super Administrador",
            "admin": "Administrador",
            "usuario": "Usuario", 
            "optica": "Óptica"
        }
        
        return {
            "id": role_name,
            "name": role_name,
            "display_name": custom_config.get("display_name") if custom_config else display_names.get(role_name),
            "description": custom_config.get("description") if custom_config else f"Rol de sistema: {role_name}",
            "permissions": custom_config.get("permissions") if custom_config else PERMISSIONS.get(role_name, {}),
            "color": custom_config.get("color") if custom_config else "gray",
            "is_system": True,
            "is_active": True,
            "user_count": user_count
        }
    
    # Buscar rol personalizado
    role = await db.roles.find_one({"name": role_name})
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    user_count = await db.users.count_documents({"role": role_name})
    
    return {
        "id": str(role["_id"]),
        "name": role["name"],
        "display_name": role.get("display_name", role["name"]),
        "description": role.get("description", ""),
        "permissions": role.get("permissions", {}),
        "color": role.get("color", "gray"),
        "is_system": False,
        "is_active": role.get("is_active", True),
        "user_count": user_count
    }


@router.post("/")
async def create_role(
    role_data: RoleCreate,
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Crear un nuevo rol personalizado"""
    # Normalizar nombre (lowercase, sin espacios)
    role_name = role_data.name.lower().replace(" ", "_")
    
    # Verificar que no exista
    if role_name in SYSTEM_ROLES:
        raise HTTPException(status_code=400, detail="No se puede usar el nombre de un rol del sistema")
    
    existing = await db.roles.find_one({"name": role_name})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")
    
    now = datetime.now(timezone.utc).isoformat()
    
    new_role = {
        "name": role_name,
        "display_name": role_data.display_name,
        "description": role_data.description,
        "permissions": role_data.permissions,
        "color": role_data.color or "gray",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "created_by": current_user.get("username", "system")
    }
    
    result = await db.roles.insert_one(new_role)
    
    return {
        "message": f"Rol '{role_data.display_name}' creado exitosamente",
        "role": {
            "id": str(result.inserted_id),
            "name": role_name,
            **{k: v for k, v in new_role.items() if k != "_id"}
        }
    }


@router.put("/{role_name}")
async def update_role(
    role_name: str,
    role_data: RoleUpdate,
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Actualizar un rol existente"""
    now = datetime.now(timezone.utc).isoformat()
    
    update_fields = {"updated_at": now, "updated_by": current_user.get("username", "system")}
    
    if role_data.display_name is not None:
        update_fields["display_name"] = role_data.display_name
    if role_data.description is not None:
        update_fields["description"] = role_data.description
    if role_data.permissions is not None:
        update_fields["permissions"] = role_data.permissions
    if role_data.color is not None:
        update_fields["color"] = role_data.color
    if role_data.is_active is not None and role_name not in SYSTEM_ROLES:
        update_fields["is_active"] = role_data.is_active
    
    # Para roles del sistema, crear/actualizar registro en DB para personalización
    if role_name in SYSTEM_ROLES:
        await db.roles.update_one(
            {"name": role_name},
            {"$set": update_fields},
            upsert=True
        )
        return {"message": f"Rol '{role_name}' actualizado exitosamente"}
    
    # Para roles personalizados
    result = await db.roles.update_one(
        {"name": role_name},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    return {"message": f"Rol '{role_name}' actualizado exitosamente"}


@router.delete("/{role_name}")
async def delete_role(
    role_name: str,
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Eliminar un rol personalizado"""
    # No permitir eliminar roles del sistema
    if role_name in SYSTEM_ROLES:
        raise HTTPException(status_code=400, detail="No se pueden eliminar roles del sistema")
    
    # Verificar que no haya usuarios con este rol
    user_count = await db.users.count_documents({"role": role_name})
    if user_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar el rol porque hay {user_count} usuario(s) asignado(s)"
        )
    
    # Obtener datos del rol antes de eliminarlo para el log de auditoría
    role_data = await db.roles.find_one({"name": role_name})
    
    result = await db.roles.delete_one({"name": role_name})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    # También eliminar configuración de menús para este rol
    await db.menu_configurations.delete_one({"role": role_name})
    
    # Registrar en log de auditoría
    audit_entry = {
        "action": "role_deleted",
        "role_name": role_name,
        "role_display_name": role_data.get("display_name", role_name) if role_data else role_name,
        "deleted_by": current_user.get("username", "system"),
        "deleted_at": datetime.now(timezone.utc).isoformat(),
        "role_data_backup": {
            "permissions": role_data.get("permissions", {}) if role_data else {},
            "description": role_data.get("description", "") if role_data else "",
            "color": role_data.get("color", "gray") if role_data else "gray"
        }
    }
    await db.audit_logs.insert_one(audit_entry)
    
    return {"message": f"Rol '{role_name}' eliminado exitosamente"}


@router.post("/{role_name}/reset-permissions")
async def reset_role_permissions(
    role_name: str,
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Restaurar permisos por defecto de un rol del sistema"""
    if role_name not in SYSTEM_ROLES:
        raise HTTPException(status_code=400, detail="Solo se pueden restaurar permisos de roles del sistema")
    
    # Eliminar personalización de la DB
    await db.roles.delete_one({"name": role_name})
    
    return {
        "message": f"Permisos del rol '{role_name}' restaurados a valores por defecto",
        "default_permissions": PERMISSIONS.get(role_name, {})
    }


@router.get("/{role_name}/users")
async def get_role_users(
    role_name: str,
    current_user: dict = Depends(require_permission("manage_users"))
):
    """Obtener lista de usuarios con un rol específico"""
    users = await db.users.find(
        {"role": role_name},
        {"_id": 0, "password": 0}
    ).to_list(100)
    
    return {
        "role": role_name,
        "user_count": len(users),
        "users": users
    }
