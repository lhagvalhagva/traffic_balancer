import cv2
import numpy as np
from ultralytics import YOLO
from shapely.geometry import Point


class VehicleDetector:
    """
    YOLOv8 ашиглан тээврийн хэрэгсэл илрүүлэх сервис.
    """
    
    def __init__(self, model_path="yolov8s.pt", device="cpu"):
        """
        Детектор үүсгэх
        
        Args:
            model_path (str): YOLO моделийн зам
            device (str): Ашиглах төхөөрөмж (cpu, cuda, mps)
        """
        self.model = YOLO(model_path)
        self.device = device
        
        # Илрүүлэх боломжтой тээврийн хэрэгслийн төрлүүд
        self.vehicle_classes = ['car', 'bus', 'truck', 'motorcycle', 'bicycle']
        
    def detect_vehicles(self, frame):
        """
        Нэг фрэймд тээврийн хэрэгсэл илрүүлэх
        
        Args:
            frame (numpy.ndarray): Зургийн фрэйм
            
        Returns:
            list: Илэрсэн тээврийн хэрэгслүүдийн жагсаалт
                  [{class_name, confidence, box}]
        """
        results = self.model(frame)[0]
        vehicles = []
        
        for r in results.boxes.data.tolist():
            x1, y1, x2, y2, confidence, class_id = r
            class_name = self.model.names[int(class_id)]
            
            # Зөвхөн тээврийн хэрэгсэл байх
            if class_name in self.vehicle_classes:
                vehicles.append({
                    'class_name': class_name,
                    'confidence': confidence,
                    'box': [int(x1), int(y1), int(x2), int(y2)]
                })
                
        return vehicles
    
    def draw_detections(self, frame, vehicles):
        """
        Илэрсэн тээврийн хэрэгслүүдийг зураг дээр зурах
        
        Args:
            frame (numpy.ndarray): Зургийн фрэйм
            vehicles (list): Илэрсэн тээврийн хэрэгслүүдийн жагсаалт
            
        Returns:
            numpy.ndarray: Боловсруулсан зургийн фрэйм
        """
        result_frame = frame.copy()
        
        for vehicle in vehicles:
            x1, y1, x2, y2 = vehicle['box']
            class_name = vehicle['class_name']
            confidence = vehicle['confidence']
            
            # Хүрээг зурах
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Текст зурах
            label = f"{class_name} {confidence:.2f}"
            cv2.putText(result_frame, label, (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
        return result_frame 