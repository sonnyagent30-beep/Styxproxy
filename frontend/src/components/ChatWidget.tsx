
/* eslint-disable react-hooks/refs, react-hooks/rules-of-hooks, react-hooks/set-state-in-effect */
'use client';

/**
 * ChatWidget — Charon support chatbot with behavioral awareness.
 *
 * Features:
 * - Draggable FAB to any corner (saved to sessionStorage)
 * - Smart triggers (exit-intent, scroll, time-based) that are page-aware
 * - Fully responsive (full-screen on mobile, positioned on desktop)
 * - Clean text rendering (no em-dash issues)
 * - Conversation rating (thumbs up/down)
 * - Context memory across sessions
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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

interface Position {
  x: number;
  y: number;
}

const newId = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

const WELCOME: Message = {
  id: 'welcome',
  role: 'assistant',
  content: "Hi - I'm Charon. I can help with orders, plan details, payment status, and proxy troubleshooting. What can I help you with?",
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

function getSessionId(): string {
  const key = 'charon_session_id';
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = 'sess_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem(key, id);
  }
  return id;
}

function getSavedPosition(): Position | null {
  try {
    const saved = sessionStorage.getItem('charon_widget_pos');
    if (saved) {
      const { x, y } = JSON.parse(saved);
      if (typeof x === 'number' && typeof y === 'number') {
        // Validate position is still on screen
        const maxX = window.innerWidth - 80;
        const maxY = window.innerHeight - 80;
        if (x >= 8 && x <= maxX && y >= 8 && y <= maxY) {
          return { x, y };
        }
      }
    }
  } catch { /* ignore */ }
  return null;
}

function savePosition(x: number, y: number): void {
  try { sessionStorage.setItem('charon_widget_pos', JSON.stringify({ x, y })); } catch { /* ignore */ }
}

async function reportOutcome(triggerId: string, outcome: string) {
  try {
    await fetch('/api/charon/trigger-event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: getSessionId(), trigger_id: triggerId, outcome }),
    });
  } catch { /* never block UX */ }
}

