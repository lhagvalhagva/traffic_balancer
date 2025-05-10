'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { TrafficLight as TrafficLightType } from '@/lib/socketio';

// Leaflet динамикаар import хийх - server side рендеринг үед алдаа гаргахгүйн тулд
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
);

const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
);

const Marker = dynamic(
  () => import('react-leaflet').then((mod) => mod.Marker),
  { ssr: false }
);

const Popup = dynamic(
  () => import('react-leaflet').then((mod) => mod.Popup),
  { ssr: false }
);

// Маркерын default icon typescript-д алдаа өгөхөөс зайлсхийхийн тулд any ашиглана
let leafletModule: any = null;

interface MapComponentProps {
  trafficLights: TrafficLightType[];
  onSelectLight?: (lightId: string) => void;
}

const MapComponent: React.FC<MapComponentProps> = ({ trafficLights, onSelectLight }) => {
  // Монголын төв байршил (Улаанбаатар)
  const center: [number, number] = [47.918, 106.917];
  const zoom = 13;
  
  // Газрын зураг байгаа эсэхийг шалгах
  const [mapReady, setMapReady] = useState(false);
  
  useEffect(() => {
    // Leaflet лавлах сан импортлох
    const setupLeaflet = async () => {
      try {
        const L = await import('leaflet');
        leafletModule = L;
        setMapReady(true);
      } catch (err) {
        console.error('Leaflet импортлоход алдаа гарлаа:', err);
      }
    };
    
    setupLeaflet();
  }, []);
  
  // Байршил дээр дарах үед дуудагдах функц
  const handleMarkerClick = (lightId: string) => {
    if (onSelectLight) {
      onSelectLight(lightId);
    }
  };
  
  // Гэрлэн дохионы байршлын өгөгдөл зохиомлоор үүсгэх
  const trafficLightLocations: Record<string, [number, number]> = {
    light1: [47.918, 106.917],  // Уулзвар 1 - Чингисийн өргөн чөлөө
    light2: [47.920, 106.925],  // Уулзвар 2 
    light3: [47.912, 106.910],  // Уулзвар 3
  };

  if (!mapReady) {
    return <div className="w-full h-96 bg-gray-100 flex items-center justify-center">Газрын зураг ачаалж байна...</div>;
  }

  return (
    <div className="w-full h-96 rounded-lg overflow-hidden shadow-md">
      <MapContainer 
        center={center} 
        zoom={zoom} 
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {trafficLights.map((light) => {
          const location = trafficLightLocations[light.id];
          if (!location) return null;
          
          return (
            <Marker 
              key={light.id}
              position={location}
              eventHandlers={{
                click: () => handleMarkerClick(light.id)
              }}
            >
              <Popup>
                <div>
                  <h3 className="font-semibold">{light.name}</h3>
                  <p className="text-sm">{light.location}</p>
                  <p className="text-sm mt-1">
                    Төлөв: 
                    <span className={`ml-1 font-medium ${
                      light.currentState === 'red' ? 'text-red-600' : 
                      light.currentState === 'yellow' ? 'text-yellow-600' : 
                      'text-green-600'
                    }`}>
                      {light.currentState === 'red' ? 'Улаан' : 
                       light.currentState === 'yellow' ? 'Шар' : 
                       'Ногоон'}
                    </span>
                  </p>
                  <p className="text-sm">Үлдсэн хугацаа: {light.timeLeft} сек</p>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
};

export default MapComponent;