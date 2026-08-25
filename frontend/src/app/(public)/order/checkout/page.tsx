
/* eslint-disable react-hooks/set-state-in-effect */
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { formatPrice, COUNTRIES } from '@/lib/products';
import { Flag } from '@/components/ui/Flag';
import type { CartItem } from '@/types';
import api from '@/lib/api';
import { tryStartOrder, setInflightOrder, getDeviceId, addToOrderHistory } from '@/lib/device-id';

// Sprint 13: per-GB vs per-IP pricing
function itemPrice(item: import('@/types').CartItem): number {
  const isPerGb = (item.plan_type === 'RESIDENTIAL' || item.plan_type === 'MOBILE')
    && typeof item.price_per_gb === 'number'
    && typeof item.quantity_gb === 'number';
  if (isPerGb) {
    const perGb = item.price_per_gb as number;
    const qtyGb = item.quantity_gb as number;
    return perGb * qtyGb;
  }
  return item.price_ngn * item.quantity;
}

function generateTxRef(): string {
  // Format: STX-XXXXXX (e.g. STYX-A3K9L2)
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // no 0/1/I/O confusion
  let suffix = '';
  for (let i = 0; i < 6; i++) suffix += chars.charAt(Math.floor(Math.random() * chars.length));
  return `STX-${suffix}`;
}

