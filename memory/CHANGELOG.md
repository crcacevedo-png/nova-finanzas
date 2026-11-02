# CHANGELOG — NovaVisión ERP

## 2026-10-29 — Precio variable por renglón en POS de Clínica — Fase 1 MVP
**Plan aprobado:** permitir cambiar el precio de un artículo al vender (solo POS clínica), con mínimo = costo (precio_compra), sin tope superior, sin autorización. Se marca internamente el renglón como precio variable y se guarda el precio de lista original; el comprobante NO muestra la marca. Óptica sin cambios.
**Backend (`routes/ventas.py`):**
- `VentaItem` + `precio_variable: bool`, `precio_lista: Optional[float]`.
- En el loop de venta: si `precio_variable` valida `precio_unitario >= precio_compra` (400 si es menor y costo>0); si NO es variable, fuerza `precio_unitario = precio_venta` (lista) — evita bypass. Guarda `precio_variable` y `precio_lista` en el item.
- `ProductoPOSResponse` + `precio_compra` (poblado en `/productos` y `/productos-rapidos`) para que la UI valide el costo.
**Frontend (`PuntoVenta.js`):**
- Ícono Tag por renglón (`pv-precio-variable-toggle-<id>`) que activa input editable (`pv-precio-variable-input-<id>`); borde rojo + 'menor al costo' si < costo; recálculo inmediato del total.
- Toggle OFF restaura el precio de lista. Pre-chequeos antes de cobrar: precio>0 y precio>=costo. Payload envía `precio_variable` y `precio_lista`.
**Testing:** it.108 (6/7) → correcciones → it.109 (retest, ambos HIGH corregidos, 95%, sin retest pendiente). DB confirma item con precio_variable=true, precio_lista=100, precio_unitario=150; renglón no variable guarda precio de lista. Comprobante sin marca de precio variable. Óptica sin cambios.
**Futuro:** Fase 2 reporte de ventas con precio variable (lista/aplicado/diferencia/usuario) + margen sobre costo; Fase 3 políticas por rol/categoría.



## 2026-10-29 — IVA incluido en el precio (todo el sistema) — Fase 1 MVP
**Plan aprobado:** el precio del producto ya incluye el IVA; el sistema deja de sumar 12% por encima. Total = suma de precios − descuento. El IVA se calcula "hacia adentro" (total − total/1.12) después del descuento, solo para contabilidad, y permanece oculto en pantalla/tickets. Aplica a POS Clínica y Óptica. Ventas históricas NO se recalculan.
**Backend:**
- `routes/ventas.py` — `total = subtotal − descuento_monto` (sin sumar IVA); `iva_total = total − total/1.12`. Se eliminó la lógica `afecto_iva`/factor del cálculo.
- `routes/optica.py` — `create_optica_sale_v2`: guarda `iva = total − total/1.12` en el documento de venta (antes óptica no guardaba IVA).
**Frontend:**
- `PuntoVenta.js` — `calcularTotales`: `total = subtotal − descGlobal`; `iva = total − total/1.12` (oculto). La resta ahora cuadra en pantalla.
- `Productos.js` — se eliminó `afecto_iva` del formulario de ingreso/edición y de la plantilla/ayuda de importación CSV.
**Testing (iteración 107, frontend 100%):** Clínica: 1 ítem 300 → Total 300 (sin +12%); con 10% → Total 270 exacto; venta creada con `iva=28.93` (=270−270/1.12) en DB; sin línea de IVA en resumen/pago/ticket/detalle. Óptica: 150 → Total 150; con 10%+autorizador → 135. Formulario de productos sin casilla "Afecto a IVA".
**Nota:** hallazgo ajeno a este cambio — stock a nivel de lote de "Fenilefrina 2.5% gotas" no coincide con el stock de la tarjeta (dato preexistente de dispensario), no relacionado con IVA.
**Pendiente (futuro):** Fase 2 reporte de IVA por período + exportación contable; Fase 3 facturación electrónica (FEL) con esquema IVA incluido.



