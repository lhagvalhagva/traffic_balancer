'use client';

import { useState, useEffect } from 'react';
import { useSocket } from '@/lib/socketio';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import dynamic from 'next/dynamic';
import CongestionStatus from '@/components/CongestionStatus';
import TrafficLight from '@/components/TrafficLight';

const MapComponent = dynamic(() => import('@/components/Map'), { ssr: false });

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();
  const { trafficLights, sendManualControl, isConnected } = useSocket();
  const [selectedLight, setSelectedLight] = useState<string | null>(null);

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

  const visibleLights = selectedLight
    ? trafficLights.filter(light => light.id === selectedLight)
    : trafficLights;

  return (
    <>
      <div className="mb-8">
        <CongestionStatus />
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Гэрлэн дохионы байршил</h2>
        <MapComponent trafficLights={trafficLights} onSelectLight={handleSelectLight} />
        {selectedLight && (
          <div className="mt-2 text-sm text-right">
            <button 
              onClick={() => setSelectedLight(null)}
              className="text-blue-600 hover:underline"
            >
              Бүх гэрлэн дохиог харуулах
            </button>
          </div>
        )}
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">
          Гэрлэн дохионы удирдлага
          {selectedLight && ` - ${trafficLights.find(l => l.id === selectedLight)?.name}`}
        </h2>

        {trafficLights.length === 0 ? (
          <div className="text-center py-10">
            <p className="text-gray-500">Гэрлэн дохионы мэдээлэл ачаалж байна...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {visibleLights.map(light => (
              <TrafficLight 
                key={light.id} 
                light={light} 
                onControl={handleLightControl} 
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
