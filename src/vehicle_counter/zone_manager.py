import cv2
import numpy as np
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
        self.current_count = count
    
    def get_display_count(self):
        """
        Харуулах тоо авах
        """
        return self.vehicle_count if self.is_count_zone() else self.current_count
    
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
        
        # Олон талт зурах
        points_array = np.array(self.points)
        cv2.polylines(frame, [points_array], True, color, 2)
        
        # Текст бичих
        if len(self.points) > 0:
            label_pos = self.points[0]
            zone_type_name = "COUNT" if self.is_count_zone() else "SUM"
            count_text = f"{self.name} ({zone_type_name}): {self.get_display_count()}"
            
            cv2.putText(frame, count_text, 
                       (label_pos[0], label_pos[1] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return frame


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
        result_frame = frame.copy()
        
        for zone in self.zones:
            result_frame = zone.draw(result_frame)
            
        return result_frame
    
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