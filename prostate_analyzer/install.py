#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de instalación para Prostate Analyzer 3D
Crea la estructura de directorios y verifica las dependencias
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def check_dependencies():
    """Verifica si las dependencias están instaladas"""
    try:
        # Importar módulos críticos para verificar
        import PyQt5
        import numpy
        print("✓ PyQt5 y NumPy están instalados")
    except ImportError as e:
        print(f"✗ Error: {e}")
        print("Algunas dependencias críticas no están instaladas.")
        return False
    
    # Verificar dependencias opcionales
    optional_packages = {
        "vtk": "Visualización 3D",
        "SimpleITK": "Procesamiento de imágenes médicas",
        "monai": "Procesamiento avanzado",
        "torch": "Modelos de IA",
        "matplotlib": "Generación de gráficos",
        "reportlab": "Generación de PDF"
    }
    
    missing_optional = []
    for package, description in optional_packages.items():
        try:
            __import__(package)
            print(f"✓ {package} está instalado ({description})")
        except ImportError:
            missing_optional.append(f"{package} ({description})")
    
    if missing_optional:
        print("\nAdvertencia: Las siguientes dependencias opcionales no están instaladas:")
        for pkg in missing_optional:
            print(f"✗ {pkg}")
        print("\nAlgunas funcionalidades pueden estar limitadas.")
    
    return True

def create_directory_structure():
    """Crea la estructura de directorios necesaria"""
    print("Creando estructura de directorios...")
    
    # Directorios principales
    directories = [
        "app",
        "app/models",
        "app/views",
        "app/controllers",
        "app/utils",
        "resources",
        "resources/styles",
        "resources/icons",
        "resources/images",
        "resources/models",
        "data",
        "temp"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Directorio creado: {directory}")
    
    # Crear archivos __init__.py en cada paquete
    init_files = [
        "app/__init__.py",
        "app/models/__init__.py",
        "app/views/__init__.py",
        "app/controllers/__init__.py",
        "app/utils/__init__.py"
    ]
    
    for init_file in init_files:
        with open(init_file, 'w') as f:
            f.write('"""Paquete de la aplicación Prostate Analyzer 3D"""\n')
        print(f"✓ Archivo creado: {init_file}")
    
    print("Estructura de directorios creada correctamente.")

def install_requirements():
    """Instala las dependencias desde requirements.txt"""
    if not os.path.exists("requirements.txt"):
        print("Archivo requirements.txt no encontrado. Creando archivo con dependencias básicas...")
        with open("requirements.txt", "w") as f:
            f.write("PyQt5>=5.15.0\n")
            f.write("numpy>=1.19.0\n")
            f.write("SimpleITK>=2.0.0\n")
            f.write("vtk>=9.0.0\n")
            f.write("monai>=0.9.0\n")
            f.write("torch>=1.9.0\n")
            f.write("matplotlib>=3.3.0\n")
            f.write("reportlab>=3.5.0\n")
            f.write("nibabel>=3.2.0\n")
            f.write("scikit-image>=0.18.0\n")
    
    print("\nInstalando dependencias...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencias instaladas correctamente.")
    except subprocess.CalledProcessError:
        print("✗ Error al instalar dependencias.")
        print("Intente instalarlas manualmente con:")
        print("pip install -r requirements.txt")

def create_dummy_model():
    """Crea un modelo dummy para pruebas"""
    model_dir = "resources/models"
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, "prostate_segmentation_model.pth")
    
    if not os.path.exists(model_path):
        print("\nCreando modelo de ejemplo para pruebas...")
        try:
            # Crear archivo binario dummy
            with open(model_path, 'wb') as f:
                f.write(b'DUMMY_MODEL_FILE')
            print(f"✓ Modelo creado: {model_path}")
            
            # Crear archivo Python con funciones dummy
            with open(os.path.join(model_dir, "dummy_model.py"), 'w') as f:
                f.write("""# Modelo dummy para pruebas
import numpy as np

def predict(image):
    \"\"\"Función de predicción simulada\"\"\"
    shape = image.shape
    # Crear segmentación simulada (esfera en el centro)
    segmentation = np.zeros(shape)
    
    # Coordenadas del centro
    center = [dim // 2 for dim in shape]
    radius = min(shape) // 8
    
    # Crear una esfera
    for x in range(max(0, center[0] - radius), min(shape[0], center[0] + radius)):
        for y in range(max(0, center[1] - radius), min(shape[1], center[1] + radius)):
            for z in range(max(0, center[2] - radius), min(shape[2], center[2] + radius)):
                dist = np.sqrt((x - center[0])**2 + (y - center[1])**2 + (z - center[2])**2)
                if dist < radius:
                    segmentation[x, y, z] = 1
    
    return segmentation

def get_dummy_results():
    \"\"\"Retorna resultados simulados\"\"\"
    return {
        'segmentation': np.ones((10, 10, 10)),  # Segmentación simulada
        'lesions': [
            {
                'id': 1,
                'volume_mm3': 450.5,
                'max_diameter_mm': 12.3,
                'centroid': [45.2, 65.7, 23.1],
                'probability': 0.85,
                'severity': "Alta"
            },
            {
                'id': 2,
                'volume_mm3': 210.8,
                'max_diameter_mm': 8.7,
                'centroid': [62.1, 48.3, 35.9],
                'probability': 0.65,
                'severity': "Media"
            }
        ],
        'num_lesions': 2,
        'has_significant_lesion': True,
        'total_lesion_volume': 661.3,
        'prediction_date': "2023-05-09 15:30:45"
    }
""")
            print(f"✓ Archivo modelo dummy creado: {os.path.join(model_dir, 'dummy_model.py')}")
        except Exception as e:
            print(f"✗ Error al crear modelo dummy: {e}")

