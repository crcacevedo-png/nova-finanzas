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
9. **surgeries.py** - ✅ NEW: CRUD completo + reportes Excel/PDF

### 🟡 Módulos Pendientes de Extracción:
1. **Pacientes** (~600 líneas) - Incluye importación/exportación masiva
2. **Óptica** (~1200 líneas) - Inventario, ventas, compras, médicos
3. **Autorizaciones de pago** (~350 líneas)
4. **Reportes generales** (~400 líneas)

### 📊 Progreso de Refactorización:
- **Antes**: server.py ~6500 líneas
- **Extraído**: ~2500 líneas (en `/routes/`)
- **Pendiente**: ~4000 líneas

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

### P1 (Próximo)
- Importación masiva de pacientes
- Búsqueda de pacientes insensible a tildes

### P2 (Futuro)
- Completar refactorización de server.py
- Módulo de Citas
- Extraer módulos: Pacientes, Óptica, Autorizaciones

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

## Última Actualización: 28 Julio 2026
