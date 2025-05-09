#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para instalación del Analizador de Imágenes de Próstata
"""

import os
import sys
import shutil
from setuptools import setup, find_packages

# Verificar que estamos en Python 3.6+
if sys.version_info < (3, 6):
    sys.exit('Se requiere Python 3.6 o superior')

# Crear directorios de recursos si no existen
def create_resource_dirs():
    """Crea los directorios de recursos necesarios"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    resources_dir = os.path.join(base_dir, 'resources')
    
    # Subdirectorios
    dirs = [
        os.path.join(resources_dir, 'icons'),
        os.path.join(resources_dir, 'styles'),
        os.path.join(resources_dir, 'models'),
        os.path.join(resources_dir, 'templates'),
        os.path.join(resources_dir, 'images'),
        os.path.join(base_dir, 'temp')
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"Directorio creado: {d}")

# Instalar archivo de estilo CSS
def install_styles():
    """Copia los archivos de estilo a los directorios correctos"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    styles_dir = os.path.join(base_dir, 'resources', 'styles')
    
    # Verificar si existe dark_theme.qss
    src_style = os.path.join(base_dir, 'app', 'dark_theme.qss')
    if os.path.exists(src_style):
        dst_style = os.path.join(styles_dir, 'dark_theme.qss')
        shutil.copy2(src_style, dst_style)
        print(f"Estilo copiado: {dst_style}")

# Crear directorios
create_resource_dirs()

# Instalar estilos
install_styles()

# Configuración del paquete
setup(
    name="prostate_analyzer",
    version="1.0.0",
    description="Analizador de Imágenes de Próstata con IA",
    author="Medical Research Labs",
    author_email="info@medicalresearchlabs.example.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'PyQt5>=5.15.0',
        'numpy>=1.19.0',
        'SimpleITK>=2.0.0',
        'vtk>=9.0.0',
        'monai>=0.9.0',
        'torch>=1.9.0',
        'matplotlib>=3.3.0',
        'reportlab>=3.5.0',
        'nibabel>=3.2.0',
        'scikit-image>=0.18.0',
    ],
    entry_points={
        'console_scripts': [
            'prostate_analyzer=main:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Healthcare Industry',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
    ],
    python_requires='>=3.6',
)

print("\nInstalación completada. Ejecute 'prostate_analyzer' para iniciar la aplicación.")