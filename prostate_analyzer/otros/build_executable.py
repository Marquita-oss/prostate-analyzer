#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para empaquetar la aplicación de análisis de próstata en un ejecutable
Utiliza PyInstaller para crear un ejecutable independiente con todas las dependencias
"""

import os
import sys
import shutil
import platform
import subprocess
import site
import pkg_resources

# Verificar que PyInstaller está instalado
try:
    import PyInstaller
except ImportError:
    print("PyInstaller no está instalado. Instalando...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

# Obtener directorio base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Determinar sistema operativo
OS_TYPE = platform.system()  # 'Windows', 'Linux', 'Darwin' (macOS)

def find_package_data_dir(package_name):
    """
    Encuentra el directorio de datos de un paquete instalado
    
    Args:
        package_name: Nombre del paquete
    
    Returns:
        Ruta al directorio de datos o None si no se encuentra
    """
    try:
        package = pkg_resources.get_distribution(package_name)
        package_dir = package.location
        return os.path.join(package_dir, package_name)
    except pkg_resources.DistributionNotFound:
        return None

def create_executable():
    """Crea el ejecutable con PyInstaller"""
    print(f"Creando ejecutable para {OS_TYPE}...")
    
    # Nombre del ejecutable
    exe_name = "ProstatisAnalyzer"
    
    # Icono específico por plataforma
    icon_path = ""
    if OS_TYPE == 'Windows':
        icon_path = os.path.join(BASE_DIR, "resources", "icons", "app_icon.ico")
    elif OS_TYPE == 'Darwin':
        icon_path = os.path.join(BASE_DIR, "resources", "icons", "app_icon.icns")
    else:  # Linux
        icon_path = os.path.join(BASE_DIR, "resources", "icons", "app_icon.png")
    
    # Verificar que existe el icono
    if not os.path.exists(icon_path):
        print(f"Advertencia: No se encontró el icono en {icon_path}")
        icon_arg = ""
    else:
        icon_arg = f"--icon={icon_path}"
    
    # Archivos para incluir
    include_files = [
        os.path.join(BASE_DIR, "resources"),
    ]
    
    # Directorio de datos para PyInstaller
    datas = []
    for file_path in include_files:
        if os.path.exists(file_path):
            rel_path = os.path.relpath(file_path, BASE_DIR)
            datas.append(f"{file_path}{os.pathsep}{rel_path}")
    
    # Incluir datos de paquetes críticos
    packages_to_include = ["monai", "torch", "vtk"]
    for package in packages_to_include:
        package_dir = find_package_data_dir(package)
        if package_dir and os.path.exists(package_dir):
            datas.append(f"{package_dir}{os.pathsep}{package}")
    
    # Convertir lista de datos a argumento para PyInstaller
    datas_arg = "--add-data=" + " --add-data=".join(datas) if datas else ""
    
    # Paquetes ocultos que podrían ser necesarios
    hidden_imports = [
        "skimage",
        "sklearn",
        "SimpleITK",
        "vtk",
        "torch",
        "monai",
        "numpy",
        "reportlab.graphics.barcode",
        "reportlab.graphics.charts",
        "reportlab.graphics.shapes",
        "reportlab.lib.styles",
        "reportlab.platypus",
        "reportlab.pdfgen",
        "matplotlib.pyplot",
        "matplotlib.backends.backend_agg",
        "matplotlib.backends.backend_pdf",
        "nibabel"
    ]
    hidden_imports_arg = "--hidden-import=" + " --hidden-import=".join(hidden_imports)
    
    # Comando base de PyInstaller
    cmd = [
        "pyinstaller",
        "--name", exe_name,
        "--onefile",
        "--windowed",
        icon_arg,
        datas_arg,
        hidden_imports_arg,
        "--clean",
        "--noconfirm",
        os.path.join(BASE_DIR, "main.py")
    ]
    
    # Filtrar argumentos vacíos
    cmd = [arg for arg in cmd if arg]
    
    # Ejecutar comando
    print("Ejecutando PyInstaller...")
    print(f"Comando: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        
        # Ruta al ejecutable generado
        if OS_TYPE == 'Windows':
            exe_path = os.path.join(BASE_DIR, "dist", f"{exe_name}.exe")
        elif OS_TYPE == 'Darwin':
            exe_path = os.path.join(BASE_DIR, "dist", f"{exe_name}.app")
        else:  # Linux
            exe_path = os.path.join(BASE_DIR, "dist", exe_name)
        
        print(f"\nEjecutable creado exitosamente: {exe_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error al crear el ejecutable: {str(e)}")
        return False

def create_installer():
    """Crea un instalador para el ejecutable (solo Windows)"""
    if OS_TYPE != 'Windows':
        print("La creación de instaladores solo está implementada para Windows.")
        return
    
    print("Creando instalador para Windows...")
    
    try:
        # Verificar que NSIS está instalado
        nsis_path = shutil.which("makensis")
        if not nsis_path:
            print("NSIS no está instalado o no está en el PATH.")
            print("Descargue NSIS desde https://nsis.sourceforge.io/Download")
            return False
        
        # Crear script NSIS
        installer_script = os.path.join(BASE_DIR, "installer.nsi")
        with open(installer_script, 'w') as f:
            f.write(f'''
!include "MUI2.nsh"

; Definir nombre del instalador
Name "Prostate Analyzer 3D"
OutFile "dist/ProstateAnalyzer3D_Setup.exe"

; Carpeta de instalación por defecto
InstallDir "$PROGRAMFILES\\Prostate Analyzer 3D"

; Pedir privilegios de administrador
RequestExecutionLevel admin

;--------------------------------
; Páginas del instalador
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Páginas del desinstalador
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Idioma
!insertmacro MUI_LANGUAGE "Spanish"

;--------------------------------
; Sección principal
Section "Instalar"
  SetOutPath "$INSTDIR"
  
  ; Añadir archivos
  File "dist\\ProstatisAnalyzer.exe"
  File /r "resources\\*.*"
  
  ; Crear acceso directo en el escritorio
  CreateShortCut "$DESKTOP\\Prostate Analyzer 3D.lnk" "$INSTDIR\\ProstatisAnalyzer.exe"
  
  ; Crear acceso directo en el menú de inicio
  CreateDirectory "$SMPROGRAMS\\Prostate Analyzer 3D"
  CreateShortCut "$SMPROGRAMS\\Prostate Analyzer 3D\\Prostate Analyzer 3D.lnk" "$INSTDIR\\ProstatisAnalyzer.exe"
  CreateShortCut "$SMPROGRAMS\\Prostate Analyzer 3D\\Desinstalar.lnk" "$INSTDIR\\uninstall.exe"
  
  ; Crear desinstalador
  WriteUninstaller "$INSTDIR\\uninstall.exe"
SectionEnd

;--------------------------------
; Sección de desinstalación
Section "Uninstall"
  ; Eliminar archivos
  Delete "$INSTDIR\\ProstatisAnalyzer.exe"
  RMDir /r "$INSTDIR\\resources"
  Delete "$INSTDIR\\uninstall.exe"
  
  ; Eliminar accesos directos
  Delete "$DESKTOP\\Prostate Analyzer 3D.lnk"
  Delete "$SMPROGRAMS\\Prostate Analyzer 3D\\Prostate Analyzer 3D.lnk"
  Delete "$SMPROGRAMS\\Prostate Analyzer 3D\\Desinstalar.lnk"
  RMDir "$SMPROGRAMS\\Prostate Analyzer 3D"
  
  ; Eliminar directorio de instalación
  RMDir "$INSTDIR"
SectionEnd
''')
        
        # Ejecutar NSIS
        subprocess.check_call(["makensis", installer_script])
        
        # Verificar que se creó el instalador
        installer_path = os.path.join(BASE_DIR, "dist", "ProstateAnalyzer3D_Setup.exe")
        if os.path.exists(installer_path):
            print(f"\nInstalador creado exitosamente: {installer_path}")
            return True
        else:
            print("Error: No se pudo encontrar el instalador generado.")
            return False
        
    except Exception as e:
        print(f"Error al crear el instalador: {str(e)}")
        return False

if __name__ == "__main__":
    # Verificar argumentos
    create_exe = True
    create_inst = False
    
    if len(sys.argv) > 1:
        if "no-exe" in sys.argv:
            create_exe = False
        if "installer" in sys.argv:
            create_inst = True
    
    # Crear ejecutable
    if create_exe:
        success = create_executable()
        if not success:
            sys.exit(1)
    
    # Crear instalador si se solicita
    if create_inst:
        if OS_TYPE == 'Windows':
            create_installer()
        else:
            print(f"La creación de instaladores no está implementada para {OS_TYPE}.")
            print("Solo está disponible para Windows.")
    
    print("\nProceso completado.")