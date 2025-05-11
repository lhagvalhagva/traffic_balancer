'use client';

import { useState, useEffect } from 'react';
import { useSocket } from '@/lib/socketio';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import dynamic from 'next/dynamic';
import TrafficLight from '@/components/TrafficLight';
import { Tab } from '@/components/ui/Tab';
import Image from 'next/image';

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
    thumbnail: 'https://images.unsplash.com/photo-1605559424843-9e4c228bf1c2?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxzZWFyY2h8MXx8Y2l0eSUyMHN0cmVldCUyMGNyb3NzaW5nfGVufDB8fDB8fA%3D%3D&w=1000&q=80'
  },
  {
    id: 2,
    name: 'Энх тайвны өргөн чөлөө',
    status: 'online',
    streamUrl: '/videos/road2.mp4',
    thumbnail: 'https://media.istockphoto.com/id/675176928/photo/shanghai-elevated-road-junction-and-interchange-overpass-at-night.jpg?s=612x612&w=0&k=20&c=OTENsfMXJ1NKDqoXegmPYFvp8yd9j9MvcH_6RgRYYQQ='
  },
  {
    id: 3,
    name: 'Их тойруу',
    status: 'online',
    streamUrl: '/videos/road3.mp4', 
    thumbnail: 'https://images.pexels.com/photos/358764/pexels-photo-358764.jpeg?cs=srgb&dl=pexels-pixabay-358764.jpg&fm=jpg'
  }
];

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();
  const { trafficLights, sendManualControl, isConnected } = useSocket();
  const [selectedLight, setSelectedLight] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('traffic');
  const [autoAdjust, setAutoAdjust] = useState(false);
  
  // Выбранные значения
  const [selectedDistrict, setSelectedDistrict] = useState<number>(1); // Сүхбаатар по умолчанию
  const [selectedCrossroad, setSelectedCrossroad] = useState<number>(101); // Баруун 4 замын уулзвар по умолчанию
  const [selectedCamera, setSelectedCamera] = useState<number>(1);
  const [videoPlaying, setVideoPlaying] = useState(false);

  useEffect(() => {
    if (!user) {
      router.push('/login');
    }
  }, [user]);

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

  const handlePlayVideo = () => {
    setVideoPlaying(true);
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
              <div className="relative h-96 bg-black rounded-lg overflow-hidden mb-4">
                {videoPlaying ? (
                  <video 
                    src={selectedCameraObj?.streamUrl} 
                    className="w-full h-full object-contain"
                    controls
                    autoPlay
                  />
                ) : (
                  <div className="relative w-full h-full flex items-center justify-center">
                    <img 
                      src={selectedCameraObj?.thumbnail} 
                      alt={selectedCameraObj?.name}
                      className="w-full h-full object-cover opacity-70"
                    />
                    <button 
                      className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-colors"
                      onClick={handlePlayVideo}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="white">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </button>
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