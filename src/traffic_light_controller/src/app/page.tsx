'use client';

import { useState, useEffect, useRef } from 'react';
import { useSocket } from '@/lib/socketio';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import dynamic from 'next/dynamic';
import TrafficLight from '@/components/TrafficLight';
import { Tab } from '@/components/ui/Tab';
import Image from 'next/image';
import io from 'socket.io-client';

const MapComponent = dynamic(() => import('@/components/Map'), { ssr: false });

interface CrossroadItem {
  id: number;
  name: string;
}

interface DistrictItem {
  id: number;
  name: string;
}

interface CameraItem {
  id: number;
  name: string;
  status: 'online' | 'offline';
  streamUrl: string;
  thumbnail: string;
}

interface DetectionData {
  frame_count: number;
  fps: number;
  tracked_objects: number;
  congestion_status: {
    level: string;
    message: string;
  };
  zones: {
    id: number;
    name: string;
    count: number;
    is_stalled: boolean;
  }[];
}

// Add new interfaces for zone drawing
interface Point {
  x: number;
  y: number;
}

interface Zone {
  points: Point[];
  name: string;
  type: 'COUNT' | 'SUM';
}

// Районы и перекрестки - данные для примера
const districts: DistrictItem[] = [
  { id: 1, name: 'Сүхбаатар' },
  { id: 2, name: 'Баянгол' },
  { id: 3, name: 'Баянзүрх' },
  { id: 4, name: 'Чингэлтэй' },
  { id: 5, name: 'Хан-Уул' },
  { id: 6, name: 'Сонгинохайрхан' },
  { id: 7, name: 'Налайх' },
  { id: 8, name: 'Багануур' }
];

const crossroads: Record<number, CrossroadItem[]> = {
  1: [
    { id: 101, name: 'Баруун 4 замын уулзвар' },
    { id: 102, name: 'Дугуйн худалдааны төв' },
    { id: 103, name: 'Их сургуулийн уулзвар' }
  ],
  2: [
    { id: 201, name: '3-р эмнэлгийн уулзвар' },
    { id: 202, name: 'Баянголын товчоо' }
  ],
  3: [
    { id: 301, name: 'Дүнжингарав' },
    { id: 302, name: '13-р хороолол' }
  ],
  4: [
    { id: 401, name: 'Ард кино театр' },
    { id: 402, name: 'Чингэлтэй зах' }
  ],
  5: [
    { id: 501, name: 'Их тойруу' },
    { id: 502, name: 'Зайсан' }
  ],
  6: [
    { id: 601, name: 'Толгойт' },
    { id: 602, name: 'Баруун 4 зам' }
  ],
  7: [
    { id: 701, name: 'Налайх товчоо' }
  ],
  8: [
    { id: 801, name: 'Багануур товчоо' }
  ]
};

