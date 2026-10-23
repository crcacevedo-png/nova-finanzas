# CHANGELOG — NovaVisión ERP

## 2026-06 — NOG IGSS: descuento al asignar al paciente + diagnóstico "admin IGSS no crea NOG"
**Solicitudes:** (1) El rol administrador IGSS no podía crear NOG (reportado en producción). (2) Asignar un NOG al paciente no restaba los servicios disponibles por unidad.
**Decisión del usuario:** descontar 1 servicio del NOG AL ASIGNARLO al paciente (crear/editar), 1 solo descuento por paciente, sin volver a descontar en la evaluación.

**Punto 2 — Implementado y verificado (API e2e + testing_agent iteration_82, frontend 100%):**
- `routes/igss_nogs.py`: `_crear_acreditacion` ahora deduplica por `(nog_id, paciente_id)` (antes por evaluación). Nuevas funciones `_anular_acreditacion_interna` y `_reconciliar_nog_paciente` (mantiene exactamente 1 servicio consumido por paciente según su NOG actual; libera cupo al cambiar/quitar NOG o desactivar). `_sincronizar_acreditaciones` ahora acredita por paciente activo asignado (no por evaluación).
- `routes/patients.py`: `create_patient`, `update_patient`, `delete_patient` y `reactivate_patient` llaman a `_reconciliar_nog_paciente`.
- Nuevo endpoint `POST /api/igss-units/nogs/reconciliar-todo` (manage_igss_units): backfill idempotente para pacientes existentes. Botón UI "Recalcular consumo" en `UnidadesIGSS.js` (data-testid `reconciliar-nog-button`) + `igssNogApi.reconciliarTodo`.
- Verificado: asignar NOG descuenta (5→4), editar no duplica, quitar NOG/desactivar libera, reasignar/reactivar reconsume.

**Punto 1 — Diagnóstico (deployer debug RCA + testing_agent):** NO es un bug de código. En producción el rol `administrador_igss` (usuario `sandrac`) YA tiene `manage_igss_units: true` y el build desplegado es actual; el backend respondería 200. En preview el rol `igss.admin` crea NOG sin problema por UI. Causa: la sesión de `sandrac` cargó los permisos ANTES de que se concediera el permiso (AuthContext guarda permisos en memoria al login y solo los refresca con recarga completa vía `/auth/me`). **Acción para el usuario:** cerrar sesión y volver a entrar (o recargar) en el sitio en vivo. El punto 2 sí requiere desplegar a producción para que tome efecto.


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

## 2026-06 — Frecuencia de uso en medicamentos IGSS
- Evaluación oftalmológica, sección "Medicamentos y Procedimientos (EXCLUSIVO IGSS)": cada medicamento ahora tiene campo "Frecuencia de uso" junto al nombre.
- Backend: `MedicamentoIGSS {nombre, frecuencia}`; `MedicamentosProcedimientosIGSS.medicamentos` pasó de List[str] a List[MedicamentoIGSS] con validador que normaliza strings antiguos a {nombre, frecuencia:''}.
- Fix (HIGH): autoguardado (`PATCH /api/evaluaciones/{id}/autoguardar`) no incluía `igss_med_proc` en la whitelist y descartaba silenciosamente los cambios IGSS; ahora está en la whitelist y se normaliza con el modelo Pydantic.
- Verificado: 5/5 pytest (incluye round-trip POST/PUT, autoguardado, carga legacy) + prueba UI del testing agent (add/edit/Guardar/reabrir/legacy).

## 2026-06 — Firma y sello del médico en el expediente PDF
- PDF de evaluación (`routes/evaluaciones.py`): al final del expediente se agrega bloque de firma centrado con línea de firma, nombre del médico, especialidad y "Colegiado No. {license_number}".
- Firma digital: nuevo campo `firma_digital` (imagen base64) en el médico. Se sube en Médicos → editar médico → "Firma digital" (`Medicos.js`); la imagen se redimensiona en el cliente (máx 400px) y en el PDF se limita a máx 3 cm ancho × 2 cm alto conservando proporción.
- Resolución del médico en el PDF: por `medico_id`, si no, por coincidencia de `medico_nombre` con el nombre del médico, y si no, por el usuario que creó la evaluación (`doctors.usuario_id`).
- Backend `optica.py`: `firma_digital` agregado a DoctorBase/Update/Response y a la creación.
- Verificado: PUT de firma + colegiado, generación de PDF y render (firma dentro de límites, nombre/especialidad/colegiado correctos). Frontend compila sin errores.

