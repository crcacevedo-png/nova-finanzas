# Sala de Operaciones — Captura de datos IGSS en cada cirugía

Al registrar una cirugía con institución IGSS, el formulario pedirá los mismos datos que un paciente IGSS (unidad, afiliación, NOG, SPS, código) y llenará el procedimiento automáticamente desde el servicio del NOG. Esta captura es solo informativa: no consume NOG ni crea registros en Producción IGSS.

## Para quién es
- Personal de clínica que registra cirugías en el módulo Sala de Operaciones (roles con acceso a ese módulo).
- Administración IGSS, que necesita que la cirugía quede documentada con su unidad, NOG, SPS y código, sin que eso afecte los contadores ni la producción de IGSS.

## Funcionalidad y experiencia
Hoy, al elegir institución "IGSS" en una cirugía, aparece un bloque con Unidad, SPS, No. de afiliación, Código y Costo, todos como texto libre. El cambio reemplaza ese bloque por una captura guiada equivalente a la de un paciente IGSS:

- **Unidad**: se elige de la lista de unidades IGSS ya existente en el sistema (en vez de texto libre).
- **NOG**: una vez elegida la unidad, se selecciona el NOG de la lista de esa unidad (mismos NOG que se ven en la ficha del paciente). También se permite escribir un NOG libre si no está en la lista.
- **Procedimiento**: se llena automáticamente con el nombre del servicio contratado del NOG elegido y queda **bloqueado** (no editable) mientras la institución sea IGSS.
- **SPS** y **Código**: se capturan a mano.
- **No. de afiliación** y **Costo del procedimiento**: se conservan como hoy.
- Todos estos datos se guardan en el registro de la cirugía y se muestran en el detalle de la cirugía.

Comportamiento clave (sin efectos sobre IGSS):
- Ingresar o elegir un NOG aquí **no** descuenta el cupo del NOG ni cambia sus contadores.
- La cirugía **no** aparece en el módulo de Producción IGSS ni genera acreditaciones.
- La producción y el consumo de NOG siguen funcionando exactamente igual que hoy (se alimentan desde pacientes y evaluaciones, no desde cirugías).

Si la institución no es IGSS, el formulario se comporta igual que hoy (incluido "Seguro Privado" con su nombre de seguro, y el procedimiento como campo escribible normal).

## Flujo de uso
1. El usuario abre "Registrar cirugía" (o edita una existente).
2. Llena fecha, hora, paciente, cirujano, ojo y anestesia como hoy; el procedimiento es escribible.
3. En Institución elige "IGSS". Aparece el bloque IGSS.
4. Elige la **Unidad** de la lista.
5. Elige el **NOG** de la lista de esa unidad (o escribe uno libre). El **Procedimiento** de la cirugía se llena solo con el servicio de ese NOG y queda bloqueado.
6. Escribe **SPS**, **Código**, **No. de afiliación** y **Costo**.
7. Guarda. La cirugía queda con todos los datos IGSS; no se toca ningún contador de NOG ni la Producción IGSS.
8. Si luego cambia la institución a una distinta de IGSS, el procedimiento vuelve a ser escribible.

## Sensación visual (UI/UX)
- Mantiene el bloque "Datos IGSS" actual (tarjeta azul con su etiqueta), respetando el estilo del formulario existente.
- Unidad y NOG como menús desplegables; el NOG muestra número y nombre del servicio, igual que en la ficha del paciente.
- El campo Procedimiento, cuando es IGSS, se ve claramente como "lleno automáticamente / no editable".
- Sin pantallas nuevas: todo ocurre dentro del formulario de cirugía ya existente (crear y editar).

## Fases de implementación
**Fase 1 (MVP, lo que se construye ahora):**
- Reemplazar en el formulario de cirugía el bloque IGSS por: Unidad (lista), NOG (lista de la unidad + opción libre), SPS, Código, No. de afiliación, Costo.
- Autollenar el Procedimiento con el servicio del NOG elegido y bloquearlo mientras la institución sea IGSS.
- Guardar y mostrar estos datos en el registro y el detalle de la cirugía, en crear y editar.
- Garantizar que no hay consumo de NOG ni alta en Producción IGSS.

**Fase 2 (después):**
- Prefijar unidad y afiliación desde la ficha del paciente IGSS seleccionado (cuando exista).
- Mostrar NOG y Código como columnas en la tabla de cirugías y en la exportación a Excel.
- Validaciones de campos obligatorios para cirugía IGSS.

**Fase 3 (después):**
- Reporte de cirugías por unidad/NOG (solo lectura), independiente de Producción IGSS.

## Supuestos
- "Los mismos datos de un paciente IGSS" = unidad, No. de afiliación, NOG, SPS y código; se agregan NOG (nuevo) y se cambia Unidad de texto libre a lista. El Costo del procedimiento se mantiene.
- La Unidad pasa a elegirse del catálogo de unidades IGSS existente; se permite NOG libre por compatibilidad, pero el autollenado del procedimiento solo ocurre cuando el NOG viene de la lista (un NOG libre no tiene servicio asociado).
- El procedimiento bloqueado aplica solo cuando la institución es IGSS; en las demás instituciones sigue siendo campo escribible.
- Se reutilizan las listas de unidades y NOG que ya usa la ficha del paciente; no se crea ningún catálogo nuevo de códigos.
- Las cirugías IGSS ya registradas con el formato anterior se conservan tal cual; el cambio aplica a nuevas capturas y ediciones.
- Nada de lo anterior modifica el consumo de NOG ni la Producción IGSS, que siguen alimentándose desde pacientes y evaluaciones como hasta hoy.
