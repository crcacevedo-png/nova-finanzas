# LÍNEA BASE DE CONFIGURACIÓN SEGURA - NOVAVISION ERP

**Documento:** SECURITY_BASELINE.md  
**Fecha:** 2026-08-18  
**Versión:** 1.0  

---

## 1. VARIABLES DE ENTORNO REQUERIDAS

### Backend (.env)

```env
# ==================== OBLIGATORIAS ====================

# MongoDB - Conexión segura
MONGO_URL="mongodb://[usuario]:[password]@[host]:[puerto]/[database]?authSource=admin"
DB_NAME="novavision_production"

# JWT - Secreto criptográficamente seguro (mínimo 64 caracteres)
# Generar con: python -c "import secrets; print(secrets.token_urlsafe(64))"
JWT_SECRET="[SECRETO_GENERADO_SEGURO_DE_64+_CARACTERES]"

# Entorno
ENVIRONMENT="production"

# CORS - Lista de orígenes permitidos (separados por coma, sin espacios)
CORS_ORIGINS="https://novavision.clinica.gt,https://admin.novavision.clinica.gt"

# ==================== OPCIONALES ====================

# Documentación API (deshabilitar en producción)
ENABLE_DOCS="false"

# Rate limiting personalizado (por defecto: 200/minute global, 5/minute login)
RATE_LIMIT_DEFAULT="200/minute"
RATE_LIMIT_LOGIN="5/minute"

# JWT Expiración en horas (por defecto: 8)
JWT_EXPIRATION_HOURS="8"

# ==================== FUTURAS (NO USAR AÚN) ====================

# FEL Guatemala (mantener en false hasta implementación)
FEL_ENABLED="false"
# FEL_NIT=""
# FEL_USUARIO=""
# FEL_LLAVE=""
# FEL_CERTIFICADOR_URL=""

# Google Calendar (pendiente de implementación)
# GOOGLE_CALENDAR_CLIENT_ID=""
# GOOGLE_CALENDAR_CLIENT_SECRET=""
# GOOGLE_CALENDAR_REDIRECT_URI=""
```

### Frontend (.env)

```env
# URL del backend (sin trailing slash)
REACT_APP_BACKEND_URL="https://api.novavision.clinica.gt"

# WebSocket (automático basado en backend URL)
# WDS_SOCKET_PORT=443

# Health check (desarrollo solamente)
ENABLE_HEALTH_CHECK="false"
```

---

## 2. PERMISOS MÍNIMOS DE MONGODB

### Usuario de Aplicación (novavision_app)

```javascript
// Crear usuario con permisos mínimos
db.createUser({
  user: "novavision_app",
  pwd: "[PASSWORD_SEGURO_32_CHARS]",
  roles: [
    { role: "readWrite", db: "novavision_production" }
  ]
});
```

**NO debe tener:**
- `dbAdmin` (no necesita crear índices en runtime)
- `userAdmin` (no necesita gestionar usuarios)
- `root` (nunca en producción)

### Usuario de Respaldos (novavision_backup)

```javascript
db.createUser({
  user: "novavision_backup",
  pwd: "[PASSWORD_SEGURO_32_CHARS]",
  roles: [
    { role: "backup", db: "admin" },
    { role: "read", db: "novavision_production" }
  ]
});
```

### Usuario de Reportes (novavision_reports)

```javascript
db.createUser({
  user: "novavision_reports",
  pwd: "[PASSWORD_SEGURO_32_CHARS]",
  roles: [
    { role: "read", db: "novavision_production" }
  ]
});
```

---

## 3. CABECERAS HTTP OBLIGATORIAS

Todas las respuestas DEBEN incluir:

| Header | Valor | Propósito |
|--------|-------|-----------|
| `X-Frame-Options` | `DENY` | Prevenir clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevenir MIME sniffing |
| `X-XSS-Protection` | `1; mode=block` | Protección XSS (navegadores antiguos) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controlar información de referrer |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Deshabilitar APIs del navegador |
| `Content-Security-Policy` | Ver sección 3.1 | Política de seguridad de contenido |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Forzar HTTPS (solo producción) |
| `Cache-Control` | Según tipo de recurso | Control de caché |

### 3.1 Content-Security-Policy Recomendada

