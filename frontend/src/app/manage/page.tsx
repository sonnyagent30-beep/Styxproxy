'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Header from '@/components/Header';

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

function ManageContent() {
  const searchParams = useSearchParams();
  const initialRef = searchParams.get('ref') || '';

  const [searchInput, setSearchInput] = useState(initialRef);
  const [order, setOrder] = useState<OrderData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (initialRef) handleSearch(initialRef);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialRef]);

  const handleSearch = async (ref: string) => {
    if (!ref.trim()) { setError('Please enter a transaction reference'); return; }
    setLoading(true); setError(''); setOrder(null);
    try {
      const res = await fetch(`/api/orders/${ref.trim()}`);
      const data = await res.json();
      if (res.ok && data.order_id) { setOrder(data); }
      else { setError(data.error || 'Order not found'); }
    } catch {
      setError('Failed to fetch order. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const isActive = order?.status === 'fulfilled' || order?.status === 'active';

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 px-4 py-24">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-3xl font-bold text-center mb-8">
            Manage <span className="gradient-text">Order</span>
          </h1>

          {/* Search Forms */}
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-8">
            <form onSubmit={(e) => { e.preventDefault(); handleSearch(searchInput); }}>
              <label className="block text-sm font-medium mb-2">Order ID or Transaction Reference</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="e.g., FLW-xxxxx"
                  className="flex-1 px-4 py-3 bg-[var(--background)] border border-[var(--border)] rounded-lg focus:outline-none focus:border-[var(--primary)] transition-colors"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  {loading ? '...' : 'Search'}
                </button>
              </div>
            </form>
          </div>

          {error && (
            <div className="bg-[var(--error)]/10 border border-[var(--error)]/30 rounded-xl p-4 mb-6">
              <p className="text-[var(--error)]">{error}</p>
            </div>
          )}

          {order && (
            <div className="animate-fade-in">
              {/* Status Card */}
              <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold">Order Details</h2>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    isActive ? 'bg-[var(--primary)]/20 text-[var(--primary)]' : 'bg-[var(--muted)]/20 text-[var(--muted)]'
                  }`}>
                    {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-[var(--muted)]">Order ID</span>
                    <p className="font-medium">{order.order_id}</p>
                  </div>
                  {order.tx_ref && (
                    <div>
                      <span className="text-sm text-[var(--muted)]">Transaction Ref</span>
                      <p className="font-medium font-mono text-sm">{order.tx_ref}</p>
                    </div>
                  )}
                  {order.plan_type && (
                    <div>
                      <span className="text-sm text-[var(--muted)]">Plan Type</span>
                      <p className="font-medium">{order.plan_type}</p>
                    </div>
                  )}
                  {order.country && (
                    <div>
                      <span className="text-sm text-[var(--muted)]">Country</span>
                      <p className="font-medium">{order.country}</p>
                    </div>
                  )}
                  {order.amount_paid_ngn && (
                    <div>
                      <span className="text-sm text-[var(--muted)]">Amount Paid</span>
                      <p className="font-medium">₦{order.amount_paid_ngn.toLocaleString('en-NG')}</p>
                    </div>
                  )}
                  {order.created_at && (
                    <div>
                      <span className="text-sm text-[var(--muted)]">Created</span>
                      <p className="font-medium">
                        {new Date(order.created_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })}
                      </p>
                    </div>
                  )}
                  {order.expires_at && (
                    <div>
                      <span className="text-sm text-[var(--muted)]">Expires</span>
                      <p className="font-medium">
                        {new Date(order.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Credentials Card */}
              {isActive && order.bunche_credential && (
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
                  <h2 className="text-xl font-semibold mb-4">Your Proxy</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm text-[var(--muted)]">Username</label>
                      <p className="font-mono text-lg">{order.bunche_credential.bun_username}</p>
                    </div>
                    <div>
                      <label className="text-sm text-[var(--muted)]">Proxy Address</label>
                      <p className="font-mono text-lg">
                        {order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm text-[var(--muted)]">Full Format</label>
                      <p className="font-mono text-sm text-[var(--muted)] break-all">
                        {order.bunche_credential.bun_username}:your_password@{order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                      </p>
                    </div>
                    {order.bunche_credential.expires_at && (
                      <div>
                        <label className="text-sm text-[var(--muted)]">Expires</label>
                        <p className="font-medium">
                          {new Date(order.bunche_credential.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Link
                  href="/order"
                  className="flex-1 px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg text-center transition-colors"
                >
                  Order Another
                </Link>
                <a
                  href="https://t.me/BuncheBot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
                >
                  Contact us to Renew
                </a>
              </div>
            </div>
          )}

          {!order && !error && !loading && (
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--card)] border border-[var(--border)] flex items-center justify-center">
                <svg className="w-8 h-8 text-[var(--muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold mb-2">Find Your Order</h2>
              <p className="text-[var(--muted)]">
                Enter your transaction reference or phone number to view your order details.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default function ManagePage() {
  return (
    <Suspense fallback={
      <main className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </main>
    }>
      <ManageContent />
    </Suspense>
  );
}
