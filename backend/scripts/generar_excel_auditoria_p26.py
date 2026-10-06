#!/usr/bin/env python3
"""Genera el Excel del informe de hallazgos P26 a partir del markdown (reutiliza openpyxl, ya en requirements.txt)."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

HALLAZGOS = [
    ("H-01", "K / J", "—", "CRITICO", "GET /api/cxc responde 500 (ResponseValidationError) por paciente_id/tipo_pagador_id nulos. Ya rompe el modulo de CxC Clinica con 5 registros reales existentes. El abono tambien crashea despues de guardarse en Mongo (riesgo de abono duplicado por reintento).", "Oculta todo el modulo de CxC; riesgo de abonos duplicados"),
    ("H-02", "G", "INV-33", "CRITICO", "recalcular_costo_promedio se ejecuta despues de actualizar_existencia -> cuenta la cantidad comprada 2 veces. Probado: 10@Q100+10@Q120 = Q73.33 en vez de Q110.00.", "Subvalua inventario y costo de ventas en TODO producto con 2+ entradas historicas"),
    ("H-03", "J", "INV-38", "CRITICO", "Abono de Q200 a CxC con registrar_en_caja=true incrementa ingresos del dashboard en Q400 (doble conteo: caja_movimientos + cuentas_por_cobrar.abonos).", "Duplica el ingreso reportado por cada abono de CxC"),
    ("H-04", "L", "INV-40/41", "CRITICO", "calcular_cierre_financiero = ingresos_caja - egresos_caja de caja_movimientos, SIN costo de ventas. Probado: Q1120 vendidos (costo real Q550) -> resultado_neto=872 en vez de utilidad operativa real.", "Resultado neto oficial sobrestimado en 100% del costo de ventas"),
    ("H-05", "K", "INV-40", "CRITICO", "Gasto autorizado y pagado (Q150) via payment_authorizations NO aparece en egresos_caja (quedo en 0.00). El pago nunca crea un caja_movimientos tipo Egreso.", "El cierre ignora el 100% de gastos pagados por el flujo correcto"),
    ("H-06", "K", "INV-43", "CRITICO", "POST /api/payments crea un pago sin verificar autorizacion previa (bypass del flujo payment_authorizations). Permiso register_payments lo tiene superadmin y admin.", "Permite pagar gastos sin autorizacion, anula el control de doble validacion"),
    ("H-07", "K", "—", "ALTO", "POST /caja/cierres/{id}/reabrir desbloquea un cierre diario sellado. cierres_financieros nunca pasa de 'Borrador' y admite PUT/recalcular/DELETE en cualquier momento.", "Cierres oficiales pueden alterarse despues de comunicados"),
    ("H-08", "I", "INV-47", "ALTO", "evaluaciones.py y surgeries.py no tienen campo de costo/honorario/receta. Todo servicio clinico entra con costo cero, sin marcarse 'sin costear'.", "Sobrestima utilidad de todo el negocio de servicios"),
    ("H-09", "L", "—", "ALTO", "reporte_rentabilidad_historico (clinica) consulta ventas_optica (coleccion equivocada) y cae a fallback que usa precio_venta/costo_promedio ACTUALES, no los vigentes al momento de cada venta historica.", "Reescribe retroactivamente la utilidad de meses pasados al cambiar el costo actual"),
    ("H-10", "H", "INV-36", "MEDIO", "POST /api/ventas no valida es_punto_venta=true en el bodega_id recibido; solo lo hace el helper de sugerencia del frontend.", "Riesgo de descontar de bodega que no es punto de venta via API directa"),
    ("H-11", "G", "—", "BAJO (positivo)", "crear_recepcion NO genera gasto (gasto_id siempre null). Confirmado correcto: compra = activo, no gasto.", "Ninguno - comportamiento correcto, no debe 'corregirse'"),
    ("H-12", "G", "—", "MEDIO", "No existe concepto de cuenta por pagar a proveedor. Compra al credito no genera ninguna obligacion registrada.", "Riesgo de omitir pagos a proveedor; sin antiguedad de CxP"),
]

wb = Workbook()
ws = wb.active
ws.title = "Hallazgos P26"

headers = ["ID", "Recorrido", "Invariante", "Severidad", "Evidencia", "Impacto financiero estimado"]
ws.append(headers)
for col in range(1, len(headers) + 1):
    cell = ws.cell(row=1, column=col)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="0D7377")
    cell.alignment = Alignment(wrap_text=True, vertical="center")

sev_colors = {"CRITICO": "F8696B", "ALTO": "FFC000", "MEDIO": "FFEB84", "BAJO (positivo)": "C6E0B4"}

for row_data in HALLAZGOS:
    ws.append(row_data)
    r = ws.max_row
    sev = row_data[3]
    if sev in sev_colors:
        ws.cell(row=r, column=4).fill = PatternFill("solid", fgColor=sev_colors[sev])
    for col in range(1, len(headers) + 1):
        ws.cell(row=r, column=col).alignment = Alignment(wrap_text=True, vertical="top")

widths = [8, 10, 10, 16, 70, 45]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w

ws2 = wb.create_sheet("Resumen Ejecutivo")
ws2.append(["Pregunta", "Respuesta"])
ws2.cell(row=1, column=1).font = Font(bold=True)
ws2.cell(row=1, column=2).font = Font(bold=True)
ws2.append(["¿La utilidad mostrada hoy es real?", "NO. Es flujo de caja (ingresos-egresos de caja), nunca resta costo de ventas."])
ws2.append(["Escenario de referencia - Costo promedio esperado", "Q110.00"])
ws2.append(["Escenario de referencia - Costo promedio mostrado por el sistema", "Q73.33 (bug H-02)"])
ws2.append(["Escenario de referencia - Utilidad operativa esperada", "Q300.00"])
ws2.append(["Escenario de referencia - 'Resultado neto' mostrado por el sistema", "Q872.00 (= solo caja cobrada, bug H-04/H-05)"])
ws2.column_dimensions["A"].width = 55
ws2.column_dimensions["B"].width = 70
for row in ws2.iter_rows():
    for cell in row:
        cell.alignment = Alignment(wrap_text=True, vertical="top")

wb.save("/app/docs/auditoria/P26_informe_hallazgos.xlsx")
print("Excel generado: /app/docs/auditoria/P26_informe_hallazgos.xlsx")
