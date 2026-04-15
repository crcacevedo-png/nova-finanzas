# NovaVision — Sistema de Gastos y Finanzas
## Product Requirements Document

### Última actualización: 2026-04-15

---

## 1. Endpoints API Implementados

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /api/auth/login | Iniciar sesión (devuelve JWT + user info) |
| POST | /api/auth/logout | Cerrar sesión (invalida token) |
| GET | /api/auth/me | Obtener usuario autenticado |

### Usuarios (SuperAdmin)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/users | Listar todos los usuarios |
| GET | /api/users/:id | Obtener usuario por ID |
| POST | /api/users | Crear usuario nuevo |
| PUT | /api/users/:id | Editar usuario |
| DELETE | /api/users/:id | Eliminar usuario |

### Gastos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/expenses | Listar con filtros y paginación |
| GET | /api/expenses/:id | Obtener gasto con pagos asociados |
| POST | /api/expenses | Crear gasto nuevo (genera número correlativo automático) |
| PUT | /api/expenses/:id | Editar gasto |
| DELETE | /api/expenses/:id | Eliminar gasto |

**Query params para GET /api/expenses:**
- `page`, `limit` - Paginación
- `type` - fijo|proveedor|variable
- `status` - pendiente|parcial|pagado|vencido
- `search` - Busca en name e invoiceNumber
- `dateFrom`, `dateTo` - Rango de fechas
- `sortBy`, `sortOrder` - Ordenamiento

**Número Correlativo (expense_number):**
- Formato: GST-XXXX (4 dígitos con ceros a la izquierda)
- Se genera automáticamente al crear un gasto usando MongoDB counters collection
- Operación atómica con find_one_and_update para evitar duplicados

### Pagos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/payments | Listar pagos con filtros |
| GET | /api/payments/:id | Detalle de un pago |
| POST | /api/payments | Registrar pago |
| DELETE | /api/payments/:id | Eliminar pago |

### Cuentas Bancarias (SuperAdmin)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/bank-accounts | Listar cuentas bancarias |
| GET | /api/bank-accounts/:id | Detalle de cuenta |
| POST | /api/bank-accounts | Crear cuenta bancaria |
| PUT | /api/bank-accounts/:id | Editar cuenta |
| DELETE | /api/bank-accounts/:id | Eliminar cuenta |

### Autorización de Pagos (SuperAdmin/Admin)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/payment-authorizations | Listar autorizaciones (filtro ?status=) |
| GET | /api/payment-authorizations/:id | Detalle de autorización |
| GET | /api/expenses-pending-authorization | Gastos disponibles para autorizar (SuperAdmin) |
| POST | /api/payment-authorizations | Crear autorización (SuperAdmin) |
| PUT | /api/payment-authorizations/:id | Editar autorización pendiente (SuperAdmin) |
| POST | /api/payment-authorizations/:id/execute | Ejecutar pago autorizado (Admin) |
| POST | /api/payment-authorizations/:id/cancel | Cancelar autorización (SuperAdmin) |
| DELETE | /api/payment-authorizations/:id | Eliminar autorización (SuperAdmin) |

### Gastos Fijos Recurrentes (Admin/SuperAdmin)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/fixed-expenses | Listar gastos fijos |
| GET | /api/fixed-expenses/:id | Detalle de gasto fijo |
| POST | /api/fixed-expenses | Crear gasto fijo |
| PUT | /api/fixed-expenses/:id | Editar gasto fijo |
| DELETE | /api/fixed-expenses/:id | Eliminar gasto fijo (soft delete) |
| POST | /api/fixed-expenses/generate-now | Generar gastos del día (solo SuperAdmin) |

### Pacientes (Base de Datos de Pacientes)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/patients | Listar con filtros y paginación |
| GET | /api/patients/:id | Detalle de paciente |
| POST | /api/patients | Crear paciente |
| PUT | /api/patients/:id | Editar paciente |
| DELETE | /api/patients/:id | Desactivar paciente (soft delete) |
| POST | /api/patients/:id/reactivate | Reactivar paciente |
| GET | /api/patients/search?q= | Búsqueda para autocompletado |
| GET | /api/patients/check-duplicate | Verificar duplicados por DPI o nombre |
| GET | /api/patients/export/excel | Exportar a Excel |
| GET | /api/patients/export/pdf | Exportar a PDF |
| GET | /api/patients/export/template | Descargar plantilla de importación |

