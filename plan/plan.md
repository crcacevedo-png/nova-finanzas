# Órdenes IGSS múltiples por paciente (dos consultas el mismo día)

Permite registrar más de una orden IGSS (cada una con su propio NOG y No. SPS) para un mismo paciente y atender ambas el mismo día como dos consultas distintas.
Cada orden se guarda en el paciente, descuenta del saldo de su unidad IGSS y genera su propio expediente/informe.

## Para quién es
Recepción y personal clínico que ingresa pacientes IGSS, y administradores IGSS que controlan el saldo de NOG por unidad.

## Funciones principales y experiencia

### 1. Lista de órdenes IGSS en el paciente
- En la ficha del paciente IGSS se agrega una sección de **Órdenes** (en lugar de un solo NOG/SPS).
- Cada orden contiene: **NOG**, **No. SPS**, **código IGSS**, y el **procedimiento/estudio** al que corresponde.
- La **unidad IGSS** de todas las órdenes es la misma unidad asignada al paciente.
- Un paciente puede tener varias órdenes (por ejemplo, dos para el mismo día, cada una para un procedimiento distinto).
- La orden IGSS que hoy tiene el paciente (NOG/SPS actuales) se conserva y pasa a ser su primera orden, sin perder datos.

### 2. Dos consultas el mismo día
- Al atender/agendar, se elige **cuál orden** aplica a esa consulta.
- Se permite crear una **segunda cita el mismo día** para el mismo paciente, vinculada a otra orden.
- Las dos consultas aparecen como **dos citas separadas** en la agenda y **cuentan como dos pacientes atendidos**.
- Cada consulta queda ligada a su orden (NOG/SPS), de modo que no se mezclan los datos de una con la otra.

### 3. Descuento de NOG con control individual
- Cada orden **descuenta 1 servicio** del saldo de la unidad IGSS del paciente (dos órdenes distintas = dos descuentos).
- Se mantiene el comportamiento actual de descontar al asignar la orden y de no duplicar el descuento del mismo NOG.
- Se agrega, en el área de unidades IGSS, la posibilidad de **aplicar o liberar el descuento de cada NOG de forma individual** (además del recálculo masivo que ya existe), para corregir casos puntuales a mano.

### 4. Un informe por consulta
- Cada consulta genera su **propio expediente/informe PDF**, mostrando el **NOG y No. SPS de la orden** que le corresponde.
- No se combinan ambas consultas en un solo PDF.

## Flujo de uso
1. Se ingresa o edita al paciente IGSS y se agregan sus órdenes (una o varias), cada una con su NOG, SPS, código y procedimiento.
2. Al asignar cada orden, el sistema descuenta 1 del saldo de la unidad IGSS del paciente.
3. Se agenda/atiende la primera consulta eligiendo la primera orden.
4. Para el mismo día, se crea una segunda cita eligiendo la segunda orden.
5. Se completa cada evaluación por separado; cada una genera su informe con su NOG/SPS.
6. El administrador IGSS puede revisar el saldo de la unidad y, si hace falta, aplicar o liberar el descuento de un NOG puntual.

## Sensación de UI/UX
- Consistente con el estilo actual del sistema (acentos azul/esmeralda, secciones claras, formularios compactos).
- La sección de Órdenes se ve como una lista con botón "Agregar orden", cada fila con sus campos y opción de eliminar.
- La selección de orden al agendar/atender es un selector corto y claro.
- El control individual de descuento en la unidad IGSS muestra, por NOG, si está descontado y botones discretos para aplicar/liberar, con confirmación breve.

## Fases de implementación

### Fase 1 (MVP — se construye ahora)
- Sección de órdenes IGSS por paciente (NOG, SPS, código, procedimiento), con migración de la orden actual a la primera orden.
- Dos citas el mismo día para el mismo paciente, cada una vinculada a una orden, contando como dos atenciones.
- Descuento de NOG por orden, con control para aplicar/liberar el descuento de cada NOG de forma individual en la unidad IGSS.
- Un informe/expediente por consulta, con el NOG y SPS de su orden.

### Fase 2 (futuro)
- Reporte de órdenes por unidad y por fecha, y alertas de saldo bajo de la unidad IGSS.
- Validaciones adicionales (por ejemplo, avisar si un NOG ya fue usado o si una orden quedó sin consulta).
- Estado de cada orden (pendiente, atendida, anulada) con su historial.

### Fase 3 (futuro)
- Adjuntar la orden escaneada (PDF/imagen) a cada orden del paciente.
- Flujo de aprobación/anulación de órdenes con registro de quién y cuándo.

## Supuestos
- Las dos órdenes del mismo día pertenecen siempre a la **misma unidad IGSS** del paciente (según lo indicado).
- Cada orden descuenta **1 servicio**; dos órdenes con NOG distintos generan dos descuentos. No se vuelve a descontar el mismo NOG ya consumido.
- El NOG y No. SPS dejan de manejarse como un único valor fijo del paciente y pasan a vivir dentro de cada orden; los datos actuales del paciente se conservan migrándolos a su primera orden.
- El informe por consulta **sí muestra** el NOG y No. SPS de su orden (esto aplica al expediente de pacientes IGSS con orden).
- Las órdenes y su selección aplican a pacientes IGSS; los pacientes particulares/otros no se ven afectados.
- No hay límite estricto de órdenes por paciente, aunque el caso típico es una o dos.
- La nota clínica, la agenda y demás funciones existentes siguen operando igual.
