# Agendar cita IGSS desde Registro de Cirugía

Al registrar una cirugía para un paciente IGSS, el personal podrá agregarlo directamente a la agenda del médico responsable con un solo clic, sin salir del formulario de cirugía. El resto del registro de la cirugía (llegada del paciente, descuento de NOG, creación de expediente) no cambia.

## Para quién es

Personal de Sala de Operaciones / recepción que registra cirugías de pacientes IGSS y necesita coordinar, en el mismo momento, la cita de ese paciente en la agenda del médico tratante.

## Funcionalidad principal y experiencia

- En el formulario "Registrar cirugía", cuando la Institución seleccionada es **IGSS**, aparece un botón adicional **"Agregar a Agenda"** justo al lado de "Guardar registro". Para cualquier otra institución, el formulario se ve y funciona exactamente igual que hoy.
- Al presionar "Agregar a Agenda":
  1. Se guarda el registro de la cirugía (misma validación de campos requeridos que "Guardar registro").
  2. Se abre un modal para elegir el médico responsable de la cita, con **4 opciones fijas**:
     1. Dr. Cristian Acevedo — se agenda en su propia agenda.
     2. Dra. Mariamercedes Palma — se agenda en su propia agenda.
     3. Dr. Manuel de la Cruz — se agenda en su propia agenda.
     4. Dra. Rocío Muñoz — se agenda en la agenda general de la clínica (no en una agenda personal).
  3. Al confirmar el médico, se crea el evento en la agenda correspondiente, usando la misma fecha y hora ya ingresadas para la cirugía.
- El evento creado en la agenda muestra, de forma visible, únicamente estos 3 datos:
  1. Nombre del paciente
  2. Institución (IGSS)
  3. Procedimiento a realizar
- Si el usuario cierra el modal de selección de médico sin confirmar, la cirugía queda guardada igual; solo se omite el paso de agendar.

## Flujo de uso

1. El usuario llena "Registrar cirugía" como hoy y selecciona Institución = IGSS.
2. Aparece el botón "Agregar a Agenda" junto a "Guardar registro".
3. El usuario presiona "Agregar a Agenda" → el sistema valida y guarda la cirugía.
4. Se abre el modal con los 4 médicos como opciones.
5. El usuario elige uno y confirma.
6. El sistema crea el evento en la agenda del médico elegido (o en la agenda de la clínica si elige a la Dra. Muñoz), con la fecha/hora de la cirugía y los 3 datos visibles (paciente, IGSS, procedimiento).
7. El modal se cierra con una confirmación visual. El resto del proceso (NOG, expediente, llegada del paciente) continúa exactamente igual que hoy.

## UI/UX feel

Mismo estilo visual ya usado en el modal de "Registrar cirugía" (fondo claro, secciones con etiquetas en mayúsculas, inputs redondeados). El modal de selección de médico es simple: una lista de 4 opciones tipo botón/radio, un resumen de los 3 datos que se van a agendar (paciente, institución, procedimiento) para que el usuario confirme antes de agendar, y una confirmación clara de que el evento quedó creado.

## Fases de implementación

**Fase 1 — MVP (se construye ahora)**
- Botón "Agregar a Agenda" visible solo para Institución = IGSS.
- Guardado de la cirugía + modal de selección entre los 4 médicos fijos.
- Creación del evento en la agenda correspondiente (propia de cada médico, o general de la clínica para la Dra. Muñoz), con la misma fecha/hora de la cirugía.
- El evento muestra únicamente los 3 datos: paciente, institución IGSS, procedimiento.

**Fase 2 — Ajuste de horario**
- Permitir elegir una fecha/hora distinta a la de la cirugía al agendar (por ejemplo, para una cita previa o posterior con el médico).
- Aviso si el horario elegido ya choca con otra cita del médico.

**Fase 3 — Extensión del flujo**
- Ofrecer este mismo botón "Agregar a Agenda" para otras instituciones/seguros, no solo IGSS.
- Permitir editar o cancelar desde la cirugía el evento de agenda que se creó, manteniendo el vínculo entre ambos registros.

## Supuestos

- Los 4 médicos ya existen en el sistema con su agenda activa hoy; solo se conectan a este flujo nuevo (confirmado por el usuario).
- El evento de agenda usa la misma fecha y hora que ya se ingresó para la cirugía; no se pide una fecha/hora aparte en el modal (confirmado por el usuario).
- "Agregar a Agenda" guarda la cirugía y abre el modal en un solo paso (confirmado por el usuario); no es necesario presionar "Guardar registro" por separado antes.
- El botón sigue las mismas reglas de validación de campos obligatorios que ya tiene "Guardar registro".
- Cualquier usuario que hoy puede registrar una cirugía también puede usar este botón; no se agrega un permiso nuevo.
- El evento creado respeta las reglas de agenda que ya existen hoy (por ejemplo, si hoy se permiten o no citas dobles en el mismo horario, se mantiene igual); no se agrega lógica nueva de conflictos en esta fase.
- En el evento de agenda solo se muestran los 3 datos pedidos (paciente, institución, procedimiento); ningún otro dato de la cirugía (cirujano, anestesia, ojo a operar, etc.) se agrega al evento en esta fase.
- Si el usuario cancela el modal de selección de médico después de guardada la cirugía, el registro de la cirugía queda guardado; no se revierte nada.