**Query params para GET /api/patients:**
- `page`, `limit` - Paginación
- `search` - Busca en nombre, apellido, DPI, teléfono, expediente
- `referral_institution` - particular|igss|seguro_privado|otra
- `igss_unit_id` - Filtro por unidad IGSS
- `gender` - masculino|femenino|otro
- `age_from`, `age_to` - Rango de edad
- `dateFrom`, `dateTo` - Rango de fecha de registro
- `is_active` - true|false

### Unidades IGSS (Catálogo - Solo SuperAdmin)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/igss-units | Listar unidades IGSS |
| GET | /api/igss-units/:id | Detalle de unidad |
| POST | /api/igss-units | Crear unidad IGSS |
| PUT | /api/igss-units/:id | Editar unidad |
| DELETE | /api/igss-units/:id | Eliminar unidad |

### Módulo Óptica (Solo optica y superadmin)

#### Médicos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/doctors | Listar médicos |
| GET | /api/doctors/:id | Detalle de médico |
| POST | /api/doctors | Crear médico |
| PUT | /api/doctors/:id | Editar médico |
| DELETE | /api/doctors/:id | Eliminar médico |
| GET | /api/doctors/search?q= | Búsqueda para autocompletado |

#### Inventario de Aros
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/optica/frames | Listar aros con filtros |
| GET | /api/optica/frames/:id | Detalle de aro |
| POST | /api/optica/frames | Crear aro |
| PUT | /api/optica/frames/:id | Editar aro |
| DELETE | /api/optica/frames/:id | Eliminar aro |
| GET | /api/optica/frames/search?q= | Búsqueda para autocompletado |

#### Lentes de Contacto
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/optica/contact-lenses | Listar lentes de contacto |
| POST | /api/optica/contact-lenses | Crear lente de contacto |
| PUT | /api/optica/contact-lenses/:id | Editar lente de contacto |
| DELETE | /api/optica/contact-lenses/:id | Eliminar lente de contacto |

#### Tipos de Lente (Catálogo)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/optica/lens-types | Listar tipos de lente |
| POST | /api/optica/lens-types | Crear tipo de lente |
| PUT | /api/optica/lens-types/:id | Editar tipo de lente |
| DELETE | /api/optica/lens-types/:id | Eliminar tipo de lente |

#### Ventas de Óptica
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/optica/sales | Listar ventas con filtros |
| GET | /api/optica/sales/:id | Detalle de venta |
| POST | /api/optica/sales | Crear venta |
| GET | /api/optica/sales/pending | Ventas con saldo pendiente |
| POST | /api/optica/sales/:id/payments | Registrar abono |
| PUT | /api/optica/sales/:id/cancel | Cancelar venta |

### Dashboard / Reportes
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/dashboard/summary | Resumen del mes actual |
| GET | /api/dashboard/monthly-chart | Gastos últimos 6 meses |
| GET | /api/dashboard/upcoming | Pagos próximos (overdue/due30/due60) |
| GET | /api/reports/expenses | Exportar (xlsx/csv/pdf) |

---

## 2. Esquema de Base de Datos

