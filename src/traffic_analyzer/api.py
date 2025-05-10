from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime
import time

from analyzer import TrafficAnalyzer

app = FastAPI(title="Traffic Analyzer API",
              description="Замын хөдөлгөөний түгжрэл шинжилгээний API",
              version="1.0.0")

# CORS зөвшөөрөх
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Байгуулагч
analyzer = TrafficAnalyzer(data_path="data")

# API моделиуд
class TrafficAnalysisResponse(BaseModel):
    location: str
    start_time: str
    end_time: str
    total_duration_seconds: float
    total_vehicles: int
    average_flow_rate: float
    peak_flow_time: str
    peak_flow_count: int
    congestion_level: str
    congestion_history: List[str]
    time_windows: List[Dict[str, Any]]

class CongestionResponse(BaseModel):
    congestion_level: str
    vehicles_per_minute: float
    timestamp: str
    location: str

class CountDataUpload(BaseModel):
    count_data: Dict[str, Any]

# Өгөгдөл хадгалах сан
congestion_history = []
static_vehicles_data = {}
latest_congestion_data = {
    "congestion_level": "low",
    "vehicles_per_minute": 0,
    "vehicles_in_roi": 0,
    "static_vehicles": 0,
    "max_static_duration": 0,
    "avg_static_duration": 0,
    "congestion_risk_score": 0,
    "timestamp": datetime.now().isoformat(),
    "location": "Уулзвар 1"
}

# Endpoint-ууд
@app.get("/")
def read_root():
    return {"message": "Traffic Analyzer API"}

@app.get("/api/analysis/latest", response_model=TrafficAnalysisResponse)
def get_latest_analysis():
    """Хамгийн сүүлийн шинжилгээний мэдээллийг авах"""
    analysis = analyzer.analyze_traffic_flow()
    
    if "error" in analysis:
        raise HTTPException(status_code=404, detail=analysis["error"])
        
    return analysis

@app.get("/api/congestion/current")
async def get_current_congestion():
    """Одоогийн түгжрэлийн түвшинг авах"""
    return latest_congestion_data

@app.get("/api/congestion/history")
async def get_congestion_history(hours: Optional[int] = 1):
    """
    Түгжрэлийн түүхийн мэдээлэл авах
    
    Args:
        hours: Хэдэн цагийн өмнөөс мэдээлэл авах (default: 1)
    """
    # Одоогийн хугацаа
    current_time = time.time()
    
    # n цагийн өмнөөс мэдээлэл авах
    time_threshold = current_time - (hours * 3600)
    
    # Хугацааны хязгаараас хойших мэдээллүүд
    filtered_history = [
        item for item in congestion_history 
        if item.get("timestamp", 0) >= time_threshold
    ]
    
    return {
        "history": filtered_history,
        "count": len(filtered_history)
    }

