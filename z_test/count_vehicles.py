import cv2
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

model = YOLO("yolov8n.pt")
tracker = DeepSort(max_age=30)
vehicle_classes = [2, 3, 5, 7]

video_path = "video.mp4"
cap = cv2.VideoCapture(video_path)

counted_ids = set()
vehicle_count = 0

roi_polygon = []
drawing = False

def draw_roi(event, x, y, flags, param):
    global roi_polygon, drawing
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_polygon.append((x, y))
    elif event == cv2.EVENT_RBUTTONDOWN and len(roi_polygon) > 2:
        drawing = False

# ROI-ийг гараар заана
cv2.namedWindow("Draw ROI (Right click to finish)")
cv2.setMouseCallback("Draw ROI (Right click to finish)", draw_roi)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Cannot read video")
        exit()
    temp_frame = frame.copy()
    if len(roi_polygon) > 1:
        cv2.polylines(temp_frame, [np.array(roi_polygon)], False, (255, 0, 0), 2)
    cv2.imshow("Draw ROI (Right click to finish)", temp_frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break
    if len(roi_polygon) > 2 and not drawing:
        roi_polygon = np.array(roi_polygon)
        break

cv2.destroyWindow("Draw ROI (Right click to finish)")

def is_inside_roi(center, roi):
    return cv2.pointPolygonTest(roi, center, False) >= 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, verbose=False)
    detections = results[0].boxes
    dets_for_tracker = []

    for box in detections:
        cls = int(box.cls[0])
        if cls in vehicle_classes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            dets_for_tracker.append(([x1, y1, x2 - x1, y2 - y1], conf, 'vehicle'))

    tracks = tracker.update_tracks(dets_for_tracker, frame=frame)

    for track in tracks:
        if not track.is_confirmed():
            continue
        track_id = track.track_id
        ltrb = track.to_ltrb()
        x1, y1, x2, y2 = map(int, ltrb)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if track_id not in counted_ids and is_inside_roi((cx, cy), roi_polygon):
            counted_ids.add(track_id)
            vehicle_count += 1

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
        cv2.putText(frame, f'ID: {track_id}', (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # ROI зурна
    cv2.polylines(frame, [roi_polygon], isClosed=True, color=(255, 0, 0), thickness=2)
    cv2.putText(frame, f'Count: {vehicle_count}', (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

    cv2.imshow("Lane Vehicle Counter", frame)
    if cv2.waitKey(30) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()