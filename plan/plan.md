# NovaVisión ERP — NOG en llegada de pacientes, NOG para óptica, y revisión de ventas de óptica

Tres ajustes que completan el manejo de órdenes IGSS (NOG) en el ingreso de pacientes
y dan a óptica/administración una pantalla para revisar y anular ventas pasadas de óptica.

## Para quién es
Para el personal de recepción y clínico que marca la llegada de pacientes IGSS, para los
usuarios de óptica que registran pacientes, y para óptica, administrador y superadministrador
que necesitan consultar las ventas de óptica ya realizadas.

## Funciones principales y experiencia

### 1. Agregar NOG al marcar la llegada del paciente (y descontar del NOG)
- En el modal "Crear expediente del paciente" (el que aparece al marcar llegada desde la Agenda),
  cuando la institución es **IGSS** y se elige una **Unidad**, aparece la misma sección de
  **Órdenes IGSS** que ya existe en el módulo de Pacientes.
- Se puede **elegir un NOG del catálogo de la unidad o escribir uno libre**, y **agregar más de
  una orden**. Cada orden lleva su propio **No. SPS**, **Código** y **Procedimiento/Estudio**.
- Al guardar, **se descuenta un servicio del NOG correspondiente en el módulo IGSS**, exactamente
  igual que cuando el paciente se registra desde el módulo de Pacientes: respeta el cupo del
  contrato, no duplica el descuento para la misma autorización y libera/ajusta el cupo si luego
  se corrige la orden.
- Las órdenes son opcionales: se puede marcar la llegada sin bloquear si aún no hay NOG.
- Lo ingresado queda guardado en el expediente del paciente y se refleja igual que si se
  hubiera capturado desde el módulo de Pacientes.

### 2. Óptica puede elegir y editar NOG en el módulo de Pacientes
- Hoy el usuario de óptica puede ingresar pacientes pero no logra elegir/editar los NOG; el
  rol "Usuario" sí puede. Se corrige para que **todos los roles con permiso de crear/editar
  pacientes** —incluido óptica— tengan exactamente la misma capacidad de elegir y editar las
  órdenes IGSS (NOG, No. SPS, código, procedimiento), que se guarden correctamente y que
  descuenten del NOG igual que para los demás usuarios.

### 3. Revisar ventas pasadas de óptica (en el menú de Óptica)
- Nueva entrada **"Ventas"** dentro del menú **Óptica**, visible para **óptica, administrador y
  superadministrador**.
- Permite **buscar y filtrar** ventas pasadas de óptica (por rango de fechas, paciente, número
  de venta y estado), **abrir el detalle** de una venta y **reimprimir su ticket/comprobante**.
- Permite **anular (cancelar)** una venta pasada, revirtiendo el **inventario** y los registros
  de **caja / cuentas por cobrar** asociados.
- La anulación es una acción sensible: **solo administrador y superadministrador** pueden
  anular; óptica puede consultar y reimprimir.

## User flow
- **Llegada del paciente:** en la Agenda se marca la llegada → se abre "Crear expediente" →
  se elige IGSS y la unidad → se agregan una o varias órdenes con su NOG, No. SPS y código →
  se guarda y se marca la llegada → el servicio queda descontado del NOG correspondiente.
- **Pacientes (óptica):** el usuario de óptica abre Pacientes → crea o edita un paciente IGSS →
  elige/edita los NOG igual que cualquier otro usuario → guarda y se descuenta del NOG.
- **Ventas de óptica:** óptica/administrador/superadmin entra a Óptica → Ventas → filtra por
  fecha/paciente/estado → abre una venta para ver el detalle y reimprimir → si es admin o
  superadmin, puede anularla (revierte inventario y caja/CxC).

## UI/UX feel
Se mantiene el estilo actual del ERP (marca NovaVisión, tarjetas y tablas limpias, acentos en
azul/teal, todo en español y montos en quetzales). La sección de Órdenes IGSS en el modal de
llegada se ve y se comporta igual que en Pacientes. La pantalla de Ventas de óptica usa el
mismo patrón de listado con filtros, detalle en diálogo y acciones por fila.

## Fases de implementación

### Fase 1 — MVP (se construye ahora)
- Sección de Órdenes IGSS (NOG múltiple con No. SPS, código y procedimiento por orden) en el
  modal de llegada/crear expediente, **con descuento del NOG correspondiente** al guardar.
- Corrección para que óptica (y todo rol con permiso de pacientes) pueda elegir/editar NOG en
  el módulo de Pacientes.
- Entrada "Ventas" en el menú de Óptica con consulta, filtros, detalle, reimpresión y anulación
  (anular restringido a administrador/superadmin), revirtiendo inventario y caja/CxC.

### Fase 2 — Futuro
- Exportar el listado de ventas de óptica a Excel/PDF y totales por período.
- Edición de una orden IGSS directamente desde la lista de llegadas/agenda sin abrir el
  expediente completo.

### Fase 3 — Futuro
- Incluir la revisión de ventas del Punto de Venta de clínica con el mismo patrón.
- Historial/auditoría visible de anulaciones (quién anuló, cuándo y por qué).

## Assumptions
- La parte 3 cubre **solo ventas de óptica** (no clínica), según lo indicado.
- **Anular** queda restringido a **administrador y superadministrador**; el rol óptica solo
  consulta y reimprime. (Según la opción elegida.)
- La nueva función de ventas se ubica en el **menú de Óptica**. (Indicado por el usuario.)
- Las órdenes IGSS en el modal de llegada son **opcionales** y usan el mismo selector de NOG del
  módulo de Pacientes (catálogo de la unidad o texto libre), con No. SPS y código **por cada
  orden**, permitiendo varias órdenes por paciente.
- El descuento del NOG desde el modal de llegada reutiliza la **misma lógica de consumo/
  conciliación** que ya usa el módulo de Pacientes (una acreditación por autorización, respeta
  el cupo, no duplica y libera al corregir), para mantener los contadores del módulo IGSS
  consistentes sin dobles descuentos.
- La anulación de una venta de óptica revierte el inventario y los movimientos de caja/CxC
  asociados, reutilizando el comportamiento de cancelación ya existente y ajustándolo si hace
  falta para dejar inventario y caja consistentes.
- Todos los montos en quetzales y las fechas en zona horaria de Guatemala, como en el resto del
  sistema.
