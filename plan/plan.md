# Agenda: eliminar citas que de verdad desaparezcan + reagendar arrastrando

Corrige dos cosas en la Agenda de Pacientes: que al eliminar una cita esta deje de aparecer en la pantalla, y que se pueda reagendar una cita arrastrándola a otro horario.

## Para quién es
Personal de la clínica NovaVisión (recepción, médicos, administración) que gestiona las citas del día y de la semana.

## Qué se corrige y cómo se verá

### 1. Eliminar una cita
Hoy, al eliminar una cita desde la vista de calendario, la cita se queda visible como si nada hubiera pasado. Se corrige así:
- Al eliminar una cita, el sistema pide una confirmación corta ("¿Eliminar esta cita?").
- Al confirmar, la cita se marca como **Cancelada** y desaparece de inmediato de todas las vistas activas de la agenda: calendario por día, por semana, por mes y el tablero del día.
- La cita no se borra de la base de datos: queda guardada como cancelada (para historial), pero ya no estorba en la agenda ni se cuenta como cita activa.
- Los contadores del día (Agendados, Confirmados, etc.) dejan de incluir las citas canceladas.

### 2. Reagendar arrastrando (click & drop)
Permite mover una cita a otro horario sin abrir ningún formulario:
- Funciona en la **vista de Día** (arrastrar entre franjas horarias del mismo día y entre médicos) y en la **vista de Semana** (arrastrar entre días y franjas horarias).
- Al soltar la cita en el nuevo espacio, se reagenda **de inmediato**, sin ventana de confirmación. Aparece un aviso breve de éxito con la opción **Deshacer** por si fue un error.
- Si el nuevo horario ya está ocupado por otra cita del mismo médico, el sistema **bloquea el movimiento**: la cita vuelve a su lugar y se muestra un mensaje claro ("Ese horario ya está ocupado para este médico").

La apariencia general de la agenda no cambia; solo mejora el comportamiento de eliminar y de arrastrar.

## Flujo de uso
1. El usuario abre la Agenda en la vista de Día o Semana.
2. Para eliminar: abre el menú de la cita, elige Eliminar, confirma, y la cita desaparece de la vista.
3. Para reagendar: toma la cita con el cursor y la suelta en la nueva franja/día.
4. Si el horario está libre, la cita se mueve al instante (con opción de deshacer). Si está ocupado, no se mueve y se avisa.

## Sensación / UI
Sin rediseño. Movimientos fluidos al arrastrar, mensajes claros de éxito/bloqueo, y una agenda que refleja de inmediato lo que el usuario hizo.

## Fases de implementación

**Fase 1 (MVP, se construye ahora):**
- Eliminar una cita: confirmación, marcado como Cancelada, y desaparición inmediata de todas las vistas de la agenda y de los contadores.
- Reagendar arrastrando en vista de Día y de Semana, con movimiento inmediato, opción de deshacer y bloqueo cuando el horario del médico ya está ocupado.

**Fase 2 (después):**
- Reagendar arrastrando también en la vista de Mes (mover una cita de un día a otro).
- Un filtro/interruptor para ver las citas canceladas cuando se necesite revisarlas.

**Fase 3 (futuro):**
- Registro de historial de reagendamientos y cancelaciones (quién, cuándo y motivo).
- Aviso automático al paciente cuando su cita se reagenda o cancela.

## Supuestos
- "Eliminar" significa marcar la cita como Cancelada (no borrado permanente), según lo confirmado.
- Las citas canceladas se ocultan de todas las vistas activas de la agenda; se podrán revisar más adelante mediante el filtro de la Fase 2.
- Se pide confirmación antes de eliminar (para evitar cancelaciones accidentales), pero NO se pide confirmación al reagendar arrastrando (se mueve de inmediato con opción de deshacer), según lo confirmado.
- El bloqueo por choque de horario considera ocupado un espacio cuando el mismo médico ya tiene otra cita activa a esa misma hora de inicio ese día.
- Las citas ya marcadas como Atendida o No asistió siguen mostrándose como hasta ahora; solo cambia el manejo de las canceladas.
- No se modifican datos históricos existentes.
