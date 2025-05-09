#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generador de reportes para la aplicación de análisis de próstata
Permite crear reportes en diferentes formatos (PDF, HTML) con resultados de análisis
"""

import os
import datetime
import tempfile
import base64
from pathlib import Path
import numpy as np

# Intentar importar reportlab para PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                  Table, TableStyle, PageBreak, Flowable)
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ADVERTENCIA: ReportLab no está disponible. La generación de PDF estará limitada.")

# Intentar importar matplotlib para gráficos
try:
    import matplotlib
    matplotlib.use('Agg')  # Usar backend no interactivo
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("ADVERTENCIA: Matplotlib no está disponible. Los gráficos en reportes estarán limitados.")

from config import REPORT_TEMPLATE_FILE, REPORT_LOGO_FILE

class ReportGenerator:
    """
    Generador de reportes para análisis de próstata
    """
    
    def __init__(self, case_data=None, prediction_results=None):
        """
        Inicializa el generador de reportes
        
        Args:
            case_data: Datos del caso (opcional)
            prediction_results: Resultados de predicción (opcional)
        """
        self.case_data = case_data
        self.prediction_results = prediction_results
        self.temp_dir = tempfile.mkdtemp(prefix="prostate_report_")
        self.images = []  # Lista para almacenar rutas de imágenes generadas
    
    def set_case_data(self, case_data):
        """
        Establece los datos del caso
        
        Args:
            case_data: Diccionario con datos del caso
        """
        self.case_data = case_data
    
    def set_prediction_results(self, prediction_results):
        """
        Establece los resultados de predicción
        
        Args:
            prediction_results: Diccionario con resultados de predicción
        """
        self.prediction_results = prediction_results
    
    def add_image(self, image_path, description=""):
        """
        Añade una imagen al reporte
        
        Args:
            image_path: Ruta a la imagen
            description: Descripción de la imagen
        """
        if os.path.exists(image_path):
            self.images.append({
                "path": image_path,
                "description": description
            })
    
    def generate_pdf_report(self, output_path, report_data=None):
        """
        Genera un reporte en formato PDF
        
        Args:
            output_path: Ruta donde guardar el PDF
            report_data: Datos adicionales para el reporte (opcional)
            
        Returns:
            True si se generó correctamente, False en caso contrario
        """
        if not REPORTLAB_AVAILABLE:
            print("ERROR: ReportLab no está disponible para generar PDF")
            return False
        
        if not self.case_data and not report_data:
            print("ERROR: No hay datos para generar el reporte")
            return False
        
        try:
            # Combinar datos del caso con datos adicionales
            data = {}
            if self.case_data:
                data.update(self.case_data)
            if report_data:
                data.update(report_data)
            
            # Crear documento
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=72,  # 1 pulgada
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
                title=f"Reporte de Análisis de Próstata - {data.get('name', 'Sin Nombre')}"
            )
            
            # Estilos
            styles = getSampleStyleSheet()
            
            # Estilo para títulos
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.darkblue,
                spaceAfter=12
            )
            
            # Estilo para subtítulos
            heading_style = ParagraphStyle(
                'HeadingStyle',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.darkblue,
                spaceAfter=6
            )
            
            # Estilo para texto normal
            normal_style = styles['Normal']
            
            # Estilo para notas
            note_style = ParagraphStyle(
                'NoteStyle',
                parent=styles['Italic'],
                fontSize=8,
                textColor=colors.gray
            )
            
            # Elementos del documento
            elements = []
            
            # Encabezado con logo
            if os.path.exists(REPORT_LOGO_FILE):
                elements.append(Image(REPORT_LOGO_FILE, width=2*inch, height=1*inch))
            
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("REPORTE DE ANÁLISIS DE PRÓSTATA", title_style))
            elements.append(Spacer(1, 12))
            
            # Información de paciente
            elements.append(Paragraph("INFORMACIÓN DEL PACIENTE", heading_style))
            
            # Tabla para información del paciente
            patient_data = [
                ["ID:", data.get('patient_id', 'No disponible')],
                ["Nombre:", data.get('patient_name', 'No disponible')],
                ["Fecha de Nacimiento:", data.get('patient_dob', 'No disponible')],
                ["Edad:", data.get('patient_age', 'No disponible')]
            ]
            
            patient_table = Table(patient_data, colWidths=[100, 300])
            patient_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.darkblue),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            
            elements.append(patient_table)
            elements.append(Spacer(1, 12))
            
            # Información del estudio
            elements.append(Paragraph("INFORMACIÓN DEL ESTUDIO", heading_style))
            
            # Tabla para información del estudio
            study_data = [
                ["Fecha:", data.get('study_date', 'No disponible')],
                ["Institución:", data.get('institution', 'No disponible')],
                ["Médico:", data.get('physician', 'No disponible')]
            ]
            
            # Añadir información de secuencias si está disponible
            if 'files' in self.case_data:
                sequences = []
                for file_info in self.case_data['files']:
                    if 'sequence_type' in file_info:
                        sequences.append(file_info['sequence_type'].upper())
                
                if sequences:
                    study_data.append(["Secuencias:", ", ".join(sequences)])
            
            study_table = Table(study_data, colWidths=[100, 300])
            study_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.darkblue),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            
            elements.append(study_table)
            elements.append(Spacer(1, 12))
            
            # Hallazgos
            elements.append(Paragraph("HALLAZGOS", heading_style))
            
            # Si hay resultados de predicción, mostrarlos
            if self.prediction_results:
                # Verificar si hay lesiones
                if 'lesions' in self.prediction_results and self.prediction_results['lesions']:
                    elements.append(Paragraph(
                        f"Se detectaron {len(self.prediction_results['lesions'])} lesión(es) sospechosa(s).",
                        normal_style
                    ))
                    
                    # Añadir tabla de lesiones
                    lesion_table_data = [
                        ["Lesión", "Volumen (mm³)", "Diámetro (mm)", "Probabilidad", "Severidad"]
                    ]
                    
                    for i, lesion in enumerate(self.prediction_results['lesions']):
                        lesion_table_data.append([
                            f"{i+1}",
                            f"{lesion.get('volume_mm3', 0):.2f}",
                            f"{lesion.get('max_diameter_mm', 0):.2f}",
                            f"{lesion.get('probability', 0):.2f}",
                            lesion.get('severity', 'No determinada')
                        ])
                    
                    lesion_table = Table(lesion_table_data, colWidths=[40, 85, 85, 85, 85])
                    lesion_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Centra la columna "Lesión"
                        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # Alinea las columnas numéricas a la derecha
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                    ]))
                    
                    elements.append(lesion_table)
                    elements.append(Spacer(1, 12))
                    
                    # Añadir gráfico de lesiones si matplotlib está disponible
                    if MATPLOTLIB_AVAILABLE and len(self.prediction_results['lesions']) > 0:
                        # Generar gráfico de barras de volúmenes de lesiones
                        chart_path = self._generate_lesion_chart()
                        if chart_path:
                            elements.append(Paragraph("Características de Lesiones", heading_style))
                            elements.append(Image(chart_path, width=6*inch, height=3*inch))
                            elements.append(Spacer(1, 12))
                
                else:
                    elements.append(Paragraph(
                        "No se detectaron lesiones sospechosas en el estudio.",
                        normal_style
                    ))
            else:
                elements.append(Paragraph(
                    "No hay resultados de análisis disponibles.",
                    normal_style
                ))
            
            # Añadir imágenes del caso
            if self.images:
                elements.append(PageBreak())
                elements.append(Paragraph("IMÁGENES", heading_style))
                
                for img_info in self.images:
                    if os.path.exists(img_info["path"]):
                        elements.append(Spacer(1, 6))
                        elements.append(Paragraph(img_info["description"], normal_style))
                        elements.append(Image(img_info["path"], width=5*inch, height=4*inch))
                        elements.append(Spacer(1, 12))
                                 
            # Conclusiones
            if 'conclusion' in data or ('has_significant_lesion' in self.prediction_results and self.prediction_results['has_significant_lesion']):
                elements.append(Paragraph("CONCLUSIONES", heading_style))
                
                if 'conclusion' in data:
                    elements.append(Paragraph(data['conclusion'], normal_style))
                elif 'has_significant_lesion' in self.prediction_results:
                    if self.prediction_results['has_significant_lesion']:
                        elements.append(Paragraph(
                            "Se detectaron lesiones con alta probabilidad de significancia clínica. "
                            "Se recomienda correlación con hallazgos clínicos y considerar biopsia dirigida.",
                            normal_style
                        ))
                    else:
                        elements.append(Paragraph(
                            "No se detectaron lesiones con alta probabilidad de significancia clínica. "
                            "Se sugiere seguimiento según protocolo habitual.",
                            normal_style
                        ))
            
            # Recomendaciones
            if 'recommendations' in data:
                elements.append(Paragraph("RECOMENDACIONES", heading_style))
                
                # Verificar si es un string o una lista
                if isinstance(data['recommendations'], str):
                    elements.append(Paragraph(data['recommendations'], normal_style))
                elif isinstance(data['recommendations'], list):
                    for rec in data['recommendations']:
                        elements.append(Paragraph(f"• {rec}", normal_style))
                else:
                    elements.append(Paragraph("No hay recomendaciones específicas.", normal_style))
            
            # Nota final
            elements.append(Spacer(1, 24))
            elements.append(Paragraph(
                "NOTA: Este reporte fue generado automáticamente mediante inteligencia artificial "
                "y debe ser revisado por un profesional médico cualificado.",
                note_style
            ))
            
            # Fecha de generación
            elements.append(Paragraph(
                f"Fecha de Generación: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
                note_style
            ))
            
            # Construir el documento
            doc.build(elements)
            
            print(f"Reporte PDF generado correctamente: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generando reporte PDF: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_html_report(self, output_path, report_data=None):
        """
        Genera un reporte en formato HTML
        
        Args:
            output_path: Ruta donde guardar el HTML
            report_data: Datos adicionales para el reporte (opcional)
            
        Returns:
            True si se generó correctamente, False en caso contrario
        """
        if not self.case_data and not report_data:
            print("ERROR: No hay datos para generar el reporte")
            return False
        
        try:
            # Combinar datos del caso con datos adicionales
            data = {}
            if self.case_data:
                data.update(self.case_data)
            if report_data:
                data.update(report_data)
            
            # Cargar plantilla si existe
            template_content = ""
            if os.path.exists(REPORT_TEMPLATE_FILE):
                with open(REPORT_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                    template_content = f.read()
            
            # Si no hay plantilla, crear HTML básico
            if not template_content:
                template_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Análisis de Próstata</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #004080; }
        h2 { color: #004080; margin-top: 20px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; color: #004080; }
        .note { color: #888; font-size: 0.8em; font-style: italic; }
        .img-container { margin: 20px 0; text-align: center; }
        .chart-container { margin: 20px 0; }
    </style>
</head>
<body>
    <header>
        <h1>REPORTE DE ANÁLISIS DE PRÓSTATA</h1>
    </header>
    
    <section id="patient-info">
        <h2>INFORMACIÓN DEL PACIENTE</h2>
        <table>
            <tr><th>ID:</th><td>{{patient_id}}</td></tr>
            <tr><th>Nombre:</th><td>{{patient_name}}</td></tr>
            <tr><th>Fecha de Nacimiento:</th><td>{{patient_dob}}</td></tr>
            <tr><th>Edad:</th><td>{{patient_age}}</td></tr>
        </table>
    </section>
    
    <section id="study-info">
        <h2>INFORMACIÓN DEL ESTUDIO</h2>
        <table>
            <tr><th>Fecha:</th><td>{{study_date}}</td></tr>
            <tr><th>Institución:</th><td>{{institution}}</td></tr>
            <tr><th>Médico:</th><td>{{physician}}</td></tr>
            <tr><th>Secuencias:</th><td>{{sequences}}</td></tr>
        </table>
    </section>
    
    <section id="findings">
        <h2>HALLAZGOS</h2>
        <div id="findings-content">
            {{findings_content}}
        </div>
        
        <div id="lesions-table">
            {{lesions_table}}
        </div>
        
        <div class="chart-container">
            {{lesion_chart}}
        </div>
    </section>
    
    <section id="images">
        <h2>IMÁGENES</h2>
        <div id="images-content">
            {{images_content}}
        </div>
    </section>
    
    <section id="conclusion">
        <h2>CONCLUSIONES</h2>
        <div id="conclusion-content">
            {{conclusion_content}}
        </div>
    </section>
    
    <section id="recommendations">
        <h2>RECOMENDACIONES</h2>
        <div id="recommendations-content">
            {{recommendations_content}}
        </div>
    </section>
    
    <footer>
        <p class="note">NOTA: Este reporte fue generado automáticamente mediante inteligencia artificial y debe ser revisado por un profesional médico cualificado.</p>
        <p class="note">Fecha de Generación: {{generation_date}}</p>
    </footer>
</body>
</html>
"""
            
            # Preparar datos para reemplazo en la plantilla
            replacements = {
                "{{patient_id}}": data.get('patient_id', 'No disponible'),
                "{{patient_name}}": data.get('patient_name', 'No disponible'),
                "{{patient_dob}}": data.get('patient_dob', 'No disponible'),
                "{{patient_age}}": data.get('patient_age', 'No disponible'),
                "{{study_date}}": data.get('study_date', 'No disponible'),
                "{{institution}}": data.get('institution', 'No disponible'),
                "{{physician}}": data.get('physician', 'No disponible'),
                "{{generation_date}}": datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
            }
            
            # Secuencias
            sequences = []
            if 'files' in self.case_data:
                for file_info in self.case_data['files']:
                    if 'sequence_type' in file_info:
                        sequences.append(file_info['sequence_type'].upper())
            
            replacements["{{sequences}}"] = ", ".join(sequences) if sequences else "No disponible"
            
            # Hallazgos
            findings_content = ""
            if self.prediction_results:
                if 'lesions' in self.prediction_results and self.prediction_results['lesions']:
                    findings_content = f"<p>Se detectaron {len(self.prediction_results['lesions'])} lesión(es) sospechosa(s).</p>"
                else:
                    findings_content = "<p>No se detectaron lesiones sospechosas en el estudio.</p>"
            else:
                findings_content = "<p>No hay resultados de análisis disponibles.</p>"
            
            replacements["{{findings_content}}"] = findings_content
            
            # Tabla de lesiones
            lesions_table = ""
            if self.prediction_results and 'lesions' in self.prediction_results and self.prediction_results['lesions']:
                lesions_table = """
                <table>
                    <thead>
                        <tr>
                            <th>Lesión</th>
                            <th>Volumen (mm³)</th>
                            <th>Diámetro (mm)</th>
                            <th>Probabilidad</th>
                            <th>Severidad</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                
                for i, lesion in enumerate(self.prediction_results['lesions']):
                    lesions_table += f"""
                        <tr>
                            <td>{i+1}</td>
                            <td>{lesion.get('volume_mm3', 0):.2f}</td>
                            <td>{lesion.get('max_diameter_mm', 0):.2f}</td>
                            <td>{lesion.get('probability', 0):.2f}</td>
                            <td>{lesion.get('severity', 'No determinada')}</td>
                        </tr>
                    """
                
                lesions_table += """
                    </tbody>
                </table>
                """
            
            replacements["{{lesions_table}}"] = lesions_table
            
            # Gráfico de lesiones
            lesion_chart = ""
            if MATPLOTLIB_AVAILABLE and self.prediction_results and 'lesions' in self.prediction_results and self.prediction_results['lesions']:
                chart_path = self._generate_lesion_chart()
                if chart_path:
                    # Convertir imagen a base64 para incrustar en HTML
                    with open(chart_path, 'rb') as img_file:
                        img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    lesion_chart = f"""
                    <div class="chart-container">
                        <h3>Características de Lesiones</h3>
                        <img src="data:image/png;base64,{img_data}" alt="Gráfico de lesiones" style="max-width:100%;">
                    </div>
                    """
            
            replacements["{{lesion_chart}}"] = lesion_chart
            
            # Imágenes
            images_content = ""
            for img_info in self.images:
                if os.path.exists(img_info["path"]):
                    # Convertir imagen a base64 para incrustar en HTML
                    with open(img_info["path"], 'rb') as img_file:
                        img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    images_content += f"""
                    <div class="img-container">
                        <p>{img_info["description"]}</p>
                        <img src="data:image/png;base64,{img_data}" alt="{img_info["description"]}" style="max-width:100%; max-height:500px;">
                    </div>
                    """
            
            replacements["{{images_content}}"] = images_content
            
            # Conclusiones
            conclusion_content = ""
            if 'conclusion' in data:
                conclusion_content = f"<p>{data['conclusion']}</p>"
            elif 'has_significant_lesion' in self.prediction_results:
                if self.prediction_results['has_significant_lesion']:
                    conclusion_content = (
                        "<p>Se detectaron lesiones con alta probabilidad de significancia clínica. "
                        "Se recomienda correlación con hallazgos clínicos y considerar biopsia dirigida.</p>"
                    )
                else:
                    conclusion_content = (
                        "<p>No se detectaron lesiones con alta probabilidad de significancia clínica. "
                        "Se sugiere seguimiento según protocolo habitual.</p>"
                    )
            
            replacements["{{conclusion_content}}"] = conclusion_content
            
            # Recomendaciones
            recommendations_content = ""
            if 'recommendations' in data:
                if isinstance(data['recommendations'], str):
                    recommendations_content = f"<p>{data['recommendations']}</p>"
                elif isinstance(data['recommendations'], list):
                    recommendations_content = "<ul>"
                    for rec in data['recommendations']:
                        recommendations_content += f"<li>{rec}</li>"
                    recommendations_content += "</ul>"
                else:
                    recommendations_content = "<p>No hay recomendaciones específicas.</p>"
            else:
                recommendations_content = "<p>No hay recomendaciones específicas.</p>"
            
            replacements["{{recommendations_content}}"] = recommendations_content
            
            # Reemplazar todas las etiquetas en la plantilla
            html_content = template_content
            for key, value in replacements.items():
                html_content = html_content.replace(key, value)
            
            # Guardar archivo HTML
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"Reporte HTML generado correctamente: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generando reporte HTML: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_text_report(self, output_path, report_data=None):
        """
        Genera un reporte en formato de texto plano
        
        Args:
            output_path: Ruta donde guardar el texto
            report_data: Datos adicionales para el reporte (opcional)
            
        Returns:
            True si se generó correctamente, False en caso contrario
        """
        if not self.case_data and not report_data:
            print("ERROR: No hay datos para generar el reporte")
            return False
        
        try:
            # Combinar datos del caso con datos adicionales
            data = {}
            if self.case_data:
                data.update(self.case_data)
            if report_data:
                data.update(report_data)
            
            # Crear contenido de texto
            text_content = "REPORTE DE ANÁLISIS DE PRÓSTATA\n"
            text_content += "=" * 40 + "\n\n"
            
            # Información del paciente
            text_content += "INFORMACIÓN DEL PACIENTE\n"
            text_content += "-" * 30 + "\n"
            text_content += f"ID: {data.get('patient_id', 'No disponible')}\n"
            text_content += f"Nombre: {data.get('patient_name', 'No disponible')}\n"
            text_content += f"Fecha de Nacimiento: {data.get('patient_dob', 'No disponible')}\n"
            text_content += f"Edad: {data.get('patient_age', 'No disponible')}\n\n"
            
            # Información del estudio
            text_content += "INFORMACIÓN DEL ESTUDIO\n"
            text_content += "-" * 30 + "\n"
            text_content += f"Fecha: {data.get('study_date', 'No disponible')}\n"
            text_content += f"Institución: {data.get('institution', 'No disponible')}\n"
            text_content += f"Médico: {data.get('physician', 'No disponible')}\n"
            
            # Secuencias
            sequences = []
            if 'files' in self.case_data:
                for file_info in self.case_data['files']:
                    if 'sequence_type' in file_info:
                        sequences.append(file_info['sequence_type'].upper())
            
            text_content += f"Secuencias: {', '.join(sequences) if sequences else 'No disponible'}\n\n"
            
            # Hallazgos
            text_content += "HALLAZGOS\n"
            text_content += "-" * 30 + "\n"
            
            if self.prediction_results:
                if 'lesions' in self.prediction_results and self.prediction_results['lesions']:
                    text_content += f"Se detectaron {len(self.prediction_results['lesions'])} lesión(es) sospechosa(s).\n\n"
                    
                    # Detalles de lesiones
                    for i, lesion in enumerate(self.prediction_results['lesions']):
                        text_content += f"Lesión {i+1}:\n"
                        text_content += f"- Volumen: {lesion.get('volume_mm3', 0):.2f} mm³\n"
                        text_content += f"- Diámetro máximo: {lesion.get('max_diameter_mm', 0):.2f} mm\n"
                        text_content += f"- Probabilidad: {lesion.get('probability', 0):.2f}\n"
                        text_content += f"- Severidad: {lesion.get('severity', 'No determinada')}\n\n"
                else:
                    text_content += "No se detectaron lesiones sospechosas en el estudio.\n\n"
            else:
                text_content += "No hay resultados de análisis disponibles.\n\n"
            
            # Conclusiones
            text_content += "CONCLUSIONES\n"
            text_content += "-" * 30 + "\n"
            
            if 'conclusion' in data:
                text_content += f"{data['conclusion']}\n\n"
            elif 'has_significant_lesion' in self.prediction_results:
                if self.prediction_results['has_significant_lesion']:
                    text_content += (
                        "Se detectaron lesiones con alta probabilidad de significancia clínica. "
                        "Se recomienda correlación con hallazgos clínicos y considerar biopsia dirigida.\n\n"
                    )
                else:
                    text_content += (
                        "No se detectaron lesiones con alta probabilidad de significancia clínica. "
                        "Se sugiere seguimiento según protocolo habitual.\n\n"
                    )
            else:
                text_content += "No hay conclusiones disponibles.\n\n"
            
            # Recomendaciones
            text_content += "RECOMENDACIONES\n"
            text_content += "-" * 30 + "\n"
            
            if 'recommendations' in data:
                if isinstance(data['recommendations'], str):
                    text_content += f"{data['recommendations']}\n\n"
                elif isinstance(data['recommendations'], list):
                    for rec in data['recommendations']:
                        text_content += f"- {rec}\n"
                    text_content += "\n"
                else:
                    text_content += "No hay recomendaciones específicas.\n\n"
            else:
                text_content += "No hay recomendaciones específicas.\n\n"
            
            # Nota final
            text_content += "NOTA: Este reporte fue generado automáticamente mediante inteligencia artificial "
            text_content += "y debe ser revisado por un profesional médico cualificado.\n\n"
            
            # Fecha de generación
            text_content += f"Fecha de Generación: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
            
            # Guardar archivo de texto
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            print(f"Reporte de texto generado correctamente: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generando reporte de texto: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_lesion_chart(self):
        """
        Genera un gráfico de barras con características de lesiones
        
        Returns:
            Ruta al archivo de imagen generado, o None si no se pudo generar
        """
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        if not self.prediction_results or 'lesions' not in self.prediction_results or not self.prediction_results['lesions']:
            return None
        
        try:
            # Crear figura
            fig = plt.figure(figsize=(8, 5))
            ax = fig.add_subplot(111)
            
            # Datos para el gráfico
            lesion_ids = [f"Lesión {i+1}" for i in range(len(self.prediction_results['lesions']))]
            volumes = [lesion.get('volume_mm3', 0) for lesion in self.prediction_results['lesions']]
            probabilities = [lesion.get('probability', 0) * 100 for lesion in self.prediction_results['lesions']]
            
            # Crear gráfico de barras
            x = np.arange(len(lesion_ids))
            width = 0.35
            
            ax.bar(x - width/2, volumes, width, label='Volumen (mm³)')
            ax.bar(x + width/2, probabilities, width, label='Probabilidad (%)')
            
            # Etiquetas y leyenda
            ax.set_ylabel('Valor')
            ax.set_title('Características de Lesiones')
            ax.set_xticks(x)
            ax.set_xticklabels(lesion_ids)
            ax.legend()
            
            # Ajustar diseño
            plt.tight_layout()
            
            # Guardar figura
            chart_path = os.path.join(self.temp_dir, 'lesion_chart.png')
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            return chart_path
            
        except Exception as e:
            print(f"Error generando gráfico de lesiones: {str(e)}")
            return None
    
    def cleanup(self):
        """Limpia archivos temporales generados"""
        try:
            # Eliminar archivos temporales
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                    except:
                        pass
            
            # Eliminar directorio temporal
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            
        except Exception as e:
            print(f"Error limpiando archivos temporales: {str(e)}")