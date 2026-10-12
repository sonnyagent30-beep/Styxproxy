'use client';

import { Component, type ReactNode } from 'react';

interface State { hasError: boolean }

/** Isolates globe (WebGL) failures so they never take down the homepage. */
export default class GlobeErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.warn('[GlobeMap] render failed:', error);
  }

  render() {
    if (this.state.hasError) {
      // Silent graceful fallback — the hero works fine without the globe
      return <div className="w-full aspect-[4/3] max-h-[420px]" aria-hidden="true" />;
    }
    return this.props.children;
  }
}
