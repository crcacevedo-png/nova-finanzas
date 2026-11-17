# Correlación entre la venta y la cuenta por cobrar

Cada cuenta por cobrar mostrará de qué venta proviene: número de orden, fecha, productos y servicios cobrados y el monto que quedó al crédito.
Cuando una cuenta no tenga venta asociada, se podrá buscarla y vincularla a mano desde la misma pantalla.

## Para quién es

- Personal de caja y administración que cobra las cuentas pendientes y necesita saber exactamente qué se le vendió al paciente y bajo qué orden.
- Dirección/finanzas, que al revisar un saldo pendiente necesita ver el respaldo de la venta sin ir a buscarla en otro listado.

## Funcionalidad y experiencia

- **Origen visible en el listado de cuentas por cobrar**: una columna nueva con el número de orden (ej. VTA-20261116-0007). Las cuentas sin venta asociada muestran un indicador "Sin venta" para que se noten de inmediato.
- **Detalle de la cuenta con el respaldo de la venta**: al abrir una cuenta se muestra un bloque con los datos de su venta: número de orden, fecha, vendedor, médico, el detalle de productos/servicios con cantidades y precios, el total de la venta y cuánto de ese total quedó al crédito (cuando parte se pagó en caja, se ve la diferencia).
- **Búsqueda por número de orden**: el buscador de cuentas por cobrar también encuentra cuentas escribiendo el número de la venta.
- **Vinculación manual**: en una cuenta sin venta (o con la venta equivocada) se puede buscar la venta por número de orden, paciente o fecha, elegirla y asociarla. También se puede quitar el vínculo. Queda registrado quién hizo el cambio y cuándo.
- **Protecciones al vincular**: solo se ofrecen ventas no anuladas; se avisa si la venta elegida ya está asociada a otra cuenta o si el monto no coincide con el de la cuenta, permitiendo continuar a conciencia (el aviso no bloquea, porque en la práctica pueden existir ajustes).
- **Nada se recalcula**: vincular o desvincular no altera montos, saldos, abonos ni el estado de la cuenta; solo cambia la referencia.

Fuera de alcance en esta entrega: no se agregan columnas ni cambios en la pantalla de Ventas, no se emparejan automáticamente los registros históricos, y una cuenta se asocia a una sola venta.

## Flujo del usuario

1. La persona entra a Cuentas por Cobrar y ve la lista habitual, ahora con la columna de orden de venta.
2. Abre una cuenta pendiente y, junto al concepto y el saldo, ve el detalle de la venta que la originó.
3. Si la cuenta no tiene venta asociada, pulsa "Vincular venta", busca por número de orden o por paciente, revisa los resultados (fecha, paciente, total) y selecciona la correcta.
4. La cuenta queda mostrando su orden; si se detecta un error, se cambia o se quita el vínculo desde el mismo lugar.
5. Para encontrar una cuenta a partir de un número de orden, lo escribe en el buscador de la lista.

## Sensación de la interfaz

Se mantiene el estilo actual del módulo: tablas limpias, tipografía sobria y badges de estado. El número de orden aparece como una etiqueta discreta en tipografía monoespaciada, igual que los números de cuenta, para que se lean como identificadores y no compitan con los montos. El bloque de la venta dentro del detalle se presenta como una tarjeta separada con un encabezado claro ("Venta de origen") y la lista de renglones en texto pequeño; la ausencia de venta se muestra en gris, no en rojo, porque no es un error sino un dato por completar. La búsqueda de ventas al vincular ocurre en una ventana modal con resultados en lista, sin sacar a la persona de la cuenta que está revisando.

## Fases

**Fase 1 (lo que se construye ahora)**: columna de orden en el listado de cuentas por cobrar, bloque "Venta de origen" en el detalle con el desglose de la venta y el monto al crédito, búsqueda de cuentas por número de orden, y vinculación/desvinculación manual con registro de quién la hizo.

**Fase 2**: conciliación en la pantalla de Ventas (ver desde la venta a qué cuenta dio origen y cuánto se ha abonado) y un reporte de ventas al crédito contra saldos pendientes, exportable.

**Fase 3**: emparejamiento asistido de los registros históricos — el sistema propone coincidencias por paciente, monto y fecha, y una persona confirma o descarta en lote.

## Supuestos

- Las ventas nuevas pagadas con "Cuenta por Cobrar" ya quedan asociadas a su cuenta al momento de confirmarse; esta entrega aprovecha esa relación existente y agrega la vinculación manual para los casos en que falte. Si se detecta que alguna venta nueva no está quedando asociada, se corrige como parte de esta fase.
- Las cuentas creadas antes de este cambio se mostrarán como "Sin venta" hasta que alguien las vincule manualmente; no se tocan sus montos ni su historial.
- El vínculo aplica tanto a las cuentas por cobrar de clínica como a las de óptica, con la misma presentación.
- Quien puede registrar abonos en una cuenta es quien puede vincular o desvincular su venta; quien solo tiene vista puede ver la venta de origen pero no modificarla.
- Se permite vincular una venta ya asociada a otra cuenta solo tras un aviso explícito, para no bloquear correcciones legítimas; el caso normal es uno a uno.
- Los montos y el detalle de la venta se muestran tal como quedaron registrados en la venta, aunque después se hayan editado precios en otros módulos.
