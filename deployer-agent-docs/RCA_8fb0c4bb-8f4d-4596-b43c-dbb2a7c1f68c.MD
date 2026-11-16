# RCA — "Ver paciente" deja de abrir el detalle tras 2-3 clics (admin.novavision.me)

## Problema reportado
Rol médico. En Agenda, "Ver paciente" (navigate a `/pacientes?id=<pacienteId>`) abre el detalle las primeras 2-3 veces y luego solo navega a la lista `/pacientes` sin detalle ni error visible.

## Ventana investigada
Run activo `8fb0c4bb-8f4d-4596-b43c-dbb2a7c1f68c` (tier_change a tier_1, live). Logs últimas ~12 h (cubre hoy 16-nov-2026). frontend_type = cloudflare.

## Hallazgos de PRODUCCIÓN (evidencia)

### 1. GET /api/patients/{id}: NO hay errores — todas 200 OK
- Consulta explícita de todas las líneas `GET /api/patients/<uuid>` **excluyendo "200 OK" → 0 resultados**. Cada fetch de detalle de paciente devolvió **200 OK**.
- Scan amplio de errores (`500|429|503|403|401|404|Traceback|Exception|ValidationError|OOM|Killed|exceeded`), 300 líneas: histograma `200:29, 401:1, 403:82, 404:188`. **Cero 500. Cero 429. Cero 503. Cero traceback.**
  - Los 404 son casi todos `GET /health HTTP/1.0` desde 127.0.0.1 (sonda interna a una ruta inexistente — ruido benigno).
  - Los 403 son todos `PATCH /api/evaluaciones/<id>/autoguardar` (problema de permiso de autoguardado, endpoint distinto, no relacionado).
  - El 401 es `GET /api/backups` (no relacionado).
- => El bug de serialización de `PatientResponse(**enriched)` con registros legados **NO se está disparando en producción**. `view_patients` funciona (los GET de detalle son 200).

### 2. Sin OOM / sin reinicios / sin alta latencia
- 2 réplicas, ambas `restart_count: 0`, estado `running`, `kill_findings: []`. Sin OOMKilled, sin terminación por Error.
- Deployment **subido de tier_0 (512Mi) a tier_1 hoy 05:39** → ahora 1Gi request / 2Gi limit, 2 réplicas, VPA activo. La preocupación previa de ~86% sobre 512Mi queda resuelta por el upgrade.
- Un pod reemplazado a las 12:55 con `restart_count 0` = reprogramación por VPA, **no un crash**.

### 3. Sin rate-limit de infraestructura
- Tráfico entra por edge de Cloudflare (172.68.x / 104.22-23.x) y todo devuelve 200. **No hay 429/503 en ninguna capa.** El límite global slowapi (200/min/IP) no se activó.

### 4. patient_id culpable de un 500
- No existe. No hay fallo de validación/serialización que atribuir a ningún documento.

## Causa raíz
El backend y la infraestructura están **sanos** para este flujo: todas las llamadas a `GET /api/patients/{id}` responden 200 OK, sin OOM/reinicios/throttling. Por lo tanto el fallo es **del lado del cliente (frontend)**, consistente con el patrón de código ya leído:

- `Pacientes.js` tiene un `useEffect` con dependencias vacías `[]` que lee el query param `id` **solo al montar el componente**. Cuando el router de React mantiene `Pacientes` montado entre navegaciones (o reutiliza la instancia), un nuevo `navigate('/pacientes?id=...')` cambia la URL pero **no vuelve a ejecutar el efecto**, así que el diálogo de detalle nunca se abre y el usuario queda en la lista. Esto explica el carácter intermitente ("funciona 2-3 veces y luego no").
- El `.catch(() => {})` vacío de `patientApi.getById` **oculta cualquier fallo en silencio** (sin toast ni log), por lo que aunque no haya error HTTP hoy, cualquier futura falla sería invisible.

NOTA: El bug es de enrutamiento/estado en React; no se reprodujo en preview (requiere ejecutar la SPA y simular navegación, sin datos de prod). Diagnóstico basado en evidencia de logs de producción + lectura de código.

## Fix recomendado (E1 / código)
1. En `Pacientes.js`: hacer que el efecto reaccione al cambio del query param `id` (p. ej. depender de `location.search` / `searchParams.get('id')` en vez de `[]`), para que cada navegación desde Agenda vuelva a abrir el diálogo de detalle. Alternativamente leer el `id` en cada render/en el handler de navegación.
2. Reemplazar el `.catch(() => {})` vacío por manejo real: `toast` de error + `console.error` (y manejar 404/403/500 explícitamente), para no volver a ocultar fallos.
3. Verificar en preview con un test de navegación repetida Agenda → Ver paciente (varias veces seguidas) tras el fix.

## Lo que NO se necesita
- No hay acción de secrets.
- No hay acción de tier (el upgrade a tier_1 ya resolvió el techo de memoria; sin evidencia de OOM en esta ventana).
- No hay acción de dominio/SSL ni de infraestructura.
