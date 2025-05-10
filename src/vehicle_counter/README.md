# Vehicle Counter Service

Тээврийн хэрэгсэл тоолох, түгжрэлийн түвшин тодорхойлох сервис

## Сервисийн агуулга

- VehicleDetector: YOLOv8 ашиглан тээврийн хэрэгсэл илрүүлэх болон объект мөрдөх
- VehicleCounter: Тээврийн хэрэгсэл тоолох, түгжрэлийн түвшинг тодорхойлох
- VehicleCounterService: Видео боловсруулалт хийх үндсэн сервис
- API: FastAPI ашиглан сервис ажиллуулах, өгөгдөл дамжуулах API

## Шаардлагатай сан суулгах

```bash
pip install ultralytics opencv-python deep-sort-realtime fastapi uvicorn
```

## Ашиглах зааварчилгаа

### Python програмаас ашиглах

```python
from vehicle_counter import VehicleCounterService

# Сервис үүсгэх
counter_service = VehicleCounterService(
    video_path="video.mp4",  # None бол камера ашиглана
    model_path="yolov8s.pt",
    device="cpu",            # cpu, cuda, mps сонгох
    output_path="data"       # Гаралтын өгөгдлийн зам
)

# Тоолох процесс эхлүүлэх
counter_service.start_counting(
    display=True,           # Видео харуулах эсэх
    save_data=True,         # Өгөгдөл хадгалах эсэх
    save_video=False        # Боловсруулсан видео хадгалах эсэх
)
```

### API сервисээр ашиглах

```python
import uvicorn
from vehicle_counter import api_app

# API сервер эхлүүлэх
uvicorn.run(api_app, host="0.0.0.0", port=8000)
```

## API Endpoints

- `GET /api/congestion/current` - Одоогийн түгжрэлийн мэдээлэл авах
- `POST /api/vehicle-counter/start` - Шинэ тоолох процесс эхлүүлэх
- `GET /api/vehicle-counter/status` - Тоолох процессийн төлөв авах 
- `GET /api/vehicle-counter/videos` - Боломжит видеоны жагсаалт авах

## Жишээ код

### Шинэ процесс эхлүүлэх

```python
import requests

response = requests.post(
    "http://localhost:8000/api/vehicle-counter/start",
    json={
        "video_path": "video.mp4",
        "model_path": "yolov8s.pt",
        "device": "cpu",
        "display": True,
        "save_data": True,
        "location": "Баянзүрх дүүрэг"
    }
)
print(response.json())
```

### Түгжрэлийн мэдээлэл авах

```python
import requests

response = requests.get("http://localhost:8000/api/congestion/current")
data = response.json()
print(data)
``` 