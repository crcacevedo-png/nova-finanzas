# NovaVisión ERP — Ventas por área, Historial de Cierres y Análisis de Producción

Tres mejoras para que la administración entienda y audite las ventas de la clínica:
separar las ventas del día por área, convertir el historial de cierres en una herramienta de comparación entre cajeros, y crear un área de análisis de producción.

## Para quién es
Para el superadministrador de la clínica, que necesita ver de dónde viene cada quetzal, comparar el desempeño de los cajeros y analizar qué se vende. El personal de caja y los demás usuarios no entran a estas vistas de análisis.

## Funciones principales y experiencia

### 1. Ventas del Día por área (Dashboard)
- La tarjeta "Ventas del Día" del Dashboard se divide en dos cifras: **Clínica** y **Óptica**, además del total.
- Cada cifra muestra su monto y la cantidad de ventas, para identificar rápidamente la fuente.

### 2. Historial de Cierres con comparación de cajeros (solo superadmin)
- El superadministrador ve los cierres de **todos los cajeros** (hoy solo ve los suyos), no solo los propios.
- Cada fila muestra fecha, cajero, estado, apertura, ingresos, egresos, efectivo contado y diferencia de arqueo.
- **Corrección del "no cuadra":** la columna de ingresos se recalcula a partir de los movimientos reales de caja de ese cajero en ese día (la misma fuente que el resumen de "Todas las cajas"), en lugar de un valor guardado que quedaba en cero o desfasado. Las cajas aún abiertas muestran su total en vivo en lugar de Q0.00.
- Cada cierre se puede abrir para ver un detalle con el desglose por tipo de ingreso (efectivo vs. otros métodos), para que el número sea verificable.
- Un resumen comparativo arriba de la tabla: por cada cajero, total vendido, número de ventas y diferencia acumulada de arqueo.

### 3. Área de Análisis de Producción (nuevo menú, solo superadmin)
Nueva sección en el menú de Finanzas, enfocada en las ventas de clínica (Punto de Venta). Incluye un selector de período: **Hoy / Esta semana / Este mes / Rango personalizado**. Dentro:
- **Indicadores clave:** total vendido, número de ventas y ticket promedio del período.
- **Top productos** en dos vistas: por ingresos (Q) y por unidades vendidas.
- **Ventas por cajero / vendedor:** ranking con monto y número de ventas por persona.
- **Ventas por médico que refiere:** monto y número de ventas asociadas a cada médico.
- **Ventas por categoría de producto:** distribución del total entre categorías.
- **Tendencia por día:** gráfica de la evolución de las ventas en el período seleccionado.

## Flujo de uso
- **Dashboard:** el superadministrador abre el Dashboard y ve de inmediato cuánto se vendió en clínica y cuánto en óptica.
- **Cierres:** en Mi Caja → Historial de Cierres, el superadministrador revisa los cierres de todos los cajeros, compara su desempeño y verifica que los ingresos coincidan con lo esperado.
- **Análisis:** desde el menú de Finanzas entra a Análisis de Producción, elige un período y revisa qué se vende más, quién vende más, qué médico refiere más y cómo evolucionan las ventas.

## Sensación visual (UI/UX)
Se mantiene el estilo actual del ERP (marca NovaVisión, tarjetas limpias, tablas claras, acentos en azul). Las cifras clave se destacan en tarjetas; los rankings se muestran como tablas ordenables; la tendencia como una gráfica sencilla. Todo en español, con montos en quetzales (Q).

## Fases de implementación

### Fase 1 — MVP (se construye ahora)
- Dashboard: ventas del día separadas en Clínica y Óptica (con total).
- Historial de Cierres para superadmin: ver todos los cajeros, ingresos recalculados de forma correcta (arreglo del "no cuadra"), detalle con desglose por tipo de ingreso y resumen comparativo por cajero.
- Área Análisis de Producción (solo superadmin, menú Finanzas) con filtro de período y: indicadores clave (total, # ventas, ticket promedio), top productos (por ingresos y por unidades), ventas por cajero/vendedor, ventas por médico, ventas por categoría, y gráfica de tendencia por día. Solo ventas de clínica.

### Fase 2 — Futuro
- Análisis por método de pago (efectivo vs. tarjeta vs. otros) y desglose de cobrado vs. crédito.
- Exportar reportes a Excel/PDF e impresión de los cierres y del análisis.
- Comparativa entre períodos (p. ej. este mes vs. mes anterior) y metas de venta.

### Fase 3 — Futuro
- Incluir óptica en el área de análisis.
- Rentabilidad/márgenes (costo vs. precio) por producto y categoría.
- Análisis por responsable de cuentas por cobrar y alertas automáticas de desempeño.

## Supuestos
- El área de análisis cubre **solo ventas de clínica** (Punto de Venta); se excluye óptica (reservada para una fase posterior). *(Confirmado por el usuario.)*
- El acceso al análisis y a la comparación de cajeros es **exclusivo del superadmin**. *(Confirmado por el usuario.)*
- Las métricas incluidas son: top productos (ingresos y unidades), ventas por cajero/vendedor, tendencia por día + ticket promedio + # de ventas, ventas por médico que refiere y por categoría. **No** se incluye "ventas por método de pago" en la Fase 1 (pasa a Fase 2). *(Según la selección del usuario.)*
- El problema de "ingresos que no cuadran" se resuelve recalculando en vivo los ingresos de cada cierre a partir de los movimientos reales de caja (misma fuente que el consolidado "Todas las cajas"), que es la cifra de referencia correcta.
- Para "ventas por categoría" se toma la categoría desde el catálogo de productos (las ventas guardan el producto, no la categoría directamente); los productos sin categoría se agrupan como "Sin categoría".
- "Vendedor" y "cajero" se tratan como la misma persona (quien registra la venta en el POS), ya que así se registra hoy en el sistema.
- El historial de cierres sigue mostrando los cierres de clínica; cada cajero no-superadmin sigue viendo solo los suyos.
- Los montos se muestran en quetzales y las fechas usan la zona horaria de Guatemala, como en el resto del sistema.
