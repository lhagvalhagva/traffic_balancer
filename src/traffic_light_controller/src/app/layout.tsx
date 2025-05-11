// app/layout.tsx
"use client";

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import 'leaflet/dist/leaflet.css';

import Header from "../components/Header";
import Footer from "../components/Footer";
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
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <html lang="mn">
      <head>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <div className="flex flex-col h-screen">
          <Header
            isConnected={true}
            onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          />

          <div className="flex flex-1 overflow-hidden relative">
            <div
              className={`fixed top-0 left-0 h-full bg-gray-100 p-4 z-40 transition-transform duration-300 ${
                sidebarOpen ? "translate-x-0" : "-translate-x-full"
              } md:relative md:translate-x-0 md:w-64`}
            >
              <SidebarMenu />
            </div>

            {sidebarOpen && (
              <div
                className="fixed inset-0 bg-black opacity-30 z-30 md:hidden"
                onClick={() => setSidebarOpen(false)}
              ></div>
            )}

            <main
              className={`flex-1 overflow-auto container mx-auto p-4 transition-all duration-300 ${
                sidebarOpen ? "md:ml-64" : ""
              }`}
            >
              <AuthProvider>{children}</AuthProvider>
            </main>
          </div>

          <Footer />
        </div>
      </body>
    </html>
  );
}
