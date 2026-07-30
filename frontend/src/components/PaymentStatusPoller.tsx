'use client';

/**
 * PaymentStatusPoller — polls /api/orders/{order_id}/status and renders based on next_action.
 *
 * Usage:
 *   <PaymentStatusPoller
 *     txRef={searchParams.get('tx_ref')}
 *     onResolve={(status) => { setCred(status.credential); }}
 *   />
 *
 * Polling flow:
 *  1. Resolve tx_ref → order_id via /api/orders/by-payment-reference/{tx_ref}
 *  2. Once we have order_id, poll /api/orders/{order_id}/status every 3.5s
 *  3. Stop on terminal states (next_action != 'poll')
 *  4. Call onResolve(status) exactly once when fulfilled
 *
 * After upgrade, the /thank-you page can use this component instead of duplicating
 * the polling logic. Currently /thank-you uses inline polling.
 */

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import type { OrderPaymentStatus } from '@/types';

interface PaymentStatusPollerProps {
  txRef: string | null;
  /** Called exactly once when the order is fulfilled. status contains the credential. */
  onResolve?: (status: OrderPaymentStatus) => void;
  /** When true, render the Loading spinner. Default true. */
  showLoadingUI?: boolean;
}

const POLL_INTERVAL_MS = 3500;
const MAX_ATTEMPTS = 60; // ~3.5 minutes

interface FetchOrderResponse {
  order_id: string;
  status?: string;
}

export function PaymentStatusPoller({ txRef, onResolve, showLoadingUI = true }: PaymentStatusPollerProps) {
  const [orderId, setOrderId] = useState<string | null>(null);
  const [status, setStatus] = useState<OrderPaymentStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [attempts, setAttempts] = useState(0);
  const attemptsRef = useRef(0);
  const resolvedRef = useRef(false);
  // Capture missingRef at render time so we don't setState synchronously in effect
  const missingRef = !txRef;

  // Stage 1: resolve tx_ref → order_id
  useEffect(() => {
    if (missingRef) {
      // Defer to a microtask so we don't setState during render
      Promise.resolve().then(() => {
        setError('No transaction reference provided.');
        setLoading(false);
      });
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`/api/orders/by-payment-reference/${txRef}`);
        if (cancelled) return;
        if (res.status === 404) {
          setTimeout(() => {
            setAttempts(a => a + 1);
          }, POLL_INTERVAL_MS);
          return;
        }
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data: FetchOrderResponse = await res.json();
        if (cancelled) return;
        if (data?.order_id) {
          setOrderId(data.order_id);
        } else {
          throw new Error('Order ID missing from response');
        }
      } catch (e) {
        if (cancelled) return;
        const message = e instanceof Error ? e.message : 'Failed to resolve order';
        Promise.resolve().then(() => {
          setError(message);
          setLoading(false);
        });
      }
    })();

    return () => { cancelled = true; };
  }, [txRef, attempts, missingRef]);

  // Stage 2: poll /api/orders/{order_id}/status
  useEffect(() => {
    if (!orderId) return;
    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;
      if (attemptsRef.current >= MAX_ATTEMPTS) {
        Promise.resolve().then(() => {
          setLoading(false);
          setError('Timed out waiting for payment. Please check /manage or contact support.');
        });
        return;
      }
      try {
        const res = await fetch(`/api/orders/${orderId}/status`);
        if (cancelled) return;
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data: OrderPaymentStatus = await res.json();
        if (cancelled) return;
        setStatus(data);

        if (data.next_action !== 'poll') {
          Promise.resolve().then(() => {
            setLoading(false);
            if (data.next_action === 'redirect_to_proxy_details' && !resolvedRef.current) {
              resolvedRef.current = true;
              onResolve?.(data);
            }
          });
          return;
        }
        attemptsRef.current += 1;
        setAttempts(attemptsRef.current);
      } catch {
        if (cancelled) return;
        attemptsRef.current += 1;
        setAttempts(attemptsRef.current);
      }
    };

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [orderId, onResolve]);

  // Loading UI
  if (loading && showLoadingUI) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4">
        <div className="w-16 h-16 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-lg font-medium text-[var(--foreground)]">
          {status?.user_message || 'Confirming your payment…'}
        </p>
        <p className="text-sm text-[var(--muted)] mt-2">
          {attempts > 0 ? `Attempt ${attempts}/${MAX_ATTEMPTS} · This usually takes 5-15 seconds.` : 'Connecting to payment provider…'}
        </p>
      </div>
    );
  }

  // Error UI
  if (error) {
    return (
      <div className="text-center py-16 px-4">
        <h1 className="text-2xl font-bold mb-4">Order Not Found</h1>
        <p className="text-[var(--muted)] mb-6">{error}</p>
        <Link
          href="/manage"
          className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
        >
          Look Up Order
        </Link>
      </div>
    );
  }

  // Status resolved — render nothing (parent renders the resolved UI)
  return null;
}

/**
 * Render the credential panel from a resolved OrderPaymentStatus.
 * Used by /thank-you after `next_action === 'redirect_to_proxy_details'`.
 */
export function CredentialPanel({ status }: { status: OrderPaymentStatus }) {
  const cred = status.credential;
  if (!cred) return null;

  return (
    <div className="rounded-xl bg-[var(--card)] border border-[var(--border)] p-6 mt-6">
      <h2 className="text-lg font-semibold mb-4 text-[var(--primary)]">Your Proxy Credentials</h2>
      <div className="space-y-3 text-sm">
        <Row label="Username" value={cred.styxproxy_username} />
        <Row label="Password" value={cred.styxproxy_password} masked />
        <Row label="SOCKS5" value={`${cred.proxy_host}:${cred.proxy_port_socks5}`} />
        <Row label="HTTP" value={`${cred.proxy_host}:${cred.proxy_port_http}`} />
        {cred.assigned_static_ip && (
          <Row label="Static IP" value={cred.assigned_static_ip} />
        )}
      </div>
      <details className="mt-4">
        <summary className="cursor-pointer text-sm text-[var(--muted)] hover:text-[var(--foreground)]">
          Show usage examples
        </summary>
        <div className="mt-3 space-y-2 text-xs font-mono bg-[var(--bg)] p-3 rounded">
          <div className="text-[var(--muted)]"># SOCKS5 curl</div>
          <div className="overflow-x-auto">{cred.curl_socks5_example}</div>
          <div className="text-[var(--muted)] mt-2"># HTTP curl</div>
          <div className="overflow-x-auto">{cred.curl_http_example}</div>
          <div className="text-[var(--muted)] mt-2"># Python requests</div>
          <div className="overflow-x-auto whitespace-pre">{cred.python_socks5_example}</div>
        </div>
      </details>
    </div>
  );
}

function Row({ label, value, masked }: { label: string; value: string; masked?: boolean }) {
  const [copied, setCopied] = useState(false);
  const display = masked && value ? '•'.repeat(value.length) : value;
  return (
    <div className="flex items-center justify-between">
      <span className="text-[var(--muted)]">{label}</span>
      <div className="flex items-center gap-2">
        <code className="font-mono text-[var(--primary)]">{display}</code>
        <button
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(value);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            } catch {
              // ignore clipboard errors
            }
          }}
          className="text-xs text-[var(--muted)] hover:text-[var(--primary)]"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
    </div>
  );
}
