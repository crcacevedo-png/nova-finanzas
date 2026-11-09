# Expediente Clínico Confiable: Autoguardado de Exámenes y Diagnósticos Persistentes

Corrige el autoguardado de "Lectura de Exámenes" en Evaluación Oftalmológica para que nunca se pierda lo escrito, y convierte los diagnósticos en una lista de problemas activos del paciente que se repite en cada consulta hasta que el médico la marque como resuelta.

## A quién afecta

Médicos y personal clínico que usan el módulo de Evaluación Oftalmológica para registrar exámenes y diagnósticos de cada paciente, en cualquier tipo de consulta (consulta general, control, etc.).

## Funcionalidad principal y experiencia

**1. Autoguardado de Lectura de Exámenes**
- Se revisa por qué el campo "Lectura de Exámenes" (interpretación de estudios auxiliares, laboratorios, imágenes) no queda guardado en el expediente al autoguardarse, y se corrige para que se comporte igual que el resto de campos de la evaluación: se guarda solo y también al presionar "Guardar".
- Se confirma con una prueba real: escribir en el campo, esperar el autoguardado (sin tocar "Guardar"), recargar el expediente y verificar que el texto sigue ahí.

**2. Diagnósticos persistentes entre consultas**
- Cada diagnóstico queda activo para el paciente hasta que alguien lo marque como resuelto — sin importar cuántas consultas pasen o de qué tipo sean (consulta, control, etc.).
- Al abrir una nueva evaluación para un paciente, los diagnósticos activos de su última consulta aparecen ya cargados en "Diagnósticos", con su mismo texto y ojo (OD/OI/OU), editables igual que uno nuevo. No se distinguen visualmente de los diagnósticos que el médico agregue en esa misma consulta.
- Cada diagnóstico (nuevo o traído de antes) tiene un botón para marcarlo como "Resuelto". Al marcarlo:
  - Deja de copiarse a las próximas consultas de ese paciente.
  - Permanece visible en el historial de la consulta donde se registró (no se borra el registro histórico, solo deja de arrastrarse hacia adelante).
- Si el médico borra un diagnóstico traído de antes (en vez de marcarlo resuelto), también deja de aparecer en consultas futuras — se trata igual que si nunca se hubiera copiado.

## Flujo de uso

1. El médico abre una evaluación nueva para un paciente que ya tiene diagnósticos activos de antes.
2. La sección "Diagnósticos" aparece con esos diagnósticos ya precargados.
3. El médico agrega nuevos diagnósticos si corresponde, y escribe en "Lectura de Exámenes" — ambos se autoguardan.
4. Si alguno de los diagnósticos activos ya se resolvió, el médico presiona el botón "Resuelto" en esa fila.
5. Al terminar y guardar, la próxima consulta de ese paciente (de cualquier tipo) arrancará con los diagnósticos que sigan activos, sin el que se marcó resuelto.

## Estilo visual

Sin cambios de estilo: se usan los mismos componentes, tipografía y colores ya existentes en la sección "Diagnóstico y Plan". El único elemento nuevo es un botón pequeño de "Resuelto" junto a cada diagnóstico, con el mismo lenguaje visual que los demás botones de acción de esa sección (como el de eliminar).

## Fases

**Fase 1 (ahora):**
- Corrección del autoguardado de "Lectura de Exámenes", confirmada con una prueba real.
- Diagnósticos activos se copian automáticamente a la siguiente evaluación del paciente, sin distinción visual de cuáles son nuevos.
- Botón "Resuelto" por diagnóstico que lo saca de futuras consultas conservando el historial.

**Fase 2 (futuro):**
- Indicador de cuánto tiempo lleva activo un diagnóstico sin resolver (ej. "activo desde hace 3 consultas").
- Filtro en el historial del paciente para ver solo diagnósticos resueltos vs. activos.

**Fase 3 (futuro):**
- Alertas o resumen para el médico al abrir el expediente si hay diagnósticos activos de larga data sin resolver.

## Supuestos

- Cualquier usuario con permiso para editar la evaluación oftalmológica (médico, admin, optica, etc., según los permisos ya existentes del módulo) puede marcar un diagnóstico como resuelto; no se crea un permiso nuevo solo para esta acción.
- "Última consulta" para efectos de copiar diagnósticos es la evaluación más reciente de ese paciente por fecha, sin importar el tipo.
- Marcar un diagnóstico como resuelto es una acción reversible solo editándolo manualmente de nuevo en una consulta futura (no se construye un botón de "deshacer resuelto").
- La corrección del autoguardado se limita al campo "Lectura de Exámenes"; si al revisarlo aparecen otros campos con el mismo problema, se corrigen como parte del mismo fix.
