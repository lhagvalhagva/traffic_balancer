import cv2
import numpy as np
import time

class TrafficLightController:
    def __init__(self):
        
        self.traffic_lights = {
            
            "West_Left": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30},    
            "West_Straight": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30}, 
            "West_Right": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30},   
            
            
            "East_Left": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30},    
            "East_Straight": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30}, 
            "East_Right": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30},   
            
            
            "North_Left": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30},    
            "North_Straight": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30}, 
            "North_Right": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30},   
            
            
            "South_Left": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30},    
            "South_Straight": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30}, 
            "South_Right": {"status": "BLUE", "changed_time": 0, "color": (255, 150, 0), "duration": 30},   
        }
        
        
        self.direction_groups = {
            "West": ["West_Left", "West_Straight", "West_Right"],
            "East": ["East_Left", "East_Straight", "East_Right"],
            "North": ["North_Left", "North_Straight", "North_Right"],
            "South": ["South_Left", "South_Straight", "South_Right"]
        }
        
        
        self.direction_names = {
            "West_Left": "West to Left",
            "West_Straight": "West Straight",
            "West_Right": "West to Right",
            "East_Left": "East to Left",
            "East_Straight": "East Straight",
            "East_Right": "East to Right",
            "North_Left": "North to Left",
            "North_Straight": "North Straight",
            "North_Right": "North to Right",
            "South_Left": "South to Left",
            "South_Straight": "South Straight",
            "South_Right": "South to Right"
        }
        
        
        self.last_change_time = time.time()
        
        self.min_change_interval = 30
        
        self.recently_changed = []
        
        self.auto_mode = True
        
        self.last_auto_check = time.time()
        
        self.auto_check_interval = 5
        
    def switch_to_red(self, direction):
        """Change the light to red for the given direction"""
        current_time = time.time()
        
        
        if self.traffic_lights[direction]["status"] != "RED":
            self.traffic_lights[direction]["status"] = "RED"
            self.traffic_lights[direction]["changed_time"] = current_time
            self.traffic_lights[direction]["color"] = (0, 0, 255)  
            
            
            self.last_change_time = current_time
            if direction not in self.recently_changed:
                self.recently_changed.append(direction)
            return True
        return False
    
    def switch_to_blue(self, direction):
        """Change the light to blue for the given direction"""
        if self.traffic_lights[direction]["status"] != "BLUE":
            self.traffic_lights[direction]["status"] = "BLUE"
            self.traffic_lights[direction]["changed_time"] = time.time()
            self.traffic_lights[direction]["color"] = (255, 150, 0)  
            
            
            if direction in self.recently_changed:
                self.recently_changed.remove(direction)
            return True
        return False
    
    def switch_to_green(self, direction):
        """Change the light to green for the given direction"""
        if self.traffic_lights[direction]["status"] != "GREEN":
            self.traffic_lights[direction]["status"] = "GREEN"
            self.traffic_lights[direction]["changed_time"] = time.time()
            self.traffic_lights[direction]["color"] = (0, 255, 0)  
            
            
            if direction in self.recently_changed:
                self.recently_changed.remove(direction)
            return True
        return False
    
    def adjust_light_duration(self, direction, vehicle_count):
        """Adjust traffic light duration based on vehicle count"""
        base_duration = 30  
        
        
        if vehicle_count < 3:
            
            new_duration = 20
        elif vehicle_count < 10:
            
            new_duration = base_duration
        else:
            
            new_duration = base_duration + min(30, (vehicle_count - 10) * 2)
        
        new_duration = max(15, min(60, new_duration))

        if self.traffic_lights[direction]["duration"] != new_duration:
            self.traffic_lights[direction]["duration"] = new_duration
            return True
        
        return False
    
    def toggle_auto_mode(self):
        """Toggle automatic mode on/off"""
        self.auto_mode = not self.auto_mode
        return self.auto_mode
    
    def check_light_durations(self):
        """Check and automatically adjust traffic light durations"""
        current_time = time.time()
        
        
        if not self.auto_mode or current_time - self.last_auto_check < self.auto_check_interval:
            return False
            
        
        self.last_auto_check = current_time
            
        changes_made = False
        
        
        for direction, light in self.traffic_lights.items():
            
            if light["status"] == "RED" and current_time - light["changed_time"] > light["duration"]:
                
                if self.switch_to_blue(direction):
                    changes_made = True
                    
        return changes_made
    
    def handle_stalled_zone(self, zone):
        """Turn off lights related to zones with stalled vehicles"""
        if not zone.is_stalled:
            return False
            
        current_time = time.time()
        
        
        if current_time - self.last_change_time < self.min_change_interval:
            return False
        
        
        # if current_time - zone.last_update_time < 0.0:
        if current_time - zone.last_update_time < 10.0:
            return False
            
        changes_made = False
        
        for direction in zone.traffic_light_directions:
            high_priority = True  
            self.adjust_light_duration(direction, len(zone.current_vehicles) * 2 if high_priority else len(zone.current_vehicles))
            
            if self.switch_to_red(direction):
                changes_made = True
                print(f"WARNING: Vehicles stalled in zone {zone.name}, changing {self.direction_names.get(direction, direction)} direction to red!")
                
        return changes_made
    
    def handle_detection(self, zone):
        """Turn off lights related to zones with vehicle detections"""
        if len(zone.current_vehicles) == 0:
            return False
        
        current_time = time.time()
        
        
        # if current_time - zone.last_update_time < 0.0:
        if current_time - zone.last_update_time < 10.0:
            return False
            
        changes_made = False
        
        
        for direction in zone.traffic_light_directions:
            
            self.adjust_light_duration(direction, len(zone.current_vehicles))
            
            if self.switch_to_red(direction):
                changes_made = True
                print(f"NOTICE: Vehicles detected in zone {zone.name}, changing {self.direction_names.get(direction, direction)} direction to red!")
                
        return changes_made
    
    def handle_empty_zone(self, zone):
        """Turn on lights related to zones that have become empty"""
        if len(zone.current_vehicles) > 0:
            return False
            
        current_time = time.time()
        
        
        if current_time - self.last_change_time < 5:
            return False
            
        changes_made = False
        
        
        for direction in zone.traffic_light_directions:
            
            self.adjust_light_duration(direction, 0)
            
            if self.switch_to_blue(direction):
                changes_made = True
                print(f"NOTICE: No vehicles in zone {zone.name}, changing {self.direction_names.get(direction, direction)} direction to blue!")
                
        return changes_made
    
    def manage_traffic_congestion(self, zones):
        """Check all zones and adjust lights for congested areas"""
        changes_made = False
        
        
        if self.check_light_durations():
            changes_made = True
        
        
        for zone in zones:
            
            if zone.is_stalled:
                if self.handle_stalled_zone(zone):
                    changes_made = True
            elif len(zone.current_vehicles) == 0:
                if self.handle_empty_zone(zone):
                    changes_made = True
            
            elif len(zone.current_vehicles) > 0:
                if self.handle_detection(zone):
                    changes_made = True
                
        return changes_made
    
    def draw_traffic_light_status(self, frame):
        """Display traffic light status on screen"""
        height, width = frame.shape[:2]
        light_size = 25
        margin = 10
        line_spacing = 30
        
        
        cv2.putText(frame, "TRAFFIC LIGHT STATUS:", 
                   (width - 300, margin + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        
        y_offset = margin + 50
        
        for section, directions in self.direction_groups.items():
            
            section_title = ""
            if section == "West": section_title = "FROM WEST:"
            elif section == "East": section_title = "FROM EAST:"
            elif section == "North": section_title = "FROM NORTH:"
            elif section == "South": section_title = "FROM SOUTH:"
            
            cv2.putText(frame, section_title, 
                      (width - 300, y_offset), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            y_offset += 25
            
            
            for direction in directions:
                light = self.traffic_lights[direction]
                
                
                if light["status"] == "RED":
                    color = (0, 0, 255)  
                elif light["status"] == "BLUE":
                    color = (255, 150, 0)  
                else:
                    color = (0, 255, 0)  
                
                
                short_description = direction.split('_')[1]  
                
                
                cv2.circle(frame, (width - 270, y_offset - 5), light_size // 2, color, -1)
                
                
                cv2.putText(frame, short_description, 
                           (width - 250, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                y_offset += line_spacing
            
            
            y_offset += 10
        
        
        if self.recently_changed:
            num_display = min(3, len(self.recently_changed))  
            short_directions = [self.direction_names.get(d, d) for d in self.recently_changed[:num_display]]
            
            if len(self.recently_changed) > num_display:
                notification = "Red lights: " + ", ".join(short_directions) + f"... +{len(self.recently_changed) - num_display}"
            else:
                notification = "Red lights: " + ", ".join(short_directions)
                
            cv2.putText(frame, notification, (10, height - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
        return frame
