# Auditoría de Seguridad AppSec — NovaVision ERP (Junio 2026)

**Alcance:** Blindaje de accesos y permisos (autenticación, autorización, RBAC) antes de producción.
**Stack:** FastAPI + React + MongoDB. **Ambiente auditado:** PREVIEW (`ENVIRONMENT=development`).

## Resumen ejecutivo
La auditoría inicial dio veredicto **NO APTO PARA PRODUCCIÓN** por un hallazgo crítico de forja de tokens y varios fallos de autorización. Tras la remediación aprobada por el usuario (todo excepto rotar el secreto JWT), los controles de acceso quedaron blindados y validados por pruebas automatizadas (25/25 pytest + navegación E2E).

## Hallazgos y estado de remediación

| ID | Severidad | Hallazgo | Estado |
|----|-----------|----------|--------|
| SEC-001 | 🔴 CRÍTICO | Secreto JWT conocido/publicado y fallbacks embebidos en código (`config/database.py`, `utils/auth.py`). | **CORREGIDO.** Fallbacks eliminados; guarda de arranque ABORTA en producción si el secreto es conocido/corto; y el **secreto JWT fue ROTADO** a un valor aleatorio de 88 caracteres (los tokens firmados con el secreto anterior son rechazados con 401). Nota: la rotación invalidó todas las sesiones activas (re-login requerido). |
| SEC-002 | 🟠 ALTO | Laboratorio de Pruebas sin autenticación (exponía credenciales, purga y generación de datos). | **Corregido.** Nueva dependencia `verificar_acceso_laboratorio` = SuperAdmin autenticado + no-producción, aplicada a TODOS los endpoints. |
| SEC-003 | 🟠 ALTO | BFLA: módulos clínicos (inventario, POS/ventas, caja) solo exigían estar logueado. | **Corregido.** `require_permission`/dependencias por módulo: `view_inventory`/`manage_inventory` (inventario), `manage_sales` (POS), `manage_caja` (caja). Matriz: superadmin/admin con acceso; usuario/optica sin acceso. |
| SEC-004 | 🟡 MEDIO | Logout inefectivo (blacklist en memoria) y `token_version` nunca verificado. | **Corregido.** Blacklist persistente unificada en `db.token_blacklist` (servidor + routers modulares); `token_version` incluido en el token y verificado en `get_current_user`; backfill de `token_version` para usuarios legados. |
| SEC-005 | 🟡 MEDIO | Usuario `optica` sembrado sin `must_change_password`. | **Corregido** para nuevos despliegues (seed agrega `must_change_password`, `token_version`, control de intentos). Usuarios existentes no se alteran. |
| RBAC gap | 🟡 MEDIO | Roles personalizados caían silenciosamente a permisos de `usuario`; `POST /api/users` bloqueaba roles personalizados por regex. | **Corregido.** `resolve_permissions()` async lee `db.roles` (deny-by-default para rol desconocido); `UserBase.role` sin regex + validación contra roles existentes en create/update. |

## Endurecimiento pendiente (P3, opcional)
- Rotar el valor de `JWT_SECRET` a un aleatorio de 64+ chars antes de producción (invalida sesiones).
- Token JWT en `localStorage` (frontend): considerar cookie HttpOnly/SameSite.
- `ENABLE_DOCS=true` expone `/api/docs`: deshabilitar en producción.
- Búsquedas con `$regex` sobre input de usuario: anclar/escapar para evitar ReDoS.

## Validación
- Backend: 25/25 pytest AppSec (`/app/backend/tests/test_appsec_audit_iter48.py`), reporte `/app/test_reports/iteration_48.json`.
- Verificado por curl: SEC-002/003/004 y RBAC de roles personalizados.
- Frontend: navegación E2E limpia para SuperAdmin (inventario, caja, POS, roles) y Óptica (su módulo).

## Nota fuera de alcance
`GET /api/patients` devolvía 500 (ResponseValidationError) por pacientes con campos incompletos. **CORREGIDO (2026-06):** los campos del modelo `PatientResponse` que podían faltar en documentos antiguos se hicieron opcionales con valores por defecto (sin mutar datos). Verificado: la lista de pacientes responde 200.
