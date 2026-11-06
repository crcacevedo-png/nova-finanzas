# Flujo IGSS: que el ingreso del paciente alimente producción (SPS, descripción del servicio, NOG por unidad)

Corregir el módulo de Producción IGSS para que cada paciente IGSS atendido aparezca correctamente, con su No. SPS y la descripción del servicio, agrupado por unidad, y para que cada autorización descuente su cupo de NOG sin importar qué usuario autorizado ingresó los datos.

## Para quién es
- Personal que ingresa pacientes IGSS y da seguimiento a la producción: roles **usuario**, **usuario IGSS**, **óptica** y **administrador IGSS** (más superadministrador). Todos los roles permitidos deben poder completar el mismo flujo de un paciente IGSS.

## Qué está fallando hoy (causa)
- El listado de Producción se arma a partir de las **evaluaciones** y, para el No. SPS y el procedimiento, solo mira la evaluación o, como respaldo, la **primera** orden del paciente. Por eso:
  - Cuando la evaluación trae NOG pero no trae No. SPS, el No. SPS sale vacío (“—”) aunque sí se haya capturado al ingresar al paciente.
  - La columna **Procedimiento** queda vacía porque no se está tomando la descripción del servicio del NOG.
  - Algunos pacientes IGSS atendidos **no aparecen** en producción por reglas de filtrado (p. ej. evaluaciones sin médico/sin datos quedan ocultas, o autorizaciones absorbidas por registros antiguos sin SPS).

## Qué cambia (Fase 1 – lo que se construye ahora)
1. **No. SPS siempre correcto por autorización.**
   - En producción, el No. SPS de cada línea se toma de la autorización del paciente (la orden IGSS cuyo NOG coincide con el de la atención). Si la evaluación no trae SPS, se completa con el de esa orden. Deja de salir “—” cuando el dato sí fue capturado.
2. **Procedimiento = descripción del NOG.**
   - La columna Procedimiento muestra la **descripción/nombre del servicio del NOG** correspondiente (del catálogo de la unidad). Ya no queda en blanco.
3. **Una línea y un descuento por autorización (NOG + No. SPS).**
   - Cada autorización distinta del paciente genera **una** línea en producción y descuenta **una** unidad de su NOG. Un paciente con dos autorizaciones aparece dos veces y descuenta dos unidades. Las consultas de seguimiento de la misma autorización se consolidan en esa misma línea (no duplican descuento).
4. **Todos los pacientes atendidos aparecen, agrupados por unidad.**
   - Se corrigen las reglas que hoy dejan fuera a pacientes IGSS válidos, de modo que cada autorización atendida en el período se muestre una vez, bajo la **unidad** y el **NOG** que le corresponde al paciente.
   - La **fecha** que se muestra y con la que se filtra cada servicio sigue siendo la **fecha de la evaluación/consulta**.
5. **NOG asignado desde el ingreso del paciente (varias órdenes por paciente).**
   - Se **mantiene tal cual** la capacidad actual de agregar **más de una orden/autorización** a un mismo paciente; no se elimina ni se limita.
   - El formulario de ingreso del paciente permite agregar/asignar el NOG (y su No. SPS) de cada orden. Cada orden del paciente se refleja en producción dentro de la unidad del paciente, como su propia línea.
6. **El descuento funciona para todos los roles permitidos.**
   - Al ingresar o editar un paciente IGSS, el descuento del NOG por autorización se aplica igual, sin importar si lo hizo usuario, usuario IGSS, óptica o administrador IGSS.
7. **Corrección de lo ya ingresado (reproceso).**
   - Un recálculo deja al día los pacientes ya ingresados: ajusta los descuentos de NOG por autorización y hace que aparezcan correctamente en producción con su SPS y descripción.

## Flujo de uso
1. Cualquier usuario permitido ingresa un paciente IGSS con todos sus datos: unidad, NOG, No. SPS y la autorización correspondiente.
2. Al guardar, el sistema descuenta una unidad del NOG por cada autorización (NOG + No. SPS) del paciente.
3. Cuando el paciente es atendido (evaluación), su servicio aparece en el listado de Producción, agrupado por unidad y NOG, con No. SPS visible, la descripción del servicio del NOG y la fecha de la consulta.
4. El administrador IGSS marca impreso/enviado/facturado/pagado y ajusta costo igual que hoy, y exporta el reporte por unidad.

## Sensación de UI/UX
- Se mantiene la pantalla actual de Producción (agrupada por unidad y por NOG, con las columnas Paciente, Exp., No. SPS, Procedimiento, Médico, Fecha, Costo y los estados). Solo cambia que No. SPS y Procedimiento ahora se llenan correctamente y aparecen todos los pacientes que corresponden.
- El formulario de ingreso del paciente conserva su aspecto; se asegura que el campo de NOG/autorización esté disponible para todos los roles permitidos.

## Fases de implementación
- **Fase 1 (MVP, se construye ahora):** correcciones de los puntos 1–7: No. SPS por autorización, Procedimiento con la descripción del NOG, una línea/descuento por autorización, visibilidad completa de pacientes agrupados por unidad, NOG desde el ingreso reflejado en producción, descuento para todos los roles permitidos y recálculo de lo ya ingresado.
- **Fase 2 (posterior):** validaciones al ingresar (avisar si una autorización no tiene No. SPS o si el NOG ya no tiene cupo), y un indicador de datos incompletos por fila en producción.
- **Fase 3 (posterior):** reportes comparativos por unidad y período, y envío/descarga programada del reporte de producción.

## Supuestos
- Cada paciente IGSS que deba aparecer en producción tiene su atención registrada como evaluación/consulta (la fecha de producción es la de esa consulta, según lo indicado).
- La “autorización” es el par **NOG + No. SPS**; dos órdenes del mismo NOG con distinto No. SPS cuentan y descuentan por separado; varias consultas con el mismo No. SPS se consolidan en una sola línea y un solo descuento.
- Se conserva la funcionalidad actual de **múltiples órdenes por paciente**: cada orden es una autorización independiente que genera su propia línea en producción y su propio descuento de NOG.
- La descripción que se muestra en Procedimiento es el nombre del servicio definido en el NOG del catálogo de la unidad.
- Un servicio sin NOG no descuenta cupo; se asigna el NOG en el ingreso del paciente y a partir de ahí se refleja en la unidad correspondiente.
- No se cambian los permisos: el acceso al listado de Producción y sus acciones sigue siendo de administrador IGSS y superadministrador; el ingreso de pacientes IGSS lo pueden hacer los roles ya permitidos (usuario, usuario IGSS, óptica, administrador IGSS).
- Se mantiene el diseño, las columnas y la exportación actuales; no se crean pantallas nuevas.
- La verificación de la causa de “pacientes que no aparecen” se confirmará durante la construcción reproduciendo el caso con datos reales antes de dar por cerrado el arreglo.
