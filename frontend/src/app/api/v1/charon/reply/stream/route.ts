/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

const BACKEND = process.env.BACKEND_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || '';

export async function POST(request: NextRequest) {
  try {
    let payload: any;
    try {
      payload = await request.json();
    } catch {
      return new Response(JSON.stringify({ error: 'invalid JSON body' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (!payload || typeof payload.user_message !== 'string' || !payload.user_message.trim()) {
      return new Response(JSON.stringify({ error: 'user_message is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const safe: Record<string, unknown> = {
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

    if (payload.page_context && typeof payload.page_context === 'object') {
      safe.page_context = payload.page_context;
    }

    // Forward customer identity fields for tool authorization
    if (typeof payload.channel_user_id === 'string' && payload.channel_user_id) {
      safe.channel_user_id = payload.channel_user_id.slice(0, 128);
    }
    if (typeof payload.customer_email === 'string' && payload.customer_email) {
      safe.customer_email = payload.customer_email.slice(0, 256);
    }
    if (typeof payload.customer_phone === 'string' && payload.customer_phone) {
      safe.customer_phone = payload.customer_phone.slice(0, 32);
    }
    if (typeof payload.customer_name === 'string' && payload.customer_name) {
      safe.customer_name = payload.customer_name.slice(0, 128);
    }

    if (!BACKEND) {
      return new Response(
        JSON.stringify({ error: 'Charon backend not configured.' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } },
      );
    }

    const resp = await fetch(`${BACKEND.replace(/\/+$/, '')}/api/v1/charon/reply/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(safe),
    });

    if (!resp.ok) {
      const text = await resp.text();
      return new Response(JSON.stringify({ error: text || `backend ${resp.status}` }), {
        status: resp.status,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const { body } = resp;
    if (!body) {
      return new Response(JSON.stringify({ error: 'no body from backend' }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const transform = new TransformStream({
      async start(controller) {
        const reader = body.getReader();
        const decoder = new TextDecoder();
        const encoder = new TextEncoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              controller.enqueue(encoder.encode(line + '\n'));
            }
          }
        }

        if (buffer.startsWith('data: ')) {
          controller.enqueue(encoder.encode(buffer + '\n'));
        }

        controller.enqueue(encoder.encode('data: [DONE]\n'));
        controller.close();
      },
    });

    return new Response(transform.readable, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: `proxy failed: ${err instanceof Error ? err.message : 'unknown'}` }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
}
