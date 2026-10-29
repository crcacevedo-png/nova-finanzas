# IVA incluido en el precio — en todo el sistema

El precio que se ingresa al registrar un producto es el precio final al público y ya lleva el IVA adentro.
El sistema deja de sumar el 12% por encima en cualquier venta; el IVA pasa a calcularse como la parte que ya viene incluida en ese precio.

## Para quién es
Personal de la clínica y de la óptica que cobra en los puntos de venta, y quien lleva la contabilidad y necesita conocer el IVA de cada venta sin que ese impuesto altere el precio cobrado al cliente.

## Qué cambia y cómo se experimenta
- **El precio es el precio.** Lo que se teclea como precio de un producto es lo que paga el cliente. El sistema nunca le agrega un 12% adicional.
- **El total cuadra a la vista.** En el punto de venta de clínica, el Total es la suma de los precios menos el descuento. Ya no aparece una diferencia inexplicable entre el subtotal, el descuento y el total.
- **El IVA se calcula “hacia adentro”.** Para efectos contables, cada venta guarda el monto de IVA que ya venía incluido en el precio (la parte correspondiente al 12% dentro del precio final), sin modificar el total cobrado.
- **Se elimina la marca “afecto a IVA”** de la pantalla de ingreso y edición de productos. Todos los productos se tratan como precio final con IVA incluido.
- **El IVA sigue oculto en pantalla y en tickets.** Al cobrar y en los comprobantes impresos solo se muestran el detalle de productos, el descuento (si lo hay) y el total. El monto de IVA queda guardado para contabilidad, no se despliega al cliente.
- **Aplica a los dos puntos de venta.** Tanto el punto de venta de clínica como el de óptica quedan bajo la misma regla: precio final sin sumar IVA, y registro del IVA incluido para contabilidad.

## Flujo de uso
1. En el ingreso de productos ya no se ve la casilla de “afecto a IVA”; se captura el precio final del producto.
2. En el punto de venta se agregan productos; el carrito muestra el subtotal con esos precios.
3. Se aplica (opcionalmente) el descuento por porcentaje con su autorizador, como ya funciona hoy.
4. El Total mostrado = suma de precios − descuento. No se añade ningún 12%.
5. Al confirmar la venta, el sistema guarda, además del total, el monto de IVA que ya estaba incluido en ese total (para contabilidad).
6. El ticket y el detalle de la venta muestran productos, descuento y total, sin línea de IVA.

## Sensación de la interfaz
Sin cambios de estilo. Se mantiene la apariencia actual (tema teal, tarjetas y tablas). El punto de venta de clínica se ve más limpio y coherente: subtotal, descuento y total que sí cuadran entre sí.

## Fases de implementación

### Fase 1 — MVP (se construye ahora)
- El sistema deja de sumar el 12% en las ventas; el total pasa a ser la suma de los precios menos el descuento.
- Cada venta (clínica y óptica) guarda el IVA como la parte incluida en el precio (precio − precio/1.12), calculada después del descuento.
- Se elimina la marca “afecto a IVA” del ingreso y edición de productos; todos los productos se tratan como precio con IVA incluido.
- Se mantiene el IVA oculto en pantalla y tickets; solo total y descuento visibles.
- Las ventas ya registradas no se recalculan: conservan sus cifras originales.

### Fase 2 — Visibilidad contable (futuro)
- Reporte de IVA por período (ventas, IVA incluido, descuentos) para clínica y óptica.
- Exportación de ese reporte para contabilidad.

### Fase 3 — Facturación electrónica (futuro)
- Integración con facturación electrónica (FEL Guatemala) usando el esquema de IVA incluido ya establecido.

## Supuestos
- Los precios ya cargados en los productos se consideran finales con IVA incluido; no se migran ni se modifican.
- Al quitar la marca “afecto a IVA”, todos los productos quedan tratados como IVA incluido; cualquier producto que antes estuviera marcado como exento pasará a calcular su IVA incluido como precio − precio/1.12.
- El IVA guardado por venta se calcula sobre el total ya con descuento aplicado.
- Las ventas históricas conservan los montos con los que se registraron (no se recalculan).
- La regla aplica a los dos puntos de venta; la óptica, que hoy no guardaba IVA, pasará a guardar el IVA incluido para mantener consistencia contable.
- Los reportes o exportaciones que hoy mostraran un IVA sumado reflejarán en su lugar el IVA incluido.
- El descuento por porcentaje con autorizador, implementado antes, se mantiene tal cual.
