# Bloqueo de Agenda (espacios, días, feriados y vacaciones)

Permite reservar espacios de la agenda para que no se puedan agendar citas: por médico (franjas de horas o días completos) y para toda la clínica (feriados o vacaciones).
Los bloqueos son consultables y respetados también por un agente externo (n8n/Claude) que agenda citas por API.

## Para quién es
- Personal de recepción y cualquier usuario del sistema que gestiona la agenda diaria.
- Médicos que necesitan apartar horarios o ausentarse.
- Un agente externo automatizado (n8n + Claude) que verifica disponibilidad y agenda citas por API con una clave fija.

## Funcionalidades y experiencia

### Bloqueos por médico
- Bloquear una **franja de horas** en una fecha específica (ej. 10:00–12:00 el 15 de julio).
- Bloquear un **día completo** para un médico.
- Cada bloqueo es individual por médico y no afecta a los demás.
- Motivo opcional (ej. Vacaciones, Congreso, Almuerzo, Personal).

### Bloqueo de clínica completa
- Bloquear un **día** o un **rango de fechas** para toda la clínica (feriados, vacaciones colectivas).
- Afecta a todos los médicos durante ese período.

### Reglas de uso
- **Cualquier usuario** puede crear bloqueos (de médico y de clínica).
- **Cualquier usuario** puede eliminar cualquier bloqueo (incluidos los de clínica completa).
- Al intentar agendar una cita en un espacio/día bloqueado, el sistema **impide** la cita y muestra el motivo del bloqueo (bloqueo duro). Esto aplica tanto a la agenda interna como al agente externo.
- Si al crear un bloqueo ya existen citas en ese horario/día, el bloqueo **se crea igual** y el sistema **lista las citas en conflicto** para que se reprogramen manualmente. Las citas existentes no se cancelan automáticamente; solo se impiden citas nuevas.

### Consulta y agendado por agente externo (API)
- Acceso mediante una **clave de API fija** (se entrega para configurarla en n8n).
- El agente externo puede:
  - **Consultar disponibilidad** de un médico en una fecha/hora, considerando bloqueos y citas existentes.
  - **Listar los bloqueos** vigentes (por médico y de clínica).
  - **Agendar una cita**, respetando los bloqueos (si el espacio está bloqueado, la API lo rechaza con el motivo).
- Los bloqueos creados desde la interfaz se reflejan de inmediato para el agente externo y viceversa.

## Flujo de uso
1. Un usuario abre la Agenda y elige "Bloquear" sobre un espacio, un día de un médico, o un período de clínica.
2. Define médico (o "toda la clínica"), fecha/rango, franja de horas o día completo, y un motivo opcional.
3. Si hay citas en conflicto, el sistema las muestra en una lista para reprogramarlas; el bloqueo queda activo.
4. En la vista de agenda, los espacios/días bloqueados se muestran marcados y no permiten agendar.
5. El agente externo (n8n) consulta disponibilidad con su clave de API; si está libre, agenda; si está bloqueado, recibe el rechazo con el motivo.
6. Cualquier usuario puede eliminar un bloqueo cuando ya no aplica.

## Estilo (UI/UX)
- Integrado a la agenda actual, sin cambiar su diseño general.
- Espacios bloqueados con indicación visual clara (sombreado/trama) y el motivo visible al pasar o tocar.
- Los bloqueos de clínica completa se muestran como una franja/etiqueta destacada en el día (ej. "Feriado", "Vacaciones").
- Un panel o listado para ver y eliminar bloqueos vigentes.
- Mensajes claros al impedir una cita por bloqueo, indicando el motivo.

## Fases de implementación

### Fase 1 — MVP (se construye ahora)
- Bloqueos por médico: franja de horas en una fecha y día completo.
- Bloqueos de clínica completa: día y rango de fechas.
- Crear y eliminar bloqueos por cualquier usuario; motivo opcional.
- Listado de citas en conflicto al crear un bloqueo (para reprogramación manual).
- Enforcement duro: la agenda interna impide agendar en espacios/días bloqueados.
- Indicación visual de bloqueos en la agenda y panel para administrarlos.
- API con clave fija para el agente externo: consultar disponibilidad, listar bloqueos y agendar citas respetando los bloqueos.

### Fase 2 — Mejoras
- Bloqueos **recurrentes** (ej. almuerzo todos los días, día libre semanal).
- Herramienta para **reprogramar en lote** las citas en conflicto.
- Notificación a pacientes afectados cuando un bloqueo genera conflicto.

### Fase 3 — Avanzado
- Horarios/calendarios laborales individuales por médico y plantillas de disponibilidad.
- Registro de auditoría de bloqueos (quién creó/eliminó y cuándo).
- API externa ampliada (cancelar/reprogramar citas, estados).

## Supuestos
- El agente externo necesita **tanto consultar disponibilidad como agendar** citas por API; la clave fija habilita ambas acciones de forma controlada.
- Los bloqueos por médico se definen como **franja de horas en una fecha** o **día completo**; los de clínica como **día o rango de fechas**.
- Cada bloqueo incluye un **motivo opcional**.
- Los bloqueos **recurrentes** quedan para la Fase 2 (en el MVP se crean por fecha o rango).
- Al bloquear con citas existentes, estas **no se cancelan automáticamente**; solo se listan para reprogramación y se impiden citas nuevas.
- La clave de API se **genera y entrega** para configurarla en n8n; puede rotarse si se requiere.
- El enforcement aplica a la creación/reprogramación de citas; las citas ya finalizadas no se ven afectadas.
