# NovaVision - Sistema de Gastos y Finanzas
## Clínica Oftalmológica

---

## Descripción General
Sistema web completo para gestión financiera de clínica oftalmológica. Base de datos: MongoDB. Moneda: Quetzales (GTQ).

### Módulos Implementados
1. **Autenticación y Seguridad** - JWT, roles, audit logs
2. **Gastos y Finanzas** - Gastos, pagos, autorizaciones, caja
3. **Pacientes y Evaluaciones** - Evaluación oftalmológica completa
4. **Sala de Operaciones** - Gestión de cirugías
5. **Óptica** - Inventario y ventas de óptica
6. **Agenda** - Citas de pacientes
7. **📦 Inventario** - Control de productos, lotes, existencias, kardex
8. **🆕 Punto de Venta (POS)** - Sistema táctil integrado con inventario FEFO

---

## 🔒 Configuración de Seguridad (Actualizado Junio 2026)

### Headers de Seguridad
- `X-Frame-Options: DENY` - Previene clickjacking
- `X-Content-Type-Options: nosniff` - Previene MIME sniffing
- `X-XSS-Protection: 1; mode=block` - Protección XSS
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`
- `Content-Security-Policy: frame-ancestors 'none'`

### Autenticación
- JWT con expiración de 8 horas
- Bcrypt (costo 12) para hashing de contraseñas
- Token blacklist persistente en MongoDB
- Rate limiting: 5 intentos/minuto en login
- Validación de fortaleza de contraseña (8+ chars, mayúscula, minúscula, número)

### CORS
- Orígenes permitidos configurados en `.env`
- Solo dominios específicos (no `*`)

### Audit Logging
- Registro de logins exitosos/fallidos
- Registro de cambios de contraseña
- Registro de logouts
- IP del cliente registrada
- Endpoint `/api/security/audit-logs` (solo superadmin)

### Endpoints de Seguridad
- `GET /api/security/status` - Estado de seguridad (superadmin)
- `GET /api/security/audit-logs` - Logs de auditoría (superadmin)
- `POST /api/security/change-password` - Cambio de contraseña

---

## Arquitectura

```
/app/
├── backend/
│   ├── server.py              # API principal (~6500 líneas - pendiente migración completa)
│   ├── config/
│   │   ├── database.py        # Conexión MongoDB, configuración JWT
│   │   └── permissions.py     # Sistema de permisos por rol
│   ├── routes/                # ✅ Módulos extraídos (parcial)
│   │   ├── __init__.py        # Exporta todos los routers y modelos
│   │   ├── auth.py            # ✅ Login, logout, usuarios, permisos
│   │   ├── expenses.py        # ✅ CRUD gastos
│   │   ├── payments.py        # ✅ CRUD pagos
│   │   ├── dashboard.py       # ✅ Dashboard y estadísticas
│   │   ├── bank_accounts.py   # ✅ Cuentas bancarias
│   │   ├── suppliers.py       # ✅ Proveedores
│   │   ├── fixed_expenses.py  # ✅ Gastos fijos
│   │   ├── igss_units.py      # ✅ Unidades IGSS
│   │   └── surgeries.py       # ✅ NEW: Cirugías completo (CRUD + reportes)
│   ├── models/                
│   └── tests/                 
├── frontend/
│   └── src/
│       ├── App.js             
│       ├── components/
│       │   ├── Layout.js      
│       ├── pages/
│       │   ├── Gastos.js      
│       │   ├── AutorizacionesPendientes.js
│       │   ├── SalaOperaciones.js  # NEW: UI Cirugías
│       │   └── ...
│       └── services/
│           └── api.js         
```

---

## Estado de Refactorización

### ✅ Módulos Completamente Extraídos a `/routes/`:
1. **auth.py** - Autenticación, usuarios, tokens JWT
2. **expenses.py** - ✅ CRUD gastos + pagos completo (640 líneas)
3. **dashboard.py** - Dashboard y estadísticas
4. **bank_accounts.py** - Cuentas bancarias (modelos en server.py)
5. **suppliers.py** - Proveedores
6. **fixed_expenses.py** - Gastos fijos
7. **igss_units.py** - Unidades IGSS
8. **surgeries.py** - ✅ CRUD completo + reportes Excel/PDF (806 líneas)
9. **caja.py** - Módulo de Caja completo
10. **agenda.py** - Módulo de Agenda de Pacientes
11. **admin.py** - Endpoints de integridad y administración
12. **dashboard_financiero.py** - Dashboard exclusivo SuperAdmin
13. **patients.py** - ✅ CRUD completo de pacientes + búsqueda (823 líneas)
14. **evaluaciones.py** - ✅ Evaluaciones oftalmológicas + catálogos (448 líneas)
15. **optica.py** - ✅ NEW: Médicos, Aros, Lentes, Ventas, Compras, Dashboard (1322 líneas)
16. **payment_authorizations.py** - ✅ NEW: Autorizaciones de pago (401 líneas)
17. **inventario.py** - ✅ Inventario completo: productos, bodegas, lotes FEFO, kardex (1775 líneas)
18. **inventario_ops.py** - ✅ Operaciones de inventario: entradas, transferencias, ajustes
19. **ventas.py** - ✅ NEW: Punto de Venta (POS) táctil integrado (886 líneas)

### 🟡 Módulos Pendientes de Extracción:
- Cuentas bancarias (rutas) - ~100 líneas aún en server.py
- Proveedores (rutas) - ~100 líneas aún en server.py
- Dashboard general (rutas) - ~150 líneas aún en server.py

### 📊 Progreso de Refactorización FINAL:
- **Antes (Julio 2026)**: server.py ~8000 líneas
- **Después (1 Agosto 2026)**: server.py **3029 líneas**
- **Reducción total**: ~4971 líneas extraídas (**62%**)
- **Módulos extraídos**: 17 archivos en `/routes/`
- **Total código modularizado**: ~5326 líneas

---

## 🆕 Punto de Venta (POS) - Implementado 6 Agosto 2026

### Descripción
Sistema de Punto de Venta táctil integrado con el módulo de Inventario, optimizado para tablets.

### Características:
- **Ventas anónimas**: Permite vender a "Cliente General" sin requerir paciente registrado
- **Formas de Pago**: Efectivo, Tarjeta, Transferencia, Cheque, Pago Mixto, Crédito (→ Cuentas por Cobrar)
- **Pago Mixto**: Permite combinar múltiples métodos de pago en una misma venta (ej: Q100 efectivo + Q200 tarjeta)
- **Integración FEFO**: Descuenta inventario usando First Expire First Out
- **Control de Caja**: Requiere caja abierta para operar
- **Tickets**: Numeración correlativa (VTA-YYYYMMDD-####)
- **IVA Guatemala**: 12% calculado automáticamente
- **Impresión Térmica**: Tickets optimizados para impresoras de 58mm y 80mm
- **Productos Rápidos**: Grid de acceso rápido con los productos más vendidos (últimos 30 días)

### Archivos Clave:
- `/app/backend/routes/ventas.py` - Router backend (~886 líneas)
- `/app/frontend/src/pages/PuntoVenta.js` - UI táctil (~1210 líneas)

### Endpoints:
- `GET /api/ventas/bodega-pos` - Obtener bodega POS predeterminada
- `GET /api/ventas/productos` - Buscar productos con stock
- `GET /api/ventas/productos-rapidos` - Productos más vendidos (últimos 30 días)
- `POST /api/ventas/verificar-stock` - Verificar disponibilidad
- `POST /api/ventas` - Crear venta (descuenta inventario)
- `GET /api/ventas/hoy` - Ventas del día
- `GET /api/ventas/resumen-dia` - Resumen con totales
- `GET /api/ventas/{id}/ticket` - Datos para impresión de ticket
- `POST /api/ventas/{id}/anular` - Anular venta (solo SuperAdmin)

### Modelo de Datos (ventas):
```json
{
  "id": "uuid",
  "numero_venta": "VTA-20260806-0001",
  "origen": "clinica",
  "bodega_id": "uuid",
  "paciente_id": null | "uuid",
  "paciente_nombre": "Cliente General",
  "items": [{ "producto_id", "nombre", "cantidad", "precio_unitario", "descuento", "subtotal", "lotes_consumidos": [] }],
  "subtotal": 150.00,
  "descuento_global": 0,
  "iva": 18.00,
  "total": 168.00,
  "formas_pago": [{ "metodo": "Efectivo", "monto": 168.00 }],
  "efectivo_recibido": 200.00,
  "cambio": 32.00,
  "estado": "completada",
  "fecha": "2026-08-06T...",
  "creado_por": "uuid"
}
```

### Testing:
- Backend: 8/8 tests pasando (`/app/backend/tests/test_ventas_pos.py`)
- Frontend: 100% funcional
- Reporte: `/app/test_reports/iteration_32.json`

---

## Módulos Implementados

### 1. Autenticación y Roles
- **SuperAdmin**: Control total
- **Admin**: Gestión general
- **Usuario**: Solo lectura
- **Óptica**: Solo módulo óptica
- JWT con permisos granulares

### 2. Gastos (Hub Central)
- CRUD gastos manuales/fijos
- Número correlativo (GST-0001)
- Estados: pendiente, parcial, pagado, vencido
- Flujo de autorización SuperAdmin→Admin

### 3. Autorizaciones Pendientes
- Vista exclusiva Admin
- Ejecutar pagos autorizados

### 4. Sala de Operaciones (✅ NUEVO 25/04/2026)
- CRUD completo de cirugías oftalmológicas
- Campos IGSS específicos
- Gestión de equipo e insumos
- Cálculo automático de costos

### 5. Agenda de Pacientes (✅ NUEVO 29/07/2026)
**IMPORTANTE: Separada de la agenda de Sala de Operaciones (tipoAgenda: "pacientes")**

#### Modelo de Datos:
- **medicos**: nombre, especialidad, color, usuario_id (vínculo), activo
- **citas**: paciente, médico, fecha, hora, estado, tipo_cita, hora_llegada, etc.
- **agenda_config**: horarios, slots, tipos de cita configurables

#### Estados de Cita:
Agendada → Confirmada → Presente → En consulta → Atendida / No asistió / Cancelada

#### Vistas Frontend:
1. **Calendario**: Columnas por médico, slots de tiempo, color-coded por estado
2. **Tablero del Día**: Contadores en vivo, lista de citas, panel de presentes por médico
3. **Mi Agenda**: Vista del médico autenticado (vinculado via usuario_id)

#### Endpoints:
- `GET /api/agenda/citas` - Listar citas del día
- `POST /api/agenda/citas` - Crear cita
- `PATCH /api/agenda/citas/:id/estado` - Cambiar estado
- `PATCH /api/agenda/citas/:id/asignar` - Reasignar paciente a otro médico
- `GET /api/agenda/presentes` - Pacientes presentes agrupados por médico
- `GET /api/agenda/mi-dia` - Agenda del médico autenticado
- `POST /api/agenda/walk-in` - Registrar paciente sin cita
- `POST /api/agenda/proxima-cita` - Crear cita desde evaluación

#### Integración con Evaluación Oftalmológica:
- Sección "Próxima Cita" en el formulario
- Checkbox para agendar con médico, fecha, hora, tipo
- Se imprime en las recetas (medicamentos, anteojos, lentes de contacto)

#### Google Calendar:
- Preparado para integración (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
- Campo googleEventId en citas
- Pendiente de credenciales
- Exportación Excel/PDF
- Cancelación con motivo

### 5. Otros Módulos
- Historial de Pagos
- Óptica (inventario, ventas)
- CRM Pacientes
- Configuración

---

## Credenciales de Prueba
Ver `/app/memory/test_credentials.md`

---

## Backlog Actualizado

### P0 (Completado)
- ✅ Módulo Sala de Operaciones
- ✅ Exportación Excel/PDF de cirugías
- ✅ Módulo `routes/surgeries.py` extraído
- ✅ Módulo de Auditoría visual (solo SuperAdmin) - Julio 2026
- ✅ **Módulo de Evaluación Oftalmológica** - Julio 2026
- ✅ **Módulo de Caja** (Caja Diaria, Cuentas por Cobrar, Cierres Financieros) - 29 Julio 2026
- ✅ **Refactorización P0: Pacientes** - 1 Agosto 2026 (routes/patients.py)
- ✅ **Refactorización P1: Evaluaciones** - 1 Agosto 2026 (routes/evaluaciones.py)
- ✅ **Refactorización P1: Cirugías registradas** - 1 Agosto 2026

### P1 (Próximo)
- Extraer módulo de Gastos completo a routes/expenses.py (endpoints)
- Extraer módulo de Óptica a routes/optica.py
- Importación masiva de pacientes (template Excel existe)

### P2 (Futuro)
- Completar refactorización de server.py
- Módulo de Citas
- Extraer módulos: Pacientes, Óptica, Autorizaciones
- Exportar evaluación oftalmológica a PDF

---

## Notas Técnicas

### Módulo de Evaluación Oftalmológica (Nuevo - Julio 2026)
- **Ruta Frontend**: `/evaluacion-oftalmologica`
- **Archivo**: `/app/frontend/src/pages/EvaluacionOftalmologica.js`
- **Permisos**: SuperAdmin y Admin pueden editar, Usuario solo lectura
- **Sellado**: Expedientes se sellan automáticamente 24 horas después de creados
- **Endpoints**:
  - `GET /api/evaluaciones` - Lista con paginación
  - `POST /api/evaluaciones` - Crear nueva
  - `PUT /api/evaluaciones/{id}` - Actualizar (rechaza si sellada)
  - `PATCH /api/evaluaciones/{id}/autoguardar` - Autoguardado parcial
  - `DELETE /api/evaluaciones/{id}` - Eliminar (solo SuperAdmin, no selladas)
  - `GET /api/catalogos/medicamentos` - Autocomplete medicamentos
  - `GET /api/catalogos/estudios` - Autocomplete estudios
  - `GET /api/catalogos/diagnosticos` - Autocomplete diagnósticos
  - `GET /api/pacientes/buscar` - Búsqueda rápida de pacientes
- **Funcionalidades**:
  - Layout de 3 columnas en una sola pantalla
  - Autoguardado con debounce (2.5s)
  - Indicador de tiempo restante para sellado
  - 3 catálogos de autocomplete que se alimentan automáticamente
  - Impresión de 3 tipos de recetas (Medicamentos, Anteojos, Lentes de Contacto)
- **Catálogos precargados**:
  - 21 medicamentos oftalmológicos comunes
  - 22 estudios oftalmológicos
  - 30 diagnósticos oftalmológicos
- **Modelo de datos**: `/app/backend/models/evaluacion_oftalmologica.py`

### Módulo de Caja (Nuevo - 29 Julio 2026)
- **Ruta Frontend**: `/caja`
- **Archivo**: `/app/frontend/src/pages/Caja.js`
- **Modelo Backend**: `/app/backend/models/caja.py`
- **Permisos**: `view_payment_authorizations` (Admin y SuperAdmin)
- **Características**:
  - **Aislamiento total de Óptica**: Todas las transacciones usan `origen: "clinica"`
  - **Caja Diaria**:
    - Apertura de caja con monto inicial
    - Registro de movimientos (ingresos/egresos por categoría)
    - **Método de pago "Cuenta por Cobrar"**: Al seleccionarlo:
      - Requiere seleccionar paciente y tipo de pagador
      - Si es Aseguradora: permite dividir pago entre deducible (caja) y CxC
      - Muestra resumen visual de distribución del pago
    - Cierre de caja con arqueo y diferencia
    - Reapertura de caja solo para SuperAdmin
    - Historial de cierres con impresión
  - **Cuentas por Cobrar (CxC)**:
    - Catálogo de tipos de pagador editable (IGSS, Aseguradora, Particular, Empresa)
    - Crear cuentas por cobrar asociadas a pacientes
    - Registro de abonos con opción de afectar caja diaria
    - Resumen por tipo de pagador
  - **Cierres Financieros**:
    - Cierres mensuales y semestrales
    - Resumen de ingresos, egresos y CxC del período
    - Recálculo de totales
    - Reportes imprimibles
- **Endpoints**:
  - `GET /api/caja/estado` - Estado de caja del día
  - `POST /api/caja/apertura` - Abrir caja
  - `GET/POST/PUT/DELETE /api/caja/movimientos` - CRUD movimientos
  - `POST /api/caja/cierre` - Cerrar caja
  - `GET /api/caja/cierres` - Historial de cierres
  - `POST /api/caja/cierres/{id}/reabrir` - Reabrir caja (SuperAdmin)
  - `GET/POST/PUT/DELETE /api/catalogos/pagadores` - Catálogo pagadores
  - `GET/POST/PUT /api/cxc` - Cuentas por cobrar
  - `POST /api/cxc/{id}/abono` - Registrar abono
  - `GET /api/cxc/resumen` - Resumen CxC por tipo
  - `GET/POST/DELETE /api/cierres-financieros` - Cierres financieros
  - `POST /api/cierres-financieros/{id}/recalcular` - Recalcular cierre

### Módulo de Auditoría (Nuevo - Julio 2026)
- **Ruta Frontend**: `/auditoria`
- **Archivo**: `/app/frontend/src/pages/AuditLogs.js`
- **Permiso**: `view_audit_logs` (solo superadmin)
- **Endpoints**:
  - `GET /api/security/audit-logs` - Logs con paginación y filtros
  - `GET /api/security/audit-actions` - Lista de acciones únicas
  - `GET /api/security/status` - Métricas de seguridad
- **Funcionalidades**:
  - Cards de métricas (total registros, logins fallidos, usuarios activos, tokens revocados)
  - Tabla paginada con filtros por acción, usuario, fechas
  - Búsqueda por usuario, acción o IP

### Importante para Refactorización:
1. Los módulos en `/routes/` ya funcionan pero **no están activos** en producción
2. Para activarlos, se debe:
   - Importar los routers en server.py
   - Usar `app.include_router(router, prefix="/api")` 
   - Eliminar el código duplicado de server.py
3. El módulo `routes/surgeries.py` está **listo para uso** pero no se activó para mantener estabilidad

### Stack Tecnológico
- **Backend**: FastAPI, Motor (MongoDB async), APScheduler
- **Frontend**: React, Tailwind CSS, Shadcn/UI
- **Base de datos**: MongoDB
- **Reportes**: openpyxl (Excel), reportlab (PDF)

---

## Bugs Corregidos

### ✅ P2: Búsqueda de pacientes con tildes/acentos (30 Julio 2026)
- **Problema**: La búsqueda de pacientes fallaba cuando el término contenía tildes (ej: buscar "María" no encontraba resultados)
- **Causa raíz**: Pipeline de MongoDB usaba `$split` con separador vacío (no soportado)
- **Solución**: Se implementó `generate_accent_regex()` que genera clases de caracteres regex `[aáàäâ]` para buscar ignorando diacríticos
- **Endpoints afectados**: `GET /api/patients`, `GET /api/pacientes/buscar`
- **Testing**: 18/18 tests pasaron (pytest), frontend verificado
- **Archivo de tests**: `/app/backend/tests/test_accent_search.py`

---

## Mejoras Implementadas

### ✅ Gastos Fijos - Fecha de inicio completa (31 Julio 2026)
- **Cambio**: El formulario de Gastos Fijos ahora incluye campo "Fecha de inicio del cobro" (día/mes/año completo) además del día del mes
- **Nuevo campo**: `start_date` (YYYY-MM-DD) en modelo `FixedExpense` - Obligatorio
- **Lógica**: La generación automática de gastos solo inicia cuando `fecha_actual >= start_date`
- **UI**: Nueva columna "FECHA INICIO" en tabla de gastos fijos
- **Testing**: 6/6 tests en `/app/backend/tests/test_fixed_expense_start_date.py`

### ✅ Formato de fechas estandarizado dd/mm/yy (31 Julio 2026)
- **Cambio**: Todas las fechas del sistema ahora se muestran en formato `dd/mm/yy` (estándar Guatemala)
- **Archivos actualizados**: 
  - `services/api.js` - formatDate() global
  - `SalaOperaciones.js` - formatDateDisplay()
  - `AuditLogs.js` - formatDate() local (incluye hora: dd/mm/yy HH:mm:ss)
- **Fix adicional**: Se corrigió problema de zona horaria agregando `T00:00:00` a fechas YYYY-MM-DD

### ✅ Auditoría y Sincronización del Flujo Clínico (31 Julio 2026)
- **Documento creado**: `/app/FLOW_AUDIT.md` - Auditoría completa del flujo Cita→Paciente→Evaluación→Óptica→Sala
- **Modelos actualizados**:
  - `Surgery`: Agregados campos `paciente_id` y `evaluacion_id` opcionales para vincular cirugías con pacientes
  - `EvaluacionOftalmologica`: Agregado campo `cita_id` para trazabilidad cita→evaluación
- **Endpoints de integridad** (solo SuperAdmin):
  - `GET /api/admin/integridad-pacientes` - Detecta pacientes sin referencias, referencias huérfanas, duplicados por DPI
  - `GET /api/admin/integridad-datos` - Verifica documentos sin tag origen, catálogos duplicados
- **Testing**: 15/15 tests en `/app/backend/tests/test_dashboard_financiero.py`

### ✅ Dashboard Financiero (31 Julio 2026)
- **Acceso**: Solo SuperAdmin (protegido en frontend y backend)
- **Ruta**: `/dashboard-financiero`
- **KPIs**:
  - Ingresos Cobrados (Caja + Abonos CxC)
  - Gastos Pagados
  - Balance Neto (verde si positivo, rojo si negativo)
  - CxC Pendientes
- **Gráficos** (recharts):
  - Barras: Ingresos vs Gastos mensual (12 meses)
  - Línea: Balance mensual
  - Pie: Ingresos por tipo de pagador
  - Pie: Gastos por categoría
- **Filtros**: Mes actual, Semestre, Anual, Personalizado (fechas)
- **Exportación**: Excel (openpyxl) y PDF (reportlab)
- **Endpoints**:
  - `GET /api/dashboard/financiero` - Datos del dashboard
  - `GET /api/dashboard/financiero/exportar?formato=excel|pdf` - Exportación

---

## 🎨 Tema Visual Global - Azul Celeste e Intenso (Agosto 2026)

### Descripción
La interfaz fue completamente rediseñada con un esquema de colores azul celeste (`sky blue`) y azul intenso (`deep blue`) con degradados modernos.

### Paleta de Colores Implementada
```css
/* Colores Primarios Azul - Azure a Deep Blue */
--blue-900: #1E3A5F;   /* Azul más oscuro */
--blue-800: #1E4D7B;   /* Sidebar background */
--blue-700: #2563EB;   /* Botones primarios */
--blue-600: #3B82F6;   /* Acentos */
--blue-500: #60A5FA;   /* Hover states */
--blue-400: #93C5FD;   /* Bordes activos */
--blue-300: #BFDBFE;   /* Bordes hover */
--blue-200: #DBEAFE;   /* Fondos suaves */
--blue-100: #EFF6FF;   /* Fondos cards */
--blue-50: #F0F9FF;    /* Fondo página */

