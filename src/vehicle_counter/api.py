from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from datetime import datetime
import time
import threading
import os

# Хэрэглэгдэх класс импортлох
from .detector import VehicleDetector
from .counter import VehicleCounter
from .main import VehicleCounterService

app = FastAPI(title="Түгжрэлийн мэдээллийн API", 
              description="Тээврийн хэрэгсэл тоолох, түгжрэлийн түвшин тодорхойлох API")

# CORS зөвшөөрөх
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобал мэдээллийн сан
congestion_data = {
    "congestion_level": "low",
    "vehicles_per_minute": 0,
    "vehicles_in_roi": 0,
    "static_vehicles": 0,
    "max_static_duration": 0,
    "timestamp": datetime.now().isoformat(),
    "location": "Уулзвар 1"
}

# Counter сервисийн хувьсагч
vehicle_counter_service = None
counter_thread = None
is_running = False

class VideoSettings(BaseModel):
    video_path: str = None
    model_path: str = "yolov8s.pt"
    device: str = "cpu"
    display: bool = True
    save_data: bool = True
    save_video: bool = False
    location: str = "Уулзвар 1"

# Түгжрэлийн түвшин эргүүлэх API
@app.get("/api/congestion/current")
async def get_current_congestion():
    return congestion_data

# Түгжрэлийн түвшин шинэчлэх API - VehicleCounter сервисээс дуудагдана
@app.post("/api/congestion/update")
async def update_congestion(data: dict):
    global congestion_data
    
    # Өгөгдлийг шалгах
    required_fields = ["congestion_level", "vehicles_per_minute", "vehicles_in_roi", "static_vehicles"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Шаардлагатай талбар дутуу: {field}")
            
    # Өгөгдлийг шинэчлэх
    congestion_data = {
        "congestion_level": data["congestion_level"],
        "vehicles_per_minute": data["vehicles_per_minute"],
        "vehicles_in_roi": data["vehicles_in_roi"],
        "static_vehicles": data["static_vehicles"],
        "max_static_duration": data.get("max_static_duration", 0),
        "timestamp": datetime.now().isoformat(),
        "location": data.get("location", "Уулзвар 1")
    }
    
    return {"status": "success"}

def run_vehicle_counter(settings: VideoSettings):
    """
    Ажиллаж байгаа потокт тээврийн хэрэгслийн тоологчийг ажиллуулах
    """
    global vehicle_counter_service, congestion_data, is_running
    
    try:
        is_running = True
        vehicle_counter_service = VehicleCounterService(
            video_path=settings.video_path,
            model_path=settings.model_path,
            device=settings.device,
            output_path="data"
        )
        
        # API-д өгөгдөл дамжуулах callback функц
        def update_api_data(data):
            global congestion_data
            congestion_data = data
            congestion_data["location"] = settings.location
            congestion_data["timestamp"] = datetime.now().isoformat()
        
        # Counter сервис эхлүүлэх
        vehicle_counter_service.start_counting(
            display=settings.display, 
            save_data=settings.save_data, 
            save_video=settings.save_video,
            api_callback=update_api_data
        )
        
        is_running = False
    except Exception as e:
        is_running = False
        print(f"Тээврийн хэрэгсэл тоолох үед алдаа гарлаа: {e}")

@app.post("/api/vehicle-counter/start")
async def start_vehicle_counter(settings: VideoSettings, background_tasks: BackgroundTasks):
    global counter_thread, is_running
    
    if is_running:
        raise HTTPException(status_code=400, detail="Тээврийн хэрэгсэл тоологч аль хэдийн ажиллаж байна")
    
    # Өмнөх поток ажиллаж дууссан эсэхийг шалгах
    if counter_thread and counter_thread.is_alive():
        raise HTTPException(status_code=400, detail="Өмнөх тоологч дуусаагүй байна")
    
    # Шинэ поток эхлүүлэх
    counter_thread = threading.Thread(target=run_vehicle_counter, args=(settings,))
    counter_thread.daemon = True
    counter_thread.start()
    
    return {"status": "success", "message": "Тээврийн хэрэгсэл тоологч амжилттай эхэллээ"}

@app.get("/api/vehicle-counter/status")
async def get_vehicle_counter_status():
    return {
        "is_running": is_running,
        "congestion_data": congestion_data
    }

# Шалгах зориулалттай API руут
@app.get("/")
async def root():
    return {"message": "Түгжрэлийн мэдээллийн API ажиллаж байна"}

@app.get("/api/vehicle-counter/videos")
async def list_available_videos():
    """Боломжит видеоны жагсаалтыг буцаана"""
    videos = []
    try:
        for file in os.listdir("."):
            if file.endswith((".mp4", ".avi", ".mov", ".mkv")):
                videos.append(file)
    except Exception as e:
        print(f"Видео файл хайх үед алдаа гарлаа: {e}")
    
    return {"videos": videos}

if __name__ == "__main__":
    # Серверийг эхлүүлэх
    uvicorn.run(app, host="0.0.0.0", port=8000) 