## 2026-10-29 — POS: descuento por % con autorizador + IVA oculto en clínica
**Solicitud:** (1) Descuento por un solo % sobre el total en POS Óptica y Clínica, con nombre de quien autoriza (obligatorio si descuento>0). (2) Ocultar IVA del POS de clínica (decisión del usuario: solo ocultar en pantalla/tickets pero seguir calculándolo y guardándolo).
**Backend:**
- `routes/optica.py` — `OpticaSaleCreateV2` + `discount_percent`, `discount_authorized_by`; `create_optica_sale_v2` calcula `total = subtotal - subtotal*%/100`, valida autorizador (400 si falta) y guarda `discount_percent/amount/authorized_by`; respuesta incluye estos campos.
- `routes/ventas.py` — `VentaCreate` + `descuento_porcentaje`, `descuento_autoriza`; descuento global % aplicado al subtotal, IVA 12% recalculado sobre base afecta con factor (1-%/100), valida autorizador; guarda `descuento_total/porcentaje/monto/autoriza`, `iva`, `total`. `VentaResponse` expone los nuevos campos.
**Frontend:**
- Óptica (`OpticaPOS.js` + `POSCart.js`): campos `pos-optica-descuento-pct` y `pos-optica-descuento-autoriza`, línea de descuento, reset tras venta, se agregó `<Toaster/>`.
- Clínica (`PuntoVenta.js`): campos `pv-descuento-pct` y `pv-descuento-autoriza`; línea de IVA ELIMINADA de resumen, ticket y detalle; reset en `limpiarCarrito`.
**Testing:** iteración 105 (hallazgos) + 106 (retest 100% frontend). Backend óptica validado por curl (400 sin autorizador; 150→135 con 10%).
**PENDIENTE DE CONFIRMAR CON USUARIO:** por la decisión de "seguir sumando/guardando el IVA pero ocultarlo", el Total visible = (Subtotal − Descuento) + IVA oculto, por lo que la resta visible NO cuadra (ej. Subtotal 300 − Desc 30 → Total 302.40). Si los precios YA incluyen IVA, lo correcto sería que el total = suma de precios finales (IVA incluido, no sumado aparte).



## 2026-10-28 — Dashboard: accesos rápidos de fecha (Hoy / Esta semana / Este mes)
**Solicitud:** Agregar botones "Hoy", "Esta semana" y "Este mes" junto al filtro de fecha.
**Frontend:** `Dashboard.js` — 3 botones (testids `resumen-rapido-hoy/semana/mes`) que ajustan modo (Día/Rango), fechas y recargan el resumen de inmediato. "Hoy" = día actual; "Esta semana" = lunes→hoy; "Este mes" = día 1→hoy. Base de cálculo = `hoyGt` (día actual en hora Guatemala, tomado de la primera respuesta del backend). Refactor: `fetchResumenConParams` compartido por Aplicar y los accesos rápidos.
**Verificado:** screenshots — "Esta semana" (26–28/10) y "Este mes" (01–28/10: 6 ventas Q2,230, 28 citas) actualizan etiqueta, inputs y tarjetas; sin overflow en escritorio ni móvil.



## 2026-10-28 — Dashboard: filtro de fecha/rango + tarjeta Producción IGSS
**Solicitud:** (1) Elegir un día o rango para ver el resumen de cualquier fecha. (2) Tarjeta con la facturación IGSS del día desde el módulo de producción.
**Backend:** `GET /api/dashboard/resumen-dia` ahora acepta `fecha` (un día) o `desde`/`hasta` (rango); sin params usa hoy (GT). Óptica y acreditaciones filtran por rango UTC del/los día(s) GT; citas y evaluaciones por string de fecha. Nuevo bloque `produccion_igss` reutilizando `_build_produccion_rows`/`_produccion_totales` de `routes/igss_nogs.py`: servicios, total (costo), facturado, pagado, pendiente. Respuesta incluye `fecha`, `desde`, `hasta`.
**Frontend:** `Dashboard.js` — toggle Día/Rango con inputs de fecha y botón Aplicar (testids `resumen-mode-dia/rango`, `resumen-fecha/desde/hasta-input`, `resumen-aplicar-btn`); título cambia a "Resumen del período" en rango; 5ª tarjeta "Producción IGSS" (icono FileText). Helper `fmtFecha` evita desfase de día al mostrar fechas. `dashboardApi.getResumenDia(params)`.
**Verificado:** curl día/rango con datos reales (rango 21–23 oct: evals 37, citas 3, acreditaciones 112/Q132,550, producción 1 servicio/Q100); screenshots escritorio (5 tarjetas en fila) y móvil sin overflow.



