# AUDITORÍA DE SEGURIDAD - NOVAVISION ERP
## Sistema de Gestión de Clínica Oftalmológica

**Fecha de Auditoría:** 2026-08-18  
**Versión del Sistema:** 1.0  
**Auditor:** Sistema de Auditoría Automatizada E1  
**Clasificación:** CONFIDENCIAL - USO INTERNO

---

## 1. RESUMEN EJECUTIVO

### Para la Dirección de la Clínica

El sistema NovaVision ha sido sometido a una auditoría de seguridad exhaustiva. A continuación se presentan los hallazgos principales en términos comprensibles:

**Estado General:** ⚠️ REQUIERE ATENCIÓN INMEDIATA

#### Hallazgos Críticos (Requieren acción inmediata):
1. **Usuarios con contraseñas conocidas:** El sistema tiene usuarios predeterminados (superadmin, admin, usuario, optica) con contraseñas que aparecen en el código fuente y archivos de pruebas. Cualquier persona con acceso al código conoce estas contraseñas.

2. **Sin protección CORS aplicada:** Aunque el sistema importa protección contra acceso desde otros sitios web, esta no está activada, lo que podría permitir que sitios maliciosos interactúen con el sistema.

3. **Política de contraseñas insuficiente:** La longitud mínima actual (8 caracteres) es menor al estándar recomendado (12 caracteres) para proteger datos clínicos sensibles.

#### Aspectos Positivos:
- ✅ Autenticación JWT implementada correctamente
- ✅ Sistema de auditoría de acciones (audit log) funcional
- ✅ Rate limiting en endpoint de login (5 intentos/minuto)
- ✅ Cifrado de contraseñas con bcrypt (costo 12)
- ✅ Blacklist de tokens para logout real
- ✅ Headers de seguridad implementados (X-Frame-Options, CSP, etc.)
- ✅ Separación de permisos por roles (RBAC)

#### Riesgos Residuales Documentados (Decisiones Tomadas):
- Sin MFA: La autenticación depende de un solo factor (contraseña)
- JWT en localStorage: Exposición potencial si hay vulnerabilidad XSS
- Sin cifrado a nivel de campo: Los datos clínicos se almacenan en texto claro en la base de datos
- Acceso remoto sin restricción: El sistema es accesible desde cualquier ubicación
- Retención indefinida: Los datos se conservan permanentemente

**Recomendación:** Implementar las correcciones de Fase 1 antes de poner el sistema en producción con datos reales de pacientes.

---

## 2. TABLA DE HALLAZGOS

