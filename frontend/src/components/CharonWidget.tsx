'use client';

import { useEffect, useCallback, useRef, useState } from 'react';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useCharonStore } from '@/store/charon-store';
import ChatPanel from './ChatPanel';

const FAB_SIZE = 56;
const STORAGE_KEY = 'charon_fab_position';

function loadPosition(): { x: number; y: number } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw);
    if (typeof p.x === 'number' && typeof p.y === 'number') return p;
  } catch { /* ignore */ }
  return null;
}

function savePosition(x: number, y: number) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ x, y })); } catch { /* ignore */ }
}

/**
 * CharonWidget — floating chat button + proactive message bubble.
 * FAB is draggable; position persists in localStorage.
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
  const dragRef = useRef<{ startX: number; startY: number; baseX: number; baseY: number; moved: boolean } | null>(null);
  const [fabPos, setFabPos] = useState<{ x: number; y: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // ── All hooks must run unconditionally (rules-of-hooks) ──────────────
  // These were previously AFTER a conditional `if (isBlocked) return null`,
  // which caused React to throw "Rendered more hooks than during the
  // previous render" when navigating into or out of /admin.

  useEffect(() => {
    pathnameRef.current = pathname;
  }, [pathname]);

  // Restore saved position on mount
  useEffect(() => {
    const saved = loadPosition();
    if (saved) setFabPos(saved);
  }, []);

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

  // ── Now the conditional return ─────────────────────────────────────────
  const isBlocked =
    pathname?.startsWith('/admin') ||
    pathname?.startsWith('/login') ||
    pathname?.startsWith('/setup') ||
    pathname?.startsWith('/superadmin');

  if (isBlocked) return null;

  const handleOpen = useCallback(() => {
    setProactiveMessage(null);
    setOpen(true);
  }, [setOpen, setProactiveMessage]);

  const handleDismiss = useCallback(() => {
    setProactiveMessage(null);
  }, [setProactiveMessage]);

  // ── Drag handlers ──────────────────────────────────────────────
  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return;
    const el = e.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();
    dragRef.current = { startX: e.clientX, startY: e.clientY, baseX: rect.left, baseY: rect.top, moved: false };
    try { el.setPointerCapture(e.pointerId); } catch { /* synthetic events */ }
  }, []);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    const d = dragRef.current;
    if (!d) return;
    const dx = e.clientX - d.startX;
    const dy = e.clientY - d.startY;
    if (!d.moved && Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
    d.moved = true;
    setIsDragging(true);
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const x = Math.max(0, Math.min(vw - FAB_SIZE, d.baseX + dx));
    const y = Math.max(0, Math.min(vh - FAB_SIZE, d.baseY + dy));
    setFabPos({ x, y });
  }, []);

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    const d = dragRef.current;
    if (!d) return;
    try { (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId); } catch { /* synthetic events */ }
    if (d.moved) {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const x = Math.max(0, Math.min(vw - FAB_SIZE, d.baseX + (e.clientX - d.startX)));
      const y = Math.max(0, Math.min(vh - FAB_SIZE, d.baseY + (e.clientY - d.startY)));
      savePosition(x, y);
    }
    dragRef.current = null;
    setIsDragging(false);
  }, []);

  const isVisible = isOpen || isMinimized;

  // FAB positioning: saved position > mobile bottom-20 > desktop bottom-6
  const fabStyle: React.CSSProperties = fabPos
    ? { position: 'fixed' as const, left: fabPos.x, top: fabPos.y, zIndex: 9998 }
    : { position: 'fixed' as const, bottom: '5rem', right: '1.5rem', zIndex: 9998 };

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
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onClick={handleOpen}
          style={fabStyle}
          className={`w-14 h-14 rounded-full bg-[var(--primary)] hover:bg-[var(--primary-dark)] flex items-center justify-center transition-transform hover:scale-105 active:scale-95 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
          aria-label="Ask Charon"
        >
          <div className="charon-halo--1 absolute inset-0 rounded-full" />
          <div className="relative w-8 h-8 rounded-full overflow-hidden">
            <Image src="/chatbot-logo.png" alt="Charon" width={32} height={32} className="w-full h-full object-cover" />
          </div>
        </button>
      )}
    </>
  );
}
