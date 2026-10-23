# PRD - NovaVision ERP Oftalmológico

## Descripción General
Sistema ERP completo para clínicas oftalmológicas con módulos de: Dashboard, Pacientes, Agenda, Evaluación Oftalmológica, Inventario FEFO, POS, Caja, CRM Cirugías, Óptica, y Laboratorio de Pruebas E2E.

## Estado Actual del Proyecto
**Última actualización**: 2026-06 (Sesión 41 — AV Binocular/Cerca en evaluación + institución en Pacientes Presentes)

### Sesión 41 — Campos AV Binocular / AV Cerca + Institución en "Pacientes Presentes" (2026-06)
- ✅ **AV Binocular y AV Cerca** (`EvaluacionOftalmologica.js` + `models/evaluacion_oftalmologica.py`): debajo de "Agudeza Visual" (filas Sin/Con Corrección) se agregaron dos campos de texto libre de un solo cuadro cada uno — `examen-av-binocular` y `examen-av-cerca` (ej. "20/25", "J2"). Nuevos campos de modelo `av_binocular`, `av_cerca`. Persisten al guardar/recargar.
- ✅ **Institución en "Mis Pacientes Presentes"** (`Agenda.js` `PacientePresenteCard` + backend `/presentes` y `/mi-dia`): cada tarjeta de paciente presente ahora muestra el badge de institución (verde "IGSS" u otra etiqueta / "Sin institución") junto al tipo de cita, igual que el Tablero del Día. `PacientePresenteResponse` incluye `referral_institution` y `referral_institution_label`; `/presentes` ahora llama `_enriquecer_instituciones`. data-testid `presente-institucion-badge-{cita_id}`.
- ✅ **Verificado**: testing agent `iteration_91.json` 100% (ambos campos persisten; badge IGSS en tarjetas presentes; sin regresión en flujo Iniciar/Atendida/Deshacer) + curl (round-trip AV y /presentes con institución). Sin bugs.
- **Nota**: AV Binocular/Cerca aún NO se incluyen en el PDF del reporte (no solicitado); posible mejora futura.
- ⚠️ Requiere redespliegue para producción.

### Sesión 40 — Edición de evaluaciones para Administrador IGSS + ícono de evaluación en Pacientes (2026-06)
- ✅ **El Administrador IGSS ahora puede CREAR/EDITAR evaluaciones oftalmológicas** (no solo revisar). Se otorgó el permiso `view_evaluacion` al rol `administrador_igss` (`server.py`: añadido al seed + **migración idempotente** que actualiza el rol existente en cada arranque → aplica también en producción). Además se corrigió `routes/evaluaciones.py`: las **6 verificaciones de rol hardcodeadas** (crear, editar, autoguardado, antecedentes/medicamentos, agregar medicamento de receta, agregar a CRM cirugías) ahora incluyen `administrador_igss` (antes devolvían 403 al guardar).
- ✅ **Ícono de evaluación visible en Pacientes para el rol IGSS** (`Pacientes.js`): `canCreateEvaluacion` pasó de una lista de roles fija a `hasPermission('view_evaluacion')` (equivalente para admin/usuario/medico, y ahora incluye administrador_igss).
- ✅ **Tipo de Compra en el PDF confirmado con foto**: el reporte de pacientes IGSS muestra "IGSS Tipo de Compra: Compra Directa" en los datos del paciente, en 1 página.
- ✅ **Verificado**: testing agent `iteration_90.json` 100% (igss.admin crea/edita/guarda sin 403; ícono visible; regresión medico/superadmin OK) + curl (POST/PUT 200) + pypdf/foto del PDF. Sin bugs.
- ⚠️ Requiere redespliegue; la migración de permiso aplica automáticamente al rol existente en producción.

### Sesión 39 — Acceso del Administrador IGSS a Evaluación Oftalmológica (solo lectura) + Tipo de Compra en el PDF (2026-06)
- ✅ **Bug: el rol Administrador IGSS no podía revisar expedientes oftalmológicos** pese a tener el menú "Evaluación Oftalmológica" habilitado. Causa raíz: la ruta `/evaluacion-oftalmologica` estaba protegida por `requiredPermission="view_evaluacion"` (permiso que el rol no tiene), mientras que módulos equivalentes como Sala de Operaciones usan `requiredMenu`. **Fix** (`App.js`): la ruta ahora usa `<ProtectedRoute requiredMenu="evaluacion_oftalmologica">`, por lo que habilitar el menú concede acceso. Como el rol carece de `view_evaluacion`, la página queda en **solo lectura** (puede revisar historial, abrir evaluaciones y descargar PDF, pero no crear/editar). Regresión OK: superadmin y médico mantienen acceso de edición.
- ✅ **Tipo de Compra en el PDF del reporte** (`routes/evaluaciones.py`): en el bloque "Datos del Paciente" de pacientes IGSS ahora aparece "IGSS Tipo de Compra:" con etiqueta legible (Compra Directa / Baja Cuantía / Contrato / Convenio). Aplica a todos los reportes de pacientes IGSS. El PDF sigue en 1 página.
- ✅ **Verificado**: testing agent frontend `iteration_88.json` 100% (igss.admin entra y revisa en solo lectura; superadmin/medico editan) + curl/pypdf confirma "Compra Directa" en el PDF. Sin bugs.
- **Nota preview**: se replicó la config de menús de producción para `administrador_igss` en preview (pacientes, unidades_igss, evaluacion_oftalmologica, sala_operaciones, agenda). En producción el rol ya tiene estos menús habilitados.
- ⚠️ Requiere redespliegue para producción.

### Sesión 38 — "Tipo de Compra" aparece en el expediente del paciente IGSS (2026-06)
- ✅ En la ficha/expediente del paciente (modal "ver" en Pacientes), para pacientes IGSS ahora se muestra el campo **"Tipo de Compra"** (`view-patient-igss-tipo-compra`) con etiqueta legible (Compra Directa / Baja Cuantía / Contrato / Convenio), junto a Tipo de Paciente y NOG. Antes no aparecía.
- ✅ **Frontend** (`pages/Pacientes.js`): se agregó el bloque condicional en el `detailDialogOpen` y un mapa `tipoCompraLabels`. El dato ya venía en la respuesta de `GET /api/patients/{id}` (`igss_tipo_compra`); no hubo cambios de backend.
- ✅ **Verificado**: curl confirma que el backend persiste/devuelve `igss_tipo_compra` (round-trip a 'compra_directa'); frontend compila sin errores. ⚠️ Requiere redespliegue.

### Sesión 37 — El paciente Atendido NO se elimina de la lista "Pacientes Presentes en Clínica" (2026-06)
- ✅ Al marcar a un paciente como **Atendida** (Iniciar→En consulta→Atendida), la tarjeta **permanece visible** en el panel "Pacientes Presentes en Clínica" del Tablero del Día y de "Mi Agenda", en vez de desaparecer.
- ✅ **Backend** (`routes/agenda.py`): el filtro de `GET /api/agenda/presentes` y la lista `pacientes_presentes` de `GET /api/agenda/mi-dia` ahora incluyen `EstadoCita.ATENDIDA` además de Presente y En consulta.
- ✅ **Frontend** (`Agenda.js` `PacientePresenteCard`): para estado "Atendida" la tarjeta muestra un **badge verde "Atendida"** (`presente-atendida-badge-{cita_id}`), oculta los botones Iniciar/Atendida y el tiempo de espera, y en el menú (…) ofrece **"Deshacer atendida"** (`deshacer-atendida-presente-{cita_id}`) que la regresa a "En consulta". Para Atendida se ocultan "Cancelar llegada" y "No asistió".
- ✅ **Verificado**: curl backend + testing agent frontend `iteration_87.json` 100% (flujo completo, persiste tras recargar, deshacer funciona). Sin bugs. ⚠️ Requiere redespliegue.

### Sesión 36 — PDF de evaluación en 1 página + Indicaciones por estudio/procedimiento IGSS (2026-06)
- ✅ **PDF de reporte en 1 sola página** (`routes/evaluaciones.py` `GET /{id}/pdf`): se redujeron los tamaños de letra (Título 16→13, Secciones 12→9.5, cuerpo 10→8, celdas 8→7.5) y los espaciados. **Cuadro de refracción reducido a ~la mitad** (colWidths 5×1.2" ≈ 6" → [0.85,0.6,0.6,0.5,0.6]" ≈ 3.15", fuente 9→7.5). También se redujeron la tabla de Agudeza Visual y la de Anteojos, el logo (1.0×1.35"→0.75×1.0") y el `bottomMargin` 160→150. **Verificado**: evaluación de prueba con agudeza visual + refracción + 2 estudios → PDF de **1 página** (pypdf) y render visual correcto.
- ✅ **Indicaciones de texto libre por estudio/procedimiento IGSS**: el modelo `estudios_procedimientos` pasó de `List[str]` a `List[EstudioProcedimientoIGSS]` = `{nombre, indicaciones}` (`models/evaluacion_oftalmologica.py`, validator acepta strings legacy y dicts → retrocompatible). En la UI (`EvaluacionOftalmologica.js`, sección "Medicamentos y Procedimientos (EXCLUSIVO IGSS)") cada estudio ahora tiene su `Autocomplete` de nombre (`igss-estudio-{idx}`) + un `Textarea` de indicaciones debajo (`igss-estudio-indicaciones-{idx}`). El PDF y la vista de impresión muestran "Indicaciones: ..." debajo de cada estudio.
- ✅ **Verificado**: backend por curl (PUT guarda/GET devuelve objetos {nombre, indicaciones}; PDF 1 página con indicaciones) + testing agent frontend `iteration_86.json` 100% (agregar/editar/persistir/eliminar estudios con indicaciones independientes, persistencia tras recargar). Sin bugs.
- ⚠️ Requiere redespliegue para producción.

### Sesión 35 — IGSS: badge de institución en el Tablero + Motivo de consulta automático desde el NOG (2026-06)
- ✅ **Badge de institución en cada tarjeta de cita** (`CitaCard` en `Agenda.js`): pacientes IGSS muestran un badge verde "IGSS"; otras instituciones muestran su etiqueta (`referral_institution_label`), o "Sin institución". data-testid `institucion-badge-{cita.id}`. Aplica a Tablero del Día, vista Día y Mi Agenda.
- ✅ **Backend** (`routes/agenda.py` `/mi-dia`): citas enriquecidas con `referral_institution`, `referral_institution_label` y `orden_id` del paciente/orden vinculada.
- ✅ **Motivo de consulta automático** (`EvaluacionOftalmologica.js` `cargarNotaPaciente`): al abrir una NUEVA evaluación de un paciente IGSS, se resuelve el NOG (preferido el de la cita, si no el primero) vía `GET /igss-units/{unit_id}/nogs-activos` y se autollena `motivo_consulta` con la descripción del servicio (`nombre_servicio`). Usa `setFormData` → el textarea es controlado (`value={formData.motivo_consulta}`), por lo que el valor queda en el estado y se guarda al enviar.
- ✅ **Decisión del usuario**: si el NOG del paciente IGSS NO tiene descripción, el motivo se **deja vacío** para que el médico lo escriba (ya implementado con `if (desc)`). No se agregaron más elementos al Tablero por ahora (el usuario respondió "Ninguna").
- ✅ **Verificado**: screenshots previos (badges "IGSS" en el Tablero + "Retina" autollenado en el textarea) + revisión de código (binding de estado controlado correcto). App carga sin errores.
- **Pendiente Fase 2 (futuro, no solicitado aún)**: filtrar/ordenar el Tablero por institución; mostrar NOG/No. SPS junto al nombre en la tarjeta. **Fase 3**: resumen del día por institución (conteo IGSS vs otros) en las tarjetas superiores.
- ⚠️ Requiere redespliegue para producción.

### Sesión 34 — Respaldos automáticos semanales (2026-10)
- ✅ Backend `routes/backups.py`: vuelca TODAS las colecciones a JSON gzip y lo sube al almacenamiento de objetos de Emergent (`INTEGRATION_PROXY_URL` + `EMERGENT_LLM_KEY`). Metadatos en colección `backups`. Endpoints solo superadmin: `GET /api/backups`, `POST /api/backups/run`, `GET /api/backups/{id}/download`, `DELETE /api/backups/{id}`. Webhook cron `POST /api/cron/backup` (auth `Bearer WEBHOOK_CRON_SECRET`, ack inmediato, trabajo en background).
- ✅ Cron `/app/.emergent/crons.yml`: `respaldo-semanal`, `0 6 * * 0`, tz `America/Guatemala` (domingos 06:00).
- ✅ Frontend `pages/Respaldos.js` + ruta `/respaldos` (superadmin) + nav `nav-respaldos`: lista, crear ahora, descargar (blob), eliminar; auto-refresco mientras hay en progreso. Conservar todos (sin borrado automático).
- ✅ Env nuevas en `backend/.env`: `EMERGENT_LLM_KEY`, `WEBHOOK_CRON_SECRET`.
- ✅ Verificado en preview: cron 401/200, respaldo completado (64 colecciones, 57,499 docs, ~9.3MB), descarga gzip válida, run manual, delete, crons.yml válido.
- ⚠️ **Requiere REDEPLOY** para activar endpoints + env + cron semanal en producción.

### Sesión 34 — Migración de datos a PRODUCCIÓN y validaciones DPI/email (2026-10)
- ✅ **Email y DPI opcionales**: en `Pacientes.js` (`validateForm`) y backend `patients.py` (create+update). **DPI obligatorio SOLO para pacientes IGSS** (asterisco dinámico en etiqueta). Email solo valida formato si se ingresa. Mismo criterio en el flujo de Agenda (`fichaIncompleta`, `guardarCompletarFicha`, etiqueta `cf-dpi`): DPI ya no es obligatorio salvo IGSS.
- ✅ **Migración preview → producción** (datos históricos de Access). Preview y producción usan **bases MongoDB SEPARADAS**; los datos importados a preview NO pasan solos a producción. No hay conectividad directa del pod de preview a Atlas (puerto 27017 bloqueado), así que la migración se hizo vía **API HTTPS** de la app desplegada.
  - Pacientes: **17,753** reales (expediente numérico 1..N, sin datos de prueba) insertados vía `POST /api/patients/import/batch` (preserve_record_numbers=True). Se desactivaron los 8 pacientes demo `EXP-202604-000X`.
  - Evaluaciones: **36,419** presentes en prod pero quedaron apuntando a `paciente_id` antiguos (ids de la migración del primer deploy) → **100% huérfanas**.
  - Fix: nuevo endpoint de mantenimiento `POST /api/evaluaciones/admin/relink-por-expediente` (solo superadmin) re-vincula cada evaluación a su paciente por `paciente_expediente == patients.record_number`. Resultado prod: **36,418 actualizadas, 0 huérfanas, 0 sin expediente**.
  - ✅ **Verificado**: conteos de evaluaciones por expediente preview==producción (exp 1=12, 2=9, 50=2, 100=7, 500=1, 1000=2, 5000=1, 9849=1, 17778=1); huérfanas ~0%; captura de producción muestra 17,753 pacientes con expedientes originales.
  - Credenciales producción (superadmin): distintas a preview — ver `test_credentials.md`.
  - Script de migración conservado: `/app/scripts/migrate_to_prod.py` (modos deldemo/patients/evals/verify).
  - **Nota**: el endpoint `relink-por-expediente` quedó en el código; es seguro (superadmin, solo corrige paciente_id). Puede eliminarse en un deploy futuro de limpieza si se desea.

### Sesión 33 — Flujo de llegada

### Agenda: Flujo de llegada — completar expediente antes de pasar a Presente (2026-10 Sesión 33)
- ✅ **Detección automática de ficha incompleta** (`fichaIncompleta` en `Agenda.js`): un paciente es "incompleto" si le falta nombre, apellido, sexo, fecha de nacimiento, teléfono, dirección o institución; **el DPI solo es obligatorio si la institución es IGSS** (que también exige unidad IGSS). Aplica retroactivamente a pacientes ya existentes (incluye los agendados como "nuevo" solo con nombre/teléfono/sexo/edad).
- ✅ **Modal al marcar llegada** (`completar-ficha-dialog`): al elegir "Marcar llegada" en una cita agendada con ficha incompleta se abre el formulario precargado con los datos existentes. El paciente **NO** pasa a "Presente" hasta guardar todos los obligatorios. Al guardar se hace `PUT /api/patients/{id}` sobre el **mismo expediente** (sin duplicar) y recién entonces `cambiarEstado→Presente`.
- ✅ **Llegada directa** cuando la ficha ya está completa (sin modal), vinculada a su expediente existente.
- ✅ **Walk-ins incluidos**: `handleWalkIn` aplica la misma validación antes de `createWalkIn`; si falta algún dato abre el mismo modal y registra la llegada solo al completar.
- ✅ El paciente presente aparece en "Pacientes Presentes en Clínica" bajo su médico y queda disponible para evaluación con su expediente.
- ✅ **"Procedimiento"** agregado a los tipos de consulta (`TIPOS_CITA` en `Agenda.js`), disponible en Nueva Cita y Walk-in. (Backend acepta `tipo_cita` como texto libre.)
- ✅ data-testids: `completar-ficha-dialog`, `cf-first-name/last-name/gender/birth-date/phone/dpi/address/institution/igss-unit`, `cf-guardar`, `marcar-llegada-cita-{id}`, `cita-tipo-select`, `walkin-tipo-select`.
- ✅ **Verificado**: testing agent `iteration_74.json` — flujo crítico 100% E2E (modal abre con datos precargados, validación de obligatorios bloquea guardar, guardar actualiza mismo expediente→Presente→aparece en Presentes; "Procedimiento" presente). Sin bugs funcionales.
- **Pendiente Fase 2 (futuro)**: indicador visual en la agenda de citas con ficha incompleta antes de llegar; reporte de expedientes incompletos. **Fase 3**: capturar más datos al agendar; detección de duplicados por DPI al completar.


