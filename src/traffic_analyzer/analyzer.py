import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import matplotlib.pyplot as plt
from collections import defaultdict

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
        
        # Зогссон хугацааны босгууд (секундээр)
        self.static_time_thresholds = {
            "short": 10,     # 10 секундээс бага
            "medium": 30,    # 10-30 секунд
            "long": 60,      # 30-60 секунд
            "very_long": 120 # 60-120 секунд
            # 120 секундээс дээш бол маш удаан
        }
        
        # Түгжрэлийн эрсдлийн оноо
        self.congestion_risk_weights = {
            "vehicles_in_roi": 0.3,        # Машины тоо
            "static_vehicles_ratio": 0.3,  # Зогссон машины харьцаа
            "max_static_duration": 0.2,    # Хамгийн удаан зогссон хугацаа
            "avg_static_duration": 0.2     # Дундаж зогссон хугацаа
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
            "time_windows": [],
            "static_vehicles_distribution": {
                "short": 0,
                "medium": 0,
                "long": 0,
                "very_long": 0,
                "extreme": 0
            },
            "congestion_risk_score": 0  # 0-100 хооронд
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

                current_time += timedelta(seconds=self.window_size // 2)

        # Дундаж түгжрэлийн түвшин
        if analysis["congestion_history"]:
            # Хамгийн их давтагдсан түгжрэлийн түвшинг сонгох
            congestion_counts = pd.Series(analysis["congestion_history"]).value_counts()
            analysis["congestion_level"] = congestion_counts.index[0]
        
        # Хэрэв дэлгэрэнгүй өгөгдөл байвал зогссон машинуудын хувиарлалтыг шинжлэх
        if "static_durations" in count_data:
            analysis["static_vehicles_distribution"] = self.analyze_static_vehicles(count_data["static_durations"])
            
        # Түгжрэлийн эрсдлийн оноог тооцоолох
        if "congestion_metrics" in count_data:
            analysis["congestion_risk_score"] = self.calculate_congestion_risk(count_data["congestion_metrics"])
            
        return analysis
    
    def analyze_static_vehicles(self, static_durations):
        """
        Зогссон машинуудын хугацааны хуваарилалтыг шинжлэх
        
        Args:
            static_durations: Зогссон машинуудын хугацаа {vehicle_id: duration}
            
        Returns:
            distribution: Хугацааны хуваарилалт
        """
        distribution = {
            "short": 0,      # 0-10 сек
            "medium": 0,     # 10-30 сек
            "long": 0,       # 30-60 сек
            "very_long": 0,  # 60-120 сек
            "extreme": 0     # >120 сек
        }
        
        for vehicle_id, duration in static_durations.items():
            if duration < self.static_time_thresholds["short"]:
                distribution["short"] += 1
            elif duration < self.static_time_thresholds["medium"]:
                distribution["medium"] += 1
            elif duration < self.static_time_thresholds["long"]:
                distribution["long"] += 1
            elif duration < self.static_time_thresholds["very_long"]:
                distribution["very_long"] += 1
            else:
                distribution["extreme"] += 1
                
        return distribution
                
    def calculate_congestion_risk(self, metrics):
        """
        Түгжрэлийн эрсдлийн оноог тооцоолох (0-100)
        
        Args:
            metrics: Түгжрэлийн метрикүүд
            
        Returns:
            risk_score: Эрсдлийн оноо (0-100)
        """
        # Машины тооны оноо (0-30)
        vehicles_score = min(30, metrics.get("vehicles_in_roi", 0) * 2)
        
        # Зогссон машины харьцаа (0-30)
        static_ratio = metrics.get("static_vehicles", 0) / max(1, metrics.get("vehicles_in_roi", 1))
        static_ratio_score = min(30, static_ratio * 100)
        
        # Хамгийн удаан зогссон хугацаа (0-20)
        max_duration = metrics.get("max_static_duration", 0)
        max_duration_score = min(20, max_duration / 6)  # 2 минут (120 сек) бол бүрэн оноо
        
        # Дундаж зогссон хугацаа (0-20)
        avg_duration = metrics.get("avg_static_duration", 0)
        avg_duration_score = min(20, avg_duration / 3)  # 1 минут (60 сек) бол бүрэн оноо
        
        # Нийт эрсдлийн оноо (0-100)
        risk_score = vehicles_score + static_ratio_score + max_duration_score + avg_duration_score
        
        return round(risk_score, 1)
        
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
    
    def generate_traffic_graphs(self, analysis, output_path=None):
        """
        Замын хөдөлгөөний шинжилгээний график үүсгэх
        
        Args:
            analysis: Шинжилгээний үр дүн
            output_path: Графикийг хадгалах зам
            
        Returns:
            output_files: Үүсгэсэн файлуудын нэр
        """
        if "error" in analysis:
            return []
            
        if output_path is None:
            output_path = os.path.join(self.data_path, "graphs")
            
        os.makedirs(output_path, exist_ok=True)
        
        output_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Цагт ногдох машины тоо
        if "time_windows" in analysis and analysis["time_windows"]:
            times = [window["start_time"] for window in analysis["time_windows"]]
            counts = [window["vehicles_per_minute"] for window in analysis["time_windows"]]
            
            plt.figure(figsize=(10, 6))
            plt.plot(times, counts, marker='o')
            plt.title('Замын хөдөлгөөний урсгал (машин/мин)')
            plt.ylabel('Машин/минут')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            flow_file = os.path.join(output_path, f"traffic_flow_{timestamp}.png")
            plt.savefig(flow_file)
            plt.close()
            output_files.append(flow_file)
            
        # 2. Зогссон машины хуваарилалт (pie chart)
        if "static_vehicles_distribution" in analysis:
            dist = analysis["static_vehicles_distribution"]
            labels = ["Бага (0-10с)", "Дунд (10-30с)", "Урт (30-60с)", "Маш урт (60-120с)", "Хэт удаан (>120с)"]
            values = [dist["short"], dist["medium"], dist["long"], dist["very_long"], dist["extreme"]]
            
            # Тэг биш утгыг л харуулах
            non_zero_labels = [label for i, label in enumerate(labels) if values[i] > 0]
            non_zero_values = [value for value in values if value > 0]
            
            if non_zero_values:
                plt.figure(figsize=(8, 8))
                plt.pie(non_zero_values, labels=non_zero_labels, autopct='%1.1f%%')
                plt.title('Зогссон машинуудын хуваарилалт')
                plt.tight_layout()
                
                static_file = os.path.join(output_path, f"static_vehicles_{timestamp}.png")
                plt.savefig(static_file)
                plt.close()
                output_files.append(static_file)
                
        return output_files
        
    def get_current_congestion_level(self, count_data=None):
        """
        Одоогийн түгжрэлийн түвшинг авах
        
        Args:
            count_data: Машин тоолсон өгөгдөл (None бол файлаас ачаална)
            
        Returns:
            level: Түгжрэлийн түвшин (low, medium, high, very_high)
            vehicles_per_minute: Минутад тоологдсон машины тоо
            risk_score: Түгжрэлийн эрсдлийн оноо (0-100)
        """
        analysis = self.analyze_traffic_flow(count_data)
        
        if "error" in analysis:
            return "unknown", 0, 0
            
        # Хамгийн сүүлийн цонхны мэдээлэл
        if analysis["time_windows"]:
            last_window = analysis["time_windows"][-1]
            return last_window["congestion_level"], last_window["vehicles_per_minute"], analysis.get("congestion_risk_score", 0)
            
        return "unknown", 0, 0 