'use client';

import { Component, lazy, ReactNode, Suspense, useEffect, useState } from 'react';

const CharonWidget = lazy(() => import('@/components/CharonWidget'));

class CharonErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error('[CharonWidget] Render error:', error, info.componentStack);
    // Report to Sentry in ALL environments — a hidden mount failure is how
    // we spent two rounds chasing a widget that was silently broken.
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      (window as any).Sentry.captureException(error, {
        extra: { componentStack: info.componentStack, context: 'CharonWidget mount' },
      });
    }
  }

  render() {
    if (this.state.hasError) {
      // Render a visible marker in development, minimal in production —
      // but NEVER silently return null. A hidden failure is worse than a broken widget.
      if (process.env.NODE_ENV === 'development') {
        return (
          <div
            style={{
              position: 'fixed',
              bottom: 16,
              right: 16,
              zIndex: 9999,
              background: '#dc2626',
              color: '#fff',
              padding: '8px 12px',
              borderRadius: 8,
              fontSize: 12,
              fontFamily: 'monospace',
              maxWidth: 320,
            }}
          >
            Charon widget failed to mount: {this.state.error?.message ?? 'unknown error'}
          </div>
        );
      }
      // Production: still log visibly and report, but don't break the page.
      console.error('[CharonWidget] Mount failure (production):', this.state.error);
      return null;
    }
    return this.props.children;
  }
}

export function LazyCharonWidget() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShow(true), 1500);
    return () => clearTimeout(timer);
  }, []);

  if (!show) return null;

  return (
    <CharonErrorBoundary>
      <Suspense fallback={null}>
        <CharonWidget />
      </Suspense>
    </CharonErrorBoundary>
  );
}