### POS: Médico obligatorio y autollenable tras seleccionar paciente (2026-10 Sesión 32)
- ✅ En el POS de Clínica (`PuntoVenta.js`) y de Óptica (`OpticaPOS.js`/`POSCart.js`): al seleccionar un paciente aparece el campo "Médico *" con autocompletado desde la lista general de médicos (`GET /api/doctors/search?q=`).
- ✅ Obligatorio solo cuando hay paciente: bloquea el cobro con "Seleccione el médico para esta venta" si falta. Con Cliente/Consumidor General no se exige.
- ✅ Persistencia: `ventas` guarda `medico_id/medico_nombre` (VentaCreate/VentaResponse); `optica_sales` guarda `doctor_id/doctor_name` (OpticaSaleCreateV2). 
- ✅ **Verificado**: `iteration_72.json` 100% backend + frontend.

### Agenda: elegir y ordenar médicos visibles (2026-10 Sesión 32)
- ✅ Panel "Organizar médicos" (botón "Médicos") en la vista Día: lista arrastrable para **reordenar** columnas y un **ojo** para mostrar/ocultar cada médico (no es obligatorio verlos todos), más "Restablecer" y badge visibles/total.
- ✅ Preferencia guardada **en la cuenta** (servidor, por usuario): `GET/PUT /api/agenda/preferencias-medicos` (colección `user_preferences`: `medicos_orden`, `medicos_ocultos`).
- ✅ Aplica a **vista Día** (columnas via `medicosVisibles`) y **Tablero del Día** ("Citas del día" y "Pacientes Presentes" filtran ocultos y ordenan por preferencia). El filtro "Médico" del toolbar sigue listando todos.
- ✅ **Verificado**: `iteration_71.json` 100% backend + frontend (ocultar quita columna, reordenar persiste tras recargar, Restablecer).

### Agenda Multi-día del Médico + Auditoría de expedientes (2026-10 Sesión 32)
- ✅ **Mi Agenda navegable por día**: barra con Anterior/Hoy/Siguiente (data-testid `mi-agenda-prev/hoy/next`) que cambia la fecha de trabajo (hora Guatemala).
- ✅ **Vista Semana propia** (`mi-agenda-semana`): toggle Día/Semana; grid de 7 días (Lun-Dom) con las citas activas del médico agrupadas por día; Anterior/Siguiente saltan de semana en semana; click en cita abre el paciente; click en cabecera de día abre esa fecha en vista Día.
- ✅ **Backend**: nuevo `GET /api/agenda/mi-semana?desde=&hasta=` (resuelve médico vía `doctors.usuario_id`, excluye Canceladas, 403 si no vinculado); `mi-dia` respeta `fecha` y excluye Canceladas.
- ✅ **Fase 3 (aclarada por el usuario)**: la restricción "solo mis pacientes" aplica SOLO a la agenda (ya cubierta por mi-dia/mi-semana). El médico puede abrir cualquier expediente desde Pacientes; sus cambios quedan en Auditoría. Se agregó registro `PATIENT_UPDATED` en `PUT /api/patients/{id}` (antes no se auditaba; evaluaciones ya auditaban).
- ✅ **Verificado**: `iteration_70.json` 100% backend (5/5) + frontend; auditoría de edición de paciente verificada (user medico_test, campos modificados).
- **Pendiente Fase 2 restante**: permisos clínicos más finos (ver evaluación sin editar).

### Acceso clínico configurable para rol Médico (2026-10 Sesión 32)
- ✅ **Permisos clínicos activables por rol**: nueva categoría "Clínica" en Roles con `view_agenda`, `view_evaluacion`, `manage_recetas`, `view_sala_operaciones` (roles.py AVAILABLE_PERMISSIONS). Disponibles para cualquier rol.
- ✅ **Rol "medico"** como rol de sistema editable (SYSTEM_ROLES + SYSTEM_ROLES_MENU), preconfigurado: Agenda, Evaluación, Recetas, Sala de Operaciones, crear/editar Pacientes (sin eliminar). Menús: pacientes, agenda, evaluacion_oftalmologica, sala_operaciones.
- ⚠️ IMPORTANTE: existen DOS matrices PERMISSIONS (server.py y config/permissions.py) — ambas deben mantenerse sincronizadas. `validar_rol_existe` (server.py) incluye 'medico'.
- ✅ **Agenda del médico** abre en pestaña "Mi Agenda" (activeTab inicial según rol) y muestra solo sus citas (mi-dia filtra por `doctors.usuario_id`). Si no hay ficha vinculada, muestra aviso (data-testid `mi-agenda-sin-vinculo`).
- ✅ **Vínculo usuario↔ficha** en Gestión de Usuarios: selector "Médico asignado (ficha)" cuando role==='medico'; al guardar hace PATCH /api/medicos-agenda/{id} con usuario_id.
- ✅ **Rutas clínicas** (/agenda, /evaluacion-oftalmologica, /sala-operaciones) ahora con requiredPermission; canEdit en Evaluación/Sala por permiso. Roles existentes conservan acceso.
- ✅ **Verificado**: `iteration_69.json` 100% backend (9/9) + frontend. Credencial de prueba: `medico_test`/`medico2024` (ficha Dr. Carlos Méndez).
- **Pendiente Fase 2**: médico ve días anteriores/siguientes y resumen semanal; permisos más finos (ver sin editar).

### Agenda: Eliminar (cancelar) + Reagendar arrastrando (2026-10 Sesión 32)
- ✅ **Eliminar cita**: nuevo ítem "Eliminar" (ícono papelera, data-testid `eliminar-cita-{id}`) con confirmación; marca la cita como `Cancelada` (soft, no se borra de BD) y desaparece de inmediato de todas las vistas activas.
- ✅ **Ocultar canceladas** (backend agenda.py): `listar_citas` excluye Cancelada salvo filtro `estado` explícito (permite Fase 2 ver canceladas); `listar_citas_rango` (semana/mes) excluye Cancelada; `obtener_contadores` excluye canceladas del total por médico.
- ✅ **Reagendar drag & drop** (Día y Semana): ya existía el arrastre; ahora al soltar se reagenda sin confirmación con toast "Cita reagendada" + botón **Deshacer** (revierte médico/fecha/hora originales).
- ✅ **Bloqueo de choque** (`actualizar_cita`): si el mismo médico ya tiene otra cita activa a esa hora de inicio ese día → 409 "Ese horario ya está ocupado para este médico"; la cita permanece en su lugar.
- ✅ **Verificado**: `iteration_68.json` 100% backend (4/4 pytest) + frontend (eliminar, drag libre, Deshacer, drag conflicto bloqueado con mensaje exacto).
- **Pendiente Fase 2**: drag&drop también en vista Mes; filtro para ver citas canceladas.

### Corrección Zona Horaria Guatemala GMT-6 (2026-10 Sesión 32)
- ✅ **Problema resuelto**: el sistema adelantaba el día (a las 6:46 PM jueves GT mostraba viernes) porque "hoy" se calculaba en UTC. Ahora TODO el sistema usa hora oficial de Guatemala (GMT-6, sin horario de verano).
- ✅ **Util central nueva** `/app/backend/utils/timezone.py`: `now_gt()`, `today_gt()`, `today_str_gt()`, `dia_gt_a_rango_utc(fecha)` (día GT→rango UTC [fecha 06:00, fecha+1 05:59:59]), `rango_gt_a_utc(ini,fin)`, `GUATEMALA_TZ`.
- ✅ **Estrategia**: almacenamiento sigue en UTC isoformat (sin migración de datos). Solo se corrige (a) cálculo de "hoy" a GT y (b) filtros/totales "del día" convierten el día GT a rango UTC, lo que agrupa correctamente incluso datos históricos.
- ✅ **Backend corregido**: caja.py (estado/abrir/movimientos/cierre/totales/cierres financieros), ventas.py (/hoy, /resumen-dia, nº venta, caja abierta), agenda.py (citas/contadores/presentes/mi-agenda/walk-in), dashboard.py, dashboard_financiero.py, expenses.py, payments.py, inventario.py, inventario_ops.py, evaluaciones.py, optica.py, cuentas_cobrar.py, laboratorio_pruebas.py, patients.py, surgeries.py, server.py (gastos fijos + CronTrigger con timezone GT + /dashboard/upcoming).
- ✅ **Frontend corregido**: nuevo `getGuatemalaTimeHM()` en api.js; Agenda.js (fechaSeleccionada/botón Hoy/esHoy), Caja.js, Gastos.js, GastosFijos.js, SalaOperaciones.js, OpticaCompras.js, OpticaVentas.js, OpticaDashboard.js, Sociedades.js, EvaluacionOftalmologica.js, CRMCirugias.js, Pacientes.js (defaults de fecha/mes/año y min/max de date pickers) + AuditLogs.js (muestra marcas de tiempo en America/Guatemala).
- ✅ **Google Calendar** ya usaba America/Guatemala (sin cambios).
- ✅ **Verificado**: `iteration_67.json` 100% backend (11/11 pytest `test_timezone_gt_fix.py`) + frontend. Probado en ventana crítica (UTC=Oct 9 / GT=Oct 8): Agenda muestra "Jueves 8 de Octubre" correctamente.
- **Pendiente Fase 2**: etiqueta opcional "hora de Guatemala (GMT-6)" en pantallas clave; revisar recordatorios programados.

### Módulo IGSS separado de Configuración (2026-10 Sesión 32)
- ✅ Se creó el módulo/categoría "IGSS" (menu_config.py) y se movió "Unidades IGSS" ahí (ruta `/igss/unidades`), sacándolo de Configuración. Aparece como grupo propio en el sidebar y como categoría seleccionable en Usuarios→Menús por Rol.

### Búsqueda Walk-in por nombre (2026-10 Sesión 32)
- ✅ Corregido: el diálogo Walk-in en Agenda.js usaba `first_name/last_name` pero `/api/patients/search` devuelve `full_name`; ahora muestra el nombre completo.


### Auditoría (2026-10 Sesión 31) — Prompt 26: ¿Es real la utilidad que muestra el sistema?
- ✅ **Nota de cirugía (cierre de sesión anterior)**: `iteration_64.json` confirmó 100% backend+frontend, sin bugs (solo advertencia a11y opcional). Tarea cerrada.
- ✅ **Auditoría integral ejecutada** (solo lectura en producción; pruebas con datos sintéticos `AUD26-*` ya purgados). Entregables: `/app/docs/auditoria/P26_descubrimiento.md` (Fase 0: mapa de colecciones + origen literal de cada cifra financiera), `/app/docs/auditoria/P26_informe.md` + `.xlsx` (Fase 3: hallazgos + plan de corrección NO aplicado), `/app/backend/scripts/test_auditoria_p26_utilidad_real.py` (script reproducible del escenario de referencia), `/app/backend/tests/test_auditoria_p26_invariantes.py` (INV-33/37/38/42/43, xfail documentando hallazgos vigentes).
- **Conclusión ejecutiva: la utilidad mostrada HOY NO es real.** Es flujo de caja (ingresos−egresos de `caja_movimientos`), nunca resta costo de ventas. Hallazgos críticos confirmados **empíricamente** contra el backend real:
  - **H-01 (CRÍTICO, YA ACTIVO en esta BD)**: `GET /api/cxc` responde 500 si una CxC no tiene `paciente_id`/`tipo_pagador_id` (5 registros reales ya en este estado) — el módulo de CxC Clínica está roto ahora mismo. El abono también crashea después de guardarse en Mongo (riesgo de duplicado por reintento).
  - **H-02 (CRÍTICO)**: `recalcular_costo_promedio` se llama DESPUÉS de `actualizar_existencia`, duplicando la cantidad comprada en el denominador. Probado: 10@Q100+10@Q120 → costo promedio Q73.33 en vez de Q110.00. Afecta a todo producto con 2+ compras ya registradas.
  - **H-03 (CRÍTICO)**: un abono de Q200 a CxC con `registrar_en_caja=true` duplica el ingreso en el Dashboard Financiero (Q400 en vez de Q200).
  - **H-04/H-05 (CRÍTICO)**: el "Resultado Neto" de Cierres Financieros = ingresos−egresos de `caja_movimientos`, sin costo de ventas, e IGNORA gastos pagados vía el flujo de Autorizaciones (egresos_caja quedó en Q0 tras pagar Q150 autorizados).
  - **H-06 (CRÍTICO)**: `POST /api/payments` paga cualquier gasto SIN verificar autorización previa (bypass de `payment_authorizations`).
  - **H-07 (ALTO)**: `reabrir_caja` (SuperAdmin) desbloquea cierres diarios sellados; `cierres_financieros` nunca llega a un estado sellado.
  - **H-08 (ALTO)**: servicios clínicos (consultas/cirugías) no tienen costo/honorario — entran con costo cero sin marcarse "sin costear".
  - **H-09 (ALTO)**: "Evolución Mensual de Rentabilidad" (clínica) usa precio/costo ACTUALES del catálogo, no los vigentes al momento de cada venta histórica (reescribe retroactivamente la utilidad pasada).
  - **H-10/H-12 (MEDIO)**: `crear_venta` no valida `es_punto_venta` en el `bodega_id` recibido; no existe concepto de cuentas por pagar a proveedor.
  - **H-11 (positivo, confirmar)**: las compras de inventario NO se registran como gasto (correcto, no tocar).
- ⚠️ **NO se aplicó ninguna corrección** (regla de la auditoría: detectar, no corregir, sin aprobación explícita). Plan de corrección priorizado por riesgo financiero en `P26_informe.md`, sección final.
- **Pendiente de decisión del SuperAdmin**: aprobar o no el plan de corrección (empezar por H-01, cambio de bajo riesgo: volver opcionales `paciente_id`/`tipo_pagador_id` en el modelo de respuesta de CxC, ya que el módulo está roto en producción/preview en este momento).

### Correcciones aplicadas (2026-10 Sesión 31b) — Aprobadas por el SuperAdmin tras la auditoría P26
- ✅ **H-01 (CxC roto)**: `paciente_id`/`tipo_pagador_id` ahora `Optional` en `CuentaCobrarBase`/`CuentaCobrarResponse` (`models/caja.py`). `GET /api/cxc` y los abonos vuelven a funcionar con ventas de "Cliente General" sin paciente vinculado.
- ✅ **H-02 (costo promedio ponderado)**: se corrigió el orden de llamadas en `crear_recepcion` (`inventario_ops.py`) y `registrar_entrada_rapida` (`inventario.py`) — ahora `recalcular_costo_promedio` corre ANTES de `actualizar_existencia`. Verificado: 10 unid@Q100 + 10 unid@Q120 → Q110.00 (antes Q73.33). **Corrección histórica**: solo se corrigió automáticamente el producto `PRB-SRV-002` (caso sin ambigüedad: todas sus entradas al mismo costo, desde existencia cero). El producto `PROD-00009` tiene un salto de costo fuera del kardex (posible edición manual) y quedó señalado para revisión manual — NO se tocó para evitar sobrescribir un valor potencialmente correcto. Script de detección conservador en `backend/scripts/corregir_costo_promedio_historico.py`.
- ✅ **H-04/H-05 (utilidad real en cierres financieros)**: `calcular_cierre_financiero` (`caja.py`) ahora calcula `costo_ventas` (desde el kardex, costo vigente al momento de cada venta) y `gastos_pagados` (desde `db.payments`, incluye pagos vía Autorizaciones que antes no se reflejaban). Nuevos campos `costo_ventas`, `gastos_pagados`, `utilidad_bruta` en `CierreFinancieroResponse` y en la UI (`Caja.js`: columnas nuevas en la tabla + Card "Utilidad Real" en el detalle, `data-testid="cierre-utilidad-real-card"`). `resultado_neto = utilidad_bruta − gastos_pagados − egresos_caja`.
- 🐛 **Regresión encontrada y corregida por el testing_agent**: `fecha_inicio`/`fecha_fin` en `CierreFinancieroResponse` eran `str` obligatorios y rompían `GET /api/cierres-financieros` (500) para cierres legacy sin esos campos — se cambiaron a `Optional[str] = ""`.
- ✅ **Validado**: 11/11 pytest (`backend/tests/test_auditoria_p26_fixes.py` del testing_agent + `backend/tests/test_auditoria_p26_invariantes.py`) y E2E frontend (`iteration_65.json`). Sin regresiones en login, dashboard, POS, pacientes, inventario, gastos, autorizaciones, agenda.
- ✅ **H-03 (doble conteo de abonos en Dashboard Financiero) — corregido 2026-10-06**: `registrar_abono` (`caja.py`) ahora guarda `movimiento_caja_id` en el abono SOLO si realmente se creó el movimiento de caja (evita falsos positivos si la caja no está abierta). `dashboard_financiero.py` excluye del conteo de `ingresos_cxc_periodo` cualquier abono que ya tenga `movimiento_caja_id` (ya contado vía `caja_movimientos`). Validado: abono de Q100 con `registrar_en_caja=true` ahora suma exactamente Q100 al dashboard (antes Q200); con `registrar_en_caja=false` también suma Q100. 8/8 pytest + UI (`iteration_66.json`). Nota: abonos legados anteriores a este fix sin `movimiento_caja_id` pero con un `caja_movimiento` ya creado seguirán duplicados en reportes históricos (no se corrigió retroactivamente, siguiendo la política de la auditoría de no tocar datos históricos sin aprobación explícita adicional).
- ⚠️ **Pendientes del backlog P26 (no tocados, requieren aprobación futura)**: H-06 (pago de gastos sin autorización vía `POST /payments`), H-07 (cierres reabribles/no sellados), H-08 (servicios clínicos sin costo), H-09 (reporte histórico de rentabilidad usa costo/precio actuales), H-10 (bodega no-POS no validada en venta), H-12 (sin cuentas por pagar a proveedor). Ver `/app/docs/auditoria/P26_informe.md`.

