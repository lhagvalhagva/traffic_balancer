/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3000'],
    },
    serverComponentsExternalPackages: ['mqtt'],
  },
  // MQTT ашиглаж буй роутуудыг node runtime дээр ажиллуулах
  // "edge" runtime-д "navigator" объект байхгүй учир MQTT ажиллахгүй
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin',
          },
        ],
      },
    ];
  },
  serverRuntimeConfig: {
    PROJECT_ROOT: __dirname,
  },
  serverExternalPackages: ['leaflet'],
  images: {
    domains: ['localhost'],
  },
};

export default nextConfig;
