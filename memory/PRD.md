# PRD - NovaVision ERP Oftalmológico

## Descripción General
Sistema ERP completo para clínicas oftalmológicas con módulos de: Dashboard, Pacientes, Agenda, Evaluación Oftalmológica, Inventario FEFO, POS, Caja, CRM Cirugías, Óptica, y Laboratorio de Pruebas E2E.

## Estado Actual del Proyecto
**Última actualización**: 2026-08-18

### ✅ Funcionalidades Completadas

#### Core
- [x] Autenticación JWT con roles (superadmin, admin, usuario, optica)
- [x] Dashboard con estadísticas y alertas
- [x] Gestión de Pacientes con campos IGSS (NOG, afiliación, unidad, etc.)
- [x] Importación masiva de pacientes (JSON/Excel)
- [x] Plantillas Excel descargables

#### Seguridad (Fase 1 - AppSec)
- [x] Headers de seguridad (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, CSP)
- [x] Rate limiting en login (5 intentos/minuto con bloqueo de 15 min)
- [x] Bcrypt con costo 12 para hashing
- [x] Flag `must_change_password` para usuarios sembrados
- [x] Timeout de inactividad de 30 minutos con advertencia modal
- [x] Token blacklist persistente en MongoDB
- [x] Panel de alertas de seguridad para SuperAdmin

#### Agenda
- [x] Calendario con múltiples médicos
- [x] Creación/edición de citas con campos separados (nombre, apellido, género obligatorio)
- [x] Estados de citas (pendiente, confirmada, en sala, atendida, cancelada)
- [x] WebSocket para actualizaciones en tiempo real (opcional)

#### Evaluación Oftalmológica
- [x] Formulario completo con todas las secciones clínicas
- [x] Soporte offline con LocalStorage
- [x] Autoguardado cada 30 segundos
- [x] Plantilla Excel con variables de evaluación

#### Finanzas
- [x] Módulo Caja con apertura/cierre de sesiones
- [x] Movimientos de ingresos/egresos
- [x] Historial de cierres con arqueo
- [x] WebSocket para actualizaciones en tiempo real (opcional)

#### POS (Punto de Venta)
- [x] Integración con inventario FEFO
- [x] Carrito de compras touch-friendly
- [x] Métodos de pago múltiples
- [x] Bloqueo de ventas con caja cerrada

#### Inventario
- [x] Control de lotes con FEFO (First Expire First Out)
- [x] Multi-almacén
- [x] Kardex inmutable
- [x] Alertas de stock bajo y vencimiento

#### Óptica (Módulo Separado)
- [x] Inventario de aros (`optica_frames`)
- [x] Lentes de contacto (`optica_contact_lenses`)
- [x] Tipos de lente (`optica_lens_types`)
- [x] Ventas de óptica (`optica_sales`) - Colecciones SEPARADAS de clínica
- [x] **NOTA CRÍTICA**: Óptica NO usa Kardex inmutable ni sistema de bodegas

#### CRM Cirugías
- [x] Pipeline de seguimiento de pacientes quirúrgicos
- [x] Estados configurables

#### Laboratorio de Pruebas E2E (NUEVO)
- [x] Panel accesible solo para SuperAdmin en ambiente de desarrollo
- [x] Seed de Datos Maestros (Fase 1): Bodegas, Proveedores, Productos, Usuarios, Médicos
- [x] Seed de Pacientes (Fase 2): 14 pacientes con perfiles específicos
- [x] Función de Purga: Elimina todos los datos con `esDatoPrueba: true`
- [x] Ruta en frontend: `/laboratorio-pruebas`
- [x] Bloqueo en producción vía `NODE_ENV`/`ENVIRONMENT`

#### Optimizaciones
- [x] GZIP Middleware
- [x] Headers de caché para assets estáticos
- [x] Índices compuestos en MongoDB
- [x] ErrorBoundary global en React
- [x] Performance tests (scripts en /backend/scripts/)