### Mejora (2026-06 Sesión 30b) — Nombre del seguro en exportaciones de cirugías
- ✅ Las exportaciones de cirugías (Excel y PDF, `GET /api/reports/surgeries`) ahora muestran la institución como "Seguro Privado (Nombre del seguro)" cuando aplica. Helper `format_institution` en `routes/surgeries.py`; ancho de columna del PDF ajustado.
- **Verificado por curl**: xlsx 200 (contiene el nombre del seguro) y pdf 200.

### Feature (2026-06 Sesión 30) — Sala de Operaciones: cirujano desde médicos, anestesia e instituciones
- ✅ **Cirujano** ahora se selecciona de la lista de médicos registrados (Select poblado de `/api/doctors`); el anestesiólogo queda como texto libre. En edición conserva el valor previo aunque no esté en la lista.
- ✅ **Tipos de anestesia** reducidos a: **Tópica / Local / Local Asistida / General** (`local_asistida` nuevo). Etiquetas corregidas en tabla, detalle y export Excel/PDF.
- ✅ **Instituciones**: **Novavision / Alquiler / Seguro Privado / IGSS**. IGSS mantiene su bloque de datos. **Seguro Privado** muestra campo obligatorio "Nombre del seguro" (`insurance_name`, validado en frontend y backend). Novavision/Alquiler sin campos extra.
- ✅ **Migración de datos** aplicada: anestesia `retrobulbar`→`local`; institución `Privado`→`Seguro Privado` (equivalencias confirmadas por el usuario).
- **Backend** (`routes/surgeries.py`): `insurance_name` en `SurgeryBase/Update/Response`; validación de nombre de seguro en `create_surgery`.
- **Verificado**: testing agent iteration_63.json → backend 100% + frontend E2E 100%, sin issues. Script: `/app/backend/scripts/test_sala_operaciones.py`.
- ⚠️ Requiere redespliegue para producción.

### Feature (2026-06 Sesión 29) — Horario de disponibilidad por médico
- ✅ **Horario semanal por médico** (claves "1"=Lun.."7"=Dom, cada día {activo, hora_inicio, hora_fin}) configurable en la pantalla de Médicos (`horario_semanal` en el doctor).
- ✅ **Enforcement duro**: agendar/reprogramar/próxima-cita fuera del horario del médico → 409 ("Fuera del horario del médico" / "El médico no atiende ese día"). Respetado también por la API del agente externo (`/agenda/external/disponibilidad` y `/citas`).
- ✅ **Compatibilidad**: médico sin horario configurado = sin restricción.
- ✅ **Disponibilidad = horario + sin bloqueos/feriados** (combina con los bloqueos de la Sesión 28).
- **Backend** (`routes/agenda.py`): `verificar_horario_medico`, `motivo_no_disponible`. **Frontend** (`Medicos.js`): editor de 7 días con toggle + horas.
- **Verificado**: testing agent iteration_62.json → backend 100% + frontend 100%. Script: `/app/backend/scripts/test_horario_medico.py`.

### Feature (2026-06 Sesión 28) — Bloqueo de Agenda (espacios, días, feriados y vacaciones) [Fase 1 MVP]
- ✅ **Bloqueos por médico**: franja de horas en una fecha o día completo (individual por médico).
- ✅ **Bloqueos de clínica completa**: un día o rango de fechas (feriados/vacaciones), afecta a todos los médicos.
- ✅ **Crear/eliminar por cualquier usuario**; motivo opcional.
- ✅ **Enforcement duro**: crear cita (`POST /api/agenda/citas`), reprogramar (`PUT`) y próxima-cita en un espacio bloqueado devuelven **409** con el motivo. Aplica a agenda interna y API externa.
- ✅ **Conflictos**: al crear un bloqueo con citas existentes, el bloqueo se crea igual y se devuelven `citas_en_conflicto` (las citas NO se cancelan; se listan para reprogramar).
- ✅ **API agente externo (n8n/Claude)** con clave fija `X-API-Key` (env `AGENDA_API_KEY`):
  - `GET /api/agenda/external/disponibilidad?medico_id=&fecha=&hora_inicio=&hora_fin=` → {disponible, motivo, bloqueo, citas_existentes}
  - `GET /api/agenda/external/bloqueos` → lista bloqueos vigentes
  - `POST /api/agenda/external/citas` → agenda respetando bloqueos (409 si bloqueado). Sin clave/clave inválida → 401.
- ✅ **Frontend** (`AgendaBloqueos.js` integrado en `Agenda.js`): botones "Bloquear agenda"/"Ver bloqueos", diálogo de creación (tipo, médico, fecha/rango, día completo/franja, motivo, lista de conflictos), banner de bloqueos del día con eliminación, panel de gestión. Refresco cada 15s.
- **Backend**: colección `bloqueos_agenda`; helpers `verificar_bloqueo`, `listar_citas_conflicto`, `insertar_cita` en `routes/agenda.py`.
- **Verificado**: testing agent iteration_61.json → backend 100% (10/10 script + 3/3 pytest), frontend E2E 100%.
- **Clave API para n8n** (preview): `nova_agenda_1eH6M_ssw5iOnYeYVK_rGwnWUIh3_U1FXULX2AZB8jk` (en `backend/.env` `AGENDA_API_KEY`; puede rotarse).
- **Pendiente (Fase 2)**: bloqueos recurrentes, reprogramación en lote de conflictos, notificación a pacientes; (nice-to-have) tachar slots bloqueados en la grilla además del banner.
- ⚠️ Requiere redespliegue para producción.

### Feature (2026-06 Sesión 27c) — Permisos rol 'usuario' en Inventario (entrada rápida y mín/máx)
- 🐛 El rol `usuario` recibía 403 en `POST /api/inventario/entrada` (Entrada Rápida) y `PUT /api/inventario/productos/{id}` (editar mín/máx); en el frontend los campos mín/máx estaban `disabled`.
- ✅ **Fix backend**: `registrar_entrada_rapida` y `actualizar_producto` permiten `usuario` (en update, whitelist a `existencia_minima`/`existencia_maxima`; precio sigue protegido a superadmin). **Fix frontend** (`inventario/Productos.js`): flag `puedeEditarExistencias` habilita mín/máx para `usuario`. Verificado (iteration_60.json, 100%).

### Aclaración/Fix menor (2026-06 Sesión 27b) — Overlay "Uncaught runtime errors: Script error." en el preview
- ❓ Reporte: aparecía el overlay rojo "Uncaught runtime errors: Script error." sobre la pantalla de login.
- 🔎 **Causa**: NO es un error de la app. Es un error **cross-origin** de scripts externos cargados en `public/index.html` (PostHog analytics / `assets.emergent.sh/scripts/emergent-main.js`). El navegador enmascara su detalle como el genérico "Script error." y el overlay de **modo desarrollo** de React (el preview corre `craco start`) lo muestra. En producción (build) ese overlay no existe.
- ✅ **Fix** (`public/index.html`): supresor específico (junto al ya existente de `DataCloneError`) que descarta sólo el "Script error." cross-origin genérico (`!e.filename && !e.error`); los errores reales de la app (con mensaje/filename) NO se suprimen. Verificado: login carga sin overlay.

### Feature + Bug fix crítico (2026-06 Sesión 27) — Tiempo real en POS + anti-sobreventa bajo concurrencia
- 🐛 **Bug crítico de sobreventa (data/dinero)**: `descontar_inventario` (`routes/inventario.py`) validaba el stock y LUEGO descontaba (check-then-act) y los lotes se decrementaban con `$inc` incondicional. Con varios cajeros vendiendo el mismo producto/lote a la vez → **sobreventa** (existencia/lote negativos), justo lo que el usuario temía ("vender el mismo lote agotado").
  - ✅ **Fix (descuento ATÓMICO + rollback)**: sin lotes → `find_one_and_update` con guard `{'cantidad': {'$gte': cantidad}}`; con lotes (FEFO) → `update_one` por lote con guard `{'cantidad_disponible': {'$gte': usar}}` + reintento FEFO cuando otro usuario toma el lote en paralelo; si no se puede completar, **rollback** de todo lo descontado en esa venta y error 400. `crear_movimiento_kardex` ahora acepta `existencia_anterior` explícita para snapshots correctos.
  - ✅ **Fix número de venta atómico**: `generar_numero_venta` (`routes/ventas.py`) usaba read-then-write (VTA duplicado). Ahora contador atómico en `counters` (`find_one_and_update $inc`) por día + reintento anti-drift.
  - **Verificado (testing agent, iteration_59.json, backend+frontend 100%)**: 6 ventas concurrentes con stock 3 → exactamente 3 OK / 3 x 400, existencia final 0 (nunca negativa); 5 concurrentes con lote 2 → 2 OK / 3 x 400, lote 0, existencia 0; 10 concurrentes → 10 números de venta únicos. Scripts: `/app/backend/scripts/test_concurrencia_pos.py`, `test_concurrencia_pos_lotes.py`; pytest `/app/backend/tests/test_pos_concurrencia_iter59.py`.
- ✅ **Refresco automático de stock en POS** (`PuntoVenta.js`): `refrescarStockSilencioso` cada 12s (silencioso, respeta búsqueda/categoría y se pausa si la pestaña está oculta) para que la existencia se sincronice entre cajeros. Smoke UI OK sin errores de consola.
- ⚠️ Requiere redespliegue para producción.

### Features + Bug fix (2026-06 Sesión 26) — Concurrencia (10 usuarios) y auto-actualización en tiempo real
- 🐛 **Bug crítico de concurrencia (data integrity)**: `get_next_record_number` (`routes/patients.py`) leía el último expediente y sumaba 1 (read-then-write). Con 3 usuarios creando pacientes en simultáneo generaba **números de expediente DUPLICADOS**.
  - ✅ **Fix**: contador atómico por mes en la colección `counters` (`find_one_and_update` con `$inc` + `ReturnDocument.AFTER`), inicialización idempotente con `$setOnInsert` (toma el máximo existente del mes una sola vez) y bucle de reintento anti-drift (si el candidato ya existe, avanza). Import `from pymongo import ReturnDocument`.
  - **Verificado (testing agent, iteration_58.json, 4/4 backend)**: 20 POST /api/patients concurrentes → 0 expedientes duplicados; 10 POST con el MISMO DPI en paralelo → solo 1 crea (resto 400). Script: `/app/backend/scripts/test_concurrencia_pacientes.py` y `/app/backend/tests/test_concurrencia_pacientes.py`.
- ✅ **Refresco automático en Agenda** (`Agenda.js`): el polling (cada 15s) ahora TAMBIÉN refresca las citas (`pollCitas`), no solo contadores/presentes, para **evitar duplicar citas** entre usuarios. Guardas: no refresca con el diálogo de cita abierto, walk-in abierto ni durante arrastre (drag&drop). Skip si la pestaña está oculta (`document.hidden`).
- ✅ **Auto-actualización en Pacientes** (`Pacientes.js`): polling silencioso cada 15s (`pollPatients`) respetando página/búsqueda/filtros actuales; no corre con el formulario abierto.
- ✅ **Aviso discreto de cambios**: cuando el refresco automático detecta registros nuevos creados por OTROS usuarios, se muestra un `toast.info` breve (3s): "Agenda actualizada: N cita(s) nueva(s)", "Lista actualizada: N paciente(s) nuevo(s)", "Se agregó N médico(s) nuevo(s)". Detección por `useRef` de IDs conocidos (no avisa por las acciones propias).
- ℹ️ **Ruta de Médicos**: la página vive en `/optica/medicos` (no `/medicos`).
- ℹ️ El rol `usuario` NO tiene permiso `create_patients` (recibe 403 al crear pacientes) — comportamiento esperado.
- ⚠️ Requiere redespliegue para producción.

### Bug fix (2026-06 Sesión 25) — Datos no se actualizaban entre usuarios simultáneos (médico nuevo tardaba ~10 min)
- 🐛 **Bug (en pruebas, 10 usuarios simultáneos)**: al agregar un médico, no aparecía para otro usuario hasta ~10 min después.
- 🔎 **Causa raíz**: el middleware de seguridad (`server.py`) marcaba `/api/doctors`, `/api/igss-units` y `/api/catalogos/` con `Cache-Control: public, max-age=300`. Al ser `public` + 5 min, el navegador/CDN servía la lista **cacheada** a los demás usuarios → los cambios no se veían hasta expirar el caché.
- ✅ **Fix backend** (`server.py`): TODOS los endpoints `/api/` ahora responden `no-cache, no-store, must-revalidate` (se eliminó la lista `cacheable_endpoints`). Verificado por curl: `GET /api/doctors` → `cache-control: no-store, no-cache, must-revalidate`.
- ✅ **Fix frontend** (`Medicos.js`): auto-actualización en tiempo real — polling silencioso cada 15s (solo si la pestaña está visible) para que los médicos nuevos aparezcan sin recargar. La página ya tenía botón "Actualizar" manual.
- ⚠️ **Nota**: la verificación por UI (screenshot) no pudo autenticarse en el preview por rate-limit de IP de la automatización de login; el fix está verificado a nivel de API. Requiere redespliegue para producción.


### Bug fix (2026-06 Sesión 24) — El rol "usuario" no podía agregar productos en Inventario
- 🐛 **Bug**: como `usuario`, al dar clic en "Nuevo Producto" no se podía crear (y los catálogos de apoyo daban 403).
- 🔎 **Causa**: el backend restringía a admin/superadmin: `crear_producto` (403 al guardar), `GET /suppliers` y `GET /inventario/sociedades/catalogo` (403 al cargar el formulario).
- ✅ **Fix**: se agregó el rol `usuario` a esos tres chequeos: `crear_producto` (`routes/inventario.py`), `listar_sociedades` (catálogo) y `get_suppliers` (`server.py`). Se mantienen restringidos a superadmin: eliminar producto y editar `precio_venta`.
- **Verificado por testing agent (backend 6/6 + frontend 100%, iteration_57.json)**: `usuario` abre el modal y crea productos por UI (PROD-00023) y por API (POST→200); `GET /suppliers`, `/sociedades/catalogo`, `/bodegas`→200; DELETE producto sigue 403. Test: `/app/backend/tests/test_inventario_usuario_role.py`. Productos QA purgados. Requiere redespliegue para producción.
- (Nota menor no bloqueante: el modal "Nuevo Producto" carece de `DialogDescription` — advertencia de accesibilidad, pendiente opcional.)



### Bug fix (2026-06 Sesión 23) — No se podía eliminar una bodega "con productos" aunque el inventario estaba vacío
- 🐛 **Bug (producción)**: inventario vacío pero al eliminar una bodega decía que tenía productos/existencias.
- 🔎 **Causa raíz**: el stock real vive en la colección `existencias_inventario`, pero el force-delete de productos (`eliminar_producto`) borraba de `existencias_bodega` (colección incorrecta). Al eliminar productos quedaban existencias **huérfanas** con cantidad>0 (de productos ya inexistentes) que la UI no muestra pero que el chequeo de `eliminar_bodega` sí contaba → bloqueaba el borrado.
- ✅ **Fix** (`routes/inventario.py`): (1) `eliminar_producto` con `force=true` ahora borra de `existencias_inventario` (colección correcta); (2) `eliminar_bodega` ahora ignora existencias de productos inexistentes (huérfanas), solo bloquea si hay stock de productos que aún existen, y limpia las huérfanas de la bodega antes de eliminarla.
- **Verificado por testing agent (backend 4/4, 100%, iteration_56.json)**: bodega huérfana→200 eliminada; bodega con stock real→400 bloqueada; no-superadmin→403; force-delete de producto limpia `existencias_inventario` y permite borrar la bodega. Test: `/app/backend/tests/test_bodega_orphan_fix.py`. **NOTA producción**: las bodegas afectadas ya podrán eliminarse tras redesplegar (el propio borrado limpia las huérfanas). Requiere redespliegue.



### Mejoras (2026-06 Sesión 22) — Cupos por NOG en el filtro + Exportar con Unidad y NOG
- ✅ **1. Cupos por NOG en el desplegable**: además del conteo de pacientes, cada NOG muestra ahora **usados/total según contrato**, ej. "EXP-100 — Consulta (2 pac. · 7/50)". Backend: `nogs-activos` agrega `acreditados`; frontend agrega `· {acreditados}/{cantidad}` al label.
- ✅ **2. Exportación de Pacientes con Unidad y NOG**: los export a **Excel y PDF** ahora respetan los filtros `igss_unit_id` e `igss_nog` (antes el Excel ignoraba NOG y el PDF ignoraba unidad, NOG y fechas) e incluyen columnas **"Unidad IGSS"** y **"NOG"**. Frontend `patientApi.exportExcel/exportPdf` pasan unidad, NOG y fechas.
- **Verificado**: curl (nogs-activos → 2 pac · 7/50; Excel con columnas Unidad/NOG y 2 filas filtradas; PDF válido) y screenshot del desplegable con cupos. Datos de prueba purgados. ESLint limpio. Requiere redespliegue para producción.



### Mejora (2026-06 Sesión 21) — Contador de pacientes por NOG en el filtro
- ✅ El desplegable de NOG (filtro de Pacientes, cascada desde Unidad IGSS) ahora muestra junto a cada NOG **cuántos pacientes tiene asignados**: ej. "CNT-100 — Consulta (3 pac.)".
- Backend: el endpoint `GET /igss-units/{unit_id}/nogs-activos` incluye ahora `pacientes_asignados`, calculado con una sola agregación sobre `patients` (activos, agrupados por `igss_nog`) para esa unidad.
- Frontend (`Pacientes.js`): el label de cada `SelectItem` del NOG añade `(${n.pacientes_asignados} pac.)`.
- **Verificado**: curl (CNT-100→3, CNT-200→1) y screenshot del desplegable con el conteo. Datos de prueba purgados. ESLint limpio. Requiere redespliegue para producción.



