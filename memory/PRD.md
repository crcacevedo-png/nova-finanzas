# PRD - NovaVision ERP Oftalmológico

## Descripción General
Sistema ERP completo para clínicas oftalmológicas con módulos de: Dashboard, Pacientes, Agenda, Evaluación Oftalmológica, Inventario FEFO, POS, Caja, CRM Cirugías, Óptica, y Laboratorio de Pruebas E2E.

## Estado Actual del Proyecto
**Última actualización**: 2026-08-26 (Sesión 3)

### Últimos Cambios (2026-08-26 Sesión 3)
- ✅ **Campo "Precio de Compra" agregado a Productos de Inventario**
  - Nuevo campo `precio_compra` en formulario de Nuevo Producto y Edición
  - Backend actualizado: Modelo Pydantic (`ProductoBase`, `ProductoUpdate`, `ProductoResponse`)
  - Soporte en importación Excel (columna `precio_compra`)
  - Plantilla CSV actualizada con el nuevo campo

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
