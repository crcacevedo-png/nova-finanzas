# Caja y Punto de Venta Individuales por Usuario

Cada usuario maneja su propia caja y su propio punto de venta: abre, registra y cierra únicamente lo suyo.
Las ventas y movimientos quedan atribuidos, en caja y en auditoría, al usuario responsable, y los supervisores ven todo consolidado.

## Para quién es
- Cajeros y recepción de la clínica, que abren y cierran su caja diaria.
- Vendedores de óptica, que cobran ventas a su nombre.
- Administradores y SuperAdmin, que supervisan y cierran las cajas de todos.

## Funcionalidades y experiencia

### Caja de la clínica (individual)
- Cada usuario abre **su** caja del día con su monto de apertura. No hereda ni comparte la caja de otro.
- Un usuario puede registrar ingresos y egresos solo si **su** caja está abierta; esos movimientos pertenecen a su caja.
- El estado, los totales por método de pago y el saldo en efectivo que ve cada usuario corresponden solo a su propia caja.
- Cada usuario hace **su** cierre: cuenta su efectivo, el sistema calcula el esperado y la diferencia, y bloquea sus movimientos del día.
- Una sola caja por usuario por día: tras cerrarla no se vuelve a abrir ese día (salvo reapertura por un supervisor).

### Punto de venta de óptica (individual)
- Cada venta queda registrada a nombre del vendedor que la cobró.
- No se exige tener una caja abierta para cobrar: la venta se procesa igual, pero siempre atribuida al usuario responsable.
- Cada vendedor ve el resumen de **sus** ventas del día (total cobrado y desglose por método de pago).

### Supervisión (Admin y SuperAdmin)
- Vista consolidada de todas las cajas de un día: por usuario, con su estado (abierta/cerrada), montos y diferencia.
- Pueden cerrar o reabrir la caja de cualquier usuario.
- Pueden ver las ventas de óptica de todos los vendedores.

### Auditoría
- Apertura, cierre, reapertura, movimientos y ventas registran al usuario responsable y quedan en el historial de auditoría.

## Flujo del usuario
1. El cajero inicia sesión y abre su caja del día con el monto inicial.
2. Durante el día registra ingresos/egresos, que se suman solo a su caja.
3. En óptica, el vendedor cobra ventas; cada una queda a su nombre.
4. Al terminar, cada usuario cuenta su efectivo y cierra su propia caja; el sistema muestra el esperado y la diferencia.
5. Un supervisor entra a la vista consolidada, revisa las cajas de todos, y si hace falta cierra o reabre alguna.

## Estilo / sensación
- Se mantiene la línea visual actual del sistema (tonos teal, tarjetas y tablas ya usadas).
- La pantalla de caja encabeza con "Mi caja" para el usuario; los supervisores tienen un acceso adicional a "Todas las cajas".
- Indicadores claros de caja abierta/cerrada y de diferencias en el arqueo.

## Fases de implementación

### Fase 1 — MVP (se construye ahora)
- Caja de la clínica individual por usuario: apertura, movimientos, estado, totales y cierre diario, todo acotado a cada usuario (una caja por usuario por día).
- Ventas de óptica atribuidas al vendedor responsable, sin exigir caja abierta, con resumen diario por vendedor.
- Vista consolidada para Admin y SuperAdmin con las cajas de todos y la opción de cerrar/reabrir cualquiera.
- Auditoría de todas las acciones por usuario responsable.

### Fase 2 (posterior)
- Corte de caja formal de óptica por usuario, con conteo de efectivo contra lo esperado y comprobante imprimible.
- Reportes y exportación de cajas y ventas por usuario y rango de fechas.

### Fase 3 (posterior)
- Varios turnos por día por usuario y entrega de turno entre cajeros.
- Tableros de diferencias y alertas por usuario a lo largo del tiempo.

## Supuestos
- El modelo pasa a ser "una caja por usuario por día"; los cierres y movimientos antiguos (caja compartida) se conservan tal cual, visibles para supervisores, sin reescribir históricos.
- Un usuario no puede registrar movimientos de clínica si no tiene su propia caja abierta ese día.
- Un abono de cuentas por cobrar que se marque "registrar en caja" entra a la caja abierta del usuario que lo registra; si ese usuario no tiene caja abierta, el abono se guarda pero no genera movimiento de caja (igual que hoy cuando la caja está cerrada).
- Las ventas de óptica siguen funcionando sin caja; solo se les agrega la atribución al vendedor y el resumen por usuario.
- "Ver todas" y "cerrar/reabrir cualquiera" quedan limitados a los roles Admin y SuperAdmin; el resto solo su propia caja.
- Se mantiene la separación actual entre caja de clínica y óptica.
