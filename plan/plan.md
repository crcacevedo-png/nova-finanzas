# Módulo de Producción IGSS (seguimiento y cierre por unidad)

Un módulo dentro de Unidades IGSS que reúne, día a día, a los pacientes IGSS atendidos y permite dar seguimiento al estado de cada servicio (impreso, enviado, facturado, pagado) y a su costo.
Permite organizar la información por unidad y por NOG, abrir e imprimir cada expediente, y generar un cierre con el total de producción de la unidad (mensual o por rango de fechas).

## Para quién es
Personal administrativo del IGSS y dirección: Superadmin, Admin y Administrador IGSS. Ningún otro rol tiene acceso al módulo.

## Funciones principales y experiencia

### 1. Listado diario de producción
- Muestra los pacientes IGSS que tienen una evaluación/expediente creado ese día.
- Cada registro corresponde a **una orden IGSS**: si un paciente tiene varias órdenes atendidas el mismo día (p. ej. 2 o 3 NOG), aparece una línea por cada una, cada una con su propio NOG, No. SPS, procedimiento y costo.
- Se puede elegir el día, y también ver un rango de fechas.
- Se puede organizar y filtrar por **unidad** y por **NOG** (agrupado para ver subtotales por unidad y por NOG).
- Cada fila muestra: paciente y expediente, unidad, NOG, No. SPS, procedimiento, médico, fecha, costo y los cuatro estados de seguimiento.

### 2. Costo del servicio
- Cada registro trae precargado el **precio del NOG** (precio unitario del contrato).
- El costo es **editable por registro** por si hace falta ajustarlo; el ajuste solo afecta a ese registro y no cambia el precio del NOG en el catálogo.

### 3. Estados de seguimiento (por registro)
- Cuatro marcas independientes: **Informe impreso**, **Informe enviado**, **Informe facturado** y **Servicio pagado**.
- Se marcan/desmarcan a mano. Al imprimir el expediente desde el módulo, la marca "impreso" se activa automáticamente.

### 4. Acciones por paciente
- **Abrir expediente**: lleva a la evaluación/expediente del paciente.
- **Imprimir expediente**: genera el PDF del informe (con el NOG y No. SPS de esa orden).

### 5. Cierre / reporte de producción
- Genera un reporte **mensual o por rango de fechas**, para una unidad o para todas.
- Incluye el **total de producción**: cantidad de servicios, suma de costos, desglose por NOG y resumen por estado (cuántos y cuánto están impresos, enviados, facturados y pagados; total pagado vs. pendiente).
- El reporte se puede exportar/imprimir.
- En esta primera versión el cierre **solo genera el reporte con totales; no bloquea los registros** (los estados se pueden seguir modificando después).

## Flujo de uso
1. El usuario entra al módulo de Producción IGSS (dentro de Unidades IGSS).
2. Elige el día (o un rango) y, si quiere, filtra por unidad y por NOG.
3. Ve la lista de servicios del periodo, agrupada por unidad/NOG con sus subtotales.
4. Sobre cada servicio: abre o imprime el expediente, ajusta el costo si hace falta, y marca los estados a medida que avanza (impreso → enviado → facturado → pagado).
5. Al cierre de mes o cuando lo requiera, genera el reporte de producción de la unidad con los totales y lo exporta/imprime.

## Sensación de UI/UX
- Consistente con el resto del sistema (acentos azul/esmeralda, tablas claras y compactas, filtros arriba).
- Vista tipo tabla con agrupación por unidad y por NOG y subtotales visibles.
- Los cuatro estados se ven como indicadores/toggles discretos con color (pendiente vs. hecho) y una confirmación breve al marcar.
- Barra superior de totales del periodo (servicios y montos) siempre visible.
- Montos en Quetzales (Q).

## Fases de implementación

### Fase 1 (MVP — se construye ahora)
- Listado diario (y por rango) de servicios IGSS, una línea por orden, organizable y filtrable por unidad y por NOG, con subtotales.
- Costo precargado del NOG y editable por registro.
- Cuatro estados por registro (impreso, enviado, facturado, pagado), con "impreso" automático al imprimir.
- Abrir e imprimir el expediente desde cada fila.
- Reporte/cierre mensual o por rango con totales de producción por unidad (y desglose por NOG y por estado), exportable. Sin bloqueo.
- Acceso restringido a Superadmin, Admin y Administrador IGSS.

### Fase 2 (futuro)
- Cierre formal que bloquea el periodo y queda como constancia, con reapertura controlada (solo Superadmin).
- Acciones en lote (marcar varios como facturado/pagado) y número de factura por registro.
- Alertas de pendientes (enviados sin facturar, facturados sin pagar) y antigüedad.

### Fase 3 (futuro)
- Adjuntar la factura o el informe escaneado a cada registro.
- Exportación/conciliación con el módulo de Caja (pagos) y generación de archivos de facturación.

## Supuestos
- "Paciente que llega a consulta" se define como un paciente IGSS con una evaluación/expediente creado ese día; los pacientes no IGSS no aparecen en este módulo.
- Cada registro de producción equivale a una evaluación IGSS, que ya lleva asociada una sola orden (NOG, No. SPS, procedimiento); de ahí sale la línea y su costo.
- El costo por defecto es el precio unitario del NOG; editarlo afecta solo a ese registro y no modifica el catálogo de NOG.
- Los cuatro estados son independientes y se marcan manualmente; imprimir el expediente desde el módulo marca "impreso" automáticamente.
- El módulo es una vista de seguimiento: no cambia por sí mismo el consumo del NOG (eso ya ocurre al asignar las órdenes al paciente). El listado refleja los servicios ya registrados.
- La fecha de referencia es la fecha clínica de la evaluación, en horario de Guatemala; la vista abre por defecto en el día actual.
- El reporte de cierre se puede exportar/imprimir (PDF y/o Excel) e incluye totales por unidad, por NOG y por estado.
- Los montos se muestran en Quetzales (Q).
