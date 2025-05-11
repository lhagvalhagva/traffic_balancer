import time
import numpy as np


class VehicleTracker:
    """
    Class for tracking, counting and eliminating vehicle duplicates
    """
    
    def __init__(self, cooldown_time=2.0, iou_threshold=0.3):
        """
        Initialize vehicle tracker
        
        Args:
            cooldown_time (float): Time before recounting the same vehicle (seconds)
            iou_threshold (float): IoU threshold for considering the same vehicle
        """
        self.tracked_vehicles = {}  # ID -> box information
        self.vehicles_in_zones = {}  # Zone ID -> vehicle IDs
        self.vehicles_zone_history = {}
        self.cooldown_time = cooldown_time
        self.iou_threshold = iou_threshold
        self.previous_frame_data = {}  # Previous frame information
        
    def initialize_zones(self, zones):
        """
        Register zones
        
        Args:
            zones (list): List of zones
        """
        self.vehicles_in_zones = {zone.id: set() for zone in zones}
    
    def calculate_iou(self, box1, box2):
        """
        Calculate IoU (Intersection over Union)
        
        Args:
            box1 (list): [x1, y1, x2, y2]
            box2 (list): [x1, y1, x2, y2]
            
        Returns:
            float: IoU value 0.0 ~ 1.0
        """
        # Intersection coordinates
        x1_inter = max(box1[0], box2[0])
        y1_inter = max(box1[1], box2[1])
        x2_inter = min(box1[2], box2[2])
        y2_inter = min(box1[3], box2[3])
        
        # Intersection area
        inter_width = max(0, x2_inter - x1_inter)
        inter_height = max(0, y2_inter - y1_inter)
        inter_area = inter_width * inter_height
        
        # Area of both boxes
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        # Calculate IoU
        union_area = box1_area + box2_area - inter_area
        if union_area == 0:
            return 0
        return inter_area / union_area
    
    def track_vehicle(self, vehicle_box, current_time):
        """
        Track vehicle, assign ID
        
        Args:
            vehicle_box (list): [x1, y1, x2, y2]
            current_time (float): Current time
            
        Returns:
            tuple: (vehicle_id, is_new)
        """
        # If no vehicles are registered, create a new one
        if not self.tracked_vehicles:
            vehicle_id = 1
            self.tracked_vehicles[vehicle_id] = vehicle_box
            return vehicle_id, True
        
        # Find vehicle with highest IoU
        best_iou = 0
        best_vehicle_id = None
        
        for vid, box in self.tracked_vehicles.items():
            iou = self.calculate_iou(vehicle_box, box)
            if iou > best_iou:
                best_iou = iou
                best_vehicle_id = vid
        
        # If IoU is above threshold, consider it the same vehicle
        if best_iou > self.iou_threshold:
            # Update vehicle position
            self.tracked_vehicles[best_vehicle_id] = vehicle_box
            return best_vehicle_id, False
        else:
            # New vehicle
            vehicle_id = max(self.tracked_vehicles.keys()) + 1 if self.tracked_vehicles else 1
            self.tracked_vehicles[vehicle_id] = vehicle_box
            return vehicle_id, True
    
    def update_zone_presence(self, vehicle_id, zone_id, current_time):
        """
        Update whether a vehicle has entered a zone
        
        Args:
            vehicle_id (int): Vehicle ID
            zone_id (int): Zone ID
            current_time (float): Current time
            
        Returns:
            bool: Whether the vehicle is newly entered
        """
        # Mark that the vehicle is now in the zone
        self.vehicles_in_zones[zone_id].add(vehicle_id)
        
        # Create vehicle history
        if vehicle_id not in self.vehicles_zone_history:
            self.vehicles_zone_history[vehicle_id] = {}
            
        # Check if previously entered the zone
        is_first_entry = zone_id not in self.vehicles_zone_history[vehicle_id]
        
        # Prevent recounting, check cooldown time
        last_entry_time = self.vehicles_zone_history.get(vehicle_id, {}).get(zone_id, 0)
        should_count = is_first_entry or (current_time - last_entry_time) > self.cooldown_time
        
        # Update vehicle entry time
        self.vehicles_zone_history[vehicle_id][zone_id] = current_time
        self.vehicles_zone_history[vehicle_id]['last_seen'] = current_time
        
        return should_count
    
    def cleanup_stale_tracks(self, current_time, timeout=5.0):
        """
        Clean up vehicles that have been missing for a long time
        
        Args:
            current_time (float): Current time
            timeout (float): Timeout (seconds)
        """
        for vid in list(self.tracked_vehicles.keys()):
            if vid in self.vehicles_zone_history and 'last_seen' in self.vehicles_zone_history[vid]:
                if current_time - self.vehicles_zone_history[vid]['last_seen'] > timeout:
                    self.tracked_vehicles.pop(vid, None)
    
    def process_frame(self, vehicles, zones, current_time):
        """
        Process all vehicles in one frame
        
        Args:
            vehicles (list): Detected vehicles
            zones (list): List of zones
            current_time (float): Current time
            
        Returns:
            dict: Processed result {
                'vehicle_ids': {id: vehicle},
                'zone_counts': {zone_id: count},
                'zone_vehicles': {zone_id: set(vehicle_ids)}
            }
        """
        # Vehicles in zones in the current frame
        current_zone_vehicles = {zone.id: set() for zone in zones}
        current_vehicles_by_id = {}
        
        # Track all vehicles
        for vehicle in vehicles:
            box = vehicle['box']
            vehicle_id, is_new = self.track_vehicle(box, current_time)
            
            # Save vehicle information
            vehicle['id'] = vehicle_id
            current_vehicles_by_id[vehicle_id] = vehicle
            
            # Check which zone the vehicle is in
            for zone in zones:
                if zone.contains_point(
                    int((box[0] + box[2]) / 2),  # cx
                    int((box[1] + box[3]) / 2)   # cy
                ):
                    # Register vehicle in zone
                    current_zone_vehicles[zone.id].add(vehicle_id)
                    
                    # Check if newly entered zone (Type 1 - COUNT)
                    if zone.is_count_zone():
                        was_in_zone = vehicle_id in self.vehicles_in_zones.get(zone.id, set())
                        
                        # Update zone entry
                        if not was_in_zone:
                            should_count = self.update_zone_presence(vehicle_id, zone.id, current_time)
                            
                            # Count if needed
                            if should_count:
                                zone.increment_count()
        
        # Update current count for Type 2 (SUM) zones
        for zone in zones:
            if zone.is_sum_zone():
                zone.set_current_count(len(current_zone_vehicles[zone.id]))
            
            # Assign current vehicles to zone
            zone.update_vehicles(current_zone_vehicles[zone.id])
            
            # Update if vehicles are stalled
            zone.update_stalled_status()
        
        # Update vehicles in zones to avoid recounting new vehicles
        self.vehicles_in_zones = current_zone_vehicles
        
        # Clean up old vehicles
        self.cleanup_stale_tracks(current_time)
        
        # Check connections between zones
        zone_connections = self.check_zone_connections(zones, current_zone_vehicles)
        
        return {
            'vehicle_ids': current_vehicles_by_id,
            'zone_vehicles': current_zone_vehicles,
            'zone_connections': zone_connections
        }
    
    def track_vehicles(self, frame, boxes, scores, class_ids, zones):
        """
        New format: Track vehicles using boxes, scores, class_ids
        
        Args:
            frame (numpy.ndarray): Image frame
            boxes (list): Detected boxes [[x1,y1,x2,y2], ...]
            scores (list): Scores [score1, score2, ...]
            class_ids (list): Class IDs [class_id1, class_id2, ...]
            zones (list): Zones
            
        Returns:
            tuple: (tracked_objects, zone_vehicles)
                tracked_objects: Tracked vehicles
                zone_vehicles: Vehicles in each zone
        """
        current_time = time.time()
        
        # Vehicles in zones in current frame
        current_zone_vehicles = {zone.id: set() for zone in zones}
        tracked_objects = []
        
        # Track all detected objects
        for i, box in enumerate(boxes):
            score = scores[i]
            class_id = class_ids[i]
            
            vehicle_id, is_new = self.track_vehicle(box, current_time)
            
            # Tracked object information
            tracked_obj = {
                "id": vehicle_id,
                "bbox": box,
                "score": score,
                "class_id": class_id,
                "is_new": is_new
            }
            tracked_objects.append(tracked_obj)
            
            # Check which zone the vehicle is in
            center_x = int((box[0] + box[2]) / 2)
            center_y = int((box[1] + box[3]) / 2)
            
            for zone in zones:
                if zone.contains_point(center_x, center_y):
                    # Register vehicle in zone
                    current_zone_vehicles[zone.id].add(vehicle_id)
                    
                    # Check if newly entered zone (Type 1 - COUNT)
                    if zone.is_count_zone():
                        was_in_zone = vehicle_id in self.vehicles_in_zones.get(zone.id, set())
                        
                        # Update zone entry
                        if not was_in_zone:
                            should_count = self.update_zone_presence(vehicle_id, zone.id, current_time)
                            
                            # Count if needed
                            if should_count:
                                zone.increment_count()
        
        # Update current count for Type 2 (SUM) zones
        for zone in zones:
            if zone.is_sum_zone():
                zone.set_current_count(len(current_zone_vehicles[zone.id]))
            
            # Assign current vehicles to zone
            zone.update_vehicles(current_zone_vehicles[zone.id])
            
            # Update if vehicles are stalled
            zone.update_stalled_status()
        
        # Update vehicles in zones to avoid recounting new vehicles
        self.vehicles_in_zones = current_zone_vehicles
        
        # Clean up old vehicles
        self.cleanup_stale_tracks(current_time)
        
        return tracked_objects, current_zone_vehicles
    
    def check_zone_connections(self, zones, current_zone_vehicles):
        """
        Check relationships between zones, determine vehicle flow
        
        Args:
            zones (list): List of zones
            current_zone_vehicles (dict): Vehicles in each zone
        """
        # Find SUM zones that can determine flow between zones
        sum_zones = [zone for zone in zones if zone.is_sum_zone()]
        
        for zone in sum_zones:
            # If zone is full of vehicles and congested
            if zone.is_stalled and len(current_zone_vehicles[zone.id]) > 5:
                # Find other zones connected to this zone by traffic lights
                for other_zone in zones:
                    if other_zone.id != zone.id:
                        # Check for connected lights
                        common_lights = set(zone.traffic_light_directions) & set(other_zone.traffic_light_directions)
                        if common_lights:
                            # Add logger
                            print(f"WARNING: Congestion in zone {zone.name}, connected to zone {other_zone.name} by lights: {', '.join(common_lights)}") 