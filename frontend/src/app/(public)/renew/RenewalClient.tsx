'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowRight,
  Check,
  Clock,
  Copy,
  Eye,
  EyeSlash,
  HardDrives,
  House,
  DeviceMobile,
  Database,
  Globe,
  MagnifyingGlass,
  WarningCircle,
  X,
} from '@phosphor-icons/react';
import api from '@/lib/api';
import { getDeviceId, getOrderHistory, addToOrderHistory } from '@/lib/device-id';
import type { Order, RenewalResponse, RenewalHistoryResponse } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.styxproxy.com';

// ── Types ──

interface ProxyOrder {
  order_id: string;
  status: string;
  plan_type: string;
  plan_code?: string;
  country?: string;
  quantity?: number;
  amount_paid_ngn?: number;
  expires_at?: string;
  data_remaining_gb?: number;
  data_total_gb?: number;
  styxproxy_credential?: {
    styxproxy_username: string;
    styxproxy_password?: string;
    upstream_proxy_ip?: string;
    upstream_proxy_port?: number;
    status?: string;
  };
}

// ── Helper: get plan type icon ──
function getPlanIcon(planType: string) {
  switch (planType?.toLowerCase()) {
    case 'residential':
      return <House className="w-5 h-5" />;
    case 'mobile':
      return <DeviceMobile className="w-5 h-5" />;
    case 'datacenter':
    case 'dc':
      return <Database className="w-5 h-5" />;
    case 'isp':
      return <Globe className="w-5 h-5" />;
    default:
      return <Globe className="w-5 h-5" />;
  }
}

