import argparse
import os
from vehicle_counter_service import VehicleCounterService

def main():
    """
    Main function for vehicle counting.
    """
    # Configure arguments
    parser = argparse.ArgumentParser(description="Vehicle Counting System")
    
    parser.add_argument("--video", "-v", type=str, default="viiddeo.mov",
                        help="Video file path (uses camera if not specified)")
    
    parser.add_argument("--model", "-m", type=str, default="yolov8s.pt",
                       help="YOLO model path")
    
    parser.add_argument("--device", "-d", type=str, default="cpu",
                       help="Device to use (cpu, cuda, mps)")
    
    parser.add_argument("--output", "-o", type=str, default="data",
                       help="Output data path")
    
    parser.add_argument("--save-video", "-sv", action="store_true", 
                       help="Save processed video")
    
    parser.add_argument("--save-data", "-sd", action="store_true",
                      help="Save data")
    
    parser.add_argument("--no-display", "-nd", action="store_true",
                      help="Do not display video")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create service
    service = VehicleCounterService(
        video_path=args.video,
        model_path=args.model,
        device=args.device,
        output_path=args.output
    )
    
    # Start counting process
    service.start_counting(
        display=not args.no_display,
        save_data=args.save_data,
        save_video=args.save_video
    )

if __name__ == "__main__":
    main()