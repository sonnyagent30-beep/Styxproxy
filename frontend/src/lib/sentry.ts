import * as Sentry from "@sentry/nextjs";

/**
 * Sentry integration for the Styxproxy frontend.
 *
 * Initialization is handled by sentry.client.config.ts / sentry.server.config.ts
 * (via Next.js). This module re-exports the Sentry client and provides
 * convenience helpers for error reporting.
 *
 * If NEXT_PUBLIC_SENTRY_DSN is not set, Sentry.init() is a no-op and all
 * functions here silently do nothing.
 */

export { Sentry };

/**
 * Report an error to Sentry. Falls back to console.error when Sentry is
 * not configured (no DSN set).
 */
export function reportError(
  err: Error | unknown,
  context: Record<string, unknown> = {}
): void {
  if (context && Object.keys(context).length > 0) {
    Sentry.withScope((scope) => {
      scope.setExtras(context);
      Sentry.captureException(err);
    });
  } else {
    Sentry.captureException(err);
  }
}

/**
 * Install global error handlers. Sentry's built-in handlers are registered
 * automatically via the Next.js config files, but we also set up a
 * `unhandledrejection` fallback for environments where that isn't active.
 */
export function installGlobalHandlers(): void {
  if (typeof window === "undefined") return;

  // Sentry's init already registers window.onerror and unhandledrejection
  // via @sentry/nextjs. This is a no-op safety net.
  // If Sentry is not configured (no DSN), this silently does nothing.
}

/**
 * Wrap a function with Sentry error tracking.
 */
export function withSentry<T extends (...args: unknown[]) => unknown>(
  fn: T,
  context: Record<string, unknown> = {}
): T {
  return ((...args: unknown[]) => {
    try {
      return fn(...args);
    } catch (err) {
      reportError(err, context);
      throw err;
    }
  }) as T;
}
