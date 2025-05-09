#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para generar un caso de prueba con imágenes sintéticas
Útil para probar la aplicación sin datos médicos reales
"""

import os
import numpy as np
import argparse
from pathlib import Path
import datetime

# Intentar importar SimpleITK para guardar imágenes en formato NIFTI
try:
    import SimpleITK as sitk
    SITK_AVAILABLE = True
except ImportError:
    SITK_AVAILABLE = False
    print("ADVERTENCIA: SimpleITK no está disponible. Se intentará usar nibabel.")
    
    # Intentar importar nibabel como alternativa
    try:
        import nibabel as nib
        NIBABEL_AVAILABLE = True
    except ImportError:
        NIBABEL_AVAILABLE = False
        print("ADVERTENCIA: Ni SimpleITK ni nibabel están disponibles. Use pip para instalar uno de ellos.")

def create_phantom_t2w(shape=(64, 64, 24), noise_level=0.1):
    """
    Crea una imagen sintética que simula una secuencia T2W de próstata
    
    Args:
        shape: Forma de la imagen (x, y, z)
        noise_level: Nivel de ruido a añadir (0-1)
    
    Returns:
        Array numpy con la imagen
    """
    # Crear array base
    phantom = np.zeros(shape)
    
    # Coordenadas del centro
    center = [dim // 2 for dim in shape]
    
    # Crear "próstata" (elipsoide central brillante)
    prostate_radii = [shape[0] // 4, shape[1] // 4, shape[2] // 3]
    
    for x in range(shape[0]):
        for y in range(shape[1]):
            for z in range(shape[2]):
                # Distancia normalizada al centro (elipsoide)
                dist = np.sqrt(
                    ((x - center[0]) / prostate_radii[0]) ** 2 +
                    ((y - center[1]) / prostate_radii[1]) ** 2 +
                    ((z - center[2]) / prostate_radii[2]) ** 2
                )
                
                if dist < 1.0:
                    # Interior de la próstata: más brillante en el centro
                    intensity = 0.7 * (1.0 - 0.5 * dist)
                    phantom[x, y, z] = intensity
                else:
                    # Exterior: tejidos circundantes, más oscuros
                    intensity = 0.2 * (1.0 / (1.0 + dist))
                    phantom[x, y, z] = intensity
    
    # Crear "vejiga" (estructura brillante en la parte superior)
    bladder_center = [center[0], center[1], center[2] - shape[2] // 3]
    bladder_radius = shape[2] // 4
    
    for x in range(shape[0]):
        for y in range(shape[1]):
            for z in range(max(0, bladder_center[2] - bladder_radius), min(shape[2], bladder_center[2] + bladder_radius)):
                # Distancia al centro de la vejiga
                dist = np.sqrt(
                    (x - bladder_center[0]) ** 2 +
                    (y - bladder_center[1]) ** 2 +
                    (z - bladder_center[2]) ** 2
                )
                
                if dist < bladder_radius:
                    # Interior de la vejiga: muy brillante
                    intensity = 0.9 * (1.0 - dist / bladder_radius)
                    phantom[x, y, z] = max(phantom[x, y, z], intensity)
    
    # Crear una "lesión" (área oscura dentro de la próstata)
    lesion_center = [
        center[0] + shape[0] // 8,
        center[1] - shape[1] // 8,
        center[2]
    ]
    lesion_radius = shape[0] // 10
    
    for x in range(max(0, lesion_center[0] - lesion_radius), min(shape[0], lesion_center[0] + lesion_radius)):
        for y in range(max(0, lesion_center[1] - lesion_radius), min(shape[1], lesion_center[1] + lesion_radius)):
            for z in range(max(0, lesion_center[2] - lesion_radius), min(shape[2], lesion_center[2] + lesion_radius)):
                # Distancia al centro de la lesión
                dist = np.sqrt(
                    (x - lesion_center[0]) ** 2 +
                    (y - lesion_center[1]) ** 2 +
                    (z - lesion_center[2]) ** 2
                )
                
                if dist < lesion_radius:
                    # Lesión oscura
                    reduction = 0.7 * (1.0 - dist / lesion_radius)
                    phantom[x, y, z] *= (1.0 - reduction)
    
    # Añadir ruido
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, phantom.shape)
        phantom += noise
        
        # Asegurar rango válido
        phantom = np.clip(phantom, 0, 1)
    
    # Multiplicar por 1000 para tener un rango similar a datos médicos reales
    phantom *= 1000
    
    return phantom

def create_phantom_adc(t2w_phantom, shape=(64, 64, 24), noise_level=0.15):
    """
    Crea una imagen sintética que simula una secuencia ADC de próstata
    basada en la imagen T2W
    
    Args:
        t2w_phantom: Imagen T2W sintética
        shape: Forma de la imagen (x, y, z)
        noise_level: Nivel de ruido a añadir (0-1)
    
    Returns:
        Array numpy con la imagen
    """
    # Crear array base
    phantom = np.zeros(shape)
    
    # Coordenadas del centro
    center = [dim // 2 for dim in shape]
    
    # Invertir contraste de T2W para ADC (próstata más oscura)
    phantom = 1000 - (t2w_phantom / 2)
    
    # Hacer la lesión más brillante en ADC (restricción de difusión)
    lesion_center = [
        center[0] + shape[0] // 8,
        center[1] - shape[1] // 8,
        center[2]
    ]
    lesion_radius = shape[0] // 10
    
    for x in range(max(0, lesion_center[0] - lesion_radius), min(shape[0], lesion_center[0] + lesion_radius)):
        for y in range(max(0, lesion_center[1] - lesion_radius), min(shape[1], lesion_center[1] + lesion_radius)):
            for z in range(max(0, lesion_center[2] - lesion_radius), min(shape[2], lesion_center[2] + lesion_radius)):
                # Distancia al centro de la lesión
                dist = np.sqrt(
                    (x - lesion_center[0]) ** 2 +
                    (y - lesion_center[1]) ** 2 +
                    (z - lesion_center[2]) ** 2
                )
                
                if dist < lesion_radius:
                    # Lesión brillante en ADC
                    increase = 1.5 * (1.0 - dist / lesion_radius)
                    phantom[x, y, z] *= (1.0 + increase)
    
    # Añadir ruido
    if noise_level > 0:
        noise = np.random.normal(0, noise_level * 100, phantom.shape)
        phantom += noise
        
        # Asegurar rango válido
        phantom = np.clip(phantom, 0, 1500)
    
    return phantom

def create_segmentation_mask(shape=(64, 64, 24), lesion_center=None, lesion_radius=None):
    """
    Crea una máscara de segmentación con una lesión
    
    Args:
        shape: Forma de la imagen (x, y, z)
        lesion_center: Centro de la lesión [x, y, z] (opcional)
        lesion_radius: Radio de la lesión (opcional)
    
    Returns:
        Array numpy con la máscara (0: fondo, 1: lesión)
    """
    # Crear máscara vacía
    mask = np.zeros(shape)
    
    # Coordenadas del centro
    center = [dim // 2 for dim in shape]
    
    # Si no se especifica centro de lesión, usar posición predeterminada
    if lesion_center is None:
        lesion_center = [
            center[0] + shape[0] // 8,
            center[1] - shape[1] // 8,
            center[2]
        ]
    
    # Si no se especifica radio, usar valor predeterminado
    if lesion_radius is None:
        lesion_radius = shape[0] // 10
    
    # Crear lesión
    for x in range(max(0, lesion_center[0] - lesion_radius), min(shape[0], lesion_center[0] + lesion_radius)):
        for y in range(max(0, lesion_center[1] - lesion_radius), min(shape[1], lesion_center[1] + lesion_radius)):
            for z in range(max(0, lesion_center[2] - lesion_radius), min(shape[2], lesion_center[2] + lesion_radius)):
                # Distancia al centro de la lesión
                dist = np.sqrt(
                    (x - lesion_center[0]) ** 2 +
                    (y - lesion_center[1]) ** 2 +
                    (z - lesion_center[2]) ** 2
                )
                
                if dist < lesion_radius:
                    mask[x, y, z] = 1
    
    return mask

def save_nifti(data, filename, spacing=(1.0, 1.0, 3.0)):
    """
    Guarda un array como archivo NIFTI
    
    Args:
        data: Array numpy con los datos
        filename: Nombre del archivo a guardar
        spacing: Espaciado de voxels en mm (x, y, z)
    
    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    try:
        if SITK_AVAILABLE:
            # Usar SimpleITK
            img = sitk.GetImageFromArray(data.astype(np.float32))
            img.SetSpacing(spacing)
            sitk.WriteImage(img, filename)
            return True
        elif NIBABEL_AVAILABLE:
            # Usar nibabel
            affine = np.eye(4)
            affine[0, 0] = spacing[0]
            affine[1, 1] = spacing[1]
            affine[2, 2] = spacing[2]
            nifti_img = nib.Nifti1Image(data.astype(np.float32), affine)
            nib.save(nifti_img, filename)
            return True
        else:
            print(f"ERROR: No se puede guardar {filename}, instale SimpleITK o nibabel.")
            return False
    except Exception as e:
        print(f"Error al guardar {filename}: {str(e)}")
        return False