/* Acentos */
--sky-400: #38BDF8;    /* Celeste brillante */
--sky-300: #7DD3FC;    /* Celeste suave */
--indigo-600: #4F46E5; /* Acentos violeta */
--cyan-400: #22D3EE;   /* Cyan highlights */
```

### Archivos Modificados
- `/app/frontend/src/index.css` - Variables CSS, estilos globales, componentes
- `/app/frontend/src/App.css` - Estilos específicos de la app
- Todos los componentes frontend - Clases Tailwind migradas de `teal-*` a `blue-*`

### Características del Nuevo Tema
1. **Gradientes en Botones**: `linear-gradient(135deg, blue-600 → blue-700 → indigo-600)`
2. **Efecto Glassmorphism**: Login con `backdrop-filter: blur(24px)`
3. **Hover States Modernos**: Transiciones suaves con sombras azules
4. **Sidebar Oscuro**: Gradiente `bg-sidebar: #0F172A → #1E3A5F`
5. **Cards con Sombras Azules**: `box-shadow: rgba(37, 99, 235, 0.12)`

---

## Última Actualización: 7 Agosto 2026

### Cambios Realizados:
1. **Suite de Testing Completa** - Vitest, Playwright, Pytest configurados
2. **Tema UI Azul** - Documentado en PRD
3. **78 tests totales** implementados y pasando

