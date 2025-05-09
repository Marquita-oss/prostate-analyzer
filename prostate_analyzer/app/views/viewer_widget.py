#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Widget de visualización principal para imágenes médicas
Integra visualización 2D multiplanar y renderizado 3D volumétrico
"""

import os
import sys
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QLabel, QSlider, QComboBox, QSplitter, QFrame,
                            QPushButton, QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QIcon

import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

# Intentamos importar MONAI para procesamiento avanzado
try:
    import monai
    from monai.transforms import ScaleIntensityRange
    MONAI_AVAILABLE = True
except ImportError:
    MONAI_AVAILABLE = False
    print("ADVERTENCIA: MONAI no está disponible. Algunas funcionalidades estarán limitadas.")

# Intentamos importar SimpleITK para carga de imágenes médicas
try:
    import SimpleITK as sitk
    SITK_AVAILABLE = True
except ImportError:
    SITK_AVAILABLE = False
    print("ADVERTENCIA: SimpleITK no está disponible. Se usará VTK para cargar imágenes.")

from config import ICONS_DIR, DEFAULT_COLORMAP, DEFAULT_WINDOW_LEVEL, DEFAULT_WINDOW_WIDTH

class ViewerWidget(QWidget):
    """
    Widget principal para visualización de imágenes médicas.
    Integra vistas 2D (axial, sagital, coronal) y renderizado 3D.
    """
    
    # Señales
    view_changed = pyqtSignal(dict)  # Informa cuando cambia la vista (tipo, posición, valor)
    
    def __init__(self, parent=None):
        super(ViewerWidget, self).__init__(parent)
        
        # Configuración inicial
        self.case_data = None
        self.image_data = None  # Datos de imagen VTK
        self.sitk_image = None  # Imagen SimpleITK (si está disponible)
        self.volume_actor = None  # Actor de volumen para VRT
        
        # Estado de visualización
        self.current_view_mode = "axial"  # Opciones: "axial", "sagital", "coronal", "3d"
        self.vrt_mode_enabled = False
        self.current_sequence = 0
        self.window_level = DEFAULT_WINDOW_LEVEL
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.prediction_overlay_enabled = False
        
        # Configurar interfaz de usuario
        self.setup_ui()
        
        # Inicializar renderizadores VTK
        self.initialize_vtk_renderers()
    
    def setup_ui(self):
        """Configura la interfaz de usuario del visualizador"""
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Panel superior para selección de secuencia y controles
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # Selector de secuencia
        sequence_layout = QHBoxLayout()
        sequence_layout.addWidget(QLabel("Secuencia:"))
        self.sequence_combo = QComboBox()
        self.sequence_combo.currentIndexChanged.connect(self.on_sequence_changed)
        sequence_layout.addWidget(self.sequence_combo)
        control_layout.addLayout(sequence_layout)
        
        # Controles de ventaneo (window/level)
        window_group = QGroupBox("Ventaneo")
        window_layout = QGridLayout(window_group)
        
        # Level slider
        window_layout.addWidget(QLabel("Nivel:"), 0, 0)
        self.level_slider = QSlider(Qt.Horizontal)
        self.level_slider.setRange(0, 2000)
        self.level_slider.setValue(int(DEFAULT_WINDOW_LEVEL))
        self.level_slider.valueChanged.connect(self.on_window_level_changed)
        window_layout.addWidget(self.level_slider, 0, 1)
        self.level_value_label = QLabel(f"{DEFAULT_WINDOW_LEVEL}")
        window_layout.addWidget(self.level_value_label, 0, 2)
        
        # Width slider
        window_layout.addWidget(QLabel("Ancho:"), 1, 0)
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 4000)
        self.width_slider.setValue(int(DEFAULT_WINDOW_WIDTH))
        self.width_slider.valueChanged.connect(self.on_window_width_changed)
        window_layout.addWidget(self.width_slider, 1, 1)
        self.width_value_label = QLabel(f"{DEFAULT_WINDOW_WIDTH}")
        window_layout.addWidget(self.width_value_label, 1, 2)
        
        control_layout.addWidget(window_group)
        
        # Selector de mapa de colores
        colormap_layout = QHBoxLayout()
        colormap_layout.addWidget(QLabel("Colores:"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["Grays", "Jet", "HSV", "Hot", "Cool"])
        self.colormap_combo.currentTextChanged.connect(self.on_colormap_changed)
        colormap_layout.addWidget(self.colormap_combo)
        control_layout.addLayout(colormap_layout)
        
        # Checkbox para superponer predicción
        self.overlay_checkbox = QCheckBox("Mostrar Predicción")
        self.overlay_checkbox.setEnabled(False)
        self.overlay_checkbox.toggled.connect(self.toggle_prediction_overlay)
        control_layout.addWidget(self.overlay_checkbox)
        
        # Estirar para que los controles queden bien distribuidos
        control_layout.addStretch()
        
        # Añadir panel de control al layout principal
        main_layout.addWidget(control_panel)
        
        # Frame principal para visualizadores
        view_frame = QFrame()
        view_frame.setFrameShape(QFrame.StyledPanel)
        view_frame.setObjectName("viewerFrame")
        view_layout = QVBoxLayout(view_frame)
        view_layout.setContentsMargins(0, 0, 0, 0)
        
        # Frame que contiene las vistas
        self.view_container = QWidget()
        self.view_container_layout = QGridLayout(self.view_container)
        self.view_container_layout.setContentsMargins(0, 0, 0, 0)
        self.view_container_layout.setSpacing(2)
        
        view_layout.addWidget(self.view_container)
        
        # Añadir frame principal al layout
        main_layout.addWidget(view_frame)
        
        # Panel inferior para slider de navegación
        nav_panel = QWidget()
        nav_layout = QHBoxLayout(nav_panel)
        
        nav_layout.addWidget(QLabel("Corte:"))
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.setEnabled(False)
        self.slice_slider.valueChanged.connect(self.on_slice_changed)
        nav_layout.addWidget(self.slice_slider)
        
        self.slice_label = QLabel("0/0")
        nav_layout.addWidget(self.slice_label)
        
        main_layout.addWidget(nav_panel)
    
    def initialize_vtk_renderers(self):
        """Inicializa los renderizadores VTK para las diferentes vistas"""
        # Crear el contenedor para los widgets VTK
        self.vtk_widgets = {}
        
        # Configurar layoutf para los diferentes modos de visualización
        
        # 1. Modo de visualización único (axial, sagital o coronal)
        self.single_view_widget = QVTKRenderWindowInteractor(self.view_container)
        self.view_container_layout.addWidget(self.single_view_widget, 0, 0)
        
        # Ocultar inicialmente (se mostrará cuando se establezca un modo)
        self.single_view_widget.hide()
        
        # 2. Modo de visualización multiplanar (MPR)
        self.mpr_container = QWidget()
        mpr_layout = QGridLayout(self.mpr_container)
        mpr_layout.setContentsMargins(0, 0, 0, 0)
        mpr_layout.setSpacing(2)
        
        # Crear los tres widgets para MPR
        self.axial_widget = QVTKRenderWindowInteractor(self.mpr_container)
        mpr_layout.addWidget(self.axial_widget, 0, 0)
        
        self.sagittal_widget = QVTKRenderWindowInteractor(self.mpr_container)
        mpr_layout.addWidget(self.sagittal_widget, 0, 1)
        
        self.coronal_widget = QVTKRenderWindowInteractor(self.mpr_container)
        mpr_layout.addWidget(self.coronal_widget, 1, 0)
        
        # 3. Modo de visualización 3D
        self.volume_widget = QVTKRenderWindowInteractor(self.mpr_container)
        mpr_layout.addWidget(self.volume_widget, 1, 1)
        
        # Agregar el contenedor MPR al layout principal
        self.view_container_layout.addWidget(self.mpr_container, 0, 0)
        self.mpr_container.hide()  # Ocultar inicialmente
        
        # Inicializar renderizadores y actores para cada vista
        self.renderers = {}
        
        # Renderizador para vista única
        self.renderers['single'] = vtk.vtkRenderer()
        self.single_view_widget.GetRenderWindow().AddRenderer(self.renderers['single'])
        self.vtk_widgets['single'] = self.single_view_widget
        
        # Renderizadores para MPR
        self.renderers['axial'] = vtk.vtkRenderer()
        self.axial_widget.GetRenderWindow().AddRenderer(self.renderers['axial'])
        self.vtk_widgets['axial'] = self.axial_widget
        
        self.renderers['sagittal'] = vtk.vtkRenderer()
        self.sagittal_widget.GetRenderWindow().AddRenderer(self.renderers['sagittal'])
        self.vtk_widgets['sagittal'] = self.sagittal_widget
        
        self.renderers['coronal'] = vtk.vtkRenderer()
        self.coronal_widget.GetRenderWindow().AddRenderer(self.renderers['coronal'])
        self.vtk_widgets['coronal'] = self.coronal_widget
        
        # Renderizador para volumen 3D
        self.renderers['volume'] = vtk.vtkRenderer()
        self.volume_widget.GetRenderWindow().AddRenderer(self.renderers['volume'])
        self.vtk_widgets['volume'] = self.volume_widget
        
        # Configurar fondos de los renderizadores
        for renderer in self.renderers.values():
            renderer.SetBackground(0.1, 0.1, 0.1)  # Fondo oscuro
        
        # Inicializar interactores
        for widget in self.vtk_widgets.values():
            widget.Initialize()
            widget.Start()  # Necesario para que responda a interacciones
    
    def load_case_data(self, case_data):
        """
        Carga los datos de un caso y configura el visualizador
        
        Args:
            case_data: Diccionario con datos del caso (incluyendo archivos de secuencias)
        """
        self.case_data = case_data
        
        # Limpiar visualizador primero
        self.clear()
        
        # Comprobar que hay archivos
        if 'files' not in case_data or not case_data['files']:
            print("No hay archivos en el caso")
            return
        
        # Actualizar combo de secuencias
        self.sequence_combo.clear()
        for file_info in case_data['files']:
            sequence_name = file_info.get('sequence_type', 'Desconocida')
            file_name = os.path.basename(file_info['path'])
            self.sequence_combo.addItem(f"{sequence_name.upper()} - {file_name}")
        
        # Seleccionar la primera secuencia
        if self.sequence_combo.count() > 0:
            self.sequence_combo.setCurrentIndex(0)
            self.load_current_sequence()
    
    def load_current_sequence(self):
        """Carga la secuencia actualmente seleccionada"""
        if not self.case_data or 'files' not in self.case_data:
            return
        
        # Obtener el índice actual
        index = self.sequence_combo.currentIndex()
        if index < 0 or index >= len(self.case_data['files']):
            return
        
        # Obtener información del archivo
        file_info = self.case_data['files'][index]
        file_path = file_info['path']
        
        # Cargar el archivo usando SimpleITK si está disponible
        if SITK_AVAILABLE:
            try:
                # Cargar imagen con SimpleITK
                self.sitk_image = sitk.ReadImage(file_path)
                
                # Convertir a VTK para visualización
                self.image_data = self._convert_sitk_to_vtk(self.sitk_image)
                
                # Actualizar visualización
                self._update_visualization()
                return
            except Exception as e:
                print(f"Error al cargar imagen con SimpleITK: {e}")
                # Continuar con método alternativo
        
        # Método alternativo: usar VTK directamente
        try:
            # Determinar el tipo de archivo
            _, ext = os.path.splitext(file_path)
            
            # Usar el lector adecuado según la extensión
            if ext.lower() == '.mha':
                reader = vtk.vtkMetaImageReader()
            elif ext.lower() in ['.nii', '.gz']:
                reader = vtk.vtkNIFTIImageReader()
            else:
                reader = vtk.vtkImageReader2()
                
            reader.SetFileName(file_path)
            reader.Update()
            
            self.image_data = reader.GetOutput()
            self._update_visualization()
        except Exception as e:
            print(f"Error al cargar imagen con VTK: {e}")
    
    def _convert_sitk_to_vtk(self, sitk_image):
        """Convierte una imagen SimpleITK a formato VTK"""
        # Obtener array numpy de la imagen SimpleITK
        array = sitk.GetArrayFromImage(sitk_image)
        
        # Crear imagen VTK a partir del array
        vtk_image = vtk.vtkImageData()
        
        # Configurar dimensiones
        vtk_image.SetDimensions(array.shape[2], array.shape[1], array.shape[0])
        
        # Configurar origen y espaciado
        vtk_image.SetOrigin(sitk_image.GetOrigin())
        vtk_image.SetSpacing(sitk_image.GetSpacing())
        
        # Determinar tipo de datos para VTK
        numpy_dtype = array.dtype
        if numpy_dtype == np.uint8:
            vtk_dtype = vtk.VTK_UNSIGNED_CHAR
        elif numpy_dtype == np.int16:
            vtk_dtype = vtk.VTK_SHORT
        elif numpy_dtype == np.uint16:
            vtk_dtype = vtk.VTK_UNSIGNED_SHORT
        elif numpy_dtype == np.int32:
            vtk_dtype = vtk.VTK_INT
        elif numpy_dtype == np.float32:
            vtk_dtype = vtk.VTK_FLOAT
        elif numpy_dtype == np.float64:
            vtk_dtype = vtk.VTK_DOUBLE
        else:
            vtk_dtype = vtk.VTK_FLOAT
            array = array.astype(np.float32)
        
        # Configurar tipo de datos
        vtk_image.AllocateScalars(vtk_dtype, 1)
        
        # Obtener puntero a los datos y copiar array
        memory_size = array.nbytes
        flat_array = array.flatten(order='F')  # VTK usa orden Fortran
        vtk_array = vtk.vtkImageImportExecutive()
        vtk_array.CopyImportVoidPointer(flat_array, memory_size)
        
        # Asignar array a la imagen
        vtk_image.GetPointData().SetScalars(vtk_array)
        
        return vtk_image
    
    def _update_visualization(self):
        """Actualiza la visualización después de cargar una imagen"""
        if not self.image_data:
            return
        
        # Determinar dimensiones
        dims = self.image_data.GetDimensions()
        
        # Configurar el rango del slider de cortes según el modo de vista actual
        if self.current_view_mode == "axial":
            self.slice_slider.setMaximum(dims[2] - 1)
            self.slice_slider.setValue(dims[2] // 2)
        elif self.current_view_mode == "sagittal":
            self.slice_slider.setMaximum(dims[0] - 1)
            self.slice_slider.setValue(dims[0] // 2)
        elif self.current_view_mode == "coronal":
            self.slice_slider.setMaximum(dims[1] - 1)
            self.slice_slider.setValue(dims[1] // 2)
        
        # Habilitar el slider
        self.slice_slider.setEnabled(True)
        
        # Actualizar visualización según el modo actual
        self._update_view_for_current_mode()
    
    def _update_view_for_current_mode(self):
        """Actualiza la vista según el modo actual"""
        if not self.image_data:
            return
        
        # Ocultar todos los contenedores primero
        self.single_view_widget.hide()
        self.mpr_container.hide()
        
        # Actualizar según el modo
        if self.vrt_mode_enabled:
            # Modo de renderizado volumétrico
            self._setup_volume_rendering()
            self.mpr_container.show()
        elif self.current_view_mode in ["axial", "sagittal", "coronal"]:
            # Modo de visualización 2D único
            self._setup_single_slice_view()
            self.single_view_widget.show()
        
        # Forzar actualización de todas las vistas
        for widget in self.vtk_widgets.values():
            widget.GetRenderWindow().Render()
    
    def _setup_single_slice_view(self):
        """Configura la vista de corte único (axial, sagital o coronal)"""
        if not self.image_data:
            return
        
        # Limpiar renderizador
        renderer = self.renderers['single']
        renderer.RemoveAllViewProps()
        
        # Crear plano de corte
        slice_number = self.slice_slider.value()
        
        # Crear imagen para mostrar el corte
        viewer = vtk.vtkImageViewer2()
        viewer.SetInputData(self.image_data)
        
        # Configurar orientación según modo de vista
        if self.current_view_mode == "axial":
            viewer.SetSliceOrientationToXY()
        elif self.current_view_mode == "sagittal":
            viewer.SetSliceOrientationToYZ()
        elif self.current_view_mode == "coronal":
            viewer.SetSliceOrientationToXZ()
        
        # Establecer el corte
        viewer.SetSlice(slice_number)
        
        # Configurar ventaneo
        viewer.SetColorWindow(self.window_width)
        viewer.SetColorLevel(self.window_level)
        
        # Obtener actor y añadirlo al renderizador
        viewer.GetRenderer().SetBackground(0.1, 0.1, 0.1)
        slice_actor = viewer.GetImageActor()
        renderer.AddActor(slice_actor)
        
        # Actualizar etiqueta de corte
        max_slice = self.slice_slider.maximum()
        self.slice_label.setText(f"{slice_number+1}/{max_slice+1}")
        
        # Resetear cámara
        renderer.ResetCamera()
        
        # Actualizar ventana
        self.single_view_widget.GetRenderWindow().Render()
    
    def _setup_volume_rendering(self):
        """Configura el renderizado volumétrico 3D"""
        if not self.image_data:
            return
        
        # Limpiar renderizador
        volume_renderer = self.renderers['volume']
        volume_renderer.RemoveAllViewProps()
        
        # Crear función de transferencia de color y opacidad
        color_function = vtk.vtkColorTransferFunction()
        opacity_function = vtk.vtkPiecewiseFunction()
        
        # Configurar mapa de color según selección
        colormap = self.colormap_combo.currentText()
        
        # Determinar valores mínimo y máximo de la imagen
        range = self.image_data.GetScalarRange()
        min_val = range[0]
        max_val = range[1]
        
        # Configurar funciones de transferencia según el mapa de colores
        if colormap == "Grays":
            # Escala de grises
            color_function.AddRGBPoint(min_val, 0.0, 0.0, 0.0)
            color_function.AddRGBPoint(max_val, 1.0, 1.0, 1.0)
        elif colormap == "Jet":
            # Mapa tipo 'jet' (azul-cian-verde-amarillo-rojo)
            color_function.AddRGBPoint(min_val, 0.0, 0.0, 1.0)
            color_function.AddRGBPoint(min_val + (max_val-min_val)*0.25, 0.0, 1.0, 1.0)
            color_function.AddRGBPoint(min_val + (max_val-min_val)*0.5, 0.0, 1.0, 0.0)
            color_function.AddRGBPoint(min_val + (max_val-min_val)*0.75, 1.0, 1.0, 0.0)
            color_function.AddRGBPoint(max_val, 1.0, 0.0, 0.0)
        elif colormap == "HSV":
            # Mapa tipo HSV
            color_function.AddRGBPoint(min_val, 1.0, 0.0, 0.0)
            color_function.AddRGBPoint(min_val + (max_val-min_val)*0.25, 1.0, 1.0, 0.0)
            color_function.AddRGBPoint(min_val + (max_val-min_val)*0.5, 0.0, 1.0, 0.0)
            color_function.AddRGBPoint(min_val + (max_val-min_val)*0.75, 0.0, 1.0, 1.0)
            color_function.AddRGBPoint(max_val, 1.0, 0.0, 1.0)
        elif colormap == "Hot":
            # Mapa tipo 'hot' (negro-rojo-amarillo-blanco)
            color_function.AddRGBPoint(min_val, 0.0, 0.0, 0.0)
            color_function.AddRGBPoint(min_val + (max_val-min_val)*0.33, 1.0, 0.0, 0.0)
            color_function.AddRGBPoint(min_val + (max_val-min_val)*0.66, 1.0, 1.0, 0.0)
            color_function.AddRGBPoint(max_val, 1.0, 1.0, 1.0)
        else:  # Cool
            # Mapa tipo 'cool' (cian-magenta)
            color_function.AddRGBPoint(min_val, 0.0, 1.0, 1.0)
            color_function.AddRGBPoint(max_val, 1.0, 0.0, 1.0)
        
        # Configurar función de opacidad
        # Valores más altos son más opacos
        opacity_function.AddPoint(min_val, 0.0)
        opacity_function.AddPoint(min_val + (max_val-min_val)*0.2, 0.0)  # Hacer transparentes los valores más bajos
        opacity_function.AddPoint(max_val, 1.0)
        
        # Crear propiedades de volumen
        volume_property = vtk.vtkVolumeProperty()
        volume_property.SetColor(color_function)
        volume_property.SetScalarOpacity(opacity_function)
        volume_property.SetInterpolationTypeToLinear()
        volume_property.ShadeOn()  # Activar sombreado para mejor percepción 3D
        
        # Crear mapper
        volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
        volume_mapper.SetInputData(self.image_data)
        
        # Crear actor de volumen
        volume_actor = vtk.vtkVolume()
        volume_actor.SetMapper(volume_mapper)
        volume_actor.SetProperty(volume_property)
        
        # Añadir actor al renderizador
        volume_renderer.AddVolume(volume_actor)
        
        # Guardar referencia al actor
        self.volume_actor = volume_actor
        
        # Resetear cámara
        volume_renderer.ResetCamera()
        
        # Actualizar ventana
        self.volume_widget.GetRenderWindow().Render()
    
    def on_sequence_changed(self, index):
        """Manejador cuando se cambia la secuencia seleccionada"""
        if index >= 0:
            self.current_sequence = index
            self.load_current_sequence()
    
    def on_slice_changed(self, value):
        """Manejador cuando se cambia el corte con el slider"""
        if self.image_data:
            # Actualizar vista
            self._update_view_for_current_mode()
            
            # Emitir señal con información de la vista
            view_info = {
                'type': self.current_view_mode,
                'slice': value,
            }
            
            # Añadir posición y valor (si está disponible)
            if self.sitk_image:
                # Calcular posición dependiendo del modo de vista
                dims = self.sitk_image.GetSize()
                spacing = self.sitk_image.GetSpacing()
                origin = self.sitk_image.GetOrigin()
                
                if self.current_view_mode == "axial":
                    pos_z = origin[2] + value * spacing[2]
                    position = (0, 0, pos_z)
                elif self.current_view_mode == "sagittal":
                    pos_x = origin[0] + value * spacing[0]
                    position = (pos_x, 0, 0)
                elif self.current_view_mode == "coronal":
                    pos_y = origin[1] + value * spacing[1]
                    position = (0, pos_y, 0)
                else:
                    position = (0, 0, 0)
                
                view_info['position'] = position
                
                # Intentar obtener valor en el centro del corte
                try:
                    center_x = dims[0] // 2
                    center_y = dims[1] // 2
                    center_z = dims[2] // 2
                    
                    if self.current_view_mode == "axial":
                        pixel_value = sitk.GetArrayFromImage(self.sitk_image)[value, center_y, center_x]
                    elif self.current_view_mode == "sagittal":
                        pixel_value = sitk.GetArrayFromImage(self.sitk_image)[center_z, center_y, value]
                    elif self.current_view_mode == "coronal":
                        pixel_value = sitk.GetArrayFromImage(self.sitk_image)[center_z, value, center_x]
                    else:
                        pixel_value = 0
                    
                    view_info['value'] = float(pixel_value)
                except:
                    view_info['value'] = 0
            
            self.view_changed.emit(view_info)
    
    def on_window_level_changed(self, value):
        """Manejador cuando se cambia el nivel de ventana"""
        self.window_level = value
        self.level_value_label.setText(f"{value}")
        
        # Actualizar visualización
        self._update_view_for_current_mode()
    
    def on_window_width_changed(self, value):
        """Manejador cuando se cambia el ancho de ventana"""
        self.window_width = value
        self.width_value_label.setText(f"{value}")
        
        # Actualizar visualización
        self._update_view_for_current_mode()
    
    def on_colormap_changed(self, colormap_name):
        """Manejador cuando se cambia el mapa de colores"""
        # Actualizar visualización
        self._update_view_for_current_mode()
    
    def toggle_prediction_overlay(self, enabled):
        """Activa o desactiva la superposición de predicción"""
        self.prediction_overlay_enabled = enabled
        
        # Actualizar visualización
        self._update_view_for_current_mode()
    
    def set_view_mode(self, mode):
        """
        Establece el modo de visualización
        
        Args:
            mode: Modo de visualización ("axial", "sagittal", "coronal")
        """
        if mode not in ["axial", "sagittal", "coronal"]:
            print(f"Modo de visualización no válido: {mode}")
            return
        
        self.current_view_mode = mode
        
        # Actualizar rango de slider según el modo
        if self.image_data:
            dims = self.image_data.GetDimensions()
            
            if mode == "axial":
                self.slice_slider.setMaximum(dims[2] - 1)
                self.slice_slider.setValue(dims[2] // 2)
            elif mode == "sagittal":
                self.slice_slider.setMaximum(dims[0] - 1)
                self.slice_slider.setValue(dims[0] // 2)
            elif mode == "coronal":
                self.slice_slider.setMaximum(dims[1] - 1)
                self.slice_slider.setValue(dims[1] // 2)
        
        # Actualizar visualización
        self._update_view_for_current_mode()
    
    def set_vrt_mode(self, enabled):
        """
        Activa o desactiva el modo de renderizado volumétrico
        
        Args:
            enabled: True para activar, False para desactivar
        """
        self.vrt_mode_enabled = enabled
        
        # Deshabilitar slider de cortes en modo 3D
        self.slice_slider.setEnabled(not enabled)
        
        # Actualizar visualización
        self._update_view_for_current_mode()
    
    def show_prediction_results(self, prediction_results):
        """
        Muestra los resultados de predicción
        
        Args:
            prediction_results: Diccionario con resultados de la predicción
        """
        # Activar checkbox de superposición
        self.overlay_checkbox.setEnabled(True)
        self.overlay_checkbox.setChecked(True)
        
        # Almacenar resultados
        self.prediction_results = prediction_results
        
        # Actualizar visualización
        self._update_view_for_current_mode()
    
    def clear(self):
        """Limpia la visualización"""
        # Limpiar datos
        self.case_data = None
        self.image_data = None
        self.sitk_image = None
        self.volume_actor = None
        
        # Limpiar combobox de secuencias
        self.sequence_combo.clear()
        
        # Deshabilitar controles
        self.slice_slider.setEnabled(False)
        self.overlay_checkbox.setEnabled(False)
        self.overlay_checkbox.setChecked(False)
        
        # Limpiar renderizadores
        for renderer in self.renderers.values():
            renderer.RemoveAllViewProps()
        
        # Actualizar ventanas
        for widget in self.vtk_widgets.values():
            widget.GetRenderWindow().Render()