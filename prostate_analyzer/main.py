#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Analizador de Imágenes de Próstata - Visualizador 3D y Predicción
-----------------------------------------------------------------
Este programa permite visualizar imágenes médicas de próstata,
realizar predicciones automáticas de lesiones, y generar reportes.
"""

import sys
import os
import traceback
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QIcon

# Importar componentes principales de la aplicación
from app.main_window import MainWindow
from app.utils.image_loader import check_dependencies
from config import APP_NAME, APP_VERSION, SPLASH_DURATION

def exception_hook(exc_type, exc_value, exc_traceback):
    """Manejador global de excepciones para capturar errores no controlados"""
    print("Excepción no controlada:", exc_type, exc_value)
    print("Traceback:")
    traceback.print_tb(exc_traceback)
    
    # Mostrar diálogo de error si ya existe la aplicación
    if 'app' in globals():
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(f"Ha ocurrido un error inesperado: {str(exc_value)}")
        msg_box.setDetailedText("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        msg_box.exec_()
    
    # Llamar al manejador original
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

def main():
    """Función principal que inicia la aplicación"""
    # Reemplazar el manejador de excepciones para captura global
    sys.excepthook = exception_hook
    
    # Crear aplicación Qt
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # Establecer estilo Fusion (más moderno y consistente entre plataformas)
    app.setStyle("Fusion")
    
    # Cargar y aplicar hoja de estilos para tema oscuro
    try:
        style_path = os.path.join(os.path.dirname(__file__), "resources/styles/dark_theme.qss")
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Error al cargar la hoja de estilos: {e}")
    
    # Crear y mostrar pantalla de carga
    try:
        splash_path = os.path.join(os.path.dirname(__file__), "resources/images/splash.png")
        if os.path.exists(splash_path):
            splash_pixmap = QPixmap(splash_path)
            splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
            splash.show()
            splash.showMessage(f"{APP_NAME} v{APP_VERSION} - Cargando...", 
                              Qt.AlignBottom | Qt.AlignCenter, Qt.white)
            app.processEvents()
        else:
            splash = None
    except Exception as e:
        print(f"Error al mostrar splash screen: {e}")
        splash = None
    
    # Verificar dependencias
    dependencies_ok, missing_deps = check_dependencies()
    if not dependencies_ok:
        error_msg = "No se pudieron cargar las siguientes dependencias críticas:\n"
        error_msg += "\n".join([f"- {dep}" for dep in missing_deps])
        error_msg += "\n\nAlgunas funcionalidades pueden no estar disponibles."
        
        if splash:
            splash.showMessage(error_msg, Qt.AlignBottom | Qt.AlignLeft, Qt.red)
            app.processEvents()
            QTimer.singleShot(3000, lambda: _show_error_and_continue(error_msg, splash))
        else:
            QMessageBox.warning(None, "Dependencias faltantes", error_msg)
    
    # Crear y mostrar la ventana principal después de un breve retraso
    def show_main_window():
        window = MainWindow()
        window.show()
        if splash:
            splash.finish(window)
    
    # Usar un temporizador para mostrar la ventana principal después de la pantalla de carga
    QTimer.singleShot(SPLASH_DURATION if splash else 0, show_main_window)
    
    # Ejecutar el bucle principal de la aplicación
    return app.exec_()

def _show_error_and_continue(error_msg, splash):
    """Muestra un error pero permite que la aplicación continúe"""
    if splash:
        splash.hide()
    QMessageBox.warning(None, "Dependencias faltantes", error_msg)
    if splash:
        splash.show()

if __name__ == "__main__":
    sys.exit(main())