## 2026-06 — Contador de espera se congela al atender (Agenda/Tablero del día)
- Bug: el tiempo de espera ("Espera: X min") seguía creciendo aunque el paciente ya estuviera en consulta/atendido, porque `calcular_tiempo_espera` siempre usaba la hora actual.
- Fix (`routes/agenda.py`): la espera ahora se congela en `hora_inicio_consulta` (o `hora_fin_consulta` si aplica). Mientras el paciente sigue "Presente" el contador corre; al iniciar consulta / atender, se detiene. Aplicado en `/agenda/presentes` y `/agenda/mi-dia`.
- Verificado: unitario (600→20 congelado) y e2e real vía `mi-dia` con cita En consulta retrodatada (devuelve 20, no 600).

## 2026-06 — Ajustes evaluación en Agenda y Pacientes
- Agenda (tarjeta de paciente presente): se eliminó la opción "Ver evaluación" del menú; queda solo "Evaluación Oftalmológica" (crear nueva, autocarga paciente).
- Pacientes (tabla ACCIONES): el icono "Crear evaluación" (estetoscopio) ahora también se muestra para el rol `medico` (antes solo superadmin/admin/usuario). Al pulsarlo navega a `/evaluacion-oftalmologica?paciente_id=` y la pantalla autocarga los datos del paciente.

## 2026-06 — Firma del médico en la misma hoja del expediente
- Antes la firma podía saltar a una hoja nueva (se usaba KeepTogether + spacer). Ahora se dibuja al pie de la ÚLTIMA página del expediente mediante un canvas personalizado (SignatureCanvas), reservando margen inferior (bottomMargin=160) para que el contenido no la invada.
- La firma (imagen máx 3×2 cm + línea + nombre + especialidad + "Colegiado No.") aparece solo en la última página, junto al contenido final del expediente; no genera hoja suelta.
- Verificado renderizando PDF real (2 páginas): firma únicamente en la última, bajo el contenido.

## 2026-06 — Corrección del nombre de marca: "Novavisión"
- Reemplazado el texto de marca visible "NovaVision"/"NOVAVISION" por "Novavisión"/"NOVAVISIÓN".
- Frontend: Login (footer + alt logo), Layout (alt logo), impresión de Evaluación Oftalmológica (título y pie), recibo POS.
- Backend (títulos de documentos/PDF/Excel): Lista de Pacientes, Reporte de Cirugías, encabezado de Evaluación, Reporte Financiero (PDF y Excel), nombre por defecto en recibos de ventas, resumen y descripción de eventos de Google Calendar, nombre sembrado del usuario genérico.
- NO modificado: el valor de institución de negocio "Novavision" (v minúscula) usado en comparaciones/BD de cirugías y sala de operaciones, para no romper la lógica ni los datos existentes.

## 2026-06 — Ajustes PDF informe médico (evaluación)
- Nombre del paciente: ahora apellidos primero, luego nombres (last_name + first_name).
- Sello/firma del médico: ya no muestra la especialidad; muestra nombre + "Oftalmólogo" + "Colegiado No.".
- Agregados cuadros (tablas) de MEDICAMENTOS (con columna Frecuencia de uso) y ESTUDIOS / PROCEDIMIENTOS, tomados de igss_med_proc.
- Tabla de agudeza visual reducida (columnas más angostas, fuente 8, padding 2, alineada a la izquierda).
- Logo del encabezado aumentado 1.5x (de 0.67x0.9 a 1.0x1.35 in).
- Verificado renderizando PDF real de 2 páginas.

