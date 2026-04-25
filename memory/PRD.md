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
│   ├── server.py              # API principal FastAPI (6500+ líneas)
│   ├── config/                # database.py, permissions.py
│   ├── routes/                # Archivos base para refactorización futura
│   ├── models/                
│   ├── tests/                 # Tests pytest (test_surgeries.py, etc.)
│   └── utils/                 
├── frontend/
│   └── src/
│       ├── App.js             
│       ├── components/
│       │   ├── Layout.js      # Sidebar con permisos por rol
│       ├── pages/
│       │   ├── Gastos.js      # Hub central de gastos y autorizaciones
│       │   ├── AutorizacionesPendientes.js  # Vista Admin para ejecutar pagos
│       │   ├── SalaOperaciones.js           # Módulo de cirugías (NUEVO)
│       │   ├── HistorialPagos.js
│       │   └── (Otras páginas...)
│       └── services/
│           └── api.js         # Servicios API y utilidades (formatDate, formatCurrency)
```

---

## Módulos Implementados

### 1. Autenticación y Roles
- **SuperAdmin**: Control total, autoriza gastos, cancela/elimina cirugías
- **Admin**: Ejecuta pagos autorizados, gestión general, crea/edita cirugías
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

### 7. Sala de Operaciones (NUEVO - 25 Abril 2026)
- Ruta: `/sala-operaciones`
- **CRUD completo de cirugías oftalmológicas**
- Campos: fecha, hora, paciente, procedimiento, cirujano, ojo (OD/OI/AO), tipo anestesia, anestesiólogo, institución
- **Datos IGSS**: unidad, SPS, número afiliación, código procedimiento, costo
- **Equipo utilizado**: lista de equipos con cantidad
- **Insumos**: con categorías (lente, medicamento, material, descartable, sutura, viscoelástico, otro), cantidad, costo unitario, costo total
- **Cálculo de costos**: Costo procedimiento + Total insumos = Total general
- **Cancelación de cirugías**: con motivo y opción de reagendamiento
- **Exportación**: Excel y PDF con filtros
- **Permisos**: Admin puede crear/editar, SuperAdmin puede eliminar/cancelar

### 8. Configuración
- Cuentas bancarias
- Proveedores
- Usuarios

---

## Cambios Recientes (Abril 2026)

### Sesión 25 Abril 2026
1. ✅ **Módulo Sala de Operaciones completo**: CRUD de cirugías, equipo, insumos, exportación Excel/PDF
2. ✅ **Corrección de permisos**: Cambiado `manage_expenses` a `create_expenses`/`edit_expenses` para Admin
3. ✅ **Testing completo**: 22/22 tests backend + validación frontend (iteration_14.json)

### Sesión Anterior
1. ✅ **Autorización directa**: Al autorizar gasto, se crea automáticamente la autorización de pago
2. ✅ **Eliminado sidebar "Autorizaciones" para SuperAdmin**: Solo visible para Admin
3. ✅ **Corregido bug N/A en autorizaciones**: Frontend ahora usa campos planos
4. ✅ **Formato de fecha corregido**: Ahora es día/mes/año (DD/MM/YYYY)

---

## Endpoints Clave

### Gastos
- `POST /api/expenses/{id}/authorize` - Autoriza gasto y crea payment_authorization
- `GET /api/expenses` - Lista gastos con filtros

### Autorizaciones de Pago
- `GET /api/payment-authorizations` - Lista autorizaciones (filtro por status)
- `POST /api/payment-authorizations/{id}/execute` - Admin ejecuta pago
- `POST /api/payment-authorizations/{id}/cancel` - SuperAdmin cancela

### Cirugías (NUEVO)
- `GET /api/surgeries` - Lista cirugías con filtros
- `POST /api/surgeries` - Registrar nueva cirugía
- `PUT /api/surgeries/{id}` - Editar cirugía
- `DELETE /api/surgeries/{id}` - Eliminar (solo SuperAdmin)
- `POST /api/surgeries/{id}/cancel` - Cancelar con motivo
- `POST /api/surgeries/{id}/equipment` - Agregar equipo
- `DELETE /api/surgeries/{id}/equipment/{eq_id}` - Eliminar equipo
- `POST /api/surgeries/{id}/supplies` - Agregar insumo
- `DELETE /api/surgeries/{id}/supplies/{sup_id}` - Eliminar insumo
- `GET /api/reports/surgeries?format=xlsx|pdf` - Exportar a Excel/PDF

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
- **Reportes**: openpyxl (Excel), reportlab (PDF)

---

## URLs
- **Preview**: https://novavision-finanzas.preview.emergentagent.com
- **Producción**: https://novavision-finanzas.emergent.host
