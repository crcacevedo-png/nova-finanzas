# Medicamentos y Procedimientos (EXCLUSIVO IGSS) en la Evaluación Oftalmológica

Nueva sección dentro de la evaluación oftalmológica para registrar, en listas, los medicamentos y los estudios/procedimientos relacionados con IGSS.
Se ubica entre la sección de Diagnóstico y la de Candidato a cirugía, se distingue con un color verde esmeralda, y su contenido aparece en la impresión de la evaluación.

## Para quién es
Médicos y personal de la clínica NovaVisión que documentan la evaluación oftalmológica del paciente y necesitan dejar registrados los medicamentos y los estudios/procedimientos asociados a IGSS.

## Funciones y experiencia principales
- **Sección propia titulada "Medicamentos y Procedimientos (EXCLUSIVO IGSS)".** Aparece siempre, en toda evaluación, sin importar si el paciente es afiliado IGSS o no.
- **Color distintivo verde esmeralda.** El bloque usa un color verde esmeralda (distinto del teal del resto de la evaluación) para diferenciarlo visualmente de las demás secciones.
- **Ubicación fija.** Se muestra entre la sección de Diagnóstico y la de Candidato a cirugía.
- **Lista de Medicamentos.** El usuario agrega uno o más medicamentos, cada uno en su propio renglón de texto libre. Puede agregar renglones, editarlos y eliminarlos.
- **Lista de Estudios / Procedimientos.** El usuario agrega uno o más estudios/procedimientos, cada uno en su propio renglón de texto libre. Puede agregar renglones, editarlos y eliminarlos.
- **Texto libre por ahora.** Cada renglón se escribe libremente. Más adelante se incorporará el autorelleno a partir de un Excel que el usuario proporcionará (fuera del alcance actual).
- **Se guarda con la evaluación.** El contenido se conserva junto con el resto de la evaluación y se vuelve a mostrar al abrirla.
- **Aparece en la impresión.** Ambas listas se incluyen en la hoja/resumen impreso de la evaluación, con sus respectivos títulos.

## Flujo del usuario
1. El usuario abre o crea una evaluación oftalmológica.
2. Baja hasta la sección "Medicamentos y Procedimientos (EXCLUSIVO IGSS)", ubicada después de Diagnóstico y antes de Candidato a cirugía, identificable por su color verde esmeralda.
3. En Medicamentos, agrega los renglones que necesite (uno por medicamento) y escribe el texto de cada uno.
4. En Estudios / Procedimientos, agrega los renglones que necesite (uno por estudio/procedimiento) y escribe el texto de cada uno.
5. Puede editar o eliminar cualquier renglón.
6. Guarda la evaluación; el contenido queda registrado.
7. Al imprimir la evaluación, las dos listas aparecen en el documento.

## UI/UX feel
Se mantiene el estilo visual actual de la evaluación (mismas tipografías, tarjetas y disposición de las demás secciones), pero este bloque adopta un acento verde esmeralda en su encabezado/borde para diferenciarse del teal usado en el resto. La sección se presenta con dos bloques: "Medicamentos" y "Estudios / Procedimientos". Cada bloque muestra sus renglones con un control para agregar uno nuevo y un control para eliminar cada renglón existente. Cuando no hay renglones, se muestra un estado vacío discreto invitando a agregar el primero.

## Fases de implementación

**Fase 1 (MVP — se construye ahora):**
- Agregar la sección "Medicamentos y Procedimientos (EXCLUSIVO IGSS)" entre Diagnóstico y Candidato a cirugía, visible siempre y con color distintivo verde esmeralda.
- Lista de Medicamentos con texto libre: agregar, editar y eliminar renglones (uno o varios).
- Lista de Estudios / Procedimientos con texto libre: agregar, editar y eliminar renglones (uno o varios).
- Guardar y recuperar el contenido junto con la evaluación.
- Incluir ambas listas en la impresión/PDF de la evaluación.

**Fase 2 (después):**
- Autorelleno de Medicamentos desde el Excel que el usuario proporcionará (sugerencias/selección al escribir).
- Autorelleno de Estudios / Procedimientos desde el Excel correspondiente.

**Fase 3 (después):**
- Refinamientos derivados del uso del autorelleno (por ejemplo, catálogos editables o campos adicionales por renglón), según se definan más adelante.

## Assumptions
- La sección se muestra en todas las evaluaciones, para cualquier paciente (no se limita a afiliados IGSS), según lo indicado.
- El color distintivo del bloque es verde esmeralda, aplicado al encabezado/borde de la sección sin alterar el estilo general de la evaluación.
- Cada medicamento y cada estudio/procedimiento es una sola línea de texto libre; no se piden campos separados adicionales (dosis, código, etc.) en esta fase.
- Se permiten cero, uno o varios renglones en cada lista; una lista vacía es válida.
- El título visible de la sección es "Medicamentos y Procedimientos (EXCLUSIVO IGSS)" y los sub-bloques se llaman "Medicamentos" y "Estudios / Procedimientos".
- En la impresión, cada lista aparece bajo su título; si una lista está vacía, no se agrega contenido de esa lista.
- El autorelleno desde Excel queda fuera del alcance actual y se abordará cuando el usuario adjunte los archivos.
- Las evaluaciones existentes que no tengan esta información se mostrarán con las listas vacías, sin afectar su contenido actual.
