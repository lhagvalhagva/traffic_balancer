import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

class TrafficAnalyzer:
    def __init__(self, data_path="data", window_size=60):
        """
        Замын хөдөлгөөний дүн шинжилгээний модуль
        
        Args:
            data_path: Тоолсон өгөгдлийн зам
            window_size: Дүн шинжилгээний цонхны хэмжээ (секунд)
        """
        self.data_path = data_path
        self.window_size = window_size
        self.congestion_thresholds = {
            "low": 5,       # 1 минутад 5-аас бага машин
            "medium": 10,   # 1 минутад 5-10 машин
            "high": 20      # 1 минутад 10-20 машин
            # 20-оос дээш машин бол маш өндөр түгжрэл
        }
        
    def load_count_data(self, filename=None):
        """
        Тоолсон өгөгдлийг ачаалах
        
        Args:
            filename: Тодорхой файлын нэр (None бол хамгийн сүүлийн файл)
            
        Returns:
            data: Ачаалсан өгөгдөл
        """
        if filename:
            file_path = os.path.join(self.data_path, filename)
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            # Хамгийн сүүлийн файлыг олох
            json_files = [f for f in os.listdir(self.data_path) if f.startswith('vehicle_count_') and f.endswith('.json')]
            if not json_files:
                return None
            
            latest_file = max(json_files, key=lambda f: os.path.getmtime(os.path.join(self.data_path, f)))
            with open(os.path.join(self.data_path, latest_file), 'r') as f:
                return json.load(f)
    
    def analyze_traffic_flow(self, count_data=None):
        """
        Замын хөдөлгөөний урсгалыг шинжлэх
        
        Args:
            count_data: Машин тоолсон өгөгдөл (None бол файлаас ачаална)
            
        Returns:
            analysis: Шинжилгээний үр дүн
        """
        if count_data is None:
            count_data = self.load_count_data()
            
        if count_data is None or "counts" not in count_data or not count_data["counts"]:
            return {"error": "Өгөгдөл олдсонгүй эсвэл хоосон байна"}
            
        # Өгөгдлийг DataFrame болгох
        df = pd.DataFrame(count_data["counts"])
        
        # Хугацааг datetime болгох
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Шинжилгээний үр дүн
        analysis = {
            "location": count_data.get("location", "Unknown"),
            "start_time": count_data.get("start_time", ""),
            "end_time": count_data.get("end_time", ""),
            "total_duration_seconds": count_data.get("duration", 0),
            "total_vehicles": count_data.get("total_count", 0),
            "average_flow_rate": 0,
            "peak_flow_time": "",
            "peak_flow_count": 0,
            "congestion_level": "",
            "congestion_history": [],
            "time_windows": []
        }
        
        # Нийт урсгалын дундаж (машин/мин)
        total_minutes = analysis["total_duration_seconds"] / 60
        if total_minutes > 0:
            analysis["average_flow_rate"] = analysis["total_vehicles"] / total_minutes
            
        # Цонхоор хөдөлгөөнийг шинжлэх (машин/мин)
        if len(df) > 0:
            # Хугацааны цонхоор бүлэглэх (sliding window)
            min_time = df['timestamp'].min()
            max_time = df['timestamp'].max()
            
            current_time = min_time
            window_size_td = timedelta(seconds=self.window_size)
            
            while current_time <= max_time:
                window_end = current_time + window_size_td
                window_vehicles = df[(df['timestamp'] >= current_time) & 
                                    (df['timestamp'] < window_end)]
                
                count = len(window_vehicles)
                vehicles_per_minute = count / (self.window_size / 60)
                
                # Түгжрэлийн түвшин тодорхойлох
                congestion_level = "very_high"
                if vehicles_per_minute < self.congestion_thresholds["low"]:
                    congestion_level = "low"
                elif vehicles_per_minute < self.congestion_thresholds["medium"]:
                    congestion_level = "medium"
                elif vehicles_per_minute < self.congestion_thresholds["high"]:
                    congestion_level = "high"
                
                window_data = {
                    "start_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": window_end.strftime("%Y-%m-%d %H:%M:%S"),
                    "vehicle_count": count,
                    "vehicles_per_minute": vehicles_per_minute,
                    "congestion_level": congestion_level
                }
                
                analysis["time_windows"].append(window_data)
                analysis["congestion_history"].append(congestion_level)
                
                # Оргил түгжрэлийг шинэчлэх
                if count > analysis["peak_flow_count"]:
                    analysis["peak_flow_count"] = count
                    analysis["peak_flow_time"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                    
                current_time += timedelta(seconds=self.window_size // 2)  # 50% overlap
        
        # Дундаж түгжрэлийн түвшин
        if analysis["congestion_history"]:
            # Хамгийн их давтагдсан түгжрэлийн түвшинг сонгох
            congestion_counts = pd.Series(analysis["congestion_history"]).value_counts()
            analysis["congestion_level"] = congestion_counts.index[0]
            
        return analysis
        
    def save_analysis(self, analysis, filename=None):
        """
        Шинжилгээний үр дүнг хадгалах
        
        Args:
            analysis: Шинжилгээний үр дүн
            filename: Хадгалах файлын нэр (None бол автоматаар үүсгэнэ)
            
        Returns:
            filename: Хадгалсан файлын нэр
        """
        os.makedirs(self.data_path, exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"traffic_analysis_{timestamp}.json"
            
        file_path = os.path.join(self.data_path, filename)
        
        with open(file_path, 'w') as f:
            json.dump(analysis, f, indent=4)
            
        return filename
        
    def get_current_congestion_level(self, count_data=None):
        """
        Одоогийн түгжрэлийн түвшинг авах
        
        Args:
            count_data: Машин тоолсон өгөгдөл (None бол файлаас ачаална)
            
        Returns:
            level: Түгжрэлийн түвшин (low, medium, high, very_high)
            vehicles_per_minute: Минутад тоологдсон машины тоо
        """
        analysis = self.analyze_traffic_flow(count_data)
        
        if "error" in analysis:
            return "unknown", 0
            
        # Хамгийн сүүлийн цонхны мэдээлэл
        if analysis["time_windows"]:
            last_window = analysis["time_windows"][-1]
            return last_window["congestion_level"], last_window["vehicles_per_minute"]
            
        return "unknown", 0 