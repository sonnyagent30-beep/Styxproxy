'use client';

import { useState } from 'react';
import Link from 'next/link';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import { useToast } from '@/components/Toast';

interface OrderData {
  order_id: string;
  status: string;
  plan_type?: string;
  country?: string;
  amount_paid_ngn?: number;
  tx_ref?: string;
  bunche_credential?: {
    bun_username?: string;
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
  const [renewing, setRenewing] = useState(false);
  const [error, setError] = useState('');
  const { toast } = useToast();

  const handleSearch = async (ref: string) => {
    if (!ref.trim()) { setError('Please enter an order ID or transaction reference'); return; }
    setLoading(true); setError(''); setOrder(null);
    try {
      const res = await fetch(`/api/orders/${ref.trim()}`);
      const data = await res.json();
      if (res.ok && data.order_id) { setOrder(data); }
      else { setError(data.error || 'Order not found. Double-check your order ID and try again.'); }
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
      if (res.ok && data.bunche_credential) {
        setOrder(prev => prev ? { ...prev, bunche_credential: data.bunche_credential, rotation_count: (prev.rotation_count ?? 0) + 1 } : null);
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

  const handleRenew = async () => {
    if (!order?.order_id) return;
    setRenewing(true);
    try {
      const res = await fetch(`/api/orders/${order.order_id}/renew`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setOrder(prev => prev ? { ...prev, expires_at: data.expires_at, is_renewable: false } : null);
        toast({ type: 'success', title: 'Proxy renewed!', message: 'Your expiry date has been updated.' });
      } else {
        toast({ type: 'error', title: 'Renewal failed', message: data.error || 'Please try again.' });
      }
    } catch {
      toast({ type: 'error', title: 'Network error', message: 'Could not renew. Try again.' });
    } finally {
      setRenewing(false);
    }
  };

  const isActive = order?.status === 'fulfilled' || order?.status === 'active';
  const rotationsLeft = (order?.max_rotations ?? 3) - (order?.rotation_count ?? 0);
  const isNearExpiry = order?.expires_at && new Date(order.expires_at).getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000;

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 px-4 py-24">
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
              <svg className="w-5 h-5 text-red-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
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
                        <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                        <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
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
              {isActive && order.bunche_credential && (
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wide">Your Proxy Credentials</h2>
                    <span className="text-xs text-[var(--muted)]">
                      {rotationsLeft} rotation{rotationsLeft !== 1 ? 's' : ''} left
                    </span>
                  </div>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-[var(--background)] rounded-xl p-4">
                        <span className="text-xs text-[var(--muted)]">Username</span>
                        <p className="font-mono text-sm font-medium break-all">{order.bunche_credential.bun_username}</p>
                      </div>
                      <div className="bg-[var(--background)] rounded-xl p-4">
                        <span className="text-xs text-[var(--muted)]">Password</span>
                        <p className="font-mono text-sm text-[var(--muted)]">Sent to email</p>
                      </div>
                      <div className="bg-[var(--background)] rounded-xl p-4">
                        <span className="text-xs text-[var(--muted)]">Proxy Address</span>
                        <p className="font-mono text-sm font-medium">
                          {order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                        </p>
                      </div>
                      <div className="bg-[var(--background)] rounded-xl p-4">
                        <span className="text-xs text-[var(--muted)]">Protocol</span>
                        <p className="font-mono text-sm font-medium">HTTP / SOCKS5</p>
                      </div>
                    </div>
                    <div className="bg-[var(--background)] rounded-xl p-4">
                      <span className="text-xs text-[var(--muted)]">Full Format</span>
                      <p className="font-mono text-xs text-[var(--muted)] break-all leading-relaxed">
                        http://{order.bunche_credential.bun_username}:YOUR_PASSWORD@{order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                      </p>
                    </div>

                    {/* Rotate Proxy Key */}
                    {rotationsLeft > 0 && (
                      <button
                        onClick={handleRotateKey}
                        disabled={rotating}
                        className="w-full px-4 py-2.5 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-xl transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        {rotating ? 'Rotating…' : `Rotate Proxy Key (${rotationsLeft} left)`}
                      </button>
                    )}
                    {rotationsLeft === 0 && (
                      <p className="text-xs text-[var(--muted)] text-center">Rotation limit reached for this proxy.</p>
                    )}

                    {/* Renewal */}
                    {(isNearExpiry || order.is_renewable) && (
                      <button
                        onClick={handleRenew}
                        disabled={renewing}
                        className="w-full px-4 py-2.5 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-xl transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {renewing ? 'Renewing…' : 'Renew This Proxy'}
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
                  onClick={() => window.dispatchEvent(new CustomEvent('open-chat-widget'))}
                  className="px-5 py-3 bg-[#0088cc] hover:bg-[#006699] text-white font-semibold rounded-xl text-sm text-center transition-colors"
                >
                  Get Support
                </button>
              </div>
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
