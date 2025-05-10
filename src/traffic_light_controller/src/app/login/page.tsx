'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/AuthContext';
import Image from 'next/image';

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login(username);
  };

  return (
    <div className="min-h-screen flex items-center justify-between px-8 relative overflow-hidden">
      {/* Left Panel */}
      <div className="w-1/2 h-1/2 flex flex-col justify-between py-16 pr-8 z-10 bg-white shadow-lg rounded-r-xl">
        <h1 className="text-4xl font-bold text-blue-900 leading-snug p-4">
          Орчин үеийн дэд бүтэц —<br /> өгөгдөлд суурилсан хөдөлгөөний зохицуулалт
        </h1>

        {/* Bottom Map Inside Main Panel */}
        <div className="relative w-full h-64 mt-12">
          <Image
            src="/images/map.svg"
            alt="Map background"
            layout="fill"
            objectFit="cover"
            className="opacity-40"
            priority
          />
        </div>
      </div>

      {/* Right Panel (Login Form) */}
      <div className="w-1/3 z-10">
        <form onSubmit={handleSubmit} className="bg-white/90 backdrop-blur-lg p-8 rounded shadow-md w-full">
          <h2 className="text-2xl font-semibold mb-6">Нэвтрэх</h2>
          <input
            type="text"
            placeholder="Хэрэглэгчийн нэр"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded mb-4"
          />
          <button type="submit" className="w-full bg-blue-600 text-white p-3 rounded hover:bg-blue-700">
            Нэвтрэх
          </button>
        </form>
      </div>

      {/* Full Background Map Overlay */}
      <div className="absolute inset-0 -z-10">
        <Image
          src="/images/map.svg"
          alt="Full map background"
          layout="fill"
          objectFit="cover"
          className="blur-sm brightness-90"
          priority
        />
      </div>
    </div>
  );
}
