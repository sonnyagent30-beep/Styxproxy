import { NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'https://bunche.railway.app';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res = await fetch(`${API_BASE}/api/v1/charon/trigger-event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) return NextResponse.json({ error: 'upstream error' }, { status: 502 });
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: 'fetch failed' }, { status: 503 });
  }
}
