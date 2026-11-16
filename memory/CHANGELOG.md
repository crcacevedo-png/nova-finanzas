# CHANGELOG - NovaVision ERP Oftalmológico

Historial cronológico de sesiones de desarrollo (más reciente primero dentro de cada bloque agregado). Para el problema original y alcance del producto ver PRD.md. Para pendientes/backlog ver ROADMAP.md.

## Estado Actual del Proyecto
### Sesión 57 — Fix: Punto de Venta de Óptica no permitía confirmar la venta (2026-02) — RESUELTO y verificado
- 🐛 **Reporte del usuario (con captura de pantalla)**: al escribir el monto en el diálogo de pago del Punto de Venta de Óptica, "Pagado" seguía en Q0.00 y "Confirmar Venta" quedaba deshabilitado.
- 🔍 **Causa raíz**: el monto escrito en el campo "Monto" es solo un valor en espera hasta que se presiona el botón "+" para agregarlo a la lista de formas de pago; "Pagado"/"Pendiente" y el habilitado de "Confirmar Venta" solo se calculan sobre esa lista, no sobre el texto escrito. El usuario escribió el monto pero no presionó "+", por lo que el sistema seguía viendo la venta como no pagada (comportamiento técnicamente esperado por el código, pero confuso/bloqueante en la práctica — mismo patrón ya existente también en el Punto de Venta de la Clínica, no es exclusivo de Óptica, pero solo se corrigió en Óptica ya que es el flujo reportado).
- ✅ **Fix**: (1) "Confirmar Venta" ahora también resta el monto escrito aún no agregado al calcular si debe habilitarse; (2) al procesar la venta, si queda un monto válido sin agregar explícitamente con "+", se agrega automáticamente antes de validar y enviar — el usuario ya no necesita presionar "+" si va a pagar todo con una sola forma de pago.
- ✅ **Verificado**: testing E2E 100% (6/6 escenarios + regresión FEL/impresión): pagar sin presionar "+", pago dividido (parte con "+", resto sin "+"), monto insuficiente sigue bloqueado correctamente, Cuenta por Cobrar sin/con paciente se comporta igual que antes. Flujo original (con "+") sigue funcionando sin cambios. Punto de Venta de la Clínica no fue tocado.
- ⚠️ Requiere redespliegue para producción.

### Sesión 56 — Facturación Electrónica (FEL) en el Punto de Venta de Óptica (2026-02) — COMPLETADO y verificado
- 🎯 Plan aprobado: el Punto de Venta de Óptica (`OpticaPOS.js`, ruta `/optica/punto-venta`) ahora puede emitir, consultar e imprimir la factura electrónica (FEL) de cada venta, igual que ya funcionaba en el Punto de Venta de la Clínica. Reutiliza la misma configuración/credenciales de prueba de Digifact ya usada para la Clínica (sin configuración separada para Óptica).
- ✅ **Backend** (`routes/optica.py`): nuevo endpoint `GET /optica/sales/{sale_id}/ticket` (mismo formato que el ya existente de la Clínica, adaptado a `items_v2`/pagos de Óptica, con fallback para ventas legacy sin `items_v2`).
- 🐛 **Bug pre-existente encontrado y corregido**: el modelo `OpticaSaleResponse` no declaraba el campo `fel`, así que Pydantic lo descartaba silenciosamente (`extra="ignore"`) cada vez que se reconsultaba el detalle de una venta — esto afectaba tanto a la nueva función de Óptica POS como al módulo ya existente `OpticaVentas.js` (riesgo de que el estado de FEL pareciera "revertirse" al reabrir una venta certificada). Fix: se agregó `fel: Optional[dict] = None` al modelo.
- ✅ **Frontend**: `POSSuccessDialog` (pantalla "Venta Exitosa") ahora incluye el control `<FELButton origen="optica">` y el botón "Imprimir" quedó conectado. "Ver Ventas del Día" (`POSSalesDialog`) ahora tiene filas clickeables que abren un nuevo `POSSaleDetailDialog` (items, totales, pagos, badge de estado, FEL e Imprimir) — estilo oscuro/teal consistente con el resto del POS de Óptica. Ticket térmico adaptado a Óptica (`generarTicketHTMLOptica`, copiado/ajustado del de la Clínica, sin tocar `PuntoVenta.js`).
- 🐛 **Bug encontrado y corregido durante el testing (MEDIUM)**: al certificar FEL desde el detalle de "Ver Ventas del Día" y volver a abrir la misma fila sin recargar, mostraba de nuevo "Facturar FEL" (estado obsoleto) porque el refresco solo actualizaba el detalle abierto, no la fila cacheada en la lista. Fix: el refresco ahora también sincroniza esa fila dentro de la lista en memoria.
- ✅ Mejoras menores agregadas durante el testing: hover visible en las filas de la lista (antes el estilo inline lo bloqueaba), insignia de estado "Cancelado"/"Pendiente" en filas no pagadas, diseño del control FEL en "Venta Exitosa" apilado verticalmente (antes se envolvía mal), manejo de ventana de impresión bloqueada por el navegador.
- ✅ **Verificado**: pytest 8/8 (`tests/test_optica_pos_fel.py`) + 2 rondas de testing E2E de UI (`iteration_129.json` 90%→`iteration_130.json` 100%, sin acciones pendientes). Confirmado sin regresión en Punto de Venta de la Clínica (código no tocado) ni en `OpticaVentas.js` (se beneficia del fix del campo `fel`, sigue mostrando correctamente el estado certificado tras recargar).
- ⚠️ Requiere redespliegue para producción.

### Sesión 55 — Rol "usuario" puede cancelar, reprogramar y eliminar cirugías (2026-02) — COMPLETADO y verificado
- 🎯 Plan aprobado: el rol "usuario" en Sala de Operaciones (que ya podía crear/editar cirugías y gestionar equipo/insumos desde la Sesión 54) ahora también puede **cancelar** (con motivo + reprogramación opcional, que clona la cirugía a la nueva fecha/hora igual que ya hacía SuperAdmin) y **eliminar** cirugías, acciones antes exclusivas de SuperAdmin. Admin, Médico y Anestesia no cambiaron (confirmado explícitamente que Admin sigue sin esta capacidad).
- ✅ **Backend** (`routes/surgeries.py`): `cancel_surgery` y `delete_surgery` cambiaron de `require_role("superadmin")` a `require_role(["superadmin", "usuario"])`. Se reutilizó 100% la lógica de clonado/reagendamiento existente, sin tocarla.
- ✅ **Frontend** (`SalaOperaciones.js`): nueva variable `canCancelOrDelete` (SuperAdmin o "usuario") reemplaza el guard anterior en los íconos Cancelar/Eliminar del listado. Se agregaron botones "Cancelar"/"Eliminar" también en el pie del diálogo de DETALLE (antes solo existían en el listado), reutilizando exactamente los mismos diálogos/handlers ya existentes — disponible también para SuperAdmin como superficie adicional (misma capacidad que ya tenía).
- 🐛 **Bug encontrado y corregido durante el testing**: `cancel_surgery` no validaba si la cirugía ya estaba cancelada, permitiendo re-cancelarla y crear un clon duplicado si se reenviaba la petición (doble click / reintento de API). Fix: ahora devuelve 400 "La cirugía ya está cancelada" si se intenta cancelar una ya cancelada.
- ✅ Mejoras menores de testing agregadas: data-testid en textarea de motivo, botones de confirmación de cancelar/eliminar y botón "Editar" del detalle; el formulario de cancelación se limpia al cerrar el diálogo (antes conservaba datos de la cirugía anterior si se reabría para otra).
- ✅ **Verificado**: pytest 13/13 (incluye el caso de re-cancelación ya corregido) + testing E2E de UI (`iteration_128.json`, 100% frontend): "usuario" cancela con/sin reprogramación desde listado y detalle, elimina desde ambos lugares; "anestesia" sigue sin ver ni poder usar estos botones (403 por API); superadmin sin regresión.
- ⚠️ Requiere redespliegue para producción.

### Sesión 54 — Fix: rol "usuario" no podía crear/guardar cirugías + cierre de bypass de cancelación (2026-02) — RESUELTO y verificado
- 🐛 **Reporte desde producción**: el rol "usuario" no podía guardar/crear cirugías en Sala de Operaciones.
- 🔍 **Causa raíz (no era regresión reciente)**: los endpoints de escritura de `routes/surgeries.py` (crear/editar cirugía, equipo, insumos) usaban por error los permisos `create_expenses`/`edit_expenses` (del módulo de Gastos) en vez de un permiso propio del módulo, mientras el frontend ya mostraba los botones según `view_sala_operaciones`. Como "usuario" tenía `view_sala_operaciones: False` (decisión explícita anterior: solo ver + editar paciente) nunca veía los botones; pero el mismo desalineamiento también afectaba silenciosamente a "medico" (botones visibles, 403 al guardar) sin que nadie lo hubiera notado.
- ✅ **Confirmado con el usuario**: "usuario" debe tener acceso completo en Sala de Operaciones, igual que Médico/Admin (crear, editar, equipo, insumos; cancelar/eliminar siguen exclusivos de superadmin, igual que ya era para admin/médico).
- ✅ **Fix de permisos**: nuevo permiso `manage_sala_operaciones` (distinto de `view_sala_operaciones`, que vuelve a significar solo "puede ver el módulo"). Los 8 endpoints de escritura ahora requieren `manage_sala_operaciones`; se agregó `True` para superadmin/admin/medico/usuario en **ambas** matrices (`config/permissions.py` y `server.py`, deuda técnica conocida de duplicación). El rol `anestesia` (personalizado en `db.roles`, sin esta clave nueva) queda automáticamente en `False` — conserva el acceso de SOLO LECTURA que tenía por diseño explícito de una sesión anterior (ver sesión "Rol anestesia: acceso a Sala de Operaciones"), evitando una regresión de seguridad que el primer intento de fix iba a introducir sin querer. Frontend (`SalaOperaciones.js`): `canEdit = hasPermission('manage_sala_operaciones')`.
- 🛡️ **Bug de seguridad encontrado y corregido durante el testing**: `PUT /api/surgeries/{id}` aceptaba y aplicaba ciegamente `status`/`cancellation_reason`/`rescheduled_to`, permitiendo a cualquier usuario con el permiso de escritura cancelar una cirugía sin pasar por `POST /{id}/cancel` (restringido a superadmin). Fix: `update_surgery` descarta esos 3 campos del body sin importar el rol; la cancelación real solo es posible vía el endpoint dedicado.
- ✅ **Verificado**: pytest 17/17 (`tests/test_surgeries_usuario_permissions.py` + `tests/test_surgeries_manage_permission.py`, creados por el testing agent) y testing E2E de UI (`iteration_126.json`, `iteration_127.json`): "usuario" crea/edita cirugías y gestiona equipo/insumos sin error; "anestesia" sigue sin ver ningún botón de escritura (API 403 en los 9 endpoints de escritura, lectura sigue en 200); "medico"/admin/superadmin sin regresión; bypass de cancelación cerrado para todos los roles.
- ⚠️ Nota operativa: si en PRODUCCIÓN existe un documento personalizado para el rol "usuario" en `db.roles` (guardado vía Gestión de Roles) que no incluya `manage_sala_operaciones`, el valor por defecto (True) no se aplicará — verificar tras desplegar.
- ⚠️ Requiere redespliegue para producción (el reporte original llegó desde producción).

### Sesión 53 — Expediente Clínico Confiable: autoguardado de "Lectura de Exámenes" + diagnósticos persistentes (2026-02) — COMPLETADO y verificado
- 🎯 Plan aprobado por el usuario: (1) corregir el autoguardado de "Lectura de Exámenes" en Evaluación Oftalmológica, que nunca quedaba guardado si no se presionaba "Guardar" manualmente; (2) convertir los diagnósticos en una lista de problemas activos del paciente que se arrastra automáticamente de consulta en consulta hasta que se marquen como "Resuelto" (o se eliminen de la consulta donde se arrastraron).
- 🔍 **Causa raíz del autoguardado**: el endpoint `PATCH /api/evaluaciones/{id}/autoguardar` (`routes/evaluaciones.py`) filtra el body recibido contra una whitelist `allowed_fields` antes de escribir en Mongo; a `lectura_examenes` nunca se le agregó a esa lista (aunque sí existía en los modelos Pydantic y en el formulario del frontend), así que el autoguardado lo descartaba silenciosamente en cada ciclo, mientras que el botón "Guardar" (que usa el modelo completo `EvaluacionOftalmologicaUpdate`) sí lo persistía. Fix: se agregó `"lectura_examenes"` a `allowed_fields`. Se revisó el resto de la whitelist contra el modelo completo; no se encontraron otros campos de texto editables con el mismo problema.
- ✅ **Diagnósticos persistentes**: nuevo campo `resuelto: bool = False` en el modelo `Diagnostico` (`models/evaluacion_oftalmologica.py`). `GET /api/evaluaciones/paciente/{id}/historial-medico` ahora calcula `diagnosticos_activos` = diagnósticos de la evaluación MÁS RECIENTE del paciente (ordenada por fecha desc, cualquier tipo de consulta) que no tengan `resuelto=true`, y los agrega a la respuesta junto con antecedentes/medicamentos (mismo endpoint ya existente, mismo patrón). Como el cálculo siempre parte del estado actual de la última evaluación guardada, tanto marcar "Resuelto" como simplemente ELIMINAR un diagnóstico arrastrado de esa última consulta logran el mismo efecto: dejar de copiarse hacia adelante, sin necesidad de un mecanismo de borrado separado.
- ✅ **Frontend** (`EvaluacionOftalmologica.js`): `seleccionarPaciente` ahora precarga `formData.diagnosticos` desde `diagnosticos_activos` al iniciar una evaluación nueva (sin evaluación de hoy ya existente), editables igual que uno nuevo y sin distinción visual. Cada fila de diagnóstico tiene un botón "Resuelto" (ícono `CheckCircle`, test-id `diagnostico-resuelto-btn-{idx}`) que al presionarlo lo convierte en una insignia estática de solo lectura (`diagnostico-resuelto-badge-{idx}`, texto tachado, SIN botón para deshacer, tal como se definió en los supuestos del plan); el botón de eliminar (`diagnostico-eliminar-btn-{idx}`) se oculta para diagnósticos ya resueltos (para no poder borrar el registro histórico de esa consulta). Botón "Agregar" con test-id `diagnostico-agregar-btn`; input de descripción con test-id `diagnostico-descripcion-input-{idx}`.
- 🐛 **Bug encontrado y corregido durante testing**: la precarga de diagnósticos activos hacía que `tieneDatosClinicos(formData)` devolviera `true` solo por tener diagnósticos arrastrados, disparando el autoguardado y creando una evaluación de HOY vacía (sin médico ni datos reales) con solo abrir el expediente de un paciente crónico. Fix: `skipAutoguardadoRef.current = true` antes del `setFormData` de la precarga (mismo patrón ya usado en `cargarEvaluacion`), para que ese cambio puntual no dispare el ciclo de autoguardado; un cambio real del usuario sí lo dispara con normalidad. También se limpia el estado "Cambios sin guardar" cuando la precarga no disparó ningún guardado real.
- ✅ **Verificado por testing agent** (`iteration_124.json` y retest `iteration_125.json`, ambos frontend E2E con Playwright, rol superadmin): autoguardado de "Lectura de Exámenes" persiste tras recargar; sin regresión en motivo_consulta/antecedentes/examen/plan; diagnósticos activos se precargan correctamente (mismo texto y ojo); botón Resuelto se vuelve insignia sin reversa; siguiente evaluación nueva solo arrastra los no resueltos; eliminar un diagnóstico arrastrado también lo saca de consultas futuras; modo solo lectura (sellado) no muestra botones de acción pero sí la insignia; rol `anestesia` no puede acceder al módulo. Tras el fix del bug de auto-creación: confirmado que seleccionar un paciente con diagnósticos activos ya NO crea ninguna evaluación espuria (0 POST/PATCH), y que una edición real del usuario sí dispara el autoguardado normalmente.
- ⚠️ Requiere redespliegue para producción (el reporte original del usuario llegó desde producción).

### Sesión 52 — NOG: monto total + monto individual por servicio (2026-06)
- 🎯 En el ingreso de NOG se puede capturar el **Monto total del NOG** además del **Monto individual por servicio** (antes solo aparecía el individual). Ambos se muestran en la tabla.
- ✅ **Backend** (`routes/igss_nogs.py`): nuevo campo editable `monto_total` en `NogCreate`/`NogUpdate`, documento y `_nog_con_derivados` (fallback = precio×cantidad para NOG existentes). Si no se envía al crear, se asigna precio×cantidad.
- ✅ **Frontend** (`pages/GestionNOG.js`): campo "Monto total del NOG (Q)" (autosugerido = individual×cupos mientras no se edite a mano; respeta el valor manual), relabel "Monto individual por servicio"; nuevas columnas "Monto individual" y "Monto total" en la tabla.
- ✅ **Verificado**: testing agent `iteration_102.json` (autosugerencia 5×100→500; total manual 3000 respetado tras cambiar individual/cupos; columnas correctas; edición 3000→3500; default 4×250→1000). Backend confirmado por curl.
- ⚠️ Requiere redespliegue para producción.

**Última actualización**: 2026-06 (Sesión 52 — NOG: monto total + monto individual)

