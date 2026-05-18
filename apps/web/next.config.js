/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@cloudvisor/ui', '@cloudvisor/hooks'],
  reactStrictMode: true,
  swcMinify: true,
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.amazonaws.com',
      },
      {
        protocol: 'https',
        hostname: '**.googleusercontent.com',
      },
      {
        protocol: 'https',
        hostname: '**.blob.core.windows.net',
      },
    ],
  },
  async rewrites() {
    return [
      // Keep UI backend API — proxied to AIOps service
      {
        source: '/api/:path*',
        destination: 'http://localhost:8011/:path*',
      },
      // Keep UI backend route (used by Keep UI client via /backend prefix)
      {
        source: '/backend/:path*',
        destination: 'http://localhost:8011/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
