# CHANGELOG — NovaVisión ERP

## 2026-06 — Permisos del rol "médico" en Evaluaciones Oftalmológicas
**Problema:** El rol `medico` tenía los permisos `view_evaluacion` y `manage_recetas` en `config/permissions.py`, pero los endpoints CRUD de `routes/evaluaciones.py` usaban listas de roles codificadas a mano `["superadmin", "admin", "usuario"]` que excluían a `medico`. Resultado: los médicos recibían 403 al crear/editar evaluaciones.

**Corrección (`/app/backend/routes/evaluaciones.py`):**
- Se agregó `medico` a los chequeos de rol de: crear (POST), editar (PUT), autoguardar (PATCH), historial médico del paciente (PUT), agregar medicamento desde receta, agregar a CRM de cirugías.
- Regla de propiedad confirmada con el usuario: **el médico solo puede editar las evaluaciones que él mismo creó** (`creado_por == current_user["id"]`). Aplicada en PUT `/{id}` y PATCH `/{id}/autoguardar` → 403 "Solo puede editar las evaluaciones que usted creó".
- Admin/SuperAdmin/Usuario conservan edición sobre cualquier evaluación. Eliminar evaluación sigue siendo solo SuperAdmin.

**Verificado vía curl (preview):** médico crea (200), edita la propia (200), bloqueado al editar/autoguardar ajena (403), superadmin edita cualquiera (200). Datos de prueba limpiados.

## Pendiente (de sesión previa, requiere despliegue a producción)
- Fix de Agenda con `paciente_id` obsoletos (endpoint `POST /api/agenda/admin/relink-citas`) y backups automáticos: corregido en preview, pendiente desplegar a producción y ejecutar el relink de las citas obsoletas.
