import cv2
import json
import os
import time
from datetime import datetime
from .detector import VehicleDetector
from .counter import VehicleCounter

class VehicleCounterService:
    def __init__(self, video_path=None, model_path="yolov8n.pt", output_path="data"):
        """
        Тээврийн хэрэгсэл тоолох үйлчилгээ
        
        Args:
            video_path: Видеоны зам (None бол камераас)
            model_path: YOLO загварын зам
            output_path: Гаралтын өгөгдлийн санын зам
        """
        self.video_path = video_path
        self.detector = VehicleDetector(model_path=model_path)
        self.counter = VehicleCounter()
        self.output_path = output_path
        
        # Өгөгдөл хадгалах папка үүсгэх
        os.makedirs(output_path, exist_ok=True)
        
    def process_video(self, display=True, save_data=True, save_video=False):
        """
        Бүтэн видеоны боловсруулалт хийх
        
        Args:
            display: Видеог харуулах эсэх
            save_data: Өгөгдлийг хадгалах эсэх
            save_video: Боловсруулсан видеог хадгалах эсэх
            
        Returns:
            count_data: Тоолсон өгөгдөл
        """
        # Видео эсвэл камера нээх
        if self.video_path:
            cap = cv2.VideoCapture(self.video_path)
        else:
            cap = cv2.VideoCapture(0)  # Веб камераас
            
        if not cap.isOpened():
            print("Видео нээх боломжгүй")
            return None
            
        # Анхны frame авах
        ret, frame = cap.read()
        if not ret:
            print("Frame уншиж чадсангүй")
            return None
            
        # ROI тохируулах
        self.counter.setup_roi(frame)
        
        # Видео бичлэгийн тохиргоо
        if save_video:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            output_video = cv2.VideoWriter(
                os.path.join(self.output_path, 'output.mp4'),
                fourcc, fps, (width, height)
            )
            
        # Өгөгдөл хадгалах
        count_data = {
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "location": self.video_path if self.video_path else "Live Camera",
            "counts": [],
            "total_count": 0
        }
        
        start_time = time.time()
        frame_count = 0
        
        # Үндсэн боловсруулалтын давталт
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Тоолох бүх процесс
            tracks, _ = self.detector.detect_and_track(frame)
            count, new_ids = self.counter.count_vehicles(tracks)
            annotated_frame = self.counter.draw_visualization(frame, tracks)
            
            # Шинэ өгөгдөл хадгалах
            current_time = time.time()
            if new_ids:
                for vehicle_id in new_ids:
                    count_data["counts"].append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "elapsed_time": current_time - start_time,
                        "frame": frame_count,
                        "vehicle_id": vehicle_id,
                        "total_count": count
                    })
            
            # FPS тооцох
            frame_count += 1
            elapsed_time = current_time - start_time
            fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            
            # FPS харуулах
            cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
            # Видео харуулах
            if display:
                cv2.imshow("Vehicle Counter", annotated_frame)
                if cv2.waitKey(1) & 0xFF == 27:  # ESC key to exit
                    break
                    
            # Видео хадгалах
            if save_video:
                output_video.write(annotated_frame)
                
        # Бүх зүйлийг хаах
        cap.release()
        if save_video:
            output_video.release()
        cv2.destroyAllWindows()
        
        # Эцсийн өгөгдөл шинэчлэх
        count_data["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count_data["duration"] = time.time() - start_time
        count_data["total_count"] = self.counter.vehicle_count
        
        # Өгөгдлийг JSON файлд хадгалах
        if save_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(os.path.join(self.output_path, f"vehicle_count_{timestamp}.json"), "w") as f:
                json.dump(count_data, f, indent=4)
                
        return count_data
        
    def start_counting(self, display=True, save_data=True, save_video=False):
        """
        Тоолох процессийг эхлүүлэх
        """
        return self.process_video(display, save_data, save_video)
        
if __name__ == "__main__":
    # Жишээ ашиглалт
    counter_service = VehicleCounterService(video_path="video.mp4")
    result = counter_service.start_counting(display=True, save_data=True)