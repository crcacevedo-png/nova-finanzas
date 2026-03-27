# NovaVision — Sistema de Gastos y Finanzas
## Product Requirements Document

### Última actualización: 2026-03-27

---

## 1. Problema Original
Construir una aplicación web completa llamada "NovaVision — Sistema de Gastos y Finanzas" para una clínica oftalmológica con:
- Autenticación multiusuario con JWT (8 horas de sesión)
- Manejo de roles (Superadmin, Admin, Usuario)
- Sistema de permisos granular
- Módulos para registrar gastos con pagos parciales
- Control de pagos y alertas de vencimiento (30/60 días)
- Dashboard financiero
- Base de datos MongoDB
- Moneda: Quetzales (GTQ)
- Idioma: Español

---

## 2. Arquitectura Implementada

### Stack Tecnológico
- **Frontend**: React 19 con Tailwind CSS y Shadcn UI
- **Backend**: FastAPI (Python)
- **Base de datos**: MongoDB con Motor (async)
- **Autenticación**: JWT con bcrypt
- **Gráficas**: Recharts

### Esquema de Base de Datos

#### Users
```
{
  id: string (UUID)
  username: string (unique, lowercase)
  password: string (bcrypt hash)
  name: string
  role: "superadmin" | "admin" | "usuario"
  is_active: boolean
  last_login: datetime
  created_at: datetime
  updated_at: datetime
}
```

#### Expenses (Gastos)
```
{
  id: string (UUID)
  name: string
  type: "fijo" | "proveedor" | "variable"
  amount: number (total en GTQ)
  date: datetime
  due_date: datetime | null
  invoice_number: string | null
  status: "pendiente" | "parcial" | "pagado" | "vencido"
  notes: string
  paid_amount: number (calculado)
  remaining_amount: number (calculado)
  created_by: string (user_id)
  created_at: datetime
  updated_at: datetime
}
```

#### Payments (Pagos)
```
{
  id: string (UUID)
  expense_id: string (referencia a expense)
  amount: number
  date: datetime
  method: "Efectivo" | "Transferencia bancaria" | "Tarjeta de crédito" | "Tarjeta de débito" | "Cheque"
  reference: string | null
  notes: string
  created_by: string (user_id)
  created_at: datetime
}
```

---

## 3. Sistema de Permisos

| Permiso | SuperAdmin | Admin | Usuario |
|---------|:----------:|:-----:|:-------:|
| Ver dashboard | ✅ | ✅ | ✅ |
| Ver gastos | ✅ | ✅ | ✅ |
| Ver historial de pagos | ✅ | ✅ | ✅ |
| Ver pagos por vencer | ✅ | ✅ | ✅ |
| Crear gastos | ✅ | ✅ | ❌ |
| Editar gastos | ✅ | ✅ | ❌ |
| Eliminar gastos | ✅ | ❌ | ❌ |
| Registrar pagos | ✅ | ✅ | ❌ |
| Eliminar pagos | ✅ | ❌ | ❌ |
| Gestionar usuarios | ✅ | ❌ | ❌ |
| Ver gestión de usuarios | ✅ | ❌ | ❌ |
| Exportar reportes | ✅ | ✅ | ❌ |

---

## 4. Usuarios Seed

| Usuario | Contraseña | Nombre | Rol |
|---------|-----------|--------|-----|
| superadmin | nova2024 | Administrador General | superadmin |
| admin | admin2024 | Administrador | admin |
| usuario | user2024 | Usuario NovaVision | usuario |

---

## 5. Implementación Completada

| Feature | Status | Fecha |
|---------|--------|-------|
| Backend API con nuevo esquema | ✅ | 2026-03-27 |
| Sistema de permisos granular | ✅ | 2026-03-27 |
| Login con username | ✅ | 2026-03-27 |
| Usuarios seed | ✅ | 2026-03-27 |
| Dashboard con 4 estados (pendiente/parcial/pagado/vencido) | ✅ | 2026-03-27 |
| Alertas 30/60 días | ✅ | 2026-03-27 |
| CRUD Gastos con nuevo esquema | ✅ | 2026-03-27 |
| Sistema de pagos parciales | ✅ | 2026-03-27 |
| Historial de pagos por gasto | ✅ | 2026-03-27 |
| Barra de progreso de pagos | ✅ | 2026-03-27 |
| Gestión de Usuarios | ✅ | 2026-03-27 |
| Logo NovaVision actualizado | ✅ | 2026-03-27 |

---

## 6. Backlog Priorizado

### P0 - Crítico
- [x] MVP completo implementado

### P1 - Alta Prioridad
- [ ] Exportar reportes a PDF/Excel
- [ ] Detección automática de gastos vencidos (cron job)

### P2 - Media Prioridad
- [ ] Gráficas de tendencia mensual/anual
- [ ] Presupuestos por categoría
- [ ] Notificaciones email

### P3 - Baja Prioridad
- [ ] Dark mode
- [ ] App móvil

---

## 7. URLs

- **Frontend**: https://novavision-finanzas.preview.emergentagent.com
- **API Base**: https://novavision-finanzas.preview.emergentagent.com/api

