import { NextRequest, NextResponse } from 'next/server';

// Vercel proxy for Charon.
//
// Browser posts to /api/charon/reply (relative).
// This route forwards to the FastAPI backend (configured via env var),
// redacting the user's IP before forwarding — Charon's policy is that
// customer IPs never enter the LLM pipeline.
//
// When n8n is wired in, replace the direct backend call here with a
// webhook into n8n's Charon workflow. Nothing else in the system
// needs to change.

export const dynamic = 'force-dynamic';

const BACKEND = process.env.BACKEND_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    let payload: any;
    try {
      payload = await request.json();
    } catch {
      return NextResponse.json({ error: 'invalid JSON body' }, { status: 400 });
    }

    if (!payload || typeof payload.user_message !== 'string' || !payload.user_message.trim()) {
      return NextResponse.json({ error: 'user_message is required' }, { status: 400 });
    }

    // Enforce payload safety: limit message length and shape.
    const safe = {
      channel: typeof payload.channel === 'string' ? payload.channel.slice(0, 32) : 'web',
      conversation_id: typeof payload.conversation_id === 'string' ? payload.conversation_id.slice(0, 64) : undefined,
      user_message: payload.user_message.slice(0, 4000),
      history: Array.isArray(payload.history)
        ? payload.history
            .filter((m: any) => m && typeof m.content === 'string' && ['user', 'assistant', 'system'].includes(m.role))
            .slice(-12)
            .map((m: any) => ({ role: m.role, content: m.content.slice(0, 4000) }))
        : [],
    };

    // Forward to FastAPI without forwarding the customer's IP.
    const resp = await fetch(`${BACKEND.replace(/\/+$/, '')}/api/v1/charon/reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(safe),
      cache: 'no-store',
    });

    const text = await resp.text();
    let data: any;
    try {
      data = JSON.parse(text);
    } catch {
      return NextResponse.json(
        { error: `backend returned non-JSON (${resp.status}): ${text.slice(0, 200)}` },
        { status: 502 },
      );
    }

    if (!resp.ok) {
      return NextResponse.json(
        { error: data?.error || `backend returned ${resp.status}` },
        { status: resp.status },
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (err) {
    return NextResponse.json(
      { error: `proxy failed: ${err instanceof Error ? err.message : 'unknown'}` },
      { status: 500 },
    );
  }
}

export async function GET() {
  return NextResponse.json(
    { error: 'POST to this endpoint. Charon is on the other side.' },
    { status: 405 },
  );
}