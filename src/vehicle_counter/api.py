import os
import logging
import threading
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from .vehicle_counter_service import VehicleCounterService


# API хэрэглэгчийн загварууд үүсгэх
class CountingConfig(BaseModel):
    """
    Тээврийн хэрэгсэл тоолох тохиргоо
    """
    video_path: Optional[str] = None
    model_path: str = "yolov8s.pt"
    device: str = "cpu"
    display: bool = True
    save_data: bool = True
    save_video: bool = False
    location: Optional[str] = None


class CountingStatus(BaseModel):
    """
    Тоолох процессийн төлөвийн мэдээлэл
    """
    is_running: bool
    video_path: Optional[str] = None
    model_path: str
    frame_count: int = 0
    fps: float = 0.0
    zones: List[Dict] = []


class CongestionData(BaseModel):
    """
    Түгжрэлийн мэдээлэл
    """
    timestamp: float
    location: Optional[str] = None
    zone_data: List[Dict]
    total_vehicles: int


# API сервис үүсгэх
app = FastAPI(
    title="Тээврийн хэрэгсэл тоолох API",
    description="Зоны тээврийн хэрэгсэл тоолох, тооцоолох API",
    version="1.0.0"
)

# Процессийн төлөв
counter_status = CountingStatus(
    is_running=False,
    model_path="yolov8s.pt",
    video_path=None,
    zones=[]
)

# Сервис инстанс
counter_service = None
counter_thread = None


@app.get("/api/vehicle-counter/status", response_model=CountingStatus)
async def get_status():
    """
    Процессийн төлөв авах
    """
    global counter_status, counter_service
    
    if counter_service and counter_service.processing:
        # Төлөв шинэчлэх
        counter_status.frame_count = counter_service.frame_count
        counter_status.fps = counter_service.fps
        
        # Бүсийн мэдээлэл шинэчлэх
        counter_status.zones = []
        for zone in counter_service.zone_manager.zones:
            counter_status.zones.append({
                "id": zone.id,
                "name": zone.name,
                "type": "COUNT" if zone.is_count_zone() else "SUM",
                "count": zone.get_display_count()
            })
    
    return counter_status


@app.post("/api/vehicle-counter/start", response_model=CountingStatus)
async def start_counting(config: CountingConfig):
    """
    Шинэ тоолох процесс эхлүүлэх
    """
    global counter_status, counter_service, counter_thread
    
    # Видео зам шалгах
    if config.video_path and not os.path.exists(config.video_path):
        raise HTTPException(status_code=404, detail=f"Видео файл олдсонгүй: {config.video_path}")
    
    # Өмнөх процесс зогсоох
    if counter_service and counter_service.processing:
        counter_service.stop_counting()
        if counter_thread:
            counter_thread.join(timeout=3.0)
    
    # Шинэ сервис үүсгэх
    counter_service = VehicleCounterService(
        video_path=config.video_path,
        model_path=config.model_path,
        device=config.device,
        output_path="data"
    )
    
    # Төлөв шинэчлэх
    counter_status.is_running = True
    counter_status.video_path = config.video_path
    counter_status.model_path = config.model_path
    counter_status.frame_count = 0
    counter_status.fps = 0.0
    counter_status.zones = []
    
    # Тоолох процесс эхлүүлэх
    counter_thread = threading.Thread(
        target=counter_service.start_counting,
        kwargs={
            "display": config.display,
            "save_data": config.save_data,
            "save_video": config.save_video
        }
    )
    counter_thread.daemon = True
    counter_thread.start()
    
    return counter_status


@app.get("/api/vehicle-counter/stop")
async def stop_counting():
    """
    Тоолох процесс зогсоох
    """
    global counter_status, counter_service, counter_thread
    
    if not counter_service or not counter_service.processing:
        raise HTTPException(status_code=400, detail="Тоолох процесс ажиллаж байхгүй байна")
    
    # Процесс зогсоох
    counter_service.stop_counting()
    if counter_thread:
        counter_thread.join(timeout=3.0)
    
    # Төлөв шинэчлэх
    counter_status.is_running = False
    
    return {"status": "Процесс зогсоолоо"}


@app.get("/api/vehicle-counter/videos")
async def list_videos():
    """
    Боломжит видеоны жагсаалт авах
    """
    videos = []
    
    # Стандарт видео хадгалах зам
    video_dirs = ["data", "videos"]
    
    for video_dir in video_dirs:
        if os.path.exists(video_dir):
            for file in os.listdir(video_dir):
                if file.endswith((".mp4", ".avi", ".mov", ".mkv")):
                    videos.append({
                        "path": os.path.join(video_dir, file),
                        "name": file
                    })
    
    return {"videos": videos}


@app.get("/api/congestion/current", response_model=CongestionData)
async def get_congestion():
    """
    Одоогийн түгжрэлийн мэдээлэл авах
    """
    global counter_service
    
    if not counter_service or not counter_service.processing:
        raise HTTPException(
            status_code=400, 
            detail="Тоолох процесс ажиллаж байхгүй байна. Эхлээд процесс эхлүүлнэ үү."
        )
    
    # Бүс тус бүрийн өгөгдөл
    zone_data = []
    total_vehicles = 0
    
    for zone in counter_service.zone_manager.zones:
        count = zone.get_display_count()
        total_vehicles += count
        
        zone_data.append({
            "id": zone.id,
            "name": zone.name,
            "type": "COUNT" if zone.is_count_zone() else "SUM",
            "count": count,
            # Түгжрэлийн түвшин тооцоолох
            "congestion_level": get_congestion_level(count, zone.is_count_zone())
        })
    
    return CongestionData(
        timestamp=counter_service.start_time,
        zone_data=zone_data,
        total_vehicles=total_vehicles
    )


def get_congestion_level(count, is_count_zone):
    """
    Түгжрэлийн түвшин тооцоолох
    
    Args:
        count (int): Тээврийн хэрэгслийн тоо
        is_count_zone (bool): COUNT төрлийн бүс эсэх
    
    Returns:
        str: Түгжрэлийн түвшин (low, medium, high)
    """
    # COUNT ба SUM бүсийн хувьд өөр логик хэрэглэнэ
    if is_count_zone:
        # COUNT бүсийн хувьд (нэвтрэлтийн хурд)
        if count < 10:
            return "low"
        elif count < 20:
            return "medium"
        else:
            return "high"
    else:
        # SUM бүсийн хувьд (одоогийн тоо)
        if count < 5:
            return "low"
        elif count < 10:
            return "medium"
        else:
            return "high"


# API сервер эхлүүлэх
def start_api_server(host="0.0.0.0", port=8000):
    """
    API сервер эхлүүлэх
    """
    uvicorn.run(app, host=host, port=port)


# API модуль дангаараа ажиллах
if __name__ == "__main__":
    start_api_server() 