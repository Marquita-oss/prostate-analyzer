#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuración global para la aplicación de análisis de próstata
"""

import os
from enum import Enum

# Información de la aplicación
APP_NAME = "Prostate Analyzer 3D"
APP_VERSION = "1.0.0"
ORGANIZATION_NAME = "Medical Research Labs"

# Rutas principales
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(BASE_DIR, "resources")
MODELS_DIR = os.path.join(RESOURCES_DIR, "models")
ICONS_DIR = os.path.join(RESOURCES_DIR, "icons")
STYLES_DIR = os.path.join(RESOURCES_DIR, "styles")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Configuración de la UI
SPLASH_DURATION = 2000  # en milisegundos
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
DEFAULT_FONT_SIZE = 10
DEFAULT_COLORMAP = "gray"

# Valores por defecto para visualización
DEFAULT_WINDOW_LEVEL = 40
DEFAULT_WINDOW_WIDTH = 400
SLICE_VIEW_MIN_SIZE = 300
VOLUME_VIEW_MIN_SIZE = 400

# Tipos de secuencia
class SequenceType(str, Enum):
    """Tipos de secuencias de RM disponibles"""
    T2W = "t2w"
    ADC = "adc"
    DWI = "dwi"
    COR = "cor"
    SAG = "sag"
    UNKNOWN = "unknown"

# Configuración del modelo de predicción
MODEL_THRESHOLD = 0.5  # Umbral de confianza para detección
DEFAULT_MODEL_FILE = "prostate_segmentation_model.pth"

# Formatos de archivo soportados
SUPPORTED_FORMATS = [".nii", ".nii.gz", ".mha", ".dicom", ".dcm"]

# Configuración del reporte
REPORT_TEMPLATE_FILE = os.path.join(RESOURCES_DIR, "templates", "report_template.html")
REPORT_LOGO_FILE = os.path.join(RESOURCES_DIR, "images", "logo.png")
DEFAULT_REPORT_DIR = os.path.expanduser("~/Documents/ProstateAnalyzer")

# Creación de directorios necesarios
def ensure_directories_exist():
    """Asegura que existan los directorios necesarios"""
    for directory in [TEMP_DIR, DEFAULT_REPORT_DIR]:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except Exception as e:
                print(f"No se pudo crear el directorio {directory}: {e}")