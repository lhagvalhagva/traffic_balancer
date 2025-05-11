import argparse
import os
from vehicle_counter_service import VehicleCounterService


def main():
    """
    Тээврийн хэрэгсэл тоолох үндсэн функц.
    """
    # Аргументууд зохицуулах
    parser = argparse.ArgumentParser(description="Тээврийн хэрэгсэл тоолох систем")
    
    parser.add_argument("--video", "-v", type=str, default="viiddeo.mov",
                        help="Видео файлын зам (заагаагүй бол камер ашиглана)")
    
    parser.add_argument("--model", "-m", type=str, default="yolov8s.pt",
                       help="YOLO моделийн зам")
    
    parser.add_argument("--device", "-d", type=str, default="cpu",
                       help="Ашиглах төхөөрөмж (cpu, cuda, mps)")
    
    parser.add_argument("--output", "-o", type=str, default="data",
                       help="Өгөгдөл хадгалах зам")
    
    parser.add_argument("--save-video", "-sv", action="store_true", 
                       help="Боловсруулсан видео хадгалах эсэх")
    
    parser.add_argument("--save-data", "-sd", action="store_true",
                      help="Өгөгдөл хадгалах эсэх")
    
    parser.add_argument("--no-display", "-nd", action="store_true",
                      help="Видео харуулахгүй")
    
    # Аргументууд задлах
    args = parser.parse_args()
    
    # Сервис үүсгэх
    service = VehicleCounterService(
        video_path=args.video,
        model_path=args.model,
        device=args.device,
        output_path=args.output
    )
    
    # Тоолох процесс эхлүүлэх
    service.start_counting(
        display=not args.no_display,
        save_data=args.save_data,
        save_video=args.save_video
    )


if __name__ == "__main__":
    main()
