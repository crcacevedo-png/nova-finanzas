# RCA — NovaVision (novavision-finanzas) — Autoguardado y "Iniciar" en Agenda fallan SOLO en producción

## Resumen ejecutivo
Ambos síntomas tienen **la misma causa raíz** y **NO** es la validación del `response_model` (no hay 500 ni ValidationError en producción). La causa es de **CORS**: el middleware CORS de la app **no incluye el método `PATCH`** en `allow_methods`. Los dos endpoints afectados son `@router.patch(...)`, por lo que el navegador envía un **preflight OPTIONS** que Starlette rechaza con **400 "Disallowed CORS method"**. El PATCH real nunca llega al handler → el frontend interpreta el fallo como "guardado offline" (Síntoma 1) o muestra el toast "Error al cambiar estado" (Síntoma 2).

## Evidencia (logs de producción, run 1b8bbd6b-edac-4280-b483-2b3ffd6a8055, últimas 24h)
Preflight OPTIONS de los endpoints PATCH → **400 Bad Request** de forma sistemática:
```
OPTIONS /api/evaluaciones/{id}/autoguardar HTTP/1.1" 400 Bad Request
OPTIONS /api/agenda/citas/{cita_id}/estado HTTP/1.1" 400 Bad Request
```
Mientras que los demás verbos funcionan (mismo origen/credenciales, el preflight pasa):
```
POST /api/evaluaciones HTTP/1.1" 200 OK
PUT  /api/evaluaciones/{id} HTTP/1.1" 200 OK
OPTIONS /api/evaluaciones/{id} HTTP/1.1" 200 OK   (ruta base, sin /autoguardar)
OPTIONS /api/agenda/bloqueos ... / /api/doctors / /api/auth/me ... 200 OK
```
- Conteo de status en la ventana: 200, 400, 404 y un único 422 (`POST /api/patients`, no relacionado). **No hay ningún 500 ni ValidationError** en `.../autoguardar` ni en `.../estado`. Esto descarta la hipótesis del `response_model`: la petición PATCH **nunca llega al servidor**, se corta en el preflight.
- Que el origen esté permitido se demuestra porque GET/POST/PUT sí responden 200 al preflight; si el Origin estuviera bloqueado, TODOS los preflights darían 400. Lo único que se rechaza es el **método PATCH**.

## Causa raíz (código fuente, del run activo)
`backend/server.py` líneas 99-107:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],   # <-- falta "PATCH"
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)
```
Endpoints afectados (ambos son PATCH):
- `backend/routes/agenda.py:563` → `@router.patch("/citas/{cita_id}/estado", response_model=CitaResponse)`
- `backend/routes/evaluaciones.py:1585` → `@router.patch("/{evaluacion_id}/autoguardar", response_model=EvaluacionOftalmologicaResponse)`

Starlette `CORSMiddleware`, al recibir un preflight con `Access-Control-Request-Method: PATCH`, comprueba el método contra `allow_methods`; como `PATCH` no está, responde `400 "Disallowed CORS method"`. El `max_age=600` hace que el navegador cachee el preflight fallido hasta 10 min.

## Por qué funciona en preview y no en producción
En preview el PATCH se probó sin preflight cross-origin real (mismo origen / prueba directa sin cabecera `Origin`), por lo que el middleware CORS nunca evalúa el método y el happy-path responde 200. En producción (frontend Cloudflare + cabecera `Authorization` → petición "no simple") el navegador **obliga** al preflight OPTIONS, que la propia app rechaza. Es puramente un problema de configuración CORS, independiente de los datos.

## Fix recomendado (lo aplica E1 — cambio de código, redeploy)
Añadir `PATCH` a `allow_methods` en `backend/server.py`:
```python
allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
```
(o `allow_methods=["*"]`). Es un cambio de una línea, retrocompatible. Tras el redeploy, el preflight de `.../autoguardar` y `.../estado` devolverá 200 y el PATCH llegará al handler.

Nota: el endpoint `backend/routes/inventario.py:1366` `@router.patch("/productos/{producto_id}/estado")` sufre el mismo problema y quedará corregido con el mismo cambio.

## Lo que NO es necesario
Relajar los `response_model` a `Optional` NO resuelve esto (y podría enmascarar otros problemas): la validación nunca se ejecuta porque la petición se bloquea en el preflight. Si tras corregir CORS aparecieran 500 por documentos antiguos/parciales, se abordaría por separado — pero hoy no hay evidencia de ello en los logs de producción.

## Verificación
- Confirmado por logs de producción (patrón 400 en OPTIONS de ambos endpoints PATCH; 0 errores 5xx).
- Confirmado por inspección del código fuente del run activo (CORS sin PATCH; ambos endpoints son `@router.patch`).
- No se modificó ningún dato de producción.
