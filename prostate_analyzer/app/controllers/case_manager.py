#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gestor de casos para la aplicación de análisis de próstata
Se encarga de cargar, organizar y gestionar los casos y sus archivos
"""

import os
import sys
import json
import datetime
from pathlib import Path
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

# Intentar importar SimpleITK para procesamiento avanzado
try:
    import SimpleITK as sitk
    SITK_AVAILABLE = True
except ImportError:
    SITK_AVAILABLE = False
    print("ADVERTENCIA: SimpleITK no está disponible. Algunas funcionalidades estarán limitadas.")

from config import TEMP_DIR, SequenceType, ensure_directories_exist

class CaseManager(QObject):
    """
    Gestor de casos para la aplicación
    Se encarga de cargar, organizar y gestionar los casos de estudio
    """
    
    # Señales
    case_loaded = pyqtSignal(dict)  # Emitida cuando un caso es cargado correctamente
    case_closed = pyqtSignal()      # Emitida cuando se cierra un caso
    case_saved = pyqtSignal(str)    # Emitida cuando un caso es guardado (ruta)
    
    def __init__(self, parent=None):
        super(CaseManager, self).__init__(parent)
        
        # Asegurar que existan los directorios necesarios
        ensure_directories_exist()
        
        # Lista de casos cargados
        self.cases = []
        
        # Caso actualmente activo
        self.current_case_index = -1
    
    def load_case(self, file_paths):
        """
        Carga un nuevo caso a partir de una lista de archivos
        
        Args:
            file_paths: Lista de rutas a archivos de imágenes médicas
        
        Returns:
            Diccionario con datos del caso cargado
        
        Raises:
            ValueError: Si no se pudieron cargar los archivos
        """
        # Verificar que hay archivos
        if not file_paths:
            raise ValueError("No se proporcionaron archivos para cargar")
        
        # Crear un nuevo caso
        case = {
            'id': f"case_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'name': self._generate_case_name(file_paths),
            'files': [],
            'metadata': {},
            'created_date': datetime.datetime.now().isoformat(),
            'modified_date': datetime.datetime.now().isoformat(),
            'has_changes': False
        }
        
        # Procesar cada archivo
        for file_path in file_paths:
            try:
                file_info = self._process_file(file_path)
                case['files'].append(file_info)
            except Exception as e:
                print(f"Error procesando archivo {file_path}: {str(e)}")
                # Continuar con el siguiente archivo
        
        # Verificar que se hayan procesado archivos
        if not case['files']:
            raise ValueError("No se pudo procesar ninguno de los archivos proporcionados")
        
        # Extraer metadatos generales del caso desde el primer archivo
        self._extract_case_metadata(case)
        
        # Añadir el caso a la lista
        self.cases.append(case)
        
        # Establecer como caso actual
        self.current_case_index = len(self.cases) - 1
        
        # Emitir señal
        self.case_loaded.emit(case)
        
        return case
    
    def _generate_case_name(self, file_paths):
        """
        Genera un nombre para el caso basado en el nombre de los archivos
        
        Args:
            file_paths: Lista de rutas de archivos
        
        Returns:
            Nombre generado para el caso
        """
        if not file_paths:
            return "Caso sin nombre"
        
        # Usar el nombre del directorio como nombre del caso
        first_file = file_paths[0]
        dir_name = os.path.basename(os.path.dirname(first_file))
        
        if dir_name:
            return f"Caso {dir_name}"
        else:
            # Si no hay directorio, usar el nombre del primer archivo
            base_name = os.path.basename(first_file)
            name, _ = os.path.splitext(base_name)
            return f"Caso {name}"
    
    def _process_file(self, file_path):
        """
        Procesa un archivo y extrae información
        
        Args:
            file_path: Ruta al archivo
        
        Returns:
            Diccionario con información del archivo
        
        Raises:
            ValueError: Si no se pudo procesar el archivo
        """
        # Intentar importar el módulo de carga de imágenes desde el paquete utils
        try:
            from app.utils.image_loader import load_medical_image
        except ImportError:
            # Si falla la importación, intentar desde el directorio local
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from utils.image_loader import load_medical_image
        
        # Intentar cargar la imagen médica
        file_info = load_medical_image(file_path)
        
        if not file_info:
            raise ValueError(f"No se pudo procesar el archivo {file_path}")
        
        # Intentar determinar el tipo de secuencia a partir del nombre de archivo
        file_name = os.path.basename(file_path).lower()
        
        if 't2' in file_name or 't2w' in file_name:
            file_info['sequence_type'] = 't2w'
        elif 'adc' in file_name:
            file_info['sequence_type'] = 'adc'
        elif 'dwi' in file_name or 'hbv' in file_name:
            file_info['sequence_type'] = 'dwi'
        elif 'cor' in file_name:
            file_info['sequence_type'] = 'cor'
        elif 'sag' in file_name:
            file_info['sequence_type'] = 'sag'
        else:
            file_info['sequence_type'] = 'unknown'
        
        return file_info
    
    def _extract_case_metadata(self, case):
        """
        Extrae metadatos generales del caso a partir de los archivos
        
        Args:
            case: Diccionario con datos del caso
        """
        if not case['files']:
            return
        
        # Usar el primer archivo para extraer metadatos generales
        first_file = case['files'][0]
        
        if 'metadata' in first_file:
            # Extraer metadatos comunes
            # Estos pueden variar según el formato del archivo
            metadata = first_file['metadata']
            
            # Buscar ID de paciente en metadatos DICOM
            patient_id = None
            for key in metadata:
                if isinstance(key, str) and ('patientid' in key.lower() or 'patient id' in key.lower()):
                    patient_id = metadata[key]
                    break
            
            if patient_id:
                case['metadata']['patient_id'] = patient_id
            
            # Buscar fecha de estudio
            study_date = None
            for key in metadata:
                if isinstance(key, str) and ('study date' in key.lower() or 'studydate' in key.lower()):
                    study_date = metadata[key]
                    break
            
            if study_date:
                case['metadata']['study_date'] = study_date
    
    def get_case_count(self):
        """
        Obtiene el número de casos cargados
        
        Returns:
            Número de casos
        """
        return len(self.cases)
    
    def get_current_case(self):
        """
        Obtiene el caso actualmente activo
        
        Returns:
            Diccionario con datos del caso o None si no hay caso activo
        """
        if self.current_case_index < 0 or self.current_case_index >= len(self.cases):
            return None
        
        return self.cases[self.current_case_index]
    
    def close_current_case(self):
        """
        Cierra el caso actualmente activo
        """
        if self.current_case_index < 0 or self.current_case_index >= len(self.cases):
            return
        
        # Eliminar caso de la lista
        self.cases.pop(self.current_case_index)
        
        # Actualizar índice del caso actual
        if len(self.cases) == 0:
            self.current_case_index = -1
        elif self.current_case_index >= len(self.cases):
            self.current_case_index = len(self.cases) - 1
        
        # Emitir señal
        self.case_closed.emit()
    
    def close_all_cases(self):
        """
        Cierra todos los casos abiertos
        """
        self.cases = []
        self.current_case_index = -1
        self.case_closed.emit()
    
    def has_open_cases(self):
        """
        Verifica si hay casos abiertos
        
        Returns:
            True si hay casos abiertos, False en caso contrario
        """
        return len(self.cases) > 0
    
    def current_case_has_changes(self):
        """
        Verifica si el caso actual tiene cambios sin guardar
        
        Returns:
            True si hay cambios, False en caso contrario
        """
        if self.current_case_index < 0 or self.current_case_index >= len(self.cases):
            return False
        
        return self.cases[self.current_case_index].get('has_changes', False)
    
    def save_current_case(self, file_path=None):
        """
        Guarda el caso actual
        
        Args:
            file_path: Ruta donde guardar el caso (opcional)
        
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        if self.current_case_index < 0 or self.current_case_index >= len(self.cases):
            return False
        
        current_case = self.cases[self.current_case_index]
        
        # Si no se especifica ruta, usar directorio temporal
        if not file_path:
            file_path = os.path.join(TEMP_DIR, f"{current_case['id']}.json")
        
        try:
            # Actualizar fecha de modificación
            current_case['modified_date'] = datetime.datetime.now().isoformat()
            
            # Guardar en archivo JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                # Filtrar datos grandes que no se pueden serializar
                save_data = current_case.copy()
                for file_info in save_data['files']:
                    # Eliminar arrays numpy que no son serializables
                    if 'array' in file_info:
                        del file_info['array']
                
                json.dump(save_data, f, indent=2)
            
            # Marcar como sin cambios
            current_case['has_changes'] = False
            
            # Emitir señal
            self.case_saved.emit(file_path)
            
            return True
        except Exception as e:
            print(f"Error al guardar caso: {str(e)}")
            return False
    
    def load_case_from_file(self, file_path):
        """
        Carga un caso desde un archivo
        
        Args:
            file_path: Ruta al archivo
        
        Returns:
            Diccionario con datos del caso cargado o None si hubo un error
        
        Raises:
            ValueError: Si no se pudo cargar el archivo
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                case = json.load(f)
            
            # Verificar que el caso tiene la estructura correcta
            if not all(key in case for key in ['id', 'name', 'files', 'metadata']):
                raise ValueError("El archivo no contiene un caso válido")
            
            # Añadir el caso a la lista
            self.cases.append(case)
            
            # Establecer como caso actual
            self.current_case_index = len(self.cases) - 1
            
            # Emitir señal
            self.case_loaded.emit(case)
            
            return case
        except Exception as e:
            print(f"Error al cargar caso desde archivo: {str(e)}")
            raise ValueError(f"No se pudo cargar el caso desde {file_path}: {str(e)}")
    
    def add_file_to_current_case(self, file_path):
        """
        Añade un archivo al caso actual
        
        Args:
            file_path: Ruta al archivo a añadir
        
        Returns:
            True si se añadió correctamente, False en caso contrario
        
        Raises:
            ValueError: Si no hay caso actual o si no se pudo procesar el archivo
        """
        if self.current_case_index < 0 or self.current_case_index >= len(self.cases):
            raise ValueError("No hay caso actual")
        
        current_case = self.cases[self.current_case_index]
        
        try:
            # Procesar archivo
            file_info = self._process_file(file_path)
            
            # Añadir al caso
            current_case['files'].append(file_info)
            
            # Marcar como modificado
            current_case['modified_date'] = datetime.datetime.now().isoformat()
            current_case['has_changes'] = True
            
            # Emitir señal
            self.case_loaded.emit(current_case)
            
            return True
        except Exception as e:
            print(f"Error al añadir archivo al caso: {str(e)}")
            raise ValueError(f"No se pudo añadir el archivo {file_path}: {str(e)}")
    
    def update_current_case_metadata(self, metadata):
        """
        Actualiza los metadatos del caso actual
        
        Args:
            metadata: Diccionario con metadatos a actualizar
        
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        if self.current_case_index < 0 or self.current_case_index >= len(self.cases):
            return False
        
        current_case = self.cases[self.current_case_index]
        
        # Actualizar metadatos
        current_case['metadata'].update(metadata)
        
        # Marcar como modificado
        current_case['modified_date'] = datetime.datetime.now().isoformat()
        current_case['has_changes'] = True
        
        return True
    
    def set_current_case_prediction_results(self, results):
        """
        Establece los resultados de predicción para el caso actual
        
        Args:
            results: Diccionario con resultados de predicción
        
        Returns:
            True si se estableció correctamente, False en caso contrario
        """
        if self.current_case_index < 0 or self.current_case_index >= len(self.cases):
            return False
        
        current_case = self.cases[self.current_case_index]
        
        # Almacenar resultados
        current_case['prediction_results'] = results
        
        # Marcar como modificado
        current_case['modified_date'] = datetime.datetime.now().isoformat()
        current_case['has_changes'] = True
        
        return True
    
    def get_current_case_prediction_results(self):
        """
        Obtiene los resultados de predicción del caso actual
        
        Returns:
            Diccionario con resultados de predicción o None si no hay resultados
        """
        if self.current_case_index < 0 or self.current_case_index >= len(self.cases):
            return None
        
        current_case = self.cases[self.current_case_index]
        
        return current_case.get('prediction_results')
    
    def get_file_paths_by_sequence(self, sequence_type=None):
        """
        Obtiene las rutas de archivos por tipo de secuencia para el caso actual
        
        Args:
            sequence_type: Tipo de secuencia a filtrar (opcional)
        
        Returns:
            Lista de rutas de archivos o diccionario {sequence_type: [paths]}
        """
        if self.current_case_index < 0 or self.current_case_index >= len(self.cases):
            return [] if sequence_type else {}
        
        current_case = self.cases[self.current_case_index]
        
        if sequence_type:
            # Filtrar por tipo de secuencia
            return [
                file_info['path'] 
                for file_info in current_case['files'] 
                if file_info.get('sequence_type') == sequence_type
            ]
        else:
            # Agrupar por tipo de secuencia
            result = {}
            for file_info in current_case['files']:
                seq_type = file_info.get('sequence_type', 'unknown')
                if seq_type not in result:
                    result[seq_type] = []
                result[seq_type].append(file_info['path'])
            
            return result
    
    def remove_file_from_current_case(self, file_index):
        """
        Elimina un archivo del caso actual
        
        Args:
            file_index: Índice del archivo a eliminar
        
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        if self.current_case_index < 0 or self.current_case_index >= len(self.cases):
            return False
        
        current_case = self.cases[self.current_case_index]
        
        if file_index < 0 or file_index >= len(current_case['files']):
            return False
        
        # Eliminar archivo
        del current_case['files'][file_index]
        
        # Marcar como modificado
        current_case['modified_date'] = datetime.datetime.now().isoformat()
        current_case['has_changes'] = True
        
        # Emitir señal
        self.case_loaded.emit(current_case)
        
        return True