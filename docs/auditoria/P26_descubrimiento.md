# Prompt 26 — Fase 0: Documento de Descubrimiento

**Fecha**: 2026-10-06 | **Entorno**: Preview/Dev (`test_database`, Mongo local) | **Alcance**: Solo lectura en producción; pruebas con datos sintéticos (`AUD26-*`) ya purgados.

## 1. Mapa de colecciones

| Colección | Campos clave | `origen` | `paciente_id` | Índices únicos relevantes |
|---|---|---|---|---|
| `patients` | `id`, `record_number`, `dpi` | sí (implícito, 1 solo origen clínico) | — | `id_lookup`; dpi no es único a nivel de índice (ver hallazgo) |
| `productos_inventario` | `id`, `codigo`, `precio_compra`, `precio_venta`, `costo_promedio`, `ultimo_costo` | sí | n/a | `id_lookup` |
| `bodegas_inventario` | `id`, `es_punto_venta`, `origen` | sí | n/a | — |
| `lotes_inventario` | `id`, `producto_id`, `costo_unitario`, `cantidad_disponible`, `fecha_vencimiento` | sí | n/a | — |
| `existencias_inventario` | `producto_id`, `bodega_id`, `cantidad` | sí | n/a | compuesto producto+bodega (no único declarado, usa upsert) |
| `movimientos_inventario` (kardex) | `tipo`, `cantidad`, `costo_unitario`, `costo_total`, `existencia_anterior/nueva`, `referencia_tipo/id` | sí | n/a | inmutable (sin UPDATE/DELETE expuesto) |
| `suppliers` | `id`, `name` (único) | n/a | n/a | único por `name` |
| `ordenes_compra` | `id`, `estado` (borrador/autorizada/parcial/recibida/cancelada), `items[].cantidad_recibida` | sí | n/a | — |
| `recepciones_inventario` | `id`, `orden_compra_id`, `total_costo`, `gasto_id` (siempre `null` en la práctica) | sí | n/a | — |
| `ventas` (POS clínica) | `id`, `numero_venta`, `items[].lotes_consumidos[].costo_unitario`, `total`, `cxc_id` | `clinica` fijo | sí (opcional) | — |
| `optica_sales` | ventas de óptica (estructura distinta) | n/a (es el módulo óptica) | sí (`client_id`/paciente) | — |
| `cuentas_por_cobrar` | `id`, `origen`, `monto_total`, `monto_pagado`, `saldo_pendiente`, `estado`, **dos campos de historial de pago**: `abonos[]` (usado por `/cxc`) y `pagos[]` (usado por `/cuentas-cobrar`) | `clinica`/`optica` | opcional | ninguno — **`paciente_id`/`tipo_pagador_id` son `Optional` al crearse pero `response_model` los exige como `str`** (hallazgo H-01) |
| `responsables_cxc` | `id`, `nombre`, `tipo` | n/a | n/a | — |
| `expenses` (gastos) | `id`, `status` (pendiente/parcial/pagado/vencido), `paid_amount`, `remaining_amount` | n/a (gasto de empresa, no por origen) | n/a | — |
| `payments` | `id`, `expense_id`, `amount` — **se crea sin referencia a ninguna autorización** | n/a | n/a | — |
| `payment_authorizations` | `id`, `expense_id`, `status` (pendiente/ejecutado/cancelado), `amount_to_pay` | n/a | n/a | único "pendiente" por `expense_id` |
| `bank_accounts` | `id`, `bank_name` | n/a | n/a | — |
| `caja_cierres` (cierre diario) | `fecha`, `estado` (Abierto/Cerrado), `bloqueado` (vía movimientos) | `clinica` | n/a | único por fecha+origen (implícito) |
| `caja_movimientos` | `tipo` (Ingreso/Egreso), `categoria`, `monto`, `bloqueado` | `clinica` | opcional | — |
| `cierres_financieros` (cierre mensual/semestral) | `tipo`, `periodo`, `ingresos_caja`, `egresos_caja`, `resultado_neto`, `estado` (Borrador — nunca se sella) | `clinica` | n/a | único por `tipo`+`periodo` |

## 2. Diagramas de estado (tal como está implementado)

- **Venta (POS)**: `creada` → (sin más estados; no hay devoluciones, solo `anular_venta` con reverso de inventario).
- **CxC**: `Pendiente` → `Parcial` → `Pagado` | `Vencido` (por fecha) | `Anulado` (solo si `monto_pagado == 0`).
- **Orden de compra**: `borrador` → `autorizada` → `parcial`/`recibida` (según recepciones) | `cancelada`.
- **Gasto (`expenses`)**: `pendiente` → `parcial` → `pagado` | `vencido`. Se alcanza por **dos caminos independientes**: (a) `payment_authorizations` (pendiente→ejecutado) que crea un `payment`, o (b) `POST /payments` **directo, sin autorización previa** (ver hallazgo H-06).
- **Cierre de caja diario**: `Abierto` → `Cerrado` (bloquea movimientos del día) → `Abierto` de nuevo vía `POST /caja/cierres/{id}/reabrir` (solo SuperAdmin) — **viola la regla cerrada "cierres diarios inmutables"** (hallazgo H-07).
- **Cierre financiero (mensual/semestral)**: se crea en estado `"Borrador"` y **no tiene transición a un estado sellado**: `PUT` y `POST /recalcular` lo modifican libremente en cualquier momento; `DELETE` (SuperAdmin) lo elimina. No existe un "cierre financiero cerrado/sellado".

