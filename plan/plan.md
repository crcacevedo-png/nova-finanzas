# Manual Operativo del Superadministrador — NovaVisión ERP

Un manual en PDF, en español, que explica cómo operar correctamente todos los módulos de NovaVisión ERP desde la cuenta de superadmin. Se entrega como archivo descargable en este chat, listo para imprimir o compartir con quien asuma ese rol.

## Para quién es

- El superadmin actual del sistema (uso diario y de referencia).
- Cualquier persona que en el futuro reciba el rol de superadmin o admin y necesite ponerse al día sin depender de explicaciones verbales.

## Qué cubre el documento

Manual operativo completo, organizado por módulo, cada uno con los pasos para usarlo correctamente y qué cuidar para que no se generen datos inconsistentes:

- **Pacientes**: alta, edición, búsqueda, datos de institución/seguro/IGSS.
- **Agenda**: programación de citas, sincronización con Google Calendar.
- **Sala de Operaciones**: registrar/editar/cancelar/reprogramar cirugías, Pre-Ops, LIO, equipo e insumos.
- **Procedimientos de Anestesia**: registros automáticos desde cirugía, cierre mensual, pago individual por procedimiento, exportación Excel/PDF.
- **Evaluaciones Oftalmológicas**: autoguardado, diagnósticos persistentes, recetas.
- **Óptica y Punto de Venta (POS)**: ventas, cobros, FEL (factura electrónica), ventas del día.
- **Caja**: apertura/cierre de caja, conciliación, cuentas por cobrar.
- **Facturación Electrónica (FEL)**: certificación, consulta, anulación.
- **Roles y Permisos**: qué controla cada rol (admin, médico, usuario, anestesia, óptica, administrador_igss) y cómo ajustar permisos sin romper accesos.
- **Respaldos**: respaldo semanal automático y cómo verificarlo.
- **Correos automáticos**: cierre del día (18:00) e informe diario de anestesia (17:00) — qué contienen, a quién llegan y cómo cambiar destinatarios.
- **Solución de problemas comunes**: ej. un correo automático no llegó, un usuario no ve un menú que debería, un enlace de pago no confirma, un mes de anestesia aparece cerrado y no se puede editar, etc. — causa probable y qué revisar primero.

No incluye capturas de pantalla (solo texto e instrucciones paso a paso, con los nombres exactos de botones/menús entre comillas) ni valores reales de contraseñas o llaves — para esas se indica dónde se gestionan, nunca el valor.

## Cómo se entrega y se usa

1. Se genera el documento como PDF.
2. Se comparte el archivo en este mismo chat para descarga directa.
3. El superadmin lo abre, usa el índice para saltar a la sección que necesita, o lo lee completo una vez al recibirlo.
4. Puede imprimirse o guardarse como referencia permanente.

## Estilo del documento

- Portada con el nombre del sistema y fecha de emisión.
- Índice al inicio con los módulos como en la lista de arriba.
- Cada sección numerada, con pasos en listas claras y los nombres de botones/menús citados tal como aparecen en el sistema (ej. "clic en 'Registrar cirugía'").
- Recuadros destacados para advertencias importantes (ej. "no cerrar el mes de anestesia hasta confirmar todos los pagos").
- Sección final de solución de problemas en formato pregunta → causa probable → qué hacer.
- Tipografía y colores simples, pensados para lectura en pantalla o impresión en blanco y negro.

## Fases

**Fase 1 — MVP (se construye ahora)**
Manual completo en PDF con todos los módulos listados arriba y la sección de solución de problemas, entregado en este chat.

**Fase 2 — futuro**
Agregar capturas de pantalla reales a cada sección una vez que el usuario confirme que el diseño actual de cada módulo ya es estable y no cambiará pronto.

**Fase 3 — futuro**
Versiones cortas tipo "hoja de referencia rápida" derivadas del manual completo, una por rol (admin, médico, usuario, anestesia, óptica), con solo lo que cada rol necesita.

## Supuestos

- El documento se escribe en español, igual que el resto del sistema.
- Se basa en las funcionalidades ya implementadas y documentadas a la fecha; no describe funciones pendientes del backlog.
- Se entrega como un único archivo PDF enlazado en el chat, no por correo.
- No se incluyen capturas de pantalla en esta fase (elegido por el usuario).
- No se incluyen contraseñas, llaves ni datos sensibles reales — solo referencia a dónde se gestionan.
- El documento es de uso interno del superadmin; no se publica dentro de la aplicación.
