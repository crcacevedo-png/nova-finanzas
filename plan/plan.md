# Corrección de Horario a Hora de Guatemala (GMT-6) en Todo el Sistema

El sistema actualmente adelanta el día: a las 6:46 PM del jueves ya muestra el viernes. Este trabajo hace que todo el sistema use la hora oficial de Guatemala (GMT-6) de forma consistente, para que "hoy", las fechas y las horas coincidan con la realidad local.

## Para quién es
Personal de la clínica NovaVisión en Guatemala (recepción, médicos, caja, administración) que depende de que la agenda, las ventas y los cierres reflejen el día y la hora correctos.

## Qué se corrige y cómo se verá

- **El día "hoy" será siempre el de Guatemala.** El cambio de día ocurrirá a la medianoche de Guatemala, no a las 6:00 PM. La Agenda abrirá en el día correcto y el botón "Hoy" llevará al día real.
- **Las horas mostradas serán horas de Guatemala.** Horas de citas, timbres de llegada de pacientes, fechas de ventas, movimientos de caja, cierres financieros, historial de pagos, reportes y registros de auditoría se mostrarán y se agruparán según la hora local.
- **Los filtros y totales "del día" cuadrarán con el calendario local.** "Ventas de hoy", "citas de hoy", "pacientes presentes", conteos del tablero y cierres de caja tomarán como referencia el día de Guatemala.
- **Los selectores de fecha** (nueva cita, reportes, cierres) partirán del día correcto por defecto.
- **La sincronización con Google Calendar** enviará los eventos con la zona horaria de Guatemala para que no se corran de hora.

La apariencia y el funcionamiento no cambian; solo se corrige el cálculo de fechas y horas.

## Alcance acordado
- **Todo el sistema** (Agenda, Dashboards, Caja/Cierres, reportes financieros, auditoría y cualquier punto que use "hoy" o fechas).
- **Los datos ya guardados no se modifican.** La corrección aplica de aquí en adelante en cómo se calcula "hoy" y cómo se muestran las horas. Registros históricos muy antiguos podrían verse desfasados por unas horas en su presentación, pero no se tocan para evitar riesgo sobre la información existente.

## Experiencia del usuario (flujo)
1. El usuario entra al sistema estando en Guatemala (o desde cualquier lugar) y el sistema asume siempre hora de Guatemala.
2. La Agenda muestra el día local correcto; "Hoy" y la navegación por día/semana/mes respetan ese día.
3. Al registrar citas, ventas, pagos o cierres, la fecha y hora quedan ancladas a Guatemala.
4. Los tableros y reportes "del día" muestran lo ocurrido en el día local, sin adelantarse ni atrasarse.

## Sensación / UI
Sin cambios visuales de diseño. El beneficio es de confianza: las fechas y horas "simplemente son correctas" sin importar la hora del día.

## Fases de implementación

**Fase 1 (MVP, se construye ahora):**
- Establecer una única forma de obtener "hoy" y la hora actual en Guatemala, usada en todo el sistema.
- Corregir el cálculo de "hoy" y la presentación de fechas/horas en: Agenda, Dashboard, Dashboard Financiero, Caja y Cierres, Gastos e Historial de Pagos, reportes y Auditoría.
- Asegurar que los filtros/totales "del día" usen el día de Guatemala.
- Ajustar la sincronización con Google Calendar para usar zona horaria de Guatemala.
- Verificar el caso crítico (entre 6:00 PM y medianoche) en Agenda y en los conteos del día.

**Fase 2 (después):**
- Mostrar de forma opcional una etiqueta "hora de Guatemala (GMT-6)" en pantallas clave para dejarlo explícito.
- Revisar notificaciones/recordatorios programados para que disparen según hora local.

**Fase 3 (futuro):**
- Si algún día se opera en más de un país, permitir zona horaria configurable por sede.

## Supuestos
- Guatemala no usa horario de verano; se usa un desfase fijo GMT-6 todo el año.
- El sistema siempre debe operar en hora de Guatemala, aunque un usuario ingrese desde un dispositivo o servidor en otra zona horaria.
- No se migran ni recalculan los datos históricos ya almacenados; solo se corrige el cálculo y la presentación de ahora en adelante.
- No se cambia el diseño ni el flujo; es una corrección de exactitud de fecha/hora.
