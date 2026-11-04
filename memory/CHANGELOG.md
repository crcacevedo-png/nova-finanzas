# CHANGELOG — NovaVisión ERP

## 2026-06 — Sala de Operaciones: Insumos/Equipos, Estado para caja, Nota operatoria y Anestesia (Fase 1 MVP)
**Backend (`routes/quirofano.py` nuevo):**
- Catálogo `surgery_catalog` (insumos/equipos, SIN precio): CRUD + desactivar.
- `anesthesia_types` (honorario fijo por tipo): CRUD.
- `anesthesia_records`: auto-generados desde cada cirugía (crear/editar) + manuales; se eliminan al borrar/cancelar la cirugía si el mes no está cerrado.
- Cierre mensual `/anesthesia/closure`: agrupa por anestesiólogo (cuenta, tipos, total), cerrar mes = marca pagado y solo lectura; reabrir (superadmin). Omite anestesiólogo 'N/A'.
**Backend (`routes/surgeries.py`):** PATCH `/surgeries/{id}/supplies-status` (pendiente/registrados/sin_adicionales, solo Alquiler); add_equipment/add_supply aceptan `catalog_id`; nota operatoria guarda `firma`=cirujano y su PUT edita procedimiento+firma; `supplies_status` en SurgeryResponse.
**Frontend:** páginas nuevas `InsumosEquiposQuirurgicos.js` (2 pestañas CRUD) y `ProcedimientosAnestesia.js` (tipos + cierre mensual); rutas `/quirofano/*` + 2 items de sidebar (menú `quirofano_insumos`, `quirofano_anestesia`, con migración para roles con sala_operaciones). SalaOperaciones: insumos/equipos ahora por Select del catálogo, tipo de anestesia desde el catálogo de tipos, bloque de Estado de insumos para caja (Alquiler) + etiqueta en tabla; se eliminaron los totales por precio de insumos (Total insumos/Total general y columnas de la tabla principal).
**Verificado:** backend por curl (catálogo, tipos, cierre 2026-11, auto-registros, borrado de huérfanos, omisión N/A); frontend testing agent iteration_116.json 100% de flujos solicitados + fixes posteriores (huérfano al eliminar/cancelar, tipo de anestesia desde catálogo, contraste de badge, limpieza de totales). Datos de ejemplo solo en preview.
**Pendiente menor:** dentro de la lista de insumos de cada cirugía aún aparecen columnas unitario/total en Q0.00 (secundario). Fase 2: exportar cierre/nota a PDF-Excel, integrar estado en pantalla de cobro de caja, categorías/filtros de catálogo.
**IMPORTANTE:** requiere REDEPLOY para producción.



## 2026-06 — Sala de Operaciones: captura de datos IGSS por cirugía (Fase 1 MVP)
**Solicitud (plan aprobado):** al registrar/editar una cirugía con institución IGSS, pedir los mismos datos que un paciente IGSS (Unidad desde lista, NOG desde lista de la unidad + opción libre, SPS, No. afiliación, Código, Costo) y autollenar el Procedimiento desde el servicio del NOG, bloqueándolo mientras sea IGSS. Captura SOLO informativa: NO consume NOG ni crea registros en Producción IGSS.
**Backend (`routes/surgeries.py`):** `IGSSData` ahora incluye `unit_id`, `nog_id`, `nog_number` (además de unit, sps, affiliation_number, code, procedure_cost). El flujo de cirugías solo inserta en `db.surgeries`; no toca contadores de NOG ni acreditaciones (verificado: acreditados 0→0 al crear cirugía IGSS).
**Frontend (`SalaOperaciones.js`):** bloque IGSS con selects de Unidad (GET /igss-units) y NOG (GET /igss-units/{id}/nogs-activos, formato 'numero — servicio') + opción 'Escribir NOG libre…'. Al elegir NOG de la lista se autollena y bloquea el Procedimiento (si el servicio está vacío, no se bloquea para permitir escribirlo). Detalle de cirugía muestra Unidad y NOG. data-testids añadidos.
**Verificado:** backend por curl (persistencia + NOG no consumido); frontend testing agent iteration_115.json 100% (9/9 flujos). Fixes menores aplicados tras el test (bloqueo condicionado a servicio no vacío, legibilidad del campo bloqueado, testids).
**Fase 2/3 pendientes:** prefijar unidad/afiliación desde la ficha del paciente; columnas NOG/Código en tabla y export; validaciones obligatorias IGSS; reporte de cirugías por unidad/NOG.
**IMPORTANTE:** requiere REDEPLOY para producción.