### Refactorización Completada (1 Agosto 2026):
- **P0 - Pacientes**: Extraído a `/app/backend/routes/patients.py` (823 líneas)
  - CRUD completo de pacientes
  - Búsqueda rápida con soporte de tildes
  - Exportación Excel/PDF
  - Importación masiva
- **P1 - Evaluaciones**: Extraído a `/app/backend/routes/evaluaciones.py` (448 líneas)
  - CRUD evaluaciones oftalmológicas
  - Catálogos de autocomplete (medicamentos, estudios, diagnósticos)
  - Autoguardado y sellado automático
- **P1 - Gastos y Pagos**: Extraído a `/app/backend/routes/expenses.py` (640 líneas)
  - CRUD completo de gastos
  - CRUD de pagos
  - Autorizaciones y estados (pendiente, parcial, pagado, vencido)
- **P1 - Óptica**: Extraído a `/app/backend/routes/optica.py` (1322 líneas)
  - CRUD Médicos, Aros, Lentes de contacto, Tipos de lente
  - Ventas con abonos y pagos parciales
  - Compras y Dashboard de óptica
- **P1 - Autorizaciones**: Extraído a `/app/backend/routes/payment_authorizations.py` (401 líneas)
  - CRUD autorizaciones de pago
  - Ejecución y cancelación de autorizaciones
