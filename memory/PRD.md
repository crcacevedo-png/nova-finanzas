# NovaVision — Sistema de Gastos y Finanzas
## Product Requirements Document

### Fecha de Creación: 2026-03-27

---

## 1. Problema Original
Construir una aplicación web completa llamada "NovaVision — Sistema de Gastos y Finanzas" para una clínica oftalmológica con:
- Autenticación multiusuario con JWT
- Manejo de roles (Superadmin, Admin, Usuario)
- Módulos para registrar gastos
- Control de pagos y alertas de vencimiento
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

### Estructura
```
/app/
├── backend/
│   ├── server.py          # API FastAPI completa
│   └── .env               # Configuración
├── frontend/
│   ├── src/
│   │   ├── context/       # AuthContext
│   │   ├── pages/         # Login, Register, Dashboard, Gastos, Usuarios
│   │   ├── components/    # Layout, UI components
│   │   └── services/      # API helpers
│   └── .env
└── memory/
    └── PRD.md
```

---

## 3. User Personas

### Superadmin
- Acceso total al sistema
- Gestión de usuarios (crear, activar/desactivar, eliminar)
- Gestión completa de gastos
- Vista de dashboard y reportes

### Admin
- Gestión de gastos
- Vista de dashboard y reportes
- Sin acceso a gestión de usuarios

### Usuario
- Registro y consulta de gastos
- Vista de dashboard

---

## 4. Core Requirements (Implementados)

### ✅ Autenticación
- Registro de usuarios con validación
- Login con JWT (24h expiration)
- Primer usuario automáticamente superadmin
- Rutas protegidas por rol

### ✅ Dashboard Financiero
- Total de gastos
- Pagos pendientes y pagados
- Desglose por categoría (Gastos Fijos, Proveedores, Variables)
- Alertas de vencimiento a 30 y 60 días
- Gráficas de barras y pie chart

### ✅ Módulo de Gastos
- CRUD completo de gastos
- Campos: Concepto, Monto, Fecha, Categoría, Estado, Vencimiento, Proveedor, Notas
- Filtros por categoría y estado
- Búsqueda por concepto/proveedor

### ✅ Gestión de Usuarios (Superadmin)
- Crear nuevos usuarios con rol
- Activar/Desactivar usuarios
- Eliminar usuarios

---

## 5. Implementación Completada

| Feature | Status | Fecha |
|---------|--------|-------|
| Backend API completa | ✅ | 2026-03-27 |
| Autenticación JWT | ✅ | 2026-03-27 |
| Dashboard con métricas | ✅ | 2026-03-27 |
| Alertas 30/60 días | ✅ | 2026-03-27 |
| CRUD Gastos | ✅ | 2026-03-27 |
| Gestión Usuarios | ✅ | 2026-03-27 |
| Tema teal profesional | ✅ | 2026-03-27 |
| Responsive design | ✅ | 2026-03-27 |

---

## 6. Backlog Priorizado

### P0 - Crítico
- [x] MVP completo implementado

### P1 - Alta Prioridad
- [ ] Exportar reportes a PDF/Excel
- [ ] Notificaciones por email de vencimientos
- [ ] Historial de cambios/auditoría

### P2 - Media Prioridad
- [ ] Gráficas de tendencia mensual/anual
- [ ] Presupuestos por categoría
- [ ] Integración con contabilidad externa

### P3 - Baja Prioridad
- [ ] Dark mode
- [ ] App móvil
- [ ] Multi-tenant (múltiples clínicas)

---

## 7. Credenciales de Prueba

- **Usuario**: admin@novavision.gt
- **Contraseña**: admin123
- **Rol**: Superadmin

---

## 8. URLs

- **Frontend**: https://novavision-finanzas.preview.emergentagent.com
- **API Base**: https://novavision-finanzas.preview.emergentagent.com/api
