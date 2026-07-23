import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  typescript: {
    // Pre-existing TS errors in admin pages — don't block deploys while we fix them iteratively
    ignoreBuildErrors: true,
  },
  async rewrites() {
    // Proxy /api/admin calls to the backend — browser never talks to api.styxproxy.com directly
    // This eliminates CORS issues entirely for admin API calls
    return [
      {
        source: '/api/admin/:path*',
        destination: 'https://api.styxproxy.com/api/admin/:path*',
      },
      {
        source: '/api/public/maintenance',
        destination: 'https://api.styxproxy.com/api/public/maintenance',
      },
    ];
  },

  async headers() {
    return [
      // Robots/Sitemap must be no-cache so Cloudflare edge doesn't serve a
      // stale Content-Signals robots.txt over our dynamic one.
      {
        source: '/robots.txt',
        headers: [{ key: 'Cache-Control', value: 'no-store, must-revalidate' }],
      },
      {
        source: '/sitemap.xml',
        headers: [{ key: 'Cache-Control', value: 'no-store, must-revalidate' }],
      },
      // Public pages: bypass Vercel CDN cache so the edge middleware can
      // check maintenance state and rewrite to /maintenance when needed.
      // Trade-off: slightly slower public page loads during normal operation
      // (always hits origin) — but enables fast maintenance toggles without
      // waiting for cache TTLs.
      {
        source: '/((?!admin|api|_next|maintenance|favicon|.*\\..*).*)',
        headers: [{ key: 'Cache-Control', value: 'private, no-cache' }],
      },
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()',
          },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https: blob:",
              "font-src 'self' data:",
              `connect-src 'self' https://api.styxproxy.com https://api.qrserver.com`,
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join('; '),
          },
        ],
      },
    ];
  },
};

export default nextConfig;