- **server.py reducido**: De ~8000 a **3029 líneas (-62%)**
- **Testing**: Todos los endpoints verificados (8/8 tests)

---

## Historial de Cambios Recientes

### 2026-08-03 - Bug Fix: Cards de Gastos Pendientes mostraban Q0.00
**Problema**: El endpoint `/api/dashboard/upcoming` devolvía error 500 Internal Server Error. Las cards de "Resumen de Montos Pendientes" mostraban Q0.00 en producción.

**Causa Raíz**: El modelo Pydantic `UpcomingPayments` en `server.py` estaba definido incorrectamente con campos `data`, `total`, `total_amount` cuando debería usar `overdue`, `due30`, `due60`. Además, el modelo `AlertResponse` no estaba definido antes de ser usado.

**Solución**:
1. Se agregó el modelo `AlertResponse` en `server.py` (línea 447-458)
2. Se corrigió el modelo `UpcomingPayments` para usar `overdue`, `due30`, `due60`
3. Se eliminó la importación duplicada de `AlertResponse` desde `routes/dashboard.py`

**Archivos modificados**:
- `/app/backend/server.py`

**Verificación**: Las cards ahora muestran correctamente:
- Total Vencido (9): Q 38,467.00
- Por vencer -30 días (0): Q 0.00
- Por vencer 30-60 días (0): Q 0.00