## 2026-06 — Cierre del Día: solo admin/superadmin + Clínica/Óptica separados + Concepto
**Solicitud:** (1) el cierre del día solo para superadmin/administrador; (2) el cierre debe llevar separado Clínica de Óptica; (3) columna 'Concepto' en Ventas del día; (correo a dra.mpalma@novavision.me corregido).
**Backend (`routes/caja.py` `calcular_cierre_diario`):** la respuesta ahora es `{general, clinica:{resumen,cobrado_por_metodo,por_usuario,ventas}, optica:{...}, conciliacion_cajas}`. Cada módulo calcula su propio ingreso facturado (devengado = cobrado + CxC), cobrado por método, abonos previos, egresos (solo clínica) y ventas por usuario. Cada venta incluye `concepto` (nombres de productos/servicios: clínica `items[].nombre`, óptica `items_v2[].name`). Se mantienen los filtros de T1 (excluye anuladas/canceladas, ajuste de vuelto, 400 en fecha inválida) y la exclusión de pagos de ventas óptica canceladas.
**Acceso (ya aplicado y verificado):** ruta `/cierre-diario` con `requiredRole={['admin','superadmin']}` (ProtectedRoute ahora acepta lista), backend `require_role(['admin','superadmin'])`, menú solo `isAdminOrSuperAdmin`. Rol óptica recibe 403 y no ve el item.
**Frontend (`CierreDiario.js`):** rediseño con Resumen General + secciones separadas Clínica y Óptica (cada una con tarjetas, métodos, usuarios y tabla de ventas con columna Concepto) + Conciliación de cajas.
**Email (`email_service.py`):** plantilla reconstruida con resumen general + bloques Clínica/Óptica (cada uno con métodos, usuarios y ventas con concepto) + conciliación. Destinatarios corregidos: cacevedo@novavision.me, dra.mpalma@novavision.me.
**Verificado:** backend por curl (general 955 = clínica 805 + óptica 150; concepto poblado; correo enviado a ambos sin errores). Frontend testing agent iteration_114.json 100% (secciones separadas, columna Concepto, control de acceso óptica bloqueado).
**IMPORTANTE:** requiere REDEPLOY para producción.



## 2026-06 — FIX: reportes/dashboard de Óptica deben incluir TODO lo vendido y comprado
**Solicitud:** "todo lo que se vende en la optica debe aparecer en el reporte de rentabilidad... todo debe aparecer en el dashboard de la optica, ventas, compras, de todos los insumos".
**Causas raíz encontradas (bugs preexistentes):**
1. Las ventas del POS v2 guardan los ítems en `items_v2`, pero `rentabilidad` e `informe-mensual` leían `venta.get("items", [])` (campo inexistente). Resultado: accesorios (y cualquier ítem no-legacy) quedaban fuera de rentabilidad y de Top Productos.
2. Los endpoints de dashboard (`stats`, `ventas-dia`, `rentabilidad`, `informe-mensual`, `historial-mensual`) leían `paid_amount`, pero las ventas almacenan `total_paid`. Resultado: "Cobrado/Pagado" salía Q0.
3. La ruta `/optica/dashboard` era `requiredRole="superadmin"` y el item de menú exigía `isSuperAdmin`, así que el rol **optica no podía abrir su propio dashboard**.
**Fix (backend `routes/optica.py`):**
- `rentabilidad`: se reescribió el bucle para usar `items_v2` cuando existe (frame/contact_lens/lens_type/accessory + catch-all `otros`), con fallback a campos legacy si no hay `items_v2` (evita doble conteo). Se agregaron categorías `accesorios` y `otros` a `desglose_categorias`.
- `informe-mensual` Top Productos: misma lógica items_v2/legacy → lista todos los tipos vendidos.
- `replace_all` `paid_amount` → `total_paid` en todas las agregaciones/proyecciones de reportes.
**Fix (menú/acceso):**
- `menu_config.py` default rol optica + migración idempotente en `server.py`: agregan `optica_dashboard` a roles con `optica_pos`.
- `App.js`: `/optica/dashboard` ahora `requiredPermission="view_optica"`.
- `Layout.js`: item `nav-optica-dashboard` visible con `isMenuEnabled('optica_dashboard')` (sin gate superadmin).
**Fix (frontend `OpticaDashboard.js`):** columna Pagado usa `venta.total_paid`; tabla rentabilidad con mapa de etiquetas {aros, lentes_contacto, tipos_lente, accesorios, otros}, oculta filas con cantidad 0; selector de año en Informes ahora dinámico (getFullYear-2..+1).
**Verificado:** backend por curl (stats.cobrado_mes=150, ventas-dia cobrado=150, rentabilidad incluye Accesorios Q150/Q100 ganancia, año muestra las 4 categorías). Frontend rol `optica` por testing agent (iteration_112.json, 100%): abre dashboard, Cobrado Q150, fila Accesorios, Top Productos lista accesorios.
**IMPORTANTE:** requiere REDEPLOY para producción.



