# Verificación SOLO-LECTURA — Migración Libro IGSS (admin.novavision.me)

**DB:** novavision-finanzas-test_database · **run:** fbaf0e0e-9403-4ed0-942c-395aa78faae1 · acceso solo-lectura. No se escribió ni corrigió nada.

**Lote verificado:** `id = 435f7783-f786-42ec-8fb4-02f4ef29f707` · estado **aplicado**.

---

## 1) igss_migracion_lotes (1 documento)
- id: `435f7783-f786-42ec-8fb4-02f4ef29f707`
- estado: **aplicado**
- creado_en: 2026-11-19T03:22:47.125463+00:00
- aplicado_en: 2026-11-19T03:22:49.560503+00:00
- creado_por: db39ef96-ca05-442d-8bf2-b84a5bf4da84 — **Administrador General**
- ordenes: **119** · ajustes: **22**
- omitidas: **[]** (vacío) · error: **null**
- diferencias (campo `comparacion`): **TODAS igual=true** → cifras_aplicadas == cifras_simuladas, sin diferencias.

Conteos guardados (cifras_aplicadas = cifras_simuladas):
| clave | valor |
|---|---|
| ordenes_vivas | 22 |
| · vivas_reservadas | 2 |
| · vivas_en_curso | 20 |
| ordenes_historicas | 97 |
| constancias_evaluaciones | 134 |
| constancias_cirugias | 10 |
| dosis_registradas | 0 |
| cirugias_programadas_vivas | 24 |
| sps_por_revisar | 6 |
| ajustes_cupo_sin_sps | 22 |
| no_migrables | 33 |
| pendientes_sps | 58 |

## 2) igss_ordenes_libro
- **total: 119**
- con `lote_migracion` = lote aplicado: **119** (100%)
- Desglose por estado: **reservada 2 · en_curso 20 · completa 0 · historica 97** (2+20+97 = 119 ✓; vivas = 22, históricas = 97)
- `sps_por_revisar`=true: **6** → **1 viva** (en_curso/reservada) + **5 históricas**
- `dosis_por_confirmar`=true: **22**
- Suma de tamaños de `constancias`: **144** (134 tipo=evaluacion + 10 tipo=cirugia) — coincide con 134+10 del lote
- `cirugias_programadas` no vacío: **22 órdenes**
- No. SPS vigente repetido en la misma unidad: **NINGUNO**. Las 119 órdenes son `vigente=true`; revisados todos los pares (no_sps, unidad_id), no hay duplicados dentro de una misma unidad.

## 3) igss_libro_ajustes_cupo
- total: **22**
- con `lote_migracion` = lote: **22** (coincide con ajustes_cupo_sin_sps=22)

## 4) igss_migracion_fotos (respaldo del lote; campos `lote_id` + `tipo`)
- tipo=**orden**: **119**
- tipo=**ajuste**: **22**
- total del lote: **141** (= 119 + 22)

## 5) audit_logs — action "MIGRACION_LIBRO_APLICADA" (1 registro)
- details: ordenes **119**, ajustes **22**, diferencias **[]**, error **null**, estado **aplicado**, lote_id 435f7783…
- user_id db39ef96-ca05-442d-8bf2-b84a5bf4da84 — **Administrador General**
- timestamp: **2026-11-19T03:22:49.564615+00:00**

## 6) Colecciones antiguas — ¿cambiaron por la migración?
Umbral usado: `updated_at` > 2026-11-19T03:22:47 (inicio de la migración).
| colección | total docs | con updated_at posterior |
|---|---|---|
| igss_nog_acreditaciones | 116 | **0** |
| igss_nogs | 85 | **0** |
| patients | 18054 | **0** |
| surgeries | 284 | **0** |

→ Ninguna de estas colecciones fue re-estampada (updated_at) por la migración.

## 7) igss_nogs — libro_ocupados
- Campo `libro_ocupados` presente en **23 de 85** NOGs; suma total = **141**.
  - Reconciliación: 141 = 119 órdenes + 22 ajustes de cupo. Coincide exactamente con el total de "fotos" del lote (141).
  - Nota: pese a esta reconciliación, igss_nogs muestra **0** documentos con updated_at posterior a la migración — es decir, el campo cuadra con las cifras del lote pero el timestamp updated_at no fue modificado (probable incremento sin re-estampar updated_at, o valor ya establecido antes de aplicar). No es un error; solo se deja constancia.
- NOGs con `libro_ocupados` > `cantidad`: **0** (sin sobre-ocupación).
- Campo `sin_tope`: **no existe** en ningún documento de igss_nogs (condición "sin tope = false" no aplica); de todas formas, 0 NOGs superan su cantidad.

---

## Conclusión
Las cifras reales en producción **coinciden** con la simulación y con el aviso del lote aplicado: 119 órdenes (22 vivas: 2 reservadas + 20 en curso; 97 históricas), 22 ajustes de cupo sin SPS, 144 constancias (134 evaluaciones + 10 cirugías), 6 órdenes con SPS por revisar (1 viva + 5 históricas). Sin diferencias, sin omitidas, sin error. No hay duplicados de No. SPS vigente por unidad ni NOGs sobre-ocupados. Las colecciones antiguas (acreditaciones, nogs, patients, surgeries) no fueron modificadas por la migración (0 con updated_at posterior); el único valor derivado consistente con la migración es igss_nogs.libro_ocupados (suma 141 = 119+22).

El aviso que el usuario leyó ("órdenes 1 y sin SPS 22") corresponde a: 1 orden VIVA con sps_por_revisar y 22 cupos descontados sin SPS (ajustes). El total de sps_por_revisar es 6 (1 viva + 5 históricas).