### 2026-08-05 - Bug Fix: SuperAdmin no tenía link a Autorizaciones
**Problema**: El SuperAdmin no podía navegar al módulo de "Autorizaciones de Pago" desde el menú lateral. El link solo estaba visible para Admin.

**Causa Raíz**: En `Layout.js` línea 96, la condición usaba `isAdmin` en lugar de `isAdminOrSuperAdmin`.

**Solución**: Se cambió la condición para que el link de Autorizaciones sea visible para Admin y SuperAdmin.

**Archivo modificado**: `/app/frontend/src/components/Layout.js`

**Verificación via Testing Agent (iteration_31.json)**:
- ✅ Flujo completo de gastos verificado: Crear → Autorizar → Ejecutar pago
- ✅ Cards de Resumen muestran montos correctos (Q 38,467.00 vencidos)
- ✅ Link de Autorizaciones ahora visible para SuperAdmin
- ✅ Historial de pagos registra correctamente
- ✅ Gastos fijos listados (5 items, Q 18,350.00 mensual)


### 2026-08-06 - NUEVO: Módulo de Inventario Completo

**Implementación del módulo de inventario de nivel farmacia/clínica** que incluye:

#### Backend (`/app/backend/routes/inventario.py`, `inventario_ops.py`)
- **Bodegas**: CRUD completo, soporte para puntos de venta
- **Categorías de Productos**: Con iconos Lucide y colores
- **Productos**: 
  - Tipos: producto, servicio, insumo
  - Control de inventario y control de lotes opcional
  - Costo promedio ponderado y último costo
  - Precios de venta con margen calculado
