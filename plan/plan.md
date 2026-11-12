# Cierre de Producción Diario — Dra. Mariamercedes Palma

Cada día a las 5:00 PM (hora Guatemala), el sistema envía automáticamente a dra.mpalma@gmail.com un PDF con el detalle de su producción personal del día. Funciona igual que el informe diario de anestesia que ya se envía por correo, pero con el contenido y horario propios de la Dra. Palma.

## Para quién es
- La Dra. Mariamercedes Palma, quien recibe el correo diario en su bandeja.
- La administración de la clínica, que deja de tener que armar este cierre manualmente.

## Funcionalidad principal
- Un nuevo cron diario a las **5:00 PM hora Guatemala**, independiente de los dos que ya existen a las 6:00 PM (informe de anestesia y cierre diario general).
- El reporte reúne **toda su producción del día como médico que refiere**, sin importar la categoría:
  - Ventas de la clínica general donde ella aparece como médico que refiere.
  - Ventas de Óptica (armazones, lentes, lentes de contacto, accesorios) donde ella aparece como médico que refiere.
- Contenido del PDF: un renglón por cada producto/servicio vendido ese día (fecha, número de venta, paciente, producto/servicio, cantidad, monto), con el total general al final — mismo nivel de detalle que el desglose de producción por médico que ya existe en el Dashboard.
- Se envía como **PDF adjunto**, con el mismo estilo del informe de anestesia (membrete, tabla clara, total destacado).
- Si ese día no tuvo producción, igual llega el correo mostrando el cierre en cero, para que el envío sea predecible todos los días.
- Es un reporte de solo lectura: no modifica ninguna venta, cron o pantalla existente.

## Flujo de uso
No requiere ninguna acción manual:
1. A las 5:00 PM hora Guatemala, el sistema reúne las ventas de clínica general del día donde la Dra. Palma es el médico que refiere.
2. Reúne también las ventas de Óptica del día donde ella es el médico que refiere, en cualquier categoría.
3. Arma un solo PDF combinado con el detalle línea por línea y el total.
4. Envía el PDF por correo a dra.mpalma@gmail.com.

Para confirmar que llegó, basta con revisar su correo después de las 5:00 PM; esta fase no agrega una pantalla dentro del sistema para verlo.

## Estilo del PDF
Se mantiene la misma línea visual que el informe de anestesia ya existente: encabezado con el nombre de la clínica y la fecha, tabla ordenada con las columnas del detalle, y el total resaltado al final.

## Fases de implementación
**Fase 1 (MVP — se construye ahora)**
- Cron diario a las 5:00 PM hora Guatemala.
- Combinación de ventas de clínica general + Óptica, en cualquier categoría, filtradas por Dra. Mariamercedes Palma como médico que refiere.
- PDF con detalle línea por línea y total.
- Envío automático a dra.mpalma@gmail.com.
- Envío también en los días sin producción (reporte en cero).

**Fase 2**
- Pantalla de administración para cambiar el correo destino o el horario sin pedírselo al equipo de desarrollo.
- Historial de los reportes enviados, con opción de reenviar uno puntual.

**Fase 3**
- Extender este mismo "cierre de producción personal" a otros médicos que quieran su propio reporte diario, eligiéndolos de una lista en vez de dejarlo fijo a un solo médico.

## Supuestos
- Hoy la clínica general y Óptica llevan catálogos de médicos separados; la coincidencia con "Dra. Mariamercedes Palma" se hará por nombre en ambos catálogos. Si el nombre está escrito de forma distinta en alguno de los dos, se ajustará durante la construcción.
- "Producción" significa ventas donde ella está registrada como médico que refiere (igual que el resto del sistema lo define hoy), no procedimientos que ella haya realizado personalmente.
- El reporte cubre únicamente las ventas del día del envío (hora Guatemala); no es un reporte de rango de fechas.
- En esta fase el correo destino y el horario quedan fijos en la configuración del sistema, igual que el informe de anestesia; cambiarlos más adelante se maneja como un ajuste de configuración, no desde una pantalla.
- Si el envío falla, se registra igual que los demás reportes automáticos existentes, sin agregar alertas adicionales en esta fase.
