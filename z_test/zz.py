# importing libraries
import cv2
import numpy as np
import time

# capturing or reading video
#cap = cv2.VideoCapture(0)
cap = cv2.VideoCapture('video.mp4')

fps = cap.set(cv2.CAP_PROP_FPS,1)

min_contour_width=40
min_contour_height=40
offset=10

line_start_x = 0
line_start_y = 550
line_end_x = 1200
line_end_y = 550

line_defined = False  # Зураас тодорхойлогдсон эсэх
line_points = []  # Зураасын 2 цэгийг хадгалах

# Машины хөдөлгөөн дагах хувьсагчид
vehicles = []  # Машины мэдээлэл хадгалах жагсаалт
next_vehicle_id = 0  # Машины ID
max_disappeared = 20  # Алга болох хамгийн их фрэймийн тоо
counted_vehicles = set()  # Тоологдсон машины ID-г хадгалах олонлог
cars = 0  # Нийт тоологдсон машины тоо

# Vehicle class to track individual vehicles
class Vehicle:
    def __init__(self, vehicle_id, centroid):
        self.id = vehicle_id
        self.centroids = [centroid]  # Машины төвүүдийн түүх
        self.disappeared = 0  # Алга болсон фрэймийн тоо
        self.counted = False  # Тоологдсон эсэх

    def update_centroid(self, new_centroid):
        self.centroids.append(new_centroid)
        self.disappeared = 0

    def increment_disappeared(self):
        self.disappeared += 1

# Машины төвүүдийн хоорондын зай тооцоолох функц
def calculate_distance(centroid1, centroid2):
    return np.sqrt(((centroid1[0] - centroid2[0]) ** 2) + ((centroid1[1] - centroid2[1]) ** 2))

# Машин зураас дээр очсон эсэхийг шалгах функц
def is_vehicle_crossing_line(vehicle, line_start, line_end, offset):
    # Сүүлийн 2 байрлалыг авах
    if len(vehicle.centroids) < 2:
        return False

    # Машины сүүлийн 2 байрлал
    old_centroid = vehicle.centroids[-2]
    current_centroid = vehicle.centroids[-1]
    
    # Шулууны тэгшитгэл
    if line_start[0] != line_end[0]:  # Хэвтээ биш зураас
        m = (line_end[1] - line_start[1]) / (line_end[0] - line_start[0])
        c = line_start[1] - m * line_start[0]
        
        # Эхний болон одоогийн цэгээс шулуун хүртэлх зай
        old_distance = abs(old_centroid[1] - (m * old_centroid[0] + c)) / np.sqrt(1 + m**2)
        current_distance = abs(current_centroid[1] - (m * current_centroid[0] + c)) / np.sqrt(1 + m**2)
        
        # Шулуун дээр цэгийн проекцүүд
        old_x_proj = (old_centroid[0] + m * old_centroid[1] - m * c) / (1 + m**2)
        old_y_proj = m * old_x_proj + c
        current_x_proj = (current_centroid[0] + m * current_centroid[1] - m * c) / (1 + m**2)
        current_y_proj = m * current_x_proj + c
        
        # Проекцүүд шулууны сегментэд орших эсэх
        min_x, max_x = min(line_start[0], line_end[0]), max(line_start[0], line_end[0])
        min_y, max_y = min(line_start[1], line_end[1]), max(line_start[1], line_end[1])
        
        old_proj_on_segment = min_x <= old_x_proj <= max_x and min_y <= old_y_proj <= max_y
        current_proj_on_segment = min_x <= current_x_proj <= max_x and min_y <= current_y_proj <= max_y
        
        # Зураас огтолсон эсэх
        if (old_distance <= offset and current_distance <= offset and
            old_proj_on_segment and current_proj_on_segment):
            # Зураасын янз бүрийн талд байгаа эсэхийг шалгах
            p1 = np.array([line_start[0], line_start[1]])
            p2 = np.array([line_end[0], line_end[1]])
            
            # Шулууны нормал вектор
            normal = np.array([-(p2[1] - p1[1]), p2[0] - p1[0]])
            
            # Цэгүүдээс шулуун руу чиглэсэн векторууд
            vec_old = np.array([old_centroid[0], old_centroid[1]]) - p1
            vec_current = np.array([current_centroid[0], current_centroid[1]]) - p1
            
            # Векторуудын дотоод үржвэр
            old_sign = np.dot(vec_old, normal)
            current_sign = np.dot(vec_current, normal)
            
            # Тэмдэг өөрчлөгдсөн эсэх
            return (old_sign * current_sign) <= 0
    else:  # Босоо шулуун
        # Босоо шулууны хувьд x координатаар шалгах
        old_on_line = abs(old_centroid[0] - line_start[0]) <= offset
        current_on_line = abs(current_centroid[0] - line_start[0]) <= offset
        min_y, max_y = min(line_start[1], line_end[1]), max(line_start[1], line_end[1])
        
        if old_on_line and current_on_line and min_y <= old_centroid[1] <= max_y and min_y <= current_centroid[1] <= max_y:
            # Шулууны зүүн ба баруун талд байх
            return (old_centroid[0] - line_start[0]) * (current_centroid[0] - line_start[0]) <= 0
    
    return False

