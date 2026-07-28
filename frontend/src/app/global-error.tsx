'use client';

// Last-resort error boundary. Triggers when the root layout itself fails
// (i.e., when nothing else can render). Must include its own <html>/<body>.

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error('[GLOBAL error]', error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          background: '#0a0a0a',
          color: '#fafafa',
          padding: '2rem',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>⚠️</div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 0.5rem' }}>
          Critical Error
        </h1>
        <p style={{ fontSize: '0.875rem', color: '#a1a1aa', maxWidth: '28rem', marginBottom: '1.5rem' }}>
          {error.message || 'The application encountered a critical error and could not render.'}
        </p>
        <button
          onClick={reset}
          style={{
            padding: '0.5rem 1rem',
            background: '#0ad25a',
            color: '#000',
            border: 'none',
            borderRadius: '0.5rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Reload
        </button>
      </body>
    </html>
  );
}
