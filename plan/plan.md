# Mejoras a la Evaluación Oftalmológica: Notas, Lensometría/Autorefractómetro y Copiar Refracción

Tres mejoras a la pantalla de evaluación oftalmológica: una nota por paciente que se mantiene entre consultas, un identificador para el área de Lensometría/Autorefractómetro, y un botón para copiar la refracción a la receta de anteojos.
El objetivo es agilizar la carga clínica y evitar reescribir datos que ya existen en el examen.

## Para quién es
Médicos oftalmólogos y personal clínico de Novavisión que registran evaluaciones en el expediente del paciente.

## Funciones principales y experiencia

### 1. Notas por paciente (constante en todas las consultas)
- Se agrega una casilla de **Notas** debajo de la columna de Medicamentos.
- La nota pertenece al paciente: el texto escrito aparece en todas sus consultas, actuales y futuras.
- Es editable en cualquier consulta; al guardar, siempre se muestra el último texto ingresado para ese paciente.
- No forma parte del informe PDF (es una nota de trabajo interna), salvo que se pida lo contrario más adelante.

### 2. Identificador Lensometría / Autorefractómetro
- En el área que hoy se llama "Lensometría" se agrega un botón para marcar si esos valores corresponden a **Lensometría** o a **Autorefractómetro**.
- El título visible del área cambia según la opción elegida.
- La selección se guarda con la evaluación.
- El PDF del informe conserva su título actual (la etiqueta elegida solo se ve en pantalla).

### 3. Copiar Refracción a la primera receta de anteojos
- En el área de **Refracción** se agrega un botón para copiar los valores de refracción (esfera, cilindro, eje y adición de OD y OS) a la **primera receta de anteojos**.
- La receta solo se crea/llena cuando se presiona el botón; no ocurre de forma automática.
- Si todavía no existe una receta de anteojos, se crea la primera con esos valores.
- Si la primera receta ya tiene datos, **se sobrescribe** con los valores de la refracción.

## Flujo de uso
1. El médico abre la evaluación del paciente.
2. Escribe o consulta la nota del paciente en la casilla de Notas (aparece el texto de consultas previas si ya existía).
3. En el área de mediciones, marca si es Lensometría o Autorefractómetro y captura los valores.
4. Captura la refracción; si desea, presiona "Copiar a receta de anteojos" para trasladar los valores a la primera receta.
5. Guarda la evaluación; la nota queda disponible para la próxima consulta del paciente.

## Sensación de UI/UX
- Consistente con el estilo actual del formulario (secciones colapsables, campos OD/OS, acentos azul/esmeralda).
- Los botones nuevos son discretos, con íconos claros y texto corto, ubicados dentro de su sección correspondiente.
- La acción de copiar muestra una confirmación breve (toast) indicando que los valores se copiaron.

## Fases de implementación

### Fase 1 (MVP — se construye ahora)
- Casilla de Notas por paciente, persistente entre consultas.
- Botón e identificador Lensometría/Autorefractómetro (solo en pantalla).
- Botón para copiar refracción a la primera receta de anteojos (sobrescribe si ya tiene datos).

### Fase 2 (futuro)
- Historial/versionado de la nota del paciente (ver quién y cuándo la modificó).
- Opción de incluir la nota en el PDF cuando el médico lo decida.

### Fase 3 (futuro)
- Plantillas de notas rápidas reutilizables.
- Copiar refracción también a lentes de contacto y a recetas adicionales seleccionables.

## Supuestos
- La nota se guarda a nivel del paciente y siempre muestra el último texto; editar en una consulta posterior actualiza la nota para todas (no se mantiene una copia distinta por consulta).
- La nota es texto libre, sin límite estricto de longitud, y no aparece en el informe PDF.
- El identificador Lensometría/Autorefractómetro aplica a ambos ojos (OD y OS) del área; no se separan en dos mediciones distintas.
- "Primera receta de anteojos" es la primera de la lista de recetas de anteojos de esa evaluación.
- Copiar refracción traslada esfera, cilindro, eje y adición para OD y OS; no modifica otros campos de la receta (material, tipo de lente, distancia pupilar, etc.).
- Estas funciones aplican solo a evaluaciones editables (no selladas/bloqueadas).
