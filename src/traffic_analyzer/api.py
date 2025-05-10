from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime

from .analyzer import TrafficAnalyzer

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

@app.get("/api/congestion/current", response_model=CongestionResponse)
def get_current_congestion():
    """Одоогийн түгжрэлийн түвшинг авах"""
    level, rate = analyzer.get_current_congestion_level()
    
    if level == "unknown":
        raise HTTPException(status_code=404, detail="Түгжрэлийн мэдээлэл олдсонгүй")
        
    # Сүүлийн шинжилгээний мэдээллийг авах
    analysis = analyzer.analyze_traffic_flow()
    
    return {
        "congestion_level": level,
        "vehicles_per_minute": rate,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "location": analysis.get("location", "Unknown")
    }

@app.post("/api/analysis/upload", response_model=TrafficAnalysisResponse)
def upload_count_data(data: CountDataUpload):
    """
    Машин тоолсон өгөгдлийг хүлээн авч шинжилгээ хийх
    """
    analysis = analyzer.analyze_traffic_flow(data.count_data)
    
    if "error" in analysis:
        raise HTTPException(status_code=400, detail=analysis["error"])
        
    # Шинжилгээг хадгалах
    analyzer.save_analysis(analysis)
    
    return analysis

@app.get("/api/analysis/history")
def get_analysis_history():
    """
    Шинжилгээний түүхийг авах
    """
    try:
        data_path = analyzer.data_path
        json_files = [f for f in os.listdir(data_path) if f.startswith('traffic_analysis_') and f.endswith('.json')]
        
        history = []
        for file in sorted(json_files, key=lambda f: os.path.getmtime(os.path.join(data_path, f)), reverse=True):
            with open(os.path.join(data_path, file), 'r') as f:
                analysis = json.load(f)
                history.append({
                    "filename": file,
                    "timestamp": file.split("_")[2].split(".")[0],
                    "congestion_level": analysis.get("congestion_level", "unknown"),
                    "total_vehicles": analysis.get("total_vehicles", 0),
                    "location": analysis.get("location", "Unknown")
                })
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def start_api(host="0.0.0.0", port=8000):
    """API серверийг эхлүүлэх"""
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_api() 