### 🔄 En Progreso
- [x] WebSockets para Caja y Agenda - **COMPLETADO** (2026-08-17)
- [x] Laboratorio de Pruebas E2E - **COMPLETADO** (2026-08-18)
  - ✅ Fase 0: Documentación de precondiciones en `INFORME_PRUEBAS_E2E.md`
  - ✅ Fase 1: Seed de datos maestros funcionando
  - ✅ Fase 2: Seed de pacientes funcionando
  - ✅ Fase 3: 9 Recorridos E2E automatizados
  - ✅ Fase 4: 50 pruebas de verificación (100% PASA)
  - ✅ Fase 5: Pruebas de volumen y rendimiento
  - ✅ Fase 6: Generación de informe automático
  - ✅ Fase 7: Función de purga funcionando

### 📋 Backlog (Próximas Tareas)

#### P1 - Alta Prioridad
- [ ] **FEL Guatemala**: Estructura de Facturación Electrónica (deshabilitada con `FEL_ENABLED=false`)

#### P2 - Media Prioridad
- [ ] **PDF Evaluaciones**: Exportar evaluación oftalmológica completa a PDF
- [ ] **Google Calendar**: Sincronización activa en módulo Agenda

#### P3 - Baja Prioridad
- [ ] Indicador visual de estado de WebSocket en UI
- [ ] Refactorización de `server.py` (extraer inicialización de índices MongoDB)

## Arquitectura Técnica

### Backend
- FastAPI con routers modulares en `/routes/`
- MongoDB con índices compuestos
- WebSocket ConnectionManager en `server.py`
- JWT para autenticación

### Frontend
- React con hooks personalizados
- Shadcn/UI components
- LocalStorage para modo offline
- WebSocket opcional (funciona sin él)

### Estructura de Archivos Clave
```
/app/
├── backend/
│   ├── server.py                # Main + WebSocket Manager
│   ├── routes/
│   │   ├── caja.py
│   │   ├── agenda.py
│   │   ├── patients.py
│   │   ├── laboratorio_pruebas.py  # NUEVO: Endpoints QA E2E
│   ├── seed/                    # NUEVO: Generadores de datos de prueba
│   │   ├── __init__.py
│   │   ├── datos_maestros.py
│   │   ├── pacientes.py
│   └── scripts/
│       ├── performance_test.py
│       ├── generar_plantilla_*.py
├── frontend/
│   ├── src/
│   │   ├── hooks/useWebSocket.js
│   │   ├── hooks/useInactivityTimeout.js  # NUEVO: Timeout 30 min
│   │   ├── components/
│   │   │   ├── ErrorBoundary.js
│   │   │   ├── InactivityWarning.js  # NUEVO: Modal advertencia
│   │   │   ├── Layout.js
│   │   ├── pages/
│   │       ├── Caja.js
│   │       ├── Agenda.js
│   │       ├── LaboratorioPruebas.js  # NUEVO: Panel QA E2E
│   └── public/
│       ├── plantilla_*.xlsx
├── docs/                        # NUEVO: Documentación de seguridad
│   ├── SECURITY_AUDIT.md
│   ├── SECURITY_REMEDIATION_PLAN.md
│   ├── SECURITY_BASELINE.md
├── INFORME_PRUEBAS_E2E.md       # NUEVO: Reporte de auditoría QA
```

## Credenciales de Prueba
Ver `/app/memory/test_credentials.md`

## Endpoints WebSocket
- `ws://{host}/ws/caja?token={jwt}`
- `ws://{host}/ws/agenda?token={jwt}`
- `ws://{host}/ws/pos?token={jwt}`

## Notas Importantes
- WebSocket puede no funcionar en entornos preview sin soporte WSS
- Índices MongoDB envueltos en try/except para evitar `IndexSpecsConflict`
- FEL debe mantenerse deshabilitado hasta implementación completa
