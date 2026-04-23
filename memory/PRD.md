# NovaVision - Sistema de Gastos y Finanzas
## Clínica Oftalmológica

---

## Descripción General
Sistema web completo para gestión financiera de clínica oftalmológica. Base de datos: MongoDB. Moneda: Quetzales (GTQ).

---

## Arquitectura

```
/app/
├── backend/
│   ├── server.py              # API principal FastAPI (5500+ líneas)
│   ├── config/                # database.py, permissions.py
│   ├── routes/                # Archivos base para refactorización futura
│   ├── models/                
│   └── utils/                 
├── frontend/
│   └── src/
│       ├── App.js             
│       ├── components/
│       │   ├── Layout.js      # Sidebar con permisos por rol
│       ├── pages/
│       │   ├── Gastos.js      # Hub central de gastos y autorizaciones
│       │   ├── AutorizacionesPendientes.js  # Vista Admin para ejecutar pagos
│       │   ├── HistorialPagos.js
│       │   └── (Otras páginas...)
│       └── services/
│           └── api.js         # Servicios API y utilidades (formatDate, formatCurrency)
```

---

## Módulos Implementados

### 1. Autenticación y Roles
- **SuperAdmin**: Control total, autoriza gastos
- **Admin**: Ejecuta pagos autorizados, gestión general
- **Optica**: Solo módulo de óptica
- JWT con permisos granulares

### 2. Gastos (Hub Central)
- CRUD de gastos manuales y fijos
- Número correlativo automático (GST-0001, GST-0002...)
- Estados: pendiente, parcial, pagado, vencido
- Dashboard de montos pendientes integrado
- **Flujo de Autorización**:
  1. SuperAdmin selecciona gasto → Clic "Autorizar" → Modal selección cuenta bancaria
  2. Se crea automáticamente autorización de pago para Admin
  3. Gasto se marca verde (is_authorized: true)

### 3. Autorizaciones Pendientes (Solo Admin)
- Ruta: `/autorizaciones-pendientes`
- Lista autorizaciones pendientes de ejecución
- Filtros por estado (pendiente, ejecutado, cancelado)
- Botón "Ejecutar" crea el pago real
- Muestra: No. Gasto, nombre, proveedor, monto, cuenta bancaria

### 4. Historial de Pagos
- Registro completo de pagos ejecutados
- Filtros por fecha, método de pago
- Exportación Excel/PDF

### 5. Módulo Óptica
- Inventario de productos
- Ventas con pagos parciales
- Compras a proveedores
- Tipos de lente

### 6. CRM Pacientes
- Base de datos de pacientes
- Historial médico básico

### 7. Configuración
- Cuentas bancarias
- Proveedores
- Usuarios

---

## Cambios Recientes (Abril 2026)

### Sesión Actual
1. ✅ **Autorización directa**: Al autorizar gasto, se crea automáticamente la autorización de pago (eliminado paso "Confirmar Autorizaciones")
2. ✅ **Eliminado sidebar "Autorizaciones" para SuperAdmin**: Solo visible para Admin
3. ✅ **Corregido bug N/A en autorizaciones**: Frontend ahora usa campos planos (expense_name, bank_account_alias) en lugar de objetos anidados
4. ✅ **Formato de fecha corregido**: Ahora es día/mes/año (DD/MM/YYYY) en todo el sistema

### Sesión Anterior
- Número correlativo automático para gastos (GST-XXXX)
- Búsqueda mejorada de gastos (por proveedor, nombre, número)
- Eliminación de módulos independientes "Pagos por Vencer" y "Autorización de Pagos"
- Dashboard movido a página de Gastos
- Refactorización Fase 1-3 (estructura base en /routes/)

---

## Endpoints Clave

### Gastos
- `POST /api/expenses/{id}/authorize` - Autoriza gasto y crea payment_authorization
- `GET /api/expenses` - Lista gastos con filtros

### Autorizaciones de Pago
- `GET /api/payment-authorizations` - Lista autorizaciones (filtro por status)
- `POST /api/payment-authorizations/{id}/execute` - Admin ejecuta pago
- `POST /api/payment-authorizations/{id}/cancel` - SuperAdmin cancela

### Pagos
- `GET /api/payments` - Historial de pagos
- `POST /api/payments` - Registrar pago manual

---

## Credenciales de Prueba
Ver `/app/memory/test_credentials.md`

---

## Backlog

### P1 (Próximas)
- Importación masiva de pacientes
- Búsqueda de pacientes insensible a tildes/acentos

### P2 (Futuras)
- Refactorización completa de server.py → /routes/
- Módulo de Citas
- Notificaciones de autorizaciones pendientes

---

## Stack Tecnológico
- **Backend**: FastAPI, Motor (MongoDB async), APScheduler
- **Frontend**: React, Tailwind CSS, Shadcn/UI
- **Base de datos**: MongoDB (Atlas en producción)
- **Autenticación**: JWT

---

## URLs
- **Preview**: https://novavision-finanzas.preview.emergentagent.com
- **Producción**: https://novavision-finanzas.emergent.host
