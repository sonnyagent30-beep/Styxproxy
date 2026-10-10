'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { useCharonStore } from '@/store/charon-store';
import { getDeviceId } from '@/lib/device-id';
import ChatMessage from './ChatMessage';

export default function ChatPanel() {
  const pathname = usePathname();
  const {
    messages,
    addMessage,
    appendToMessage,
    updateMessage,
    isOpen,
    isMinimized,
    isTyping,
    setOpen,
    setMinimized,
    setTyping,
    streamingMessageId,
    setStreamingMessageId,
    pageContext,
    setPageContext,
    charonAvailable,
    setCharonAvailable,
  } = useCharonStore();

  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // A2: Fetch health on mount to get charon_available flag
  useEffect(() => {
    let cancelled = false;
    async function fetchHealth() {
      try {
        const res = await fetch('/api/v1/health', { credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled) {
          setCharonAvailable(data.charon_available !== false);
        }
      } catch {
        // If health check fails, assume available (fail-open for UX)
        if (!cancelled) setCharonAvailable(true);
      }
    }
    fetchHealth();
    return () => { cancelled = true; };
  }, [setCharonAvailable]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  useEffect(() => {
    if (isOpen && !isMinimized) {
      textareaRef.current?.focus();
    }
  }, [isOpen, isMinimized]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const path = window.location.pathname;
    const ctx: Record<string, unknown> = {
      page_type: getPageType(path),
      path,
      themes: getThemes(path),
    };
    const planMatch = path.match(/\/(residential|mobile|isp|datacenter)/);
    if (planMatch) {
      ctx.plan_being_viewed = planMatch[1];
    }
    setPageContext(ctx);
  }, [pathname, setPageContext]);

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      addMessage({
        id: 'welcome',
        role: 'assistant',
        content: "Hi — I'm Charon. I can help with orders, plan details, payment status, and proxy troubleshooting. What can I help you with?",
        timestamp: Date.now(),
      });
    }
  }, [isOpen, messages.length, addMessage]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isTyping) return;

      addMessage({
        id: genId(),
        role: 'user',
        content: trimmed,
        timestamp: Date.now(),
      });
      setInput('');
      setTyping(true);

      const assistantId = genId();
      addMessage({
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        isStreaming: true,
      });
      setStreamingMessageId(assistantId);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const history = messages
          .filter((m) => m.id !== 'welcome' && !m.isStreaming)
          .slice(-12)
          .map((m) => ({
            role: m.role === 'assistant' ? 'assistant' : 'user',
            content: m.content,
          }));

        const deviceId = getDeviceId();
        const res = await fetch('/api/v1/charon/reply/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            channel: 'web',
            conversation_id: undefined,
            user_message: trimmed,
            history,
            page_context: pageContext,
            channel_user_id: deviceId || undefined,
            customer_email: undefined,
            customer_phone: undefined,
            customer_name: undefined,
          }),
          signal: controller.signal,
        });

        if (!res.ok) throw new Error('Charon returned ' + res.status);

        const reader = res.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';
        let fullContent = '';
        let streamInterrupted = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6).trim();
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              if (parsed.delta) {
                fullContent += parsed.delta;
                appendToMessage(assistantId, parsed.delta);
              }
              if (parsed.escalated !== undefined) {
                updateMessage(assistantId, { escalated: parsed.escalated });
              }
              if (parsed.tokens_used !== undefined) {
                updateMessage(assistantId, { tokens_used: parsed.tokens_used });
              }
              // A5: Capture interrupted signal from stream
              if (parsed.interrupted !== undefined) {
                streamInterrupted = parsed.interrupted;
              }
            } catch {
              // skip non-JSON
            }
          }
        }

        // A5: Mark interrupted on the message
        if (streamInterrupted) {
          updateMessage(assistantId, { interrupted: true });
        }

        if (!fullContent && !streamInterrupted) {
          updateMessage(assistantId, {
            content: "I'm having trouble reaching the support backend. Please email support@styxproxy.com while we resolve this.",
            isStreaming: false,
          });
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        updateMessage(assistantId, {
          content: "I'm having trouble reaching the support backend. Please email support@styxproxy.com while we resolve this.",
          isStreaming: false,
        });
      } finally {
        updateMessage(assistantId, { isStreaming: false });
        setStreamingMessageId(null);
        setTyping(false);
      }
    },
    [isTyping, messages, pageContext, addMessage, appendToMessage, updateMessage, setTyping, setStreamingMessageId],
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void sendMessage(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void sendMessage(input);
    }
  };

  if (!isOpen) return null;

  const panelClass = isMinimized
    ? 'rounded-2xl w-72 h-14'
    : 'rounded-2xl w-[380px] h-[600px] max-w-[calc(100vw-32px)] max-h-[calc(100dvh-120px)]';

  return (
    <div
      className={`flex flex-col bg-[var(--background)] border border-[var(--border)] shadow-2xl overflow-hidden transition-all duration-200 charon-chat-panel ${panelClass}`}
      style={{ position: 'fixed', bottom: isMinimized ? 24 : 100, right: 24, zIndex: 9999 }}
    >
      <div
        className={`shrink-0 flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--card)] ${isMinimized ? 'rounded-2xl' : 'rounded-t-2xl'}`}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-full overflow-hidden shrink-0 bg-[var(--primary)] flex items-center justify-center">
            <svg className="w-5 h-5 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="font-bold text-sm truncate">Charon</p>
            <p className="text-xs text-[var(--muted)]">
              {isTyping ? 'Typing...' : 'Online — Chat to get started'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => setMinimized(!isMinimized)}
            className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors"
            aria-label={isMinimized ? 'Expand chat' : 'Minimize chat'}
          >
            {isMinimized ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
              </svg>
            )}
          </button>
          <button
            onClick={() => setOpen(false)}
            className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors"
            aria-label="Close chat"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.map((m) => (
              <ChatMessage
                key={m.id}
                message={m}
                onRetry={m.interrupted ? () => {
                  const lastUserMsg = [...messages].reverse().find(
                    (msg) => msg.role === 'user' && msg.id !== m.id
                  );
                  if (lastUserMsg) {
                    void sendMessage(lastUserMsg.content);
                  }
                } : undefined}
              />
            ))}
            {isTyping && streamingMessageId === null && (
              <div className="flex justify-start">
                <div className="px-4 py-2.5 rounded-2xl rounded-bl-md bg-[var(--card)] border border-[var(--border)]">
                  <span className="charon-typing-indicator inline-flex items-center gap-1.5">
                    <span className="inline-block w-2 h-2 rounded-full bg-[var(--muted)] animate-pulse" />
                    <span className="inline-block w-2 h-2 rounded-full bg-[var(--muted)] animate-pulse [animation-delay:0.2s]" />
                    <span className="inline-block w-2 h-2 rounded-full bg-[var(--muted)] animate-pulse [animation-delay:0.4s]" />
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* A1: Offline state — replace composer with status card */}
          {!charonAvailable ? (
            <div className="shrink-0 border-t border-[var(--border)] bg-[var(--card)] p-4 rounded-b-2xl">
              <div className="flex flex-col items-center text-center gap-3">
                <p className="text-sm text-[var(--muted)]">
                  Charon's offline right now.
                </p>
                <a
                  href="https://wa.me/2347032981049"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center min-h-[44px] px-6 py-2.5 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl text-sm transition-colors"
                >
                  Contact support
                </a>
                <a
                  href="https://t.me/StyxproxyBot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center min-h-[44px] px-6 py-2.5 border border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] text-[var(--foreground)] font-semibold rounded-xl text-sm transition-colors"
                >
                  Telegram
                </a>
              </div>
            </div>
          ) : (
            <form
              onSubmit={handleSubmit}
              className="shrink-0 flex gap-2 border-t border-[var(--border)] bg-[var(--card)] p-3 rounded-b-2xl"
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder="Type a message — Enter to send"
                className="flex-1 resize-none px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--primary)] transition-colors"
                disabled={isTyping}
              />
              <button
                type="submit"
                disabled={isTyping || !input.trim()}
                className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Send
              </button>
            </form>
          )}
        </>
      )}
    </div>
  );
}

