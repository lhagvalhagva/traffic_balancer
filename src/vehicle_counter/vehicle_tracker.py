import time
import numpy as np


class VehicleTracker:
    """
    Тээврийн хэрэгслийг мөрдөх, тоолох, давхардал арилгах класс
    """
    
    def __init__(self, cooldown_time=2.0, iou_threshold=0.3):
        """
        Тээврийн хэрэгсэл мөрдөгч үүсгэх
        
        Args:
            cooldown_time (float): Нэг тээврийн хэрэгслийг дахин тоолохгүй байх хугацаа (секунд)
            iou_threshold (float): Ижил тээврийн хэрэгсэл гэж үзэх IoU босго
        """
        self.tracked_vehicles = {}  # ID -> боксын мэдээлэл
        self.vehicles_in_zones = {}  # Зоны ID -> тээврийн хэрэгслийн ID-үүд
        self.vehicles_zone_history = {}  # Тээврийн хэрэгсэл бүрийн бүсэд орсон түүх
        self.cooldown_time = cooldown_time
        self.iou_threshold = iou_threshold
        
    def initialize_zones(self, zones):
        """
        Бүсүүдийг бүртгэх
        
        Args:
            zones (list): Бүсүүдийн жагсаалт
        """
        self.vehicles_in_zones = {zone.id: set() for zone in zones}
    
    def calculate_iou(self, box1, box2):
        """
        IoU (Intersection over Union) тооцоолох
        
        Args:
            box1 (list): [x1, y1, x2, y2]
            box2 (list): [x1, y1, x2, y2]
            
        Returns:
            float: IoU утга 0.0 ~ 1.0
        """
        # Огтлолцлын хэсгийн координат
        x1_inter = max(box1[0], box2[0])
        y1_inter = max(box1[1], box2[1])
        x2_inter = min(box1[2], box2[2])
        y2_inter = min(box1[3], box2[3])
        
        # Огтлолцлын талбай
        inter_width = max(0, x2_inter - x1_inter)
        inter_height = max(0, y2_inter - y1_inter)
        inter_area = inter_width * inter_height
        
        # Хоёр боксын талбай
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        # IoU тооцоолох
        union_area = box1_area + box2_area - inter_area
        if union_area == 0:
            return 0
        return inter_area / union_area
    
    def track_vehicle(self, vehicle_box, current_time):
        """
        Тээврийн хэрэгслийг мөрдөх, ID олгох
        
        Args:
            vehicle_box (list): [x1, y1, x2, y2]
            current_time (float): Одоогийн цаг
            
        Returns:
            tuple: (vehicle_id, is_new)
        """
        # Хэрэв ямар ч тээврийн хэрэгсэл бүртгэгдээгүй бол шинээр үүсгэнэ
        if not self.tracked_vehicles:
            vehicle_id = 1
            self.tracked_vehicles[vehicle_id] = vehicle_box
            return vehicle_id, True
        
        # Хамгийн их IoU-тай тээврийн хэрэгсэл хайх
        best_iou = 0
        best_vehicle_id = None
        
        for vid, box in self.tracked_vehicles.items():
            iou = self.calculate_iou(vehicle_box, box)
            if iou > best_iou:
                best_iou = iou
                best_vehicle_id = vid
        
        # Хэрэв IoU босгоос дээш бол ижил тээврийн хэрэгсэл
        if best_iou > self.iou_threshold:
            # Тээврийн хэрэгслийн байрлалыг шинэчлэх
            self.tracked_vehicles[best_vehicle_id] = vehicle_box
            return best_vehicle_id, False
        else:
            # Шинэ тээврийн хэрэгсэл
            vehicle_id = max(self.tracked_vehicles.keys()) + 1 if self.tracked_vehicles else 1
            self.tracked_vehicles[vehicle_id] = vehicle_box
            return vehicle_id, True
    
    def update_zone_presence(self, vehicle_id, zone_id, current_time):
        """
        Тээврийн хэрэгсэл бүсэд орсон эсэхийг шинэчлэх
        
        Args:
            vehicle_id (int): Тээврийн хэрэгслийн ID
            zone_id (int): Бүсийн ID
            current_time (float): Одоогийн цаг
            
        Returns:
            bool: Тээврийн хэрэгсэл шинээр орсон эсэх
        """
        # Тээврийн хэрэгсэл одоо бүсэд байгаа гэж тэмдэглэх
        self.vehicles_in_zones[zone_id].add(vehicle_id)
        
        # Тээврийн хэрэгслийн түүх үүсгэх
        if vehicle_id not in self.vehicles_zone_history:
            self.vehicles_zone_history[vehicle_id] = {}
            
        # Бүсэд өмнө орж байсан эсэхийг шалгах
        is_first_entry = zone_id not in self.vehicles_zone_history[vehicle_id]
        
        # Дахин тоололтоос хамгаалах, хугацааны саатал шалгах
        last_entry_time = self.vehicles_zone_history.get(vehicle_id, {}).get(zone_id, 0)
        should_count = is_first_entry or (current_time - last_entry_time) > self.cooldown_time
        
        # Тээврийн хэрэгсэл орсон хугацааг шинэчлэх
        self.vehicles_zone_history[vehicle_id][zone_id] = current_time
        self.vehicles_zone_history[vehicle_id]['last_seen'] = current_time
        
        return should_count
    
    def cleanup_stale_tracks(self, current_time, timeout=5.0):
        """
        Удаан хугацаанд алга болсон тээврийн хэрэгслийг цэвэрлэх
        
        Args:
            current_time (float): Одоогийн цаг
            timeout (float): Хугацаа (секунд)
        """
        for vid in list(self.tracked_vehicles.keys()):
            if vid in self.vehicles_zone_history and 'last_seen' in self.vehicles_zone_history[vid]:
                if current_time - self.vehicles_zone_history[vid]['last_seen'] > timeout:
                    self.tracked_vehicles.pop(vid, None)
    
    def process_frame(self, vehicles, zones, current_time):
        """
        Нэг фреймд байгаа бүх тээврийн хэрэгслийг боловсруулах
        
        Args:
            vehicles (list): Илрүүлсэн тээврийн хэрэгслүүд
            zones (list): Бүсүүдийн жагсаалт
            current_time (float): Одоогийн цаг
            
        Returns:
            dict: Боловсруулсан үр дүн {
                'vehicle_ids': {id: vehicle},
                'zone_counts': {zone_id: count},
                'zone_vehicles': {zone_id: set(vehicle_ids)}
            }
        """
        # Одоогийн фреймд хянаж байгаа бүсэд байгаа тээврийн хэрэгслүүд
        current_zone_vehicles = {zone.id: set() for zone in zones}
        current_vehicles_by_id = {}
        
        # Бүх тээврийн хэрэгслийг мөрдөх
        for vehicle in vehicles:
            box = vehicle['box']
            vehicle_id, is_new = self.track_vehicle(box, current_time)
            
            # Тээврийн хэрэгслийн мэдээлэл хадгалах
            vehicle['id'] = vehicle_id
            current_vehicles_by_id[vehicle_id] = vehicle
            
            # Тээврийн хэрэгсэл аль бүсэд байгааг шалгах
            for zone in zones:
                if zone.contains_point(
                    int((box[0] + box[2]) / 2),  # cx
                    int((box[1] + box[3]) / 2)   # cy
                ):
                    # Тээврийн хэрэгслийг бүсэд бүртгэх
                    current_zone_vehicles[zone.id].add(vehicle_id)
                    
                    # Шинээр бүсэд орсон эсэхийг шалгах (Type 1 - COUNT)
                    if zone.is_count_zone():
                        was_in_zone = vehicle_id in self.vehicles_in_zones.get(zone.id, set())
                        
                        # Бүсэд орсон эсэхийг шинэчлэх
                        if not was_in_zone:
                            should_count = self.update_zone_presence(vehicle_id, zone.id, current_time)
                            
                            # Тоолох хэрэгтэй бол тоолох
                            if should_count:
                                zone.increment_count()
        
        # Type 2 (SUM) бүсүүдийн одоогийн тоог шинэчлэх
        for zone in zones:
            if zone.is_sum_zone():
                zone.set_current_count(len(current_zone_vehicles[zone.id]))
        
        # Бүсэд байгаа тээврийн хэрэгслийн мэдээллийг шинэчлэх
        for zone_id, vehicles in current_zone_vehicles.items():
            self.vehicles_in_zones[zone_id] = vehicles
        
        # Хуучирсан тээврийн хэрэгслийг цэвэрлэх
        self.cleanup_stale_tracks(current_time)
        
        return {
            'vehicle_ids': current_vehicles_by_id,
            'zone_vehicles': current_zone_vehicles
        } 