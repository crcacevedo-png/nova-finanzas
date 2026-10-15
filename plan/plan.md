# Flujo de llegada: completar expediente antes de pasar a evaluación

Al marcar la llegada de un paciente a la clínica, si su ficha está incompleta se completa el expediente en ese momento; si ya está completo, se usa el expediente existente. Aplica a todas las agendas y todos los médicos.

## Para quién es
Recepción y personal de la clínica NovaVisión que registra la llegada de pacientes, y los médicos que luego los atienden en evaluación.

## Funcionalidades y experiencia

**1. Detección de ficha incompleta**
Un paciente se considera "sin expediente completo" cuando le falta alguno de estos datos obligatorios: nombre, sexo, fecha de nacimiento, teléfono, documento/DPI, dirección e institución (IGSS o particular). La detección es automática y también aplica a los pacientes que ya existen agendados (no solo a los nuevos). Hoy la agenda permite agendar un paciente "nuevo" capturando solo nombre, teléfono, sexo y edad aproximada, por lo que esos quedan como fichas incompletas.

**2. Completar la ficha al marcar llegada**
Al marcar "Presente" (llegada) a un paciente cuya ficha está incompleta, se abre el formulario completo de paciente con los datos que ya se tienen precargados. El paciente no queda marcado como presente hasta que se guarden todos los datos obligatorios. Al guardar, se actualiza el mismo expediente existente (no se crea uno duplicado).

**3. Llegada directa cuando la ficha ya está completa**
Si el paciente ya tiene su expediente completo, marcar "Presente" lo registra de inmediato, vinculado a su expediente existente, sin pedir datos otra vez.

**4. Asignación a evaluación con su médico**
Una vez presente (con ficha completa), el paciente aparece en "Mis Pacientes Presentes" del médico asignado y puede abrirse su evaluación usando su expediente ya creado.

**5. Walk-ins incluidos**
El mismo comportamiento aplica a los pacientes que llegan sin cita (walk-in): si su ficha está incompleta, se completa al registrarlos como presentes.

## User flow
1. Recepción marca la llegada del paciente (desde una cita agendada o como walk-in).
2. El sistema revisa si la ficha está completa.
3. Si falta algún dato obligatorio: se abre el formulario de paciente con lo ya capturado; recepción completa y guarda; recién entonces el paciente pasa a "Presente".
4. Si la ficha ya está completa: el paciente pasa a "Presente" de inmediato, con su expediente existente.
5. El paciente presente queda disponible para su médico, que abre la evaluación sobre ese expediente.

## UI/UX feel
Se mantiene el estilo actual del sistema (mismos colores, componentes y disposición). La captura de la ficha reutiliza el formulario de paciente ya existente, mostrado al momento de marcar la llegada, con los datos previos precargados y los campos obligatorios claramente señalados.

## Fases de implementación

**Fase 1 (MVP, se construye ahora)**
- Detección automática de ficha incompleta por campos obligatorios faltantes (incluye pacientes ya existentes).
- Al marcar llegada con ficha incompleta: formulario completo precargado, obligatorio completar antes de quedar "Presente"; actualiza el mismo expediente (sin duplicar).
- Llegada directa cuando la ficha está completa, vinculada al expediente existente.
- Mismo flujo para citas agendadas y walk-ins, para todas las agendas y médicos.
- El paciente presente queda asignado a su médico y disponible para evaluación con su expediente.

**Fase 2 (futuro)**
- Indicador visual en la agenda de qué pacientes agendados tienen ficha incompleta (antes de que lleguen).
- Reporte/listado de expedientes incompletos para completarlos por adelantado.

**Fase 3 (futuro)**
- Captura de más datos al momento de agendar para reducir lo que se completa en recepción.
- Detección de duplicados por documento/DPI al completar la ficha.

## Supuestos
- Campos obligatorios para considerar el expediente "completo": nombre, sexo, fecha de nacimiento, teléfono, documento/DPI, dirección e institución (IGSS/particular). Si la institución es IGSS, se piden además los datos IGSS que el formulario ya solicita.
- Completar la ficha es obligatorio para pasar a "Presente": no se puede marcar presente ni abrir la evaluación con ficha incompleta.
- La detección de "incompleto" aplica de forma retroactiva a los pacientes ya existentes, no solo a los nuevos.
- Al completar la ficha se actualiza el expediente existente del paciente; nunca se crea un expediente nuevo para un paciente que ya tenía uno.
- El flujo se dispara en el momento de marcar la llegada ("Presente"), tanto en citas agendadas como en walk-ins.
- Cualquier usuario con acceso a la agenda puede completar la ficha al registrar la llegada.
- Exigir documento/DPI puede generar fricción en casos sin DPI (menores o extranjeros); se asume obligatorio según lo indicado y podría revisarse más adelante.
- El idioma de toda la interfaz se mantiene en español.
