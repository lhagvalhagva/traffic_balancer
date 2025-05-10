import cv2
import time
import os
import json
from datetime import datetime

from vehicle_detector import VehicleDetector
from zone_manager import Zone, ZoneManager
from vehicle_tracker import VehicleTracker
from zone_setup import ZoneSetupUI


class VehicleCounterService:
    """
    Тээврийн хэрэгсэл тоолох үндсэн сервис
    """
    
    def __init__(self, video_path=None, model_path="yolov8s.pt", device="cpu", output_path="data"):
        """
        Тээврийн хэрэгсэл тоолох сервис үүсгэх
        
        Args:
            video_path (str): Видео файлын зам (None бол камер)
            model_path (str): YOLO моделийн зам
            device (str): Төхөөрөмж (cpu, cuda, mps)
            output_path (str): Өгөгдөл хадгалах зам
        """
        self.video_path = video_path
        self.model_path = model_path
        self.device = device
        self.output_path = output_path
        
        # Сервис компонентүүд
        self.detector = VehicleDetector(model_path, device)
        self.zone_manager = ZoneManager()
        self.tracker = VehicleTracker()
        
        # Видео бичлэг боловсруулалт
        self.cap = None
        self.frame_count = 0
        self.start_time = None
        self.fps = 0
        self.processing = False
        
        # Өгөгдөл хадгалах зам үүсгэх
        os.makedirs(output_path, exist_ok=True)
    
    def _open_video_capture(self):
        """
        Видео бичлэг эсвэл камер нээх
        
        Returns:
            bool: Амжилттай нээсэн эсэх
        """
        if self.video_path is None:
            self.cap = cv2.VideoCapture(0)  # Үндсэн камер
        else:
            self.cap = cv2.VideoCapture(self.video_path)
        
        return self.cap.isOpened()
    
    def _close_video_capture(self):
        """
        Видео бичлэг хаах
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def _setup_zones(self):
        """
        Бүсүүдийг тохируулах
        
        Returns:
            bool: Амжилттай тохируулсан эсэх
        """
        # Видео нээх
        if not self._open_video_capture():
            print("Видео эсвэл камер нээж чадсангүй.")
            return False
        
        # Эхний фрейм авах
        ret, frame = self.cap.read()
        if not ret:
            print("Видео фрейм уншиж чадсангүй.")
            self._close_video_capture()
            return False
        
        # Бүс тохируулах UI
        ui = ZoneSetupUI(self.zone_manager)
        result = ui.setup_from_frame(frame)
        
        # Видео хаах
        self._close_video_capture()
        
        # Tracker инициализаци
        if result:
            self.tracker.initialize_zones(self.zone_manager.zones)
        
        return result
    
    def _save_data(self, frame_number, timestamp, zones_data):
        """
        Тоолсон өгөгдлийг хадгалах
        
        Args:
            frame_number (int): Фрейм дугаар
            timestamp (float): Хугацааны тэмдэглэл
            zones_data (dict): Бүсийн өгөгдөл
        """
        # Өгөгдөл бэлтгэх
        data = {
            "frame": frame_number,
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "zones": []
        }
        
        # Бүс тус бүрийн өгөгдөл
        for zone in self.zone_manager.zones:
            zone_data = {
                "id": zone.id,
                "name": zone.name,
                "type": "COUNT" if zone.is_count_zone() else "SUM",
                "count": zone.get_display_count(),
                "vehicles": list(zones_data.get("zone_vehicles", {}).get(zone.id, []))
            }
            data["zones"].append(zone_data)
        
        # JSON файл нэр үүсгэх
        timestamp_str = datetime.fromtimestamp(timestamp).strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_path}/vehicle_data_{timestamp_str}.json"
        
        # Өгөгдөл хадгалах
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    
    def start_counting(self, display=True, save_data=True, save_video=False):
        """
        Тээврийн хэрэгсэл тоолох процесс эхлүүлэх
        
        Args:
            display (bool): Видео харуулах эсэх
            save_data (bool): Өгөгдөл хадгалах эсэх
            save_video (bool): Боловсруулсан видео хадгалах эсэх
            
        Returns:
            bool: Процесс амжилттай эсэх
        """
        # Бүс тохируулах
        if not self._setup_zones():
            return False
        
        # Бүс тохируулагдсан эсэхийг шалгах
        if len(self.zone_manager.zones) == 0:
            print("Тохируулсан бүс алга. Процесс дууслаа.")
            return False
        
        # Видео нээх
        if not self._open_video_capture():
            print("Видео эсвэл камер нээж чадсангүй.")
            return False
        
        # Видео бичлэгийн бэлтгэл
        video_writer = None
        if save_video and self.video_path is not None:
            # Видео бичлэгийн параметрүүд
            frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            # Гаралтын файлын нэр үүсгэх
            video_filename = os.path.basename(self.video_path)
            output_path = f"{self.output_path}/{os.path.splitext(video_filename)[0]}_output.mp4"
            
            # Видео бичигч
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        
        # Тоолох процесс эхлүүлэх
        self.processing = True
        self.frame_count = 0
        self.start_time = time.time()
        
        # Тоолох гол цикл
        try:
            while self.cap.isOpened() and self.processing:
                # Фрейм унших
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                self.frame_count += 1
                current_time = time.time()
                
                # Тээврийн хэрэгслүүд илрүүлэх
                vehicles = self.detector.detect_vehicles(frame)
                
                # Тээврийн хэрэгслүүд мөрдөх
                results = self.tracker.process_frame(
                    vehicles, 
                    self.zone_manager.zones, 
                    current_time
                )
                
                # Өгөгдөл хадгалах
                if save_data and self.frame_count % 30 == 0:  # Секунд тутам хадгалах
                    self._save_data(self.frame_count, current_time, results)
                
                # Визуализаци
                if display or save_video:
                    # Тээврийн хэрэгслүүд зурах
                    frame = self.detector.draw_detections(frame, vehicles)
                    
                    # Бүсүүдийг зурах
                    frame = self.zone_manager.draw_zones(frame)
                    
                    # FPS харуулах
                    if self.frame_count % 10 == 0:  # 10 фрейм тутамд FPS тооцоолох
                        elapsed_time = current_time - self.start_time
                        self.fps = self.frame_count / elapsed_time if elapsed_time > 0 else 0
                    
                    cv2.putText(
                        frame, 
                        f"FPS: {self.fps:.1f}", 
                        (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7, 
                        (0, 0, 255), 
                        2
                    )
                    
                    # Боловсруулсан видеог хадгалах
                    if save_video and video_writer is not None:
                        video_writer.write(frame)
                    
                    # Харуулах
                    if display:
                        cv2.imshow("Traffic Detection", frame)
                
                # Хэрэглэгчийн оролт шалгах
                key = cv2.waitKey(1)
                if key == ord('q'):
                    print("Хэрэглэгч процессийг зогсоолоо.")
                    break
        
        finally:
            # Цэвэрлэх
            self.processing = False
            self._close_video_capture()
            
            if video_writer is not None:
                video_writer.release()
            
            if display:
                cv2.destroyAllWindows()
        
        return True
    
    def stop_counting(self):
        """
        Тоолох процессийг зогсоох
        """
        self.processing = False 