import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Proxy /api/admin calls to the backend — eliminates CORS issues for admin API calls
// since the browser always talks to the same origin (styxproxy.com)
export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith('/api/admin/')) {
    const url = request.nextUrl.clone();
    url.host = 'api.styxproxy.com';
    url.protocol = 'https:';

    const response = NextResponse.rewrite(url);
    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/api/admin/:path*'],
};
