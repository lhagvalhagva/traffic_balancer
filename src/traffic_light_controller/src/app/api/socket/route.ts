// Edge runtime-д бус nodejs дээр ажиллуулах
export const runtime = 'nodejs';

import { Server as NetServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import { Socket as NetSocket } from 'net';
import { NextRequest, NextResponse } from 'next/server';
// Серверийн талд ажиллаж байгаа учир шууд импортлож болно
import mqtt from 'mqtt';
import axios from 'axios';

// Сокет серверийн глобал хувьсагч
export let io: SocketIOServer | null = null;

// MQTT клиент
let mqttClient: any = null;

// HTTP сервертэй холбогдсон эсэхийг шалгах
let isIOInitialized = false;

// Тохиргоо
const config = {
  apiUrl: 'http://localhost:8000', // Traffic analyzer API хаяг
  updateInterval: 10000, // 10 секунд тутамд шинэчлэх
  trafficLights: [
    {
      id: 'light1',
      name: 'Уулзвар 1',
      location: 'Чингисийн өргөн чөлөө',
      defaultTiming: {
        green: 30,
        yellow: 5,
        red: 40
      },
      currentState: 'red',
      timeLeft: 40,
      autoControl: true,
      mqttTopic: 'traffic/light1'
    }
  ],
  congestionAdjustments: {
    low: { green: 20, yellow: 5, red: 50 },
    medium: { green: 30, yellow: 5, red: 40 },
    high: { green: 45, yellow: 5, red: 30 },
    very_high: { green: 60, yellow: 5, red: 20 }
  }
};

// Гэрлэн дохио удирдах функц
let timers: Record<string, NodeJS.Timeout> = {};

function startTrafficLightCycle(light: any) {
  if (timers[light.id]) {
    clearTimeout(timers[light.id]);
  }

  const updateState = (state: string, duration: number) => {
    if (!io) return;
    
    light.currentState = state;
    light.timeLeft = duration;
    
    // MQTT сервер рүү шинэ төлөвийг илгээх
    if (mqttClient && mqttClient.connected) {
      mqttClient.publish(light.mqttTopic, JSON.stringify({
        state: state,
        duration: duration
      }));
    }
    
    // Клиент рүү мэдээлэл илгээх
    io.emit('trafficLightUpdate', { 
      id: light.id, 
      state: state, 
      timeLeft: duration 
    });
    
    // Үлдсэн хугацааг шинэчлэх
    let timeRemaining = duration;
    const countdownInterval = setInterval(() => {
      if (!io) {
        clearInterval(countdownInterval);
        return;
      }
      
      timeRemaining -= 1;
      light.timeLeft = timeRemaining;
      
      io.emit('trafficLightCountdown', { 
        id: light.id, 
        timeLeft: timeRemaining 
      });
      
      if (timeRemaining <= 0) {
        clearInterval(countdownInterval);
      }
    }, 1000);
    
    // Дараагийн төлөвт шилжих
    timers[light.id] = setTimeout(() => {
      clearInterval(countdownInterval);
      
      if (state === 'green') {
        updateState('yellow', light.defaultTiming.yellow);
      } else if (state === 'yellow') {
        updateState('red', light.defaultTiming.red);
      } else if (state === 'red') {
        updateState('green', light.defaultTiming.green);
      }
    }, duration * 1000);
  };
  
  // Эхний төлөв
  updateState(light.currentState, light.timeLeft);
}

// Түгжрэлийн түвшингээс хамаарч гэрлэн дохионы хугацааг тохируулах
async function adjustTrafficLightsByTrafficData() {
  if (!io) return;
  
  try {
    console.log('Түгжрэлийн мэдээлэл шинэчилж байна...');
    
    // Traffic analyzer API-с түгжрэлийн түвшин авах
    const response = await axios.get(`${config.apiUrl}/api/congestion/current`);
    const congestionData = response.data;
    
    console.log(`Одоогийн түгжрэлийн түвшин: ${congestionData.congestion_level}, Машин/мин: ${congestionData.vehicles_per_minute}`);
    
    // Гэрлэн дохионы хугацааг шинэчлэх
    config.trafficLights.forEach(light => {
      if (light.autoControl) {
        // Түгжрэлийн түвшингээс хамаарах хугацааны тохиргоо
        const adjustments = config.congestionAdjustments[congestionData.congestion_level as keyof typeof config.congestionAdjustments] || config.congestionAdjustments.medium;
        
        // Тохиргоог шинэчлэх
        light.defaultTiming.green = adjustments.green;
        light.defaultTiming.yellow = adjustments.yellow;
        light.defaultTiming.red = adjustments.red;
        
        console.log(`Гэрлэн дохио [${light.name}] шинэчлэгдлээ: Green=${adjustments.green}s, Yellow=${adjustments.yellow}s, Red=${adjustments.red}s`);
        
        // Шинэ тохиргоог хэрэгжүүлэх
        if (light.currentState === 'red' || light.currentState === 'green') {
          light.timeLeft = light.defaultTiming[light.currentState as keyof typeof light.defaultTiming];
        }
      }
    });
    
    // Клиент рүү шинэчлэлтийг илгээх
    io.emit('timingUpdate', config.trafficLights.map(light => ({
      id: light.id,
      timing: light.defaultTiming,
      currentState: light.currentState,
      timeLeft: light.timeLeft,
      autoControl: light.autoControl
    })));
    
  } catch (error) {
    console.error('Түгжрэлийн мэдээлэл авахад алдаа гарлаа:', error);
  }
}

// Socket.IO серверийг эхлүүлэх
function initSocketServer(server: NetServer) {
  // Аль хэдийн эхэлсэн бол дахин эхлүүлэхгүй
  if (isIOInitialized) return;
  
  io = new SocketIOServer(server, {
    cors: {
      origin: '*',
      methods: ['GET', 'POST']
    }
  });

  // MQTT холболт - динамик импорт болон try/catch ашиглах
  const initMqtt = async () => {
    try {
      if (typeof window === 'undefined') {
        // Сервер талд
        const mqtt = await import('mqtt');
        mqttClient = mqtt.connect('mqtt://localhost:1883');
        
        mqttClient.on('connect', () => {
          console.log('MQTT серверт амжилттай холбогдлоо (сервер талаас)');
          mqttClient?.subscribe('traffic/commands');
        });
        
        mqttClient.on('message', (topic: string, message: Buffer) => {
          if (topic === 'traffic/commands') {
            try {
              const command = JSON.parse(message.toString());
              console.log('MQTT командыг хүлээн авлаа:', command);
              
              // Команд боловсруулах
              if (command.type === 'setLight' && command.lightId && command.state) {
                const light = config.trafficLights.find(l => l.id === command.lightId);
                if (light) {
                  light.currentState = command.state as 'red' | 'yellow' | 'green';
                  light.timeLeft = command.duration || light.defaultTiming[command.state as keyof typeof light.defaultTiming];
                  light.autoControl = command.autoControl !== undefined ? command.autoControl : light.autoControl;
                  
                  // Циклийг дахин эхлүүлэх
                  startTrafficLightCycle(light);
                }
              }
            } catch (e) {
              console.error('MQTT мессеж боловсруулахад алдаа гарлаа:', e);
            }
          }
        });
      } else {
        console.log('MQTT холболт client талд дуудагдсан');
      }
    } catch (error) {
      console.log('MQTT холболт амжилтгүй: ', error);
    }
  };
  
  initMqtt();

  // Socket.IO холболт
  io.on('connection', (socket) => {
    console.log('Шинэ клиент холбогдлоо:', socket.id);
    
    // Клиентэд одоогийн төлөвийг илгээх
    socket.emit('trafficLightInit', config.trafficLights.map(light => ({
      id: light.id,
      name: light.name,
      location: light.location,
      timing: light.defaultTiming,
      currentState: light.currentState,
      timeLeft: light.timeLeft,
      autoControl: light.autoControl
    })));
    
    // Клиентээс ирэх удирдлагын комманд
    socket.on('manualControl', (data) => {
      console.log('Гар удирдлагын команд хүлээн авлаа:', data);
      
      const light = config.trafficLights.find(l => l.id === data.lightId);
      if (light) {
        if (data.autoControl !== undefined) {
          light.autoControl = data.autoControl;
        }
        
        if (data.state) {
          light.currentState = data.state as 'red' | 'yellow' | 'green';
          light.timeLeft = data.duration || light.defaultTiming[data.state as keyof typeof light.defaultTiming];
          
          // Циклийг дахин эхлүүлэх
          startTrafficLightCycle(light);
        }
      }
    });
    
    socket.on('disconnect', () => {
      console.log('Клиент салгагдлаа:', socket.id);
    });
  });

  // Гэрлэн дохио эхлүүлэх
  config.trafficLights.forEach(light => {
    startTrafficLightCycle(light);
  });
  
  // Түгжрэлийн мэдээлэл шинэчлэх хуваарь
  setInterval(adjustTrafficLightsByTrafficData, config.updateInterval);
  
  isIOInitialized = true;
}

// API Route handler
export async function GET(req: NextRequest) {
  return NextResponse.json({ status: 'Socket server is running' });
}

// Серверийг глобал хувьсагчаар экспортлох - middleware.ts-д ашиглагдана
export { initSocketServer };