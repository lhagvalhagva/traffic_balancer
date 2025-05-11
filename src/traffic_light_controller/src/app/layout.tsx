// app/layout.tsx
"use client";

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import 'leaflet/dist/leaflet.css';
import { usePathname } from 'next/navigation';

import Header from "../components/Header";
import SidebarMenu from "../components/SidebarMenu";
import { AuthProvider } from "@/lib/AuthContext";

import { useState } from "react";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

// export const metadata: Metadata = {
//   title: "Замын хөдөлгөөний удирдлагын систем",
//   description: "Гэрлэн дохионы удирдлага болон замын хөдөлгөөний хяналтын систем",
// };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/login';

  return (
    <html lang="mn">
      <head>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <div className="flex flex-col h-screen">
          <Header isConnected={true} />

          <div className="flex flex-1 overflow-hidden relative">
            {!isLoginPage && (
              <div
                className={`fixed top-0 left-0 h-full bg-[#2B78E4] z-40 transition-transform duration-300 shadow-lg md:relative md:translate-x-0 md:w-30`}
              >
                <SidebarMenu />
              </div>
            )}

            <main
              className={`flex-1 overflow-auto container mx-auto p-4 transition-all duration-300`}
            >
              <AuthProvider>{children}</AuthProvider>
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
