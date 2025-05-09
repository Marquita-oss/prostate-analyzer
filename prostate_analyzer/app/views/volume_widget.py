#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Widget para visualización volumétrica 3D de imágenes médicas
Permite renderizado de volúmenes con diferentes técnicas y mapas de transferencia
"""

import os
import sys
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QSlider, QComboBox, QGroupBox, QCheckBox,
                           QPushButton, QFormLayout, QColorDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QColor

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
    from app.utils.vtk_utils import setup_vtk_renderer, create_volume_property
except ImportError:
    try:
        # Intento alternativo si la estructura de directorios es diferente
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.vtk_utils import setup_vtk_renderer, create_volume_property
    except ImportError:
        # Definir funciones básicas si no se puede importar el módulo
        def setup_vtk_renderer(renderer, background_color=(0.1, 0.1, 0.1)):
            """Configura un renderizador VTK"""
            renderer.SetBackground(background_color)
            return renderer
        
        def create_volume_property(preset='CT-Bones'):
            """Crea propiedades para renderizado volumétrico"""
            volume_property = vtk.vtkVolumeProperty()
            
            # Configurar según el preset
            if preset == 'CT-Bones':
                # Propiedades para huesos en CT
                volume_property.SetColor(create_ct_bone_color_function())
                volume_property.SetScalarOpacity(create_ct_bone_opacity_function())
            elif preset == 'MRI-Default':
                # Propiedades para MRI general
                volume_property.SetColor(create_mri_default_color_function())
                volume_property.SetScalarOpacity(create_mri_default_opacity_function())
            elif preset == 'MRI-Soft-Tissue':
                # Propiedades para tejidos blandos en MRI
                volume_property.SetColor(create_mri_soft_tissue_color_function())
                volume_property.SetScalarOpacity(create_mri_soft_tissue_opacity_function())
            else:
                # Propiedades por defecto
                volume_property.SetColor(create_default_color_function())
                volume_property.SetScalarOpacity(create_default_opacity_function())
            
            # Configuraciones comunes
            volume_property.SetInterpolationTypeToLinear()
            volume_property.ShadeOn()
            volume_property.SetAmbient(0.2)
            volume_property.SetDiffuse(0.9)
            volume_property.SetSpecular(0.3)
            volume_property.SetSpecularPower(15.0)
            
            return volume_property
        
        def create_default_color_function():
            # Función de transferencia por defecto
            color_function = vtk.vtkColorTransferFunction()
            color_function.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
            color_function.AddRGBPoint(0.5, 0.5, 0.5, 0.5)
            color_function.AddRGBPoint(1.0, 1.0, 1.0, 1.0)
            return color_function
        
        def create_default_opacity_function():
            # Función de opacidad por defecto
            opacity_function = vtk.vtkPiecewiseFunction()
            opacity_function.AddPoint(0.0, 0.0)
            opacity_function.AddPoint(0.3, 0.0)
            opacity_function.AddPoint(0.7, 0.5)
            opacity_function.AddPoint(1.0, 1.0)
            return opacity_function
        
        def create_mri_default_color_function():
            # Función de color para MRI general
            color_function = vtk.vtkColorTransferFunction()
            color_function.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
            color_function.AddRGBPoint(0.2, 0.0, 0.0, 0.8)
            color_function.AddRGBPoint(0.5, 0.0, 0.8, 0.8)
            color_function.AddRGBPoint(0.8, 0.8, 0.8, 0.0)
            color_function.AddRGBPoint(1.0, 1.0, 0.0, 0.0)
            return color_function
        
        def create_mri_default_opacity_function():
            # Función de opacidad para MRI general
            opacity_function = vtk.vtkPiecewiseFunction()
            opacity_function.AddPoint(0.0, 0.0)
            opacity_function.AddPoint(0.1, 0.0)
            opacity_function.AddPoint(0.3, 0.2)
            opacity_function.AddPoint(0.6, 0.5)
            opacity_function.AddPoint(1.0, 0.8)
            return opacity_function
        
        def create_mri_soft_tissue_color_function():
            # Función de color para tejidos blandos en MRI
            color_function = vtk.vtkColorTransferFunction()
            color_function.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
            color_function.AddRGBPoint(0.3, 0.6, 0.3, 0.0)
            color_function.AddRGBPoint(0.6, 0.8, 0.6, 0.2)
            color_function.AddRGBPoint(1.0, 1.0, 0.8, 0.6)
            return color_function
        
        def create_mri_soft_tissue_opacity_function():
            # Función de opacidad para tejidos blandos en MRI
            opacity_function = vtk.vtkPiecewiseFunction()
            opacity_function.AddPoint(0.0, 0.0)
            opacity_function.AddPoint(0.2, 0.0)
            opacity_function.AddPoint(0.4, 0.2)
            opacity_function.AddPoint(0.7, 0.6)
            opacity_function.AddPoint(1.0, 0.9)
            return opacity_function
        
        def create_ct_bone_color_function():
            # Función de color para huesos en CT
            color_function = vtk.vtkColorTransferFunction()
            color_function.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
            color_function.AddRGBPoint(0.4, 0.5, 0.3, 0.1)
            color_function.AddRGBPoint(0.7, 0.8, 0.7, 0.5)
            color_function.AddRGBPoint(1.0, 1.0, 0.9, 0.8)
            return color_function
        
        def create_ct_bone_opacity_function():
            # Función de opacidad para huesos en CT
            opacity_function = vtk.vtkPiecewiseFunction()
            opacity_function.AddPoint(0.0, 0.0)
            opacity_function.AddPoint(0.3, 0.0)
            opacity_function.AddPoint(0.5, 0.2)
            opacity_function.AddPoint(0.8, 0.8)
            opacity_function.AddPoint(1.0, 1.0)
            return opacity_function

class VolumeWidget(QWidget):
    """
    Widget para visualización volumétrica 3D de imágenes médicas
    """
    
    # Señales
    render_updated = pyqtSignal()  # Emitida cuando se actualiza el renderizado
    position_changed = pyqtSignal(dict)  # Emitida cuando cambia la posición (para coordenadas 3D)
    
    def __init__(self, parent=None):
        super(VolumeWidget, self).__init__(parent)
        
        # Estado de visualización
        self.vtk_image = None       # Imagen VTK
        self.sitk_image = None      # Imagen SimpleITK
        self.volume_actor = None    # Actor de volumen
        self.clipping_planes = []   # Planos de corte
        
        # Configuraciones de renderizado
        self.rendering_technique = 'ray_cast'  # Técnica de renderizado
        self.preset = 'MRI-Default'  # Preset de visualización
        self.opacity_scale = 1.0     # Escala de opacidad
        self.quality = 'medium'      # Calidad de renderizado
        self.use_shading = True      # Usar sombreado
        
        # Configuraciones de mapas de transferencia
        self.custom_color_points = []  # Puntos personalizados para color
        self.custom_opacity_points = []  # Puntos personalizados para opacidad
        
        # Configurar UI
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Layout superior para controles
        top_layout = QHBoxLayout()
        
        # Grupo de controles de renderizado
        render_group = QGroupBox("Renderizado")
        render_layout = QFormLayout(render_group)
        
        # Selector de técnica de renderizado
        self.technique_combo = QComboBox()
        self.technique_combo.addItems(["Ray Casting", "GPU Ray Casting", "Texture Mapping"])
        self.technique_combo.currentIndexChanged.connect(self.on_technique_changed)
        render_layout.addRow("Técnica:", self.technique_combo)
        
        # Selector de preset
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["MRI-Default", "MRI-Soft-Tissue", "CT-Bones", "Custom"])
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        render_layout.addRow("Preset:", self.preset_combo)
        
        # Selector de calidad
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Baja", "Media", "Alta"])
        self.quality_combo.setCurrentIndex(1)  # Media por defecto
        self.quality_combo.currentIndexChanged.connect(self.on_quality_changed)
        render_layout.addRow("Calidad:", self.quality_combo)
        
        # Checkbox para sombreado
        self.shading_checkbox = QCheckBox("Activado")
        self.shading_checkbox.setChecked(True)
        self.shading_checkbox.toggled.connect(self.on_shading_toggled)
        render_layout.addRow("Sombreado:", self.shading_checkbox)
        
        top_layout.addWidget(render_group)
        
        # Grupo de controles de opacidad
        opacity_group = QGroupBox("Opacidad")
        opacity_layout = QVBoxLayout(opacity_group)
        
        # Slider para escala de opacidad
        opacity_layout.addWidget(QLabel("Escala de Opacidad:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(int(self.opacity_scale * 100))
        self.opacity_slider.valueChanged.connect(self.on_opacity_scale_changed)
        opacity_layout.addWidget(self.opacity_slider)
        
        # Botón para editar puntos de opacidad personalizados
        self.edit_opacity_button = QPushButton("Editar Función de Opacidad...")
        self.edit_opacity_button.clicked.connect(self.edit_opacity_function)
        opacity_layout.addWidget(self.edit_opacity_button)
        
        top_layout.addWidget(opacity_group)
        
        # Grupo para clipping (planos de corte)
        clipping_group = QGroupBox("Planos de Corte")
        clipping_layout = QFormLayout(clipping_group)
        
        # Checkbox para activar clipping
        self.clipping_checkbox = QCheckBox("Activado")
        self.clipping_checkbox.toggled.connect(self.on_clipping_toggled)
        clipping_layout.addRow("Clipping:", self.clipping_checkbox)
        
        # Sliders para posición de planos de corte
        self.clip_sliders = {}
        for axis, label in zip(['x', 'y', 'z'], ['X:', 'Y:', 'Z:']):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(0)  # Inicialmente en 0
            slider.setEnabled(False)  # Deshabilitado hasta que se active clipping
            slider.valueChanged.connect(lambda val, a=axis: self.on_clip_slider_changed(a, val))
            clipping_layout.addRow(label, slider)
            self.clip_sliders[axis] = slider
        
        top_layout.addWidget(clipping_group)
        
        main_layout.addLayout(top_layout)
        
        # Widget para el renderizado volumétrico
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        main_layout.addWidget(self.vtk_widget, 1)  # El 1 como factor de estiramiento
        
        # Configurar renderizador VTK
        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        setup_vtk_renderer(self.renderer, background_color=(0.05, 0.05, 0.2))  # Azul oscuro para 3D
        
        # Configurar estilo de interacción
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)
        
        # Botones de vista predefinida
        buttons_layout = QHBoxLayout()
        
        # Vistas predefinidas
        view_buttons = {
            'Axial': lambda: self.set_view_orientation('axial'),
            'Sagital': lambda: self.set_view_orientation('sagittal'),
            'Coronal': lambda: self.set_view_orientation('coronal'),
            'Isométrica': lambda: self.set_view_orientation('isometric'),
        }
        
        for name, func in view_buttons.items():
            button = QPushButton(name)
            button.clicked.connect(func)
            buttons_layout.addWidget(button)
        
        # Botón para capturar vista
        self.capture_button = QPushButton("Capturar Vista")
        self.capture_button.clicked.connect(self.capture_view)
        buttons_layout.addWidget(self.capture_button)
        
        main_layout.addLayout(buttons_layout)
        
        # Inicializar interactor
        self.vtk_widget.Initialize()
        self.vtk_widget.Start()
        
        # Desactivar botones hasta que se cargue una imagen
        self.edit_opacity_button.setEnabled(False)
        self.capture_button.setEnabled(False)
    
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
        
        # Configurar rangos de clipping basados en dimensiones de la imagen
        self._setup_clipping_ranges()
        
        # Crear renderizado volumétrico
        self._setup_volume_rendering()
        
        # Habilitar botones
        self.edit_opacity_button.setEnabled(True)
        self.capture_button.setEnabled(True)
    
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
    
    def _setup_clipping_ranges(self):
        """Configura los rangos de los sliders de clipping basados en la imagen"""
        if not self.vtk_image:
            return
        
        # Obtener dimensiones y origen
        dims = self.vtk_image.GetDimensions()
        origin = self.vtk_image.GetOrigin()
        spacing = self.vtk_image.GetSpacing()
        
        # Calcular rangos
        x_range = (origin[0], origin[0] + dims[0] * spacing[0])
        y_range = (origin[1], origin[1] + dims[1] * spacing[1])
        z_range = (origin[2], origin[2] + dims[2] * spacing[2])
        
        # Guardar rangos para conversión de sliders a posiciones reales
        self.clip_ranges = {
            'x': x_range,
            'y': y_range,
            'z': z_range
        }
        
        # Reestablecer sliders a 0
        for slider in self.clip_sliders.values():
            slider.setValue(0)
    
    def _setup_volume_rendering(self):
        """Configura el renderizado volumétrico usando la técnica actual"""
        if not self.vtk_image:
            return
        
        # Limpiar renderer
        if self.volume_actor:
            self.renderer.RemoveViewProp(self.volume_actor)

        # Crear propiedades de volumen según el preset
        volume_property = create_volume_property(self.preset)
        
        # Aplicar escala de opacidad
        if self.opacity_scale != 1.0:
            # Obtener función de opacidad actual
            opacity_function = volume_property.GetScalarOpacity()
            
            # Crear nueva función con escala
            scaled_opacity = vtk.vtkPiecewiseFunction()
            
            # Copiar puntos con escala
            for i in range(opacity_function.GetSize()):
                x, y = opacity_function.GetNodeValue(i)
                scaled_opacity.AddPoint(x, y * self.opacity_scale)
            
            # Asignar nueva función
            volume_property.SetScalarOpacity(scaled_opacity)
        
        # Aplicar puntos de transferencia personalizados si existen
        if self.preset == 'Custom' and self.custom_color_points:
            color_function = vtk.vtkColorTransferFunction()
            for point in self.custom_color_points:
                color_function.AddRGBPoint(point[0], point[1], point[2], point[3])
            volume_property.SetColor(color_function)
        
        if self.preset == 'Custom' and self.custom_opacity_points:
            opacity_function = vtk.vtkPiecewiseFunction()
            for point in self.custom_opacity_points:
                opacity_function.AddPoint(point[0], point[1])
            volume_property.SetScalarOpacity(opacity_function)
        
        # Configurar sombreado
        if self.use_shading:
            volume_property.ShadeOn()
            volume_property.SetAmbient(0.2)
            volume_property.SetDiffuse(0.9)
            volume_property.SetSpecular(0.3)
            volume_property.SetSpecularPower(15.0)
        else:
            volume_property.ShadeOff()
        
        # Crear mapper según la técnica seleccionada
        if self.rendering_technique == 'ray_cast':
            # CPU Ray Casting
            mapper = vtk.vtkFixedPointVolumeRayCastMapper()
            
            # Ajustar calidad
            if self.quality == 'low':
                mapper.SetImageSampleDistance(2.0)
                mapper.SetSampleDistance(2.0)
            elif self.quality == 'medium':
                mapper.SetImageSampleDistance(1.0)
                mapper.SetSampleDistance(1.0)
            else:  # high
                mapper.SetImageSampleDistance(0.5)
                mapper.SetSampleDistance(0.5)
                
        elif self.rendering_technique == 'gpu_ray_cast':
            # GPU Ray Casting
            mapper = vtk.vtkGPUVolumeRayCastMapper()
            
            # Ajustar calidad
            if self.quality == 'low':
                mapper.SetAutoAdjustSampleDistances(True)
                mapper.SetSampleDistance(2.0)
            elif self.quality == 'medium':
                mapper.SetAutoAdjustSampleDistances(True)
                mapper.SetSampleDistance(1.0)
            else:  # high
                mapper.SetAutoAdjustSampleDistances(True)
                mapper.SetSampleDistance(0.5)
                
        else:  # texture_mapping
            # Texture Mapping
            mapper = vtk.vtkVolumeTextureMapper3D()
            
        # Asignar imagen al mapper
        mapper.SetInputData(self.vtk_image)
        
        # Crear actor de volumen
        self.volume_actor = vtk.vtkVolume()
        self.volume_actor.SetMapper(mapper)
        self.volume_actor.SetProperty(volume_property)
        
        # Agregar actor al renderizador
        self.renderer.AddViewProp(self.volume_actor)
        
        # Configurar clipping planes si están activados
        if self.clipping_checkbox.isChecked():
            self._update_clipping_planes()
        
        # Resetear cámara
        self.renderer.ResetCamera()
        
        # Actualizar ventana
        self.vtk_widget.GetRenderWindow().Render()
        
        # Emitir señal
        self.render_updated.emit()
    
    def _update_clipping_planes(self):
        """Actualiza los planos de corte basados en los sliders"""
        if not self.vtk_image or not self.volume_actor:
            return
        
        # Limpiar planos existentes
        self.clipping_planes = []
        
        # Obtener dimensiones y origen
        dims = self.vtk_image.GetDimensions()
        origin = self.vtk_image.GetOrigin()
        spacing = self.vtk_image.GetSpacing()
        
        # Crear nuevos planos según posiciones de sliders
        for axis, slider in self.clip_sliders.items():
            if slider.value() > 0:  # Solo si el slider no está en cero
                plane = vtk.vtkPlane()
                
                # Convertir valor del slider a posición real
                value = slider.value() / 100.0  # Normalizar a [0, 1]
                range_min, range_max = self.clip_ranges[axis]
                position = range_min + value * (range_max - range_min)
                
                # Configurar plano
                if axis == 'x':
                    plane.SetNormal(1, 0, 0)
                    plane.SetOrigin(position, origin[1], origin[2])
                elif axis == 'y':
                    plane.SetNormal(0, 1, 0)
                    plane.SetOrigin(origin[0], position, origin[2])
                elif axis == 'z':
                    plane.SetNormal(0, 0, 1)
                    plane.SetOrigin(origin[0], origin[1], position)
                
                self.clipping_planes.append(plane)
        
        # Crear colección de planos
        if self.clipping_planes:
            planes_collection = vtk.vtkPlaneCollection()
            for plane in self.clipping_planes:
                planes_collection.AddItem(plane)
            
            # Asignar planos al mapper
            mapper = self.volume_actor.GetMapper()
            mapper.SetClippingPlanes(planes_collection)
        else:
            # Si no hay planos, asignar None
            mapper = self.volume_actor.GetMapper()
            mapper.SetClippingPlanes(None)
        
        # Actualizar visualización
        self.vtk_widget.GetRenderWindow().Render()
    
    def on_technique_changed(self, index):
        """
        Manejador cuando se cambia la técnica de renderizado
        
        Args:
            index: Índice de la técnica seleccionada
        """
        if index == 0:
            self.rendering_technique = 'ray_cast'
        elif index == 1:
            self.rendering_technique = 'gpu_ray_cast'
        else:
            self.rendering_technique = 'texture_mapping'
        
        # Actualizar renderizado
        if self.vtk_image:
            self._setup_volume_rendering()
    
    def on_preset_changed(self, index):
        """
        Manejador cuando se cambia el preset
        
        Args:
            index: Índice del preset seleccionado
        """
        presets = ["MRI-Default", "MRI-Soft-Tissue", "CT-Bones", "Custom"]
        self.preset = presets[index]
        
        # Habilitar/deshabilitar edición de funciones personalizadas
        self.edit_opacity_button.setEnabled(self.preset == 'Custom')
        
        # Actualizar renderizado
        if self.vtk_image:
            self._setup_volume_rendering()
    
    def on_quality_changed(self, index):
        """
        Manejador cuando se cambia la calidad
        
        Args:
            index: Índice de la calidad seleccionada
        """
        qualities = ["low", "medium", "high"]
        self.quality = qualities[index]
        
        # Actualizar renderizado
        if self.vtk_image:
            self._setup_volume_rendering()
    
    def on_shading_toggled(self, enabled):
        """
        Manejador cuando se activa/desactiva el sombreado
        
        Args:
            enabled: True si se activa, False si se desactiva
        """
        self.use_shading = enabled
        
        # Actualizar renderizado
        if self.vtk_image:
            self._setup_volume_rendering()
    
    def on_opacity_scale_changed(self, value):
        """
        Manejador cuando se cambia la escala de opacidad
        
        Args:
            value: Nuevo valor del slider (1-100)
        """
        self.opacity_scale = value / 100.0
        
        # Actualizar renderizado
        if self.vtk_image:
            self._setup_volume_rendering()
    
    def on_clipping_toggled(self, enabled):
        """
        Manejador cuando se activa/desactiva el clipping
        
        Args:
            enabled: True si se activa, False si se desactiva
        """
        # Habilitar/deshabilitar sliders
        for slider in self.clip_sliders.values():
            slider.setEnabled(enabled)
        
        # Si se desactiva, resetear los sliders
        if not enabled:
            for slider in self.clip_sliders.values():
                slider.setValue(0)
        
        # Actualizar clipping planes
        if self.vtk_image and self.volume_actor:
            self._update_clipping_planes()
    
    def on_clip_slider_changed(self, axis, value):
        """
        Manejador cuando se cambia un slider de clipping
        
        Args:
            axis: Eje afectado ('x', 'y', 'z')
            value: Nuevo valor del slider (0-100)
        """
        if self.vtk_image and self.volume_actor:
            self._update_clipping_planes()
    
    def set_view_orientation(self, orientation):
        """
        Establece una orientación predefinida para la cámara
        
        Args:
            orientation: Orientación ('axial', 'sagittal', 'coronal', 'isometric')
        """
        if not self.renderer:
            return
        
        # Obtener cámara
        camera = self.renderer.GetActiveCamera()
        
        # Configurar según orientación
        if orientation == 'axial':
            camera.SetViewUp(0, 1, 0)
            camera.SetPosition(0, 0, 1)
            camera.SetFocalPoint(0, 0, 0)
        elif orientation == 'sagittal':
            camera.SetViewUp(0, 0, 1)
            camera.SetPosition(1, 0, 0)
            camera.SetFocalPoint(0, 0, 0)
        elif orientation == 'coronal':
            camera.SetViewUp(0, 0, 1)
            camera.SetPosition(0, 1, 0)
            camera.SetFocalPoint(0, 0, 0)
        elif orientation == 'isometric':
            camera.SetViewUp(0, 0, 1)
            camera.SetPosition(1, 1, 1)
            camera.SetFocalPoint(0, 0, 0)
        
        # Resetear cámara y actualizar
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
    
    def edit_opacity_function(self):
        """Abre un cuadro de diálogo para editar la función de opacidad personalizada"""
        # Solo permitir edición en modo Custom
        if self.preset != 'Custom':
            self.preset_combo.setCurrentText('Custom')
            self.preset = 'Custom'
        
        # Implementación básica: usar rangos de la imagen para crear puntos
        if not self.vtk_image or not self.custom_opacity_points:
            # Si no hay puntos personalizados, crear algunos por defecto
            scalar_range = self.vtk_image.GetScalarRange()
            min_val = scalar_range[0]
            max_val = scalar_range[1]
            range_size = max_val - min_val
            
            # Crear puntos equidistantes
            self.custom_opacity_points = [
                (min_val, 0.0),
                (min_val + range_size * 0.25, 0.0),
                (min_val + range_size * 0.5, 0.3),
                (min_val + range_size * 0.75, 0.7),
                (max_val, 1.0)
            ]
            
            # Crear puntos de color por defecto
            self.custom_color_points = [
                (min_val, 0.0, 0.0, 0.0),
                (min_val + range_size * 0.25, 0.0, 0.0, 0.5),
                (min_val + range_size * 0.5, 0.0, 0.5, 0.5),
                (min_val + range_size * 0.75, 0.5, 0.0, 0.0),
                (max_val, 1.0, 1.0, 1.0)
            ]
        
        # En una implementación completa, aquí se abriría un diálogo con controles
        # para editar los puntos de opacidad y color. Por simplicidad, solo
        # actualizamos el renderizado con los puntos por defecto.
        
        # Actualizar renderizado
        self._setup_volume_rendering()
        
        # Notificar al usuario
        print("Función de opacidad personalizada aplicada.")
        
    def capture_view(self):
        """Captura la vista actual como imagen"""
        if not self.vtk_widget or not self.vtk_image:
            return
        
        try:
            # Crear filtro para capturar ventana
            window_to_image = vtk.vtkWindowToImageFilter()
            window_to_image.SetInput(self.vtk_widget.GetRenderWindow())
            window_to_image.Update()
            
            # Mostrar diálogo para guardar archivo
            from PyQt5.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Captura",
                "",
                "Imágenes PNG (*.png);;Imágenes JPG (*.jpg);;Todos los archivos (*.*)"
            )
            
            if not file_path:
                return
            
            # Determinar tipo de escritor según extensión
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            if ext == '.png':
                writer = vtk.vtkPNGWriter()
            elif ext == '.jpg' or ext == '.jpeg':
                writer = vtk.vtkJPEGWriter()
            else:
                # Por defecto usar PNG
                writer = vtk.vtkPNGWriter()
                if not ext:
                    file_path += '.png'
            
            # Guardar imagen
            writer.SetFileName(file_path)
            writer.SetInputConnection(window_to_image.GetOutputPort())
            writer.Write()
            
            print(f"Vista capturada y guardada en: {file_path}")
            
        except Exception as e:
            print(f"Error al capturar vista: {str(e)}")
    
    def set_prediction_overlay(self, prediction_data):
        """
        Añade una superposición de la predicción al volumen
        
        Args:
            prediction_data: Diccionario con datos de predicción
        """
        if not self.vtk_image or not prediction_data:
            return
        
        if 'segmentation' not in prediction_data:
            print("ADVERTENCIA: No hay datos de segmentación en la predicción")
            return
        
        # Obtener segmentación
        segmentation = prediction_data['segmentation']
        
        # Convertir a formato VTK
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
        
        # Crear modelo de superficie para la segmentación
        contour = vtk.vtkContourFilter()
        contour.SetInputData(seg_vtk)
        contour.SetValue(0, 0.5)  # Nivel de isosuperficie
        
        # Suavizar la superficie
        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputConnection(contour.GetOutputPort())
        smoother.SetNumberOfIterations(15)
        smoother.SetRelaxationFactor(0.1)
        smoother.Update()
        
        # Crear mapper para la superficie
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(smoother.GetOutputPort())
        
        # Crear actor para la superficie
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        
        # Configurar color (rojo semitransparente)
        actor.GetProperty().SetColor(1.0, 0.0, 0.0)
        actor.GetProperty().SetOpacity(0.5)
        
        # Añadir actor al renderizador
        self.renderer.AddActor(actor)
        
        # Actualizar visualización
        self.vtk_widget.GetRenderWindow().Render()
    
    def clear(self):
        """Limpia la visualización"""
        # Limpiar datos
        self.vtk_image = None
        self.sitk_image = None
        
        # Limpiar renderer
        if self.volume_actor:
            self.renderer.RemoveViewProp(self.volume_actor)
            self.volume_actor = None
        
        # Limpiar todos los actores
        self.renderer.RemoveAllViewProps()
        
        # Actualizar ventana
        self.vtk_widget.GetRenderWindow().Render()
        
        # Deshabilitar controles
        self.edit_opacity_button.setEnabled(False)
        self.capture_button.setEnabled(False)
    
    def resizeEvent(self, event):
        """
        Manejador cuando se redimensiona el widget
        
        Args:
            event: Evento de redimensionamiento
        """
        super(VolumeWidget, self).resizeEvent(event)
        
        # Actualizar ventana de renderizado
        if self.vtk_widget:
            self.vtk_widget.GetRenderWindow().Render()