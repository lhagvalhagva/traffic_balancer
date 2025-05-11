'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/AuthContext';
import Image from 'next/image';

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login(username, password); // Assuming this sets `user` in context
  };

  return (
    <div className="min-h-screen flex items-center justify-between px-8 relative overflow-hidden">
      {/* Left Panel */}
      <div className="w-1/2 h-1/2 flex flex-col items-center justify-center z-10 bg-white shadow-lg rounded-r-xl">
        <h1 className="text-3xl font-bold text-blue-900 leading-snug text-center p-8">
          Орчин үеийн дэд бүтэц — өгөгдөлд <br /> суурилсан хөдөлгөөний зохицуулалт
        </h1>
        <div className="mt-8">
          <Image src="/images/map.svg" alt="Map" width={600} height={400} className="opacity-40" priority />
        </div>
      </div>

      {/* Right Panel (Login Form) */}
      <div className="w-2/7 z-10">
        <form onSubmit={handleSubmit} className="bg-white/90 backdrop-blur-lg p-8 border border-white rounded-md shadow-md w-full">
          <h2 className="text-2xl text-blue-900 font-semibold mb-6">
            Авто замын хөдөлгөөний <br /> нэгдсэн хяналтын систем
          </h2>

          {/* Username */}
          <div className="mb-4 relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-blue-900">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.121 17.804A9 9 0 0112 15a9 9 0 016.879 2.804M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </span>
            <input
              type="text"
              placeholder="Хэрэглэгчийн нэр/имэйл"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full pl-10 pr-10 py-2 border-b-2 border-blue-900 text-blue-900 placeholder-blue-400 focus:outline-none focus:border-blue-800 bg-transparent"
            />
          </div>

          {/* Password */}
          <div className="mb-6 relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-blue-900">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 11c.944 0 1.795.39 2.414 1.005A3.413 3.413 0 0115.828 14H8.172a3.413 3.413 0 011.414-1.995A3.413 3.413 0 0112 11z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 8V6a5 5 0 10-10 0v2" />
                <rect width="16" height="10" x="4" y="8" rx="2" ry="2" />
              </svg>
            </span>
            <input
              type="password"
              placeholder="Нууц үг"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-10 pr-10 py-2 border-b-2 border-blue-900 text-blue-900 placeholder-blue-400 focus:outline-none focus:border-blue-800 bg-transparent"
            />
          </div>

          <button type="submit" className="w-full bg-blue-600 text-white p-3 rounded-xl hover:bg-blue-700">
            Нэвтрэх
          </button>
        </form>
      </div>

      {/* Full Background Map */}
      <div className="absolute inset-0 -z-10">
        <Image
          src="/images/map.svg"
          alt="Full map"
          layout="fill"
          objectFit="cover"
          className="blur-sm brightness-90"
          priority
        />
      </div>
    </div>
  );
}