export default function CheckoutPage() {
  const router = useRouter();
  const [cart, setCart] = useState<CartItem[]>([]);
  const [email, setEmail] = useState('');
  const [gateway, setGateway] = useState<'flutterwave' | 'paystack' | 'crypto'>('flutterwave');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  // Bug walk theme-B fix: precheck state. Map of plan_code → precheck result.
  // Default {checking: true} until precheck returns. Pay button disabled
  // until every cart item has available=true.
  const [precheck, setPrecheck] = useState<Record<string, {
    checking: boolean;
    available?: boolean;
    reason?: string;
    etaSeconds?: number;
  }>>({});

  useEffect(() => {
    // Read cart from sessionStorage (set by order page navigation) or
    // localStorage (Zustand persist) — cart must survive page navigation.
    const stored =
      sessionStorage.getItem('styxproxy_cart') ||
      localStorage.getItem('styxproxy_cart');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setCart(parsed);
          // Keep sessionStorage in sync so back-navigation also works
          sessionStorage.setItem('styxproxy_cart', stored);
          return;
        }
      } catch {
        // malformed — fall through to redirect
      }
    }
    router.replace('/order');
  }, [router]);

  // Sync cart changes back to sessionStorage so order page sees them too
  useEffect(() => {
    sessionStorage.setItem('styxproxy_cart', JSON.stringify(cart));
  }, [cart]);

  // Bug walk theme-B fix: when cart loads or changes, fire a precheck per item.
  // Precheck tells us if the provider has inventory for that plan+country+qty.
  // Display "Usually delivered in ~Xs" + warn if any item unavailable.
  useEffect(() => {
    if (cart.length === 0) return;

    let cancelled = false;
    const runPrecheck = async () => {
      // Initialize all to checking state
      const initial: typeof precheck = {};
      cart.forEach(item => { initial[item.plan_code] = { checking: true }; });
      setPrecheck(initial);

      for (const item of cart) {
        try {
          const isPerGb = (item.plan_type === 'RESIDENTIAL' || item.plan_type === 'MOBILE')
            && typeof item.price_per_gb === 'number';
          const r = await api.precheckOrder(
            item.plan_code,
            item.country_code || 'NG',
            isPerGb ? 1 : item.quantity,
            {
              quantity_gb: isPerGb ? item.quantity_gb : undefined,
              city_id: item.city_id ?? null,
              city_name: item.city_name ?? null,
            },
          );
          if (cancelled) return;
          if (r.data) {
            setPrecheck(prev => ({
              ...prev,
              [item.plan_code]: {
                checking: false,
                available: r.data!.available,
                reason: r.data!.reason,
                etaSeconds: r.data!.estimated_delivery_seconds,
              },
            }));
          } else {
            // Network error or 5xx — treat as available=true so we don't block
            // the customer from buying. Worst case: backend will fail at
            // /api/payments/initiate anyway.
            setPrecheck(prev => ({
              ...prev,
              [item.plan_code]: { checking: false, available: true, etaSeconds: 60 },
            }));
          }
        } catch {
          if (cancelled) return;
          setPrecheck(prev => ({
            ...prev,
            [item.plan_code]: { checking: false, available: true, etaSeconds: 60 },
          }));
        }
      }
    };
    runPrecheck();
    return () => { cancelled = true; };
  }, [cart]);

  const updateQuantity = (plan_code: string, delta: number) => {
    setCart(prev => {
      const updated = prev.map(item => {
        if (item.plan_code === plan_code) {
          const newQty = Math.max(1, item.quantity + delta);
          return { ...item, quantity: newQty };
        }
        return item;
      }).filter(item => item.quantity > 0);
      sessionStorage.setItem('styxproxy_cart', JSON.stringify(updated));
      return updated;
    });
  };

  const removeItem = (plan_code: string) => {
    const updated = cart.filter(i => i.plan_code !== plan_code);
    setCart(updated);
    sessionStorage.setItem('styxproxy_cart', JSON.stringify(updated));
    if (updated.length === 0) router.replace('/order');
  };

  const subtotal = cart.reduce((sum, i) => sum + itemPrice(i), 0);

  // Bug walk theme-B fix: aggregate precheck state for the Pay button.
  // Disabled while any item is still checking OR any item is unavailable.
  const allChecked = cart.length > 0 && cart.every(
    item => !precheck[item.plan_code]?.checking,
  );
  const anyUnavailable = cart.some(
    item => precheck[item.plan_code]?.available === false,
  );
  const payDisabled = loading || cart.length === 0 || !allChecked || anyUnavailable;

  const handlePay = async () => {
    if (cart.length === 0) return;
    setError('');
    setLoading(true);

    try {
      // Bug walk theme-B fix (#6): handle multi-item cart.
      // Previously the checkout took only cart[0] and silently dropped
      // cart[1..N]. Now we fire one /api/payments/initiate per cart item
      // in parallel and redirect to the FIRST successful checkout_url.
      //
      // The customer pays item #1 via Flutterwave → returns to /thank-you.
      // cart[1..N] remain in the cart. After payment #1 completes, we
      // show a "Pay remaining items" CTA on /thank-you that re-opens this
      // page with cart[1..N] in styxproxy_cart. One click = one payment.
      //
      // This is intentionally a per-payment redirect (not a single
      // aggregate Flutterwave transaction) because Flutterwave Standard
      // doesn't support multi-line invoices, and the multi-item Order
      // schema refactor needed for that would touch the entire order
      // model. Per-payment keeps Order.payment_reference consistent and
      // matches the existing webhook lookup logic.
      const trimmedEmail = email.trim();
      if (trimmedEmail) {
        sessionStorage.setItem('styxproxy_email', trimmedEmail);
      }

      // Generate one tx_ref per cart item so /thank-you /manage page can
      // reference each independently. Keep cart[0]'s tx_ref in
      // styxproxy_active_tx for backward-compat with the existing
      // polling flow (commit 4f9679b).
      const txRefs = cart.map(() => generateTxRef());
      sessionStorage.setItem('styxproxy_active_tx', txRefs[0]);

      // Track each pending order in local device history so /manage page
      // can recover them. addToOrderHistory dedupes by tx_ref.
      for (let i = 0; i < cart.length; i++) {
        addToOrderHistory({
          tx_ref: txRefs[i],
          order_id: txRefs[i],
          plan_code: cart[i].plan_code,
          country: cart[i].country_code || 'NG',
          amount: itemPrice(cart[i]),
          status: 'pending',
          created_at: new Date().toISOString(),
        });
      }

      // Double-payment prevention: if ANY of the cart items has an
      // in-flight tx_ref from the last 5 minutes, refuse and tell the
      // customer to complete or close the existing tab.
      const { tryStartOrder } = await import('@/lib/device-id');
      for (let i = 0; i < cart.length; i++) {
        const { is_resume } = tryStartOrder(cart[i].plan_code, () => txRefs[i]);
        if (is_resume) {
          setError(
            `Payment already in progress for ${cart[i].name}. Complete or close the existing tab.`,
          );
          setLoading(false);
          return;
        }
      }

      // Fire one initiate per cart item in parallel. allSettled means
      // one item's failure doesn't block the others.
      const results = await Promise.allSettled(
        cart.map((item) => {
          const isPerGb = (item.plan_type === 'RESIDENTIAL' || item.plan_type === 'MOBILE')
            && typeof item.price_per_gb === 'number';
          return api.initiatePayment(
            item.plan_code,
            isPerGb ? 1 : item.quantity,
            '',
            trimmedEmail || undefined,
            gateway,
          );
        }),
      );

      // Find first successful result with a checkout_url.
      let firstCheckoutUrl = '';
      let lastError = '';
      for (let i = 0; i < results.length; i++) {
        const r = results[i];
        if (r.status === 'fulfilled' && r.value.data?.checkout_url) {
          firstCheckoutUrl = r.value.data.checkout_url;
          break;
        }
        if (r.status === 'rejected') {
          lastError = r.reason?.message || 'payment initiation failed';
        } else if (r.status === 'fulfilled' && r.value.error) {
          lastError = r.value.error;
        }
      }

      if (firstCheckoutUrl) {
        // Don't clear in-flight — webhook will clear it on payment confirm
        // OR 5-min expiry will auto-clear.
        window.location.href = firstCheckoutUrl;
        return;
      }

      // All items failed.
      setError(
        `Could not start payment for any items. ${lastError ? `Last error: ${lastError}` : 'Please try again.'}`,
      );
      setLoading(false);
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
                    <Flag countryCode={item.country_code} size={28} />
                    <div>
                      <p className="font-semibold">{item.name}</p>
                      {country && (
                        <p className="text-xs text-[var(--muted)]">
                          <Flag countryCode={item.country_code} size={14} /> {country.name} · {country.region}
                          {item.city_name ? ` · ${item.city_name}` : ''}
                        </p>
                      )}
                      <p className="text-sm text-[var(--muted)]">
                        {(() => {
                          const isPerGb = (item.plan_type === 'RESIDENTIAL' || item.plan_type === 'MOBILE')
                            && typeof item.price_per_gb === 'number';
                          if (isPerGb) {
                            return `${formatPrice(item.price_per_gb as number)}/GB`;
                          }
                          return `${formatPrice(item.price_ngn)} each`;
                        })()}
                      </p>
                      {/* Bug walk theme-B fix: per-item precheck badge */}
                      {precheck[item.plan_code]?.checking && (
                        <p className="text-xs text-[var(--muted)] mt-1 flex items-center gap-1">
                          <span className="inline-block w-3 h-3 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
                          Checking availability…
                        </p>
                      )}
                      {precheck[item.plan_code]?.available === true && precheck[item.plan_code]?.etaSeconds != null && (
                        <p className="text-xs text-green-400 mt-1">
                          ✓ Available · Usually delivered in ~{precheck[item.plan_code]!.etaSeconds}s
                        </p>
                      )}
                      {precheck[item.plan_code]?.available === false && (
                        <p className="text-xs text-red-400 mt-1">
                          ✗ Currently unavailable
                          {precheck[item.plan_code]?.reason ? ` (${precheck[item.plan_code]!.reason})` : ''}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {/* Quantity controls */}
                    {(() => {
                      const isPerGb = (item.plan_type === 'RESIDENTIAL' || item.plan_type === 'MOBILE')
                        && typeof item.price_per_gb === 'number';
                      if (isPerGb) {
                        return (
                          <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
                            <span className="px-2 py-1 rounded bg-[var(--card-hover)] border border-[var(--border)]">
                              {item.quantity_gb ?? item.min_gb ?? 5} GB
                            </span>
                            {item.city_name && (
                              <span className="px-2 py-1 rounded bg-[var(--card-hover)] border border-[var(--border)]">
                                {item.city_name}
                              </span>
                            )}
                          </div>
                        );
                      }
                      return (
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
                      );
                    })()}
                    {/* Line total */}
                    <span className="font-semibold text-[var(--primary)] w-28 text-right">
                      {formatPrice(itemPrice(item))}
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
              We&apos;ll email your receipt after payment. No spam — ever.
            </p>
          </div>

        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Payment method */}
        <div className="mb-4">
          <p className="text-sm font-medium mb-2 text-[var(--muted)]">Payment method</p>
          <div className="grid grid-cols-3 gap-2">
            {([
              { id: 'flutterwave', label: 'Card / Bank', sub: 'Flutterwave' },
              { id: 'paystack', label: 'Card / Transfer', sub: 'Paystack' },
              { id: 'crypto', label: 'Crypto', sub: 'USDT · BTC' },
            ] as const).map(opt => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setGateway(opt.id)}
                className={`px-3 py-3 rounded-xl border text-center transition-colors ${
                  gateway === opt.id
                    ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]'
                    : 'border-[var(--border)] bg-[var(--card)] text-[var(--muted)] hover:border-[var(--primary)]/40'
                }`}
              >
                <span className="block text-sm font-semibold">{opt.label}</span>
                <span className="block text-xs opacity-70 mt-0.5">{opt.sub}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Pay Button */}
        <button
          onClick={handlePay}
          disabled={payDisabled}
          className="w-full py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:opacity-50 disabled:cursor-not-allowed text-black font-semibold rounded-xl transition-colors text-lg"
        >
          {loading
            ? 'Redirecting to payment...'
            : !allChecked
              ? 'Checking availability...'
              : anyUnavailable
                ? 'Some items unavailable'
                : `Pay ${formatPrice(subtotal)}`}
        </button>

        <p className="text-xs text-center text-[var(--muted)] mt-3">
          Your proxy credentials will be shown on the next page.
        </p>
      </div>
    </div>
  );
}
