// Edge runtime-д бус nodejs дээр ажиллуулах
export const runtime = 'nodejs';

import { NextRequest, NextResponse } from 'next/server';
import { io } from '../socket/route';

// Одоогийн тохиргоог fetch хийх эндпойнт
export async function GET(req: NextRequest) {
  // Express app.js-н тохиргоог Next.js API Routes-д гаргаж өгөх
  const config = {
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

  return NextResponse.json({
    trafficLights: config.trafficLights.map(light => ({
      id: light.id,
      name: light.name,
      location: light.location,
      timing: light.defaultTiming,
      currentState: light.currentState,
      timeLeft: light.timeLeft,
      autoControl: light.autoControl
    }))
  });
}

// Гэрлэн дохио удирдах эндпойнт
export async function POST(req: NextRequest) {
  try {
    const data = await req.json();
    const { lightId, state, duration, autoControl } = data;
    
    if (!lightId) {
      return NextResponse.json({ error: 'lightId шаардлагатай' }, { status: 400 });
    }
    
    // Socket.io холболт биш бол
    if (!io) {
      return NextResponse.json({ error: 'Socket сервер эхлээгүй байна' }, { status: 500 });
    }
    
    // Гэрлэн дохио хайх
    const config = {
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
          autoControl: true
        }
      ]
    };
    
    const light = config.trafficLights.find(l => l.id === lightId);
    if (!light) {
      return NextResponse.json({ error: 'Гэрлэн дохио олдсонгүй' }, { status: 404 });
    }
    
    // Автомат горим өөрчлөх
    if (autoControl !== undefined) {
      light.autoControl = autoControl;
    }
    
    // Төлөв өөрчлөх
    if (state) {
      if (!['red', 'yellow', 'green'].includes(state)) {
        return NextResponse.json({ error: 'Буруу төлөв. red, yellow, green-ээс сонгоно уу' }, { status: 400 });
      }
      
      light.currentState = state as 'red' | 'yellow' | 'green';
      light.timeLeft = duration || light.defaultTiming[state as keyof typeof light.defaultTiming];
      
      // Socket.io-р комманд илгээх
      io.emit('manualControl', {
        lightId: lightId,
        state: state,
        duration: duration || light.defaultTiming[state as keyof typeof light.defaultTiming],
        autoControl: autoControl
      });
    }
    
    return NextResponse.json({
      success: true,
      light: {
        id: light.id,
        currentState: light.currentState,
        timeLeft: light.timeLeft,
        autoControl: light.autoControl
      }
    });
  } catch (error) {
    console.error('API алдаа:', error);
    return NextResponse.json({ error: 'Серверийн алдаа гарлаа' }, { status: 500 });
  }
} 