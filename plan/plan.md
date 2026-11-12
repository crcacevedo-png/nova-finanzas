# Desglose de Producción por Médico que Refiere

En el Dashboard Financiero, la lista "Ventas por médico que refiere" se vuelve interactiva: al hacer clic en el nombre de un médico se abre el detalle completo de su producción, con filtro de fechas propio y exportación a Excel.

## Para quién es

Administradores y Superadministradores que hoy consultan el Dashboard Financiero y la lista "Ventas por médico que refiere", y necesitan ver el detalle detrás de cada monto sin tener que buscarlo manualmente en otras pantallas.

## Funcionalidad principal y experiencia

- En la lista "Ventas por médico que refiere" (la misma que ya existe hoy en el Dashboard Financiero), el **nombre de cada médico se vuelve clicable**.
- Al hacer clic se abre un desglose con:
  - Nombre del médico y el rango de fechas que se está mostrando.
  - Un resumen con el total de artículos/servicios y el monto total de ese rango.
  - Una tabla con **una fila por cada producto o servicio vendido** que esté asociado a ese médico (si una venta tuvo 3 artículos, aparecen 3 filas). Cada fila muestra: fecha, número de venta, paciente, producto o servicio, cantidad y monto.
- El desglose **abre con el mismo rango de fechas que ya se está viendo en el Dashboard Financiero** en ese momento (por ejemplo, si el dashboard muestra "este mes", el desglose abre mostrando ese mismo mes).
- Dentro del desglose, se puede **cambiar el rango de fechas** (por ejemplo, para ver otro mes o un rango personalizado) sin tener que cerrar la ventana; la tabla y los totales se actualizan según el nuevo rango elegido.
- Botón para **exportar a Excel** el contenido del desglose tal como se está viendo (con el rango de fechas seleccionado en ese momento), incluyendo el resumen de totales.
- Solo "Ventas por médico que refiere" obtiene esta función por ahora; la lista "Ventas por cajero" y el resto del Dashboard Financiero quedan exactamente igual que hoy.

## Flujo de uso

1. El usuario entra al Dashboard Financiero y ve la lista "Ventas por médico que refiere" con el período que ya tenía seleccionado.
2. Hace clic sobre el nombre de un médico.
3. Se abre el desglose de ese médico, ya filtrado con el mismo período del dashboard, mostrando el resumen de totales y la tabla de artículos/servicios vendidos.
4. Si quiere revisar otro período, cambia el rango de fechas dentro del desglose; la tabla y los totales se recalculan.
5. Si necesita el detalle para otro uso (reportes, respaldo, revisión contable), presiona "Exportar a Excel" y descarga el archivo con lo que está viendo en pantalla.
6. Cierra el desglose y vuelve al Dashboard Financiero, que permanece sin cambios.

## UI/UX feel

Mismo estilo visual que el resto del sistema: el desglose se presenta como un panel/ventana sobre el Dashboard Financiero (sin navegar a otra pantalla), con una tabla clara, totales destacados en la parte superior y un selector de fechas sencillo. El nombre del médico se distingue visualmente como elemento clicable (por ejemplo, subrayado o con un color distinto al pasar el mouse) para que sea evidente que se puede abrir el detalle.

## Fases de implementación

**Fase 1 — MVP (se construye ahora)**
- Nombre del médico clicable en "Ventas por médico que refiere".
- Desglose con una fila por producto/servicio vendido, resumen de totales, filtro de fechas propio que inicia con el período del dashboard y se puede cambiar.
- Exportación a Excel del desglose filtrado.

**Fase 2 — Acceso directo a la venta completa**
- Desde una fila del desglose, poder abrir el detalle completo de esa venta (todos los artículos de esa venta, forma de pago, etc.), no solo la fila de ese médico.

**Fase 3 — Extender a otras listas**
- Aplicar esta misma función de clic + desglose + exportar también a "Ventas por cajero" y a otras listas similares del Dashboard Financiero.

## Supuestos

- "Producción" de un médico corresponde a las ventas donde ese médico está registrado como médico que refiere, exactamente el mismo criterio que ya usa la lista actual para calcular sus totales — no se agrega ni se excluye ninguna venta por otro criterio.
- El archivo Excel incluye las mismas columnas que se ven en pantalla (fecha, número de venta, paciente, producto/servicio, cantidad, monto) más el resumen de totales.
- El acceso al desglose queda disponible para los mismos roles que ya pueden ver hoy el Dashboard Financiero; no se amplía ni se restringe el acceso a nadie más.
- El selector de fechas del desglose es independiente: cambiarlo dentro del desglose no modifica el período que se está viendo en el resto del Dashboard Financiero.
- La fila "Sin médico" (ventas sin médico que refiere asignado) también es clicable y muestra su propio desglose, igual que cualquier otro nombre de la lista.
