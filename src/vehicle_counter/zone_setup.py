import cv2
import numpy as np
from zone_manager import Zone
import os

class ZoneSetupUI:
    """
    UI for zone setup screen
    """
    
    def __init__(self, zone_manager, window_name="Setup Zones"):
        """
        Create zone setup UI
        
        Args:
            zone_manager: Zone manager
            window_name (str): Window name
        """
        self.zone_manager = zone_manager
        self.window_name = window_name
        self.thumbnail = None
        self.original_thumbnail = None
        self.selecting_type = False
        self.selecting_lights = False
        self.selecting_direction = False
        self.current_type = None
        self.selected_main_direction = None
        
        # Direction groups
        self.direction_groups = {
            "West": ["West_Left", "West_Straight", "West_Right"],
            "East": ["East_Left", "East_Straight", "East_Right"],
            "North": ["North_Left", "North_Straight", "North_Right"],
            "South": ["South_Left", "South_Straight", "South_Right"]
        }

        # Direction descriptions
        self.direction_names = {
            "West": "From West",
            "East": "From East",
            "North": "From North",
            "South": "From South",
            "Left": "Turn Left",
            "Straight": "Go Straight",
            "Right": "Turn Right"
        }
        
        self.selected_directions = []
        # Track selected main directions
        self.selected_main_directions = []
    
    def setup_mouse_callback(self):
        """
        Set up mouse click callback
        """
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)
    
    def _mouse_callback(self, event, x, y, flags, param):
        """
        Process mouse click events
        
        Args:
            event: Event type
            x, y: Coordinates
            flags: Additional flags
            param: Additional parameters
        """
        if self.selecting_type:
            # Type selection screen
            if event == cv2.EVENT_LBUTTONDOWN:
                if 50 <= x <= 150 and 50 <= y <= 100:  # COUNT type
                    self.current_type = Zone.ZONE_TYPE_COUNT
                    self.selecting_type = False
                    self.selecting_direction = True
                    self.selected_main_directions = []  # Reset selected main directions
                    self._show_main_direction_selection()
                elif 200 <= x <= 300 and 50 <= y <= 100:  # SUM type
                    self.current_type = Zone.ZONE_TYPE_SUM
                    self.selecting_type = False
                    self.selecting_direction = True
                    self.selected_main_directions = []  # Reset selected main directions
                    self._show_main_direction_selection()
        
        elif self.selecting_direction:
            # Traffic light main direction selection screen
            if event == cv2.EVENT_LBUTTONDOWN:
                # Check directions
                button_width = 150
                button_height = 50
                button_margin = 20
                
                # Check Done button
                if 200 <= x <= 350 and 400 <= y <= 450:
                    if self.selected_directions:
                        self.selecting_direction = False
                        self.selecting_lights = False
                        self._complete_zone_creation()
                    return
                
                for i, direction in enumerate(["West", "East", "North", "South"]):
                    # 2x2 grid buttons
                    row = i // 2
                    col = i % 2
                    
                    btn_x = 50 + col * (button_width + button_margin)
                    btn_y = 150 + row * (button_height + button_margin)
                    
                    if btn_x <= x <= btn_x + button_width and btn_y <= y <= btn_y + button_height:
                        # Select/deselect main direction
                        self.selected_main_direction = direction
                        # Only proceed to lights selection if not already selected
                        if direction not in self.selected_main_directions:
                            self.selected_main_directions.append(direction)
                            self.selecting_direction = False
                            self.selecting_lights = True
                            self._show_traffic_light_selection()
                        else:
                            # If already selected, highlight and show which lights are selected
                            self.selected_main_direction = direction
                            self.selecting_direction = False
                            self.selecting_lights = True
                            self._show_traffic_light_selection()
                        break
        
        elif self.selecting_lights:
            # Traffic light direction selection screen
            if event == cv2.EVENT_LBUTTONDOWN:
                # Back button to return to main direction selection
                if 50 <= x <= 180 and 400 <= y <= 450:
                    self.selecting_lights = False
                    self.selecting_direction = True
                    self._show_main_direction_selection()
                    return
                
                # Done button for current direction
                elif 200 <= x <= 350 and 400 <= y <= 450:
                    self.selecting_lights = False
                    self.selecting_direction = True
                    self._show_main_direction_selection()
                    return
                
                # Check direction buttons (turn left, straight, turn right)
                for i, turn_type in enumerate(["Left", "Straight", "Right"]):
                    full_direction = f"{self.selected_main_direction}_{turn_type}"
                    
                    if 50 <= x <= 150 and (180 + i*60) <= y <= (220 + i*60):
                        # Add/remove selected direction
                        if full_direction in self.selected_directions:
                            self.selected_directions.remove(full_direction)
                        else:
                            self.selected_directions.append(full_direction)
                        # Show selection again
                        self._show_traffic_light_selection()
        else:
            # Zone creation screen
            if event == cv2.EVENT_LBUTTONDOWN:
                # Add new point
                self.zone_manager.add_point_to_current_polygon(x, y)
                # Draw new point
                if self.thumbnail is not None:
                    cv2.circle(self.thumbnail, (x, y), 3, (0, 0, 255), -1)
            
            elif event == cv2.EVENT_RBUTTONDOWN:
                # Finish zone creation
                if self.zone_manager.is_current_polygon_valid():
                    self.selecting_type = True
                    self.selected_directions = []  # Clear directions
                    self.selected_main_directions = []  # Clear main directions
                    self._show_type_selection()
    
    def _show_type_selection(self):
        """
        Show zone type selection screen
        """
        if self.thumbnail is None:
            return
            
        # Create copy of current screen
        selection_img = self.thumbnail.copy()
        
        # Draw type selection buttons
        cv2.rectangle(selection_img, (50, 50), (150, 100), (0, 255, 0), -1)
        cv2.putText(selection_img, "COUNT", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        cv2.rectangle(selection_img, (200, 50), (300, 100), (0, 120, 255), -1)
        cv2.putText(selection_img, "SUM", (210, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        # Description
        cv2.putText(selection_img, "COUNT: Count vehicles passing through the zone", 
                   (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(selection_img, "SUM: Count vehicles currently in the zone", 
                   (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow(self.window_name, selection_img)
    
    def _show_main_direction_selection(self):
        """
        Show traffic light main direction selection screen
        """
        if self.thumbnail is None:
            return
            
        # Create copy of current screen
        direction_img = self.thumbnail.copy()
        
        # Description text
        cv2.putText(direction_img, "Which direction of traffic does this zone affect?", 
                   (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(direction_img, "Select multiple directions (one by one)", 
                   (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Draw directions - 2x2 grid
        button_width = 150
        button_height = 50
        button_margin = 20
        
        for i, direction in enumerate(["West", "East", "North", "South"]):
            # 2x2 grid buttons
            row = i // 2
            col = i % 2
            
            btn_x = 50 + col * (button_width + button_margin)
            btn_y = 150 + row * (button_height + button_margin)
            
            # Draw button - highlight already selected directions
            color = (0, 255, 0) if direction in self.selected_main_directions else (0, 150, 255)
            cv2.rectangle(direction_img, (btn_x, btn_y), (btn_x + button_width, btn_y + button_height), color, -1)
            
            # Button text
            cv2.putText(direction_img, self.direction_names[direction], 
                      (btn_x + 10, btn_y + 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show selected directions count
        cv2.putText(direction_img, f"Selected: {len(self.selected_directions)} traffic lights", 
                  (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        
        # Done button (only if directions selected)
        btn_color = (0, 255, 0) if self.selected_directions else (150, 150, 150)
        cv2.rectangle(direction_img, (200, 400), (350, 450), btn_color, -1)
        cv2.putText(direction_img, "Done", (245, 430), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show screen
        cv2.imshow(self.window_name, direction_img)
    
    def _show_traffic_light_selection(self):
        """
        Show traffic light direction selection screen
        """
        if self.thumbnail is None:
            return
            
        # Create copy of current screen
        light_selection_img = self.thumbnail.copy()
        
        # Description
        main_dir_name = self.direction_names.get(self.selected_main_direction, self.selected_main_direction)
        cv2.putText(light_selection_img, f"Which traffic lights apply to the {main_dir_name} direction?", 
                   (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Traffic light selection buttons
        for i, turn_type in enumerate(["Left", "Straight", "Right"]):
            full_direction = f"{self.selected_main_direction}_{turn_type}"
            
            # Select color based on selection
            color = (0, 255, 0) if full_direction in self.selected_directions else (200, 200, 200)
            
            # Draw button
            cv2.rectangle(light_selection_img, (50, 180 + i*60), (150, 220 + i*60), color, -1)
            cv2.putText(light_selection_img, self.direction_names[turn_type], (60, 200 + i*60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        # Back button to return to direction selection
        cv2.rectangle(light_selection_img, (50, 400), (180, 450), (0, 120, 255), -1)
        cv2.putText(light_selection_img, "Back", (90, 430), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Done button for this direction
        cv2.rectangle(light_selection_img, (200, 400), (350, 450), (0, 255, 0), -1)
        cv2.putText(light_selection_img, "Done", (245, 430), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Selected directions information
        cv2.putText(light_selection_img, "Selected directions:", 
                   (200, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # List selected directions
        for i, direction in enumerate(self.selected_directions):
            direction_parts = direction.split('_')
            if len(direction_parts) == 2:
                main_dir = self.direction_names.get(direction_parts[0], direction_parts[0])
                turn_type = self.direction_names.get(direction_parts[1], direction_parts[1])
                display_name = f"{main_dir} {turn_type}"
            else:
                display_name = direction
                
            # Only show a limited number of items to avoid overflow
            if i < 8:
                cv2.putText(light_selection_img, display_name, 
                           (200, 210 + i*30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            elif i == 8:
                cv2.putText(light_selection_img, f"... and {len(self.selected_directions)-8} more", 
                           (200, 210 + i*30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Show screen
        cv2.imshow(self.window_name, light_selection_img)
    
    def _complete_zone_creation(self):
        """
        Complete zone creation
        """
        # Create new zone
        zone = self.zone_manager.create_zone(
            self.zone_manager.current_polygon,
            self.current_type
        )
        
        # Configure selected traffic lights
        zone.traffic_light_directions = self.selected_directions.copy()
        
        # Log
        print(f"Zone {zone.id} added with type {zone.type}")
        
        # Print selected directions
        direction_names = []
        for direction in zone.traffic_light_directions:
            direction_parts = direction.split('_')
            if len(direction_parts) == 2:
                main_dir = self.direction_names.get(direction_parts[0], direction_parts[0])
                turn_type = self.direction_names.get(direction_parts[1], direction_parts[1])
                direction_names.append(f"{main_dir} {turn_type}")
            else:
                direction_names.append(direction)
        
        print(f"Traffic light directions: {', '.join(direction_names)}")
        
        # Prepare new zone
        self.zone_manager.reset_current_polygon()
        self.current_type = None
        self.selected_directions = []
        self.selected_main_directions = []
        self.selected_main_direction = None
        
        # Update zone image
        display_img = self.original_thumbnail.copy()
        display_img = self.zone_manager.draw_zones(display_img)
        self.thumbnail = display_img
        cv2.imshow(self.window_name, self.thumbnail)
    
    def setup_from_frame(self, frame):
        """
        Create zone setup screen from video frame
        
        Args:
            frame (numpy.ndarray): Video frame
            
        Returns:
            bool: Whether setup was completed
        """
        # Хуучин горим
        if not os.environ.get('HEADLESS', '0') == '1':
            self.thumbnail = frame.copy()
            self.original_thumbnail = frame.copy()
            
            self.setup_mouse_callback()
            cv2.imshow(self.window_name, self.thumbnail)
            
            print("Zone creation instructions:")
            print("- Click left button to select zone points")
            print("- Click right button to finish the zone")
            print("- Click COUNT or SUM button to select zone type")
            print("- Select multiple directions as needed")
            print("- Press Enter to finish zone configuration")
            print("- Press 'c' to clear zone points")
            
            zone_mode = True
            while zone_mode:
                # Update screen
                display_img = self.original_thumbnail.copy()
                
                # Draw current polygon
                display_img = self.zone_manager.draw_current_polygon(display_img)
                
                # Draw zones
                display_img = self.zone_manager.draw_zones(display_img)
                
                # Update screen
                if not (self.selecting_type or self.selecting_direction or self.selecting_lights):
                    self.thumbnail = display_img
                    cv2.imshow(self.window_name, self.thumbnail)
                
                # Wait for user input
                key = cv2.waitKey(1)
                if key == 13:  # Enter key
                    if self.zone_manager.is_current_polygon_valid():
                        print("Unfinished zone exists. Please finish the zone first.")
                    else:
                        print("Zone configuration completed.")
                        zone_mode = False
                elif key == ord('q'):
                    print("Cancelled.")
                    cv2.destroyWindow(self.window_name)
                    return False
                elif key == ord('c'):
                    self.zone_manager.reset_current_polygon()
                    print("Current polygon cleared.")
            
            cv2.destroyWindow(self.window_name)
            return True
        else:
            # Headless горим - автоматаар зоны тохиргоо хийх
            print("Running in headless mode, creating predefined zones automatically")
            
            # Зургийн хэмжээ авах
            height, width = frame.shape[:2]
            
            # Дөрвөн зоны тохиргоо
            zones_config = [
                {
                    "name": "Зүүн зам",
                    "points": [
                        (int(width * 0.05), int(height * 0.4)),
                        (int(width * 0.3), int(height * 0.4)), 
                        (int(width * 0.3), int(height * 0.6)),
                        (int(width * 0.05), int(height * 0.6))
                    ],
                    "type": Zone.ZONE_TYPE_COUNT,
                    "directions": ["West_Straight", "West_Right"]
                },
                {
                    "name": "Баруун зам",
                    "points": [
                        (int(width * 0.7), int(height * 0.4)),
                        (int(width * 0.95), int(height * 0.4)),
                        (int(width * 0.95), int(height * 0.6)),
                        (int(width * 0.7), int(height * 0.6))
                    ],
                    "type": Zone.ZONE_TYPE_COUNT,
                    "directions": ["East_Straight", "East_Left"]
                },
                {
                    "name": "Дээд зам",
                    "points": [
                        (int(width * 0.4), int(height * 0.05)),
                        (int(width * 0.6), int(height * 0.05)),
                        (int(width * 0.6), int(height * 0.3)),
                        (int(width * 0.4), int(height * 0.3))
                    ],
                    "type": Zone.ZONE_TYPE_COUNT,
                    "directions": ["North_Straight", "North_Right"]
                },
                {
                    "name": "Доод зам",
                    "points": [
                        (int(width * 0.4), int(height * 0.7)),
                        (int(width * 0.6), int(height * 0.7)),
                        (int(width * 0.6), int(height * 0.95)),
                        (int(width * 0.4), int(height * 0.95))
                    ],
                    "type": Zone.ZONE_TYPE_COUNT,
                    "directions": ["South_Straight", "South_Left"]
                },
                {
                    "name": "Уулзварын төв",
                    "points": [
                        (int(width * 0.3), int(height * 0.3)),
                        (int(width * 0.7), int(height * 0.3)),
                        (int(width * 0.7), int(height * 0.7)),
                        (int(width * 0.3), int(height * 0.7))
                    ],
                    "type": Zone.ZONE_TYPE_SUM,
                    "directions": ["West_Straight", "East_Straight", "North_Straight", "South_Straight"]
                }
            ]
            
            # Зонуудыг бүгдийг давтан үүсгэх
            created_zones = 0
            for zone_config in zones_config:
                self.zone_manager.reset_current_polygon()
                
                # Зон цэгүүдийг нэмэх
                for point in zone_config["points"]:
                    self.zone_manager.add_point_to_current_polygon(*point)
                
                # Зон үүсгэх
                zone = self.zone_manager.create_zone(
                    self.zone_manager.current_polygon,
                    zone_config["type"]
                )
                
                # Зоны нэр болон чиглэлүүдийг тохируулах
                zone.name = zone_config["name"]
                zone.traffic_light_directions = zone_config["directions"]
                created_zones += 1
            
            print(f"Created {created_zones} predefined zones automatically")
            return True
