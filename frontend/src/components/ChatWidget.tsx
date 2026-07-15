'use client';

/**
 * ChatWidget — Charon support chatbot.
 *
 * Charon only responds when the customer initiates. No proactive messages,
 * no behavioral tracking, no unsolicited outreach. The customer is in full
 * control of when they engage.
 *
 * Learning happens on the backend when customers open conversations — the
 * trigger_event records the chat open, and the learning cron adjusts weights.
 * This is aggregate learning from conversation open rates, not individual tracking.
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

const newId = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

const WELCOME: Message = {
  id: 'welcome',
  role: 'assistant',
  content:
    'Hi \u2014 I\u2019m Charon. I can help with orders, plan details, payment status, and proxy troubleshooting. What can I help you with?',
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

/** Generate or retrieve the anonymous session ID (no PII). */
function getSessionId(): string {
  const key = 'charon_session_id';
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = 'sess_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem(key, id);
  }
  return id;
}

/** Report a conversation open to the backend for aggregate learning (silent failure). */
async function reportChatOpen() {
  const sessionId = getSessionId();
  try {
    await fetch('/api/charon/trigger-event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        trigger_id: 'chat_opened',
        outcome: 'opened_chat',
      }),
    });
  } catch {
    // never block UX for analytics
  }
}

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const [fabX, setFabX] = useState(-1);
  const dragState = useRef({ dragging: false, moved: false, startX: 0, startY: 0, startFabX: 0 });
  const isBusyRef = useRef(false);
  isBusyRef.current = isBusy;

  // ── Drag handlers ─────────────────────────────────────────────────
  const onHeaderMouseDown = useCallback((e: React.MouseEvent) => {
    if (typeof window !== 'undefined' && window.innerWidth < 640) return;
    e.preventDefault();
    dragState.current = {
      dragging: true,
      moved: false,
      startX: e.clientX,
      startY: e.clientY,
      startFabX: fabX === -1 ? window.innerWidth - 80 : fabX,
    };
  }, [fabX]);

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

  // ── Auto-scroll ───────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isBusy]);

  // ── Show welcome message when chat opens ──────────────────────────
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([WELCOME]);
    }
  }, [isOpen, messages.length]);

  // ── Listen for programmatic open ─────────────────────────────────
  useEffect(() => {
    const handler = () => setIsOpen(true);
    window.addEventListener('open-chat-widget', handler);
    return () => window.removeEventListener('open-chat-widget', handler);
  }, []);

  // ── Open chat (reports open to backend for aggregate learning) ────
  const openChat = useCallback(() => {
    void reportChatOpen(); // fire-and-forget, never blocks UX
    setIsOpen(true);
  }, []);

  // ── Send message ──────────────────────────────────────────────────
  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isBusyRef.current) return;

    setMessages(prev => [
      ...prev,
      { id: newId(), role: 'user', content: trimmed, ts: Date.now() },
    ]);
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

      if (!res.ok) throw new Error(`Charon returned ${res.status}`);
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
    } catch {
      setMessages(prev => [
        ...prev,
        {
          id: newId(),
          role: 'assistant',
          content: 'I\u2019m having trouble reaching the support backend. Please email support@styxproxy.com while we resolve this.',
          ts: Date.now(),
        },
      ]);
    } finally {
      setIsBusy(false);
    }
  }, [messages]);

  const toggleOpen = (open: boolean) => {
    if (!open && dragState.current.moved) return;
    dragState.current.moved = false;
    setIsOpen(open);
  };

  // ── Positions ─────────────────────────────────────────────────────
  const fabStyle: React.CSSProperties = fabX === -1
    ? { bottom: 24, right: 24 }
    : { bottom: 24, left: fabX, right: 'auto' };

  return (
    <>
      {/* ── Chat window ─────────────────────────────────────────── */}
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
          {/* Header */}
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
                <p className="text-xs text-[var(--muted)]">Online \u00b7 Chat to get started</p>
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

          {/* Messages */}
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

          {/* Input */}
          <form
            onSubmit={e => { e.preventDefault(); void sendMessage(input); }}
            className="shrink-0 flex gap-2 border-t border-[var(--border)] bg-[var(--card)] p-3"
          >
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void sendMessage(input);
                }
              }}
              rows={1}
              placeholder="Type a message \u2014 Enter to send"
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

      {/* ── FAB button ────────────────────────────────────────────── */}
      {!isOpen && (
        <button
          onClick={openChat}
          className="fixed z-[9998] charon-fab w-14 h-14 rounded-full flex items-center justify-center shadow-lg hover:scale-105 transition-transform"
          style={fabStyle}
          aria-label="Open chat with Charon"
        >
          <svg className="w-7 h-7 text-black" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </button>
      )}
    </>
  );
}

/* ── MessageBubble ────────────────────────────────────────────────────── */
function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'bg-[var(--primary)] text-black rounded-br-md'
            : 'bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] rounded-bl-md'
        }`}
      >
        {msg.content}
        {msg.escalated && (
          <p className="mt-2 text-xs text-[var(--muted)]">
            A team member has been notified and will follow up via email.
          </p>
        )}
      </div>
    </div>
  );
}
