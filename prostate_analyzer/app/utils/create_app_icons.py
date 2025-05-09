#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para crear iconos básicos para la aplicación
Genera iconos simples con formas geométricas y colores para la demostración
"""

import os
import sys
import math

# Intentar importar PIL para crear imágenes
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Error: PIL/Pillow no está instalado.")
    print("Para instalar: pip install Pillow")
    sys.exit(1)

def create_icon(filename, size=(256, 256), bg_color=(20, 20, 30), fg_color=(70, 130, 180), text=None):
    """
    Crea un icono simple con forma geométrica
    
    Args:
        filename: Nombre del archivo de salida
        size: Tamaño del icono (ancho, alto)
        bg_color: Color de fondo (R, G, B)
        fg_color: Color de la forma (R, G, B)
        text: Texto a mostrar en el centro (opcional)
    """
    # Crear imagen con fondo
    img = Image.new('RGBA', size, bg_color + (255,))
    draw = ImageDraw.Draw(img)
    
    # Calcular dimensiones para centrar la forma
    width, height = size
    center_x, center_y = width // 2, height // 2
    radius = min(width, height) // 3
    
    # Dibujar círculo exterior
    draw.ellipse(
        (center_x - radius, center_y - radius, 
         center_x + radius, center_y + radius), 
        fill=fg_color + (200,)
    )
    
    # Dibujar forma interior (cérvix estilizado)
    inner_radius = radius * 0.6
    draw.ellipse(
        (center_x - inner_radius, center_y - inner_radius, 
         center_x + inner_radius, center_y + inner_radius), 
        fill=(40, 80, 120, 200)
    )
    
    # Añadir puntos para simular lesiones
    spots = [
        (center_x + radius * 0.3, center_y - radius * 0.2, radius * 0.15),
        (center_x - radius * 0.4, center_y + radius * 0.3, radius * 0.18),
    ]
    
    for x, y, r in spots:
        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            fill=(180, 50, 50, 220)
        )
    
    # Añadir texto si se proporciona
    if text:
        try:
            # Intentar cargar fuente
            try:
                font = ImageFont.truetype("arial.ttf", size=radius // 2)
            except:
                # Usar fuente por defecto si no está disponible arial
                font = ImageFont.load_default()
            
            # Calcular posición del texto
            text_width = draw.textlength(text, font=font)
            text_position = (center_x - text_width // 2, center_y + radius + 10)
            
            # Dibujar texto
            draw.text(text_position, text, fill=(255, 255, 255, 255), font=font)
        except Exception as e:
            print(f"Error al añadir texto: {str(e)}")
    
    # Guardar imagen
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    img.save(filename)
    print(f"Icono creado: {filename}")
    
    return filename

def create_app_icons():
    """Crea conjunto de iconos para la aplicación"""
    print("Creando iconos para la aplicación...")
    
    # Crear directorio de iconos
    # icons_dir = "resources/icons"
    icons_dir = "prostate_analyzer/resources/icons"
    os.makedirs(icons_dir, exist_ok=True)
    
    # Iconos principales
    create_icon(
        os.path.join(icons_dir, "app_icon.png"), 
        size=(256, 256),
        bg_color=(20, 20, 30),
        fg_color=(70, 130, 180),
        text="MRI"
    )
    
    # Icono para Windows
    if os.name == 'nt':  # Solo en Windows
        create_icon(
            os.path.join(icons_dir, "app_icon.ico"), 
            size=(256, 256),
            bg_color=(20, 20, 30),
            fg_color=(70, 130, 180),
        )
    
    # Icono para macOS
    if os.name == 'posix' and sys.platform == 'darwin':  # Solo en macOS
        # Nota: Un archivo .icns real requiere múltiples tamaños y un formato especial
        # Para una demostración real, deberíamos usar iconutil o similar
        create_icon(
            os.path.join(icons_dir, "app_icon.icns"), 
            size=(256, 256),
            bg_color=(20, 20, 30),
            fg_color=(70, 130, 180),
        )
    
    # Iconos de funcionalidades
    functionality_icons = [
        ("open_icon.png", (64, 64), (40, 40, 50), (120, 180, 120)),
        ("save_icon.png", (64, 64), (40, 40, 50), (180, 180, 120)),
        ("report_icon.png", (64, 64), (40, 40, 50), (180, 120, 120)),
        ("predict_icon.png", (64, 64), (40, 40, 50), (120, 120, 180)),
        ("axial_icon.png", (64, 64), (40, 40, 50), (180, 140, 100)),
        ("sagittal_icon.png", (64, 64), (40, 40, 50), (100, 180, 140)),
        ("coronal_icon.png", (64, 64), (40, 40, 50), (140, 100, 180)),
        ("3d_icon.png", (64, 64), (40, 40, 50), (180, 100, 180)),
        ("close_icon.png", (64, 64), (40, 40, 50), (180, 100, 100)),
    ]
    
    for icon_name, size, bg_color, fg_color in functionality_icons:
        create_icon(
            os.path.join(icons_dir, icon_name), 
            size=size,
            bg_color=bg_color,
            fg_color=fg_color,
        )
    
    # Crear ícono para splash screen
    # splash_dir = "resources/images"
    splash_dir = "prostate_analyzer/resources/images"
    os.makedirs(splash_dir, exist_ok=True)
    
    create_icon(
        os.path.join(splash_dir, "splash.png"), 
        size=(600, 400),
        bg_color=(20, 20, 40),
        fg_color=(100, 160, 200),
        text="Prostate Analyzer 3D"
    )
    
    # Crear logo para reportes
    create_icon(
        os.path.join(splash_dir, "logo.png"), 
        size=(200, 200),
        bg_color=(255, 255, 255),
        fg_color=(70, 130, 180),
        text=""
    )
    
    print("Iconos creados correctamente.")

if __name__ == "__main__":
    create_app_icons()
    print("\nProceso completado.")