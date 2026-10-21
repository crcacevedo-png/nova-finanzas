# CHANGELOG — NovaVisión ERP

## 2026-06 — Fix: el NOG no se guardaba al editar un paciente IGSS
**Problema reportado:** "al asignar el NOG al momento de ingresar al paciente, no lo está guardando".

**Causa raíz:** Al **editar** un paciente IGSS con NOG del catálogo, `NogSelector` renderiza primero un `<Input>` (mientras carga el catálogo) y luego cambia a un `<Select>` de Radix v2 con valor preseleccionado. Radix dispara `onValueChange('')` al montar, lo que ejecutaba `handleSelect('')` → `onChange('')`, borrando `formData.igss_nog`. El PUT enviaba `igss_nog:''` y el backend sobreescribía el NOG. (Crear sí funcionaba.)

**Corrección (`/app/frontend/src/components/NogSelector.js`):** Se agregó `if (!val) return;` al inicio de `handleSelect` para ignorar el evento vacío espurio de Radix. El borrado explícito sigue disponible vía la opción "Otro (escribir NOG)".
**Extra (`/app/frontend/src/pages/Pacientes.js`):** El diálogo "Ver paciente" ahora muestra el NOG (`data-testid="view-patient-igss-nog"`).

**Verificado (testing_agent, iteration_81, 100%):** crear con NOG de catálogo y texto libre (200), editar sin cambios conserva el NOG en el PUT y en el detalle, repetido 2 veces.

**Pendiente relacionado (hallazgo del tester, NO corregido):** El diálogo "completar ficha / crear expediente" de la **Agenda** (`/app/frontend/src/pages/Agenda.js`) no tiene campo NOG; un paciente creado/completado desde la Agenda queda con `igss_nog=''`.


## 2026-06 — Permisos del rol "médico" en Evaluaciones Oftalmológicas
**Problema:** El rol `medico` tenía los permisos `view_evaluacion` y `manage_recetas` en `config/permissions.py`, pero los endpoints CRUD de `routes/evaluaciones.py` usaban listas de roles codificadas a mano `["superadmin", "admin", "usuario"]` que excluían a `medico`. Resultado: los médicos recibían 403 al crear/editar evaluaciones.

**Corrección (`/app/backend/routes/evaluaciones.py`):**
- Se agregó `medico` a los chequeos de rol de: crear (POST), editar (PUT), autoguardar (PATCH), historial médico del paciente (PUT), agregar medicamento desde receta, agregar a CRM de cirugías.
- Regla de propiedad confirmada con el usuario: **el médico solo puede editar las evaluaciones que él mismo creó** (`creado_por == current_user["id"]`). Aplicada en PUT `/{id}` y PATCH `/{id}/autoguardar` → 403 "Solo puede editar las evaluaciones que usted creó".
- Admin/SuperAdmin/Usuario conservan edición sobre cualquier evaluación. Eliminar evaluación sigue siendo solo SuperAdmin.

**Verificado vía curl (preview):** médico crea (200), edita la propia (200), bloqueado al editar/autoguardar ajena (403), superadmin edita cualquiera (200). Datos de prueba limpiados.

## Pendiente (de sesión previa, requiere despliegue a producción)
- Fix de Agenda con `paciente_id` obsoletos (endpoint `POST /api/agenda/admin/relink-citas`) y backups automáticos: corregido en preview, pendiente desplegar a producción y ejecutar el relink de las citas obsoletas.

## 2026-10-21 - PDF de Evaluación mejorado
- Logo de la clínica incrustado en el encabezado del PDF (backend/assets/logo_nova.png).
- Se agregan TODOS los datos del paciente del expediente (incluye DPI, teléfono, email, profesión, dirección, contacto de emergencia, institución y campos IGSS). Celdas con ajuste de texto (Paragraph) para evitar solapamientos.
- Eliminado el pie de página administrativo (sellado/creado por).
- Frontend: menú Imprimir ahora ofrece "Descargar PDF Completo" e "Imprimir PDF Completo" (abre el PDF y lanza el diálogo de impresión).
- Verificado con curl + render visual (2 páginas, logo y datos correctos).