### Mejora (2026-06 Sesión 20) — Filtro NOG en cascada desde la Unidad IGSS
- ✅ En los filtros de Pacientes, al **seleccionar una Unidad IGSS** el filtro de **NOG** ahora se convierte en un **desplegable** con los NOG activos de esa unidad (cascada Unidad → NOG) usando `igssNogApi.getActivos(unitId)`. Sin unidad seleccionada, el NOG sigue siendo un campo de texto libre (búsqueda parcial). Al cambiar de unidad se **resetea** el NOG.
- Implementación en `Pacientes.js`: nuevo estado `filterNogs` + efecto que carga los NOG al cambiar `filters.igss_unit_id`; render condicional `filter-igss-nog-select` (Select) vs `filter-igss-nog` (Input).
- **Verificado por testing agent (frontend 5/5, 100%, iteration_55.json)**: aparición del desplegable con los NOG correctos, filtrado de la tabla por NOG, reseteo al cambiar unidad y "Limpiar filtros". Datos de prueba (unidad "QA Unidad NOG", 2 NOG, 3 pacientes QN) purgados. ESLint limpio. Requiere redespliegue para producción.



### Ajustes UI (2026-06 Sesión 19) — Receta de Medicamentos
- ✅ **1. Unir Dosis/Frecuencia/Duración**: en la sección "Receta de Medicamentos" de `EvaluacionOftalmologica.js` los tres campos (antes un `grid grid-cols-3` de inputs separados tipo píldora) ahora forman **un solo grupo conectado**: un contenedor con borde redondeado que envuelve los tres inputs sin borde propio, separados por divisores verticales. Verificado por screenshot (grupo unido visible con la receta desplegada).
- ✅ **2. Logo de la receta 1.5x**: el logo del encabezado de impresión de la receta pasó de `h-8` (2rem) a `h-12` (3rem). Verificado por código.
- ESLint limpio. Requiere redespliegue para producción.



### Feature (2026-06 Sesión 18) — Filtros de Pacientes: quitar edad + filtros IGSS por Unidad y NOG
- ✅ Se **eliminó el filtro por edad** ("Edad desde"/"Edad hasta") del panel de filtros de Pacientes (estado, `clearFilters`, UI y param en `patientApi.getAll`).
- ✅ Al seleccionar **Institución = IGSS** aparecen dos filtros condicionales: **Unidad IGSS** (selector, `filter-igss-unit`) y **NOG** (texto, `filter-igss-nog`). Al cambiar a otra institución se ocultan y se limpian.
- Backend (`routes/patients.py get_patients`): nuevo query param `igss_nog` (regex substring case-insensitive con `re.escape`). `igss_unit_id` ya existía.
- **Verificado**: backend por curl (unidad A=2, unidad B=2, NOG-2001=1, NOG-10 parcial=2) y **testing agent frontend 7/7 (100%, iteration_54.json)**: filtros de edad ausentes, aparición/ocultamiento condicional, filtrado por unidad y NOG (exacto y parcial), combinación unidad+NOG, limpiar filtros y exclusión de IGSS al elegir Particular. Datos de prueba (5 pacientes QA + unidad "Zona 5 QA") purgados. ESLint limpio. Requiere redespliegue para producción.



### Features/Fix (2026-06 Sesión 17) — Copiar permisos de rol base + nombre de Unidad IGSS con texto y números
- ✅ **1. Copiar permisos de un rol base al crear un rol personalizado**: en el diálogo "Nuevo Rol" (`Usuarios.js`) se agregó el selector **"Copiar permisos de"** (`select-copy-permissions`, solo al crear, oculto al editar). Lista roles de sistema + personalizados (filtra superadmin salvo para superadmin) más "Ninguno (partir de cero)". Al elegir uno se precargan sus `permissions` (editables antes de guardar) y se expanden las categorías con permisos activos. Verificado (copió 64 permisos, toast de confirmación).
- ✅ **2. Nombre de Unidad IGSS con texto y números, tal cual se escribe**: el código actual ya preservaba el nombre (probado por curl y UI: "Clínica Zona 5 Prueba 123" se guarda exacto). Como refuerzo: (a) input `unit-name-input` con `autoCapitalize="none"`, `autoCorrect="off"`, `spellCheck={false}` (evita auto-mayúsculas en móvil); (b) backend (`server.py` create/update) ahora escapa el regex del chequeo de duplicados con `re.escape(...)` y guarda `name.strip()` (solo recorta espacios extremos, NO cambia mayúsculas ni quita números). **El síntoma en producción se debía a un build anterior; requiere redespliegue.**
- ESLint limpio. Datos de prueba purgados.



### Bug fix (2026-06 Sesión 16) — Roles personalizados no aparecían al crear/editar usuarios
- 🐛 **Bug (producción)**: al crear un rol personalizado en Gestión de Usuarios → Roles, no aparecía como opción en el formulario de crear/editar usuario. Causa: en `Usuarios.js` el `Select` de rol tenía las opciones **hardcodeadas** (usuario, admin, optica, administrador_igss, superadmin) y además `roles` solo se cargaba en la pestaña "Roles". El backend YA aceptaba roles personalizados (`create_user`/`update_user` validan con `validar_rol_existe` contra `db.roles`).
- ✅ **Fix (solo frontend, `Usuarios.js`)**: (1) el dropdown de rol ahora se construye dinámicamente desde `rolesApi.getAll()` (sistema + personalizados), con etiqueta "(personalizado)" y filtrando `superadmin` salvo para superadmin; (2) `fetchRoles()` se ejecuta al montar (no solo en la pestaña Roles); (3) el badge del listado usa `display_name` del rol (fallback a nombre) y color por defecto, para que los roles personalizados no salgan en blanco. Mismo diálogo cubre crear y editar.
- **Verificado**: screenshot del diálogo "Nuevo Usuario" muestra las opciones: Super Administrador, Administrador, Usuario, Óptica, Administrador IGSS (personalizado), Enfermería (personalizado), QA Iter48 (personalizado). ESLint limpio. Requiere redespliegue para producción.



### Cambio de permisos (2026-06 Sesión 15) — El rol "usuario" AHORA puede modificar evaluaciones
- ✅ A pedido del usuario, se habilitó la **escritura de Evaluaciones Oftalmológicas para el rol `usuario`**.
- Backend (`routes/evaluaciones.py`): se añadió `"usuario"` a los 6 chequeos de escritura inline: crear (`POST ''`), editar (`PUT /{id}`), autoguardar (`PATCH /{id}/autoguardar`), actualizar historial médico, `agregar-medicamento-desde-receta` y `agregar-crm-cirugia`. **Eliminar** (`DELETE /{id}`) sigue restringido a **superadmin**; catálogos e import siguen en admin/superadmin.
- Frontend: `canEdit` en `EvaluacionOftalmologica.js` y `canCreateEvaluacion` en `Pacientes.js` ahora incluyen `usuario` (formulario editable, botón Guardar visible, botón "Crear evaluación" restaurado).
- **Verificado E2E**: curl como `usuario` → crear 200, PUT 200, PATCH autoguardar 200 (delete solo superadmin). UI como `usuario`: 37 campos editables + botón "Guardar" + 20 botones "Crear evaluación". ESLint limpio. Requiere redespliegue para producción.



### Verificación + fix UX (2026-06 Sesión 14) — El rol "usuario" NO puede escribir evaluaciones
- ❓ **Pregunta del usuario**: ¿el rol `usuario` puede escribir en las Evaluaciones Oftalmológicas? **Respuesta: NO.** Verificado con el testing agent (`/app/test_reports/iteration_53.json`, backend 4/4 pytest).
  - Backend (`routes/evaluaciones.py`): `POST /api/evaluaciones` y `PUT /api/evaluaciones/{id}` exigen rol `superadmin`/`admin`; el `usuario` recibe **403** ("No tiene permisos para crear/editar evaluaciones"). admin/superadmin → 200.
  - Frontend (`EvaluacionOftalmologica.js`): `canEdit = role superadmin|admin`; para `usuario` todos los campos quedan en **solo lectura** y NO se muestra el botón Guardar.
- ✅ **Fix UX** (`Pacientes.js`): el botón "Crear evaluación" (agregado en Sesión 10) aparecía para el rol `usuario` y lo llevaba a una pantalla donde no podía guardar. Ahora se muestra **solo a superadmin/admin** (`canCreateEvaluacion = role superadmin|admin`). Verificado por screenshot (usuario → 0 botones; sin regresión para admin).



### Feature (2026-06 Sesión 13) — Botón "Limpiar duplicados" de Google Calendar
- ✅ Nuevo botón **"Limpiar duplicados"** en el encabezado de la Agenda (solo SuperAdmin, junto a "Google Calendar", `agenda-limpiar-duplicados-btn`). Pide confirmación y elimina citas duplicadas que comparten el mismo `google_event_id`, **conservando una por evento**.
- Backend: `POST /api/google-calendar/limpiar-duplicados` (require_role superadmin). Agrupa por `google_event_id` (no vacío) y, en grupos con >1, conserva por prioridad: **Atendida/No asistió > con paciente vinculado > más antigua**; elimina el resto. Devuelve `{grupos_con_duplicados, citas_eliminadas}`. `googleCalendarApi.limpiarDuplicados` + `handleLimpiarDuplicados` en Agenda.js (toast con resumen, recarga).
- **Verificado (curl)**: 3 duplicados del mismo evento (uno vinculado a paciente) → elimina 2 y **conserva la vinculada**. UI: botón visible por screenshot. ESLint limpio. Requiere redespliegue para producción.



### Fix (2026-06 Sesión 12) — Google Calendar: no duplicar eventos al sincronizar
- 🐛 **Bug**: al "Actualizar" Google Calendar se duplicaban las citas. Causa: la deduplicación al importar dependía SOLO de la propiedad extendida `nova_cita_id`. En calendarios **compartidos** (sin permiso de edición) el `patch` que escribe esa etiqueta falla, así que cada sync volvía a ver el evento "sin etiqueta" y creaba otra cita.
- ✅ **Fix** (`routes/google_calendar.py` `_apply_event`): antes de crear una cita nueva, se busca una existente por **`google_event_id`**; si existe, se actualiza (fecha/hora) en vez de duplicar y se reintenta etiquetar el evento (mejor esfuerzo). Import ahora **idempotente** aunque el patch falle. Índice `citas_google_event` (sparse) agregado en `server.py`.
- **Verificado**: 3 syncs del mismo evento con `patch` fallando (calendario compartido simulado) → **1 sola cita** (import=1, luego 0/0). Backend OK. Requiere redespliegue para producción.



### Fix (2026-06 Sesión 11) — Desfase de -1 día en el texto de fecha (Agenda y Mi Agenda)
- 🐛 **Bug**: el input mostraba p.ej. 16/09/2026 pero el texto decía "martes 15 de septiembre". Causa: `formatDate` hacía `new Date("2026-09-16")` (medianoche UTC) y luego aplicaba `timeZone: 'America/Guatemala'` (UTC-6), retrocediendo al día anterior.
- ✅ **Fix** (`Agenda.js` `formatDate`): si el valor es una fecha `YYYY-MM-DD` (sin hora) se construye como **fecha local** (`new Date(y, m-1, d)`) y se formatea **sin** el override de zona, evitando el desfase. Los valores con hora conservan el comportamiento previo. Aplica tanto al encabezado del Calendario como al de "Mi Agenda" (`miAgenda.fecha`). Verificado por screenshot: input 16/09 → "miércoles, 16 de septiembre de 2026" en ambas vistas.



### Mejoras (2026-06 Sesión 10) — Cancelar llegada, fecha de Mi Agenda, crear evaluación desde Pacientes
- ✅ **1. Cancelar llegada (revertir "Presente" por error)**: en el panel "Pacientes Presentes en Clínica" (Tablero del Día y Mi Agenda) el menú de la tarjeta ahora tiene **"Cancelar llegada"** (`cancelar-llegada-{cita_id}`). Backend: al marcar `Presente` se guarda `estado_previo` (Agendada/Confirmada); nuevo endpoint `PATCH /api/agenda/citas/{id}/revertir-llegada` devuelve la cita a su estado original y limpia `hora_llegada`/`hora_inicio_consulta`/`asistio` (solo si está Presente/En consulta, si no 400). `agendaApi.revertirLlegada` + `handleCancelarLlegada` en Agenda.js. Verificado por curl (Presente→revertir→Agendada, 2º intento 400) y screenshot.
- ✅ **2. Fecha de "Mi Agenda" correlacionada**: `GET /api/agenda/mi-dia` ahora acepta `?fecha=YYYY-MM-DD` y por defecto usa **hoy en hora Guatemala (UTC-6)** (antes usaba UTC y siempre "hoy", ignorando la fecha de trabajo). `agendaApi.getMiDia(fecha)` y `fetchMiAgenda` pasan `fechaSeleccionada`. Verificado por curl (`?fecha=2026-09-14`→total 1, `?fecha=2025-01-01`→0).
- ✅ **3. Crear evaluación desde el listado de Pacientes**: nuevo botón **"Crear evaluación"** (ícono estetoscopio, `crear-evaluacion-patient-{id}`) entre "Ver detalle" y "Ver evaluaciones previas"; navega a `/evaluacion-oftalmologica?paciente_id={id}`. `EvaluacionOftalmologica.js` lee el query param con `useSearchParams`, hace `GET /api/patients/{id}`, calcula la edad y preselecciona al paciente (toast "Paciente cargado para nueva evaluación"). Verificado por screenshot (20 botones, navegación + paciente precargado).
- **NOTA**: cambios de preview; requieren REDESPLIEGUE para aplicar en producción. ESLint limpio.


### Mejoras (2026-06 Sesión 9) — Vincular citas de Google a pacientes + fix búsqueda multi-palabra
- ✅ **Cerrado el ítem en curso: vincular cita importada de Google (sin ficha) a un paciente**. En el diálogo "Editar Cita" de `Agenda.js`, si la cita no tiene `paciente_id` y proviene de Google, se muestra el banner `cita-google-ref` ("Cita de Google sin ficha. Texto original: ...") y el buscador de pacientes; al seleccionar un paciente se guarda `paciente_id` vía `PUT /agenda/citas/{id}` (preserva `google_event_id`). NOTA UX: en vista Día la cita se edita desde el menú "⋮" → "Editar cita" (el cuerpo de la tarjeta tiene `stopPropagation`).
- 🐛 **CAUSA RAÍZ corregida (bug que bloqueaba el vínculo)**: el buscador del diálogo usa `GET /api/patients/search?q=` (`patientApi.search`), un TERCER endpoint que NO tenía la búsqueda multi-palabra (solo se había aplicado a `/api/patients?search=` y `/api/pacientes/buscar?q=`). Resultado: `maria` devolvía 5 pero `maria garcia` devolvía 0, imposibilitando encontrar al paciente por su nombre completo. Se aplicó `build_patient_search_conditions` en `search_patients` (`routes/patients.py`). Verificado por curl: `maria garcia`/`garcia maria`/`lopez maria garcia` devuelven resultados en cualquier orden.
- **Verificado E2E**: curl (search multi-palabra + PUT vincular preserva google_event_id) y screenshots (diálogo con banner, búsqueda→3 opciones, selección, "Guardar cambios"→toast "Cita actualizada", tarjeta muestra el nombre del paciente). Dato de prueba purgado.


### Mejoras (2026-06 Sesión 8) — Agenda: resaltado al arrastrar, Semana por médico, sync automática GCal
- **Resaltado de slot destino** al arrastrar: estado `dragOverSlot`; los slots (Día y Semana-por-médico) se resaltan (`bg-blue-100 ring-2 ring-blue-400`) con `onDragEnter/onDragLeave`.
- **Vista Semana por médico**: en la vista "Semana", si el filtro de médico ≠ "todos", se muestra una **grilla por hora** (columna de horas × 7 días) del médico seleccionado, con click-para-agendar y drag&drop entre días/horas (`data-testid semanamed-slot-{diaISO}-{HH:MM}`). Con "todos" se mantiene el resumen semanal.
- **Sincronización automática Google Calendar**: job APScheduler `google_calendar_sync` cada 10 min en `server.py` (usa `run_sync_all()` refactorizado en `google_calendar.py`). Log al iniciar: "Google Calendar: cada 10min".
- **Verificado**: screenshot de la grilla Semana-por-médico; log del scheduler; ESLint limpio.


- **Click en slot**: en la vista Día, hacer clic en un horario vacío abre "Nueva Cita" prellenando médico + fecha + hora (`handleOpenCitaDialog(null, {medicoId, hora, fecha})`, `handleSlotClick`). Slots con `data-testid="slot-{medicoId}-{HH:MM}"` y pista "+ Agregar" al pasar el mouse.
- **Drag & drop**: cada cita es `draggable`; al soltarla en otro slot/columna se llama `PUT /agenda/citas/{id}` con nuevo `medico_id`/`hora_inicio`/`fecha` (`handleMoverCita`, recalcula `hora_fin` en backend). DnD nativo HTML5 (sin librerías).
- **Vistas Día/Semana/Mes**: selector (`data-testid vista-dia|semana|mes`). Día = columnas por médico con slots (existente). Semana = 7 columnas (Lun-Dom) con citas del día, clic en día → vista Día. Mes = grilla mensual con citas por celda (máx 3 + "+N más"), clic en día → vista Día. Semana/Mes usan `agendaApi.getCitasRango(desde,hasta)` (respuesta `{data,total}`).
- **Verificado**: screenshots de las 3 vistas y del diálogo prellenado al hacer clic en el slot 08:00; ESLint limpio. Drag&drop verificado a nivel de wiring + endpoint `updateCita` (el gesto real de arrastre no se automatizó).


