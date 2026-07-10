import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Generate a short correlation ID (8 hex chars)
function generateCorrelationId(): string {
  return Math.random().toString(16).slice(2, 10).padStart(8, '0');
}

export function middleware(request: NextRequest) {
  const requestId = request.headers.get('x-request-id') || generateCorrelationId();
  const response = NextResponse.next();

  // Attach correlation ID to response headers for client + server tracing
  response.headers.set('x-request-id', requestId);
  response.headers.set('x-correlation-id', requestId);

  return response;
}

export const config = {
  // Apply to all routes except static files and Next.js internals
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js|woff|woff2|ttf|otf)).*)',
  ],
};
