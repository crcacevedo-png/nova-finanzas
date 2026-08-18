# PLAN DE REMEDIACIÓN DE SEGURIDAD - NOVAVISION ERP

**Documento:** SECURITY_REMEDIATION_PLAN.md  
**Fecha:** 2026-08-18  
**Basado en:** SECURITY_AUDIT.md  

---

## RESUMEN DE FASES

| Fase | Alcance | Hallazgos | Esfuerzo Total |
|------|---------|-----------|----------------|
| **Fase 1** | Críticos y Altos explotables | SEC-001, SEC-002, SEC-003, SEC-012, SEC-005, SEC-006 | 8-12 horas |
| **Fase 2** | Medios y endurecimiento | SEC-004, SEC-007, SEC-008, SEC-010, SEC-011, SEC-013, SEC-014 | 16-24 horas |
| **Fase 3** | Mejora continua | SEC-009, SEC-015, SEC-016, Monitoreo, Políticas | Continuo |

---

## FASE 1: REMEDIACIÓN INMEDIATA

### 1.1 SEC-001 + SEC-012: Credenciales por Defecto y Cambio Forzado

**Prioridad:** 🔴 CRÍTICA  
**Esfuerzo:** 2-3 horas  
**Riesgo de Regresión:** Bajo  

**Cambios Requeridos:**

1. **Agregar campo `must_change_password` a modelo de usuario**
```python
# En seed_default_users():
user_doc = {
    ...
    "must_change_password": True,  # NUEVO: Forzar cambio
    "password_changed_at": None,
    ...
}
```

2. **Validar en login si debe cambiar contraseña**
```python
# En endpoint login:
if user.get("must_change_password"):
    return {
        "access_token": token,
        "must_change_password": True,
        "message": "Debe cambiar su contraseña antes de continuar"
    }
```

3. **Frontend: Redirigir a cambio de contraseña**
```javascript
// En AuthContext.js
if (response.must_change_password) {
    navigate('/change-password', { state: { forced: true } });
}
```

4. **Actualizar flag después de cambio exitoso**
```python
# En change_password:
await db.users.update_one(
    {"id": user_id},
    {"$set": {
        "password": hash_password(new_password),
        "must_change_password": False,
        "password_changed_at": datetime.now(timezone.utc).isoformat()
    }}
)
```

**Archivos a Modificar:**
- `/app/backend/server.py` (líneas 829-856, 2155-2213, 2338-2383)
- `/app/frontend/src/context/AuthContext.js`
- `/app/frontend/src/pages/Login.js`

**Pruebas:**
- [ ] Usuario nuevo con must_change_password=True no puede acceder al sistema
- [ ] Después de cambiar contraseña, puede acceder normalmente
- [ ] must_change_password se resetea a False

---

### 1.2 SEC-002: Aplicar CORS Middleware

**Prioridad:** 🔴 ALTA  
**Esfuerzo:** 30 minutos  
**Riesgo de Regresión:** Bajo  

**Cambio Requerido:**

Agregar después de la línea 84 en `server.py`:

```python
# CORS Middleware - DEBE estar después de GZipMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
    max_age=600,  # Cache preflight por 10 minutos
)
```

**Archivos a Modificar:**
- `/app/backend/server.py` (después de línea 84)

**Pruebas:**
- [ ] Peticiones desde origen permitido funcionan
- [ ] Peticiones desde origen no permitido son rechazadas (403)
- [ ] Preflight OPTIONS funciona correctamente

---

### 1.3 SEC-003: Fortalecer JWT_SECRET

**Prioridad:** 🔴 ALTA  
**Esfuerzo:** 30 minutos  
**Riesgo de Regresión:** ALTO (invalida sesiones activas)  

**Cambio Requerido:**

1. **Generar nuevo secreto:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

2. **Actualizar .env:**
```
JWT_SECRET="[NUEVO_SECRETO_GENERADO]"
```

3. **Agregar validación en server.py:**
```python
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET no configurado. Configure en .env")
if len(JWT_SECRET) < 64:
    logging.warning("⚠️ JWT_SECRET demasiado corto. Recomendado: 64+ caracteres")
```

**Advertencia:** Este cambio invalida TODAS las sesiones activas. Coordinar con usuarios.

**Archivos a Modificar:**
- `/app/backend/.env`
- `/app/backend/server.py` (líneas 52-57)

**Pruebas:**
- [ ] Servidor inicia con nuevo secreto
- [ ] Tokens viejos son rechazados
- [ ] Nuevos tokens funcionan correctamente

---