def main():
    """Función principal"""
    # Parsear argumentos
    parser = argparse.ArgumentParser(description="Genera imágenes sintéticas para pruebas")
    parser.add_argument("--output", "-o", default="test_case", help="Directorio de salida")
    parser.add_argument("--size", "-s", type=int, default=64, help="Tamaño de la imagen (isométrico)")
    parser.add_argument("--name", "-n", default="test_patient", help="Nombre del paciente")
    parser.add_argument("--noise", type=float, default=0.1, help="Nivel de ruido (0-1)")
    args = parser.parse_args()
    
    # Verificar que al menos una biblioteca de imágenes está disponible
    if not SITK_AVAILABLE and not NIBABEL_AVAILABLE:
        print("ERROR: Se requiere SimpleITK o nibabel para guardar imágenes.")
        print("Instale con: pip install SimpleITK")
        print("         o: pip install nibabel")
        return
    
    # Crear directorio de salida
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Tamaño de la imagen
    size_xy = args.size
    size_z = max(12, size_xy // 3)  # Asegurar al menos 12 cortes
    shape = (size_xy, size_xy, size_z)
    
    print(f"Generando caso de prueba en: {output_dir}")
    print(f"Tamaño de imagen: {shape}")
    
    # Crear imagen T2W
    print("Generando imagen T2W...")
    t2w = create_phantom_t2w(shape, args.noise)
    
    # Crear imagen ADC
    print("Generando imagen ADC...")
    adc = create_phantom_adc(t2w, shape, args.noise * 1.5)
    
    # Crear máscara de segmentación
    print("Generando máscara de segmentación...")
    segmentation = create_segmentation_mask(shape)
    
    # Guardar imágenes
    case_id = f"test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"Guardando archivos con ID: {case_id}")
    
    # Guardar T2W
    t2w_file = output_dir / f"{case_id}_t2w.nii.gz"
    if save_nifti(t2w, str(t2w_file)):
        print(f"✓ T2W guardado: {t2w_file}")
    
    # Guardar ADC
    adc_file = output_dir / f"{case_id}_adc.nii.gz"
    if save_nifti(adc, str(adc_file)):
        print(f"✓ ADC guardado: {adc_file}")
    
    # Guardar segmentación
    seg_file = output_dir / f"{case_id}_seg.nii.gz"
    if save_nifti(segmentation, str(seg_file)):
        print(f"✓ Segmentación guardada: {seg_file}")
    
    # Crear archivo JSON con metadatos
    import json
    metadata = {
        "case_id": case_id,
        "patient_name": args.name,
        "patient_id": f"ID_{case_id}",
        "patient_age": 65,
        "study_date": datetime.datetime.now().strftime('%Y%m%d'),
        "institution": "Hospital Virtual",
        "modality": "MR",
        "sequences": ["t2w", "adc"],
        "files": [
            {"path": str(t2w_file), "sequence_type": "t2w"},
            {"path": str(adc_file), "sequence_type": "adc"}
        ],
        "synthetic": True,
        "lesions": [
            {
                "id": 1,
                "location": "Zona periférica derecha",
                "volume_mm3": 450.5,
                "max_diameter_mm": 12.3,
                "probability": 0.85,
                "severity": "Alta"
            }
        ]
    }
    
    meta_file = output_dir / f"{case_id}_metadata.json"
    with open(meta_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✓ Metadatos guardados: {meta_file}")
    
    print("\nGeneración completada. Para usar este caso en la aplicación:")
    print(f"1. Abra la aplicación")
    print(f"2. Seleccione Archivo > Abrir Caso")
    print(f"3. Navegue hasta: {output_dir}")
    print(f"4. Seleccione los archivos {case_id}_t2w.nii.gz y {case_id}_adc.nii.gz")

if __name__ == "__main__":
    main()