// ── Helper: format date ──
function formatDate(dateStr?: string) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-NG', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// ── Helper: days until expiry ──
function daysUntilExpiry(expiresAt?: string): number | null {
  if (!expiresAt) return null;
  const diff = new Date(expiresAt).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

// ── Credential field with show/hide ──
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

// ── Main component ──
export default function RenewalClient() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [orders, setOrders] = useState<ProxyOrder[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<ProxyOrder | null>(null);
  const [customGb, setCustomGb] = useState<string>('');
  const [selectedTier, setSelectedTier] = useState<number | null>(null);
  const [renewalHistory, setRenewalHistory] = useState<RenewalResponse[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [renewalError, setRenewalError] = useState<string | null>(null);
  const [renewalSuccess, setRenewalSuccess] = useState<string | null>(null);

  // GB tiers for residential/mobile
  const GB_TIERS = [5, 10, 20, 50];

  // Fetch orders for this device
  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const deviceId = getDeviceId();
      const res = await fetch(`${API_BASE_URL}/api/orders/by-device`, {
        headers: {
          'X-Device-Id': deviceId,
        },
      });
      const data = await res.json();
      if (res.ok && Array.isArray(data)) {
        // Filter to active/fulfilled orders only (renewable)
        const renewable = data.filter(
          (o: ProxyOrder) => o.status === 'active' || o.status === 'fulfilled' || o.status === 'expired'
        );
        setOrders(renewable);
      } else {
        setError('Could not load your orders. Please try again.');
      }
    } catch {
      setError('Network error. Please check your connection.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch renewal history for selected order
  const fetchRenewalHistory = useCallback(async (orderId: string) => {
    setHistoryLoading(true);
    try {
      const res = await api.getRenewalsForOrder(orderId);
      if (res.data) {
        setRenewalHistory(res.data.renewals);
      }
    } catch {
      // Non-critical — history is optional
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  // Fetch renewal history when order is selected
  useEffect(() => {
    if (selectedOrder) {
      fetchRenewalHistory(selectedOrder.order_id);
    }
  }, [selectedOrder, fetchRenewalHistory]);

  // ── Handle renewal payment ──
  const handleRenew = async () => {
    if (!selectedOrder) return;

    const planType = (selectedOrder.plan_type || '').toLowerCase();
    const isPerGb = planType === 'residential' || planType === 'mobile';

    // Validate GB selection for residential/mobile
    if (isPerGb) {
      const gb = selectedTier || parseInt(customGb, 10);
      if (!gb || gb < 5) {
        setRenewalError('Minimum renewal is 5 GB');
        return;
      }
    }

    setProcessing(true);
    setRenewalError(null);
    setRenewalSuccess(null);

    try {
      const idempotencyKey = `renew-${selectedOrder.order_id}-${Date.now()}`;
      const res = await api.initiateRenewal({
        order_id: selectedOrder.order_id,
        quantity_gb: isPerGb ? (selectedTier || parseInt(customGb, 10)) : undefined,
        gateway: 'flutterwave',
        idempotency_key: idempotencyKey,
      });

      if (res.data?.checkout_url) {
        // Add to order history
        addToOrderHistory({
          tx_ref: res.data.tx_ref,
          order_id: selectedOrder.order_id,
          plan_code: selectedOrder.plan_code || '',
          country: selectedOrder.country || '',
          amount: res.data.amount_ngn,
          status: 'pending',
          created_at: new Date().toISOString(),
        });

        // Redirect to payment
        window.location.href = res.data.checkout_url;
      } else {
        setRenewalError(res.error || 'Could not start renewal. Please try again.');
      }
    } catch (err) {
      setRenewalError('Network error. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  // ── Render ──
  return (
    <div className="min-h-screen flex flex-col">
      <section className="flex-1 px-4 pt-16 pb-16">
        <div className="max-w-2xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[var(--primary)]/30 bg-[var(--primary)]/5 mb-6">
              <div className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] shadow-[0_0_8px_var(--primary)] animate-pulse" />
              <span className="text-xs font-medium tracking-widest uppercase text-[var(--muted)]">Renewal</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight mb-3">Renew Your Proxy</h1>
            <p className="text-[var(--muted)] leading-relaxed">
              Add more data or extend your subscription. Renewals stack from the renewal date.
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-[var(--error)]/10 border border-[var(--error)]/30 rounded-xl p-4 mb-6 flex items-start gap-3">
              <WarningCircle className="w-5 h-5 text-[var(--error)] shrink-0 mt-0.5" />
              <p className="text-[var(--error)] text-sm">{error}</p>
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="text-center py-12">
              <div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-[var(--muted)] text-sm">Loading your proxies...</p>
            </div>
          )}

          {/* No orders */}
          {!loading && !error && orders.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-2xl bg-[var(--card)] border border-[var(--border)] flex items-center justify-center mx-auto mb-4">
                <MagnifyingGlass className="w-8 h-8 text-[var(--muted)]" />
              </div>
              <p className="text-[var(--muted)] mb-4">No active proxies found for this device.</p>
              <Link
                href="/order"
                className="inline-flex items-center gap-2 px-5 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors"
              >
                Order a Proxy <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}

          {/* Order selection */}
          {!loading && !error && orders.length > 0 && !selectedOrder && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wide mb-4">Select a Proxy to Renew</h2>
              {orders.map((order) => {
                const daysLeft = daysUntilExpiry(order.expires_at);
                const isExpired = daysLeft !== null && daysLeft < 0;
                const isPerGb = (order.plan_type || '').toLowerCase() === 'residential' || (order.plan_type || '').toLowerCase() === 'mobile';

                return (
                  <button
                    key={order.order_id}
                    onClick={() => setSelectedOrder(order)}
                    className="w-full text-left bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] rounded-2xl p-5 transition-colors group"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] shrink-0">
                          {getPlanIcon(order.plan_type || '')}
                        </div>
                        <div>
                          <p className="font-semibold text-sm">{order.plan_code || order.plan_type}</p>
                          <p className="text-xs text-[var(--muted)] mt-0.5">
                            {order.country} · {isPerGb ? `${order.data_remaining_gb || 0} GB remaining` : 'Static IP'}
                          </p>
                          <p className="text-xs text-[var(--muted)] mt-0.5">
                            Expires: {formatDate(order.expires_at)}
                            {daysLeft !== null && !isExpired && (
                              <span className={daysLeft <= 7 ? 'text-[var(--warning)] ml-1' : 'ml-1'}>
                                ({daysLeft} days left)
                              </span>
                            )}
                            {isExpired && <span className="text-[var(--error)] ml-1">(Expired)</span>}
                          </p>
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-[var(--muted)] group-hover:text-[var(--primary)] transition-colors shrink-0 mt-1" />
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* Renewal configuration */}
          {!loading && !error && selectedOrder && (
            <div className="space-y-4">
              {/* Back button */}
              <button
                onClick={() => {
                  setSelectedOrder(null);
                  setSelectedTier(null);
                  setCustomGb('');
                  setRenewalError(null);
                  setRenewalSuccess(null);
                }}
                className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors flex items-center gap-1"
              >
                <X className="w-4 h-4" /> Back to proxy list
              </button>

              {/* Selected order summary */}
              <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] shrink-0">
                    {getPlanIcon(selectedOrder.plan_type || '')}
                  </div>
                  <div>
                    <p className="font-semibold text-sm">{selectedOrder.plan_code || selectedOrder.plan_type}</p>
                    <p className="text-xs text-[var(--muted)] mt-0.5">
                      {selectedOrder.country} · {formatDate(selectedOrder.expires_at)}
                    </p>
                  </div>
                </div>

                {/* Credential info */}
                {selectedOrder.styxproxy_credential && (
                  <div className="space-y-2 mb-4">
                    <CredentialField
                      label="Username"
                      value={selectedOrder.styxproxy_credential.styxproxy_username}
                    />
                    <CredentialField
                      label="Password"
                      value={selectedOrder.styxproxy_credential.styxproxy_password || ''}
                      sensitive
                    />
                    <CredentialField
                      label="Proxy Address"
                      value={`${selectedOrder.styxproxy_credential.upstream_proxy_ip || ''}:${selectedOrder.styxproxy_credential.upstream_proxy_port || 1080}`}
                    />
                  </div>
                )}
              </div>

              {/* GB selection for residential/mobile */}
              {(selectedOrder.plan_type || '').toLowerCase() === 'residential' || (selectedOrder.plan_type || '').toLowerCase() === 'mobile' ? (
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
                  <h3 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Select Data Amount</h3>

                  {/* GB Tiers */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                    {GB_TIERS.map((tier) => (
                      <button
                        key={tier}
                        onClick={() => {
                          setSelectedTier(tier);
                          setCustomGb('');
                        }}
                        className={`p-4 rounded-xl border text-center transition-all ${
                          selectedTier === tier
                            ? 'border-[var(--primary)] bg-[var(--primary)]/10'
                            : 'border-[var(--border)] hover:border-[var(--primary)]'
                        }`}
                      >
                        <p className="text-lg font-bold">{tier}</p>
                        <p className="text-xs text-[var(--muted)]">GB</p>
                      </button>
                    ))}
                  </div>

                  {/* Custom GB input */}
                  <div>
                    <label className="block text-sm font-medium mb-2">Or enter custom amount (min 5 GB)</label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        min={5}
                        value={customGb}
                        onChange={(e) => {
                          setCustomGb(e.target.value);
                          setSelectedTier(null);
                        }}
                        placeholder="e.g. 15"
                        className="flex-1 px-4 py-3 bg-[var(--background)] border border-[var(--border)] rounded-xl focus:outline-none focus:border-[var(--primary)] transition-colors text-sm"
                      />
                      <span className="px-4 py-3 bg-[var(--background)] border border-[var(--border)] rounded-xl text-sm text-[var(--muted)]">
                        GB
                      </span>
                    </div>
                  </div>

                  {/* Price preview */}
                  {(selectedTier || parseInt(customGb, 10) >= 5) && (
                    <div className="mt-4 p-4 bg-[var(--background)] rounded-xl">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-[var(--muted)]">Total</span>
                        <span className="text-lg font-bold text-[var(--primary)]">
                          ₦{((selectedTier || parseInt(customGb, 10)) * 1000).toLocaleString('en-NG')}
                        </span>
                      </div>
                      <p className="text-xs text-[var(--muted)] mt-1">
                        30 days from renewal date · Unlimited renewals
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                /* DC/ISP: simple renewal */
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
                  <h3 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Renew Subscription</h3>
                  <p className="text-sm text-[var(--muted)] mb-4">
                    Extend your proxy expiry by 30 days from the renewal date.
                  </p>
                  <div className="p-4 bg-[var(--background)] rounded-xl">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-[var(--muted)]">Total</span>
                      <span className="text-lg font-bold text-[var(--primary)]">
                        ₦{(selectedOrder.amount_paid_ngn || 0).toLocaleString('en-NG')}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--muted)] mt-1">
                      30 days from renewal date · Unlimited renewals
                    </p>
                  </div>
                </div>
              )}

              {/* Renewal error */}
              {renewalError && (
                <div className="bg-[var(--error)]/10 border border-[var(--error)]/30 rounded-xl p-4 flex items-start gap-3">
                  <WarningCircle className="w-5 h-5 text-[var(--error)] shrink-0 mt-0.5" />
                  <p className="text-[var(--error)] text-sm">{renewalError}</p>
                </div>
              )}

              {/* Renewal success */}
              {renewalSuccess && (
                <div className="bg-[var(--success)]/10 border border-[var(--success)]/30 rounded-xl p-4 flex items-start gap-3">
                  <Check className="w-5 h-5 text-[var(--success)] shrink-0 mt-0.5" />
                  <p className="text-[var(--success)] text-sm">{renewalSuccess}</p>
                </div>
              )}

              {/* Renew button */}
              <button
                onClick={handleRenew}
                disabled={processing || (() => {
                  const planType = (selectedOrder.plan_type || '').toLowerCase();
                  const isPerGb = planType === 'residential' || planType === 'mobile';
                  if (isPerGb) {
                    return !selectedTier && !(parseInt(customGb, 10) >= 5);
                  }
                  return false;
                })()}
                className="w-full px-5 py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {processing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    Renew Now <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              {/* Renewal history */}
              {renewalHistory.length > 0 && (
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
                  <h3 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Renewal History</h3>
                  <div className="space-y-2">
                    {renewalHistory.map((r) => (
                      <div key={r.id} className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0">
                        <div>
                          <p className="text-sm font-medium">
                            {r.quantity_gb ? `${r.quantity_gb} GB` : '30 days extension'}
                          </p>
                          <p className="text-xs text-[var(--muted)]">{formatDate(r.created_at)}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-[var(--primary)]">₦{r.amount_paid_ngn.toLocaleString('en-NG')}</p>
                          <p className={`text-xs ${
                            r.status === 'completed' ? 'text-[var(--success)]' :
                            r.status === 'pending' ? 'text-[var(--warning)]' :
                            'text-[var(--error)]'
                          }`}>
                            {r.status}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Help footer */}
          <div className="text-center pt-8 mt-8 border-t border-[var(--border)]">
            <p className="text-sm text-[var(--muted)]">
              Need help?{' '}
              <button
                onClick={() => window.dispatchEvent(new CustomEvent('open-chat-widget', { detail: { context: 'support' } }))}
                className="text-[var(--primary)] hover:underline font-medium"
              >
                Chat with Charon →
              </button>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
