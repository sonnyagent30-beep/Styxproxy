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
  }

  render() {
    if (this.state.hasError) {
      console.error('[CharonWidget] Not rendering due to error:', this.state.error);
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
