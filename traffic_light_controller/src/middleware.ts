import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { IncomingMessage, Server as HttpServer } from 'http';
import { initSocketServer } from './app/api/socket/route';

export function middleware(request: NextRequest) {
  return NextResponse.next();
}

const serverStartup = (httpServer: HttpServer<typeof IncomingMessage, any>) => {
  // Серверийн талд л socket.io-г эхлүүлэх
  if (typeof window === 'undefined') {
    initSocketServer(httpServer);
  }
};

export default function initSocketConnection() {
  // Server-side execution check
  if (typeof window === 'undefined' && process.env.NEXT_PUBLIC_API_URL) {
    console.log('Socket.IO server starting on middleware...');
    
    if (process.env.NODE_ENV !== 'production') {
      const httpServer = process.env.__NEXT_HTTP_SERVER__ as unknown as HttpServer<typeof IncomingMessage, any>;
      if (httpServer) {
        serverStartup(httpServer);
      }
    } else {
      // Production орчинд
      const { createServer } = require('http');
      const server = createServer();
      serverStartup(server);
      server.listen(3001, () => {
        console.log('Socket.IO server started on port 3001');
      });
    }
  }
}

// Зөвхөн сервер талд дуудагдах
if (typeof window === 'undefined') {
  initSocketConnection();
} 