- **Existencias**: Por producto y bodega, matriz de existencias
- **Lotes**: Control de vencimientos, FEFO (First Expired, First Out)
- **Movimientos (Kardex)**: Inmutable, tipos de entrada/salida/ajuste/transferencia
- **Órdenes de Compra**: Estados borrador/enviada/parcial/recibida/cancelada
- **Recepciones**: Parciales y completas, recálculo de costo promedio
- **Transferencias**: Entre bodegas con kardex dual
- **Tomas Físicas**: Flujo guiado con ajustes automáticos
- **Alertas**: Bajo mínimo, próximo vencimiento, vencidos
- **Configuración**: FEFO, existencia negativa, días alerta

#### Frontend (`/app/frontend/src/pages/inventario/`)
- **PanelInventario.js**: Dashboard con KPIs, alertas, gráfica por categoría, acciones rápidas
  - Entrada Rápida: Agregar stock a productos existentes
  - Nueva Orden: Crear orden de compra
  - Nueva Recepción: Recibir mercadería de proveedores
  - Transferencia: Mover entre bodegas
- **Productos.js**: Catálogo con filtros, búsqueda, CRUD completo, botón de entrada rápida por producto
- **Lotes.js**: Vista de vencimientos con código de color, baja de lotes
- **Movimientos.js**: Kardex con filtros avanzados

