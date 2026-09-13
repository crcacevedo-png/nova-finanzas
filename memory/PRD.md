# PRD - NovaVision ERP Oftalmológico

## Descripción General
Sistema ERP completo para clínicas oftalmológicas con módulos de: Dashboard, Pacientes, Agenda, Evaluación Oftalmológica, Inventario FEFO, POS, Caja, CRM Cirugías, Óptica, y Laboratorio de Pruebas E2E.

## Estado Actual del Proyecto
**Última actualización**: 2026-06 (Sesión 8)

### Últimos Cambios (2026-06 Sesión 8) — NOG por Unidad IGSS (contratos + contador)
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
