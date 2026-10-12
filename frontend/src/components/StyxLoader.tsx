'use client';

import { useEffect, useState } from 'react';

/**
 * Styxproxy unified loading spinner.
 * Uses the brand green (#0AD25A) with a pulsing ring animation.
 * Works in both light and dark mode via CSS variables.
 */
export function StyxLoader({ size = 'md', text }: { size?: 'sm' | 'md' | 'lg'; text?: string }) {
  const sizeMap = { sm: 'w-6 h-6', md: 'w-10 h-10', lg: 'w-16 h-16' };
  const textSize = { sm: 'text-xs', md: 'text-sm', lg: 'text-base' };

  return (
    <div className="flex flex-col items-center justify-center gap-3" role="status" aria-label="Loading">
      <div className="relative">
        {/* Outer ring */}
        <div className={`${sizeMap[size]} rounded-full border-2 border-[var(--border)]`} />
        {/* Spinning arc */}
        <div
          className={`absolute inset-0 ${sizeMap[size]} rounded-full border-2 border-transparent border-t-[var(--primary)] animate-spin`}
          style={{ animationDuration: '0.8s' }}
        />
        {/* Inner pulse */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className={`${size === 'sm' ? 'w-2 h-2' : size === 'md' ? 'w-3 h-3' : 'w-5 h-5'} rounded-full bg-[var(--primary)] animate-pulse`} />
        </div>
      </div>
      {text && (
        <p className={`${textSize[size]} text-[var(--muted)] animate-pulse`}>
          {text}
        </p>
      )}
    </div>
  );
}

/**
 * Full-page loading state with branded spinner.
 * Used as Next.js loading.tsx boundary.
 */
export function PageLoading({ text = 'Loading…' }: { text?: string }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <StyxLoader size="lg" text={text} />
    </div>
  );
}

/**
 * Inline loading state for buttons and small areas.
 */
export function InlineLoader({ text }: { text?: string }) {
  return (
    <div className="flex items-center gap-2" role="status" aria-label="Loading">
      <div className="w-4 h-4 rounded-full border-2 border-transparent border-t-[var(--primary)] animate-spin" />
      {text && <span className="text-sm text-[var(--muted)]">{text}</span>}
    </div>
  );
}

/**
 * Skeleton loader for content areas.
 */
export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-[var(--card)] rounded animate-pulse ${className}`} />
  );
}

/**
 * Card skeleton for product/blog cards.
 */
export function CardSkeleton() {
  return (
    <div className="rounded-2xl bg-[var(--card)] border border-[var(--border)] p-6 space-y-4">
      <div className="w-12 h-12 bg-[var(--surface)] rounded-full animate-pulse" />
      <div className="w-3/4 h-6 bg-[var(--surface)] rounded animate-pulse" />
      <div className="space-y-2">
        <div className="w-full h-4 bg-[var(--surface)] rounded animate-pulse" />
        <div className="w-5/6 h-4 bg-[var(--surface)] rounded animate-pulse" />
      </div>
      <div className="w-1/3 h-8 bg-[var(--surface)] rounded animate-pulse" />
    </div>
  );
}

/**
 * Table skeleton for admin data tables.
 */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex gap-4 p-3 bg-[var(--card)] rounded-lg border border-[var(--border)]">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="flex-1 h-4 bg-[var(--surface)] rounded animate-pulse" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 p-3 bg-[var(--card)] rounded-lg border border-[var(--border)]">
          {[1, 2, 3, 4].map(j => (
            <div key={j} className="flex-1 h-4 bg-[var(--surface)] rounded animate-pulse" style={{ animationDelay: `${i * 100}ms` }} />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * Hook for managing loading state with minimum display time.
 * Prevents flash of loading indicator for fast operations.
 */
export function useLoadingState(minDisplayTime = 300) {
  const [isLoading, setIsLoading] = useState(false);
  const [showLoader, setShowLoader] = useState(false);

  useEffect(() => {
    if (isLoading) {
      setShowLoader(true);
      const timer = setTimeout(() => {
        setShowLoader(false);
      }, minDisplayTime);
      return () => clearTimeout(timer);
    } else {
      setShowLoader(false);
    }
  }, [isLoading, minDisplayTime]);

  return { isLoading, setIsLoading, showLoader };
}

export default StyxLoader;