@app.post("/api/congestion/update")
async def update_congestion(data: dict):
    global latest_congestion_data, congestion_history, static_vehicles_data
    
    # Өгөгдлийг шалгах
    required_fields = ["congestion_level", "vehicles_per_minute", "vehicles_in_roi", "static_vehicles"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Шаардлагатай талбар дутуу: {field}")
            
    # Түгжрэлийн эрсдлийн оноог тооцоолох
    congestion_metrics = {
        "vehicles_in_roi": data["vehicles_in_roi"],
        "static_vehicles": data["static_vehicles"],
        "max_static_duration": data.get("max_static_duration", 0),
        "avg_static_duration": data.get("max_static_duration", 0) / 2 if data.get("static_vehicles", 0) > 0 else 0
    }
    
    risk_score = analyzer.calculate_congestion_risk(congestion_metrics)
    
    # Өгөгдлийг шинэчлэх
    latest_congestion_data = {
        "congestion_level": data["congestion_level"],
        "vehicles_per_minute": data["vehicles_per_minute"],
        "vehicles_in_roi": data["vehicles_in_roi"],
        "static_vehicles": data["static_vehicles"],
        "max_static_duration": data.get("max_static_duration", 0),
        "avg_static_duration": congestion_metrics["avg_static_duration"],
        "congestion_risk_score": risk_score,
        "timestamp": time.time(),
        "location": data.get("location", "Уулзвар 1")
    }
    
    # Түүхэд нэмэх
    congestion_history.append(latest_congestion_data)
    
    # Түүхийг 1000 элементээр хязгаарлах
    if len(congestion_history) > 1000:
        congestion_history = congestion_history[-1000:]
    
    # Хэрэв зогссон машины дэлгэрэнгүй мэдээлэл байвал хадгалах
    if "static_vehicles_durations" in data:
        static_vehicles_data.update(data["static_vehicles_durations"])
    
    return {"status": "success", "risk_score": risk_score}

@app.get("/api/congestion/static_vehicles")
async def get_static_vehicles_distribution():
    """Зогссон машинуудын хугацааны хуваарилалт авах"""
    
    # Мэдээлэл байхгүй бол хоосон хариу буцаах
    if not static_vehicles_data:
        return {
            "distribution": {
                "short": 0,
                "medium": 0,
                "long": 0,
                "very_long": 0,
                "extreme": 0
            },
            "count": 0
        }
    
    # Хуваарилалт тооцоолох
    distribution = analyzer.analyze_static_vehicles(static_vehicles_data)
    
    # Нийт тоо
    total_count = sum(distribution.values())
    
    return {
        "distribution": distribution,
        "count": total_count
    }

@app.get("/api/congestion/risk_score")
async def get_congestion_risk_score():
    """Түгжрэлийн эрсдлийн оноо авах (0-100)"""
    return {
        "risk_score": latest_congestion_data.get("congestion_risk_score", 0),
        "level": get_risk_level(latest_congestion_data.get("congestion_risk_score", 0)),
        "timestamp": latest_congestion_data.get("timestamp", datetime.now().isoformat())
    }

@app.get("/api/congestion/graphs")
async def generate_congestion_graphs():
    """Түгжрэлийн графикууд үүсгэх"""
    
    # Өгөгдөл бэлтгэх
    analysis_data = {
        "counts": congestion_history,
        "static_durations": static_vehicles_data,
        "congestion_metrics": {
            "vehicles_in_roi": latest_congestion_data.get("vehicles_in_roi", 0),
            "static_vehicles": latest_congestion_data.get("static_vehicles", 0),
            "max_static_duration": latest_congestion_data.get("max_static_duration", 0),
            "avg_static_duration": latest_congestion_data.get("avg_static_duration", 0)
        }
    }
    
    # Шинжилгээ хийх
    analysis = analyzer.analyze_traffic_flow(analysis_data)
    
    # Графикууд үүсгэх
    graph_files = analyzer.generate_traffic_graphs(analysis)
    
    return {
        "graphs": [os.path.basename(f) for f in graph_files],
        "analysis": {
            "congestion_level": analysis.get("congestion_level", "unknown"),
            "risk_score": analysis.get("congestion_risk_score", 0),
            "static_distribution": analysis.get("static_vehicles_distribution", {})
        }
    }

@app.get("/api/congestion/graphs/{filename}")
async def get_graph_file(filename: str):
    """График файл татах"""
    
    file_path = os.path.join("data", "graphs", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="График файл олдсонгүй")
    
    return FileResponse(file_path)

# Эрсдлийн түвшин тодорхойлох функц
def get_risk_level(risk_score):
    """
    Эрсдлийн оноо (0-100)-н дагуу түвшин тодорхойлох
    
    Args:
        risk_score: Эрсдлийн оноо (0-100)
        
    Returns:
        level: Эрсдлийн түвшин (low, medium, high, critical)
    """
    if risk_score < 25:
        return "low"  # Бага
    elif risk_score < 50:
        return "medium"  # Дунд
    elif risk_score < 75:
        return "high"  # Өндөр
    else:
        return "critical"  # Маш өндөр

def start_api(host="0.0.0.0", port=8000):
    """API серверийг эхлүүлэх"""
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_api()