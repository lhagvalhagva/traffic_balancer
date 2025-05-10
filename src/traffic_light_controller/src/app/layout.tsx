import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import 'leaflet/dist/leaflet.css';

import Header from "../components/Header";
import Footer from "../components/Footer";
import { AuthProvider } from "@/lib/AuthContext";
// import { SocketProvider } from "@/lib/socketio"; // if you want context to be global

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Замын хөдөлгөөний удирдлагын систем",
  description: "Гэрлэн дохионы удирдлага болон замын хөдөлгөөний хяналтын систем",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="mn">
      <head>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {/* <SocketProvider> */}
        <Header isConnected={true} /> {/* Optional: Pass static value or use context */}
        <main className="container mx-auto">
          <AuthProvider>

            {children}
          </AuthProvider>
        </main>
        <Footer />
        {/* </SocketProvider> */}
      </body>
    </html>
  );
}
