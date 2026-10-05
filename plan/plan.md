# Nota de cirugía en el historial clínico del paciente

Al registrar una cirugía para un paciente, el sistema crea automáticamente un evento en el historial clínico de ese paciente con el nombre de la cirugía realizada y una nota de cirugía editable. La nota puede cerrarse para dejarla como registro definitivo y se bloquea automáticamente un mes después de creada.

## Para quién es
- Médicos y cirujanos que documentan lo realizado en cada cirugía.
- Personal de recepción/asistentes que registran cirugías en la Sala de Operaciones.
- Cualquier usuario que consulta el historial clínico del paciente.

## Funcionalidades y experiencia

### 1. Vincular la cirugía a un paciente registrado
- En el formulario de "Registrar cirugía", el campo de paciente pasa de texto libre a un **buscador de pacientes registrados** (por nombre/expediente/DPI).
- Si se selecciona un paciente registrado, la cirugía queda asociada a ese paciente.
- Si no se encuentra/selecciona un paciente registrado, la cirugía puede guardarse igual (con nombre escrito), pero **no se crea evento clínico** para ese caso.

### 2. Evento de cirugía en el historial clínico
- Al registrar una cirugía para un paciente registrado, aparece automáticamente un **evento** en el historial clínico de ese paciente.
- El evento muestra como título el **nombre de la cirugía realizada** (el procedimiento) y datos de referencia: fecha, ojo, cirujano e institución.
- El evento queda listado junto al resto del historial del paciente, ordenado por fecha.

### 3. Nota de cirugía
- Cada evento de cirugía tiene una **nota de cirugía** donde se escribe el detalle de lo realizado.
- La nota admite **formato básico** (negritas, cursiva, listas) además de texto.
- Mientras está abierta, cualquier usuario puede escribir y editar la nota.

### 4. Cierre y bloqueo de la nota
- Botón **"Cerrar nota"**: al cerrarla, queda **bloqueada de inmediato** y pasa a ser solo lectura.
- **Bloqueo automático**: aunque no se cierre manualmente, la nota se bloquea **un mes después de haber sido creada**.
- Una nota bloqueada (cerrada o vencido el mes) **no puede modificarse**, con una excepción: el **superadmin** sí puede editarla.
- El estado de la nota se muestra claramente: Abierta / Cerrada / Bloqueada por tiempo, con la fecha a partir de la cual queda bloqueada.

## Flujo de uso
1. Un usuario registra una cirugía en la Sala de Operaciones y busca/selecciona al paciente registrado.
2. Al guardar, se crea el evento de cirugía en el historial clínico del paciente, con el nombre del procedimiento.
3. El médico abre el evento y redacta la nota de cirugía (con formato básico); puede guardarla y seguir editándola.
4. Cuando la da por terminada, pulsa "Cerrar nota": la nota queda bloqueada y de solo lectura.
5. Si nunca se cierra, al cumplirse un mes desde su creación se bloquea sola.
6. Después del bloqueo, solo el superadmin puede hacer correcciones.

## Estilo (UI/UX)
- Integrado al historial clínico existente del paciente, sin cambiar su diseño general; el evento de cirugía se distingue con una etiqueta/ícono propio.
- Editor de nota sencillo y limpio, con una barra mínima de formato (negrita, cursiva, lista).
- Indicadores de estado visibles (Abierta/Cerrada/Bloqueada) y, cuando está bloqueada, mensaje claro del motivo y la fecha.
- Acceso a la nota tanto desde el historial clínico del paciente como desde el detalle de la cirugía en la Sala de Operaciones.

## Fases de implementación

### Fase 1 — MVP (se construye ahora)
- Buscador de paciente registrado en el formulario de cirugía (reemplaza el texto libre; permite guardar sin evento si no hay paciente registrado).
- Creación automática del evento de cirugía en el historial clínico, titulado con el nombre del procedimiento y con datos de referencia.
- Nota de cirugía con formato básico, editable mientras está abierta.
- Botón "Cerrar nota" (bloqueo inmediato) y bloqueo automático al mes de creada.
- Nota bloqueada en solo lectura para todos, con excepción del superadmin.
- Visualización del estado de la nota y acceso desde historial clínico y desde el detalle de la cirugía.

### Fase 2 — Mejoras
- Sincronizar el evento si la cirugía se edita (p. ej. cambia el procedimiento) y manejar el caso de cirugía cancelada/eliminada.
- Adjuntar imágenes/archivos a la nota de cirugía.
- Imprimir/exportar la nota de cirugía (PDF).

### Fase 3 — Avanzado
- Plantillas de nota de cirugía por tipo de procedimiento.
- Registro de auditoría de la nota (quién creó/editó/cerró y cuándo), incluidas las ediciones del superadmin tras el bloqueo.
- Firma electrónica del cirujano en la nota.

## Supuestos
- El "nombre de la cirugía" del evento es el **procedimiento** registrado en la cirugía.
- El mes de bloqueo se cuenta **desde la creación de la nota** (no desde la fecha de la cirugía ni desde el cierre).
- "Cerrar nota" puede hacerlo cualquier usuario; una vez cerrada, solo el superadmin puede reabrir/editar.
- Si una cirugía no se asocia a un paciente registrado, no se genera evento clínico (se permite guardar la cirugía con nombre escrito).
- Eliminar o cancelar una cirugía **no borra** el evento clínico ya creado en el MVP (se aborda en la Fase 2).
- Solo se crea **una nota de cirugía por evento de cirugía**.
- El formato básico se limita a negritas, cursiva y listas (sin imágenes ni tablas en el MVP).
- El bloqueo aplica a la nota; los datos de la cirugía en la Sala de Operaciones conservan sus reglas actuales.