#### Función para el módulo POS
- `descontarInventario(items, bodega_id, referencia)`: Transaccional, FEFO, genera kardex

#### Seed Data (25 productos)
- 3 Bodegas: General, Dispensario, Quirófano
- 8 Categorías con iconos
- Productos oftalmológicos: gotas, medicamentos, lentes de contacto, accesorios, insumos quirúrgicos, servicios
- 47 Lotes con vencimientos escalonados (vencidos, 30d, 60d, 90d, 180d)
- 2 Órdenes de compra con recepciones
- Movimientos de kardex de ejemplo

#### Colecciones MongoDB
- `bodegas_inventario`
- `categorias_inventario`
- `productos_inventario`
- `existencias_inventario`
- `lotes_inventario`
- `movimientos_inventario`
- `ordenes_compra`
- `recepciones_inventario`
- `transferencias_inventario`
- `tomas_fisicas`
- `config_inventario`

**Todas las colecciones usan `origen: "clinica"` para aislamiento del módulo de óptica.**

#### Menú del Sidebar
Nuevo menú "Inventario" con submenús:
- Panel (Dashboard)
- Productos
- Lotes y Vencimientos
- Kardex (Movimientos)

#### Estado
- ✅ Backend completo y funcionando
- ✅ Frontend implementado
- ✅ Seed data generado
- ✅ KPIs mostrando datos correctos (Q 80,760.63 valor inventario, 25 productos, 47 lotes)
- ⏳ Pendiente: Órdenes de compra UI, Recepciones UI, Transferencias UI, Toma física UI, Reportes