## 2026-11-02 — FIX: óptica no podía cobrar en POS de clínica ("Sin permisos para realizar ventas")
**Síntoma:** el usuario óptica ya veía el menú de Punto de Venta de clínica, pero al cobrar: "Sin permisos para realizar ventas".
**Causa:** `routes/ventas.py` `crear_venta` tenía un chequeo HARDCODEADO por rol (`if role not in ["superadmin","admin","usuario"]: 403`) además de la dependencia que ya valida `manage_sales`. Ese check excluía a óptica (y a cualquier rol personalizado con el permiso).
**Fix:** se eliminó el chequeo por rol redundante; la autorización queda solo en `get_current_user_dependency()` (permiso `manage_sales`). Verificado: óptica POST /api/ventas ya no da 403 de permiso (pasa a validación normal 400 por venta vacía). caja.py y cuentas_cobrar.py no tienen checks por rol (usan permisos), así que óptica también puede abrir caja/CxC.
**IMPORTANTE:** requiere REDEPLOY para producción.



## 2026-11-02 — FIX: crash "Algo salió mal" al agregar orden NOG a un paciente
**Síntoma:** al agregar una orden NOG en la ficha del paciente (IGSS) aparecía la página de error (ErrorBoundary).
**Causa raíz:** el endpoint `GET /api/igss-units/{unit}/nogs-activos` devolvía NOGs con `numero` vacío. En el selector de NOG (`NogSelector`, Radix Select) un `<SelectItem value="">` lanza una excepción ("A <Select.Item /> must have a value prop that is not an empty string") → crash capturado por el ErrorBoundary. Verificado: la unidad 9d8260dc devolvía 11 NOGs, el primero con numero="".
**Fix (doble capa):**
- `backend/routes/igss_nogs.py` — `listar_nogs_activos` ahora excluye NOGs con numero null/"" (`numero: {$nin:[None,""]}`). Verificado: la unidad pasó de 11 a 10 NOGs, 0 vacíos. Cubre tanto el selector de la ficha como el filtro de NOG de la lista (ambos usan este endpoint).
- `frontend/src/components/NogSelector.js` — filtra NOGs sin número antes de renderizar (defensa adicional).
**Verificado:** API sin NOGs vacíos; el formulario de paciente IGSS renderiza y permite agregar orden sin ErrorBoundary.
**IMPORTANTE:** requiere REDEPLOY para producción.



## 2026-11-02 — Rol óptica: acceso al Punto de Venta de CLÍNICA
**Pedido:** el usuario óptica ya tenía Caja, pero faltaba el Punto de Venta de clínica (`/punto-venta`).
**Causa:** el POS de clínica exige el permiso `manage_sales` (ventas.py `get_current_user_dependency`), que el rol óptica no tenía; y no había ítem de menú de POS clínica para óptica.
**Fix:**
- `frontend/src/components/Layout.js` — ítem "Punto de Venta Clínica" (`/punto-venta`, testid `nav-optica-pos-clinica`) en la sección Óptica, visible con `hasPermission('manage_sales')`.
- `backend/server.py` — `_MODULE_PERMS['optica'].manage_sales = True` (default del sistema).
- `backend/server.py` (startup) — migración idempotente: `db.roles['optica']` recibe `manage_caja=true` y `manage_sales=true` en cada arranque (asegura que producción obtenga el permiso tras el redeploy, aunque el doc de rol ya exista; `resolve_permissions` fusiona default + db.roles).
**Verificado (preview):** óptica → `/auth/me` manage_sales=true; el menú muestra "Punto de Venta Clínica" y la ruta `/punto-venta` carga sin 403.
**IMPORTANTE:** requiere REDEPLOY (la migración corre al iniciar el backend en producción) y que los usuarios óptica cierren sesión y vuelvan a entrar.



## 2026-11-02 — FIX: menú del rol óptica (POS, CxC ya por config; Caja por código)
**Síntoma (producción):** el usuario óptica tenía permisos de POS óptica, Cuentas por Cobrar y Caja, pero no aparecían en el menú.
**RCA (deployer, lectura de prod):** el menú se controla por `menu_configurations` (Menús por Rol), NO por permisos. POS óptica y CxC óptica YA estaban habilitados en la config de prod (editada por superadmin) → solo requieren re-login (los menús se cargan al iniciar sesión). 'Caja' NO podía aparecer para óptica por código: en `Layout.js` el bloque Finanzas (con Caja) está excluido para rol óptica y no existía ítem de Caja para óptica.
**Fix de código:**
- `frontend/src/components/Layout.js` — se agregó ítem 'Caja' (`/caja`, testid `nav-optica-caja`) en la sección Óptica, visible con `hasPermission('manage_caja')`. La ruta `/caja` ya está protegida por permiso (no por rol), así que óptica con manage_caja puede entrar.
- `backend/server.py` — `_MODULE_PERMS['optica'].manage_caja` ahora True (antes False), para alinear el rol de sistema óptica con la intención/producción.
**Verificado (preview):** login como óptica → `/auth/me` manage_caja=true; menú muestra Punto de Venta, Cuentas por Cobrar y Caja (nav-optica-pos/cxc/caja presentes).
**IMPORTANTE:** requiere REDEPLOY para producción. Además, los usuarios óptica deben cerrar sesión y volver a entrar para que se recarguen los menús.