## 2026-10-28 — Dashboard: sección "Resumen del día"
**Solicitud:** Agregar al dashboard (superadmin) las ventas del día, citas y evaluaciones del día, e incluir servicios al IGSS y su total.
**Backend:** nuevo `GET /api/dashboard/resumen-dia` (require_permission view_dashboard) en server.py. Devuelve, en hora Guatemala:
- `ventas` (óptica de hoy): cantidad, total vendido, total cobrado (optica_sales por rango UTC del día GT).
- `citas` de hoy (colección `citas`, campo `fecha` YYYY-MM-DD): total, atendidas (Atendida/En consulta/Presente), canceladas (Cancelada/No asistió).
- `evaluaciones` de hoy (`evaluaciones_oftalmologicas.fecha`): total.
- `igss`: servicios del día = acreditaciones NOG no anuladas (`igss_nog_acreditaciones.fecha_acreditacion`) + `total` monetario = suma del `precio` del NOG asociado (`igss_nogs.precio`).
**Frontend:** `Dashboard.js` nueva sección "Resumen del día" (data-testid `resumen-dia-section`) con 4 StatCards (Ventas del Día, Citas del Día, Evaluaciones del Día, Servicios IGSS con total). `dashboardApi.getResumenDia`.
**Verificado:** curl 200 con datos reales; lógica de total IGSS validada (112/112 acreditaciones con precio); screenshot desktop+móvil sin overflow.
**Supuestos (confirmables):** "ventas del día" = ventas de óptica; "servicios al IGSS" = acreditaciones NOG del día y su valor por precio de NOG (no la producción/facturación IGSS de `igss_produccion`).



## 2026-10-28 — Caja y Punto de Venta Individuales por Usuario (Fase 1 MVP)
**Solicitud:** Cada usuario opera exclusivamente su propia caja clínica diaria y cada venta de óptica queda atribuida al vendedor. Supervisores (Admin/SuperAdmin) ven consolidado y pueden cerrar/reabrir cajas ajenas. Conservar históricos del modelo compartido.

**Backend `routes/caja.py` (todo verificado por curl E2E):**
- `calcular_totales_caja_dia(fecha, cajero_id=None)` scoped por usuario.
- `/estado`, `/movimientos` (GET), `/cierres` (historial): scoped a `current_user` (cierre por `abierto_por`, movimientos por `cajero_id`).
- `/apertura`: una caja por usuario por día. `/movimientos` (POST): exige caja PROPIA abierta; setea `cajero_id`+`cierre_id`. `PUT /movimientos`: no-supervisor solo edita los propios.
- `/cierre`: cierra la caja propia; bloquea solo los movimientos del usuario (helper `_aplicar_cierre`).
- `GET /consolidado` + `POST /consolidado/{id}/cerrar` (require_role admin/superadmin): ver todas las cajas del día con totales/saldo/diferencia por usuario y cerrar cualquiera.
- `POST /cierres/{id}/reabrir`: ampliado de solo-superadmin a Admin+SuperAdmin; desbloquea solo movimientos del dueño.
- Abono CxC `registrar_en_caja`: usa la caja abierta del usuario que registra; sin caja propia abierta guarda el abono sin movimiento; movimiento atribuido con `cajero_id`/`cajero_nombre`.

**Backend `routes/optica.py`:**
- v1 create ahora guarda `created_by_name`.
- `GET /sales/resumen-dia` (vendedor actual): total vendido, cobrado, cantidad, `por_metodo` y `sales[]` (solo del día, scoped por `created_by` y rango UTC del día GT). `GET /sales/resumen-dia/consolidado` (admin/superadmin) por vendedor.

**Frontend:** `Caja.js` encabezado "Mi Caja", botón "Todas las cajas" (admin/superadmin) → diálogo consolidado con cerrar/reabrir por usuario; estado "Sin abrir/Cerrada/Abierta"; egresos en rojo con `-`. `OpticaPOS.js`+`POSSalesDialogs.js`: diálogo "Mis Ventas del Día" con desglose por método y lista solo de hoy.

**Testing:** testing_agent iteration_104 → 7/7 flujos OK (usuario normal sin controles de supervisor, apertura/movimiento/cierre con diferencia, supervisor consolidado+cerrar+reabrir, aislamiento entre usuarios, POS resumen por vendedor). Fix HIGH posterior: la lista "Mis Ventas del Día" ahora solo muestra ventas de hoy (verificado curl+UI).

**Pendiente (fuera de MVP / pre-existente, NO regresiones):** no hay selector Tipo Ingreso/Egreso en el diálogo de movimiento (diseño previo; egresos entran por otros flujos/API); `formatDate` global tiene off-by-one en fechas 'YYYY-MM-DD' (util compartida app-wide); el rol `usuario` no tiene el menú `finanzas_caja` habilitado (decisión de configuración — habilitarlo por rol desde Configuración de menús). Fase 2: corte formal óptica por usuario + comprobante. Fase 3: turnos múltiples y entrega entre cajeros.



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

## 2026-06 — Producción IGSS: verificación testing agent (iteration_85) + fixes
- Testing agent: backend 92% (único fallo: validación de costo negativo), frontend 100% tras corregir la ruta de "abrir expediente" (/evaluacion-oftalmologica). Retest no requerido.
- Fixes aplicados: costo_override ahora Field(ge=0) (negativo → 422); costo_override=null restablece al precio del NOG ($unset); PATCH valida que la evaluación sea de paciente IGSS; listado optimizado (carga por lotes, de ~2-5s a ~0.15s); fecha por defecto usa hora de Guatemala; debounce (350ms) en filtros; input de costo se refresca al cambiar el valor del servidor.

