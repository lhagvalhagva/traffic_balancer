import cv2
from ultralytics import YOLO

# Load model
model = YOLO("yolov8s.pt").to()

# Globals
drawing = False
ix, iy = -1, -1
zones = []  # List of dicts: {id, x1, y1, x2, y2, name, type}
current_zone_id = 1
zone_mode = True
vehicle_ids_in_frame = set()  # Set to track vehicles in the current frame

def draw_zone(event, x, y, flags, param):
    global ix, iy, drawing, zones, current_zone_id

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        zone_type = input("Enter zone type (1 for sum, 2 for counting): ")
        zones.append({
            "id": current_zone_id,
            "x1": min(ix, x),
            "y1": min(iy, y),
            "x2": max(ix, x),
            "y2": max(iy, y),
            "name": f"Zone {current_zone_id}",
            "type": int(zone_type)  # Store type of the zone
        })
        print(f"Zone {current_zone_id} added with type {zone_type}")
        current_zone_id += 1

def is_inside_zone(x, y, zone):
    return zone["x1"] <= x <= zone["x2"] and zone["y1"] <= y <= zone["y2"]

# Load video
# cap = cv2.VideoCapture("video.mp4")
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

# Show the first frame, allowing zone setup
thumbnail = frame.copy()  # Capture thumbnail (first frame)
cv2.imshow("Setup Zones", thumbnail)

zone_mode = True
while zone_mode:
    # Show zones drawn so far
    for zone in zones:
        cv2.rectangle(thumbnail, (zone["x1"], zone["y1"]), (zone["x2"], zone["y2"]), (255, 0, 0), 2)
        cv2.putText(thumbnail, zone["name"], (zone["x1"], zone["y1"] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # Show the frame with the zones and allow user interaction
    cv2.imshow("Setup Zones", thumbnail)

    # Wait for user interaction
    key = cv2.waitKey(1)
    if key == 13:  # Enter key to finish zone setup
        print("Finished zone setup.")
        zone_mode = False
    elif key == ord('q'):  # Cancel zone setup
        print("Cancelled.")
        cap.release()
        cv2.destroyAllWindows()
        exit()

cv2.destroyWindow("Setup Zones")
cap.release()  # Release the video capture after zone setup is complete

# ---- Step 2: Start Detection ----
# cap = cv2.VideoCapture("video.mp4")  # Restart video capture
cap = cv2.VideoCapture("viiddeo.mov")  # Restart video capture
vehicle_counts = {zone['id']: 0 for zone in zones}  # Initialize vehicle counts for each zone

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame)[0]

    # Track vehicles that have already been counted in this frame
    vehicle_ids_in_frame.clear()

    # Count vehicles per zone
    zone_counts = {zone['id']: 0 for zone in zones}

    for r in results.boxes.data.tolist():
        x1, y1, x2, y2, score, cls_id = r
        label = model.names[int(cls_id)]

        if label in ['car', 'bus', 'truck', 'motorbike']:
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            # Draw bounding box for the vehicle
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, label, (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Generate unique ID for the vehicle
            vehicle_id = f"{int(x1)}_{int(y1)}_{int(x2)}_{int(y2)}"  # Combine coordinates to form a unique ID

            if vehicle_id not in vehicle_ids_in_frame:
                # Vehicle has not been counted in this frame
                vehicle_ids_in_frame.add(vehicle_id)

                for zone in zones:
                    if is_inside_zone(cx, cy, zone):
                        if zone["type"] == 1:
                            # Type 1: Sum all vehicles
                            vehicle_counts[zone['id']] += 1
                        elif zone["type"] == 2:
                            # Type 2: Count only if a vehicle is inside, reset if not
                            zone_counts[zone['id']] += 1
                        break

    # Display zones and counts on the frame
    for zone in zones:
        cv2.rectangle(frame, (zone["x1"], zone["y1"]), (zone["x2"], zone["y2"]), (255, 0, 0), 2)
        count_text = f"{zone['name']}: {vehicle_counts[zone['id']]}" if zone["type"] == 1 else f"{zone['name']}: {zone_counts[zone['id']] or 0}"
        cv2.putText(frame, count_text, (zone["x1"], zone["y1"] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # Display frame with zones and vehicle counts
    cv2.imshow("Traffic Detection", frame)

    key = cv2.waitKey(1)
    if key == ord('q'):  # Press 'q' to quit
        break
    elif key == ord('s'):  # Stop detection early
        print("Stopped by user.")
        break

cap.release()
cv2.destroyAllWindows()