import argparse
import logging
from api import start_api_server
import socketio
from fastapi import FastAPI
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("vehicle_counter_api")

app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

# Холбогдсон Socket.IO event-үүд энд бичигдэнэ

def main():
    """
    Тээврийн хэрэгсэл тоолох API серверийг ажиллуулах
    """
    parser = argparse.ArgumentParser(description="Тээврийн хэрэгсэл тоолох API сервер")
    
    parser.add_argument("--host", type=str, default="0.0.0.0",
                       help="Хост нэр эсвэл IP хаяг")
    
    parser.add_argument("--port", type=int, default=8000,
                       help="Порт дугаар")
    
    args = parser.parse_args()
    
    logger.info(f"API сервер эхлүүлж байна {args.host}:{args.port}")
    
    uvicorn.run(socket_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main() 