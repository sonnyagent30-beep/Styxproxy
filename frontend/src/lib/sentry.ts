'use client';

/**
 * Lightweight Sentry reporter for the Styxproxy frontend.
 *
 * We don't pull in @sentry/nextjs (heavy, requires build-time init). Instead
 * we POST errors directly to Sentry's HTTP API when SENTRY_DSN_PUBLIC is set.
 *
 * Usage:
 *   import { reportError } from '@/lib/sentry';
 *   try { ... } catch (err) { reportError(err, { context: 'blog-list' }); }
 *
 * Falls back to console.error when DSN is not set (dev / unconfigured).
 */

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN || '';

interface SentryContext {
  [key: string]: unknown;
}

function getDsnParts(dsn: string): { publicKey: string; host: string; projectId: string } | null {
  // DSN format: https://<key>@<host>/<project_id>
  const match = dsn.match(/^https?:\/\/([^@]+)@([^/]+)\/(\d+)/);
  if (!match) return null;
  return { publicKey: match[1], host: match[2], projectId: match[3] };
}

export function reportError(err: Error | unknown, context: SentryContext = {}): void {
  // Always log to console for dev
  // eslint-disable-next-line no-console
  console.error('[styxproxy:error]', err, context);

  if (!SENTRY_DSN || typeof window === 'undefined') return;

  const parts = getDsnParts(SENTRY_DSN);
  if (!parts) return;

  const error = err instanceof Error
    ? { type: err.name, message: err.message, stack: err.stack }
    : { type: 'Unknown', message: String(err) };

  const event = {
    event_id: crypto.randomUUID().replace(/-/g, ''),
    timestamp: new Date().toISOString(),
    platform: 'javascript',
    level: 'error',
    logger: 'styxproxy-frontend',
    environment: process.env.NEXT_PUBLIC_ENVIRONMENT || 'production',
    release: process.env.NEXT_PUBLIC_RELEASE || 'styxproxy-frontend@1.0.0',
    exception: {
      values: [
        {
          type: error.type,
          value: error.message,
          stacktrace: error.stack
            ? { frames: error.stack.split('\n').map((line: string) => ({ function: line })) }
            : undefined,
        },
      ],
    },
    extra: context,
    tags: {
      'browser.name': navigator.userAgent,
      'browser.url': window.location.href,
    },
  };

  // Send via Sentry's envelope endpoint. Best-effort; no await.
  fetch(`https://${parts.host}/api/${parts.projectId}/store/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Sentry-Auth': `Sentry sentry_version=7, sentry_key=${parts.publicKey}`,
    },
    body: JSON.stringify(event),
    keepalive: true,
  }).catch(() => {
    // swallow — fire-and-forget
  });
}

/**
 * Global handler for unhandled errors. Call once from root layout.
 */
export function installGlobalHandlers(): void {
  if (typeof window === 'undefined') return;

  window.addEventListener('error', (event) => {
    reportError(event.error || new Error(event.message), {
      kind: 'window.onerror',
      filename: event.filename,
      lineno: event.lineno,
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    reportError(event.reason || new Error('Unhandled promise rejection'), {
      kind: 'unhandledrejection',
    });
  });
}
