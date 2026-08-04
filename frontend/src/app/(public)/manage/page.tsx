'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import { useToast } from '@/components/Toast';
import { getOrderHistory, type OrderHistoryEntry, getInflightOrder, clearInflightOrder } from '@/lib/device-id';
import { Eye, EyeSlash, Copy, Clock, Check, ArrowRight, ArrowClockwise, X, WarningCircle } from '@phosphor-icons/react';

// Helper: Copy to clipboard with toast feedback
function copyToClipboard(text: string, label: string) {
  navigator.clipboard.writeText(text).then(() => {
    // Trigger toast via custom event (Toast component listens)
    window.dispatchEvent(new CustomEvent('show-toast', { 
      detail: { type: 'success', title: 'Copied!', message: `${label} copied to clipboard` } 
    }));
  }).catch(() => {
    window.dispatchEvent(new CustomEvent('show-toast', { 
      detail: { type: 'error', title: 'Copy failed', message: 'Could not copy to clipboard' } 
    }));
  });
}

// Helper: Format time remaining until expiry
function formatTimeRemaining(expiresAt: string): string {
  const now = Date.now();
  const expiry = new Date(expiresAt).getTime();
  const diff = expiry - now;
  
  if (diff <= 0) return 'Expired';
  
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  
  if (days > 0) return `${days}d ${hours}h remaining`;
  if (hours > 0) return `${hours}h ${minutes}m remaining`;
  return `${minutes}m remaining`;
}

// Reusable credential field with copy button
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
            onClick={() => copyToClipboard(value, label)}
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

interface OrderData {
  order_id: string;
  status: string;
  plan_type?: string;
  country?: string;
  amount_paid_ngn?: number;
  tx_ref?: string;
  styxproxy_credential?: {
    bun_username?: string;
    styxproxy_username?: string;
    styxproxy_password?: string;
    upstream_proxy_ip?: string;
    upstream_proxy_port?: number;
    expires_at?: string;
  };
  created_at?: string;
  expires_at?: string;
  is_renewable?: boolean;
  rotation_count?: number;
  max_rotations?: number;
}

