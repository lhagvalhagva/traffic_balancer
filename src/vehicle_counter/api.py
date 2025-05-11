import os
import logging
import threading
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from vehicle_counter_service import VehicleCounterService


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


class ZoneCreationRequest(BaseModel):
    points: list
    zone_type: int
    name: str
    traffic_light_directions: list = []


class TrafficLightRequest(BaseModel):
    direction: str
    action: str  # "red", "blue", "green"
    duration: int = None


class TrafficLightAutoModeRequest(BaseModel):
    enabled: bool


# API сервис үүсгэх
app = FastAPI(
    title="Замын хөдөлгөөн удирдлагын API",
    description="Тээврийн хэрэгсэл тоолох, түгжрэл тодорхойлох ба гэрлэн дохио удирдах API"
)

# CORS зөвшөөрөх
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/")
def read_root():
    return {"message": "Замын хөдөлгөөнийг хянах ба удирдах системийн API"}


@app.get("/api/zones")
def get_zones():
    """
    Бүх бүсийн жагсаалтыг авах
    """
    if counter_service is None:
        raise HTTPException(status_code=503, detail="Систем бэлэн бус байна")
    
    zones = []
    
    for zone in counter_service.zone_manager.zones:
        zones.append({
            "id": zone.id,
            "name": zone.name,
            "type": zone.type,
            "vehicle_count": zone.get_display_count(),
            "is_stalled": zone.is_stalled,
            "traffic_light_directions": zone.traffic_light_directions,
            "points": zone.points
        })
    
    return {"zones": zones}


