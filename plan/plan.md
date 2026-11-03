# Sala de Operaciones — Insumos/Equipos, Nota Operatoria y Anestesia

Amplía el módulo de Sala de Operaciones con un catálogo de insumos y equipos quirúrgicos (sin precio), un estado de insumos para que caja sepa si hay cobro adicional en alquileres, notas operatorias que se guardan en el expediente del paciente, y un módulo de Procedimientos de Anestesia con control financiero mensual de honorarios.

## Para quién es
- Personal de quirófano/clínica que registra cirugías y los insumos/equipos que se usaron.
- Usuarios de caja, que necesitan saber si una cirugía de alquiler ya tiene definidos sus insumos para hacer el cobro adicional.
- Médicos cirujanos, que firman y adjuntan la nota operatoria al expediente del paciente.
- Administración y anestesiólogos, que necesitan llevar el record mensual de anestesias y el pago de honorarios.

## Funcionalidades y experiencia

### 1. Submenú "Insumos y Equipos Quirúrgicos"
- Nuevo submenú dentro de Sala de Operaciones para administrar dos listas: **Insumos quirúrgicos** y **Equipos quirúrgicos**.
- Cada elemento del catálogo tiene nombre y una nota/categoría opcional. **No llevan precio.**
- Se pueden crear, editar y desactivar elementos. Esta lista es la que alimenta el registro de cada cirugía.

### 2. Registro de insumos/equipos en la cirugía desde el catálogo
- En el detalle de la cirugía, "Agregar insumo" y "Agregar equipo" ya **no** serán texto libre: se eligen de las listas del catálogo anterior, indicando cantidad y una nota opcional.
- Como los insumos no llevan precio, el detalle de la cirugía deja de mostrar "Total insumos / Total general" basado en precios de insumos (para IGSS se conserva el costo del procedimiento tal como hoy).

### 3. Estado de insumos para caja (solo Alquiler)
- Las cirugías con institución **Alquiler** llevan un estado operativo que indica una de tres situaciones: **pendiente de revisar**, **insumos registrados (listo)** o **sin insumos adicionales**.
- El personal de quirófano marca el estado. Caja ve ese estado claramente para decidir el cobro adicional del alquiler.
- Para instituciones distintas de Alquiler se pueden registrar insumos/equipos igual, pero sin este énfasis de estado para caja.

### 4. Nota operatoria
- Un ícono en cada cirugía abre la "Nota operatoria".
- El **nombre del procedimiento** se copia automáticamente del procedimiento con el que se programó la cirugía (editable).
- Permite escribir el contenido de la nota y una **firma del médico en texto**, autollenada con el nombre del cirujano programado (editable).
- Al guardar, la nota queda en el **expediente del paciente** y aparece en su **historial de consultas** etiquetada como "Nota operatoria — [nombre del procedimiento]".
- Requiere que la cirugía tenga un paciente registrado; si no lo tiene, primero se solicita vincular/seleccionar al paciente.

### 5. Submenú "Procedimientos de Anestesia"
- **Tipos de anestesia**: catálogo donde se crean varios tipos (p. ej. tópica, local, local asistida, general…), cada uno con su **valor/honorario fijo** (igual para todos los anestesiólogos).
- **Registro de anestesias**: cada cirugía genera automáticamente un registro de anestesia (tipo, anestesiólogo y fecha tomados de la cirugía), editable; además se pueden agregar registros manuales.
- **Cierre mensual**: por mes, el sistema agrupa las anestesias por anestesiólogo, mostrando cantidad de procedimientos, el valor por tipo y el **monto total a pagar** a cada anestesiólogo.
- Permite **cerrar el mes** y marcar los honorarios como pagados, para un control financiero completo del pago de anestesias.