## 2026-06 — PDF informe médico: encabezado, medicamentos y datos del paciente
- Encabezado: menos margen superior (topMargin 50→24) y menos espacio antes de la línea divisoria (spacer 10→2); sin padding extra en la tabla de encabezado.
- Medicamentos: ya no se muestran en cuadros/tabla; ahora es una lista compacta numerada "N. Medicamento — Frecuencia" para optimizar espacio. (Estudios/Procedimientos se mantienen en tabla).
- Datos del paciente en el PDF: se ocultan Teléfono, Dirección, Profesión, Institución/Otra Institución, IGSS Tipo Compra, IGSS Tipo Paciente e IGSS NOG. Los datos NO se eliminan del expediente, solo no aparecen en el PDF. Se conservan Paciente, Expediente, Edad, Sexo, Fecha Nac., DPI, Email, IGSS Unidad/Afiliación/SPS/Código, Fecha Evaluación y Médico.
- Verificado renderizando PDF real (2 páginas).

## 2026-06 — FIX: próxima cita no se guardaba ni se agendaba (producción)
- Causa raíz: el autoguardado (camino de guardado más usado) descartaba `proxima_cita` porque no estaba en su whitelist, y la creación de la cita solo ocurría en el guardado manual explícito. Al confiar en el autoguardado, la próxima cita se perdía (aparecía vacía al reabrir) y no se agendaba en el calendario.
- Fix backend (`routes/evaluaciones.py`): 
  - `proxima_cita` agregado a la whitelist de `/autoguardar` (+ preserva `cita_id` existente).
  - Nuevo campo `cita_id` en el modelo `ProximaCita` (idempotencia).
  - Nuevo helper `sincronizar_proxima_cita` que crea/actualiza la cita en la agenda de forma idempotente; se invoca en crear (POST), actualizar (PUT) y autoguardar (PATCH). No agenda fechas pasadas, evita duplicados y actualiza la cita si cambian fecha/hora/médico.
- Fix frontend (`EvaluacionOftalmologica.js`): se eliminó la creación de cita desde el cliente (ahora la agenda el backend), evitando duplicados.
- Verificado e2e en preview: autoguardado persiste la próxima cita y la agenda en el calendario del médico (estado Agendada); idempotente (2 autoguardados → 1 sola cita).

## 2026-06 — FIX: contador "Atendidos" (pacientes se quedaban en "En consulta")
- Causa: los pacientes se atendían (evaluación hecha) pero su cita nunca pasaba a "Atendida"; quedaban en "En consulta", por lo que "Atendidos" mostraba 0.
- Fix backend (`routes/evaluaciones.py`): nuevo helper `marcar_cita_atendida_por_evaluacion`; al crear (POST) o actualizar (PUT) una evaluación, la cita del día del paciente (Presente/En consulta) pasa automáticamente a "Atendida" (asistio=True, hora_fin_consulta). NO se dispara en autoguardado-PATCH, pero sí en el POST de creación automática (que es como el autoguardado crea una evaluación nueva con contenido clínico).
- Reconciliación histórica: nuevo endpoint `POST /api/agenda/reconciliar-atendidos` (admin/superadmin) que marca "Atendida" las citas atascadas en Presente/En consulta que ya tienen evaluación ese día (coincidencia de fecha tolerante a formatos legacy). Botón "Reconciliar atendidos" agregado en el Tablero del Día (`Agenda.js`) para ejecutarlo una vez en producción.
- Verificado e2e: guardar evaluación marca la cita como Atendida; el endpoint de reconciliación responde 200 y respeta las citas sin evaluación.

## 2026-06 — Deshacer atendido + Resumen del día por médico
- Deshacer atendido: en el menú de cada cita (Citas del día), las citas en estado "Atendida" tienen la opción "Deshacer atendida", que las regresa a "En consulta". Backend: al pasar a "En consulta" se limpian hora_fin_consulta y asistio (deshace la marca de atención).
- Resumen del día por médico: nueva tarjeta en el Tablero del Día que lista cada médico con sus pacientes atendidos (y total del día), ordenada por atendidos. Usa `contadores.por_medico` (ya existente en el backend).
- Verificado e2e: revertir Atendida→En consulta (limpia campos) y el resumen por médico muestra el conteo correcto de atendidos.

