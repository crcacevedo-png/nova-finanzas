# Permisos de "usuario" en Sala de Operaciones: Cancelar, Reprogramar y Eliminar

El rol "usuario" podrá cancelar, reprogramar y eliminar cirugías en Sala de Operaciones, acciones que hoy son exclusivas de SuperAdmin. Los demás roles (Admin, Médico, Anestesia) no cambian.

## Quién lo usa
Personal con rol "usuario" que gestiona el día a día de Sala de Operaciones. Ya puede crear/editar cirugías y gestionar equipo e insumos; hoy le falta poder cancelar, reprogramar o eliminar un registro sin depender de un SuperAdmin.

## Funcionalidad principal y experiencia
- Botón de cancelar (ícono X) visible para "usuario" tanto en el listado como en el detalle de cada cirugía activa.
- Al cancelar, puede indicar un motivo y, opcionalmente, una fecha y hora de reprogramación. Si se indica, se crea automáticamente la nueva cirugía activa en esa fecha/hora, igual que ya ocurre hoy cuando lo hace SuperAdmin.
- Botón de eliminar (ícono de basurero) visible para "usuario", con la misma confirmación que ve hoy SuperAdmin. Es una acción permanente, no hay papelera de reciclaje.
- Sin cambios para Admin, Médico o Anestesia: Admin sigue sin poder cancelar, reprogramar ni eliminar (igual que hoy, confirmado); Médico sigue como hasta ahora; Anestesia sigue en solo lectura.

## Flujo de uso
1. "usuario" abre Sala de Operaciones → Cirugías.
2. En una fila, o dentro del detalle de una cirugía, ahora ve los íconos de ver, cancelar y eliminar (antes solo tenía "ver" para esas dos acciones).
3. Cancelar: abre el mismo diálogo que usa hoy SuperAdmin (motivo + fecha/hora opcional de reprogramación). Al confirmar, la cirugía queda marcada como cancelada y, si se indicó reprogramación, aparece la nueva cirugía en la fecha elegida.
4. Eliminar: abre el mismo diálogo de confirmación que usa hoy SuperAdmin. Al confirmar, el registro desaparece del listado de forma permanente.

## Estilo visual
Sin cambios de estilo ni de componentes: se reutilizan exactamente los mismos botones, íconos y diálogos que SuperAdmin ya usa hoy para estas dos acciones; solo se habilitan también para el rol "usuario".

## Fases
**Fase 1 (ahora — MVP):** Habilitar para "usuario" las acciones de cancelar/reprogramar y eliminar cirugías, reutilizando los flujos y diálogos ya existentes. Ningún otro rol cambia.

**Fase 2 (futuro):** Evaluar si Admin también debería tener acceso a cancelar/reprogramar cirugías (hoy tampoco lo tiene, a diferencia de lo que se creía). Queda pendiente de una solicitud explícita, no se construye ahora.

**Fase 3 (futuro):** Vista de auditoría para revisar quién canceló, reprogramó o eliminó cada cirugía y cuándo (hoy esa información se guarda internamente pero no hay una pantalla dedicada para consultarla).

## Supuestos
- Las capacidades que "usuario" ya tenía (ver, crear, editar cirugías, agregar/editar/eliminar equipo e insumos) no cambian con este plan.
- Admin no gana ninguna capacidad nueva en este plan; se confirmó que debe quedar como está hoy.
- La lógica de reprogramación no cambia: sigue clonando la cirugía original a la nueva fecha/hora exactamente igual que cuando lo hace SuperAdmin hoy.
- Eliminar sigue siendo una acción permanente e irreversible, igual que hoy para SuperAdmin; no se agrega confirmación adicional ni papelera de reciclaje.
- No se crean roles nuevos ni se tocan los menús o accesos ya configurados para otros roles.
