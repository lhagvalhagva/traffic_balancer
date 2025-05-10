const express = require('express');
const http = require('http');
const socketIO = require('socket.io');
const axios = require('axios');
const cors = require('cors');
const mqtt = require('mqtt');
const path = require('path');
const fs = require('fs');

// App тохиргоо
const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// HTTP сервер
const server = http.createServer(app);
const io = socketIO(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

// MQTT клиент
let mqttClient;
try {
  mqttClient = mqtt.connect('mqtt://localhost:1883'); // MQTT broker хаяг
} catch (error) {
  console.log('MQTT холболт амжилтгүй: ', error.message);
}

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
let timers = {};

function startTrafficLightCycle(light) {
  if (timers[light.id]) {
    clearTimeout(timers[light.id]);
  }

  const updateState = (state, duration) => {
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
        const adjustments = config.congestionAdjustments[congestionData.congestion_level] || config.congestionAdjustments.medium;
        
        // Тохиргоог шинэчлэх
        light.defaultTiming.green = adjustments.green;
        light.defaultTiming.yellow = adjustments.yellow;
        light.defaultTiming.red = adjustments.red;
        
        console.log(`Гэрлэн дохио [${light.name}] шинэчлэгдлээ: Green=${adjustments.green}s, Yellow=${adjustments.yellow}s, Red=${adjustments.red}s`);
        
        // Шинэ тохиргоог хэрэгжүүлэх
        if (light.currentState === 'red' || light.currentState === 'green') {
          light.timeLeft = light.defaultTiming[light.currentState];
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
    console.error('Түгжрэлийн мэдээлэл авахад алдаа гарлаа:', error.message);
  }
}

// Серверийг эхлүүлэх
function startServer(port = 3000) {
  // Гэрлэн дохио эхлүүлэх
  config.trafficLights.forEach(light => {
    startTrafficLightCycle(light);
  });
  
  // Түгжрэлийн мэдээлэл шинэчлэх хуваарь
  setInterval(adjustTrafficLightsByTrafficData, config.updateInterval);
  
  // MQTT холболт
  if (mqttClient) {
    mqttClient.on('connect', () => {
      console.log('MQTT серверт амжилттай холбогдлоо');
      mqttClient.subscribe('traffic/commands');
    });
    
    mqttClient.on('message', (topic, message) => {
      if (topic === 'traffic/commands') {
        try {
          const command = JSON.parse(message.toString());
          console.log('MQTT командыг хүлээн авлаа:', command);
          
          // Команд боловсруулах
          if (command.type === 'setLight' && command.lightId && command.state) {
            const light = config.trafficLights.find(l => l.id === command.lightId);
            if (light) {
              light.currentState = command.state;
              light.timeLeft = command.duration || light.defaultTiming[command.state];
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
  }
  
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
          light.currentState = data.state;
          light.timeLeft = data.duration || light.defaultTiming[data.state];
          
          // Циклийг дахин эхлүүлэх
          startTrafficLightCycle(light);
        }
      }
    });
    
    socket.on('disconnect', () => {
      console.log('Клиент салгагдлаа:', socket.id);
    });
  });
  
  // HTTP сервер эхлүүлэх
  server.listen(port, () => {
    console.log(`Гэрлэн дохио удирдах сервер ${port} портод ажиллаж эхэллээ`);
  });
}

// API endpoints
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/api/lights', (req, res) => {
  res.json({
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
});

app.post('/api/lights/control', (req, res) => {
  try {
    const { lightId, state, duration, autoControl } = req.body;
    
    if (!lightId) {
      return res.status(400).json({ error: 'lightId шаардлагатай' });
    }
    
    const light = config.trafficLights.find(l => l.id === lightId);
    if (!light) {
      return res.status(404).json({ error: 'Гэрлэн дохио олдсонгүй' });
    }
    
    if (autoControl !== undefined) {
      light.autoControl = autoControl;
    }
    
    if (state) {
      if (!['red', 'yellow', 'green'].includes(state)) {
        return res.status(400).json({ error: 'Буруу төлөв. red, yellow, green-ээс сонгоно уу' });
      }
      
      light.currentState = state;
      light.timeLeft = duration || light.defaultTiming[state];
      
      // Циклийг дахин эхлүүлэх
      startTrafficLightCycle(light);
    }
    
    res.json({
      success: true,
      light: {
        id: light.id,
        currentState: light.currentState,
        timeLeft: light.timeLeft,
        autoControl: light.autoControl
      }
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Серверийг эхлүүлэх
if (require.main === module) {
  startServer();
}

module.exports = { app, startServer }; 