- **Problema**: se forzaba un calendario nuevo y vacío "NovaVision - Citas", por lo que "Actualizar" no importaba nada (las citas reales estaban en el calendario principal/compartido del médico).
- **Cambios** (`routes/google_calendar.py`): al conectar, `calendar_id` por defecto = `"primary"` (ya no se crea/forzar "NovaVision - Citas"). Nuevos endpoints: `GET /api/google-calendar/calendars?doctor_id=` (lista TODOS los calendarios accesibles: propios y compartidos, principal primero) y `POST /api/google-calendar/select-calendar` (fija el calendario elegido y **reinicia `sync_token=None`** para releer todo desde hoy). Push y pull usan `gc.calendar_id` (o "primary"). El pull lee **desde el inicio de hoy** (hora Guatemala).
- **Frontend** (`GoogleCalendarDialog.js`): cada médico conectado muestra un **selector** con sus calendarios; al cambiarlo se llama `selectCalendar` (toast). `googleCalendarApi.getCalendars/selectCalendar` en `api.js`.
- **Verificado**: `select-calendar` actualiza `calendar_id`/`calendar_name` y resetea `sync_token` (curl); selector visible en el diálogo (screenshot, médico conectado simulado); ESLint limpio. Import real de eventos requiere que el médico complete el OAuth y se elija su calendario real.


- **Backend NUEVO** `routes/google_calendar.py` (registrado en `server.py`): OAuth 2.0 por médico conectado por SuperAdmin.
  - `GET /api/oauth/calendar/connect?doctor_id=` (superadmin) → URL de consentimiento (access_type=offline, prompt=consent, scope calendar). `GET /api/oauth/calendar/callback` → intercambia código, guarda tokens en `db.doctors.google_calendar`, crea calendario dedicado "NovaVision - Citas".
  - `GET /api/google-calendar/status` (superadmin), `POST /api/google-calendar/disconnect`, `POST /api/google-calendar/sync`.
  - **PUSH**: `crear/actualizar/cambiar_estado(Cancelada)/eliminar` cita en `agenda.py` llama a `push_cita`/`delete_cita_event` (try/except, nunca bloquea). Guarda `google_event_id` en la cita.
  - **PULL (bidireccional)**: `_sync_doctor` usa `events.list` con `syncToken` (resync completo ante 410). Eventos con `nova_cita_id` → refleja reprogramaciones y cancelaciones en la cita; eventos externos nuevos → crea cita ("origen_google", sin paciente, nombre = título) y etiqueta el evento con `nova_cita_id`.
- **Frontend**: `components/GoogleCalendarDialog.js` (superadmin: lista médicos, Conectar/Desconectar, última sync). En `Agenda.js` el botón **"Actualizar"** ahora ejecuta `googleCalendarApi.sync()` y luego recarga (toast con importadas/actualizadas/canceladas); botón "Google Calendar" (superadmin); aviso al volver de OAuth (`?gcal=connected|error`). `googleCalendarApi` en `api.js`.
- **Credenciales**: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, `APP_PUBLIC_URL` en `backend/.env` (preview). Redirect URI: `.../api/oauth/calendar/callback`.
- **Verificado**: endpoints (status/connect/sync) responden OK; UI (botón + diálogo con médicos y "Conectar") verificada por screenshot; ESLint limpio. PENDIENTE por el usuario: completar el consentimiento OAuth de cada médico (su Gmail debe estar como "usuario de prueba" en la pantalla de consentimiento) para activar el push/pull real. Para PRODUCCIÓN: registrar la redirect URI del dominio productivo y definir estas env vars allí.


- **Problema**: buscar "Juan Pérez" no encontraba al paciente porque el texto completo se buscaba dentro de un solo campo (nombre o apellido).
- **Solución** (`routes/patients.py`, helper `build_patient_search_conditions`): el texto se separa en palabras; cada palabra debe aparecer en el nombre O el apellido (en cualquier orden), sin distinguir mayúsculas/acentos (reutiliza `generate_accent_regex`). Se combinan con AND (todas las palabras). Se mantiene la coincidencia por expediente, DPI y teléfono con el texto completo (`re.escape`). Aplicado en AMBOS buscadores: listado `GET /api/patients?search=` y autocompletado `GET /api/pacientes/buscar?q=`. El autocompletado subió su tope por defecto de 10 → 50.
- **Verificado (curl)**: 'juan perez' y 'perez juan' devuelven lo mismo (orden independiente); cruza campos ('garcia carlos' → "Juan Carlos López García"); 'PEREZ' insensible a acento/mayúsculas; búsqueda por teléfono y expediente OK. Datos de prueba purgados.


- **Bug 1 (Caja → Pacientes)**: la ruta `/caja` en `App.js` exigía el permiso equivocado `view_payment_authorizations` (que es de "Autorizaciones de Pago"); al no tenerlo, `ProtectedRoute` redirigía a `/pacientes`. Corregido a `requiredPermission="manage_caja"` (consistente con el backend de Caja).
- **Bug 2 ("configure bodegas" con 3 bodegas)**: `obtener_bodega_pos` en `routes/ventas.py` filtraba `activo: True` de forma estricta e ignoraba bodegas creadas sin el campo `activo` (por seed/import). Ahora usa `activo: {$ne: False}` y trata el campo ausente como activo. Además el POS respondía 403 (sin `manage_sales`) que el frontend mostraba como "Sin Bodega Configurada".
- **Decisión del usuario (opción a)**: se concedió al rol `usuario` los permisos `manage_sales`, `manage_caja` y `view_inventory` (para leer categorías del POS). IMPORTANTE: existen DOS matrices de permisos que deben mantenerse sincronizadas: `server.py` `_MODULE_PERMS` y `config/permissions.py` `_MODULE_PERMS` (el router de Caja usa `routes/auth.py`→`config.permissions`; ventas/`/auth/me` usan `server.py`). Se actualizaron ambas.
- **UX**: `PuntoVenta.js` ahora distingue 403 (muestra "Sin permiso para el Punto de Venta") de 404/sin bodega.
- Verificado: como `usuario`, `ventas/bodega-pos`, `caja/estado`, `inventario/categorias`, `ventas/productos-rapidos` → 200; UI de `/caja` y `/punto-venta` cargan correctamente. Requiere REDESPLIEGUE para aplicar en producción.


- ✅ **Cambio de contraseña por el propio usuario**: en el área del menú de usuario del sidebar (`Layout.js`) se agregó el botón **"Cambiar contraseña"** (sobre "Cerrar sesión", `data-testid=change-password-button`), disponible para TODOS los roles. Abre `components/ChangePasswordDialog.js` (contraseña actual + nueva + confirmar, con ver/ocultar y validación de política). Usa el endpoint EXISTENTE `POST /api/security/change-password` (verifica actual, política: ≥8 chars con mayúscula/minúscula/número, rechaza igual a la actual, resetea `must_change_password`; no bumpea token_version por lo que la sesión actual sigue válida). Nueva función `changePassword` en `AuthContext`. Verificado por curl (200, token vigente, login con nueva, 400 en actual incorrecta/débil/igual) y screenshot del diálogo. NOTA: se reutilizó el endpoint inline de `server.py` (el router `routes/auth.py` NO se incluye; sus rutas son solo referencia de helpers).

- ✅ **NUEVO módulo NOG por Unidad IGSS** (sin menú nuevo: vive dentro de cada Unidad IGSS). Cada NOG = contrato de servicios del IGSS (numero, nombre_servicio, tipo_compra, **cantidad** contratada = límite, **precio** unitario) con derivados: acreditados, disponibles, porcentaje, estado y valores en Q (total/acreditado/disponible).
  - Backend NUEVO `routes/igss_nogs.py` (router prefix `/igss-units`): `GET/POST /{unit_id}/nogs`, `GET /{unit_id}/nogs-activos` (selector ligero, cualquier autenticado), `PUT/DELETE /nogs/{nog_id}`, `POST /nogs/{nog_id}/recalcular`, `GET /nogs/{nog_id}/pacientes`, `POST /nogs/{nog_id}/acreditaciones/{acred_id}/anular`, `GET /nogs/{nog_id}/export/excel`, `GET /{unit_id}/nogs/export/excel`. Todo lo de gestión exige permiso `manage_igss_units` (SuperAdmin + Administrador IGSS).
  - **Conteo de servicios (decisiones del usuario)**: se acredita **1 por CADA atención/evaluación** (no 1 por paciente). El disparador es la **creación de la Evaluación Oftalmológica** (hook `_acreditar_evaluacion` en `evaluaciones.py` create_evaluacion, envuelto en try/except → la clínica NUNCA se bloquea). **Guarda atómica** (`update_one {acreditados:{$lt:cantidad}} $inc`) evita sobregiro incluso en concurrencia. **Aviso al 90%** (estado `por_completarse`) y **bloqueo al 100%** (estado `completado`, no acredita más). Dedup por `(nog_id, evaluacion_id)`.
  - **Conteo retroactivo** automático al crear un NOG (`_sincronizar_acreditaciones`, respeta el cupo). **Recalcular** idempotente (para drift tras importaciones) que respeta anulaciones. **Anular** una acreditación libera el cupo (queda disponible).
  - Colecciones nuevas: `igss_nogs` (índice único `(unidad_id, numero)`) y `igss_nog_acreditaciones` (índices por nog/eval/paciente). Registradas en `server.py` (include_router + índices en startup).
  - Frontend: `components/NogsUnidadDialog.js` (diálogo de gestión por unidad: métricas, tabla con barra de avance + estado, crear/editar/eliminar NOG, expandir para ver pacientes acreditados + anular, exportar por NOG y por unidad, recalcular). `components/NogSelector.js` (en la ficha del paciente el campo NOG es selector de NOG de la unidad + opción **texto libre**; los completados no se pueden elegir para pacientes nuevos). Botón "NOG" por unidad en `UnidadesIGSS.js`. `igssNogApi` en `api.js`.
  - Listados y exportaciones consideran **solo pacientes activos**. Columnas de export por paciente: expediente, nombre y apellido, DPI, afiliación IGSS, No. SPS, código, tipo de compra, teléfono, edad, NOG y fecha de acreditación (encabezado con servicio/tipo/cantidad/precio/acreditados/disponibles/valores).
  - **Verificado E2E (testing agent, `/app/test_reports/iteration_52.json`): backend 12/12 PASS, frontend 100%, 0 issues.** Datos de prueba purgados del preview.
  - ✅ **Tarjetas de resumen en el catálogo**: `GET /api/igss-units/nogs/resumen` (permiso `manage_igss_units`) devuelve totales globales (nogs_disponibles, servicios_disponibles/acreditados/contratados, valor). En `UnidadesIGSS.js` la fila superior del Catálogo ahora tiene 3 tarjetas: **Total Unidades IGSS**, **NOG disponibles** (sublabel: servicios disponibles) y **Servicios acreditados** (sublabel: de N contratados). Se refresca junto con las alertas (`alertReload`). Verificado por curl y screenshot.
  - ✅ **Alertas de límite de NOG**: `GET /api/igss-units/nogs/alertas` (permiso `manage_igss_units`) devuelve los NOG activos al **90%+** (`por_completarse`) y al **100%** (`completado`), ordenados (completados primero). Banner reutilizable `components/NogAlertasBanner.js` (autoabastecido del endpoint; `onVer` configurable; `reloadSignal` para refrescar). Se muestra en la parte superior de `UnidadesIGSS.js` (el "Ver" abre el diálogo de la unidad y **expande** ese NOG vía `initialNogId`) y también en el **Dashboard principal del SuperAdmin** (`Dashboard.js`), donde "Ver" **navega** a `/configuracion/unidades-igss?nogUnidad=&nog=&nombre=` y auto-abre el diálogo (query params leídos en UnidadesIGSS y limpiados con navigate replace). Verificado por curl (completado+90% listados, normal excluido, igss.admin 200 / optica 403) y screenshots (banner en Dashboard + navegación/auto-apertura, desktop 1920 y móvil 390).


### Últimos Cambios (2026-06 Sesión 7) — Reporte por Unidad IGSS
- ✅ **NUEVO Reporte por Unidad IGSS**: pestaña "Reporte" dentro de `/configuracion/unidades-igss` (`UnidadesIGSS.js`) junto a "Catálogo". Muestra por cada unidad: nombre, código, estado (activa/inactiva), **# pacientes** y **# evaluaciones**, más tarjetas de totales y un renglón "Sin unidad IGSS asignada". Botón "Exportar CSV".
  - Backend: `GET /api/igss-units/reporte` (permiso `manage_igss_units`; accesible a SuperAdmin y Administrador IGSS). Definido ANTES de `/igss-units/{unit_id}` para no chocar con la ruta paramétrica.
  - Cálculo eficiente (sin N+1): 1 lectura de unidades + 1 de pacientes (campos mínimos, mapa paciente→unidad) + 1 agregación de evaluaciones agrupadas por `paciente_id`. Las evaluaciones se atribuyen a la unidad del paciente (evaluaciones → paciente_id → patient.igss_unit_id). Oculta unidades inactivas sin datos.
  - `igssUnitApi.getReporte()` agregado en `api.js`.
  - Verificado E2E (curl + UI): atribución correcta (demo temporal revertida: unidad con 1 paciente/5 evaluaciones; "sin unidad" 49/1), ruta `/{unit_id}` intacta (404 para inexistente), acceso `igss.admin` 200.

- ✅ **NUEVO rol "Administrador IGSS"** (`administrador_igss`, personalizado/editable desde Usuarios → Roles). Se siembra en `server.py` startup (crear-si-no-existe) con base: `manage_igss_units` + pacientes (ver/crear/editar/importar/exportar). El SuperAdmin puede ajustar sus permisos eligiendo del catálogo existente (`GET /roles/available-permissions`).
- ✅ **Menú "Unidades IGSS" ahora configurable por rol**: agregado `unidades_igss` a `AVAILABLE_MENUS` (`menu_config.py`, categoría Configuración). El configurador "Menús por Rol" (`/usuarios` → pestaña Menús por Rol) ahora **soporta roles personalizados** (antes estaba limitado a 4 roles fijos): nuevo helper `_get_configurable_roles()` usado en `available-menus`, `role/{role}`, `all-roles`, `PUT role/{role}` y `reset/{role}`. Default para `administrador_igss`: `["pacientes","unidades_igss"]`.
- ✅ **Visibilidad de Unidades IGSS**: en `Layout.js` el enlace dejó de estar limitado a `isSuperAdmin`; ahora aparece si `isMenuEnabled('unidades_igss') && hasPermission('manage_igss_units')`. SuperAdmin lo sigue viendo (tiene todos los menús + permiso); otros roles lo ven solo si se activa en "Menús por Rol" y tienen el permiso.
- ✅ **Fix guard de página**: `UnidadesIGSS.js` bloqueaba con "Acceso Restringido" a todo lo que no fuera `superadmin`. Cambiado a chequeo por permiso `manage_igss_units` (SuperAdmin conserva acceso). Sin esto, el nuevo rol veía el menú pero no podía abrir la página.
- ✅ Frontend: `roleLabels` (api.js) y `roleColors`/`getRoleIcon` (Usuarios.js) incluyen `administrador_igss`; el selector de rol del formulario de usuario permite asignarlo; el dropdown de Menús por Rol usa fallback `roleLabels[role] || role` para roles personalizados.
- ✅ Verificado E2E: `GET /roles` lo lista (is_system=false), `available-menus`/`all-roles` lo incluyen, login `igss.admin` → permisos correctos (manage_igss_units=True, inventario=403, pacientes=200), `/my-menus` = [pacientes, unidades_igss], POST /igss-units=200. Frontend: sidebar muestra Unidades IGSS y la página abre el catálogo (antes "Acceso Restringido"). Usuario de prueba: `igss.admin / IgssAdmin2024`.

- ✅ **NUEVO: "Ver evaluaciones previas" en el módulo de Pacientes**: cada fila de la tabla de pacientes tiene un botón (icono portapapeles, `data-testid=evaluaciones-patient-{id}`) que abre un diálogo de SOLO LECTURA con TODAS las evaluaciones del paciente. Componente autocontenido `frontend/src/components/EvaluacionesPacienteDialog.js` (usa `GET /evaluaciones?paciente_id=` y `GET /evaluaciones/{id}`; descarga PDF con `GET /evaluaciones/{id}/pdf`).
  - Vista LISTA: fecha (DD/MM/YYYY), badge "Sellado", diagnóstico principal (+N más), médico, y acciones Ver/PDF por evaluación. Estado vacío cuando no hay evaluaciones.
  - Vista DETALLE (al pulsar "Ver"): datos de consulta, diagnósticos con CIE10 y ojo, examen oftalmológico (AV s/c y c/c, PIO, segmentos, motilidad, pupilas), recetas de anteojos (OD/OS esfera/cilindro/eje/adición + tipo/material/DP), recetas de lentes de contacto, medicamentos y plan/recomendaciones. Botón "Descargar PDF completo".
  - No se modificó el editor de 3.000 líneas (no soporta deep-linking); la revisión es independiente y de solo lectura. Verificado E2E (desktop + móvil 390px sin overflow): la receta migrada se muestra correctamente en el detalle.

- ✅ **Migración de recetas legacy EJECUTADA** (`backend/scripts/migrar_recetas_legacy.py`):
  - 🐛 El script apuntaba a la colección equivocada `db.evaluaciones`; **corregido a `db.evaluaciones_oftalmologicas`** (la real).
  - Ejecutado en preview (DB `test_database`): 1 receta de anteojos migrada al array `anteojos_lista` (paciente María García López), 3 evaluaciones inicializadas con `anteojos_lista` vacía y 4 con `lentes_contacto_lista` vacía. 0 errores. Idempotente (2ª corrida = 0).