| ID | Título | Componente | Archivo/Línea | Severidad | OWASP | Impacto | Remediación |
|----|--------|------------|---------------|-----------|-------|---------|-------------|
| SEC-001 | Credenciales por defecto conocidas | Autenticación | server.py:829-856, routes/auth.py, tests/*.py | **CRÍTICA** | A07:2021 | Acceso no autorizado total al sistema | Forzar cambio de contraseña en primer login, no usar en producción |
| SEC-002 | CORS Middleware no aplicado | Servidor | server.py | **ALTA** | A05:2021 | Posibles ataques CSRF desde otros orígenes | Agregar app.add_middleware(CORSMiddleware, ...) |
| SEC-003 | JWT_SECRET débil en .env | Autenticación | backend/.env | **ALTA** | A02:2021 | Falsificación de tokens JWT | Usar secret de 256+ bits, rotación periódica |
| SEC-004 | Política de contraseñas insuficiente | Autenticación | server.py:726-736 | **MEDIA** | A07:2021 | Contraseñas fáciles de adivinar | Mínimo 12 caracteres, lista de contraseñas comunes |
| SEC-005 | Sin bloqueo por intentos fallidos | Autenticación | server.py:2155-2213 | **MEDIA** | A07:2021 | Ataques de fuerza bruta sostenidos | Implementar bloqueo temporal tras N intentos |
| SEC-006 | Sin registro de dispositivo/IP en sesión | Autenticación | server.py | **MEDIA** | A07:2021 | No hay detección de acceso sospechoso | Registrar y alertar acceso desde nuevos dispositivos |
| SEC-007 | Sin timeout de inactividad en backend | Sesión | Frontend | **IMPLEMENTADO** | A07:2021 | Sesiones abandonadas vulnerables | ✅ Timeout 30 minutos implementado |
| SEC-008 | Falta validación NoSQL en búsquedas | Validación | routes/*.py | **MEDIA** | A03:2021 | Inyección NoSQL potencial | Sanitizar operadores $ en inputs |
| SEC-009 | Console.log con datos sensibles | Logging | Frontend (98 instancias) | **BAJA** | A09:2021 | Exposición de datos en consola del navegador | Remover en producción |
| SEC-010 | Sin bitácora de acceso a expedientes | Auditoría | Backend | **MEDIA** | A09:2021 | No hay trazabilidad de consultas a datos clínicos | Implementar log de acceso a expedientes |
| SEC-011 | Exportaciones sin restricción de rol | Datos | routes/patients.py | **MEDIA** | A01:2021 | Exportación masiva de datos sin control | Restringir y auditar exportaciones |
| SEC-012 | Falta forzar cambio de contraseña inicial | Autenticación | server.py | **ALTA** | A07:2021 | Usuarios con contraseñas conocidas permanentes | Implementar flag must_change_password |
| SEC-013 | Sin revocación masiva de sesiones | Sesión | server.py | **MEDIA** | A07:2021 | No se puede cerrar todas las sesiones de un usuario | Implementar token_version por usuario |
| SEC-014 | Falta Content-Security-Policy completa | Headers | server.py:222-223 | **BAJA** | A05:2021 | CSP muy básica (solo frame-ancestors) | Expandir CSP con script-src, style-src |
| SEC-015 | Sin límite de paginación en algunos endpoints | API | routes/*.py | **BAJA** | A04:2021 | Denegación de servicio por consultas masivas | Imponer límite máximo obligatorio |
| SEC-016 | Datos sensibles en URL de WebSocket | WebSocket | useWebSocket.js | **INFO** | A04:2021 | Token visible en logs de red | Considerar envío post-conexión |

---

## 3. CLASIFICACIÓN OWASP

### OWASP Top 10 2021

| Categoría | Hallazgos Relacionados | Estado |
|-----------|------------------------|--------|
| A01: Broken Access Control | SEC-011 | ⚠️ Parcial |
| A02: Cryptographic Failures | SEC-003 | ⚠️ Atención |
| A03: Injection | SEC-008 | ⚠️ Revisar |
| A04: Insecure Design | SEC-015, SEC-016 | ℹ️ Bajo |
| A05: Security Misconfiguration | SEC-002, SEC-014 | 🔴 Crítico |
| A06: Vulnerable Components | Ver sección dependencias | ⚠️ Pendiente |
| A07: Auth Failures | SEC-001, SEC-004, SEC-005, SEC-006, SEC-007, SEC-012, SEC-013 | 🔴 Crítico |
| A08: Data Integrity Failures | N/A | ✅ OK |
| A09: Logging Failures | SEC-009, SEC-010 | ⚠️ Parcial |
| A10: SSRF | N/A | ✅ OK |

### OWASP API Security Top 10 2023

| Categoría | Estado |
|-----------|--------|
| API1: Broken Object Level Authorization | ⚠️ Revisar IDOR en endpoints con IDs |
| API2: Broken Authentication | 🔴 Ver SEC-001, SEC-005, SEC-012 |
| API3: Broken Object Property Level Auth | ⚠️ Verificar mass assignment |
| API4: Unrestricted Resource Consumption | ⚠️ Ver SEC-015 |
| API5: Broken Function Level Auth | ✅ RBAC implementado |
| API6: Unrestricted Access to Sensitive Flows | ⚠️ Exportaciones |
| API7: Server Side Request Forgery | ✅ No detectado |
| API8: Security Misconfiguration | 🔴 Ver SEC-002 |
| API9: Improper Inventory Management | ✅ API documentada |
| API10: Unsafe Consumption of APIs | ✅ No hay consumo de APIs externas críticas |

---

## 4. MAPA DE SUPERFICIE DE ATAQUE

### Endpoints de Autenticación

| Método | Ruta | Autenticación | Rol Requerido | Datos Sensibles |
|--------|------|---------------|---------------|-----------------|
| POST | /api/auth/login | ❌ No | Ninguno | Devuelve JWT token |
| POST | /api/auth/logout | ✅ Sí | Cualquiera | - |
| GET | /api/auth/me | ✅ Sí | Cualquiera | Datos del usuario |
| POST | /api/security/change-password | ✅ Sí | Cualquiera | - |

### Endpoints de Usuarios

| Método | Ruta | Autenticación | Rol Requerido | Datos Sensibles |
|--------|------|---------------|---------------|-----------------|
| GET | /api/users | ✅ Sí | view_user_management | Lista de usuarios |
| GET | /api/users/{id} | ✅ Sí | view_user_management | Datos de usuario |
| POST | /api/users | ✅ Sí | manage_users | - |
| PUT | /api/users/{id} | ✅ Sí | manage_users | - |
| DELETE | /api/users/{id} | ✅ Sí | manage_users | - |

### Endpoints de Pacientes

| Método | Ruta | Autenticación | Rol Requerido | Datos Sensibles |
|--------|------|---------------|---------------|-----------------|
| GET | /api/patients | ✅ Sí | view_patients | **PII: Nombres, DPI, teléfonos** |
| GET | /api/patients/{id} | ✅ Sí | view_patients | **PII: Datos completos del paciente** |
| POST | /api/patients | ✅ Sí | create_patients | - |
| PUT | /api/patients/{id} | ✅ Sí | edit_patients | - |
| DELETE | /api/patients/{id} | ✅ Sí | delete_patients | - |
| POST | /api/patients/bulk-import | ✅ Sí | import_patients | **Importación masiva de PII** |
| GET | /api/patients/export | ✅ Sí | export_patients | **Exportación masiva de PII** |

### Endpoints de Evaluaciones Oftalmológicas

| Método | Ruta | Autenticación | Rol Requerido | Datos Sensibles |
|--------|------|---------------|---------------|-----------------|
| GET | /api/evaluaciones/{paciente_id} | ✅ Sí | Autenticado | **Datos clínicos sensibles** |
| POST | /api/evaluaciones | ✅ Sí | Autenticado | - |
| PUT | /api/evaluaciones/{id} | ✅ Sí | Autenticado | - |

### Endpoints de Caja/Finanzas

| Método | Ruta | Autenticación | Rol Requerido | Datos Sensibles |
|--------|------|---------------|---------------|-----------------|
| GET | /api/caja/movimientos | ✅ Sí | Autenticado | Datos financieros |
| POST | /api/caja/movimientos | ✅ Sí | Autenticado | - |
| GET | /api/caja/estado | ✅ Sí | Autenticado | Balance actual |
| POST | /api/caja/abrir | ✅ Sí | Autenticado | - |
| POST | /api/caja/cerrar | ✅ Sí | Autenticado | - |

### Endpoints de Inventario

| Método | Ruta | Autenticación | Rol Requerido | Datos Sensibles |
|--------|------|---------------|---------------|-----------------|
| GET | /api/inventario/productos | ✅ Sí | Autenticado | **Costos (restringir a roles)** |
| GET | /api/inventario/lotes | ✅ Sí | Autenticado | Costos unitarios |
| GET | /api/inventario/kardex | ✅ Sí | Autenticado | Historial de movimientos |
| POST | /api/inventario/movimientos | ✅ Sí | Autenticado | - |

### Endpoints de Auditoría

| Método | Ruta | Autenticación | Rol Requerido | Datos Sensibles |
|--------|------|---------------|---------------|-----------------|
| GET | /api/security/audit-logs | ✅ Sí | **superadmin** | Logs de auditoría |
| GET | /api/security/status | ✅ Sí | **superadmin** | Estado de seguridad |

### WebSocket Endpoints

| Ruta | Autenticación | Propósito |
|------|---------------|-----------|
| /ws/caja | ✅ Token en query | Actualizaciones tiempo real de caja |
| /ws/agenda | ✅ Token en query | Actualizaciones de agenda |
| /ws/pos | ✅ Token en query | Actualizaciones de punto de venta |

---

## 5. DETALLE DE HALLAZGOS CRÍTICOS

### SEC-001: Credenciales por Defecto Conocidas

**Severidad:** 🔴 CRÍTICA  
**OWASP:** A07:2021 Identification and Authentication Failures

**Descripción:**
El sistema contiene usuarios predeterminados con contraseñas hardcodeadas en el código fuente:

```python
# server.py línea 829-836
default_users = [
    {"username": "superadmin", "password": "Nova$2024Secure!", "role": "superadmin"},
    {"username": "admin", "password": "Admin$2024Secure!", "role": "admin"},
    {"username": "usuario", "password": "User$2024Secure!", "role": "usuario"}
]
```

Además, los archivos de pruebas contienen múltiples variantes:
- `tests/conftest.py`: nova2024, Admin2024Nuevo!, user2024, optica2024
- `tests/test_*.py`: Múltiples archivos con credenciales en texto plano

**Impacto en el Negocio:**
- Acceso total al sistema con privilegios de superadmin
- Exposición de todos los datos de pacientes
- Manipulación de registros financieros
- Compromiso total de la confidencialidad

**Prueba de Concepto:**
```bash
curl -X POST https://sistema/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"superadmin","password":"nova2024"}'
```

**Remediación:**
1. Implementar flag `must_change_password` en usuarios sembrados
2. Forzar cambio de contraseña en primer login
3. NO ejecutar seed de usuarios en producción
4. Usar variables de entorno para credenciales iniciales de producción

---

### SEC-002: CORS Middleware No Aplicado

**Severidad:** 🔴 ALTA  
**OWASP:** A05:2021 Security Misconfiguration

**Descripción:**
El sistema importa `CORSMiddleware` pero nunca lo aplica:

```python
# server.py línea 9
from starlette.middleware.cors import CORSMiddleware

# La variable ALLOWED_ORIGINS está definida (línea 62-71)
# PERO nunca se ejecuta app.add_middleware(CORSMiddleware, ...)
```

**Impacto:**
- Sitios web maliciosos pueden hacer peticiones al API
- Posibilidad de ataques CSRF si se combinan con otras vulnerabilidades
- Sin control sobre qué orígenes pueden acceder

**Remediación:**
Agregar después de la línea 84:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

### SEC-003: JWT_SECRET Débil en Archivo .env

**Severidad:** 🔴 ALTA  
**OWASP:** A02:2021 Cryptographic Failures

**Descripción:**
El secreto JWT en producción es predecible:
```
JWT_SECRET="novavision_secure_secret_key_2024_gtq_production_v2"
```

Este valor tiene patrones obvios (novavision, 2024, gtq) que lo hacen vulnerable a ataques de diccionario.

**Remediación:**
Generar un secreto criptográficamente seguro:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 6. RIESGOS RESIDUALES DOCUMENTADOS

### 6.1 Sin Autenticación Multifactor (Decisión #1)

**Riesgo:** La cuenta queda protegida por un solo factor (contraseña). Si la contraseña es comprometida mediante phishing, ingeniería social, o brute force, el atacante obtiene acceso total.

**Controles Compensatorios Implementados/Requeridos:**
- [x] Rate limiting en login (5/minuto)
- [ ] Bloqueo agresivo tras intentos fallidos (PENDIENTE)
- [ ] Alerta al SuperAdmin ante acceso desde nueva IP/dispositivo (PENDIENTE)
- [ ] Sesiones cortas con timeout de inactividad (PENDIENTE)
- [ ] Revocación remota de sesiones (PENDIENTE)

### 6.2 JWT en localStorage (Decisión #2)

**Riesgo:** El token es accesible mediante JavaScript. Una vulnerabilidad XSS permitiría robar el token y suplantar al usuario.

**Controles Compensatorios:**
- [x] Headers de seguridad (X-XSS-Protection)
- [x] CSP básica (frame-ancestors)
- [ ] CSP completa con script-src restrictivo (PENDIENTE)
- [x] No hay uso de dangerouslySetInnerHTML
- [ ] Sanitización de campos de texto libre clínicos (REVISAR)

### 6.3 Sin Cifrado a Nivel de Campo (Decisión #4)

**Riesgo:** Quien obtenga acceso a la base de datos (backup robado, servidor comprometido) lee todos los diagnósticos y datos clínicos en texto claro.

**Controles Compensatorios:**
- [ ] Cifrado de volumen/motor de MongoDB (VERIFICAR EN PRODUCCIÓN)
- [ ] Respaldos cifrados obligatoriamente (PENDIENTE)
- [ ] Bitácora de accesos a expedientes (PENDIENTE)
- [x] Acceso a BD solo desde aplicación (red privada)

### 6.4 Acceso Remoto Sin Restricción (Decisión #8)

**Riesgo:** Este es el riesgo más alto del sistema. No hay barrera de red ni segundo factor: la contraseña es el único control entre un atacante de internet y el expediente clínico completo de todos los pacientes.

**Controles Compensatorios OBLIGATORIOS para Fase 1:**
- [ ] Registro de dispositivo, IP y user-agent en cada sesión
- [ ] Alerta inmediata al SuperAdmin ante nueva IP/dispositivo
- [ ] Bloqueo temporal agresivo tras intentos fallidos
- [ ] Panel de sesiones activas con revocación remota
- [ ] Alerta ante patrones anómalos (acceso masivo, exportaciones fuera de horario)

---

## 7. DEPENDENCIAS Y CADENA DE SUMINISTRO

### Backend (Python)
```
bcrypt>=4.0.0 - ✅ Actual, sin CVEs conocidos
PyJWT>=2.8.0 - ✅ Actual
fastapi>=0.100.0 - ⚠️ Verificar versión actual
motor>=3.0.0 - ✅ Driver MongoDB async
```

**Acción:** Ejecutar `pip audit` y revisar resultados.

### Frontend (Node.js)
```
react>=18.0.0 - ✅ Actual
```

**Acción:** Ejecutar `npm audit` en /app/frontend.

---

## 8. CUMPLIMIENTO REGULATORIO (GUATEMALA)

### Advertencia Legal
Este análisis es un insumo técnico y NO constituye asesoría jurídica. Los siguientes puntos requieren validación por un abogado guatemalteco:

### Puntos a Verificar

1. **Secreto Profesional Médico**
   - Código de Salud y Código Deontológico del Colegio de Médicos
   - Verificar que los controles de acceso cumplan con el deber de confidencialidad

2. **Datos Personales Sensibles**
   - Ley de Acceso a la Información Pública (Decreto 57-2008)
   - Verificar procedimientos de consentimiento para tratamiento de datos

3. **Facturación Electrónica (FEL)**
   - Normativas SAT para conservación de documentos tributarios
   - Verificar integridad y disponibilidad de registros

4. **IGSS y Seguros**
   - Verificar que la transferencia de datos a estas entidades tenga base legal
   - Documentar flujos de datos hacia terceros

5. **Retención Indefinida**
   - Verificar que no entre en conflicto con derechos de supresión de datos
   - Documentar base legal para retención permanente de expedientes

---

## 9. PRÓXIMOS PASOS

1. **Inmediato (Fase 1):** Corregir SEC-001, SEC-002, SEC-003, SEC-012
2. **Corto Plazo (Fase 2):** Implementar controles compensatorios para decisiones tomadas
3. **Continuo (Fase 3):** Establecer monitoreo, respaldos y procedimientos

Ver documento `/docs/SECURITY_REMEDIATION_PLAN.md` para el plan detallado.

---

**Fin del Informe de Auditoría**
