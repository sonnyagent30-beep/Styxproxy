'use client';

import { useState } from 'react';
import Link from 'next/link';
import Header from '@/components/Header';
import Footer from '@/components/Footer';

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
}

export default function ManagePage() {
  const [searchInput, setSearchInput] = useState('');
  const [order, setOrder] = useState<OrderData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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

  const isActive = order?.status === 'fulfilled' || order?.status === 'active';

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
                  <h2 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Your Proxy Credentials</h2>
                  <div className="space-y-3">
                    <div className="bg-[var(--background)] rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-[var(--muted)]">Username</span>
                        <button
                          onClick={() => navigator.clipboard.writeText(order.bunche_credential!.bun_username!)}
                          className="text-xs text-[var(--primary)] hover:underline"
                        >
                          Copy
                        </button>
                      </div>
                      <p className="font-mono text-sm font-medium break-all">{order.bunche_credential.bun_username}</p>
                    </div>
                    <div className="bg-[var(--background)] rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-[var(--muted)]">Proxy Address</span>
                        <button
                          onClick={() => navigator.clipboard.writeText(`${order.bunche_credential!.upstream_proxy_ip}:${order.bunche_credential!.upstream_proxy_port}`)}
                          className="text-xs text-[var(--primary)] hover:underline"
                        >
                          Copy
                        </button>
                      </div>
                      <p className="font-mono text-sm font-medium">
                        {order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                      </p>
                    </div>
                    <div className="bg-[var(--background)] rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-[var(--muted)]">Full Proxy String</span>
                        <button
                          onClick={() => navigator.clipboard.writeText(`${order.bunche_credential!.bun_username}:your_password@${order.bunche_credential!.upstream_proxy_ip}:${order.bunche_credential!.upstream_proxy_port}`)}
                          className="text-xs text-[var(--primary)] hover:underline"
                        >
                          Copy
                        </button>
                      </div>
                      <p className="font-mono text-xs text-[var(--muted)] break-all">
                        {order.bunche_credential.bun_username}:your_password@{order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-[var(--muted)] mt-3">
                    Replace <code className="bg-[var(--background)] px-1 rounded">your_password</code> with the password sent to your email after payment.
                  </p>
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
                <a
                  href="https://t.me/StyxproxyBot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-5 py-3 bg-[#0088cc] hover:bg-[#006699] text-white font-semibold rounded-xl text-sm text-center transition-colors"
                >
                  Get Support
                </a>
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
