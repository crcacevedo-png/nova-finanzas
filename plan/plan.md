# Caja Chica — Óptica

Un menú nuevo para que el personal de Óptica lleve el control del dinero de caja chica: cuánto dinero entra, quién pide dinero y para qué, y cuánto queda disponible. A fin de mes, se puede generar un informe de los movimientos.

## Para quién es

- Personal de Óptica (rol usuario): registra los ingresos y egresos del día a día.
- Admin y Superadmin: también pueden ver y usar Caja Chica, para supervisión.
- Solo Superadmin puede eliminar un registro (ingreso o egreso) ya guardado.

## Funcionalidad principal y experiencia

- **Registrar un ingreso**: monto y fecha. Se usa tanto para el monto inicial de caja chica como para cualquier monto adicional que se reciba después durante el mes.
- **Registrar un egreso**: quién solicitó el dinero, para qué lo solicitó, monto y fecha.
- **Saldo continuo**: la pantalla muestra en todo momento el total ingresado, el total de egresos y el saldo disponible (ingresos menos egresos). Este saldo no se reinicia cada mes; lo que sobra de un mes pasa al siguiente.
- **Historial de movimientos**: lista de todos los ingresos y egresos registrados, con quién los capturó.
- **Edición**: la persona que registró un ingreso o egreso puede editarlo después (por ejemplo, para corregir un error de captura).
- **Eliminación restringida**: solo Superadmin puede eliminar un ingreso o un egreso.
- **Informe de fin de mes**: se elige un mes y se obtiene un resumen (totales de ingresos, egresos y saldo, más el detalle de cada movimiento). El informe se puede ver en pantalla o descargar en Excel.

## Flujo de uso

1. Una persona de Óptica, Admin o Superadmin abre el menú "Caja Chica".
2. Ve el saldo actual: total ingresado, total de egresos y saldo disponible.
3. Cuando se recibe dinero para caja chica (el monto inicial o un refuerzo durante el mes), lo registra como ingreso (monto + fecha).
4. Cuando alguien solicita dinero de caja chica, se registra como egreso: quién lo solicitó, para qué, cuánto y en qué fecha.
5. Si algún dato quedó mal capturado, quien lo registró puede entrar y corregirlo.
6. A fin de mes (o cuando se necesite), se elige el mes a revisar y se genera el informe: un resumen en pantalla con los totales y el detalle de movimientos, con opción de descargarlo en Excel.
7. Si un registro debe eliminarse por completo, solo Superadmin puede hacerlo.

## UI/UX feel

Mismo estilo visual ya usado en el resto del sistema (paneles claros, tablas con totales destacados). El saldo disponible se muestra de forma prominente en la parte superior del menú. Los ingresos y egresos se distinguen claramente en la lista de movimientos (por ejemplo, con color o etiqueta).

En el menú de navegación, "Caja Chica" se coloca como la primera opción, por encima de todos los demás menús existentes.

## Fases de implementación

**Fase 1 — MVP (se construye ahora)**
- Registrar ingresos (monto + fecha).
- Registrar egresos (quién solicitó, para qué, monto, fecha).
- Saldo continuo: total ingresado, total egresado, saldo disponible.
- Historial de movimientos.
- Edición de un movimiento por quien lo registró.
- Eliminación de un movimiento restringida a Superadmin.
- Informe de fin de mes: resumen en pantalla + descarga en Excel.
- Acceso para personal de Óptica, Admin y Superadmin.

**Fase 2 — Comprobantes y categorías**
- Adjuntar un comprobante o foto de recibo a cada egreso.
- Clasificar los egresos por categoría (por ejemplo: papelería, limpieza, transporte) y ver el informe desglosado por categoría.

**Fase 3 — Controles adicionales**
- Aviso cuando el saldo disponible baja de un monto mínimo definido.
- Aprobación previa de egresos grandes antes de descontarlos del saldo.
- Más de una caja chica (por ejemplo, una por sucursal) en vez de una sola para Óptica.

## Supuestos

- La moneda es Quetzales (Q), igual que el resto del sistema.
- "Quién solicitó el dinero" se captura como texto libre (nombre), no como una lista de empleados del sistema.
- El informe de fin de mes se puede generar para cualquier mes pasado, no solo el mes en curso.
- No se pide adjuntar comprobante o foto de recibo en esta fase (queda para la Fase 2).
- El saldo disponible inicia en Q0.00 hasta que se registre el primer ingreso.
- La fecha de un ingreso o egreso se puede ingresar manualmente (no tiene que ser la fecha en que se captura en el sistema), para reflejar la fecha real en que ocurrió el movimiento.
