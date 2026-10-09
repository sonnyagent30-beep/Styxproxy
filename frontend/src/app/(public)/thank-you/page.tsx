'use client';

/* eslint-disable react-hooks/set-state-in-effect */

export const dynamic = 'force-dynamic';

import { useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState, Suspense } from 'react';
import Link from 'next/link';
import { useToast } from '@/components/Toast';
import { Flag } from '@/components/ui/Flag';
import { generateReceiptPDF, detectReceiptTheme } from '@/lib/pdf-receipt';
import type { ReceiptOrder } from '@/lib/pdf-receipt';
import type { CartItem } from '@/types';
import { Check, Copy, Warning, XCircle, ArrowLineDown, WarningCircle } from '@phosphor-icons/react';
import { PaymentStatusPoller, CredentialPanel } from '@/components/PaymentStatusPoller';

interface OrderData {
  order_id?: string;
  status?: string;
  plan_type?: string;
  country?: string;
  amount_paid_ngn?: number;
  tx_ref?: string;
  customer_name?: string | null;
  is_renewable?: boolean;
  rotation_count?: number;
  max_rotations?: number;
  plan_code?: string;
  quantity?: number;
  city_name?: string | null;
  data_total_gb?: number;
  // Full details for the BUYER on this page only — it is rendered right after
  // their own payment from the order-status poll keyed to their order. This is
  // deliberately NOT the public receipt shape: generateReceiptPDF receives a
  // status-only projection so no emailed/forwardable PDF contains credentials.
  styxproxy_credential?: {
    bun_username?: string;
    styxproxy_username?: string;
    styxproxy_password?: string;
    upstream_proxy_ip?: string;
    upstream_proxy_port?: number;
    expires_at?: string;
    status?: string;
  };
  // For basket orders: ALL credentials created for this order.
  // The customer paid for every item in one transaction and must see
  // every proxy on the thank-you page.
  credentials?: Array<{
    styxproxy_username?: string;
    styxproxy_password?: string;
    upstream_proxy_ip?: string;
    upstream_proxy_port?: number;
    status?: string;
  }>;
  user_message?: string | null;
  created_at?: string;
  fulfilled_at?: string;
  expires_at?: string;
}

