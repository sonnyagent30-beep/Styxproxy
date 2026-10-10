'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import StatusBanner from '@/components/order/StatusBanner';
import ActionBar from '@/components/order/ActionBar';
import OrderTimeline from '@/components/order/OrderTimeline';
import RenewalModal from '@/components/order/RenewalModal';
import { getActionsForStatus, getTimelineSteps, getStatusGroup } from '@/lib/order-status';
import { getOrderHistory, type OrderHistoryEntry, cleanupStalePendingOrders, clearOrderHistory, removeFromHistory } from '@/lib/device-id';
import { Eye, EyeSlash, Copy, Clock, Check, ArrowRight, WarningCircle, MagnifyingGlass, X } from '@phosphor-icons/react';
import { useCharonStore } from '@/store/charon-store';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.styxproxy.com';

interface OrderData {
  order_id: string;
  tx_ref?: string;
  status: string;
  plan_type: string;
  country: string;
  amount_paid_ngn: number;
  created_at?: string;
  expires_at?: string;
  styxproxy_credential?: {
    styxproxy_username: string;
    styxproxy_password: string;
    upstream_proxy_ip: string;
    upstream_proxy_port: number;
    expires_at: string;
  };
  // For basket orders: ALL credentials created for this order.
  credentials?: Array<{
    styxproxy_username: string;
    styxproxy_password: string;
    upstream_proxy_ip: string;
    upstream_proxy_port: number;
    status?: string;
  }>;
  max_rotations?: number;
  rotation_count?: number;
  is_renewable?: boolean;
  user_message?: string;
  next_action?: string;
}

