# INFORME DE PRUEBAS END-TO-END - NOVAVISION ERP
## Auditoría de Calidad y Trazabilidad del Sistema

**Fecha de Inicio:** 2026-08-18  
**Versión del Sistema:** 1.0  
**Auditor:** Sistema de QA Automatizado  

---

# FASE 0 — INVENTARIO DE PRECONDICIONES

## 1. RESUMEN DE MÓDULOS

| Módulo | Estado | Colecciones | Endpoints | Observaciones |
|--------|--------|-------------|-----------|---------------|
| Autenticación | ✅ COMPLETO | users, audit_logs, token_blacklist, security_alerts | /api/auth/* | JWT + roles |
| Pacientes | ✅ COMPLETO | patients | /api/patients/* | Con campos IGSS |
| Agenda | ✅ COMPLETO | citas, medicos_agenda | /api/agenda/* | WebSocket integrado |
| Evaluación Oftalmológica | ✅ COMPLETO | evaluaciones_oftalmologicas, catalogos_diagnosticos, catalogos_* | /api/evaluaciones/* | Sello 24h, offline |
| Caja | ✅ COMPLETO | caja_movimientos, caja_cierres | /api/caja/* | origen: "clinica" |
| Inventario Clínica | ✅ COMPLETO | productos_inventario, lotes_inventario, movimientos_kardex, bodegas_inventario | /api/inventario/* | FEFO, origen: "clinica" |
| Ventas POS | ✅ COMPLETO | ventas, tickets_espera | /api/ventas/* | IVA 12%, correlativos |
| Gastos | ✅ COMPLETO | expenses, expense_payments, fixed_expenses | /api/expenses/* | Autorización de pagos |
| Cirugías | ✅ COMPLETO | surgeries | /api/surgeries/* | Kanban, campos IGSS |
| Surgery CRM | ✅ COMPLETO | surgery_crm | /api/surgery-crm/* | Pipeline quirúrgico |
| **Óptica** | ✅ COMPLETO | optica_sales, optica_frames, optica_contact_lenses, optica_lens_types, optica_sale_payments, doctors | /api/optica/* | **Colecciones separadas** |
| Dashboard Financiero | ✅ COMPLETO | (usa otras colecciones) | /api/dashboard-financiero/* | Analítica |

---

## 2. ANÁLISIS DETALLADO DEL MÓDULO DE ÓPTICA

### 2.1 Arquitectura de Separación

**HALLAZGO CRÍTICO - Arquitectura Mixta:**

El módulo de óptica utiliza un modelo de **colecciones separadas**, NO el campo `origen` como filtro:

| Aspecto | Clínica | Óptica | ¿Compartido? |
|---------|---------|--------|--------------|
| Ventas | `ventas` | `optica_sales` | ❌ No |
| Productos | `productos_inventario` (origen: "clinica") | `optica_frames`, `optica_contact_lenses` | ❌ No |
| Movimientos inventario | `movimientos_kardex` | NO TIENE (stock directo en producto) | ❌ No |
| Caja/Pagos | `caja_movimientos` | `optica_sale_payments` | ❌ No |
| Pacientes | `patients` | `patients` | ✅ **Sí** |
| Correlativos | VTA-YYYYMMDD-XXXX | ORD-YYYYMM-XXXX | ❌ Separados |

### 2.2 Puntos de Riesgo Identificados

1. **⚠️ RIESGO: Óptica NO tiene Kardex inmutable**
   - El stock se actualiza directamente en `optica_frames.stock` y `optica_contact_lenses.stock`
   - NO hay trazabilidad de movimientos como en el inventario clínico
   - Esto viola el principio de inmutabilidad del Prompt 19

2. **⚠️ RIESGO: Óptica NO se integra con Caja**
   - Los pagos van a `optica_sale_payments`, NO a `caja_movimientos`
   - El cierre de caja de la clínica NO incluye ventas de óptica (esto es CORRECTO)
   - PERO: No hay mecanismo de cierre/arqueo para óptica

3. **⚠️ RIESGO: Recetas de lentes NO llegan a Óptica**
   - Las evaluaciones generan recetas de lentes en `evaluaciones_oftalmologicas`
   - El módulo de óptica NO consulta estas recetas
   - NO hay campos `pacienteId`, `evaluacionId`, `recetaId` en `optica_sales`

4. **✅ CORRECTO: Aislamiento de datos financieros**
   - Las ventas de óptica NO aparecen en reportes de clínica
   - Los correlativos son series independientes
   - Los dashboards están separados

### 2.3 Bodegas

| Código | Nombre | Origen | esPuntoVenta |
|--------|--------|--------|--------------|
| (auto) | Bodegas en `bodegas_inventario` | clinica | Varía |
| N/A | Óptica usa stock directo en productos | - | - |

**HALLAZGO: Óptica NO usa el sistema de bodegas**
- No hay bodega con `origen: "optica"`
- El inventario de óptica (aros, lentes de contacto) maneja stock directamente en cada documento

---

## 3. COLECCIONES POR MÓDULO

### 3.1 Autenticación y Seguridad
```
- users: Usuarios del sistema
- audit_logs: Bitácora de auditoría
- token_blacklist: Tokens revocados
- security_alerts: Alertas de seguridad
```

### 3.2 Pacientes
```
- patients: Registro de pacientes (compartido clínica/óptica)
  Campos IGSS: igss_unidad, igss_afiliacion, igss_no_sps, igss_codigo, igss_nog, igss_tipo_compra
```

### 3.3 Agenda
```
- citas: Citas médicas
- medicos_agenda: Médicos con sus colores de agenda
```

### 3.4 Evaluación Oftalmológica
```
- evaluaciones_oftalmologicas: Historias clínicas
- catalogo_diagnosticos: Diagnósticos (autocompletado)
- catalogo_medicamentos: Medicamentos de receta
- catalogo_cirugias: Tipos de cirugías
- catalogo_lentes: Tipos de lentes
```

### 3.5 Inventario Clínica
```
- bodegas_inventario: Bodegas (origen: "clinica")
- productos_inventario: Productos (origen: "clinica")
- lotes_inventario: Lotes con vencimiento
- movimientos_kardex: Kardex inmutable (origen: "clinica")
- alertas_inventario: Alertas de stock/vencimiento
- config_inventario: Configuración
```

### 3.6 Ventas POS
```
- ventas: Ventas completadas
- tickets_espera: Tickets en espera (reserva de inventario)
```

### 3.7 Caja
```
- caja_movimientos: Movimientos de caja (origen: "clinica")
- caja_cierres: Cierres diarios (origen: "clinica")
```

### 3.8 Gastos
```
- expenses: Gastos
- expense_payments: Pagos de gastos
- fixed_expenses: Gastos fijos
- payment_authorizations: Autorizaciones de pago
```

### 3.9 Cirugías
```
- surgeries: Cirugías programadas (Kanban)
- surgery_crm: Pipeline CRM quirúrgico
```

### 3.10 Óptica (Colecciones Propias)
```
- doctors: Médicos de óptica
- optica_frames: Inventario de aros
- optica_contact_lenses: Lentes de contacto
- optica_lens_types: Tipos de lentes oftálmicos
- optica_sales: Ventas de óptica
- optica_sale_payments: Pagos/abonos de óptica
```

---

## 4. ENDPOINTS PRINCIPALES

### 4.1 Autenticación
| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| POST | /api/auth/login | Público | Login |
| POST | /api/auth/logout | Auth | Logout |
| GET | /api/auth/me | Auth | Usuario actual |
| POST | /api/security/change-password | Auth | Cambiar contraseña |
| GET | /api/security/alerts | SuperAdmin | Alertas de seguridad |

### 4.2 Pacientes
| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| GET | /api/patients | Auth | Listar pacientes |
| POST | /api/patients | Auth | Crear paciente |
| GET | /api/patients/{id} | Auth | Obtener paciente |
| PUT | /api/patients/{id} | Auth | Actualizar paciente |
| POST | /api/patients/bulk-import | Admin+ | Importación masiva |

### 4.3 Agenda
| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| GET | /api/agenda/citas | Auth | Listar citas |
| POST | /api/agenda/citas | Auth | Crear cita |
| GET | /api/agenda/medicos | Auth | Listar médicos |
| WS | /ws/agenda | Auth | Actualizaciones tiempo real |

### 4.4 Evaluaciones
| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| GET | /api/evaluaciones/paciente/{id} | Auth | Evaluaciones del paciente |
| POST | /api/evaluaciones | Auth | Crear evaluación |
| PUT | /api/evaluaciones/{id} | Auth | Actualizar (si no sellada) |
| GET | /api/evaluaciones/catalogos/* | Auth | Catálogos |

### 4.5 Inventario
| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| GET | /api/inventario/productos | Auth | Listar productos |
| GET | /api/inventario/lotes | Auth | Listar lotes |
| GET | /api/inventario/kardex | Auth | Kardex |
| POST | /api/inventario/movimientos | Auth | Crear movimiento |
| POST | /api/inventario/toma-fisica | Admin+ | Toma física |

### 4.6 Ventas POS
| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| POST | /api/ventas | Auth | Crear venta |
| GET | /api/ventas | Auth | Listar ventas |
| POST | /api/ventas/ticket-espera | Auth | Crear ticket en espera |
| POST | /api/ventas/{id}/anular | Admin+ | Anular venta |

### 4.7 Caja
| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| GET | /api/caja/estado | Auth | Estado actual |
| POST | /api/caja/abrir | Auth | Abrir caja |
| POST | /api/caja/cerrar | Auth | Cerrar caja |
| POST | /api/caja/movimientos | Auth | Registrar movimiento |

### 4.8 Óptica
| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| GET | /api/optica/sales | Auth | Ventas de óptica |
| POST | /api/optica/sales | Auth | Crear venta óptica |
| GET | /api/optica/frames | Auth | Inventario aros |
| GET | /api/optica/contact-lenses | Auth | Lentes de contacto |
| POST | /api/optica/sales/{id}/payments | Auth | Registrar pago |

---

## 5. FUNCIONES DE SERVICIO INTERNAS

### 5.1 Inventario
- `descontar_inventario_fefo()` - Descuento FEFO con rollback
- `registrar_movimiento_kardex()` - Crear movimiento inmutable
- `calcular_costo_promedio()` - Costo promedio ponderado
- `verificar_existencia()` - Validar disponibilidad

### 5.2 Ventas
- `generar_numero_venta()` - Correlativo VTA-YYYYMMDD-XXXX
- `calcular_iva()` - Desglose IVA 12%
- `reservar_inventario()` - Tickets en espera

### 5.3 Caja
- `registrar_movimiento_caja()` - Ingreso/egreso
- `obtener_estado_caja()` - Balance actual

### 5.4 Óptica
- `get_next_order_number()` - Correlativo ORD-YYYYMM-XXXX
- `enrich_sale()` - Enriquecer venta con datos relacionados

---

## 6. RESPUESTAS A PREGUNTAS ESPECÍFICAS

### 6.1 ¿Cómo está separado el módulo de óptica?

**Arquitectura de colecciones separadas, NO filtro por origen.**

- Óptica tiene sus propias colecciones: `optica_*`
- NO usa `origen: "optica"` en colecciones compartidas
- El único elemento compartido es la colección `patients`

### 6.2 ¿La venta de óptica descuenta de qué bodega?

**NO descuenta de ninguna bodega del sistema de bodegas.**

El stock se actualiza directamente:
```python
# En optica.py línea ~945
await db.optica_frames.update_one(
    {"id": frame_id},
    {"$inc": {"stock": -1}}
)
```

**HALLAZGO CRÍTICO:** Esto viola la inmutabilidad del kardex.

### 6.3 ¿Las recetas de lentes llegan a óptica?

**NO.**

- Las evaluaciones guardan recetas en `evaluaciones_oftalmologicas.recetas`
- El módulo de óptica NO tiene campo para referenciar recetas
- No hay flujo automatizado de receta → orden de óptica

### 6.4 ¿Existe bodega de dispensario distinta?

**SÍ, el sistema lo soporta.**

Bodegas se crean en `bodegas_inventario` con flags:
- `esPuntoVenta: true` para dispensario/POS
- `es_quirofano: true` (presumiblemente para quirófano)

Las bodegas de prueba deben crearse explícitamente.

---

## 7. HALLAZGOS CRÍTICOS PRE-PRUEBAS

| ID | Hallazgo | Severidad | Impacto |
|----|----------|-----------|---------|
| PRE-01 | Óptica no tiene kardex inmutable | CRÍTICA | No hay trazabilidad de movimientos de inventario |
| PRE-02 | Recetas de lentes no se conectan con óptica | ALTA | Flujo incompleto evaluación → venta óptica |
| PRE-03 | Óptica no tiene cierre de caja | MEDIA | No hay arqueo de óptica |
| PRE-04 | No hay endpoint de devoluciones en POS | INFO | Fuera de alcance (documentado) |

---

## 8. DECISIONES PARA PRUEBAS

Basado en el análisis de precondiciones:

1. **Pruebas de aislamiento (AIS-*)**: Se enfocarán en verificar que colecciones de óptica NO se mezclan con colecciones de clínica.

2. **Pruebas de inventario (INV-*)**: Solo aplican a inventario clínico con kardex. El inventario de óptica se probará por separado sin expectativa de kardex.

3. **Pruebas de recorrido B (Óptica pura)**: Se omitirá la verificación de conexión con recetas (PRE-02), marcando como OMITIDA con razón documentada.

4. **Pruebas de caja**: Solo aplican a clínica. El cierre de óptica se marcará como OMITIDA (PRE-03).

---

**Fin de Fase 0 - Inventario de Precondiciones**

---

# FASE 1-7: EN PROGRESO

*Las siguientes fases se documentarán a medida que se implementen...*
