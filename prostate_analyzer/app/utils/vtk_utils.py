#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilidades para trabajar con VTK en la aplicación
Funciones auxiliares para visualización, renderizado y procesamiento 3D
"""

import os
import numpy as np
import vtk

# Intentar importar SimpleITK para conversiones
try:
    import SimpleITK as sitk
    SITK_AVAILABLE = True
except ImportError:
    SITK_AVAILABLE = False
    print("ADVERTENCIA: SimpleITK no está disponible. Algunas funcionalidades estarán limitadas.")

def setup_vtk_renderer(renderer, background_color=(0.1, 0.1, 0.1)):
    """
    Configura un renderizador VTK con ajustes comunes
    
    Args:
        renderer: Renderizador VTK a configurar
        background_color: Color de fondo (R, G, B)
    
    Returns:
        El renderizador configurado
    """
    # Establecer color de fondo
    renderer.SetBackground(background_color)
    
    # Activar iluminación de dos caras
    renderer.LightFollowCameraOn()
    renderer.TwoSidedLightingOn()
    
    # Activar sombreado de Phong por defecto
    renderer.UseFXAAOn()  # Antialiasing
    
    return renderer

def create_image_actor(vtk_image, color_window=None, color_level=None):
    """
    Crea un actor para una imagen VTK con mapa de colores
    
    Args:
        vtk_image: Imagen VTK
        color_window: Ancho de ventana (opcional)
        color_level: Nivel de ventana (opcional)
    
    Returns:
        Actor VTK para la imagen
    """
    # Crear mapeador de colores
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
    
    # Crear actor
    actor = vtk.vtkImageActor()
    actor.GetMapper().SetInputConnection(mapper.GetOutputPort())
    
    return actor

def create_slice_actor(vtk_image, orientation='axial', slice_index=None, color_window=None, color_level=None):
    """
    Crea un actor para un corte específico de una imagen 3D
    
    Args:
        vtk_image: Imagen VTK 3D
        orientation: Orientación del corte ('axial', 'sagittal', 'coronal')
        slice_index: Índice del corte (si es None, se usa el corte central)
        color_window: Ancho de ventana (opcional)
        color_level: Nivel de ventana (opcional)
    
    Returns:
        Actor VTK para el corte
    """
    # Obtener dimensiones de la imagen
    dims = vtk_image.GetDimensions()
    
    # Calcular índice de corte central si no se especifica
    if slice_index is None:
        if orientation == 'axial':
            slice_index = dims[2] // 2
        elif orientation == 'sagittal':
            slice_index = dims[0] // 2
        elif orientation == 'coronal':
            slice_index = dims[1] // 2
    
    # Crear extractor de corte (reslice)
    reslice = vtk.vtkImageReslice()
    reslice.SetInputData(vtk_image)
    reslice.SetOutputDimensionality(2)  # Salida 2D
    
    # Configurar orientación del corte
    if orientation == 'axial':
        reslice.SetResliceAxesDirectionCosines(
            1, 0, 0,  # eje x
            0, 1, 0,  # eje y
            0, 0, 1   # eje z
        )
        # Posición del corte en Z
        origin = vtk_image.GetOrigin()
        spacing = vtk_image.GetSpacing()
        reslice.SetResliceAxesOrigin(
            origin[0] + dims[0] * spacing[0] / 2,
            origin[1] + dims[1] * spacing[1] / 2,
            origin[2] + slice_index * spacing[2]
        )
    elif orientation == 'sagittal':
        reslice.SetResliceAxesDirectionCosines(
            0, 0, 1,  # eje x (era z)
            0, 1, 0,  # eje y
            1, 0, 0   # eje z (era x)
        )
        # Posición del corte en X
        origin = vtk_image.GetOrigin()
        spacing = vtk_image.GetSpacing()
        reslice.SetResliceAxesOrigin(
            origin[0] + slice_index * spacing[0],
            origin[1] + dims[1] * spacing[1] / 2,
            origin[2] + dims[2] * spacing[2] / 2
        )
    elif orientation == 'coronal':
        reslice.SetResliceAxesDirectionCosines(
            1, 0, 0,  # eje x
            0, 0, 1,  # eje y (era z)
            0, 1, 0   # eje z (era y)
        )
        # Posición del corte en Y
        origin = vtk_image.GetOrigin()
        spacing = vtk_image.GetSpacing()
        reslice.SetResliceAxesOrigin(
            origin[0] + dims[0] * spacing[0] / 2,
            origin[1] + slice_index * spacing[1],
            origin[2] + dims[2] * spacing[2] / 2
        )
    
    reslice.SetInterpolationModeToLinear()
    reslice.Update()
    
    # Crear actor para el corte
    slice_actor = create_image_actor(reslice.GetOutput(), color_window, color_level)
    
    return slice_actor

def create_volume_property(preset='MRI-Default'):
    """
    Crea propiedades para renderizado volumétrico según un preset
    
    Args:
        preset: Preset predefinido ('MRI-Default', 'MRI-Soft-Tissue', 'CT-Bones', 'Custom')
    
    Returns:
        Propiedades de volumen VTK configuradas
    """
    volume_property = vtk.vtkVolumeProperty()
    
    # Configurar según el preset
    if preset == 'MRI-Default':
        # Configuración para MRI general
        volume_property.SetColor(create_mri_default_color_function())
        volume_property.SetScalarOpacity(create_mri_default_opacity_function())
        volume_property.SetAmbient(0.2)
        volume_property.SetDiffuse(0.9)
        volume_property.SetSpecular(0.3)
        volume_property.SetSpecularPower(15.0)
    elif preset == 'MRI-Soft-Tissue':
        # Configuración para tejidos blandos en MRI
        volume_property.SetColor(create_mri_soft_tissue_color_function())
        volume_property.SetScalarOpacity(create_mri_soft_tissue_opacity_function())
        volume_property.SetAmbient(0.2)
        volume_property.SetDiffuse(0.9)
        volume_property.SetSpecular(0.2)
        volume_property.SetSpecularPower(10.0)
    elif preset == 'CT-Bones':
        # Configuración para huesos en CT
        volume_property.SetColor(create_ct_bone_color_function())
        volume_property.SetScalarOpacity(create_ct_bone_opacity_function())
        volume_property.SetAmbient(0.1)
        volume_property.SetDiffuse(0.9)
        volume_property.SetSpecular(0.4)
        volume_property.SetSpecularPower(30.0)
    else:  # Custom o preset no reconocido
        # Configuración personalizada (usando valores intermedios)
        volume_property.SetColor(create_default_color_function())
        volume_property.SetScalarOpacity(create_default_opacity_function())
        volume_property.SetAmbient(0.2)
        volume_property.SetDiffuse(0.7)
        volume_property.SetSpecular(0.3)
        volume_property.SetSpecularPower(15.0)
    
    # Configuraciones comunes
    volume_property.SetInterpolationTypeToLinear()
    volume_property.ShadeOn()
    
    return volume_property

def create_default_color_function():
    """
    Crea una función de transferencia de color por defecto
    
    Returns:
        Función de transferencia de color VTK
    """
    color_function = vtk.vtkColorTransferFunction()
    color_function.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
    color_function.AddRGBPoint(0.5, 0.5, 0.5, 0.5)
    color_function.AddRGBPoint(1.0, 1.0, 1.0, 1.0)
    return color_function

def create_default_opacity_function():
    """
    Crea una función de opacidad por defecto
    
    Returns:
        Función de opacidad VTK
    """
    opacity_function = vtk.vtkPiecewiseFunction()
    opacity_function.AddPoint(0.0, 0.0)
    opacity_function.AddPoint(0.3, 0.0)
    opacity_function.AddPoint(0.7, 0.5)
    opacity_function.AddPoint(1.0, 1.0)
    return opacity_function

def create_mri_default_color_function():
    """
    Crea una función de transferencia de color para MRI general
    
    Returns:
        Función de transferencia de color VTK
    """
    color_function = vtk.vtkColorTransferFunction()
    color_function.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
    color_function.AddRGBPoint(0.2, 0.0, 0.0, 0.8)  # Azul oscuro para valores bajos
    color_function.AddRGBPoint(0.5, 0.0, 0.8, 0.8)  # Cian para valores medios
    color_function.AddRGBPoint(0.8, 0.8, 0.8, 0.0)  # Amarillo para valores altos
    color_function.AddRGBPoint(1.0, 1.0, 0.0, 0.0)  # Rojo para valores máximos
    return color_function

def create_mri_default_opacity_function():
    """
    Crea una función de opacidad para MRI general
    
    Returns:
        Función de opacidad VTK
    """
    opacity_function = vtk.vtkPiecewiseFunction()
    opacity_function.AddPoint(0.0, 0.0)
    opacity_function.AddPoint(0.1, 0.0)
    opacity_function.AddPoint(0.3, 0.2)
    opacity_function.AddPoint(0.6, 0.5)
    opacity_function.AddPoint(1.0, 0.8)
    return opacity_function

def create_mri_soft_tissue_color_function():
    """
    Crea una función de transferencia de color para tejidos blandos en MRI
    
    Returns:
        Función de transferencia de color VTK
    """
    color_function = vtk.vtkColorTransferFunction()
    color_function.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
    color_function.AddRGBPoint(0.3, 0.6, 0.3, 0.0)  # Verde para valores bajos-medios
    color_function.AddRGBPoint(0.6, 0.8, 0.6, 0.2)  # Verde más claro para valores medios-altos
    color_function.AddRGBPoint(1.0, 1.0, 0.8, 0.6)  # Amarillo claro para valores máximos
    return color_function

def create_mri_soft_tissue_opacity_function():
    """
    Crea una función de opacidad para tejidos blandos en MRI
    
    Returns:
        Función de opacidad VTK
    """
    opacity_function = vtk.vtkPiecewiseFunction()
    opacity_function.AddPoint(0.0, 0.0)
    opacity_function.AddPoint(0.2, 0.0)
    opacity_function.AddPoint(0.4, 0.2)
    opacity_function.AddPoint(0.7, 0.6)
    opacity_function.AddPoint(1.0, 0.9)
    return opacity_function

def create_ct_bone_color_function():
    """
    Crea una función de transferencia de color para huesos en CT
    
    Returns:
        Función de transferencia de color VTK
    """
    color_function = vtk.vtkColorTransferFunction()
    color_function.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
    color_function.AddRGBPoint(0.4, 0.5, 0.3, 0.1)  # Marrón-verde para valores medios-bajos
    color_function.AddRGBPoint(0.7, 0.8, 0.7, 0.5)  # Marfil para valores medios-altos
    color_function.AddRGBPoint(1.0, 1.0, 0.9, 0.8)  # Blanco hueso para valores máximos
    return color_function

def create_ct_bone_opacity_function():
    """
    Crea una función de opacidad para huesos en CT
    
    Returns:
        Función de opacidad VTK
    """
    opacity_function = vtk.vtkPiecewiseFunction()
    opacity_function.AddPoint(0.0, 0.0)
    opacity_function.AddPoint(0.3, 0.0)
    opacity_function.AddPoint(0.5, 0.2)
    opacity_function.AddPoint(0.8, 0.8)
    opacity_function.AddPoint(1.0, 1.0)
    return opacity_function

def convert_sitk_to_vtk(sitk_image):
    """
    Convierte una imagen SimpleITK a formato VTK
    
    Args:
        sitk_image: Imagen SimpleITK
    
    Returns:
        Imagen VTK
    """
    if not SITK_AVAILABLE:
        raise ImportError("SimpleITK no está disponible para la conversión")
        
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
    
    # Convertir array a VTK
    flat_array = array.flatten(order='F')  # VTK usa orden Fortran
    vtk_array = vtk.util.numpy_support.numpy_to_vtk(
        num_array=flat_array,
        deep=True,
        array_type=vtk_dtype
    )
    
    # Asignar array a la imagen
    vtk_image.GetPointData().SetScalars(vtk_array)
    
    return vtk_image

def convert_vtk_to_sitk(vtk_image):
    """
    Convierte una imagen VTK a formato SimpleITK
    
    Args:
        vtk_image: Imagen VTK
    
    Returns:
        Imagen SimpleITK
    """
    if not SITK_AVAILABLE:
        raise ImportError("SimpleITK no está disponible para la conversión")
    
    # Obtener dimensiones, origen y espaciado
    dims = vtk_image.GetDimensions()
    origin = vtk_image.GetOrigin()
    spacing = vtk_image.GetSpacing()
    
    # Obtener array de datos
    vtk_array = vtk_image.GetPointData().GetScalars()
    numpy_array = vtk.util.numpy_support.vtk_to_numpy(vtk_array)
    
    # Reorganizar el array para SimpleITK (cambiar de orden Fortran a C)
    numpy_array = numpy_array.reshape(dims[2], dims[1], dims[0], order='F')
    numpy_array = np.transpose(numpy_array, (2, 1, 0))
    
    # Crear imagen SimpleITK
    sitk_image = sitk.GetImageFromArray(numpy_array)
    sitk_image.SetOrigin(origin)
    sitk_image.SetSpacing(spacing)
    
    return sitk_image

def create_surface_from_segmentation(segmentation_array, smoothing=True):
    """
    Crea una superficie 3D a partir de una segmentación
    
    Args:
        segmentation_array: Array numpy de segmentación (0-1)
        smoothing: Si se debe aplicar suavizado a la superficie
    
    Returns:
        Actor VTK para la superficie
    """
    # Crear imagen VTK desde el array
    vtk_image = vtk.vtkImageData()
    dims = segmentation_array.shape
    vtk_image.SetDimensions(dims[2], dims[1], dims[0])
    vtk_image.SetOrigin(0, 0, 0)
    vtk_image.SetSpacing(1, 1, 1)
    
    # Convertir a tipo de datos adecuado para contorneo
    vtk_image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
    
    # Copiar datos
    flat_array = segmentation_array.flatten(order='F')
    vtk_array = vtk.util.numpy_support.numpy_to_vtk(
        num_array=flat_array,
        deep=True,
        array_type=vtk.VTK_UNSIGNED_CHAR
    )
    vtk_image.GetPointData().SetScalars(vtk_array)
    
    # Crear contorno (marching cubes)
    contour = vtk.vtkContourFilter()
    contour.SetInputData(vtk_image)
    contour.SetValue(0, 0.5)  # Valor de isosuperficie (borde entre 0 y 1)
    
    # Aplicar suavizado si se especifica
    if smoothing:
        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputConnection(contour.GetOutputPort())
        smoother.SetNumberOfIterations(15)
        smoother.SetRelaxationFactor(0.1)
        smoother.Update()
        surface = smoother.GetOutput()
    else:
        contour.Update()
        surface = contour.GetOutput()
    
    # Calcular normales para mejor iluminación
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(surface)
    normals.ComputePointNormalsOn()
    normals.ComputeCellNormalsOn()
    normals.SplittingOff()
    normals.Update()
    
    # Crear mapper
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())
    
    # Crear actor
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    
    # Configurar propiedades
    actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # Rojo
    actor.GetProperty().SetOpacity(0.5)  # Semitransparente
    actor.GetProperty().SetSpecular(0.3)
    actor.GetProperty().SetSpecularPower(20)
    
    return actor

def create_annotation_text(text, position, font_size=12, color=(1.0, 1.0, 1.0)):
    """
    Crea un actor de texto para anotaciones en la escena 3D
    
    Args:
        text: Texto de la anotación
        position: Posición (x, y, z) del texto
        font_size: Tamaño de fuente
        color: Color del texto (r, g, b)
    
    Returns:
        Actor VTK de texto
    """
    # Crear objeto de texto
    text_actor = vtk.vtkTextActor3D()
    text_actor.SetInput(text)
    
    # Establecer posición
    text_actor.SetPosition(position)
    
    # Configurar texto
    text_prop = text_actor.GetTextProperty()
    text_prop.SetFontSize(font_size)
    text_prop.SetColor(color)
    text_prop.SetBold(True)
    text_prop.SetShadow(True)
    
    return text_actor

def create_axes_actor(length=100.0, labels=True):
    """
    Crea un actor de ejes 3D para referencia espacial
    
    Args:
        length: Longitud de los ejes
        labels: Si se deben mostrar etiquetas (X, Y, Z)
    
    Returns:
        Actor VTK de ejes
    """
    # Crear ejes
    axes = vtk.vtkAxesActor()
    axes.SetTotalLength(length, length, length)
    
    # Configurar etiquetas
    if not labels:
        axes.SetXAxisLabelVisibility(0)
        axes.SetYAxisLabelVisibility(0)
        axes.SetZAxisLabelVisibility(0)
    
    return axes

def capture_render_window(render_window, file_path, magnification=1):
    """
    Captura una imagen de una ventana de renderizado VTK
    
    Args:
        render_window: Ventana de renderizado VTK
        file_path: Ruta donde guardar la imagen
        magnification: Factor de ampliación para mayor resolución
    
    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    try:
        # Crear filtro para capturar ventana
        window_to_image = vtk.vtkWindowToImageFilter()
        window_to_image.SetInput(render_window)
        window_to_image.SetMagnification(magnification)
        window_to_image.Update()
        
        # Determinar tipo de escritor según extensión
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
        print(f"Error al capturar ventana: {str(e)}")
        return False

def create_orientaton_marker(render_window, scale=0.15, position=(0.9, 0.9)):
    """
    Crea un marcador de orientación para la ventana de renderizado
    
    Args:
        render_window: Ventana de renderizado VTK
        scale: Tamaño relativo del marcador
        position: Posición relativa en la ventana (0-1, 0-1)
    
    Returns:
        Widget de orientación
    """
    # Crear ejes
    axes = vtk.vtkAxesActor()
    axes.SetShaftTypeToCylinder()
    axes.SetXAxisLabelText("R")  # Right
    axes.SetYAxisLabelText("A")  # Anterior
    axes.SetZAxisLabelText("S")  # Superior
    
    # Propiedades de etiquetas
    axes.GetXAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
    axes.GetYAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
    axes.GetZAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
    
    # Crear widget de orientación
    orientation_marker = vtk.vtkOrientationMarkerWidget()
    orientation_marker.SetOrientationMarker(axes)
    orientation_marker.SetViewport(position[0] - scale, position[1] - scale, position[0], position[1])
    orientation_marker.SetInteractor(render_window.GetInteractor())
    orientation_marker.EnabledOn()
    orientation_marker.InteractiveOff()
    
    return orientation_marker