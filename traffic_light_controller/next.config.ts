/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: true,
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
  }
};

export default nextConfig;
