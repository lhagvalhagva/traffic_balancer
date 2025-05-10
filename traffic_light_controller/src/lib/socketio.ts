import { io as socketIOClient, Socket } from 'socket.io-client';
import { useState, useEffect, useCallback } from 'react';

export interface TrafficLight {
  id: string;
  name: string;
  location: string;
  timing: {
    green: number;
    yellow: number;
    red: number;
  };
  currentState: 'red' | 'yellow' | 'green';
  timeLeft: number;
  autoControl: boolean;
}

// Socket.IO клиент талын hook
export const useSocket = () => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [trafficLights, setTrafficLights] = useState<TrafficLight[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Серверийн хаяг
    const socketInstance = socketIOClient(process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:3000');

    // Socket холболтын үйл явдлууд
    socketInstance.on('connect', () => {
      console.log('Socket холбогдлоо');
      setIsConnected(true);
    });

    socketInstance.on('disconnect', () => {
      console.log('Socket салгагдлаа');
      setIsConnected(false);
    });

    // Анхны гэрлэн дохионы мэдээлэл
    socketInstance.on('trafficLightInit', (lights: TrafficLight[]) => {
      console.log('Гэрлэн дохионы мэдээлэл хүлээн авлаа:', lights);
      setTrafficLights(lights);
    });

    // Гэрлэн дохионы төлөв шинэчлэгдсэн
    socketInstance.on('trafficLightUpdate', (data: { id: string; state: 'red' | 'yellow' | 'green'; timeLeft: number }) => {
      setTrafficLights(prevLights => prevLights.map(light => {
        if (light.id === data.id) {
          return { ...light, currentState: data.state, timeLeft: data.timeLeft };
        }
        return light;
      }));
    });

    // Үлдсэн хугацаа шинэчлэгдсэн
    socketInstance.on('trafficLightCountdown', (data: { id: string; timeLeft: number }) => {
      setTrafficLights(prevLights => prevLights.map(light => {
        if (light.id === data.id) {
          return { ...light, timeLeft: data.timeLeft };
        }
        return light;
      }));
    });

    // Хугацааны тохиргоо шинэчлэгдсэн
    socketInstance.on('timingUpdate', (lights: TrafficLight[]) => {
      setTrafficLights(prevLights => {
        return prevLights.map(prevLight => {
          const updatedLight = lights.find(l => l.id === prevLight.id);
          if (updatedLight) {
            return {
              ...prevLight,
              timing: updatedLight.timing,
              autoControl: updatedLight.autoControl
            };
          }
          return prevLight;
        });
      });
    });

    setSocket(socketInstance);

    // Цэвэрлэх
    return () => {
      socketInstance.disconnect();
    };
  }, []);

  // Гар удирдлагын комманд илгээх функц
  const sendManualControl = useCallback((lightId: string, data: { state?: string; autoControl?: boolean; duration?: number }) => {
    if (socket && isConnected) {
      socket.emit('manualControl', {
        lightId,
        ...data
      });
    }
  }, [socket, isConnected]);

  return {
    socket,
    isConnected,
    trafficLights,
    sendManualControl
  };
}; 