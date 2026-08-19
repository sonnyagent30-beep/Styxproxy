import type { NextConfig } from "next";

import { withSentryConfig } from "@sentry/nextjs";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.styxproxy.com";

const nextConfig: NextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return [
      { source: '/api/admin/:path*', destination: `${API_BASE_URL}/api/admin/:path*` },
      { source: '/api/blog/:path*', destination: `${API_BASE_URL}/api/blog/:path*` },
      { source: '/api/public/maintenance', destination: `${API_BASE_URL}/api/public/maintenance` },
      { source: '/api/catalog', destination: `${API_BASE_URL}/api/catalog` },
      { source: '/api/countries', destination: `${API_BASE_URL}/api/countries` },
      { source: '/api/products', destination: `${API_BASE_URL}/api/products` },
      { source: '/api/me/:path*', destination: `${API_BASE_URL}/api/me/:path*` },
      { source: '/api/v1/health', destination: `${API_BASE_URL}/api/v1/health` },
      { source: '/api/v1/admin/analytics/:path*', destination: `${API_BASE_URL}/api/v1/admin/analytics/:path*` },
      { source: '/api/v1/admin/charon/ab-test/:path*', destination: `${API_BASE_URL}/api/v1/admin/charon/ab-test/:path*` },
      { source: '/api/charon/:path*', destination: `${API_BASE_URL}/api/charon/:path*` },
      { source: '/api/maintenance', destination: `${API_BASE_URL}/api/maintenance` },
      { source: '/api/v1/charon/:path*', destination: `${API_BASE_URL}/api/v1/charon/:path*` },
      { source: '/orders/:path*', destination: `${API_BASE_URL}/api/orders/:path*` },
      { source: '/api/payments/initiate', destination: `${API_BASE_URL}/api/payments/initiate` },
      { source: '/payments/initiate', destination: `${API_BASE_URL}/api/payments/initiate` },
      { source: '/payments/:tx_ref/status', destination: `${API_BASE_URL}/api/payments/:tx_ref/status` },
      { source: '/credentials/:order_id', destination: `${API_BASE_URL}/api/credentials/:order_id` },
      { source: '/public/checkout-status', destination: `${API_BASE_URL}/api/public/checkout-status` },
      { source: '/api/blog/admin/:path*', destination: `${API_BASE_URL}/api/blog/admin/:path*` },
      { source: '/api/orders/:path*', destination: `${API_BASE_URL}/api/orders/:path*` },
      { source: '/api/orders/:tx_ref/:subpath*', destination: `${API_BASE_URL}/api/orders/:tx_ref/:subpath*` },
    ];
  },
  async headers() {
    return [
      { source: '/robots.txt', headers: [{ key: 'Cache-Control', value: 'no-store, must-revalidate' }] },
      { source: '/sitemap.xml', headers: [{ key: 'Cache-Control', value: 'no-store, must-revalidate' }] },
      { source: '/((?!admin|api|_next|maintenance|favicon|.*\\..*).*)', headers: [{ key: 'Cache-Control', value: 'private, no-cache' }] },
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()' },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https: blob:",
              "font-src 'self' data:",
              `connect-src 'self' ${API_BASE_URL} https://api.qrserver.com`,
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