## 2026-11-02 — FIX producción: autoguardado y cambio de estado de citas (CORS PATCH)
**Síntomas (solo producción):** (1) el autoguardado de expedientes no persistía; (2) al presionar "Iniciar" (Presente → En consulta) en Agenda salía "Error al cambiar estado".
**Causa raíz (RCA del deployer):** el `CORSMiddleware` en `backend/server.py` NO incluía `PATCH` en `allow_methods`. Los endpoints afectados son PATCH (`/api/evaluaciones/{id}/autoguardar` y `/api/agenda/citas/{id}/estado`), por lo que el preflight OPTIONS del navegador era rechazado (400 'Disallowed CORS method') y la petición PATCH nunca llegaba al handler. El front caía a "guardado offline" / "Error al cambiar estado". En preview no se notaba por configuración de origin.
**Fix:** `server.py` — `allow_methods` ahora incluye `PATCH` (GET, POST, PUT, PATCH, DELETE, OPTIONS). Corrige también cualquier otro endpoint PATCH (p.ej. inventario). Verificado: preflight OPTIONS PATCH → 200 con `access-control-allow-methods` incluyendo PATCH en /autoguardar y /citas/{id}/estado.
**Robustez adicional (defensa, no era la causa):** `CitaResponse` y `EvaluacionOftalmologicaResponse` ahora descartan valores `null` de nivel superior (validator `mode="before"`) para tolerar documentos antiguos/parciales sin romper la validación del response.
**IMPORTANTE:** requiere REDEPLOY para aplicar en producción.



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

