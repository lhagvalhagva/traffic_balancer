import cv2
import numpy as np

class VehicleCounter:
    def __init__(self, roi_polygon=None):
        """
        Тээврийн хэрэгсэл тоолох класс
        
        Args:
            roi_polygon: Тоолох бүсийн полигон (хэрэв байгаа бол)
        """
        self.roi_polygon = roi_polygon
        self.counted_ids = set()
        self.vehicle_count = 0
        
    def setup_roi(self, frame):
        """
        ROI (Region of Interest) буюу тоолох бүсийг тохируулах
        
        Args:
            frame: Анхны дүрсийн frame
            
        Returns:
            roi_polygon: Тохируулсан ROI полигон
        """
        roi_polygon = []
        drawing = False
        
        def draw_roi(event, x, y, flags, param):
            nonlocal roi_polygon, drawing
            if event == cv2.EVENT_LBUTTONDOWN:
                roi_polygon.append((x, y))
            elif event == cv2.EVENT_RBUTTONDOWN and len(roi_polygon) > 2:
                drawing = False

        cv2.namedWindow("Draw ROI (Right click to finish)")
        cv2.setMouseCallback("Draw ROI (Right click to finish)", draw_roi)

        while True:
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
        self.roi_polygon = roi_polygon
        return roi_polygon
    
    def is_inside_roi(self, center):
        """
        Өгөгдсөн цэг ROI доторх эсэхийг шалгах
        
        Args:
            center: Шалгах цэгийн координат (x, y)
            
        Returns:
            bool: ROI доторх эсэх
        """
        if self.roi_polygon is None:
            return True
        return cv2.pointPolygonTest(self.roi_polygon, center, False) >= 0
    
    def count_vehicles(self, tracks):
        """
        Илэрсэн тээврийн хэрэгслийн мөрийг ашиглан тоолох
        
        Args:
            tracks: DeepSort-с гарсан тээврийн хэрэгслийн мөр
            
        Returns:
            count: Одоогийн нийт тоо
            new_vehicles: Шинээр илэрсэн тээврийн хэрэгслийн ID-ууд
        """
        new_vehicles = []
        
        for track in tracks:
            if not track.is_confirmed():
                continue
                
            track_id = track.track_id
            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = map(int, ltrb)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            
            if track_id not in self.counted_ids and self.is_inside_roi((cx, cy)):
                self.counted_ids.add(track_id)
                self.vehicle_count += 1
                new_vehicles.append(track_id)
                
        return self.vehicle_count, new_vehicles
    
    def draw_visualization(self, frame, tracks):
        """
        Тэмдэглэгээтэй frame үүсгэх
        
        Args:
            frame: Анхны frame
            tracks: Тээврийн хэрэгслийн мөрүүд
            
        Returns:
            frame: Тэмдэглэгээтэй frame
        """
        # Тээврийн хэрэгслүүдийг зурах
        for track in tracks:
            if not track.is_confirmed():
                continue
                
            track_id = track.track_id
            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = map(int, ltrb)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            
            # Тоолсон бол ногоон, эсрэг тохиолдолд улаан
            color = (0, 255, 0) if track_id in self.counted_ids else (0, 0, 255)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.circle(frame, (cx, cy), 4, color, -1)
            cv2.putText(frame, f'ID: {track_id}', (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # ROI зурах
        if self.roi_polygon is not None:
            cv2.polylines(frame, [self.roi_polygon], isClosed=True, color=(255, 0, 0), thickness=2)
            
        # Тоог харуулах
        cv2.putText(frame, f'Count: {self.vehicle_count}', (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                    
        return frame 