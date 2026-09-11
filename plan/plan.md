# NOGs por Unidad IGSS (con contrato y contador de servicios)

## Objetivo
Cada Unidad IGSS tendrá un listado de **NOG**. Cada NOG representa un **contrato de servicios**
del IGSS (por ejemplo, 100 servicios) que la clínica debe cumplir de forma exacta: ni más, ni
menos. El sistema lleva un **contador** que va acreditando (contando) los servicios conforme los
pacientes son atendidos, avisa cuando se acerca al límite y bloquea el NOG cuando se completa.

Se apoya en lo que ya existe: al registrar un paciente referido por IGSS ya se captura su NOG y su
unidad. Lo nuevo es el catálogo de NOG por unidad, los datos del servicio y el conteo automático.

## Qué se va a construir

### 1. NOG = contrato de servicios (dentro de cada unidad)
Cada NOG tendrá:
- **Número de NOG** (identificador, obligatorio).
- **Nombre del servicio** (ej. "Consulta oftalmológica").
- **Tipo de compra**.
- **Cantidad de servicios** contratados (ej. 100) = el límite.
- **Precio del servicio** (unitario).
- Derivados que se calculan solos: **servicios acreditados**, **disponibles** (cantidad −
  acreditados), y valores en quetzales: total (cantidad × precio), acreditado y disponible.

Se podrá crear, editar, activar/desactivar y eliminar NOG (con las mismas personas que hoy
gestionan Unidades IGSS: SuperAdmin y Administrador IGSS).

### 2. Conteo automático de servicios (acreditación)
- Los servicios **no se "descuentan": se acreditan/contabilizan** hacia el total del contrato.
- **Se acredita automáticamente 1 servicio por paciente** cuando el paciente (que tiene ese NOG
  y esa unidad en su ficha) es atendido.
- El conteo es **una sola vez por paciente** en cada NOG (aunque tenga varias atenciones, cuenta 1).
- Se puede **anular** una acreditación hecha por error, y ese servicio vuelve a quedar disponible.

### 3. Avisos y bloqueo (cumplir exacto)
- Al alcanzar el **90%** de la cantidad contratada, el sistema **avisa** (indicador visible) de que
  el NOG está por completarse.
- Al alcanzar el **100%**, el NOG queda **completado/bloqueado**: no se acreditan más servicios
  (no hay sobregiro) y ese NOG deja de poder asignarse a pacientes nuevos.
- La atención clínica del paciente nunca se bloquea; lo que se detiene es el conteo por encima del
  límite, mostrando el aviso correspondiente.

### 4. Listado de pacientes por NOG (dentro de la unidad)
- Al abrir una unidad se ve su lista de NOG con: acreditados / cantidad, disponibles, y estado
  (activo, 90%+, completado).
- Cada NOG se despliega para ver los pacientes acreditados (con fecha de acreditación) y permite
  anular una acreditación.
- También se muestran, aparte, los pacientes de la unidad cuyo NOG aún no está en el catálogo y
  los que no tienen NOG, para no perder de vista a nadie. Solo pacientes activos.

### 5. Registro del paciente
- Al elegir unidad IGSS en la ficha del paciente, el campo NOG ofrecerá los NOG de esa unidad
  (los completados/bloqueados no se podrán elegir). Se mantiene compatibilidad con los NOG que hoy
  están como texto libre.

### 6. Exportar a Excel
- Exportar a Excel (.xlsx) el listado de pacientes de un NOG, y opcionalmente la unidad completa.
- Columnas por paciente: expediente, nombre y apellido, DPI, afiliación IGSS, No. SPS, código,
  tipo de compra, teléfono, edad, NOG y fecha de acreditación.
- El encabezado del NOG mostrará: servicio, tipo de compra, cantidad, precio, acreditados,
  disponibles y valores.

## Decisiones ya confirmadas
- Conteo **automático**, **1 por paciente**, **reversible** (acreditaciones, no descuentos).
- **Aviso al 90%** y **bloqueo al 100%** (cumplir exacto: ni más, ni menos).
- Precio **unitario**; valor total del NOG = cantidad × precio.

## Supuestos que conviene confirmar
1. **Qué dispara la acreditación**: se cuenta cuando el paciente es efectivamente atendido, tomando
   como señal la **creación de su Evaluación Oftalmológica**. Las **citas** de agenda por sí solas
   NO cuentan (una cita puede cancelarse o no presentarse, y eso rompería el conteo exacto).
   Alternativa si lo prefieres: contar cuando una **cita se marque como "atendida"**.
2. **1 por paciente** = cada paciente cuenta 1 sola vez por NOG, sin importar cuántas atenciones
   tenga. Si en realidad necesitas **1 por atención/servicio** (un paciente puede consumir varios),
   dímelo y lo ajusto.
3. Los listados y exportaciones consideran **solo pacientes activos**.

## Fuera de alcance
- No se toca FEL, Google Calendar u otros módulos.
- No se crea menú nuevo: los NOG viven dentro de cada Unidad IGSS.
