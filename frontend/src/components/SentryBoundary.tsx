'use client';

import { useEffect } from 'react';
import { installGlobalHandlers } from '@/lib/sentry';

/**
 * Client-side global error handler. Mounts window.onerror and
 * unhandledrejection listeners that ship to Sentry.
 *
 * No-ops when NEXT_PUBLIC_SENTRY_DSN is not set.
 */
export default function SentryBoundary({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    installGlobalHandlers();
  }, []);
  return <>{children}</>;
}
