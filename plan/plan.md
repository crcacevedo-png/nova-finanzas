# Precio variable en el Punto de Venta de Clínica

Permite que, al momento de vender, el cajero cambie el precio de cualquier artículo del inventario por uno distinto al de lista.
La venta queda registrada igual que siempre, pero deja constancia interna de que ese artículo se vendió a precio variable y guarda el precio aplicado.

## Para quién es
Personal de la clínica que cobra en el punto de venta de clínica y necesita, en casos puntuales, cobrar un artículo a un precio distinto del precio de lista sin perder el registro ni el control del costo.

## Qué cambia y cómo se experimenta
- **Un ícono por cada artículo del carrito.** Al agregar un producto a la venta, junto a su precio aparece un ícono (por ejemplo, una etiqueta/lápiz) que activa el modo de precio variable para ese artículo.
- **Ajuste del precio en línea.** Al activar el ícono, el precio del artículo se vuelve editable y el cajero teclea el nuevo precio. El total de la venta se recalcula al instante.
- **Mínimo protegido por el costo.** El precio variable puede ser desde el precio de costo registrado en inventario hacia arriba, sin tope superior. Puede quedar por encima del precio de lista normal.
- **Bloqueo si es menor al costo.** Si el cajero intenta dejar un precio menor al costo del artículo, el sistema avisa y no permite continuar con la venta hasta corregirlo.
- **Disponible para todos.** Cualquier usuario del punto de venta de clínica puede activar el precio variable; no requiere autorización ni nombre de quien lo aprueba.
- **Constancia interna en el registro.** La venta se guarda como de costumbre (el artículo de inventario, su cantidad, su descuento de inventario, etc.) y además deja marcado internamente que ese renglón fue precio variable y cuál fue el precio aplicado frente al precio de lista.
- **No aparece en el comprobante.** El ticket y el detalle que se entrega al cliente muestran el precio cobrado como cualquier otro renglón; no indican que fue precio variable ni muestran el precio de lista original. La marca de precio variable queda solo en el registro interno.
- **Solo clínica.** Esta funcionalidad existe únicamente en el punto de venta de clínica. El punto de venta de óptica no cambia.

## Flujo de uso
1. El cajero agrega artículos al carrito de la venta de clínica, como siempre.
2. En el renglón de un artículo, toca el ícono de precio variable.
3. El precio de ese renglón se vuelve editable; el cajero escribe el nuevo precio.
4. Si el precio es igual o mayor al costo, se acepta y el total se actualiza. Si es menor al costo, el sistema avisa y pide corregir.
5. El cajero puede aplicar el precio variable a más de un artículo, y también el descuento por porcentaje ya existente, que se calcula sobre el total resultante.
6. Al confirmar la venta, queda registrada normalmente; los renglones con precio variable quedan marcados como tales (de forma interna) con su precio aplicado.
7. El ticket y el detalle del comprobante muestran únicamente el precio cobrado, sin ninguna indicación de precio variable.

## Sensación de la interfaz
Sin cambios de estilo. Se mantiene la apariencia actual (tema teal, tarjetas y tablas). El carrito se siente igual, con un ícono discreto por renglón que, al activarse, resalta el campo de precio editable para dejar claro que ese artículo está en precio variable.

## Fases de implementación

### Fase 1 — MVP (se construye ahora)
- Ícono por renglón en el carrito del POS de clínica para activar precio variable.
- Edición del precio del renglón con recálculo inmediato del total.
- Regla de mínimo: el precio variable no puede ser menor al costo del artículo; si lo es, se bloquea y avisa.
- Precio variable sin tope superior (puede superar el precio de lista).
- Disponible para cualquier usuario del POS de clínica, sin autorización.
- La venta se guarda marcando internamente cada renglón de precio variable con el precio aplicado y el precio de lista original.
- El comprobante (ticket y detalle) NO muestra ninguna indicación de precio variable; solo el precio cobrado.
- Solo aplica al POS de clínica; óptica queda igual.

### Fase 2 — Visibilidad y control (futuro)
- Reporte interno de ventas con precio variable (artículo, precio de lista, precio aplicado, diferencia, usuario, fecha).
- Indicador del margen sobre costo al momento de ajustar el precio.

### Fase 3 — Políticas avanzadas (futuro)
- Opción configurable para exigir autorización o límites por rol cuando se use precio variable.
- Topes o rangos de precio por categoría de producto.

## Supuestos
- "Precio de costo" es el precio de compra registrado en el inventario del artículo; ese es el mínimo permitido.
- El precio variable aplica por renglón del carrito y afecta a toda la cantidad de ese renglón.
- El precio variable se puede combinar con el descuento por porcentaje ya existente, que se calcula sobre el total ya con precios variables aplicados.
- Se mantiene la regla vigente de IVA incluido: el precio variable también es un precio final con IVA incluido.
- Las ventas ya registradas no cambian; la marca de precio variable solo aplica a ventas nuevas.
- Si un artículo no tiene costo registrado, el mínimo permitido es cero (no se bloquea por costo), hasta que se registre su costo.
- La marca de precio variable y el precio de lista original quedan guardados internamente para efectos de control, pero no se despliegan en el comprobante entregado al cliente.
- El punto de venta de óptica no se modifica.
