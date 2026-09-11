# /app/backend/config/permissions.py
# Sistema de permisos por rol

from config.database import db

PERMISSIONS = {
    "superadmin": {
        "view_dashboard": True,
        "view_expenses": True,
        "view_payment_history": True,
        "view_due_payments": True,
        "create_expenses": True,
        "edit_expenses": True,
        "delete_expenses": True,
        "register_payments": True,
        "delete_payments": True,
        "manage_users": True,
        "view_user_management": True,
        "export_reports": True,
        "authorize_payments": True,
        "view_payment_authorizations": True,
        # Permisos de Pacientes
        "view_patients": True,
        "create_patients": True,
        "edit_patients": True,
        "delete_patients": True,
        "manage_igss_units": True,
        "import_patients": True,
        "export_patients": True,
        # Permisos de Óptica (SuperAdmin tiene acceso total)
        "view_optica": True,
        "manage_optica_inventory": True,
        "manage_optica_sales": True,
        "manage_optica_expenses": True,
        "view_optica_reports": True,
        "manage_doctors": True,
        "manage_lens_catalog": True
    },
    "admin": {
        "view_dashboard": True,
        "view_expenses": True,
        "view_payment_history": True,
        "view_due_payments": True,
        "create_expenses": True,
        "edit_expenses": True,
        "delete_expenses": False,
        "register_payments": True,
        "delete_payments": False,
        "manage_users": False,
        "view_user_management": False,
        "export_reports": True,
        "authorize_payments": False,
        "view_payment_authorizations": True,
        "execute_payment_authorizations": True,
        # Permisos de Pacientes
        "view_patients": True,
        "create_patients": True,
        "edit_patients": True,
        "delete_patients": False,
        "manage_igss_units": False,
        "import_patients": True,
        "export_patients": True,
        # Sin acceso a Óptica
        "view_optica": False,
        "manage_optica_inventory": False,
        "manage_optica_sales": False,
        "manage_optica_expenses": False,
        "view_optica_reports": False,
        "manage_doctors": False,
        "manage_lens_catalog": False
    },
    "usuario": {
        "view_dashboard": True,
        "view_expenses": True,
        "view_payment_history": True,
        "view_due_payments": True,
        "create_expenses": False,
        "edit_expenses": False,
        "delete_expenses": False,
        "register_payments": False,
        "delete_payments": False,
        "manage_users": False,
        "view_user_management": False,
        "export_reports": False,
        "authorize_payments": False,
        "view_payment_authorizations": False,
        "execute_payment_authorizations": False,
        # Permisos de Pacientes (solo lectura)
        "view_patients": True,
        "create_patients": False,
        "edit_patients": False,
        "delete_patients": False,
        "manage_igss_units": False,
        "import_patients": False,
        "export_patients": False,
        # Sin acceso a Óptica
        "view_optica": False,
        "manage_optica_inventory": False,
        "manage_optica_sales": False,
        "manage_optica_expenses": False,
        "view_optica_reports": False,
        "manage_doctors": False,
        "manage_lens_catalog": False
    },
    "optica": {
        # Sin acceso al módulo de finanzas general
        "view_dashboard": False,
        "view_expenses": False,
        "view_payment_history": False,
        "view_due_payments": False,
        "create_expenses": False,
        "edit_expenses": False,
        "delete_expenses": False,
        "register_payments": False,
        "delete_payments": False,
        "manage_users": False,
        "view_user_management": False,
        "export_reports": False,
        "authorize_payments": False,
        "view_payment_authorizations": False,
        "execute_payment_authorizations": False,
        # Acceso a Pacientes (para seleccionar clientes)
        "view_patients": True,
        "create_patients": True,
        "edit_patients": True,
        "delete_patients": False,
        "manage_igss_units": False,
        "import_patients": False,
        "export_patients": False,
        # Acceso a Proveedores (solo ver y crear)
        "view_suppliers": True,
        "create_suppliers": True,
        "edit_suppliers": False,
        "delete_suppliers": False,
        # Permisos completos de Óptica
        "view_optica": True,
        "manage_optica_inventory": True,
        "manage_optica_sales": True,
        "manage_optica_expenses": True,
        "view_optica_reports": True,
        "manage_doctors": True,
        "manage_lens_catalog": True
    }
}

# SEC-003: Permisos de módulos clínicos (inventario, POS/ventas, caja)
_MODULE_PERMS = {
    "superadmin": {"view_inventory": True, "manage_inventory": True, "manage_sales": True, "manage_caja": True},
    "admin": {"view_inventory": True, "manage_inventory": True, "manage_sales": True, "manage_caja": True},
    "usuario": {"view_inventory": False, "manage_inventory": False, "manage_sales": False, "manage_caja": False},
    "optica": {"view_inventory": False, "manage_inventory": False, "manage_sales": False, "manage_caja": False},
}
for _rol, _perms_mod in _MODULE_PERMS.items():
    PERMISSIONS.setdefault(_rol, {}).update(_perms_mod)


def get_permissions(role: str) -> dict:
    """Obtener permisos para un rol específico"""
    return PERMISSIONS.get(role, PERMISSIONS["usuario"])


async def resolve_permissions(role: str) -> dict:
    """SEC-003/RBAC: Resuelve los permisos efectivos de un rol.
    - superadmin siempre tiene todos los permisos.
    - roles personalizados y personalizaciones de roles de sistema se leen de db.roles.
    - roles de sistema sin personalización usan la matriz por defecto.
    - rol desconocido => sin permisos (deny by default)."""
    if role == "superadmin":
        return PERMISSIONS["superadmin"]
    try:
        custom = await db.roles.find_one({"name": role})
    except Exception:
        custom = None
    if custom and isinstance(custom.get("permissions"), dict) and custom["permissions"]:
        return custom["permissions"]
    if role in PERMISSIONS:
        return PERMISSIONS[role]
    return {}
