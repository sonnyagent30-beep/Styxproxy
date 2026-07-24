'use client';

// Next.js error boundary for the admin auth routes (login, setup).

import { useEffect } from 'react';

export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error('[admin auth error]', error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
      <div className="text-5xl mb-4">⚠️</div>
      <h2 className="text-2xl font-bold mb-2">Sign-in failed</h2>
      <p className="text-sm text-[var(--muted)] mb-4 max-w-md">
        {error.message || 'Something went wrong on the sign-in page.'}
      </p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg text-sm font-medium hover:opacity-90 transition"
      >
        Try Again
      </button>
    </div>
  );
}