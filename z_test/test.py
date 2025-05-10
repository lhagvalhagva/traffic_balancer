import cv2
import numpy as np

# OpenCV трекерийн боломжит эсэхийг шалгах
OPENCV_OBJECT_TRACKERS = {
    "csrt": cv2.legacy.TrackerCSRT_create if hasattr(cv2, 'legacy') else None,
    "kcf": cv2.legacy.TrackerKCF_create if hasattr(cv2, 'legacy') else None,
    "boosting": cv2.legacy.TrackerBoosting_create if hasattr(cv2, 'legacy') else None,
    "mil": cv2.legacy.TrackerMIL_create if hasattr(cv2, 'legacy') else None,
    "tld": cv2.legacy.TrackerTLD_create if hasattr(cv2, 'legacy') else None,
    "medianflow": cv2.legacy.TrackerMedianFlow_create if hasattr(cv2, 'legacy') else None,
    "mosse": cv2.legacy.TrackerMOSSE_create if hasattr(cv2, 'legacy') else None
}

# Ашиглах боломжтой трекерийг олох
TRACKER_FUNC = None
for name, func in OPENCV_OBJECT_TRACKERS.items():
    if func is not None:
        TRACKER_FUNC = func
        print(f"Ашиглах трекер: {name}")
        break

# Хэрэв трекер олдоогүй бол, хялбар аргыг ашиглах
if TRACKER_FUNC is None:
    print("Трекер алга байна. Энгийн аргаар ажиллана.")

cap = cv2.VideoCapture('viiddeo.mov')

fps = cap.set(cv2.CAP_PROP_FPS,1)

min_contour_width=40
min_contour_height=40
offset=10
matches =[]
cars=0
roi_points = []  # 4 цэгийн координат
roi_set = False  # ROI талбайг тодорхойлсон эсэх
tracked_objects = {}  # Тоолсон машинууд
object_trackers = {}  # Трекерүүд

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
                cv2.waitKey(1000)  # 1 секунд хүлээх
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
ret, frame2 = cap.read()

# Объектын ID
next_object_id = 1
# Давхар тоолохоос сэргийлэх
already_counted = set()

# ROI полигоныг нэг удаа урьдчилан хөрвүүлэх
roi_contour = np.array(roi_points, dtype=np.int32)

# Видео боловсруулах үндсэн давталт
while ret:
    # Одоогийн фрэймний хуулбар хийх
    frame_display = frame1.copy()
    
    # Хөдөлгөөн илрүүлэх
    d = cv2.absdiff(frame1, frame2)
    grey = cv2.cvtColor(d, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(grey, (5, 5), 0)
    ret, th = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(th, np.ones((3, 3)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    closing = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)
    contours, h = cv2.findContours(closing, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # ROI цэгүүдийг харуулах
    for i, point in enumerate(roi_points):
        cv2.circle(frame_display, point, 5, (0, 0, 255), -1)
        if i > 0:
            cv2.line(frame_display, roi_points[i-1], point, (0, 0, 255), 2)
    
    # Хамгийн сүүлийн цэгээс эхний рүү шугам татах
    cv2.line(frame_display, roi_points[3], roi_points[0], (0, 0, 255), 2)

    # Шинээр илэрсэн машинуудыг олох
    new_objects = []
    
    for (i, c) in enumerate(contours):
        (x, y, w, h) = cv2.boundingRect(c)
        contour_valid = (w >= min_contour_width) and (h >= min_contour_height)

        if not contour_valid:
            continue
        
        # Төвийг олох
        centroid = get_centroid(x, y, w, h)
        cx, cy = centroid
        
        # Тухайн талбайд машин орсон эсэхийг шалгах
        if cv2.pointPolygonTest(roi_contour, (cx, cy), False) >= 0:
            # Машин тоологдох бүсэд байна
            new_objects.append((x, y, w, h, cx, cy))
    
    # Одоогийн трекерүүдийг шинэчлэх
    objects_to_delete = []
    
    # Хэрэв трекер боломжтой бол ашиглах
    if TRACKER_FUNC is not None:
        for obj_id, tracker in object_trackers.items():
            # Трекерийг шинэчлэх
            success, bbox = tracker.update(frame1)
            
            if success:
                x, y, w, h = map(int, bbox)
                cx, cy = get_centroid(x, y, w, h)
                
                # Машин ROI доторх эсэхийг шалгах
                if cv2.pointPolygonTest(roi_contour, (cx, cy), False) >= 0:
                    # Машиныг дугуйлган хүрээлэх
                    cv2.rectangle(frame_display, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    # Машины дугаарыг харуулах
                    cv2.putText(frame_display, f"#{obj_id}", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    # Төвийг тэмдэглэх
                    cv2.circle(frame_display, (cx, cy), 5, (0, 255, 0), -1)
                    
                    # Шинэчлэх
                    tracked_objects[obj_id] = (cx, cy)
                else:
                    objects_to_delete.append(obj_id)
            else:
                # Трекер амжилтгүй болсон тул устгана
                objects_to_delete.append(obj_id)
    
    # Алдагдсан трекерүүдийг устгах
    for obj_id in objects_to_delete:
        if obj_id in object_trackers:
            del object_trackers[obj_id]
        if obj_id in tracked_objects:
            del tracked_objects[obj_id]
    
    # Шинэ объектуудыг трекерт нэмэх
    for (x, y, w, h, cx, cy) in new_objects:
        # Шинэ машин эсвэл одоо байгаа машин мөн эсэхийг шалгах
        found_match = False
        for obj_id, (old_cx, old_cy) in tracked_objects.items():
            distance = calculate_distance((cx, cy), (old_cx, old_cy))
            if distance < 50:  # Зайн босго
                found_match = True
                break
                
        if not found_match:
            # Шинэ машин илэрлээ
            new_id = next_object_id
            next_object_id += 1
            
            # Хэрэв трекер ашиглаж байгаа бол инициализ хийх
            if TRACKER_FUNC is not None:
                tracker = TRACKER_FUNC()
                tracker.init(frame1, (x, y, w, h))
                object_trackers[new_id] = tracker
                
            # Трекерийг хадгалах
            tracked_objects[new_id] = (cx, cy)
            
            # Машин тоолох
            if new_id not in already_counted:
                cars += 1
                already_counted.add(new_id)
                print(f"Шинэ машин #{new_id}, нийт тоологдсон: {cars}")
                
            # Шинэ илрүүлсэн машиныг дугуйлган хүрээлэх
            cv2.rectangle(frame_display, (x, y), (x+w, y+h), (255, 0, 0), 2)
            # Машины дугаарыг харуулах
            cv2.putText(frame_display, f"#{new_id}", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            # Төвийг тэмдэглэх
            cv2.circle(frame_display, (cx, cy), 5, (0, 255, 0), -1)

    # Машины тоог харуулах
    cv2.putText(frame_display, "Нийт тоологдсон машин: " + str(cars), (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (0, 170, 0), 2)
    cv2.putText(frame_display, f"Хянагдаж буй машин: {len(tracked_objects)}", (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (0, 170, 0), 2)

    cv2.imshow("OUTPUT", frame_display)
    if cv2.waitKey(1) == 27:
        break
        
    frame1 = frame2
    ret, frame2 = cap.read()

cv2.destroyAllWindows()
cap.release()