import cv2
import json
import os
import time
import platform
from datetime import datetime
from .detector import VehicleDetector
from .counter import VehicleCounter
import argparse

class VehicleCounterService:
    def __init__(self, video_path=None, model_path="yolov8s.pt", output_path="data", device="cpu"):
        """
        Тээврийн хэрэгсэл тоолох үйлчилгээ
        
        Args:
            video_path: Видеоны зам (None бол камераас)
            model_path: YOLO загварын зам (yolov8s.pt гэж өөрчлөгдсөн)
            output_path: Гаралтын өгөгдлийн санын зам
            device: Ашиглах төхөөрөмж (cpu, cuda, mps)
        """
        self.video_path = video_path
        self.device = device
        
        # Загвар үүсгэх
        print(f"YOLOv8s загвар '{device}' төхөөрөмж дээр ажиллуулж байна")
        self.detector = VehicleDetector(model_path=model_path, device=device)
        self.counter = VehicleCounter()
        self.output_path = output_path
        
        # FPS сайжруулах тохиргоо
        self.process_every_n_frames = 2  # Зөвхөн n дахь frame-ийг боловсруулна
        self.display_every_n_frames = 1  # Зөвхөн n дахь frame-ийг харуулна
        self.down_scale_factor = 1.0     # Видеог багасгах хэмжээ (1.0 = өөрчлөхгүй)
        
        # Өгөгдөл хадгалах папка үүсгэх
        os.makedirs(output_path, exist_ok=True)
        
    def process_video(self, display=True, save_data=True, save_video=False, api_callback=None):
        """
        Бүтэн видеоны боловсруулалт хийх
        
        Args:
            display: Видеог харуулах эсэх
            save_data: Өгөгдлийг хадгалах эсэх
            save_video: Боловсруулсан видеог хадгалах эсэх
            api_callback: API-д мэдээлэл дамжуулах callback функц
            
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
        
        # Видеоны параметрүүд
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        width = original_width
        height = original_height
        
        # Видеоны нарийвчлалыг бууруулах - FPS сайжруулахад тустай
        if self.down_scale_factor != 1.0:
            width = int(original_width / self.down_scale_factor)
            height = int(original_height / self.down_scale_factor)
            print(f"Видеоны нарийвчлалыг {width}x{height} болгож бууруулав")
        
        # FPS олж авах
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30  # Default FPS
            print("Видеоны FPS олдсонгүй, 30 FPS-ийг хэрэглэж байна")
        else:
            print(f"Видеоны FPS: {fps}")
        
        # Counter класст FPS-ийг шинэчлэх
        self.counter.update_fps(fps)
            
        # Анхны frame авах
        ret, frame = cap.read()
        if not ret:
            print("Frame уншиж чадсангүй")
            return None
            
        # Хэмжээг бууруулах
        if self.down_scale_factor != 1.0:
            frame = cv2.resize(frame, (width, height))
            
        # ROI тохируулах
        self.counter.setup_roi(frame)
        
        # Видео бичлэгийн тохиргоо
        if save_video:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            output_video = cv2.VideoWriter(
                os.path.join(self.output_path, 'output.mp4'),
                fourcc, fps, (width, height)
            )
            
        # Өгөгдөл хадгалах
        count_data = {
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "location": self.video_path if self.video_path else "Live Camera",
            "counts": [],
            "total_count": 0,
            "congestion_data": []  # Түгжрэлийн мэдээлэл
        }
        
        start_time = time.time()
        # Counter класст start_time байвал түүнийг ашиглана
        self.counter.start_time = start_time
        frame_count = 0
        last_congestion_update = start_time
        congestion_update_interval = 5  # 5 сек тутам шинэчилнэ
        
        # FPS хэмжих хувьсагчууд
        fps_start_time = start_time
        fps_frame_count = 0
        fps_display = 0
        
        # Сүүлийн tracks хадгалах - frame алгасаж боловсруулах үед ашиглана
        last_tracks = None
        
        api_callback_interval = 1
        last_api_callback = start_time
        
        # Үндсэн боловсруулалтын давталт
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Хэмжээг бууруулах
            if self.down_scale_factor != 1.0:
                frame = cv2.resize(frame, (width, height))
                
            frame_count += 1
            fps_frame_count += 1
            
            # FPS тооцох
            if (time.time() - fps_start_time) > 1.0:
                fps_display = fps_frame_count / (time.time() - fps_start_time)
                fps_frame_count = 0
                fps_start_time = time.time()
            
            # n дахь frame-ийг л боловсруулах
            if frame_count % self.process_every_n_frames == 0:
                # Тоолох бүх процесс
                tracks, _ = self.detector.detect_and_track(frame)
                last_tracks = tracks
                count, new_ids = self.counter.count_vehicles(tracks)
                
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
                
                # Түгжрэлийн мэдээлэл шинэчлэх (хуваарьтай)
                if current_time - last_congestion_update >= congestion_update_interval:
                    congestion_data = self.counter.get_congestion_data()
                    congestion_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    count_data["congestion_data"].append(congestion_data)
                    last_congestion_update = current_time
                    
                    # Консолд хэвлэх
                    self.print_congestion_status(congestion_data)
                    
                    if api_callback and current_time - last_api_callback >= api_callback_interval:
                        api_callback(congestion_data)
                        last_api_callback = current_time
            else:
                # Боловсруулахгүй frame-д өмнөх tracks ашиглах
                if last_tracks is not None:
                    tracks = last_tracks
                else:
                    tracks = []
            
            # Visualization хийх
            annotated_frame = self.counter.draw_visualization(frame, tracks)
            
            # FPS харуулах
            cv2.putText(annotated_frame, f"FPS: {fps_display:.1f}", (20, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
            # Видео харуулах (n дахь frame-д)
            if display and frame_count % self.display_every_n_frames == 0:
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
    
    def print_congestion_status(self, congestion_data):
        """
        Түгжрэлийн мэдээллийг консолд хэвлэх
        """
        level = congestion_data["congestion_level"]
        level_text = {
            "low": "Бага",
            "medium": "Дунд",
            "high": "Өндөр",
            "very_high": "Маш өндөр"
        }
        
        print(f"=== Түгжрэлийн мэдээлэл ===")
        print(f"Түвшин: {level_text.get(level, level)}")
        print(f"ROI доторх машин: {congestion_data['vehicles_in_roi']}")
        print(f"Хөдөлгөөнгүй машин: {congestion_data['static_vehicles']}")
        if 'max_static_duration' in congestion_data:
            print(f"Хамгийн удаан зогссон: {congestion_data['max_static_duration']:.1f} сек")
        print(f"Минутад тоологдсон машин: {congestion_data['vehicles_per_minute']:.1f}")
        
    def start_counting(self, display=True, save_data=True, save_video=False, api_callback=None):
        """
        Тоолох процессийг эхлүүлэх
        
        Args:
            display: Видеог харуулах эсэх
            save_data: Өгөгдлийг хадгалах эсэх
            save_video: Боловсруулсан видеог хадгалах эсэх
            api_callback: API-д мэдээлэл дамжуулах callback функц
            
        Returns:
            count_data: Тоолсон өгөгдөл
        """
        return self.process_video(display, save_data, save_video, api_callback)
        
if __name__ == "__main__":
    # Command line аргументууд зохицуулах
    parser = argparse.ArgumentParser(description="Тээврийн хэрэгсэл тоолох систем")
    parser.add_argument("--video", type=str, default="video2.mp4", help="Видеоны зам (default: videos.mp4)")
    parser.add_argument("--device", type=str, default="auto", help="Төхөөрөмж (auto, cpu, cuda, mps)")
    parser.add_argument("--scale", type=float, default=1.5, help="Дүрсийн хэмжээг бууруулах харьцаа (default: 1.5)")
    parser.add_argument("--skip", type=int, default=2, help="Frame алгасах харьцаа (default: 2)")
    
    args = parser.parse_args()
    
    # Хэрэв "auto" бол автоматаар хурдасгуур сонгох
    device = args.device
    
    if device == "auto":
        device = "cpu"  
        
        # Apple Silicon дээр MPS ашиглах
        if platform.system() == "Darwin" and "arm" in platform.processor():
            try:
                import torch
                if torch.backends.mps.is_available():
                    device = "mps"
                    print("Apple MPS хурдасгуур ашиглаж байна")
            except Exception as e:
                print(f"MPS шалгахад алдаа: {e}")
                
        # NVIDIA GPU шалгах
        elif platform.system() in ["Linux", "Windows"]:
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    print("CUDA GPU хурдасгуур ашиглаж байна")
            except Exception as e:
                print(f"CUDA шалгахад алдаа: {e}")
    
    # Тоолох үйлчилгээ эхлүүлэх
    counter_service = VehicleCounterService(
        video_path=args.video,
        model_path="yolov8s.pt",
        output_path="data",
        device=device
    )
    
    # FPS сайжруулах тохиргоо
    counter_service.process_every_n_frames = args.skip
    counter_service.display_every_n_frames = 1
    counter_service.down_scale_factor = args.scale
    
    # Тоолж эхлэх
    print(f"Видео: {args.video}")
    print(f"Хурдасгуур: {device}")
    print(f"Хэмжээ бууруулах харьцаа: {args.scale}")
    print(f"Frame алгасах харьцаа: {args.skip}")
    
    result = counter_service.start_counting(display=True, save_data=True)