# defining a function
def get_centroid(x, y, w, h):
    x1 = int(w / 2)
    y1 = int(h / 2)

    cx = x + x1
    cy = y + y1
    return cx,cy

# Mouse callback function
def define_line(event, x, y, flags, param):
    global line_points, line_defined, line_start_x, line_start_y, line_end_x, line_end_y
    
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(line_points) < 2:
            line_points.append((x, y))
            
        if len(line_points) == 2:
            line_start_x, line_start_y = line_points[0]
            line_end_x, line_end_y = line_points[1]
            line_defined = True

cap.set(3,1920)
cap.set(4,1080)

if cap.isOpened():
    ret,frame1 = cap.read()
else:
    ret = False
ret,frame1 = cap.read()
ret,frame2 = cap.read()

# Цонхыг үүсгэж callback функцийг оноох
cv2.namedWindow("OUTPUT")
cv2.setMouseCallback("OUTPUT", define_line)

# Хэрэглэгчид зааварчилгаа үзүүлэх
print("Зураас зурахын тулд дэлгэц дээр 2 цэг сонгоно уу")

while ret:
    frame_display = frame1.copy()
    
    # Зураасыг зурах
    if len(line_points) >= 1:
        cv2.circle(frame_display, line_points[0], 5, (0, 0, 255), -1)
    
    if line_defined:
        cv2.line(frame_display, (line_start_x, line_start_y), (line_end_x, line_end_y), (0, 255, 0), 2)
    elif len(line_points) == 1:
        cv2.line(frame_display, line_points[0], (line_points[0][0] + 1, line_points[0][1] + 1), (0, 255, 0), 2)
    
    # Зааварчилгаа үзүүлэх
    if not line_defined:
        text = "Зураас зурахын тулд {} цэг сонгоно уу".format(2 - len(line_points))
        cv2.putText(frame_display, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    d = cv2.absdiff(frame1,frame2)
    grey = cv2.cvtColor(d,cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(grey,(5,5),0)

    ret, th = cv2.threshold(blur,20,255,cv2.THRESH_BINARY)
    dilated = cv2.dilate(th,np.ones((3,3)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))

    # Fill any small holes
    closing = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)
    contours,h = cv2.findContours(closing,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    
    # Одоогийн олдсон машинуудын төвүүд
    current_centroids = []
    
    for(i,c) in enumerate(contours):
        (x,y,w,h) = cv2.boundingRect(c)
        contour_valid = (w >= min_contour_width) and (h >= min_contour_height)

        if not contour_valid:
            continue
        
        # Get centroid of contour
        centroid = get_centroid(x, y, w, h)
        current_centroids.append(centroid)
        
        # Draw rectangle around vehicle
        cv2.rectangle(frame_display, (x-10, y-10), (x+w+10, y+h+10), (255, 0, 0), 2)
    
    # Хэрэв машин байхгүй бол
    if len(current_centroids) == 0:
        # Бүх машиныг алга болсон гэж тэмдэглэх
        for vehicle in vehicles:
            vehicle.increment_disappeared()
        
        # Алга болсон хугацаа хэтэрсэн машиныг устгах
        vehicles = [v for v in vehicles if v.disappeared <= max_disappeared]
    else:
        # Хэрэв машин одоогоор эхлээгүй бол
        if len(vehicles) == 0:
            # Бүх илрүүлсэн машинд ID оноох
            for centroid in current_centroids:
                vehicles.append(Vehicle(next_vehicle_id, centroid))
                next_vehicle_id += 1
        else:
            # Замагчлалын матриц үүсгэх (Олдсон төв бүрийг одоогийн машин бүрт замагчлах)
            distances = {}
            for i, vehicle in enumerate(vehicles):
                for j, centroid in enumerate(current_centroids):
                    if j not in distances:
                        distances[j] = {}
                    # Машины сүүлийн байрлалаас одоогийн төв хүртэлх зай
                    distances[j][i] = calculate_distance(vehicle.centroids[-1], centroid)
            
            # Бүртгэгдсэн машин руу замагчлагдсан төвүүд
            used_centroids = set()
            used_vehicles = set()
            
            # Машинуудыг хамгийн ойрын төвтэй замагчлах
            while True:
                # Хамгийн бага зайтай (машин, төв) хослолыг олох
                min_distance = float("inf")
                min_centroid_idx = None
                min_vehicle_idx = None
                
                for centroid_idx in distances:
                    if centroid_idx in used_centroids:
                        continue
                        
                    for vehicle_idx in distances[centroid_idx]:
                        if vehicle_idx in used_vehicles:
                            continue
                            
                        if distances[centroid_idx][vehicle_idx] < min_distance:
                            min_distance = distances[centroid_idx][vehicle_idx]
                            min_centroid_idx = centroid_idx
                            min_vehicle_idx = vehicle_idx
                
                # Хэрэв илүү замагчлал олдохгүй юмуу зай хэт их бол гарах
                if min_centroid_idx is None or min_distance > 50:  # Хамгийн их зай
                    break
                    
                # Машин ба төвийг замагчлах
                vehicles[min_vehicle_idx].update_centroid(current_centroids[min_centroid_idx])
                used_centroids.add(min_centroid_idx)
                used_vehicles.add(min_vehicle_idx)
            
            # Замагчлагдаагүй машинуудыг алга болсон гэж тэмдэглэх
            for i, vehicle in enumerate(vehicles):
                if i not in used_vehicles:
                    vehicle.increment_disappeared()
            
            # Замагчлагдаагүй төвүүдийг шинэ машин гэж үзэх
            for i, centroid in enumerate(current_centroids):
                if i not in used_centroids:
                    vehicles.append(Vehicle(next_vehicle_id, centroid))
                    next_vehicle_id += 1
            
            # Алга болсон хугацаа хэтэрсэн машиныг устгах
            vehicles = [v for v in vehicles if v.disappeared <= max_disappeared]
    
    # Машинуудыг зурах ба тоолох
    if line_defined:
        for vehicle in vehicles:
            # Машин дээрх ID-г харуулах
            centroid = vehicle.centroids[-1]
            cv2.circle(frame_display, centroid, 5, (0, 255, 0), -1)
            cv2.putText(frame_display, f"ID {vehicle.id}", (centroid[0] - 10, centroid[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Машин зураас дээр очсон эсэхийг шалгах (тоолоогүй бол)
            if not vehicle.counted and is_vehicle_crossing_line(vehicle, 
                                                           (line_start_x, line_start_y), 
                                                           (line_end_x, line_end_y), 
                                                           offset):
                vehicle.counted = True
                cars += 1
                print(f"Vehicle ID {vehicle.id} counted. Total: {cars}")
    
    # Тоологдсон машиныг харуулах
    cv2.putText(frame_display, "Total Vehicles Detected: " + str(cars), (10, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 170, 0), 2)

    # Дэлгэцэд харуулах
    cv2.imshow("OUTPUT", frame_display)
    if cv2.waitKey(1) == 27:
        break
    frame1 = frame2
    ret, frame2 = cap.read()

cv2.destroyAllWindows()
cap.release()