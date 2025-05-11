import cv2
import time
import os
import json
from datetime import datetime

from vehicle_detector import VehicleDetector
from zone_manager import Zone, ZoneManager
from vehicle_tracker import VehicleTracker
from zone_setup import ZoneSetupUI
from traffic_light_controller import TrafficLightController


class VehicleCounterService:
    """
    Main service for vehicle counting
    """
    
    def __init__(self, video_path=None, model_path="yolov8s.pt", device="cpu", output_path="data"):
        """
        Initialize vehicle counting service
        
        Args:
            video_path (str): Video file path (None for camera)
            model_path (str): YOLO model path
            device (str): Device to use (cpu, cuda, mps)
            output_path (str): Output data path
        """
        self.video_path = video_path
        self.model_path = model_path
        self.device = device
        self.output_path = output_path
        
        # Service components
        self.detector = VehicleDetector(model_path, device)
        self.zone_manager = ZoneManager()
        self.tracker = VehicleTracker()
        self.traffic_light_controller = TrafficLightController()
        
        # Video processing
        self.cap = None
        self.frame_count = 0
        self.start_time = None
        self.fps = 0
        self.processing = False
        
        # Create output path
        os.makedirs(output_path, exist_ok=True)
    
    def _open_video_capture(self):
        """
        Open video capture or camera
        
        Returns:
            bool: Success status
        """
        if self.video_path is None:
            self.cap = cv2.VideoCapture(0)  # Default camera
        else:
            self.cap = cv2.VideoCapture(self.video_path)
        
        return self.cap.isOpened()
    
    def _close_video_capture(self):
        """
        Close video capture
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def _setup_zones(self):
        """
        Setup zones
        
        Returns:
            bool: Success status
        """
        # Open video
        if not self._open_video_capture():
            print("Failed to open video or camera.")
            return False
        
        # Get first frame
        ret, frame = self.cap.read()
        if not ret:
            print("Failed to read video frame.")
            self._close_video_capture()
            return False
        
        # Zone setup UI
        ui = ZoneSetupUI(self.zone_manager)
        result = ui.setup_from_frame(frame)
        
        # Close video
        self._close_video_capture()
        
        # Tracker initialization
        if result:
            self.tracker.initialize_zones(self.zone_manager.zones)
        
        return result
    
    def _save_data(self, frame_number, timestamp, zones_data):
        """
        Save counting data
        
        Args:
            frame_number (int): Frame number
            timestamp (float): Timestamp
            zones_data (dict): Zone data
        """
        # Prepare data
        data = {
            "frame": frame_number,
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "zones": []
        }
        
        # Data for each zone
        for zone in self.zone_manager.zones:
            zone_data = {
                "id": zone.id,
                "name": zone.name,
                "type": "COUNT" if zone.is_count_zone() else "SUM",
                "count": zone.get_display_count(),
                "vehicles": list(zones_data.get("zone_vehicles", {}).get(zone.id, [])),
                "is_stalled": zone.is_stalled,
                "traffic_lights": zone.traffic_light_directions
            }
            data["zones"].append(zone_data)
        
        # Create JSON file name
        timestamp_str = datetime.fromtimestamp(timestamp).strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_path}/vehicle_data_{timestamp_str}.json"
        
        # Save data
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    
    def start_counting(self, display=True, save_data=True, save_video=False):
        """
        Start vehicle counting process
        
        Args:
            display (bool): Display video
            save_data (bool): Save data
            save_video (bool): Save processed video
            
        Returns:
            bool: Process success
        """
        # Setup zones
        if not self._setup_zones():
            return False
        
        # Check if zones are setup
        if len(self.zone_manager.zones) == 0:
            print("No zones configured. Process finished.")
            return False
        
        # Open video
        if not self._open_video_capture():
            print("Failed to open video or camera.")
            return False
        
        # Video writer setup
        video_writer = None
        if save_video and self.video_path is not None:
            # Video parameters
            frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            # Create output file name
            video_filename = os.path.basename(self.video_path)
            output_path = f"{self.output_path}/{os.path.splitext(video_filename)[0]}_output.mp4"
            
            # Video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        
        # Start counting process
        self.processing = True
        self.frame_count = 0
        self.start_time = time.time()
        last_save_time = time.time()  # Last save time
        save_interval = 60  # Save interval (seconds)
        last_statistics_time = time.time()  # Last statistics update time
        statistics_interval = 5  # Statistics update interval (seconds)
        
        # Start API server (if specified in constructor)
        try:
            from api import start_api
            api_thread = start_api(vehicle_counter=self, host="0.0.0.0", port=8000)
            print("API server started successfully (port 8000)")
        except Exception as e:
            print(f"Error starting API server: {e}")
        
        # Main counting loop
        try:
            while self.cap.isOpened() and self.processing:
                # Read frame
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                self.frame_count += 1
                current_time = time.time()
                
                # Detect vehicles
                detections = self.detector.detect_vehicles(frame)
                
                # If detect_vehicles function returns one object, unpack it
                if isinstance(detections, tuple) and len(detections) == 3:
                    boxes, scores, class_ids = detections
                else:
                    # For old version of detector, use detected objects directly
                    boxes = []
                    scores = []
                    class_ids = []
                    
                    if detections:
                        for det in detections:
                            if isinstance(det, dict) and 'box' in det:
                                x1, y1, x2, y2 = det['box']
                                boxes.append([x1, y1, x2, y2])
                                scores.append(det.get('confidence', 1.0))
                                class_ids.append(det.get('class_id', 0))
                
                # Track vehicles
                try:
                    tracked_objects, zone_vehicles = self.tracker.track_vehicles(
                        frame, boxes, scores, class_ids, self.zone_manager.zones
                    )
                except Exception as e:
                    print(f"Tracking error: {e}")
                    tracked_objects = []
                    zone_vehicles = {}
                
                # Update statistics for each zone
                if current_time - last_statistics_time >= statistics_interval:
                    for zone in self.zone_manager.zones:
                        zone.update_statistics()
                    last_statistics_time = current_time
                
                # Manage traffic lights
                if self.traffic_light_controller.manage_traffic_congestion(self.zone_manager.zones):
                    print(f"Frame {self.frame_count}: Traffic light status changed.")
                
                # Display processed image
                if display:
                    # Calculate FPS
                    elapsed_time = current_time - self.start_time
                    if elapsed_time > 0:
                        self.fps = self.frame_count / elapsed_time
                    
                    # Draw FPS
                    cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Draw congestion information
                    congestion_status = self.get_congestion_status()
                    congestion_level = congestion_status.get("level", "Normal")
                    congestion_color = (0, 255, 0)  # Green - Normal
                    
                    if congestion_level == "Medium":
                        congestion_color = (0, 165, 255)  # Yellow
                    elif congestion_level == "High":
                        congestion_color = (0, 0, 255)  # Red
                    
                    cv2.putText(frame, f"Congestion: {congestion_level}", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, congestion_color, 2)
                    
                    # Draw zones
                    frame = self.zone_manager.draw_zones(frame)
                    
                    # Draw current polygon
                    frame = self.zone_manager.draw_current_polygon(frame)
                    
                    # Draw vehicles
                    for obj in tracked_objects:
                        x1, y1, x2, y2 = obj["bbox"]
                        track_id = obj["id"]
                        
                        # Draw vehicle box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        
                        # Draw ID
                        cv2.putText(frame, f"ID: {track_id}", (x1, y1 - 10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    
                    # Draw traffic light status
                    frame = self.traffic_light_controller.draw_traffic_light_status(frame)
                    
                    # Show image
                    cv2.imshow("Vehicle Counter", frame)
                    
                    # Exit
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:  # ESC
                        break
                
                # Write video
                if video_writer is not None:
                    video_writer.write(frame)
                
                # Save data
                if save_data and current_time - last_save_time >= save_interval:
                    self._save_data(self.frame_count, current_time, {"zone_vehicles": zone_vehicles})
                    last_save_time = current_time
                    
                    # Save statistics
                    self._save_statistics(current_time)
        
        except KeyboardInterrupt:
            print("Process stopped by user request.")
        except Exception as e:
            print(f"Process stopped with error: {e}")
        finally:
            # Cleanup
            self.processing = False
            self._close_video_capture()
            
            if video_writer is not None:
                video_writer.release()
            
            cv2.destroyAllWindows()
            
            # Save final data
            if save_data:
                self._save_data(self.frame_count, time.time(), {})
                self._save_statistics(time.time())
            
            print(f"Vehicle counting process finished. Processed {self.frame_count} frames total.")
            
            return True
    
    def _save_statistics(self, timestamp):
        """
        Save statistics data
        
        Args:
            timestamp (float): Timestamp
        """
        # Get all zone statistics
        all_stats = self.zone_manager.get_all_statistics()
        
        # Prepare summary
        summary = {
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "total_zones": len(all_stats),
            "congestion_status": self.get_congestion_status(),
            "traffic_lights": {
                "auto_mode": self.traffic_light_controller.auto_mode,
                "red_light_count": sum(1 for light in self.traffic_light_controller.traffic_lights.values() if light["status"] == "RED"),
                "blue_light_count": sum(1 for light in self.traffic_light_controller.traffic_lights.values() if light["status"] == "BLUE"),
                "green_light_count": sum(1 for light in self.traffic_light_controller.traffic_lights.values() if light["status"] == "GREEN")
            }
        }
        
        # Create JSON file name
        timestamp_str = datetime.fromtimestamp(timestamp).strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_path}/statistics_{timestamp_str}.json"
        
        # Save data
        with open(filename, "w") as f:
            json.dump({"zones": all_stats, "summary": summary}, f, indent=2)
    
    def stop_counting(self):
        """
        Stop counting process
        
        Returns:
            bool: Process stopped
        """
        if self.processing:
            self.processing = False
            return True
        return False
    
    def get_congestion_status(self):
        """
        Get current congestion information
        
        Returns:
            dict: Congestion information
        """
        zones_status = []
        total_vehicles = 0
        
        # Information for each zone
        for zone in self.zone_manager.zones:
            count = zone.get_display_count()
            total_vehicles += count
            
            # Determine congestion level function
            congestion_level = self._determine_congestion_level(zone)
            
            # Zone information
            zone_data = {
                "id": zone.id,
                "name": zone.name,
                "type": "COUNT" if zone.is_count_zone() else "SUM",
                "vehicle_count": count,
                "is_stalled": zone.is_stalled,
                "congestion_level": congestion_level,
                "traffic_lights": {
                    direction: self.traffic_light_controller.traffic_lights[direction]["status"]
                    for direction in zone.traffic_light_directions
                }
            }
            
            zones_status.append(zone_data)
        
        return {
            "timestamp": time.time(),
            "total_vehicles": total_vehicles,
            "zones": zones_status
        }
    
    def _determine_congestion_level(self, zone):
        """
        Determine zone congestion level
        
        Args:
            zone (Zone): Zone
            
        Returns:
            str: Congestion level (LOW/MEDIUM/HIGH)
        """
        count = zone.get_display_count()
        
        if zone.is_stalled:
            return "HIGH"  # If vehicles are stalled for a long time, high congestion
        
        if zone.is_count_zone():
            # Based on incoming vehicle count in COUNT zone
            if count < 5:
                return "LOW"
            elif count < 15:
                return "MEDIUM"
            else:
                return "HIGH"
        else:
            # Based on current vehicle count in SUM zone
            if count < 5:
                return "LOW"
            elif count < 10:
                return "MEDIUM"
            else:
                return "HIGH"
    
    def _check_vehicles_moving(self, zone, results):
        """Check if vehicles are moving in the zone"""
        zone_vehicles = results.get("zone_vehicles", {}).get(zone.id, [])
        if not zone_vehicles:
            return True
            
        # Check vehicle speed
        for vehicle_id in zone_vehicles:
            vehicle_data = self.tracker.tracked_objects.get(vehicle_id)
            if vehicle_data and vehicle_data.get("speed", 0) > 2.0:  # speed in km/h
                return True
                
        return False 