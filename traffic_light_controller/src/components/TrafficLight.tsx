import React from 'react';
import { TrafficLight as TrafficLightType } from '@/lib/socketio';

interface TrafficLightProps {
  light: TrafficLightType;
  onControl: (lightId: string, data: { state?: string; autoControl?: boolean; }) => void;
}

export const TrafficLight: React.FC<TrafficLightProps> = ({ light, onControl }) => {
  const { id, name, location, currentState, timeLeft, autoControl, timing } = light;

  const handleStateChange = (state: 'red' | 'yellow' | 'green') => {
    onControl(id, { state });
  };

  const handleAutoControlToggle = () => {
    onControl(id, { autoControl: !autoControl });
  };

  return (
    <div className="col-span-1">
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="bg-blue-600 text-white p-4">
          <h3 className="text-lg font-semibold">{name} - {location}</h3>
        </div>
        
        <div className="p-4 flex flex-col items-center">
          {/* Гэрлэн дохионы дүрслэл */}
          <div className="w-20 h-56 bg-gray-800 rounded-lg flex flex-col items-center justify-around p-4 mb-4">
            <div 
              className={`w-14 h-14 rounded-full ${currentState === 'red' ? 'bg-red-600 shadow-lg shadow-red-300' : 'bg-red-600/30'}`}
            />
            <div 
              className={`w-14 h-14 rounded-full ${currentState === 'yellow' ? 'bg-yellow-400 shadow-lg shadow-yellow-200' : 'bg-yellow-400/30'}`}
            />
            <div 
              className={`w-14 h-14 rounded-full ${currentState === 'green' ? 'bg-green-500 shadow-lg shadow-green-300' : 'bg-green-500/30'}`}
            />
          </div>
          
          {/* Үлдсэн хугацаа */}
          <div className="text-2xl font-bold mb-4">{timeLeft} сек</div>
          
          {/* Автомат/Гар удирдлагын тогглер */}
          <div className="mb-4 flex items-center">
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                checked={autoControl} 
                onChange={handleAutoControlToggle}
                className="sr-only peer" 
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              <span className="ml-3 text-sm font-medium text-gray-900">
                {autoControl ? 'Автомат горим' : 'Гар удирдлага'}
              </span>
            </label>
          </div>
          
          {/* Удирдлагын товчууд */}
          <div className="grid grid-cols-3 gap-2 mb-4 w-full">
            <button 
              onClick={() => handleStateChange('red')}
              className="px-2 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Улаан
            </button>
            <button 
              onClick={() => handleStateChange('yellow')}
              className="px-2 py-2 bg-yellow-400 text-gray-800 rounded hover:bg-yellow-500"
            >
              Шар
            </button>
            <button 
              onClick={() => handleStateChange('green')}
              className="px-2 py-2 bg-green-600 text-white rounded hover:bg-green-700"
            >
              Ногоон
            </button>
          </div>
          
          {/* Хугацааны тохиргоо */}
          <div className="w-full">
            <p className="text-sm text-gray-600 mb-2">Хугацааны тохиргоо:</p>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-green-100 p-2 rounded text-xs text-center">
                Ногоон: {timing.green}s
              </div>
              <div className="bg-yellow-100 p-2 rounded text-xs text-center">
                Шар: {timing.yellow}s
              </div>
              <div className="bg-red-100 p-2 rounded text-xs text-center">
                Улаан: {timing.red}s
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TrafficLight; 