function genId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function getPageType(path: string): string {
  const clean = path.split('?')[0].split('#')[0];
  if (clean.startsWith('/order') || clean === '/thank-you' || clean === '/receipt') return 'payment';
  if (clean === '/pricing' || clean === '/how-it-works' || clean === '/') return 'pricing';
  if (clean.startsWith('/products') || clean.startsWith('/residential') || clean.startsWith('/mobile') || clean.startsWith('/isp') || clean.startsWith('/datacenter')) return 'product';
  if (clean.startsWith('/blog')) return 'blog_post';
  return 'general';
}

function getThemes(path: string): string[] {
  const clean = path.split('?')[0].split('#')[0];
  const themes: Record<string, string[]> = {
    '/': ['landing page', 'proxy overview', 'hero section'],
    '/pricing': ['pricing', 'plan comparison', 'ISP', 'datacenter', 'residential'],
    '/products': ['product catalog', 'proxy types'],
    '/residential': ['residential proxies', 'home IPs'],
    '/datacenter': ['datacenter proxies', 'cloud servers'],
    '/mobile': ['mobile proxies', '4G'],
    '/isp': ['ISP proxies', 'static IPs'],
    '/blog': ['blog', 'guides'],
    '/how-it-works': ['setup', 'configuration', 'SOCKS5'],
    '/order': ['order form', 'checkout', 'cart'],
  };
  return themes[clean] ?? [];
}
