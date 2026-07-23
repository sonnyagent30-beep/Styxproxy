'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useMaintenanceStatus } from '@/lib/useMaintenanceStatus';

/**
 * Animated maintenance page — shown when /api/public/maintenance returns
 * enabled=true (e.g. via Next.js fetch override or by the
 * maintenance-block middleware in the backend).
 *
 * Renders:
 * - Soft animated gradient (the river Styx)
 * - Centered card with logo, message, ready_at countdown
 * - Admin login link (superadmins can still access /admin/* during maint)
 */
export default function MaintenanceClient() {
  const { state, loading } = useMaintenanceStatus();
  const [countdown, setCountdown] = useState<string>('');

  useEffect(() => {
    if (!state?.ready_at) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCountdown('');
      return;
    }
    const target = new Date(state.ready_at).getTime();
    const tick = () => {
      const now = Date.now();
      const diff = target - now;
      if (diff <= 0) {
        setCountdown('Returning now…');
        return;
      }
      const m = Math.floor(diff / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setCountdown(`${m}m ${s.toString().padStart(2, '0')}s`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [state?.ready_at]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
        <div className="animate-pulse text-[var(--muted)]">Loading…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative overflow-hidden bg-[var(--background)] flex items-center justify-center p-4">
      {/* Animated gradient orbs — the river Styx */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 -left-32 w-[40rem] h-[40rem] rounded-full bg-[var(--primary)]/10 blur-3xl animate-float" />
        <div className="absolute -bottom-32 -right-32 w-[40rem] h-[40rem] rounded-full bg-[var(--accent)]/10 blur-3xl animate-float-delay" />
        <div className="absolute top-1/3 right-1/4 w-96 h-96 rounded-full bg-[var(--primary)]/5 blur-3xl animate-float-slow" />
      </div>

      <main className="relative max-w-xl w-full text-center space-y-8">
        {/* Logo */}
        <div className="flex justify-center">
          <div className="w-20 h-20 relative">
            <Image
              src="/chatbot-logo.png"
              alt="Styxproxy"
              fill
              className="object-contain"
              priority
            />
          </div>
        </div>

        <div className="space-y-3">
          <h1 className="text-4xl sm:text-5xl font-bold text-[var(--foreground)] tracking-[-0.02em]">
            We&apos;re crossing the river
          </h1>
          <p className="text-base sm:text-lg text-[var(--muted)] max-w-md mx-auto leading-relaxed">
            Styxproxy is undergoing scheduled maintenance. We&apos;ll be back
            shortly with faster boats.
          </p>
        </div>

        {/* Custom message from admin */}
        {state?.message && (
          <div className="glass-card p-4 rounded-2xl text-sm text-[var(--foreground)] border border-[var(--border)]">
            {state.message}
          </div>
        )}

        {/* Ready-at countdown */}
        {state?.ready_at && (
          <div className="inline-flex flex-col items-center gap-1 px-6 py-4 rounded-2xl bg-[var(--surface)] border border-[var(--border)]">
            <p className="text-xs uppercase tracking-widest text-[var(--muted)]">
              Estimated return
            </p>
            <p className="text-2xl font-mono font-bold text-[var(--primary)] tabular-nums">
              {countdown || '…'}
            </p>
            <p className="text-xs text-[var(--muted)]">
              {new Date(state.ready_at).toLocaleString()}
            </p>
          </div>
        )}

        {/* Status pulse */}
        <div className="flex items-center justify-center gap-2 text-sm text-[var(--muted)]">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full rounded-full bg-[var(--primary)] opacity-75 animate-ping" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--primary)]" />
          </span>
          Maintenance in progress
        </div>

        {/* Contact + admin */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <Link
            href="https://t.me/StyxproxyBot"
            className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            target="_blank"
            rel="noopener noreferrer"
          >
            Telegram: @StyxproxyBot
          </Link>
          <span className="hidden sm:inline text-[var(--border)]">•</span>
          <Link
            href="/admin/login"
            className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
          >
            Admin login
          </Link>
        </div>
      </main>
    </div>
  );
}