## 3. Origen literal de cada cifra financiera (núcleo de la auditoría)

| Cifra mostrada | Dónde se muestra | Archivo / función / línea | Fórmula literal | Colección/campo que lee |
|---|---|---|---|---|
| "Total Ingresos Cobrados" | Dashboard Financiero (`/dashboard-financiero`) | `routes/dashboard_financiero.py::get_dashboard_financiero` L81-110 | `total_ingresos (caja_movimientos tipo=Ingreso) + ingresos_cxc_periodo (cuentas_por_cobrar.abonos[] en rango)` | `caja_movimientos`, `cuentas_por_cobrar.abonos` |
| "Balance Neto" (dashboard) | Dashboard Financiero | `dashboard_financiero.py` L152 | `total_ingresos_cobrado - gastos_pagados` | igual que arriba + `expenses.paid_amount` |
| "Resultado Neto" (cierre mensual/semestral) | Caja → Cierres Financieros | `routes/caja.py::calcular_cierre_financiero` L785-807 | `ingresos_caja (caja_movimientos tipo=Ingreso) - egresos_caja (caja_movimientos tipo=Egreso)` | `caja_movimientos` **únicamente** |
| "Margen %, Ganancia/unidad" | Inventario → Rentabilidad (por categoría) | `routes/inventario.py::reporte_rentabilidad_categorias` L2308-2316 | `(precio_venta - (precio_compra o costo_promedio)) / precio_venta * 100` sobre el **catálogo actual**, no sobre ventas reales | `productos_inventario.precio_compra/costo_promedio/precio_venta` |
| "Ingresos Brutos / Costo Total / Ganancia Neta" (Evolución Mensual) | Inventario → Rentabilidad → Evolución Mensual | `routes/inventario.py::reporte_rentabilidad_historico` L2449-2563 | Intenta `ventas_optica` (vacío para clínica) y cae a `movimientos_inventario` tipo=`venta`: `ingresos = precio_venta_actual_del_catalogo × cantidad`; `costo = (precio_compra o costo_promedio_ACTUAL) × cantidad` | `movimientos_inventario` + `productos_inventario` (valores **actuales**, no históricos) |
| "Margen/Ganancia" Óptica | Óptica → Dashboard → Rentabilidad | `routes/optica.py::get_rentabilidad_optica` L1607-1700+ | `Σ precio_venta_linea - Σ cost_price_catalogo_ACTUAL` | `optica_sales`, `optica_frames/contact_lenses/lens_types.cost_price` |
| Costo por unidad al momento de vender | Kardex (no expuesto en ningún reporte de utilidad) | `routes/inventario.py::crear_movimiento_kardex` / `descontar_inventario` | Snapshot correcto (`costo_unitario` del lote FEFO o `costo_promedio` vigente) | `movimientos_inventario.costo_unitario`, `ventas.items[].lotes_consumidos[].costo_unitario` |

**Conclusión de la Fase 0**: existen **tres fuentes de "utilidad" totalmente independientes y ninguna resta costo de ventas de forma consistente ni usa el costo histórico correcto**: (1) Dashboard Financiero (ingresos de caja, sin costo), (2) Cierre Financiero mensual/semestral (ingresos − egresos de caja, sin costo, e ignora gastos pagados fuera de `caja_movimientos`), (3) Reporte de Rentabilidad de Inventario (sí resta costo, pero usa catálogo actual, no histórico, y para clínica usualmente cae al *fallback* de kardex). Óptica tiene su propio cálculo de margen, aislado y no consolidado con clínica.

## 4. ¿Hay snapshot de costo por línea de venta?

**Sí, a nivel de kardex** (`movimientos_inventario.costo_unitario`, y `ventas.items[].lotes_consumidos[].costo_unitario`), con el valor correcto vigente al momento de la venta (lote FEFO o costo promedio). **Pero ningún reporte de utilidad usa esta fuente** — todos leen el costo *actual* del catálogo (`productos_inventario.precio_compra`/`costo_promedio`), lo que retro-calcula la utilidad histórica cada vez que cambia el costo promedio.

## 5. Costeo de servicios clínicos

`routes/evaluaciones.py` y `routes/surgeries.py` **no tienen ningún campo de costo, honorario ni receta de insumos**. Toda consulta, procedimiento o cirugía registrada entra al ingreso (vía `caja_movimientos`/CxC) con **costo cero implícito**, sin marcarse como "sin costear" en ningún reporte.

## 6. IVA y origen

Confirmado: `item_subtotal` en `ventas.py` se trata como **neto** (antes de IVA) y el 12% se suma para obtener el total — comportamiento correcto para separar impuesto de ingreso, siempre que el precio neto cargado en el POS sea el correcto (no verificado contra el precio público con IVA incluido, responsabilidad de captura).
