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
2. **expenses.py** - CRUD gastos manuales
3. **payments.py** - CRUD pagos
4. **dashboard.py** - Dashboard y estadísticas
5. **bank_accounts.py** - Cuentas bancarias
6. **suppliers.py** - Proveedores
7. **fixed_expenses.py** - Gastos fijos
8. **igss_units.py** - Unidades IGSS
9. **surgeries.py** - CRUD completo + reportes Excel/PDF
10. **caja.py** - ✅ NEW: Módulo de Caja completo (29 Julio 2026)
    - Caja Diaria (apertura, movimientos, cierre, reapertura SuperAdmin)
    - Cuentas por Cobrar (CRUD, abonos, estados de cuenta)
    - Cierres Financieros (mensuales/semestrales)
    - Catálogo de Pagadores

### 🟡 Módulos Pendientes de Extracción:
1. **Pacientes** (~600 líneas) - Incluye importación/exportación masiva
2. **Óptica** (~1200 líneas) - Inventario, ventas, compras, médicos
3. **Autorizaciones de pago** (~350 líneas)
4. **Reportes generales** (~400 líneas)
5. **Evaluaciones Oftalmológicas** (~600 líneas)

### 📊 Progreso de Refactorización:
- **Antes**: server.py ~8800 líneas
- **Después de Caja**: server.py ~7800 líneas
- **Extraído**: ~3500 líneas (en `/routes/`)
- **Pendiente**: ~4300 líneas

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

### P1 (Próximo)
- Importación masiva de pacientes
- Búsqueda de pacientes insensible a tildes

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

## Última Actualización: 29 Julio 2026
