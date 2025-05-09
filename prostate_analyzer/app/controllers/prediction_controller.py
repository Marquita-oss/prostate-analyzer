#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Controlador de predicciones para la aplicación de análisis de próstata
Se encarga de gestionar la predicción de lesiones usando modelos de IA
"""

import os
import time
import json
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot

# Intentar importar torch/MONAI para el modelo de predicción
try:
    import torch
    import monai
    from monai.transforms import (
        LoadImaged,
        EnsureChannelFirstd,
        ScaleIntensityRanged,
        CropForegroundd,
        ToTensord,
        Compose
    )
    from monai.networks.nets import UNet
    from monai.inferers import sliding_window_inference
    
    TORCH_AVAILABLE = True
    MONAI_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    MONAI_AVAILABLE = False
    print("ADVERTENCIA: PyTorch y/o MONAI no están disponibles. La predicción con IA no estará disponible.")

# Intentar importar SimpleITK para procesar imágenes médicas
try:
    import SimpleITK as sitk
    SITK_AVAILABLE = True
except ImportError:
    SITK_AVAILABLE = False
    print("ADVERTENCIA: SimpleITK no está disponible. Algunas funcionalidades estarán limitadas.")

from config import MODELS_DIR, MODEL_THRESHOLD

class PredictionWorker(QThread):
    """
    Worker thread para realizar la predicción en segundo plano
    """
    # Señales
    prediction_result = pyqtSignal(dict)  # Emitida cuando la predicción finaliza con éxito
    prediction_error = pyqtSignal(str)    # Emitida cuando hay un error en la predicción
    progress_update = pyqtSignal(int)     # Emitida para actualizar el progreso (0-100)
    
    def __init__(self, case_data, model_path, device=None):
        super(PredictionWorker, self).__init__()
        self.case_data = case_data
        self.model_path = model_path
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
    
    def run(self):
        """Ejecuta la predicción en segundo plano"""
        try:
            # Verificar que las librerías necesarias están disponibles
            if not TORCH_AVAILABLE or not MONAI_AVAILABLE or not SITK_AVAILABLE:
                self.prediction_error.emit("No se pueden realizar predicciones porque faltan dependencias")
                return
            
            # Verificar que hay un caso cargado
            if not self.case_data or 'files' not in self.case_data:
                self.prediction_error.emit("No hay caso cargado para predicción")
                return
            
            # Actualizar progreso
            self.progress_update.emit(5)
            
            # Preparar datos para predicción
            prepared_data = self._prepare_data()
            if not prepared_data:
                self.prediction_error.emit("No se pudieron preparar los datos para predicción")
                return
            
            # Actualizar progreso
            self.progress_update.emit(30)
            
            # Cargar modelo
            model = self._load_model()
            if not model:
                self.prediction_error.emit("No se pudo cargar el modelo de IA")
                return
            
            # Actualizar progreso
            self.progress_update.emit(50)
            
            # Realizar predicción
            prediction_result = self._perform_prediction(model, prepared_data)
            
            # Actualizar progreso
            self.progress_update.emit(80)
            
            # Procesar y formatear resultados
            final_results = self._process_results(prediction_result)
            
            # Actualizar progreso
            self.progress_update.emit(100)
            
            # Emitir resultados
            self.prediction_result.emit(final_results)
            
        except Exception as e:
            self.prediction_error.emit(f"Error en predicción: {str(e)}")
    
    def _prepare_data(self):
        """
        Prepara los datos para el modelo de predicción
        
        Returns:
            Diccionario con datos preparados o None si hubo un error
        """
        try:
            # Buscar secuencias T2W y ADC en los archivos del caso
            t2w_file = None
            adc_file = None
            
            for file_info in self.case_data['files']:
                sequence_type = file_info.get('sequence_type', '').lower()
                if sequence_type == 't2w':
                    t2w_file = file_info['path']
                elif sequence_type == 'adc':
                    adc_file = file_info['path']
            
            # Verificar que tenemos ambas secuencias
            if not t2w_file or not adc_file:
                self.prediction_error.emit("Se requieren secuencias T2W y ADC para la predicción")
                return None
            
            # Cargar imágenes con SimpleITK
            t2w_image = sitk.ReadImage(t2w_file)
            adc_image = sitk.ReadImage(adc_file)
            
            # Verificar que las imágenes tienen dimensiones comparables
            t2w_size = t2w_image.GetSize()
            adc_size = adc_image.GetSize()
            
            if any(abs(t2w_size[i] - adc_size[i]) > 10 for i in range(3)):
                self.prediction_error.emit("Las secuencias T2W y ADC tienen dimensiones muy diferentes")
                return None
            
            # Convertir a arrays para preprocesamiento
            t2w_array = sitk.GetArrayFromImage(t2w_image)
            adc_array = sitk.GetArrayFromImage(adc_image)
            
            # Configurar transformaciones MONAI para preprocesamiento
            transforms = Compose([
                # Asegurar canal primero (batch, channel, dim1, dim2, dim3)
                lambda x: np.expand_dims(x, axis=0),
                
                # Normalizar intensidades
                lambda x: (x - x.min()) / (x.max() - x.min() + 1e-5),
                
                # Convertir a tensor PyTorch
                lambda x: torch.from_numpy(x.astype(np.float32))
            ])
            
            # Aplicar transformaciones
            t2w_tensor = transforms(t2w_array).to(self.device)
            adc_tensor = transforms(adc_array).to(self.device)
            
            # Combinar tensores en una entrada multicanal
            # (batch, 2_channels, dim1, dim2, dim3)
            input_tensor = torch.cat([t2w_tensor, adc_tensor], dim=0).unsqueeze(0)
            
            # Guardar metadatos de imagen para post-procesamiento
            image_metadata = {
                't2w_spacing': t2w_image.GetSpacing(),
                't2w_origin': t2w_image.GetOrigin(),
                't2w_direction': t2w_image.GetDirection(),
                't2w_size': t2w_image.GetSize(),
                'adc_spacing': adc_image.GetSpacing(),
                'adc_origin': adc_image.GetOrigin(),
                'adc_direction': adc_image.GetDirection(),
                'adc_size': adc_image.GetSize()
            }
            
            return {
                'input_tensor': input_tensor,
                'image_metadata': image_metadata,
                't2w_image': t2w_image,
                'adc_image': adc_image
            }
            
        except Exception as e:
            self.prediction_error.emit(f"Error preparando datos: {str(e)}")
            return None
    
    def _load_model(self):
        """
        Carga el modelo de predicción desde el archivo
        
        Returns:
            Modelo cargado o None si hubo un error
        """
        try:
            # Verificar que el archivo del modelo existe
            if not os.path.exists(self.model_path):
                self.prediction_error.emit(f"Archivo de modelo no encontrado: {self.model_path}")
                return None
            
            # Crear arquitectura del modelo
            # Nota: La arquitectura debe coincidir exactamente con la del modelo guardado
            model = UNet(
                spatial_dims=3,
                in_channels=2,  # T2W + ADC
                out_channels=2,  # Fondo + Lesión
                channels=(16, 32, 64, 128, 256),
                strides=(2, 2, 2, 2),
                num_res_units=2
            )
            
            # Cargar pesos del modelo
            model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            
            # Configurar para inferencia
            model.eval()
            model.to(self.device)
            
            return model
            
        except Exception as e:
            self.prediction_error.emit(f"Error cargando modelo: {str(e)}")
            return None
    
    def _perform_prediction(self, model, data):
        """
        Realiza la predicción con el modelo
        
        Args:
            model: Modelo cargado
            data: Datos preparados
        
        Returns:
            Resultado de la predicción o None si hubo un error
        """
        try:
            # Obtener tensor de entrada
            input_tensor = data['input_tensor']
            
            # Realizar inferencia con ventana deslizante para manejar grandes volúmenes
            with torch.no_grad():
                prediction = sliding_window_inference(
                    inputs=input_tensor,
                    roi_size=(96, 96, 16),  # Tamaño de ventana (ajustar según memoria disponible)
                    sw_batch_size=1,
                    predictor=model,
                    overlap=0.5  # 50% de superposición entre ventanas
                )
            
            # Aplicar softmax para obtener probabilidades
            prediction_softmax = torch.nn.functional.softmax(prediction, dim=1)
            
            # Obtener el canal de la clase positiva (lesión)
            prediction_lesion = prediction_softmax[:, 1].cpu().numpy()
            
            return {
                'lesion_probability': prediction_lesion,
                'image_metadata': data['image_metadata'],
                't2w_image': data['t2w_image'],
                'adc_image': data['adc_image']
            }
            
        except Exception as e:
            self.prediction_error.emit(f"Error realizando predicción: {str(e)}")
            return None
    
    def _process_results(self, prediction_result):
        """
        Procesa los resultados de la predicción
        
        Args:
            prediction_result: Resultado de la predicción
        
        Returns:
            Resultados procesados en formato adecuado para visualización
        """
        try:
            # Extraer información
            lesion_probability = prediction_result['lesion_probability'][0]  # Eliminar dim batch
            t2w_image = prediction_result['t2w_image']
            
            # Aplicar umbral para obtener segmentación binaria
            lesion_mask = (lesion_probability > MODEL_THRESHOLD).astype(np.float32)
            
            # Crear imagen de segmentación con SimpleITK
            segmentation = sitk.GetImageFromArray(lesion_mask)
            segmentation.SetSpacing(t2w_image.GetSpacing())
            segmentation.SetOrigin(t2w_image.GetOrigin())
            segmentation.SetDirection(t2w_image.GetDirection())
            
            # Analizar componentes conectados para identificar lesiones individuales
            connected_components = sitk.ConnectedComponent(sitk.Cast(segmentation, sitk.sitkUInt8))
            stats = sitk.LabelShapeStatisticsImageFilter()
            stats.Execute(connected_components)
            
            # Recopilar estadísticas de cada lesión
            lesions = []
            for label in stats.GetLabels():
                # Calcular volumen en mm³
                volume_mm3 = stats.GetPhysicalSize(label)
                
                # Calcular diámetro máximo en mm
                if hasattr(stats, 'GetPrincipalAxes'):
                    # Usar ejes principales si están disponibles
                    axes = stats.GetPrincipalAxes(label)
                    max_diameter = max([
                        np.linalg.norm(axes[0:3]),
                        np.linalg.norm(axes[3:6]),
                        np.linalg.norm(axes[6:9])
                    ])
                else:
                    # Aproximación simple basada en el volumen
                    max_diameter = 2 * ((3 * volume_mm3) / (4 * np.pi)) ** (1/3)
                
                # Obtener centroide (x, y, z)
                centroid = stats.GetCentroid(label)
                
                # Calcular score de probabilidad promedio para esta lesión
                label_mask = (sitk.GetArrayFromImage(connected_components) == label)
                mean_probability = np.mean(lesion_probability[label_mask])
                
                # Clasificar lesión según tamaño y probabilidad
                # Nota: estos umbrales son ejemplos y deberían ajustarse según validación clínica
                if volume_mm3 > 500 and mean_probability > 0.75:
                    severity = "Alta"
                elif volume_mm3 > 200 or mean_probability > 0.6:
                    severity = "Media"
                else:
                    severity = "Baja"
                
                lesions.append({
                    'id': int(label),
                    'volume_mm3': float(volume_mm3),
                    'max_diameter_mm': float(max_diameter),
                    'centroid': [float(c) for c in centroid],
                    'probability': float(mean_probability),
                    'severity': severity
                })
            
            # Ordenar lesiones por volumen (de mayor a menor)
            lesions.sort(key=lambda x: x['volume_mm3'], reverse=True)
            
            # Resultado final
            results = {
                'segmentation': lesion_mask,
                'lesions': lesions,
                'num_lesions': len(lesions),
                'has_significant_lesion': any(l['severity'] == "Alta" for l in lesions),
                'total_lesion_volume': sum(l['volume_mm3'] for l in lesions),
                'prediction_date': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return results
            
        except Exception as e:
            self.prediction_error.emit(f"Error procesando resultados: {str(e)}")
            return None

class PredictionController(QObject):
    """
    Controlador para gestionar las predicciones de IA
    """
    
    # Señales
    prediction_started = pyqtSignal()          # Emitida cuando comienza una predicción
    prediction_completed = pyqtSignal(dict)    # Emitida cuando finaliza exitosamente
    prediction_failed = pyqtSignal(str)        # Emitida cuando hay un error
    prediction_progress = pyqtSignal(int)      # Emitida para actualizar progreso
    
    def __init__(self, parent=None):
        super(PredictionController, self).__init__(parent)
        
        # Ruta al modelo
        self.model_path = os.path.join(MODELS_DIR, "prostate_segmentation_model.pth")
        
        # Resultados de la última predicción
        self.last_results = None
        
        # Worker thread para predicción
        self.worker = None
    
    def start_prediction(self, case_data):
        """
        Inicia el proceso de predicción para un caso
        
        Args:
            case_data: Diccionario con datos del caso
        
        Raises:
            ValueError: Si no se puede iniciar la predicción
        """
        # Verificar que las librerías necesarias están disponibles
        if not TORCH_AVAILABLE or not MONAI_AVAILABLE:
            raise ValueError("No se pueden realizar predicciones porque PyTorch o MONAI no están disponibles")
        
        # Verificar que hay un caso cargado
        if not case_data or 'files' not in case_data:
            raise ValueError("No hay caso cargado para predicción")
        
        # Verificar que no hay una predicción en proceso
        if self.worker and self.worker.isRunning():
            raise ValueError("Ya hay una predicción en proceso")
        
        # Verificar que existe el modelo
        if not os.path.exists(self.model_path):
            # Intentar con modelo de ejemplo
            self.model_path = os.path.join(MODELS_DIR, "sample_model.pth")
            if not os.path.exists(self.model_path):
                raise ValueError(f"No se encontró el modelo en {self.model_path}")
        
        # Iniciar worker
        self.worker = PredictionWorker(case_data, self.model_path)
        
        # Conectar señales
        self.worker.prediction_result.connect(self.on_prediction_completed)
        self.worker.prediction_error.connect(self.on_prediction_failed)
        self.worker.progress_update.connect(self.prediction_progress)
        
        # Emitir señal de inicio
        self.prediction_started.emit()
        
        # Iniciar proceso
        self.worker.start()
    
    @pyqtSlot(dict)
    def on_prediction_completed(self, results):
        """
        Manejador cuando la predicción finaliza exitosamente
        
        Args:
            results: Resultados de la predicción
        """
        # Guardar resultados
        self.last_results = results
        
        # Emitir señal con resultados
        self.prediction_completed.emit(results)
    
    @pyqtSlot(str)
    def on_prediction_failed(self, error_message):
        """
        Manejador cuando la predicción falla
        
        Args:
            error_message: Mensaje de error
        """
        # Emitir señal con mensaje de error
        self.prediction_failed.emit(error_message)
    
    def has_results(self):
        """
        Verifica si hay resultados de predicción disponibles
        
        Returns:
            True si hay resultados, False en caso contrario
        """
        return self.last_results is not None
    
    def get_results(self):
        """
        Obtiene los resultados de la última predicción
        
        Returns:
            Diccionario con resultados o None si no hay
        """
        return self.last_results
    
    def save_results(self, file_path):
        """
        Guarda los resultados de la predicción en un archivo
        
        Args:
            file_path: Ruta donde guardar los resultados
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        if not self.last_results:
            return False
        
        try:
            # Crear copia de resultados para guardar (sin arrays numpy grandes)
            results_to_save = {
                'lesions': self.last_results['lesions'],
                'num_lesions': self.last_results['num_lesions'],
                'has_significant_lesion': self.last_results['has_significant_lesion'],
                'total_lesion_volume': self.last_results['total_lesion_volume'],
                'prediction_date': self.last_results['prediction_date']
            }
            
            # Guardar en formato JSON
            with open(file_path, 'w') as f:
                json.dump(results_to_save, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error guardando resultados: {str(e)}")
            return False
    
    def clear_results(self):
        """Limpia los resultados de la última predicción"""
        self.last_results = None