## 2026-06 — Menú lateral: Sala de Operaciones como grupo colapsable
- Layout.js: "Sala de operaciones", "Insumos y Equipos Qx" y "Proced. de Anestesia" dejan de ser ítems planos y ahora son subítems de un grupo colapsable "Sala de Operaciones" (ícono Scissors), igual que Óptica/Finanzas/Inventario.
- Subítems: Cirugías (/sala-operaciones), Insumos y Equipos Qx (/quirofano/insumos-equipos), Proced. de Anestesia (/quirofano/anestesia). Cada uno respeta su isMenuEnabled.
- El grupo se auto-expande/resalta en rutas /sala-operaciones o /quirofano/*. Sin cambios de rutas ni funcionalidad. Orden especial del rol médico intacto.

## 2026-06 — Acceso CRM a rol "usuario" + Exportación de Anestesia
- Rol `usuario` ahora puede revisar el CRM de Cirugías: `crm_cirugias` agregado a DEFAULT_MENU_CONFIG['usuario'] (menu_config.py) y migración de startup en server.py ($addToSet a db.menu_configurations). Layout.js: el ítem CRM ahora se rige por isMenuEnabled('crm_cirugias') en vez de admin-only.
- Cierre mensual de anestesia exportable: nuevo endpoint GET /api/quirofano/anesthesia/closure/export?month=YYYY-MM&format=xlsx|pdf (require_role admin/superadmin), con openpyxl/reportlab. Botones Excel/PDF en el tab "Cierre mensual" (ProcedimientosAnestesia.js).
- Nota operatoria imprimible: botón "Imprimir" (data-testid nota-imprimir) en NotaCirugia.js abre ventana de impresión formateada (paciente, procedimiento, fecha, ojo, cirujano, institución, contenido, firma), visible en notas abiertas y cerradas.
- Fix: num_registros del cierre ahora cuenta solo registros agrupados (excluye sin anestesiólogo) para consistencia entre header, Excel y PDF.
- Verificado: testing_agent iteration_117 (3 flujos frontend OK); exports curl-validados.

## 2026-11 — Dashboard Óptica: fix ventas del día (zona horaria) + reorganización de cards
- BUG FIX: "Ventas Hoy" mostraba Q0 aunque había ventas del día. Causa: /optica/dashboard/ventas-dia usaba medianoche UTC en vez del día local de Guatemala (GMT-6). Ahora usa today_str_gt() + dia_gt_a_rango_utc(). Verificado end-to-end (testing_agent iter_118): venta creada a las 22:17 GT se registró como venta de hoy.
- Dashboard reorganizado a 7 cards: Ventas Hoy, Cobrado Hoy, Cuentas por Cobrar (nuevo, saldo pendiente global), Rentabilidad (mes), Pagos de Óptica (nuevo, compras/egresos del período), Ingresos (mes, sin cambios), Utilidad (nuevo = Ingresos − Pagos).
- Backend: ventas-dia agrega cuentas_por_cobrar y cuentas_por_cobrar_count; rentabilidad agrega total_compras, num_compras, utilidad.
- Rentabilidad ahora calcula los límites de período (día/semana/mes/año) en hora de Guatemala; filtro de compras compara contra fecha-only para incluir el día 1 del período.
- Archivos: backend/routes/optica.py (get_ventas_del_dia, get_rentabilidad_optica), frontend/src/pages/OpticaDashboard.js.

## 2026-11-03 — Meta de Ventas en Dashboard de Óptica
### Backend (routes/optica.py)
- Nuevo modelo MetasVentasUpdate (meta_diaria, meta_mensual >= 0).
- GET /api/optica/dashboard/metas (perm view_optica): devuelve meta_diaria, meta_mensual, ventas_hoy, ventas_mes (hora Guatemala), progreso_dia, progreso_mes, falta_dia, falta_mes. Guard de división por cero (meta 0 -> 0%).
- PUT /api/optica/dashboard/metas (perm manage_optica_sales): guarda metas en colección optica_dashboard_config (_id="metas_ventas", upsert).
- ventas_hoy usa dia_gt_a_rango_utc(today_str_gt()); ventas_mes desde día 1 del mes local GT.
### Frontend
- api.js: opticaSaleApi.getMetas() y setMetas(data).
- OpticaDashboard.js: nueva tarjeta "Meta de Ventas" (testId metas-ventas-card) con 2 barras de progreso personalizadas (día azul/mes ámbar, verde al 100%), estado vacío, y diálogo "Definir metas" (testIds edit-metas-btn, metas-dialog, meta-diaria-input, meta-mensual-input, metas-save-btn). Carga en loadDashboardData.
Verificado: curl GET/PUT OK (195/1500=13%, 195/40000=0.5%); screenshot desktop (barras + 7 tarjetas) y móvil (diálogo con inputs). Preview URL real: novavision-finanzas.preview.emergentagent.com.

## 2026-11-03 — Reorganización menú rol Óptica (Layout.js)
- Quitados del grupo "Óptica" los ítems de clínica: "Punto de Venta Clínica" (/punto-venta) y "Caja" (/caja).
- Nuevo grupo "Finanzas" para rol optica (rama else en finanzasItems) con ítems de clínica: Punto de Venta (/punto-venta, gate manage_sales), Cuentas por Cobrar (/cuentas-cobrar-finanzas, gate manage_sales), Caja (/caja, gate manage_caja). testIds: nav-punto-venta, nav-cxc-finanzas, nav-caja.
- Añadido /cuentas-cobrar-finanzas a paths de estado activo y a init de finanzasOpen.
- Rol optica tiene manage_sales y manage_caja (confirmado vía login). Sin cambios de backend ni de permisos.
Verificado: screenshot — grupo Óptica sin ítems de clínica; grupo Finanzas con los 3 ítems presentes.

## 2026-11-03 — Inventario vs POS clínica: stock por bodega + total, y productos por bodega
Causa raíz: el panel de Inventario suma TODAS las bodegas (6 bodegas; 19/24 productos en varias), mientras el POS mostraba solo la bodega de venta → descuadre aparente en productos multi-bodega.
### Backend (routes/ventas.py)
- ProductoPOSResponse: nuevo campo existencia_total (suma todas las bodegas).
- buscar_productos_pos y obtener_productos_rapidos: calculan existencia_total con obtener_existencias_totales (reusado de inventario.py). Servicios (controla_inventario=False) -> -1.
### Frontend
- PuntoVenta.js: cada tarjeta de producto muestra línea "Bodega: X · Total: Y" (testId stock-detalle-{id}) cuando el total difiere de la bodega.
- inventario/Bodegas.js: botón "Ver productos" por bodega (testId ver-productos-{id}) abre diálogo (bodega-productos-dialog) con tabla de productos + cantidad, buscador y total; usa GET /inventario/existencias?bodega_id.
Verificado: curl (Acetazolamida bodega=0/total=60, BSS Plus 3/31); screenshots desktop+móvil (POS sin overflow a 390px) y diálogo de bodega con 24 productos.
Nota: 1 producto (Acetazolamida) tiene drift real existencia(60) vs suma de lotes(28); el usuario pidió NO corregir históricos.

## 2026-11-03 — Botón "Reconciliar lotes" (solo admin)
### Backend (routes/inventario.py)
- Helper _detectar_discrepancias_lotes: compara existencias_inventario.cantidad vs suma de lotes_inventario.cantidad_disponible por (producto,bodega) para productos controla_lotes.
- GET /inventario/reconciliar-lotes/preview (admin/superadmin): lista descuadres.
- POST /inventario/reconciliar-lotes (admin/superadmin): fija existencia = suma de lotes y registra movimiento en kardex (referencia_tipo=reconciliacion_lotes).
### Frontend
- api.js: inventarioApi.reconciliarLotesPreview() y reconciliarLotes().
- inventario/Bodegas.js: botón "Reconciliar lotes" en header solo para admin/superadmin (testId reconciliar-lotes-btn) usando useAuth; diálogo (reconciliar-dialog) con tabla de descuadres (existencia/lotes/ajuste), estado "Todo cuadra", y botón Reconciliar (reconciliar-aplicar-btn) que aplica y re-verifica.
Verificado: curl preview(1: Acetazolamida 60 vs 28)→aplicar→preview(0); screenshots del flujo completo en UI (detectar y "Todo cuadra" tras reconciliar). Acetazolamida quedó corregida en preview.

## 2026-11-03 — Selector de bodega en Punto de Venta (clínica)
Problema (producción): el POS estaba fijo a una bodega (Dispensario); productos con stock en otra bodega mostraban "Bodega: 0" y no se podían vender.
### Frontend (PuntoVenta.js)
- Nuevo estado bodegasList; fetchBodegaPOS ahora también carga bodegas activas (inventarioApi.getBodegas({activo:true})).
- Header: el texto fijo "Bodega: X" se reemplazó por un Select (testId pos-bodega-selector, opciones pos-bodega-option-{id}) cuando hay >1 bodega; cualquier usuario del POS puede cambiarla.
- handleCambiarBodega: cambia bodegaPOS (dispara refetch de productos para la nueva bodega) y vacía el carrito para evitar vender stock de otra bodega.
- La venta usa bodegaPOS.bodega_id de la bodega seleccionada.
Verificado: screenshot — al cambiar de Dispensario a Bodega General, Acetazolamida pasó de "Bodega: 0 · Total: 28" a "Bodega: 28" (vendible). 3 bodegas (Bodega General, Dispensario, Quirófano). Móvil OK (overflow restante es layout pre-existente del POS).
Pendiente sugerido: no existe "Traslado entre bodegas" (el Kardex solo exporta informe); el usuario lo mencionó.

## 2026-11-03 — Traslado entre bodegas (clínica)
### Backend (routes/inventario.py)
- POST /inventario/traslados (admin/superadmin): mueve N unidades de un producto entre bodegas.
  - Valida existencia en origen; actualiza existencias agregadas de ambas bodegas.
  - Productos con lotes (FEFO): lote completo -> reasigna bodega_id; parcial -> reduce origen y crea/mezcla lote en destino con número sufijado "-{codigo_destino}" (índice único producto_id+numero_lote impide duplicar el mismo número).
  - Registra en kardex: transferencia_salida (origen) + transferencia_entrada (destino), referencia_tipo="traslado".
- Modelo TrasladoRequest(producto_id, bodega_origen_id, bodega_destino_id, cantidad>0, motivo?).
### Frontend
- api.js: inventarioApi.crearTraslado(data).
- inventario/Bodegas.js: botón "Traslado" en header (solo admin, testId traslado-btn) + diálogo (traslado-dialog): select origen -> carga productos con stock de esa bodega -> select producto (muestra disponible) -> cantidad (máx=disponible, deshabilitada hasta elegir producto) -> select destino (excluye origen) -> motivo opcional. testIds: traslado-origen-select/-{id}, traslado-producto-select/-{id}, traslado-cantidad-input, traslado-destino-select/-{id}, traslado-motivo-input, traslado-guardar-btn. Header responsive (flex-col/flex-wrap en móvil).
Verificado: curl (Prednisolona lote parcial General 31->28, Dispensario 15->18; reconcile preview=0; kardex con salida+entrada); UI e2e (24 productos, cantidad se habilita, toast "Traslado de 2 unidad(es)... realizado").

## 2026-11-03 — Meta de Óptica: solo meta mensual (se quitó la diaria)
- OpticaDashboard.js: eliminada la barra "Meta del Día" (meta-dia-progress) y el campo meta-diaria-input del diálogo; la "Meta del Mes" ocupa todo el ancho. handleSaveMetas envía meta_diaria:0; openMetasDialog y estado solo manejan meta mensual.
- optica.py: MetasVentasUpdate.meta_diaria ahora opcional (default 0).
Verificado: screenshot — solo aparece Meta del Mes y el diálogo solo pide "Meta mensual (Q)".

## 2026-11-03 — Proyección de cierre de mes (Meta de Óptica)
- optica.py GET /dashboard/metas: agrega proyeccion_mes = ventas_mes / dias_transcurridos * dias_mes (hora Guatemala), más dias_transcurridos y dias_mes.
- OpticaDashboard.js: bajo la barra de Meta del Mes, línea (testId meta-mes-proyeccion) "A este ritmo cerrarás el mes en Q X" con color verde si proyeccion>=meta o ámbar si por debajo (icono TrendingUp).
Verificado: curl (195 en día 3/30 -> proyección 1950) y screenshot de la línea en la UI.

## 2026-11-03 — Facturación FEL (Digifact / Guatemala SAT) — Fase 1
Alcance: Régimen General (FACT, IVA 12% incluido), ventas de clínica y óptica, ambiente PRUEBAS primero, receptor CF por defecto o NIT+nombre, con anulación (admin).
### Backend (routes/fel.py, registrado en server.py)
- Cliente Digifact: _get_token (login/get_token), _certificar_nuc (v2/transform/nuc_json), CancelFelGT, GetDocument.
- Credenciales: DIGIFACT_USERNAME (usuario corto) + DIGIFACT_PASSWORD en secretos; NIT del emisor en config FEL -> usuario completo GT.NIT12.usuario.
- Config en colección fel_config (GET/PUT /api/fel/config, admin): enabled, environment(test/prod), nit, emisor_nombre, afiliacion_iva(GEN), establecimiento, direccion/municipio/depto/cp, frase_tipo/escenario.
- _build_nuc: NUC-JSON FACT (Seller con AfiliacionIVA y frase ISR, BranchInfo, Buyer CF/NIT, Items con IVA 12% hacia adentro, Totals, AdditionalDocumentInfo/ADENDA GUID).
- Endpoints: POST /fel/certificar {origen,sale_id,receptor_nit,receptor_nombre}; POST /fel/anular (admin); GET /fel/documento; GET /fel/estado. Guarda en fel_documents y campo fel en la venta (ventas / optica_sales).
- IMPORTANTE: errores de Digifact se devuelven como 400 (no 5xx) porque Cloudflare reemplaza 5xx con su página de error.
### Frontend
- services/api.js: felApi.
- components/FELButton.jsx: dialogo certificar (CF/NIT), ver/descargar PDF, anular (admin). Badges de estado.
- pages/FELConfig.js: pantalla admin de configuración (ruta /fel/configuracion, menú Finanzas, testId fel-config-page).
- Integrado en OpticaVentas.js (detalle de venta) y PuntoVenta.js (modal post-venta).
Verificado: config GET/PUT OK; pipeline certify llega a Digifact (login + NUC) y retorna error JSON limpio (401 con NIT ficticio, esperado); pantalla de config renderiza con credenciales detectadas.
PENDIENTE para completar prueba real: el usuario debe ingresar su NIT real de emisor en Configuración FEL (va ligado a las credenciales TESTUSER), habilitar FEL y certificar una venta. No se pudo certificar exitosamente sin el NIT correcto.

## 2026-11-03 — FEL Digifact: integración funcional, bloqueo del lado Digifact
- Autenticación OK (token). Respuesta de token viene como "Token" (mayúscula) -> _get_token lee ambos.
- Errores de Digifact ahora usan campo "description" (field-level) y se devuelven como 400 (Cloudflare bloquea 5xx).
- Esquema NUC corregido: SIN wrapper {"NUC":...} (raíz directa), Version "1.00", y campos tipo código como STRING (Tax.Code, BranchInfo.Code, frase Value). BranchInfo requiere "Name" (nombre comercial).
- Frase tributaria: Data string, y Name debe ser "TipoFrase" + "Escenario" (NO "CodigoEscenario") para que el transform la empareje. frase_tipo/frase_escenario configurables en la UI.
- Estado actual: la certificación pasa validación de esquema y de frase; falla en paso Digifact "PrepareEmisorForTOSIGN" con "Root element is missing" (3064). Es del lado Digifact: el emisor de PRUEBAS (NIT 90042247, establecimiento 1) requiere aprovisionamiento/plantilla de firma en su ambiente TEST. Pendiente confirmar con soporte Digifact (soporte-gt@digifact.com).

## 2026-11-03 — Fixes Caja + Dashboard (ventas del día)
- Dashboard /dashboard/resumen-dia (server.py): "Ventas del Día" sumaba SOLO optica_sales. Ahora también suma ventas de clínica (db.ventas origen=clinica, estado!=anulada) por fecha (rango UTC del día GT). "Cobrado" clínica = formas_pago no "Cuenta por Cobrar". Verificado: Q0 -> Q300.
- Caja /caja/movimientos (routes/caja.py): admin/superadmin ahora ven los movimientos de TODAS las cajas del día (no solo los propios); cajeros normales siguen viendo solo los suyos. Frontend Caja.js: columna "Cajero" visible solo para admin/superadmin en "Movimientos del Día".

## 2026-11-03 — Ventas por área + Historial comparativo + Análisis de Producción (Fase 1)
- Dashboard /dashboard/resumen-dia (server.py): añade ventas_clinica y ventas_optica {cantidad,total,cobrado} además del total combinado. Frontend Dashboard.js: tarjeta "Ventas del Día" muestra líneas Clínica y Óptica.
- Caja /caja/cierres (caja.py): superadmin ve cierres de TODOS los cajeros con ingresos recalculados de movimientos reales (helper _desglose_ingresos_dia), + resumen_cajeros (total vendido, # ventas, # cierres, diferencia acumulada) y is_superadmin. No-superadmin solo ve los suyos. Frontend Caja.js: diálogo Historial con comparativo + columna Cajero + detalle con desglose por tipo (efectivo/otros/por método).
- Caja /caja/cierres/{id}: detalle con ingresos_efectivo/otros, num_ventas, desglose_por_metodo. Fix IDOR: no-superadmin solo puede ver su propio cierre (403 si ajeno).
- Ventas /ventas/analisis (ventas.py, solo superadmin): KPIs (total/num/ticket), top productos (ingresos y unidades), por_cajero, por_medico, por_categoria (lookup productos_inventario->categorias_inventario, "Sin categoría" si falta), tendencia por día GT. Período hoy/semana/mes/rango. Fecha inválida -> 400.
- Nueva página AnalisisProduccion.js (/analisis-produccion, requiredRole superadmin), nav "Análisis de Producción" en Finanzas (solo superadmin).
- Testing iteration_119: frontend 100%, backend fixes (IDOR, 400 fecha) verificados por curl.
- PENDIENTE (preexistente, fuera de este plan): drift de permisos óptica entre config/permissions.py (manage_caja=False) y server.py (True) -> óptica recibe 403 en /api/caja/*. No modificado para no tocar la matriz de permisos.

## 2026-11-04 — NOG en llegada, NOG óptica y revisión de Ventas de óptica (3 features)
- Feature 1 (Agenda.js): el modal "Crear/Completar expediente" (al marcar llegada) ahora incluye la sección "Órdenes IGSS" (NogSelector reutilizado, múltiples órdenes con No.SPS/Código/Procedimiento). Al guardar llama patientApi.create/update que descuenta el NOG vía _reconciliar_nog_paciente. Verificado: NOG 0->1 al guardar.
- Feature 2 (verificado, sin cambio de código): óptica YA puede elegir/editar NOG en Pacientes y descuenta (nogs-activos usa get_current_user; create/update patients solo requieren create/edit_patients que óptica tiene). Confirmado por curl y testing agent (acreditados 0->1->2).
- Feature 3: nueva entrada "Ventas" en menú Óptica (Layout.js, canViewOptica). OpticaVentas.js: filtros de fecha (dateFrom/dateTo), botón Reimprimir ticket (handlePrintTicket con escape HTML), botón Anular (solo admin/superadmin). Backend optica.py: cancel_optica_sale ahora require_role(admin/superadmin) y revierte inventario por items_v2 (frame/contact_lens/accessory por cantidad, fallback legacy) + marca cancelled_by/at. Verificado: stock 90->88->90.
- Fixes post-testing (optica.py): OpticaSaleResponse incluye items_v2 + campos de cancelación (detalle/ticket ahora muestran productos); enrich_sale ya no sobrescribe patient_name/doctor_name en ventas walk-in (muestra "Consumidor Final"); filtro dateFrom/dateTo usa rango GT->UTC; _resumen_ventas (resumen-dia/consolidado POS) excluye ventas canceladas y sus pagos. OpticaVentas detalle renderiza items_v2; fetchDashboard() tras anular.
- Testing iteration_120: backend 5/5, frontend 100% de los flujos pedidos. Pendiente menor (no bloqueante): N+1 en GET /optica/sales; "()" vacío en historial de pagos cuando método/creador en blanco.

## 2026-11-04 — Fix "Ver paciente" (Agenda) + mejora "Copiar a receta de anteojos"
- Agenda "Ver paciente" abría /pacientes?id= pero Pacientes.js no leía el id -> agregado useEffect que lee ?id= y abre el expediente (detailDialogOpen). Verificado en pantalla.
- EvaluacionOftalmologica.js copiarRefraccionAReceta: el copiado desde Refracción ya funcionaba en preview (producción corre build anterior; requiere redeploy). Mejora: si Refracción está vacía, copia desde Lensometría/Autorefractómetro; si todo está vacío, NO crea receta vacía y muestra error. Verificado en preview (lensometría->receta OK; vacío->error).

## 2026-11-04 — FEL Digifact: corrección estructura NUC + IVA incluido
- routes/fel.py _build_nuc: corregida estructura NUC para pasar el esquema de Digifact (verificado contra ejemplo oficial FACT CF): Items como array, Taxes.Tax[].Code y BranchInfo.Code como String, frase con Name "TipoFrase"+"Escenario" (NO "CodigoEscenario"), agregado UnitOfMeasure "UND" y Rate 12.
- IVA incluido: Price del ítem ahora = precio con IVA incluido (TotalItem/Qty); base=total/1.12, IVA=total-base. Clínica total ya traía iva aparte sumado al total; óptica total=subtotal IVA-incl. Verificado: clínica 168=150+18; óptica 680=607.15+72.85.
- BLOQUEO RESTANTE (lado Digifact): certificación falla en PrepareEmisorForTOSIGN [3064] Root element is missing, idéntico para cualquier TipoFrase/Escenario -> el emisor NIT 000090042247 no está aprovisionado/habilitado para firmar en test. Requiere acción de Digifact. frase_tipo/frase_escenario configurables en Configuración FEL.