---

## 🧪 Suite de Testing Completa - Implementada 7 Agosto 2026

### Descripción
Suite completa de testing para el sistema NovaVision ERP, que incluye tests unitarios, de integración y end-to-end (E2E).

### Frontend Testing

#### Vitest (Tests Unitarios)
- **Configuración**: `/app/frontend/vitest.config.js`
- **Setup**: `/app/frontend/src/test/setup.js`
- **Utilidades**: `/app/frontend/src/test/utils.js`

**Tests Implementados (58 tests):**
- `Login.test.js`: Validación de credenciales, JWT, roles, rate limiting
- `PuntoVenta.test.js`: Cálculos de venta, pago mixto, FEFO, tickets
- `api.test.js`: Validaciones (DPI, teléfono, email), cálculos financieros

**Comandos:**
```bash
yarn test:unit          # Ejecutar tests
yarn test:unit:watch    # Modo watch
yarn test:unit:coverage # Con cobertura
```

#### Playwright (Tests E2E)
- **Configuración**: `/app/frontend/playwright.config.js`
- **Directorio**: `/app/frontend/tests/e2e/`

**Tests E2E Implementados:**
- `auth.spec.js`: Login, logout, permisos por rol
- `pos.spec.js`: Flujo completo de POS, pago mixto, tickets
- `inventario.spec.js`: Panel, productos, lotes, kardex

**Comandos:**
```bash
yarn test:e2e        # Ejecutar E2E
yarn test:e2e:ui     # Interfaz visual
yarn test:e2e:report # Ver reporte HTML
```

### Backend Testing (Pytest)

- **Configuración**: `/app/backend/pytest.ini`
- **Fixtures**: `/app/backend/tests/conftest.py`

**Tests de Lógica de Negocio (20 tests):**
- `test_inventario_completo.py`:
  - TestLogicaFEFO: Ordenamiento, distribución, stock insuficiente
  - TestCalculosInventario: Costo promedio, margen, punto de reorden
  - TestAlertasVencimiento: Clasificación, días para vencer
  - TestValidaciones: Códigos, cantidades, precios
  - TestKardex: Entradas, salidas, ajustes, inmutabilidad

**Comandos:**
```bash
python -m pytest tests/ -v        # Todos los tests
python -m pytest -m "inventario"  # Por marker
```

### Reportes
- **Vitest**: `/app/test_reports/vitest/results.json`
- **Playwright**: `/app/test_reports/playwright/html/`
- **Pytest**: `/app/test_reports/pytest/`

### Documentación
Ver `/app/memory/TESTING.md` para documentación completa de la suite de testing.

---

## Backlog Actualizado (7 Agosto 2026)

### ✅ Completado
- Suite de Testing (Vitest, Playwright, Pytest)
- Tema UI global azul celeste e intenso
- Módulo POS completo con FEFO
- Pago mixto y tickets térmicos
- Entrada rápida de inventario

### 🟡 P1 (Próximo)
- FEL Guatemala (Facturación Electrónica) - Estructura lista, deshabilitada

### 🟢 P2 (Futuro)
- Importación masiva de pacientes (Excel)
- Exportar evaluación oftalmológica a PDF
- Sincronización Google Calendar
- UI para Órdenes de compra, Recepciones, Transferencias, Toma física
