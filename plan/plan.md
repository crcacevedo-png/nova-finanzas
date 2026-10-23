# Identificación IGSS en el Tablero del Día y motivo de consulta automático

Dos mejoras para el flujo IGSS: ver de un vistazo qué paciente viene por el IGSS y cuál por otra institución en el Tablero del Día, y que al abrir la evaluación de un paciente IGSS su motivo de consulta ya traiga la descripción del servicio (NOG).

## Para quién es
Personal de la clínica que opera la agenda y los médicos que atienden pacientes IGSS y de otras instituciones (particulares, seguros, convenios), donde hoy no se distingue el origen del paciente en la lista del día ni se repite manualmente el servicio IGSS como motivo.

## Funciones y experiencia

### 1. Etiqueta de institución en el Tablero del Día
- Cada cita de la lista "Citas del día" muestra una etiqueta que indica el origen del paciente:
  - **IGSS**: etiqueta distintiva (verde) con el texto "IGSS".
  - **Otra institución**: etiqueta con el nombre de la institución registrada en la ficha del paciente (p. ej. "Particular", "Visualiza", el seguro o convenio correspondiente).
- Si el paciente no tiene institución registrada, la etiqueta muestra un texto neutro ("Sin institución").
- La etiqueta es solo informativa (no cambia el comportamiento de la cita).

### 2. Motivo de consulta automático desde el NOG (pacientes IGSS)
- Al abrir la evaluación de un paciente IGSS, el campo **Motivo de consulta** se completa con la **descripción del servicio del NOG** (solo el texto, sin el número de NOG).
- La descripción usada es la del **NOG vinculado a esa cita/evaluación**. Si la cita no tiene una orden vinculada, se usa la primera orden IGSS del paciente.
- El motivo se coloca **siempre** con la descripción del NOG al abrir la evaluación (reemplaza lo que hubiera en ese campo).
- El campo sigue siendo **editable**: el médico puede ajustar el texto después.
- Para pacientes que no son IGSS, el motivo de consulta se comporta como hasta ahora (no se autocompleta).

## Flujo de uso
1. El personal abre Agenda → Tablero del Día y ve, por cada cita, la etiqueta IGSS o el nombre de la otra institución.
2. Al atender a un paciente IGSS, abre su evaluación oftalmológica.
3. El Motivo de consulta ya aparece con la descripción del servicio del NOG correspondiente a esa cita.
4. El médico confirma o edita el motivo y continúa la evaluación.

## Sensación de UI/UX
- Etiquetas pequeñas tipo "pill", coherentes con las que ya existen en las tarjetas de cita (como "otro"/tipo de cita), sin recargar la tarjeta.
- Color verde reservado para IGSS (consistente con el resto del módulo IGSS); color neutro/secundario para otras instituciones.
- El autocompletado del motivo es inmediato y silencioso al abrir la evaluación; no interrumpe con avisos.

## Fases de implementación

### Fase 1 (MVP — se construye ahora)
- Etiqueta IGSS / nombre de institución en cada cita del Tablero del Día.
- Autocompletado del Motivo de consulta con la descripción del NOG vinculado a la cita/evaluación para pacientes IGSS, campo editable.

### Fase 2 (futuro)
- Filtrar u ordenar el Tablero del Día por institución (p. ej. ver solo IGSS).
- Mostrar también el número de NOG / No. SPS junto al nombre del paciente en la tarjeta de cita.

### Fase 3 (futuro)
- Resumen del día por institución (conteos IGSS vs otras) en las tarjetas superiores del tablero.

## Supuestos
- "Otra institución" se toma del campo de institución de referencia ya existente en la ficha del paciente; se muestra tal cual está registrado.
- La "descripción del NOG" es el nombre del servicio del NOG (texto), no su número.
- El autocompletado del motivo ocurre al abrir la evaluación; si el paciente IGSS no tiene NOG/orden con descripción, el motivo se deja como está.
- La etiqueta de institución se muestra para todas las citas del Tablero del Día, incluidas las citas tipo walk-in cuando tienen paciente asociado.
- No se modifica el PDF ni otros reportes; estos cambios afectan solo el Tablero del Día y la pantalla de evaluación.