## 2026-06 — Importación oficial de NOG IGSS (listado del cliente)
- Se cargó el listado oficial de 54 NOG (10 unidades) provisto por el usuario en Excel (NOGs_IGSS.xlsx).
- Datos en /app/backend/data/igss_nogs_seed.json (generados fielmente desde el xlsx con openpyxl).
- Importador idempotente seed_igss_nogs_from_list() en server.py, ejecutado al arranque (tras seed_catalogos_igss):
  - Reutiliza unidades por nombre (case/espacios-insensible) y crea las que falten.
  - NOG se identifican por (unidad, número) para compra directa y por (unidad, servicio) para baja cuantía sin número.
  - NO duplica ni modifica NOG existentes; los omite. Preserva acreditados del listado.
  - tipo_compra: con número = compra_directa; sin número = baja_cuantia (según indicación del usuario).
  - monto_total = "Precio total del contrato"; precio = "Precio individual".
- Verificado en preview: 1ra corrida creó 10 unidades + 54 NOG; 2da corrida omitió los 54 (idempotencia). API /api/igss-units/nogs/all devuelve 82 NOG con montos individual/total correctos y etiqueta de tipo de compra.
- Queda activo en producción al publicar (se ejecuta en el arranque del backend). Si los NOG ya existen en prod, se omiten (sin duplicar).

## 2026-06 — Corrección de duplicados NOG/Unidades IGSS
- Causa raíz: el importador automático de NOG (startup) no reconoció unidades/NOG ya existentes en PRODUCCIÓN por diferencias de acentos/espacios/comillas en los nombres, y creó copias (unidades y NOG duplicados en Gestión NOG y en Unidades IGSS).
- Fix 1: se desactivó la llamada automática a `seed_igss_nogs_from_list()` en el startup (ya no crea copias).
- Fix 2: nueva función `cleanup_igss_nog_seed_duplicates()` en server.py:
  - Agrupa unidades por nombre NORMALIZADO (sin acentos, espacios colapsados, mayúsculas).
  - Conserva la unidad MÁS ANTIGUA (registro original del usuario); reapunta NOG/pacientes a ella.
  - Por cada NOG de la copia: si el número/servicio ya existe en la conservada, lo elimina; si no, lo reapunta (NOG genuinamente nuevo no se pierde).
  - Elimina las unidades duplicadas ya vaciadas.
  - Guard de ejecución única por entorno (colección `system_flags`, key `nog_dedup_cleanup_v1`): corre una sola vez por BD (preview y producción separadas).
- Validado en preview: pruebas de inyección con variantes de acento/espacio -> deduplicación correcta (eliminó copia seed, conservó original con sus acreditados, reapuntó NOG nuevos). Idempotente; guard omite ejecuciones posteriores.
- PENDIENTE: al REPUBLICAR, la limpieza corre una vez en producción y elimina las copias conservando los originales.

## 2026-06 — Fase 1 regla de facturación por AUTORIZACIÓN (No. SPS) — correcciones E2E
- Unidad facturable = autorización (No. SPS). 1ra consulta por No. SPS descuenta cupo y genera fila de producción; seguimientos bajo el mismo SPS no descuentan ni duplican fila. Otro SPS del mismo NOG = nuevo servicio. Sin SPS = 1 descuento por paciente/NOG (comodín legado).
- Fix HIGH #1 (_build_produccion_rows): la "primera consulta" se calcula GLOBALMENTE (todas las fechas del paciente), no solo dentro de la ventana consultada. La autorización aparece solo si su primera consulta cae en el filtro (helper _en_ventana). Un seguimiento en otro día/mes ya NO genera fila nueva.
- Fix HIGH #2 (_reconciliar_nog_paciente): los objetivos ahora son la UNIÓN de las órdenes del paciente y las autorizaciones de sus evaluaciones REALES (SPS no vacío, no borrador). Editar un dato no-IGSS (p.ej. teléfono) ya NO anula un cupo descontado por una evaluación con SPS nuevo (origen='evaluacion').
- Producción oculta autorizaciones por SPS que un comodín legado (acreditación sin SPS del mismo paciente/NOG) ya absorbió. DECISIÓN DEL USUARIO: una autorización que no descontó cupo por NOG al 100% SÍ aparece en Producción.
- Hook de acreditación en evaluaciones.py ahora registra los fallos (logging) en vez de ignorarlos.
- Pruebas: tests/test_nog_por_autorizacion.py -> 16/16 PASS (antes 13/16). Suite autolimpia datos TEST_.
