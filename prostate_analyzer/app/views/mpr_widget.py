#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Widget para visualización multiplanar (MPR) de imágenes médicas
Permite visualizar cortes axiales, sagitales y coronales simultáneamente
"""

import os
import sys
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QSlider, QGridLayout, QGroupBox, QFrame,
                           QComboBox, QCheckBox, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon

import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

# Intentar importar MONAI para procesamiento avanzado
try:
    import monai
    from monai.transforms import ScaleIntensityRange
    MONAI_AVAILABLE = True
except ImportError:
    MONAI_AVAILABLE = False
    print("ADVERTENCIA: MONAI no está disponible. Algunas funcionalidades estarán limitadas.")

# Intentar importar SimpleITK para carga de imágenes médicas
try:
    import SimpleITK as sitk
    SITK_AVAILABLE = True
except ImportError:
    SITK_AVAILABLE = False
    print("ADVERTENCIA: SimpleITK no está disponible. Se usará VTK para cargar imágenes.")

# Importar utilidades para VTK
try:
    from app.utils.vtk_utils import create_image_actor, setup_vtk_renderer
except ImportError:
    try:
        # Intento alternativo si la estructura de directorios es diferente
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.vtk_utils import create_image_actor, setup_vtk_renderer
    except ImportError:
        # Definir funciones básicas si no se puede importar el módulo
        def create_image_actor(vtk_image, color_window=None, color_level=None):
            """Crea un actor para una imagen VTK"""
            mapper = vtk.vtkImageMapToColors()
            mapper.SetInputData(vtk_image)
            
            # Configurar ventaneo si se especifica
            if color_window is not None and color_level is not None:
                lookup_table = vtk.vtkLookupTable()
                lookup_table.SetTableRange(
                    color_level - color_window/2.0,
                    color_level + color_window/2.0
                )
                lookup_table.SetSaturationRange(0, 0)
                lookup_table.SetHueRange(0, 0)
                lookup_table.SetValueRange(0, 1)
                lookup_table.Build()
                
                mapper.SetLookupTable(lookup_table)
            
            actor = vtk.vtkImageActor()
            actor.GetMapper().SetInputConnection(mapper.GetOutputPort())
            return actor
        
        def setup_vtk_renderer(renderer, background_color=(0.1, 0.1, 0.1)):
            """Configura un renderizador VTK"""
            renderer.SetBackground(background_color)
            return renderer

from config import DEFAULT_WINDOW_LEVEL, DEFAULT_WINDOW_WIDTH

class MPRWidget(QWidget):
    """
    Widget para visualización multiplanar (MPR) de imágenes médicas
    Muestra tres vistas: axial, sagital y coronal
    """
    
    # Señales
    view_changed = pyqtSignal(dict)  # Informa cuando cambia la vista (tipo, posición, valor)
    
    def __init__(self, parent=None):
        super(MPRWidget, self).__init__(parent)
        
        # Estado de visualización
        self.vtk_image = None           # Imagen VTK
        self.sitk_image = None          # Imagen SimpleITK
        self.window_level = DEFAULT_WINDOW_LEVEL  # Nivel de ventana
        self.window_width = DEFAULT_WINDOW_WIDTH  # Ancho de ventana
        self.slice_positions = {        # Posición de los cortes
            'axial': 0,
            'sagittal': 0,
            'coronal': 0
        }
        self.prediction_overlay_enabled = False  # Superposición de predicción
        self.prediction_data = None     # Datos de predicción
        
        # Configurar UI
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Layout para los controles de visualización
        controls_layout = QHBoxLayout()
        
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
        
        controls_layout.addWidget(window_group)
        
        # Selector de mapa de colores
        colormap_group = QGroupBox("Colores")
        colormap_layout = QHBoxLayout(colormap_group)
        
        colormap_layout.addWidget(QLabel("Esquema:"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["Grays", "Jet", "HSV", "Hot", "Cool"])
        self.colormap_combo.currentTextChanged.connect(self.on_colormap_changed)
        colormap_layout.addWidget(self.colormap_combo)
        
        controls_layout.addWidget(colormap_group)
        
        # Checkbox para superponer predicción
        overlay_group = QGroupBox("Predicción")
        overlay_layout = QHBoxLayout(overlay_group)
        
        self.overlay_checkbox = QCheckBox("Mostrar predicción")
        self.overlay_checkbox.setEnabled(False)
        self.overlay_checkbox.toggled.connect(self.toggle_prediction_overlay)
        overlay_layout.addWidget(self.overlay_checkbox)
        
        controls_layout.addWidget(overlay_group)
        
        main_layout.addLayout(controls_layout)
        
        # Grid para las vistas
        self.views_grid = QGridLayout()
        self.views_grid.setSpacing(5)
        
        # Crear widgets VTK para cada vista
        self.create_vtk_widgets()
        
        # Añadir widgets al grid
        # Vista axial (superior izquierda)
        axial_layout = QVBoxLayout()
        axial_layout.addWidget(QLabel("Axial"))
        axial_layout.addWidget(self.axial_widget)
        self.axial_slider = QSlider(Qt.Horizontal)
        self.axial_slider.setEnabled(False)
        self.axial_slider.valueChanged.connect(lambda val: self.on_slice_changed('axial', val))
        axial_layout.addWidget(self.axial_slider)
        self.views_grid.addLayout(axial_layout, 0, 0)
        
        # Vista sagital (superior derecha)
        sagittal_layout = QVBoxLayout()
        sagittal_layout.addWidget(QLabel("Sagital"))
        sagittal_layout.addWidget(self.sagittal_widget)
        self.sagittal_slider = QSlider(Qt.Horizontal)
        self.sagittal_slider.setEnabled(False)
        self.sagittal_slider.valueChanged.connect(lambda val: self.on_slice_changed('sagittal', val))
        sagittal_layout.addWidget(self.sagittal_slider)
        self.views_grid.addLayout(sagittal_layout, 0, 1)
        
        # Vista coronal (inferior izquierda)
        coronal_layout = QVBoxLayout()
        coronal_layout.addWidget(QLabel("Coronal"))
        coronal_layout.addWidget(self.coronal_widget)
        self.coronal_slider = QSlider(Qt.Horizontal)
        self.coronal_slider.setEnabled(False)
        self.coronal_slider.valueChanged.connect(lambda val: self.on_slice_changed('coronal', val))
        coronal_layout.addWidget(self.coronal_slider)
        self.views_grid.addLayout(coronal_layout, 1, 0)
        
        # Panel de información (inferior derecha)
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        
        self.info_label = QLabel("Sin imagen cargada")
        info_layout.addWidget(self.info_label)
        
        # Botones de navegación
        nav_layout = QGridLayout()
        
        self.nav_buttons = {}
        # Botones para axial
        self.nav_buttons['axial_prev'] = QPushButton("◀")
        self.nav_buttons['axial_prev'].setToolTip("Corte axial anterior")
        self.nav_buttons['axial_prev'].clicked.connect(lambda: self.navigate_slice('axial', -1))
        nav_layout.addWidget(self.nav_buttons['axial_prev'], 0, 0)
        
        self.nav_buttons['axial_next'] = QPushButton("▶")
        self.nav_buttons['axial_next'].setToolTip("Corte axial siguiente")
        self.nav_buttons['axial_next'].clicked.connect(lambda: self.navigate_slice('axial', 1))
        nav_layout.addWidget(self.nav_buttons['axial_next'], 0, 1)
        
        # Botones para sagital
        self.nav_buttons['sagittal_prev'] = QPushButton("◀")
        self.nav_buttons['sagittal_prev'].setToolTip("Corte sagital anterior")
        self.nav_buttons['sagittal_prev'].clicked.connect(lambda: self.navigate_slice('sagittal', -1))
        nav_layout.addWidget(self.nav_buttons['sagittal_prev'], 1, 0)

        self.nav_buttons['sagittal_next'] = QPushButton("▶")
        self.nav_buttons['sagittal_next'].setToolTip("Corte sagital siguiente")
        self.nav_buttons['sagittal_next'].clicked.connect(lambda: self.navigate_slice('sagittal', 1))
        nav_layout.addWidget(self.nav_buttons['sagittal_next'], 1, 1)
        
        # Botones para coronal
        self.nav_buttons['coronal_prev'] = QPushButton("◀")
        self.nav_buttons['coronal_prev'].setToolTip("Corte coronal anterior")
        self.nav_buttons['coronal_prev'].clicked.connect(lambda: self.navigate_slice('coronal', -1))
        nav_layout.addWidget(self.nav_buttons['coronal_prev'], 2, 0)
        
        self.nav_buttons['coronal_next'] = QPushButton("▶")
        self.nav_buttons['coronal_next'].setToolTip("Corte coronal siguiente")
        self.nav_buttons['coronal_next'].clicked.connect(lambda: self.navigate_slice('coronal', 1))
        nav_layout.addWidget(self.nav_buttons['coronal_next'], 2, 1)
        
        # Deshabilitar botones inicialmente
        for button in self.nav_buttons.values():
            button.setEnabled(False)
        
        info_layout.addLayout(nav_layout)
        
        # Añadir panel de información al grid
        self.views_grid.addWidget(info_frame, 1, 1)
        
        # Añadir grid al layout principal
        main_layout.addLayout(self.views_grid)
    
    def create_vtk_widgets(self):
        """Crea los widgets VTK para las diferentes vistas"""
        # Crear widgets VTK
        self.axial_widget = QVTKRenderWindowInteractor(self)
        self.sagittal_widget = QVTKRenderWindowInteractor(self)
        self.coronal_widget = QVTKRenderWindowInteractor(self)
        
        # Configurar renderizadores
        self.renderers = {}
        
        self.renderers['axial'] = vtk.vtkRenderer()
        self.axial_widget.GetRenderWindow().AddRenderer(self.renderers['axial'])
        setup_vtk_renderer(self.renderers['axial'])
        
        self.renderers['sagittal'] = vtk.vtkRenderer()
        self.sagittal_widget.GetRenderWindow().AddRenderer(self.renderers['sagittal'])
        setup_vtk_renderer(self.renderers['sagittal'])
        
        self.renderers['coronal'] = vtk.vtkRenderer()
        self.coronal_widget.GetRenderWindow().AddRenderer(self.renderers['coronal'])
        setup_vtk_renderer(self.renderers['coronal'])
        
        # Inicializar interactores
        self.axial_widget.Initialize()
        self.sagittal_widget.Initialize()
        self.coronal_widget.Initialize()
        
        # Configurar estilo de interacción
        for widget in [self.axial_widget, self.sagittal_widget, self.coronal_widget]:
            style = vtk.vtkInteractorStyleImage()
            widget.GetRenderWindow().GetInteractor().SetInteractorStyle(style)
    
    def load_image(self, image_data, metadata=None):
        """
        Carga una imagen para visualización
        
        Args:
            image_data: Datos de la imagen (VTK o SimpleITK)
            metadata: Metadatos adicionales (opcional)
        """
        # Limpiar primero
        self.clear()
        
        # Determinar tipo de datos y configurar
        if isinstance(image_data, vtk.vtkImageData):
            self.vtk_image = image_data
        elif SITK_AVAILABLE and isinstance(image_data, sitk.Image):
            self.sitk_image = image_data
            self.vtk_image = self._convert_sitk_to_vtk(image_data)
        else:
            print("ADVERTENCIA: Tipo de datos de imagen no soportado")
            return
        
        # Configurar sliders según dimensiones de la imagen
        self._setup_sliders()
        
        # Actualizar información
        self._update_info_label(metadata)
        
        # Actualizar visualización
        self.update_views()
    
    def _convert_sitk_to_vtk(self, sitk_image):
        """
        Convierte una imagen SimpleITK a formato VTK
        
        Args:
            sitk_image: Imagen SimpleITK
            
        Returns:
            Imagen en formato VTK
        """
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
        vtk_array = vtk.util.numpy_support.numpy_to_vtk(
            num_array=flat_array,
            deep=True,
            array_type=vtk_dtype
        )
        
        # Asignar array a la imagen
        vtk_image.GetPointData().SetScalars(vtk_array)
        
        return vtk_image
    
    def _setup_sliders(self):
        """Configura los sliders basados en las dimensiones de la imagen"""
        if not self.vtk_image:
            return
        
        # Obtener dimensiones
        dims = self.vtk_image.GetDimensions()
        
        # Configurar sliders
        self.axial_slider.setRange(0, dims[2] - 1)
        self.axial_slider.setValue(dims[2] // 2)
        self.axial_slider.setEnabled(True)
        
        self.sagittal_slider.setRange(0, dims[0] - 1)
        self.sagittal_slider.setValue(dims[0] // 2)
        self.sagittal_slider.setEnabled(True)
        
        self.coronal_slider.setRange(0, dims[1] - 1)
        self.coronal_slider.setValue(dims[1] // 2)
        self.coronal_slider.setEnabled(True)
        
        # Habilitar botones de navegación
        for button in self.nav_buttons.values():
            button.setEnabled(True)
    
    def _update_info_label(self, metadata=None):
        """Actualiza la etiqueta de información con metadatos de la imagen"""
        if not self.vtk_image:
            self.info_label.setText("Sin imagen cargada")
            return
        
        # Obtener dimensiones
        dims = self.vtk_image.GetDimensions()
        spacing = self.vtk_image.GetSpacing()
        
        # Crear texto informativo
        info_text = f"<b>Dimensiones:</b> {dims[0]} x {dims[1]} x {dims[2]}<br>"
        info_text += f"<b>Espaciado:</b> {spacing[0]:.2f} x {spacing[1]:.2f} x {spacing[2]:.2f} mm<br>"
        
        if metadata:
            # Añadir metadatos relevantes
            if 'patient_id' in metadata:
                info_text += f"<b>Paciente:</b> {metadata['patient_id']}<br>"
            if 'study_date' in metadata:
                info_text += f"<b>Fecha:</b> {metadata['study_date']}<br>"
            if 'sequence_type' in metadata:
                info_text += f"<b>Secuencia:</b> {metadata['sequence_type'].upper()}<br>"
        
        self.info_label.setText(info_text)
    
    def update_views(self):
        """Actualiza todas las vistas con la configuración actual"""
        if not self.vtk_image:
            return
        
        # Actualizar cada vista
        self.update_axial_view()
        self.update_sagittal_view()
        self.update_coronal_view()
    
    def update_axial_view(self):
        """Actualiza la vista axial"""
        if not self.vtk_image:
            return
        
        # Obtener posición del corte
        slice_pos = self.slice_positions['axial']
        
        # Limpiar renderizador
        self.renderers['axial'].RemoveAllViewProps()
        
        # Crear plano de corte
        extract_slice = vtk.vtkImageMapToColors()
        extract_slice.SetInputData(self.vtk_image)
        
        # Crear lookup table
        lut = vtk.vtkLookupTable()
        lut.SetTableRange(
            self.window_level - self.window_width/2.0,
            self.window_level + self.window_width/2.0
        )
        lut.SetSaturationRange(0, 0)
        lut.SetHueRange(0, 0)
        lut.SetValueRange(0, 1)
        lut.Build()
        extract_slice.SetLookupTable(lut)
        
        # Configurar reslice para mostrar corte axial
        reslice = vtk.vtkImageReslice()
        reslice.SetInputData(self.vtk_image)
        reslice.SetOutputDimensionality(2)
        reslice.SetResliceAxesDirectionCosines(
            1, 0, 0,  # eje x
            0, 1, 0,  # eje y
            0, 0, 1   # eje z
        )
        
        # Configurar corte específico en eje Z
        dims = self.vtk_image.GetDimensions()
        origin = self.vtk_image.GetOrigin()
        spacing = self.vtk_image.GetSpacing()
        slice_point = [
            origin[0] + dims[0] * spacing[0] / 2,
            origin[1] + dims[1] * spacing[1] / 2,
            origin[2] + slice_pos * spacing[2]
        ]
        reslice.SetResliceAxesOrigin(slice_point)
        reslice.SetInterpolationModeToLinear()
        reslice.Update()
        
        # Conectar reslice a mapper
        extract_slice.SetInputConnection(reslice.GetOutputPort())
        
        # Crear actor
        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(extract_slice.GetOutputPort())
        
        # Añadir actor al renderizador
        self.renderers['axial'].AddActor(actor)
        
        # Superponer predicción si está habilitado
        if self.prediction_overlay_enabled and self.prediction_data is not None:
            self._add_prediction_overlay('axial', slice_pos)
        
        # Resetear cámara
        self.renderers['axial'].ResetCamera()
        
        # Actualizar vista
        self.axial_widget.GetRenderWindow().Render()
    
    def update_sagittal_view(self):
        """Actualiza la vista sagital"""
        if not self.vtk_image:
            return
        
        # Obtener posición del corte
        slice_pos = self.slice_positions['sagittal']
        
        # Limpiar renderizador
        self.renderers['sagittal'].RemoveAllViewProps()
        
        # Crear plano de corte
        extract_slice = vtk.vtkImageMapToColors()
        extract_slice.SetInputData(self.vtk_image)
        
        # Crear lookup table
        lut = vtk.vtkLookupTable()
        lut.SetTableRange(
            self.window_level - self.window_width/2.0,
            self.window_level + self.window_width/2.0
        )
        lut.SetSaturationRange(0, 0)
        lut.SetHueRange(0, 0)
        lut.SetValueRange(0, 1)
        lut.Build()
        extract_slice.SetLookupTable(lut)
        
        # Configurar reslice para mostrar corte sagital
        reslice = vtk.vtkImageReslice()
        reslice.SetInputData(self.vtk_image)
        reslice.SetOutputDimensionality(2)
        reslice.SetResliceAxesDirectionCosines(
            0, 0, 1,  # eje x (era z)
            0, 1, 0,  # eje y
            1, 0, 0   # eje z (era x)
        )
        
        # Configurar corte específico en eje X
        dims = self.vtk_image.GetDimensions()
        origin = self.vtk_image.GetOrigin()
        spacing = self.vtk_image.GetSpacing()
        slice_point = [
            origin[0] + slice_pos * spacing[0],
            origin[1] + dims[1] * spacing[1] / 2,
            origin[2] + dims[2] * spacing[2] / 2
        ]
        reslice.SetResliceAxesOrigin(slice_point)
        reslice.SetInterpolationModeToLinear()
        reslice.Update()
        
        # Conectar reslice a mapper
        extract_slice.SetInputConnection(reslice.GetOutputPort())
        
        # Crear actor
        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(extract_slice.GetOutputPort())
        
        # Añadir actor al renderizador
        self.renderers['sagittal'].AddActor(actor)
        
        # Superponer predicción si está habilitado
        if self.prediction_overlay_enabled and self.prediction_data is not None:
            self._add_prediction_overlay('sagittal', slice_pos)
        
        # Resetear cámara
        self.renderers['sagittal'].ResetCamera()
        
        # Actualizar vista
        self.sagittal_widget.GetRenderWindow().Render()
    
    def update_coronal_view(self):
        """Actualiza la vista coronal"""
        if not self.vtk_image:
            return
        
        # Obtener posición del corte
        slice_pos = self.slice_positions['coronal']
        
        # Limpiar renderizador
        self.renderers['coronal'].RemoveAllViewProps()
        
        # Crear plano de corte
        extract_slice = vtk.vtkImageMapToColors()
        extract_slice.SetInputData(self.vtk_image)
        
        # Crear lookup table
        lut = vtk.vtkLookupTable()
        lut.SetTableRange(
            self.window_level - self.window_width/2.0,
            self.window_level + self.window_width/2.0
        )
        lut.SetSaturationRange(0, 0)
        lut.SetHueRange(0, 0)
        lut.SetValueRange(0, 1)
        lut.Build()
        extract_slice.SetLookupTable(lut)
        
        # Configurar reslice para mostrar corte coronal
        reslice = vtk.vtkImageReslice()
        reslice.SetInputData(self.vtk_image)
        reslice.SetOutputDimensionality(2)
        reslice.SetResliceAxesDirectionCosines(
            1, 0, 0,  # eje x
            0, 0, 1,  # eje y (era z)
            0, 1, 0   # eje z (era y)
        )
        
        # Configurar corte específico en eje Y
        dims = self.vtk_image.GetDimensions()
        origin = self.vtk_image.GetOrigin()
        spacing = self.vtk_image.GetSpacing()
        slice_point = [
            origin[0] + dims[0] * spacing[0] / 2,
            origin[1] + slice_pos * spacing[1],
            origin[2] + dims[2] * spacing[2] / 2
        ]
        reslice.SetResliceAxesOrigin(slice_point)
        reslice.SetInterpolationModeToLinear()
        reslice.Update()
        
        # Conectar reslice a mapper
        extract_slice.SetInputConnection(reslice.GetOutputPort())
        
        # Crear actor
        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(extract_slice.GetOutputPort())
        
        # Añadir actor al renderizador
        self.renderers['coronal'].AddActor(actor)
        
        # Superponer predicción si está habilitado
        if self.prediction_overlay_enabled and self.prediction_data is not None:
            self._add_prediction_overlay('coronal', slice_pos)
        
        # Resetear cámara
        self.renderers['coronal'].ResetCamera()
        
        # Actualizar vista
        self.coronal_widget.GetRenderWindow().Render()
    
    def _add_prediction_overlay(self, view_type, slice_pos):
        """
        Añade superposición de predicción a una vista
        
        Args:
            view_type: Tipo de vista ('axial', 'sagittal', 'coronal')
            slice_pos: Posición del corte
        """
        if not self.prediction_data or 'segmentation' not in self.prediction_data:
            return
        
        # Obtener segmentación
        segmentation = self.prediction_data['segmentation']
        
        # Crear imagen VTK para la segmentación
        seg_vtk = vtk.vtkImageData()
        seg_vtk.SetDimensions(segmentation.shape[2], segmentation.shape[1], segmentation.shape[0])
        
        # Asumimos el mismo espaciado y origen que la imagen original
        seg_vtk.SetSpacing(self.vtk_image.GetSpacing())
        seg_vtk.SetOrigin(self.vtk_image.GetOrigin())
        
        # Configurar tipo de datos
        seg_vtk.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
        
        # Copiar datos a la imagen VTK
        seg_array = segmentation.astype(np.uint8)
        flat_array = seg_array.flatten(order='F')  # VTK usa orden Fortran
        vtk_array = vtk.util.numpy_support.numpy_to_vtk(
            num_array=flat_array,
            deep=True,
            array_type=vtk.VTK_UNSIGNED_CHAR
        )
        
        # Asignar array a la imagen
        seg_vtk.GetPointData().SetScalars(vtk_array)
        
        # Crear plano de corte para la segmentación
        extract_slice = vtk.vtkImageMapToColors()
        extract_slice.SetInputData(seg_vtk)
        
        # Crear lookup table colorida para la segmentación
        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(2)  # 0: Fondo, 1: Lesión
        lut.SetTableValue(0, 0, 0, 0, 0)  # Fondo transparente
        lut.SetTableValue(1, 1, 0, 0, 0.5)  # Lesión en rojo semitransparente
        lut.Build()
        extract_slice.SetLookupTable(lut)
        
        # Configurar reslice según el tipo de vista
        reslice = vtk.vtkImageReslice()
        reslice.SetInputData(seg_vtk)
        reslice.SetOutputDimensionality(2)
        
        dims = seg_vtk.GetDimensions()
        origin = seg_vtk.GetOrigin()
        spacing = seg_vtk.GetSpacing()
        
        if view_type == 'axial':
            reslice.SetResliceAxesDirectionCosines(
                1, 0, 0,  # eje x
                0, 1, 0,  # eje y
                0, 0, 1   # eje z
            )
            slice_point = [
                origin[0] + dims[0] * spacing[0] / 2,
                origin[1] + dims[1] * spacing[1] / 2,
                origin[2] + slice_pos * spacing[2]
            ]
        elif view_type == 'sagittal':
            reslice.SetResliceAxesDirectionCosines(
                0, 0, 1,  # eje x (era z)
                0, 1, 0,  # eje y
                1, 0, 0   # eje z (era x)
            )
            slice_point = [
                origin[0] + slice_pos * spacing[0],
                origin[1] + dims[1] * spacing[1] / 2,
                origin[2] + dims[2] * spacing[2] / 2
            ]
        elif view_type == 'coronal':
            reslice.SetResliceAxesDirectionCosines(
                1, 0, 0,  # eje x
                0, 0, 1,  # eje y (era z)
                0, 1, 0   # eje z (era y)
            )
            slice_point = [
                origin[0] + dims[0] * spacing[0] / 2,
                origin[1] + slice_pos * spacing[1],
                origin[2] + dims[2] * spacing[2] / 2
            ]
        
        reslice.SetResliceAxesOrigin(slice_point)
        reslice.SetInterpolationModeToNearest()  # Mejor para segmentaciones
        reslice.Update()
        
        # Conectar reslice a mapper
        extract_slice.SetInputConnection(reslice.GetOutputPort())
        
        # Crear actor
        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(extract_slice.GetOutputPort())
        
        # Añadir actor al renderizador
        self.renderers[view_type].AddActor(actor)
    
    def on_slice_changed(self, view_type, value):
        """
        Manejador cuando se cambia el corte con el slider
        
        Args:
            view_type: Tipo de vista ('axial', 'sagittal', 'coronal')
            value: Nuevo valor del slider
        """
        if not self.vtk_image:
            return
        
        # Actualizar posición del corte
        self.slice_positions[view_type] = value
        
        # Actualizar vista correspondiente
        if view_type == 'axial':
            self.update_axial_view()
        elif view_type == 'sagittal':
            self.update_sagittal_view()
        elif view_type == 'coronal':
            self.update_coronal_view()
        
        # Emitir señal con información de la vista
        view_info = {
            'type': view_type,
            'slice': value,
            'position': self._calculate_world_position(view_type, value)
        }
        
        # Añadir valor de intensidad si es posible
        if self.sitk_image:
            try:
                # Convertir posición de slice a coordenadas de mundo
                world_pos = view_info['position']
                # Convertir coordenadas de mundo a índices de imagen
                index = self.sitk_image.TransformPhysicalPointToIndex(world_pos)
                # Obtener valor de intensidad
                value = self.sitk_image.GetPixel(index)
                view_info['value'] = float(value)
            except:
                view_info['value'] = 0
        
        self.view_changed.emit(view_info)
    
    def _calculate_world_position(self, view_type, slice_pos):
        """
        Calcula la posición en coordenadas mundo para un corte
        
        Args:
            view_type: Tipo de vista
            slice_pos: Posición del corte
            
        Returns:
            Tupla (x, y, z) con coordenadas mundo
        """
        if not self.vtk_image:
            return (0, 0, 0)
        
        # Obtener dimensiones, origen y espaciado
        dims = self.vtk_image.GetDimensions()
        origin = self.vtk_image.GetOrigin()
        spacing = self.vtk_image.GetSpacing()
        
        # Calcular centro en X e Y
        center_x = origin[0] + dims[0] * spacing[0] / 2
        center_y = origin[1] + dims[1] * spacing[1] / 2
        center_z = origin[2] + dims[2] * spacing[2] / 2
        
        # Calcular posición según el tipo de vista
        if view_type == 'axial':
            # El eje Z varía, X e Y centrados
            return (center_x, center_y, origin[2] + slice_pos * spacing[2])
        elif view_type == 'sagittal':
            # El eje X varía, Y y Z centrados
            return (origin[0] + slice_pos * spacing[0], center_y, center_z)
        elif view_type == 'coronal':
            # El eje Y varía, X y Z centrados
            return (center_x, origin[1] + slice_pos * spacing[1], center_z)
        
        # Valor por defecto
        return (0, 0, 0)
    
    def navigate_slice(self, view_type, delta):
        """
        Navega entre cortes usando los botones
        
        Args:
            view_type: Tipo de vista ('axial', 'sagittal', 'coronal')
            delta: Incremento (+1 o -1)
        """
        if not self.vtk_image:
            return
        
        # Obtener slider correspondiente
        slider = None
        if view_type == 'axial':
            slider = self.axial_slider
        elif view_type == 'sagittal':
            slider = self.sagittal_slider
        elif view_type == 'coronal':
            slider = self.coronal_slider
        
        if not slider:
            return
        
        # Calcular nuevo valor
        current_value = slider.value()
        new_value = current_value + delta
        
        # Verificar límites
        if new_value < slider.minimum():
            new_value = slider.minimum()
        elif new_value > slider.maximum():
            new_value = slider.maximum()
        
        # Establecer nuevo valor
        slider.setValue(new_value)
    
    def on_window_level_changed(self, value):
        """
        Manejador cuando se cambia el nivel de ventana
        
        Args:
            value: Nuevo valor del nivel
        """
        self.window_level = value
        self.level_value_label.setText(f"{value}")
        
        # Actualizar visualización
        self.update_views()
    
    def on_window_width_changed(self, value):
        """
        Manejador cuando se cambia el ancho de ventana
        
        Args:
            value: Nuevo valor del ancho
        """
        self.window_width = value
        self.width_value_label.setText(f"{value}")
        
        # Actualizar visualización
        self.update_views()
    
    def on_colormap_changed(self, colormap_name):
        """
        Manejador cuando se cambia el mapa de colores
        
        Args:
            colormap_name: Nombre del nuevo mapa de colores
        """
        # Actualizar visualización 
        self.update_views()
    
    def toggle_prediction_overlay(self, enabled):
        """
        Activa o desactiva la superposición de predicción
        
        Args:
            enabled: True para activar, False para desactivar
        """
        self.prediction_overlay_enabled = enabled
        
        # Actualizar visualización
        self.update_views()
    
    def set_prediction_data(self, prediction_data):
        """
        Establece los datos de predicción para superposición
        
        Args:
            prediction_data: Diccionario con resultados de predicción
        """
        self.prediction_data = prediction_data
        
        # Habilitar checkbox de superposición
        self.overlay_checkbox.setEnabled(True)
        self.overlay_checkbox.setChecked(True)
        
        # Actualizar visualización
        self.update_views()
    
    def clear(self):
        """Limpia la visualización"""
        # Limpiar datos
        self.vtk_image = None
        self.sitk_image = None
        self.prediction_data = None
        
        # Deshabilitar controles
        self.axial_slider.setEnabled(False)
        self.sagittal_slider.setEnabled(False)
        self.coronal_slider.setEnabled(False)

        self.overlay_checkbox.setEnabled(False)
        self.overlay_checkbox.setChecked(False)
        
        for button in self.nav_buttons.values():
            button.setEnabled(False)
        
        # Limpiar renderizadores
        for renderer in self.renderers.values():
            renderer.RemoveAllViewProps()
        
        # Actualizar ventanas
        self.axial_widget.GetRenderWindow().Render()
        self.sagittal_widget.GetRenderWindow().Render()
        self.coronal_widget.GetRenderWindow().Render()
        
        # Actualizar etiqueta de información
        self.info_label.setText("Sin imagen cargada")
    
    def save_current_view(self, file_path, view_type='axial'):
        """
        Guarda la vista actual como imagen
        
        Args:
            file_path: Ruta donde guardar la imagen
            view_type: Tipo de vista a guardar ('axial', 'sagittal', 'coronal')
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        if not self.vtk_image:
            return False
        
        try:
            # Obtener ventana de renderizado correspondiente
            render_window = None
            if view_type == 'axial':
                render_window = self.axial_widget.GetRenderWindow()
            elif view_type == 'sagittal':
                render_window = self.sagittal_widget.GetRenderWindow()
            elif view_type == 'coronal':
                render_window = self.coronal_widget.GetRenderWindow()
            else:
                return False
            
            # Crear objeto para exportar imagen
            window_to_image = vtk.vtkWindowToImageFilter()
            window_to_image.SetInput(render_window)
            window_to_image.Update()
            
            # Determinar formato de salida
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            # Crear escritor según formato
            if ext == '.png':
                writer = vtk.vtkPNGWriter()
            elif ext == '.jpg' or ext == '.jpeg':
                writer = vtk.vtkJPEGWriter()
            elif ext == '.tiff' or ext == '.tif':
                writer = vtk.vtkTIFFWriter()
            else:
                # Por defecto usar PNG
                writer = vtk.vtkPNGWriter()
                if not ext:
                    file_path += '.png'
            
            # Guardar imagen
            writer.SetFileName(file_path)
            writer.SetInputConnection(window_to_image.GetOutputPort())
            writer.Write()
            
            return True
        except Exception as e:
            print(f"Error al guardar vista como imagen: {str(e)}")
            return False
    
    def get_current_slice_data(self, view_type='axial'):
        """
        Obtiene datos del corte actual para una vista específica
        
        Args:
            view_type: Tipo de vista ('axial', 'sagittal', 'coronal')
            
        Returns:
            Tuple (array de datos, metadata) o (None, None) si no hay datos
        """
        if not self.vtk_image or view_type not in self.slice_positions:
            return None, None
        
        slice_pos = self.slice_positions[view_type]
        
        # Si tenemos imagen SimpleITK, extraer corte de ahí (más preciso)
        if self.sitk_image:
            try:
                # Obtener array
                array = sitk.GetArrayFromImage(self.sitk_image)
                
                # Extraer corte según la vista
                if view_type == 'axial':
                    slice_data = array[slice_pos, :, :]
                elif view_type == 'sagittal':
                    slice_data = array[:, :, slice_pos]
                elif view_type == 'coronal':
                    slice_data = array[:, slice_pos, :]
                
                # Crear metadatos
                metadata = {
                    'view_type': view_type,
                    'slice_position': slice_pos,
                    'window_level': self.window_level,
                    'window_width': self.window_width
                }
                
                return slice_data, metadata
            except Exception as e:
                print(f"Error al extraer datos de corte de SimpleITK: {str(e)}")
        
        # Si no hay imagen SimpleITK o falló la extracción, intentar con VTK
        try:
            # Configurar el mismo reslice que usamos para visualización
            reslice = vtk.vtkImageReslice()
            reslice.SetInputData(self.vtk_image)
            reslice.SetOutputDimensionality(2)
            
            dims = self.vtk_image.GetDimensions()
            origin = self.vtk_image.GetOrigin()
            spacing = self.vtk_image.GetSpacing()
            
            if view_type == 'axial':
                reslice.SetResliceAxesDirectionCosines(
                    1, 0, 0,  # eje x
                    0, 1, 0,  # eje y
                    0, 0, 1   # eje z
                )
                slice_point = [
                    origin[0] + dims[0] * spacing[0] / 2,
                    origin[1] + dims[1] * spacing[1] / 2,
                    origin[2] + slice_pos * spacing[2]
                ]
            elif view_type == 'sagittal':
                reslice.SetResliceAxesDirectionCosines(
                    0, 0, 1,  # eje x (era z)
                    0, 1, 0,  # eje y
                    1, 0, 0   # eje z (era x)
                )
                slice_point = [
                    origin[0] + slice_pos * spacing[0],
                    origin[1] + dims[1] * spacing[1] / 2,
                    origin[2] + dims[2] * spacing[2] / 2
                ]
            elif view_type == 'coronal':
                reslice.SetResliceAxesDirectionCosines(
                    1, 0, 0,  # eje x
                    0, 0, 1,  # eje y (era z)
                    0, 1, 0   # eje z (era y)
                )
                slice_point = [
                    origin[0] + dims[0] * spacing[0] / 2,
                    origin[1] + slice_pos * spacing[1],
                    origin[2] + dims[2] * spacing[2] / 2
                ]
            
            reslice.SetResliceAxesOrigin(slice_point)
            reslice.SetInterpolationModeToLinear()
            reslice.Update()
            
            # Obtener array de la salida
            output = reslice.GetOutput()
            dims_output = output.GetDimensions()
            vtk_array = output.GetPointData().GetScalars()
            
            # Convertir a numpy
            numpy_array = vtk.util.numpy_support.vtk_to_numpy(vtk_array)
            numpy_array = numpy_array.reshape(dims_output[1], dims_output[0])
            
            # Crear metadatos
            metadata = {
                'view_type': view_type,
                'slice_position': slice_pos,
                'window_level': self.window_level,
                'window_width': self.window_width,
                'dimensions': dims_output,
                'spacing': output.GetSpacing()
            }
            
            return numpy_array, metadata
        except Exception as e:
            print(f"Error al extraer datos de corte de VTK: {str(e)}")
            return None, None
    
    def resizeEvent(self, event):
        """
        Manejador cuando se redimensiona el widget
        
        Args:
            event: Evento de redimensionamiento
        """
        super(MPRWidget, self).resizeEvent(event)
        
        # Actualizar ventanas de renderizado
        for widget in [self.axial_widget, self.sagittal_widget, self.coronal_widget]:
            widget.GetRenderWindow().Render()