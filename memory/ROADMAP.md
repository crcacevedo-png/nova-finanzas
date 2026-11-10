# ROADMAP - NovaVision ERP Oftalmológico

Backlog priorizado. Para contexto completo de cada ítem ver `CHANGELOG.md` (sesión donde se originó).

## P0 — Bloqueadores / pendientes de confirmación en producción
- Confirmar que el deploy del fix "texto superpuesto en PDF de Cierre + columna Institución" (Sesión, 2026-11) quedó activo en producción.
- Confirmar que el deploy de "pago individual por procedimiento en Cierre mensual de Anestesia" (2026-11) quedó activo y validado por el usuario en producción.
- Confirmar deploy y validación en producción del fix de Sesión 53 (2026-02): autoguardado de "Lectura de Exámenes" + diagnósticos persistentes.
- Confirmar deploy y validación en producción del fix de Sesión 54 (2026-02): rol "usuario" puede crear/editar cirugías + cierre de bypass de cancelación. Verificar si existe un doc personalizado de "usuario" en `db.roles` de producción que necesite actualizarse manualmente (vía Gestión de Roles) para incluir `manage_sala_operaciones`.
- Confirmar deploy y validación en producción del fix de Sesión 55 (2026-02): rol "usuario" puede cancelar/reprogramar/eliminar cirugías.
- Confirmar deploy y validación en producción de la Sesión 56 (2026-02): FEL en el Punto de Venta de Óptica.
- Confirmar deploy y validación en producción de la Sesión 57 (2026-02): fix de "Confirmar Venta" deshabilitado en el POS de Óptica.
- Investigación sin causa raíz confirmada: "Tipo de Compra" IGSS desactualizado en un PDF de producción — pendiente de que el usuario indique el PDF/reporte exacto para reproducir.
- Confirmar que el usuario importó exitosamente las 192 cirugías pendientes a producción vía el importador de Excel.

## P1 — Próximos pasos conocidos (mencionados por el usuario o como continuación natural)
- Diagnósticos (Fase 2 del plan aprobado): indicador de cuánto tiempo lleva activo un diagnóstico sin resolver (ej. "activo desde hace 3 consultas"); filtro en historial del paciente para ver solo diagnósticos resueltos vs. activos.
- Diagnósticos (Fase 3): alertas/resumen al abrir el expediente si hay diagnósticos activos de larga data sin resolver.
- Paciente rápido desde Registrar Cirugía — Fase 2: alertas de ficha incompleta en próximas cirugías, sugerencia de fusión de pacientes duplicados/similares.
- Paciente rápido — Fase 3: permitir creación rápida de paciente solo con nombre desde Agenda, tras validación real del flujo actual.
- Sala de Operaciones: alertas/filtro opcional de Pre-Ops incompletos.
- NOG: exportación de la lista + alertas automáticas al 90%/100% de cupo; control de vigencia/vencimiento.
- Completar valores faltantes en registros IGSS/seguro importados desde la hoja de cálculo original.
- Confirmar si el rol "medico" debería tener el menú "sala_operaciones" por defecto (en preview no lo tiene, pero test_credentials.md documenta que sí debería verlo; no bloquea el backend, que ya funciona vía API para medico).
- Confirmar si "administrador_igss" debe seguir siendo de solo lectura en Sala de Operaciones (hoy no tiene `manage_sala_operaciones`).
- Sala de Operaciones: agregar una insignia visual "Cancelada" en las filas canceladas del listado (hoy solo se ven atenuadas/grises).
- Evaluar si Admin también debería poder cancelar/reprogramar/eliminar cirugías (Fase 2 del plan de Sesión 55, no solicitado aún).
- Vista de auditoría de quién canceló/reprogramó/eliminó cada cirugía y cuándo (Fase 3 del plan de Sesión 55).
- Óptica POS FEL — Fase 2: indicador de estado de factura (facturada/pendiente) directamente en cada fila de "Ver Ventas del Día" sin abrir el detalle.
- Óptica POS FEL: bloquear en el backend la certificación de una venta ya cancelada (hoy no lo impide; aplica igual para Clínica, no introducido por esta sesión).
- "Ver Ventas del Día" (Óptica y posible paridad en Clínica): el conteo del encabezado excluye ventas canceladas aunque sí aparecen en la lista con su insignia; evaluar si se debe aclarar o filtrar.
- Punto de Venta de Óptica: mostrar en el diálogo de pago cuánto se "agregará" del monto escrito aún no confirmado con "+" (ej. "Se agregará Q45.00 (Efectivo) al confirmar"), para que el usuario entienda el nuevo comportamiento sin ambigüedad.
- Al cancelar una venta de Óptica con Cuenta por Cobrar asociada, la cuenta por cobrar queda abierta (no se cancela junto con la venta) — pre-existente, no introducido por el fix reciente.
- Evaluar si el mismo problema de "Confirmar Venta deshabilitado al escribir el monto sin presionar +" también debería corregirse en el Punto de Venta de la Clínica (no se tocó, usa código separado).

## P2 — Pausado / depende de terceros
- FEL/Digifact: activación de producción pendiente de certificado SAT/Digifact, aprovisionamiento y credenciales seguras del usuario.

## Notas de arquitectura a vigilar (deuda técnica, no bloqueante)
- `EvaluacionOftalmologica.js` supera las 3800 líneas; se recomienda extraer secciones (ej. `DiagnosticosSection`) a componentes propios.
- Las filas de diagnósticos usan `key={idx}`; un id estable sería más robusto ante reordenamientos.
- Existen dos matrices de permisos (`config/permissions.py` y una heredada en `server.py`) que deben mantenerse sincronizadas manualmente para cualquier permiso nuevo.