export default function ManagePage() {
  const [searchInput, setSearchInput] = useState('');
  const [order, setOrder] = useState<OrderData | null>(null);
  const [loading, setLoading] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<OrderHistoryEntry[]>([]);
  const [inflight, setInflight] = useState(getInflightOrder());
  const { toast } = useToast();

  // Load local order history on mount
  useEffect(() => {
    setHistory(getOrderHistory());
    setInflight(getInflightOrder());
  }, []);

  const handleSearch = async (ref: string) => {
    if (!ref.trim()) { setError('Please enter an order ID or transaction reference'); return; }
    setLoading(true); setError(''); setOrder(null);
    const trimmedRef = ref.trim();
    // Bug walk theme-B fix: route by reference format.
    // - STX-XXXXXX (FE payment_reference) → use auth-less /by-payment-reference/{ref}
    // - ORD-XXXXXX (BE order_id) → use auth-required /{order_id}
    // Previously the manage page always called /{order_id} which 404'd for
    // STX- references (most common case after /thank-you flow) and 400'd
    // for anonymous customers (no JWT = no customer).
    const endpoint = trimmedRef.startsWith('STX-') || trimmedRef.startsWith('stx-')
      ? `/api/orders/by-payment-reference/${trimmedRef}`
      : `/api/orders/${trimmedRef}`;
    try {
      const res = await fetch(endpoint);
      const data = await res.json();
      if (res.ok && data.order_id) { setOrder(data); }
      else { setError(data.detail || data.error || 'Order not found. Double-check your order ID and try again.'); }
    } catch {
      setError('Network error. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRotateKey = async () => {
    if (!order?.order_id) return;
    const maxRot = order.max_rotations ?? 3;
    const current = order.rotation_count ?? 0;
    if (current >= maxRot) {
      toast({ type: 'warning', title: 'Rotation limit reached', message: `You can only rotate ${maxRot} times per proxy.` });
      return;
    }
    setRotating(true);
    try {
      const res = await fetch(`/api/orders/${order.order_id}/rotate`, { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.styxproxy_credential) {
        setOrder(prev => prev ? { ...prev, styxproxy_credential: data.styxproxy_credential, rotation_count: (prev.rotation_count ?? 0) + 1 } : null);
        toast({ type: 'success', title: 'Proxy rotated!', message: 'Your new credentials are ready.' });
      } else {
        toast({ type: 'error', title: 'Rotation failed', message: data.error || 'Please try again.' });
      }
    } catch {
      toast({ type: 'error', title: 'Network error', message: 'Could not rotate proxy. Try again.' });
    } finally {
      setRotating(false);
    }
  };

  // Renew → redirects to checkout
  const handleRenew = () => {
    if (!order?.order_id) return;
    window.location.href = `/order/checkout?renew=${order.order_id}`;
  };

  const isActive = order?.status === 'fulfilled' || order?.status === 'active';
  const rotationsLeft = (order?.max_rotations ?? 3) - (order?.rotation_count ?? 0);
  const isNearExpiry = order?.expires_at && new Date(order.expires_at).getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000;

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 px-4 pt-32 pb-16">
        <div className="max-w-xl mx-auto">

          {/* Page Header */}
          <div className="text-center mb-10">
            <h1 className="text-3xl sm:text-4xl font-bold mb-3">
              Manage <span className="gradient-text">Order</span>
            </h1>
            <p className="text-[var(--muted)] text-sm">
              Enter your order ID or transaction reference to view your proxy details.
            </p>
          </div>

          {/* In-flight order banner */}
          {inflight && !order && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 mb-6">
              <div className="flex items-start gap-3">
                <Clock className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-amber-400 text-sm font-medium">Order In Progress</p>
                  <p className="text-xs text-[var(--muted)] mt-1">
                    You have an unpaid order <span className="font-mono text-foreground">{inflight.tx_ref}</span>{' '}
                    for {inflight.plan_code}.{' '}
                    <button
                      onClick={() => handleSearch(inflight.tx_ref)}
                      className="text-[var(--primary)] hover:underline font-medium"
                    >
                      Check status →
                    </button>
                  </p>
                </div>
                <button
                  onClick={() => {
                    clearInflightOrder();
                    setInflight(null);
                    toast({ type: 'info', title: 'In-flight order cleared', message: 'You can place a new order now.' });
                  }}
                  className="text-[var(--muted)] hover:text-foreground text-xs"
                  aria-label="Dismiss"
                >
                  ✕
                </button>
              </div>
            </div>
          )}

          {/* Local order history */}
          {history.length > 0 && !order && (
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wide mb-3">
                Recent Orders (this device)
              </h2>
              <div className="space-y-2">
                {history.slice(0, 5).map((h) => (
                  <button
                    key={h.tx_ref}
                    onClick={() => handleSearch(h.tx_ref)}
                    className="w-full text-left bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] rounded-xl p-3 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-mono text-sm font-medium">{h.tx_ref}</span>
                        <p className="text-xs text-[var(--muted)] mt-0.5">
                          {h.plan_code} · {h.country} · ₦{h.amount.toLocaleString('en-NG')}
                        </p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-md ${
                        h.status === 'active' || h.status === 'fulfilled'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-amber-500/20 text-amber-400'
                      }`}>
                        {h.status}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Search Card */}
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
            <label className="block text-sm font-medium mb-3">Order ID or Transaction Reference</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch(searchInput)}
                placeholder="e.g. TXF-XXXXX"
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
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6 flex items-start gap-3">
              <WarningCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              <p className="text-red-500 text-sm">{error}</p>
            </div>
          )}

          {/* Order Found */}
          {order && (
            <div className="space-y-4 animate-fade-in">

              {/* Status Banner */}
              <div className={`rounded-2xl p-5 border ${
                isActive
                  ? 'bg-emerald-500/10 border-emerald-500/30'
                  : 'bg-amber-500/10 border-amber-500/30'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {isActive ? (
                      <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                        <Check className="w-5 h-5 text-emerald-400" weight="bold" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                        <Clock className="w-5 h-5 text-amber-400" />
                      </div>
                    )}
                    <div>
                      <p className={`font-semibold text-sm ${isActive ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {isActive ? 'Proxy Active' : 'Order Processing'}
                      </p>
                      <p className="text-xs text-[var(--muted)] mt-0.5">
                        {isActive
                          ? 'Your proxy credentials are ready'
                          : 'Your order is being processed — check back shortly'}
                      </p>
                    </div>
                  </div>
                  <span className={`text-xs font-mono px-2 py-1 rounded-md ${
                    isActive
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-amber-500/20 text-amber-400'
                  }`}>
                    {order.status}
                  </span>
                </div>
              </div>

              {/* Order Details Card */}
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
                  {order.amount_paid_ngn && (
                    <div className="flex items-center justify-between py-2 border-b border-[var(--border)]">
                      <span className="text-sm text-[var(--muted)]">Amount Paid</span>
                      <span className="text-sm font-semibold" style={{ color: 'var(--primary)' }}>
                        ₦{order.amount_paid_ngn.toLocaleString('en-NG')}
                      </span>
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

              {/* Credentials Card */}
              {isActive && order.styxproxy_credential && (
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wide">Your Proxy Credentials</h2>
                    <span className="text-xs text-[var(--muted)]">
                      {rotationsLeft} rotation{rotationsLeft !== 1 ? 's' : ''} left
                    </span>
                  </div>
                  <div className="space-y-3">
                    {/* Expiry Countdown */}
                    {order.expires_at && (
                      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4 text-amber-400" />
                          <span className="text-sm text-amber-400">
                            {formatTimeRemaining(order.expires_at)}
                          </span>
                        </div>
                        <span className="text-xs text-[var(--muted)]">
                          Expires {new Date(order.expires_at).toLocaleDateString('en-NG', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </span>
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-3">
                      <CredentialField label="Username" value={order.styxproxy_credential.styxproxy_username || ''} />
                      <CredentialField label="Password" value={order.styxproxy_credential.styxproxy_password || 'N/A'} sensitive />
                      <CredentialField 
                        label="Proxy Address" 
                        value={`${order.styxproxy_credential.upstream_proxy_ip}:${order.styxproxy_credential.upstream_proxy_port}`} 
                      />
                      <div className="bg-[var(--background)] rounded-xl p-4">
                        <span className="text-xs text-[var(--muted)]">Protocol</span>
                        <p className="font-mono text-sm font-medium">HTTP / SOCKS5</p>
                      </div>
                    </div>
                    <div className="bg-[var(--background)] rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-[var(--muted)]">Full Format</span>
                        <button
                          onClick={() => copyToClipboard(`http://${order.styxproxy_credential?.styxproxy_username}:${order.styxproxy_credential?.styxproxy_password || 'N/A'}@${order.styxproxy_credential?.upstream_proxy_ip}:${order.styxproxy_credential?.upstream_proxy_port}`, 'Proxy URL')}
                          className="text-xs text-[var(--primary)] hover:underline flex items-center gap-1"
                        >
                          <Copy className="w-3 h-3" />
                          Copy
                        </button>
                      </div>
                      <p className="font-mono text-xs text-[var(--muted)] break-all leading-relaxed">
                        http://{order.styxproxy_credential.styxproxy_username}:{order.styxproxy_credential.styxproxy_password || 'N/A'}@{order.styxproxy_credential.upstream_proxy_ip}:{order.styxproxy_credential.upstream_proxy_port}
                      </p>
                    </div>

                    {/* Rotate Proxy Key */}
                    {rotationsLeft > 0 && (
                      <button
                        onClick={handleRotateKey}
                        disabled={rotating}
                        className="w-full px-4 py-2.5 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-xl transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        <ArrowClockwise className="w-4 h-4" />
                        {rotating ? 'Rotating…' : `Rotate Proxy Key (${rotationsLeft} left)`}
                      </button>
                    )}
                    {rotationsLeft === 0 && (
                      <p className="text-xs text-[var(--muted)] text-center">Rotation limit reached for this proxy.</p>
                    )}

                    {/* Renewal — takes user to checkout */}
                    {(isNearExpiry || order.is_renewable) && (
                      <button
                        onClick={handleRenew}
                        className="w-full px-4 py-2.5 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-xl transition-colors text-sm flex items-center justify-center gap-2"
                      >
                        <ArrowClockwise className="w-4 h-4" />
                        Renew This Proxy
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-3 pt-2">
                <Link
                  href="/order"
                  className="px-5 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl text-sm text-center transition-colors"
                >
                  Order Another
                </Link>
                <button
                  onClick={() => {
                    // Open ChatWidget — Charon handles it, escalates to human if needed
                    window.dispatchEvent(new CustomEvent('open-chat-widget', { detail: { context: 'support', orderId: order?.order_id } }));
                  }}
                  className="px-5 py-3 bg-[#0088cc] hover:bg-[#006699] text-white font-semibold rounded-xl text-sm text-center transition-colors"
                >
                  Get Support
                </button>
              </div>

              {/* Chatbot can't help? Direct to human */}
              <p className="text-xs text-center text-[var(--muted)] pt-2">
                Charon can&apos;t solve it?{' '}
                <Link href="/contact" className="text-[var(--primary)] hover:underline font-medium">
                  Get in touch with a human →
                </Link>
              </p>
            </div>
          )}

          {/* Empty State */}
          {!order && !error && !loading && (
            <div className="text-center py-10 animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-[var(--card)] border border-[var(--border)] flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-[var(--muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803a7.5 7.5 0 0010.607 10.607z" />
                </svg>
              </div>
              <p className="text-sm text-[var(--muted)]">
                Enter your order ID or tx_ref above to look up your proxy details.
              </p>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
