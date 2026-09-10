# Plan: Mejoras al Expediente Clínico

## 1. Eliminar límite de 24 horas para guardar expediente
- Remover la validación que bloquea guardar/editar el expediente clínico después de 24 horas de creado
- Los usuarios podrán modificar expedientes sin restricción temporal

## 2. Múltiples recetas de anteojos y lentes de contacto
- Permitir agregar más de una receta de anteojos por expediente
- Permitir agregar más de una receta de lentes de contacto por expediente
- Cada receta tendrá su propio botón de impresión individual
- Las recetas se mostrarán en una lista expandible/colapsable

## 3. Campo ADD en receta de lentes de contacto
- Agregar campo "ADD" (Adición) después del campo "CB" (Curva Base) en el formulario de lentes de contacto
- El campo aplica para ambos ojos (OD y OS)

## 4. Diagnóstico y lectura de exámenes en historial
- En la vista de historial de expedientes clínicos, al expandir una historia pasada, mostrar:
  - Diagnóstico principal
  - Lectura/resultados de exámenes realizados
  - Además del nombre del paciente que ya se muestra

---

## Supuestos
- Las recetas múltiples se almacenarán como arrays en el documento del expediente
- El campo ADD en lentes de contacto es numérico (similar a la adición en anteojos)
- El historial mostrará un resumen del diagnóstico (no el texto completo si es muy largo)
