# NovaVision ERP - Suite de Testing

## Descripción General

Suite completa de testing para el sistema NovaVision ERP, que incluye tests unitarios, de integración y end-to-end (E2E).

---

## Estructura de Directorios

```
/app/
├── frontend/
│   ├── vitest.config.js          # Configuración de Vitest
│   ├── playwright.config.js      # Configuración de Playwright
│   ├── src/
│   │   ├── test/
│   │   │   ├── setup.js          # Setup global de Vitest
│   │   │   └── utils.js          # Utilidades de testing
│   │   ├── pages/__tests__/
│   │   │   ├── Login.test.js     # Tests del módulo Login
│   │   │   └── PuntoVenta.test.js # Tests del POS
│   │   └── services/__tests__/
│   │       └── api.test.js       # Tests de utilidades API
│   └── tests/e2e/
│       ├── auth.spec.js          # Tests E2E de autenticación
│       ├── pos.spec.js           # Tests E2E del POS
│       └── inventario.spec.js    # Tests E2E de inventario
├── backend/
│   ├── pytest.ini                # Configuración de pytest
│   └── tests/
│       ├── conftest.py           # Fixtures centralizadas
│       ├── test_inventario_completo.py  # Tests de lógica de inventario
│       ├── test_ventas_pos.py    # Tests del POS
│       └── [otros tests existentes...]
└── test_reports/
    ├── vitest/                   # Reportes de Vitest
    ├── playwright/               # Reportes de Playwright
    └── pytest/                   # Reportes de pytest
```

---

## Frontend Testing

### Vitest (Tests Unitarios)

**Tecnologías:**
- Vitest 1.6.0
- @testing-library/react 14.3.1
- @testing-library/jest-dom 6.4.6
- @testing-library/user-event 14.5.2
- jsdom 24.1.0

**Comandos:**

```bash
# Ejecutar todos los tests unitarios
cd /app/frontend
yarn test:unit

# Ejecutar en modo watch
yarn test:unit:watch

# Con interfaz visual
yarn test:unit:ui

# Con cobertura de código
yarn test:unit:coverage
```

**Tests Implementados:**

1. **Login.test.js** (16 tests)
   - Validación de credenciales
   - Manejo de Token JWT
   - Roles y permisos
   - Validación de contraseña
   - Rate limiting

2. **PuntoVenta.test.js** (18 tests)
   - Cálculos de venta (subtotal, IVA, total)
   - Pago mixto
   - Productos rápidos
   - Número de venta correlativo
   - Validación de stock
   - Estados de venta
   - Ticket de impresión

3. **api.test.js** (24 tests)
   - Formato de fechas
   - Formato de moneda (GTQ)
   - Validaciones (DPI, teléfono, email)
   - Cálculos financieros (IVA 12%)
   - Descuentos
   - Lógica FEFO

**Total: 58 tests unitarios**

---

### Playwright (Tests E2E)

**Tecnologías:**
- Playwright 1.44.1

**Configuración:**
- Browsers: Chromium, Firefox, WebKit
- Dispositivos móviles: Pixel 5, iPhone 12
- Tablet: iPad Pro 11 (importante para POS táctil)

**Comandos:**

```bash
# Ejecutar tests E2E
cd /app/frontend
yarn test:e2e

# Con interfaz visual
yarn test:e2e:ui

# En modo debug
yarn test:e2e:debug

# Ver reporte HTML
yarn test:e2e:report
```

**Tests E2E Implementados:**

1. **auth.spec.js**
   - Página de login visible
   - Login exitoso con superadmin
   - Error con credenciales inválidas
   - Logout funcional
   - Manejo de token expirado
   - Permisos por rol

2. **pos.spec.js**
   - Acceso a página de POS
   - Productos disponibles
   - Productos rápidos
   - Agregar al carrito
   - Resumen de venta
   - Métodos de pago
   - Pago mixto
   - Impresión de tickets

3. **inventario.spec.js**
   - Panel de inventario
   - KPIs del inventario
   - Alertas de stock/vencimiento
   - Navegación a submenús
   - Lista de productos
   - Búsqueda de productos
   - Entrada rápida
   - Lotes y vencimientos
   - Kardex (movimientos)

---

## Backend Testing

### Pytest

**Tecnologías:**
- pytest 9.0.2
- pytest-asyncio 1.4.0
- httpx (para tests async)

**Comandos:**

```bash
# Ejecutar todos los tests
cd /app/backend
python -m pytest

# Tests específicos
python -m pytest tests/test_inventario_completo.py -v

# Por marker
python -m pytest -m "inventario" -v

# Con reporte detallado
python -m pytest --tb=long -v
```

**Tests de Lógica de Negocio (test_inventario_completo.py) - 20 tests:**

1. **TestLogicaFEFO**
   - Ordenamiento FEFO
   - Descuento de lote único
   - Distribución en múltiples lotes
   - Detección de stock insuficiente
   - Filtrado de lotes vencidos

2. **TestCalculosInventario**
   - Costo promedio ponderado
   - Valor total de inventario
   - Margen de utilidad
   - Punto de reorden

3. **TestAlertasVencimiento**
   - Clasificación por proximidad
   - Cálculo de días para vencer

4. **TestValidaciones**
   - Código de producto único
   - Cantidades positivas
   - Precio vs costo
   - Formato de código de lote

5. **TestKardex**
   - Entrada suma existencia
   - Salida resta existencia
   - Ajuste positivo
   - Ajuste negativo
   - Inmutabilidad de movimientos

**Tests de API Existentes (test_ventas_pos.py) - 8 tests:**
- Bodega POS
- Búsqueda de productos
- Ventas del día
- Productos rápidos
- Verificación de stock
- Creación de venta
- Resumen del día
- Datos de ticket

---

## Markers de Pytest

```python
# Disponibles en pytest.ini
@pytest.mark.slow        # Tests lentos
@pytest.mark.integration # Tests de integración
@pytest.mark.e2e         # Tests end-to-end
@pytest.mark.auth        # Tests de autenticación
@pytest.mark.pos         # Tests del Punto de Venta
@pytest.mark.inventario  # Tests de inventario
```

---

## Credenciales de Testing

Ver `/app/memory/test_credentials.md`

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| Super Admin | superadmin | nova2024 |
| Admin | admin | Admin2024Nuevo! |
| Usuario | usuario | user2024 |
| Óptica | optica | optica2024 |

---

## Reportes

Los reportes se generan en `/app/test_reports/`:

- **Vitest**: `/app/test_reports/vitest/results.json`
- **Playwright**: `/app/test_reports/playwright/html/` y `results.json`
- **Pytest**: `/app/test_reports/pytest/*.xml`

---

## Ejecutar Todos los Tests

```bash
# Frontend (unitarios + E2E)
cd /app/frontend && yarn test:all

# Backend
cd /app/backend && python -m pytest

# Total de tests configurados:
# - Frontend Unitarios: 58
# - Frontend E2E: ~30 (depende de browser)
# - Backend: 20+ (lógica de negocio) + tests de API existentes
```

---

## Notas Importantes

1. **Rate Limiting**: El backend tiene rate limiting (5 requests/minuto en login). Los tests de API usan fixtures con scope="module" para evitar esto.

2. **Datos de Prueba**: Los tests de lógica de negocio no requieren conexión a la API/DB.

3. **FEFO**: La lógica First Expire First Out está completamente testeada en `test_inventario_completo.py`.

4. **IVA Guatemala**: Todos los cálculos usan 12% de IVA.

5. **Formato de Fecha**: Estándar Guatemala `dd/mm/yy`.

---

## Última Actualización: 7 Agosto 2026
