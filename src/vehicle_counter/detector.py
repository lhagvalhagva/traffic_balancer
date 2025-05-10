import cv2
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

class VehicleDetector:
    def __init__(self, model_path="yolov8n.pt", max_age=30):
        """
        Тээврийн хэрэгсэл илрүүлэх, мөрдөх модуль
        
        Args:
            model_path: YOLO загварын зам
            max_age: Tracker-ийн max_age параметр
        """
        self.model = YOLO(model_path)
        self.tracker = DeepSort(max_age=max_age)
        self.vehicle_classes = [2, 3, 5, 7]  # car, motorcycle, bus, truck
        
    def detect_and_track(self, frame):
        """
        Өгөгдсөн frame дээрх тээврийн хэрэгслийг илрүүлж, мөрдөнө
        
        Args:
            frame: CV2 дүрсийн frame
            
        Returns:
            tracks: Илэрсэн тээврийн хэрэгслүүдийн мөр
            annotated_frame: Тэмдэглэгээтэй дүрсийн frame
        """
        results = self.model(frame, verbose=False)
        detections = results[0].boxes
        dets_for_tracker = []

        for box in detections:
            cls = int(box.cls[0])
            if cls in self.vehicle_classes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                dets_for_tracker.append(([x1, y1, x2 - x1, y2 - y1], conf, 'vehicle'))

        tracks = self.tracker.update_tracks(dets_for_tracker, frame=frame)
        return tracks, frame 