## 2026-06 — Notas por paciente + Lensometría/Autorefractómetro + Copiar refracción
- Notas del paciente: campo `nota_clinica` a nivel de paciente, persistente entre consultas. Endpoint `PATCH /api/patients/{id}/nota-clinica`. Casilla "Notas del Paciente" bajo la columna de Medicamentos en la evaluación (no aparece en el PDF). Verificado por curl.
- Lensometría/Autorefractómetro: toggle en el examen que cambia el título en pantalla; campo `tipo_lensometria` en el modelo ExamenOftalmologico. Persiste al guardar. Verificado por curl.
- Copiar refracción: botón "Copiar a receta de anteojos" en el área de Refracción; copia esfera/cilindro/eje/adición OD/OS a la primera receta de anteojos (crea si no existe, sobrescribe si ya tiene).
- Eliminado el recuadro "Recomendaciones Generales" de la hoja de evaluación.

## 2026-06 — Órdenes IGSS múltiples por paciente (dos consultas el mismo día)
- Pacientes: cada paciente IGSS ahora tiene una lista de ÓRDENES (NOG, No. SPS, código, procedimiento) en lugar de un solo NOG/SPS. Migración lazy + script (scripts/migrar_ordenes_igss.py) convirtió el NOG/SPS actual en la 1ª orden. Afiliación, Tipo de Compra y Tipo de Paciente siguen a nivel de paciente.
- Descuento de NOG por orden: cada orden descuenta 1 servicio del NOG de la unidad; 2 órdenes con NOG distintos = 2 descuentos; no se duplica el mismo NOG. Reconciliación (_reconciliar_nog_paciente) itera las órdenes.
- Dos consultas el mismo día: la cita y la evaluación guardan la orden elegida (igss_orden_id + NOG/SPS/procedimiento). Dos citas el mismo día = dos atenciones. Selector de orden en Agenda (nueva cita) y en la pantalla de Evaluación (auto-selecciona la primera).
- Un informe por consulta: el PDF de cada evaluación muestra el NOG y No. SPS de SU orden (verificado extrayendo el PDF).
- Unidades IGSS: nuevo endpoint y UI para APLICAR un descuento de un NOG a un paciente individual (buscar + aplicar); la LIBERACIÓN (anular) por acreditación ya existía. Recalcular ahora también corrige sobre-conteos del contador.
- FIX de producción: una edición previa había eliminado el decorador @router.post("") de create_patient (POST /api/patients daba 405: creación de pacientes rota). Restaurado.
- Bugs HIGH encontrados por testing y corregidos: (1) borrar todas las órdenes (igss_ordenes=[]) ahora limpia órdenes y libera descuentos (sin fallback legacy); (2) un descuento manual (origen='manual') ya no se cancela al editar el paciente.
- Verificado por curl/API/DB: 2 órdenes→2 descuentos, quitar orden libera 1, aplicar (+1 y 400 duplicado), PDF por orden, descuento manual sobrevive a edición. Testing agent (iteration_84): flujos de UI 100%.

## 2026-06 — Módulo de Producción IGSS (seguimiento y cierre por unidad)
- Nueva pestaña "Producción" dentro de Unidades IGSS (/igss/unidades), restringida a superadmin/admin/administrador_igss (médico → 403).
- Listado diario o por rango de servicios IGSS: una línea por evaluación (orden), con paciente, expediente, unidad, NOG, No. SPS, procedimiento, médico, fecha, costo y 4 estados. Agrupado por unidad y NOG con subtotales; barra de totales (servicios, producción, pagado, pendiente, facturado, enviado) en Q.
- Costo precargado del precio del NOG, editable por registro (costo_override) sin tocar el catálogo.
- 4 estados independientes (impreso/enviado/facturado/pagado) con toggle manual; imprimir el expediente desde el módulo marca "impreso" automáticamente.
- Acciones por fila: abrir expediente (navega a la evaluación del paciente) e imprimir PDF.
- Reporte exportable a Excel (detalle + totales por estado y por NOG). Cierre sin bloqueo (Fase 1).
- Backend: GET /api/igss-units/produccion, PATCH /api/igss-units/produccion/{evaluacion_id}, GET /api/igss-units/produccion/reporte/excel. Colección igss_produccion (estados+costo por evaluacion_id); datos derivados de evaluaciones IGSS + precio del NOG.
- Verificado por API/curl: listado con totales, PATCH de estado y costo reflejados en totales, rol médico 403, endpoint Excel. Frontend compila sin errores. PENDIENTE: verificación interactiva de UI (el harness de screenshot no mantuvo la sesión); recomendable prueba manual o testing agent.
