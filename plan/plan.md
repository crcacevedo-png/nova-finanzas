# Menú NOG: ingreso y gestión central de NOG IGSS

Un menú propio llamado "NOG" para dar de alta y administrar todos los NOG que el IGSS va asignando. Al ingresar un NOG se asigna a su unidad y queda disponible de inmediato para el ingreso de pacientes.

## Para quién es
- Administrador IGSS, SuperAdmin y Administrador (de la clínica). Los tres con el mismo acceso completo: crear, editar y activar/desactivar NOG.

## Qué resuelve
Hoy los NOG se administran únicamente desde adentro de cada Unidad IGSS. Este menú los reúne en un solo lugar, con una lista de todos los NOG de todas las unidades y un formulario para ingresarlos, sin tener que entrar unidad por unidad.

## Datos de cada NOG
- Número de NOG
- Servicio (nombre del servicio del NOG)
- Tipo de compra: Compra Directa, Baja Cuantía, Contrato o Convenio
- Cantidad de cupos (cuántos pacientes/atenciones cubre)
- Precio por cupo
- Unidad a la que pertenece (se elige de las unidades IGSS existentes)
- Fecha de asignación (nuevo campo: la fecha en que el IGSS asignó/autorizó el NOG)

## Funcionalidad y experiencia
- **Lista completa + gestión**: una tabla con todos los NOG de todas las unidades. Cada fila muestra el número, servicio, unidad, tipo de compra, fecha de asignación, cupos (usados / total), disponibles, precio y estado (Activo, Por completarse al 90%, Completado al 100%, Inactivo).
- **Buscador** por número de NOG o servicio, y **filtro por unidad** y por estado.
- **Crear NOG**: botón "Nuevo NOG" que abre un formulario con todos los datos de arriba; la unidad es obligatoria. Al guardar, el NOG queda registrado en esa unidad.
- **Disponible para pacientes de inmediato**: una vez creado (y activo), el NOG aparece como opción al registrar/asignar pacientes de esa unidad, sin pasos adicionales.
- **Editar** cualquier dato del NOG y **activar/desactivar** un NOG. Un NOG inactivo deja de ofrecerse para nuevos pacientes pero conserva su historial.
- **Avisos de cupo**: se mantiene el comportamiento actual — aviso al llegar al 90% de los cupos y bloqueo de nuevas acreditaciones al 100%.
- Este menú convive con la gestión de NOG que ya existe dentro de cada Unidad IGSS; ambas muestran la misma información.

## Flujo del usuario
1. El usuario entra al menú "NOG".
2. Ve la lista de todos los NOG; puede buscar o filtrar por unidad/estado.
3. Presiona "Nuevo NOG", llena los datos, elige la unidad y la fecha de asignación, y guarda.
4. El NOG aparece en la lista y queda disponible para asignarse a pacientes de esa unidad.
5. Cuando sea necesario, edita un NOG o lo desactiva desde la misma lista.

## UI/UX
- Pantalla de tabla consistente con el resto del sistema (mismo estilo que Unidades IGSS), con badges de estado por color y acciones por fila.
- Formulario en diálogo/modal, con validación de campos obligatorios (número, cantidad, unidad).
- En español, con etiquetas claras de tipo de compra y estado.

## Fases
- **Fase 1 (ahora, MVP)**: nuevo menú "NOG" visible para los tres roles; lista completa de NOG de todas las unidades con buscador y filtros; crear NOG (con el campo nuevo Fecha de asignación) asignándolo a una unidad; editar y activar/desactivar; el NOG queda disponible para pacientes al crearse.
- **Fase 2 (después)**: exportación de la lista de NOG y resumen por unidad; alertas automáticas cuando un NOG llega al 90%/100%.
- **Fase 3 (después)**: control de vigencia (fecha de vencimiento) con avisos de NOG por vencer y manejo de renovaciones.

## Supuestos
- El número de NOG es único dentro de una misma unidad; un mismo número puede repetirse en unidades distintas.
- "Administrador" se refiere al rol de administrador general de la clínica (distinto de Administrador IGSS); los tres roles indicados reciben el menú con acceso completo.
- El menú se agrega como una opción propia (submenú) dentro del área IGSS, junto a Unidades IGSS.
- La "disponibilidad para ingreso de pacientes" significa que el NOG activo de la unidad aparece como opción al registrar/editar pacientes de esa unidad; no cambia el flujo de registro de pacientes actual.
- La Fecha de asignación es un dato informativo que se muestra en la lista y en el detalle; no restringe por sí sola la disponibilidad (eso lo definen el estado activo y los cupos).
- Los NOG existentes se conservan tal cual; a los que no tengan Fecha de asignación simplemente se les podrá agregar al editarlos.
- El estado y los contadores de cupos siguen las reglas actuales (90% aviso, 100% bloqueo).
