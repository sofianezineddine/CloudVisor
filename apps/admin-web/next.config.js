/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: false,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  // Proxy API calls to the backend — eliminates CORS entirely
  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_ADMIN_API_BASE_URL || 'http://localhost:8002';
    return [
      {
        source: '/api/proxy/:path*',
        destination: `${apiBase}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
