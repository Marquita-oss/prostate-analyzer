#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ventana principal de la aplicación de análisis de próstata
"""

import os
import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QAction, QMenu, QToolBar, 
                            QStatusBar, QFileDialog, QMessageBox, QSplitter,
                            QTabWidget, QDockWidget, QProgressDialog)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QIcon, QPixmap

from config import (APP_NAME, APP_VERSION, DEFAULT_WINDOW_WIDTH, 
                   DEFAULT_WINDOW_HEIGHT, ICONS_DIR, SUPPORTED_FORMATS)

# Importar vistas principales
from app.views.viewer_widget import ViewerWidget
from app.views.case_panel import CasePanel
from app.views.report_dialog import ReportDialog

# Importar controladores
from app.controllers.case_manager import CaseManager
from app.controllers.prediction_controller import PredictionController

class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación que contiene todos los 
    componentes de la interfaz de usuario.
    """
    
    # Señales
    status_message = pyqtSignal(str, int)  # Mensaje, duración en ms
    
    def __init__(self):
        super(MainWindow, self).__init__()
        
        # Inicializar componentes internos
        self.case_manager = CaseManager(self)
        self.prediction_controller = PredictionController(self)
        self.settings = QSettings(APP_NAME, "settings")
        
        # Configurar la ventana
        self.setup_window()
        
        # Crear componentes UI
        self.setup_ui()
        
        # Configurar menús y barras de herramientas
        self.setup_menus()
        self.setup_toolbar()
        
        # Restaurar configuración guardada
        self.restore_settings()
        
        # Conexiones de señales
        self.setup_connections()
        
        # Mensaje inicial en la barra de estado
        self.statusBar().showMessage(f"{APP_NAME} v{APP_VERSION} - Listo")
    
    def setup_window(self):
        """Configura propiedades básicas de la ventana"""
        self.setWindowTitle(APP_NAME)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        
        # Intentar cargar icono de la aplicación
        icon_path = os.path.join(ICONS_DIR, "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Establecer barra de estado
        self.setStatusBar(QStatusBar())
    
    def setup_ui(self):
        """Crea y organiza los widgets principales de la UI"""
        # Widget central principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Splitter principal que divide panel de casos y visualizador
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Panel de casos (lado izquierdo)
        self.case_panel = CasePanel(self.case_manager)
        self.main_splitter.addWidget(self.case_panel)
        
        # Widget de visualización (lado derecho)
        self.viewer_widget = ViewerWidget()
        self.main_splitter.addWidget(self.viewer_widget)
        
        # Establecer proporciones iniciales del splitter (20% casos, 80% visualizador)
        self.main_splitter.setSizes([int(DEFAULT_WINDOW_WIDTH * 0.2), 
                                    int(DEFAULT_WINDOW_WIDTH * 0.8)])
        
        # Panel de información (dock inferior)
        self.info_dock = QDockWidget("Información", self)
        self.info_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.info_dock.setFeatures(QDockWidget.DockWidgetClosable | 
                                  QDockWidget.DockWidgetFloatable)
        
        # Crear widget para la información
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # Agregar contenido al panel de información
        self.info_label = QLabel("No hay caso cargado")
        self.info_label.setObjectName("infoLabel")
        info_layout.addWidget(self.info_label)
        
        # Botones para predicción y reporte
        button_layout = QHBoxLayout()
        
        self.predict_button = QPushButton("Realizar Predicción")
        self.predict_button.setObjectName("predictButton")
        self.predict_button.setEnabled(False)
        self.predict_button.setIcon(QIcon(os.path.join(ICONS_DIR, "predict_icon.png")))
        self.predict_button.clicked.connect(self.on_predict_clicked)
        button_layout.addWidget(self.predict_button)
        
        # Botón para informe
        self.report_button = QPushButton("Generar Reporte")
        self.report_button.setObjectName("reportButton")
        self.report_button.setEnabled(False)
        self.report_button.setIcon(QIcon(os.path.join(ICONS_DIR, "report_icon.png")))
        self.report_button.clicked.connect(self.on_report_clicked)
        button_layout.addWidget(self.report_button)
        
        info_layout.addLayout(button_layout)
        
        # Asignar el widget al dock y añadirlo a la ventana principal
        self.info_dock.setWidget(info_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.info_dock)
        
    def setup_menus(self):
        """Configura la barra de menú y submenús"""
        # Menú Archivo
        file_menu = self.menuBar().addMenu("&Archivo")
        
        # Acción para abrir caso
        open_action = QAction("&Abrir Caso...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip("Abrir un nuevo caso")
        open_action.triggered.connect(self.on_open_case)
        file_menu.addAction(open_action)
        
        # Acción para cerrar caso actual
        close_action = QAction("&Cerrar Caso", self)
        close_action.setShortcut("Ctrl+W")
        close_action.setStatusTip("Cerrar el caso actual")
        close_action.setEnabled(False)
        close_action.triggered.connect(self.on_close_case)
        file_menu.addAction(close_action)
        self.close_case_action = close_action  # Guardar referencia para habilitar/deshabilitar
        
        file_menu.addSeparator()
        
        # Acción para salir
        exit_action = QAction("&Salir", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.setStatusTip("Salir de la aplicación")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menú Ver
        view_menu = self.menuBar().addMenu("&Ver")
        
        # Acción para alternar panel de casos
        toggle_case_panel_action = QAction("Panel de &Casos", self)
        toggle_case_panel_action.setCheckable(True)
        toggle_case_panel_action.setChecked(True)
        toggle_case_panel_action.triggered.connect(self.toggle_case_panel)
        view_menu.addAction(toggle_case_panel_action)
        
        # Acción para alternar panel de información
        toggle_info_panel_action = QAction("Panel de &Información", self)
        toggle_info_panel_action.setCheckable(True)
        toggle_info_panel_action.setChecked(True)
        toggle_info_panel_action.triggered.connect(self.toggle_info_panel)
        view_menu.addAction(toggle_info_panel_action)
        
        view_menu.addSeparator()
        
        # Acción para activar modo VRT (Volume Rendering)
        vrt_action = QAction("Activar Renderizado 3D", self)
        vrt_action.setCheckable(True)
        vrt_action.setStatusTip("Activar visualización 3D volumétrica")
        vrt_action.triggered.connect(self.toggle_vrt_mode)
        view_menu.addAction(vrt_action)
        self.vrt_action = vrt_action  # Guardar referencia
        
        # Menú Herramientas
        tools_menu = self.menuBar().addMenu("&Herramientas")
        
        # Acción para realizar predicción
        predict_action = QAction("&Realizar Predicción", self)
        predict_action.setStatusTip("Detectar lesiones usando inteligencia artificial")
        predict_action.setEnabled(False)
        predict_action.triggered.connect(self.on_predict_clicked)
        tools_menu.addAction(predict_action)
        self.predict_action = predict_action  # Guardar referencia
        
        # Acción para generar reporte
        report_action = QAction("Generar &Reporte", self)
        report_action.setStatusTip("Crear un informe con los resultados")
        report_action.setEnabled(False)
        report_action.triggered.connect(self.on_report_clicked)
        tools_menu.addAction(report_action)
        self.report_action = report_action  # Guardar referencia
        
        # Menú Ayuda
        help_menu = self.menuBar().addMenu("A&yuda")
        
        # Acción para mostrar acerca de
        about_action = QAction("&Acerca de", self)
        about_action.setStatusTip("Mostrar información sobre la aplicación")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
    def setup_toolbar(self):
        """Configura la barra de herramientas principal"""
        # Crear barra de herramientas principal
        self.toolbar = QToolBar("Barra Principal")
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        
        # Botón para abrir caso
        open_button = QAction(QIcon(os.path.join(ICONS_DIR, "open_icon.png")), "Abrir Caso", self)
        open_button.triggered.connect(self.on_open_case)
        self.toolbar.addAction(open_button)
        
        self.toolbar.addSeparator()
        
        # Botones para control de visualización
        axial_button = QAction(QIcon(os.path.join(ICONS_DIR, "axial_icon.png")), "Vista Axial", self)
        axial_button.setCheckable(True)
        axial_button.setChecked(True)
        axial_button.triggered.connect(lambda: self.viewer_widget.set_view_mode("axial"))
        self.toolbar.addAction(axial_button)
        
        sagittal_button = QAction(QIcon(os.path.join(ICONS_DIR, "sagittal_icon.png")), "Vista Sagital", self)
        sagittal_button.setCheckable(True)
        sagittal_button.triggered.connect(lambda: self.viewer_widget.set_view_mode("sagittal"))
        self.toolbar.addAction(sagittal_button)
        
        coronal_button = QAction(QIcon(os.path.join(ICONS_DIR, "coronal_icon.png")), "Vista Coronal", self)
        coronal_button.setCheckable(True)
        coronal_button.triggered.connect(lambda: self.viewer_widget.set_view_mode("coronal"))
        self.toolbar.addAction(coronal_button)
        
        # Agrupar botones de vista para comportamiento de radio button
        self.view_buttons = [axial_button, sagittal_button, coronal_button]
        for button in self.view_buttons:
            button.triggered.connect(self.update_view_buttons)
        
        self.toolbar.addSeparator()
        
        # Botón para activar visualización 3D
        vrt_button = QAction(QIcon(os.path.join(ICONS_DIR, "3d_icon.png")), "Visualización 3D", self)
        vrt_button.setCheckable(True)
        vrt_button.triggered.connect(self.toggle_vrt_mode)
        self.toolbar.addAction(vrt_button)
        self.vrt_button = vrt_button  # Guardar referencia
        
        self.toolbar.addSeparator()
        
        # Botón para realizar predicción
        predict_button = QAction(QIcon(os.path.join(ICONS_DIR, "predict_icon.png")), "Realizar Predicción", self)
        predict_button.setEnabled(False)
        predict_button.triggered.connect(self.on_predict_clicked)
        self.toolbar.addAction(predict_button)
        self.predict_toolbar_action = predict_button  # Guardar referencia
        
        # Botón para generar reporte
        report_button = QAction(QIcon(os.path.join(ICONS_DIR, "report_icon.png")), "Generar Reporte", self)
        report_button.setEnabled(False)
        report_button.triggered.connect(self.on_report_clicked)
        self.toolbar.addAction(report_button)
        self.report_toolbar_action = report_button  # Guardar referencia
        
    def setup_connections(self):
        """Configura las conexiones de señales entre componentes"""
        # Conectar señales del administrador de casos
        self.case_manager.case_loaded.connect(self.on_case_loaded)
        self.case_manager.case_closed.connect(self.on_case_closed)
        
        # Conectar señales del visualizador
        self.viewer_widget.view_changed.connect(self.update_status_info)
        
        # Conectar señales del controlador de predicción
        self.prediction_controller.prediction_started.connect(self.on_prediction_started)
        self.prediction_controller.prediction_completed.connect(self.on_prediction_completed)
        self.prediction_controller.prediction_failed.connect(self.on_prediction_failed)
        
        # Conectar señal propia para mensajes de estado
        self.status_message.connect(self.show_timed_status_message)
        
    def restore_settings(self):
        """Restaura configuración guardada de sesiones anteriores"""
        # Restaurar geometría de la ventana
        if self.settings.contains("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        
        # Restaurar estado de la ventana
        if self.settings.contains("windowState"):
            self.restoreState(self.settings.value("windowState"))
        
        # Restaurar estado del splitter principal
        if self.settings.contains("splitterSizes"):
            # Obtener valores como lista y convertir cada elemento a entero
            sizes_raw = self.settings.value("splitterSizes")
            if isinstance(sizes_raw, (list, tuple)):
                # Convertir cada elemento a entero
                sizes = [int(size) if isinstance(size, str) else size for size in sizes_raw]
                self.main_splitter.setSizes(sizes)
            else:
                # Si no es una lista, usar valores predeterminados
                default_width = self.width()
                self.main_splitter.setSizes([int(default_width * 0.2), int(default_width * 0.8)])
    
    def save_settings(self):
        """Guarda configuración actual para futuras sesiones"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("splitterSizes", self.main_splitter.sizes())
    
    def closeEvent(self, event):
        """Manejador del evento de cierre de la ventana"""
        # Guardar configuración antes de cerrar
        self.save_settings()
        
        # Cerrar casos pendientes
        if self.case_manager.has_open_cases():
            reply = QMessageBox.question(
                self,
                "Confirmar Salida",
                "Hay casos abiertos. ¿Desea cerrarlos y salir?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Cerrar todos los casos
                self.case_manager.close_all_cases()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    # Manejadores de eventos
    def on_open_case(self):
        """Manejador para abrir un nuevo caso"""
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
                self.status_message.emit("Caso cargado correctamente", 3000)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error al Cargar Caso",
                    f"No se pudo cargar el caso: {str(e)}"
                )
    
    def on_close_case(self):
        """Manejador para cerrar el caso actual"""
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
        
        # Cerrar el caso actual
        self.case_manager.close_current_case()
        self.status_message.emit("Caso cerrado", 3000)
    
    def on_case_loaded(self, case_data):
        """Manejador cuando un caso es cargado correctamente"""
        # Actualizar UI para reflejar que hay un caso cargado
        self.close_case_action.setEnabled(True)
        self.predict_action.setEnabled(True)
        self.predict_toolbar_action.setEnabled(True)
        self.predict_button.setEnabled(True)
        
        # Actualizar la información mostrada
        self.update_case_info(case_data)
        
        # Pasar los datos al visualizador
        self.viewer_widget.load_case_data(case_data)
    
    def on_case_closed(self):
        """Manejador cuando un caso es cerrado"""
        # Actualizar UI
        self.close_case_action.setEnabled(False)
        self.predict_action.setEnabled(False)
        self.predict_toolbar_action.setEnabled(False)
        self.predict_button.setEnabled(False)
        self.report_action.setEnabled(False)
        self.report_toolbar_action.setEnabled(False)
        self.report_button.setEnabled(False)
        
        # Limpiar visualizador
        self.viewer_widget.clear()
        
        # Limpiar información
        self.info_label.setText("No hay caso cargado")
    
    def on_predict_clicked(self):
        """Manejador para iniciar predicción"""
        # Verificar que hay un caso cargado
        if not self.case_manager.has_open_cases():
            QMessageBox.warning(
                self,
                "Sin Caso Activo",
                "No hay ningún caso cargado para realizar predicción."
            )
            return
        
        # Iniciar predicción
        try:
            self.prediction_controller.start_prediction(self.case_manager.get_current_case())
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al Iniciar Predicción",
                f"No se pudo iniciar la predicción: {str(e)}"
            )
    
    def on_prediction_started(self):
        """Manejador cuando comienza el proceso de predicción"""
        # Deshabilitar botones durante la predicción
        self.predict_action.setEnabled(False)
        self.predict_toolbar_action.setEnabled(False)
        self.predict_button.setEnabled(False)
        
        # Mostrar mensaje
        self.status_message.emit("Predicción en progreso...", 0)  # 0 para que no desaparezca
    
    def on_prediction_completed(self, prediction_results):
        """Manejador cuando la predicción finaliza correctamente"""
        # Volver a habilitar botones
        self.predict_action.setEnabled(True)
        self.predict_toolbar_action.setEnabled(True)
        self.predict_button.setEnabled(True)
        
        # Habilitar reporte ahora que hay resultados
        self.report_action.setEnabled(True)
        self.report_toolbar_action.setEnabled(True)
        self.report_button.setEnabled(True)
        
        # Actualizar visualizador con resultados
        self.viewer_widget.show_prediction_results(prediction_results)
        
        # Mostrar mensaje
        self.status_message.emit("Predicción completada correctamente", 3000)
    
    def on_prediction_failed(self, error_message):
        """Manejador cuando la predicción falla"""
        # Volver a habilitar botones
        self.predict_action.setEnabled(True)
        self.predict_toolbar_action.setEnabled(True)
        self.predict_button.setEnabled(True)
        
        # Mostrar mensaje de error
        QMessageBox.critical(
            self,
            "Error en Predicción",
            f"La predicción falló: {error_message}"
        )
        
        self.status_message.emit("Predicción fallida", 3000)
    
    def on_report_clicked(self):
        """Manejador para generar reporte"""
        # Verificar que hay resultados de predicción
        if not self.prediction_controller.has_results():
            QMessageBox.warning(
                self,
                "Sin Resultados",
                "No hay resultados de predicción para generar un reporte."
            )
            return
        
        # Abrir diálogo de reporte
        dialog = ReportDialog(
            self.case_manager.get_current_case(),
            self.prediction_controller.get_results(),
            self
        )
        dialog.exec_()
    
    def update_case_info(self, case_data):
        """Actualiza la información mostrada sobre el caso actual"""
        # Crear texto informativo sobre el caso
        info_text = f"<b>Caso:</b> {case_data.get('name', 'Sin nombre')}<br>"
        info_text += f"<b>Archivos:</b> {len(case_data.get('files', []))} secuencias<br>"
        
        if 'metadata' in case_data:
            metadata = case_data['metadata']
            if 'patient_id' in metadata:
                info_text += f"<b>ID Paciente:</b> {metadata['patient_id']}<br>"
            if 'study_date' in metadata:
                info_text += f"<b>Fecha Estudio:</b> {metadata['study_date']}<br>"
        
        self.info_label.setText(info_text)
    
    def update_status_info(self, view_info):
        """Actualiza información en la barra de estado según la vista actual"""
        if view_info:
            view_type = view_info.get('type', 'desconocida')
            position = view_info.get('position', (0, 0, 0))
            value = view_info.get('value', 0)
            
            status_text = f"Vista: {view_type.capitalize()} | "
            status_text += f"Posición: ({position[0]:.1f}, {position[1]:.1f}, {position[2]:.1f}) | "
            status_text += f"Valor: {value:.2f}"
            
            self.statusBar().showMessage(status_text)
    
    def show_timed_status_message(self, message, duration):
        """Muestra un mensaje en la barra de estado por un tiempo determinado"""
        self.statusBar().showMessage(message)
        
        # Si la duración es mayor que cero, programar borrado automático
        if duration > 0:
            QTimer.singleShot(duration, lambda: self.statusBar().showMessage(""))
    
    def update_view_buttons(self):
        """Actualiza el estado de los botones de vista para comportamiento de radio button"""
        sender = self.sender()
        for button in self.view_buttons:
            if button is not sender:
                button.setChecked(False)
    
    def toggle_case_panel(self, visible):
        """Muestra u oculta el panel de casos"""
        if visible:
            self.case_panel.show()
        else:
            self.case_panel.hide()
    
    def toggle_info_panel(self, visible):
        """Muestra u oculta el panel de información"""
        if visible:
            self.info_dock.show()
        else:
            self.info_dock.hide()
    
    def toggle_vrt_mode(self, enabled):
        """Activa o desactiva el modo de renderizado volumétrico 3D"""
        # Asegurar que VRT action y button estén sincronizados
        self.vrt_action.setChecked(enabled)
        self.vrt_button.setChecked(enabled)
        
        # Activar/desactivar modo VRT en el visualizador
        self.viewer_widget.set_vrt_mode(enabled)
        
        # Actualizar mensaje de estado
        mode_str = "activado" if enabled else "desactivado"
        self.status_message.emit(f"Modo de renderizado 3D {mode_str}", 3000)
    
    def show_about_dialog(self):
        """Muestra diálogo con información sobre la aplicación"""
        about_text = f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
        about_text += "<p>Aplicación para análisis de imágenes de próstata con IA</p>"
        about_text += "<p>Desarrollada para proyecto de investigación académica</p>"
        about_text += "<p>&copy; 2025 Medical Research Labs</p>"
        
        QMessageBox.about(self, "Acerca de " + APP_NAME, about_text)