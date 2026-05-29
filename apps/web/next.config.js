/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@cloudvisor/ui', '@cloudvisor/hooks', '@xyflow/react', '@xyflow/system', '@copilotkit/react-core', '@copilotkit/react-ui', '@copilotkit/react-textarea'],
  reactStrictMode: false,
  swcMinify: true,
  compiler: {
    ...(process.env.NODE_ENV === 'production' && !process.env.TURBOPACK
      ? { removeConsole: true }
      : {}),
  },

  // Silence Sass legacy API deprecation warnings
  sassOptions: {
    silenceDeprecations: ['legacy-js-api'],
  },

  // Output standalone build for Docker deployment
  output: 'standalone',

  // Ensure all pages are included in the build
  typescript: {
    // Don't fail build on type errors (they're checked separately)
    ignoreBuildErrors: true,
  },
  eslint: {
    // Don't fail build on lint errors
    ignoreDuringBuilds: true,
  },

  // Skip type checking during build (run separately with `npm run typecheck`)
  typescript: {
    ignoreBuildErrors: true,
  },

  // Skip ESLint during build
  eslint: {
    ignoreDuringBuilds: true,
  },

  // ─── Performance: Turbopack for dev (10-50x faster HMR) ────────────────────
  // Uncomment the next line if using Next.js 14.2+ with --turbo flag:
  // experimental: { turbo: {} },

  // ─── Performance: Reduce module graph size ──────────────────────────────────
  experimental: {
    optimizePackageImports: [
      '@tremor/react',
      '@heroicons/react',
      'react-icons',
      'lucide-react',
      'date-fns',
      'lodash',
      'recharts',
    ],
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
      // Keep UI backend API — proxied to Keep service
      // Exclude CopilotKit API route (handled by Next.js route handler)
      {
        source: '/api/:path((?!copilotkit).*)',
        destination: 'http://cv-keep:8007/:path*',
      },
      // Keep UI backend route (used by Keep UI client via /backend prefix)
      {
        source: '/backend/:path*',
        destination: 'http://cv-keep:8007/:path*',
      },
    ];
  },

  // ─── Security Headers ───────────────────────────────────────────────────────
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://accounts.google.com",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' https://fonts.gstatic.com",
              "img-src 'self' data: blob: https://*.googleapis.com https://*.googleusercontent.com",
              "connect-src 'self' http://localhost:* ws://localhost:* wss://localhost:* https://*.copilotkit.ai https://cdn.copilotkit.ai https://api.copilotkit.ai https://accounts.google.com https://oauth2.googleapis.com https://www.googleapis.com",
              "frame-src 'self' https://accounts.google.com",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self' https://accounts.google.com https://github.com",
            ].join('; '),
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