### Users
```json
{
  "id": "uuid",
  "username": "string (unique)",
  "password": "bcrypt hash",
  "name": "string",
  "role": "superadmin|admin|usuario",
  "is_active": "boolean",
  "last_login": "datetime",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Expenses
```json
{
  "id": "uuid",
  "expense_number": "string (GST-XXXX, auto-generado)",
  "provider": "string|null",
  "name": "string",
  "type": "fijo|proveedor|variable",
  "amount": "number",
  "date": "datetime",
  "due_date": "datetime|null",
  "invoice_number": "string|null",
  "status": "pendiente|parcial|pagado|vencido",
  "notes": "string",
  "paid_amount": "number (calculado)",
  "remaining_amount": "number (calculado)",
  "created_by": "user_id",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Counters (para números correlativos)
```json
{
  "_id": "expense_number",
  "seq": "number (último número usado)"
}
```

### Payments
```json
{
  "id": "uuid",
  "expense_id": "expense_id",
  "amount": "number",
  "date": "datetime",
  "method": "Efectivo|Transferencia|Tarjeta crédito|Tarjeta débito|Cheque",
  "reference": "string|null",
  "notes": "string",
  "created_by": "user_id",
  "created_at": "datetime"
}
```

### Bank Accounts
```json
{
  "id": "uuid",
  "bank_name": "string",
  "account_number": "string",
  "account_alias": "string",
  "is_active": "boolean",
  "created_by": "user_id",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Payment Authorizations
```json
{
  "id": "uuid",
  "expense_id": "expense_id",
  "bank_account_id": "bank_account_id",
  "amount_to_pay": "number",
  "status": "pendiente|ejecutado|cancelado",
  "notes": "string",
  "authorized_by": "user_id",
  "authorized_at": "datetime",
  "executed_by": "user_id|null",
  "executed_at": "datetime|null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Fixed Expenses (Gastos Fijos)
```json
{
  "id": "uuid",
  "supplier_id": "supplier_id",
  "expense_name": "string",
  "amount": "number",
  "day_of_month": "int (1-31)",
  "is_active": "boolean",
  "created_by": "user_id",
  "created_at": "datetime",
  "updated_at": "datetime",
  "last_generated": "string (YYYY-MM) | null"
}
```

### Patients (Pacientes)
```json
{
  "id": "uuid",
  "record_number": "string (EXP-YYYYMM-XXXX)",
  "first_name": "string",
  "last_name": "string",
  "gender": "masculino|femenino|otro",
  "birth_date": "date (YYYY-MM-DD)",
  "profession": "string|null",
  "phone": "string",
  "email": "string|null",
  "dpi": "string (13 dígitos)|null",
  "emergency_phone": "string|null",
  "emergency_contact_name": "string|null",
  "emergency_contact_relationship": "string|null",
  "referral_institution": "particular|igss|seguro_privado|otra",
  "insurance_name": "string|null (si seguro_privado)",
  "other_institution_name": "string|null (si otra)",
  "igss_unit_id": "igss_unit_id|null (si igss)",
  "comments": "string|null",
  "is_active": "boolean",
  "created_by": "user_id",
  "created_at": "datetime",
  "updated_by": "user_id|null",
  "updated_at": "datetime"
}
```
**Nota:** La edad se calcula dinámicamente a partir de birth_date (no se almacena).

### IGSS Units (Unidades IGSS)
```json
{
  "id": "uuid",
  "name": "string",
  "code": "string|null",
  "description": "string|null",
  "is_active": "boolean",
  "created_by": "user_id",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 3. Sistema de Permisos

| Permiso | SuperAdmin | Admin | Usuario |
|---------|:----------:|:-----:|:-------:|
| Ver dashboard | ✅ | ✅ | ✅ |
| Ver gastos | ✅ | ✅ | ✅ |
| Ver historial pagos | ✅ | ✅ | ✅ |
| Crear gastos | ✅ | ✅ | ❌ |
| Editar gastos | ✅ | ✅ | ❌ |
| Eliminar gastos | ✅ | ❌ | ❌ |
| Registrar pagos | ✅ | ✅ | ❌ |
| Eliminar pagos | ✅ | ❌ | ❌ |
| Gestionar usuarios | ✅ | ❌ | ❌ |
| Exportar reportes | ✅ | ✅ | ❌ |
| **Autorizar pagos** | ✅ | ❌ | ❌ |
| **Ver autorizaciones** | ✅ | ✅ | ❌ |
| **Ejecutar autorizaciones** | ❌ | ✅ | ❌ |
| **Ver pacientes** | ✅ | ✅ | ✅ |
| **Crear pacientes** | ✅ | ✅ | ❌ |
| **Editar pacientes** | ✅ | ✅ | ❌ |
| **Desactivar pacientes** | ✅ | ❌ | ❌ |
| **Gestionar unidades IGSS** | ✅ | ❌ | ❌ |
| **Importar/Exportar pacientes** | ✅ | ✅ | ❌ |

---

## 4. Usuarios Seed

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| superadmin | nova2024 | Super Admin |
| admin | admin2024 | Administrador |
| usuario | user2024 | Usuario |
| optica | optica2024 | Óptica |

---

## 5. Features Implementadas

- ✅ API REST completa con todos los endpoints
- ✅ Autenticación JWT con logout
- ✅ Sistema de permisos granular
- ✅ Paginación y filtros avanzados
- ✅ Pagos parciales con cálculo automático
- ✅ Dashboard con métricas y alertas
- ✅ Exportación a Excel, CSV y PDF
- ✅ UI responsive con Tailwind + Shadcn
- ✅ **Rediseño TEAL SERENIDAD:**
  - ✅ Nueva paleta de colores Teal (#0F6E56, #1D9E75)
  - ✅ Login con glassmorphism y gradiente animado
  - ✅ Sidebar oscuro (#0C2E2A) con logo transparente
  - ✅ Badges de tipo, estado y rol
  - ✅ Rate limiting (5 intentos/minuto en login)
  - ✅ Tipografía Plus Jakarta Sans
- ✅ **Módulo Cuentas Bancarias (SuperAdmin):**
  - ✅ CRUD completo de cuentas bancarias
  - ✅ Acceso exclusivo SuperAdmin
- ✅ **Módulo Autorización de Pagos (Abril 2026):**
  - ✅ SuperAdmin crea autorizaciones (selecciona gasto + cuenta bancaria)
  - ✅ Admin ejecuta autorizaciones (genera pago real)
  - ✅ Estados: pendiente, ejecutado, cancelado
  - ✅ Vista diferenciada por rol
  - ✅ Filtro por estado
  - ✅ Historial completo de autorizaciones
  - ✅ Tests automatizados (100% backend, 100% frontend)
- ✅ **Módulo Gastos Fijos Recurrentes (Abril 2026):**
  - ✅ CRUD completo de gastos fijos (proveedor, nombre, monto, día del mes)
  - ✅ Vinculación con proveedores existentes (selector dinámico)
  - ✅ Acceso para Admin y SuperAdmin
  - ✅ APScheduler para generación automática diaria (00:05)
  - ✅ Generación manual con botón "Generar Ahora" (solo SuperAdmin)
  - ✅ Prevención de duplicados (campo last_generated)
  - ✅ Gastos generados con vencimiento automático +30 días
  - ✅ Tests automatizados (100% backend, 100% frontend)
- ✅ **Módulo Base de Datos de Pacientes (Abril 2026):**
  - ✅ CRUD completo (crear, listar, ver detalle, editar, desactivar/reactivar)
  - ✅ Campos: nombre, apellido, género, fecha nacimiento, profesión, teléfono, email, DPI (13 dígitos único)
  - ✅ Contacto de emergencia (nombre, parentesco, teléfono)
  - ✅ Institución referente con campos condicionales (IGSS→Unidad, Seguro→Aseguradora, Otra→Nombre)
  - ✅ Número de expediente correlativo automático (EXP-YYYYMM-XXXX)
  - ✅ Edad calculada dinámicamente (no almacenada en BD)
  - ✅ Detección de duplicados (por DPI o nombre+fecha nacimiento)
  - ✅ Soft delete con posibilidad de reactivar
  - ✅ Exportación a Excel y PDF con filtros
  - ✅ Plantilla descargable para importación
  - ✅ Endpoint de búsqueda para autocompletado (/api/patients/search)
  - ✅ Paginación y filtros avanzados
  - ✅ Permisos: SuperAdmin (total), Admin (CRUD sin eliminar), Usuario (solo lectura)
  - ✅ Tests automatizados (100% backend, 100% frontend)
- ✅ **Catálogo de Unidades IGSS (Abril 2026):**
  - ✅ CRUD completo para unidades del IGSS
  - ✅ Acceso exclusivo SuperAdmin
  - ✅ Validación de uso antes de eliminar (pacientes asociados)
  - ✅ Catálogo inicia vacío, administrable desde el panel
- ✅ **Módulo Óptica - Fase 1 (Abril 2026):**
  - ✅ Nuevo rol `optica` con permisos específicos
  - ✅ Acceso exclusivo para roles `optica` y `superadmin`
  - ✅ Submenú colapsable en sidebar con 4 secciones
  - ✅ **Base de Médicos:** CRUD completo (nombre, especialidad, licencia, teléfono, email)
  - ✅ **Inventario de Aros:** CRUD (marca, código, modelo, color, costo, venta, stock)
  - ✅ **Catálogo Tipos de Lente:** CRUD administrable (nombre, descripción, costo, precio venta)
  - ✅ **Ventas de Óptica:** 
    - ✅ Crear venta con búsqueda de paciente (conectado a tabla patients)
    - ✅ Selección de médico referente (opcional)
    - ✅ Agregar aro desde inventario
    - ✅ Agregar tipos de lente con cantidad y precio editable
    - ✅ Descuento porcentual
    - ✅ Pago inicial y abonos posteriores
    - ✅ Estados: pendiente, pagado, cancelado
  - ✅ Dashboard de cards con métricas (stock, valor inventario, ventas totales, saldo pendiente)
  - ✅ Seed data: 4 médicos, 6 aros, 7 tipos de lente
  - ✅ Tests automatizados (100% backend, 100% frontend)
- ✅ **Módulo Óptica - Fase 2 (Abril 2026):**
  - ✅ **Dashboard de Ventas Óptica:**
    - ✅ Métricas: Ventas del mes, Cobrado mes, Saldo pendiente, Órdenes mes, Pendientes
    - ✅ Gráfico de barras: Ventas últimos 6 meses (con Recharts)
    - ✅ Top 3 Médicos por ventas
    - ✅ Top 3 Marcas de Aros por ventas
  - ✅ **Exportar Informe Mensual:**
    - ✅ Modal con selector de año y mes
    - ✅ Exportar a Excel (.xlsx) con formato profesional
    - ✅ Exportar a PDF con tabla de ventas
  - ✅ Endpoints backend: `/api/optica/dashboard/stats`, `/api/optica/dashboard/monthly-chart`, `/api/optica/dashboard/top-doctors`, `/api/optica/dashboard/top-brands`, `/api/optica/reports/monthly`
- ✅ **Número Correlativo Automático en Gastos (Abril 2026):**
  - ✅ Generación automática al crear gasto (formato GST-XXXX)
  - ✅ Secuencia atómica usando colección MongoDB `counters`
  - ✅ Campo `expense_number` en modelos ExpenseResponse, PaymentResponse, PaymentAuthorizationResponse
  - ✅ Columna "No." visible en tabla de Gastos (antes de Proveedor)
  - ✅ Columna "No." visible en Autorización de Pagos (ambas vistas)
  - ✅ Columna "No." visible en Historial de Pagos
  - ✅ Gastos anteriores muestran "-" (compatibilidad retroactiva)
  - ✅ **Gastos Fijos generados automáticamente también reciben correlativo**
  - ✅ Tests automatizados (100% backend, 100% frontend)

---

## 6. URLs

- **Frontend**: https://novavision-finanzas.preview.emergentagent.com
- **API**: https://novavision-finanzas.preview.emergentagent.com/api

---

## 7. Tareas Pendientes

### P1 - Mejoras Óptica
- [ ] Inventario de Lentes de Contacto (UI similar a Aros)
- [ ] Submódulo de "Gastos de Óptica" (usando proveedores globales)

### P2 - Mejoras Generales
- [ ] Refactorización de `server.py` (separar modelos, rutas, servicios - archivo tiene 5000+ líneas)
- [ ] Importación masiva de pacientes desde Excel/CSV

### Backlog
- [ ] Módulo de reportes gráficos avanzados
- [ ] Notificaciones push/email para autorizaciones pendientes
- [ ] Módulo de Citas médicas (debe usar tabla patients)
- [ ] Vista de detalle del paciente con pestañas de historial (Óptica, Citas, etc.)
