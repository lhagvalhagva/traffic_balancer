import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface CongestionStatusProps {
  apiUrl?: string;
}

interface CongestionData {
  congestion_level: 'low' | 'medium' | 'high' | 'very_high' | 'unknown';
  vehicles_per_minute: number;
  vehicles_in_roi: number;
  static_vehicles: number;
  max_static_duration: number;
  avg_static_duration: number;
  congestion_risk_score: number;
  timestamp: string;
  location: string;
}

interface StaticVehiclesData {
  distribution: {
    short: number;
    medium: number;
    long: number;
    very_long: number;
    extreme: number;
  };
  count: number;
}

export const CongestionStatus: React.FC<CongestionStatusProps> = ({ 
  apiUrl = 'http://localhost:8000'
}) => {
  const [congestionData, setCongestionData] = useState<CongestionData | null>(null);
  const [staticVehiclesData, setStaticVehiclesData] = useState<StaticVehiclesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'risk' | 'static'>('overview');
  
  // API-с мэдээлэл авах
  const fetchCongestionData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${apiUrl}/api/congestion/current`);
      setCongestionData(response.data);
      
      // Зогссон машины хуваарилалт авах
      const staticResponse = await axios.get(`${apiUrl}/api/congestion/static_vehicles`);
      setStaticVehiclesData(staticResponse.data);
      
      setError(null);
    } catch (err) {
      console.error('Түгжрэлийн мэдээлэл авахад алдаа гарлаа:', err);
      setError('Түгжрэлийн мэдээлэл ачаалахад алдаа гарлаа');
      // Хэрэв API холбогдохгүй бол тестийн өгөгдөл үүсгэх
      setCongestionData({
        congestion_level: 'medium',
        vehicles_per_minute: 8,
        vehicles_in_roi: 12,
        static_vehicles: 3,
        max_static_duration: 32.5,
        avg_static_duration: 15.2,
        congestion_risk_score: 45,
        timestamp: new Date().toISOString(),
        location: 'Тэст байршил'
      });
      
      setStaticVehiclesData({
        distribution: {
          short: 10,
          medium: 5,
          long: 3,
          very_long: 2,
          extreme: 1
        },
        count: 21
      });
    } finally {
      setLoading(false);
    }
  };
  
  // Анх компонент ачаалагдахад болон 10 секунд тутамд дахин авах
  useEffect(() => {
    fetchCongestionData();
    
    const interval = setInterval(() => {
      fetchCongestionData();
    }, 10000);
    
    return () => clearInterval(interval);
  }, [apiUrl]);
  
  // Түгжрэлийн түвшин тус бүрийн өнгө тодорхойлох
  const getLevelColor = (level: string) => {
    switch (level) {
      case 'low': return 'text-green-600';
      case 'medium': return 'text-yellow-600';
      case 'high': return 'text-orange-600';
      case 'very_high': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };
  
  // Түгжрэлийн түвшин тус бүрийн текст монголоор
  const getLevelText = (level: string) => {
    switch (level) {
      case 'low': return 'Бага';
      case 'medium': return 'Дунд зэрэг';
      case 'high': return 'Өндөр';
      case 'very_high': return 'Маш өндөр';
      default: return 'Тодорхойгүй';
    }
  };
  
  // Progress bar-н өнгө
  const getProgressBarColor = (level: string) => {
    switch (level) {
      case 'low': return 'bg-green-600';
      case 'medium': return 'bg-yellow-500';
      case 'high': return 'bg-orange-600';
      case 'very_high': return 'bg-red-600';
      default: return 'bg-gray-400';
    }
  };
  
  // Progress bar-н хувь
  const getProgressBarPercentage = (level: string) => {
    switch (level) {
      case 'low': return '25%';
      case 'medium': return '50%';
      case 'high': return '75%';
      case 'very_high': return '100%';
      default: return '0%';
    }
  };
  
  // Эрсдлийн оноогоор өнгө авах
  const getRiskScoreColor = (score: number) => {
    if (score < 25) return 'text-green-600';
    if (score < 50) return 'text-yellow-600';
    if (score < 75) return 'text-orange-600';
    return 'text-red-600';
  };
  
  // Эрсдлийн прогресс баарын өнгө
  const getRiskScoreBarColor = (score: number) => {
    if (score < 25) return 'bg-green-600';
    if (score < 50) return 'bg-yellow-500';
    if (score < 75) return 'bg-orange-600';
    return 'bg-red-600';
  };
  
  // Эрсдлийн түвшин текст
  const getRiskLevelText = (score: number) => {
    if (score < 25) return 'Бага';
    if (score < 50) return 'Дунд';
    if (score < 75) return 'Өндөр';
    return 'Маш өндөр';
  };
  
  if (loading) {
    return (
      <div className="bg-blue-50 p-4 rounded-lg shadow-sm animate-pulse">
        <div className="h-6 bg-blue-200 rounded w-1/3 mb-2"></div>
        <div className="h-4 bg-blue-200 rounded w-1/2 mb-2"></div>
        <div className="h-4 bg-blue-200 rounded w-full"></div>
      </div>
    );
  }
  
  if (error && !congestionData) {
    return (
      <div className="bg-red-50 p-4 rounded-lg border border-red-200">
        <h3 className="text-red-700 font-medium">Алдаа</h3>
        <p className="text-red-600">{error}</p>
        <button 
          onClick={fetchCongestionData}
          className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
        >
          Дахин оролдох
        </button>
      </div>
    );
  }
  
  if (!congestionData) return null;

  // Ерөнхий мэдээлэл
  const renderOverview = () => (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
        <div>
          <p className="text-gray-600">
            Одоогийн түгжрэлийн түвшин: 
            <span className={`ml-2 font-bold ${getLevelColor(congestionData.congestion_level)}`}>
              {getLevelText(congestionData.congestion_level)}
            </span>
          </p>
        </div>
        
        <div>
          <p className="text-gray-600">
            Минутад тоологдсон машин: 
            <span className="ml-2 font-bold">
              {congestionData.vehicles_per_minute.toFixed(1)}
            </span>
          </p>
        </div>
      </div>
      
      <div className="w-full bg-gray-200 h-2.5 rounded-full mb-1">
        <div 
          className={`h-2.5 rounded-full ${getProgressBarColor(congestionData.congestion_level)}`}
          style={{ width: getProgressBarPercentage(congestionData.congestion_level) }}
        ></div>
      </div>
      
      <div className="flex justify-between text-xs text-gray-500">
        <span>Бага</span>
        <span>Дунд</span>
        <span>Өндөр</span>
        <span>Маш өндөр</span>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mt-4">
        <div className="bg-white p-3 rounded-md shadow-sm">
          <p className="text-sm text-gray-500">Бүсэд байгаа машин</p>
          <p className="text-2xl font-bold">{congestionData.vehicles_in_roi}</p>
        </div>
        
        <div className="bg-white p-3 rounded-md shadow-sm">
          <p className="text-sm text-gray-500">Зогссон машин</p>
          <p className="text-2xl font-bold">{congestionData.static_vehicles}</p>
        </div>
      </div>
    </>
  );
  
  // Эрсдлийн оноо
  const renderRiskScore = () => (
    <>
      <div className="text-center mb-4">
        <p className="text-gray-600 mb-1">Түгжрэлийн эрсдлийн оноо:</p>
        <div className="relative inline-flex items-center justify-center">
          <svg viewBox="0 0 36 36" className="w-24 h-24 transform -rotate-90">
            <path
              className="stroke-current text-gray-200"
              fill="none"
              strokeWidth="3"
              d="M18 2.0845
                a 15.9155 15.9155 0 0 1 0 31.831
                a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path
              className={`stroke-current ${getRiskScoreBarColor(congestionData.congestion_risk_score)}`}
              fill="none"
              strokeWidth="3"
              strokeDasharray={`${congestionData.congestion_risk_score}, 100`}
              d="M18 2.0845
                a 15.9155 15.9155 0 0 1 0 31.831
                a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-2xl font-bold ${getRiskScoreColor(congestionData.congestion_risk_score)}`}>
              {Math.round(congestionData.congestion_risk_score)}
            </span>
          </div>
        </div>
        <p className={`font-medium ${getRiskScoreColor(congestionData.congestion_risk_score)}`}>
          {getRiskLevelText(congestionData.congestion_risk_score)}
        </p>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mt-4">
        <div className="bg-white p-3 rounded-md shadow-sm">
          <p className="text-sm text-gray-500">Хамгийн удаан зогссон</p>
          <p className="text-2xl font-bold">{congestionData.max_static_duration.toFixed(1)}s</p>
        </div>
        
        <div className="bg-white p-3 rounded-md shadow-sm">
          <p className="text-sm text-gray-500">Дундаж зогссон хугацаа</p>
          <p className="text-2xl font-bold">{congestionData.avg_static_duration.toFixed(1)}s</p>
        </div>
      </div>
    </>
  );
  
  // Зогссон машинуудын мэдээлэл
  const renderStaticVehicles = () => {
    if (!staticVehiclesData) return <p>Зогссон машины мэдээлэл байхгүй байна.</p>;
    
    const { distribution } = staticVehiclesData;
    const totalCount = staticVehiclesData.count || 1;
    
    return (
      <>
        <p className="text-gray-600 mb-3">
          Зогссон машинуудын хуваарилалт: <span className="font-bold">{totalCount}</span> машин
        </p>
        
        <div className="space-y-3">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm">Бага (0-10с)</span>
              <span className="text-sm font-medium">{distribution.short} ({((distribution.short / totalCount) * 100).toFixed(1)}%)</span>
            </div>
            <div className="w-full bg-gray-200 h-2 rounded-full">
              <div className="bg-green-500 h-2 rounded-full" style={{ width: `${(distribution.short / totalCount) * 100}%` }}></div>
            </div>
          </div>
          
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm">Дунд (10-30с)</span>
              <span className="text-sm font-medium">{distribution.medium} ({((distribution.medium / totalCount) * 100).toFixed(1)}%)</span>
            </div>
            <div className="w-full bg-gray-200 h-2 rounded-full">
              <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${(distribution.medium / totalCount) * 100}%` }}></div>
            </div>
          </div>
          
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm">Урт (30-60с)</span>
              <span className="text-sm font-medium">{distribution.long} ({((distribution.long / totalCount) * 100).toFixed(1)}%)</span>
            </div>
            <div className="w-full bg-gray-200 h-2 rounded-full">
              <div className="bg-yellow-500 h-2 rounded-full" style={{ width: `${(distribution.long / totalCount) * 100}%` }}></div>
            </div>
          </div>
          
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm">Маш урт (60-120с)</span>
              <span className="text-sm font-medium">{distribution.very_long} ({((distribution.very_long / totalCount) * 100).toFixed(1)}%)</span>
            </div>
            <div className="w-full bg-gray-200 h-2 rounded-full">
              <div className="bg-orange-500 h-2 rounded-full" style={{ width: `${(distribution.very_long / totalCount) * 100}%` }}></div>
            </div>
          </div>
          
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm">Хэт удаан (&gt;120с)</span>
              <span className="text-sm font-medium">{distribution.extreme} ({((distribution.extreme / totalCount) * 100).toFixed(1)}%)</span>
            </div>
            <div className="w-full bg-gray-200 h-2 rounded-full">
              <div className="bg-red-500 h-2 rounded-full" style={{ width: `${(distribution.extreme / totalCount) * 100}%` }}></div>
            </div>
          </div>
        </div>
      </>
    );
  };

  return (
    <div className="bg-blue-50 p-4 rounded-lg shadow-sm">
      <h3 className="text-lg font-semibold text-blue-800 mb-4">
        Түгжрэлийн мэдээлэл
      </h3>
      
      <div className="flex border-b mb-4">
        <button
          className={`py-2 px-4 font-medium text-sm focus:outline-none ${
            activeTab === 'overview' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'
          }`}
          onClick={() => setActiveTab('overview')}
        >
          Ерөнхий
        </button>
        <button
          className={`py-2 px-4 font-medium text-sm focus:outline-none ${
            activeTab === 'risk' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'
          }`}
          onClick={() => setActiveTab('risk')}
        >
          Эрсдэл
        </button>
        <button
          className={`py-2 px-4 font-medium text-sm focus:outline-none ${
            activeTab === 'static' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'
          }`}
          onClick={() => setActiveTab('static')}
        >
          Зогссон машин
        </button>
      </div>
      
      {activeTab === 'overview' && renderOverview()}
      {activeTab === 'risk' && renderRiskScore()}
      {activeTab === 'static' && renderStaticVehicles()}
      
      <div className="mt-4 text-xs text-gray-500 text-right">
        Сүүлийн шинэчлэл: {new Date(congestionData.timestamp).toLocaleTimeString()}
        <br />
        Байршил: {congestionData.location}
      </div>
    </div>
  );
};

export default CongestionStatus; 