def create_empty_qss():
    """Crea un archivo QSS vacío si no existe"""
    qss_dir = "resources/styles"
    os.makedirs(qss_dir, exist_ok=True)
    
    qss_path = os.path.join(qss_dir, "dark_theme.qss")
    
    if not os.path.exists(qss_path):
        print("\nCreando archivo de estilo QSS básico...")
        try:
            with open(qss_path, 'w') as f:
                f.write("""/* 
  Tema Oscuro para Prostate Analyzer 3D
*/

/* Estilos generales */
QWidget {
    background-color: #1e1e1e;
    color: #f0f0f0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}

/* Ventana principal */
QMainWindow {
    background-color: #151515;
    border: none;
}

/* Menús */
QMenuBar {
    background-color: #151515;
    color: #f0f0f0;
}

QMenuBar::item:selected, QMenuBar::item:pressed {
    background-color: #3d3d3d;
}

QMenu {
    background-color: #252525;
    border: 1px solid #2d2d2d;
}

QMenu::item:selected {
    background-color: #3d3d3d;
}

/* Barras de herramientas */
QToolBar {
    background-color: #252525;
    border: none;
}

QToolButton:hover {
    background-color: #3d3d3d;
}

/* Botones */
QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 3px;
    padding: 5px 15px;
}

QPushButton:hover {
    background-color: #3d3d3d;
}

QPushButton:pressed {
    background-color: #505050;
}

QPushButton:disabled {
    background-color: #252525;
    color: #777777;
}
""")
            print(f"✓ Archivo QSS creado: {qss_path}")
        except Exception as e:
            print(f"✗ Error al crear archivo QSS: {e}")

def run_icon_generator():
    """Ejecuta el generador de iconos si existe"""
    icon_generator = "app/utils/create_app_icons.py"
    
    if os.path.exists(icon_generator):
        print("\nEjecutando generador de iconos...")
        try:
            subprocess.check_call([sys.executable, icon_generator])
            print("✓ Iconos generados correctamente.")
        except subprocess.CalledProcessError:
            print("✗ Error al generar iconos.")
            print("Puede generarlos manualmente ejecutando:")
            print(f"python {icon_generator}")
    else:
        print("\nGenerador de iconos no encontrado.")
        print("Si tiene el archivo create_app_icons.py, colóquelo en app/utils/ y ejecútelo.")

def main():
    """Función principal"""
    print("=" * 60)
    print(" Instalación de Prostate Analyzer 3D ".center(60, "="))
    print("=" * 60)
    
    # Verificar Python
    python_version = sys.version_info
    print(f"Versión de Python: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 7):
        print("✗ Se requiere Python 3.7 o superior.")
        sys.exit(1)
    
    # Sistema operativo
    system = platform.system()
    print(f"Sistema operativo: {system}")
    
    # Crear estructura
    create_directory_structure()
    
    # Instalar dependencias
    user_input = input("\n¿Desea instalar las dependencias ahora? (s/n): ")
    if user_input.lower() in ['s', 'si', 'y', 'yes']:
        install_requirements()
    
    # Verificar dependencias
    print("\nVerificando dependencias instaladas...")
    check_dependencies()
    
    # Crear modelo dummy
    create_dummy_model()
    
    # Crear archivo QSS
    create_empty_qss()
    
    # Ejecutar generador de iconos
    run_icon_generator()
    
    print("\n" + "=" * 60)
    print(" Instalación Completada ".center(60, "="))
    print("=" * 60)
    print("\nPara ejecutar la aplicación:")
    print("python main.py")
    
    # Si estamos en Windows, podemos crear un archivo .bat
    if system == "Windows":
        with open("run.bat", "w") as f:
            f.write("@echo off\n")
            f.write("python main.py\n")
            f.write("pause\n")
        print("O simplemente haga doble clic en run.bat")

if __name__ == "__main__":
    main()