- ✅ **Fix crítico del `response_model` de evaluaciones**: el modelo Pydantic `Recetas` (`models/evaluacion_oftalmologica.py`) NO declaraba `anteojos_lista`/`lentes_contacto_lista`, por lo que el `response_model` de `GET /evaluaciones/{id}` **descartaba silenciosamente las recetas migradas/importadas** (dejaba las listas vacías). Esto rompía las evaluaciones IMPORTADAS con múltiples recetas (donde solo existe la lista, no el objeto legacy). Añadidos ambos campos como `List[dict]`. Verificado: `GET /{id}` ya devuelve `anteojos_lista` completo (id, od.esfera -1.50, material, `migrado_de_legacy`). El objeto legacy `anteojos` se sigue preservando (fallback del frontend intacto).
- ✅ **Optimización rendimiento — caché de permisos por rol** (`config/permissions.py`): `resolve_permissions` se llamaba en CADA request autenticado → lectura a `db.roles`. Ahora usa caché en memoria por rol con TTL de 10s (`_PERM_CACHE_TTL`). `superadmin` sigue devolviendo la matriz estática sin tocar DB. Se invalida al instante al crear/editar/eliminar/resetear roles (`invalidate_permissions_cache` en `routes/roles.py`). Verificado: login superadmin (33 permisos), `/me` 200, inventario superadmin 200, óptica 403 (RBAC intacto).
- ✅ **Optimización rendimiento — índice TTL en `token_blacklist`** (`server.py` startup): antes había un índice simple sobre `expires_at` y `expires_at` se guardaba como STRING ISO (TTL no funciona sobre strings). Ahora `blacklist_token` guarda `expires_at` como `datetime` (BSON date), backfill convierte las entradas antiguas de string→date y marca las legadas sin campo, y se crea índice TTL `blacklist_ttl` (`expireAfterSeconds=0`). MongoDB purga automáticamente los tokens expirados. `cleanup_expired_tokens` (backup, cada 6h) ahora compara datetime. Verificado: índice TTL presente, 5/5 entradas con fecha.


### Últimos Cambios (2026-06 Sesión 6) — Auditoría de Seguridad AppSec
- ✅ **Optimización de rendimiento (para ~10 usuarios concurrentes)**:
  - 🔴 Faltaban índices sobre el campo `id` (uuid) en TODAS las colecciones → COLLSCAN en cada búsqueda/edición por id (a escala: ~100ms/paciente con 17k, ~400ms/eval con 68k). Agregados índices `id_lookup` a 40 colteciones + `roles_name` + `eval_import_source` en el startup de `server.py`. Verificado: ahora IXSCAN.
  - 🟠 N+1 en `GET /inventario/productos` (llamaba `obtener_existencia_total` por producto). Nuevo helper `obtener_existencias_totales` (1 sola consulta). Medido: **49→172 req/s, p50 215ms→55ms** (~4x). Existencias verificadas consistentes.
  - Mongo es local (ping 0.5ms); pool por defecto (maxPoolSize 100) ok para 10 usuarios. Concurrencia 10 usuarios: ~170-195 req/s, p95 ~67ms, 0 errores.
  - Recomendaciones pendientes: producción con múltiples workers sin `--reload`; caché corta de permisos por rol; TTL en `token_blacklist`.
- ✅ **Bug "Nueva Cita" (Agenda)**: el buscador mostraba "Exp: N" sin nombre y "undefined undefined" al seleccionar. Doble causa: (a) frontend leía `first_name`/`last_name` pero `/patients/search` devuelve `full_name` (corregido en `Agenda.js`); (b) **CRÍTICO** `/patients/search` lanzaba `KeyError('phone')` (500) con pacientes importados sin teléfono — bloqueaba TODA búsqueda de pacientes (Agenda y Evaluación); corregido con `.get()` en `record_number/first_name/last_name/phone` (`patients.py`). Verificado por agente (`iteration_51.json`) + curl.
- ✅ **Autoguardado no crea borradores vacíos**: guard `tieneDatosClinicos()` en `EvaluacionOftalmologica.js` (no crea evaluación nueva si no hay datos clínicos reales).
- ✅ **Limpieza de vacías**: endpoints `GET /api/evaluaciones/vacias/contar` y `DELETE /api/evaluaciones/vacias/purgar` (admin/superadmin; no toca selladas ni importadas) + botón "Limpiar vacías" con confirmación (toast). Verificado por curl (cuenta/purga correctas, optica 403) y agente.
- ✅ **Fix Historial de Evaluaciones**: el menú "Historial" mostraba evaluaciones de TODOS los pacientes (usaba `GET /evaluaciones?limit=50` global). Ahora se acota al paciente cargado (`?paciente_id=`), ordenado por fecha clínica desc; se limpia al iniciar "Nueva" o sin paciente. **Historial enriquecido**: cada fila muestra fecha DD/MM/YYYY + diagnóstico principal (array `diagnosticos`, con "+N más" y "Sin diagnóstico registrado"). data-testids: historial-toggle-btn, historial-item/fecha/dx-{id}. **Verificado por agente de pruebas: frontend 100% (`/app/test_reports/iteration_50.json`)**. Es fix de frontend: llega a producción al redesplegar.
- ⚠️ **Hallazgo (pendiente):** el autoguardado crea evaluaciones VACÍAS ("Sin diagnóstico registrado", fecha de hoy) con solo abrir/editar el formulario, lo que ensucia el historial. Conviene que el autoguardado se salte cuando no hay datos significativos.
- ✅ **Importador masivo de EVALUACIONES** (nuevo): endpoints `POST /api/evaluaciones/import/validate`, `POST /api/evaluaciones/import/batch`, `GET /api/evaluaciones/import/template` + página `/importar-evaluaciones` (ImportarEvaluaciones.js, guard de ruta `requiredPermission="import_patients"`). Enlaza cada evaluación con su paciente por `expediente` (record_number) o `dpi`; deduplica por `id_origen`; normaliza fechas; guarda recetas en arrays (`anteojos_lista`/`lentes_contacto_lista`). Solo admin/superadmin. **Validado por agente de pruebas: backend 12/12 pytest, frontend 100% (`/app/test_reports/iteration_49.json`).**
- ⚠️ Durante los tests la contraseña de superadmin quedó alterada; se **restauró a `nova2024`** y se limpiaron los contadores de bloqueo de superadmin/admin/optica.
- ✅ **Script de carga masiva** `backend/scripts/importar_evaluaciones_masivo.py` (solo Python 3 stdlib): login + validación + importación por lotes con reintentos, manejo de rate limit, resumen final y archivo de huérfanas. Probado contra el backend (login, validate, batch). Plantilla `GET /api/evaluaciones/import/template` ampliada con `diccionario_campos` (referencia completa de campos).
- ✅ **Auditoría AppSec completa + remediación** (blindaje de accesos/permisos). Informe: `/app/docs/SECURITY_AUDIT_2026-06.md`
  - SEC-001 (JWT): eliminados fallbacks de secreto embebidos; guarda de arranque ABORTA en producción si el secreto es conocido/corto. **Secreto JWT ROTADO** a valor aleatorio de 88 chars (tokens con el secreto anterior → 401). Rotación invalidó sesiones activas (re-login).
  - SEC-002: Laboratorio de Pruebas ahora exige SuperAdmin autenticado + no-producción (dependencia `verificar_acceso_laboratorio`).
  - SEC-003: Autorización por módulo (inventario `view_inventory`/`manage_inventory`, POS `manage_sales`, caja `manage_caja`). superadmin/admin con acceso; usuario/optica sin acceso a módulos clínicos.
  - SEC-004: Blacklist persistente unificada (`db.token_blacklist`) + `token_version` verificado en `get_current_user` + backfill legado.
  - SEC-005: Seed de usuario `optica` con `must_change_password` y campos de seguridad (solo nuevos despliegues).
  - RBAC gap: `resolve_permissions()` async lee `db.roles` (deny-by-default); `POST/PUT /api/users` permite roles personalizados con validación.
  - Validado: 25/25 pytest AppSec (`/app/test_reports/iteration_48.json`) + curl + navegación E2E (SuperAdmin y Óptica).
- ✅ **Bug de Pacientes corregido**: `GET /api/patients` devolvía 500 (ResponseValidationError) por documentos antiguos con campos faltantes. Se hicieron opcionales los campos del modelo `PatientResponse` (sin mutar datos). Verificado: 200 con 34 pacientes.
- ✅ **Verificación E2E de permisos de roles** (inicio de sesión): `/app/test_reports/iteration_47.json`
- ✅ **Fix motor ESLint**: creado `/app/frontend/eslint.config.js` (config plana ESLint 9).

### Últimos Cambios (2026-08-26 Sesión 5)
- ✅ **Módulo Completo de Sociedades Médicas** (`/sociedades`)
  - CRUD de Sociedades: Crear, editar, eliminar sociedades médicas con campos (nombre, descripción, NIT, teléfono, email, contacto, dirección, color identificador)
  - 4 pestañas: Sociedades, Consumos, Productos, Resumen mensual
  - Asignación de productos a sociedades específicas mediante dropdown en formulario de productos
  - Contador de productos asignados por sociedad
  - Exportación PDF y Excel de consumos
  - API: `/api/inventario/sociedades/catalogo` (CRUD), `/sociedades/productos`, `/sociedades/consumos`, `/sociedades/resumen`, `/sociedades/exportar/excel`, `/sociedades/exportar/pdf`
- ✅ **Bug Fix**: Campos `es_sociedad` y `sociedad_id` ahora se devuelven correctamente en GET `/api/inventario/productos` y GET `/api/inventario/productos/{id}`
- ✅ **Dropdown de Sociedad en Productos**: Al activar el switch "Sociedad" aparece un selector para elegir la sociedad médica a la que pertenece el producto

### Últimos Cambios (2026-08-26 Sesión 4)
- ✅ **Configuración Dinámica de Menús por Rol** (`/usuarios` - Tab "Menús por Rol")
- ✅ **CRUD de Roles Personalizados** (`/usuarios` - Tab "Roles")
- ✅ **Campo "Sociedad" en Productos** - Switch para marcar productos de sociedades médicas
- ✅ **Superadmin puede modificar cantidades** - Endpoint de ajuste ya existente solo para superadmin

### Cambios Previos (2026-08-26 Sesión 3)
- ✅ **Campo "Precio de Compra" agregado a Productos de Inventario**
  - Nuevo campo `precio_compra` en formulario de Nuevo/Editar Producto
  - Backend actualizado: Modelos Pydantic (`ProductoBase`, `ProductoUpdate`, `ProductoResponse`)
  - Soporte en importación Excel (columna `precio_compra`)
  - Plantilla CSV actualizada con el nuevo campo
- ✅ **Cálculo de Margen en Tiempo Real**
  - Indicador visual en el formulario de producto al editar precios
  - Muestra: Margen %, Ganancia por unidad (Q), Markup sobre costo
  - Colores: Verde (≥30%), Amarillo (15-30%), Rojo (<15%)
- ✅ **Columna de Rentabilidad en Tabla de Productos**
  - Columna "P. Compra" agregada a la tabla
  - Margen calculado en base a precio de compra (no costo promedio)
  - Código de colores para identificar rápidamente rentabilidad
- ✅ **Reporte de Rentabilidad por Categoría** (`/inventario/rentabilidad`)
  - Vista completa con resumen general: margen promedio, ganancia potencial, valor inventario
  - Tabla detallada por categoría: margen promedio, mín, máx, ganancia/unidad, valores
  - Barra de progreso visual para cada categoría
  - Estados: Excelente (≥40%), Bueno (30-39%), Regular (20-29%), Bajo (10-19%), Crítico (<10%)
  - Exportación a CSV
  - Toggle "Solo con stock" para filtrar productos con existencias
- ✅ **Gráfica de Evolución Histórica de Rentabilidad**
  - Tab "Evolución Mensual" con datos de ventas mes a mes
  - Gráfica combinada: Línea de Margen % + Área de Ganancia Neta
  - Gráfica de barras: Ingresos vs Costos Mensuales
  - Indicadores de tendencia (creciente/estable/decreciente) y variación último mes
  - Tabla de detalle mensual con ventas, productos, ingresos, costos, ganancia, margen
  - Selector de período (6, 12, 18, 24 meses)
  - Exportación CSV del histórico
- ✅ **Corrección de bugs detectados en evaluación**
  - Fix: Método `getProveedores` agregado a `inventarioApi` en api.js
  - Fix: Gráficas recharts solo se renderizan cuando el tab está activo (evita warning width=-1)
- ✅ **Dashboard Completo de Óptica** (`/optica/dashboard`)
  - Tab Resumen: Ventas del día, historial de ventas y compras (12 meses)
  - Tab Rentabilidad: Margen por período (día/semana/mes/año), desglose por categoría (Aros, Lentes Contacto, Lentes Oftálmicos)
  - Tab Por Origen: Gráfica pastel de distribución, detalle por origen (Particular, IGSS, Seguro Privado, Otras), desglose por unidad IGSS
  - Tab Informes: Informe mensual completo (ventas, compras, balance), Top 10 productos vendidos, exportación CSV
  - Endpoints backend: `/optica/dashboard/ventas-dia`, `/optica/dashboard/rentabilidad`, `/optica/dashboard/ventas-por-origen`, `/optica/dashboard/informe-mensual`, `/optica/dashboard/historial-mensual`
- ✅ **Restricción de Dashboards a SuperAdmin**
  - Dashboard del Sistema (`/dashboard`): Solo SuperAdmin
  - Dashboard Financiero (`/dashboard-financiero`): Solo SuperAdmin
  - Dashboard de Óptica (`/optica/dashboard`): Solo SuperAdmin
  - Reporte de Rentabilidad Inventario (`/inventario/rentabilidad`): Solo SuperAdmin
  - Usuarios no-superadmin son redirigidos a `/pacientes` por defecto
  - Menú lateral oculta enlaces de dashboards para roles no autorizados

### Cambios Previos (2026-08-19 Sesión 2)
- ✅ **P0 Verificado**: Integración completa de Bodegas en todo el sistema de inventario
  - `Bodegas.js` - UI CRUD completa para gestión de almacenes
  - `Productos.js` - Entrada Rápida con selector de bodega
  - `Lotes.js` - Filtro por bodega funcional
  - `Movimientos.js` - Filtro por bodega funcional
  - `PuntoVenta.js` - Usa bodegaPOS configurada
- ✅ **Zona Horaria Guatemala (UTC-6)**: Sistema corregido para mostrar fechas/horas en horario local
  - Funciones `formatDate`, `formatDateTime`, `formatTime` actualizadas con `timeZone: 'America/Guatemala'`
  - Todas las llamadas `toLocaleString`, `toLocaleDateString`, `toLocaleTimeString` actualizadas
  - `Caja.js` y `PuntoVenta.js` usan `formatTime()` para mostrar horas correctamente

### ✅ Funcionalidades Completadas

#### Core
- [x] Autenticación JWT con roles (superadmin, admin, usuario, optica)
- [x] Dashboard con estadísticas y alertas
- [x] Gestión de Pacientes con campos IGSS (NOG, afiliación, unidad, etc.)
- [x] Importación masiva de pacientes (JSON/Excel)
- [x] Plantillas Excel descargables

#### Seguridad (Fase 1 - AppSec)
- [x] Headers de seguridad (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, CSP)
- [x] Rate limiting en login (5 intentos/minuto con bloqueo de 15 min)
- [x] Bcrypt con costo 12 para hashing
- [x] Flag `must_change_password` para usuarios sembrados
- [x] Timeout de inactividad de 30 minutos con advertencia modal
- [x] Token blacklist persistente en MongoDB
- [x] Panel de alertas de seguridad para SuperAdmin

#### Agenda
- [x] Calendario con múltiples médicos
- [x] Creación/edición de citas con campos separados (nombre, apellido, género obligatorio)
- [x] Estados de citas (pendiente, confirmada, en sala, atendida, cancelada)
- [x] WebSocket para actualizaciones en tiempo real (opcional)

#### Evaluación Oftalmológica
- [x] Formulario completo con todas las secciones clínicas
- [x] Soporte offline con LocalStorage
- [x] Autoguardado cada 30 segundos
- [x] Plantilla Excel con variables de evaluación

#### Finanzas
- [x] Módulo Caja con apertura/cierre de sesiones
- [x] Movimientos de ingresos/egresos
- [x] Historial de cierres con arqueo
- [x] WebSocket para actualizaciones en tiempo real (opcional)
- [x] **Cuentas por Cobrar Clínica** (`/cuentas-cobrar-finanzas`) - CxC con responsables configurables:
  - Médico, Institución, Seguro, Convenio, IGSS, Otro
  - Catálogo de responsables CRUD
  - Filtros por tipo de responsable y estado
  - Registro de abonos parciales/totales

#### POS (Punto de Venta)
- [x] Integración con inventario FEFO
- [x] Carrito de compras touch-friendly
- [x] Métodos de pago múltiples
- [x] Bloqueo de ventas con caja cerrada

#### Inventario
- [x] Control de lotes con FEFO (First Expire First Out)
- [x] Multi-almacén (Bodegas)
- [x] **Gestión de Bodegas** (`/inventario/bodegas`) - CRUD completo 2026-08-19
  - [x] Crear/Editar/Eliminar/Desactivar bodegas
  - [x] Filtros de búsqueda y toggle de inactivas
  - [x] Integración en Productos, Lotes, Movimientos y POS
- [x] **Precio de Compra en Productos** - 2026-08-26
  - [x] Campo `precio_compra` en formulario de productos
  - [x] Soporte en importación Excel
- [x] Kardex inmutable
- [x] Alertas de stock bajo y vencimiento

#### Óptica (Módulo Separado)
- [x] Inventario de aros (`optica_frames`)
- [x] Lentes de contacto (`optica_contact_lenses`)
- [x] Tipos de lente (`optica_lens_types`)
- [x] Ventas de óptica (`optica_sales`) - Colecciones SEPARADAS de clínica
- [x] **Punto de Venta Óptica** (`/optica/punto-venta`) - Interfaz POS dedicada
  - [x] Categoría unificada "Lentes" con filtro (Contacto/Oftálmico/Todos) - 2026-08-19
  - [x] Precios de lentes oftálmicos visibles (mapeo default_price → sale_price)
  - [x] Lentes de contacto seleccionables (lens_type opcional)
