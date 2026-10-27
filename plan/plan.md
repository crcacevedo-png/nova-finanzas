# Producción IGSS — Un servicio por orden, sin duplicados

La pestaña Producción IGSS deja de repetir al mismo paciente. Cada orden (No. SPS) aparece como una sola línea por paciente, y las evaluaciones en blanco creadas por error ya no se listan ni suman a la producción.

## Para quién es
- Administrador IGSS y administración de la clínica que revisan, imprimen, facturan y cobran la producción de servicios IGSS por día o por rango de fechas.

## Qué cambia (comportamiento)
- **Una línea por orden (No. SPS) por paciente.** Si un paciente tiene varias evaluaciones el mismo día sobre la misma orden, se muestra una sola fila consolidada en lugar de una por cada evaluación.
- **Órdenes distintas siguen separadas.** Si el mismo paciente tiene dos órdenes diferentes (dos No. SPS), sí aparecen como dos líneas.
- **Evaluaciones en blanco ocultas.** Una evaluación sin médico asignado y sin datos clínicos (sin procedimiento, sin diagnóstico ni contenido real) se considera borrador creado por error y no se muestra ni cuenta como servicio.
- **La fila consolidada representa el servicio real.** Para cada orden se toma la evaluación con datos (la más completa / más reciente con contenido). Desde esa fila se abre el expediente, se imprime el PDF y se marcan los estados Impreso / Enviado / Facturado / Pagado y el costo, igual que hoy.
- **Totales corregidos.** Los contadores de arriba (Servicios, Producción, Pagado, Pendiente, Facturado, Enviado) y los subtotales por unidad y por NOG reflejan las líneas ya consolidadas, por lo que los montos dejan de estar inflados.
- **Solo cambia la vista.** Las evaluaciones vacías que ya quedaron guardadas en la base de datos no se borran; simplemente dejan de aparecer y de duplicar en Producción.

## Flujo del usuario
1. El usuario entra a IGSS → Unidades IGSS → pestaña Producción.
2. Elige Día o Rango, y opcionalmente filtra por unidad o por NOG (igual que ahora).
3. Ve la lista agrupada por unidad y NOG, con una sola línea por paciente y orden.
4. Abre el expediente, imprime, ajusta costo o marca estados desde esa línea; los totales cuadran con lo mostrado.
5. Exporta a Excel: el archivo sale con las mismas líneas consolidadas que se ven en pantalla.

## Qué NO cambia
- No se modifican las evaluaciones oftalmológicas ni la forma de crearlas/continuarlas.
- No se eliminan registros de la base de datos.
- No cambian los filtros, permisos ni la estética de la pantalla.

## Cómo se decide qué es "evaluación en blanco"
Se considera vacía (y se oculta) cuando no tiene médico asignado y no tiene ningún dato clínico cargado (sin procedimiento IGSS, sin diagnóstico, sin agudeza visual/refracción ni otros campos del examen). Si tiene cualquiera de esos datos, se trata como servicio real.

## Fases
- **Fase 1 (ahora, MVP):** Consolidar Producción a una línea por paciente + No. SPS, ocultar evaluaciones en blanco, y corregir totales, subtotales y exportación a Excel para que coincidan con la vista. Solo a nivel de vista/reporte.
- **Fase 2 (después):** Herramienta opcional para revisar y limpiar en la base los borradores vacíos duplicados que ya existen (con confirmación), y recálculo del consumo de NOG para que no quede inflado por evaluaciones vacías previas.
- **Fase 3 (después):** Evitar desde el origen que se generen borradores vacíos (no crear evaluación hasta que haya un dato real) para que el problema no se repita.

## Supuestos
- La orden se identifica por su No. SPS; cuando una evaluación no trae No. SPS pero sí NOG, se agrupa por NOG como respaldo, y si no trae ninguno, se agrupa por paciente de ese día.
- Al consolidar, si varias evaluaciones de la misma orden tienen datos, se usa la más reciente con contenido como representante para abrir/imprimir y para los estados y el costo.
- Los estados y el costo ya marcados sobre una evaluación se conservan y se muestran en la fila consolidada correspondiente.
- El alcance es la pestaña Producción y su exportación; el conteo de acreditaciones/consumo de NOG se revisa en la Fase 2.
