import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface CongestionStatusProps {
  apiUrl?: string;
}

interface CongestionData {
  congestion_level: 'low' | 'medium' | 'high' | 'very_high' | 'unknown';
  vehicles_per_minute: number;
  timestamp: string;
  location: string;
}

export const CongestionStatus: React.FC<CongestionStatusProps> = ({ 
  apiUrl = 'http://localhost:8000'
}) => {
  const [congestionData, setCongestionData] = useState<CongestionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // API-с мэдээлэл авах
  const fetchCongestionData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${apiUrl}/api/congestion/current`);
      setCongestionData(response.data);
      setError(null);
    } catch (err) {
      console.error('Түгжрэлийн мэдээлэл авахад алдаа гарлаа:', err);
      setError('Түгжрэлийн мэдээлэл ачаалахад алдаа гарлаа');
      // Хэрэв API холбогдохгүй бол тестийн өгөгдөл үүсгэх
      setCongestionData({
        congestion_level: 'medium',
        vehicles_per_minute: 8,
        timestamp: new Date().toISOString(),
        location: 'Тэст байршил'
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

  return (
    <div className="bg-blue-50 p-4 rounded-lg shadow-sm">
      <h3 className="text-lg font-semibold text-blue-800 mb-2">
        Түгжрэлийн мэдээлэл
      </h3>
      
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
      
      <div className="mt-2 text-xs text-gray-500 text-right">
        Сүүлийн шинэчлэл: {new Date(congestionData.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
};

export default CongestionStatus; 