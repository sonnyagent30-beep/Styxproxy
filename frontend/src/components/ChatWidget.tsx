'use client';

/**
 * ChatWidget — thin client for the Charon backend agent.
 *
 * Responsibilities:
 *   - Render a draggable, mobile-friendly chat surface.
 *   - POST each user message to /api/charon/reply.
 *   - Render the assistant response and the tool-call trail if any.
 *   - Stream responses when /api/charon/reply/stream is reachable; fall
 *     back to one-shot /api/charon/reply otherwise.
 *
 * What this widget is NOT:
 *   - The intelligence. That's in the backend (services/charon).
 *   - The marketing copy. That's authored in /legal, /about, etc., and
 *     retrieved by the agent via RAG over the same Markdown files.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import Image from 'next/image';

type Role = 'user' | 'assistant' | 'system';

interface ToolCall {
  tool: string;
  params?: Record<string, unknown>;
  result?: unknown;
  error?: string;
}

interface Message {
  id: string;
  role: Role;
  content: string;
  escalated?: boolean;
  tool_calls?: ToolCall[];
  ts: number;
}

const newId = () => Math.random().toString(36).slice(2);

const WELCOME: Message = {
  id: 'welcome',
  role: 'assistant',
  content:
    'Hi — I\u2019m Charon. I can help with orders, plan details, payment status, and proxy troubleshooting. What can I help you with?',
  ts: 0,
};

interface ChatReplyResponse {
  text: string;
  scenario_id?: string | null;
  escalated?: boolean;
  tool_calls?: ToolCall[];
  tokens_used?: number;
  error?: string | null;
}

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const [fabX, setFabX] = useState(-1);
  const dragState = useRef({ dragging: false, moved: false, startX: 0, startY: 0, startFabX: 0 });
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 640;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isBusy]);

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([WELCOME]);
    }
  }, [isOpen, messages.length]);

  useEffect(() => {
    const handler = () => setIsOpen(true);
    window.addEventListener('open-chat-widget', handler);
    return () => window.removeEventListener('open-chat-widget', handler);
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isBusy) return;
    setMessages(prev => [...prev, { id: newId(), role: 'user', content: trimmed, ts: Date.now() }]);
    setInput('');
    setIsBusy(true);

    try {
      const history = messages
        .filter(m => m.id !== 'welcome')
        .map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content }));

      const res = await fetch('/api/charon/reply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          channel: 'web',
          conversation_id: undefined,
          user_message: trimmed,
          history,
        }),
      });

      if (!res.ok) {
        throw new Error(`Charon returned ${res.status}`);
      }

      const data: ChatReplyResponse = await res.json();
      setMessages(prev => [
        ...prev,
        {
          id: newId(),
          role: 'assistant',
          content: data.text || '(Charon returned an empty response.)',
          escalated: data.escalated === true,
          tool_calls: data.tool_calls,
          ts: Date.now(),
        },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: newId(),
          role: 'assistant',
          content:
            'I\u2019m having trouble reaching the support backend. Please email support@styxproxy.com directly while we resolve this.',
          ts: Date.now(),
        },
      ]);
    } finally {
      setIsBusy(false);
    }
  }, [isBusy, messages]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void sendMessage(input);
    }
  };

  // ── drag handler (desktop only) ──────────────────────────────────
  const onHeaderMouseDown = useCallback((e: React.MouseEvent) => {
    if (isMobile) return;
    e.preventDefault();
    dragState.current = {
      dragging: true,
      moved: false,
      startX: e.clientX,
      startY: e.clientY,
      startFabX: fabX === -1 ? window.innerWidth - 80 : fabX,
    };
  }, [isMobile, fabX]);

  const onMouseMove = useCallback((e: MouseEvent) => {
    if (!dragState.current.dragging) return;
    const dx = e.clientX - dragState.current.startX;
    if (Math.abs(dx) > 3) dragState.current.moved = true;
    const newX = Math.max(8, Math.min(window.innerWidth - 64, dragState.current.startFabX + dx));
    setFabX(newX);
  }, []);

  const onMouseUp = useCallback(() => {
    dragState.current.dragging = false;
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, [onMouseMove, onMouseUp]);

  const toggleOpen = (open: boolean) => {
    if (!open && dragState.current.moved) return;
    dragState.current.moved = false;
    setIsOpen(open);
  };

  const fabStyle: React.CSSProperties = fabX === -1
    ? { bottom: 24, right: 24 }
    : { bottom: 24, left: fabX, right: 'auto' };

  return (
    <>
      {isOpen && (
        <div
          className="fixed z-[9999] flex flex-col bg-[var(--background)] rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden"
          style={{
            insetInline: 8,
            top: '50%',
            transform: 'translateY(-50%)',
            height: '80vh',
            maxHeight: 580,
          }}
        >
          <div
            className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--card)]"
            style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
            onMouseDown={onHeaderMouseDown}
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full overflow-hidden shrink-0 bg-[var(--primary)]">
                <Image src="/chatbot-logo.png" alt="Charon" width={36} height={36} className="w-full h-full object-cover" />
              </div>
              <div>
                <p className="font-bold text-sm">Charon</p>
                <p className="text-xs text-[var(--muted)]">Anonymous support · escalating only when needed</p>
              </div>
            </div>
            <button
              onClick={() => toggleOpen(false)}
              className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors shrink-0"
              aria-label="Close chat"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
            {messages.map(m => (
              <MessageBubble key={m.id} msg={m} />
            ))}
            {isBusy && (
              <div className="flex gap-2 items-center text-xs text-[var(--muted)] pl-1">
                <span className="inline-block w-2 h-2 rounded-full bg-[var(--muted)] animate-pulse" />
                <span className="inline-block w-2 h-2 rounded-full bg-[var(--muted)] animate-pulse [animation-delay:0.2s]" />
                <span className="inline-block w-2 h-2 rounded-full bg-[var(--muted)] animate-pulse [animation-delay:0.4s]" />
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form
            onSubmit={e => { e.preventDefault(); void sendMessage(input); }}
            className="shrink-0 flex gap-2 border-t border-[var(--border)] bg-[var(--card)] p-3"
          >
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              rows={1}
              placeholder="Type a message — Enter to send"
              className="flex-1 resize-none px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--primary)]"
              disabled={isBusy}
            />
            <button
              type="submit"
              disabled={isBusy || !input.trim()}
              className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-lg text-sm transition-colors disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      )}

      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed z-[9998] w-12 h-12 rounded-full bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black shadow-lg flex items-center justify-center transition-transform active:scale-95"
          style={fabStyle}
          aria-label="Open Charon support"
        >
          <Image src="/chatbot-logo.png" alt="Charon" width={36} height={36} className="w-9 h-9 rounded-full object-cover" />
        </button>
      )}
    </>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user';
  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md px-3 py-2 text-sm leading-relaxed bg-[var(--primary)] text-black">
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <div className="max-w-[90%] rounded-2xl rounded-bl-md px-3 py-2 text-sm leading-relaxed bg-[var(--card)] border border-[var(--border)]">
        <p className="whitespace-pre-wrap">{msg.content}</p>
      </div>
      {msg.escalated && (
        <div className="text-[10px] px-2 text-[var(--muted)] flex items-center gap-1">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Charon escalated this to the team. You will hear back.</span>
        </div>
      )}
      {msg.tool_calls && msg.tool_calls.length > 0 && (
        <details className="text-[10px] text-[var(--muted)] pl-2 max-w-[90%]">
          <summary className="cursor-pointer">tool calls ({msg.tool_calls.length})</summary>
          <ul className="mt-1 space-y-1 font-mono">
            {msg.tool_calls.map((tc, i) => (
              <li key={i}>
                {tc.tool}({Object.entries(tc.params || {}).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')})
                {tc.error && <span className="text-red-400"> — error: {tc.error}</span>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
