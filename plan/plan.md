# Regla del NOG: una consulta facturable por autorización, el resto es seguimiento

La primera consulta de un paciente bajo cada autorización del IGSS (No. SPS) es la que descuenta cupo del NOG y aparece en el listado de producción.
Las consultas siguientes bajo esa misma autorización se guardan como evaluación clínica, pero no descuentan cupo ni generan otra línea de producción.

## Para quién es
Personal de NovaVisión que gestiona pacientes IGSS, las evaluaciones oftalmológicas y el listado de producción que se factura al IGSS.

## Qué cambia y cómo se comporta
- La unidad que se factura y descuenta cupo deja de ser "el NOG del paciente" y pasa a ser **la autorización del IGSS (No. SPS)** vinculada a la consulta.
- Bajo una misma autorización (mismo No. SPS), el paciente puede tener varias consultas, pero:
  - solo la **primera por fecha** descuenta un cupo del NOG y aparece en el listado de producción;
  - las demás quedan guardadas como evaluación oftalmológica normal, sin descuento y sin línea nueva en producción.
- Si el mismo paciente tiene **otra autorización distinta (otro No. SPS)** bajo el mismo NOG, esa sí cuenta como un nuevo servicio: descuenta otro cupo y genera otra línea de producción.
- Cuando una consulta no tiene No. SPS registrado, se mantiene el comportamiento actual: un solo descuento por paciente dentro de ese NOG.
- El conteo de cupos del NOG, el aviso al 90% y el bloqueo al 100% siguen funcionando igual; lo único que cambia es **qué** cuenta como un consumo.
- La regla aplica **de ahora en adelante**. No se recalculan ni se tocan los descuentos ni las líneas de producción ya existentes.

## Flujo de uso
1. El paciente llega con una orden del IGSS (No. SPS + NOG) y se le crea su primera evaluación bajo esa orden: se descuenta un cupo del NOG y aparece una línea en producción con la fecha de esa primera consulta.
2. El paciente regresa para control bajo la misma orden: se documenta la evaluación en su historial, pero el listado de producción y el cupo del NOG no cambian.
3. El paciente recibe una nueva orden del IGSS (otro No. SPS) para otro servicio bajo el mismo NOG: su primera consulta de esa nueva orden descuenta otro cupo y agrega otra línea de producción.
4. En el listado de producción, cada autorización del paciente aparece una sola vez, con la fecha de su primera consulta.

## Apariencia y experiencia
Sin pantallas nuevas en esta fase. Las consultas de seguimiento siguen viéndose como evaluaciones oftalmológicas normales dentro del historial del paciente, sin distintivos adicionales. El listado de producción y la gestión de NOG se ven igual; solo cambia qué filas y qué descuentos se generan.

## Fases de implementación

### Fase 1 (lo que se construye ahora)
- Aplicar la regla usando la autorización (No. SPS) como unidad facturable, de ahora en adelante.
- Primera consulta por autorización = un descuento de cupo + una línea de producción, fechada en esa primera consulta.
- Consultas siguientes bajo la misma autorización = solo evaluación clínica (sin descuento, sin línea).
- Autorizaciones distintas (otro No. SPS) bajo el mismo NOG = cuentan por separado.
- Sin migración ni recálculo de datos históricos.

### Fase 2 (futuro)
- Recálculo retroactivo opcional y bajo confirmación, con vista previa, para aplicar la regla a los registros históricos (unificar repeticiones antiguas y otorgar los descuentos faltantes de autorizaciones múltiples).
- Distintivo visible de "seguimiento (no facturable)" en el listado del NOG y/o en producción.

### Fase 3 (futuro)
- Reportes por paciente: historial de consultas bajo cada NOG y conteo de consultas facturables vs. de seguimiento.

## Supuestos
- "Autorización" = No. SPS de la orden IGSS vinculada a la evaluación (o la orden del paciente). Si no hay No. SPS, el descuento se limita a uno por paciente dentro del NOG (comportamiento actual).
- "Primera" = la consulta más antigua por fecha; si hay empate, la de creación más temprana.
- No hay migración de datos: los descuentos y las líneas de producción ya registrados se dejan tal cual; la regla rige solo para consultas nuevas.
- Las consultas de seguimiento permanecen visibles únicamente en el historial clínico del paciente, sin marcas nuevas.
- El cupo contratado del NOG, el aviso al 90% y el bloqueo al 100% no cambian de lógica.