### Sesión 51 — Menú "NOG": ingreso y gestión central de NOG IGSS (2026-06)
- 🎯 Nuevo menú propio "NOG" (bajo IGSS) para dar de alta y administrar todos los NOG de todas las unidades en un solo lugar, sin entrar unidad por unidad.
- ✅ **Acceso (3 roles con acceso completo)**: SuperAdmin, Administrador IGSS y Administrador general. Se otorgó `manage_igss_units` al rol `admin` (`config/permissions.py`). El ítem del sidebar se muestra por **permiso** `manage_igss_units` (no por config de menú guardada), para garantizar visibilidad en despliegues existentes.
- ✅ **Backend** (`routes/igss_nogs.py`): nuevo `GET /api/igss-units/nogs/all` (lista global con `unidad_nombre`/`unidad_codigo` + derivados). Campo nuevo **`fecha_asignacion`** agregado a `NogCreate`/`NogUpdate`, al documento, y a `_nog_con_derivados`. Reutiliza `POST /{unit_id}/nogs` (crear eligiendo unidad) y `PUT /nogs/{nog_id}` (editar/activar-desactivar). Reglas de cupo (90% aviso, 100% bloqueo) y unicidad de número por unidad sin cambios.
- ✅ **Frontend**: nueva página `pages/GestionNOG.js` (ruta `/igss/nog`, `ProtectedRoute requiredPermission=manage_igss_units`): tabla de todos los NOG con buscador (número/servicio), filtros por unidad y estado, tarjetas de totales, diálogo crear/editar (unidad obligatoria y bloqueada al editar, fecha de asignación, tipo de compra, cupos, precio), y activar/desactivar por fila. Menú registrado en `menu_config.py` (`gestion_nog`) y en el sidebar (`Layout.js`). Cada página monta su propio `<Toaster />`.
- ✅ **Verificado**: testing agent `iteration_101.json` (backend 7/7; UI: render, crear con fecha_asignacion, validación, editar con unidad deshabilitada, toggle estado, buscador+filtros con totales; roles: superadmin/igss.admin ven y usan, usuario 403 y redirigido). Fix aplicado: faltaba `<Toaster/>` en la página.
- 🔜 Fase 2: exportación de la lista + alertas automáticas 90%/100%. Fase 3: control de vigencia/vencimiento.
- ⚠️ Requiere redespliegue para producción.

### Sesión 50 — Fix: Google Calendar no sincronizaba en producción (2026-06)
- 🐛 **Reporte**: en producción la integración con Google Calendar está conectada pero no sincronizaba (0 eventos importados en ~3 días).
- 🔍 **RCA (deployer)**: el scheduler interno SÍ corre en producción (1 worker uvicorn, job cada 10 min, `last_sync` avanzando). La causa real era un **fallo silencioso** en `routes/google_calendar.py::_sync_doctor`: ante CUALQUIER excepción (incl. `403 rateLimitExceeded`) hacía un resync recortado a hoy y **avanzaba `sync_token`/`last_sync` igualmente**, marcando como exitosa una ventana fallida → esos eventos nunca se volvían a leer.
- ✅ **Fix** (`_sync_doctor`): solo se hace resync completo ante un **410** (token inválido) real; errores transitorios (403/429/5xx) se reintentan con backoff (`execute(num_retries=5)`) y, si persisten, **se CONSERVA el token** (se reintenta en la próxima ventana) sin avanzar `last_sync`; el resync usa una ventana de **30 días** hacia atrás (no solo hoy) para recuperar lo perdido; `run_sync_all` ahora expone `errores[]` por médico.
- ✅ **Recuperación**: nuevo `POST /api/google-calendar/resync-full` (superadmin) reinicia el `sync_token` de todos los médicos conectados y resincroniza; botón "Resincronización completa" en `GoogleCalendarDialog`.
- ↩️ Se descartó la migración a cron de plataforma (el scheduler interno ya funciona); se mantuvo el job APScheduler cada 10 min.
- ✅ **Verificado**: test unitario con servicio Google mockeado (4/4): 403→token conservado; 410→resync y avance; éxito→avance; error de red→token conservado. Scheduler reiniciado y disparándose. Endpoints sync/resync-full OK (en preview 0 médicos conectados; las conexiones OAuth viven en la BD de producción).
- ⚠️ **Requiere REDESPLIEGUE**. Tras desplegar, el superadmin debe usar "Resincronización completa" (Agenda → Google Calendar) para recuperar los ~3 días omitidos.

