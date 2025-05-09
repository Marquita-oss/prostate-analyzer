#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilidad para cargar imágenes médicas y verificar dependencias
"""

import os
import sys
import importlib
from typing import Tuple, List, Dict, Any, Optional

def check_dependencies() -> Tuple[bool, List[str]]:
    """
    Verifica que todas las dependencias necesarias estén disponibles
    
    Returns:
        Tupla (todas_disponibles, lista_faltantes)
    """
    # Lista de dependencias críticas
    critical_deps = [
        "PyQt5",
        "numpy",
        "vtk"
    ]
    
    # Lista de dependencias opcionales (mejoran funcionalidad pero no son críticas)
    optional_deps = [
        "SimpleITK",
        "monai",
        "torch",
        "nibabel",
        "matplotlib",
        "reportlab"
    ]
    
    # Verificar dependencias críticas
    missing_critical = []
    for dep in critical_deps:
        if not _check_module(dep):
            missing_critical.append(dep)
    
    # Verificar dependencias opcionales
    missing_optional = []
    for dep in optional_deps:
        if not _check_module(dep):
            missing_optional.append(dep)
    
    # Si falta alguna dependencia crítica, no se puede continuar
    if missing_critical:
        return False, missing_critical
    
    # Advertir sobre dependencias opcionales faltantes
    if missing_optional:
        print("ADVERTENCIA: Las siguientes dependencias opcionales no están disponibles:")
        for dep in missing_optional:
            print(f"- {dep}")
        print("Algunas funcionalidades pueden estar limitadas.")
    
    return True, missing_optional

def _check_module(module_name: str) -> bool:
    """
    Verifica si un módulo está disponible
    
    Args:
        module_name: Nombre del módulo a verificar
    
    Returns:
        True si está disponible, False en caso contrario
    """
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def load_medical_image(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Carga una imagen médica en diferentes formatos
    Intenta usar las bibliotecas disponibles en orden de preferencia
    
    Args:
        file_path: Ruta al archivo de imagen médica
    
    Returns:
        Diccionario con datos y metadatos de la imagen, o None si no se pudo cargar
    """
    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        print(f"Error: El archivo {file_path} no existe")
        return None
    
    # Determinar la extensión del archivo
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    # Si es .gz, obtener la extensión anterior
    if ext == '.gz':
        _, prev_ext = os.path.splitext(os.path.splitext(file_path)[0])
        ext = prev_ext.lower() + ext
    
    # Resultados por defecto
    result = {
        'path': file_path,
        'format': ext,
        'loaded_with': None,
        'array': None,
        'metadata': {}
    }
    
    # 1. Intentar con SimpleITK (mejor opción para imágenes médicas)
    if _check_module('SimpleITK'):
        try:
            import SimpleITK as sitk
            
            # Cargar imagen
            image = sitk.ReadImage(file_path)
            
            # Obtener array
            array = sitk.GetArrayFromImage(image)
            
            # Obtener metadatos
            metadata = {
                'dimensions': image.GetSize(),
                'spacing': image.GetSpacing(),
                'origin': image.GetOrigin(),
                'direction': image.GetDirection()
            }
            
            # Añadir metadatos DICOM si están disponibles
            for key in image.GetMetaDataKeys():
                metadata[key] = image.GetMetaData(key)
            
            # Actualizar resultado
            result['loaded_with'] = 'SimpleITK'
            result['array'] = array
            result['metadata'] = metadata
            
            return result
            
        except Exception as e:
            print(f"Error cargando con SimpleITK: {str(e)}")
            # Continuar con el siguiente método
    
    # 2. Intentar con nibabel (bueno para NIfTI)
    if _check_module('nibabel') and (ext == '.nii' or ext == '.nii.gz'):
        try:
            import nibabel as nib
            
            # Cargar imagen
            image = nib.load(file_path)
            
            # Obtener array
            array = image.get_fdata()
            
            # Obtener metadatos
            metadata = {
                'dimensions': image.shape,
                'affine': image.affine.tolist(),
                'header': {k: str(v) for k, v in image.header.items()}
            }
            
            # Actualizar resultado
            result['loaded_with'] = 'nibabel'
            result['array'] = array
            result['metadata'] = metadata
            
            return result
            
        except Exception as e:
            print(f"Error cargando con nibabel: {str(e)}")
            # Continuar con el siguiente método
    
    # 3. Intentar con VTK (opción de respaldo)
    if _check_module('vtk'):
        try:
            import vtk
            from vtk.util import numpy_support
            
            # Seleccionar el lector adecuado según la extensión
            if ext == '.mha' or ext == '.mhd':
                reader = vtk.vtkMetaImageReader()
            elif ext == '.nii' or ext == '.nii.gz':
                reader = vtk.vtkNIFTIImageReader()
            elif ext == '.dcm':
                reader = vtk.vtkDICOMImageReader()
            else:
                reader = vtk.vtkImageReader2()
            
            # Leer la imagen
            reader.SetFileName(file_path)
            reader.Update()
            
            # Obtener datos
            vtk_image = reader.GetOutput()
            
            # Convertir a array numpy
            vtk_array = vtk_image.GetPointData().GetScalars()
            dimensions = vtk_image.GetDimensions()
            numpy_array = numpy_support.vtk_to_numpy(vtk_array)
            numpy_array = numpy_array.reshape(dimensions[2], dimensions[1], dimensions[0])
            
            # Obtener metadatos disponibles
            metadata = {
                'dimensions': dimensions,
                'spacing': vtk_image.GetSpacing(),
                'origin': vtk_image.GetOrigin()
            }
            
            # Actualizar resultado
            result['loaded_with'] = 'VTK'
            result['array'] = numpy_array
            result['metadata'] = metadata
            
            return result
            
        except Exception as e:
            print(f"Error cargando con VTK: {str(e)}")
            # Continuar con método básico
    
    # 4. Método básico (último recurso, solo devuelve información básica)
    result['loaded_with'] = 'basic_info'
    result['metadata'] = {
        'file_size': os.path.getsize(file_path),
        'last_modified': os.path.getmtime(file_path)
    }
    
    return result

def get_supported_formats() -> List[str]:
    """
    Obtiene la lista de formatos de imagen médica soportados
    basado en las bibliotecas disponibles
    
    Returns:
        Lista de extensiones soportadas incluyendo el punto
    """
    # Formatos básicos soportados por defecto
    formats = ['.mha', '.nii', '.nii.gz']
    
    # Añadir formatos adicionales si SimpleITK está disponible
    if _check_module('SimpleITK'):
        formats.extend(['.dcm', '.ima', '.mhd', '.nhdr', '.nrrd', '.vtk', '.hdr'])
    
    # Añadir formatos adicionales si nibabel está disponible
    if _check_module('nibabel'):
        formats.extend(['.mgz', '.gii', '.trk'])
    
    # Eliminar duplicados y ordenar
    return sorted(list(set(formats)))

if __name__ == "__main__":
    # Prueba de funcionalidad
    deps_ok, missing = check_dependencies()
    print(f"Todas las dependencias críticas disponibles: {deps_ok}")
    if missing:
        print(f"Dependencias faltantes: {', '.join(missing)}")
    
    print(f"Formatos soportados: {', '.join(get_supported_formats())}")