// Пример камер для просмотра
const cameras: CameraItem[] = [
  {
    id: 1,
    name: 'Баруун 4 замын уулзвар',
    status: 'online',
    streamUrl: '/videos/road1.mp4',
    thumbnail: '/videos/thumbnails/road1.png'
  },
  {
    id: 2,
    name: 'Энх тайвны өргөн чөлөө',
    status: 'online',
    streamUrl: '/videos/road2.mp4',
    thumbnail: '/videos/thumbnails/road2.png'
  },
  {
    id: 3,
    name: 'Их тойруу',
    status: 'online',
    streamUrl: '/videos/road3.mp4', 
    thumbnail: '/videos/thumbnails/road3.png'
  }
];

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();
  const { trafficLights, sendManualControl, isConnected } = useSocket();
  
  const [selectedLight, setSelectedLight] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('traffic');
  const [autoAdjust, setAutoAdjust] = useState(false);
  
  // Socket.IO for vehicle detection
  const [detectionSocket, setDetectionSocket] = useState<any>(null);
  const [detectionActive, setDetectionActive] = useState(false);
  const [currentFrame, setCurrentFrame] = useState<string | null>(null);
  const [detectionData, setDetectionData] = useState<DetectionData | null>(null);
  const [loadingDetection, setLoadingDetection] = useState(false);
  
  // Выбранные значения
  const [selectedDistrict, setSelectedDistrict] = useState<number>(1);
  const [selectedCrossroad, setSelectedCrossroad] = useState<number>(101); // Баруун 4 замын уулзвар по умолчанию
  const [selectedCamera, setSelectedCamera] = useState<number>(1);
  const [videoPlaying, setVideoPlaying] = useState(false);
  
  // Add new state for zone drawing
  const [isDrawingMode, setIsDrawingMode] = useState(false);
  const [currentZone, setCurrentZone] = useState<Point[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [showZoneTypeSelector, setShowZoneTypeSelector] = useState(false);
  const [zonePreviewImage, setZonePreviewImage] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) {
      router.push('/login');
    }
  }, [user]);

  useEffect(() => {
    // Connect to the Socket.IO server with specific options
    const socket = io('http://localhost:8000', {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      timeout: 30000,
      extraHeaders: {
        'Origin': 'http://localhost:3000'
      }
    });

    socket.on('connect', () => {
      console.log('Connected to detection server');
      setDetectionSocket(socket);
    });

    socket.on('connect_error', (error) => {
      console.error('Connection error:', error);
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from detection server');
      setDetectionActive(false);
      setCurrentFrame(null);
      setDetectionData(null);
    });

    socket.on('processing_status', (data: { active: boolean }) => {
      setDetectionActive(data.active);
      setLoadingDetection(false);
    });

    socket.on('frame', (data: { image: string, detection_data: DetectionData }) => {
      setCurrentFrame(`data:image/jpeg;base64,${data.image}`);
      setDetectionData(data.detection_data);
    });

    socket.on('detection_error', (data: { message: string }) => {
      console.error('Detection error:', data.message);
      setLoadingDetection(false);
      setDetectionActive(false);
    });

    return () => {
      // Clean up the socket connection when component unmounts
      socket.disconnect();
    };
  }, []);

  if (!user) return null;

  const handleLightControl = (lightId: string, data: { state?: string; autoControl?: boolean }) => {
    sendManualControl(lightId, data);
  };

  const handleSelectLight = (lightId: string) => {
    setSelectedLight(lightId);
  };
  
  const handleDistrictChange = (districtId: number) => {
    setSelectedDistrict(districtId);
    // Выбираем первый перекресток в выбранном районе
    if (crossroads[districtId] && crossroads[districtId].length > 0) {
      setSelectedCrossroad(crossroads[districtId][0].id);
    }
  };
  
  const handleCrossroadChange = (crossroadId: number) => {
    setSelectedCrossroad(crossroadId);
  };

  const handleCameraSelect = (cameraId: number) => {
    setSelectedCamera(cameraId);
    setVideoPlaying(false);
  };

  // Add function to handle canvas click for drawing zones
  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawingMode) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // Add point to current zone
    setCurrentZone([...currentZone, { x, y }]);
    
    // Redraw zones
    drawZones();
  };
  
  // Add function to finish current zone
  const finishCurrentZone = () => {
    if (currentZone.length < 3) {
      alert('Дор хаяж 3 цэг сонгох шаардлагатай!');
      return;
    }
    
    // Generate preview image
    if (canvasRef.current) {
      const dataUrl = canvasRef.current.toDataURL();
      setZonePreviewImage(dataUrl);
    }
    
    // Show zone type selector
    setShowZoneTypeSelector(true);
  };
  
  // Add function to save zone with type
  const saveZoneWithType = (type: 'COUNT' | 'SUM') => {
    if (currentZone.length < 3) return;
    
    const zoneName = `Зон ${zones.length + 1}`;
    const newZone: Zone = {
      points: [...currentZone],
      name: zoneName,
      type
    };
    
    setZones([...zones, newZone]);
    setCurrentZone([]);
    setShowZoneTypeSelector(false);
    setZonePreviewImage(null);
  };
  
  // Add function to cancel zone drawing
  const cancelZoneDrawing = () => {
    setCurrentZone([]);
    setIsDrawingMode(false);
    setShowZoneTypeSelector(false);
    setZonePreviewImage(null);
  };
  
  // Add function to draw zones on canvas
  const drawZones = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw saved zones
    zones.forEach((zone, index) => {
      ctx.beginPath();
      ctx.moveTo(zone.points[0].x, zone.points[0].y);
      
      for (let i = 1; i < zone.points.length; i++) {
        ctx.lineTo(zone.points[i].x, zone.points[i].y);
      }
      
      ctx.closePath();
      ctx.fillStyle = zone.type === 'COUNT' ? 'rgba(0, 255, 0, 0.2)' : 'rgba(255, 165, 0, 0.2)';
      ctx.fill();
      ctx.strokeStyle = zone.type === 'COUNT' ? 'rgba(0, 255, 0, 0.8)' : 'rgba(255, 165, 0, 0.8)';
      ctx.lineWidth = 2;
      ctx.stroke();
      
      // Draw zone name
      const centerX = zone.points.reduce((sum, point) => sum + point.x, 0) / zone.points.length;
      const centerY = zone.points.reduce((sum, point) => sum + point.y, 0) / zone.points.length;
      
      ctx.fillStyle = 'white';
      ctx.font = '14px Arial';
      ctx.textAlign = 'center';
      ctx.fillText(zone.name, centerX, centerY);
      ctx.fillText(zone.type, centerX, centerY + 20);
    });
    
    // Draw current zone being created
    if (currentZone.length > 0 && isDrawingMode) {
      ctx.beginPath();
      ctx.moveTo(currentZone[0].x, currentZone[0].y);
      
      for (let i = 1; i < currentZone.length; i++) {
        ctx.lineTo(currentZone[i].x, currentZone[i].y);
      }
      
      if (currentZone.length > 2) {
        ctx.lineTo(currentZone[0].x, currentZone[0].y);
      }
      
      ctx.strokeStyle = 'rgba(255, 0, 0, 0.8)';
      ctx.lineWidth = 2;
      ctx.stroke();
      
      // Draw points
      currentZone.forEach(point => {
        ctx.beginPath();
        ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
        ctx.fillStyle = 'red';
        ctx.fill();
      });
    }
  };
  
  // Update canvas size when active tab changes
  useEffect(() => {
    if (activeTab === 'camera' && videoContainerRef.current && canvasRef.current) {
      const container = videoContainerRef.current;
      const canvas = canvasRef.current;
      
      canvas.width = container.offsetWidth;
      canvas.height = container.offsetHeight;
      
      drawZones();
    }
  }, [activeTab, videoContainerRef.current?.offsetWidth, videoContainerRef.current?.offsetHeight]);
  
  // Redraw zones whenever they change
  useEffect(() => {
    drawZones();
  }, [currentZone, zones]);
  
  // Modified handleToggleDetection to include zones
  const handleToggleDetection = () => {
    if (!detectionSocket) {
      console.error('Socket connection not available');
      return;
    }
    
    if (detectionActive) {
      // Stop the detection
      setLoadingDetection(true);
      detectionSocket.emit('stop_detection', (response: any) => {
        console.log('Stop detection response:', response);
        setLoadingDetection(false);
      });
    } else {
      // Start the detection
      setLoadingDetection(true);
      
      // Send zones along with video path to the backend
      detectionSocket.emit('start_detection', { 
        video_path: 'viiddeo.mov', // Сервер талд байгаа видео файл
        custom_zones: zones.length > 0 ? zones.map(zone => ({
          points: zone.points,
          name: zone.name,
          type: zone.type
        })) : undefined
      }, (response: any) => {
        console.log('Start detection response:', response);
        if (response && response.status === 'error') {
          console.error("Error starting detection:", response.message);
          setLoadingDetection(false);
        } else {
          console.log("Detection started successfully");
        }
      });
    }
  };

  const visibleLights = selectedLight
    ? trafficLights.filter(light => light.id === selectedLight)
    : trafficLights;
    
  // Находим выбранный район и перекресток
  const selectedDistrictObj = districts.find(d => d.id === selectedDistrict);
  const selectedCrossroadObj = crossroads[selectedDistrict]?.find(c => c.id === selectedCrossroad);
  const selectedCameraObj = cameras.find(c => c.id === selectedCamera);

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <div className="flex">
          <Tab 
            isActive={activeTab === 'traffic'} 
            onClick={() => setActiveTab('traffic')}
          >
            Замын хөдөлгөөн
          </Tab>
          <Tab 
            isActive={activeTab === 'camera'} 
            onClick={() => setActiveTab('camera')}
          >
            Камер харах
          </Tab>
        </div>
      </div>

      <div className="flex">
        <div className="w-2/3 pr-4">
          {activeTab === 'traffic' && (
        <MapComponent trafficLights={trafficLights} onSelectLight={handleSelectLight} />
          )}
          
          {activeTab === 'camera' && (
            <div className="h-full bg-white rounded-lg p-4 flex flex-col">
              <div ref={videoContainerRef} className="relative h-96 bg-black rounded-lg overflow-hidden mb-4">
                {/* Canvas overlay for zone drawing */}
                <canvas
                  ref={canvasRef}
                  className={`absolute top-0 left-0 w-full h-full z-10 ${isDrawingMode ? 'cursor-crosshair' : ''}`}
                  onClick={handleCanvasClick}
                />
                
                {detectionActive && currentFrame ? (
                  // Show detection results
                  <div className="relative w-full h-full">
                    <img 
                      src={currentFrame}
                      alt="Live detection"
                      className="w-full h-full object-contain"
                    />
                    {detectionData && (
                      <div className="absolute top-2 left-2 bg-black bg-opacity-50 text-white p-2 rounded text-sm">
                        <div>FPS: {detectionData.fps.toFixed(1)}</div>
                        <div>Tracked: {detectionData.tracked_objects}</div>
                        <div className={`font-bold ${
                          detectionData.congestion_status.level === 'High' ? 'text-red-500' : 
                          detectionData.congestion_status.level === 'Medium' ? 'text-yellow-500' : 'text-green-500'
                        }`}>
                          {detectionData.congestion_status.level}
                        </div>
                      </div>
                    )}
                  </div>
                ) : videoPlaying && !detectionActive ? (
                  // Show normal video playback
                  <video 
                    src={selectedCameraObj?.streamUrl} 
                    className="w-full h-full object-contain"
                    controls
                    autoPlay
                  />
                ) : (
                  // Show thumbnail with play button
                  <div className="relative w-full h-full flex items-center justify-center">
                    <img 
                      src={selectedCameraObj?.thumbnail} 
                      alt={selectedCameraObj?.name}
                      className="w-full h-full object-cover opacity-70"
                    />
                    <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-4">
                      <button 
                        className="bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-colors"
                        onClick={() => setVideoPlaying(true)}
                        disabled={detectionActive || loadingDetection || isDrawingMode}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="white">
                          <path d="M8 5v14l11-7z" />
                        </svg>
                      </button>
                      
                      {/* Add new zone drawing controls */}
                      <div className="flex gap-2 mb-2">
                        {isDrawingMode ? (
                          <>
                            <button
                              className="px-4 py-2 rounded-md text-white bg-green-500 hover:bg-green-600"
                              onClick={finishCurrentZone}
                              disabled={currentZone.length < 3}
                            >
                              Дуусгах
                            </button>
                            <button
                              className="px-4 py-2 rounded-md text-white bg-red-500 hover:bg-red-600"
                              onClick={cancelZoneDrawing}
                            >
                              Цуцлах
                            </button>
                          </>
                        ) : (
                          <button
                            className="px-4 py-2 rounded-md text-white bg-blue-500 hover:bg-blue-600"
                            onClick={() => setIsDrawingMode(true)}
                            disabled={detectionActive || loadingDetection}
                          >
                            Бүс зурах
                          </button>
                        )}
                        
                        {zones.length > 0 && (
                          <button
                            className="px-4 py-2 rounded-md text-white bg-red-500 hover:bg-red-600"
                            onClick={() => setZones([])}
                            disabled={detectionActive || loadingDetection || isDrawingMode}
                          >
                            Бүс устгах
                          </button>
                        )}
                      </div>
                      
                      <button
                        className={`px-4 py-2 rounded-md text-white ${
                          detectionActive ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'
                        } ${loadingDetection || isDrawingMode ? 'opacity-50 cursor-not-allowed' : ''}`}
                        onClick={handleToggleDetection}
                        disabled={loadingDetection || isDrawingMode}
                      >
                        {loadingDetection ? 'Уншиж байна...' : detectionActive ? 'Зогсоох' : 'Тээврийн хэрэгсэл илрүүлэх'}
                      </button>
                    </div>
                  </div>
                )}
                
                {/* Zone type selector modal */}
                {showZoneTypeSelector && zonePreviewImage && (
                  <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center z-20">
                    <div className="bg-white p-5 rounded-lg max-w-md w-full">
                      <h3 className="text-lg font-bold mb-3">Бүсийн төрлийг сонгоно уу</h3>
                      
                      <div className="mb-4">
                        <img 
                          src={zonePreviewImage} 
                          alt="Зоны урьдчилсан харагдац" 
                          className="w-full h-40 object-contain border"
                        />
                      </div>
                      
                      <div className="grid grid-cols-2 gap-3 mb-4">
                        <button
                          className="bg-green-500 text-white py-2 px-4 rounded"
                          onClick={() => saveZoneWithType('COUNT')}
                        >
                          Тоолох (COUNT)
                        </button>
                        <button
                          className="bg-orange-500 text-white py-2 px-4 rounded"
                          onClick={() => saveZoneWithType('SUM')}
                        >
                          Нэмэх (SUM)
                        </button>
                      </div>
                      
                      <div className="text-sm text-gray-600 mb-4">
                        <p><strong>Тоолох:</strong> Бүс дундуур өнгөрсөн тээврийн хэрэгслийг тоолно</p>
                        <p><strong>Нэмэх:</strong> Бүс доторх тээврийн хэрэгслийн тоог харуулна</p>
                      </div>
                      
                      <button
                        className="bg-gray-500 text-white py-2 px-4 rounded w-full"
                        onClick={cancelZoneDrawing}
                      >
                        Цуцлах
                      </button>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="grid grid-cols-3 gap-4">
                {cameras.map(camera => (
                  <div 
                    key={camera.id}
                    className={`relative cursor-pointer rounded-lg overflow-hidden ${
                      selectedCamera === camera.id ? 'ring-2 ring-blue-500' : ''
                    }`}
                    onClick={() => handleCameraSelect(camera.id)}
                  >
                    <img 
                      src={camera.thumbnail} 
                      alt={camera.name}
                      className="w-full h-32 object-cover"
                    />
                    <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 p-2">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm truncate">{camera.name}</span>
                        <span className={`ml-2 w-2 h-2 rounded-full ${
                          camera.status === 'online' ? 'bg-green-500' : 'bg-red-500'
                        }`}></span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {detectionActive && detectionData && (
                <div className="mt-4 bg-gray-100 p-3 rounded-lg">
                  <h3 className="font-medium text-gray-700 mb-2">Илрүүлсэн дүн:</h3>
                  <div className="grid grid-cols-2 gap-2">
                    {detectionData.zones.map(zone => (
                      <div key={zone.id} className="bg-white p-2 rounded border">
                        <div className="flex justify-between">
                          <span className="font-medium">{zone.name}:</span>
                          <span className="font-medium">{zone.count}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-500">Төлөв:</span>
                          <span className={`${zone.is_stalled ? 'text-red-500' : 'text-green-500'}`}>
                            {zone.is_stalled ? 'Түгжрэлтэй' : 'Түгжрэлгүй'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        
        <div className="w-1/3 bg-white rounded-lg p-6 shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-blue-600 font-medium">Замын мэдээлэл</h2>
            <button className="text-gray-500">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="4" y1="12" x2="20" y2="12"></line>
                <line x1="4" y1="6" x2="20" y2="6"></line>
                <line x1="4" y1="18" x2="20" y2="18"></line>
              </svg>
            </button>
          </div>
          
          <div className="mb-4">
            <div className="mb-4">
              <h3 className="text-gray-600 mb-2">Дүүрэг:</h3>
              <div className="relative">
                <select 
                  className="w-full appearance-none border border-gray-300 rounded-md py-2 px-3 pr-8 bg-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={selectedDistrict}
                  onChange={(e) => handleDistrictChange(Number(e.target.value))}
                >
                  {districts.map((district) => (
                    <option key={district.id} value={district.id}>
                      {district.name}
                    </option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>
            
            <div className="mb-4">
              <h3 className="text-gray-600 mb-2">Уулзвар:</h3>
              <div className="relative">
                <select 
                  className="w-full appearance-none border border-gray-300 rounded-md py-2 px-3 pr-8 bg-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={selectedCrossroad}
                  onChange={(e) => handleCrossroadChange(Number(e.target.value))}
                >
                  {crossroads[selectedDistrict]?.map((crossroad) => (
                    <option key={crossroad.id} value={crossroad.id}>
                      {crossroad.name}
                    </option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>
            
            <div className="pl-0 mt-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-gray-800">Баруун</span>
                  <span className="bg-red-400 text-white px-4 py-1 rounded-full text-sm">
                    Түгжрэлтэй
                  </span>
      </div>

                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-600">Ногоон</span>
                  <span className="bg-gray-100 px-3 py-1 rounded-md text-sm">
                    150 секунд
                  </span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Улаан</span>
                  <span className="bg-gray-100 px-3 py-1 rounded-md text-sm">
                    100 секунд
                  </span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="mt-8">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="text-gray-600">Авто тохируулга:</span>
                <div 
                  className={`w-12 h-6 rounded-full flex items-center p-1 cursor-pointer transition-colors ${autoAdjust ? 'bg-green-400' : 'bg-gray-300'}`}
                  onClick={() => setAutoAdjust(!autoAdjust)}
                >
                  <div 
                    className={`w-4 h-4 rounded-full bg-white transition-transform ${autoAdjust ? 'transform translate-x-6' : ''}`} 
                  />
                </div>
              </div>
              
              <button className="bg-green-400 text-white px-6 py-2 rounded-md">
                Хадгалах
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}