### 1.4 SEC-005 + SEC-006: Bloqueo por Intentos Fallidos y Registro de Dispositivo

**Prioridad:** 🔴 ALTA (Control compensatorio crítico)  
**Esfuerzo:** 3-4 horas  
**Riesgo de Regresión:** Medio  

**Cambios Requeridos:**

1. **Agregar campos a modelo de usuario:**
```python
user_doc = {
    ...
    "failed_login_attempts": 0,
    "locked_until": None,
    "known_devices": [],  # Lista de {ip, user_agent, first_seen, last_seen}
}
```

2. **Crear colección de sesiones activas:**
```python
# Nueva colección: active_sessions
session_doc = {
    "id": str(uuid.uuid4()),
    "user_id": user_id,
    "token_jti": jti,  # ID único del token
    "ip_address": ip,
    "user_agent": user_agent,
    "device_fingerprint": fingerprint,
    "created_at": now,
    "last_activity": now,
    "is_new_device": is_new  # Para alertas
}
```

3. **Modificar endpoint login:**
```python
@api_router.post("/auth/login")
async def login(request: Request, credentials: UserLogin):
    # Verificar bloqueo
    user = await db.users.find_one({"username": credentials.username.lower()})
    if user and user.get("locked_until"):
        locked_until = datetime.fromisoformat(user["locked_until"])
        if locked_until > datetime.now(timezone.utc):
            remaining = (locked_until - datetime.now(timezone.utc)).seconds // 60
            raise HTTPException(
                status_code=429, 
                detail=f"Cuenta bloqueada. Intente en {remaining} minutos"
            )
        else:
            # Desbloquear
            await db.users.update_one(
                {"id": user["id"]},
                {"$set": {"locked_until": None, "failed_login_attempts": 0}}
            )
    
    # ... verificación de credenciales ...
    
    if not valid:
        # Incrementar intentos fallidos
        attempts = (user.get("failed_login_attempts", 0) if user else 0) + 1
        if user:
            update_data = {"failed_login_attempts": attempts}
            if attempts >= 5:
                # Bloquear por 15 minutos
                update_data["locked_until"] = (
                    datetime.now(timezone.utc) + timedelta(minutes=15)
                ).isoformat()
                # Alertar a SuperAdmin
                await alert_superadmin(
                    f"Cuenta {user['username']} bloqueada tras {attempts} intentos fallidos"
                )
            await db.users.update_one({"id": user["id"]}, {"$set": update_data})
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    # Login exitoso - resetear contador
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"failed_login_attempts": 0, "locked_until": None}}
    )
    
    # Registrar dispositivo y verificar si es nuevo
    is_new_device = await register_device_and_check_new(
        user["id"], 
        request.client.host,
        request.headers.get("user-agent", "")
    )
    
    if is_new_device:
        await alert_superadmin(
            f"Nuevo dispositivo detectado para {user['username']} desde IP {request.client.host}"
        )
    
    # Crear sesión
    session_id = await create_active_session(user["id"], jti, request)
    
    return TokenResponse(...)
```

4. **Crear función de alerta a SuperAdmin:**
```python
async def alert_superadmin(message: str, severity: str = "warning"):
    """Enviar alerta al SuperAdmin"""
    await db.security_alerts.insert_one({
        "id": str(uuid.uuid4()),
        "message": message,
        "severity": severity,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "acknowledged": False
    })
    # También registrar en audit log
    await audit.log(
        action="SECURITY_ALERT",
        user_id="system",
        user_name="system",
        details={"message": message, "severity": severity}
    )
```

**Archivos a Modificar:**
- `/app/backend/server.py` (endpoint login, funciones auxiliares)
- `/app/backend/routes/auth.py` (si se usa)

**Pruebas:**
- [ ] Después de 5 intentos fallidos, cuenta se bloquea por 15 minutos
- [ ] SuperAdmin recibe alerta de bloqueo
- [ ] Login desde nueva IP genera alerta
- [ ] Dispositivos conocidos no generan alerta
- [ ] Sesión se registra en active_sessions

---

## FASE 2: ENDURECIMIENTO (REQUIERE APROBACIÓN)

### 2.1 SEC-004: Política de Contraseñas Mejorada

**Esfuerzo:** 2 horas  
**Riesgo de Regresión:** Bajo  

**Cambios:**
- Aumentar mínimo a 12 caracteres
- Agregar verificación contra lista de contraseñas comunes (10,000 más comunes)
- Agregar verificación de contraseñas anteriores (últimas 5)

