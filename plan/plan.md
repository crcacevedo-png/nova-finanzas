# Facturación Electrónica (FEL) en el Punto de Venta de Óptica

El Punto de Venta de Óptica podrá emitir, consultar e imprimir la factura electrónica (FEL) de cada venta, igual que ya funciona hoy en el Punto de Venta de la Clínica. Se reutiliza la misma configuración y credenciales de prueba de Digifact ya usadas para la Clínica; no se crea una configuración separada para Óptica.

## A quién afecta

Personal de Óptica que cobra ventas en el Punto de Venta (armazones, lentes, accesorios) y necesita emitir o consultar la factura electrónica de esa venta sin salir del flujo de cobro.

## Funcionalidad principal y experiencia

- **Pantalla de "Venta Exitosa"** (justo después de cobrar): aparece el mismo control de Facturación Electrónica que ya existe en el Punto de Venta de la Clínica — certificar la factura, ver su estado (pendiente, certificada, con error, anulada), descargar/ver el documento, y anular si corresponde.
- **"Ver Ventas del Día"**: hoy esa lista solo muestra el resumen de cada venta sin poder abrir el detalle. Se agrega poder tocar una venta para ver su detalle (productos, totales, forma de pago) y desde ahí también facturar o consultar su FEL, igual que en la pantalla de venta exitosa.
- **Impresión de ticket**: el botón "Imprimir" de la pantalla de "Venta Exitosa" (hoy no hace nada) queda conectado para imprimir el ticket de la venta, con el mismo formato y estilo de ticket térmico que ya usa el Punto de Venta de la Clínica, adaptado a los productos de Óptica (armazones, lentes, accesorios). También se podrá imprimir desde el nuevo detalle de "Ver Ventas del Día".
- Sin cambios en el Punto de Venta de la Clínica ni en el módulo de "Ventas" de Óptica (el historial administrativo aparte), que ya tiene su propia facturación FEL funcionando.

## Flujo de uso

1. El personal de Óptica cobra una venta normalmente.
2. En la pantalla de "Venta Exitosa", además del total y el botón "Imprimir" (ahora funcional), aparece el control de Facturación Electrónica para certificarla al momento.
3. Si no se factura de inmediato, puede hacerlo después: abre "Ver Ventas del Día", toca la venta en la lista, y desde su detalle certifica, consulta o anula la factura igual que en el paso anterior.
4. En cualquiera de las dos pantallas puede volver a imprimir el ticket cuando lo necesite.

## UI/UX feel

Mismo lenguaje visual y componentes que el Punto de Venta de la Clínica usa hoy para esto (mismo control de Facturación Electrónica, mismos estados y colores). El nuevo detalle de "Ver Ventas del Día" sigue el estilo general ya establecido en el Punto de Venta de Óptica (fondo oscuro, acentos teal), sin introducir un estilo nuevo.

## Fases de implementación

**Fase 1 (ahora — MVP):**
- Control de Facturación Electrónica en la pantalla de "Venta Exitosa" del Punto de Venta de Óptica.
- Detalle de venta (nuevo) dentro de "Ver Ventas del Día", con el mismo control de Facturación Electrónica.
- Botón "Imprimir" funcional en ambas pantallas, con ticket adaptado a productos de Óptica.

**Fase 2 (futuro):**
- Indicador visual de estado de factura (facturada / pendiente) directamente en cada fila de "Ver Ventas del Día", sin necesidad de abrir el detalle.

**Fase 3 (futuro):**
- Activación en producción ante SAT/Digifact (hoy pausada igual que para la Clínica, pendiente de certificación real); hasta entonces todo opera en modo de prueba con las mismas credenciales ya usadas.

## Supuestos

- Se usa la misma configuración global de FEL (NIT, establecimiento, credenciales de prueba de Digifact) ya configurada para la Clínica; no se crea una configuración ni credenciales separadas para Óptica.
- El alcance de esta mejora es solo el Punto de Venta de Óptica; el módulo de "Ventas" de Óptica (gestión/historial administrativo) no cambia porque ya tiene su propia facturación FEL funcionando de forma independiente.
- La lista de "Ver Ventas del Día" en sí (lo que se ve sin abrir el detalle) no muestra el estado de la factura; eso queda para la Fase 2.
- El formato del ticket impreso en Óptica sigue el mismo estilo que el de la Clínica (encabezado de la empresa, productos, totales, forma de pago, mensaje de agradecimiento), ajustado a los productos propios de Óptica.
