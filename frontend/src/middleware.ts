import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Edge middleware for Styxproxy frontend.
 *
 * 1. Proxies /api/admin/* requests to the backend (no CORS).
 * 2. When maintenance mode is on, rewrites public pages to /maintenance
 *    so the entire site shows the maintenance page (not 404, not blank).
 *    Admin routes are exempt.
 */

// Routes that must always render normally (admin, auth, maintenance itself)
const ALWAYS_AVAILABLE_PREFIXES = [
  '/admin',
  '/maintenance',
  '/api',
  '/_next',
  '/favicon',
  '/og-image',
  '/header-logo',
  '/footer-logo',
  '/hero-logo',
  '/chatbot-logo',
  '/app-icon',
  '/globe',
  '/file',
  '/blog/rss',
  '/robots.txt',
  '/sitemap.xml',
  '/manifest',
  '/legal',
  '/cookie-policy',
  '/refund-policy',
];

export async function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;

  // 1. /api/admin support proxy
  if (path.startsWith('/api/admin/support/')) {
    const url = request.nextUrl.clone();
    url.pathname = '/api/v1/admin/support' + path.slice('/api/admin/support'.length);
    url.host = 'api.styxproxy.com';
    url.protocol = 'https:';
    return NextResponse.rewrite(url);
  }

  // 2. /api/admin proxy
  if (path.startsWith('/api/admin/')) {
    const url = request.nextUrl.clone();
    url.host = 'api.styxproxy.com';
    url.protocol = 'https:';
    return NextResponse.rewrite(url);
  }

  // 3. Maintenance mode — only for public pages
  if (request.method === 'GET' && !ALWAYS_AVAILABLE_PREFIXES.some((p) => path.startsWith(p))) {
    try {
      // Check the public maintenance endpoint directly via the backend.
      // (Going through /api/public/maintenance would cause a self-rewrite
      // loop or stack-overflow — the edge can talk to the backend directly.)
      const apiHost = request.headers.get('host')?.includes('styxproxy.com')
        ? 'https://api.styxproxy.com'
        : '';  // localhost / preview — call same origin (works in dev)
      const url = apiHost
        ? `${apiHost}/api/public/maintenance`
        : new URL('/api/public/maintenance', request.url).toString();
      const res = await fetch(url, {
        cache: 'no-store',
        signal: AbortSignal.timeout(800),
      });
      if (res.ok) {
        const data = (await res.json()) as { enabled: boolean };
        if (data.enabled) {
          // Rewrite to /maintenance so the page renders
          const rewriteUrl = request.nextUrl.clone();
          rewriteUrl.pathname = '/maintenance';
          return NextResponse.rewrite(rewriteUrl);
        }
      }
    } catch {
      // If maintenance check fails, allow normal render
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (handled above)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - common public files
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)',
  ],
};