```python
COMMON_PASSWORDS = set(open('/app/backend/data/common_passwords.txt').read().splitlines())

def validate_password_strength(password: str, user_id: str = None) -> tuple[bool, str]:
    if len(password) < 12:
        return False, "La contraseña debe tener al menos 12 caracteres"
    if password.lower() in COMMON_PASSWORDS:
        return False, "Esta contraseña es muy común. Elija otra."
    # ... resto de validaciones ...
    
    # Verificar contraseñas anteriores
    if user_id:
        user = await db.users.find_one({"id": user_id})
        for old_hash in user.get("password_history", []):
            if verify_password(password, old_hash):
                return False, "No puede reutilizar contraseñas anteriores"
    
    return True, "OK"
```

---

### 2.2 SEC-007: Timeout de Inactividad (30 minutos)

**Esfuerzo:** 3 horas  
**Riesgo de Regresión:** Medio  
**Estado:** ✅ IMPLEMENTADO

**Cambios Implementados:**

1. **Hook `useInactivityTimeout.js`**: Detecta inactividad del usuario mediante eventos de mouse, teclado y scroll.

2. **Componente `InactivityWarning.js`**: Modal que advierte al usuario 5 minutos antes del cierre.

3. **Integración en `AuthContext.js`**: El timeout se activa automáticamente cuando hay un usuario logueado.

**Comportamiento:**
- Después de 25 minutos de inactividad: aparece modal de advertencia con countdown
- El usuario puede hacer clic en "Continuar trabajando" para extender la sesión
- Después de 30 minutos totales: cierre automático de sesión
- En la página de login se muestra mensaje explicativo si la sesión expiró por inactividad

**Configuración:**
- Timeout configurable via `REACT_APP_INACTIVITY_TIMEOUT` (en minutos, default: 30)

---

### 2.3 SEC-008: Sanitización NoSQL

**Esfuerzo:** 4 horas  
**Riesgo de Regresión:** Medio  

**Crear middleware de sanitización:**
```python
def sanitize_nosql_input(data: dict) -> dict:
    """Eliminar operadores MongoDB peligrosos de la entrada"""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Rechazar claves que empiecen con $
            if key.startswith('$'):
                raise HTTPException(
                    status_code=400, 
                    detail="Caracteres no permitidos en la entrada"
                )
            sanitized[key] = sanitize_nosql_input(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_nosql_input(item) for item in data]
    elif isinstance(data, str):
        # Rechazar valores que contengan operadores
        if any(op in data for op in ['$gt', '$lt', '$ne', '$regex', '$where']):
            raise HTTPException(
                status_code=400,
                detail="Caracteres no permitidos en la entrada"
            )
        return data
    return data
```

**Aplicar en endpoints de búsqueda:**
```python
@api_router.get("/patients")
async def get_patients(
    search: Optional[str] = Query(None, max_length=100),
    ...
):
    if search:
        # Sanitizar antes de usar en regex
        search = re.escape(search)  # Escapar caracteres especiales de regex
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
        ]
```

---

### 2.4 SEC-010: Bitácora de Acceso a Expedientes

**Esfuerzo:** 3 horas  
**Riesgo de Regresión:** Bajo  

```python
async def log_expediente_access(
    user_id: str, 
    user_name: str,
    patient_id: str,
    action: str,  # "view", "edit", "export"
    ip_address: str
):
    """Registrar acceso a expediente clínico (bitácora inmutable)"""
    await db.expediente_access_log.insert_one({
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "user_name": user_name,
        "patient_id": patient_id,
        "action": action,
        "ip_address": ip_address
    })

# Crear índice único para prevenir modificaciones
# En startup:
await db.expediente_access_log.create_index([("id", 1)], unique=True)
# NO crear índices que permitan update/delete
```

**Uso en endpoints:**
```python
@api_router.get("/patients/{patient_id}")
async def get_patient(patient_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    patient = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if patient:
        # Registrar acceso
        await log_expediente_access(
            user_id=current_user["id"],
            user_name=current_user.get("username"),
            patient_id=patient_id,
            action="view",
            ip_address=request.client.host
        )
    return patient
```

---

### 2.5 SEC-011: Restricción y Auditoría de Exportaciones

**Esfuerzo:** 2 horas  

```python
@api_router.get("/patients/export")
async def export_patients(
    request: Request,
    current_user: dict = Depends(require_permission("export_patients"))
):
    # Verificar que solo roles autorizados pueden exportar
    if current_user["role"] not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="No autorizado para exportar")
    
    # Contar registros
    total = await db.patients.count_documents({"is_active": True})
    
    # Registrar exportación en auditoría
    await audit.log(
        action="EXPORT_PATIENTS",
        user_id=current_user["id"],
        user_name=current_user.get("username"),
        details={
            "total_records": total,
            "format": "excel",
            "ip_address": request.client.host
        },
        ip_address=request.client.host
    )
    
    # Proceder con exportación...
```

