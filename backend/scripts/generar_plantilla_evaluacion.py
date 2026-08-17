#!/usr/bin/env python3
"""
Genera plantilla Excel para importación de Evaluaciones Oftalmológicas
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import os

def crear_plantilla_evaluaciones():
    wb = Workbook()
    
    # ==================== HOJA 1: PLANTILLA DE DATOS ====================
    ws_datos = wb.active
    ws_datos.title = "Plantilla_Datos"
    
    # Definir columnas con sus descripciones
    columnas = [
        # Encabezado
        ("paciente_expediente", "Número de expediente del paciente", "EXP-202408-0001", "Obligatorio"),
        ("paciente_nombre", "Nombre completo del paciente", "Juan Pérez López", "Obligatorio"),
        ("paciente_edad", "Edad en años", "45", "Obligatorio"),
        ("paciente_sexo", "masculino o femenino", "masculino", "Obligatorio"),
        ("fecha", "Fecha de evaluación YYYY-MM-DD", "2024-08-15", "Obligatorio"),
        ("medico_nombre", "Nombre del médico", "Dr. García", "Obligatorio"),
        ("motivo_consulta", "Motivo principal de la consulta", "Visión borrosa", "Obligatorio"),
        ("padecimiento_actual", "Descripción detallada del padecimiento", "Paciente refiere...", "Opcional"),
        
        # Antecedentes
        ("ant_personales_patologicos", "Antecedentes personales patológicos", "Ninguno conocido", "Opcional"),
        ("ant_diabetes", "¿Tiene diabetes? SI o NO", "NO", "Opcional"),
        ("ant_hipertension", "¿Tiene hipertensión? SI o NO", "SI", "Opcional"),
        ("ant_cardiopatia", "¿Tiene cardiopatía? SI o NO", "NO", "Opcional"),
        ("ant_enfermedad_tiroidea", "¿Tiene enfermedad tiroidea? SI o NO", "NO", "Opcional"),
        ("ant_oftalmologicos", "Antecedentes oftalmológicos", "Usa lentes desde 2010", "Opcional"),
        ("ant_quirurgicos", "Antecedentes quirúrgicos", "Cirugía de catarata OD 2020", "Opcional"),
        ("ant_alergias", "Alergias conocidas", "Penicilina", "Opcional"),
        ("ant_familiares", "Antecedentes familiares", "Madre con glaucoma", "Opcional"),
        ("ant_habitos", "Hábitos (tabaco, alcohol, etc.)", "No fuma, no alcohol", "Opcional"),
        
        # Agudeza Visual
        ("avsc_od", "Agudeza visual sin corrección OD", "20/40", "Opcional"),
        ("avsc_os", "Agudeza visual sin corrección OS", "20/30", "Opcional"),
        ("avcc_od", "Agudeza visual con corrección OD", "20/20", "Opcional"),
        ("avcc_os", "Agudeza visual con corrección OS", "20/20", "Opcional"),
        
        # Lensometría (lentes actuales)
        ("lensometria_od_esfera", "Lensometría OD Esfera", "-2.00", "Opcional"),
        ("lensometria_od_cilindro", "Lensometría OD Cilindro", "-0.75", "Opcional"),
        ("lensometria_od_eje", "Lensometría OD Eje", "180", "Opcional"),
        ("lensometria_os_esfera", "Lensometría OS Esfera", "-1.75", "Opcional"),
        ("lensometria_os_cilindro", "Lensometría OS Cilindro", "-0.50", "Opcional"),
        ("lensometria_os_eje", "Lensometría OS Eje", "175", "Opcional"),
        
        # Refracción
        ("refraccion_od_esfera", "Refracción OD Esfera", "-2.25", "Opcional"),
        ("refraccion_od_cilindro", "Refracción OD Cilindro", "-0.75", "Opcional"),
        ("refraccion_od_eje", "Refracción OD Eje", "180", "Opcional"),
        ("refraccion_od_adicion", "Refracción OD Adición (presbicia)", "+2.00", "Opcional"),
        ("refraccion_os_esfera", "Refracción OS Esfera", "-2.00", "Opcional"),
        ("refraccion_os_cilindro", "Refracción OS Cilindro", "-0.50", "Opcional"),
        ("refraccion_os_eje", "Refracción OS Eje", "175", "Opcional"),
        ("refraccion_os_adicion", "Refracción OS Adición (presbicia)", "+2.00", "Opcional"),
        
        # Queratometría
        ("queratometria_od", "Queratometría OD", "43.00/44.00 @ 180", "Opcional"),
        ("queratometria_os", "Queratometría OS", "43.25/44.25 @ 175", "Opcional"),
        
        # Presión Intraocular
        ("pio_od", "Presión intraocular OD (mmHg)", "14", "Opcional"),
        ("pio_os", "Presión intraocular OS (mmHg)", "15", "Opcional"),
        ("pio_metodo", "Método de medición PIO", "Goldmann", "Opcional"),
        
        # Segmentos
        ("segmento_anterior", "Descripción segmento anterior", "Córnea clara, CA formada...", "Opcional"),
        ("segmento_posterior", "Descripción fondo de ojo", "Papila rosada, bordes definidos...", "Opcional"),
        ("motilidad_ocular", "Motilidad y ducción", "Normal en todas las posiciones", "Opcional"),
        
        # Diagnósticos (hasta 3)
        ("diagnostico_1", "Diagnóstico principal", "Miopía", "Opcional"),
        ("diagnostico_1_cie10", "Código CIE-10 diagnóstico 1", "H52.1", "Opcional"),
        ("diagnostico_1_ojo", "Ojo afectado (OD/OS/OU)", "OU", "Opcional"),
        ("diagnostico_2", "Diagnóstico secundario", "Astigmatismo", "Opcional"),
        ("diagnostico_2_cie10", "Código CIE-10 diagnóstico 2", "H52.2", "Opcional"),
        ("diagnostico_2_ojo", "Ojo afectado (OD/OS/OU)", "OU", "Opcional"),
        ("diagnostico_3", "Diagnóstico adicional", "Presbicia", "Opcional"),
        ("diagnostico_3_cie10", "Código CIE-10 diagnóstico 3", "H52.4", "Opcional"),
        ("diagnostico_3_ojo", "Ojo afectado (OD/OS/OU)", "OU", "Opcional"),
        
        # Plan y Recomendaciones
        ("plan", "Plan de tratamiento", "Control en 6 meses", "Opcional"),
        ("recomendaciones_generales", "Recomendaciones generales", "Uso de lentes permanente", "Opcional"),
        ("estudios_a_realizar", "Estudios solicitados (separados por ;)", "OCT;Campo visual", "Opcional"),
        ("lectura_examenes", "Interpretación de exámenes previos", "OCT normal", "Opcional"),
        
        # Receta de Anteojos
        ("rx_od_esfera", "Receta anteojos OD Esfera", "-2.25", "Opcional"),
        ("rx_od_cilindro", "Receta anteojos OD Cilindro", "-0.75", "Opcional"),
        ("rx_od_eje", "Receta anteojos OD Eje", "180", "Opcional"),
        ("rx_od_adicion", "Receta anteojos OD Adición", "+2.00", "Opcional"),
        ("rx_os_esfera", "Receta anteojos OS Esfera", "-2.00", "Opcional"),
        ("rx_os_cilindro", "Receta anteojos OS Cilindro", "-0.50", "Opcional"),
        ("rx_os_eje", "Receta anteojos OS Eje", "175", "Opcional"),
        ("rx_os_adicion", "Receta anteojos OS Adición", "+2.00", "Opcional"),
        ("rx_distancia_pupilar", "Distancia pupilar (mm)", "62", "Opcional"),
        ("rx_tipo_lente", "Tipo de lente: Monofocal/Bifocal/Progresivo", "Progresivo", "Opcional"),
        ("rx_material", "Material del lente", "Policarbonato", "Opcional"),
        ("rx_tratamientos", "Tratamientos del lente", "Antirreflejo, Filtro azul", "Opcional"),
        ("rx_uso", "Uso: Permanente/Lectura/Distancia", "Permanente", "Opcional"),
        
        # Medicamentos recetados (hasta 3)
        ("med_1_nombre", "Medicamento 1 nombre", "Lagricel", "Opcional"),
        ("med_1_dosis", "Medicamento 1 dosis", "1 gota", "Opcional"),
        ("med_1_frecuencia", "Medicamento 1 frecuencia", "Cada 4 horas", "Opcional"),
        ("med_1_duracion", "Medicamento 1 duración", "30 días", "Opcional"),
        ("med_2_nombre", "Medicamento 2 nombre", "Prednisolona 1%", "Opcional"),
        ("med_2_dosis", "Medicamento 2 dosis", "1 gota", "Opcional"),
        ("med_2_frecuencia", "Medicamento 2 frecuencia", "Cada 6 horas", "Opcional"),
        ("med_2_duracion", "Medicamento 2 duración", "7 días", "Opcional"),
        
        # Próxima cita
        ("proxima_cita_fecha", "Fecha próxima cita YYYY-MM-DD", "2024-12-15", "Opcional"),
        ("proxima_cita_notas", "Notas para próxima cita", "Traer exámenes", "Opcional"),
    ]
    
    # Estilos
    header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    obligatorio_fill = PatternFill(start_color="FFE6E6", end_color="FFE6E6", fill_type="solid")
    opcional_fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
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
        ws_datos.column_dimensions[get_column_letter(col_idx)].width = max(15, len(nombre) + 2)
    
    # Fila de descripciones
    for col_idx, (nombre, descripcion, ejemplo, requerido) in enumerate(columnas, 1):
        cell = ws_datos.cell(row=2, column=col_idx, value=descripcion)
        cell.fill = obligatorio_fill if requerido == "Obligatorio" else opcional_fill
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.border = thin_border
    
    # Fila de ejemplos
    for col_idx, (nombre, descripcion, ejemplo, requerido) in enumerate(columnas, 1):
        cell = ws_datos.cell(row=3, column=col_idx, value=ejemplo)
        cell.font = Font(italic=True, color="666666")
        cell.border = thin_border
    
    # Filas vacías para datos (100 filas)
    for row in range(4, 104):
        for col_idx in range(1, len(columnas) + 1):
            cell = ws_datos.cell(row=row, column=col_idx, value="")
            cell.border = thin_border
    
    # Congelar primera fila
    ws_datos.freeze_panes = "A4"
    
    # ==================== HOJA 2: DICCIONARIO DE DATOS ====================
    ws_dict = wb.create_sheet("Diccionario_Datos")
    
    dict_headers = ["Campo", "Descripción", "Ejemplo", "Requerido", "Valores Válidos"]
    for col_idx, header in enumerate(dict_headers, 1):
        cell = ws_dict.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = thin_border
    
    # Valores válidos por campo
    valores_validos = {
        "paciente_sexo": "masculino, femenino",
        "ant_diabetes": "SI, NO",
        "ant_hipertension": "SI, NO",
        "ant_cardiopatia": "SI, NO",
        "ant_enfermedad_tiroidea": "SI, NO",
        "pio_metodo": "Goldmann, Tonopen, iCare, Perkins, NCT",
        "diagnostico_1_ojo": "OD (derecho), OS (izquierdo), OU (ambos)",
        "diagnostico_2_ojo": "OD, OS, OU",
        "diagnostico_3_ojo": "OD, OS, OU",
        "rx_tipo_lente": "Monofocal, Bifocal, Progresivo",
        "rx_uso": "Permanente, Lectura, Distancia, Computadora",
    }
    
    for row_idx, (nombre, descripcion, ejemplo, requerido) in enumerate(columnas, 2):
        ws_dict.cell(row=row_idx, column=1, value=nombre).border = thin_border
        ws_dict.cell(row=row_idx, column=2, value=descripcion).border = thin_border
        ws_dict.cell(row=row_idx, column=3, value=ejemplo).border = thin_border
        ws_dict.cell(row=row_idx, column=4, value=requerido).border = thin_border
        ws_dict.cell(row=row_idx, column=5, value=valores_validos.get(nombre, "Texto libre")).border = thin_border
        
        if requerido == "Obligatorio":
            for col in range(1, 6):
                ws_dict.cell(row=row_idx, column=col).fill = obligatorio_fill
    
    # Ajustar anchos
    ws_dict.column_dimensions['A'].width = 25
    ws_dict.column_dimensions['B'].width = 40
    ws_dict.column_dimensions['C'].width = 25
    ws_dict.column_dimensions['D'].width = 12
    ws_dict.column_dimensions['E'].width = 40
    
    # ==================== HOJA 3: CÓDIGOS CIE-10 COMUNES ====================
    ws_cie = wb.create_sheet("Codigos_CIE10_Oftalmologia")
    
    cie10_headers = ["Código", "Descripción"]
    for col_idx, header in enumerate(cie10_headers, 1):
        cell = ws_cie.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
    
    codigos_cie10 = [
        ("H52.1", "Miopía"),
        ("H52.0", "Hipermetropía"),
        ("H52.2", "Astigmatismo"),
        ("H52.4", "Presbicia"),
        ("H40.1", "Glaucoma primario de ángulo abierto"),
        ("H40.2", "Glaucoma primario de ángulo cerrado"),
        ("H25.0", "Catarata senil incipiente"),
        ("H25.1", "Catarata senil nuclear"),
        ("H25.2", "Catarata senil tipo Morgagnian"),
        ("H25.8", "Otras cataratas seniles"),
        ("H25.9", "Catarata senil, no especificada"),
        ("H26.9", "Catarata, no especificada"),
        ("H35.3", "Degeneración de la mácula y del polo posterior"),
        ("H35.30", "DMAE no especificada"),
        ("H35.31", "DMAE seca"),
        ("H35.32", "DMAE húmeda"),
        ("H36.0", "Retinopatía diabética"),
        ("E11.3", "Diabetes mellitus tipo 2 con complicaciones oftálmicas"),
        ("H33.0", "Desprendimiento de retina con desgarro"),
        ("H33.2", "Desprendimiento seroso de retina"),
        ("H34.1", "Oclusión de arteria central de la retina"),
        ("H34.2", "Oclusión de arteria de rama retiniana"),
        ("H34.8", "Oclusión de vena central de la retina"),
        ("H04.1", "Ojo seco"),
        ("H10.1", "Conjuntivitis aguda atópica"),
        ("H10.3", "Conjuntivitis aguda, no especificada"),
        ("H10.4", "Conjuntivitis crónica"),
        ("H16.0", "Úlcera corneal"),
        ("H18.6", "Queratocono"),
        ("H20.0", "Iridociclitis aguda"),
        ("H20.1", "Iridociclitis crónica"),
        ("H43.1", "Hemorragia vítrea"),
        ("H43.3", "Otros opacidades vítreas"),
        ("H47.1", "Papiledema"),
        ("H50.0", "Estrabismo convergente concomitante"),
        ("H50.1", "Estrabismo divergente concomitante"),
        ("H53.0", "Ambliopía ex anopsia"),
        ("H53.4", "Defectos del campo visual"),
        ("H54.0", "Ceguera binocular"),
        ("H54.4", "Ceguera monocular"),
        ("H57.1", "Dolor ocular"),
        ("S05.0", "Lesión de conjuntiva y abrasión corneal sin cuerpo extraño"),
    ]
    
    for row_idx, (codigo, descripcion) in enumerate(codigos_cie10, 2):
        ws_cie.cell(row=row_idx, column=1, value=codigo)
        ws_cie.cell(row=row_idx, column=2, value=descripcion)
    
    ws_cie.column_dimensions['A'].width = 12
    ws_cie.column_dimensions['B'].width = 60
    
    # ==================== HOJA 4: INSTRUCCIONES ====================
    ws_inst = wb.create_sheet("Instrucciones")
    
    instrucciones = [
        "INSTRUCCIONES PARA IMPORTACIÓN DE EVALUACIONES OFTALMOLÓGICAS",
        "",
        "1. PREPARACIÓN DE DATOS:",
        "   - Use la hoja 'Plantilla_Datos' para ingresar sus evaluaciones",
        "   - La fila 2 (rosa/azul) muestra la descripción de cada campo",
        "   - La fila 3 (gris) muestra ejemplos de valores válidos",
        "   - Ingrese sus datos a partir de la fila 4",
        "",
        "2. CAMPOS OBLIGATORIOS (rosa):",
        "   - paciente_expediente: Número único del paciente",
        "   - paciente_nombre: Nombre completo",
        "   - paciente_edad: Edad en años",
        "   - paciente_sexo: 'masculino' o 'femenino'",
        "   - fecha: Formato YYYY-MM-DD (ej: 2024-08-15)",
        "   - medico_nombre: Nombre del médico",
        "   - motivo_consulta: Razón de la visita",
        "",
        "3. CAMPOS OPCIONALES (azul):",
        "   - Todos los demás campos son opcionales",
        "   - Puede dejarlos vacíos si no tiene la información",
        "",
        "4. FORMATO DE VALORES:",
        "   - Fechas: YYYY-MM-DD (2024-08-15)",
        "   - Booleanos: SI o NO",
        "   - Dioptrías: Con signo y decimales (-2.25, +1.50)",
        "   - PIO: Solo número en mmHg (14, 15, 16)",
        "   - Ojos: OD (derecho), OS (izquierdo), OU (ambos)",
        "",
        "5. DIAGNÓSTICOS:",
        "   - Puede agregar hasta 3 diagnósticos por evaluación",
        "   - Use los códigos CIE-10 de la hoja 'Codigos_CIE10_Oftalmologia'",
        "",
        "6. MEDICAMENTOS:",
        "   - Puede agregar hasta 2 medicamentos por evaluación",
        "   - Si necesita más, contacte al administrador",
        "",
        "7. EXPORTACIÓN:",
        "   - Una vez completados los datos, guarde el archivo",
        "   - Convierta a CSV o JSON para importar al sistema",
        "   - O contacte al administrador para importación directa",
        "",
        "8. CONTACTO SOPORTE:",
        "   - Para ayuda con la importación, contacte al administrador del sistema",
    ]
    
    for row_idx, linea in enumerate(instrucciones, 1):
        cell = ws_inst.cell(row=row_idx, column=1, value=linea)
        if linea.startswith("INSTRUCCIONES") or linea.endswith(":"):
            cell.font = Font(bold=True, size=12)
    
    ws_inst.column_dimensions['A'].width = 80
    
    # Guardar archivo
    output_path = "/app/plantilla_evaluaciones_oftalmologicas.xlsx"
    wb.save(output_path)
    print(f"✅ Plantilla generada: {output_path}")
    return output_path

if __name__ == "__main__":
    crear_plantilla_evaluaciones()
