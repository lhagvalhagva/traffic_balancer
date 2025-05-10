import cv2
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

class VehicleDetector:
    def __init__(self, model_path="yolov8s.pt", max_age=30, device="cpu"):
        """
        Тээврийн хэрэгсэл илрүүлэх, мөрдөх модуль
        Args:
            model_path: YOLO загварын зам
            max_age: Tracker-ийн max_age параметр
            device: Загварыг ажиллуулах төхөөрөмж (cpu, cuda, mps)
        """
        # YOLO загварыг хурдасгуур дээр ачаалах
        self.model = YOLO(model_path)
        self.device = device
        
        # PyTorch устгаад дахин импортлох хэрэгтэй болж магадгүй
        if device != "cpu":
            try:
                self.model.to(device)
                print(f"YOLOv8 загвар '{device}' дээр ачаалагдлаа")
            except Exception as e:
                print(f"Хурдасгуур дээр загвар ачаалахад алдаа гарлаа: {e}")
                print("CPU дээр үргэлжлүүлж байна...")
        
        self.tracker = DeepSort(max_age=max_age)
        # Тээврийн хэрэгсэлийн ангилалууд (COCO dataset)
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
        # YOLO загвар дуудах (илүү хурдан ажиллах тохиргоо)
        results = self.model(
            frame, 
            verbose=False, 
            conf=0.25,      # Конфиденс босго (бага байх тусам илүү олон объект илэрнэ)
            iou=0.45,       # IoU босго (бага байх тусам давхардсан box-уудыг багасгана)
            max_det=50,     # Хамгийн ихдээ хэдэн объект илрүүлэх вэ
            classes=self.vehicle_classes  # Зөвхөн тээврийн хэрэгсэл илрүүлэх
        )
        
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