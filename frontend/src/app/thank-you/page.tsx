'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import Header from '@/components/Header';
import Footer from '@/components/Footer';

interface OrderData {
  order_id?: string;
  status?: string;
  plan_type?: string;
  country?: string;
  amount_paid_ngn?: number;
  bunche_credential?: {
    bun_username?: string;
    upstream_proxy_ip?: string;
    upstream_proxy_port?: number;
    expires_at?: string;
  };
  created_at?: string;
  expires_at?: string;
}

function ThankYouContent() {
  const searchParams = useSearchParams();
  const txRef = searchParams.get('tx_ref');

  const [order, setOrder] = useState<OrderData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const maxAttempts = 60;

  useEffect(() => {
    if (!txRef) {
      setError(true);
      setLoading(false);
      return;
    }

    const fetchOrder = async () => {
      try {
        const res = await fetch(`/api/orders/${txRef}`);
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();

        if (data.order_id) setOrder(data);

        if (data.status === 'fulfilled' || data.status === 'active' ||
            data.status === 'expired' || data.status === 'cancelled') {
          setLoading(false);
          return;
        }
        setAttempts(prev => prev + 1);
      } catch {
        setAttempts(prev => prev + 1);
      }
    };

    fetchOrder();

    const interval = setInterval(() => {
      if (attempts >= maxAttempts) {
        setLoading(false);
        clearInterval(interval);
        return;
      }
      fetchOrder();
    }, 5000);

    return () => clearInterval(interval);
  }, [txRef, attempts]);

  if (!txRef || error) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 flex items-center justify-center px-4">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4">Order Not Found</h1>
            <p className="text-[var(--muted)] mb-6">
              We couldn't find an order with that reference.
            </p>
            <Link
              href="/order"
              className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
            >
              Place New Order
            </Link>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const isPending = order?.status === 'pending' || order?.status === 'paid';
  const isSuccess = order?.status === 'fulfilled' || order?.status === 'active';
  const isError = order?.status === 'expired' || order?.status === 'cancelled';

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 flex items-center justify-center px-4 py-24">
        <div className="max-w-lg w-full">
          {loading && isPending && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 mx-auto mb-6 rounded-full border-4 border-[var(--primary)] border-t-transparent animate-spin" />
              <h1 className="text-2xl font-bold mb-2">Payment Confirmed!</h1>
              <p className="text-[var(--muted)]">
                Preparing your proxy credentials...
              </p>
              <p className="text-sm text-[var(--muted)] mt-4">
                Reference: {txRef}
              </p>
            </div>
          )}

          {isSuccess && order?.bunche_credential && (
            <div className="animate-fade-in">
              <div className="text-center mb-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--primary)]/20 flex items-center justify-center">
                  <svg className="w-8 h-8 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h1 className="text-3xl font-bold text-[var(--primary)] mb-2">Order Complete!</h1>
                <p className="text-[var(--muted)]">
                  Your proxy is ready. Here are your credentials:
                </p>
              </div>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">Proxy Credentials</h2>
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
                    <label className="text-sm text-[var(--muted)]">Format</label>
                    <p className="font-mono text-sm text-[var(--muted)] break-all">
                      {order.bunche_credential.bun_username}:your_password@{order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm text-[var(--muted)]">Expires</label>
                    <p className="font-medium">
                      {order.bunche_credential.expires_at
                        ? new Date(order.bunche_credential.expires_at).toLocaleDateString('en-NG', {
                            year: 'numeric', month: 'long', day: 'numeric',
                          })
                        : 'N/A'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-[var(--muted)]">Order ID</span>
                    <p className="font-medium">{order.order_id}</p>
                  </div>
                  <div>
                    <span className="text-[var(--muted)]">Plan</span>
                    <p className="font-medium">{order.plan_type} - {order.country}</p>
                  </div>
                  <div>
                    <span className="text-[var(--muted)]">Amount Paid</span>
                    <p className="font-medium">₦{order.amount_paid_ngn?.toLocaleString('en-NG')}</p>
                  </div>
                  <div>
                    <span className="text-[var(--muted)]">Status</span>
                    <p className="font-medium text-[var(--primary)] capitalize">{order.status}</p>
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-4">
                <Link
                  href={`/manage?ref=${txRef}`}
                  className="flex-1 px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg text-center transition-colors"
                >
                  Manage Order
                </Link>
                <Link
                  href="/order"
                  className="flex-1 px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
                >
                  Order Another
                </Link>
              </div>
            </div>
          )}

          {!loading && isError && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--error)]/20 flex items-center justify-center">
                <svg className="w-8 h-8 text-[var(--error)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold mb-2">Order {order?.status === 'expired' ? 'Expired' : 'Cancelled'}</h1>
              <p className="text-[var(--muted)] mb-6">This order is no longer active.</p>
              <Link
                href="/order"
                className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
              >
                Place New Order
              </Link>
            </div>
          )}

          {!loading && !order && attempts >= maxAttempts && (
            <div className="text-center animate-fade-in">
              <h1 className="text-2xl font-bold mb-2">Still Processing</h1>
              <p className="text-[var(--muted)] mb-6">
                Your order is being processed. Please check back in a few minutes.
              </p>
              <Link
                href={`/manage?ref=${txRef}`}
                className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
              >
                Check Order Status
              </Link>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default function ThankYouPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 flex items-center justify-center">
          <div className="animate-pulse text-[var(--muted)]">Loading...</div>
        </main>
        <Footer />
      </div>
    }>
      <ThankYouContent />
    </Suspense>
  );
}
