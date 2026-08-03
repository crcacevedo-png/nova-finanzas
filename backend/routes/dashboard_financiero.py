# /app/backend/routes/dashboard.py
# Módulo de Dashboard Financiero - Solo SuperAdmin

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from calendar import monthrange
from pydantic import BaseModel
from io import BytesIO

from config.database import db
from routes.auth import require_role

router = APIRouter(prefix="/dashboard", tags=["Dashboard Financiero"])


class DashboardFinancieroResponse(BaseModel):
    """Respuesta del dashboard financiero"""
    periodo: dict
    ingresos: dict
    gastos: dict
    balance: dict
    cuentas_por_cobrar: dict
    ingresos_por_pagador: List[dict]
    gastos_por_categoria: List[dict]
    evolucion_mensual: List[dict]


@router.get("/financiero")
async def get_dashboard_financiero(
    periodo: str = Query("mes_actual", description="mes_actual, semestre, anual, personalizado"),
    fecha_inicio: Optional[str] = Query(None, description="YYYY-MM-DD para período personalizado"),
    fecha_fin: Optional[str] = Query(None, description="YYYY-MM-DD para período personalizado"),
    current_user: dict = Depends(require_role("superadmin"))
):
    """
    Dashboard Financiero exclusivo para SuperAdmin
    Muestra ingresos de Caja y gastos de la empresa
    """
    from datetime import date
    
    now = datetime.now(timezone.utc)
    
    # Calcular fechas según período seleccionado
    if periodo == "mes_actual":
        fecha_inicio_dt = date(now.year, now.month, 1)
        fecha_fin_dt = date(now.year, now.month, now.day)
        periodo_nombre = f"Mes actual ({now.strftime('%B %Y')})"
    elif periodo == "semestre":
        mes_inicio = now.month - 5 if now.month > 5 else now.month + 7
        anio_inicio = now.year if now.month > 5 else now.year - 1
        fecha_inicio_dt = date(anio_inicio, mes_inicio, 1)
        fecha_fin_dt = date(now.year, now.month, now.day)
        periodo_nombre = "Últimos 6 meses"
    elif periodo == "anual":
        fecha_inicio_dt = date(now.year, 1, 1)
        fecha_fin_dt = date(now.year, now.month, now.day)
        periodo_nombre = f"Año {now.year}"
    elif periodo == "personalizado" and fecha_inicio and fecha_fin:
        fecha_inicio_dt = date.fromisoformat(fecha_inicio)
        fecha_fin_dt = date.fromisoformat(fecha_fin)
        periodo_nombre = f"Del {fecha_inicio} al {fecha_fin}"
    else:
        fecha_inicio_dt = date(now.year, now.month, 1)
        fecha_fin_dt = date(now.year, now.month, now.day)
        periodo_nombre = f"Mes actual ({now.strftime('%B %Y')})"
    
    fecha_inicio_str = fecha_inicio_dt.isoformat()
    fecha_fin_str = fecha_fin_dt.isoformat()
    
    # ========== INGRESOS DE CAJA (solo clínica) ==========
    ingresos_query = {
        "origen": "clinica",
        "tipo": "Ingreso",
        "fecha": {"$gte": fecha_inicio_str + "T00:00:00", "$lte": fecha_fin_str + "T23:59:59"}
    }
    movimientos_ingreso = await db.caja_movimientos.find(ingresos_query, {"_id": 0}).to_list(10000)
    
    total_ingresos = sum(m.get("monto", 0) for m in movimientos_ingreso)
    ingresos_por_metodo = {"efectivo": 0, "tarjeta": 0, "transferencia": 0, "cheque": 0}
    for m in movimientos_ingreso:
        metodo = m.get("metodo_pago", "Efectivo").lower()
        if metodo in ingresos_por_metodo:
            ingresos_por_metodo[metodo] += m.get("monto", 0)
    
    # Ingresos por tipo de pagador
    ingresos_por_pagador = {}
    for m in movimientos_ingreso:
        tipo = m.get("categoria", "Otro")
        ingresos_por_pagador[tipo] = ingresos_por_pagador.get(tipo, 0) + m.get("monto", 0)
    
    # Abonos de CxC como ingresos
    cxc_con_abonos = await db.cuentas_por_cobrar.find({
        "origen": "clinica",
        "abonos": {"$exists": True, "$ne": []}
    }, {"_id": 0, "tipo_pagador": 1, "abonos": 1}).to_list(10000)
    
    ingresos_cxc_periodo = 0
    for cxc in cxc_con_abonos:
        tipo = cxc.get("tipo_pagador", "Otro")
        for abono in cxc.get("abonos", []):
            fecha_abono = abono.get("fecha", "")[:10]
            if fecha_inicio_str <= fecha_abono <= fecha_fin_str:
                monto_abono = abono.get("monto", 0)
                ingresos_cxc_periodo += monto_abono
                ingresos_por_pagador[tipo] = ingresos_por_pagador.get(tipo, 0) + monto_abono
    
    total_ingresos_cobrado = total_ingresos + ingresos_cxc_periodo
    
    ingresos_por_pagador_list = [
        {"tipo": k, "monto": round(v, 2)} 
        for k, v in sorted(ingresos_por_pagador.items(), key=lambda x: -x[1])
    ]
    
    # ========== GASTOS DE LA EMPRESA ==========
    gastos_query = {"date": {"$gte": fecha_inicio_str, "$lte": fecha_fin_str}}
    gastos = await db.expenses.find(gastos_query, {"_id": 0}).to_list(10000)
    
    total_gastos = sum(g.get("amount", 0) for g in gastos)
    gastos_pagados = sum(g.get("paid_amount", 0) for g in gastos)
    gastos_pendientes = sum(g.get("remaining_amount", 0) for g in gastos)
    
    gastos_por_tipo = {}
    gastos_por_estado = {"pendiente": 0, "parcial": 0, "pagado": 0, "vencido": 0}
    for g in gastos:
        tipo = g.get("type", "variable")
        gastos_por_tipo[tipo] = gastos_por_tipo.get(tipo, 0) + g.get("amount", 0)
        estado = g.get("status", "pendiente")
        if estado in gastos_por_estado:
            gastos_por_estado[estado] += g.get("amount", 0)
    
    gastos_por_categoria_list = [
        {"categoria": k, "monto": round(v, 2)}
        for k, v in sorted(gastos_por_tipo.items(), key=lambda x: -x[1])
    ]
    
    # ========== CUENTAS POR COBRAR PENDIENTES ==========
    cxc_pendientes = await db.cuentas_por_cobrar.find({
        "origen": "clinica",
        "saldo_pendiente": {"$gt": 0}
    }, {"_id": 0, "saldo_pendiente": 1, "tipo_pagador": 1}).to_list(10000)
    
    total_cxc_pendiente = sum(c.get("saldo_pendiente", 0) for c in cxc_pendientes)
    cxc_por_tipo = {}
    for c in cxc_pendientes:
        tipo = c.get("tipo_pagador", "Otro")
        cxc_por_tipo[tipo] = cxc_por_tipo.get(tipo, 0) + c.get("saldo_pendiente", 0)
    
    # ========== BALANCE ==========
    balance_neto = total_ingresos_cobrado - gastos_pagados
    
    # ========== EVOLUCIÓN MENSUAL (últimos 12 meses) ==========
    # Usar cálculo explícito de (año, mes) para evitar problemas con meses de diferentes longitudes
    evolucion = []
    current_year = now.year
    current_month = now.month
    
    for i in range(11, -1, -1):
        # Calcular el mes correcto restando i meses
        target_month = current_month - i
        target_year = current_year
        
        # Ajustar año si el mes es <= 0
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        mes_inicio = date(target_year, target_month, 1)
        ultimo_dia = monthrange(target_year, target_month)[1]
        
        # Para el mes actual, usar el día de hoy; para meses anteriores, usar el último día
        if i == 0:
            mes_fin = date(current_year, current_month, now.day)
        else:
            mes_fin = date(target_year, target_month, ultimo_dia)
        
        # Ingresos del mes
        ingresos_mes = await db.caja_movimientos.aggregate([
            {"$match": {
                "origen": "clinica",
                "tipo": "Ingreso",
                "fecha": {"$gte": mes_inicio.isoformat() + "T00:00:00", "$lte": mes_fin.isoformat() + "T23:59:59"}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$monto"}}}
        ]).to_list(1)
        total_ing_mes = ingresos_mes[0]["total"] if ingresos_mes else 0
        
        # Gastos del mes
        gastos_mes = await db.expenses.aggregate([
            {"$match": {"date": {"$gte": mes_inicio.isoformat(), "$lte": mes_fin.isoformat()}}},
            {"$group": {"_id": None, "total": {"$sum": "$paid_amount"}}}
        ]).to_list(1)
        total_gasto_mes = gastos_mes[0]["total"] if gastos_mes else 0
        
        evolucion.append({
            "mes": mes_inicio.strftime("%Y-%m"),
            "mes_nombre": mes_inicio.strftime("%b %Y"),
            "ingresos": round(total_ing_mes, 2),
            "gastos": round(total_gasto_mes, 2),
            "balance": round(total_ing_mes - total_gasto_mes, 2)
        })
    
    return {
        "periodo": {"nombre": periodo_nombre, "fecha_inicio": fecha_inicio_str, "fecha_fin": fecha_fin_str},
        "ingresos": {
            "total_cobrado": round(total_ingresos_cobrado, 2),
            "efectivo": round(ingresos_por_metodo["efectivo"], 2),
            "tarjeta": round(ingresos_por_metodo["tarjeta"], 2),
            "transferencia": round(ingresos_por_metodo["transferencia"], 2),
            "cheque": round(ingresos_por_metodo["cheque"], 2),
            "de_caja_directa": round(total_ingresos, 2),
            "de_abonos_cxc": round(ingresos_cxc_periodo, 2)
        },
        "gastos": {
            "total": round(total_gastos, 2),
            "pagado": round(gastos_pagados, 2),
            "pendiente": round(gastos_pendientes, 2),
            "por_estado": gastos_por_estado
        },
        "balance": {"neto": round(balance_neto, 2), "positivo": balance_neto >= 0},
        "cuentas_por_cobrar": {"total_pendiente": round(total_cxc_pendiente, 2), "por_tipo": cxc_por_tipo},
        "ingresos_por_pagador": ingresos_por_pagador_list,
        "gastos_por_categoria": gastos_por_categoria_list,
        "evolucion_mensual": evolucion
    }


@router.get("/financiero/exportar")
async def exportar_dashboard_financiero(
    formato: str = Query("excel", description="excel o pdf"),
    periodo: str = Query("mes_actual"),
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    current_user: dict = Depends(require_role("superadmin"))
):
    """Exportar reporte financiero a Excel o PDF"""
    datos = await get_dashboard_financiero(periodo, fecha_inicio, fecha_fin, current_user)
    
    if formato == "excel":
        from openpyxl import Workbook
        from openpyxl.styles import Font
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte Financiero"
        
        currency_format = '"Q"#,##0.00'
        row = 1
        
        ws.cell(row=row, column=1, value="REPORTE FINANCIERO - NOVAVISION").font = Font(bold=True, size=16)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 1
        ws.cell(row=row, column=1, value=f"Período: {datos['periodo']['nombre']}")
        row += 2
        
        ws.cell(row=row, column=1, value="RESUMEN").font = Font(bold=True)
        row += 1
        for label, value in [
            ("Total Ingresos Cobrados", datos['ingresos']['total_cobrado']),
            ("Total Gastos Pagados", datos['gastos']['pagado']),
            ("Balance Neto", datos['balance']['neto']),
            ("CxC Pendientes", datos['cuentas_por_cobrar']['total_pendiente'])
        ]:
            ws.cell(row=row, column=1, value=label)
            ws.cell(row=row, column=2, value=value).number_format = currency_format
            row += 1
        row += 1
        
        ws.cell(row=row, column=1, value="INGRESOS POR PAGADOR").font = Font(bold=True)
        row += 1
        for item in datos['ingresos_por_pagador']:
            ws.cell(row=row, column=1, value=item['tipo'])
            ws.cell(row=row, column=2, value=item['monto']).number_format = currency_format
            row += 1
        row += 1
        
        ws.cell(row=row, column=1, value="GASTOS POR CATEGORÍA").font = Font(bold=True)
        row += 1
        for item in datos['gastos_por_categoria']:
            ws.cell(row=row, column=1, value=item['categoria'])
            ws.cell(row=row, column=2, value=item['monto']).number_format = currency_format
            row += 1
        row += 1
        
        ws.cell(row=row, column=1, value="EVOLUCIÓN MENSUAL").font = Font(bold=True)
        row += 1
        for header in ["Mes", "Ingresos", "Gastos", "Balance"]:
            ws.cell(row=row, column=["Mes", "Ingresos", "Gastos", "Balance"].index(header) + 1, value=header)
        row += 1
        for item in datos['evolucion_mensual']:
            ws.cell(row=row, column=1, value=item['mes_nombre'])
            ws.cell(row=row, column=2, value=item['ingresos']).number_format = currency_format
            ws.cell(row=row, column=3, value=item['gastos']).number_format = currency_format
            ws.cell(row=row, column=4, value=item['balance']).number_format = currency_format
            row += 1
        
        ws.column_dimensions['A'].width = 35
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 18
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=reporte_financiero_{datos['periodo']['fecha_inicio']}_{datos['periodo']['fecha_fin']}.xlsx"}
        )
    
    elif formato == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter, topMargin=50, bottomMargin=50)
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=1, spaceAfter=20)
        elements.append(Paragraph("REPORTE FINANCIERO - NOVAVISION", title_style))
        elements.append(Paragraph(f"Período: {datos['periodo']['nombre']}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        resumen_data = [
            ["Concepto", "Monto (GTQ)"],
            ["Total Ingresos Cobrados", f"Q {datos['ingresos']['total_cobrado']:,.2f}"],
            ["Total Gastos Pagados", f"Q {datos['gastos']['pagado']:,.2f}"],
            ["Balance Neto", f"Q {datos['balance']['neto']:,.2f}"],
            ["CxC Pendientes", f"Q {datos['cuentas_por_cobrar']['total_pendiente']:,.2f}"]
        ]
        
        resumen_table = Table(resumen_data, colWidths=[250, 150])
        resumen_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D7377')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(resumen_table)
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("Evolución Mensual", styles['Heading2']))
        evol_data = [["Mes", "Ingresos", "Gastos", "Balance"]]
        for item in datos['evolucion_mensual'][-6:]:
            evol_data.append([item['mes_nombre'], f"Q {item['ingresos']:,.2f}", f"Q {item['gastos']:,.2f}", f"Q {item['balance']:,.2f}"])
        
        evol_table = Table(evol_data, colWidths=[100, 120, 120, 120])
        evol_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D7377')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(evol_table)
        
        doc.build(elements)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=reporte_financiero_{datos['periodo']['fecha_inicio']}_{datos['periodo']['fecha_fin']}.pdf"}
        )
    
    raise HTTPException(status_code=400, detail="Formato no soportado. Use 'excel' o 'pdf'")
