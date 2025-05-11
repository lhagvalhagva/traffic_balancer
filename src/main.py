import os
import time
import threading
import json
import argparse
import subprocess
from pathlib import Path

# Create paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
os.makedirs(DATA_DIR, exist_ok=True)

def start_vehicle_counter(video_path=None, display=True):
    """
    Start the vehicle counting module
    
    Args:
        video_path: Video file path
        display: Whether to display the video
    """
    from vehicle_counter.vehicle_counter_service import VehicleCounterService
    print("Vehicle counting module started...")
    
    service = VehicleCounterService(
        video_path=video_path,
        output_path=str(DATA_DIR)
    )
    service.start_counting(display=display, save_data=True)

def start_traffic_analyzer(host="0.0.0.0", port=8000):
    """
    Start the traffic congestion analysis API server
    
    Args:
        host: Host address
        port: Port
    """
    from traffic_analyzer.api import start_api
    print(f"Starting traffic analyzer API server at {host}:{port}...")
    
    start_api(host=host, port=port)

def start_traffic_light_controller(port=3000):
    """
    Start the traffic light controller server
    
    Args:
        port: Port
    """
    controller_dir = BASE_DIR / "src" / "traffic_light_controller"
    
    print(f"Starting traffic light controller server on port {port}...")
    
    # Start Node.js server
    process = subprocess.Popen(
        ["node", "app.js"],
        cwd=controller_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Monitor logs
    for line in iter(process.stdout.readline, ""):
        print(f"[Traffic Light Controller] {line.strip()}")

def main():
    """
    Main program
    """
    parser = argparse.ArgumentParser(description="Traffic monitoring and control system")
    parser.add_argument("--video", type=str, help="Video file path")
    parser.add_argument("--no-display", action="store_true", help="Do not display video")
    parser.add_argument("--api-port", type=int, default=8000, help="Traffic analyzer API port")
    parser.add_argument("--controller-port", type=int, default=3000, help="Traffic light controller port")
    args = parser.parse_args()
    
    try:
        # Start modules in separate threads
        counter_thread = threading.Thread(
            target=start_vehicle_counter,
            args=(args.video, not args.no_display)
        )
        
        analyzer_thread = threading.Thread(
            target=start_traffic_analyzer,
            args=("0.0.0.0", args.api_port)
        )
        
        controller_thread = threading.Thread(
            target=start_traffic_light_controller,
            args=(args.controller_port,)
        )
        
        counter_thread.start()
        time.sleep(2) 
        
        analyzer_thread.start()
        time.sleep(2) 
        
        controller_thread.start()
        
        while True:
            time.sleep(1)
            if not counter_thread.is_alive() and not analyzer_thread.is_alive() and not controller_thread.is_alive():
                print("All modules stopped. Program finished.")
                break
    
    except KeyboardInterrupt:
        print("\nProgram stopped by user request.")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main() 