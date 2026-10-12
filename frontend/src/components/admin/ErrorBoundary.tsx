'use client';

import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: string | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error: error.message };
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="flex flex-col items-center justify-center min-h-[200px] text-center p-8">
          <div className="text-red-500 text-4xl mb-3">⚠️</div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Something went wrong</h2>
          <p className="text-sm text-gray-500 mb-4 max-w-sm">
            {this.state.error ?? 'An unexpected error occurred.'}
          </p>
          <button
            onClick={this.handleReset}
            className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:opacity-90 transition"
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