```
default-src 'self';
script-src 'self' 'unsafe-inline' https://assets.emergent.sh;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' data: blob:;
connect-src 'self' wss: https:;
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

**Nota:** `'unsafe-inline'` es necesario temporalmente para React. Evaluar eliminar en futuras versiones.

---

## 4. POLÍTICA DE CONTRASEÑAS

### Requisitos Mínimos (Implementados)

| Criterio | Valor Actual | Valor Recomendado |
|----------|--------------|-------------------|
| Longitud mínima | 8 caracteres | **12 caracteres** |
| Mayúsculas | ≥1 | ≥1 |
| Minúsculas | ≥1 | ≥1 |
| Números | ≥1 | ≥1 |
| Caracteres especiales | No requerido | Recomendado |
| Lista negra | No implementada | **Top 10,000 contraseñas comunes** |
| Historial | No implementado | **Últimas 5 contraseñas** |
| Expiración forzada | No aplicar | No aplicar (decisión tomada) |

### Proceso de Cambio de Contraseña

1. Usuario autenticado accede a "Cambiar Contraseña"
2. Ingresa contraseña actual (validación)
3. Ingresa nueva contraseña (validación de fortaleza)
4. Confirma nueva contraseña
5. Sistema actualiza y registra en audit log
6. Todas las sesiones anteriores se mantienen (opcional: invalidar)

### Bloqueo por Intentos Fallidos

| Intentos Fallidos | Acción |
|-------------------|--------|
| 1-4 | Mensaje genérico "Credenciales inválidas" |
| 5 | Bloqueo de cuenta por 15 minutos |
| +5 (después de desbloqueo) | Bloqueo por 30 minutos |
| Repetido | Alerta a SuperAdmin para revisión manual |

---

## 5. POLÍTICA DE RESPALDOS

### Esquema Aprobado

| Tipo | Frecuencia | Retención | Cifrado | Ubicación |
|------|------------|-----------|---------|-----------|
| Completo | Quincenal (domingos) | Indefinida | AES-256 | Storage externo |
| Incremental | Diario (3:00 AM) | 30 días | AES-256 | Storage externo |

### Objetivos de Recuperación

- **RPO (Recovery Point Objective):** 24 horas máximo
- **RTO (Recovery Time Objective):** 4 horas (estimado)

### Procedimiento de Respaldo

```bash
#!/bin/bash
# backup_novavision.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/novavision"
DB_NAME="novavision_production"
ENCRYPTION_KEY="[LLAVE_CIFRADO_RESPALDOS]"

# Crear respaldo
mongodump --uri="mongodb://novavision_backup:$BACKUP_PASSWORD@localhost:27017/$DB_NAME" \
  --out="$BACKUP_DIR/dump_$DATE" \
  --gzip

# Comprimir
tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" "$BACKUP_DIR/dump_$DATE"

# Cifrar
openssl enc -aes-256-cbc -salt -pbkdf2 \
  -in "$BACKUP_DIR/backup_$DATE.tar.gz" \
  -out "$BACKUP_DIR/backup_$DATE.tar.gz.enc" \
  -pass pass:"$ENCRYPTION_KEY"

# Verificar checksum
sha256sum "$BACKUP_DIR/backup_$DATE.tar.gz.enc" > "$BACKUP_DIR/backup_$DATE.sha256"

# Limpiar archivos temporales
rm -rf "$BACKUP_DIR/dump_$DATE" "$BACKUP_DIR/backup_$DATE.tar.gz"

# Notificar éxito
echo "Backup completado: backup_$DATE.tar.gz.enc"
```

### Procedimiento de Restauración

```bash
#!/bin/bash
# restore_novavision.sh

BACKUP_FILE=$1
ENCRYPTION_KEY="[LLAVE_CIFRADO_RESPALDOS]"

# Verificar checksum
sha256sum -c "${BACKUP_FILE}.sha256" || exit 1

# Descifrar
openssl enc -aes-256-cbc -d -pbkdf2 \
  -in "$BACKUP_FILE" \
  -out "backup_decrypted.tar.gz" \
  -pass pass:"$ENCRYPTION_KEY"

# Descomprimir
tar -xzf backup_decrypted.tar.gz

# Restaurar
mongorestore --uri="mongodb://novavision_app:$APP_PASSWORD@localhost:27017" \
  --drop \
  --gzip \
  dump_*/

