import argparse
import logging
from api import start_api
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import base64
import cv2
import numpy as np
import time
import asyncio
import os
from vehicle_counter_service import VehicleCounterService

# Set headless mode by default for server environment
os.environ['HEADLESS'] = '1'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("vehicle_counter_api")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create socket.io instance with explicit cors
sio = socketio.AsyncServer(
    async_mode='asgi', 
    cors_allowed_origins=['http://localhost:3000', 'http://localhost:8000', '*'],
    logger=True,
    engineio_logger=True,
    allow_upgrades=True
)
socket_app = socketio.ASGIApp(sio, app)

# Global variables to store the vehicle counter service and frame data
vehicle_counter = None
latest_frame = None
latest_detection_data = None
processing_active = False

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    # Send the current status to the newly connected client
    if processing_active:
        await sio.emit('processing_status', {'active': True}, room=sid)
    else:
        await sio.emit('processing_status', {'active': False}, room=sid)

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def start_detection(sid, data):
    global vehicle_counter, processing_active
    if not processing_active:
        processing_active = True
        await sio.emit('processing_status', {'active': True})
        
        # Start the vehicle detection in a separate thread
        video_path = data.get('video_path', None)
        
        # Check if custom zones are provided
        custom_zones = data.get('custom_zones', None)
        
        # Initialize vehicle counter with custom zones if provided
        vehicle_counter = VehicleCounterService(
            video_path=video_path,
            model_path="yolov8s.pt",
            device="cpu",
            output_path="data",
            custom_zones=custom_zones
        )
        
        # Run the detection process in a separate task
        asyncio.create_task(run_detection())
        
        return {'status': 'success', 'message': 'Vehicle detection started'}
    else:
        return {'status': 'error', 'message': 'Detection already running'}

@sio.event
async def stop_detection(sid):
    global vehicle_counter, processing_active
    if processing_active and vehicle_counter:
        vehicle_counter.stop_counting()
        processing_active = False
        await sio.emit('processing_status', {'active': False})
        return {'status': 'success', 'message': 'Vehicle detection stopped'}
    else:
        return {'status': 'error', 'message': 'No detection running'}

async def run_detection():
    global vehicle_counter, latest_frame, latest_detection_data, processing_active
    
    # Initialize the detector with modified start_counting function
    def frame_callback(frame, detection_data):
        global latest_frame, latest_detection_data
        latest_frame = frame
        latest_detection_data = detection_data
    
    # Start the vehicle counter with our callback
    success = await asyncio.to_thread(
        start_detection_process, 
        vehicle_counter,
        frame_callback
    )
    
    if not success:
        processing_active = False
        await sio.emit('processing_status', {'active': False})
        await sio.emit('detection_error', {'message': 'Detection process failed to start'})

def start_detection_process(counter, callback):
    """Custom function to start detection and pass frames to callback"""
    if not counter._setup_zones():
        return False
    
    if len(counter.zone_manager.zones) == 0:
        print("No zones configured. Process finished.")
        return False
    
    if not counter._open_video_capture():
        print("Failed to open video or camera.")
        return False
    
    counter.processing = True
    counter.frame_count = 0
    counter.start_time = time.time()
    
    try:
        while counter.cap.isOpened() and counter.processing:
            ret, frame = counter.cap.read()
            if not ret:
                break
            
            counter.frame_count += 1
            current_time = time.time()
            
            # Detect vehicles
            detections = counter.detector.detect_vehicles(frame)
            
            # Process detections format
            if isinstance(detections, tuple) and len(detections) == 3:
                boxes, scores, class_ids = detections
            else:
                boxes = []
                scores = []
                class_ids = []
                
                if detections:
                    for det in detections:
                        if isinstance(det, dict) and 'box' in det:
                            x1, y1, x2, y2 = det['box']
                            boxes.append([x1, y1, x2, y2])
                            scores.append(det.get('confidence', 1.0))
                            class_ids.append(det.get('class_id', 0))
            
            # Track vehicles
            try:
                tracked_objects, zone_vehicles = counter.tracker.track_vehicles(
                    frame, boxes, scores, class_ids, counter.zone_manager.zones
                )
            except Exception as e:
                print(f"Tracking error: {e}")
                tracked_objects = []
                zone_vehicles = {}
            
            # Update statistics
            for zone in counter.zone_manager.zones:
                zone.update_statistics()
            
            # Draw zones and tracked objects
            frame_with_viz = frame.copy()
            frame_with_viz = counter.zone_manager.draw_zones(frame_with_viz)
            
            for obj in tracked_objects:
                x1, y1, x2, y2 = obj["bbox"]
                track_id = obj["id"]
                
                cv2.rectangle(frame_with_viz, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame_with_viz, f"ID: {track_id}", (x1, y1 - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            # Get congestion status
            congestion_status = counter.get_congestion_status()
            
            # Prepare detection data to send to clients
            detection_data = {
                'frame_count': counter.frame_count,
                'fps': counter.frame_count / (current_time - counter.start_time) if current_time > counter.start_time else 0,
                'tracked_objects': len(tracked_objects),
                'congestion_status': congestion_status,
                'zones': []
            }
            
            for zone in counter.zone_manager.zones:
                zone_data = {
                    'id': zone.id,
                    'name': zone.name,
                    'count': zone.get_display_count(),
                    'is_stalled': zone.is_stalled,
                }
                detection_data['zones'].append(zone_data)
            
            # Call the callback with the processed frame and detection data
            callback(frame_with_viz, detection_data)
            
            # Sleep to reduce CPU usage
            time.sleep(0.03)  # Adjust for desired frame rate
            
    except Exception as e:
        print(f"Process stopped with error: {e}")
        return False
    finally:
        counter.processing = False
        counter._close_video_capture()
        cv2.destroyAllWindows()
        return True

async def send_frames():
    """Task to send processed frames to connected clients"""
    global latest_frame, latest_detection_data, processing_active
    
    while True:
        # Only send if processing is active and we have data
        if processing_active and latest_frame is not None and latest_detection_data is not None:
            try:
                # Convert frame to JPEG
                _, buffer = cv2.imencode('.jpg', latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                # Convert to base64 string
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                # Emit the frame and detection data to all connected clients
                await sio.emit('frame', {
                    'image': frame_b64,
                    'detection_data': latest_detection_data
                })
            except Exception as e:
                print(f"Error sending frame: {e}")
        
        # Sleep to maintain reasonable frame rate (adjust as needed)
        await asyncio.sleep(0.1)  # 10 FPS

async def start_server():
    """
    Starts the frame sending task and the server
    """
    # Start frame sending task
    frame_sender = asyncio.create_task(send_frames())
    
    # Configure server
    config = uvicorn.Config(
        app=socket_app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    
    # Start server
    server = uvicorn.Server(config)
    await server.serve()
    
    # This will run after server is stopped
    frame_sender.cancel()
    try:
        await frame_sender
    except asyncio.CancelledError:
        print("Frame sender task cancelled")

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
    
    # Run the server using asyncio
    asyncio.run(start_server())


if __name__ == "__main__":
    main() 