---

### 2.6 SEC-013: Revocación Masiva de Sesiones

**Esfuerzo:** 2 horas  

```python
# Agregar token_version a usuarios
user_doc = {
    ...
    "token_version": 1,
    ...
}

# Modificar create_token para incluir versión
def create_token(user_id: str, username: str, role: str, token_version: int) -> str:
    payload = {
        ...
        "tv": token_version,  # Token version
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# Modificar get_current_user para validar versión
async def get_current_user(...):
    payload = jwt.decode(...)
    user = await db.users.find_one({"id": payload["sub"]})
    
    # Verificar versión del token
    if payload.get("tv", 1) != user.get("token_version", 1):
        raise HTTPException(status_code=401, detail="Sesión invalidada")
    
    return user

# Endpoint para revocar todas las sesiones
@api_router.post("/users/{user_id}/revoke-sessions")
async def revoke_all_sessions(
    user_id: str,
    current_user: dict = Depends(require_permission("manage_users"))
):
    # Incrementar versión invalida todos los tokens existentes
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"token_version": 1}}
    )
    
    # También limpiar active_sessions
    await db.active_sessions.delete_many({"user_id": user_id})
    
    await audit.log(
        action="REVOKE_ALL_SESSIONS",
        user_id=current_user["id"],
        user_name=current_user.get("username"),
        details={"target_user_id": user_id}
    )
    
    return {"message": "Todas las sesiones han sido revocadas"}
```

---

## FASE 3: MEJORA CONTINUA (PROPUESTAS)

### 3.1 SEC-009: Limpiar Console.logs

**Esfuerzo:** 2 horas  
**Acción:** Script para encontrar y evaluar cada console.log

```bash
grep -rn "console.log\|console.error" /app/frontend/src/ --include="*.js"
```

Clasificar cada uno:
- Eliminar: logs de debug
- Mantener: logs de errores críticos para troubleshooting
- Reemplazar: usar sistema de logging con niveles

---

### 3.2 SEC-014: CSP Completa

**Propuesta de CSP:**
```python
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://assets.emergent.sh; "  # Necesario para React
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: blob:; "
    "connect-src 'self' wss: https:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)
```

---

### 3.3 Monitoreo y Alertas

**Sistema de alertas automatizadas para:**
- Múltiples intentos fallidos de login (>3 en 5 minutos)
- Acceso desde país inusual (requiere geo-IP)
- Exportación masiva fuera de horario laboral (8am-6pm)
- Creación de usuario SuperAdmin
- Modificación de permisos
- Acceso a >50 expedientes en 1 hora

---

### 3.4 Respaldos (Esquema Aprobado)

**Implementar:**
1. Backup completo quincenal (automatizado)
2. Backup incremental diario
3. Cifrado AES-256 de archivos
4. Verificación checksum post-backup
5. Alertas en caso de fallo
6. Descarga cifrada para SuperAdmin
7. Prueba de restauración trimestral documentada

---

## CHECKLIST DE IMPLEMENTACIÓN FASE 1

- [ ] SEC-001: Agregar must_change_password a seed
- [ ] SEC-001: Modificar login para verificar flag
- [ ] SEC-001: Frontend: Redirigir a cambio obligatorio
- [ ] SEC-002: Agregar CORSMiddleware con configuración
- [ ] SEC-003: Generar nuevo JWT_SECRET (coordinar desconexión)
- [ ] SEC-003: Agregar validación de longitud mínima
- [ ] SEC-005: Implementar contador de intentos fallidos
- [ ] SEC-005: Implementar bloqueo temporal (15 min)
- [ ] SEC-006: Crear colección active_sessions
- [ ] SEC-006: Implementar detección de nuevo dispositivo
- [ ] SEC-006: Crear función alert_superadmin
- [ ] Pruebas de seguridad automatizadas
- [ ] Actualizar test_credentials.md

---

## APROBACIONES REQUERIDAS

Antes de implementar Fase 2 y Fase 3, se requiere aprobación explícita para:

1. **Cambio de política de contraseñas:** Afecta a todos los usuarios actuales
2. **Timeout de inactividad:** Puede interrumpir trabajo si no se guarda
3. **Sanitización NoSQL:** Podría afectar búsquedas con caracteres especiales
4. **Bitácora de expedientes:** Incrementa uso de almacenamiento

¿Procedo con las correcciones de Fase 1?
