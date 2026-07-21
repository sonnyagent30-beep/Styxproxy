import { NextRequest, NextResponse } from 'next/server';

const BACKEND = 'https://api.styxproxy.com';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': 'https://styxproxy.com',
  'Access-Control-Allow-Credentials': 'true',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS',
  'Access-Control-Allow-Headers': 'Authorization, Content-Type',
  'Access-Control-Max-Age': '86400',
};

export async function OPTIONS(): Promise<NextResponse> {
  return new NextResponse(null, { status: 204, headers: CORS_HEADERS });
}

async function proxy(request: NextRequest, pathSegments: string[]): Promise<NextResponse> {
  const { path } = { path: pathSegments };
  const method = request.method;
  const pathStr = path.join('/');
  const url = new URL(request.url);
  const backendUrl = `${BACKEND}/${pathStr}${url.search}`;

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    const auth = request.headers.get('authorization');
    if (auth) headers['Authorization'] = auth;

    const fetchOptions: RequestInit = { method, headers };

    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      const text = await request.text();
      fetchOptions.body = text;
    }

    const response = await fetch(backendUrl, fetchOptions);
    const body = await response.text();
    const contentType = response.headers.get('content-type') || 'application/json';

    const resp = new NextResponse(body, {
      status: response.status,
      headers: { 'Content-Type': contentType, ...CORS_HEADERS },
    });

    // Proxy: set HttpOnly cookie for auth responses (bypasses Vercel cross-origin Secure-cookie strip)
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) {
      // Backend sends Set-Cookie with token; forward as-is
      resp.headers.set('Set-Cookie', setCookie);
    } else if (
      (pathStr.endsWith('/login/step2') || pathStr.endsWith('/setup')) &&
      response.ok
    ) {
      // Extract token from response body and set cookie via proxy (same-origin)
      try {
        const data = JSON.parse(body);
        if (data.access_token) {
          const cookieMaxAge = 60 * 60 * 24; // 24 hours
          const cookieValue = `admin_token=${data.access_token}; HttpOnly; SameSite=Strict; Max-Age=${cookieMaxAge}; Path=/`;
          resp.headers.set('Set-Cookie', cookieValue);
        }
      } catch {}
    }

    return resp;
  } catch (error) {
    console.error(`Proxy error [${method}] ${backendUrl}:`, error);
    return NextResponse.json(
      { error: 'Backend unreachable' },
      { status: 503, headers: CORS_HEADERS }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxy(request, path);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxy(request, path);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxy(request, path);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxy(request, path);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxy(request, path);
}

export async function HEAD(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxy(request, path);
}
