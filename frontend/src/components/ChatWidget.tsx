'use client';

/**
 * ChatWidget — Charon support chatbot with behavioral awareness.
 *
 * Charon is quiet during payment/checkout flows (customer is in a transaction).
 * On all other pages, Charon watches anonymous session behavior and may reach out
 * once — a single contextual prompt, never repeated until cooldown expires.
 *
 * Tracking is fully anonymous: no PII, sessionStorage only, no cookies.
 * Outreach is suppressed on /order, /thank-you, /preview, /receipt.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { SessionTracker } from '@/lib/SessionTracker';
import { TriggerEngine, Trigger } from '@/lib/TriggerEngine';

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

/** Anonymous session ID — random, no PII, sessionStorage only. */
function getSessionId(): string {
  const key = 'charon_session_id';
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = 'sess_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem(key, id);
  }
  return id;
}

/** Report trigger outcome to backend for aggregate learning (silent failure). */
async function reportOutcome(triggerId: string, outcome: string) {
  const sessionId = getSessionId();
  try {
    await fetch('/api/charon/trigger-event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, trigger_id: triggerId, outcome }),
    });
  } catch {
    // never block UX for analytics
  }
}

export default function ChatWidget() {
  // Spec: public-only. Suppress on any admin/superadmin/manage route.
  // The widget never even opens if the user shouldn't see it.
  const pathname = usePathname();
  // P0 spec: Charon must NEVER render on admin / superadmin / manage / operator
  // surfaces. Block-list is centralised here so the public-only rule is
  // enforced in one place.
  const isBlocked = ["admin", "superadmin", "manage", "login", "admin-setup"].some(
    (p) => pathname === "/" + p || (pathname != null && (pathname.startsWith("/" + p + "/") || pathname.startsWith("/" + p)))
  );
  if (isBlocked) return null;
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const [fabX, setFabX] = useState(-1);
  const dragState = useRef({ dragging: false, moved: false, startX: 0, startY: 0, startFabX: 0 });

  // ── Behavioral awareness ───────────────────────────────────────────
  const trackerRef = useRef<SessionTracker | null>(null);
  const engineRef = useRef<TriggerEngine | null>(null);
  const [activeTrigger, setActiveTrigger] = useState<Trigger | null>(null);
  const [showBubble, setShowBubble] = useState(false);
  const ignoreTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // pathname already declared at top of component for public-only gating

  // ── Public-only gating (P1-1 Jul 22 2026) ─────────────────────────
  // Charon must NEVER appear on auth/admin/internal pages. Mounting the
  // widget there would (a) leak the AI to admins who don't need it,
  // (b) make admin sessions pollute Charon's anonymous metrics with
  // non-customer traffic, and (c) expose the LLM proxy to admin
  // sessions that should go through the superadmin-only endpoints.
  if (
    pathname.startsWith('/admin') ||
    pathname.startsWith('/login') ||
    pathname.startsWith('/setup') ||
    pathname.startsWith('/superadmin')
  ) {
    return null;
  }

  // Refs to avoid stale closures in intervals
  const isOpenRef = useRef(false);
  const activeTriggerRef = useRef<Trigger | null>(null);
  const pathnameRef = useRef(pathname);
  isOpenRef.current = isOpen;
  activeTriggerRef.current = activeTrigger;
  pathnameRef.current = pathname;

  // ── Init tracker + engine once ────────────────────────────────────
  useEffect(() => {
    if (!trackerRef.current) {
      trackerRef.current = new SessionTracker();
      engineRef.current = new TriggerEngine(trackerRef.current);
    }
  }, []);

  // ── Track page visits ─────────────────────────────────────────────
  useEffect(() => {
    trackerRef.current?.onPageVisit(pathname);
    // Dismiss bubble on any navigation
    setShowBubble(false);
    setActiveTrigger(null);
    if (ignoreTimerRef.current) clearTimeout(ignoreTimerRef.current);
  }, [pathname]);

  // ── Track scroll depth ─────────────────────────────────────────────
  useEffect(() => {
    const onScroll = () => {
      const scrolled = window.scrollY + window.innerHeight;
      const total = document.documentElement.scrollHeight;
      if (scrolled >= total - 120) {
        trackerRef.current?.onScrollBottom(pathnameRef.current);
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // ── Track cart events ─────────────────────────────────────────────
  useEffect(() => {
    const onCartAdd = () => trackerRef.current?.onCartAdd();
    const onCartClear = () => trackerRef.current?.onCartClear();
    window.addEventListener('cart-add', onCartAdd);
    window.addEventListener('cart-clear', onCartClear);
    return () => {
      window.removeEventListener('cart-add', onCartAdd);
      window.removeEventListener('cart-clear', onCartClear);
    };
  }, []);

  // ── Trigger evaluation loop (every 5s) — suppressed on payment pages ─
  useEffect(() => {
    const interval = setInterval(async () => {
      if (isOpenRef.current) return; // don't intrude while chat is open
      if (!engineRef.current || !trackerRef.current) return;

      // Refresh weights from backend (cached after first load)
      await engineRef.current.refreshWeights();

      // evaluate() already returns null on payment pages
      const trigger = engineRef.current.evaluate(pathnameRef.current);
      if (!trigger) return;

      // Fire
      trackerRef.current.markTriggerFired(trigger.id);
      setActiveTrigger(trigger);
      setShowBubble(true);

      // Auto-dismiss after 8s if ignored
      if (ignoreTimerRef.current) clearTimeout(ignoreTimerRef.current);
      ignoreTimerRef.current = setTimeout(() => {
        setShowBubble(false);
        void reportOutcome(trigger.id, 'ignored');
      }, 8000);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // ── Exit-intent detection (desktop only) — suppressed on payment pages ─
  useEffect(() => {
    const onMouseLeave = (e: MouseEvent) => {
      if (e.clientY <= 5 && !isOpenRef.current && engineRef.current && trackerRef.current) {
        const trigger = engineRef.current.evaluate(pathnameRef.current);
        if (
          trigger?.id === 'exit_intent' &&
          trackerRef.current.canFire('exit_intent', (trigger.cooldownMs ?? 5 * 60 * 1000))
        ) {
          trackerRef.current.markTriggerFired(trigger.id);
          setActiveTrigger(trigger);
          setShowBubble(true);

          if (ignoreTimerRef.current) clearTimeout(ignoreTimerRef.current);
          ignoreTimerRef.current = setTimeout(() => {
            setShowBubble(false);
            void reportOutcome(trigger.id, 'ignored');
          }, 8000);
        }
      }
    };
    document.addEventListener('mouseleave', onMouseLeave);
    return () => document.removeEventListener('mouseleave', onMouseLeave);
  }, []);

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

  // ── Open chat ──────────────────────────────────────────────────────
  const openChat = useCallback(() => {
    const t = activeTriggerRef.current;
    setShowBubble(false);
    if (t) {
      void reportOutcome(t.id, 'opened_chat');
    }
    setIsOpen(true);
  }, []);

  // ── Dismiss bubble ────────────────────────────────────────────────
  const dismissBubble = useCallback(() => {
    const t = activeTriggerRef.current;
    setShowBubble(false);
    if (t) {
      trackerRef.current?.dismissTrigger?.(t.id);
      void reportOutcome(t.id, 'dismissed');
    }
  }, []);

  // ── Send message ──────────────────────────────────────────────────
  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isBusy) return;

    const t = activeTriggerRef.current;

    setMessages(prev => [
      ...prev,
      { id: newId(), role: 'user', content: trimmed, ts: Date.now() },
    ]);
    setInput('');
    setIsBusy(true);

    // Dismiss any trigger bubble when user types
    setShowBubble(false);
    if (t) {
      void reportOutcome(t.id, 'opened_chat');
    }

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
  }, [isBusy, messages]);

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

  const toggleOpen = (open: boolean) => {
    if (!open && dragState.current.moved) return;
    dragState.current.moved = false;
    setIsOpen(open);
  };

  // ── Positions ─────────────────────────────────────────────────────
  const fabStyle: React.CSSProperties = fabX === -1
    ? { bottom: 24, right: 24 }
    : { bottom: 24, left: fabX, right: 'auto' };

  const bubbleStyle: React.CSSProperties = fabX === -1
    ? { bottom: 88, right: 24 }
    : { bottom: 88, left: fabX, right: 'auto' };

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

      {/* ── FAB + Reach-out bubble ──────────────────────────────── */}
      {!isOpen && (
        <>
          {/* Behavioral reach-out bubble */}
          {showBubble && activeTrigger && (
            <button
              onClick={openChat}
              className="fixed z-[9997] animate-reach-out"
              style={bubbleStyle}
              aria-label="Chat with Charon"
            >
              <div className="relative flex items-center gap-2 pl-3 pr-4 py-2.5 bg-[var(--card)] border border-[var(--border)] rounded-2xl shadow-xl max-w-[240px]">
                <div className="absolute left-0 top-3 bottom-3 w-0.5 rounded-full bg-[var(--primary)]" />
                <div className="w-7 h-7 rounded-full overflow-hidden shrink-0 bg-[var(--primary)]">
                  <Image src="/chatbot-logo.png" alt="Charon" width={28} height={28} className="w-full h-full object-cover" />
                </div>
                <p className="text-sm text-[var(--foreground)] text-left leading-snug">
                  {activeTrigger.message}
                </p>
                <button
                  onClick={e => { e.stopPropagation(); dismissBubble(); }}
                  className="shrink-0 w-6 h-6 flex items-center justify-center rounded-full hover:bg-[var(--card-hover)] text-[var(--muted)]"
                  aria-label="Dismiss"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </button>
          )}

          {/* FAB — uses the Charon avatar (chatbot-logo.png) so the floating
              button matches the avatar inside the chat panel header. */}
          <button
            onClick={openChat}
            className="fixed z-[9998] charon-fab w-14 h-14 rounded-full bg-[var(--primary)] overflow-hidden flex items-center justify-center shadow-lg hover:scale-105 transition-transform"
            style={fabStyle}
            aria-label="Open chat with Charon"
          >
            <Image src="/chatbot-logo.png" alt="Charon" width={56} height={56} className="w-full h-full object-cover" />
          </button>
        </>
      )}
    </>
  );
}

/* ── MessageBubble ───────────────────────────────────────────────────── */
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
