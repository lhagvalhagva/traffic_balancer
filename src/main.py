import os
import time
import threading
import json
import argparse
import subprocess
from pathlib import Path

# Зам үүсгэх
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
os.makedirs(DATA_DIR, exist_ok=True)

def start_vehicle_counter(video_path=None, display=True):
    """
    Тээврийн хэрэгсэл тоолох модулийг эхлүүлэх
    
    Args:
        video_path: Видео бичлэгийн зам
        display: Видеог харуулах эсэх
    """
    from vehicle_counter.main import VehicleCounterService
    print("Тээврийн хэрэгсэл тоолох модуль эхэллээ...")
    
    service = VehicleCounterService(
        video_path=video_path,
        output_path=str(DATA_DIR)
    )
    service.start_counting(display=display, save_data=True)

def start_traffic_analyzer(host="0.0.0.0", port=8000):
    """
    Түгжрэлийн түвшин тодорхойлох API серверийг эхлүүлэх
    
    Args:
        host: Хост хаяг
        port: Порт
    """
    from traffic_analyzer.api import start_api
    print(f"Түгжрэлийн шинжээч API серверийг {host}:{port} хаягт эхлүүлж байна...")
    
    start_api(host=host, port=port)

def start_traffic_light_controller(port=3000):
    """
    Гэрлэн дохио удирдлагын серверийг эхлүүлэх
    
    Args:
        port: Порт
    """
    controller_dir = BASE_DIR / "src" / "traffic_light_controller"
    
    print(f"Гэрлэн дохио удирдлагын сервер {port} портод эхлүүлж байна...")
    
    # Node.js сервер эхлүүлэх
    process = subprocess.Popen(
        ["node", "app.js"],
        cwd=controller_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Бүртгэлийг хянах
    for line in iter(process.stdout.readline, ""):
        print(f"[Traffic Light Controller] {line.strip()}")

def main():
    """
    Үндсэн програм
    """
    parser = argparse.ArgumentParser(description="Замын хөдөлгөөний хяналт, удирдлагын систем")
    parser.add_argument("--video", type=str, help="Видео файлын зам")
    parser.add_argument("--no-display", action="store_true", help="Видеог харуулахгүй")
    parser.add_argument("--api-port", type=int, default=8000, help="Түгжрэлийн API порт")
    parser.add_argument("--controller-port", type=int, default=3000, help="Гэрлэн дохио удирдлагын порт")
    args = parser.parse_args()
    
    try:
        # Модулиудыг тус тусдаа thread-д эхлүүлэх
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
                print("Бүх модулиуд зогссон. Програм дууссан.")
                break
    
    except KeyboardInterrupt:
        print("\nПрограм хэрэглэгчийн хүсэлтээр зогссон.")
    except Exception as e:
        print(f"Алдаа гарлаа: {e}")

if __name__ == "__main__":
    main() 