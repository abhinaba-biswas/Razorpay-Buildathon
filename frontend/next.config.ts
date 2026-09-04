import type { NextConfig } from 'next';

const BACKEND_URL = (process.env.BACKEND_URL ?? 'http://localhost:8000').replace(/\/$/, '');

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      // Browser code always uses same-origin /api/* requests. Next.js forwards
      // them server-side, so BACKEND_URL and backend credentials stay private.
      { source: '/api/:path*', destination: `${BACKEND_URL}/:path*` },
    ];
  },
};

export default nextConfig;
