from ultralytics import YOLO

import cv2
import numpy as np
import torch
import time

# Төхөөрөмж шалгах
device = 'cpu'

cap = cv2.VideoCapture('viiddeo.mov')

fps = cap.set(cv2.CAP_PROP_FPS,1)

min_contour_width=40
min_contour_height=40
offset=10
matches =[]
cars=0
roi_points = []  
roi_set = False  
tracked_objects = {}  

# YOLOv8 загвар ачаалах - лог мэдээллийг хаах
print(f"Модель {device} төхөөрөмж дээр ачаалж байна...")
model = YOLO('yolov8s.pt', verbose=False).to(device)

def get_centroid(x, y, w, h):
    x1 = int(w / 2)
    y1 = int(h / 2)

    cx = x + x1
    cy = y + y1
    return cx,cy


cap.set(3,1920)
cap.set(4,1080)

# Нэг фрэйм унших
ret, setup_frame = cap.read()
if not ret:
    print("Видео уншиж чадсангүй")
    exit()

# Хулганы эвентийг дуудах функц
def draw_roi(event, x, y, flags, param):
    global roi_points, roi_set, setup_frame
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(roi_points) < 4:
            roi_points.append((x, y))
            print(f"Цэг {len(roi_points)}: ({x}, {y})")
            
            # Цэгүүдийг харуулах
            temp_frame = setup_frame.copy()
            for i, point in enumerate(roi_points):
                cv2.circle(temp_frame, point, 5, (0, 0, 255), -1)
                if i > 0:
                    cv2.line(temp_frame, roi_points[i-1], point, (0, 0, 255), 2)
            
            # Зааварчилгаа харуулах
            remaining = 4 - len(roi_points)
            cv2.putText(temp_frame, f"Үлдсэн цэгийн тоо: {remaining}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow("Тохиргоо", temp_frame)
            
            if len(roi_points) == 4:
                # Хамгийн сүүлийн цэгээс эхний рүү шугам татах
                cv2.line(temp_frame, roi_points[3], roi_points[0], (0, 0, 255), 2)
                cv2.imshow("Тохиргоо", temp_frame)
                roi_set = True
                print("4 цэг бүгд тодорхойлогдлоо! Бичлэг эхэлж байна...")
                cv2.waitKey(1)  # 1 секунд хүлээх
                cv2.destroyWindow("Тохиргоо")

# Машин тодорхойлсон бүсэд орсон эсэхийг шалгах функц (cv2.pointPolygonTest ашиглан)
def is_point_in_roi(point, vertices):
    # vertices-г numpy array болгож хөрвүүлэх
    contour = np.array(vertices, dtype=np.int32)
    
    # pointPolygonTest нь дараах утгуудыг буцаана:
    # > 0: цэг полигон дотор
    # = 0: цэг полигоны хилийн дээр
    # < 0: цэг полигоноос гадна
    result = cv2.pointPolygonTest(contour, point, False)
    
    # 0 эсвэл эерэг утга буцвал True, бусад тохиолдолд False
    return result >= 0

# Зайг тооцох функц
def calculate_distance(p1, p2):
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# 4 цэгийг зурах цонх үүсгэх
cv2.namedWindow("Тохиргоо")
cv2.setMouseCallback("Тохиргоо", draw_roi)

# Зааварчилгаа харуулах
print("4 цэгийг тодорхойлохын тулд дэлгэц дээр 4 газар дарна уу.")
temp_frame = setup_frame.copy()
cv2.putText(temp_frame, "4 цэгийг тодорхойлохын тулд дэлгэц дээр дарна уу (Үлдсэн: 4)", (10, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
cv2.imshow("Тохиргоо", temp_frame)

# Хэрэглэгч 4 цэгийг зуртал хүлээх
while not roi_set:
    if cv2.waitKey(1) == 27:  # ESC товч дарвал гарах
        exit()

# Видеог эхнээс нь дахин эхлүүлэх
cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
if cap.isOpened():
    ret, frame1 = cap.read()
else:
    ret = False
ret, frame1 = cap.read()

# Объектын ID
next_object_id = 1
# Давхар тоолохоос сэргийлэх
already_counted = set()

# ROI полигоныг нэг удаа урьдчилан хөрвүүлэх
roi_contour = np.array(roi_points, dtype=np.int32)

# Машин илрүүлэх классууд (YOLO индексүүд)
vehicle_classes = [2, 3, 5, 7]  # 2: car, 3: motorcycle, 5: bus, 7: truck

# Машин төрлүүдийн өнгө
vehicle_colors = {
    'car': (0, 255, 0),        # ногоон
    'motorcycle': (255, 0, 0),  # цэнхэр
    'bus': (0, 165, 255),      # улбар шар
    'truck': (128, 0, 128)     # ягаан
}

# Хугацааг хэмжих хувьсагчид
frame_count = 0
last_fps_update = cv2.getTickCount()
fps_display = 0
skip_frames = 0
process_times = []  # Боловсруулалтын хугацааг хэмжих

# Оновчлолын тохируулга
input_size = 320  # Оролтын зургийн хэмжээ (бага - хурдан / их - нарийвчлалтай)
confidence_threshold = 0.3  # Итгэмжлэлийн босго

# Видео боловсруулах үндсэн давталт
while ret:
    # Боловсруулалтын эхлэл цагийг тэмдэглэх
    start_time = time.time()
    
    # Фрэйм алгасах (хурд сайжруулахын тулд)
    if skip_frames > 0:
        skip_frames -= 1
        ret, frame1 = cap.read()
        continue
    
    # FPS тооцоолох
    frame_count += 1
    if frame_count % 10 == 0:  # Арван фрэйм тутамд FPS шинэчлэх
        current_tick = cv2.getTickCount()
        time_diff = (current_tick - last_fps_update) / cv2.getTickFrequency()
        fps_display = 10 / time_diff if time_diff > 0 else 0
        last_fps_update = current_tick
    
    # YOLOv8 модель ашиглан объектуудыг илрүүлэх
    results = model(frame1, conf=confidence_threshold, verbose=False, imgsz=input_size)
    
    # ROI цэгүүдийг харуулах
    for i, point in enumerate(roi_points):
        cv2.circle(frame1, point, 5, (0, 0, 255), -1)
        if i > 0:
            cv2.line(frame1, roi_points[i-1], point, (0, 0, 255), 2)
    
    # Хамгийн сүүлийн цэгээс эхний рүү шугам татах
    cv2.line(frame1, roi_points[3], roi_points[0], (0, 0, 255), 2)

    # Мөрдөгдөж байгаа объектуудыг хадгалах түр хувьсагч
    current_objects = {}
    
    # Илрүүлсэн объектуудыг боловсруулах
    detections = results[0].boxes
    
    for detection in detections:
        # Объектын класс, итгэмжлэлийн хувь, координатууд
        class_id = int(detection.cls.item())
        confidence = detection.conf.item()
        
        # Зөвхөн машины төрлийн объектуудыг авч үзэх
        if class_id in vehicle_classes:
            # Координатуудыг авах
            x1, y1, x2, y2 = [int(value) for value in detection.xyxy[0].tolist()]
            
            # Объектын төв цэгийг олох
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            centroid = (cx, cy)
            
            # Объектын нэрийг авах
            class_name = model.names[class_id]
            
            # Өнгийг сонгох
            color = vehicle_colors.get(class_name, (0, 255, 0))
            
            # Тодорхойлсон бүсэд машин орсон эсэхийг шалгах
            if cv2.pointPolygonTest(roi_contour, centroid, False) >= 0:
                # Машин тодорхойлогдсон бүсэд байна
                
                # Олж авсан машиныг мөрдөгдөж байгаа объектуудтай харьцуулах
                found_match = False
                matching_id = None
                
                # Одоо мөрдөгдөж байгаа объектуудыг шалгах
                for obj_id, obj_data in tracked_objects.items():
                    obj_centroid = obj_data['centroid']
                    # Хэрвээ уг объект өмнө тодорхойлогдсон объекттэй ойролцоо бол ижил гэж үзнэ
                    distance = calculate_distance(centroid, obj_centroid)
                    if distance < 50:  # Зай хязгаар (тохируулж болно)
                        found_match = True
                        matching_id = obj_id
                        current_objects[obj_id] = {
                            'centroid': centroid,
                            'class': class_name,
                            'confidence': confidence
                        }
                        break
                
                # Хэрэв шинэ объект бол тодорхойлж, тоонд нэмэх
                if not found_match:
                    # Шинэ машин тодорхойлогдлоо
                    obj_id = next_object_id
                    next_object_id += 1
                    current_objects[obj_id] = {
                        'centroid': centroid,
                        'class': class_name,
                        'confidence': confidence
                    }
                    
                    # Машин тоолох, хэрэв өмнө тоологдоогүй бол
                    if obj_id not in already_counted:
                        cars += 1
                        already_counted.add(obj_id)
                        print(f"Шинэ {class_name}, нийт тоологдсон: {cars}")
            
            # Машины хүрээг зурах
            cv2.rectangle(frame1, (x1, y1), (x2, y2), color, 2)
            
            # Машины төрлийг харуулах
            cv2.putText(frame1, class_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Машины төвийг тэмдэглэх
            cv2.circle(frame1, centroid, 5, color, -1)

    # Tracked objects шинэчлэх
    tracked_objects = current_objects.copy()
    
    # Боловсруулалтын хугацааг тооцоолох
    end_time = time.time()
    process_time = end_time - start_time
    process_times.append(process_time)
    
    # Хамгийн сүүлийн 30 фрэймийн дундаж боловсруулалтын хугацааг тооцоолох
    avg_process_time = sum(process_times[-30:]) / min(len(process_times), 30)

    # Дэлгэцэнд мэдээлэл харуулах
    cv2.putText(frame1, "Нийт тоологдсон машин: " + str(cars), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                (0, 170, 0), 2)
    cv2.putText(frame1, f"FPS: {fps_display:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                (0, 170, 0), 2)
    cv2.putText(frame1, f"Боловсруулалтын хугацаа: {avg_process_time*1000:.1f}ms", (10, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 170, 0), 2)
    cv2.putText(frame1, f"Төхөөрөмж: {device}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                (0, 170, 0), 2)

    cv2.imshow("OUTPUT", frame1)
    key = cv2.waitKey(1)
    if key == 27:  # ESC товч дарвал гарах
        break
    elif key == ord('f'):  # 'f' товч дарвал хурдасгах
        skip_frames = 2  # 2 фрэйм алгасах
    elif key == ord('+'):  # '+' товч дарвал нарийвчлалыг нэмэгдүүлэх
        input_size = min(640, input_size + 64)
        print(f"Оролтын зургийн хэмжээг нэмэгдүүлэв: {input_size}")
    elif key == ord('-'):  # '-' товч дарвал нарийвчлалыг багасгах
        input_size = max(192, input_size - 64)
        print(f"Оролтын зургийн хэмжээг багасгав: {input_size}")
    
    # Дараагийн фрэймрүү шилжих
    ret, frame1 = cap.read()

print(f"Нийт тоологдсон машин: {cars}")
print(f"Дундаж FPS: {fps_display:.1f}")
cv2.destroyAllWindows()
cap.release()