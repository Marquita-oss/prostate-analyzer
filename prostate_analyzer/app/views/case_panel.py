#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Panel para gestión de casos de la aplicación de análisis de próstata
Muestra la lista de casos cargados y permite interactuar con ellos
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget, 
                             QListWidgetItem, QPushButton, QHBoxLayout,
                             QMenu, QAction, QFileDialog, QMessageBox,
                             QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QColor

from config import ICONS_DIR, SUPPORTED_FORMATS

class CasePanel(QWidget):
    """
    Panel para gestión y visualización de casos
    """
    
    def __init__(self, case_manager, parent=None):
        super(CasePanel, self).__init__(parent)
        
        # Referencia al gestor de casos
        self.case_manager = case_manager
        
        # Configurar interfaz
        self.setup_ui()
        
        # Conectar señales del gestor de casos
        self.case_manager.case_loaded.connect(self.on_case_loaded)
        self.case_manager.case_closed.connect(self.on_case_closed)
    
    def setup_ui(self):
        """Configura la interfaz del panel de casos"""
        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # Título del panel
        title_label = QLabel("Casos")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # Botones para acciones de casos
        buttons_layout = QHBoxLayout()
        
        # Botón para abrir caso
        self.open_button = QPushButton("Abrir")
        self.open_button.setIcon(QIcon(os.path.join(ICONS_DIR, "open_icon.png")))
        self.open_button.clicked.connect(self.on_open_clicked)
        buttons_layout.addWidget(self.open_button)
        
        # Botón para cerrar caso
        self.close_button = QPushButton("Cerrar")
        self.close_button.setIcon(QIcon(os.path.join(ICONS_DIR, "close_icon.png")))
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.on_close_clicked)
        buttons_layout.addWidget(self.close_button)
        
        main_layout.addLayout(buttons_layout)
        
        # Lista de casos
        self.case_list = QListWidget()
        self.case_list.setAlternatingRowColors(True)
        self.case_list.itemClicked.connect(self.on_case_selected)
        self.case_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.case_list.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addWidget(self.case_list)
        
        # Panel de información del caso
        info_group = QGroupBox("Información")
        info_layout = QFormLayout(info_group)
        
        self.case_name_label = QLabel("No hay caso seleccionado")
        info_layout.addRow("Nombre:", self.case_name_label)
        
        self.case_date_label = QLabel("")
        info_layout.addRow("Fecha:", self.case_date_label)
        
        self.case_sequences_label = QLabel("")
        info_layout.addRow("Secuencias:", self.case_sequences_label)
        
        self.case_patient_label = QLabel("")
        info_layout.addRow("ID Paciente:", self.case_patient_label)
        
        main_layout.addWidget(info_group)
        
        # Establecer tamaños mínimos
        self.setMinimumWidth(250)
    
    def update_case_list(self):
        """Actualiza la lista de casos mostrados"""
        # Limpiar lista
        self.case_list.clear()
        
        # Obtener casos del gestor
        for i in range(self.case_manager.get_case_count()):
            case = self.case_manager.cases[i]
            
            # Crear item para la lista
            item = QListWidgetItem(case['name'])
            
            # Destacar caso actual
            if i == self.case_manager.current_case_index:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setBackground(QColor(53, 53, 53))  # Fondo ligeramente más claro
            
            # Añadir metadatos
            item.setData(Qt.UserRole, case)
            
            # Añadir a la lista
            self.case_list.addItem(item)
    
    def update_case_info(self, case=None):
        """
        Actualiza la información mostrada del caso
        
        Args:
            case: Caso a mostrar, o None para limpiar información
        """
        if case:
            # Actualizar etiquetas
            self.case_name_label.setText(case['name'])
            
            # Fecha
            if 'created_date' in case:
                # Formatear fecha para mostrar solo fecha, no hora
                date_str = case['created_date'].split('T')[0]
                self.case_date_label.setText(date_str)
            else:
                self.case_date_label.setText("Desconocida")
            
            # Secuencias
            if 'files' in case:
                sequences = set()
                for file_info in case['files']:
                    if 'sequence_type' in file_info:
                        sequences.add(file_info['sequence_type'].upper())
                
                self.case_sequences_label.setText(", ".join(sorted(sequences)))
            else:
                self.case_sequences_label.setText("Ninguna")
            
            # ID de paciente
            if 'metadata' in case and 'patient_id' in case['metadata']:
                self.case_patient_label.setText(case['metadata']['patient_id'])
            else:
                self.case_patient_label.setText("Desconocido")
        else:
            # Limpiar etiquetas
            self.case_name_label.setText("No hay caso seleccionado")
            self.case_date_label.setText("")
            self.case_sequences_label.setText("")
            self.case_patient_label.setText("")
    
    def on_open_clicked(self):
        """Manejador para el botón de abrir caso"""
        # Filtro para formatos soportados
        file_filter = "Archivos de Imagen Médica ("
        file_filter += " ".join(["*" + ext for ext in SUPPORTED_FORMATS])
        file_filter += ");;Todos los archivos (*)"
        
        # Mostrar diálogo para seleccionar archivos
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Abrir Archivos de Caso",
            "",
            file_filter
        )
        
        if file_paths:
            # Intentar cargar los archivos seleccionados
            try:
                self.case_manager.load_case(file_paths)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error al Cargar Caso",
                    f"No se pudo cargar el caso: {str(e)}"
                )
    
    def on_close_clicked(self):
        """Manejador para el botón de cerrar caso"""
        # Verificar que hay un caso actual
        if not self.case_manager.has_open_cases() or self.case_manager.current_case_index < 0:
            return
        
        # Preguntar confirmación si hay cambios sin guardar
        if self.case_manager.current_case_has_changes():
            reply = QMessageBox.question(
                self,
                "Confirmar Cierre",
                "Hay cambios sin guardar. ¿Desea cerrar el caso?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        # Cerrar caso
        self.case_manager.close_current_case()
    
    def on_case_selected(self, item):
        """
        Manejador cuando se selecciona un caso de la lista
        
        Args:
            item: Item seleccionado
        """
        # Obtener caso asociado al item
        case = item.data(Qt.UserRole)
        
        # Actualizar información
        self.update_case_info(case)
    
    def on_case_loaded(self, case_data):
        """
        Manejador cuando se carga un nuevo caso
        
        Args:
            case_data: Datos del caso cargado
        """
        # Actualizar lista
        self.update_case_list()
        
        # Actualizar información
        self.update_case_info(case_data)
        
        # Habilitar botón de cerrar
        self.close_button.setEnabled(True)
    
    def on_case_closed(self):
        """Manejador cuando se cierra un caso"""
        # Actualizar lista
        self.update_case_list()
        
        # Actualizar información con caso actual
        current_case = self.case_manager.get_current_case()
        self.update_case_info(current_case)
        
        # Deshabilitar botón de cerrar si no hay casos
        self.close_button.setEnabled(self.case_manager.has_open_cases())
    
    def show_context_menu(self, position):
        """
        Muestra el menú contextual para la lista de casos
        
        Args:
            position: Posición donde se solicitó el menú
        """
        # Verificar que hay un elemento seleccionado
        item = self.case_list.itemAt(position)
        if not item:
            return
        
        # Crear menú
        context_menu = QMenu(self)
        
        # Acciones
        view_action = QAction("Ver", self)
        view_action.triggered.connect(lambda: self.on_case_selected(item))
        context_menu.addAction(view_action)
        
        close_action = QAction("Cerrar", self)
        close_action.triggered.connect(self.on_close_clicked)
        context_menu.addAction(close_action)
        
        # Mostrar menú
        context_menu.exec_(self.case_list.mapToGlobal(position))