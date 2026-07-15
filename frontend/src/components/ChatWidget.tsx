'use client';

/**
 * ChatWidget — Charon support chatbot with proactive behavioral triggers.
 *
 * Extends the original widget with:
 *  - SessionTracker: anonymous page visits, dwell time, scroll depth, cart state
 *  - TriggerEngine: evaluates 9 behavioral triggers every 5s
 *  - Reach-out bubble: contextual proactive message based on user behavior
 *  - Learning: reports outcomes (opened/dismissed/ignored) to backend for weight learning
 *
 * All tracking is anonymous — no PII, no cookies, sessionStorage only.
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
  trigger_id?: string; // which trigger prompted this conversation
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

/** Report a trigger outcome to the backend (silent failure). */
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
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const [fabX, setFabX] = useState(-1);
  const dragState = useRef({ dragging: false, moved: false, startX: 0, startY: 0, startFabX: 0 });
  const pathname = usePathname();

  // ── Behavioral awareness ─────────────────────────────────────────────
  const trackerRef = useRef<SessionTracker | null>(null);
  const engineRef = useRef<TriggerEngine | null>(null);

  // Current active trigger bubble
  const [activeTrigger, setActiveTrigger] = useState<Trigger | null>(null);
  const [showTriggerBubble, setShowTriggerBubble] = useState(false);

  // Track if we've shown the initial reach-out (6s)
  const [showInitialReachOut, setShowInitialReachOut] = useState(false);
  const initialTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ignoreTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Refs to current state (avoid stale closures in intervals)
  const isOpenRef = useRef(false);
  const activeTriggerRef = useRef<Trigger | null>(null);
  const pathnameRef = useRef(pathname);
  isOpenRef.current = isOpen;
  activeTriggerRef.current = activeTrigger;
  pathnameRef.current = pathname;

  // ── Initialize tracker + engine once ────────────────────────────────
  useEffect(() => {
    if (!trackerRef.current) {
      trackerRef.current = new SessionTracker();
      trackerRef.current.start();
      engineRef.current = new TriggerEngine(trackerRef.current);
    }
  }, []);

  // ── Track page visits ─────────────────────────────────────────────
  useEffect(() => {
    trackerRef.current?.onPageVisit(pathname);
    // Dismiss any trigger bubble on navigation
    setShowTriggerBubble(false);
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

  // ── Track cart state via custom event ──────────────────────────────
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

  // ── Initial reach-out at 6s ────────────────────────────────────────
  useEffect(() => {
    // Don't show if user already opened chat
    if (sessionStorage.getItem('charon_reachout_seen')) return;

    initialTimerRef.current = setTimeout(() => {
      if (!isOpenRef.current) {
        setShowInitialReachOut(true);
        sessionStorage.setItem('charon_reachout_seen', '1');
      }
    }, 6000);

    return () => {
      if (initialTimerRef.current) clearTimeout(initialTimerRef.current);
    };
  }, []);

  // ── Trigger evaluation loop (every 5s) ───────────────────────────
  useEffect(() => {
    const interval = setInterval(async () => {
      if (isOpenRef.current) return; // don't intrude while chat is open
      if (!engineRef.current || !trackerRef.current) return;

      // Refresh weights from backend (cached)
      await engineRef.current.refreshWeights();

      // Evaluate all triggers
      const trigger = engineRef.current.evaluate(pathnameRef.current);
      if (!trigger) return;

      // Fire it
      trackerRef.current.markTriggerFired(trigger.id);
      setActiveTrigger(trigger);
      setShowTriggerBubble(true);

      // Auto-dismiss after 8s if ignored
      if (ignoreTimerRef.current) clearTimeout(ignoreTimerRef.current);
      ignoreTimerRef.current = setTimeout(() => {
        setShowTriggerBubble(false);
        void reportOutcome(trigger.id, 'ignored');
      }, 8000);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // ── Exit-intent detection (desktop only) ──────────────────────────
  useEffect(() => {
    const onMouseLeave = (e: MouseEvent) => {
      if (e.clientY <= 5 && !isOpenRef.current && engineRef.current && trackerRef.current) {
        const trigger = engineRef.current.evaluate(pathnameRef.current);
        if (
          trigger?.id === 'exit_intent' &&
          trackerRef.current.canFire('exit_intent', trigger.cooldownMs)
        ) {
          trackerRef.current.markTriggerFired(trigger.id);
          setActiveTrigger(trigger);
          setShowTriggerBubble(true);

          if (ignoreTimerRef.current) clearTimeout(ignoreTimerRef.current);
          ignoreTimerRef.current = setTimeout(() => {
            setShowTriggerBubble(false);
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

  // ── Send message ──────────────────────────────────────────────────
  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isBusy) return;

    const currentTrigger = activeTriggerRef.current;

    setMessages(prev => [
      ...prev,
      { id: newId(), role: 'user', content: trimmed, ts: Date.now(), trigger_id: currentTrigger?.id },
    ]);
    setInput('');
    setIsBusy(true);

    // Dismiss trigger bubble when user engages
    setShowTriggerBubble(false);
    if (currentTrigger) {
      void reportOutcome(currentTrigger.id, 'opened_chat');
      trackerRef.current?.dismissTrigger(currentTrigger.id);
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
          trigger_id: currentTrigger?.id, // context for Charon
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
          content: 'I\u2019m having trouble reaching the support backend. Please email oyebiyiayomide30@gmail.com while we resolve this.',
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

  // ── Bubble interaction handlers ──────────────────────────────────
  const handleTriggerOpen = () => {
    const t = activeTriggerRef.current;
    setShowTriggerBubble(false);
    setIsOpen(true);
    if (t) {
      void reportOutcome(t.id, 'opened_chat');
    }
  };

  const handleTriggerDismiss = () => {
    const t = activeTriggerRef.current;
    setShowTriggerBubble(false);
    if (t) {
      trackerRef.current?.dismissTrigger(t.id);
      void reportOutcome(t.id, 'dismissed');
    }
    sessionStorage.setItem('charon_reachout_seen', '1');
  };

  const handleInitialOpen = () => {
    setShowInitialReachOut(false);
    setIsOpen(true);
  };

  const handleInitialDismiss = () => {
    setShowInitialReachOut(false);
    sessionStorage.setItem('charon_reachout_seen', '1');
  };

  // ── Positions ─────────────────────────────────────────────────────
  const fabStyle: React.CSSProperties = fabX === -1
    ? { bottom: 24, right: 24 }
    : { bottom: 24, left: fabX, right: 'auto' };

  const bubbleStyle: React.CSSProperties = fabX === -1
    ? { bottom: 88, right: 24 }
    : { bottom: 88, left: fabX, right: 'auto' };

  // Determine which bubble to show (behavioral trigger takes priority)
  const showBubble = showTriggerBubble || showInitialReachOut;
  const bubbleMessage = activeTrigger?.message ?? "Need help with your proxy? I'm online.";
  const bubbleOnClick = showTriggerBubble ? handleTriggerOpen : handleInitialOpen;
  const bubbleOnDismiss = showTriggerBubble ? handleTriggerDismiss : handleInitialDismiss;

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
                <p className="text-xs text-[var(--muted)]">Anonymous support \u00b7 escalating only when needed</p>
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
          {/* Reach-out bubble */}
          {showBubble && (
            <button
              onClick={bubbleOnClick}
              className="fixed z-[9997] animate-reach-out"
              style={bubbleStyle}
              aria-label="Chat with Charon"
            >
              <div className="relative flex items-center gap-2 pl-3 pr-4 py-2.5 bg-[var(--card)] border border-[var(--border)] rounded-2xl shadow-xl max-w-[220px]">
                {/* Green accent line */}
                <div className="absolute left-0 top-3 bottom-3 w-0.5 rounded-full bg-[var(--primary)]" />
                {/* Avatar */}
                <div className="w-7 h-7 rounded-full overflow-hidden shrink-0 bg-[var(--primary)]">
                  <Image src="/chatbot-logo.png" alt="Charon" width={28} height={28} className="w-full h-full object-cover" />
                </div>
                <div className="text-left">
                  <p className="text-xs font-bold leading-tight">Charon here</p>
                  <p className="text-[10px] text-[var(--muted)] leading-tight mt-0.5">{bubbleMessage}</p>
                </div>
                {/* Dismiss */}
                <button
                  onClick={e => { e.stopPropagation(); bubbleOnDismiss(); }}
                  className="ml-1 w-5 h-5 rounded-full flex items-center justify-center text-[var(--muted)] hover:text-[var(--foreground)] shrink-0"
                  aria-label="Dismiss"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              {/* Bubble pointer */}
              <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 rotate-45 bg-[var(--card)] border-l border-b border-[var(--border)]" />
            </button>
          )}

          {/* FAB with breathing halo */}
          <button
            onClick={() => setIsOpen(true)}
            className="fixed z-[9998] w-12 h-12 rounded-full bg-[var(--primary)] text-black shadow-lg flex items-center justify-center transition-transform active:scale-95 charon-fab"
            style={fabStyle}
            aria-label="Open Charon support"
          >
            <span className="absolute inset-0 rounded-full charon-halo charon-halo--1" />
            <span className="absolute inset-0 rounded-full charon-halo charon-halo--2" />
            <div className="relative z-10 w-10 h-10 rounded-full overflow-hidden">
              <Image src="/chatbot-logo.png" alt="Charon" width={40} height={40} className="w-full h-full object-cover" />
            </div>
          </button>
        </>
      )}
    </>
  );
}

// ── Message Bubble ───────────────────────────────────────────────────────

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
                {tc.tool}(
                {Object.entries(tc.params ?? {}).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')}
                )
                {tc.error && <span className="text-red-400"> \u2014 error: {tc.error}</span>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