function CredentialField({ label, value, sensitive = false }: { label: string; value: string; sensitive?: boolean }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div className="bg-[var(--background)] rounded-xl p-4">
      <span className="text-xs text-[var(--muted)]">{label}</span>
      <div className="flex items-center justify-between mt-1">
        <p className={`font-mono text-sm font-medium ${sensitive && !revealed ? 'blur-sm select-none' : 'break-all'}`}>
          {sensitive && !revealed ? '••••••••' : value}
        </p>
        <div className="flex items-center gap-1">
          {sensitive && (
            <button
              onClick={() => setRevealed(!revealed)}
              className="text-[var(--muted)] hover:text-foreground p-1"
              aria-label={revealed ? 'Hide' : 'Show'}
            >
              {revealed ? <EyeSlash className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          )}
          <button
            onClick={() => navigator.clipboard.writeText(value)}
            className="text-[var(--muted)] hover:text-foreground p-1"
            aria-label={`Copy ${label}`}
          >
            <Copy className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function OrderStatusContent() {
  const searchParams = useSearchParams();
  const [searchInput, setSearchInput] = useState('');
  const [order, setOrder] = useState<OrderData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<OrderHistoryEntry[]>([]);
  const [rotating, setRotating] = useState(false);
  const [showRenewalModal, setShowRenewalModal] = useState(false);
  // Charon: the store is the single source of truth for the widget's open
  // state. Both "Contact Support" affordances used to dispatch a window
  // CustomEvent that nothing listened for, so they silently did nothing.
  const setCharonOpen = useCharonStore((s) => s.setOpen);
  const setCharonProactive = useCharonStore((s) => s.setProactiveMessage);
  const charonAvailable = useCharonStore((s) => s.charonAvailable);
  const setCharonAvailable = useCharonStore((s) => s.setCharonAvailable);
  const openCharon = () => { setCharonProactive(null); setCharonOpen(true); };

  // A2: Fetch health to get charon_available flag
  useEffect(() => {
    let cancelled = false;
    async function fetchHealth() {
      try {
        const res = await fetch('/api/v1/health', { credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled) {
          setCharonAvailable(data.charon_available !== false);
        }
      } catch {
        if (!cancelled) setCharonAvailable(true);
      }
    }
    fetchHealth();
    return () => { cancelled = true; };
  }, [setCharonAvailable]);

  useEffect(() => {
    cleanupStalePendingOrders();
    setHistory(getOrderHistory());
    const orderId = searchParams.get('order_id');
    if (orderId) {
      setSearchInput(orderId);
      handleSearch(orderId);
    }
  }, [searchParams]);

  async function handleSearch(ref: string) {
    if (!ref.trim()) {
      setError('Please enter an order ID or transaction reference');
      return;
    }
    setLoading(true);
    setError('');
    setOrder(null);
    const trimmedRef = ref.trim();
    const isPaymentRef = trimmedRef.startsWith('STX-') || trimmedRef.startsWith('stx-')
      || trimmedRef.startsWith('TXF-') || trimmedRef.startsWith('txf-');
    const endpoint = isPaymentRef
      ? `${API_BASE_URL}/api/orders/by-payment-reference/${trimmedRef}`
      : `${API_BASE_URL}/api/orders/${trimmedRef}`;
    try {
      const res = await fetch(endpoint);
      const data = await res.json();
      if (res.ok && data.order_id) {
        setOrder(data);
      } else {
        const msg = typeof data.detail === 'string' ? data.detail
          : typeof data.error === 'string' ? data.error
          : JSON.stringify(data.detail || data.error || data);
        setError(typeof msg === 'string' ? msg : 'Order not found. Double-check your order ID and try again.');
      }
    } catch {
      setError('Network error. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleRotateKey() {
    if (!order?.order_id) return;
    setRotating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/orders/${order.order_id}/rotate`, { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.styxproxy_credential) {
        setOrder(prev => prev ? { ...prev, styxproxy_credential: data.styxproxy_credential, rotation_count: (prev.rotation_count ?? 0) + 1 } : null);
      } else {
        alert(data.error || 'Rotation failed. Please try again.');
      }
    } catch {
      alert('Network error. Please try again.');
    } finally {
      setRotating(false);
    }
  }

  const isNearExpiry = order?.expires_at
    ? new Date(order.expires_at).getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000
    : false;

  const actions = order ? getActionsForStatus(order.status, order.order_id, {
    rotationsLeft: (order.max_rotations ?? 3) - (order.rotation_count ?? 0),
    isRenewable: order.is_renewable,
    isNearExpiry,
  }) : [];

  const timelineSteps = order ? getTimelineSteps(order.status, {
    created: order.created_at,
    expires: order.expires_at,
  }) : [];

  // Return to the lookup form. There was NO way back once a result rendered —
  // the page became a dead end (only the header nav remained, and the lookup
  // card is hidden while a result is shown). Clears the result, the error and
  // the input so the reader lands on a clean search.
  const handleBack = () => {
    setOrder(null);
    setError(null);
    setSearchInput('');
  };

  return (
    <div className="min-h-screen flex flex-col">
      <section className="flex-1 px-4 pt-16 pb-16">
        <div className="max-w-2xl mx-auto">
          {/* Back to search — only meaningful once a result is on screen */}
          {order && (
            <button
              type="button"
              onClick={handleBack}
              className="inline-flex items-center gap-2 mb-4 text-sm font-medium text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              <ArrowRight className="w-4 h-4 rotate-180" aria-hidden="true" />
              Back to search
            </button>
          )}

          {/* Search Card */}
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
            <h1 className="text-2xl font-bold mb-4">Order Status</h1>
            <label className="block text-sm font-medium mb-3">Order ID or Transaction Reference</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch(searchInput)}
                placeholder="e.g. STX-XXXXX"
                className="flex-1 px-4 py-3 bg-[var(--background)] border border-[var(--border)] rounded-xl focus:outline-none focus:border-[var(--primary)] transition-colors text-sm"
              />
              <button
                onClick={() => handleSearch(searchInput)}
                disabled={loading}
                className="px-5 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors disabled:opacity-50 text-sm whitespace-nowrap"
              >
                {loading ? 'Searching…' : 'Look Up'}
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-[var(--error)]/10 border border-[var(--error)]/30 rounded-xl p-4 mb-6 flex items-start gap-3">
              <WarningCircle className="w-5 h-5 text-[var(--error)] shrink-0 mt-0.5" />
              <p className="text-[var(--error)] text-sm">{error}</p>
            </div>
          )}

          {/* Order Found */}
          {order && (
            <div className="space-y-4">
              {/* Status Banner */}
              <StatusBanner status={order.status} userMessage={order.user_message} />

              {/* Action Bar */}
              <ActionBar
                actions={actions}
                onAction={(action) => {
                  if (action.kind === 'rotate') handleRotateKey();
                  if (action.kind === 'cancel') {
                    if (confirm('Are you sure you want to cancel this order?')) {
                      alert('Please contact support to cancel your order.');
                    }
                  }
                  if (action.kind === 'renew') setShowRenewalModal(true);
                  if (action.kind === 'contact_support') {
                    openCharon();
                  }
                }}
              />

              {/* Renewal Modal */}
              {showRenewalModal && (
                <RenewalModal
                  order={order}
                  onClose={() => setShowRenewalModal(false)}
                  onRenewed={(updatedOrder) => setOrder(updatedOrder)}
                />
              )}

              {/* Order Details */}
              <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
                <h2 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Order Details</h2>
                <div className="space-y-3">
                  {order.order_id && (
                    <div className="flex items-center justify-between py-2 border-b border-[var(--border)]">
                      <span className="text-sm text-[var(--muted)]">Order ID</span>
                      <span className="text-sm font-mono font-medium">{order.order_id}</span>
                    </div>
                  )}
                  {order.tx_ref && (
                    <div className="flex items-center justify-between py-2 border-b border-[var(--border)]">
                      <span className="text-sm text-[var(--muted)]">Transaction Ref</span>
                      <span className="text-sm font-mono font-medium">{order.tx_ref}</span>
                    </div>
                  )}
                  {order.plan_type && (
                    <div className="flex items-center justify-between py-2 border-b border-[var(--border)]">
                      <span className="text-sm text-[var(--muted)]">Plan</span>
                      <span className="text-sm font-medium">{order.plan_type}</span>
                    </div>
                  )}
                  {order.country && (
                    <div className="flex items-center justify-between py-2 border-b border-[var(--border)]">
                      <span className="text-sm text-[var(--muted)]">Country</span>
                      <span className="text-sm font-medium">{order.country}</span>
                    </div>
                  )}
                  {order.amount_paid_ngn != null && (
                    <div className="flex items-center justify-between py-2 border-b border-[var(--border)]">
                      <span className="text-sm text-[var(--muted)]">Amount Paid</span>
                      <span className="text-sm font-semibold text-[var(--primary-text)]">₦{order.amount_paid_ngn.toLocaleString('en-NG')}</span>
                    </div>
                  )}
                  {order.created_at && (
                    <div className="flex items-center justify-between py-2 border-b border-[var(--border)]">
                      <span className="text-sm text-[var(--muted)]">Ordered</span>
                      <span className="text-sm">{new Date(order.created_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                    </div>
                  )}
                  {order.expires_at && (
                    <div className="flex items-center justify-between py-2">
                      <span className="text-sm text-[var(--muted)]">Expires</span>
                      <span className="text-sm">{new Date(order.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Credentials — shows ALL proxies for basket orders */}
              {(order.status === 'fulfilled' || order.status === 'active') && (order.credentials && order.credentials.length > 0 || order.styxproxy_credential) && (
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wide">
                      {order.credentials && order.credentials.length > 1
                        ? `Your Proxy Credentials (${order.credentials.length})`
                        : 'Your Proxy Credentials'}
                    </h2>
                    <span className="text-xs text-[var(--muted)]">
                      {(order.max_rotations ?? 3) - (order.rotation_count ?? 0)} rotation{(order.max_rotations ?? 3) - (order.rotation_count ?? 0) !== 1 ? 's' : ''} left
                    </span>
                  </div>
                  <div className="space-y-3">
                    {order.expires_at && isNearExpiry && (
                      <div className="bg-[var(--warning)]/10 border border-[var(--warning)]/30 rounded-xl p-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4 text-[var(--warning)]" />
                          <span className="text-sm text-[var(--warning)]">Expires soon</span>
                        </div>
                        <span className="text-xs text-[var(--muted)]">
                          {new Date(order.expires_at).toLocaleDateString('en-NG', { month: 'short', day: 'numeric' })}
                        </span>
                      </div>
                    )}
                    {order.credentials && order.credentials.length > 0 ? (
                      <div className="space-y-4">
                        {order.credentials.map((cred, idx) => (
                          <div key={idx} className={idx > 0 ? 'pt-4 border-t border-[var(--border)]' : ''}>
                            {order.credentials!.length > 1 && (
                              <p className="text-xs font-medium text-[var(--primary-text)] mb-2">Proxy {idx + 1}</p>
                            )}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                              <CredentialField label="Username" value={cred.styxproxy_username} />
                              <CredentialField label="Password" value={cred.styxproxy_password} sensitive />
                              <CredentialField label="Proxy Address" value={`${cred.upstream_proxy_ip}:${cred.upstream_proxy_port}`} />
                              <div className="bg-[var(--background)] rounded-xl p-4">
                                <span className="text-xs text-[var(--muted)]">Protocol</span>
                                <p className="font-mono text-sm font-medium">HTTP / SOCKS5</p>
                              </div>
                            </div>
                            <div className="bg-[var(--background)] rounded-xl p-4 mt-3">
                              <span className="text-xs text-[var(--muted)]">Full Format</span>
                              <p className="font-mono text-base text-[var(--muted)] break-all leading-relaxed">
                                http://{cred.styxproxy_username}:{cred.styxproxy_password}@{cred.upstream_proxy_ip}:{cred.upstream_proxy_port}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : order.styxproxy_credential ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <CredentialField label="Username" value={order.styxproxy_credential.styxproxy_username} />
                        <CredentialField label="Password" value={order.styxproxy_credential.styxproxy_password} sensitive />
                        <CredentialField label="Proxy Address" value={`${order.styxproxy_credential.upstream_proxy_ip}:${order.styxproxy_credential.upstream_proxy_port}`} />
                        <div className="bg-[var(--background)] rounded-xl p-4">
                          <span className="text-xs text-[var(--muted)]">Protocol</span>
                          <p className="font-mono text-sm font-medium">HTTP / SOCKS5</p>
                        </div>
                      </div>
                    ) : null}
                    {order.styxproxy_credential && (
                      <div className="bg-[var(--background)] rounded-xl p-4">
                        <span className="text-xs text-[var(--muted)]">Full Format</span>
                        <p className="font-mono text-base text-[var(--muted)] break-all leading-relaxed">
                          http://{order.styxproxy_credential.styxproxy_username}:{order.styxproxy_credential.styxproxy_password}@{order.styxproxy_credential.upstream_proxy_ip}:{order.styxproxy_credential.upstream_proxy_port}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Timeline */}
              <OrderTimeline steps={timelineSteps} />

              {/* Help Footer */}
              <div className="text-center pt-4 border-t border-[var(--border)]">
                <p className="text-sm text-[var(--muted)]">
                  Need help with this order?{' '}
                  {charonAvailable ? (
                    <button
                      onClick={openCharon}
                      className="text-[var(--primary-text)] hover:underline font-medium"
                    >
                      Chat with Charon →
                    </button>
                  ) : (
                    <a
                      href="https://wa.me/2347032981049"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[var(--primary-text)] hover:underline font-medium"
                    >
                      Contact support
                    </a>
                  )}
                </p>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!order && !error && !loading && (
          <div className="text-center py-10">
          <div className="w-16 h-16 rounded-2xl bg-[var(--card)] border border-[var(--border)] flex items-center justify-center mx-auto mb-4">
            <MagnifyingGlass className="w-8 h-8 text-[var(--muted)]" />
          </div>
          <p className="text-sm text-[var(--muted)]">
            Enter your order ID or tx_ref above to look up your proxy details.
          </p>
          </div>
          )}

          {/* Recent Orders */}
          {history.length > 0 && !order && (
          <div className="mt-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wide">Recent Orders (This Device)</h2>
            {history.length > 1 && (
              <button
                onClick={() => { clearOrderHistory(); setHistory([]); }}
                className="text-xs text-[var(--muted)] hover:text-[var(--error)] transition-colors"
              >
                Clear all
              </button>
            )}
          </div>
          <div className="space-y-2">
            {history.map((h) => (
              <div
                key={h.tx_ref}
                className="w-full text-left bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] rounded-xl p-3 transition-colors relative group"
              >
                <button
                  onClick={() => { setSearchInput(h.tx_ref); handleSearch(h.tx_ref); }}
                  className="w-full text-left"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-mono text-sm font-medium">{h.tx_ref}</span>
                      <p className="text-base text-[var(--muted)] mt-0.5">
                        {h.plan_code} · {h.country} · ₦{h.amount.toLocaleString('en-NG')}
                      </p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-md ${
                      h.status === 'active' || h.status === 'fulfilled'
                        ? 'bg-[var(--success)]/20 text-[var(--success)]'
                        : 'bg-[var(--warning)]/20 text-[var(--warning)]'
                    }`}>
                      {h.status}
                    </span>
                  </div>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); removeFromHistory(h.tx_ref); setHistory(getOrderHistory()); }}
                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-[var(--muted)] hover:text-[var(--error)] transition-all p-1"
                  title="Remove from history"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
          </div>
          )}
        </div>
      </section>
    </div>
  );
}

function LoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-[var(--muted)]">Loading...</div>
    </div>
  );
}

export default function OrderStatusClient() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <OrderStatusContent />
    </Suspense>
  );
}