- [x] **Gestión de Lentes de Contacto** (`/optica/lentes-contacto`) - 2026-08-19
  - [x] CRUD completo de lentes de contacto
  - [x] Campos: tipo, marca, nombre, descripción, precio costo, precio venta, stock
  - [x] Filtros por tipo de lente y stock bajo
- [x] **Cuentas por Cobrar Óptica** (`/optica/cuentas-cobrar`) - CxC vinculadas al paciente/cliente
- [x] **NOTA CRÍTICA**: Óptica NO usa Kardex inmutable ni sistema de bodegas

#### CRM Cirugías
- [x] Pipeline de seguimiento de pacientes quirúrgicos
- [x] Estados configurables

#### Laboratorio de Pruebas E2E (NUEVO)
- [x] Panel accesible solo para SuperAdmin en ambiente de desarrollo
- [x] Seed de Datos Maestros (Fase 1): Bodegas, Proveedores, Productos, Usuarios, Médicos
- [x] Seed de Pacientes (Fase 2): 14 pacientes con perfiles específicos
- [x] Función de Purga: Elimina todos los datos con `esDatoPrueba: true`
- [x] Ruta en frontend: `/laboratorio-pruebas`
- [x] Bloqueo en producción vía `NODE_ENV`/`ENVIRONMENT`
- [x] **Pruebas de Transacción (NUEVO)**:
  - Apertura/cierre de caja de prueba
  - 4 tipos de ventas POS (simple, múltiple, con descuento, pago mixto)
  - Movimientos de caja (ingresos/egresos)
  - Verificación de kardex e integridad
  - Verificación de totales de caja
  - **Pruebas de Devolución (NUEVO)**:
    - Anulación con devolución de inventario (TRX-12)
    - Anulación SIN devolución (TRX-13)
    - Verificación de reversión en kardex (TRX-14)
    - Verificación de totales post-anulación (TRX-15)
  - 15 pruebas que validan el flujo financiero completo

#### Optimizaciones
- [x] GZIP Middleware
- [x] Headers de caché para assets estáticos
- [x] Índices compuestos en MongoDB
- [x] ErrorBoundary global en React
- [x] Performance tests (scripts en /backend/scripts/)
- [x] **Zona Horaria Guatemala (UTC-6)** - 2026-08-19
  - Funciones de formateo con `timeZone: 'America/Guatemala'`
  - `formatDate`, `formatDateTime`, `formatTime`, `getGuatemalaDate`, `getGuatemalaDateTime` en `api.js`

### 🔄 En Progreso
- [x] WebSockets para Caja y Agenda - **COMPLETADO** (2026-08-17)
- [x] Laboratorio de Pruebas E2E - **COMPLETADO** (2026-08-18)
  - ✅ Fase 0: Documentación de precondiciones en `INFORME_PRUEBAS_E2E.md`
  - ✅ Fase 1: Seed de datos maestros funcionando
  - ✅ Fase 2: Seed de pacientes funcionando
  - ✅ Fase 3: 9 Recorridos E2E automatizados
  - ✅ Fase 4: 50 pruebas de verificación (100% PASA)
  - ✅ Fase 5: Pruebas de volumen y rendimiento
  - ✅ Fase 6: Generación de informe automático
  - ✅ Fase 7: Función de purga funcionando
- [x] Cuentas por Cobrar Independientes - **COMPLETADO** (2026-08-18)
  - ✅ Backend: `/api/cuentas-cobrar/optica` y `/api/cuentas-cobrar/clinica`
  - ✅ Backend: CRUD de responsables (`/api/cuentas-cobrar/responsables`)
  - ✅ Backend: Registro de abonos (`/api/cuentas-cobrar/{id}/abono`)
  - ✅ Frontend: CuentasCobrarOptica.js con resumen y tabla
  - ✅ Frontend: CuentasCobrarFinanzas.js con tabs (Cuentas/Responsables)
  - ✅ Submenús agregados en Layout.js para Óptica y Finanzas
- [x] Bug Fix: POS Óptica - **COMPLETADO** (2026-08-19)
  - ✅ Bug P0 (CxC con monto incorrecto): VERIFICADO - NO SE REPRODUJO (funciona correctamente)
  - ✅ Bug P1 (Búsqueda pacientes sin nombre): CORREGIDO - Campos en español añadidos al endpoint `/api/pacientes/buscar`
  - ✅ Bug Adicional (Mismatch ?q= vs ?search=): CORREGIDO - Alias añadido en backend

### 📋 Backlog (Próximas Tareas)

#### P1 - Alta Prioridad
- [ ] **Google Calendar Sync**: Sincronización bidireccional con calendarios de médicos (requiere credenciales OAuth de Google Cloud)
- [ ] **FEL Guatemala**: Estructura de Facturación Electrónica (deshabilitada con `FEL_ENABLED=false`)
- [ ] **Endurecer validación de `ImportarPacientes`**: rechazar filas con datos inválidos en vez de rellenar con dummy (`1900-01-01`, `00000000`); alinear plantilla descargable (Excel) con el formato que espera el importador (JSON)

> ✅ **Importador masivo de Pacientes**: ya realizado (confirmado por el usuario, Sesión 7).

#### P2 - Media Prioridad
- [ ] **PDF Evaluaciones**: Exportar evaluación oftalmológica completa a PDF para anexar al expediente
- [ ] **Integración CxC-POS**: Permitir crear ventas a crédito directamente desde Punto de Venta

#### P3 - Baja Prioridad
- [ ] Indicador visual de estado de WebSocket en UI
- [ ] Refactorización de `CuentasCobrarFinanzas.js` (separar en subcomponentes)
- [ ] Anulación/reversión de abonos en CxC

## Arquitectura Técnica

### Backend
- FastAPI con routers modulares en `/routes/`
- MongoDB con índices compuestos
- WebSocket ConnectionManager en `server.py`
- JWT para autenticación

### Frontend
- React con hooks personalizados
- Shadcn/UI components
- LocalStorage para modo offline
- WebSocket opcional (funciona sin él)

### Estructura de Archivos Clave
```
/app/
├── backend/
│   ├── server.py                # Main + WebSocket Manager
│   ├── routes/
│   │   ├── caja.py
│   │   ├── agenda.py
│   │   ├── patients.py
│   │   ├── cuentas_cobrar.py    # NUEVO: CxC Óptica y Clínica
│   │   ├── laboratorio_pruebas.py  # Endpoints QA E2E
│   ├── seed/                    # Generadores de datos de prueba
│   │   ├── __init__.py
│   │   ├── datos_maestros.py
│   │   ├── pacientes.py
│   │   ├── pruebas_transaccion.py
│   │   ├── verificaciones_e2e.py
│   └── scripts/
│       ├── performance_test.py
│       ├── generar_plantilla_*.py
├── frontend/
│   ├── src/
│   │   ├── hooks/useWebSocket.js
│   │   ├── hooks/useInactivityTimeout.js
│   │   ├── components/
│   │   │   ├── ErrorBoundary.js
│   │   │   ├── InactivityWarning.js
│   │   │   ├── Layout.js           # Submenús CxC Óptica y Finanzas
│   │   ├── pages/
│   │       ├── Caja.js
│   │       ├── Agenda.js
│   │       ├── PuntoVenta.js       # POS Clínica
│   │       ├── OpticaPOS.js        # NUEVO: POS Óptica
│   │       ├── CuentasCobrarOptica.js    # NUEVO: CxC Óptica
│   │       ├── CuentasCobrarFinanzas.js  # NUEVO: CxC Clínica
│   │       ├── LaboratorioPruebas.js     # Panel QA E2E
│   └── public/
│       ├── plantilla_*.xlsx
├── docs/                        # Documentación de seguridad
│   ├── SECURITY_AUDIT.md
│   ├── SECURITY_REMEDIATION_PLAN.md
│   ├── SECURITY_BASELINE.md
├── INFORME_PRUEBAS_E2E.md       # Reporte de auditoría QA
```

## Credenciales de Prueba
Ver `/app/memory/test_credentials.md`

## Endpoints WebSocket
- `ws://{host}/ws/caja?token={jwt}`
- `ws://{host}/ws/agenda?token={jwt}`
- `ws://{host}/ws/pos?token={jwt}`

## Notas Importantes
- WebSocket puede no funcionar en entornos preview sin soporte WSS
- Índices MongoDB envueltos en try/except para evitar `IndexSpecsConflict`
- FEL debe mantenerse deshabilitado hasta implementación completa

## Médico por defecto en POS (sugerencia por cita de hoy) — Implementado (2026-10-13)
- Al seleccionar un paciente en el POS (Clínica y Óptica), si tiene una cita activa HOY (hora Guatemala), el campo "Médico" se autocompleta con el médico de esa cita y muestra un aviso.
- Endpoint: `GET /api/agenda/cita-hoy-paciente/{paciente_id}` → `{medico: {id, name} | null}` (ignora canceladas, toma la más temprana por `hora_inicio`).
- El médico sigue siendo editable/removible manualmente; la sugerencia no impide elegir otro.
- Archivos: `backend/routes/agenda.py`, `frontend/src/services/agendaApi.js`, `frontend/src/pages/PuntoVenta.js`, `frontend/src/pages/OpticaPOS.js`.
- Verificado por curl E2E (devuelve el médico de la cita de hoy; null si no hay cita).

## Fix navegación rol Médico: todos los botones iban a Pacientes (2026-06) — CAUSA RAÍZ RESUELTA
- Síntoma (en PRODUCCIÓN): con usuario médico, al pulsar Agenda/Evaluación/Sala, todas las rutas redirigían a `/pacientes`.
- Causa raíz: el sistema de auth EN VIVO está en `server.py` (NO en `routes/auth.py` ni `config/permissions.py`, que son duplicados sin uso para estas rutas). Su `resolve_permissions()` devolvía `custom["permissions"]` DIRECTO cuando existía un override del rol en `db.roles`. En producción hay un rol `medico` guardado en `db.roles` (vía UI de Roles) creado ANTES de que existieran los permisos clínicos, por lo que le faltaban `view_agenda/view_evaluacion/view_sala_operaciones/manage_recetas`. Tras login, el frontend llama a `/auth/me` → `get_current_user` → `resolve_permissions` → devolvía el override incompleto → `ProtectedRoute` redirigía a `/pacientes`.
- Por qué preview no lo reproducía: preview NO tenía documento `medico` en `db.roles`, así que caía en los defaults estáticos (correctos). Producción usa otra base de datos con el override incompleto.
- Fix: en `server.py::resolve_permissions`, FUSIONAR los permisos por defecto del rol de sistema con el override de `db.roles` (`perms = dict(PERMISSIONS.get(role, {})); perms.update(custom["permissions"])`). Así, claves nuevas faltantes toman el valor por defecto; las personalizaciones explícitas siguen ganando.
- También se alineó `routes/auth.py` (`/login` usa `await resolve_permissions`) y `config/permissions.py` por consistencia, aunque no son la ruta activa.
- Verificación E2E (preview, simulando el override incompleto de producción en `db.roles`): `/auth/me` devuelve 34 permisos con clínicos en True; navegación headless Login→Pacientes, +reload, Agenda→/agenda, Sala→/sala-operaciones, Evaluación→/evaluacion-oftalmologica, todas correctas. Rol de simulación eliminado tras la prueba.
- Requiere REDESPLIEGUE para que producción tome el fix de `server.py`.

## Ajustes Agenda/Médico + fix 422 Pacientes (2026-06) — Implementado y verificado
Contexto: tras implementar (y verificar por testing agent, iteration_73) las 4 mejoras (Sala configurable por rol, Ayudante en cirugía, modal paciente 900px, Tipo de Paciente IGSS), el usuario pidió ajustes adicionales.

1) Tipos de cita (Agenda): se reemplazaron por: 'Primera Consulta', 'Control', 'Control Post Operatorio', 'Lectura de estudios', 'Emergencia'. Las citas antiguas conservan su etiqueta: el Select agrega un SelectItem extra con el valor actual si no está en la lista. Default nuevo: 'Primera Consulta'. Archivo: frontend/src/pages/Agenda.js (const TIPOS_CITA). Backend tipo_cita es str libre (no requiere cambio).

2) Menú del rol Médico: orden Agenda → Pacientes → Evaluación Oftalmológica, y se quitó 'Sala de operaciones'. 
   - frontend/src/components/Layout.js: si user.role==='medico' se reordena navItems por [agenda, pacientes, evaluacion].
   - backend/routes/menu_config.py: DEFAULT_MENU_CONFIG['medico'] = ['pacientes','agenda','evaluacion_oftalmologica'] (sin sala_operaciones). El médico usa default (sin config almacenada). Solo aplica al rol médico; los demás roles no cambian.

3) Acción 'Evaluación Oftalmológica' en el menú de 3 puntos de la Agenda (tanto en 'Mis Citas del Día'/CitaCard como en 'Mis Pacientes Presentes'/PacientePresenteCard): navega (misma pantalla) a /evaluacion-oftalmologica?paciente_id=<id>, que abre una hoja de evaluación NUEVA con el paciente ya cargado. 
   - frontend/src/pages/Agenda.js: handleNuevaEvaluacion + useNavigate; prop onNuevaEvaluacion en ambas tarjetas; data-testid nueva-evaluacion-cita-{id} y nueva-evaluacion-presente-{citaId}. Icono Stethoscope.
   - El mecanismo ?paciente_id= ya existía en EvaluacionOftalmologica.js (preselección + nueva evaluación).

Fix adicional (bug HIGH de iteration_73): frontend/src/pages/Pacientes.js crasheaba al recibir error 422 (FastAPI detail como lista de objetos). Se agregó helper extractErrorMessage() que convierte detail (array/string) a texto legible; aplicado en los catch de crear/actualizar y desactivar paciente.

Verificación: smoke tests headless OK — sidebar médico [Agenda, Pacientes, Evaluación] sin Sala; menú 3 puntos muestra 'Evaluación Oftalmológica' y al pulsar abre /evaluacion-oftalmologica?paciente_id=... con el paciente cargado en una evaluación nueva; cita muestra el nuevo tipo 'Primera Consulta'. Registros de prueba eliminados.

## Evaluación Oftalmológica: regresar a la evaluación del día + médico autocompletado (2026-06) — Implementado y verificado
1) Regresar a la evaluación en curso: al abrir una evaluación del Historial (otra fecha), antes se perdía la evaluación del día. Ahora, al entrar al historial se guarda un snapshot del borrador (formData + evaluacionActual + searchPaciente) en borradorRef, y el dropdown de Historial muestra en la parte superior "← Volver a la evaluación del día" (data-testid historial-volver-actual) que restaura el borrador en curso (editable, sin sello). Se resetea al iniciar nueva evaluación o seleccionar otro paciente. Estado: viendoHistorial. Archivo: frontend/src/pages/EvaluacionOftalmologica.js (cargarEvaluacion, volverAEvaluacionActual, nuevaEvaluacion, seleccionarPaciente, dropdown Historial).
2) Médico autocompletado: para usuarios con rol 'medico', el campo "Médico" se autoselecciona con su médico asignado. Se agregó usuario_id a DoctorResponse (backend/routes/optica.py) y un useEffect en EvaluacionOftalmologica.js que hace medicos.find(m => m.usuario_id === user.id) y setea medico_id/medico_nombre cuando está vacío. medico_test.id == doctors.usuario_id de 'Dr. Carlos Méndez'.
Verificación headless: médico auto-llenado con "Dr. Carlos Méndez"; abrir una evaluación sellada del historial y pulsar "Volver" regresa a la evaluación del día editable (con Guardar, sin "Expediente sellado").

## Flujo de llegada: citas SIN expediente vinculado (Google Calendar) (2026-06) — Implementado y verificado E2E
Bug reportado por el usuario: las citas importadas de Google Calendar no tienen paciente_id, y "Marcar llegada" las marcaba Presente directamente sin pedir vincular/crear expediente; luego "Iniciar/Nueva Evaluación" fallaba con "Esta cita no tiene un paciente vinculado".
Fix (frontend/src/pages/Agenda.js):
- handleMarcarLlegada: si la cita NO tiene paciente_id abre el modal en modo 'vincular' (completarModo='vincular', vincularCitaRef) en vez de marcar Presente.
- Modal completar-ficha-dialog ahora tiene un panel 'vincular' (data-testid vincular-panel) con buscador (vincular-search) de expedientes existentes (vincular-result-{id}) y botón "Crear expediente nuevo" (vincular-crear-nuevo).
- seleccionarPacienteVincular: si el expediente existente está completo, vincula la cita (agendaApi.updateCita {paciente_id, paciente_nombre}) y marca Presente; si está incompleto, abre el formulario precargado para completarlo y luego vincula + Presente (nunca duplica).
- iniciarCrearExpediente + guardarCompletarFicha: si completarEsNuevo crea el paciente (patientApi.create) y luego vincula la cita; si no, actualiza el mismo expediente. Tras guardar, si vincularCitaRef está seteado, vincula paciente_id a la cita y ejecuta la acción pendiente (marcar Presente / walk-in).
Backend:
- routes/patients.py: se agregó y persiste el campo 'address' (dirección) en PatientBase, PatientUpdate, dict de creación y PatientResponse (antes NO se guardaba; fichaIncompleta ahora puede exigir dirección de forma real).
- models/agenda.py CitaResponse.creado_por_nombre -> Optional[str]="" (antes required; un null legacy/importado 500-eaba toda la lista /api/agenda/citas).
Verificación: iteration_75.json — PATH A (crear expediente nuevo desde cita sin vincular), PATH B (vincular expediente existente), REGRESIÓN (cita con paciente incompleto abre completar), y "Procedimiento" presente en selectores de tipo de cita (Nueva Cita y Walk-in). Curl confirma persistencia de address y que /api/agenda/citas devuelve 200 con creado_por_nombre=None.

