import { NextRequest, NextResponse } from 'next/server';

// Step 3: verify TOTP code → creates admin account
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const backendUrl = 'https://api.styxproxy.com/api/admin/auth/setup/complete-totp';
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: 'Failed to reach backend server' },
      { status: 503 }
    );
  }
}
