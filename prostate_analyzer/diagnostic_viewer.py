#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Herramienta de diagnóstico para visualizar imágenes médicas
Esta utilidad independiente ayuda a verificar si hay problemas con la carga o visualización
"""

import sys
import os
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLabel, QPushButton, QFileDialog,
                           QComboBox, QSlider, QCheckBox, QTextEdit)
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Intentar importar las bibliotecas de procesamiento de imágenes médicas
try:
    import SimpleITK as sitk
    HAS_SITK = True
except ImportError:
    HAS_SITK = False

try:
    import nibabel as nib
    HAS_NIB = True
except ImportError:
    HAS_NIB = False

try:
    import vtk
    from vtk.util import numpy_support
    HAS_VTK = True
except ImportError:
    HAS_VTK = False

class DiagnosticViewer(QMainWindow):
    """Ventana de diagnóstico para verificar problemas de visualización"""
    
    def __init__(self):
        super().__init__()
        
        self.image_data = None  # Datos de imagen como array NumPy
        self.image_path = None  # Ruta al archivo de imagen
        self.current_slice = 0   # Slice actual para visualización
        
        self.setWindowTitle("Diagnóstico de Visualización")
        self.setGeometry(100, 100, 800, 600)
        
        self.setup_ui()
        self.check_dependencies()
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Panel de control superior
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # Botón para cargar imagen
        self.load_button = QPushButton("Cargar Imagen")
        self.load_button.clicked.connect(self.load_image)
        control_layout.addWidget(self.load_button)
        
        # Selector de biblioteca
        self.lib_combo = QComboBox()
        self.lib_combo.addItems(["Auto", "SimpleITK", "Nibabel", "VTK"])
        control_layout.addWidget(QLabel("Biblioteca:"))
        control_layout.addWidget(self.lib_combo)
        
        main_layout.addWidget(control_panel)
        
        # Área de visualización (matplotlib)
        self.figure = plt.figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)
        
        # Panel de control inferior
        bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(bottom_panel)
        
        # Slider para navegar por slices
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.setEnabled(False)
        self.slice_slider.valueChanged.connect(self.update_slice)
        
        bottom_layout.addWidget(QLabel("Slice:"))
        bottom_layout.addWidget(self.slice_slider)
        
        self.slice_label = QLabel("0/0")
        bottom_layout.addWidget(self.slice_label)
        
        main_layout.addWidget(bottom_panel)
        
        # Área de log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        main_layout.addWidget(self.log_text)
    
    def check_dependencies(self):
        import matplotlib
        """Verificar y mostrar dependencias disponibles"""
        self.log("=== Diagnóstico de Dependencias ===")
        self.log(f"SimpleITK: {'Disponible' if HAS_SITK else 'No disponible'}")
        self.log(f"Nibabel: {'Disponible' if HAS_NIB else 'No disponible'}")
        self.log(f"VTK: {'Disponible' if HAS_VTK else 'No disponible'}")
        self.log(f"NumPy: {np.__version__}")
        self.log(f"Matplotlib: {matplotlib.__version__}")
        self.log("===================================")
    
    def log(self, message):
        """Añadir mensaje al área de log"""
        self.log_text.append(message)
    
    def load_image(self):
        """Cargar imagen médica"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Abrir Archivo de Imagen Médica", 
            "", 
            "Archivos de Imagen (*.nii *.nii.gz *.mha *.dcm)"
        )
        
        if not file_path:
            return
        
        self.image_path = file_path
        self.log(f"Cargando imagen: {file_path}")
        
        # Determinar qué biblioteca usar
        method = self.lib_combo.currentText()
        
        if method == "Auto" or method == "SimpleITK" and HAS_SITK:
            self.load_with_sitk(file_path)
        elif method == "Nibabel" and HAS_NIB:
            self.load_with_nibabel(file_path)
        elif method == "VTK" and HAS_VTK:
            self.load_with_vtk(file_path)
        else:
            # Si falla método específico o Auto, intentar todos disponibles
            if HAS_SITK:
                if self.load_with_sitk(file_path):
                    return
            if HAS_NIB:
                if self.load_with_nibabel(file_path):
                    return
            if HAS_VTK:
                if self.load_with_vtk(file_path):
                    return
            
            self.log("ERROR: No se pudo cargar la imagen con ninguna biblioteca")
    
    def load_with_sitk(self, file_path):
        """Cargar imagen con SimpleITK"""
        try:
            if not HAS_SITK:
                self.log("SimpleITK no está disponible")
                return False
                
            self.log("Intentando cargar con SimpleITK...")
            
            # Cargar imagen
            image = sitk.ReadImage(file_path)
            
            # Convertir a array numpy
            array = sitk.GetArrayFromImage(image)
            
            # Configurar visualización
            self.image_data = array
            
            # Extraer metadatos
            size = image.GetSize()
            spacing = image.GetSpacing()
            
            self.log(f"Imagen cargada con SimpleITK")
            self.log(f"Dimensiones: {array.shape}")
            self.log(f"Tipo de datos: {array.dtype}")
            self.log(f"Tamaño (ancho, alto, profundidad): {size}")
            self.log(f"Espaciado (mm): {spacing}")
            
            # Configurar slider
            if len(array.shape) > 2:  # 3D
                self.slice_slider.setMaximum(array.shape[0] - 1)
                self.slice_slider.setValue(array.shape[0] // 2)
                self.slice_slider.setEnabled(True)
                self.current_slice = array.shape[0] // 2
            else:  # 2D
                self.slice_slider.setEnabled(False)
            
            self.update_display()
            return True
            
        except Exception as e:
            self.log(f"Error cargando con SimpleITK: {str(e)}")
            return False
    
    def load_with_nibabel(self, file_path):
        """Cargar imagen con Nibabel"""
        try:
            if not HAS_NIB:
                self.log("Nibabel no está disponible")
                return False
            
            # Verificar si es un archivo que Nibabel puede manejar
            _, ext = os.path.splitext(file_path)
            if ext.lower() != '.nii' and not (ext.lower() == '.gz' and os.path.splitext(os.path.splitext(file_path)[0])[1].lower() == '.nii'):
                self.log("Nibabel solo puede cargar archivos NIfTI (.nii, .nii.gz)")
                return False
                
            self.log("Intentando cargar con Nibabel...")
            
            # Cargar imagen
            img = nib.load(file_path)
            
            # Convertir a array
            array = img.get_fdata()
            
            # Reordenar dimensiones si es necesario
            if len(array.shape) == 3:
                # En Nibabel, comúnmente los datos están en (x, y, z)
                # Necesitamos cambiar a (z, y, x) para compatibilidad con SimpleITK/visualización
                array = np.transpose(array, (2, 1, 0))
            
            # Configurar visualización
            self.image_data = array
            
            # Extraer metadatos
            affine = img.affine
            header = img.header
            
            self.log(f"Imagen cargada con Nibabel")
            self.log(f"Dimensiones originales: {img.shape}")
            self.log(f"Dimensiones transpuestas: {array.shape}")
            self.log(f"Tipo de datos: {array.dtype}")
            
            # Configurar slider
            if len(array.shape) > 2:  # 3D
                self.slice_slider.setMaximum(array.shape[0] - 1)
                self.slice_slider.setValue(array.shape[0] // 2)
                self.slice_slider.setEnabled(True)
                self.current_slice = array.shape[0] // 2
            else:  # 2D
                self.slice_slider.setEnabled(False)
            
            self.update_display()
            return True
            
        except Exception as e:
            self.log(f"Error cargando con Nibabel: {str(e)}")
            return False
    
    def load_with_vtk(self, file_path):
        """Cargar imagen con VTK"""
        try:
            if not HAS_VTK:
                self.log("VTK no está disponible")
                return False
                
            self.log("Intentando cargar con VTK...")
            
            # Determinar el tipo de archivo
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            # Si es .gz, obtener la extensión anterior
            if ext == '.gz':
                _, prev_ext = os.path.splitext(os.path.splitext(file_path)[0])
                ext = prev_ext.lower() + ext
            
            # Seleccionar el lector adecuado según la extensión
            if ext == '.mha' or ext == '.mhd':
                reader = vtk.vtkMetaImageReader()
            elif ext == '.nii' or ext == '.nii.gz':
                reader = vtk.vtkNIFTIImageReader()
            elif ext == '.dcm':
                reader = vtk.vtkDICOMImageReader()
            else:
                reader = vtk.vtkImageReader2()
                
            reader.SetFileName(file_path)
            reader.Update()
            
            # Obtener la imagen
            vtk_image = reader.GetOutput()
            
            # Obtener dimensiones
            dims = vtk_image.GetDimensions()
            
            # Convertir a array numpy
            vtk_array = vtk_image.GetPointData().GetScalars()
            if not vtk_array:
                self.log("Error: No hay datos escalares en la imagen")
                return False
                
            # Convertir a numpy
            numpy_array = numpy_support.vtk_to_numpy(vtk_array)
            
            # Reformar según dimensiones
            # En VTK, el orden es (x, y, z) pero para visualización queremos (z, y, x)
            try:
                reshaped_array = numpy_array.reshape(dims[2], dims[1], dims[0])
            except:
                # Si falla el reshape, intentar un enfoque más simple
                try:
                    reshaped_array = numpy_array.reshape(-1, dims[1], dims[0])
                    self.log("Advertencia: Usando reshape alternativo")
                except:
                    self.log("Error: No se pudo reformar el array")
                    return False
            
            # Configurar visualización
            self.image_data = reshaped_array
            
            self.log(f"Imagen cargada con VTK")
            self.log(f"Dimensiones: {dims}")
            self.log(f"Forma del array: {reshaped_array.shape}")
            self.log(f"Tipo de datos: {reshaped_array.dtype}")
            
            # Configurar slider
            if len(reshaped_array.shape) > 2:  # 3D
                self.slice_slider.setMaximum(reshaped_array.shape[0] - 1)
                self.slice_slider.setValue(reshaped_array.shape[0] // 2)
                self.slice_slider.setEnabled(True)
                self.current_slice = reshaped_array.shape[0] // 2
            else:  # 2D
                self.slice_slider.setEnabled(False)
            
            self.update_display()
            return True
            
        except Exception as e:
            self.log(f"Error cargando con VTK: {str(e)}")
            return False
    
    def update_slice(self, value):
        """Actualizar slice a mostrar"""
        if self.image_data is not None and len(self.image_data.shape) > 2:
            if 0 <= value < self.image_data.shape[0]:
                self.current_slice = value
                self.update_display()
    
    def update_display(self):
        """Actualizar visualización"""
        if self.image_data is None:
            return
        
        # Limpiar figura
        self.figure.clear()
        
        # Añadir subplot
        ax = self.figure.add_subplot(111)
        
        # Mostrar imagen
        if len(self.image_data.shape) > 2:  # 3D
            # Obtener slice actual
            slice_data = self.image_data[self.current_slice]
            title = f"Corte {self.current_slice + 1}/{self.image_data.shape[0]}"
            self.slice_label.setText(f"{self.current_slice + 1}/{self.image_data.shape[0]}")
        else:  # 2D
            slice_data = self.image_data
            title = "Imagen 2D"
            self.slice_label.setText("2D")
        
        # Normalizar para mejor visualización
        try:
            p_min = np.percentile(slice_data, 1)
            p_max = np.percentile(slice_data, 99)
            normalized = np.clip((slice_data - p_min) / (p_max - p_min), 0, 1)
        except:
            # Si falla la normalización, usar imagen original
            normalized = slice_data
        
        # Mostrar imagen
        im = ax.imshow(normalized, cmap='gray')
        ax.set_title(title)
        
        # Opcional: añadir barra de color
        self.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        
        # Actualizar canvas
        self.canvas.draw()
        
        # Log info
        min_val = np.min(slice_data)
        max_val = np.max(slice_data)
        mean_val = np.mean(slice_data)
        self.log(f"Estadísticas del corte: Min={min_val:.2f}, Max={max_val:.2f}, Media={mean_val:.2f}")

def main():
    """Función principal"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Estilo moderno y consistente
    
    viewer = DiagnosticViewer()
    viewer.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()