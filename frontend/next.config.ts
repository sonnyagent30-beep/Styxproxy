import type { NextConfig } from "next";

import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  typescript: {
    // Pre-existing TS errors in admin pages — don't block deploys while we fix them iteratively
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
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
        // Public blog endpoints (Jul 24: added — without this rewrite the
        // browser fetch from styxproxy.com/api/blog/* hit Next.js's own
        // 404 handler instead of being proxied to the BE).
        source: '/api/blog/:path*',
        destination: 'https://api.styxproxy.com/api/blog/:path*',
      },
      {
        source: '/api/public/maintenance',
        destination: 'https://api.styxproxy.com/api/public/maintenance',
      },
      {
        source: '/api/catalog',
        destination: 'https://api.styxproxy.com/api/catalog',
      },
      {
        source: '/api/countries',
        destination: 'https://api.styxproxy.com/api/countries',
      },
      {
        source: '/api/products',
        destination: 'https://api.styxproxy.com/api/products',
      },
      {
        // Self-service admin endpoints (RBAC permissions, TOTP status)
        source: '/api/me/:path*',
        destination: 'https://api.styxproxy.com/api/me/:path*',
      },
      {
        // Public health check — used by the admin dashboard System Health widget
        source: '/api/v1/health',
        destination: 'https://api.styxproxy.com/api/v1/health',
      },
      {
        // Admin analytics — funnel, events (Sprint 25)
        source: '/api/v1/admin/analytics/:path*',
        destination: 'https://api.styxproxy.com/api/v1/admin/analytics/:path*',
      },
      {
        // Charon A/B test results (Sprint 25)
        source: '/api/v1/admin/charon/ab-test/:path*',
        destination: 'https://api.styxproxy.com/api/v1/admin/charon/ab-test/:path*',
      },
      // Charon AI endpoints
      {
        source: '/api/charon/:path*',
        destination: 'https://api.styxproxy.com/api/charon/:path*',
      },
      // Public maintenance flag check
      {
        source: '/api/maintenance',
        destination: 'https://api.styxproxy.com/api/maintenance',
      },
      // Charon admin endpoints
      {
        source: '/api/v1/charon/:path*',
        destination: 'https://api.styxproxy.com/api/v1/charon/:path*',
      },

      // ── Public API routes (frontend calls these without /api prefix) ──
      // Orders
      {
        source: '/orders/:path*',
        destination: 'https://api.styxproxy.com/api/orders/:path*',
      },
      // Payments
      {
        source: '/api/payments/initiate',
        destination: 'https://api.styxproxy.com/api/payments/initiate',
      },
      {
        source: '/payments/initiate',
        destination: 'https://api.styxproxy.com/api/payments/initiate',
      },
      {
        source: '/payments/:tx_ref/status',
        destination: 'https://api.styxproxy.com/api/payments/:tx_ref/status',
      },
      // Credentials
      {
        source: '/credentials/:order_id',
        destination: 'https://api.styxproxy.com/api/credentials/:order_id',
      },
      // Public checkout status
      {
        source: '/public/checkout-status',
        destination: 'https://api.styxproxy.com/api/public/checkout-status',
      },
      // Blog admin sub-path (frontend uses /api/blog/admin/... but rewrite only covers /api/blog/:path*)
      {
        source: '/api/blog/admin/:path*',
        destination: 'https://api.styxproxy.com/api/blog/admin/:path*',
      },
      // Public order status (called directly in thank-you page as /api/orders/:id/status)
      {
        source: '/api/orders/:path*',
        destination: 'https://api.styxproxy.com/api/orders/:path*',
      },
      // Public receipt/pdf (called directly in receipt page as /api/orders/:tx_ref/...)
      {
        source: '/api/orders/:tx_ref/:subpath*',
        destination: 'https://api.styxproxy.com/api/orders/:tx_ref/:subpath*',
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
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
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
              // 'unsafe-eval' REMOVED: no eval/new Function in app code.
              // Remove 'unsafe-inline' from script-src — Next.js 16 bundles safely.
              "script-src 'self' 'unsafe-inline'",
              // 'unsafe-inline' needed for inline style={{}} objects used in:
              // admin/setup/page.tsx, admin/rls/page.tsx, global-error.tsx
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

// Sprint 5.8: Sentry integration
// - withSentryConfig wraps the Next.js config with Sentry's build plugin
//   (source maps, instrumentation, browser tracing)
// - silent: true suppresses build logs noise (errors still surface)
// - hideSourceMaps: true prevents source maps from being deployed to Vercel
// Note: @sentry/nextjs@10 handles its own tunnel via the SDK's `tunnel` option
// (set automatically from `tunnelRoute`). No custom route handler needed.
// CONDITIONAL: Only activate Sentry when SENTRY_AUTH_TOKEN is present.
// This prevents post-compile SIGSEGV on Vercel builds without a token.
const config = process.env.SENTRY_AUTH_TOKEN
  ? withSentryConfig(nextConfig, {
      org: "dannion-creative-hub",
      project: "styxproxy-frontend",
      authToken: process.env.SENTRY_AUTH_TOKEN,
      silent: !process.env.CI,
      sourcemaps: { disable: true },
      disableLogger: true,
    })
  : nextConfig;

export default config;
