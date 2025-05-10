'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { TrafficLight as TrafficLightType } from '@/lib/socketio';

const MapContainer = dynamic(() => import('react-leaflet').then(mod => mod.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import('react-leaflet').then(mod => mod.TileLayer), { ssr: false });
const Marker = dynamic(() => import('react-leaflet').then(mod => mod.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then(mod => mod.Popup), { ssr: false });

let leafletModule: any = null;

interface MapComponentProps {
  trafficLights: TrafficLightType[];
  onSelectLight?: (lightId: string) => void;
}

interface Signal {
  id: number;
  lat: number;
  lon: number;
}

const MapComponent: React.FC<MapComponentProps> = ({ trafficLights, onSelectLight }) => {
  const center: [number, number] = [47.918, 106.917];
  const zoom = 13;

  const [mapReady, setMapReady] = useState(false);
  const [trafficSignals, setTrafficSignals] = useState<Signal[]>([]);

  useEffect(() => {
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

  useEffect(() => {
    if (!mapReady) return;

    const fetchTrafficSignals = async () => {
      const overpassUrl = 'https://overpass-api.de/api/interpreter';
      const query = `
        [out:json];
        node["highway"="traffic_signals"](47.8,106.8,48.1,107.0);
        out body;
      `;

      try {
        const response = await fetch(overpassUrl + '?data=' + encodeURIComponent(query));
        const data = await response.json();
        setTrafficSignals(data.elements || []);
      } catch (error) {
        console.error('Error fetching traffic signals:', error);
      }
    };

    fetchTrafficSignals();
  }, [mapReady]);

  const handleMarkerClick = (lightId: string) => {
    if (onSelectLight) {
      onSelectLight(lightId);
    }
  };

  const cameraIcon = leafletModule?.icon({
    iconUrl: '/camera.png',
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30],
  });

  if (!mapReady) {
    return <div className="w-full h-96 bg-gray-100 flex items-center justify-center">Газрын зураг ачаалж байна...</div>;
  }

  return (
    <div className="w-full h-96 rounded-lg overflow-hidden shadow-md">
      <MapContainer center={center} zoom={zoom} scrollWheelZoom={true} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {trafficLights.map((light) => (
          <Marker
            key={light.id}
            position={[...trafficLightLocations[light.id]]}
            eventHandlers={{ click: () => handleMarkerClick(light.id) }}
          >
            <Popup>
              <div>
                <h3 className="font-semibold">{light.name}</h3>
                <p className="text-sm">{light.location}</p>
                <p className="text-sm mt-1">
                  Төлөв: <span className={`ml-1 font-medium ${
                    light.currentState === 'red' ? 'text-red-600' :
                    light.currentState === 'yellow' ? 'text-yellow-600' :
                    'text-green-600'
                  }`}>{light.currentState}</span>
                </p>
                <p className="text-sm">Үлдсэн хугацаа: {light.timeLeft} сек</p>
              </div>
            </Popup>
          </Marker>
        ))}

        {trafficSignals.map((signal) => (
          <Marker
            key={`signal-${signal.id}`}
            position={[signal.lat, signal.lon]}
            icon={cameraIcon}
          >
            <Popup>
              <strong>Traffic Signal</strong><br />
              Lat: {signal.lat}, Lng: {signal.lon}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
};

const trafficLightLocations: Record<string, [number, number]> = {
  light1: [47.918, 106.917],
  light2: [47.920, 106.925],
  light3: [47.912, 106.910],
};

export default MapComponent;