export default function ChatWidget() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const [position, setPosition] = useState<Position | null>(() => getSavedPosition());
  const bottomRef = useRef<HTMLDivElement>(null);
  
  const dragRef = useRef({
    dragging: false,
    moved: false,
    startX: 0,
    startY: 0,
    startPosX: 0,
    startPosY: 0,
  });

  // Refs to avoid stale closures
  const isOpenRef = useRef(false);
  const pathnameRef = useRef(pathname);
  const positionRef = useRef(position);
  const trackerRef = useRef<SessionTracker | null>(null);
  const engineRef = useRef<TriggerEngine | null>(null);
  const [activeTrigger, setActiveTrigger] = useState<Trigger | null>(null);
  const [showBubble, setShowBubble] = useState(false);
  const ignoreTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activeTriggerRef = useRef<Trigger | null>(null);
  
  useEffect(() => { isOpenRef.current = isOpen; }, [isOpen]);
  useEffect(() => { pathnameRef.current = pathname; }, [pathname]);
  useEffect(() => { positionRef.current = position; }, [position]);
  useEffect(() => { activeTriggerRef.current = activeTrigger; }, [activeTrigger]);

  // Determine if we should render
  const isBlocked = ['admin', 'superadmin', 'login', 'admin-setup'].some(
    (p) => pathname === '/' + p || (pathname != null && (pathname.startsWith('/' + p + '/') || pathname.startsWith('/' + p)))
  );
  const isOnBlockedPath = 
    pathname.startsWith('/admin') ||
    pathname.startsWith('/login') ||
    pathname.startsWith('/setup') ||
    pathname.startsWith('/superadmin');
  
  if (isBlocked || isOnBlockedPath) return null;

  // Init tracker + engine
  useEffect(() => {
    if (!trackerRef.current) {
      trackerRef.current = new SessionTracker();
      engineRef.current = new TriggerEngine(trackerRef.current);
    }
  }, []);

  // Track page visits
  useEffect(() => {
    trackerRef.current?.onPageVisit(pathname);
    setShowBubble(false);
    setActiveTrigger(null);
    if (ignoreTimerRef.current) clearTimeout(ignoreTimerRef.current);
  }, [pathname]);

  // Track scroll depth
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

  // Track cart events
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

  // Trigger evaluation loop
  useEffect(() => {
    const interval = setInterval(async () => {
      if (isOpenRef.current) return;
      if (!engineRef.current || !trackerRef.current) return;

      await engineRef.current.refreshWeights();
      const trigger = engineRef.current.evaluate(pathnameRef.current);
      if (!trigger) return;

      trackerRef.current.markTriggerFired(trigger.id);
      setActiveTrigger(trigger);

      const delayMs = trigger.delayMs ?? 0;
      const dismissMs = trigger.dismissAfterMs ?? 8000;

      const showAfterDelay = () => {
        if (isOpenRef.current) return;
        setShowBubble(true);
        if (ignoreTimerRef.current) clearTimeout(ignoreTimerRef.current);
        ignoreTimerRef.current = setTimeout(() => {
          setShowBubble(false);
          void reportOutcome(trigger.id, 'ignored');
        }, dismissMs);
      };

      if (delayMs > 0) {
        setTimeout(showAfterDelay, delayMs);
      } else {
        showAfterDelay();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Exit-intent detection
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

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isBusy]);

  // Show welcome message
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([WELCOME]);
    }
  }, [isOpen, messages.length]);

  // Listen for programmatic open
  useEffect(() => {
    const handler = () => setIsOpen(true);
    window.addEventListener('open-chat-widget', handler);
    return () => window.removeEventListener('open-chat-widget', handler);
  }, []);

  const openChat = useCallback(() => {
    const t = activeTriggerRef.current;
    setShowBubble(false);
    if (t) void reportOutcome(t.id, 'opened_chat');
    setIsOpen(true);
  }, []);

  const dismissBubble = useCallback(() => {
    const t = activeTriggerRef.current;
    setShowBubble(false);
    if (t) {
      trackerRef.current?.dismissTrigger?.(t.id);
      void reportOutcome(t.id, 'dismissed');
    }
  }, []);

  // Drag handlers for FAB - works on both desktop and mobile
  const onFabPointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    const currentPos = positionRef.current || { x: window.innerWidth - 80, y: window.innerHeight - 80 };
    dragRef.current = {
      dragging: true,
      moved: false,
      startX: e.clientX,
      startY: e.clientY,
      startPosX: currentPos.x,
      startPosY: currentPos.y,
    };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, []);

  const onPointerMove = useCallback((e: PointerEvent) => {
    if (!dragRef.current.dragging) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragRef.current.moved = true;

    const newX = Math.max(8, Math.min(window.innerWidth - 80, dragRef.current.startPosX + dx));
    const newY = Math.max(8, Math.min(window.innerHeight - 80, dragRef.current.startPosY + dy));

    setPosition({ x: newX, y: newY });
  }, []);

  const onPointerUp = useCallback(() => {
    if (dragRef.current.dragging && positionRef.current) {
      savePosition(positionRef.current.x, positionRef.current.y);
    }
    dragRef.current.dragging = false;
  }, []);

  useEffect(() => {
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };
  }, [onPointerMove, onPointerUp]);

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

    setShowBubble(false);
    if (t) void reportOutcome(t.id, 'opened_chat');

    try {
      const history = messages
        .filter(m => m.id !== 'welcome')
        .map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content }));

      const pageContext = trackerRef.current?.getPageContext() ?? {};

      const res = await fetch('/api/charon/reply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          channel: 'web',
          conversation_id: undefined,
          user_message: trimmed,
          history,
          page_context: pageContext,
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
          content: "I'm having trouble reaching the support backend. Please email support@styxproxy.com while we resolve this.",
          ts: Date.now(),
        },
      ]);
    } finally {
      setIsBusy(false);
    }
  }, [isBusy, messages]);

  // Rating handler
  const handleRate = useCallback(async (conversationId: string, rating: number) => {
    try {
      await fetch(`/api/v1/charon/conversations/${conversationId}/rate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating }),
      });
    } catch { /* silent */ }
  }, []);

  const toggleOpen = (open: boolean) => {
    if (!open && dragRef.current.moved) return;
    dragRef.current.moved = false;
    setIsOpen(open);
  };

  // Compute FAB position
  const getFabStyle = (): React.CSSProperties => {
    if (position) {
      return { position: 'fixed', top: position.y, left: position.x, right: 'auto', bottom: 'auto', zIndex: 9998 };
    }
    return { position: 'fixed', bottom: 24, right: 24, zIndex: 9998 };
  };

  // Compute chat window position - always within viewport
  const getChatStyle = (): React.CSSProperties => {
    const isMobile = typeof window !== 'undefined' && window.innerWidth < 640;
    
    if (isMobile) {
      return {
        position: 'fixed',
        inset: 0,
        width: '100vw',
        height: '100dvh' as any,
        maxHeight: '100dvh' as any,
        zIndex: 9999,
        borderRadius: 0,
      };
    }
    
    if (position) {
      const chatWidth = Math.min(380, window.innerWidth - 32);
      const chatHeight = Math.min(600, window.innerHeight - 120);
      const top = Math.max(16, position.y - chatHeight - 16);
      const left = Math.max(16, Math.min(window.innerWidth - chatWidth - 16, position.x - chatWidth / 2 + 28));
      
      return {
        position: 'fixed',
        top,
        left,
        width: chatWidth,
        height: chatHeight,
        maxHeight: 'calc(100dvh - 32px)',
        zIndex: 9999,
      };
    }
    
    return {
      position: 'fixed',
      bottom: 100,
      right: 24,
      width: Math.min(380, window.innerWidth - 32),
      height: Math.min(600, window.innerHeight - 120),
      maxHeight: 'calc(100dvh - 32px)',
      zIndex: 9999,
    };
  };

  // Compute bubble position
  const getBubbleStyle = (): React.CSSProperties => {
    if (position) {
      return {
        position: 'fixed',
        top: Math.max(16, position.y - 80),
        left: position.x - 100,
        right: 'auto',
        bottom: 'auto',
        zIndex: 9997,
      };
    }
    return { position: 'fixed', bottom: 88, right: 24, zIndex: 9997 };
  };

  return (
    <>
      {/* Chat window */}
      {isOpen && (
        <div
          className="flex flex-col bg-[var(--background)] rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden charon-chat-window"
          style={getChatStyle()}
        >
          {/* Header */}
          <div
            className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--card)] cursor-grab active:cursor-grabbing select-none"
            onPointerDown={onFabPointerDown}
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full overflow-hidden shrink-0 bg-[var(--primary)]">
                <Image src="/chatbot-logo.png" alt="Charon" width={36} height={36} className="w-full h-full object-cover" />
              </div>
              <div>
                <p className="font-bold text-sm">Charon</p>
                <p className="text-xs text-[var(--muted)]">Online - Chat to get started</p>
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
              <MessageBubble key={m.id} msg={m} onRate={(rating) => handleRate(m.id, rating)} />
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
              placeholder="Type a message - Enter to send"
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

      {/* FAB + Reach-out bubble */}
      {!isOpen && (
        <>
          {/* Bubble */}
          {showBubble && activeTrigger && (
            <button
              onClick={openChat}
              className="animate-reach-out"
              style={getBubbleStyle()}
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

          {/* FAB - draggable */}
          <button
            onClick={() => toggleOpen(true)}
            onPointerDown={onFabPointerDown}
            className="w-14 h-14 rounded-full bg-[var(--primary)] hover:bg-[var(--primary-dark)] shadow-lg flex items-center justify-center transition-transform hover:scale-105 active:scale-95 touch-none"
            style={getFabStyle()}
            aria-label="Open chat"
          >
            <svg className="w-7 h-7 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </button>
        </>
      )}
    </>
  );
}

// Message bubble
function MessageBubble({ msg, onRate }: { msg: Message; onRate?: (rating: number) => void }) {
  const isUser = msg.role === 'user';
  const [rated, setRated] = useState(false);
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm ${
          isUser
            ? 'bg-[var(--primary)] text-black rounded-br-md'
            : 'bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-bl-md'
        }`}
      >
        <div className="prose prose-sm prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0 prose-strong:text-[var(--primary)] prose-a:text-[var(--primary)] prose-a:underline">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {msg.content}
          </ReactMarkdown>
        </div>
        {msg.escalated && (
          <div className="mb-1 px-2 py-0.5 bg-amber-500/20 text-amber-400 text-xs rounded">
            Escalated to support
          </div>
        )}
        {msg.tool_calls && msg.tool_calls.length > 0 && (
          <div className="mt-2 pt-2 border-t border-[var(--border)]">
            {msg.tool_calls.map((tc, i) => (
              <div key={i} className="text-xs text-[var(--muted)]">
                <span className="font-medium">{tc.tool}</span>
                {tc.result !== undefined && (
                  <pre className="mt-1 p-1 bg-[var(--background)] rounded overflow-x-auto">
                    {JSON.stringify(tc.result, null, 1)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
        {/* Thumbs up/down for assistant messages */}
        {!isUser && onRate && !rated && (
          <div className="mt-2 pt-2 border-t border-[var(--border)] flex gap-2">
            <button
              onClick={() => { setRated(true); onRate(5); }}
              className="text-xs px-2 py-1 rounded bg-[var(--background)] hover:bg-[var(--card-hover)]"
            >
              Helpful
            </button>
            <button
              onClick={() => { setRated(true); onRate(1); }}
              className="text-xs px-2 py-1 rounded bg-[var(--background)] hover:bg-[var(--card-hover)]"
            >
              Not helpful
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