## Flujo de uso
1. Administración carga en "Insumos y Equipos Quirúrgicos" los insumos y equipos disponibles (sin precio) y los tipos de anestesia con su valor.
2. Se registra o edita una cirugía como hoy; su tipo de anestesia y anestesiólogo quedan capturados.
3. En el detalle de la cirugía, el personal agrega los insumos/equipos usados eligiéndolos de la lista.
4. Si la cirugía es de Alquiler, marca el estado: "insumos registrados" o "sin insumos adicionales".
5. Caja abre la cirugía de alquiler, ve el estado y realiza (o no) el cobro adicional.
6. El cirujano abre la nota operatoria, revisa el procedimiento autollenado, redacta la nota, confirma su firma y guarda; la nota aparece en el expediente del paciente.
7. Al cierre de mes, administración entra a "Procedimientos de Anestesia", revisa el consolidado por anestesiólogo, cierra el mes y marca los pagos.

## Sensación visual (UI/UX)
- Respeta el estilo actual de Sala de Operaciones (tarjetas, diálogos y tablas existentes).
- Catálogos con listas simples de alta/edición; selección de insumos/equipos mediante menús/búsqueda dentro del detalle de la cirugía.
- Estado de insumos como etiqueta de color visible en la tabla/detalle de cirugías de alquiler.
- Nota operatoria dentro de un diálogo, con el procedimiento y la firma prellenados.
- Módulo de anestesia con una vista de tipos/tarifas y una vista de cierre mensual con totales por anestesiólogo.

## Fases de implementación

### Fase 1 (MVP, lo que se construye ahora)
- Submenú "Insumos y Equipos Quirúrgicos" con las dos listas (sin precio): crear, editar, desactivar.
- Selección de insumos/equipos en la cirugía desde el catálogo (reemplaza el texto libre); se retira el total por precio de insumos.
- Estado de insumos para caja en cirugías de Alquiler (pendiente / insumos registrados / sin insumos adicionales), visible para caja.
- Nota operatoria con procedimiento autollenado y firma en texto (cirujano), guardada en el expediente del paciente y marcada en el historial de consultas.
- Submenú "Procedimientos de Anestesia": tipos de anestesia con valor, registros automáticos desde cada cirugía + manuales, y cierre mensual por anestesiólogo con monto a pagar y marcado de pago.

### Fase 2 (después)
- Exportación a Excel/PDF del cierre mensual de anestesia y de la nota operatoria (nota imprimible).
- Integración directa del estado/insumos en la pantalla de cobro de caja para alquileres.
- Categorías y filtros en el catálogo de insumos; reporte de uso de insumos por cirugía.

### Fase 3 (después)
- Firma dibujada en pantalla (además de texto) para la nota operatoria.
- Tarifas de anestesia por anestesiólogo (además del valor fijo por tipo).
- Tableros/analítica de anestesia e insumos y, opcionalmente, descuento de insumos del inventario.

## Supuestos
- "No llevan precio": el catálogo de insumos/equipos no maneja precios; cualquier cobro adicional lo decide y registra caja, no este módulo. Por eso el detalle de la cirugía deja de sumar precios de insumos (el costo de procedimiento IGSS se mantiene como hoy).
- Insumos y equipos se administran en un mismo submenú con dos secciones, y ambos se eligen de catálogo al registrarlos en la cirugía.
- El estado de insumos para caja aplica solo a cirugías de institución "Alquiler"; las demás pueden registrar insumos/equipos sin ese estado.
- La nota operatoria requiere un paciente registrado para adjuntarse al expediente; si la cirugía no tiene paciente vinculado, se pide vincularlo primero. El nombre del procedimiento y la firma se prellenan (procedimiento de la cirugía y nombre del cirujano) y son editables.
- Los registros de anestesia se crean y mantienen sincronizados desde la cirugía (tipo, anestesiólogo y fecha) y son editables; también se permiten registros manuales.
- El honorario es un valor fijo por tipo de anestesia (igual para todos los anestesiólogos) y se pueden crear varios tipos; el monto mensual a pagar a cada anestesiólogo es la suma de los valores de los tipos de sus procedimientos del mes.
- Un mes cerrado puede marcarse como pagado y queda de solo lectura tras el cierre.
- La administración de catálogos y el cierre mensual de anestesia (financiero) quedan disponibles para los roles administrativos; el registro operativo (insumos, estado, nota operatoria) para los roles con acceso a Sala de Operaciones.
- Todo el trabajo y los datos de ejemplo permanecen solo en el entorno de preview.
