# FLOW_AUDIT.md - Auditoría del Flujo Clínico NovaVision

## Fecha de Auditoría: 31 Julio 2026

---

## RESUMEN EJECUTIVO

Este documento audita el flujo clínico completo:
**Cita → Paciente → Evaluación Médica → Óptica → Sala de Operaciones**

### Estado Actual vs Estado Deseado

| Módulo | Referencia paciente | Estado | Acción requerida |
|--------|---------------------|--------|------------------|
| Agenda (Citas) | `paciente_id` + `paciente_nombre` | ✅ Correcto | Ninguna |
| Pacientes | `id` (único) | ✅ Correcto | Ninguna |
| Evaluación | `paciente_id` + `paciente_nombre` | ⚠️ Parcial | Agregar `cita_id` |
| Óptica | Sin estructura clara | ⚠️ Pendiente revisión | Definir `paciente_id` |
| Sala Operaciones | `patient_name` (solo texto) | ❌ Incorrecto | Agregar `paciente_id` |
| Caja Movimientos | `paciente_id` + `paciente_nombre` | ✅ Correcto | Ninguna |
| Cuentas por Cobrar | `paciente_id` + `paciente_nombre` | ✅ Correcto | Ninguna |

---

## DETALLE POR COLECCIÓN

### 1. Colección: `patients` (Pacientes)
**Archivo:** `/app/backend/server.py` - Modelo `PatientResponse`

**Campos clave:**
```
id: str                  # UUID - CLAVE PRIMARIA UNIVERSAL
record_number: str       # Número de expediente (EXP-YYYYMM-XXXX)
first_name: str
last_name: str
dpi: str                 # Documento de identidad
phone: str
birth_date: str
gender: str
```

**Estado:** ✅ Estructura correcta - es la fuente de verdad para pacientes.

---

### 2. Colección: `citas` (Agenda de Pacientes)
**Archivo:** `/app/backend/models/agenda.py` - Modelo `CitaResponse`

**Campos clave:**
```
id: str                  # UUID de la cita
paciente_id: str         # ✅ Referencia a patients.id
paciente_nombre: str     # Cache del nombre (para UI rápida)
medico_id: str
medico_nombre: str
fecha: str
hora_inicio: str
estado: str              # Agendada/Confirmada/Presente/En consulta/Atendida/No asistió/Cancelada
tipo_agenda: str         # "pacientes" para diferenciar de sala de operaciones
```

**Estado:** ✅ Estructura correcta
**Observación:** El campo `paciente_nombre` es una copia que puede desincronizarse si se edita el paciente. Recomendación: siempre leer el nombre desde la referencia `paciente_id` en vistas críticas.

---

### 3. Colección: `evaluaciones_oftalmologicas` (Evaluaciones Médicas)
**Archivo:** `/app/backend/models/evaluacion_oftalmologica.py`

**Campos clave actuales:**
```
id: str
paciente_id: str         # ✅ Referencia a patients.id
paciente_nombre: str     # Cache del nombre
paciente_edad: int
paciente_expediente: str
medico_id: str
medico_nombre: str
fecha: str
sellado: bool
fecha_sellado: str
```

**Estado:** ⚠️ Parcialmente correcto
**Problema detectado:** No existe `cita_id` para trazabilidad de qué cita originó la evaluación.
**Acción requerida:** 
- Agregar campo `cita_id: Optional[str]` al modelo
- Modificar frontend para pasar `cita_id` al crear evaluación desde agenda

---

### 4. Colección: `surgeries` (Sala de Operaciones)
**Archivo:** `/app/backend/server.py` - Modelo `SurgeryBase`

**Campos clave actuales:**
```
id: str
date: str
time: str
patient_name: str        # ❌ PROBLEMA: Solo texto, no referencia
procedure: str
surgeon: str
eye: str                 # OD/OS/AO
anesthesia_type: str
anesthesiologist: str
institution: str
igss_data: Optional[IGSSData]
```

**Estado:** ❌ Incorrecto
**Problema crítico:** El campo `patient_name` es solo texto libre. No hay referencia a `paciente_id`.
**Consecuencias:**
- Imposible vincular cirugía con historial del paciente
- No se puede verificar que sea el mismo paciente del flujo
- Si se edita el nombre del paciente, la cirugía queda desvinculada

**Acción requerida:**
- Agregar campos: `paciente_id: Optional[str]`, `evaluacion_id: Optional[str]`
- Migrar cirugías existentes intentando vincular por nombre
- El campo `patient_name` se mantiene como cache pero `paciente_id` es la referencia oficial

---

### 5. Colección: `optica_ventas` (Óptica)
**Estado:** ⚠️ Por auditar en detalle

**Campos esperados:**
```
id: str
paciente_id: str         # Referencia a patients.id
evaluacion_id: str       # Referencia a evaluación que generó la receta
receta_id: str           # Referencia a la receta específica
origen: str              # "optica" - CRÍTICO para aislamiento
```

---

### 6. Colección: `caja_movimientos` (Caja)
**Archivo:** `/app/backend/routes/caja.py`

