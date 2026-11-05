# Sociedades Médicas: consumos por venta, informes mensuales y acceso de administrador

El módulo de Sociedades Médicas debe reflejar los productos de sociedad que se venden en el Punto de Venta, permitir descargar ese detalle en Excel/PDF por mes, y abrir correctamente para el administrador.
Hoy el módulo muestra cero consumos aunque haya ventas, y al administrador el botón "Sociedades" lo lleva a Pacientes.

## Para quién es
- Administrador y superadministrador de la clínica, que dan seguimiento a lo que cada sociedad (p. ej. NIDEK, FAROS) genera por los productos de alquiler/uso que tiene asignados.

## Funcionalidades principales y experiencia
1. **Conteo de consumos a partir de las ventas.**
   - Cada vez que se vende en el Punto de Venta de clínica un producto asignado a una sociedad, esa venta cuenta como un consumo de la sociedad.
   - El monto registrado por cada consumo es el **precio de venta** cobrado en esa venta (no el costo).
   - Funciona también para productos de alquiler/servicio que no manejan existencia (los que aparecen con "∞"), que es justamente lo que hoy no se contabiliza.
   - El conteo considera las ventas ya existentes en el sistema, no solo las futuras: al corregirlo, el histórico de ventas de productos de sociedad aparece de inmediato.
   - Las ventas anuladas no cuentan.
2. **Tarjetas y pestañas actualizadas.**
   - Las tarjetas "Total Consumos" (unidades) y "Costo Total" (ahora monto vendido) reflejan las ventas de productos de sociedad del período.
   - La pestaña "Consumos" lista cada venta: fecha, producto, sociedad, cantidad y monto.
   - La pestaña "Resumen" muestra el consolidado por producto del mes elegido.
   - Los filtros por sociedad, por producto y por rango de fechas siguen funcionando sobre esta nueva información.
3. **Exportación de informes mensuales (Excel y PDF).**
   - Los botones "Excel" y "PDF" descargan el informe del mes y año seleccionados con el mismo detalle de consumos por venta.
   - Respetan el filtro de sociedad activo y, si se usa, el rango de fechas.
4. **Corrección del acceso del administrador.**
   - El botón "Sociedades" abre el módulo para el administrador (hoy lo redirige a Pacientes por una regla de acceso que no coincide con lo que muestra el menú).
   - El acceso queda disponible para administrador y superadministrador, igual que el menú ya lo ofrece.

## Flujo de uso
1. El administrador entra a Inventario → Sociedades y el módulo abre correctamente.
2. Ve en las tarjetas el total de unidades y el monto vendido de productos de sociedad del período.
3. En "Consumos" revisa cada venta registrada; puede filtrar por sociedad, producto y fechas.
4. En "Resumen" elige mes y año para ver el consolidado por producto.
5. Con los botones "Excel"/"PDF" descarga el informe del mes seleccionado.

## Sensación de UI/UX
- Se mantiene la apariencia actual del módulo (encabezado morado, tarjetas, pestañas Sociedades/Consumos/Productos/Resumen).
- No se agregan pantallas nuevas; cambia el origen de los datos para que incluya las ventas, y se corrige el acceso.

## Fases de implementación
- **Fase 1 (MVP, se construye ahora):**
  - Contabilizar como consumo de sociedad cada venta del Punto de Venta de clínica de un producto asignado a una sociedad, valuada al precio de venta (incluye histórico y productos sin existencia).
  - Actualizar tarjetas, pestañas "Consumos" y "Resumen" y los filtros para reflejar esa información.
  - Hacer que la exportación Excel/PDF mensual use ese mismo detalle.
  - Corregir el acceso al módulo para el administrador.
- **Fase 2 (posterior):**
  - Desglose y totales por sociedad (ranking de sociedades por monto, no solo por producto) y comparación entre meses.
- **Fase 3 (posterior):**
  - Programación de envío automático del informe mensual por correo a cada sociedad o al administrador.

## Supuestos
- Solo cuentan las ventas del Punto de Venta de clínica; no se incluyen ventas de óptica ni salidas/ajustes/bajas manuales de inventario.
- El monto de cada consumo es el precio de venta cobrado en esa línea de venta; "Costo Total" pasa a representar el monto vendido.
- Las ventas anuladas se excluyen del conteo.
- Un producto se considera "de sociedad" cuando está marcado como tal y tiene una sociedad asignada (como hoy en la pestaña Productos).
- El acceso al módulo queda para administrador y superadministrador; no se amplía a otros roles.
- Se mantienen las pestañas, filtros y diseño actuales; no se crean pantallas nuevas.
