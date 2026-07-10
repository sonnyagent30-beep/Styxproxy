'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { formatPrice, COUNTRIES } from '@/lib/products';
import type { CartItem } from '@/types';
import api from '@/lib/api';

export default function CheckoutPage() {
  const router = useRouter();
  const [cart, setCart] = useState<CartItem[]>([]);
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const stored = sessionStorage.getItem('bunche_cart');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setCart(parsed);
        } else {
          router.replace('/order');
        }
      } catch {
        router.replace('/order');
      }
    } else {
      router.replace('/order');
    }
  }, [router]);

  const updateQuantity = (plan_code: string, delta: number) => {
    setCart(prev => {
      const updated = prev.map(item => {
        if (item.plan_code === plan_code) {
          const newQty = Math.max(1, item.quantity + delta);
          return { ...item, quantity: newQty };
        }
        return item;
      }).filter(item => item.quantity > 0);
      sessionStorage.setItem('bunche_cart', JSON.stringify(updated));
      return updated;
    });
  };

  const removeItem = (plan_code: string) => {
    const updated = cart.filter(i => i.plan_code !== plan_code);
    setCart(updated);
    sessionStorage.setItem('bunche_cart', JSON.stringify(updated));
    if (updated.length === 0) router.replace('/order');
  };

  const subtotal = cart.reduce((sum, i) => sum + i.price_ngn * i.quantity, 0);

  const handlePay = async () => {
    if (cart.length === 0) return;
    setError('');
    setLoading(true);

    try {
      // Store email in sessionStorage for thank-you page
      if (email.trim()) {
        sessionStorage.setItem('bunche_email', email.trim());
      }

      // Initiate payment with first cart item
      const firstItem = cart[0];
      const result = await api.initiatePayment(firstItem.plan_code, firstItem.quantity, '');

      if (result.error) {
        setError(result.error);
        setLoading(false);
        return;
      }

      if (result.data?.checkout_url) {
        window.location.href = result.data.checkout_url;
      } else {
        setError('Payment link not received. Please try again.');
        setLoading(false);
      }
    } catch {
      setError('Failed to initiate payment. Please try again.');
      setLoading(false);
    }
  };

  if (cart.length === 0) {
    return (
      <div className="min-h-screen pt-24 flex items-center justify-center">
        <div className="text-center">
          <p className="text-[var(--muted)] mb-4">Your cart is empty</p>
          <Link href="/order" className="px-6 py-3 bg-[var(--primary)] text-black font-semibold rounded-xl">
            Browse Proxies
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-24 pb-16">
      <div className="max-w-2xl mx-auto px-4">
        {/* Back link */}
        <Link
          href="/order"
          className="inline-flex items-center text-[var(--muted)] hover:text-[var(--foreground)] mb-6 transition-colors"
        >
          <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to browse
        </Link>

        <h1 className="text-3xl font-bold mb-8">
          Checkout
        </h1>

        {/* Cart Items */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Your Order</h2>
          <div className="space-y-3">
            {cart.map(item => {
              const country = item.country_code ? COUNTRIES[item.country_code] : null;
              return (
                <div key={item.plan_code} className="flex items-center justify-between p-4 rounded-xl bg-[var(--card)] border border-[var(--border)]">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{item.flag}</span>
                    <div>
                      <p className="font-semibold">{item.name}</p>
                      {country && (
                        <p className="text-xs text-[var(--muted)]">
                          {country.flag} {country.name} · {country.region}
                        </p>
                      )}
                      <p className="text-sm text-[var(--muted)]">{formatPrice(item.price_ngn)} each</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {/* Quantity controls */}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateQuantity(item.plan_code, -1)}
                        className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] hover:border-[var(--primary)] flex items-center justify-center transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                        </svg>
                      </button>
                      <span className="w-6 text-center font-medium">{item.quantity}</span>
                      <button
                        onClick={() => updateQuantity(item.plan_code, 1)}
                        className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] hover:border-[var(--primary)] flex items-center justify-center transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                      </button>
                    </div>
                    {/* Line total */}
                    <span className="font-semibold text-[var(--primary)] w-28 text-right">
                      {formatPrice(item.price_ngn * item.quantity)}
                    </span>
                    {/* Remove */}
                    <button
                      onClick={() => removeItem(item.plan_code)}
                      className="w-8 h-8 rounded-lg hover:bg-red-500/10 flex items-center justify-center text-[var(--muted)] hover:text-red-400 transition-colors"
                      title="Remove"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Subtotal */}
          <div className="mt-4 p-4 rounded-xl bg-[var(--card)] border border-[var(--border)]">
            <div className="flex justify-between items-center">
              <span className="text-[var(--muted)]">Subtotal</span>
              <span className="text-xl font-bold">{formatPrice(subtotal)}</span>
            </div>
          </div>
        </div>

        {/* Email */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-4">Your Receipt</h2>
          <div>
            <label className="block text-sm font-medium mb-2">
              Email address <span className="text-[var(--muted)] font-normal">(optional)</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
            />
            <p className="text-xs text-[var(--muted)] mt-2">
              We'll email your receipt after payment. No spam — ever.
            </p>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Pay Button */}
        <button
          onClick={handlePay}
          disabled={loading || cart.length === 0}
          className="w-full py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:opacity-50 disabled:cursor-not-allowed text-black font-semibold rounded-xl transition-colors text-lg"
        >
          {loading ? 'Redirecting to payment...' : `Pay ${formatPrice(subtotal)} via Flutterwave`}
        </button>

        <p className="text-xs text-center text-[var(--muted)] mt-3">
          Secured by Flutterwave. Your proxy credentials will be shown on the next page.
        </p>
      </div>
    </div>
  );
}