# Limpiar
rm -rf backup_decrypted.tar.gz dump_*
```

### Prueba de Restauración (Trimestral)

1. Descargar último respaldo completo + incrementales
2. Restaurar en ambiente de prueba
3. Verificar integridad de datos
4. Documentar resultado
5. Guardar evidencia

---

## 6. RESPONSABLE DE SEGURIDAD

**Rol:** SuperAdmin (Propietario de la clínica)

### Responsabilidades

1. **Receptor de alertas de seguridad:**
   - Intentos de acceso sospechosos
   - Bloqueos de cuentas
   - Exportaciones masivas
   - Nuevos dispositivos

2. **Aprobador de acciones críticas:**
   - Creación de nuevos SuperAdmin
   - Descarga de respaldos
   - Borrado de expedientes (previa solicitud formal)
   - Cambios de configuración de seguridad

3. **Custodio de credenciales de emergencia:**
   - Credenciales de acceso al servidor
   - Llaves de cifrado de respaldos
   - Credenciales de MongoDB

### Escenario: Compromiso de Cuenta SuperAdmin

Si la única cuenta SuperAdmin es comprometida:

1. Las acciones quedan registradas en bitácora inmutable
2. Alertas ante operaciones sensibles (aunque sea SuperAdmin)
3. Procedimiento de recuperación mediante acceso directo a BD

### Escenario: SuperAdmin No Disponible

**Procedimiento de emergencia:**

1. Contactar al proveedor de hosting con identificación legal
2. Acceder al servidor mediante credenciales de emergencia (custodiadas en sobre sellado)
3. Crear nuevo usuario SuperAdmin directamente en MongoDB:

```javascript
// Solo en emergencia con acceso directo al servidor
db.users.insertOne({
  id: UUID(),
  username: "emergencia_admin",
  password: "[HASH_BCRYPT_GENERADO]",
  role: "superadmin",
  is_active: true,
  must_change_password: true,
  created_at: new Date().toISOString(),
  created_by: "emergency_procedure"
});
```

4. Documentar el acceso y circunstancias
5. Revocar acceso de emergencia una vez SuperAdmin recupere control

---

## 7. CHECKLIST DE DESPLIEGUE

### Pre-Despliegue

- [ ] Variables de entorno configuradas (sin valores por defecto)
- [ ] JWT_SECRET de 64+ caracteres generado
- [ ] CORS_ORIGINS con dominios específicos (sin *)
- [ ] ENVIRONMENT="production"
- [ ] ENABLE_DOCS="false"
- [ ] Certificado SSL válido instalado
- [ ] MongoDB con autenticación habilitada
- [ ] Usuario de BD con permisos mínimos
- [ ] Firewall configurado (solo puertos necesarios)

### Post-Despliegue

- [ ] Acceso HTTPS funciona
- [ ] Redirección HTTP→HTTPS activa
- [ ] Headers de seguridad presentes (verificar con securityheaders.com)
- [ ] Login con credenciales incorrectas rechazado
- [ ] Rate limiting activo en /login
- [ ] Logs de auditoría registrándose
- [ ] Respaldo automático configurado y probado
- [ ] Alerta de prueba enviada a SuperAdmin

### Verificación de Seguridad

```bash
# Verificar headers de seguridad
curl -I https://novavision.clinica.gt/api/auth/me

# Verificar CORS
curl -X OPTIONS https://novavision.clinica.gt/api/auth/login \
  -H "Origin: https://sitio-malicioso.com" \
  -H "Access-Control-Request-Method: POST"
# Debe retornar error o sin header Access-Control-Allow-Origin

# Verificar rate limiting
for i in {1..10}; do
  curl -X POST https://novavision.clinica.gt/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}'
done
# Debe recibir 429 Too Many Requests después de 5 intentos

# Verificar token expirado
curl https://novavision.clinica.gt/api/auth/me \
  -H "Authorization: Bearer [TOKEN_VIEJO]"
# Debe retornar 401
```

---

## 8. CONTACTOS DE EMERGENCIA

| Situación | Contacto | Método |
|-----------|----------|--------|
| Incidente de seguridad | SuperAdmin | [Teléfono directo] |
| Fallo de servidor | Proveedor hosting | [Ticket/Teléfono] |
| Restauración de respaldo | SuperAdmin + Técnico | [Procedimiento documentado] |
| Violación de datos | Abogado + SuperAdmin | [Protocolo de notificación] |

---

## 9. HISTORIAL DE CAMBIOS

| Fecha | Versión | Cambio | Autor |
|-------|---------|--------|-------|
| 2026-08-18 | 1.0 | Documento inicial | Auditoría de Seguridad |

---

**FIN DEL DOCUMENTO**
