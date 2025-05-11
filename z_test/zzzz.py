import cv2
import numpy as np
from ultralytics import YOLO
from shapely.geometry import Point, Polygon
import time

model = YOLO("yolov8n.pt")

# Globals
current_zone_id = 1
zone_mode = True
zones = []  # List of dicts: {id, points, name, type, polygon}
vehicle_ids_in_frame = set()  # Set to track vehicles in the current frame
current_polygon = []  # Store points for the current polygon
selecting_type = False  # Flag to indicate if we're selecting zone type
current_type = None  # Current zone type (1 or 2)

# Vehicle tracking globals
tracked_vehicles = {}  # Dictionary to store tracked vehicles across frames
vehicles_in_zones = {}  # Track which vehicles are in which zones
cooldown_time = 2.0  # Cooldown time in seconds before counting the same vehicle again
iou_threshold = 0.3  # Threshold for considering boxes as the same vehicle

def check_type_selection(event, x, y, flags, param):
    global selecting_type, current_type
    
    if event == cv2.EVENT_LBUTTONDOWN:
        if 50 <= x <= 150 and 50 <= y <= 100:  # Type 1 button - COUNT
            current_type = 1
            selecting_type = False
        elif 200 <= x <= 300 and 50 <= y <= 100:  # Type 2 button - SUM
            current_type = 2
            selecting_type = False

