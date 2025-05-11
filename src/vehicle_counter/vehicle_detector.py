import cv2
import numpy as np
from ultralytics import YOLO
from shapely.geometry import Point


class VehicleDetector:
    """
    Service for detecting vehicles using YOLOv8.
    """
    
    def __init__(self, model_path="yolov8s.pt", device="cpu"):
        """
        Initialize detector
        
        Args:
            model_path (str): YOLO model path
            device (str): Device to use (cpu, cuda, mps)
        """
        self.model = YOLO(model_path)
        self.device = device
        
        # Types of vehicles that can be detected
        self.vehicle_classes = [2, 3, 5, 7, 1]  # car, motorcycle, bus, truck, person
        self.vehicle_class_names = ['car', 'bus', 'truck', 'motorcycle', 'bicycle', 'person']
        
    def detect_vehicles(self, frame):
        """
        Detect vehicles in a single frame
        
        Args:
            frame (numpy.ndarray): Image frame
            
        Returns: 
            tuple : (boxes, scores, class_ids) of vehicles
                  boxes - Box coordinates (x1, y1, x2, y2)
                  scores - Detection scores
                  class_ids - Class IDs
        """
        results = self.model(frame)[0]
        
        # Create empty lists
        boxes = []
        scores = []
        class_ids = []
        
        # Filter detected objects
        for r in results.boxes.data.tolist():
            x1, y1, x2, y2, confidence, class_id = r
            class_id = int(class_id)
            
            # Only vehicle classes
            # Or other objects of interest (people, bicycles, etc.)
            if class_id in self.vehicle_classes or self.model.names[class_id] in self.vehicle_class_names:
                boxes.append([int(x1), int(y1), int(x2), int(y2)])
                scores.append(float(confidence))
                class_ids.append(class_id)
        
        return boxes, scores, class_ids
    
    def detect_vehicles_old(self, frame):
        """
        Detect vehicles in a single frame (old format)
        
        Args:
            frame (numpy.ndarray): Image frame
            
        Returns:
            list: List of detected vehicles
                  [{class_name, confidence, box}]
        """
        results = self.model(frame)[0]
        vehicles = []
        
        for r in results.boxes.data.tolist():
            x1, y1, x2, y2, confidence, class_id = r
            class_name = self.model.names[int(class_id)]
            
            # Only vehicle classes
            if class_name in self.vehicle_class_names:
                vehicles.append({
                    'class_name': class_name,
                    'confidence': confidence,
                    'box': [int(x1), int(y1), int(x2), int(y2)],
                    'class_id': int(class_id)
                })
                
        return vehicles
    
    def draw_detections(self, frame, vehicles):
        """
        Draw detected vehicles on the image
        
        Args:
            frame (numpy.ndarray): Image frame
            vehicles (list): List of detected vehicles
            
        Returns:
            numpy.ndarray: Processed image frame
        """
        result_frame = frame.copy()
        
        # If vehicles is a list, assume it contains dictionaries (old format)
        if isinstance(vehicles, list) and len(vehicles) > 0 and isinstance(vehicles[0], dict):
            for vehicle in vehicles:
                x1, y1, x2, y2 = vehicle['box']
                class_name = vehicle['class_name']
                confidence = vehicle['confidence']
                
                # Draw box
                cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw text
                label = f"{class_name} {confidence:.2f}"
                cv2.putText(result_frame, label, (x1, y1-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        # New format (boxes, scores, class_ids)
        elif isinstance(vehicles, tuple) and len(vehicles) == 3:
            boxes, scores, class_ids = vehicles
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box
                class_id = class_ids[i]
                confidence = scores[i]
                class_name = self.model.names[class_id]
                
                # Draw box
                cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw text
                label = f"{class_name} {confidence:.2f}"
                cv2.putText(result_frame, label, (x1, y1-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
        return result_frame