## Notas en tarjetas de cita + campo único de receta (2026-06) — Implementado y verificado
1) Notas visibles en la cita: al crear/editar una cita y escribir en "Notas", el texto ahora aparece en la tarjeta. Mostrado en CitaCard (Tablero del Día y Calendario) y también en la tarjeta de "Pacientes Presentes en Clínica", con icono StickyNote. Archivos: frontend/src/pages/Agenda.js (CitaCard y PacientePresenteCard, data-testid presente-notas-{cita_id}); backend/models/agenda.py PacientePresenteResponse.notas Optional[str]; backend/routes/agenda.py endpoint /presentes incluye "notas": cita.get("notas","").
2) Receta: dosis/frecuencia/duración en un solo campo de texto libre (decisión del usuario). En Receta de Medicamentos (EvaluacionOftalmologica.js) se reemplazaron los 3 inputs separados por un único input libre almacenado en 'dosis'. La impresión/resumen conserva compatibilidad: recetas antiguas con frecuencia/duracion siguen mostrándose.
Verificación: compilación frontend NO_COMPILE_ERRORS; screenshot Tablero del Día confirma la nota "IPL ambos ojos" visible tanto en "Citas del día" como en la tarjeta de "Pacientes Presentes".

## Próxima Cita desde Evaluación: tipos unificados + solo horarios disponibles (2026-06) — Implementado y verificado E2E
El panel "Próxima Cita" de la Evaluación Oftalmológica ahora:
1) Tipo de cita unificado con la agenda: 'Primera Consulta','Control','Control Post Operatorio','Lectura de estudios','Procedimiento','Emergencia' (default 'Control'). Const TIPOS_CITA en EvaluacionOftalmologica.js. (Antes: Subsecuente/Control post-operatorio/Estudio/Otro).
2) Hora como SELECCIÓN de horarios disponibles (no campo libre). Nuevo endpoint GET /api/agenda/horarios-disponibles?medico_id&fecha&duracion=20 (routes/agenda.py) calcula slots según horario_semanal del médico (o fallback config hora_apertura/cierre + dias_laborables), bloqueos (clínica/médico, día completo y franjas), citas existentes y max_citas_por_slot. Paso del grid = config.duracion_slot_minutos. Excluye horas pasadas si fecha=hoy (GT). Devuelve {disponible,motivo,slots,duracion}. Frontend: agendaApi.getHorariosDisponibles; useEffect recarga al cambiar médico/fecha; Select proxima-cita-hora con opciones proxima-cita-slot-HH:MM; mensaje proxima-cita-motivo cuando no hay disponibilidad.
3) Enforcement en POST /api/agenda/proxima-cita: 409 si día/hora bloqueado o fuera de horario, si fecha/hora ya pasó, o si el slot está lleno (max_citas_por_slot). 400 si duplicado exacto. La evaluación SIEMPRE se guarda aunque la cita no se cree (toast de aviso con el motivo).
4) Anti-duplicado: tras crear la cita se guarda proxima_cita.cita_id y no se recrea en re-guardados/autoguardado.
5) data-testid añadidos: proxima-cita-agendar, proxima-cita-medico, proxima-cita-tipo, proxima-cita-fecha, proxima-cita-hora, proxima-cita-slot-*, proxima-cita-motivo, proxima-cita-notas.
Verificación: iteration_77.json (backend 10/10, frontend 100% de flujos). Curl confirma: past date -> 409 'la fecha ya pasó'; 4ta cita en mismo slot -> 409 'el horario ya está lleno'. La cita aparece en Agenda (Calendario/Tablero) con tipo y notas.
Pendiente (Fase 2/3 según plan): elegir duración de la próxima cita y ajustar slots; resumen de agenda del médico; reprogramar/cancelar desde la evaluación; recordatorio al paciente.

## Fix: Precio Costo en Tipos de Lente (lentes oftálmicos) no se guardaba (2026-06)
Bug: en Óptica > Inventario, al crear/editar un Tipo de Lente (modal 'Nuevo Tipo de Lente'), el 'Precio Costo' no se almacenaba (columna COSTO mostraba '–'). Causa: backend routes/optica.py — LensTypeBase/Create/Update/Response y el doc de create NO incluían 'cost_price' (el frontend sí lo enviaba). Fix: se agregó cost_price (Optional[float]) a LensTypeBase, LensTypeUpdate y LensTypeResponse, y se persiste en create_lens_type; update ya lo incluye vía model_dump. Verificado por curl: create cost_price=123.45 persiste en lista y update a 99.99 OK.
Nota: Armazones (frames) y Lentes de Contacto YA guardaban y devolvían cost_price correctamente (verificado por curl 55.5 y 33.3); no requerían cambios.

## Óptica: columna "Margen" de ganancia en catálogos (2026-06)
Se agregó la columna 'Margen' (venta − costo, con % sobre el costo, en verde si positivo / rojo si negativo) en los tres catálogos de inventario óptico: Tipos de Lente (TiposLente.js), Armazones (OpticaInventario.js) y Lentes de Contacto (LentesContacto.js). Helper compartido margenInfo(cost, sale) en services/api.js; si no hay costo/venta válidos muestra '-'. data-testid: lens-type-margen-{id}, frame-margen-{id}, contact-lens-margen-{id}. Verificado en UI: Costo Q100 + Venta Q250 => Margen Q150.00 (150%).

## Agenda: Sobrecupo de citas (2026-06) — Implementado y verificado E2E
Permite agendar en un horario ya lleno desde la Agenda (Nueva Cita y Walk-in), con aviso y confirmación. Se mantiene el bloqueo duro por horario del médico / bloqueos (Nueva Cita). La "Próxima Cita" de Evaluación NO cambia (solo horarios libres).
Backend (routes/agenda.py): nuevo GET /agenda/verificar-horario?medico_id&fecha&hora&duracion -> {estado: libre|lleno|no_disponible, motivo, ocupadas}. 'lleno' = citas en esa hora_inicio >= max_citas_por_slot. 'no_disponible' = bloqueo/horario del médico. insertar_cita (POST /citas) NO limita el sobrecupo (solo bloquea bloqueo/horario); walk-in sin cambios de bloqueo.
Frontend (Agenda.js): handleSaveCita valida y llama verificarHorario; si 'no_disponible' -> toast error y no crea; si 'lleno' -> AlertDialog de confirmación (data-testid sobrecupo-dialog / sobrecupo-cancelar / sobrecupo-confirmar); si confirma -> ejecutarGuardarCita. Walk-in: doWalkInConSobrecupo redondea la hora actual GT al slot (duracion_slot_minutos) antes de verificar; si lleno pide confirmación. Etiqueta ámbar "Sobrecupo" (CitaCard prop sobrecupo, badge sobrecupo-badge-<id>) en citas que comparten médico+fecha+hora_inicio (esSobrecupo/sobrecupoKeySet). agendaApi.verificarHorario.
Fix adicional (bug MEDIUM preexistente): el calendario Día ocultaba citas cuya hora_inicio no caía en la grilla (horas libres escritas a mano o walk-ins al minuto exacto). citasPorMedicoYSlot ahora ubica esas citas en el slot inferior más cercano (floorSlot) para no ocultarlas. Verificado: cita 09:40 ahora visible en bucket 09:30.
Verificación: iteration_78.json (backend 9/9; UI: dialog aparece en slot lleno, Cancelar no crea, Confirmar crea; badge en citas de mismo horario; regresión Próxima Cita sin sobrecupo). Fixes posteriores verificados por curl + screenshot.

## Fix: médico "sin restricción de horario" bloqueaba todos los días (2026-06)
Bug: al agendar (Nueva Cita / Próxima Cita / verificar-horario), un médico que el usuario dejó SIN restricción mostraba "El médico no atiende ese día". Causa: en Médicos.js, al guardar sin activar ningún día, el frontend enviaba un horario_semanal con los 7 días en activo:false (objeto truthy); el backend lo interpretaba como "no atiende ningún día". La UI ya prometía "Si no activas ningún día, el médico queda sin restricción" (Medicos.js línea ~516).
Fix: (1) Medicos.js envía horario_semanal: null cuando ningún día está activo. (2) Backend verificar_horario_medico y horarios_disponibles tratan un horario con cero días activos como "sin restricción" (equivale a None) — también corrige datos ya guardados sin necesidad de migración.
Verificado por curl: médico con horario todo-inactivo -> verificar-horario estado='libre' cualquier día (antes 'no_disponible'); horarios-disponibles cae al fallback de la config general de la clínica.

## Evaluación: sección "Medicamentos y Procedimientos (EXCLUSIVO IGSS)" (2026-06) — Implementado y verificado E2E
Nueva sección en la Evaluación Oftalmológica, entre "Diagnóstico y Plan" y "Candidato a Cirugía", con acento verde esmeralda. Dos listas de texto libre: "Medicamentos" y "Estudios / Procedimientos", con agregar/editar/eliminar renglones (uno o varios; vacía es válida). Se muestra siempre para cualquier paciente. Se guarda/recupera con la evaluación y aparece en la impresión (printType='igss', icono de impresora en el encabezado de la sección).
Frontend (EvaluacionOftalmologica.js): evaluacionVacia.igss_med_proc {medicamentos:[], estudios_procedimientos:[]}; CollapsibleSection ahora acepta accent ('blue'|'emerald'); handlers reutilizan addArrayItem/updateNestedField(`igss_med_proc.<lista>.<idx>`)/removeArrayItem; data-testid: igss-med-proc-section, igss-add-medicamento/igss-medicamento-<idx>/igss-remove-medicamento-<idx>, igss-add-estudio/igss-estudio-<idx>/igss-remove-estudio-<idx>; merge al cargar evaluación. Bloque de impresión en .print-area (printType==='igss').
Backend (models/evaluacion_oftalmologica.py): clase MedicamentosProcedimientosIGSS (medicamentos/estudios_procedimientos: List[str]) con field_validator que recorta y descarta renglones vacíos; campo igss_med_proc en EvaluacionOftalmologicaBase y Update. Evaluaciones antiguas sin el campo devuelven listas vacías.
Verificación: curl round-trip (create+GET) OK; validador descarta vacíos/trim OK; iteration_79.json frontend 100% (ubicación/color, agregar/editar/eliminar, guardar+reabrir persistencia, vista de impresión con títulos y subtítulos).
Fase 2 pendiente: autorelleno de ambas listas desde un Excel que proporcionará el usuario.

## Evaluación IGSS Fase 2: autorelleno desde catálogos Excel (2026-06) — Implementado y verificado
El usuario adjuntó 2 Excel: Medicamentos (33) y Procedimientos (611), cada uno con columnas Código IGSS + Descripción IGSS.
- Datos persistidos como JSON en /app/backend/data/igss_medicamentos.json y igss_procedimientos.json (codigo, nombre).
- Seed idempotente seed_catalogos_igss() en server.py (startup) -> colecciones catalogo_igss_medicamentos / catalogo_igss_procedimientos (id, codigo, nombre, usos, fecha_creacion). Para recargar tras actualizar los JSON: borrar la colección y reiniciar backend.
- Endpoints (routes/evaluaciones.py, catalogos_router): GET /api/catalogos/igss-medicamentos y /api/catalogos/igss-procedimientos (?search=&limit=), buscan por nombre O codigo (regex i), orden por nombre.
- Frontend (EvaluacionOftalmologica.js): los renglones de Medicamentos y de Estudios/Procedimientos usan el componente Autocomplete (nuevo prop testId) con fetchUrl a los endpoints IGSS. El dropdown muestra [codigo] en verde + descripción; al seleccionar rellena el renglón con la descripción (texto libre, se mantiene editable). data-testid de inputs: igss-medicamento-<idx>, igss-estudio-<idx>.
Verificación: seed 33+611 OK; búsqueda por nombre y por código OK (curl); screenshot confirma sugerencia "[1228] Timolol maleato..." al escribir en el renglón de medicamentos.
Nota: no se almacena el código por separado (plan Fase 1: una sola línea de texto libre); el código se muestra solo como pista en el dropdown.

## IGSS autorelleno: ajustes (2026-06)
1) Al seleccionar una sugerencia (medicamentos y estudios/procedimientos), el renglón ahora se rellena con "[código] nombre" (antes solo el nombre). En Autocomplete onClick: label = item.codigo ? `[${codigo}] ${nombre}` : nombre. Otros catálogos sin código quedan igual (solo nombre).
2) El dropdown de "Estudios / Procedimientos" (último renglón) quedaba cortado por overflow-hidden de CollapsibleSection. Se agregó prop overflowVisible a CollapsibleSection (root sin overflow-hidden, header con rounded-t-lg) y la sección IGSS lo usa. Verificado por screenshot: cascada visible y valor "[416631] OFTALMOLOGIA..." tras seleccionar.

## Pacientes: Tipo de Paciente IGSS como lista (2026-06)
El campo "Tipo de Paciente" (seccion IGSS del formulario Nuevo/Editar Paciente, Pacientes.js) pasó de Input de texto libre a Select con 5 opciones: Afiliado, Esposa, Beneficiario Hijo, Pensionado, Jubilado. Guarda en igss_tipo_paciente. data-testid patient-igss-tipo-paciente. Verificado por screenshot.

## Pacientes: borrado total + import 10k (2026-06)
1) Borrado total de la base de pacientes (solo administrador). Backend: DELETE /api/patients/all?confirmacion=BORRAR%20TODO (require_role admin/superadmin), delete_many({}) sobre colección patients (hard delete, TODOS incl. inactivos). NO toca citas/agenda/Google Calendar. Valida confirmacion=='BORRAR TODO' (400 si no) y registra auditoría PATIENTS_BULK_DELETED. Ruta declarada ANTES de /{patient_id}. Frontend (Pacientes.js): botón admin-only "Borrar toda la base" (data-testid delete-all-patients-button) + Dialog de confirmación que exige escribir "BORRAR TODO" (delete-all-confirm-input, delete-all-confirm-button disabled hasta coincidir). patientApi.deleteAll(). Verificado: ruteo/auth/validación (curl 400/403), borrado real 57->0 y restaurado, UI (botón disabled->enabled al escribir).
   NOTA: el usuario pidió esta función para limpiar una base importada por error; mencionó eliminarla después de usarla.
2) Importación hasta 10,000 expedientes (JSON). El flujo ya soportaba miles vía lotes de 500 (BATCH_SIZE) en ImportarPacientes.js; se amplió la validación previa de muestra de 1000 a 10000 para que los conteos (Total/Válidos/Duplicados) reflejen el total real. Backend import/batch sin tope. Formato: JSON.

## Reversión (2026-06): se eliminó borrado total de pacientes + importación masiva (frontend)
- Borrado total de pacientes ELIMINADO: se quitó el botón/diálogo/handler/estados en Pacientes.js, el helper patientApi.deleteAll en api.js, y el endpoint DELETE /api/patients/all en backend (routes/patients.py). El endpoint ahora responde 404.
- Importación masiva RETIRADA del frontend: se quitaron las entradas del sidebar "Importar Pacientes" y "Importar Evaluaciones" (Layout.js) y sus rutas /importar-pacientes e /importar-evaluaciones (App.js), además de los imports de ImportarPacientes/ImportarEvaluaciones. Los archivos de página permanecen en el repo pero son inaccesibles desde la UI. Los endpoints backend de import (import/validate, import/batch) siguen existiendo pero sin acceso desde el front.
Verificado: compilación OK, backend sin errores, screenshot confirma ausencia de nav de importación y del botón de borrado total.

## Carga histórica Access: pacientes + evaluaciones (2026-06) — COMPLETADA y verificada
Destino: vista previa. Deduplicación por ID de Access (record_number). NO se tocaron citas/agenda/Google Calendar.

### Pacientes (17,753)
- Importados desde pacientes_001.json (10,000) + pacientes_002.json (7,753) directo a Mongo.
- ID de Access preservado: patients.record_number = ID de Access (expediente visible); también en patients.access_id.
- Género: M→masculino, F→femenino, vacío→otro (mapeo fiel al origen; algunos registros del origen traen género que no coincide con el nombre).
- Institución: seguro_privado si traía aseguradora, otra si traía hospital de referencia, si no particular. Dirección extraída de comments; comentario original íntegro.
- DPI: los JSON SÍ traen campo `dpi`. 3,941 (22%) con DPI válido de 13 dígitos; 13,812 sin DPI. Rellenados por bulk_write enlazando por access_id. 1 DPI duplicado en el origen (2 pacientes) — pendiente que el usuario decida.
- Pacientes ahora buscables por expediente y por DPI (GET /api/patients?search=).

### Evaluaciones (36,411) — 73 archivos de 500 (último 411)
- Importadas vía endpoint backend POST /api/evaluaciones/import/batch (require_role admin/superadmin), skip_duplicates=true, batch_number por archivo (1..73).
- Enlace al paciente por `expediente` (= record_number = ID de Access). 100% enlazadas: 36,411 con paciente_id, 0 huérfanas, 0 sin clave, 0 duplicadas.
- Dedup por import_source_id (id_origen, ej. ACCESS-EVAL-<exp>-<fecha>). Cada eval marcada imported=True, import_batch=N.
- 16,312 pacientes distintos con historial. Verificado: 16,312/16,312 paciente_id existen en patients; API GET /api/evaluaciones?paciente_id= devuelve el historial importado (expediente 1 → 12 evals).
- La plantilla/esquema esperado está en GET /api/evaluaciones/import/template. El importador frontend (ImportarEvaluaciones.js) sigue oculto de la UI; la carga se hizo vía script+endpoint con credenciales superadmin.
