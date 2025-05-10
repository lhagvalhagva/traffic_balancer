import argparse
import sys
import os

# Замыг оруулах - package install хийгдээгүй үед ашиглах
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_as_service():
    """FastAPI ашиглан API сервис болгон ажиллуулах"""
    import uvicorn
    from src.vehicle_counter import api_app
    
    print("Vehicle Counter API сервис эхлүүлж байна... (localhost:8000)")
    uvicorn.run(api_app, host="0.0.0.0", port=8000)

def run_as_application(video_path, model_path="yolov8s.pt", device="cpu"):
    """Шууд програм болгон ажиллуулах"""
    from src.vehicle_counter import VehicleCounterService
    
    print(f"Видео файл: {video_path}")
    print(f"Загвар: {model_path}")
    print(f"Төхөөрөмж: {device}")
    
    # Сервис үүсгэх
    counter_service = VehicleCounterService(
        video_path=video_path,
        model_path=model_path,
        device=device,
        output_path="data"
    )
    
    # Тоолох процесс эхлүүлэх
    result = counter_service.start_counting(
        display=True,
        save_data=True,
        save_video=False
    )
    
    if result:
        print(f"Нийт тоологдсон: {result['total_count']} тээврийн хэрэгсэл")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Тээврийн хэрэгсэл тоолох сервис жишээ")
    
    # Ерөнхий аргументууд
    parser.add_argument("--mode", type=str, choices=["app", "api"], default="app",
                       help="Ажиллах горим: 'app' (програм), 'api' (API сервис)")
    
    # App горимын аргументууд
    parser.add_argument("--video", type=str, default="src/vehicle_counter/video.mp4",
                       help="Видео файлын зам")
    parser.add_argument("--model", type=str, default="src/vehicle_counter/yolov8s.pt",
                       help="YOLO загварын зам")
    parser.add_argument("--device", type=str, default="cpu",
                       help="Ашиглах төхөөрөмж (cpu, cuda, mps)")
    
    args = parser.parse_args()
    
    if args.mode == "api":
        run_as_service()
    else:
        run_as_application(args.video, args.model, args.device)