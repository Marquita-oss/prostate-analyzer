#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Diálogo para generación de reportes de análisis de próstata
Permite crear y guardar informes con los resultados de la predicción
"""

import os
import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QTextEdit, QPushButton, QComboBox, QGroupBox,
                           QFormLayout, QCheckBox, QFileDialog, QMessageBox,
                           QTabWidget, QWidget, QLineEdit, QDateEdit, QSpinBox)
from PyQt5.QtCore import Qt, QSize, QDate
from PyQt5.QtGui import QFont, QPixmap, QImage

# Intentar importar reportlab para generación de PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ADVERTENCIA: ReportLab no está disponible. La generación de PDF estará limitada.")

# Intentar importar matplotlib para gráficos
try:
    import matplotlib
    matplotlib.use('Agg')  # Usar backend no interactivo para reportes
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("ADVERTENCIA: Matplotlib no está disponible. Los gráficos estarán limitados.")

from config import REPORT_TEMPLATE_FILE, REPORT_LOGO_FILE, DEFAULT_REPORT_DIR

class ReportDialog(QDialog):
    """
    Diálogo para generar reportes con los resultados de predicción
    """
    
    def __init__(self, case_data, prediction_results, parent=None):
        super(ReportDialog, self).__init__(parent)
        
        # Datos para el reporte
        self.case_data = case_data
        self.prediction_results = prediction_results
        
        # Configurar diálogo
        self.setWindowTitle("Generar Reporte")
        self.setMinimumSize(700, 600)
        
        # Crear interfaz
        self.setup_ui()
        
        # Llenar campos con datos iniciales
        self.populate_fields()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # Pestañas
        self.tab_widget = QTabWidget()
        
        # Pestaña de información
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        
        # Grupo de información de paciente
        patient_group = QGroupBox("Información de Paciente")
        patient_layout = QFormLayout(patient_group)
        
        # ID de paciente
        self.patient_id_edit = QLineEdit()
        patient_layout.addRow("ID de Paciente:", self.patient_id_edit)
        
        # Nombre de paciente
        self.patient_name_edit = QLineEdit()
        patient_layout.addRow("Nombre de Paciente:", self.patient_name_edit)
        
        # Fecha de nacimiento
        self.patient_dob_edit = QDateEdit()
        self.patient_dob_edit.setCalendarPopup(True)
        self.patient_dob_edit.setDate(QDate.currentDate().addYears(-65))  # Default: 65 años
        patient_layout.addRow("Fecha de Nacimiento:", self.patient_dob_edit)
        
        # Edad
        self.patient_age_spin = QSpinBox()
        self.patient_age_spin.setRange(0, 120)
        self.patient_age_spin.setValue(65)
        patient_layout.addRow("Edad:", self.patient_age_spin)
        
        info_layout.addWidget(patient_group)
        
        # Grupo de información de estudio
        study_group = QGroupBox("Información de Estudio")
        study_layout = QFormLayout(study_group)
        
        # Fecha de estudio
        self.study_date_edit = QDateEdit()
        self.study_date_edit.setCalendarPopup(True)
        self.study_date_edit.setDate(QDate.currentDate())
        study_layout.addRow("Fecha de Estudio:", self.study_date_edit)
        
        # Institución
        self.institution_edit = QLineEdit("Hospital General")
        study_layout.addRow("Institución:", self.institution_edit)
        
        # Médico responsable
        self.physician_edit = QLineEdit("Dr. Juan Pérez")
        study_layout.addRow("Médico Responsable:", self.physician_edit)
        
        info_layout.addWidget(study_group)
        
        self.tab_widget.addTab(info_tab, "Información")
        
        # Pestaña de hallazgos
        findings_tab = QWidget()
        findings_layout = QVBoxLayout(findings_tab)
        
        # Hallazgos
        findings_label = QLabel("Descripción de Hallazgos:")
        findings_layout.addWidget(findings_label)
        
        self.findings_edit = QTextEdit()
        findings_layout.addWidget(self.findings_edit)
        
        # Grupo de resultados de predicción
        prediction_group = QGroupBox("Resultados de Predicción")
        prediction_layout = QFormLayout(prediction_group)
        
        # Número de lesiones
        self.lesion_count_spin = QSpinBox()
        self.lesion_count_spin.setRange(0, 99)
        self.lesion_count_spin.setReadOnly(True)
        prediction_layout.addRow("Número de Lesiones:", self.lesion_count_spin)
        
        # Volumen total
        self.total_volume_edit = QLineEdit()
        self.total_volume_edit.setReadOnly(True)
        prediction_layout.addRow("Volumen Total (mm³):", self.total_volume_edit)
        
        # Checkbox para incluir vista 3D
        self.include_3d_check = QCheckBox("Incluir visualización 3D en el reporte")
        self.include_3d_check.setChecked(True)
        prediction_layout.addRow("", self.include_3d_check)
        
        findings_layout.addWidget(prediction_group)
        
        self.tab_widget.addTab(findings_tab, "Hallazgos")
        
        # Pestaña de conclusiones
        conclusion_tab = QWidget()
        conclusion_layout = QVBoxLayout(conclusion_tab)
        
        # Conclusiones
        conclusion_label = QLabel("Conclusiones:")
        conclusion_layout.addWidget(conclusion_label)
        
        self.conclusion_edit = QTextEdit()
        conclusion_layout.addWidget(self.conclusion_edit)
        
        # Grupo de recomendaciones
        recommendation_group = QGroupBox("Recomendaciones")
        recommendation_layout = QVBoxLayout(recommendation_group)
        
        # Recomendaciones predefinidas
        self.follow_up_check = QCheckBox("Seguimiento en 6 meses")
        self.follow_up_check.setChecked(True)
        recommendation_layout.addWidget(self.follow_up_check)
        
        self.biopsy_check = QCheckBox("Se recomienda biopsia")
        recommendation_layout.addWidget(self.biopsy_check)
        
        self.additional_check = QCheckBox("Estudios adicionales recomendados")
        recommendation_layout.addWidget(self.additional_check)
        
        # Campo para recomendaciones personalizadas
        self.custom_recommendation_edit = QTextEdit()
        self.custom_recommendation_edit.setPlaceholderText("Recomendaciones adicionales...")
        recommendation_layout.addWidget(self.custom_recommendation_edit)
        
        conclusion_layout.addWidget(recommendation_group)
        
        self.tab_widget.addTab(conclusion_tab, "Conclusiones")
        
        # Pestaña de vista previa
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        
        preview_label = QLabel("Vista Previa del Reporte:")
        preview_layout.addWidget(preview_label)
        
        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        preview_layout.addWidget(self.preview_edit)
        
        preview_note = QLabel("Nota: Esta es una vista previa simplificada. El PDF final incluirá imágenes y mejor formato.")
        preview_note.setStyleSheet("color: gray;")
        preview_layout.addWidget(preview_note)
        
        self.tab_widget.addTab(preview_tab, "Vista Previa")
        
        # Añadir pestañas al layout principal
        main_layout.addWidget(self.tab_widget)
        
        # Botones inferiores
        buttons_layout = QHBoxLayout()
        
        # Formato de reporte
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Formato:"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PDF", "HTML", "Texto"])
        format_layout.addWidget(self.format_combo)
        
        buttons_layout.addLayout(format_layout)
        
        # Separador flexible
        buttons_layout.addStretch()
        
        # Botones de acción
        self.preview_button = QPushButton("Actualizar Vista Previa")
        self.preview_button.clicked.connect(self.update_preview)
        buttons_layout.addWidget(self.preview_button)
        
        self.save_button = QPushButton("Guardar Reporte")
        self.save_button.clicked.connect(self.save_report)
        buttons_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(buttons_layout)
    
    def populate_fields(self):
        """Llena los campos con datos iniciales"""
        # Información de paciente
        if self.case_data and 'metadata' in self.case_data:
            metadata = self.case_data['metadata']
            
            if 'patient_id' in metadata:
                self.patient_id_edit.setText(metadata['patient_id'])
            
            if 'patient_name' in metadata:
                self.patient_name_edit.setText(metadata['patient_name'])
            
            if 'study_date' in metadata:
                try:
                    # Intentar convertir fecha de estudio
                    date_str = metadata['study_date']
                    if len(date_str) == 8:  # Formato DICOM: YYYYMMDD
                        year = int(date_str[0:4])
                        month = int(date_str[4:6])
                        day = int(date_str[6:8])
                        self.study_date_edit.setDate(QDate(year, month, day))
                except:
                    pass
        
        # Resultados de predicción
        if self.prediction_results:
            # Número de lesiones
            num_lesions = self.prediction_results.get('num_lesions', 0)
            self.lesion_count_spin.setValue(num_lesions)
            
            # Volumen total
            total_volume = self.prediction_results.get('total_lesion_volume', 0)
            self.total_volume_edit.setText(f"{total_volume:.2f}")
            
            # Hallazgos
            findings_text = self._generate_findings_text()
            self.findings_edit.setPlainText(findings_text)
            
            # Conclusiones
            conclusion_text = self._generate_conclusion_text()
            self.conclusion_edit.setPlainText(conclusion_text)
        
        # Actualizar vista previa
        self.update_preview()
    
    def _generate_findings_text(self):
        """Genera texto de hallazgos basado en los resultados"""
        if not self.prediction_results:
            return "No hay resultados de predicción disponibles."
        
        num_lesions = self.prediction_results.get('num_lesions', 0)
        
        if num_lesions == 0:
            return "No se detectaron lesiones sospechosas en el estudio."
        
        text = f"Se detectaron {num_lesions} lesión(es) sospechosa(s) en el estudio.\n\n"
        
        # Añadir detalles de cada lesión
        if 'lesions' in self.prediction_results:
            for i, lesion in enumerate(self.prediction_results['lesions']):
                text += f"Lesión {i+1}:\n"
                text += f"- Volumen: {lesion['volume_mm3']:.2f} mm³\n"
                text += f"- Diámetro máximo: {lesion['max_diameter_mm']:.2f} mm\n"
                text += f"- Probabilidad: {lesion['probability']:.2f}\n"
                text += f"- Severidad: {lesion['severity']}\n"
                
                # Ubicación basada en el centroide
                if 'centroid' in lesion:
                    # Convertir coordenadas a descripción anatómica aproximada
                    x, y, z = lesion['centroid']
                    location = "No determinada"
                    
                    # Esta es una simplificación - una implementación real
                    # requeriría un atlas anatómico detallado de la próstata
                    if x < 0:
                        location = "Lado izquierdo"
                    else:
                        location = "Lado derecho"
                    
                    if z < 0:
                        location += ", zona anterior"
                    else:
                        location += ", zona posterior"
                    
                    text += f"- Ubicación: {location}\n"
                
                text += "\n"
        
        return text
    
    def _generate_conclusion_text(self):
        """Genera texto de conclusión basado en los resultados"""
        if not self.prediction_results:
            return "No hay resultados de predicción disponibles."
        
        num_lesions = self.prediction_results.get('num_lesions', 0)
        has_significant = self.prediction_results.get('has_significant_lesion', False)
        
        if num_lesions == 0:
            return "No se detectaron lesiones sospechosas. Se recomienda seguimiento rutinario."
        
        if has_significant:
            return (f"Se detectaron {num_lesions} lesión(es), incluyendo al menos una con "
                   f"alta probabilidad de ser clínicamente significativa. "
                   f"Se recomienda correlación con hallazgos clínicos y considerar biopsia dirigida.")
        else:
            return (f"Se detectaron {num_lesions} lesión(es) de baja probabilidad. "
                   f"Se recomienda seguimiento en 6 meses para evaluar cambios.")
    
    def update_preview(self):
        """Actualiza la vista previa del reporte"""
        # Cambiar a la pestaña de vista previa
        self.tab_widget.setCurrentIndex(3)
        
        # Generar vista previa en formato texto
        preview_text = self._generate_preview_text()
        
        # Mostrar en el campo de vista previa
        self.preview_edit.setPlainText(preview_text)
    
    def _generate_preview_text(self):
        """Genera texto para la vista previa del reporte"""
        text = "REPORTE DE ANÁLISIS DE PRÓSTATA\n"
        text += "=" * 40 + "\n\n"
        
        # Información de paciente
        text += "INFORMACIÓN DEL PACIENTE\n"
        text += "-" * 30 + "\n"
        text += f"ID: {self.patient_id_edit.text()}\n"
        text += f"Nombre: {self.patient_name_edit.text()}\n"
        text += f"Fecha de Nacimiento: {self.patient_dob_edit.date().toString('dd/MM/yyyy')}\n"
        text += f"Edad: {self.patient_age_spin.value()} años\n\n"
        
        # Información del estudio
        text += "INFORMACIÓN DEL ESTUDIO\n"
        text += "-" * 30 + "\n"
        text += f"Fecha: {self.study_date_edit.date().toString('dd/MM/yyyy')}\n"
        text += f"Institución: {self.institution_edit.text()}\n"
        text += f"Médico: {self.physician_edit.text()}\n\n"
        
        # Hallazgos
        text += "HALLAZGOS\n"
        text += "-" * 30 + "\n"
        text += self.findings_edit.toPlainText() + "\n\n"
        
        # Conclusiones
        text += "CONCLUSIONES\n"
        text += "-" * 30 + "\n"
        text += self.conclusion_edit.toPlainText() + "\n\n"
        
        # Recomendaciones
        text += "RECOMENDACIONES\n"
        text += "-" * 30 + "\n"
        
        recommendations = []
        if self.follow_up_check.isChecked():
            recommendations.append("- Seguimiento en 6 meses")
        
        if self.biopsy_check.isChecked():
            recommendations.append("- Se recomienda biopsia")
        
        if self.additional_check.isChecked():
            recommendations.append("- Estudios adicionales recomendados")
        
        # Añadir recomendaciones personalizadas
        custom_rec = self.custom_recommendation_edit.toPlainText().strip()
        if custom_rec:
            for line in custom_rec.split('\n'):
                if line.strip():
                    if not line.startswith('-'):
                        line = f"- {line}"
                    recommendations.append(line)
        
        if recommendations:
            text += '\n'.join(recommendations)
        else:
            text += "No se especificaron recomendaciones."
        
        # Notas finales
        text += "\n\n"
        text += "NOTA: Este reporte fue generado automáticamente y debe ser revisado por un profesional médico."
        text += "\n\n"
        text += f"Fecha de Generación: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        return text
    
    def save_report(self):
        """Guarda el reporte en el formato seleccionado"""
        # Obtener formato seleccionado
        report_format = self.format_combo.currentText()
        
        # Crear directorio de reportes si no existe
        os.makedirs(DEFAULT_REPORT_DIR, exist_ok=True)
        
        # Nombre base para el archivo
        base_filename = f"Reporte_Prostata_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if report_format == "PDF":
            # Verificar que ReportLab está disponible
            if not REPORTLAB_AVAILABLE:
                QMessageBox.warning(
                    self,
                    "ReportLab No Disponible",
                    "La generación de PDF requiere la biblioteca ReportLab, que no está instalada.\n"
                    "Por favor instale ReportLab o seleccione otro formato."
                )
                return
            
            # Mostrar diálogo para guardar archivo
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte PDF",
                os.path.join(DEFAULT_REPORT_DIR, base_filename + ".pdf"),
                "Archivos PDF (*.pdf)"
            )
            
            if file_path:
                try:
                    self._generate_pdf_report(file_path)
                    
                    QMessageBox.information(
                        self,
                        "Reporte Guardado",
                        f"El reporte ha sido guardado exitosamente en:\n{file_path}"
                    )
                    self.accept()  # Cerrar diálogo
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error al Guardar",
                        f"No se pudo guardar el reporte PDF:\n{str(e)}"
                    )
        
        elif report_format == "HTML":
            # Mostrar diálogo para guardar archivo
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte HTML",
                os.path.join(DEFAULT_REPORT_DIR, base_filename + ".html"),
                "Archivos HTML (*.html)"
            )
            
            if file_path:
                try:
                    self._generate_html_report(file_path)
                    
                    QMessageBox.information(
                        self,
                        "Reporte Guardado",
                        f"El reporte ha sido guardado exitosamente en:\n{file_path}"
                    )
                    self.accept()  # Cerrar diálogo
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error al Guardar",
                        f"No se pudo guardar el reporte HTML:\n{str(e)}"
                    )
        
        else:  # Texto
            # Mostrar diálogo para guardar archivo
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte de Texto",
                os.path.join(DEFAULT_REPORT_DIR, base_filename + ".txt"),
                "Archivos de Texto (*.txt)"
            )
            
            if file_path:
                try:
                    # Guardar contenido de vista previa
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.preview_edit.toPlainText())
                    
                    QMessageBox.information(
                        self,
                        "Reporte Guardado",
                        f"El reporte ha sido guardado exitosamente en:\n{file_path}"
                    )
                    self.accept()  # Cerrar diálogo
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error al Guardar",
                        f"No se pudo guardar el reporte de texto:\n{str(e)}"
                    )
    
    def _generate_pdf_report(self, file_path):
        """
        Genera un reporte en formato PDF
        
        Args:
            file_path: Ruta donde guardar el PDF
        """
        # Crear documento
        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            title=f"Reporte de Próstata - {self.patient_id_edit.text()}"
        )
        
        # Contenido del documento
        elements = []
        
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
        
        # Título principal
        elements.append(Paragraph("REPORTE DE ANÁLISIS DE PRÓSTATA", title_style))
        elements.append(Spacer(1, 12))
        
        # Información de paciente
        elements.append(Paragraph("INFORMACIÓN DEL PACIENTE", heading_style))
        
        # Tabla para información del paciente
        patient_data = [
            ["ID:", self.patient_id_edit.text()],
            ["Nombre:", self.patient_name_edit.text()],
            ["Fecha de Nacimiento:", self.patient_dob_edit.date().toString('dd/MM/yyyy')],
            ["Edad:", f"{self.patient_age_spin.value()} años"]
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
            ["Fecha:", self.study_date_edit.date().toString('dd/MM/yyyy')],
            ["Institución:", self.institution_edit.text()],
            ["Médico:", self.physician_edit.text()]
        ]
        
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
        for line in self.findings_edit.toPlainText().split('\n'):
            if line.strip():
                elements.append(Paragraph(line, normal_style))
            else:
                elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 12))
        
        # Añadir gráficos si matplotlib está disponible y hay resultados
        if MATPLOTLIB_AVAILABLE and self.prediction_results and 'lesions' in self.prediction_results:
            # Generar gráfico de barras de lesiones
            if len(self.prediction_results['lesions']) > 0:
                fig = plt.figure(figsize=(6, 4))
                ax = fig.add_subplot(111)
                
                lesion_ids = [f"Lesión {i+1}" for i in range(len(self.prediction_results['lesions']))]
                volumes = [lesion['volume_mm3'] for lesion in self.prediction_results['lesions']]
                probabilities = [lesion['probability'] * 100 for lesion in self.prediction_results['lesions']]
                
                x = np.arange(len(lesion_ids))
                width = 0.35
                
                ax.bar(x - width/2, volumes, width, label='Volumen (mm³)')
                ax.bar(x + width/2, probabilities, width, label='Probabilidad (%)')
                
                ax.set_ylabel('Valor')
                ax.set_title('Características de Lesiones')
                ax.set_xticks(x)
                ax.set_xticklabels(lesion_ids)
                ax.legend()
                
                # Guardar figura temporalmente
                chart_path = os.path.join(DEFAULT_REPORT_DIR, 'temp_chart.png')
                plt.savefig(chart_path, dpi=100, bbox_inches='tight')
                plt.close()
                
                # Añadir la imagen al PDF
                elements.append(Paragraph("Gráfico de Lesiones", heading_style))
                elements.append(Image(chart_path, width=400, height=300))
                elements.append(Spacer(1, 12))
                
                # Eliminar archivo temporal
                try:
                    os.remove(chart_path)
                except:
                    pass
        
        # Conclusiones
        elements.append(Paragraph("CONCLUSIONES", heading_style))
        for line in self.conclusion_edit.toPlainText().split('\n'):
            if line.strip():
                elements.append(Paragraph(line, normal_style))
            else:
                elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 12))
        
        # Recomendaciones
        elements.append(Paragraph("RECOMENDACIONES", heading_style))
        
        recommendations = []
        if self.follow_up_check.isChecked():
            recommendations.append("- Seguimiento en 6 meses")
        
        if self.biopsy_check.isChecked():
            recommendations.append("- Se recomienda biopsia")
        
        if self.additional_check.isChecked():
            recommendations.append("- Estudios adicionales recomendados")
        
        # Añadir recomendaciones personalizadas
        custom_rec = self.custom_recommendation_edit.toPlainText().strip()
        if custom_rec:
            for line in custom_rec.split('\n'):
                if line.strip():
                    if not line.startswith('-'):
                        line = f"- {line}"
                    recommendations.append(line)
        
        if recommendations:
            for rec in recommendations:
                elements.append(Paragraph(rec, normal_style))
        else:
            elements.append(Paragraph("No se especificaron recomendaciones.", normal_style))
        
        elements.append(Spacer(1, 24))
        
        # Nota final
        elements.append(Paragraph(
            "NOTA: Este reporte fue generado automáticamente y debe ser revisado por un profesional médico.",
            note_style
        ))
        
        # Fecha de generación
        elements.append(Paragraph(
            f"Fecha de Generación: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
            note_style
        ))
        
        # Construir el documento
        doc.build(elements)
    
    def _generate_html_report(self, file_path):
        """
        Genera un reporte en formato HTML
        
        Args:
            file_path: Ruta donde guardar el HTML
        """
        # HTML base
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Próstata - {self.patient_id_edit.text()}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #004080; }}
        h2 {{ color: #004080; margin-top: 20px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; color: #004080; }}
        .note {{ color: #888; font-size: 0.8em; font-style: italic; }}
    </style>
</head>
<body>
    <h1>REPORTE DE ANÁLISIS DE PRÓSTATA</h1>
    
    <h2>INFORMACIÓN DEL PACIENTE</h2>
    <table>
        <tr><th>ID:</th><td>{self.patient_id_edit.text()}</td></tr>
        <tr><th>Nombre:</th><td>{self.patient_name_edit.text()}</td></tr>
        <tr><th>Fecha de Nacimiento:</th><td>{self.patient_dob_edit.date().toString('dd/MM/yyyy')}</td></tr>
        <tr><th>Edad:</th><td>{self.patient_age_spin.value()} años</td></tr>
    </table>
    
    <h2>INFORMACIÓN DEL ESTUDIO</h2>
    <table>
        <tr><th>Fecha:</th><td>{self.study_date_edit.date().toString('dd/MM/yyyy')}</td></tr>
        <tr><th>Institución:</th><td>{self.institution_edit.text()}</td></tr>
        <tr><th>Médico:</th><td>{self.physician_edit.text()}</td></tr>
    </table>
    
    <h2>HALLAZGOS</h2>
    <div>
        {self.findings_edit.toPlainText().replace('\n', '<br>')}
    </div>
    
    <h2>CONCLUSIONES</h2>
    <div>
        {self.conclusion_edit.toPlainText().replace('\n', '<br>')}
    </div>
    
    <h2>RECOMENDACIONES</h2>
    <ul>
"""
        
        # Añadir recomendaciones
        if self.follow_up_check.isChecked():
            html += "        <li>Seguimiento en 6 meses</li>\n"
        
        if self.biopsy_check.isChecked():
            html += "        <li>Se recomienda biopsia</li>\n"
        
        if self.additional_check.isChecked():
            html += "        <li>Estudios adicionales recomendados</li>\n"
        
        # Añadir recomendaciones personalizadas
        custom_rec = self.custom_recommendation_edit.toPlainText().strip()
        if custom_rec:
            for line in custom_rec.split('\n'):
                if line.strip():
                    html += f"        <li>{line.strip().lstrip('-').strip()}</li>\n"
        
        # Finalizar HTML
        html += f"""    </ul>
    
    <p class="note">NOTA: Este reporte fue generado automáticamente y debe ser revisado por un profesional médico.</p>
    <p class="note">Fecha de Generación: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</body>
</html>
"""
        
        # Guardar archivo
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)