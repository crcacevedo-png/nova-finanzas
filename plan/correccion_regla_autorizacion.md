# Corrección: regla "una consulta facturable por autorización" (Fase 1)

## Estado actual (probado)
Funciona: 2 autorizaciones mismo NOG = 2 cupos; seguimientos con el mismo No. SPS no descuentan;
sin No. SPS = 1 cupo por paciente/NOG; aviso 90 % y bloqueo 100 % intactos; históricos sin tocar.
Pruebas: 13 de 16 pasan. Fallan 3, por los puntos 1, 2 y 3 de abajo.

## Correcciones (todas en backend/routes/igss_nogs.py)
1. **Producción por día/mes (ALTO).** Hoy, un seguimiento en otro día o mes vuelve a salir como fila nueva.
   - Se agrupa con todo el historial de los pacientes del rango.
   - La autorización solo aparece si su PRIMERA consulta cae dentro del filtro.
   - Los seguimientos nunca generan fila.
2. **Editar paciente libera cupo (ALTO).** Hoy, cambiar el teléfono anula el descuento que hizo una consulta con un No. SPS nuevo.
   - Los descuentos de origen "evaluación" se conservan, igual que los manuales.
3. **Mismo No. SPS en dos NOG distintos se fusiona.** La clave de agrupación incluye el número de NOG.
4. **Acreditación retroactiva (crear NOG / recalcular).** Hoy crea un descuento sin No. SPS, que bloquea las autorizaciones siguientes.
   - Pasa a crear un descuento por cada autorización de las órdenes del paciente.
5. **Lista de pacientes del NOG y su Excel.** Muestran el No. SPS propio de cada descuento, no el de la primera orden.
6. **Descuento manual.** Acepta un No. SPS opcional para poder aplicar una segunda autorización.
7. **Registro de fallos.** El hook de evaluación registra los fallos en el log en vez de ignorarlos.

## Pendiente de decisión
- ¿Una consulta cuya autorización NO pudo descontar cupo (NOG al 100 %) debe salir en Producción?

## Verificación
- Re-ejecutar tests/test_nog_por_autorizacion.py: los 16 deben pasar.
- Más casos: filtro por día del seguimiento sin fila, PUT con teléfono sin liberar cupo, y retroactivo con 2 No. SPS = 2 cupos.
