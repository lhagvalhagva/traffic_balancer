import cv2
import numpy as np
from zone_manager import Zone


class ZoneSetupUI:
    """
    Бүс тохируулах дэлгэцийн UI
    """
    
    def __init__(self, zone_manager, window_name="Setup Zones"):
        """
        Бүс тохируулах UI үүсгэх
        
        Args:
            zone_manager: Бүсийг зохицуулах менежер
            window_name (str): Цонхны нэр
        """
        self.zone_manager = zone_manager
        self.window_name = window_name
        self.thumbnail = None
        self.original_thumbnail = None
        self.selecting_type = False
        self.current_type = None
    
    def setup_mouse_callback(self):
        """
        Хулганы дарах үйлдлийг тохируулах
        """
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)
    
    def _mouse_callback(self, event, x, y, flags, param):
        """
        Хулганы дарах үйлдлийг боловсруулах
        
        Args:
            event: Үйлдлийн төрөл
            x, y: Координат
            flags: Нэмэлт флагууд
            param: Нэмэлт параметрүүд
        """
        if self.selecting_type:
            # Төрөл сонгох дэлгэц
            if event == cv2.EVENT_LBUTTONDOWN:
                if 50 <= x <= 150 and 50 <= y <= 100:  # COUNT төрөл
                    self.current_type = Zone.ZONE_TYPE_COUNT
                    self.selecting_type = False
                    self._complete_zone_creation()
                elif 200 <= x <= 300 and 50 <= y <= 100:  # SUM төрөл
                    self.current_type = Zone.ZONE_TYPE_SUM
                    self.selecting_type = False
                    self._complete_zone_creation()
        else:
            # Бүс үүсгэх дэлгэц
            if event == cv2.EVENT_LBUTTONDOWN:
                # Шинэ цэг нэмэх
                self.zone_manager.add_point_to_current_polygon(x, y)
                # Шинэ цэгийг зурах
                if self.thumbnail is not None:
                    cv2.circle(self.thumbnail, (x, y), 3, (0, 0, 255), -1)
            
            elif event == cv2.EVENT_RBUTTONDOWN:
                # Бүс үүсгэлтийг дуусгах
                if self.zone_manager.is_current_polygon_valid():
                    self.selecting_type = True
                    self._show_type_selection()
    
    def _show_type_selection(self):
        """
        Бүсийн төрөл сонгох дэлгэц харуулах
        """
        if self.thumbnail is None:
            return
            
        # Одоогийн дэлгэцийн хуулбар үүсгэх
        selection_img = self.thumbnail.copy()
        
        # Төрөл сонгох товчнууд зурах
        cv2.rectangle(selection_img, (50, 50), (150, 100), (0, 255, 0), -1)
        cv2.putText(selection_img, "COUNT", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        cv2.rectangle(selection_img, (200, 50), (300, 100), (0, 120, 255), -1)
        cv2.putText(selection_img, "SUM", (210, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        # Тайлбар
        cv2.putText(selection_img, "COUNT: Нэвтэрсэн тээврийн хэрэгслийг тоолох", 
                   (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(selection_img, "SUM: Бүсэд байгаа тээврийн хэрэгслийг тоолох", 
                   (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow(self.window_name, selection_img)
    
    def _complete_zone_creation(self):
        """
        Бүс үүсгэлтийг дуусгах
        """
        # Шинэ бүс үүсгэх
        zone = self.zone_manager.create_zone(
            self.zone_manager.current_polygon,
            self.current_type
        )
        
        print(f"Zone {zone.id} added with type {zone.type}")
        
        # Шинэ бүсийг бэлдэх
        self.zone_manager.reset_current_polygon()
        self.current_type = None
        
        # Хулганы callback шинэчлэх
        cv2.setMouseCallback(self.window_name, self._mouse_callback)
    
    def setup_from_frame(self, frame):
        """
        Видео фреймээс бүс тохируулах дэлгэц үүсгэх
        
        Args:
            frame (numpy.ndarray): Видео фрейм
            
        Returns:
            bool: Тохиргоо хийгдсэн эсэх
        """
        self.thumbnail = frame.copy()
        self.original_thumbnail = frame.copy()
        
        self.setup_mouse_callback()
        cv2.imshow(self.window_name, self.thumbnail)
        
        print("Зоны үүсгэх заавар:")
        print("- Зоны цэгүүдийг сонгохын тулд зүүн товчийг дарна")
        print("- Зоныг дуусгахын тулд баруун товчийг дарна")
        print("- Зоны төрлийг сонгохын тулд COUNT (тоолох) эсвэл SUM (нэмэгдүүлэх) товчийг дарна")
        print("- Зоны тохиргоог дуусгахын тулд Enter товчийг дарна")
        print("- Зоны цэгүүдийг цэвэрлэхийн тулд 'c' товчийг дарна")
        
        zone_mode = True
        while zone_mode:
            # Дэлгэц шинэчлэх
            display_img = self.original_thumbnail.copy()
            
            # Одоогийн полигон зурах
            display_img = self.zone_manager.draw_current_polygon(display_img)
            
            # Бүсүүдийг зурах
            display_img = self.zone_manager.draw_zones(display_img)
            
            # Дэлгэц шинэчлэх
            self.thumbnail = display_img
            if not self.selecting_type:  # Төрөл сонгож байх үед дэлгэц бүү шинэчил
                cv2.imshow(self.window_name, self.thumbnail)
            
            # Хэрэглэгчийн оролт хүлээх
            key = cv2.waitKey(1)
            if key == 13:  # Enter товч
                if self.zone_manager.is_current_polygon_valid():
                    print("Дуусгаагүй зон байна. Эхлээд зоныг дуусгана уу.")
                else:
                    print("Зоны тохиргоо дууслаа.")
                    zone_mode = False
            elif key == ord('q'):  # Тохиргоо цуцлах
                print("Цуцаллаа.")
                cv2.destroyWindow(self.window_name)
                return False
            elif key == ord('c'):  # Одоогийн полигон цэвэрлэх
                self.zone_manager.reset_current_polygon()
                self.thumbnail = self.original_thumbnail.copy()
        
        cv2.destroyWindow(self.window_name)
        return True 