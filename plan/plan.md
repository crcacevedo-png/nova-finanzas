# Agendar la próxima cita desde la Evaluación Oftalmológica

Permite que, al terminar una evaluación, se agende la siguiente cita del paciente con los mismos tipos de consulta de la agenda y eligiendo solo entre los horarios realmente disponibles del médico. La cita queda visible en la agenda con su tipo de consulta y sus notas, igual que cualquier otra cita.

## Para quién es
Médicos y personal de recepción de la clínica NovaVisión que atienden pacientes y necesitan dejar programada la cita de control/seguimiento sin salir de la pantalla de evaluación.

## Funciones y experiencia principales
- **Tipos de consulta unificados.** El selector "Tipo de cita" del panel "Próxima Cita" ofrece exactamente la misma lista que la pantalla "Nueva Cita" de la agenda: Primera Consulta, Control, Control Post Operatorio, Lectura de estudios, Procedimiento y Emergencia. (Hoy muestra una lista distinta: Subsecuente, Control post-operatorio, Estudio, Otro.)
- **Solo horarios disponibles del médico.** Al elegir médico y fecha, el sistema calcula y muestra únicamente las horas libres de ese médico para ese día, tomando en cuenta su horario de atención, los días/franjas bloqueados y las citas ya agendadas. El usuario escoge una de esas horas en lugar de escribir una hora libre.
- **Bloqueo real fuera de disponibilidad.** Si el médico no atiende ese día, el día está bloqueado o no quedan horas libres, el panel lo indica con el motivo y no deja agendar. No se crea ninguna cita en esos casos.
- **La cita aparece en la agenda con tipo y notas.** La cita agendada desde la evaluación se ve en la agenda (Calendario, Tablero del Día y Pacientes Presentes) mostrando su tipo de consulta y el texto de las notas, igual que las citas creadas desde la agenda.
- **La evaluación se guarda aunque no se agende.** Si por disponibilidad no se puede crear la cita, la evaluación igual se guarda normalmente y se avisa que la cita no se agendó para que el usuario elija otra fecha/hora.

## Flujo del usuario
1. En la evaluación, el usuario activa "Agendar próxima cita para este paciente".
2. Elige el médico (por defecto, el médico de la evaluación si aplica).
3. Elige el tipo de consulta de la lista unificada.
4. Elige la fecha. Al hacerlo, el sistema carga las horas disponibles de ese médico para ese día.
5. Elige una de las horas disponibles. Si no hay horas libres (día no laborable, bloqueo o agenda llena), se muestra el motivo y no se puede continuar con esa fecha.
6. Opcionalmente escribe notas para la próxima cita.
7. Al guardar la evaluación, la cita se crea y queda visible en la agenda con su tipo y notas. Si la hora dejó de estar disponible entre tanto, se avisa el motivo y la cita no se crea (la evaluación sí se guarda).

## Sensación de la interfaz (UI/UX)
Se mantiene el estilo actual del panel "Próxima Cita" dentro de la evaluación (mismos colores, tamaños y disposición en dos columnas). El único cambio visible es que el campo de hora pasa de ser una hora escrita libremente a una lista/selección de horas disponibles, y que aparece un mensaje claro de motivo cuando no hay disponibilidad. El selector de tipo de cita conserva su apariencia, solo cambian las opciones.

## Fases de implementación
**Fase 1 (MVP — se construye ahora):**
- Unificar el selector de tipo de cita con la lista de la agenda.
- Mostrar solo las horas disponibles del médico para la fecha elegida (según horario del médico, bloqueos y citas existentes).
- Bloquear el agendado con mensaje de motivo cuando no haya disponibilidad.
- Asegurar que la cita creada se vea en la agenda con tipo de consulta y notas, y que la evaluación se guarde aunque la cita no pueda crearse.

**Fase 2 (después):**
- Elegir la duración de la próxima cita (hoy es fija en 20 minutos) y que las horas disponibles se ajusten a esa duración.
- Ver en el mismo panel un resumen de la agenda de ese médico ese día (cuántas citas ya tiene) antes de elegir la hora.

**Fase 3 (después):**
- Reprogramar/cancelar la cita agendada directamente desde la evaluación.
- Confirmación automática al paciente (recordatorio) de la próxima cita.

## Supuestos
- Los tipos de consulta serán exactamente los de la lista de la agenda (Primera Consulta, Control, Control Post Operatorio, Lectura de estudios, Procedimiento, Emergencia). El valor por defecto sugerido será "Control" por tratarse de un seguimiento; el usuario puede cambiarlo.
- La duración de cada cita se mantiene en 20 minutos (igual que hoy en la próxima cita), por lo que las horas disponibles se muestran en intervalos coherentes con la configuración de la agenda.
- "Horas disponibles" significa: dentro del horario de atención del médico ese día de la semana, fuera de días/franjas bloqueados, y sin superar el máximo de citas por horario que ya permite la configuración de la agenda (es decir, se respeta el sobrecupo permitido actualmente; una hora solo se oculta cuando está llena según esa configuración).
- Si un médico no tiene horario de atención configurado, se usan como referencia el horario de apertura y cierre y los días laborables de la configuración general de la agenda.
- Las fechas y horas siguen la hora de Guatemala, como en el resto del sistema.
- La cita se crea al guardar la evaluación (comportamiento actual); no se agrega un botón separado para crear la cita antes de guardar.
- No se modifica la pantalla "Nueva Cita" de la agenda ni el comportamiento de las citas existentes; el cambio es solo en el panel "Próxima Cita" de la evaluación y en el cálculo de disponibilidad que lo alimenta.
