# NovaVision — Sistema de Gastos y Finanzas
## Product Requirements Document

### Última actualización: 2026-03-27

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

### Dashboard / Reportes
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/dashboard/summary | Resumen del mes actual |
| GET | /api/dashboard/monthly-chart | Gastos últimos 6 meses |
| GET | /api/dashboard/upcoming | Pagos próximos (overdue/due30/due60) |
| GET | /api/reports/expenses | Exportar (xlsx/csv) |

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
- ✅ Exportación a Excel y PDF
- ✅ UI responsive con Tailwind + Shadcn
- ✅ **Rediseño P0 del Frontend (Sección 6):**
  - ✅ Sidebar oscuro (slate-900)
  - ✅ Nueva página: Historial de Pagos
  - ✅ Nueva página: Pagos por Vencer
- ✅ **Rediseño TEAL SERENIDAD (Diciembre 2025):**
  - ✅ Nueva paleta de colores Teal (#0F6E56, #1D9E75)
  - ✅ Login con glassmorphism y gradiente animado
  - ✅ Sidebar oscuro (#0C2E2A) con logo transparente
  - ✅ Logo NovaVision sin marco (transparente)
  - ✅ Badges de tipo: fijo=azul, proveedor=teal, variable=ámbar
  - ✅ Badges de estado: pendiente, parcial, pagado, vencido
  - ✅ Badges de rol: superadmin, admin, usuario
  - ✅ Métricas con colores azul/teal/ámbar/rojo
  - ✅ Barras de progreso por tipo con colores específicos
  - ✅ Alertas de vencimiento 30/60 días
  - ✅ Rate limiting (5 intentos/minuto en login)
  - ✅ Tipografía Plus Jakarta Sans

---

## 6. URLs

- **Frontend**: https://novavision-finanzas.preview.emergentagent.com
- **API**: https://novavision-finanzas.preview.emergentagent.com/api

---

## 7. Tareas Pendientes (P1)

- [ ] Exportación a PDF en `/api/reports/expenses`
- [ ] Cron job/tarea para actualizar automáticamente gastos vencidos
- [ ] Refactorización de `server.py` (separar modelos, rutas, servicios)


