'use client';

import { useState } from 'react';
import { useSocket } from '@/lib/socketio';
import dynamic from 'next/dynamic';
import CongestionStatus from '@/components/CongestionStatus';
import TrafficLight from '@/components/TrafficLight';

const MapComponent = dynamic(
  () => import('@/components/Map'),
  { ssr: false }
);

export default function Home() {
  const { trafficLights, sendManualControl, isConnected } = useSocket();
  const [selectedLight, setSelectedLight] = useState<string | null>(null);

  // Гэрлэн дохионы удирдлага
  const handleLightControl = (lightId: string, data: { state?: string; autoControl?: boolean }) => {
    sendManualControl(lightId, data);
  };

  // Газрын зураг дээрээс гэрлэн дохио сонгох
  const handleSelectLight = (lightId: string) => {
    setSelectedLight(lightId);
  };

  // Тухайн хуудсыг ачаалсан хэрэглэгчид харагдах гэрлэн дохио
  const visibleLights = selectedLight 
    ? trafficLights.filter(light => light.id === selectedLight)
    : trafficLights;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-blue-700 text-white p-4 shadow-md">
        <div className="container mx-auto">
          <h1 className="text-2xl font-bold">Замын хөдөлгөөний удирдлагын систем</h1>
          <p className="text-blue-200">
            {isConnected ? 'Серверт холбогдсон' : 'Серверт холбогдоогүй...'}
          </p>
        </div>
      </header>

      <main className="container mx-auto py-8 px-4">
        {/* Түгжрэлийн мэдээлэл */}
        <div className="mb-8">
          <CongestionStatus />
        </div>

        {/* Газрын зураг */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Гэрлэн дохионы байршил</h2>
          <MapComponent 
            trafficLights={trafficLights} 
            onSelectLight={handleSelectLight} 
          />
          <div className="mt-2 text-sm text-right">
            <button 
              onClick={() => setSelectedLight(null)}
              className={`text-blue-600 hover:underline ${!selectedLight ? 'hidden' : ''}`}
            >
              Бүх гэрлэн дохиог харуулах
            </button>
          </div>
        </div>

        {/* Гэрлэн дохионы удирдлага */}
        <div>
          <h2 className="text-xl font-semibold mb-4">
            Гэрлэн дохионы удирдлага
            {selectedLight && ` - ${trafficLights.find(l => l.id === selectedLight)?.name}`}
          </h2>

          {/* Ачаалж байгаа үед харуулах */}
          {trafficLights.length === 0 && (
            <div className="text-center py-10">
              <p className="text-gray-500">Гэрлэн дохионы мэдээлэл ачаалж байна...</p>
            </div>
          )}
          
          {/* Гэрлэн дохионы жагсаалт */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {visibleLights.map(light => (
              <TrafficLight 
                key={light.id} 
                light={light} 
                onControl={handleLightControl} 
              />
            ))}
          </div>
        </div>
      </main>

      <footer className="bg-gray-800 text-white p-4 mt-12">
        <div className="container mx-auto text-center">
          <p>&copy; 2023 Замын хөдөлгөөний удирдлагын систем</p>
        </div>
      </footer>
    </div>
  );
}