function ThankYouContent() {
  const searchParams = useSearchParams();
  const urlOrderId = searchParams.get('order_id');
  const urlTxRef = searchParams.get('tx_ref');
  const [orderId, setOrderId] = useState<string | null>(urlOrderId);
  const [txRef, setTxRef] = useState<string | null>(urlTxRef);
  const { toast } = useToast();

  // Fallback: if no order_id in URL, try sessionStorage then tx_ref
  useEffect(() => {
    if (!orderId) {
      const storedOrderId = sessionStorage.getItem('styxproxy_order_id');
      if (storedOrderId) {
        setOrderId(storedOrderId);
      } else if (!txRef) {
        const stored = sessionStorage.getItem('styxproxy_active_tx');
        if (stored) {
          setTxRef(stored);
        }
      }
    }
  }, [orderId, txRef]);

  const [order, setOrder] = useState<OrderData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempts, setAttempts] = useState(0);
  // A ref, not the state value, so the polling effect does not depend on it.
  // Depending on `attempts` re-created the effect on every increment, which
  // cleared the interval before it fired and turned the poll into a busy loop.
  const attemptsRef = useRef(0);
  const [nextAction, setNextAction] = useState<string | null>(null);
  const [userMessage, setUserMessage] = useState<string | null>(null);
  const maxAttempts = 60;

  // Self-service lookup state
  const [lookupEmail, setLookupEmail] = useState('');
  const [lookupOrderId, setLookupOrderId] = useState('');
  const [lookupResult, setLookupResult] = useState<any>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState('');

  // Build receipt items from the order payload.
  //
  // The cart is cleared at checkout (CheckoutClient.tsx) — it is NOT the
  // source of truth after payment. The order is. The backend returns
  // plan_code, quantity, city_name, plan_type, country, and amount_paid_ngn
  // on the by-payment-reference endpoint. We build a CartItem-shaped array
  // from those fields so the existing PDF generator (generateReceiptPDF)
  // works unchanged.
  const receiptItems: CartItem[] = [];
  if (order) {
    const isPerGb = (order.plan_type === 'RESIDENTIAL' || order.plan_type === 'MOBILE')
      && typeof order.data_total_gb === 'number';
    receiptItems.push({
      plan_code: order.plan_code || 'unknown',
      name: order.plan_code
        ? order.plan_code.split('-').slice(0, 2).join(' ')
        : (order.plan_type || 'Proxy'),
      flag: order.country || '',
      price_ngn: order.amount_paid_ngn || 0,
      quantity: isPerGb ? 1 : (order.quantity || 1),
      country_code: order.country || 'NG',
      plan_type: (order.plan_type as CartItem['plan_type']) || 'DC',
      ...(isPerGb ? { quantity_gb: order.data_total_gb as number } : {}),
      ...(order.city_name ? { city_name: order.city_name } : {}),
    });
  }

  // Poll for order status using PaymentStatusPoller
  //
  // Two bugs lived here:
  //
  // 1. It fetched `/api/orders/{id}/status`, which DOES NOT EXIST. The backend
  //    has `/api/orders/{order_id}` (auth required) and
  //    `/api/orders/by-payment-reference/{ref}` (public). The 401/404 was
  //    swallowed by the catch, attempts incremented, and the page span the
  //    spinner until maxAttempts — "processing forever" on a fulfilled order.
  //    It now uses the public by-payment-reference endpoint, which returns the
  //    full OrderResponse including the credential.
  //
  // 2. `attempts` was in the dependency array, so every increment tore down and
  //    re-created the effect — which cleared the 3500ms interval before it ever
  //    fired and called the fetch immediately instead. That is a busy loop with
  //    no delay. The counter is now a ref, so the interval is the only poller.
  //
  // Field names were also wrong: the endpoint returns `status` (not
  // `order_status`) and `styxproxy_credential` (not `credential`), with
  // `upstream_proxy_ip` / `upstream_proxy_port` (not `proxy_host` /
  // `proxy_port_socks5`). Mapping the wrong names left the credential panel
  // permanently empty even when the order was fulfilled.
  useEffect(() => {
    if (!txRef) {
      Promise.resolve().then(() => {
        setError(true);
        setLoading(false);
      });
      return;
    }

    let cancelled = false;

    const fetchOrderStatus = async () => {
      try {
        const res = await fetch(`/api/orders/by-payment-reference/${encodeURIComponent(txRef)}`);
        if (cancelled) return;
        if (res.status === 404) {
          attemptsRef.current += 1;
          setAttempts(attemptsRef.current);
          return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        if (!data.order_id) {
          setLoading(false);
          setError(true);
          return;
        }

        const cred = data.styxproxy_credential;
        const allCreds = data.credentials;
        const orderData: OrderData = {
          order_id: data.order_id,
          status: data.status,
          plan_type: data.plan_type,
          country: data.country,
          amount_paid_ngn: data.amount_paid_ngn,
          tx_ref: txRef || undefined,
          customer_name: data.customer_name,
          is_renewable: data.is_renewable,
          rotation_count: data.rotation_count,
          max_rotations: data.max_rotations,
          plan_code: data.plan_code,
          quantity: data.quantity,
          city_name: data.city_name,
          data_total_gb: data.data_total_gb,
          created_at: data.created_at,
          expires_at: data.expires_at || undefined,
          styxproxy_credential: cred ? {
            styxproxy_username: cred.styxproxy_username,
            styxproxy_password: cred.styxproxy_password,
            upstream_proxy_ip: cred.upstream_proxy_ip,
            upstream_proxy_port: cred.upstream_proxy_port,
            expires_at: data.expires_at || undefined,
            status: cred.status,
          } : undefined,
          credentials: allCreds ? allCreds.map(c => ({
            styxproxy_username: c.styxproxy_username,
            styxproxy_password: c.styxproxy_password,
            upstream_proxy_ip: c.upstream_proxy_ip,
            upstream_proxy_port: c.upstream_proxy_port,
            status: c.status,
          })) : undefined,
        };
        setOrder(orderData);

        // Terminal states stop the poll. Anything else keeps waiting.
        const s = data.status;
        if (s === 'fulfilled' || s === 'active') {
          setLoading(false);
          setNextAction('redirect_to_proxy_details');
          import('@/lib/device-id').then(({ clearInflightOrder }) => clearInflightOrder());
          return;
        }
        if (s === 'expired' || s === 'cancelled' || s === 'refunded') {
          setLoading(false);
          setNextAction('show_failure');
          setUserMessage(data.user_message || null);
          return;
        }
        if (s === 'failed_manual_review' || s === 'failed_unfulfilled') {
          setLoading(false);
          setNextAction('provider_down');
          setUserMessage(data.user_message || null);
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

    fetchOrderStatus();

    const interval = setInterval(() => {
      if (attemptsRef.current >= maxAttempts) {
        setLoading(false);
        clearInterval(interval);
        return;
      }
      fetchOrderStatus();
    }, 3500);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [txRef]);

  // Self-service lookup
  const handleLookup = async () => {
    if (!lookupEmail || !lookupOrderId) {
      setLookupError('Please enter both email and order ID');
      return;
    }
    setLookupLoading(true);
    setLookupError('');
    setLookupResult(null);
    try {
      const res = await fetch(`/api/orders/lookup?email=${encodeURIComponent(lookupEmail)}&order_id=${encodeURIComponent(lookupOrderId)}`);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setLookupError(data.detail || 'Order not found');
        return;
      }
      const data = await res.json();
      setLookupResult(data);
    } catch (err) {
      setLookupError('Lookup failed. Please try again.');
    } finally {
      setLookupLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (order && receiptItems.length > 0) {
      // Project to status-only before generating. The PDF is an emailed,
      // forwardable, storable artefact — it must not contain proxy credentials,
      // even though this page shows them to the buyer in the browser.
      const receiptSafeOrder = {
        ...order,
        styxproxy_credential: order.styxproxy_credential
          ? { status: order.styxproxy_credential.status }
          : undefined,
      };
      // created_at is already in order from the poll response — pass it through
      // so the PDF receipt shows the real order date, not the download date.
      await generateReceiptPDF(receiptSafeOrder, receiptItems, txRef!, `styxproxy-receipt-${txRef}.pdf`, detectReceiptTheme());
    }
  };

  const handleCopyCredentials = async (cred?: OrderData['styxproxy_credential']) => {
    if (!cred) return;
    const text = [
      `Username: ${cred.styxproxy_username || ''}`,
      `Password: ${cred.styxproxy_password || ''}`,
      `Proxy: ${cred.upstream_proxy_ip || ''}:${cred.upstream_proxy_port || ''}`,
      `Full: http://${cred.styxproxy_username || ''}:${cred.styxproxy_password || ''}@${cred.upstream_proxy_ip || ''}:${cred.upstream_proxy_port || ''}`,
    ].join('\n');
    try {
      await navigator.clipboard.writeText(text);
      toast({ type: 'success', title: 'Copied!', message: 'Credentials copied to clipboard.' });
    } catch {
      toast({ type: 'error', title: 'Copy failed', message: 'Use Ctrl+C / Cmd+C instead.' });
    }
  };

  if (!txRef || error) {
    return (
      <section className="flex-1 flex items-center justify-center px-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Order Not Found</h1>
          <p className="text-[var(--muted)] mb-6">
            We couldn&apos;t find an order with that reference.
          </p>
          {/* Self-service lookup */}
          <div className="max-w-md mx-auto mb-6 p-4 bg-[var(--card)] border border-[var(--border)] rounded-xl">
            <h2 className="text-lg font-semibold mb-3">Look Up Your Order</h2>
            <p className="text-sm text-[var(--muted)] mb-4">Enter the email and order ID from your checkout confirmation.</p>
            <div className="space-y-3">
              <input
                type="email"
                value={lookupEmail}
                onChange={e => setLookupEmail(e.target.value)}
                placeholder="Email address"
                className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none text-sm"
              />
              <input
                type="text"
                value={lookupOrderId}
                onChange={e => setLookupOrderId(e.target.value)}
                placeholder="Order ID (e.g. STX-ABC123)"
                className="w-full px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none text-sm"
              />
              {lookupError && <p className="text-sm text-[var(--error)]">{lookupError}</p>}
              {lookupResult && (
                <div className="p-3 bg-[var(--card-hover)] rounded-lg text-left text-sm">
                  <p><span className="text-[var(--muted)]">Status:</span> <span className="font-medium capitalize">{lookupResult.status}</span></p>
                  <p><span className="text-[var(--muted)]">Plan:</span> {lookupResult.plan_code || 'N/A'}</p>
                  <p><span className="text-[var(--muted)]">Amount:</span> ₦{lookupResult.amount_paid_ngn?.toLocaleString() || 'N/A'}</p>
                  {lookupResult.message && <p className="mt-2 text-[var(--primary-text)]">{lookupResult.message}</p>}
                </div>
              )}
              <button
                onClick={handleLookup}
                disabled={lookupLoading}
                className="w-full px-4 py-2 bg-[var(--primary)] text-black font-medium rounded-lg text-sm disabled:opacity-50"
              >
                {lookupLoading ? 'Looking up...' : 'Look Up Order'}
              </button>
            </div>
          </div>
          <Link
            href="/order"
            className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
          >
            Place New Order
          </Link>
        </div>
      </section>
    );
  }

  const isPending = order?.status === 'pending' || order?.status === 'paid';
  const isSuccess = order?.status === 'fulfilled' || order?.status === 'active';
  const isErrorState = order?.status === 'expired' || order?.status === 'cancelled' || order?.status === 'refunded';
  const isPaymentFailed = nextAction === 'show_failure' || nextAction === 'show_retry';
  const isRetryState = nextAction === 'show_retry';
  const isProviderDown = nextAction === 'provider_down';

  return (
    <section className="flex-1 flex items-start justify-center px-4 pt-32 pb-16">
      <div className="max-w-lg w-full">
        {/* Pending/Processing State */}
        {loading && isPending && (
          <div className="text-center animate-fade-in">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full border-4 border-[var(--primary)] border-t-transparent animate-spin" />
            <h1 className="text-2xl font-bold mb-2">Payment Confirmed!</h1>
            <p className="text-[var(--muted)]">Preparing your proxy credentials...</p>
            <p className="text-sm text-[var(--muted)] mt-4">Reference: {txRef}</p>
          </div>
        )}

        {/* Success State */}
        {isSuccess && (
          <div className="animate-fade-in">
            <div className="text-center mb-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--primary)]/20 flex items-center justify-center">
                <Check className="w-8 h-8 text-[var(--primary-text)]" weight="bold" />
              </div>
              <h1 className="text-3xl font-bold text-[var(--primary-text)] mb-2">
                {order?.customer_name?.trim() ? `Thank you, ${order.customer_name.trim()}.` : 'Thank you, customer.'}
              </h1>
              <p className="text-[var(--muted)]">Your proxies are ready. Here are your credentials:</p>
            </div>

            {/* Credentials Card — shows ALL proxies for basket orders */}
            <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">
                  {order?.credentials && order.credentials.length > 1
                    ? `Proxy Credentials (${order.credentials.length})`
                    : 'Proxy Credentials'}
                </h2>
                {order?.styxproxy_credential && (
                  <button
                    onClick={() => handleCopyCredentials(order?.styxproxy_credential)}
                    className="text-xs px-3 py-1.5 bg-[var(--primary)]/10 hover:bg-[var(--primary)]/20 text-[var(--primary-text)] border border-[var(--primary)]/30 rounded-lg transition-colors flex items-center gap-1.5"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    Copy
                  </button>
                )}
              </div>

              {order?.credentials && order.credentials.length > 0 ? (
                <div className="space-y-6">
                  {order.credentials.map((cred, idx) => (
                    <div key={idx} className={idx > 0 ? 'pt-6 border-t border-[var(--border)]' : ''}>
                      {order.credentials!.length > 1 && (
                        <p className="text-sm font-medium text-[var(--primary-text)] mb-3">Proxy {idx + 1}</p>
                      )}
                      <div className="space-y-4">
                        <div>
                          <label className="text-sm text-[var(--muted)]">Username</label>
                          <p className="font-mono text-lg">{cred.styxproxy_username}</p>
                        </div>
                        <div>
                          <label className="text-sm text-[var(--muted)]">Protocol</label>
                          <p className="font-mono text-sm">HTTP / SOCKS5</p>
                        </div>
                        <div>
                          <label className="text-sm text-[var(--muted)]">Proxy Address</label>
                          <p className="font-mono text-lg">{cred.upstream_proxy_ip}:{cred.upstream_proxy_port}</p>
                        </div>
                        <div>
                          <label className="text-sm text-[var(--muted)]">Password</label>
                          <p className="font-mono text-sm">{cred.styxproxy_password || 'N/A'}</p>
                        </div>
                        <div className="col-span-2">
                          <label className="text-sm text-[var(--muted)]">Full Format</label>
                          <p className="font-mono text-base text-[var(--muted)] break-all leading-relaxed">
                            http://{cred.styxproxy_username}:{cred.styxproxy_password || 'YOUR_PASSWORD'}@{cred.upstream_proxy_ip}:{cred.upstream_proxy_port}
                          </p>
                        </div>
                        <div>
                          <label className="text-sm text-[var(--muted)]">Expires</label>
                          <p className="font-medium">
                            {order.expires_at
                              ? new Date(order.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })
                              : 'N/A'}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : order?.styxproxy_credential ? (
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-[var(--muted)]">Username</label>
                    <p className="font-mono text-lg">{order.styxproxy_credential.styxproxy_username}</p>
                  </div>
                  <div>
                    <label className="text-sm text-[var(--muted)]">Protocol</label>
                    <p className="font-mono text-sm">HTTP / SOCKS5</p>
                  </div>
                  <div>
                    <label className="text-sm text-[var(--muted)]">Proxy Address</label>
                    <p className="font-mono text-lg">{order.styxproxy_credential.upstream_proxy_ip}:{order.styxproxy_credential.upstream_proxy_port}</p>
                  </div>
                  <div>
                    <label className="text-sm text-[var(--muted)]">Password</label>
                    <p className="font-mono text-sm">{order.styxproxy_credential.styxproxy_password || 'N/A'}</p>
                  </div>
                  <div className="col-span-2">
                    <label className="text-sm text-[var(--muted)]">Full Format</label>
                    <p className="font-mono text-base text-[var(--muted)] break-all leading-relaxed">
                      http://{order.styxproxy_credential.styxproxy_username}:{order.styxproxy_credential.styxproxy_password || 'YOUR_PASSWORD'}@{order.styxproxy_credential.upstream_proxy_ip}:{order.styxproxy_credential.upstream_proxy_port}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm text-[var(--muted)]">Expires</label>
                    <p className="font-medium">
                      {order.styxproxy_credential.expires_at
                        ? new Date(order.styxproxy_credential.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })
                        : 'N/A'}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {receiptItems.map((item, idx) => (
                    <div key={item.plan_code} className="p-3 rounded-lg bg-[var(--card-hover)]">
                      <div className="flex items-center gap-2 mb-2">
                        <Flag countryCode={item.country_code} size={20} />
                        <span className="font-medium">{item.name}</span>
                        <span className="text-sm text-[var(--muted)]">× {item.quantity}</span>
                      </div>
                      <p className="text-sm text-[var(--muted)]">Credentials will be delivered shortly</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Order Summary */}
            <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-[var(--muted)]">Order ID</span>
                  <p className="font-medium">{order?.order_id || txRef}</p>
                </div>
                <div>
                  <span className="text-[var(--muted)]">Amount Paid</span>
                  <p className="font-medium">₦{(order?.amount_paid_ngn || 0).toLocaleString('en-NG')}</p>
                </div>
                <div>
                  <span className="text-[var(--muted)]">Status</span>
                  <p className="font-medium text-[var(--primary-text)] capitalize">{order?.status}</p>
                </div>
                <div>
                  <span className="text-[var(--muted)]">Items</span>
                  <p className="font-medium">
                    {(() => {
                      const qty = order?.quantity || receiptItems.reduce((s, i) => s + i.quantity, 0);
                      return `${qty || 1} ${(qty || 1) > 1 ? 'proxies' : 'proxy'}`;
                    })()}
                  </p>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-3">
              {receiptItems.length > 0 && (
                <button
                  onClick={handleDownloadPDF}
                  className="w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <ArrowLineDown className="w-5 h-5" />
                  Download Receipt (PDF)
                </button>
              )}
              <Link
                href={`/manage?ref=${txRef}`}
                className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
              >
                Manage Order
              </Link>
              <Link
                href="/order"
                className="block w-full px-6 py-3 text-[var(--muted)] hover:text-[var(--foreground)] text-center transition-colors"
              >
                Order Another
              </Link>
            </div>
          </div>
        )}

        {/* Provider Down State */}
        {!loading && isProviderDown && (
          <div className="text-center animate-fade-in">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-orange-500/20 flex items-center justify-center">
              <Warning className="w-8 h-8 text-orange-500" weight="bold" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Provider Temporarily Unavailable</h1>
            <p className="text-[var(--muted)] mb-2">Our proxy provider is temporarily out of stock for your selected region.</p>
            {order?.user_message && <p className="text-sm text-orange-400 mb-6">{order.user_message}</p>}
            <p className="text-sm text-[var(--muted)] mb-6">
              Your payment was received. Your credentials are being generated — this usually takes a few minutes.
              Reference: <span className="font-mono">{txRef}</span>
            </p>
            <div className="space-y-3">
              <Link
                href={`/manage?ref=${txRef}`}
                className="block w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg text-center transition-colors"
              >
                Check Order Status
              </Link>
              <Link
                href="/order"
                className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
              >
                Browse Other Plans
              </Link>
            </div>
          </div>
        )}

        {/* Error/Expired State */}
        {!loading && isErrorState && (
          <div className="text-center animate-fade-in">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--error)]/20 flex items-center justify-center">
              <XCircle className="w-8 h-8 text-[var(--error)]" weight="bold" />
            </div>
            <h1 className="text-2xl font-bold mb-2">
              {order?.status === 'expired' ? 'Order Expired' : order?.status === 'refunded' ? 'Order Refunded' : 'Order Cancelled'}
            </h1>
            <p className="text-[var(--muted)] mb-6">
              {order?.status === 'refunded' ? (
                <>Your order has been refunded. The provider could not deliver a working proxy. Refund processing typically takes 5–10 minutes — contact <a href="https://wa.me/2347032981049" className="text-[var(--primary-text)] hover:underline">support</a> if you don&apos;t see it within 24 hours.</>
              ) : (
                'This order is no longer active.'
              )}
            </p>
            <Link
              href="/order"
              className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
            >
              Place New Order
            </Link>
          </div>
        )}

        {/* Payment Failed State */}
        {!loading && isPaymentFailed && (
          <div className="animate-fade-in">
            {nextAction === 'show_failure' && (
              <div className="mb-6 p-4 bg-[var(--error)]/10 border border-[var(--error)]/30 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[var(--error)]/20 flex items-center justify-center flex-shrink-0">
                    <WarningCircle className="w-5 h-5 text-[var(--error)]" weight="bold" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-red-400">Payment could not be processed</h2>
                    <p className="text-sm text-[var(--muted)] mt-1">{userMessage || 'There was an issue processing your payment. Please contact support if you were charged.'}</p>
                  </div>
                </div>
              </div>
            )}
            {nextAction === 'show_retry' && (
              <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
                    <Warning className="w-5 h-5 text-yellow-500" weight="bold" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-yellow-400">Your order is still being processed</h2>
                    <p className="text-sm text-[var(--muted)] mt-1">{userMessage || 'Please wait while we complete your order. This usually takes a few moments.'}</p>
                  </div>
                </div>
              </div>
            )}
            <div className="text-center mb-6">
              <p className="text-sm text-[var(--muted)]">Reference: <span className="font-mono">{txRef}</span></p>
              {order?.order_id && <p className="text-sm text-[var(--muted)]">Order ID: <span className="font-mono">{order.order_id}</span></p>}
            </div>
            <div className="space-y-3">
              <Link
                href="/order"
                className="block w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg text-center transition-colors"
              >
                Try Again
              </Link>
              <Link
                href="/contact"
                className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--error)]/50 text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
              >
                Contact Support
              </Link>
            </div>
          </div>
        )}

        {/* Timeout State */}
        {!loading && !order && attempts >= maxAttempts && (
          <div className="text-center animate-fade-in">
            <h1 className="text-2xl font-bold mb-2">Still Processing</h1>
            <p className="text-[var(--muted)] mb-2">Your order is still being processed. Your payment was received — credentials are being generated.</p>
            <p className="text-sm text-[var(--muted)] mb-6">Reference: <span className="font-mono">{txRef}</span></p>
            <div className="space-y-3">
              <button
                onClick={() => { setAttempts(0); setOrder(null); setNextAction('poll'); }}
                className="w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
              >
                Retry Now
              </button>
              <Link
                href={`/manage?ref=${txRef}`}
                className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
              >
                Check Order Status
              </Link>
              <Link
                href="/order"
                className="block w-full px-6 py-3 text-[var(--muted)] hover:text-[var(--foreground)] text-center transition-colors"
              >
                Order Another
              </Link>
            </div>
            <p className="text-base text-[var(--muted)] mt-4">
              Tip: paste your reference (STX-XXXXXX) in the search box on the next page. If it shows credentials, you can use them immediately.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

export default function ThankYouPage() {
  return (
    <Suspense fallback={
      <section className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </section>
    }>
      <ThankYouContent />
    </Suspense>
  );
}