### Sesión 49 — IGSS Fase 2 (limpieza + recálculo) y Fase 3 (no crear vacías) (2026-06)
- 🎯 Continuación del plan de Producción IGSS. Decisiones del usuario: (1) consumo de NOG cuenta a un paciente solo si tiene una evaluación REAL de ese NOG; (2) limpieza borra todas las evaluaciones sin médico Y sin dato clínico; (3) limpieza para SuperAdmin + Administrador IGSS.
- ✅ **Definición unificada de "borrador vacío"** (`routes/igss_nogs.py`): `eval_es_borrador_vacio()` = sin médico Y sin contenido (`_eval_tiene_contenido`: igss_procedimiento, motivo/padecimiento/plan/**lectura_examenes**, diagnósticos, examen/AV/refracción, igss_med_proc, procedimientos, recetas, recomendaciones). **Antecedentes NO cuenta** (se autocargan del historial del paciente al abrir y persisten aparte en el paciente). Exime sellado/importado.
- ✅ **Fase 2 — Limpieza de borradores** (`GET/POST /api/igss-units/mantenimiento/borradores-vacios[/limpiar]`, roles superadmin/administrador_igss): preview con conteo+muestra, borrado con confirmación, audit log, limpia estados de producción huérfanos.
- ✅ **Fase 2 — Recálculo por evaluaciones** (`POST /api/igss-units/nogs/recalcular-por-evaluaciones`): recomputa acreditaciones exigiendo evaluación real; pacientes con solo borradores vacíos o sin evaluación liberan cupo; conserva acreditaciones manuales; resincroniza contadores. `_reconciliar_nog_paciente(..., solo_numeros=set)`.
- ✅ **Fase 3 — No crear evaluaciones vacías**: guard 422 en `POST /api/evaluaciones` si `eval_es_borrador_vacio`; frontend `tieneDatosClinicos` ya NO cuenta antecedentes (abrir un paciente ya no crea borrador); `lectura_examenes` agregado al modelo (Base+Update) y persiste; catch del autoguardado NO encola offline en errores 4xx (evita "pendientes" fantasma).
- ✅ **UI** (`UnidadesIGSS.js`): botón "Mantenimiento" (data-testid mantenimiento-igss-button) → diálogo con limpieza (preview+confirmar) y recálculo.
- ✅ **Verificado**: testing agent `iteration_100.json` (backend 13/13; lectura_examenes-only=200 persiste, antecedentes-only/vacía=422 por diseño; roles 403/200; UI: abrir sin trabajar no crea ni encola offline, motivo crea 1; mantenimiento borra con confirmación y recálculo OK).
- ⚠️ Requiere redespliegue para producción.

### Sesión 48 — Producción IGSS: una línea por paciente+orden, sin duplicados (2026-06)
- 🎯 **Objetivo**: la pestaña Producción IGSS repetía al mismo paciente (una fila por cada evaluación), inflando totales; además listaba evaluaciones en blanco creadas por error.
- ✅ **Consolidación (Fase 1, solo vista/reporte)** en `routes/igss_nogs.py` `_build_produccion_rows()`:
  - Una sola fila por `(paciente, orden)`. Orden = **No. SPS**; respaldo **NOG**; respaldo paciente/fecha.
  - Órdenes distintas (distinto No. SPS) del mismo paciente siguen separadas.
  - **Evaluaciones en blanco ocultas**: sin médico asignado Y sin datos clínicos (`_eval_tiene_contenido` revisa procedimiento IGSS, diagnósticos, examen/AV/refracción, med/proc IGSS, recetas, recomendaciones, motivo/padecimiento/plan). No se listan ni suman.
  - Representante del grupo = evaluación más reciente **con contenido**; se usa su `evaluacion_id` para abrir/imprimir/costo.
  - Estados (Impreso/Enviado/Facturado/Pagado) se **combinan (OR)** entre las evaluaciones de la orden para mostrar.
- ✅ **PATCH `/produccion/{evaluacion_id}`**: los estados booleanos se aplican a **todas** las evaluaciones de la orden (marcar/desmarcar estable y consistente); `costo_override` solo al representante. Helpers `_resolver_orden`/`_order_key` compartidos.
- ✅ Totales, subtotales por unidad/NOG y **exportación Excel** derivan de las filas consolidadas (sin inflar). No se borran registros de la BD.
- ✅ **Verificado**: testing agent `iteration_98.json` (backend 22/22 incl. `test_produccion_consolidacion.py`; UI e2e: SPS-110 consolidó 17 evals → 1 fila, 59 filas = Servicios 59, subtotales = Producción Q69,700, marcar/desmarcar estable tras recarga).
- 🔜 **Fase 2** (pendiente): herramienta para limpiar en BD los borradores vacíos existentes (con confirmación) y recalcular consumo de NOG. **Fase 3**: no crear evaluación hasta que haya un dato real (evitar borradores desde el origen).
- ⚠️ Requiere redespliegue para producción.

### Sesión 47 — Fix: expedientes de días anteriores EDITABLES (no "sellados") (2026-06)
- 🐛 **Reporte**: evaluaciones de días anteriores aparecían como "Solo lectura (día anterior)" y no deberían. (Esto se había introducido en la Sesión 44 como solo-lectura.)
- ✅ **Fix** (`EvaluacionOftalmologica.js`): `isReadOnly` ya NO incluye `esEvalDiaAnterior` → las evaluaciones de días anteriores son **editables**. Se conserva un badge informativo ámbar "Evaluación de día anterior". El **sellado manual** (`sellado=true`) sigue bloqueando la edición.
- ✅ **Protección contra modificación espuria**: nuevo `skipAutoguardadoRef` — al CARGAR una evaluación no se dispara autoguardado (0 requests, `fecha_actualizacion` intacta); el guardado solo ocurre al EDITAR realmente. Esto resuelve, de forma correcta, el problema original de la Sesión 44 (que abrir una eval previa cambiaba su fecha) sin bloquear la edición.
- ✅ **Verificado**: testing agent `iteration_96.json` 100% (editar+persistir día anterior; abrir sin editar no modifica; regresión one-per-day, "Nueva" y sellado manual OK).
- ⚠️ Requiere redespliegue para producción.

### Sesión 46 — Fix: el código IGSS corregido ahora se refleja en el PDF (2026-06)
- 🐛 **Bug**: al corregir el Código IGSS (y NOG/No. SPS/Procedimiento) en la orden del paciente, el cambio se veía en el modal de editar paciente pero el PDF del reporte seguía mostrando el valor anterior.
- 🔎 **Causa**: el PDF leía el *snapshot* IGSS guardado en la evaluación (`evaluacion.igss_codigo`, etc.) en vez de la orden actual del paciente.
- ✅ **Fix** (`routes/evaluaciones.py`, bloque IGSS del PDF): ahora, si la evaluación tiene `igss_orden_id`, el PDF toma los datos ACTUALES de esa orden en `paciente.igss_ordenes` (nog, no_sps, codigo, procedimiento); si no, usa el snapshot de la evaluación y, por último, los campos legacy del paciente. Así las correcciones a la orden se reflejan en el informe.
- ✅ **Verificado**: curl/pypdf con un registro real — tras corregir el código de la orden, el PDF muestra el valor corregido (ya no el anterior). Backend-only; sin cambios de frontend.
- ⚠️ Requiere redespliegue para producción.

### Sesión 45 — Buscador de pacientes en la Agenda · próximas citas (Fase 1) (2026-06)
- ✅ **Buscador de pacientes en la Agenda**: botón "Buscar paciente" (`buscar-paciente-agenda-btn`) abre un diálogo donde se escribe nombre/apellido (coincidencia parcial, sin acentos/mayúsculas vía `patientApi.search`). Al elegir un paciente se listan sus **citas futuras** (de hoy en adelante, zona Guatemala), ordenadas de la más próxima a la más lejana, con fecha, hora, médico, tipo y badge de estado. Incluye **Canceladas** y **"No asistió"** marcadas con su estado. Tocar una cita abre su detalle/edición (`handleOpenCitaDialog`). Mensajes claros "Sin citas próximas" y "Sin resultados".
- ✅ **Backend** (`routes/agenda.py`): nuevo `GET /api/agenda/paciente/{paciente_id}/citas-futuras` → citas con `fecha >= today_str_gt()` (todos los estados), ordenadas por fecha+hora, enriquecidas con institución. `agendaApi.getCitasFuturasPaciente`.
- ✅ **Verificado**: testing agent `iteration_95.json` 100% (5 flujos: búsqueda parcial/acentos, listado ordenado con estados, abrir detalle, "Sin citas próximas", "Sin resultados") + curl.
- **Futuro (Fases 2-3)**: filtros por médico/fecha/estado; agendar desde el resultado; historial de citas pasadas; búsqueda por expediente/DPI/teléfono.
- ⚠️ Requiere redespliegue para producción.

### Sesión 44 — Una sola evaluación por paciente por día + Observaciones en receta de medicamentos (2026-06)
- ✅ **Una evaluación por paciente por día (Fase 1 del plan aprobado)** (`EvaluacionOftalmologica.js`): al abrir el expediente de un paciente, si ya existe una evaluación de HOY (zona Guatemala, `fecha === today_str_gt`) se **continúa** esa misma (se carga como evaluación en curso vía `cargarEvaluacion(evalHoy, false)` → el autoguardado hace PATCH, no POST). Si no hay de hoy, formulario en blanco que se registra como la del día al primer guardado. Compartida entre médicos (toma la más reciente de hoy). `fetchEvaluaciones` ahora retorna la lista.
- ✅ **Botón "Nueva" ajustado**: mantiene el paciente seleccionado y limpia solo lo clínico, para crear una evaluación ADICIONAL el mismo día de forma explícita (antes deseleccionaba al paciente, lo que impedía crear adicionales con el auto-continuar).
- ✅ **Evaluaciones de días anteriores = SOLO LECTURA**: `isReadOnly` ahora incluye `esEvalDiaAnterior` (fecha ≠ hoy). Al abrir una evaluación previa desde el Historial ya NO se le envía autoguardado (antes cambiaba su `fecha_actualizacion`). Se muestra badge "Solo lectura (día anterior)" y el botón "Volver a la evaluación del día" regresa a la editable.
- ✅ **Observaciones en Receta de Medicamentos**: nuevo campo de texto libre (`receta-medicamentos-observaciones`) para toda la receta. Modelo `RecetaMedicamentos.observaciones`; se muestra en el PDF ("Observaciones:") y persiste. El PDF sigue en 1 página.
- ✅ **Verificado**: testing agent `iteration_93.json` (Flujo 1 y 2) + `iteration_94.json` 100% (solo-lectura día anterior sin PATCH, observaciones persiste, sin duplicados, "Nueva" funciona) + curl (persistencia + PDF).
- **Futuro (Fases 2-3)**: aviso de quién inició la evaluación del día; herramienta para fusionar duplicados previos; control de edición simultánea.
- **Nota**: NO existe integración ni cron con Google Calendar (consulta del plan respondida).
- ⚠️ Requiere redespliegue para producción.

### Sesión 43 — Sellado automático de expedientes a las 24h DESACTIVADO (temporal) (2026-06)
- ✅ **Se desactivó el sellado automático de expedientes a las 24 horas** a petición del usuario (se reactivará después). El mecanismo activo estaba en el **frontend** (`EvaluacionOftalmologica.js`): un `useEffect` calculaba una cuenta regresiva ("Se sella en Xh Ym") y marcaba `sellado=true` localmente al cumplirse 24h desde `fecha_creacion`, dejando el expediente en solo lectura.
- ✅ **Implementación**: se agregó la bandera `const SELLADO_24H_ACTIVO = false;` que corta el `useEffect` (no muestra cuenta regresiva ni auto-sella). **No se borró código de backend** ni la lógica: para reactivar basta poner la bandera en `true`.
- ✅ El **sellado MANUAL** (`sellado=true` en BD) sigue funcionando normalmente e independiente del cambio. El backend (`verificar_sellado`) ya no aplicaba el límite de 24h (era no-op), por lo que no requirió cambios.
- ✅ Verificado: el frontend compila sin errores; solo 3 evaluaciones con `sellado=true` en BD (seals manuales, no automáticos — el frontend nunca persistía el auto-sello).
- ⚠️ Requiere redespliegue para producción.

### Sesión 42 — El reporte PDF entra siempre en 1 sola página + etiquetas Binocular/Cerca (2026-06)
- ✅ **Reporte PDF garantizado en 1 página** (`routes/evaluaciones.py`): se envolvió toda la historia del PDF en `KeepInFrame(mode='shrink')` dimensionado al área disponible. Si el contenido excede una página se **encoge proporcionalmente** para caber; si es poco, se mantiene a tamaño normal. Reproducido el bug con una evaluación con TODOS los campos llenos (desbordaba a 2 páginas) → ahora 1 página, legible, con firma al pie. Verificado con pypdf (PAGES=1) + captura visual.
- ✅ **Etiquetas "Binocular" y "Cerca"** (`EvaluacionOftalmologica.js`): se quitó el prefijo "AV" de las etiquetas de los dos campos de texto libre (siguen en la misma línea).
- ⚠️ Requiere redespliegue para producción.

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

## Accesorios en Óptica + Punto de Venta (2026-06) — COMPLETADA y verificada
Solicitud: "Agrega a optica, la opcion de accesorios, agrega las opciones al punto de ventas".

### Backend (/app/backend/routes/optica.py)
- Nuevos modelos Accessory (name, brand, description, cost_price, sale_price, stock) + CRUD en colección `optica_accessories`:
  - GET /api/optica/accessories (search, low_stock; requiere view_optica)
  - POST/PUT/DELETE /api/optica/accessories (soft-delete; requiere manage_optica_inventory)
- SaleItemV2.type ahora admite "accessory"; create_optica_sale_v2 (POST /sales/v2) procesa items tipo accessory, valida y descuenta stock.
- menu_config.py: AVAILABLE_MENUS y DEFAULT_MENU_CONFIG (rol optica) incluyen `optica_accesorios`.
- server.py: migración idempotente agrega `optica_accesorios` a todo menu_configurations que ya tenga `optica_pos`.

### Frontend
- Nueva página /optica/accesorios (Accesorios.js) para gestión de inventario; ruta en App.js; nav item "Accesorios" (Layout.js, testId nav-optica-accesorios, icono Watch) condicionado a isMenuEnabled('optica_accesorios').
- OpticaPOS.js: nueva categoría "Accesorios" (CATEGORIAS_OPTICA), fetch/render/carrito; mapeo tipo 'accesorios' -> 'accessory'. Tras venta exitosa ahora refresca stock (fetchProductos()).
- POSProductCard.js: soporte de icono/nombre/stock para accesorios.

Verificado: backend E2E vía curl (crear/listar/vender descontó stock 20->18, menú incluye optica_accesorios para rol optica). Testing agent frontend 100% (5/5 flujos: nav, CRUD accesorio, categoría POS con tarjetas, venta accessory ORD-202611-0002 stock 9->7, categorías existentes intactas). Issues restantes LOW y pre-existentes (sin cap de stock en cliente).

## Ventas de Clínica — módulo de revisión y análisis (2026-11) — COMPLETADA y verificada
Solicitud: "el mismo modulo de ventas que creaste para optica, crealo para la clinica". Opciones del usuario: SOLO revisar/analizar (crear ventas sigue en el POS); mostrar los TRES rankings (Médicos, Productos, Categorías); incluir tarjetas de métricas, gráfico de 6 meses, exportar informe Excel+PDF, FEL desde el detalle, anular (admin/superadmin).

### Backend (/app/backend/routes/ventas.py)
- Nuevos endpoints (todos con dependencia manage_sales, registrados ANTES de /ventas/{venta_id} para evitar colisión de rutas):
  - GET /api/ventas/dashboard/stats → ventas_mes, ordenes_mes, ticket_promedio, ventas_hoy, ordenes_hoy, anuladas_mes (mes actual, zona GT).
  - GET /api/ventas/dashboard/monthly-chart → últimos 6 meses.
  - GET /api/ventas/dashboard/top-medicos | top-productos | top-categorias (?limit, mes actual).
  - GET /api/ventas/reports/monthly?year&month&format=excel|pdf → StreamingResponse (openpyxl / reportlab).
- VentaResponse ahora incluye `fel` (para el FELButton) y los campos de anulación; además se hicieron tolerantes (defaults) los campos que faltaban en 2 ventas legacy (bodega_id, cantidad_items, subtotal, descuento_total, iva, formas_pago, vendedor_id, created_at) — esto corrigió un 500 en GET /api/ventas?limit=200.
- anular_venta: ahora permite rol admin ADEMÁS de superadmin; guarda contra docs legacy sin bodega_id/producto_id al devolver inventario.
- listar_ventas: búsqueda con re.escape (corrige 500 con caracteres como '(' '[' '*'); filtro de fechas usa dia_gt_a_rango_utc (zona GT).
- fel.py certificar: rechaza facturar ventas con estado 'anulada' / status 'cancelado'.

### Frontend
- Nueva página /app/frontend/src/pages/VentasClinica.js (data-testid ventas-clinica-page): tarjetas, gráfico recharts, rankings en pestañas (tab-top-medicos/productos/categorias), filtros (búsqueda con debounce 400ms, estado, fechas), tabla, detalle con FELButton origen="clinica" (oculto si anulada), reimprimir ticket (print client-side), anular con motivo+devolver inventario, exportar informe Excel/PDF (años dinámicos).
- api.js: ventasApi.getDashboardStats/getMonthlyChart/getTopMedicos/getTopProductos/getTopCategorias/getMonthlyReport.
- App.js: ruta /ventas-clinica (ProtectedRoute requiredPermission="manage_sales").
- Layout.js: ítem de menú Finanzas > "Ventas" (nav-ventas-clinica, icono TrendingUp, hasPermission('manage_sales')); añadido a arrays de resaltado.

Verificado: curl (5 dashboards con datos reales, Excel 6KB/PDF válidos, list limit=200=200, getById incluye fel, search con '(' =200, rango fechas=200); testing agent iteration_121 (backend 19/20, frontend 90% — todos los flujos pedidos OK). Issues del reporte corregidos: search 500 (HIGH), FEL en anuladas (MEDIUM), fechas GT, docstring/guard anular, feedback de error. NO cambiado a propósito: el rol 'optica' puede abrir /ventas-clinica por URL (consistente con que óptica ya usa POS/CxC de clínica; el menú lo oculta).

### Ventas de Clínica — filtros por Médico y Vendedor (2026-11) — COMPLETADA y verificada
- Backend: GET /api/ventas/filtros/opciones devuelve {medicos, vendedores} distintos presentes en ventas de clínica; listar_ventas acepta medico_id y vendedor_id.
- Frontend (VentasClinica.js): dos Selects (ventas-medico-filter, ventas-vendedor-filter) + botón limpiar (ventas-filtros-clear) que reinicia todos los filtros; api.js ventasApi.getFilterOptions; fila de filtros con flex-wrap/items-end.
- Verificado: curl (opciones=1 médico/2 vendedores; medico_id→4, vendedor_id→44) y UI (filtrar por Dr. Carlos Méndez → "Lista de Ventas (4)").

### Ventas de Clínica — restringido SOLO a superadmin (2026-11) — confirmado por el usuario
- Backend (ventas.py): listar_ventas (GET /api/ventas) con check superadmin inline; filtros/opciones, dashboard/stats, monthly-chart, top-medicos/productos/categorias, reports/monthly y anular usan Depends(require_superadmin_dep()). getById se dejó SIN restringir (lo comparte el POS/PuntoVenta). ventas/hoy y resumen-dia intactos para el POS.
- Frontend: App.js ruta /ventas-clinica con ProtectedRoute requiredRole="superadmin"; Layout.js el ítem de menú "Ventas" ahora solo si isSuperAdmin.
- Verificado: curl superadmin=200 en todos; usuario=403 en los endpoints del módulo pero 200 en ventas/hoy y resumen-dia (POS no afectado). UI: usuario no ve el menú y /ventas-clinica redirige a /pacientes.

## Sociedades Médicas — consumos por venta + informes + acceso admin (2026-11) — COMPLETADA y verificada
Problema: el módulo mostraba 0 consumos (leía de movimientos_inventario, que no existe para productos sin inventario ∞ y usaba el costo), y al administrador el botón "Sociedades" lo mandaba a Pacientes (ruta con requiredPermission="manage_users").

### Backend (/app/backend/routes/inventario.py)
- Nuevo helper _recolectar_consumos_sociedad(db, sociedad_id, producto_id, fecha_gte/lt/lte): arma los consumos desde la colección `ventas` (origen=clinica, estado != anulada, items.producto_id en productos es_sociedad). Cada línea de venta = 1 consumo, valuado al PRECIO DE VENTA (item.subtotal). Incluye histórico y productos sin control de existencia.
- Reescritos: GET /sociedades/consumos (paginación en memoria; resumen total_cantidad/total_costo=monto), /sociedades/resumen (+param sociedad_id), /sociedades/exportar/excel y /pdf (+param sociedad_id, columnas con montos de venta y columna Sociedad). ConsumoSociedadItem ganó sociedad_nombre; costo_unitario/costo_total ahora llevan precio/monto de venta.
- Ventas anuladas excluidas.

### Frontend
- Sociedades.js: pestaña Consumos con columnas Fecha/Producto/Sociedad/Cantidad/Monto; tarjeta "Costo Total"→"Monto Vendido" y "Monto Vendido del Mes" en Resumen; consumos+productos se cargan al montar (tarjetas ya no quedan en 0); page se reinicia a 1 al cambiar filtros.
- App.js: ruta /sociedades con ProtectedRoute requiredRole={['admin','superadmin']} (antes manage_users) → admin ya entra, no lo manda a Pacientes.

Verificado: testing agent iteration_122 backend 22/22 (12 nuevos + 10 regresión CRUD), admin 200 y abre el módulo, usuario 403 + redirige a /pacientes; UI tarjetas Total Consumos 51 / Monto Vendido Q18,810.00, filtros y Excel/PDF OK. Pendiente opcional (no bloqueante): límites de mes/fechas en hora local GT (hoy en UTC, pequeño sesgo); date-picker shadcn y data-testids en tabs/filtros. Fase 2/3 (ranking por sociedad, comparación de meses, envío por correo) quedan pendientes.

### Sociedades — columnas Paciente y Médico en Consumos (2026-11)
- inventario.py: _recolectar_consumos_sociedad agrega medico_nombre; ConsumoSociedadItem gana paciente_nombre y medico_nombre; endpoint consumos los expone. Excel (cols Fecha/Código/Producto/Sociedad/Paciente/Médico/Cantidad/Monto Unit./Monto Total) y PDF (detalle con Paciente/Médico) actualizados.
- Sociedades.js: tabla Consumos ahora Fecha/Producto/Sociedad/Paciente/Médico/Cantidad/Monto.
- Verificado: curl (paciente/medico presentes), Excel/PDF 200, y UI muestra Paciente+Médico.

## Flujo IGSS: ingreso del paciente alimenta Producción (SPS + descripción NOG) (2026-11) — Fase 1 COMPLETADA y verificada
Causa: _build_produccion_rows/_resolver_orden solo completaban No. SPS/procedimiento desde la orden cuando la evaluación NO traía NOG; si la evaluación traía NOG pero no SPS, salía "—" y Procedimiento quedaba en blanco.

### Cambios (backend /app/backend/routes/igss_nogs.py)
- _resolver_orden: ahora, cuando la evaluación trae NOG, busca la ORDEN del paciente con el mismo NOG (prefiere la que tenga No. SPS) y completa No. SPS, código y procedimiento faltantes. Si la evaluación no trae NOG, usa la primera orden.
- _build_produccion_rows: nog_map incluye nombre_servicio; Procedimiento = proc (eval/orden) o, si está vacío, el nombre del servicio del NOG del catálogo de la unidad. Fila agrupada por unidad+NOG, fecha = fecha de la evaluación/consulta.

### Ya existente (no requirió cambios, confirmado)
- Una línea y un descuento por autorización (NOG+No. SPS): _reconciliar_nog_paciente / _crear_acreditacion dedup por (nog_id, paciente_id, no_sps).
- Descuento independiente del rol (se dispara en create/edit paciente, gated solo por create_patients/edit_patients).
- Múltiples órdenes por paciente: formulario Pacientes.js (igss_ordenes, add/remove, NOG/SPS/código/procedimiento) sin candado de rol.
- Recálculo/reproceso: POST /api/igss-units/nogs/recalcular-por-evaluaciones (permiso manage_igss_units).

### Verificación (escenario real controlado, luego limpiado)
- Evaluación con igss_nog=12345678, igss_no_sps='' y orden con no_sps='SPS-TEST-777' → fila de Producción: unidad "Zona 11", NOG 12345678, No. SPS 'SPS-TEST-777', Procedimiento 'Cirugia de catarata', fecha = fecha eval.
- Reconciliación del paciente de prueba creó 1 acreditación (SPS-TEST-777) y NOG acreditados 1→2. Datos de prueba eliminados, contador restaurado a 1.
- Página /igss/unidades pestaña Producción carga sin errores.

Fase 2 (pendiente): validaciones al ingresar (aviso SPS faltante / NOG sin cupo) e indicador de datos incompletos por fila. Fase 3: reportes comparativos por unidad/período y envío programado.

## FEL Digifact — RESUELTO (2026-11): NUC certifica correctamente en TEST
Causa raíz del error [3064] "Root element is missing" en PrepareEmisorForTOSIGN: NO era aprovisionamiento de Digifact (el archivo de ejemplo que Digifact envió certificó con NUESTRAS credenciales/token → emisor sí habilitado). El problema estaba en cómo construíamos el NUC:
1. **Seller.TaxID debía ir SIN ceros a la izquierda** (90042247), no el padding de 12 dígitos (000090042247). El XSD de SAT (tipoNITDelEFACE) rechaza el NIT con padding. (El TAXID del query param y el login SÍ usan los 12 dígitos; solo el Seller.TaxID del cuerpo va sin padding.)
2. **AdditionalDocumentInfo (ADENDA) debía ser bien formada**: con AditionalData.Data -> INFORMACION_ADICIONAL (OBSERVACIONES) y AditionalInfo VALIDAR_REFERENCIA_INTERNA=NO_VALIDAR. La ADENDA mínima [{Code,Type}] hacía que el transform generara un XML de emisor vacío → el error 3064.
Diagnóstico por morphing: el archivo correcto de Digifact certificó con nuestro token (code 1); al reemplazar solo la ADENDA por la nuestra, fallaba en PrepareEmisorForTOSIGN; al corregir ADENDA aparecía [3010] NITEmisor inválido (padding); corrigiendo ambos → code 1.
Archivos: /app/backend/routes/fel.py _build_nuc (Seller.TaxID = taxid_12.lstrip('0'); AdditionalDocumentInfo bien formado).
Verificado contra https://testnucgt.digifact.com/api v2/transform/nuc_json: FACT CF 1 ítem (Q168) → code 1 AUTH; FACT 2 ítems + NIT receptor → code 1 AUTH. Las pruebas se hicieron llamando al API directo (no por /certificar), no se persistió nada en BD. FEL sigue con enabled según config (el admin lo activa en Configuración FEL).

## Correcciones de producción Agenda + Evaluación (2026-11) — COMPLETADAS y verificadas (testing agent 4/4)
1. Receta de Medicamentos: la impresión mostraba 'indicaciones_generales' (campo inexistente); ahora muestra 'Observaciones' (recetas.medicamentos.observaciones). EvaluacionOftalmologica.js ~3685.
2. Agenda: nuevo 'Deshacer llegada' en el menú de la cita cuando está Presente/En consulta (CitaCard onCancelarLlegada → PATCH /agenda/citas/{id}/revertir-llegada, que ya existía). Agenda.js CitaCard + 3 instancias.
3. Tablero del Día: se quitó el filtro !medicosOcultos de 'Citas del día' y 'Pacientes Presentes' para que compilen TODAS las agendas, aunque haya médicos ocultos en el Calendario. (Nota: 'Citas del día' usa el estado `citas` que respeta el medicoFiltro/estadoFiltro explícito del Calendario; por defecto 'todos'.)
4. 'Ver paciente' ahora navega en la MISMA pestaña (navigate a /pacientes?id=) en vez de window.open _blank. Agenda.js handleVerPaciente.
Verificado por testing agent iteration_123 (frontend 4/4 PASS). Pendiente menor no bloqueante: handleVerEvaluacion sigue abriendo nueva pestaña con param 'paciente=' (no estaba en alcance).

## Rol anestesia: acceso a Sala de Operaciones (2026-11) — CORREGIDO y verificado
Causa: el rol anestesia tenía el permiso view_sala_operaciones pero NO tenía documento en menu_configurations (enabled_menus vacío). Las rutas /sala-operaciones y /quirofano/* usan requiredMenu (revisa enabled_menus), por eso la página salía en blanco y redirigía a /pacientes, y el menú no aparecía.
Fix:
- backend/routes/menu_config.py: DEFAULT_MENU_CONFIG["anestesia"] = ["sala_operaciones","quirofano_insumos","quirofano_anestesia"] (submenú completo). Se resuelve por defecto sin necesidad de doc en BD; funciona en preview y producción.
- frontend/src/App.js: DefaultRedirect y ProtectedRoute.defaultPage → el rol anestesia aterriza en /sala-operaciones (no /pacientes).
Verificado: login como anestesia aterriza en /sala-operaciones con la lista de cirugías; sidebar muestra Sala de Operaciones con Cirugías + Insumos y Equipos Qx + Proced. de Anestesia; rutas /quirofano/anestesia y /quirofano/insumos-equipos cargan sin redirigir. Las páginas no tienen candado de rol (SalaOperaciones usa hasPermission('view_sala_operaciones') que anestesia ya tiene). Nota: crear/editar registros de procedimientos de anestesia requiere permiso edit_expenses (anestesia hoy solo ve/lee salvo cirugías); si se requiere que registre procedimientos, ampliar esos endpoints.

## Sala de Operaciones: campo LIO + columna Pre-Ops (2026-11) — COMPLETADO y verificado
- Pausa: la plantilla/import masivo de cirugías históricas (oct/nov/meses siguientes) quedó en pausa a pedido del usuario; pendiente retomar.
1. Campo "LIO" (texto libre, opcional) en el formulario de registrar/editar cirugía, justo después de "Ojo a operar". Backend: `lio: Optional[str] = ""` en SurgeryBase/SurgeryUpdate/SurgeryResponse (routes/surgeries.py).
2. Columna "LIO" en el listado de cirugías, después de "Procedimiento". También agregada a los exports Excel y PDF (reports/surgeries) después de la columna Procedimiento, con ajuste de anchos/índices de columnas.
3. Columna "Pre-Ops" en el listado, después de "Anestesia": botón-badge que alterna Completos (verde)/Incompletos (ámbar) con un clic, sin abrir el formulario de edición. Backend: campo `preop_status` (default "incompleto") + endpoint `PATCH /api/surgeries/{id}/preop-status` body `{estado: "completo"|"incompleto"}`, protegido con permiso `view_sala_operaciones` (no `edit_expenses`) para que el rol anestesia —que solo tiene ese permiso— pueda usarlo. También visible/editable en el modal de detalle de la cirugía.
Verificado: curl end-to-end (login anestesia + superadmin, toggle completo/incompleto, rechazo de valor inválido 400) y click real en UI (toast, color del badge, revertido) en preview. Sin regresión de overflow horizontal (la tabla ya usaba scroll horizontal por tener muchas columnas).

## Plantilla Excel de cirugías + descarga desde la app (2026-11) — COMPLETADO
- Endpoint `GET /api/surgeries/template` (permiso `view_sala_operaciones`) genera un .xlsx con hoja "Cirugías" (encabezados + 2 filas de ejemplo + listas desplegables para Ojo/Tipo Anestesia/Institución/Pre-Ops) y hoja "Instrucciones". Botón "Plantilla Excel" en la toolbar de Cirugías (routes/surgeries.py, services/api.js `downloadTemplate`, SalaOperaciones.js `handleDownloadTemplate`).
- Sigue siendo solo para ingreso MANUAL (sin importación automática todavía).

## Carga masiva real de cirugías oct/2026–ene/2027 (2026-11) — COMPLETADO (reemplaza datos de ejemplo en preview)
- El usuario llenó la plantilla con datos reales (192 filas, `cirugias_novavision_oct2026_ene2027.xlsx`) y pidió borrar las 10 cirugías de ejemplo y cargar las reales en su lugar.
- Script de una sola ejecución `backend/scripts/import_surgeries_from_excel.py`: 1) borra `db.surgeries` + `anesthesia_records`/`notas_cirugia` asociados a esos ids, 2) parsea el Excel y valida/normaliza, 3) inserta 192 cirugías + genera sus registros de anestesia vía `upsert_anesthesia_from_surgery` (igual que haría la API).
- Normalizaciones aplicadas durante la carga: Institución vacía con "Institución: X" en Observaciones → `institution="Seguro Privado"`, `insurance_name=X` (5 filas, todas "Intevisa"); anestesiólogo vacío → `"N/A"` (101 filas); ojo no reconocido/vacío se deja vacío (17 filas) — el frontend ahora muestra "—" en vez de un badge vacío (`getEyeBadge` en SalaOperaciones.js).
- **Pendiente de completar por el usuario (no bloqueante, datos reales incompletos en el Excel original):**
  - 69 cirugías IGSS sin No. SPS/Afiliación/Código/Costo (se guardaron con `igss_data: null`; al editarlas desde la UI con institución IGSS habrá que llenar esos campos porque el formulario los exige).
  - 109 cirugías "Seguro Privado" sin nombre de aseguradora (`insurance_name` vacío; el formulario de edición lo exige si se vuelve a guardar).
  - 17 cirugías sin ojo especificado.
  - Fila 2 del Excel (paciente "Exceresis de Pterigion", 2026-10-01 08:30): el nombre del paciente parece ser en realidad el procedimiento (posible error de captura); se importó tal cual, revisar manualmente.
- Verificado: total 192 vía API, muestra IGSS/Seguro Privado/fechas correctas, búsqueda y badges en UI con datos reales.

## Filtro de Mes (reemplaza filtro de Ojo) + Excel con una hoja por mes (2026-11) — COMPLETADO
- Listado de Cirugías: el filtro "Ojo" (Todos/OD/OS/AO) fue reemplazado por un filtro "Mes" con formato `Mes/Año` (ej. "Noviembre/2026"), poblado dinámicamente con los meses que realmente tienen cirugías (`GET /surgeries/options` ahora devuelve `months`, orden descendente). Al elegir un mes se ignoran los inputs de fecha Desde/Hasta (quedan disponibles para rangos manuales cuando no hay mes seleccionado). Nuevo query param `month=YYYY-MM` en `GET /surgeries` y en `GET /reports/surgeries` (filtra con regex de prefijo sobre `date`).
- Exportar a Excel (`GET /reports/surgeries?format=xlsx`): antes generaba una sola hoja "Cirugías" mezclando todos los meses; ahora agrupa por mes y crea **una hoja por mes** (ej. "Octubre 2026", "Noviembre 2026", "Enero 2027"), cada una con sus propios encabezados/formato/fila de totales, sin mezclar meses. Si se exporta con el filtro de mes activo, el archivo trae solo esa hoja. El export a PDF no se modificó (sigue siendo una tabla única).
- `filterEye`/columna "Ojo" en la UI del listado se mantienen igual (badge "—" cuando no hay dato); solo se quitó el dropdown de filtro por ojo.
- Verificado con curl (options.months, filtrado por mes, conteo por hoja del xlsx = 192 en total repartidos en 3 hojas) y click real en el dropdown en preview, sin overflow horizontal.

## Ajustes de listado de Cirugías (2026-11) — COMPLETADO
1. Se eliminó la columna "Costo Proc." del listado (el dato sigue visible en el detalle de cada cirugía, dentro de "Insumos"/IGSS).
2. Botón "Hoy" junto a los filtros de fecha: fija Desde=Hasta=fecha actual (Guatemala) y limpia el filtro de Mes; clic de nuevo lo desactiva. Se mantiene sincronizado con `useEffect` existente (no requirió lógica de fetch adicional).
3. Se quitó el lápiz "Editar" de la columna Acciones del listado; el botón "Editar" ya existía dentro del modal "Ver detalle" (abre el formulario de edición desde ahí). Ajustado `colSpan` de la fila expandida de 13 a 12 tras quitar la columna de costo.
- Verificado con click real en preview: columna de costo ya no aparece, "Hoy" filtra correctamente a las cirugías del día (3 resultados de prueba), y el detalle conserva el botón "Editar".

## Investigación: "Tipo de Compra" IGSS desactualizado en PDF (producción) — SIN CAUSA RAÍZ EN CÓDIGO, pendiente de repro exacta
- El usuario reportó que al corregir el campo "Tipo de Compra" de un paciente IGSS, el PDF impreso sigue mostrando el valor viejo. Señaló la pantalla "Pacientes → Exportar PDF".
- Revisión exhaustiva (preview + diagnóstico directo contra producción vía deployer): `update_patient` persiste el campo correctamente (sin caché); los 3 lugares del código que leen `igss_tipo_compra` para generar PDFs/Excel (patients.py `export_patients_pdf`, evaluaciones.py `get_evaluacion_pdf`, igss_nogs.py exports de acreditación NOG) lo consultan EN VIVO desde `db.patients` en cada generación — confirmado que producción corre el mismo código, no una versión vieja con snapshot congelado.
- Dato clave: el PDF de "Pacientes → Exportar PDF" (listado completo) **no tiene columna "Tipo de Compra"** (ni en preview ni en producción); esa etiqueta solo aparece en la receta/Evaluación Oftalmológica y en los reportes de acreditación NOG IGSS. Las rutas de export ya tienen `Cache-Control: no-store` (middleware global `SecurityHeadersMiddleware`, confirmado con curl).
- **Pendiente**: pedir al usuario una captura real del PDF con el dato viejo (o repetir la prueba en incógnito) para identificar la pantalla exacta — lo más probable es que sea la receta de Evaluación Oftalmológica o el reporte de acreditación NOG, no el listado de Pacientes, o que el PDF que revisó era un archivo ya descargado previamente (no uno recién generado).

## Paciente rápido desde Registrar Cirugía (2026-11) — Fase 1 COMPLETADO y verificado
- **Backend** (`routes/patients.py`): nuevo endpoint `POST /api/patients/quick` (permiso `create_patients`) recibe `{name}`, separa primera palabra como `first_name` y el resto como `last_name` (vacío si es una sola palabra), genera expediente normal vía `get_next_record_number()`, y crea el paciente con el resto de campos en blanco. `enrich_patient()` ahora calcula `datos_incompletos` (True si falta `gender`, `birth_date`, `phone` o `referral_institution`) en cada lectura — sin flag persistido, se recalcula solo. Se agregó el campo a `PatientResponse` y un filtro `GET /patients?incomplete=true` (combinando `$and` con el filtro de `search` existente cuando ambos aplican).
- **Frontend Sala de Operaciones** (`SalaOperaciones.js`): en el buscador de paciente del formulario "Registrar cirugía", cuando no hay coincidencias y el usuario tiene permiso `create_patients`, aparece el botón "Crear paciente nuevo: '<nombre>'" que llama a `patientApi.createQuick()` y vincula el `patient_id` igual que si se hubiera seleccionado un paciente existente (reutiliza `selectPatient`). Sin ese permiso, se muestra "Sin coincidencias".
- **Frontend Pacientes** (`Pacientes.js`): badge ámbar "Datos incompletos" junto al nombre cuando `patient.datos_incompletos`; columnas Género/Edad/Teléfono/Institución muestran "—" si están vacías; botón toggle "Datos incompletos" junto a Buscar/Filtros que activa `filters.incomplete` (se combina con el resto de filtros existentes, sin romper el flujo de búsqueda).
- Verificado end-to-end con curl (crear rápido → aparece en `incomplete=true` → se vincula a una cirugía → se completa vía PUT normal → `datos_incompletos` pasa a `false` y desaparece del filtro) y con clicks reales en preview (flujo completo en Registrar Cirugía + badge/filtro en Pacientes). Dato real encontrado: 886 pacientes existentes de la base de producción ya calificaban como "incompletos" con esta definición (no es un bug, es data real preexistente que el filtro ahora expone).
- Fase 2 (aviso de cirugía próxima con expediente incompleto, sugerencia de fusión por duplicados) y Fase 3 (extender el alta rápida a Agenda) quedan en backlog, no implementadas aún.

## Migración de datos preview → producción (2026-11) — EN PROGRESO
- Al publicar, solo se envía código, nunca el contenido de la base de datos; por eso producción (admin.novavision.me) tenía `surgeries` en 0 tras el deploy anterior (confirmado por diagnóstico de solo lectura contra producción).
- Intento de conexión directa del agente a la base de datos de producción (connection string `mongodb+srv://` provisto por el usuario, guardado como secreto `PROD_MONGO_URL`) falló: DNS resuelve bien, pero el egress de red de este pod de preview bloquea conexiones salientes al puerto 27017 (TCP timeout), solo permite HTTPS/443. No es viable conectar directo a Atlas desde el agente.
- Solución aplicada: nuevo endpoint operativo `POST /api/admin/migrate-seed-data` (routes/admin.py), protegido por header `X-Migration-Key` comparado contra el secreto `MIGRATION_SECRET_KEY` (no requiere sesión de usuario, es una operación de infraestructura). Lee `backend/data/prod_migration_seed.json` (bundle con las 192 cirugías reales + sus `anesthesia_records` + el documento del rol `anestesia` + el usuario `anestesia`, todos ya en preview) y hace upsert por id/name/username (idempotente, se puede reintentar sin duplicar).
- Autoprueba contra preview: `surgeries:192, anesthesia_records:192, role_anestesia:true, user_anestesia:true` — OK.
- Se disparó un deploy a producción incluyendo este endpoint + el archivo de semilla. Pendiente: una vez termine el deploy, llamar `POST https://admin.novavision.me/api/admin/migrate-seed-data` con el header `X-Migration-Key` (slot "live" del secreto) y verificar el conteo resultante.
- Nota aparte investigada y descartada: el reporte de que el submenú "Procedimientos de Anestesia" no aparece para el rol anestesia **en preview** se reprodujo con una sesión 100% nueva (localStorage limpio) y el submenú sí aparece correctamente — es consistente con que el usuario tenía una pestaña/sesión vieja abierta desde antes del fix anterior. No se requirió cambio de código.
- **Cambio de enfoque final**: el usuario pidió no seguir con el endpoint de secreto (`/admin/migrate-seed-data`, que fue ELIMINADO del código junto con el fixture `data/prod_migration_seed.json`) y en su lugar pidió un botón para subir el Excel él mismo. Se construyó esa función (ver sección siguiente) y es la vía definitiva para esta migración; los secretos `PROD_MONGO_URL` y `MIGRATION_SECRET_KEY` quedaron guardados pero sin uso (no se pudieron borrar desde aquí, inofensivos).

## Importar Excel de Cirugías en bloque (2026-11) — COMPLETADO y desplegado
- Nuevo endpoint `POST /api/surgeries/import` (multipart, solo `superadmin` vía JWT normal, sin secretos): recibe el Excel de la "Plantilla Excel" ya existente, valida que tenga la hoja "Cirugías", y por cada fila válida crea una cirugía nueva (no borra ni reemplaza las existentes) aplicando las mismas normalizaciones toleranates que el script de carga inicial (institución vacía con "Institución: X" en Observaciones → Seguro Privado + insurance_name; anestesiólogo vacío → "N/A"; ojo inválido/vacío se deja vacío con advertencia; IGSS sin datos administrativos se deja `igss_data: null` con advertencia; fila sin fecha/hora/paciente/procedimiento/cirujano/anestesia se omite). También genera el `anesthesia_record` de cada cirugía igual que el alta normal.
- Frontend: botón "Importar Excel" (ícono Upload, solo visible para `isSuperAdmin`) junto a "Plantilla Excel" en Sala de Operaciones; al subir el archivo muestra un diálogo con el conteo de creadas + lista de advertencias para revisar después.
- Verificado con curl (crea N filas, devuelve advertencias, 403 para rol no-superadmin) y con clic real en preview (file picker → upload → toast → diálogo de resultado), limpiando los registros de prueba después.
- Reemplaza el enfoque anterior (migración directa a producción vía endpoint con `MIGRATION_SECRET_KEY` o conexión directa a `PROD_MONGO_URL`, descartado: la conexión directa a Atlas desde el pod de preview está bloqueada por egress de red en el puerto 27017, y el usuario prefirió no depender de sincronizar secretos test/live). Desplegado a producción; pendiente que el usuario entre como superadmin a producción y suba el mismo Excel (`cirugias_novavision_oct2026_ene2027.xlsx`) con este nuevo botón.

## Fix: rol "anestesia" seguía marcando error en Procedimientos de Anestesia (2026-11) — RESUELTO y verificado
- Causa raíz real (confirmada, no era de menú/permiso): `ProcedimientosAnestesia.js` mostraba el botón "Agregar tipo", la columna "Acciones" y los íconos de editar/activar-desactivar a **cualquier rol** autenticado, pero el backend (`routes/quirofano.py`, endpoints `POST/PUT/DELETE /quirofano/anesthesia/types...`) solo autoriza `admin`/`superadmin`/`usuario`. El rol `anestesia` sí tenía el menú y el permiso correctos (`view_sala_operaciones`), por eso la ruta cargaba bien, pero al pulsar cualquiera de esos botones recibía `403 Se requiere rol [...]`, que es el "error" que el usuario seguía viendo pese a tener rol/permiso asignados.
- Fix aplicado: se agregó la prop `canManage` a `TiposTab`, calculada en el componente padre como `['admin','superadmin','usuario'].includes(user.role)`, y se ocultan condicionalmente el botón "Agregar tipo", el `<th>`/`<td>` de "Acciones" y los botones de editar/activar-desactivar cuando `canManage` es falso. El endpoint `GET /quirofano/anesthesia/types` (listado, solo lectura) sigue abierto a cualquier usuario autenticado, así que `anestesia` ve el catálogo de precios en modo solo lectura, sin botones que fallen.
- Verificado en preview con la cuenta `anestesia` (password reseteado a `anest2024`, hash anterior no coincidía — documentado en test_credentials.md): login → `/quirofano/anestesia` → solo aparece la pestaña "Tipos de anestesia", sin "Agregar tipo" ni columna "Acciones" (screenshot). Regresión con `superadmin`: ambas pestañas y todos los botones de gestión visibles sin cambios (screenshot). `curl` confirmó `GET` 200 y `POST` 403 para el rol `anestesia`, reproduciendo exactamente el bug reportado antes del fix.
- Pendiente: el usuario mencionó que el error ocurría "tanto en preview como producción"; este fix está solo en preview. Se necesita un nuevo deploy para que la corrección llegue a `admin.novavision.me`.

## Rol anestesia: acceso de solo-lectura a Cierre mensual (2026-11) — COMPLETADO y desplegado
- El usuario pidió (reportando desde producción) que el rol `anestesia` pueda ver el "Cierre mensual" de Procedimientos de Anestesia (antes solo veía "Tipos de anestesia").
- Backend (`routes/quirofano.py`): se agregó `"anestesia"` a los roles permitidos en `GET /quirofano/anesthesia/closure` y `GET /quirofano/anesthesia/closure/export` (ver totales por anestesiólogo y exportar Excel/PDF). `POST /quirofano/anesthesia/closure/close` (cerrar mes y marcar pagado) y `POST /closure/reopen` siguen restringidos a admin/superadmin — confirmado con curl que `anestesia` recibe 403 ahí.
- Frontend (`ProcedimientosAnestesia.js`): `canSeeCierre` ahora incluye `anestesia` (pestaña "Cierre mensual" visible y es la pestaña por defecto); se agregó prop `canClose` a `CierreTab` — si el rol no puede cerrar el mes, en vez del botón "Cerrar mes y marcar pagado" se muestra un badge de solo lectura "Mes abierto (pendiente de pago)" (o el badge "Mes cerrado (pagado)" si ya está cerrado, igual que antes).
- Verificado en preview: curl como `anestesia` → `GET closure` 200, `GET closure/export` 200, `POST closure/close` 403. Screenshot con sesión `anestesia` muestra la pestaña "Cierre mensual" abierta por defecto, con totales por anestesiólogo, botones Excel/PDF, y el badge "Mes abierto (pendiente de pago)" en vez del botón de cerrar.
- Deploy a producción disparado tras este fix (job encolado; incluye también el fix anterior de los botones de gestión de "Tipos de anestesia").

## Cierre mensual de Anestesia: desglose por procedimiento (paciente/fecha/procedimiento/médico) (2026-11) — COMPLETADO y desplegado
- El usuario pidió ver en el Cierre mensual (pantalla, Excel y PDF) el desglose de cada procedimiento: nombre del paciente + fecha, tipo de procedimiento, y médico responsable (cirujano) — antes solo se veían totales agrupados por tipo de anestesia.
- Backend (`routes/quirofano.py`, `_build_closure`): ahora hace join de `anesthesia_records` del mes con `surgeries` por `surgery_id` para traer `procedure` y `surgeon` en vivo (no se duplican/congelan en el registro de anestesia). Cada grupo por anestesiólogo agrega un array `detalle` con `date, patient_name, procedure, surgeon, tipo, value`, ordenado por fecha. Se mantiene también `tipos` (resumen por tipo) por compatibilidad, aunque la UI ya no lo usa para el listado.
- Frontend (`ProcedimientosAnestesia.js`): la tabla de cada anestesiólogo ahora muestra columnas Fecha | Paciente | Procedimiento | Médico responsable | Tipo de anestesia | Honorario, una fila por procedimiento real. Página ensanchada a `max-w-6xl`; cada tarjeta de anestesiólogo tiene `overflow-x-auto` para scroll horizontal en móvil.
- Export Excel y PDF (`closure/export`): mismas columnas que la pantalla (Anestesiólogo, Fecha, Paciente, Procedimiento, Médico responsable, Tipo de anestesia, Honorario), con fila de subtotal por anestesiólogo y total general al final.
- Fix de regresión de layout aprovechado en el mismo cambio: `Layout.js` tenía un bug de flexbox (`min-width: auto` por defecto en flex items) que causaba overflow horizontal de toda la página en cualquier vista con una tabla ancha; se agregó `min-w-0` a los contenedores flex principales (`<div className="flex-1 flex flex-col...">` y `<main className="flex-1 p-6 lg:p-8 overflow-auto">`). Verificado sin regresión en Sala de Operaciones y en esta misma página (scrollWidth === clientWidth en viewport móvil 390px).
- Verificado con curl (GET closure trae `detalle` con paciente/fecha/procedimiento/médico correctos; export xlsx y pdf devuelven 200 y archivos válidos) y con screenshots desktop (1920x800) y móvil (390x844) como `superadmin`.
- Deploy a producción disparado tras este fix.

## Cierre mensual de Anestesia: columna Institución (2026-11) — COMPLETADO
- El usuario pidió agregar también el tipo de institución (Novavision, Alquiler, Seguro Privado, IGSS) al mismo desglose (pantalla, Excel, PDF).
- Backend: `_build_closure` ahora también trae `institution` de la cirugía vinculada y la agrega a cada item de `detalle`.
- Frontend: nueva columna "Institución" entre "Médico responsable" y "Tipo de anestesia" en la tabla de cada anestesiólogo (ancho mínimo de la tabla ajustado a 760px para el scroll horizontal en móvil).
- Excel y PDF: nueva columna "Institución" agregada en la misma posición; anchos de columna reajustados para que el PDF siga cabiendo en una página carta.
- Verificado con curl (campo `institution` presente en `detalle`, ej. "Seguro Privado", "Novavision") y con screenshots desktop/móvil; sin overflow horizontal de página (scrollWidth === clientWidth en 390px).

## Feature: rol "usuario" puede editar datos de pacientes desde Sala de Operaciones (2026-11) — COMPLETADO
- El usuario pidió que el rol "usuario" pueda editar los datos de un paciente desde Sala de Operaciones y desde "Editar cirugía". Alcance confirmado por el usuario: SOLO en esos dos lugares (el módulo general de Pacientes sigue de solo lectura para este rol) y con TODOS los campos del paciente editables.
- Nuevo permiso escopado `edit_patients_in_surgery` (distinto de `edit_patients`) agregado para el rol "usuario" en **dos** matrices de permisos que coexisten en el backend (hallazgo importante, ver nota abajo): `backend/config/permissions.py` (usada por `require_permission`/`require_any_permission` en `routes/auth.py`, que protege el endpoint real `PUT /api/patients/{id}`) y `backend/server.py` (una matriz de permisos DUPLICADA/heredada usada específicamente por el login/`/auth/me` que alimenta `AuthContext` y por lo tanto el `hasPermission()` del frontend). Ambas deben mantenerse sincronizadas para cualquier permiso nuevo — **riesgo conocido para futuros cambios de permisos**: si solo se edita `config/permissions.py`, el backend acepta la acción pero el botón no aparece en el frontend porque el login sigue devolviendo la matriz vieja de `server.py`.
- Nuevo helper `require_any_permission([...])` en `routes/auth.py`; `PUT /api/patients/{id}` ahora acepta `edit_patients` O `edit_patients_in_surgery`.
- Bloqueador descubierto durante la implementación: el rol "usuario" tampoco tenía acceso al menú "Sala de Operaciones" (ni en el default de `menu_config.py` ni en la configuración personalizada ya guardada en `db.menu_configurations` para ese rol desde 2026-10-15). Se agregó `"sala_operaciones"` a ambos. Esto da acceso de SOLO VISUALIZACIÓN a la lista/detalle de cirugías (el permiso `view_sala_operaciones`, que controla crear/editar/cancelar/eliminar cirugías, se dejó en `False` para "usuario" — no se pidió expandir eso).
- Nuevo componente reutilizable `frontend/src/components/PatientEditDialog.js`: formulario completo de edición de paciente (todos los campos: datos personales, contacto de emergencia, institución referente, unidad/órdenes IGSS, comentarios), independiente del formulario de Pacientes.js (no se tocó ese archivo para evitar riesgo de regresión en un componente grande y sensible). Usa `patientApi.getById`/`patientApi.update`.
- Integrado en `SalaOperaciones.js` en dos puntos: (1) el diálogo "Ver detalle" de una cirugía (enlace "Editar paciente" junto al nombre del paciente, visible si la cirugía tiene `patient_id` vinculado); (2) el formulario compartido de "Registrar/Editar cirugía" (enlace "Editar datos del paciente" junto al mensaje "✓ Vinculado al expediente"). Gateado por `canEditPatient = hasPermission('edit_patients') || hasPermission('edit_patients_in_surgery')`, independiente del permiso de edición de la cirugía en sí.
- Verificado end-to-end como "usuario": login → Sala de Operaciones visible → abrir detalle de una cirugía vinculada a un paciente real → clic en "Editar paciente" → formulario completo cargado → edición de teléfono → guardado exitoso ("Paciente actualizado exitosamente"). Verificado que el módulo general de Pacientes sigue sin botón de editar para este rol (regresión OK).

## Fix: Reagendamiento de cirugías no creaba cirugía en la nueva fecha + falta de hora (2026-11) — RESUELTO
- El usuario reportó (en producción): al cancelar y reagendar una cirugía, no se agrega nada en la nueva fecha, y pidió además que el formulario de reagendamiento incluya la hora.
- Causa raíz (confirmada leyendo el código, igual en preview y producción — no era una regresión de deploy sino una funcionalidad nunca implementada): el endpoint `POST /api/surgeries/{id}/cancel` solo marcaba la cirugía original como "cancelado" y guardaba `rescheduled_to` como un simple campo de texto informativo. Nunca creaba un nuevo registro de cirugía en la fecha reagendada, por eso no aparecía nada en el listado de ese día.
- Fix backend (`routes/surgeries.py`): `cancel_surgery` ahora acepta `reschedule_time` además de `reschedule_date`. Si se indica fecha de reagendamiento, se crea una NUEVA cirugía activa (`status: "activo"`) en esa fecha/hora, clonando todos los datos clínicos (paciente, procedimiento, cirujano, ojo, LIO, tipo de anestesia, anestesiólogo, institución, datos IGSS/seguro) con equipo/insumos vacíos y Pre-Ops en "incompleto" (es una nueva cirugía, no hereda lo ya usado). También se crea su registro de anestesia asociado (igual que al registrar una cirugía nueva). La cirugía original cancelada guarda `rescheduled_to`, `rescheduled_to_time` y `new_surgery_id` (referencia a la nueva) para trazabilidad.
- Fix frontend (`SalaOperaciones.js`): el diálogo "Cancelar cirugía" ahora tiene dos campos lado a lado (fecha + hora) en "Reagendar para", con nota explicativa "Se creará una nueva cirugía activa en esa fecha y hora con los mismos datos." El detalle de una cirugía cancelada muestra fecha+hora de reagendamiento y un indicador "— nueva cirugía creada ✓" cuando aplica.
- Verificado end-to-end en preview: cancelación con reagendamiento vía curl y vía UI real (clic en ícono cancelar, llenar motivo + fecha 22/12/26 + hora 11:15, enviar) → toast "Cirugía cancelada y reagendada" → la nueva cirugía aparece activa en el listado en la fecha/hora correctas con los mismos datos clínicos; la original queda marcada como cancelada (fila atenuada). Datos de prueba revertidos tras la verificación.

## Fix: rol "optica" no podía guardar/autoguardar evaluaciones ni recetas pese a tener permisos asignados (2026-11) — RESUELTO
- El usuario reportó (en producción): al rol "optica" ya se le asignaron los permisos de Evaluación Oftalmológica/Recetas desde Gestión de Roles, pero al guardar o esperar el autoguardado sigue apareciendo "no tiene permisos".
- Causa raíz confirmada leyendo el código (reproducible igual en preview, no específico de producción): los endpoints de `routes/evaluaciones.py` (crear evaluación, actualizar evaluación, autoguardar, actualizar historial médico, agregar medicamento desde receta, agregar a CRM cirugías) **no usan el sistema de permisos configurable** (`view_evaluacion`/`manage_recetas`) en absoluto. Cada uno tiene una validación de rol **hardcodeada** en el código: `if current_user["role"] not in ["superadmin", "admin", "usuario", "medico", "administrador_igss"]: raise 403`. El rol "optica" nunca estuvo en esa lista, así que ningún toggle de permisos en Gestión de Roles podía arreglarlo — la pantalla de administración de roles le hacía creer al usuario que el permiso estaba activo, pero el código del backend lo bloqueaba de todas formas.
- Fix: se agregó `"optica"` a la lista de roles permitidos en los 6 endpoints afectados de `routes/evaluaciones.py` (crear, actualizar, autoguardar, historial médico, agregar medicamento de receta, agregar a CRM cirugías).
- Verificado con curl usando la cuenta `optica`/`Optica2024$` en preview: `POST /evaluaciones` (crear), `PATCH /{id}/autoguardar` y `PUT /{id}` (actualizar) devuelven 200 (antes 403 "No tiene permisos para crear/editar evaluaciones"). Dato de prueba creado y eliminado tras la verificación. La generación de PDF (`GET /{id}/pdf`) ya funcionaba para cualquier rol autenticado — no requería cambios.

## Feature: pago individual por procedimiento en Cierre mensual de Anestesia (2026-11) — COMPLETADO
- El usuario pidió poder seleccionar un paciente/procedimiento individual dentro del Cierre mensual y marcarlo como pagado, descontándolo del total a pagar del mes (sin esperar al cierre del mes completo).
- Backend (`routes/quirofano.py`): nuevo endpoint `POST /quirofano/anesthesia/records/{record_id}/pagar` (body `{"paid": true|false}`, restringido a admin/superadmin — mismo nivel que "Cerrar mes"; bloqueado con 400 si el mes ya está cerrado). El campo `paid` ya existía en `anesthesia_records` (usado antes solo por el cierre masivo) — ahora es editable por registro individual, con `paid_at`/`paid_by` para trazabilidad.
- `_build_closure` reestructurado: cada item de `detalle` ahora incluye `id` y `paid`; los totales (`total` por anestesiólogo, `total_general`, subtotales por tipo) representan SOLO los montos PENDIENTES (se descuentan automáticamente los ya pagados individualmente). Se agregan `total_pagado_general`, `num_pendientes` y `count_pagado` por grupo para mostrar el desglose pagado/pendiente.
- Frontend (`ProcedimientosAnestesia.js`, pestaña Cierre mensual): nueva columna "Pago" con botón "Marcar pagado" por fila (admin/superadmin, mes abierto); al pagar, la fila se atenúa y el botón cambia a "Pagado" con opción de revertir. El encabezado ahora muestra "Total a pagar del mes (N de M procedimientos pendientes)" y, si hay pagos parciales, un indicador adicional "Pagado: QX". El rol `anestesia` (solo lectura) ve un badge "Pagado"/"Pendiente" sin poder modificarlo.
- Excel y PDF: nueva columna "Estado" (Pagado/Pendiente) por fila; los subtotales/total general en ambos formatos ahora reflejan solo lo pendiente, igual que en pantalla.
- Verificado end-to-end en preview con `superadmin`: vía curl (marcar pago individual deduce correctamente Q800 del total Q1,600→Q800; rol `anestesia` recibe 403 al intentar) y vía UI real (clic en "Marcar pagado" sobre un procedimiento real de Q800, el total en pantalla baja de Q1,600.00 a Q800.00 al instante, toast de confirmación). Exportaciones Excel/PDF verificadas con la nueva columna "Estado" sin overlap. Datos de prueba revertidos (37/37 pendientes, Q1,600.00 total restaurado).

## Fix: texto superpuesto en PDF de Cierre + columna Institución no llegó a producción (2026-11) — RESUELTO
- El usuario reportó (desde producción) que: 1) el PDF de cierre mensual mostraba el texto de columnas como "Tipo" y "Procedimiento" superpuesto sobre "Honorario"/columnas vecinas, ilegible; 2) la columna "Institución" aún no aparecía en producción.
- Causa raíz #1: la tabla del PDF (`reportlab`) usaba strings planos en las celdas; los nombres de tipo de anestesia y procedimientos son texto libre largo (ej. "Local Asistida Faco / SICS", "Lentes Privados Galaxy 1 ojo") que no cabían en el ancho de columna y, como reportlab no envuelve strings planos, el texto se dibujaba fuera de los límites de la celda superponiéndose con la columna siguiente.
- Fix: todas las celdas de texto (Anestesiólogo, Paciente, Procedimiento, Médico responsable, Institución, Tipo, y la etiqueta de subtotal) ahora usan `reportlab.platypus.Paragraph` con un estilo de celda (`fontSize=7`), lo que hace que el texto largo se ajuste (word-wrap) dentro del ancho de columna en vez de desbordarse. La fecha se reformatea a `DD/MM/YY` (antes `YYYY-MM-DD`, que partía feo en la columna angosta). Anchos de columna reajustados a 7.5in totales (ancho de página carta menos márgenes) para que quepan las 8 columnas.
- Causa raíz #2: no era un bug de código — el deploy anterior con la columna Institución seguía en cola/procesándose cuando el usuario probó producción. Se confirma en preview que la columna sí existe en pantalla, Excel y PDF (incluida en el mismo fix de wrapping).
- Verificado en preview: PDF renderizado a imagen (pdftoppm) en 2 páginas, sin superposición de texto, con la columna Institución visible ("Seguro Privado", "Novavision", "IGSS") y filas de subtotal/total legibles. Excel también verificado con openpyxl (8 columnas correctas con Institución).
- Deploy a producción disparado con este fix (incluye la columna Institución del commit anterior).

## Fix: fechas de solo-día mostraban el día previo en Guatemala (UTC-6) (2026-11) — RESUELTO
- El usuario reportó: en el listado de Sala de Operaciones la fecha es correcta, pero en el listado mensual de Procedimientos de Anestesia marca el día previo.
- Causa raíz: la función compartida `formatDate` (`frontend/src/services/api.js`) siempre convertía el string recibido a hora de Guatemala con `toLocaleDateString(..., {timeZone: 'America/Guatemala'})`. Para timestamps completos esto es correcto, pero para strings de **solo fecha** (`YYYY-MM-DD`, sin hora) JavaScript los interpreta como medianoche UTC; al convertir esa medianoche UTC a UTC-6, el resultado retrocede al día anterior. `SalaOperaciones.js` ya evitaba este bug con un parseo local (`new Date(dateStr + 'T00:00:00')`) pero `ProcedimientosAnestesia.js` usaba el `formatDate` compartido y sí lo sufría.
- Fix puntual: `ProcedimientosAnestesia.js` ahora usa el mismo patrón de parseo local que Sala de Operaciones (`formatDateDisplay`).
- Fix de raíz (tras hallazgo del testing agent de que el mismo bug podía afectar otras pantallas): `formatDate` en `services/api.js` ahora detecta si el string es exactamente `YYYY-MM-DD` (regex) y en ese caso lo formatea sin pasar por conversión de zona horaria; si trae hora/timestamp completo, mantiene el comportamiento anterior (conversión correcta a hora de Guatemala). Esto corrige automáticamente fecha de nacimiento de pacientes, vencimientos de Gastos, alertas del Dashboard, etc., sin tocar el formateo de timestamps con hora.
- Bug relacionado encontrado por el testing agent durante la verificación: `Gastos.js` → `getDaysUntilDue` tenía el mismo defecto (parseaba `due_date` con `new Date(dueDate)`), causando que el badge de "días para vencer" mostrara un día de menos en Guatemala. Corregido con el mismo patrón de parseo por componentes.
- Verificado por testing agent (`iteration_132.json`, `iteration_133.json`) en navegador con zona horaria emulada `America/Guatemala` y UTC: Cierre mensual de Anestesia (37 filas), Sala de Operaciones, fecha de nacimiento de pacientes, vencimientos de Gastos y alertas del Dashboard — todos correctos; timestamps completos (`created_at`, última modificación) siguen mostrando fecha/hora correctas sin regresión.

## Feature: informe diario de anestesia por correo (cron 5pm) (2026-11) — COMPLETADO
- El usuario pidió un cron diario a las 5:00pm que envíe por correo a `draherreranestesia@gmail.com` el informe de las anestesias del día (mismo formato/datos del PDF ya existente), y que en días sin procedimientos se envíe igual el informe en cero.
- Backend (`routes/quirofano.py`): `build_daily_report(date_str)` arma el detalle del día (paciente, procedimiento, médico responsable, institución, tipo de anestesia, anestesiólogo, honorario, estado) reutilizando `anesthesia_records` + join con `surgeries`, igual que el cierre mensual. `render_daily_report_pdf()` genera el PDF (mismo estilo visual que el cierre mensual, reportlab). Como la integración de correo gestionada por Emergent/Resend **no soporta adjuntos binarios**, el PDF se entrega vía un enlace público firmado (HMAC-SHA256 con `WEBHOOK_CRON_SECRET`, sin login, expira a los 21 días) servido por `GET /quirofano/anesthesia/daily-report/pdf?token=...`; un token inválido/expirado/forjado responde 404 (nunca expone datos).
- Backend (`routes/email_service.py`): `build_anesthesia_daily_html()` arma el correo HTML (tabla de detalle + totales + botón "Descargar PDF del informe", mismo estilo que el "Cierre del Día" ya existente). `enviar_informe_anestesia_diario()` siempre envía el correo, incluso con 0 procedimientos (Q0.00). Endpoint manual `POST /quirofano/anesthesia/daily-report/enviar?fecha=YYYY-MM-DD` (admin/superadmin/anestesia, valida formato de fecha → 400 si inválido). Endpoint de cron `POST /cron/informe-anestesia-diario` protegido con el mismo `WEBHOOK_CRON_SECRET` (Bearer) que el cron de cierre diario; responde 2xx de inmediato y envía en background.
- Nueva variable de entorno `INFORME_ANESTESIA_EMAILS="draherreranestesia@gmail.com"` en `backend/.env` (mismo patrón que `CIERRE_DIARIO_EMAILS`, admite múltiples correos separados por coma a futuro).
- Nueva entrada en `.emergent/crons.yml`: `informe-anestesia-diario`, `cron: "0 17 * * *"`, `timezone: America/Guatemala` → `POST {{BASE_URL}}/api/cron/informe-anestesia-diario`.
- Testing agent (`iteration_134.json`, 24/25 casos backend) encontró y se corrigieron 2 bugs menores: (1) un token forjado con bytes no-ASCII causaba 500 en vez de 404 en la descarga del PDF (ahora `_verify_report_token` compara bytes y atrapa el error correctamente); (2) el parámetro `fecha` del endpoint manual no validaba formato (ahora regex `YYYY-MM-DD`, 400 si inválido, aplicado también al endpoint existente de Cierre del Día por consistencia). Ambos fixes re-verificados con curl contra el enlace de preview tras el fix.
- Verificado con curl: envío manual con datos reales (200, correo aceptado por el proveedor), envío manual en un día sin procedimientos (200, informe en cero), descarga de PDF con token válido (200, PDF válido) y con token inválido/forjado (404), cron sin Bearer (401). Nota: durante pruebas repetidas se alcanzó el rate-limit del proveedor de correo (429 → nuestro código responde 502 "No se pudo enviar", comportamiento esperado y documentado en el playbook de email, no es un bug); en uso real (1 envío/día) esto no ocurre.

## Entregable: Manual Operativo del Superadministrador en PDF (2026-11) — COMPLETADO (Fase 1 / MVP)
- Plan aprobado en modo plan: manual completo en español, sin capturas de pantalla, explicando cómo operar todos los módulos desde la cuenta de superadmin, entregado como PDF descargable en el chat.
- Generador: `backend/scripts/generate_manual_superadmin.py` (reportlab, `BaseDocTemplate` + `TableOfContents` con `multiBuild` para resolver números de página reales en el índice). El contenido de cada sección se redactó revisando el código real (no se inventaron nombres de botones/menús): `config/permissions.py` y `db.roles` (roles y permisos reales de superadmin/admin/usuario/médico/óptica/anestesia/administrador_igss), `routes/menu_config.py` (labels y menús por rol por defecto), `routes/quirofano.py` (cierre mensual, pago individual, cerrar/reabrir mes), `routes/email_service.py` (horarios y contenido de los correos de Cierre del Día e Informe de Anestesia), `routes/backups.py` (respaldo semanal, botones "Ejecutar ahora"/descarga), `routes/caja.py`, `routes/fel.py`, `frontend/src/pages/SalaOperaciones.js`, `ProcedimientosAnestesia.js`, `Usuarios.js`, `FELButton.jsx` (nombres exactos de botones citados entre comillas).
- Secciones (13, con índice navegable y marcadores/outline del PDF): Introducción, Pacientes, Agenda, Sala de Operaciones, Procedimientos de Anestesia, Evaluaciones Oftalmológicas, Óptica y POS, Caja, FEL, Roles y Permisos, Respaldos, Correos automáticos, y Solución de problemas comunes (9 preguntas en formato Pregunta → Causa probable → Qué hacer).
- Estilo: portada azul marino con título, índice con números de página reales, recuadros ámbar de "ADVERTENCIA" para acciones riesgosas (ej. no cerrar el mes de anestesia sin confirmar pagos, no compartir la cuenta de superadmin), tipografía simple pensada para impresión en blanco y negro. No incluye contraseñas, llaves ni valores reales — solo referencia a dónde se gestionan.
- Entrega: generado en `/app/frontend/public/manual-superadmin-novavision.pdf` (servido como archivo estático por el mismo dominio del sistema, sin necesitar login). Verificado con `pypdf` (13 páginas, los 13 encabezados de sección presentes tanto en el índice como en el cuerpo) y visualmente con `pdftoppm` (portada, índice, recuadro de advertencia y sección de solución de problemas sin superposición de texto). Verificado que el archivo descarga correctamente (200, `application/pdf`) desde la URL pública del sistema.
- Pendiente (Fase 2, futuro, según lo acordado): agregar capturas de pantalla reales a cada sección una vez el usuario confirme que el diseño de cada módulo ya es estable. Fase 3: hojas de referencia rápida por rol derivadas de este manual.

## Feature: permiso acotado "Gestionar Equipo e Insumos" para roles tipo "sop" (2026-11) — COMPLETADO
- El usuario creó en producción un rol personalizado "sop" (vía la UI de "Gestión de Usuarios" → "Roles", que ya soporta roles 100% dinámicos) y pidió que ese rol pudiera agregar equipo/insumos en Sala de Operaciones, pero SOLO eso (confirmado explícitamente: sin crear/editar/cancelar/eliminar cirugías).
- Como el permiso existente `manage_sala_operaciones` controla TODO (crear, editar, cancelar, eliminar Y equipo/insumos), se introdujo un permiso nuevo y más granular: `manage_sala_operaciones_insumos`.
- Backend (`routes/surgeries.py`): los 6 endpoints de equipo/insumos (`POST/DELETE /surgeries/{id}/equipment`, `POST/PUT/DELETE /surgeries/{id}/supplies`, `PATCH /surgeries/{id}/supplies-status`) ahora aceptan `manage_sala_operaciones` **o** `manage_sala_operaciones_insumos` (usando el helper ya existente `require_any_permission`). Crear/editar cirugía (`POST`/`PUT /surgeries`) y cancelar/eliminar (`require_role(["superadmin","usuario"])`) NO cambiaron — siguen exigiendo el permiso/rol completo.
- Backend (`routes/roles.py`): se agregó `manage_sala_operaciones` y `manage_sala_operaciones_insumos` al catálogo `AVAILABLE_PERMISSIONS` (categoría "Clínica") — antes `manage_sala_operaciones` ni siquiera aparecía como casilla en la pestaña "Roles" de Gestión de Usuarios, por lo que no se podía asignar a un rol personalizado desde la UI. También se corrigió la descripción de `view_sala_operaciones` (antes decía "Ver y editar", ahora aclara que solo es visibilidad del menú).
- Frontend (`SalaOperaciones.js`): nueva variable `canManageSupplies = manage_sala_operaciones || manage_sala_operaciones_insumos`, usada para mostrar/ocultar los botones "+ Agregar equipo"/"+ Agregar insumo" y los botones de eliminar equipo/insumo (en las dos vistas: fila expandida de la tabla y el diálogo "Ver detalle"). El resto de controles (Editar cirugía, Cancelar, Eliminar, Registrar cirugía) siguen gateados solo por `canEdit` (permiso completo) o por rol, sin cambios.
- Probado en preview con un rol/usuario temporal (`sop_test`, solo `view_sala_operaciones` + `manage_sala_operaciones_insumos`, eliminado después de la prueba): agregar equipo (200), agregar insumo (200), crear cirugía (403), editar cirugía — PUT (403), eliminar cirugía (403), cancelar cirugía (403). Verificado visualmente que superadmin (permiso completo) sigue viendo los botones de agregar equipo/insumo sin regresión.
- Pendiente de acción del usuario: el rol "sop" existe solo en producción (no en preview), y este cambio de código recién se construyó aquí — **requiere desplegar a producción** antes de poder activar la casilla "Gestionar Equipo e Insumos" para ese rol desde "Gestión de Usuarios" → "Roles" en producción (y confirmar que el menú "Sala de Operaciones" esté habilitado en "Menús por Rol" para "sop").

## Bug reportado en producción: órdenes IGSS (NOG/SPS) "no se guardan" (2026-11) — RCA + fixes COMPLETADO
- Usuario reportó en producción: al ingresar NOG/SPS/tipo de compra/código en Órdenes IGSS de un paciente, "los datos no se guardan, se borran, se descuentan del NOG, pero no aparece la info en producción del IGSS". Se escaló a `emergent__send_to_deployer` (intent=debug) por ser síntoma en producción sin acceso directo.
- **RCA (confirmado por el deployer con datos reales de producción)**: la orden SÍ se guardó correctamente (paciente César Augusto Enríquez García, NOG 31461093/SPS 01-10124-2026-031995/código 417411, sin doble-submit, botón ya protegido con `disabled={submitting}`). La causa real: el NOG 31461093 **no existe en el catálogo** `igss_nogs` de "UNIDAD PERIFÉRICA ZONA 5" (catálogo real: 28761138, 28761545, 29917271, 29992028, 30006430). `NogSelector.js` permite escribir un NOG libre ("Otro") sin validar contra el catálogo, por lo que la orden se guarda pero: (a) `_reconciliar_nog_paciente` no encuentra el NOG → no crea acreditación → no se descuenta cupo (la frase "se descuenta del NOG" no se reprodujo para este caso puntual), y (b) "Producción IGSS" depende de evaluaciones + catálogo, así que esa orden no tiene match de precio/servicio.
- **Fix 1 (preview, listo)**: `NogSelector.js` ahora muestra una advertencia visible en ámbar cuando el NOG escrito en modo "Otro" no coincide con ningún NOG del catálogo de esa unidad: *"Este NOG no está registrado en el catálogo de esta unidad: no descontará cupo ni aparecerá en Producción IGSS..."*. Mismo componente reutilizado en Pacientes, PatientEditDialog (Sala de Operaciones) y Agenda. Probado reproduciendo el caso exacto (misma unidad/NOG del reporte) — warning se muestra correctamente.
- **Fix 2 (preview, listo, confirmado por el usuario)**: "Producción IGSS" (`_build_produccion_rows` en `igss_nogs.py`) ya no oculta en silencio las órdenes con NOG no catalogado (de hecho nunca las ocultaba del todo si había evaluación, pero no las distinguía) — ahora cada fila lleva `nog_catalogado: bool`, y el frontend (`ProduccionIGSS.js`) muestra un badge rojo "Pendiente de catalogar" tanto a nivel de fila como de grupo "NOG {numero}". La exportación a Excel agrega la columna "NOG Catalogado" (Sí/No).
- **Fix 3 (preview, listo, confirmado por el usuario)**: nuevo endpoint de mantenimiento `GET/POST /patients/mantenimiento/ordenes-legacy` y `/migrar-ordenes-legacy` (superadmin): migra (idempotente) pacientes IGSS con NOG/SPS/código "legacy" (campos antiguos `igss_nog`/`igss_no_sps`/`igss_codigo`) pero sin ninguna orden en `igss_ordenes`, creando esa orden visible en la ficha sin tocar ninguna acreditación/cupo ya existente. Botón nuevo "Migrar pacientes con NOG legacy" en el diálogo "Mantenimiento IGSS" (`UnidadesIGSS.js`), junto a los botones existentes de borradores vacíos y recálculo. Probado end-to-end con un paciente de prueba simulando el estado legacy exacto (creado directo en DB, migrado correctamente, verificado, eliminado).
- Pendiente de acción del usuario en producción: (1) registrar el NOG 31461093 en el catálogo de "UNIDAD PERIFÉRICA ZONA 5" (o corregir el NOG si fue un error de tipeo) para que ese paciente puntual quede resuelto; (2) **desplegar** estos 3 fixes a producción; (3) una vez desplegado, correr el botón "Migrar pacientes con NOG legacy" en producción para los 12 pacientes identificados por el RCA.

## Feature: filtro por médico/institución en Procedimientos de Anestesia (Cierre mensual) (2026-11) — COMPLETADO
- El usuario pidió poder filtrar el "Cierre mensual" de Procedimientos de Anestesia por médico responsable o por institución, y que la exportación (Excel/PDF) respete el filtro aplicado.
- Backend (`routes/quirofano.py`): `_build_closure(month, medico=None, institucion=None)` ahora filtra cada registro contra `surgeon`/`institution` de la cirugía asociada **antes** de agruparlo por anestesiólogo (así los totales/subtotales por anestesiólogo y el total general ya reflejan solo lo filtrado, y los grupos sin registros tras el filtro desaparecen del todo). `GET /anesthesia/closure` y `GET /anesthesia/closure/export` ahora aceptan los query params opcionales `medico` e `institucion`. El encabezado del Excel/PDF exportado muestra el filtro aplicado (ej. "Médico: Dr. Noriega").
- Nuevo endpoint `GET /anesthesia/closure/filtros?month=YYYY-MM` que devuelve los médicos e instituciones realmente presentes ese mes (listas `medicos`/`instituciones`, ordenadas), para poblar los selectores sin hardcodear valores.
- Frontend (`ProcedimientosAnestesia.js`): nueva barra "Filtrar por:" con dos `Select` (Médico responsable / Institución, ambos con opción "Todos/as") justo debajo de la selección de mes; botón "Limpiar filtros" visible solo cuando hay un filtro activo. Los filtros se reinician automáticamente al cambiar de mes (evita un filtro "fantasma" con valores que no existen en el nuevo mes). El total resumen y los botones Excel/PDF usan los mismos filtros activos (`medico`/`institucion` como query params), y la etiqueta cambia a "Total a pagar (filtrado)" / "Sin registros de anestesia con los filtros seleccionados" cuando hay un filtro aplicado. "Cerrar mes y marcar pagado" no cambió: sigue operando sobre el mes completo (no sobre el subconjunto filtrado), ya que no se pidió cierre parcial.
- Probado con curl contra datos reales de preview (noviembre 2026): `/filtros` devuelve 10 médicos y 3 instituciones reales; filtrar por médico, por institución y por ambos a la vez devuelve solo filas que coinciden (verificado con aserciones); export Excel y PDF filtrados devuelven 200 con archivo válido. Probado en navegador (desktop 1920×800 y mobile 390×844): seleccionar "Dr. Noriega" reduce la tabla de 37 a 10 filas (todas de ese médico), badge "Limpiar filtros" aparece, sin overflow horizontal nuevo introducido por la barra de filtros.

## Fix: Autoguardado confiable en Evaluación Oftalmológica (2026-11) — COMPLETADO (Fase 1 MVP)
- El usuario reportó: "algunos médicos y usuarios pierden información porque el autoguardado o el guardado manual fallan sin ningún aviso en pantalla" (plan aprobado con 3 fases; Fase 1 ejecutada).
- **Causa raíz real encontrada y corregida** (no era un supuesto, se reprodujo con curl y con un registro legacy sembrado a propósito): (A) `EvaluacionOftalmologicaCreate` exigía `List[...]` estricto para `diagnosticos`/`medicamentos_actuales`/`medicamentos_previos`/`procedimientos`/`recomendaciones`; si el formulario heredaba `null` en esos campos de una evaluación legacy/importada, el POST se rechazaba con 422 ANTES de que corriera cualquier código nuestro — y el frontend tenía una rama que ante 400/422 hacía `setAutoguardadoStatus('')` **sin toast, sin reintento, sin respaldo**: el médico no veía absolutamente nada. (B) `procesar_catalogos_evaluacion()` (en `routes/evaluaciones.py`, se ejecuta DESPUÉS de que el `update_one`/`insert_one` YA tuvo éxito) no tenía manejo de excepciones y lanzaba `TypeError`/`AttributeError` con listas en `None` o con items que eran strings sueltos (legacy) en vez de dicts — convirtiendo un guardado YA exitoso en un HTTP 500 para el frontend. (C) `EvaluacionOftalmologicaResponse` podía fallar con `ResponseValidationError` por el mismo motivo, rompiendo incluso la simple lectura (GET) de un registro ya envenenado.
- **Backend**: `backend/models/evaluacion_oftalmologica.py` — nuevo `normalizar_items_evaluacion_legacy()` (recursivo: limpia `None` dentro de cada item de lista, dentro de `recomendaciones.estudios_a_realizar` y `recetas.medicamentos.items`, y convierte items de texto suelto legacy en el dict mínimo válido) usado en `model_validator(mode="before")` de `EvaluacionOftalmologicaCreate`, `EvaluacionOftalmologicaUpdate` y `EvaluacionOftalmologicaResponse`. `backend/routes/evaluaciones.py` — `procesar_catalogos_evaluacion()` reescrito para nunca lanzar excepción (try/except + chequeos `isinstance`); nuevo `sanear_campos_legacy()` usado en el PATCH `/autoguardar` y el PUT de actualización para autocurar el documento en cada guardado.
- **Frontend** (`EvaluacionOftalmologica.js`): (1) `cargarEvaluacion()` normaliza explícitamente las 4 listas clínicas con `Array.isArray(...) ? ... : []` al cargar un registro, y conserva el nombre/edad/sexo/expediente del paciente ya mostrado si el registro legacy no los trae (antes vaciaba el encabezado); acepta un `pacienteOverride` opcional para evitar un closure obsoleto de `formData` cuando se llama justo después de seleccionar un paciente. (2) Reintento automático (`intentarConReintentos`, 1s/2s/4s, solo para 5xx/sin respuesta) aplicado tanto al autoguardado como al botón manual "Guardar", con el badge mostrando "Reintentando... (n/3)". (3) Eliminada la rama silenciosa de 400/422: ahora SIEMPRE se muestra un estado rojo claro (`mensajeFallaDefinitiva`: distingue 403 "no tienes permiso" de 400/422 "revisa los datos" de red/5xx "revisa tu conexión") + un toast con `extraerMensajeError` (soporta `detail` como string o como lista de errores 422 de FastAPI). (4) Respaldo local continuo (debounced 800ms) en `localStorage` bajo `novavision_eval_draft_<id o nueva_<pacienteId>>`, independiente de la cola de reintento offline; se limpia solo cuando el servidor CONFIRMA el guardado (con protección de timestamp para no borrar un borrador más nuevo si el usuario siguió escribiendo durante la petición). Si al abrir una evaluación (o iniciar una nueva para el mismo paciente) hay un borrador más reciente que el último guardado conocido, aparece un diálogo "Se encontró contenido sin guardar" con botones Descartar/Recuperar borrador (`data-testid="draft-recovery-dialog"`). (5) Nuevo indicador flotante fijo `position: fixed bottom-4 right-4` (`data-testid="autoguardado-floating-indicator"`) que permanece visible en toda la pantalla (incluso al hacer scroll por el formulario, que es largo) con los 4 estados de color del plan (verde/azul/ámbar/rojo); el badge del encabezado existente se recoloreó con el mismo criterio compartido (`getEstadoGuardadoClase`/`getEstadoGuardadoDot`). (6) Corregido un bug de duplicados: `limpiarColaOfflinePara()` ahora limpia la cola de reintento offline (y `syncPendingData` tiene una salvaguarda equivalente) apenas se confirma CUALQUIER guardado de ese paciente/evaluación, incluyendo entradas "crear" huérfanas (antes el sync periódico de 30s podía reenviar una entrada vieja y crear una evaluación duplicada, o pisar datos nuevos con una foto vieja).
- Nuevo archivo de regresión `backend/tests/test_evaluacion_guardado_confiable.py` (9 tests, cubre null en creación/actualización, items legacy en texto suelto, nulls anidados en recomendaciones/diagnósticos, lectura de registros legacy sin 500).
- Probado en 4 rondas con testing agent (iteration_135/136/137/138.json): ronda 1 encontró el RCA + 6 problemas, rondas 2-3 encontraron 2 problemas más de los fixes (closure obsoleto del encabezado, cola offline con match asimétrico causando evaluaciones duplicadas), ronda 4 = **PASS DEFINITIVO**, reprodujo exactamente el escenario de duplicado con `page.route` forzando 500 y confirmó que ya no ocurre (queda solo 1 evaluación con el dato más reciente). Fase 2 (edición simultánea, aviso a admin por fallos recurrentes) y Fase 3 (extender el patrón a otras pantallas largas) quedan pendientes, fuera de alcance de este pase.

## Feature: Agendar cita IGSS desde Registro de Cirugía (2026-11) — COMPLETADO (Fase 1 MVP)
- Plan aprobado: en "Registrar cirugía" (Sala de Operaciones), cuando Institución=IGSS, aparece un botón "Agregar a Agenda" junto a "Guardar registro". Al presionarlo: guarda la cirugía, abre un modal para elegir entre 4 médicos FIJOS (Dr. Cristian Acevedo, Dra. Mariamercedes Palma, Dr. Manuel de la Cruz, Dra. Rocío Muñoz — ésta última conceptualmente es "agenda general de la clínica" para el negocio, pero técnicamente es el mismo mecanismo de médico con agenda), y crea la cita en Agenda con la misma fecha/hora de la cirugía, mostrando solo paciente + institución IGSS + procedimiento.
- **Setup**: se crearon en preview los 4 médicos vía `POST /api/doctors` (sin `horario_semanal`, para no bloquear por reglas de horario que no aplican a este flujo) — no existían antes en la base de datos de prueba.
- **Backend**: NINGÚN endpoint nuevo. Se reutilizan 100% `POST /api/surgeries` (ya existente) y `POST /api/agenda/citas` (ya existente). La visibilidad de los 3 datos requeridos (paciente/IGSS/procedimiento) en la tarjeta de la cita se logra sin tocar `Agenda.js`: el badge "IGSS" sale automático del enriquecimiento ya existente `_enriquecer_instituciones` (mira `referral_institution` del paciente vinculado), el nombre del paciente ya se muestra siempre, y el procedimiento se pasa en `notas: "Procedimiento: {procedure}"` (campo que la tarjeta de cita ya renderiza de forma visible). `tipo_cita` se envía como `"Cirugía"` (string libre, sin restricción de enum en el modelo).
- **Frontend** (`SalaOperaciones.js`): `handleSaveSurgery` se refactorizó extrayendo la validación (`validarFormularioCirugia`) y el guardado (`guardarCirugia`, devuelve el registro guardado o `null`) para reutilizarlos en el nuevo `handleAgregarAAgenda` (guarda + abre el modal, matcheando los 4 nombres fijos contra `agendaApi.getMedicosAgenda()`) y `handleConfirmarAgendar` (crea la cita con `agendaApi.createCita`). Botón "Agregar a Agenda" (`data-testid="btn-agregar-a-agenda"`) visible solo si `institution === 'IGSS' && !editMode` (ver fix de duplicados abajo). Modal `dialog-agendar-cirugia`: resumen de paciente/institución/procedimiento/fecha-hora, 4 opciones tipo botón (`agendar-medico-option-{id}`), confirmación visual con ícono de check (`agendar-confirmacion`). Si el paciente de la cirugía no tiene `patient_id` vinculado a un expediente, se avisa con un toast y no se abre el modal (no se puede crear cita sin paciente real).
- **Fix de duplicados** (encontrado en ronda 1 de testing): el botón solo aparece en modo CREAR (`!editMode`), no al editar una cirugía IGSS ya guardada — evita crear una segunda cita duplicada al reabrir/editar un registro que ya se había agendado. Vincular/editar la cita desde la cirugía ya guardada queda para Fase 3 (explícitamente fuera de alcance).
- Probado en 2 rondas con testing agent (iteration_139/140.json): ronda 1 encontró el bug de duplicado (único hallazgo, resto 95% verde incluyendo flujo completo con los 4 médicos y cancelación sin confirmar), ronda 2 = **PASS 100%**, confirmó el fix y repitió el smoke test completo (crear cirugía IGSS → agendar → aparece en /agenda con badge IGSS + nota de procedimiento en la agenda del médico elegido; editar esa misma cirugía ya no muestra el botón y no duplica la cita). Fase 2 (horario distinto al de la cirugía, aviso de choque) y Fase 3 (extender a otras instituciones, vincular/editar/cancelar la cita desde la cirugía) quedan pendientes, fuera de alcance de este pase.

## Feature: Caja Chica — Óptica (2026-11) — COMPLETADO (Fase 1 MVP)
- Plan aprobado: nuevo menú "Caja Chica", primera opción del sidebar (arriba de todo). Registrar ingresos (monto+fecha) y egresos (solicitante+motivo+monto+fecha). Saldo continuo histórico (no se reinicia por mes). Historial con quién capturó cada movimiento. Edición: solo quien lo registró (o SuperAdmin). Eliminación: SOLO SuperAdmin. Informe de fin de mes (cualquier mes pasado) con resumen en pantalla + descarga Excel.
- **Aclaración de acceso resuelta con el usuario (ask_human)**: el plan decía "rol usuario", pero en el sistema el rol real del personal de Óptica es **`optica`** (ej. cuenta "diana"), mientras que `usuario` es un rol genérico sin ningún otro acceso a Óptica. El usuario confirmó: acceso = roles `optica`, `admin`, `superadmin` (NO `usuario`).
- **Backend**: `models/caja_chica.py` (validación con `model_validator`: `solicitante`/`motivo` obligatorios solo si `tipo=egreso`; `fecha` validada con `datetime.strptime` estricto YYYY-MM-DD, formato y calendario real) + `routes/caja_chica.py` (`GET /resumen`, `GET/POST/PUT/DELETE /movimientos`, `GET /informe?mes=`, `GET /informe/excel?mes=`, validación de formato `mes` regex `YYYY-MM` → 422 si inválido). Colección `caja_chica_movimientos`, ids `uuid4` (convención ya usada en el resto del backend, sin `BaseDocument`/`PyObjectId`). Permisos nuevos `view_caja_chica` (True para superadmin/admin/optica, False para usuario/medico) y `delete_caja_chica` (True solo superadmin) agregados **en los DOS diccionarios `PERMISSIONS` duplicados** (`config/permissions.py`, usado por `require_permission` de las rutas; y `server.py` línea ~318, usado por el login real/`resolve_permissions` con rate-limiting — descubierto durante esta implementación que son dos copias independientes, deuda técnica preexistente ya documentada en PRD.md, mantenida sincronizada pero no refactorizada).
- **Setup**: se sembraron en preview los 4 médicos de la feature anterior sin relación; para esta feature no se necesitó seed de datos, solo el reset de la contraseña de la cuenta `admin` de preview (no estaba documentada) a `Admin2024$` para poder probar el rol admin — actualizado en `test_credentials.md`.
- **Frontend**: `pages/CajaChica.js` nuevo (tarjetas de saldo prominente verde/rojo/teal, tabla de historial con badges Ingreso/Egreso, diálogo crear/editar, `AlertDialog` de eliminación solo si `hasPermission('delete_caja_chica')`, diálogo de informe mensual con selector `type=month` + descarga Excel vía blob). `services/api.js`: `cajaChicaApi`. `App.js`: ruta `/caja-chica` con `requiredPermission="view_caja_chica"`. `components/Layout.js`: ítem `nav-caja-chica` agregado como **primer elemento** de `navItems` (antes de Dashboard), condicionado a `hasPermission('view_caja_chica') && isMenuEnabled('caja_chica_optica')`. `routes/menu_config.py`: nuevo id de menú `caja_chica_optica` (categoría `principal`) agregado a `AVAILABLE_MENUS` y a `DEFAULT_MENU_CONFIG` de `admin` y `optica` (no `usuario`).
- **Bug crítico encontrado y corregido durante implementación (antes de testing agent)**: justo después de implementar, el ítem "Caja Chica" no aparecía para el rol `optica` pese a que los endpoints backend ya lo permitían correctamente. Causa raíz: el login real (`server.py` línea ~2630, con rate-limiting/lockout) usa su propio `PERMISSIONS`/`resolve_permissions` LOCAL, no el de `config/permissions.py` — por eso había que editar ambos diccionarios, no solo uno.
- Probado en 1 ronda con testing agent (iteration_141.json) = **PASS 100% backend y frontend** (suite nueva `backend/tests/test_caja_chica_optica.py`, 9/9). Cubrió los 4 roles, saldo continuo entre meses, validación de egreso sin campos obligatorios, permisos de edición (dueño o superadmin) y eliminación (solo superadmin), informe mensual + Excel. 2 hallazgos MENOR corregidos post-testing y re-verificados: (1) `mes` sin formato válido ahora responde 422 en vez de interpretarse como "todo el histórico"; (2) fechas imposibles como `2026-02-31` ahora responden 422 (antes solo se validaba el patrón regex, no que la fecha existiera en el calendario).
- **Nota para despliegue a producción**: si en producción el superadmin ya había personalizado los menús visibles por rol (tabla `menu_config`, vacía en preview), el nuevo ítem "Caja Chica" podría no aparecer automáticamente para `optica`/`admin` hasta que el superadmin lo habilite manualmente desde la pantalla de configuración de menús (Usuarios → Configurar Menús) — no requiere intervención técnica, es autoservicio.
- Fase 2 (comprobantes/foto de recibo, categorías de egreso) y Fase 3 (alerta de saldo mínimo, aprobación previa de egresos grandes, múltiples cajas chicas) quedan pendientes, fuera de alcance de este pase.

## Feature: Submenú "Ventas del Día" para rol usuario (2026-11) — COMPLETADO
- Solicitud: el rol `usuario` necesitaba ver las ventas del día (origen clínica) con el mismo detalle de venta que ve admin/superadmin, pero SOLO LECTURA (sin crear ventas, sin abrir/cerrar caja, sin anular).
- **Backend**: CERO cambios — los endpoints `GET /api/ventas/hoy`, `/resumen-dia`, `/{id}` ya existían y solo requieren estar logueado (en realidad, según testing agent, dependen de la misma validación que usa el permiso `manage_sales`, el cual el rol `usuario` ya tenía desde antes — no se le otorgó nada nuevo).
- **Frontend**: nueva página `pages/VentasDelDia.js` (resumen del día + lista + diálogo de detalle con items/subtotal/descuento/total/forma de pago, sin ningún botón de creación/anulación). Ruta `/ventas-del-dia` en `App.js` con `requiredMenu="ventas_del_dia"` (sin `requiredPermission`, ya que el backend no exige un permiso dedicado). Nuevo ítem de menú `ventas_del_dia` (categoría `inventario`) en `menu_config.py`, agregado a `DEFAULT_MENU_CONFIG['usuario']` únicamente (no admin/optica/superadmin, que ya tienen esta vista integrada en Punto de Venta). En `Layout.js`, el ítem solo se agrega al sidebar si `user?.role === 'usuario'`.
- **Hallazgo importante durante implementación**: el rol `usuario` tenía una configuración de menús PERSONALIZADA guardada en `db.menu_configurations` (colección distinta de `DEFAULT_MENU_CONFIG` en código — mismo problema de "doble fuente" ya documentado para Caja Chica, pero esta vez vía `db.menu_configurations` en lugar de los diccionarios `PERMISSIONS`). Se corrigió vía `PUT /api/menu-config/role/usuario` agregando `ventas_del_dia` a la lista personalizada existente.
- Probado en 1 ronda con testing agent (iteration_142.json) = **PASS 100% backend y frontend** (suite nueva `backend/tests/test_ventas_del_dia_usuario.py`). Se corrigió 1 hallazgo menor post-testing: la fecha en el diálogo de detalle usaba el día UTC en vez del día de Guatemala (podía mostrar el día siguiente en ventas tardías); ahora usa `formatDate` con zona horaria correcta.
- Notas para el usuario (no accionadas, marcadas "opcional" por el testing agent): (1) el rol `usuario` conserva el permiso técnico `manage_sales`/`manage_caja` desde antes de este cambio, por lo que en teoría podría crear ventas vía API directa aunque la UI nueva es de solo lectura (no tiene menú para acceder a Punto de Venta); (2) las ventas anuladas aparecen en la lista pero no se cuentan en el resumen — comportamiento heredado de Punto de Venta, no introducido por esta función.

## Feature: Desglose de Producción por Médico que Refiere (2026-11) — COMPLETADO (Fase 1 MVP)
- Plan aprobado: en "Análisis de Producción" (`/analisis-produccion`, acceso exclusivo superadmin hoy — el usuario la llama coloquialmente "Dashboard Financiero" pero es esta página; el plan pide explícitamente mantener el acceso igual a como está hoy, sin ampliarlo), la lista "Ventas por médico que refiere" ahora tiene nombres clicables. Al hacer clic se abre un modal con desglose línea por línea (una fila por producto/servicio vendido), selector de fechas propio precargado con el rango actual de la página (cambiable sin afectar el período general), resumen de totales, y exportación a Excel. "Ventas por cajero" y el resto de la página NO cambian.
- **Backend** (`routes/ventas.py`): 2 endpoints nuevos reutilizando exactamente el mismo criterio de agrupación que ya usa `/analisis` (`medico_id`, con `"sin"` como sentinel para ventas sin médico asignado — incluye `None`, `""` y campo ausente): `GET /ventas/analisis/medico-detalle` (JSON: resumen + filas) y `GET /ventas/analisis/medico-detalle/excel` (descarga, mismo estilo visual que el export de IGSS ya existente, nombre de archivo con fallback ASCII + `filename*=UTF-8''` para nombres con acentos). Ambos protegidos con el mismo `require_superadmin_dep()` que ya usa `/analisis` — no se amplía el acceso. El "monto total" del resumen es la suma de `venta.total` (coincide exactamente con el monto ya mostrado en la lista principal); las filas individuales muestran `item.subtotal` (antes de cualquier descuento a nivel de venta).
- **Frontend** (`pages/AnalisisProduccion.js`): `RankTable` ahora acepta un prop opcional `onRowClick`, usado SOLO en la lista "por_medico" (nombre se vuelve un botón con subrayado punteado al pasar el mouse). Nuevo componente `DetalleMedicoModal` al final del archivo: fechas Desde/Hasta + botón Aplicar, tarjetas de resumen, tabla de detalle, botón "Exportar a Excel" vía blob. El rango inicial del modal usa `data?.desde`/`data?.hasta` (el rango YA RESUELTO que la página está mostrando en ese momento, sin importar si el usuario tenía seleccionado "hoy", "mes" o un rango personalizado).
- Probado en 1 ronda con testing agent (iteration_143.json) = **PASS 100%** backend y frontend (suite nueva `backend/tests/test_analisis_medico_detalle.py`, 20/20). Se corrigieron 4 hallazgos menores post-testing: (1) el modal usaba el rango de fechas "en construcción" de la página en vez del ya resuelto (podía desincronizarse un instante); (2) el filtro "sin médico" no incluía `medico_id=""` como variante legacy; (3) exportar Excel tras cambiar de fechas en el modal usaba el input en vivo en vez del rango ya aplicado/confirmado; (4) nombre de archivo Excel con acentos (ej. "Méndez") rompía el header HTTP — ahora usa fallback ASCII + UTF-8 codificado. 1 hallazgo cosmético (botón "Exportar a Excel" se ve con poca saturación) se dejó sin cambios por usar una clase CSS compartida (`btn-primary`) en todo el sistema, fuera de alcance de este pase.
- Fase 2 (abrir la venta completa desde una fila del desglose) y Fase 3 (extender clic+desglose+exportar a "Ventas por cajero" y otras listas) quedan pendientes, fuera de alcance de este pase.

## Feature: Cierre de Producción Diario — Dra. Mariamercedes Palma (2026-11) — COMPLETADO (Fase 1 MVP)
- Plan aprobado: cada día a las 5:00 PM hora Guatemala, el sistema envía automáticamente un PDF a un correo configurado con el detalle de la producción personal del día de la Dra. Palma como médico que refiere, combinando clínica general + Óptica (cualquier categoría), funcionando igual que el informe diario de anestesia ya existente (mismo estilo de PDF, mismo patrón de cron webhook + correo con enlace de descarga firmado). Si no hubo producción ese día, igual se envía el cierre en cero (envío predecible todos los días). Solo lectura, no agrega pantalla nueva.
- **Hallazgo clave durante el análisis**: el POS de clínica y el POS de Óptica usan el MISMO catálogo compartido de médicos (`db.doctors`, vía `/api/doctors/search`) — es decir `medico_id` en `db.ventas` y `doctor_id` en `db.optica_sales` son el mismo id. Esto permitió matchear por `doctor_id` exacto además de por nombre (regex tolerante a prefijo "Dra."/mayúsculas, por si algún registro legacy solo tiene el nombre en texto libre), más confiable que la suposición original del plan de "catálogos separados".
- **Backend** (`routes/ventas.py`): `PRODUCCION_MEDICO_PALMA_NOMBRE` (constante, fijo en código esta fase — no hay pantalla de configuración), `_resolver_doctor_por_nombre` (busca en `db.doctors` por nombre normalizado), `_obtener_produccion_medico_dia` (agrega ventas de `db.ventas` origen=clinica/estado=completada + `db.optica_sales` status≠cancelado del día, un renglón por item vendido — `items_v2` para ventas V2 del POS de Óptica, o fallback a armazón/lente de contacto/lentes legacy), `render_produccion_medico_pdf` (PDF con reportlab, mismo estilo del informe de anestesia), token firmado HMAC-SHA256 (`_make_prod_medico_report_token`/`_verify_prod_medico_report_token`, 21 días de expiración) y endpoint público `GET /ventas/produccion-medico/daily-report/pdf?token=` (sin login, para el enlace del correo).
- **Backend** (`routes/email_service.py`): `_destinatarios_produccion_medico` (lee `INFORME_PRODUCCION_PALMA_EMAILS`), `build_produccion_medico_daily_html`, `enviar_informe_produccion_medico_diario`, `POST /ventas/produccion-medico/daily-report/enviar` (envío manual, admin/superadmin), `POST /cron/produccion-medico-diario` (webhook, mismo `WEBHOOK_CRON_SECRET` que los demás crons).
- **Cron** (`.emergent/crons.yml`): nueva entrada `produccion-palma`, `0 17 * * *` America/Guatemala → `/api/cron/produccion-medico-diario`.
- **Secreto nuevo**: `INFORME_PRODUCCION_PALMA_EMAILS` (correo destino, configurado por el usuario vía el formulario seguro de claves — mismo patrón que `INFORME_ANESTESIA_EMAILS`).
- Verificado manualmente por el agente principal antes de testing: cron disparado con el secreto real → email enviado (1 ok, 0 errores), PDF descargado y válido.
- Probado en 1 ronda con testing agent (iteration_144.json) = **PASS 100% backend** (suite nueva `backend/tests/test_produccion_medico_palma.py` 6/6 + suite independiente del testing agent `test_produccion_palma_independent.py` 16/16, incluyendo agregación combinada clínica+óptica con datos insertados en Mongo, exclusión de ventas de Óptica canceladas, día sin producción, seguridad de los 3 endpoints nuevos, y regresión de `/ventas/analisis` + cron de anestesia sin romperse). 1 hallazgo CRÍTICO de código (líneas muertas copiadas por error del informe de anestesia al final de `_run_cron_produccion_medico`, que hubieran lanzado una excepción no controlada si el envío fallaba) corregido y re-verificado. 2 hallazgos MENOR corregidos: columna "N° Venta" del PDF se ensanchó para no cortar números de venta reales; (retry/backoff ante 429 del proveedor de correo cuando dos crons coinciden en el mismo minuto, quedó pendiente como mejora opcional, no bloqueante — los horarios de Palma (17:00) y anestesia/cierre (18:00) no coinciden).
- Fase 2 (pantalla de administración para cambiar correo/horario, historial de reportes enviados con reenvío puntual) y Fase 3 (extender a otros médicos eligiéndolos de una lista) quedan pendientes, fuera de alcance de este pase.

## Fix: Incidente de producción — crons no registrados + limpieza de memoria/imagen (2026-11-14/15)
- **Incidente en producción (resuelto operativamente, root cause es de plataforma)**: los crons `informe-anestesia-diario` y `produccion-palma` no se disparaban en producción (solo el cron antiguo `cierre-diario` se ejecutaba) a pesar de que `.emergent/crons.yml` los tenía correctos y habilitados, y de un redeploy. RCA del agente de despliegue: el registro/scheduler de crons de producción nunca se reconcilió con el archivo actual de 4 entradas (`applied.hash` desincronizado); el pipeline de deploy no tiene un paso de reconciliación de crons, y el watcher automático del pod es solo de preview. Escalado a soporte de Emergent (plataforma) para forzar la reconciliación de crons en producción del job. Mientras tanto, se reenviaron manualmente ambos reportes perdidos disparando el webhook con el secreto real: informe de anestesia (confirmado enviado) y cierre de producción de la Dra. Palma del 14-nov (confirmado: 1 enviado, 0 errores, total Q17,075.00).
- **Memoria "crítica" (86%) en el panel de producción**: diagnosticado como un baseline fijo del plan tier_0 (límite de 512Mi por réplica), NO una fuga de memoria (sin reinicios/OOM en 22h de monitoreo). Se descartó código con acumuladores sin límite (el set `blacklisted_tokens` en memoria es código muerto, el blacklist real usa Mongo con TTL).
- **Limpieza aplicada** (bajo riesgo, verificada sin romper nada — PDF de evaluación oftalmológica probado end-to-end tras el cambio): se removieron 9 librerías pesadas instaladas pero nunca importadas en el código (`numpy`, `pandas`, `openai`, `litellm`, `google-genai`, `google-generativeai`, `huggingface_hub`, `tiktoken`, `tokenizers`) de `backend/requirements.txt` para reducir tamaño de imagen y tiempo de build/deploy; se movió el import de `reportlab` en `routes/evaluaciones.py` de nivel de módulo a diferido dentro de la función que lo usa (mismo patrón ya usado en otras rutas).
- Pendiente: respuesta de soporte/plataforma sobre la reconciliación forzada de crons en producción; resultado de la prueba de 24-48h de reinicio+observación de memoria si el usuario decide hacerla.

## Fix: Filtro en cascada mes → cirujano en Sala de Operaciones (2026-11-15)
- Reporte del usuario: al filtrar por mes y luego por cirujano, a veces no aparecían pacientes, y la combinación se sentía "rota". Reproducido en preview: el dropdown de cirujano (`GET /api/surgeries/options`) siempre devolvía la lista GLOBAL de cirujanos sin importar el mes seleccionado, permitiendo elegir una combinación mes+cirujano sin ninguna cirugía real (0 resultados confusos, indistinguibles de un error).
- **Fix backend** (`routes/surgeries.py`): `GET /surgeries/options` acepta ahora un parámetro opcional `month` (YYYY-MM); cuando se indica, `surgeons`/`institutions`/`anesthesiologists` se filtran solo a quienes tienen cirugías registradas ese mes (la lista de `months` se mantiene global).
- **Fix frontend** (`SalaOperaciones.js`, `services/api.js`): `fetchOptions()` ahora pasa el mes seleccionado; si el cirujano ya elegido deja de ser válido al cambiar de mes, se resetea automáticamente a "Todos los cirujanos" en vez de dejar una combinación con 0 resultados. Se reordenaron los selectores (Mes → Cirujano → Institución) para reforzar visualmente el flujo mes-primero pedido.
- Verificado en vivo con `screenshot_tool` (3 escenarios: mes con un solo cirujano válido → dropdown escopeado correctamente; cirujano elegido antes del mes que deja de ser válido → auto-reset a "Todos" y resultados correctos; "Limpiar filtros" → vuelve a mostrar todo) + nuevo test pytest `test_05b_get_surgery_options_scoped_by_month` en `backend/tests/test_surgeries.py` (pasando).
- **Investigación de la segunda parte del reporte** ("congruencia con el reporte de procedimientos de anestesia: si se edita en Sala de Operaciones, debe reflejarse en Procedimientos"): se verificó con una prueba end-to-end real (crear cirugía con anestesiólogo → aparece inmediatamente en el cierre mensual de anestesia; editar cirujano/procedimiento/anestesiólogo → el cierre se actualiza de inmediato) y el mecanismo de sincronización (`upsert_anesthesia_from_surgery`, llamado en create/update/import/cancel) funciona correctamente para meses NO cerrados. Única excepción EXISTENTE (no introducida ahora): si el mes de anestesia ya está "cerrado" (pagado), las ediciones de la cirugía NO se reflejan en el registro de anestesia (protección intencional de meses ya pagados), pero esto ocurre SIN ningún aviso al usuario — pendiente de confirmar con el usuario si esto explica lo que vio, o si tiene un paciente/fecha específico donde la sincronización realmente falló en un mes abierto.

## Fix CRÍTICO: honorario en Q0.00 para tipos de anestesia con caracteres especiales (2026-11-16)
- **Reporte real en producción**: la cirugía de "Mario Reyes Gomez" (tipo de anestesia "Sedación Faco + Vitrecto") se editó en Sala de Operaciones, pero en "Procedimientos de Anestesia" el honorario seguía en Q0.00 en vez del valor real del catálogo (Q1,200.00), aunque otros registros con un tipo de anestesia similar SIN "+" en el nombre sí mostraban el valor correcto.
- **Causa raíz confirmada**: en `routes/quirofano.py::_resolve_type_value`, la búsqueda del tipo de anestesia en el catálogo usaba una regex `^{label}$` sin escapar el nombre. Cualquier nombre de tipo con un carácter especial de regex (el más común: "+", también "." "(" ")" "*" "?") nunca coincidía con el catálogo — el "+" se interpretaba como cuantificador regex, no como texto literal — y la función caía al fallback `value=0`, silenciosamente, sin ningún error visible.
- **Fix**: se envuelve el nombre con `re.escape()` antes de construir la regex. Reproducido y verificado en preview (creando un tipo "Sedación Faco + Vitrecto" con Q1,200 y una cirugía con ese tipo): antes del fix el cierre mostraba Q0.00, después del fix muestra Q1,200.00 correctamente, tanto al crear como al re-editar la cirugía.
- **Importante para producción**: esto afecta a CUALQUIER tipo de anestesia cuyo nombre tenga un carácter especial de regex, no solo a Mario Reyes Gomez — hay que revisar el catálogo de tipos de anestesia en producción para identificar todos los registros afectados. Una vez desplegado el fix, los registros YA EXISTENTES con Q0.00 se autocorrigen en cuanto se vuelva a guardar esa cirugía en Sala de Operaciones (no requiere tocar la base de datos directamente) — salvo que el registro ya haya sido editado manualmente antes en Procedimientos de Anestesia (lo cual "bloquea" el valor contra la auto-sincronización, `value_locked=True`); en ese caso habría que corregir el monto manualmente ahí.
- Nueva prueba de regresión: `backend/tests/test_anesthesia_type_value_regex_fix.py` (2/2 passing), cubre el caso con "+"/paréntesis y confirma que los tipos normales siguen funcionando igual.
- Pendiente: desplegar a producción y confirmar/corregir el registro específico de Mario Reyes Gomez (y cualquier otro tipo con caracteres especiales en el catálogo real de producción).

## Auditoría completa del rol "administrador_igss" (2026-11-16)
- Pedido del usuario: correr un agente que probara todas las funciones, permisos y asignaciones del rol `administrador_igss`, y confirmar que cada menú habilitado lleva a donde debe.
- **Hallazgo principal**: el menú del rol (`db.menu_configurations`) tenía habilitados `sala_operaciones`, `agenda`, `quirofano_insumos`, `quirofano_anestesia` y `optica_accesorios`, pero el rol NUNCA tuvo los permisos de backend correspondientes (`view_sala_operaciones`, `view_agenda`, etc. — sus únicos permisos reales son pacientes, `manage_igss_units` y `view_evaluacion`). Resultado: Agenda redirigía silenciosamente a Pacientes sin aviso, y Cirugías/Insumos/Anestesia cargaban sin control de acceso real.
- **Fix de alcance del rol**: se corrigió `db.menu_configurations` (rol `administrador_igss`) vía `PUT /api/menu-config/role/administrador_igss` dejando solo `pacientes, unidades_igss, evaluacion_oftalmologica` (matching exacto con sus permisos reales). El sidebar ahora muestra solo Pacientes, Evaluación Oftalmológica e IGSS (Unidades + NOG). **Pendiente: replicar este mismo cambio en producción** (usuario `sandrac`) vía Configuración > Roles y Permisos > Menús, ya que el cambio en preview NO se propaga solo.
- **Fugas de seguridad descubiertas y corregidas (afectaban a CUALQUIER usuario autenticado, no solo a este rol)**:
  - `routes/cuentas_cobrar.py`: TODOS los endpoints (lectura y escritura: listar/crear/anular cuentas, registrar abonos, gestionar responsables) solo pedían estar logueado, sin ningún permiso. Cualquier rol podía leer y modificar Cuentas por Cobrar de Clínica y Óptica. Fix: nuevos permisos `view_cuentas_cobrar`/`manage_cuentas_cobrar` (otorgados a superadmin/admin/usuario/óptica con los niveles apropiados; óptica también los tiene porque su pantalla de Finanzas ya mostraba el link de CxC de clínica por diseño).
  - `routes/surgeries.py`: `GET /surgeries` y `/surgeries/options` no exigían ningún permiso (exponían el listado completo de cirugías de todas las instituciones). Fix: ahora exigen `view_sala_operaciones` (igual que `/surgeries/template`, que ya lo exigía).
  - `routes/surgery_crm.py`: el listado/detalle/estadísticas de candidatos a cirugía tampoco exigían permiso. Fix: ahora exigen `view_patients` (igual que los endpoints de escritura del mismo módulo, que ya lo exigían).
  - `routes/patients.py`: endpoints de importación (`/import/validate`, `/import/batch`, `/import/template`, `/import/stats`) exigían el rol admin/superadmin en vez del permiso `import_patients` ya definido (esto hacía que el permiso fuera inútil para cualquier rol personalizado al que se le otorgara). Fix: ahora usan `require_permission("import_patients")`.
  - `routes/patients.py`: exportar pacientes a Excel/PDF fallaba con error 500 (`KeyError: 'record_number'`) para CUALQUIER rol cuando algún paciente legado no tenía ese campo. Fix: acceso seguro con `.get()`.
  - `App.js`: las rutas `/cuentas-cobrar-finanzas` y `/crm-cirugias` no tenían ningún `requiredPermission`/`requiredMenu` (quien fuera podía abrirlas por URL). Fix: ahora exigen `view_cuentas_cobrar` y `view_patients` respectivamente.
- **Regresión detectada y corregida en la misma sesión**: `server.py` mantiene una copia DUPLICADA de la matriz de permisos (usada solo por `/auth/login`), separada de `config/permissions.py` (usada por los guards del backend) — deuda técnica ya documentada en ROADMAP. Al agregar los nuevos permisos solo en `config/permissions.py`, el login dejó de incluirlos, causando que `/cuentas-cobrar-finanzas` redirigiera para TODOS los roles (incluido superadmin). Fix: se sincronizaron manualmente las claves nuevas en ambos archivos. Se decidió NO consolidar ambas matrices en este pase porque se descubrió una discrepancia preexistente no relacionada (`manage_sales`/`manage_caja` de óptica difieren entre los dos archivos) que habría sido arriesgado tocar sin una prueba específica.
- **Fix adicional de UX**: los botones "Excel"/"PDF"/"Plantilla" de Pacientes usaban `window.open()` sin token de autenticación (fallaban con 403 "Not authenticated" en una pestaña nueva, para CUALQUIER rol). Fix: ahora descargan vía axios con `responseType: 'blob'` + enlace temporal, igual que el patrón ya usado en Sala de Operaciones.
- **Fix de UI**: botones "Agregar/Editar/Activar-Desactivar" en Insumos y Equipos Qx y el botón "Plantilla Excel" en Sala de Operaciones ahora se ocultan si el usuario no tiene el permiso de backend correspondiente (antes eran visibles para cualquiera y fallaban con 403 al hacer clic). Botón "Registrar Abono" en el detalle de Cuentas por Cobrar ahora se oculta si el usuario no tiene `manage_cuentas_cobrar`.
- Verificado con 3 rondas de `testing_agent` (iteration_145, 146, 147): auditoría inicial (32 checks backend + recorrido UI completo), regresión tras el primer fix (detectó las 2 regresiones arriba), y verificación final enfocada — **100% passing** en las 3 rondas de backend (69/69 y 16/16 en las últimas dos) y sin regresiones para superadmin/admin/usuario/óptica/anestesia/médico.
- `test_credentials.md` actualizado: landing real de `igss.admin` es `/pacientes` (no `/sala-operaciones` como decía antes), y se documentó el menú corregido.

## Fix: "Ver paciente" desde Agenda dejaba de abrir el expediente tras 2-3 usos (2026-11-16)
- Reporte en PRODUCCIÓN: al hacer clic en "Ver paciente" desde el menú de una cita en Agenda, el detalle del paciente se abría las primeras 2-3 veces y luego el sistema solo quedaba en la pantalla de lista de Pacientes, sin aviso ni error visible.
- **RCA vía `send_to_deployer` (debug)**: backend e infraestructura sanos (0 errores 500/429 en `GET /api/patients/{id}` en las últimas 12h, sin OOM ni reinicios, el job ya estaba en tier_1 1Gi/2Gi). El bug es 100% de frontend.
- **Causa raíz**: en `Pacientes.js`, el `useEffect` que lee el query param `?id=` (usado por `handleVerPaciente` de Agenda vía `navigate('/pacientes?id=...')`) tenía dependencias vacías `[]`, por lo que solo reaccionaba al primer montaje del componente. Además, el `.catch()` de esa llamada estaba vacío, ocultando cualquier fallo sin avisar al usuario.
- **Fix**: el efecto ahora depende de `location.search` (vía `useLocation`), reaccionando a cada navegación repetida desde Agenda; se agregó manejo real de errores (toast + distinción de 404); al cerrar el diálogo de detalle se limpia el `?id=` de la URL para evitar reaperturas fantasma.
- Verificado con Playwright simulando 4 navegaciones SPA consecutivas Agenda → Ver paciente (sin recarga completa de página, replicando exactamente el bug reportado): el diálogo de expediente se abrió correctamente las 4 veces (antes del fix solo abría la primera).

## Ajuste: rol "usuario" ahora puede registrar abonos en Cuentas por Cobrar (2026-11-16)
- El usuario reportó en producción que el rol "usuario" no podía registrar abonos en Cuentas por Cobrar, y pidió confirmar que cualquier rol con acceso de vista a CxC también pueda abonar.
- Causa: en el fix de seguridad de CxC de esta misma sesión, se dejó a "usuario" como solo lectura (`manage_cuentas_cobrar: False`), replicando por error el patrón de "view_expenses=True pero create_expenses=False" — pero en la operación real, el personal con rol "usuario" SÍ necesita poder cobrar/abonar cuentas.
- Fix: `manage_cuentas_cobrar: True` para el rol "usuario" en `config/permissions.py` y `server.py`. Verificado end-to-end (crear responsable → crear cuenta → registrar abono → 200 OK) y sin regresión para superadmin/admin/óptica/administrador_igss.
