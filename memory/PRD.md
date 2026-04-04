# NovaVision — Sistema de Gastos y Finanzas
## Product Requirements Document

### Última actualización: 2026-04-04

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
| POST | /api/expenses | Crear gasto nuevo |
| PUT | /api/expenses/:id | Editar gasto |
| DELETE | /api/expenses/:id | Eliminar gasto |

**Query params para GET /api/expenses:**
- `page`, `limit` - Paginación
- `type` - fijo|proveedor|variable
- `status` - pendiente|parcial|pagado|vencido
- `search` - Busca en name e invoiceNumber
- `dateFrom`, `dateTo` - Rango de fechas
- `sortBy`, `sortOrder` - Ordenamiento

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

---

## 4. Usuarios Seed

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| superadmin | nova2024 | Super Admin |
| admin | admin2024 | Administrador |
| usuario | user2024 | Usuario |

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

---

## 6. URLs

- **Frontend**: https://novavision-finanzas.preview.emergentagent.com
- **API**: https://novavision-finanzas.preview.emergentagent.com/api

---

## 7. Tareas Pendientes

### P2 - Mejoras
- [ ] Cron job para actualizar automáticamente gastos vencidos en DB
- [ ] Refactorización de `server.py` (separar modelos, rutas, servicios)

### Backlog
- [ ] Módulo de reportes gráficos avanzados
- [ ] Notificaciones push/email para autorizaciones pendientes


