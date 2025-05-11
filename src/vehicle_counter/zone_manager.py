import cv2
import numpy as np
import time
from shapely.geometry import Point, Polygon

class Zone:
    """
    Бүсийн класс.
    """
    ZONE_TYPE_COUNT = 1  # Нэвтэрсэн тээврийн хэрэгслийг тоолох төрөл
    ZONE_TYPE_SUM = 2    # Одоогийн байгаа тээврийн хэрэгслийг тоолох төрөл
    
    def __init__(self, zone_id, points, zone_type, name=None):
        """
        Бүс үүсгэх
        
        Args:
            zone_id (int): Бүсийн дугаар
            points (list): Бүсийн цэгүүд [(x, y), ...]
            zone_type (int): Бүсийн төрөл (1: COUNT, 2: SUM)
            name (str): Бүсийн нэр
        """
        self.id = zone_id
        self.points = points
        self.type = zone_type
        self.name = name or f"Zone {zone_id}"
        self.polygon = Polygon(points)
        self.vehicle_count = 0
        self.current_count = 0  # Type 2 (SUM) бүсийн хувьд одоогийн тээврийн хэрэгслийн тоо
        self.traffic_light_directions = []  # Холбоотой гэрлэн дохионы чиглэлүүд
        self.stalled_time = 0  # Машин хөдөлгөөнгүй зогссон хугацаа (frame count)
        self.stalled_threshold = 90  # Машин хөдөлгөөнгүй байх босго (frame count)
        self.is_stalled = False  # Машин хөдөлгөөнгүй байгаа эсэх
        self.previous_vehicles = set()  # Өмнөх frame-д байсан машинууд
        self.current_vehicles = set()  # Одоогийн frame-д байгаа машинууд
        self.vehicle_movement_detected = False  # Машин хөдөлж байгаа эсэх
        self.movement_threshold = 3  # Хөдөлгөөн мэдрэх босго
        self.last_update_time = time.time()  # Сүүлийн шинэчлэлтийн хугацаа
        
        # Статистик
        self.stat_start_time = time.time()  # Статистик эхэлсэн хугацаа
        self.hourly_stats = {}  # Цагийн статистик {hour: count}
        self.congestion_events = []  # Түгжрэлийн үйл явдлууд
        self.vehicle_history = []  # Машины түүх [{timestamp, count}]
        self.max_vehicle_count = 0  # Хамгийн их машины тоо
        self.total_stalled_time = 0  # Нийт түгжрэлд зарцуулсан хугацаа (секунд)
        self.stall_start_time = None  # Түгжрэл эхэлсэн хугацаа
    
    def contains_point(self, x, y):
        """
        Өгөгдсөн цэг бүсэд байгаа эсэхийг шалгах
        
        Args:
            x (int): X координат
            y (int): Y координат
            
        Returns:
            bool: Цэг бүсэд байгаа эсэх
        """
        return self.polygon.contains(Point(x, y))
    
    def is_count_zone(self):
        """Type 1 (COUNT) бүс мөн эсэх"""
        return self.type == self.ZONE_TYPE_COUNT
    
    def is_sum_zone(self):
        """Type 2 (SUM) бүс мөн эсэх"""
        return self.type == self.ZONE_TYPE_SUM
    
    def increment_count(self):
        """Тээврийн хэрэгслийн тоо нэмэгдүүлэх (Type 1 - COUNT)"""
        self.vehicle_count += 1
    
    def set_current_count(self, count):
        """
        Одоогийн тээврийн хэрэгслийн тоо тохируулах (Type 2 - SUM)
        """
        # Тоо өөрчлөгдсөн эсэхийг шалгах
        if self.current_count != count:
            # Тоо нэмэгдсэн бол машин хөдөлж байна гэж үзнэ
            self.vehicle_movement_detected = abs(self.current_count - count) >= self.movement_threshold
            self.last_update_time = time.time()
        elif time.time() - self.last_update_time > 5.0:  # 5 секунд өнгөрсөн бол хөдөлгөөнгүй
            self.vehicle_movement_detected = False
            
        self.current_count = count
    
    def get_display_count(self):
        """
        Харуулах тоо авах
        """
        return self.vehicle_count if self.is_count_zone() else self.current_count
    
    def update_vehicles(self, vehicle_ids):
        """
        Тухайн зонд байгаа машинуудын ID-г шинэчлэх
        
        Args:
            vehicle_ids (set): Машинуудын ID
        """
        # Өмнөх машиныг хадгалах
        self.previous_vehicles = self.current_vehicles.copy()
        
        # Одоогийн машиныг шинэчлэх
        self.current_vehicles = set(vehicle_ids)
        
        # Машин орж/гарсан эсэхийг шалгах
        vehicles_changed = len(self.previous_vehicles.symmetric_difference(self.current_vehicles))
        vehicles_count = len(self.current_vehicles)
        
        # Хэрэв хангалттай хэмжээний машин өөрчлөгдсөн бол хөдөлгөөнтэй гэж үзнэ
        self.vehicle_movement_detected = vehicles_changed >= min(self.movement_threshold, max(1, vehicles_count // 2))
        
        # Сүүлийн шинэчлэлийн хугацааг тэмдэглэх
        if self.vehicle_movement_detected:
            self.last_update_time = time.time()
    
    def update_stalled_status(self):
        """
        Машин удаан хугацаанд хөдөлгөөнгүй зогссон эсэхийг шинэчлэх
        
        Returns:
            bool: Машин удаан зогссон эсэх
        """
        # Хэрэв машин байхгүй бол хөдөлгөөнгүй гэж үзэхгүй
        if len(self.current_vehicles) == 0:
            self.stalled_time = 0
            self.is_stalled = False
            
            # Хэрэв өмнө нь түгжрэлтэй байсан бол хугацааг бүртгэх
            if self.stall_start_time is not None:
                stall_duration = time.time() - self.stall_start_time
                self.total_stalled_time += stall_duration
                self.stall_start_time = None
                
                # Түгжрэлийн үйл явдлыг бүртгэх
                self.congestion_events.append({
                    "start_time": self.stall_start_time,
                    "end_time": time.time(),
                    "duration": stall_duration,
                    "vehicle_count": len(self.previous_vehicles)
                })
            
            return False
            
        if self.vehicle_movement_detected:
            self.stalled_time = 0
            self.is_stalled = False
            
            # Хэрэв өмнө нь түгжрэлтэй байсан бол хугацааг бүртгэх
            if self.stall_start_time is not None:
                stall_duration = time.time() - self.stall_start_time
                self.total_stalled_time += stall_duration
                self.stall_start_time = None
                
                # Түгжрэлийн үйл явдлыг бүртгэх
                self.congestion_events.append({
                    "start_time": self.stall_start_time,
                    "end_time": time.time(),
                    "duration": stall_duration,
                    "vehicle_count": len(self.current_vehicles)
                })
        else:
            current_time = time.time()
            
            stall_duration = current_time - self.last_update_time
            
            # Хөдөлгөөнгүй байх хугацаа 10 секундээс их бол түгжрэл гэж үзэх
            if stall_duration > 10.0 and len(self.current_vehicles) >= 3:
                self.stalled_time += 1
            else:
                self.stalled_time = max(0, self.stalled_time - 1)  # Аажмаар буура
            
        prev_stalled = self.is_stalled
        
        self.is_stalled = self.stalled_time > 0 and time.time() - self.last_update_time >= 10.0
        
        # Хэрэв түгжрэл эхэлж байгаа бол эхлэх хугацааг тэмдэглэх
        if not prev_stalled and self.is_stalled:
            self.stall_start_time = time.time()
            
        return self.is_stalled
    
    def update_statistics(self):
        """
        Статистик мэдээллийг шинэчлэх
        """
        current_time = time.time()
        current_hour = time.strftime("%Y-%m-%d %H", time.localtime(current_time))
        vehicle_count = len(self.current_vehicles)
        
        # Цагийн статистик шинэчлэх
        if current_hour in self.hourly_stats:
            self.hourly_stats[current_hour] += vehicle_count
        else:
            self.hourly_stats[current_hour] = vehicle_count
            
        # Машины түүх шинэчлэх
        self.vehicle_history.append({
            "timestamp": current_time,
            "count": vehicle_count,
            "is_stalled": self.is_stalled
        })
        
        # Хамгийн их машины тоог шинэчлэх
        if vehicle_count > self.max_vehicle_count:
            self.max_vehicle_count = vehicle_count
        
        # Түүхийг хязгаарлах (сүүлийн 1 цагийн мэдээллийг л хадгалах)
        one_hour_ago = current_time - 3600
        self.vehicle_history = [record for record in self.vehicle_history if record["timestamp"] > one_hour_ago]
    
    def draw(self, frame):
        """
        Бүсийг зураг дээр зурах
        
        Args:
            frame (numpy.ndarray): Зургийн фрэйм
            
        Returns:
            numpy.ndarray: Боловсруулсан зураг
        """
        # Өнгө сонгох (COUNT=ногоон, SUM=улбар шар)
        color = (0, 255, 0) if self.is_count_zone() else (0, 120, 255)
        
        # Хэрэв түгжрэлтэй бол улаан өнгөтэй болгох
        if self.is_stalled:
            color = (0, 0, 255)  # Улаан - түгжрэлтэй
        
        # Олон талт зурах
        points_array = np.array(self.points)
        cv2.polylines(frame, [points_array], True, color, 2)
        
        # Текст бичих
        if len(self.points) > 0:
            label_pos = self.points[0]
            zone_type_name = "COUNT" if self.is_count_zone() else "SUM"
            count_text = f"{self.name} ({zone_type_name}): {self.get_display_count()}"
            
            # Түгжрэлийн статус нэмэх
            if self.is_stalled:
                count_text += " [ТҮГЖРЭЛТЭЙ]"
            
            cv2.putText(frame, count_text, 
                       (label_pos[0], label_pos[1] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Гэрлэн дохионы мэдээлэл
            if self.traffic_light_directions:
                directions_text = "Гэрэл: " + ", ".join(self.traffic_light_directions)
                cv2.putText(frame, directions_text, 
                          (label_pos[0], label_pos[1] + 20), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
            # Статистик мэдээлэл харуулах
            if self.max_vehicle_count > 0:
                stats_text = f"Хамгийн их: {self.max_vehicle_count} / Түгжрэл: {len(self.congestion_events)}"
                cv2.putText(frame, stats_text, 
                          (label_pos[0], label_pos[1] + 40), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return frame
    
    def get_statistics(self):
        """
        Статистик мэдээлэл авах
        
        Returns:
            dict: Статистик мэдээлэл
        """
        # Ажилласан нийт хугацаа (секунд)
        run_time = time.time() - self.stat_start_time
        
        # Хамгийн их машин байсан хугацаа
        max_vehicle_time = None
        for record in self.vehicle_history:
            if record["count"] == self.max_vehicle_count:
                max_vehicle_time = record["timestamp"]
                break
        
        # Дундаж машины тоо (хэрэв түүх байгаа бол)
        avg_vehicle_count = 0
        if self.vehicle_history:
            avg_vehicle_count = sum(record["count"] for record in self.vehicle_history) / len(self.vehicle_history)
        
        return {
            "zone_id": self.id,
            "zone_name": self.name,
            "zone_type": "COUNT" if self.is_count_zone() else "SUM",
            "current_vehicle_count": len(self.current_vehicles),
            "total_vehicle_count": self.vehicle_count if self.is_count_zone() else None,
            "max_vehicle_count": self.max_vehicle_count,
            "max_vehicle_time": max_vehicle_time,
            "avg_vehicle_count": round(avg_vehicle_count, 2),
            "congestion_events": len(self.congestion_events),
            "total_stalled_time": round(self.total_stalled_time, 2),
            "stalled_percentage": round((self.total_stalled_time / run_time) * 100, 2) if run_time > 0 else 0,
            "hourly_stats": self.hourly_stats,
            "run_time_seconds": round(run_time, 2)
        }


class ZoneManager:
    """
    Бүсүүдийг зохицуулах класс.
    """
    
    def __init__(self):
        """
        Бүсийн менежер үүсгэх
        """
        self.zones = []
        self.current_zone_id = 1
        self.current_polygon = []  # Одоогийн буй зурагдаж байгаа полигон
        self.last_statistics_update = time.time()  # Сүүлийн статистик шинэчлэлтийн хугацаа
        self.statistics_update_interval = 5.0  # Статистик шинэчлэх хугацааны зай (секунд)
    
    def create_zone(self, points, zone_type, name=None):
        """
        Шинэ бүс үүсгэх
        
        Args:
            points (list): Бүсийн цэгүүд [(x, y), ...]
            zone_type (int): Бүсийн төрөл (1: COUNT, 2: SUM)
            name (str): Бүсийн нэр
            
        Returns:
            Zone: Шинээр үүссэн бүс
        """
        zone = Zone(self.current_zone_id, points, zone_type, name)
        self.zones.append(zone)
        self.current_zone_id += 1
        return zone
    
    def get_zone_by_id(self, zone_id):
        """
        ID-р бүс олох
        
        Args:
            zone_id (int): Бүсийн дугаар
            
        Returns:
            Zone: Бүс (олдохгүй бол None)
        """
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        return None
    
    def find_zones_containing_point(self, x, y):
        """
        Өгөгдсөн цэгийг агуулж байгаа бүс олох
        
        Args:
            x (int): X координат
            y (int): Y координат
            
        Returns:
            list: Бүсүүдийн жагсаалт
        """
        return [zone for zone in self.zones if zone.contains_point(x, y)]
    
    def find_zone_containing_vehicle(self, vehicle):
        """
        Тээврийн хэрэгслийг агуулж байгаа бүс олох
        
        Args:
            vehicle (dict): Тээврийн хэрэгсэл {box: [x1, y1, x2, y2], ...}
            
        Returns:
            list: Бүсүүдийн жагсаалт
        """
        x1, y1, x2, y2 = vehicle['box']
        # Тээврийн хэрэгслийн төв цэг
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        
        return self.find_zones_containing_point(cx, cy)
    
    def add_point_to_current_polygon(self, x, y):
        """
        Одоогийн полигонд цэг нэмэх
        
        Args:
            x (int): X координат
            y (int): Y координат
        """
        self.current_polygon.append((x, y))
    
    def reset_current_polygon(self):
        """
        Одоогийн полигон цэвэрлэх
        """
        self.current_polygon = []
    
    def is_current_polygon_valid(self):
        """
        Одоогийн полигон хүчинтэй эсэх
        
        Returns:
            bool: 3 болон түүнээс дээш цэгтэй эсэх
        """
        return len(self.current_polygon) >= 3
    
    def draw_zones(self, frame):
        """
        Бүх бүсүүдийг зураг дээр зурах
        
        Args:
            frame (numpy.ndarray): Зургийн фрэйм
            
        Returns:
            numpy.ndarray: Боловсруулсан зураг
        """
        # Статистикийг шинэчлэх
        self.update_statistics()
        
        # Бүх бүсийг зурах
        for zone in self.zones:
            frame = zone.draw(frame)
        
        return frame
    
    def draw_current_polygon(self, frame):
        """
        Одоогийн зурагдаж байгаа полигоныг зурах
        
        Args:
            frame (numpy.ndarray): Зургийн фрэйм
            
        Returns:
            numpy.ndarray: Боловсруулсан зураг
        """
        result_frame = frame.copy()
        
        if len(self.current_polygon) > 0:
            # Бүх цэгүүдийг зурах
            for point in self.current_polygon:
                cv2.circle(result_frame, point, 3, (0, 0, 255), -1)
            
            # Цэгүүдийг холбох шугам
            for i in range(len(self.current_polygon)):
                cv2.line(
                    result_frame, 
                    self.current_polygon[i], 
                    self.current_polygon[(i+1) % len(self.current_polygon)], 
                    (0, 0, 255), 
                    1
                )
        
        return result_frame
    
    def update_statistics(self):
        """
        Бүх бүсийн статистикийг шинэчлэх
        """
        current_time = time.time()
        
        # Хугацааны зайг шалгаж статистикийг шинэчлэх
        if current_time - self.last_statistics_update >= self.statistics_update_interval:
            for zone in self.zones:
                zone.update_statistics()
            self.last_statistics_update = current_time
    
    def get_all_statistics(self):
        """
        Бүх бүсийн статистикийг авах
        
        Returns:
            list: Бүх бүсийн статистик
        """
        return [zone.get_statistics() for zone in self.zones]
    
    def get_zone_statistics(self, zone_id):
        """
        Тодорхой бүсийн статистикийг авах
        
        Args:
            zone_id (int): Бүсийн дугаар
            
        Returns:
            dict: Бүсийн статистик
        """
        zone = self.get_zone_by_id(zone_id)
        if zone:
            return zone.get_statistics()
        return None