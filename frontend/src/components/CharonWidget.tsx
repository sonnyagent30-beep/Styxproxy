'use client';

import { useEffect, useCallback, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { useCharonStore } from '@/store/charon-store';
import ChatPanel from './ChatPanel';

/**
 * CharonWidget — floating chat button + proactive message bubble.
 */
export default function CharonWidget() {
  const pathname = usePathname();
  const {
    isOpen,
    isMinimized,
    setOpen,
    setMinimized,
    isTyping,
    proactiveMessage,
    setProactiveMessage,
  } = useCharonStore();

  const pathnameRef = useRef(pathname);
  const ignoreTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    pathnameRef.current = pathname;
  }, [pathname]);

  const isBlocked =
    pathname.startsWith('/admin') ||
    pathname.startsWith('/login') ||
    pathname.startsWith('/setup') ||
    pathname.startsWith('/superadmin');

  if (isBlocked) return null;

  useEffect(() => {
    if (isOpen || proactiveMessage) return;

    const isCheckout = pathname === '/order' || pathname === '/checkout';
    const delay = isCheckout ? 30_000 : 60_000;

    const timer = setTimeout(() => {
      const msg = isCheckout
        ? 'Need help completing your order? I can walk you through it.'
        : 'Have questions about our plans? I am here to help.';

      setProactiveMessage({
        id: 'proactive_' + Date.now(),
        triggerId: isCheckout ? 'checkout_dwell' : 'general_dwell',
        message: msg,
        dismissAfterMs: 10_000,
        delayMs: 0,
      });

      ignoreTimerRef.current = setTimeout(() => {
        setProactiveMessage(null);
      }, 10_000);
    }, delay);

    return () => {
      clearTimeout(timer);
      if (ignoreTimerRef.current) clearTimeout(ignoreTimerRef.current);
    };
  }, [pathname, isOpen, proactiveMessage, setProactiveMessage]);

  const handleOpen = useCallback(() => {
    setProactiveMessage(null);
    setOpen(true);
  }, [setOpen, setProactiveMessage]);

  const handleDismiss = useCallback(() => {
    setProactiveMessage(null);
  }, [setProactiveMessage]);

  const isVisible = isOpen || isMinimized;

  return (
    <>
      <ChatPanel />

      {proactiveMessage && !isVisible && (
        <div
          className="fixed bottom-24 right-24 z-[9998] animate-reach-out"
          style={{ maxWidth: 280 }}
        >
          <div className="relative flex items-start gap-2 pl-3 pr-4 py-2.5 bg-[var(--card)] border border-[var(--border)] rounded-2xl shadow-xl">
            <div className="absolute left-0 top-3 bottom-3 w-0.5 rounded-full bg-[var(--primary)]" />
            <p className="text-sm text-[var(--foreground)] text-left leading-snug">
              {proactiveMessage.message}
            </p>
            <button
              onClick={handleDismiss}
              className="shrink-0 w-6 h-6 flex items-center justify-center rounded-full hover:bg-[var(--card-hover)] text-[var(--muted)]"
              aria-label="Dismiss"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {!isVisible && (
        <button
          onClick={handleOpen}
          className="fixed bottom-6 right-6 z-[9998] w-14 h-14 rounded-full bg-[var(--primary)] hover:bg-[var(--primary-dark)] shadow-lg flex items-center justify-center transition-transform hover:scale-105 active:scale-95"
          aria-label="Open chat"
        >
          <svg className="w-7 h-7 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </button>
      )}
    </>
  );
}
