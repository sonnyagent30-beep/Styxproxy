import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Proxy /api/admin calls to the backend — eliminates CORS issues for admin API calls
// since the browser always talks to the same origin (styxproxy.com)
export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;

  // /api/admin/support/* → backend /api/v1/admin/support/* (support API uses v1 prefix)
  if (path.startsWith('/api/admin/support/')) {
    const url = request.nextUrl.clone();
    url.pathname = '/api/v1/admin/support' + path.slice('/api/admin/support'.length);
    url.host = 'api.styxproxy.com';
    url.protocol = 'https:';
    return NextResponse.rewrite(url);
  }

  // Standard /api/admin/* proxy
  if (path.startsWith('/api/admin/')) {
    const url = request.nextUrl.clone();
    url.host = 'api.styxproxy.com';
    url.protocol = 'https:';
    return NextResponse.rewrite(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/api/admin/:path*'],
};