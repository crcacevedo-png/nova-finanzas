# NovaVision - Sistema de Gastos y Finanzas
## Clínica Oftalmológica

---

## Descripción General
Sistema web completo para gestión financiera de clínica oftalmológica. Base de datos: MongoDB. Moneda: Quetzales (GTQ).

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
2. **expenses.py** - ✅ CRUD gastos + pagos completo (640 líneas, 1 Agosto 2026)
3. **payments.py** - (Incluido en expenses.py)
4. **dashboard.py** - Dashboard y estadísticas
5. **bank_accounts.py** - Cuentas bancarias (modelos, rutas en server.py)
6. **suppliers.py** - Proveedores
7. **fixed_expenses.py** - Gastos fijos
8. **igss_units.py** - Unidades IGSS
9. **surgeries.py** - ✅ CRUD completo + reportes Excel/PDF (806 líneas)
10. **caja.py** - Módulo de Caja completo (29 Julio 2026)
11. **agenda.py** - Módulo de Agenda de Pacientes
12. **admin.py** - ✅ Endpoints de integridad y administración (1 Agosto 2026)
13. **dashboard_financiero.py** - ✅ Dashboard exclusivo SuperAdmin (1 Agosto 2026)
14. **patients.py** - ✅ CRUD completo de pacientes + búsqueda (823 líneas, 1 Agosto 2026)
15. **evaluaciones.py** - ✅ Evaluaciones oftalmológicas + catálogos (480 líneas, 1 Agosto 2026)

### 🟡 Módulos Pendientes de Extracción:
1. **Óptica** (~1200 líneas) - Inventario, ventas, compras, médicos
2. **Autorizaciones de pago** (~350 líneas)
3. **Cuentas bancarias (rutas)** (~100 líneas) - Modelos ya extraídos
4. **Reportes generales** (~200 líneas)

### 📊 Progreso de Refactorización:
- **Antes (Julio 2026)**: server.py ~8000 líneas
- **Después (1 Agosto 2026)**: server.py ~4978 líneas
- **Reducción total**: ~3022 líneas extraídas (~38%)
- **Módulos extraídos**: patients.py (823), evaluaciones.py (480), surgeries.py (806), expenses.py (640)
- **Routers activos**: 16 módulos en `/routes/`

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

## Última Actualización: 1 Agosto 2026

### Refactorización Completada (1 Agosto 2026):
- **P0 - Pacientes**: Extraído a `/app/backend/routes/patients.py` (823 líneas)
  - CRUD completo de pacientes
  - Búsqueda rápida con soporte de tildes
  - Exportación Excel/PDF
  - Importación masiva
- **P1 - Evaluaciones**: Extraído a `/app/backend/routes/evaluaciones.py` (480 líneas)
  - CRUD evaluaciones oftalmológicas
  - Catálogos de autocomplete (medicamentos, estudios, diagnósticos)
  - Autoguardado y sellado automático
- **P1 - Cirugías**: Router registrado correctamente en server.py
- **P1 - Gastos y Pagos**: Extraído a `/app/backend/routes/expenses.py` (640 líneas)
  - CRUD completo de gastos
  - CRUD de pagos
  - Autorizaciones y estados (pendiente, parcial, pagado, vencido)
- **server.py reducido**: De ~8000 a ~4978 líneas (-38%)
- **Testing**: 100% éxito en iteraciones 26-27