@app.post("/api/zones")
def create_zone(request: ZoneCreationRequest):
    """
    Шинэ бүс үүсгэх
    """
    if counter_service is None:
        raise HTTPException(status_code=503, detail="Систем бэлэн бус байна")
    
    try:
        # Бүс үүсгэх
        zone = counter_service.zone_manager.create_zone(
            points=request.points,
            zone_type=request.zone_type,
            name=request.name
        )
        
        # Гэрлэн дохионы чиглэлүүд тохируулах
        zone.traffic_light_directions = request.traffic_light_directions
        
        return {
            "success": True,
            "zone_id": zone.id,
            "message": f"Бүс '{zone.name}' амжилттай үүслээ"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Бүс үүсгэхэд алдаа гарлаа: {str(e)}")


@app.get("/api/zones/{zone_id}")
def get_zone(zone_id: int):
    """
    Тодорхой бүсийн дэлгэрэнгүй мэдээлэл авах
    """
    if counter_service is None:
        raise HTTPException(status_code=503, detail="Систем бэлэн бус байна")
    
    zone = counter_service.zone_manager.get_zone_by_id(zone_id)
    
    if zone is None:
        raise HTTPException(status_code=404, detail=f"Бүс ID={zone_id} олдсонгүй")
    
    # Машины ID-ний жагсаалтыг string болгох
    vehicle_ids = [str(vehicle_id) for vehicle_id in zone.current_vehicles]
    
    return {
        "id": zone.id,
        "name": zone.name,
        "type": zone.type,
        "type_name": "COUNT" if zone.is_count_zone() else "SUM",
        "vehicle_count": zone.get_display_count(),
        "current_vehicles": vehicle_ids,
        "is_stalled": zone.is_stalled,
        "traffic_light_directions": zone.traffic_light_directions,
        "points": zone.points
    }


@app.get("/api/statistics")
def get_all_statistics():
    """
    Бүх бүсийн статистик мэдээлэл авах
    """
    if counter_service is None:
        raise HTTPException(status_code=503, detail="Систем бэлэн бус байна")
    
    try:
        statistics = counter_service.zone_manager.get_all_statistics()
        
        # Нийт статистик нэмэх
        total_stats = {
            "total_zones": len(statistics),
            "total_congestion_events": sum(stat["congestion_events"] for stat in statistics),
            "avg_congestion_time": sum(stat["total_stalled_time"] for stat in statistics) / len(statistics) if statistics else 0,
            "busiest_zone": None,
            "timestamp": time.time()
        }
        
        # Хамгийн их машинтай бүсийг олох
        max_vehicles = 0
        busiest_zone = None
        
        for stat in statistics:
            if stat["max_vehicle_count"] > max_vehicles:
                max_vehicles = stat["max_vehicle_count"]
                busiest_zone = stat["zone_name"]
                
        total_stats["busiest_zone"] = busiest_zone
        total_stats["max_vehicles"] = max_vehicles
        
        return {
            "zones": statistics,
            "summary": total_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Статистик авахад алдаа гарлаа: {str(e)}")


@app.get("/api/statistics/{zone_id}")
def get_zone_statistics(zone_id: int):
    """
    Тодорхой бүсийн статистик мэдээлэл авах
    """
    if counter_service is None:
        raise HTTPException(status_code=503, detail="Систем бэлэн бус байна")
    
    stats = counter_service.zone_manager.get_zone_statistics(zone_id)
    
    if stats is None:
        raise HTTPException(status_code=404, detail=f"Бүс ID={zone_id} олдсонгүй")
        
    return stats


@app.get("/api/traffic-lights")
def get_traffic_lights():
    """
    Гэрлэн дохионуудын мэдээлэл авах
    """
    if counter_service is None or counter_service.traffic_light_controller is None:
        raise HTTPException(status_code=503, detail="Гэрлэн дохионы систем бэлэн бус байна")
    
    return {
        "lights": counter_service.traffic_light_controller.traffic_lights,
        "auto_mode": counter_service.traffic_light_controller.auto_mode
    }


@app.post("/api/traffic-lights")
def control_traffic_light(request: TrafficLightRequest):
    """
    Тодорхой гэрлэн дохио удирдах
    """
    if counter_service is None or counter_service.traffic_light_controller is None:
        raise HTTPException(status_code=503, detail="Гэрлэн дохионы систем бэлэн бус байна")
    
    controller = counter_service.traffic_light_controller
    direction = request.direction
    
    if direction not in controller.traffic_lights:
        raise HTTPException(status_code=404, detail=f"Гэрлэн дохионы чиглэл '{direction}' олдсонгүй")
    
    try:
        # Хугацаа тохируулах
        if request.duration is not None:
            controller.traffic_lights[direction]["duration"] = request.duration
        
        # Гэрлийн өнгө солих
        if request.action == "red":
            success = controller.switch_to_red(direction)
        elif request.action == "blue":
            success = controller.switch_to_blue(direction)
        elif request.action == "green":
            success = controller.switch_to_green(direction)
        else:
            raise HTTPException(status_code=400, detail=f"Үйлдэл '{request.action}' буруу байна")
        
        return {
            "success": success,
            "direction": direction,
            "status": controller.traffic_lights[direction]["status"],
            "changed_time": controller.traffic_lights[direction]["changed_time"],
            "duration": controller.traffic_lights[direction]["duration"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Гэрлэн дохио удирдахад алдаа гарлаа: {str(e)}")


@app.post("/api/traffic-lights/auto-mode")
def set_traffic_light_auto_mode(request: TrafficLightAutoModeRequest):
    """
    Гэрлэн дохионы автомат горимыг тохируулах
    """
    if counter_service is None or counter_service.traffic_light_controller is None:
        raise HTTPException(status_code=503, detail="Гэрлэн дохионы систем бэлэн бус байна")
    
    controller = counter_service.traffic_light_controller
    
    # Автомат горим тохируулах
    controller.auto_mode = request.enabled
    
    return {
        "success": True,
        "auto_mode": controller.auto_mode
    }


@app.get("/api/congestion")
def get_congestion_status():
    """
    Бүх бүсийн түгжрэлийн статусыг авах
    """
    if counter_service is None:
        raise HTTPException(status_code=503, detail="Систем бэлэн бус байна")
    
    congestion_data = []
    
    for zone in counter_service.zone_manager.zones:
        congestion_data.append({
            "zone_id": zone.id,
            "zone_name": zone.name,
            "is_stalled": zone.is_stalled,
            "vehicle_count": len(zone.current_vehicles),
            "stalled_time": zone.stalled_time
        })
    
    return {"congestion": congestion_data}


@app.get("/api/dashboard")
def get_dashboard_data():
    """
    Даашбоард харуулах мэдээлэл авах
    """
    if counter_service is None:
        raise HTTPException(status_code=503, detail="Систем бэлэн бус байна")
    
    # Бүсүүдийн мэдээлэл
    zones_data = []
    stalled_zones = 0
    total_vehicles = 0
    
    for zone in counter_service.zone_manager.zones:
        vehicle_count = len(zone.current_vehicles)
        total_vehicles += vehicle_count
        
        if zone.is_stalled:
            stalled_zones += 1
            
        zones_data.append({
            "id": zone.id,
            "name": zone.name,
            "vehicle_count": vehicle_count,
            "is_stalled": zone.is_stalled,
            "type": "COUNT" if zone.is_count_zone() else "SUM"
        })
    
    # Гэрлэн дохионы мэдээлэл
    lights_data = {}
    red_lights = 0
    
    if counter_service.traffic_light_controller:
        lights_data = counter_service.traffic_light_controller.traffic_lights
        
        # Улаан гэрлийн тоо
        for light in lights_data.values():
            if light["status"] == "RED":
                red_lights += 1
    
    # Хураангуй
    summary = {
        "total_zones": len(zones_data),
        "stalled_zones": stalled_zones,
        "total_vehicles": total_vehicles,
        "congestion_level": "Хэвийн" if stalled_zones == 0 else "Дунд зэрэг" if stalled_zones < 3 else "Хүнд",
        "red_lights": red_lights,
        "timestamp": time.time()
    }
    
    return {
        "zones": zones_data,
        "lights": lights_data,
        "summary": summary
    }


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
def start_api(vehicle_counter=None, host="0.0.0.0", port=8000):
    """
    API сервер эхлүүлэх
    
    Args:
        vehicle_counter: Тээврийн хэрэгсэл тоолох сервис
        host (str): Хост хаяг
        port (int): Порт
    """
    global counter_service
    counter_service = vehicle_counter
    
    # Тусдаа thread дээр ажиллуулах
    api_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host=host, port=port)
    )
    api_thread.daemon = True
    api_thread.start()
    
    return api_thread


# API модуль дангаараа ажиллах
if __name__ == "__main__":
    start_api() 