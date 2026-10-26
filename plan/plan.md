# Buscador de pacientes en la Agenda (citas futuras)

Un buscador dentro de la Agenda que encuentra a un paciente por nombre y apellido y muestra sus próximas citas.
Sirve para ubicar rápidamente cuándo vuelve un paciente sin recorrer el calendario día por día.

## Para quién es
Recepción, personal de agenda, médicos y administradores que necesitan saber si un paciente ya tiene cita y cuándo, atendiendo llamadas o consultas en mostrador.

## Funciones principales y experiencia
- Campo de búsqueda visible en la Agenda donde se escribe el nombre y/o apellido del paciente.
- La búsqueda tolera coincidencias parciales (por ejemplo, escribir solo el apellido) y no distingue mayúsculas ni acentos.
- Los resultados muestran los pacientes que coinciden con lo escrito.
- Al elegir un paciente, se despliega la lista de sus **próximas citas** (de hoy en adelante), cada una con fecha, hora y médico.
- La lista incluye también las citas futuras **canceladas** y marcadas **"no asistió"**, cada una señalada con su estado para distinguirlas de las vigentes.
- Al tocar una cita de la lista se abre el detalle de esa cita.
- Si el paciente no tiene citas futuras, se indica con un mensaje claro ("Sin citas próximas").
- Solo se consideran citas de hoy en adelante; las citas de días pasados no aparecen en este buscador.

## Flujo del usuario
1. El usuario entra a la Agenda y escribe el nombre o apellido en el buscador de pacientes.
2. Aparecen los pacientes que coinciden.
3. El usuario selecciona al paciente deseado.
4. Se muestra la lista de sus próximas citas (fecha, hora, médico y estado), ordenadas de la más cercana a la más lejana.
5. El usuario toca una cita y se abre su detalle.
6. El usuario puede limpiar la búsqueda y empezar otra.

## Sensación UI/UX
- Integrado de forma natural en la Agenda, coherente con el estilo actual del sistema.
- Rápido: los resultados se actualizan a medida que se escribe, sin recargar la pantalla.
- Lista ordenada y legible, con la fecha/hora destacada y una marca visible para las citas canceladas o "no asistió".
- Estados de "vacío" y "sin resultados" claramente comunicados.

## Fases de implementación

### Fase 1 (MVP, se construye ahora)
- Buscador por nombre y apellido (coincidencia parcial, sin distinguir acentos/mayúsculas) dentro de la Agenda.
- Resultados de pacientes y, al seleccionar uno, lista de sus citas de hoy en adelante con fecha, hora, médico y estado.
- Inclusión de citas futuras canceladas y "no asistió", señaladas con su estado.
- Apertura del detalle de una cita al tocarla.
- Mensaje claro cuando el paciente no tiene citas próximas.

### Fase 2 (futuro)
- Filtros dentro de los resultados: por médico, por rango de fechas o por estado de la cita.
- Acceso rápido para agendar una nueva cita al paciente desde el mismo resultado.

### Fase 3 (futuro)
- Incluir en el buscador el historial de citas pasadas (con conmutador entre "próximas" e "historial").
- Búsqueda ampliada por otros datos del paciente (número de expediente, DPI, teléfono).

## Supuestos
- "Citas futuras" = de hoy en adelante, incluyendo las citas de hoy que aún no han ocurrido; se excluyen fechas anteriores a hoy.
- El día y la hora se calculan en la zona horaria de Guatemala, igual que el resto del sistema.
- La búsqueda aplica a las citas de pacientes (no a bloqueos u otros tipos de registro de la agenda).
- Las citas se listan ordenadas de la más próxima a la más lejana.
- Las citas canceladas y "no asistió" se muestran con una marca de estado para diferenciarlas de las vigentes.
- Al seleccionar una cita se abre su detalle en la misma vista de Agenda; no se crea ni modifica nada por solo buscar.
- El buscador está disponible para los roles que ya tienen acceso a la Agenda.
- No se modifica ninguna otra función existente de la Agenda.
