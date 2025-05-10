import cv2
import numpy as np
import time
from collections import defaultdict

class VehicleCounter:
    def __init__(self, roi_polygon=None):
        """
        Тээврийн хэрэгсэл тоолох класс
        
        Args:
            roi_polygon: Тоолох бүсийн полигон (хэрэв байгаа бол)
        """
        self.roi_polygon = roi_polygon
        self.counted_ids = set()
        self.vehicle_count = 0

        # Машин хэр удаан бүсэд байгааг тооцоолоход шаардлагатай хувьсагчууд
        self.vehicle_timers = {}  # {vehicle_id: {'enter_time': timestamp, 'exit_time': timestamp or None}}
        self.vehicle_positions = {}  # {vehicle_id: [x, y]} - сүүлийн байршил
        self.vehicle_static_duration = {}  # {vehicle_id: duration_in_seconds}
        self.vehicle_static_threshold = 3  # Хөдөлгөөнгүй гэж үзэх зайн босго
        self.static_threshold_time = 10  # Х секундээс дээш зогссон бол санаа зовох
        self.congestion_threshold = 5  # Зогссон машины тоо босго
        self.fps = 30  # Анхны утга, видеоны FPS-с хамаарч өөрчлөгдөнө

        self.congestion_level = "low"  # low, medium, high, very_high
        self.vehicles_in_roi = set()  # ROI дотор одоо байгаа машинууд
        self.static_vehicles = set()  # Хөдөлгөөнгүй машинууд

        # Хөтөлбөр эхэлсэн хугацаа
        self.start_time = time.time()

    def update_fps(self, fps):
        """
        Видеоны FPS өөрчлөх
        
        Args:
            fps: Видеоны FPS
        """
        if fps > 0:
            self.fps = fps
            print(f"Видеоны FPS: {fps}")
        
    def setup_roi(self, frame):
        """
        ROI (Region of Interest) буюу тоолох бүсийг тохируулах.
        Дөрвөлжин хэлбэртэй байх ёстой.
        
        Args:
            frame: Анхны дүрсийн frame
            
        Returns:
            roi_polygon: Тохируулсан ROI полигон (дөрвөлжин)
        """
        roi_points = []
        drawing = False
        start_point = None
        
        def draw_roi(event, x, y, flags, param):
            nonlocal roi_points, drawing, start_point
            
            if event == cv2.EVENT_LBUTTONDOWN:
                # Эхний цэг бол хадгалж авна
                if not drawing:
                    roi_points = [(x, y)]
                    start_point = (x, y)
                    drawing = True
                # Дөрөв дэх цэг бол дуусгана
                elif len(roi_points) == 3:
                    roi_points.append((x, y))
                    drawing = False
                # 2, 3-р цэгүүд
                else:
                    roi_points.append((x, y))
            
            elif event == cv2.EVENT_RBUTTONDOWN and drawing:
                drawing = False

        cv2.namedWindow("Дөрвөлжин ROI зурах (4 цэг тэмдэглэ)")
        cv2.setMouseCallback("Дөрвөлжин ROI зурах (4 цэг тэмдэглэ)", draw_roi)

        while True:
            temp_frame = frame.copy()
            # Цэгүүдийг харуулах
            for i, pt in enumerate(roi_points):
                # Улаан өнгөөр цэгийг зурах
                cv2.circle(temp_frame, pt, 5, (0, 0, 255), -1)
                # Цэгийн дугаарыг харуулах
                cv2.putText(temp_frame, str(i+1), (pt[0] + 10, pt[1] + 10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
            # Холбох шугамуудыг зурах
            if len(roi_points) > 1:
                for i in range(len(roi_points) - 1):
                    # Цэнхэр шугам (BGR формат дээр B = 255, G = 0, R = 0)
                    cv2.line(temp_frame, roi_points[i], roi_points[i + 1], (255, 0, 0), 2)
                
                # Хэрэв дөрөв дэх цэг байвал, эхний цэгтэй холбох
                if len(roi_points) == 4:
                    cv2.line(temp_frame, roi_points[3], roi_points[0], (255, 0, 0), 2)
            
            cv2.imshow("Дөрвөлжин ROI зурах (4 цэг тэмдэглэ)", temp_frame)
            
            # ESC товчлуураар гарах
            if cv2.waitKey(1) & 0xFF == 27:
                break
                
            # Хэрэв дөрвөн цэг бүгд байвал автоматаар дуусгах
            if len(roi_points) == 4 and not drawing:
                roi_polygon = np.array(roi_points)
                break

        cv2.destroyWindow("Дөрвөлжин ROI зурах (4 цэг тэмдэглэ)")
        self.roi_polygon = roi_polygon
        return roi_polygon
    
    def is_inside_roi(self, center):
        """
        Өгөгдсөн цэг ROI доторх эсэхийг шалгах
        
        Args:
            center: Шалгах цэгийн координат (x, y)
            
        Returns:
            bool: ROI доторх эсэх
        """
        if self.roi_polygon is None:
            return True
        return cv2.pointPolygonTest(self.roi_polygon, center, False) >= 0
    
    def is_vehicle_static(self, track_id, current_position):
        """
        Машин хөдөлгөөнгүй эсэхийг шалгах
        
        Args:
            track_id: Машины ID
            current_position: Одоогийн байршил [x, y]
            
        Returns:
            bool: Хөдөлгөөнгүй эсэх
        """
        if track_id not in self.vehicle_positions:
            self.vehicle_positions[track_id] = current_position
            return False
            
        last_position = self.vehicle_positions[track_id]
        distance = np.sqrt((current_position[0] - last_position[0])**2 + 
                          (current_position[1] - last_position[1])**2)
        
        self.vehicle_positions[track_id] = current_position
        
        # Хэрэв машин маш бага хөдөлж байвал хөдөлгөөнгүй гэж тооцох
        return distance < self.vehicle_static_threshold
    
    def update_vehicle_times(self, track_id, center):
        """
        Машины хугацааг шинэчлэх
        
        Args:
            track_id: Машины ID
            center: Машины төвийн байршил
        """
        current_time = time.time()
        is_inside = self.is_inside_roi(center)
        
        # Шинэ машин бол
        if track_id not in self.vehicle_timers:
            self.vehicle_timers[track_id] = {
                'enter_time': current_time if is_inside else None,
                'exit_time': None,
                'in_roi': is_inside
            }
            
            if is_inside:
                self.vehicles_in_roi.add(track_id)
                
        # Хуучин машин бол шинэчлэх
        else:
            # ROI-руу анх орж ирсэн
            if is_inside and self.vehicle_timers[track_id]['enter_time'] is None:
                self.vehicle_timers[track_id]['enter_time'] = current_time
                self.vehicle_timers[track_id]['in_roi'] = True
                self.vehicles_in_roi.add(track_id)
                
            # ROI-с гарсан
            elif not is_inside and self.vehicle_timers[track_id]['in_roi']:
                self.vehicle_timers[track_id]['exit_time'] = current_time
                self.vehicle_timers[track_id]['in_roi'] = False
                self.vehicles_in_roi.discard(track_id)
                self.static_vehicles.discard(track_id)
                
        # Хөдөлгөөнгүй хугацааг тооцоолох
        if is_inside:
            is_static = self.is_vehicle_static(track_id, center)
            
            if is_static:
                if track_id not in self.static_vehicles:
                    self.static_vehicles.add(track_id)
                    self.vehicle_static_duration[track_id] = 0
                else:
                    # FPS-г ашиглан илүү нарийвчлалтай тооцоолох
                    self.vehicle_static_duration[track_id] += 1/max(self.fps, 1)
            else:
                self.static_vehicles.discard(track_id)
                self.vehicle_static_duration[track_id] = 0

    def calculate_congestion_level(self):
        """
        Түгжрэлийн түвшинг тодорхойлох
        
        Returns:
            congestion_level: Түгжрэлийн түвшин (low, medium, high, very_high)
            metrics: Хэмжилтийн метрикүүд
        """
        # Хөдөлгөөнгүй машинуудын хувь
        total_vehicles = len(self.vehicles_in_roi)
        static_count = len(self.static_vehicles)
        static_ratio = static_count / max(total_vehicles, 1)
        
        # Зогссон хугацаа
        max_static_duration = 0
        avg_static_duration = 0
        
        if static_count > 0:
            static_durations = [self.vehicle_static_duration.get(vid, 0) 
                               for vid in self.static_vehicles]
            max_static_duration = max(static_durations)
            avg_static_duration = sum(static_durations) / len(static_durations)
        
        # Түгжрэлийн түвшин тодорхойлох
        if static_count <= 1:
            self.congestion_level = "low"
        elif static_count <= self.congestion_threshold and max_static_duration < self.static_threshold_time:
            self.congestion_level = "medium"
        elif static_count > self.congestion_threshold or max_static_duration >= self.static_threshold_time:
            self.congestion_level = "high"
        elif static_count > self.congestion_threshold * 2 and max_static_duration >= self.static_threshold_time:
            self.congestion_level = "very_high"
            
        metrics = {
            "vehicles_in_roi": total_vehicles,
            "static_vehicles": static_count,
            "static_ratio": static_ratio,
            "max_static_duration": max_static_duration,
            "avg_static_duration": avg_static_duration,
            "congestion_level": self.congestion_level,
            "vehicles_per_minute": len(self.counted_ids) / (time.time() - self.start_time) * 60 if time.time() > self.start_time else 0
        }
        
        return self.congestion_level, metrics
    
    def count_vehicles(self, tracks):
        """
        Илэрсэн тээврийн хэрэгслийн мөрийг ашиглан тоолох
        
        Args:
            tracks: DeepSort-с гарсан тээврийн хэрэгслийн мөр
            
        Returns:
            count: Одоогийн нийт тоо
            new_vehicles: Шинээр илэрсэн тээврийн хэрэгслийн ID-ууд
        """
        new_vehicles = []
        
        for track in tracks:
            if not track.is_confirmed():
                continue
                
            track_id = track.track_id
            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = map(int, ltrb)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            
            # Машины хугацааг шинэчилж байна
            self.update_vehicle_times(track_id, (cx, cy))
            
            # Тоолохын тулд ROI-д байх ёстой, бас шинэ машин байх ёстой
            if track_id not in self.counted_ids and self.is_inside_roi((cx, cy)):
                self.counted_ids.add(track_id)
                self.vehicle_count += 1
                new_vehicles.append(track_id)
        
        # Түгжрэлийн түвшинг тооцоолох
        self.calculate_congestion_level()
                
        return self.vehicle_count, new_vehicles
    
    def draw_visualization(self, frame, tracks):
        """
        Тэмдэглэгээтэй frame үүсгэх
        
        Args:
            frame: Анхны frame
            tracks: Тээврийн хэрэгслийн мөрүүд
            
        Returns:
            frame: Тэмдэглэгээтэй frame
        """
        # Тээврийн хэрэгслүүдийг зурах
        for track in tracks:
            if not track.is_confirmed():
                continue
                
            track_id = track.track_id
            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = map(int, ltrb)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            
            # Машины төрлөөс хамаарсан өнгө
            if track_id in self.static_vehicles:
                # Хөдөлгөөнгүй машин - улаан
                color = (0, 0, 255)
                # Хэр удаан зогссоныг харуулах
                seconds = self.vehicle_static_duration.get(track_id, 0)
                cv2.putText(frame, f'{seconds:.1f}s', (x1, y1 - 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            elif track_id in self.vehicles_in_roi:
                # ROI дотор байгаа машин - шар
                color = (0, 255, 255)
            else:
                # Бусад машинууд - ногоон
                color = (0, 255, 0)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.circle(frame, (cx, cy), 4, color, -1)
            cv2.putText(frame, f'ID: {track_id}', (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # ROI зурах - цэнхэр өнгийн дөрвөлжин (BGR формат дээр B = 255, G = 0, R = 0)
        if self.roi_polygon is not None:
            cv2.polylines(frame, [self.roi_polygon], isClosed=True, color=(255, 0, 0), thickness=2)
            
        # Тоог харуулах
        cv2.putText(frame, f'Count: {self.vehicle_count}', (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # Түгжрэлийн түвшинг харуулах
        congestion_color = {
            "low": (0, 255, 0),     # Ногоон
            "medium": (0, 255, 255), # Шар
            "high": (0, 165, 255),   # Улбар шар
            "very_high": (0, 0, 255) # Улаан
        }
        cv2.putText(frame, f'Congestion: {self.congestion_level}', (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, congestion_color[self.congestion_level], 2)
        
        cv2.putText(frame, f'Static: {len(self.static_vehicles)}', (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    
        return frame
        
    def get_congestion_data(self):
        """
        Түгжрэлийн түвшингийн тайлан авах
        
        Returns:
            data: Түгжрэлийн мэдээлэл
        """
        _, metrics = self.calculate_congestion_level()
        
        # Мэдээлэл нэгтгэх
        return {
            "congestion_level": self.congestion_level,
            "vehicles_per_minute": len(self.counted_ids) / (time.time() - self.start_time) * 60 if time.time() > self.start_time else 0,
            "vehicles_in_roi": len(self.vehicles_in_roi),
            "static_vehicles": len(self.static_vehicles),
            "max_static_duration": max([self.vehicle_static_duration.get(vid, 0) for vid in self.static_vehicles]) if self.static_vehicles else 0,
            "timestamp": time.time(),
            "location": "Уулзвар 1"
        } 