'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import { formatPrice } from '@/lib/products';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.styxproxy.com';

interface OrderData {
  order_id: string;
  status: string;
  plan_type: string;
  plan_code: string;
  country: string;
  amount_paid_ngn: number;
  expires_at?: string;
  styxproxy_credential?: {
    styxproxy_username: string;
    styxproxy_password: string;
    upstream_proxy_ip: string;
    upstream_proxy_port: number;
    expires_at: string;
  };
}

interface CatalogPlan {
  plan_code: string;
  plan_type: string;
  country: string;
  price_per_gb: number;
  min_gb: number;
  max_gb: number;
  gb_tiers: number[];
}

function RenewalContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const orderId = searchParams.get('renew');

  const [order, setOrder] = useState<OrderData | null>(null);
  const [plan, setPlan] = useState<CatalogPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedGb, setSelectedGb] = useState<number>(0);
  const [customGb, setCustomGb] = useState<string>('');
  const [email, setEmail] = useState('');
  const [paying, setPaying] = useState(false);

  useEffect(() => {
    if (!orderId) {
      setError('No order specified. Please use the Renew button from your order status page.');
      setLoading(false);
      return;
    }

    // Fetch order details
    fetch(`${API_BASE_URL}/api/orders/${orderId}`)
      .then(r => r.json())
      .then(data => {
        if (data.order_id) {
          setOrder(data);
          // Fetch catalog for plan pricing
          return fetch(`${API_BASE_URL}/api/catalog`)
            .then(r => r.json())
            .then(catalog => {
              const plans = catalog.plans || [];
              const matchingPlan = plans.find(
                (p: any) => p.plan_code === data.plan_code && p.country === data.country
              );
              if (matchingPlan) {
                setPlan({
                  plan_code: matchingPlan.plan_code,
                  plan_type: matchingPlan.plan_type,
                  country: matchingPlan.country,
                  price_per_gb: matchingPlan.price_per_gb || 0,
                  min_gb: matchingPlan.min_gb || 5,
                  max_gb: matchingPlan.max_gb || 50,
                  gb_tiers: matchingPlan.gb_tiers || [5, 10, 20, 50],
                });
                setSelectedGb(matchingPlan.gb_tiers?.[0] || matchingPlan.min_gb || 5);
              } else {
                setError('Could not load plan pricing. Please try again.');
              }
              setLoading(false);
            });
        } else {
          setError(data.error || data.detail || 'Order not found');
          setLoading(false);
        }
      })
      .catch(() => {
        setError('Network error. Please try again.');
        setLoading(false);
      });
  }, [orderId]);

  const effectiveGb = customGb ? parseInt(customGb, 10) : selectedGb;
  const totalPrice = plan ? plan.price_per_gb * effectiveGb : 0;

  const handlePay = async () => {
    if (!orderId || !effectiveGb || effectiveGb < 5) return;
    setPaying(true);
    setError('');

    try {
      const res = await fetch(`${API_BASE_URL}/api/renewals/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: orderId,
          quantity_gb: effectiveGb,
          customer_email: email || undefined,
        }),
      });

      const data = await res.json();

      if (res.ok && data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        setError(data.error || data.detail || 'Failed to start renewal payment');
        setPaying(false);
      }
    } catch {
      setError('Network error. Please try again.');
      setPaying(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-[var(--muted)]">Loading renewal details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen pt-24 flex items-center justify-center">
        <div className="text-center max-w-md">
          <p className="text-[var(--error)] mb-4">{error}</p>
          <Link
            href="/order/status"
            className="px-6 py-3 bg-[var(--primary)] text-black font-semibold rounded-xl"
          >
            Go to Order Status
          </Link>
        </div>
      </div>
    );
  }

  if (!order || !plan) {
    return (
      <div className="min-h-screen pt-24 flex items-center justify-center">
        <div className="text-[var(--muted)]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 px-4 pt-32 pb-16">
        <div className="max-w-2xl mx-auto">
          {/* Back link */}
          <Link
            href={`/order/status?order_id=${orderId}`}
            className="inline-flex items-center text-[var(--muted)] hover:text-[var(--foreground)] mb-6 transition-colors"
          >
            <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Order Status
          </Link>

          <h1 className="text-3xl font-bold mb-2">Renew Your Proxy</h1>
          <p className="text-[var(--muted)] mb-8">
            Extend your existing proxy with additional data. Your current proxy stays active.
          </p>

          {/* Current Proxy Info */}
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 mb-6">
            <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wide mb-4">Current Proxy</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-[var(--border)]">
                <span className="text-sm text-[var(--muted)]">Plan</span>
                <span className="text-sm font-medium">{order.plan_code}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-[var(--border)]">
                <span className="text-sm text-[var(--muted)]">Country</span>
                <span className="text-sm font-medium">{order.country}</span>
              </div>
              {order.expires_at && (
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-[var(--muted)]">Expires</span>
                  <span className="text-sm">
                    {new Date(order.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'short', day: 'numeric' })}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* GB Selector */}
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 mb-6">
            <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wide mb-4">Select Data</h2>
            
            {/* Preset tiers */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              {plan.gb_tiers.map(tier => (
                <button
                  key={tier}
                  onClick={() => { setSelectedGb(tier); setCustomGb(''); }}
                  className={`p-4 rounded-xl border text-center transition-colors ${
                    selectedGb === tier && !customGb
                      ? 'border-[var(--primary)] bg-[var(--primary)]/10'
                      : 'border-[var(--border)] hover:border-[var(--primary)]/40'
                  }`}
                >
                  <span className="block text-lg font-bold">{tier} GB</span>
                  <span className="block text-xs text-[var(--muted)] mt-1">
                    {formatPrice(plan.price_per_gb * tier)}
                  </span>
                </button>
              ))}
            </div>

            {/* Custom GB input */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Custom amount (min {plan.min_gb} GB)
              </label>
              <input
                type="number"
                min={plan.min_gb}
                max={plan.max_gb}
                value={customGb}
                onChange={e => setCustomGb(e.target.value)}
                placeholder={`Enter GB (${plan.min_gb}-${plan.max_gb})`}
                className="w-full px-4 py-3 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
              />
            </div>
          </div>

          {/* Email */}
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2">
              Email <span className="text-[var(--muted)] font-normal">(optional — for receipt)</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-[var(--error)]/10 border border-[var(--error)]/20 text-[var(--error)] text-sm">
              {error}
            </div>
          )}

          {/* Summary + Pay */}
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 mb-6">
            <div className="flex justify-between items-center mb-4">
              <span className="text-[var(--muted)]">Total</span>
              <span className="text-2xl font-bold text-[var(--primary)]">{formatPrice(totalPrice)}</span>
            </div>
            <p className="text-xs text-[var(--muted)]">
              {effectiveGb} GB × {formatPrice(plan.price_per_gb)}/GB
            </p>
          </div>

          <button
            onClick={handlePay}
            disabled={paying || !effectiveGb || effectiveGb < plan.min_gb}
            className="w-full py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:opacity-50 disabled:cursor-not-allowed text-black font-semibold rounded-xl transition-colors text-lg"
          >
            {paying ? 'Redirecting to payment...' : `Pay ${formatPrice(totalPrice)}`}
          </button>

          <p className="text-xs text-center text-[var(--muted)] mt-3">
            Your proxy will be extended immediately after payment confirmation.
          </p>
        </div>
      </main>
      <Footer />
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

export default function RenewalPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <RenewalContent />
    </Suspense>
  );
}