**Campos clave:**
```
id: str
tipo: str                # "Ingreso" / "Egreso"
categoria: str
concepto: str
monto: float
metodo_pago: str
paciente_id: Optional[str]    # ✅ Referencia a patients.id
paciente_nombre: Optional[str]
origen: str              # ✅ "clinica" para aislamiento
bloqueado: bool
```

**Estado:** ✅ Estructura correcta

---

### 7. Colección: `cuentas_por_cobrar` (CxC)
**Archivo:** `/app/backend/models/caja.py`

**Campos clave:**
```
id: str
paciente_id: str         # ✅ Referencia a patients.id
paciente_nombre: str
tipo_pagador: str
monto_total: float
saldo_pendiente: float
abonos: List[Abono]
origen: str              # ✅ "clinica" para aislamiento
```

**Estado:** ✅ Estructura correcta

---

## FLUJO ESPERADO Y PUNTOS DE VERIFICACIÓN

### A. Creación de Cita
```
1. Usuario busca paciente existente (por nombre/documento/expediente)
2. Si no existe → crear paciente nuevo → obtener paciente_id
3. Crear cita con:
   - paciente_id: UUID del paciente
   - paciente_nombre: cache del nombre actual
   - tipo_agenda: "pacientes"
```
**Verificación:** ✅ Implementado correctamente en `/app/backend/routes/agenda.py`

### B. Paciente Presente (Day Board)
```
1. Recepción marca llegada → estado: "Presente"
2. Asigna médico de turno
3. El paciente_id se mantiene intacto
```
**Verificación:** ✅ Implementado correctamente

### C. Evaluación Médica
```
1. Médico abre evaluación desde cita
2. Sistema precarga datos del paciente vía paciente_id
3. FALTA: Guardar cita_id en la evaluación
4. Al guardar próxima cita, usar mismo paciente_id
```
**Verificación:** ⚠️ Falta cita_id para trazabilidad completa

### D. Óptica
```
1. Desde evaluación, se genera receta
2. Receta pasa a óptica con:
   - paciente_id
   - evaluacion_id
   - receta_id
3. Venta en óptica con origen: "optica"
```
**Verificación:** ⚠️ Por implementar vinculación completa

### E. Sala de Operaciones
```
1. Al programar cirugía, se debe seleccionar paciente_id
2. Opcionalmente vincular evaluacion_id
3. Mantener patient_name como cache
```
**Verificación:** ❌ Actualmente solo usa patient_name sin referencia

---

## ACCIONES CORRECTIVAS REQUERIDAS

### Prioridad Alta

1. **[SURGERIES] Agregar paciente_id y evaluacion_id**
   - Modificar modelos SurgeryBase, SurgeryCreate, SurgeryUpdate, SurgeryResponse
   - Actualizar endpoints CRUD
   - Script de migración para cirugías existentes

2. **[EVALUACIONES] Agregar cita_id**
   - Modificar modelo EvaluacionOftalmologicaBase
   - Actualizar frontend para pasar cita_id

### Prioridad Media

3. **[INTEGRIDAD] Endpoint de diagnóstico**
   - GET /api/admin/integridad-pacientes
   - Detectar: pacientes sin referencias, referencias huérfanas, posibles duplicados

4. **[INDICES] Crear índices en MongoDB**
   - paciente_id en todas las colecciones relevantes

### Prioridad Baja

5. **[FUSIÓN] Mecanismo manual de fusión de duplicados**
   - Solo SuperAdmin
   - Reasignar referencias antes de eliminar

---

## TAGS DE ORIGEN

### Verificación de aislamiento clínica/óptica

| Colección | Tag requerido | Implementado |
|-----------|---------------|--------------|
| caja_movimientos | origen: "clinica" | ✅ |
| caja_cierres | origen: "clinica" | ✅ |
| cuentas_por_cobrar | origen: "clinica" | ✅ |
| optica_ventas | origen: "optica" | ⚠️ Verificar |

---

## CHANGELOG DE CORRECCIONES

| Fecha | Acción | Archivos modificados |
|-------|--------|---------------------|
| 31/07/2026 | Auditoría inicial | FLOW_AUDIT.md creado |
| 31/07/2026 | Agregar paciente_id y evaluacion_id a surgeries | server.py (modelos Surgery*) |
| 31/07/2026 | Agregar cita_id a evaluaciones | models/evaluacion_oftalmologica.py |
| 31/07/2026 | Endpoint GET /api/admin/integridad-pacientes | routes/admin.py |
| 31/07/2026 | Endpoint GET /api/admin/integridad-datos | routes/admin.py |
| 31/07/2026 | Dashboard Financiero (backend + frontend) | routes/dashboard_financiero.py, DashboardFinanciero.js |
| 31/07/2026 | Menú Dashboard Financiero solo SuperAdmin | Layout.js, App.js |
| 31/07/2026 | Endpoints vinculación de cirugías | routes/admin.py |
| 31/07/2026 | Refactorización server.py (8580→7974 líneas) | server.py, routes/admin.py, routes/dashboard_financiero.py |

