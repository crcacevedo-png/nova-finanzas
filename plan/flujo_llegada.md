# Flujo de llegada + tipo "Procedimiento" — estado

## Hecho (código, frontend compila sin errores)
- `Agenda.js`: "Procedimiento" agregado a TIPOS_CITA (backend acepta `tipo_cita` como texto libre, no requiere cambio).
- `Agenda.js`: helper `fichaIncompleta` (nombre, apellido, sexo, fecha nac., teléfono, DPI, dirección, institución; IGSS exige unidad).
- `handleMarcarLlegada(cita)`: si la ficha está incompleta abre el modal `completar-ficha-dialog`; si no, marca Presente.
- `handleWalkIn`: misma validación antes de `createWalkIn`.
- `guardarCompletarFicha`: valida, hace `patientApi.update` (mismo ID, sin duplicar) y luego ejecuta la acción pendiente.
- CitaCard "Marcar llegada" usa `onMarcarLlegada` (pasado en los 3 call-sites).

## Pendiente (requiere salir de modo plan)
1. Prueba E2E: paciente de prueba `TEST-INCOMPLETO-PAC` + cita `TEST-LLEGADA-CITA` (hoy, Dr. Carlos Méndez) ya insertados.
   - Mi Agenda → ⋮ → Marcar llegada → modal → completar → Presente → aparece en "Mis Pacientes Presentes".
   - Walk-in con paciente incompleto y completo.
   - Paciente IGSS sin unidad.
2. Bloquear abrir evaluación desde Agenda si la ficha está incompleta.
3. Limpiar los datos de prueba y actualizar `/app/memory/PRD.md`.
