#!/usr/bin/env python3
"""
Genera plantilla Excel para importación masiva de Pacientes - NovaVision
Incluye campo NOG para IGSS
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

def crear_plantilla_pacientes():
    wb = Workbook()
    
    # ==================== HOJA 1: PLANTILLA DE DATOS ====================
    ws_datos = wb.active
    ws_datos.title = "Datos_Pacientes"
    
    # Definir columnas con sus descripciones
    columnas = [
        # Datos básicos
        ("expediente", "Número de expediente (opcional, se genera automático)", "EXP-202408-0001", "Opcional"),
        ("nombres", "Nombre(s) del paciente", "María José", "Obligatorio"),
        ("apellidos", "Apellido(s) del paciente", "García López", "Obligatorio"),
        ("sexo", "Género: masculino, femenino", "femenino", "Obligatorio"),
        ("fecha_nacimiento", "Fecha de nacimiento DD/MM/YYYY", "15/03/1985", "Obligatorio"),
        ("dpi", "DPI/CUI (13 dígitos)", "1234567890123", "Opcional"),
        ("telefono", "Teléfono principal", "5555-1234", "Obligatorio"),
        ("email", "Correo electrónico", "maria@email.com", "Opcional"),
        ("profesion", "Profesión u ocupación", "Maestra", "Opcional"),
        ("direccion", "Dirección completa", "4ta calle 5-20 zona 1", "Opcional"),
        ("estado_civil", "Estado civil", "Casado(a)", "Opcional"),
        
        # Contacto de emergencia
        ("emergencia_nombre", "Nombre contacto emergencia", "Juan García", "Opcional"),
        ("emergencia_parentesco", "Parentesco", "Esposo", "Opcional"),
        ("emergencia_telefono", "Teléfono emergencia", "5555-5678", "Opcional"),
        
        # Institución
        ("institucion", "Institución: particular, igss, seguro_privado, otra", "igss", "Obligatorio"),
        ("nombre_seguro", "Nombre del seguro (si es seguro_privado)", "Seguros G&T", "Condicional"),
        ("otra_institucion", "Nombre institución (si es otra)", "Hospital Roosevelt", "Condicional"),
        
        # Campos IGSS (solo si institucion = igss)
        ("igss_unidad", "Nombre de unidad IGSS", "Periférica Zona 11", "Condicional"),
        ("igss_afiliacion", "Número de afiliación IGSS", "12345678", "Condicional"),
        ("igss_no_sps", "Número SPS", "SPS-001234", "Condicional"),
        ("igss_codigo", "Código IGSS", "COD-5678", "Condicional"),
        ("igss_nog", "NOG - Número de Orden de Gestión", "NOG-2024-001234", "Condicional"),
        ("igss_tipo_compra", "Tipo de compra: evento, contrato, convenio, ges", "evento", "Condicional"),
        
        # Observaciones
        ("observaciones", "Comentarios adicionales", "Paciente referido por Dr. Pérez", "Opcional"),
    ]
    
    # Estilos
    header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    obligatorio_fill = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
    opcional_fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
    condicional_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
    igss_fill = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Escribir encabezados
    for col_idx, (nombre, descripcion, ejemplo, requerido) in enumerate(columnas, 1):
        cell = ws_datos.cell(row=1, column=col_idx, value=nombre)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border
        
        # Ajustar ancho de columna
        ws_datos.column_dimensions[get_column_letter(col_idx)].width = max(18, len(nombre) + 4)
    
    # Fila de descripciones
    for col_idx, (nombre, descripcion, ejemplo, requerido) in enumerate(columnas, 1):
        cell = ws_datos.cell(row=2, column=col_idx, value=descripcion)
        if requerido == "Obligatorio":
            cell.fill = obligatorio_fill
        elif requerido == "Condicional":
            if "igss" in nombre:
                cell.fill = igss_fill
            else:
                cell.fill = condicional_fill
        else:
            cell.fill = opcional_fill
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.border = thin_border
        cell.font = Font(size=9)
    
    # Fila de ejemplos
    for col_idx, (nombre, descripcion, ejemplo, requerido) in enumerate(columnas, 1):
        cell = ws_datos.cell(row=3, column=col_idx, value=ejemplo)
        cell.font = Font(italic=True, color="666666", size=10)
        cell.border = thin_border
    
    # Filas vacías para datos (500 filas para importación masiva)
    for row in range(4, 504):
        for col_idx in range(1, len(columnas) + 1):
            cell = ws_datos.cell(row=row, column=col_idx, value="")
            cell.border = thin_border
    
    # Validaciones de datos
    # Género
    dv_sexo = DataValidation(type="list", formula1='"masculino,femenino"', allow_blank=True)
    dv_sexo.error = 'Valor no válido'
    dv_sexo.errorTitle = 'Error de género'
    dv_sexo.prompt = 'Seleccione el género'
    dv_sexo.promptTitle = 'Género'
    ws_datos.add_data_validation(dv_sexo)
    dv_sexo.add('D4:D503')
    
    # Institución
    dv_inst = DataValidation(type="list", formula1='"particular,igss,seguro_privado,otra"', allow_blank=True)
    dv_inst.error = 'Valor no válido'
    dv_inst.errorTitle = 'Error de institución'
    ws_datos.add_data_validation(dv_inst)
    dv_inst.add('O4:O503')
    
    # Tipo de compra IGSS
    dv_compra = DataValidation(type="list", formula1='"evento,contrato,convenio,ges"', allow_blank=True)
    ws_datos.add_data_validation(dv_compra)
    dv_compra.add('X4:X503')
    
    # Congelar filas superiores
    ws_datos.freeze_panes = "A4"
    
    # ==================== HOJA 2: DICCIONARIO DE DATOS ====================
    ws_dict = wb.create_sheet("Diccionario")
    
    dict_headers = ["Campo", "Descripción", "Ejemplo", "Requerido", "Valores Válidos"]
    for col_idx, header in enumerate(dict_headers, 1):
        cell = ws_dict.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = thin_border
    
    valores_validos = {
        "sexo": "masculino, femenino",
        "institucion": "particular, igss, seguro_privado, otra",
        "igss_tipo_compra": "evento, contrato, convenio, ges",
        "fecha_nacimiento": "DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY",
        "dpi": "13 dígitos numéricos",
        "estado_civil": "Soltero(a), Casado(a), Divorciado(a), Viudo(a), Unido(a)",
    }
    
    for row_idx, (nombre, descripcion, ejemplo, requerido) in enumerate(columnas, 2):
        ws_dict.cell(row=row_idx, column=1, value=nombre).border = thin_border
        ws_dict.cell(row=row_idx, column=2, value=descripcion).border = thin_border
        ws_dict.cell(row=row_idx, column=3, value=ejemplo).border = thin_border
        ws_dict.cell(row=row_idx, column=4, value=requerido).border = thin_border
        ws_dict.cell(row=row_idx, column=5, value=valores_validos.get(nombre, "Texto libre")).border = thin_border
        
        # Color según tipo
        fill = opcional_fill
        if requerido == "Obligatorio":
            fill = obligatorio_fill
        elif requerido == "Condicional":
            fill = igss_fill if "igss" in nombre else condicional_fill
            
        for col in range(1, 6):
            ws_dict.cell(row=row_idx, column=col).fill = fill
    
    # Ajustar anchos
    ws_dict.column_dimensions['A'].width = 20
    ws_dict.column_dimensions['B'].width = 45
    ws_dict.column_dimensions['C'].width = 25
    ws_dict.column_dimensions['D'].width = 12
    ws_dict.column_dimensions['E'].width = 45
    
    # ==================== HOJA 3: EJEMPLO IGSS ====================
    ws_igss = wb.create_sheet("Ejemplo_IGSS")
    
    ejemplo_igss = [
        ["Campo", "Valor Ejemplo", "Notas"],
        ["expediente", "", "Dejar vacío para generar automático"],
        ["nombres", "Juan Carlos", ""],
        ["apellidos", "Pérez Morales", ""],
        ["sexo", "masculino", ""],
        ["fecha_nacimiento", "22/07/1975", "Formato DD/MM/YYYY"],
        ["dpi", "1234567890101", "13 dígitos"],
        ["telefono", "5555-1234", ""],
        ["email", "juan.perez@gmail.com", ""],
        ["profesion", "Contador", ""],
        ["direccion", "12 calle 3-45 zona 7, Guatemala", ""],
        ["estado_civil", "Casado", ""],
        ["emergencia_nombre", "María de Pérez", ""],
        ["emergencia_parentesco", "Esposa", ""],
        ["emergencia_telefono", "5555-5678", ""],
        ["institucion", "igss", "IMPORTANTE: debe ser 'igss' en minúsculas"],
        ["nombre_seguro", "", "Dejar vacío si es IGSS"],
        ["otra_institucion", "", "Dejar vacío si es IGSS"],
        ["igss_unidad", "Periférica Zona 11", "Nombre de la unidad IGSS"],
        ["igss_afiliacion", "12345678", "Número de afiliación del trabajador"],
        ["igss_no_sps", "SPS-001234", "Número SPS asignado"],
        ["igss_codigo", "COD-5678", "Código interno"],
        ["igss_nog", "NOG-2024-001234", "Número de Orden de Gestión"],
        ["igss_tipo_compra", "evento", "evento, contrato, convenio o ges"],
        ["observaciones", "Paciente diabético tipo 2", "Cualquier nota relevante"],
    ]
    
    for row_idx, row_data in enumerate(ejemplo_igss, 1):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws_igss.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            if row_idx == 1:
                cell.fill = header_fill
                cell.font = header_font
            elif "igss" in str(row_data[0]):
                cell.fill = igss_fill
    
    ws_igss.column_dimensions['A'].width = 22
    ws_igss.column_dimensions['B'].width = 30
    ws_igss.column_dimensions['C'].width = 45
    
    # ==================== HOJA 4: INSTRUCCIONES ====================
    ws_inst = wb.create_sheet("Instrucciones")
    
    instrucciones = [
        "═══════════════════════════════════════════════════════════════════",
        "    INSTRUCCIONES PARA IMPORTACIÓN MASIVA DE PACIENTES - NOVAVISION",
        "═══════════════════════════════════════════════════════════════════",
        "",
        "LEYENDA DE COLORES:",
        "  🔴 ROJO CLARO = Campo OBLIGATORIO (debe tener valor)",
        "  🔵 AZUL CLARO = Campo OPCIONAL (puede dejarse vacío)",
        "  🟡 AMARILLO = Campo CONDICIONAL (requerido según institución)",
        "  🟢 VERDE = Campo específico de IGSS (solo si institución = igss)",
        "",
        "═══════════════════════════════════════════════════════════════════",
        "1. CAMPOS OBLIGATORIOS (mínimos para cada paciente):",
        "═══════════════════════════════════════════════════════════════════",
        "   • nombres        → Nombre(s) del paciente",
        "   • apellidos      → Apellido(s) del paciente", 
        "   • sexo           → 'masculino' o 'femenino'",
        "   • fecha_nacimiento → Formato: DD/MM/YYYY, YYYY-MM-DD, o DD-MM-YYYY",
        "   • telefono       → Teléfono de contacto",
        "   • institucion    → 'particular', 'igss', 'seguro_privado', o 'otra'",
        "",
        "═══════════════════════════════════════════════════════════════════",
        "2. CAMPOS ESPECÍFICOS PARA IGSS:",
        "═══════════════════════════════════════════════════════════════════",
        "   Si la columna 'institucion' = 'igss', debe llenar:",
        "",
        "   • igss_unidad      → Nombre de la unidad IGSS (ej: Periférica Zona 11)",
        "   • igss_afiliacion  → Número de afiliación del trabajador",
        "   • igss_no_sps      → Número SPS asignado",
        "   • igss_codigo      → Código interno IGSS",
        "   • igss_nog         → NOG (Número de Orden de Gestión) ← NUEVO CAMPO",
        "   • igss_tipo_compra → 'evento', 'contrato', 'convenio', o 'ges'",
        "",
        "═══════════════════════════════════════════════════════════════════",
        "3. FORMATO DE FECHAS:",
        "═══════════════════════════════════════════════════════════════════",
        "   El sistema acepta estos formatos:",
        "   • DD/MM/YYYY  → 15/03/1985 (formato guatemalteco - RECOMENDADO)",
        "   • YYYY-MM-DD  → 1985-03-15 (formato ISO)",
        "   • DD-MM-YYYY  → 15-03-1985",
        "",
        "═══════════════════════════════════════════════════════════════════",
        "4. FORMATO DEL DPI:",
        "═══════════════════════════════════════════════════════════════════",
        "   • Debe tener exactamente 13 dígitos",
        "   • Solo números, sin espacios ni guiones",
        "   • Ejemplo: 1234567890123",
        "",
        "═══════════════════════════════════════════════════════════════════",
        "5. PASOS PARA IMPORTAR:",
        "═══════════════════════════════════════════════════════════════════",
        "   1. Complete los datos en la hoja 'Datos_Pacientes'",
        "   2. Guarde el archivo Excel",
        "   3. Vaya a NovaVision → Importar Pacientes",
        "   4. Convierta este Excel a JSON (puede usar herramientas online)",
        "      O exporte como CSV y luego convierta a JSON",
        "   5. Suba el archivo JSON en el sistema",
        "   6. Valide los datos antes de importar",
        "   7. Ejecute la importación",
        "",
        "═══════════════════════════════════════════════════════════════════",
        "6. RECOMENDACIONES PARA GRANDES VOLÚMENES (16,000+ registros):",
        "═══════════════════════════════════════════════════════════════════",
        "   • Divida en archivos de máximo 5,000-8,000 registros",
        "   • Ejecute importaciones fuera del horario pico",
        "   • Use 'Omitir duplicados' en la configuración",
        "   • Valide siempre antes de importar",
        "",
        "═══════════════════════════════════════════════════════════════════",
        "7. DETECCIÓN DE DUPLICADOS:",
        "═══════════════════════════════════════════════════════════════════",
        "   El sistema detecta duplicados por:",
        "   1. DPI (si está presente) - Prioridad alta",
        "   2. Nombre completo exacto - Prioridad media",
        "",
        "═══════════════════════════════════════════════════════════════════",
        "SOPORTE: Contacte al administrador del sistema para ayuda",
        "═══════════════════════════════════════════════════════════════════",
    ]
    
    for row_idx, linea in enumerate(instrucciones, 1):
        cell = ws_inst.cell(row=row_idx, column=1, value=linea)
        if "═" in linea or linea.strip().endswith(":"):
            cell.font = Font(bold=True, size=11)
        elif linea.startswith("   •"):
            cell.font = Font(size=10)
    
    ws_inst.column_dimensions['A'].width = 75
    
    # Guardar archivo
    output_path = "/app/plantilla_importacion_pacientes.xlsx"
    wb.save(output_path)
    print(f"✅ Plantilla generada: {output_path}")
    return output_path

if __name__ == "__main__":
    crear_plantilla_pacientes()