def draw_zone(event, x, y, flags, param):
    global current_polygon, zones, current_zone_id, selecting_type, current_type, thumbnail

    if selecting_type:
        return

    if event == cv2.EVENT_LBUTTONDOWN:
        # Add a new point to the polygon
        current_polygon.append((x, y))
        # Draw the new point
        if len(current_polygon) > 0:
            cv2.circle(thumbnail, current_polygon[-1], 3, (0, 0, 255), -1)
    
    elif event == cv2.EVENT_RBUTTONDOWN:
        # Complete the polygon if it has at least 3 points
        if len(current_polygon) >= 3:
            # Create a copy of the current image to show type selection buttons
            selection_img = thumbnail.copy()
            selecting_type = True
            
            # Draw buttons for type selection
            cv2.rectangle(selection_img, (50, 50), (150, 100), (0, 255, 0), -1)
            cv2.putText(selection_img, "COUNT", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            
            cv2.rectangle(selection_img, (200, 50), (300, 100), (0, 120, 255), -1)
            cv2.putText(selection_img, "SUM", (210, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            
            cv2.imshow("Setup Zones", selection_img)
            
            # Set the mouse callback for type selection
            cv2.setMouseCallback("Setup Zones", check_type_selection)
            
            # Wait for type selection
            while selecting_type:
                key = cv2.waitKey(1)
                if key == ord('q'):
                    exit()
                
                if not selecting_type:
                    break
            
            # Reset mouse callback to draw_zone for creating more zones
            cv2.setMouseCallback("Setup Zones", draw_zone)
            
            # Create a zone with the selected type
            if current_type is not None:
                # Create a Shapely polygon for point-in-polygon testing
                poly = Polygon(current_polygon)
                
                # Get bounding box for display
                points_array = np.array(current_polygon)
                x_min, y_min = points_array.min(axis=0)
                
                zones.append({
                    "id": current_zone_id,
                    "points": current_polygon.copy(),
                    "name": f"Zone {current_zone_id}",
                    "type": current_type,
                    "polygon": poly
                })
                
                print(f"Zone {current_zone_id} added with type {current_type}")
                current_zone_id += 1
                current_polygon = []  # Reset for next polygon
                current_type = None

def is_inside_zone(x, y, zone):
    # Use Shapely for point-in-polygon test
    return zone["polygon"].contains(Point(x, y))

def calculate_iou(box1, box2):
    """
    Calculate IoU (Intersection over Union) between two bounding boxes
    Each box is [x1, y1, x2, y2]
    """
    # Calculate coordinates of intersection
    x1_inter = max(box1[0], box2[0])
    y1_inter = max(box1[1], box2[1])
    x2_inter = min(box1[2], box2[2])
    y2_inter = min(box1[3], box2[3])
    
    # Calculate area of intersection
    inter_width = max(0, x2_inter - x1_inter)
    inter_height = max(0, y2_inter - y1_inter)
    inter_area = inter_width * inter_height
    
    # Calculate areas of both boxes
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    # Calculate IoU
    union_area = box1_area + box2_area - inter_area
    if union_area == 0:
        return 0
    return inter_area / union_area

def track_vehicle(vehicle_box, current_time):
    """
    Track vehicles across frames using IoU
    Returns a unique vehicle ID and whether it's a new detection
    """
    global tracked_vehicles
    
    # If no tracked vehicles yet, add this one
    if not tracked_vehicles:
        vehicle_id = 1
        tracked_vehicles[vehicle_id] = vehicle_box
        return vehicle_id, True
    
    # Check if this vehicle matches any tracked vehicle
    best_iou = 0
    best_vehicle_id = None
    
    for vid, box in tracked_vehicles.items():
        iou = calculate_iou(vehicle_box, box)
        if iou > best_iou:
            best_iou = iou
            best_vehicle_id = vid
    
    # If found a good match
    if best_iou > iou_threshold:
        # Update the vehicle's position
        tracked_vehicles[best_vehicle_id] = vehicle_box
        return best_vehicle_id, False
    else:
        # New vehicle
        vehicle_id = max(tracked_vehicles.keys()) + 1 if tracked_vehicles else 1
        tracked_vehicles[vehicle_id] = vehicle_box
        return vehicle_id, True

# Load video
cap = cv2.VideoCapture("viiddeo.mov")
cv2.namedWindow("Setup Zones")
cv2.setMouseCallback("Setup Zones", draw_zone)

# ---- Step 1: Setup Zones ----
ret, frame = cap.read()
if not ret:
    print("Failed to load video.")
    cap.release()
    cv2.destroyAllWindows()
    exit()

thumbnail = frame.copy()  # Capture thumbnail (first frame)
original_thumbnail = thumbnail.copy()  # Keep a clean copy
cv2.imshow("Setup Zones", thumbnail)

# Instructions
print("Зоны үүсгэх заавар:")
print("- Зоны цэгүүдийг сонгохын тулд зүүн товчийг дарна")
print("- Зоныг дуусгахын тулд баруун товчийг дарна")
print("- Зоны төрлийг сонгохын тулд COUNT (тоолох) эсвэл SUM (нэмэгдүүлэх) товчийг дарна")
print("- Зоны тохиргоог дуусгахын тулд Enter товчийг дарна")
print("- Зоны цэгүүдийг цэвэрлэхийн тулд 'c' товчийг дарна")

zone_mode = True
while zone_mode:
    # Make a copy of the original image
    display_img = original_thumbnail.copy()
    
    # Draw the current polygon points and lines
    if len(current_polygon) > 0:
        # Draw all points
        for point in current_polygon:
            cv2.circle(display_img, point, 3, (0, 0, 255), -1)
        
        # Draw lines connecting points
        for i in range(len(current_polygon)):
            cv2.line(display_img, current_polygon[i], current_polygon[(i+1) % len(current_polygon)], (0, 0, 255), 1)
    
    # Draw completed zones
    for zone in zones:
        points = np.array(zone["points"])
        cv2.polylines(display_img, [points], True, (255, 0, 0), 2)
        
        # Label the zone
        if len(zone["points"]) > 0:
            label_pos = zone["points"][0]
            zone_type_name = "COUNT" if zone["type"] == 1 else "SUM"
            cv2.putText(display_img, f"{zone['name']} ({zone_type_name})", 
                        (label_pos[0], label_pos[1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    
    # Update the display
    thumbnail = display_img
    cv2.imshow("Setup Zones", thumbnail)
    
    # Wait for user interaction
    key = cv2.waitKey(1)
    if key == 13:  # Enter key to finish zone setup
        if len(current_polygon) >= 3:  # If user is in the middle of creating a zone
            print("Дуусгаагүй зон байна. Эхлээд зоныг дуусгана уу.")
        else:
            print("Зоны тохиргоо дууслаа.")
            zone_mode = False
    elif key == ord('q'):  # Cancel zone setup
        print("Цуцаллаа.")
        cap.release()
        cv2.destroyAllWindows()
        exit()
    elif key == ord('c'):  # Clear current polygon
        current_polygon = []
        thumbnail = original_thumbnail.copy()

cv2.destroyWindow("Setup Zones")
cap.release()

# ---- Step 2: Start Detection ----
cap = cv2.VideoCapture("viiddeo.mov")  # Restart video capture
vehicle_counts = {zone['id']: 0 for zone in zones}  # Initialize vehicle counts for each zone

# Initialize vehicle tracking structures
tracked_vehicles.clear()
vehicles_in_zones = {zone['id']: set() for zone in zones}
vehicles_zone_history = {}  # Track which vehicles were in which zones and timestamps

# For debugging and counting
frame_count = 0
start_time = time.time()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_count += 1
    current_time = time.time()
    
    # Process every frame
    results = model(frame)[0]

    # Track vehicles in current frame
    current_vehicles = {}  # Vehicle ID -> box
    current_vehicle_positions = {}  # Vehicle ID -> (center_x, center_y)
    
    # Keep track of which vehicles are in which zones in this frame
    vehicles_in_zones_current = {zone['id']: set() for zone in zones}

    for r in results.boxes.data.tolist():
        x1, y1, x2, y2, score, cls_id = r
        
        # Convert coordinates to integers
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        
        label = model.names[int(cls_id)]

        if label in ['car', 'bus', 'truck', 'motorbike']:
            # Center of the bounding box
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            # Track this vehicle
            vehicle_id, is_new = track_vehicle([x1, y1, x2, y2], current_time)
            
            # Store this vehicle's current position
            current_vehicles[vehicle_id] = [x1, y1, x2, y2]
            current_vehicle_positions[vehicle_id] = (cx, cy)
            
            # Draw bounding box for the vehicle
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, f"ID: {vehicle_id}", (x1, y1+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            # Check which zone this vehicle is in
            for zone in zones:
                if is_inside_zone(cx, cy, zone):
                    # Add vehicle to the current zone
                    vehicles_in_zones_current[zone['id']].add(vehicle_id)
                    
                    # For counting behavior (Type 1 - COUNT) - count when vehicle enters the zone
                    if zone["type"] == 1:
                        # If this vehicle wasn't in this zone in the previous frame
                        if vehicle_id not in vehicles_in_zones[zone['id']]:
                            # Check if this vehicle has been in this zone before
                            if vehicle_id not in vehicles_zone_history:
                                vehicles_zone_history[vehicle_id] = {}
                            
                            # If we haven't seen it in this zone before, or it's been long enough
                            last_entry_time = vehicles_zone_history.get(vehicle_id, {}).get(zone['id'], 0)
                            if zone['id'] not in vehicles_zone_history[vehicle_id] or (current_time - last_entry_time) > cooldown_time:
                                # Count it
                                vehicle_counts[zone['id']] += 1
                                # Record the entry time for this zone
                                vehicles_zone_history[vehicle_id][zone['id']] = current_time
                    
                    # For sum behavior (Type 2 - SUM) - simply add to total when in zone
                    # The count will be updated later based on zone_counts

    # Update the zone count for Type 2 zones (SUM)
    zone_counts = {zone['id']: len(vehicles_in_zones_current[zone['id']]) for zone in zones if zone['type'] == 2}
    
    # Update our tracking of which vehicles are in which zones
    vehicles_in_zones = vehicles_in_zones_current
    
    # Clean up old vehicle tracks that haven't been seen for a while
    current_time = time.time()
    all_vehicle_ids = set(current_vehicles.keys())
    for vid in list(tracked_vehicles.keys()):
        if vid not in all_vehicle_ids:
            # Vehicle not in current frame
            # Remove after 5 seconds
            if vid in vehicles_zone_history and 'last_seen' in vehicles_zone_history[vid]:
                if current_time - vehicles_zone_history[vid]['last_seen'] > 5.0:
                    tracked_vehicles.pop(vid, None)
        else:
            # Update the last seen time
            if vid not in vehicles_zone_history:
                vehicles_zone_history[vid] = {}
            vehicles_zone_history[vid]['last_seen'] = current_time

    # Display zones and counts on the frame
    for zone in zones:
        # Draw polygon
        points = np.array(zone["points"])
        zone_color = (0, 255, 0) if zone["type"] == 1 else (0, 120, 255)  # Green for COUNT, Orange for SUM
        cv2.polylines(frame, [points], True, zone_color, 2)
        
        # Display count
        if len(zone["points"]) > 0:
            label_pos = zone["points"][0]
            if zone["type"] == 1:  # COUNT
                count_text = f"{zone['name']}: {vehicle_counts[zone['id']]}"
            else:  # SUM
                count_text = f"{zone['name']}: {zone_counts[zone['id']]}"
            
            cv2.putText(frame, count_text, 
                        (label_pos[0], label_pos[1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, zone_color, 2)
    
    # Display tracking info
    cv2.putText(frame, f"Tracked vehicles: {len(tracked_vehicles)}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Display FPS
    if frame_count % 10 == 0:  # Update FPS every 10 frames
        elapsed_time = current_time - start_time
        fps = frame_count / elapsed_time if elapsed_time > 0 else 0
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Display frame with zones and vehicle counts
    cv2.imshow("Traffic Detection", frame)

    key = cv2.waitKey(1)
    if key == ord('q'):
        break
    elif key == ord('s'):
        print("Stopped by user.")
        break

cap.release()
cv2.destroyAllWindows()