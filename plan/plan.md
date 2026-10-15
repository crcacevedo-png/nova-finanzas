# Sobrecupo de citas en la Agenda

Permite agendar una cita aunque el horario del médico ya esté ocupado, avisando primero que el espacio está tomado y pidiendo confirmación. Sigue sin permitir agendar fuera del horario de atención del médico ni sobre bloqueos ya colocados.

## Para quién es
Personal de recepción y médicos de la clínica NovaVisión que gestionan citas desde la pantalla de Agenda y a veces necesitan encajar un paciente adicional en un horario que ya tiene citas.

## Funciones y experiencia principales
- **Agendar sobre un horario ocupado.** Al crear una cita (o registrar un walk-in) desde la Agenda en una hora que ya alcanzó su cupo, el sistema permite continuar en lugar de bloquear.
- **Aviso y confirmación.** Antes de guardar en un horario lleno, aparece un mensaje claro ("Este horario ya está ocupado (X citas). ¿Agendar de todos modos?") y la cita solo se crea si el usuario confirma. Si cancela, no se crea nada.
- **Límites que se mantienen.** No se puede agendar fuera del horario de atención del médico ese día, ni en días/franjas bloqueadas, ni en días no laborables. En esos casos se muestra el motivo y no se permite agendar (igual que hoy).
- **Solo desde la Agenda.** El sobrecupo está disponible únicamente al agendar desde la Agenda (Nueva Cita y Walk-in). La opción "Próxima Cita" dentro de la Evaluación sigue mostrando solo horarios libres y no permite sobrecupo.
- **Identificación visual.** Las citas que comparten un mismo horario (sobrecupo) se distinguen con una etiqueta "Sobrecupo" en la Agenda, para ver de un vistazo cuándo hay más de un paciente en la misma franja.

## Flujo del usuario
1. En la Agenda, el usuario abre "Nueva Cita" (o "Walk-in") y elige médico, fecha y hora.
2. Si la fecha/hora cae fuera del horario del médico o sobre un bloqueo, el sistema lo indica con el motivo y no deja continuar.
3. Si el horario es válido pero ya está lleno, el sistema avisa que está ocupado y pregunta si desea agendar de todos modos.
4. Si el usuario confirma, la cita se crea y queda visible en la Agenda marcada como "Sobrecupo"; si cancela, no se crea.
5. Si el horario está libre, la cita se crea normalmente sin aviso.

## UI/UX feel
Se mantiene el estilo actual de la Agenda y de los formularios de Nueva Cita y Walk-in. El aviso de ocupación aparece como un cuadro de confirmación breve con dos acciones ("Agendar de todos modos" / "Cancelar"). La etiqueta "Sobrecupo" es una insignia discreta en color de advertencia (ámbar) dentro de la tarjeta de la cita, sin alterar el resto de la tarjeta.

## Fases de implementación
**Fase 1 (MVP — se construye ahora):**
- Permitir agendar en horarios ocupados desde Nueva Cita y Walk-in, con aviso y confirmación previa.
- Mantener el bloqueo para horarios fuera de atención del médico y sobre bloqueos existentes.
- Mostrar la etiqueta "Sobrecupo" en las citas que comparten horario en la Agenda.
- Mantener sin cambios la "Próxima Cita" de la Evaluación (solo horarios libres).

**Fase 2 (después):**
- Mostrar en el aviso cuántas citas y de qué pacientes ya existen en ese horario antes de confirmar.
- Indicador de cupo por franja en la vista de calendario (p. ej. "2/3", "lleno", "sobrecupo").

**Fase 3 (después):**
- Reglas de sobrecupo por médico o por tipo de cita (p. ej. permitir sobrecupo solo a ciertos médicos o solo para emergencias).
- Reporte de horarios con sobrecupo recurrente para ajustar la agenda.

## Assumptions
- El sobrecupo aplica a Nueva Cita y Walk-in de la Agenda; no aplica a la "Próxima Cita" de la Evaluación, que sigue ofreciendo solo horarios libres.
- "Ocupado/lleno" significa que el horario ya alcanzó el máximo de citas por franja definido en la configuración de la agenda; al confirmar, el sobrecupo no tiene un tope adicional.
- Se pide confirmación una sola vez por cita, justo antes de guardar.
- La etiqueta "Sobrecupo" se muestra en las citas que comparten la misma hora de inicio con otra cita del mismo médico ese día.
- No hay un permiso especial por rol: cualquier usuario que ya puede agendar desde la Agenda puede confirmar un sobrecupo.
- No se modifica el comportamiento de bloqueos ni de horarios de atención; solo se relaja el límite de cupo por franja al agendar desde la Agenda.
- Fechas y horas siguen la hora de Guatemala, como en el resto del sistema.
