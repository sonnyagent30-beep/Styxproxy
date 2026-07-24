'use client';

// Next.js error boundary for the admin dashboard routes.
// Catches any unhandled render / page-load error and surfaces the
// real message + a retry button, instead of falling through to
// Next.js's opaque "This page couldn't load" global page.

import { useEffect } from 'react';

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface the error to whatever the host env uses for logs.
    // On Vercel this goes to the deployment logs.
    // eslint-disable-next-line no-console
    console.error('[admin route error]', error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
      <div className="text-5xl mb-4">⚠️</div>
      <h2 className="text-2xl font-bold mb-2">Dashboard failed to load</h2>
      <p className="text-sm text-[var(--muted)] mb-1 max-w-md">
        {error.message || 'An unexpected error occurred while loading the admin dashboard.'}
      </p>
      {error.digest && (
        <p className="text-xs text-[var(--muted)] mb-4 font-mono">
          digest: {error.digest}
        </p>
      )}
      <div className="flex gap-3 mt-4">
        <button
          onClick={reset}
          className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg text-sm font-medium hover:opacity-90 transition"
        >
          Try Again
        </button>
        <a
          href="/admin/dashboard"
          className="px-4 py-2 bg-[var(--card)] border border-[var(--border)] rounded-lg text-sm font-medium hover:bg-[var(--card-hover)] transition"
        >
          Reload Page
        </a>
      </div>
    </div>
  );
}