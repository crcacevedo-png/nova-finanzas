# Guía de Refactorización - NovaVision Backend

## Estado Actual

El archivo `server.py` tiene **5385 líneas** con la siguiente estructura:

```
Líneas 1-54:     Imports y configuración
Líneas 55-199:   Sistema de Permisos (PERMISSIONS)
Líneas 200-863:  Modelos Pydantic
Líneas 864-996:  Helpers de Autenticación y Gastos
Líneas 997-1451: Seed de Usuarios y Datos Iniciales
Líneas 1452-1600: Rutas de Auth y Users
Líneas 1601-1763: Rutas de Gastos
Líneas 1764-1900: Rutas de Pagos
Líneas 1901-2112: Rutas de Dashboard
Líneas 2113-2195: Rutas de Cuentas Bancarias
Líneas 2196-2297: Rutas de Proveedores
Líneas 2298-2451: Rutas de Gastos Fijos
Líneas 2452-2548: Rutas de Unidades IGSS
Líneas 2549-3273: Rutas de Pacientes
Líneas 3274-4078: Rutas de Óptica (Inventario, Ventas, Lentes)
Líneas 4079-4458: Dashboard y Reportes de Óptica
Líneas 4459-4622: Rutas de Compras de Óptica
Líneas 4623-4945: Rutas de Autorizaciones de Pago
Líneas 4946-5236: Rutas de Reportes
Líneas 5237-5385: Scheduler de Gastos Fijos
```

## Estructura de Directorios Creada

```
/app/backend/
├── config/
│   ├── __init__.py
│   ├── database.py      ✅ Configuración de MongoDB y JWT
│   └── permissions.py   ✅ Sistema de permisos por rol
├── models/
│   ├── __init__.py
│   ├── expense.py       ✅ Modelos de gastos (referencia)
│   ├── optica.py        ✅ Modelos de óptica (referencia)
│   ├── patient.py       ✅ Modelos de pacientes (referencia)
│   ├── supplier.py      ✅ Modelos de proveedores (referencia)
│   └── user.py          ✅ Modelos de usuarios (referencia)
├── routes/
│   ├── __init__.py      ✅ Exporta helpers compartidos
│   ├── auth.py          ✅ Rutas de autenticación y usuarios
│   └── expenses.py      ✅ Helpers y modelos de gastos
├── services/
│   └── __init__.py
├── utils/
│   ├── __init__.py
│   └── auth.py
├── tests/
│   ├── test_expense_number.py
│   ├── test_fixed_expenses.py
│   ├── test_optica.py
│   ├── test_patients.py
│   └── test_payment_authorizations.py
├── requirements.txt
└── server.py            ← Punto de entrada principal (5385 líneas)
```

## Plan de Migración Gradual

### Fase 1 - Completada ✅
- Extraer configuración a `/config/database.py` y `/config/permissions.py`
- Crear estructura base de rutas en `/routes/auth.py` y `/routes/expenses.py`

### Fase 2 - Pendiente
- Migrar rutas de Pagos a `/routes/payments.py`
- Migrar rutas de Dashboard a `/routes/dashboard.py`
- Migrar rutas de Cuentas Bancarias a `/routes/bank_accounts.py`

### Fase 3 - Pendiente
- Migrar rutas de Proveedores a `/routes/suppliers.py`
- Migrar rutas de Gastos Fijos a `/routes/fixed_expenses.py`
- Migrar rutas de Unidades IGSS a `/routes/igss_units.py`

### Fase 4 - Pendiente
- Migrar rutas de Pacientes a `/routes/patients.py`
- Migrar rutas de Óptica a `/routes/optica.py`
- Migrar rutas de Reportes a `/routes/reports.py`

### Fase 5 - Pendiente
- Migrar rutas de Autorizaciones a `/routes/payment_authorizations.py`
- Actualizar `server.py` para importar todos los routers
- Limpieza final y testing

## Notas Importantes

1. **No romper la aplicación**: `server.py` sigue siendo funcional durante la migración
2. **Migración gradual**: Cada módulo se migra y prueba individualmente
3. **Compatibilidad**: Los archivos en `/routes/` y `/models/` sirven como referencia
4. **Testing**: Ejecutar tests después de cada fase de migración

## Comandos Útiles

```bash
# Contar líneas por sección
grep -n "# =.*=" /app/backend/server.py

# Verificar estado del backend
tail -f /var/log/supervisor/backend.err.log

# Reiniciar backend
sudo supervisorctl restart backend

# Ejecutar tests
cd /app/backend && python -m pytest tests/ -v
```
