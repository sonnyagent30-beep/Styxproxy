'use client';

/* eslint-disable react-hooks/set-state-in-effect */

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { formatPrice, COUNTRIES } from '@/lib/products';
import { Flag } from '@/components/ui/Flag';
import type { CartItem } from '@/types';
import api from '@/lib/api';
import { tryStartOrder, setInflightOrder, clearInflightOrder, getDeviceId, addToOrderHistory } from '@/lib/device-id';
import { useCartStore } from '@/store/cart-store';

// Backend is the single source of truth for pricing.
// amount_ngn is fetched from /api/payments/initiate on page load.

// Payment Flow Rewrite (Sprint 025):
// - No client-side tx_ref generation — backend owns it
// - Idempotency-Key header for safe retries
// - Payment timeout countdown (15 min)

const PAYMENT_TIMEOUT_SECONDS = 15 * 60; // 15 minutes

function generateIdempotencyKey(): string {
  // UUID v4 for idempotency key
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

type GatewayId = 'flutterwave' | 'paystack' | 'stripe' | 'paynow';

interface GatewayInfo {
  available: boolean;
  label: string;
  icon: string;
  description: string;
}

const GATEWAY_ORDER: GatewayId[] = ['flutterwave', 'paystack', 'stripe', 'paynow'];

export default function CheckoutClient() {
  const router = useRouter();
  // `total` in the cart store is a FUNCTION (`total: () => number`), so it must
  // be called. Destructuring it as `total: cartTotal` and passing `cartTotal`
  // to formatPrice passed the function itself, and
  // Intl.NumberFormat.format(function) yields NaN — which rendered as "₦NaN"
  // for the payment amount on the checkout page.
  const { items: cart, total: cartTotalFn, setCart } = useCartStore();
  const cartTotal = cartTotalFn();
  const [email, setEmail] = useState('');
  const [gateway, setGateway] = useState<GatewayId>('flutterwave');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  // Name of the item holding an in-flight payment lock, if any. Drives the
  // "Cancel and start over" control — without it a failed/abandoned payment
  // left the device permanently locked out with no in-app way out.
  const [inflight, setInflight] = useState<string | null>(null);
  const [gateways, setGateways] = useState<Record<GatewayId, GatewayInfo>>({
    flutterwave: { available: true, label: 'Flutterwave', icon: '💳', description: 'Card, Bank Transfer, USSD, QR' },
    paystack: { available: true, label: 'Paystack', icon: '🏦', description: 'Card, Bank Transfer, USSD' },
    stripe: { available: true, label: 'Stripe', icon: '💰', description: 'International cards' },
    paynow: { available: true, label: 'Paynow', icon: '₿', description: 'Bitcoin, USDT, Crypto' },
  });
  const [gatewaysLoading, setGatewaysLoading] = useState(true);
  const [precheck, setPrecheck] = useState<Record<string, {
    checking: boolean;
    available?: boolean;
    reason?: string;
    etaSeconds?: number;
  }>>({});
  
  // Payment timeout countdown
  const [timeRemaining, setTimeRemaining] = useState(PAYMENT_TIMEOUT_SECONDS);
  const [timedOut, setTimedOut] = useState(false);
  const paymentInitiated = useRef(false);

  // Fetch available gateways from backend
  useEffect(() => {
    let cancelled = false;
    const loadGateways = async () => {
      try {
        const r = await api.fetchGateways();
        if (cancelled || !r.data?.gateways) return;
        const fetched = r.data.gateways as Record<GatewayId, GatewayInfo>;
        setGateways(fetched);
        if (!fetched[gateway]?.available) {
          const firstAvailable = GATEWAY_ORDER.find(g => fetched[g]?.available);
          if (firstAvailable) setGateway(firstAvailable);
        }
      } catch {
        // Fail open — backend will reject if not available
      } finally {
        if (!cancelled) setGatewaysLoading(false);
      }
    };
    loadGateways();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (cart.length === 0) {
      router.replace('/order');
    }
  }, [cart, router]);

  // Precheck per cart item
  useEffect(() => {
    if (cart.length === 0) return;
    let cancelled = false;
    const runPrecheck = async () => {
      const initial: typeof precheck = {};
      cart.forEach(item => { initial[item.plan_code] = { checking: true }; });
      setPrecheck(initial);
      for (const item of cart) {
        try {
          const isPerGb = (item.plan_type === 'RESIDENTIAL' || item.plan_type === 'MOBILE')
            && typeof item.price_per_gb === 'number';
          // The cart stores 'GENERIC' for a country-less residential/mobile
          // order, but precheck validates `country` against a real ISO enum and
          // rejects 'GENERIC' with 422. The catch below fails open, so the user
          // still sees "available" — but they get no ETA and no out-of-stock
          // warning, silently. Send the country the order is actually created
          // with instead of the sentinel.
          const precheckCountry =
            !item.country_code || item.country_code === 'GENERIC' ? 'NG' : item.country_code;
          const r = await api.precheckOrder(
            item.plan_code,
            precheckCountry,
            isPerGb ? 1 : item.quantity,
            { quantity_gb: isPerGb ? item.quantity_gb : undefined, city_id: item.city_id ?? null, city_name: item.city_name ?? null },
          );
          if (cancelled) return;
          if (r.data) {
            setPrecheck(prev => ({ ...prev, [item.plan_code]: { checking: false, available: r.data!.available, reason: r.data!.reason, etaSeconds: r.data!.estimated_delivery_seconds } }));
          } else {
            setPrecheck(prev => ({ ...prev, [item.plan_code]: { checking: false, available: true, etaSeconds: 60 } }));
          }
        } catch {
          if (cancelled) return;
          setPrecheck(prev => ({ ...prev, [item.plan_code]: { checking: false, available: true, etaSeconds: 60 } }));
        }
      }
    };
    runPrecheck();
    return () => { cancelled = true; };
  }, [cart]);

  // Payment timeout countdown
  useEffect(() => {
    if (paymentInitiated.current) return;
    const interval = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          setTimedOut(true);
          paymentInitiated.current = true;
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const updateQuantity = (plan_code: string, delta: number) => {
    const updated = cart.map(item => {
      if (item.plan_code === plan_code) {
        const newQty = Math.max(1, item.quantity + delta);
        return { ...item, quantity: newQty };
      }
      return item;
    }).filter(item => item.quantity > 0);
    setCart(updated);
    sessionStorage.setItem('styxproxy_cart', JSON.stringify(updated));
  };

  const removeItem = (plan_code: string) => {
    const updated = cart.filter(i => i.plan_code !== plan_code);
    setCart(updated);
    sessionStorage.setItem('styxproxy_cart', JSON.stringify(updated));
    if (updated.length === 0) router.replace('/order');
  };

  const allChecked = cart.length > 0 && cart.every(item => !precheck[item.plan_code]?.checking);
  const anyUnavailable = cart.some(item => precheck[item.plan_code]?.available === false);
  const isGatewayAvailable = gateways[gateway]?.available;
  const payDisabled = loading || cart.length === 0 || !allChecked || anyUnavailable || gatewaysLoading || !isGatewayAvailable || timedOut;

  const handlePay = async () => {
    if (cart.length === 0 || !isGatewayAvailable || timedOut) return;
    setError('');
    setLoading(true);
    paymentInitiated.current = true;

    try {
      const trimmedEmail = email.trim();
      if (trimmedEmail) {
        sessionStorage.setItem('styxproxy_email', trimmedEmail);
      }

      // Double-payment prevention
      const idempotencyKey = generateIdempotencyKey();
      const deviceId = getDeviceId();
      for (let i = 0; i < cart.length; i++) {
        const { is_resume } = tryStartOrder(cart[i].plan_code, () => idempotencyKey);
        if (is_resume) {
          setInflight(cart[i].name);
          setError(
            `A payment for ${cart[i].name} is already in progress on this device. ` +
            `If you don't see it, it may have been abandoned — you can cancel it and start again.`,
          );
          setLoading(false);
          return;
        }
      }

      // Fire one initiate per cart item in parallel. Each item gets its OWN
      // idempotency key: sharing one key across items made item 2+ collide
      // with item 1's stored payload and 409.
      const results = await Promise.allSettled(
        cart.map((item) => {
          const isPerGb = (item.plan_type === 'RESIDENTIAL' || item.plan_type === 'MOBILE')
            && typeof item.price_per_gb === 'number';
          return api.initiatePayment({
            planCode: item.plan_code,
            // Residential/mobile are priced per GB, so quantity stays 1 (one
            // gateway) and the GB count travels in quantity_gb. The backend
            // multiplies price_per_gb x quantity_gb; sending GB in `quantity`
            // made the API bill a single GB.
            quantity: isPerGb ? 1 : item.quantity,
            quantityGb: isPerGb ? (item.quantity_gb || item.min_gb || 5) : undefined,
            customerEmail: trimmedEmail || undefined,
            gateway,
            idempotencyKey: generateIdempotencyKey(),
            deviceId,
          });
        }),
      );

      let firstCheckoutUrl = '';
      let lastError = '';
      for (let i = 0; i < results.length; i++) {
        const r = results[i];
        if (r.status === 'fulfilled' && r.value.data?.checkout_url) {
          firstCheckoutUrl = r.value.data.checkout_url;
          if (r.value.data.order_id) {
            sessionStorage.setItem('styxproxy_order_id', r.value.data.order_id);
            sessionStorage.setItem('styxproxy_active_tx', r.value.data.order_id);
          }
          const backendAmount = r.value.data.amount_ngn;
          addToOrderHistory({
            order_id: r.value.data.order_id,
            tx_ref: r.value.data.order_id,
            plan_code: cart[i].plan_code,
            country: cart[i].country_code || 'NG',
            amount: backendAmount,
            status: 'pending',
            created_at: new Date().toISOString(),
          });
          break;
        }
        if (r.status === 'rejected') {
          lastError = r.reason?.message || 'Payment initiation failed';
        } else if (r.status === 'fulfilled' && r.value.error) {
          lastError = r.value.error;
        }
      }

      if (firstCheckoutUrl) {
        window.location.href = firstCheckoutUrl;
        return;
      }

      // No checkout URL — release the in-flight lock. Without this, a failed
      // attempt (gateway 4xx, network blip, declined init) left the lock set
      // and every subsequent attempt on this device was refused as "already
      // in progress" — a hard sales trap with no in-app recovery.
      clearInflightOrder();
      setInflight(null);

      setError(`Could not start payment for any items. ${lastError ? `Last error: ${lastError}` : 'Please try again.'}`);
      setLoading(false);
    } catch {
      clearInflightOrder();
      setInflight(null);
      setError('Failed to initiate payment. Please try again.');
      setLoading(false);
    }
  };

  /** Release the in-flight lock so the customer can retry immediately. */
  const handleCancelInflight = () => {
    import('@/lib/device-id').then(({ clearInflightOrder }) => {
      clearInflightOrder();
      setInflight(null);
      setError('');
    });
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
        <Link href="/order" className="inline-flex items-center text-[var(--muted)] hover:text-[var(--foreground)] mb-6 transition-colors">
          <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to browse
        </Link>

        <h1 className="text-3xl font-bold mb-8">Checkout</h1>

        {/* Payment timeout warning */}
        {timedOut ? (
          <div className="mb-6 p-4 bg-[var(--error)]/10 border border-[var(--error)]/30 rounded-xl text-center">
            <p className="text-[var(--error)] font-semibold">Session expired</p>
            <p className="text-sm text-[var(--muted)] mt-1">Your checkout session has expired. Please go back and try again.</p>
            <Link href="/order" className="inline-block mt-3 px-6 py-2 bg-[var(--primary)] text-black font-medium rounded-lg">
              Start New Order
            </Link>
          </div>
        ) : (
          <div className="mb-4 p-3 bg-[var(--card)] border border-[var(--border)] rounded-xl flex items-center justify-between">
            <span className="text-sm text-[var(--muted)]">Session expires in</span>
            <span className={`font-mono font-semibold ${timeRemaining < 60 ? 'text-[var(--error)]' : 'text-[var(--primary)]'}`}>
              {formatTime(timeRemaining)}
            </span>
          </div>
        )}

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
                        <p className="text-base text-[var(--muted)]">
                          <Flag countryCode={item.country_code} size={14} /> {country.name} · {country.region}
                          {item.city_name ? ` · ${item.city_name}` : ''}
                        </p>
                      )}
                      <p className="text-sm text-[var(--muted)]">
                        {(() => {
                          const isPerGb = (item.plan_type === 'RESIDENTIAL' || item.plan_type === 'MOBILE')
                            && typeof item.price_per_gb === 'number';
                          if (isPerGb) return `${formatPrice(item.price_per_gb as number)}/GB`;
                          return `${formatPrice(item.price_ngn)} each`;
                        })()}
                      </p>
                      {precheck[item.plan_code]?.checking && (
                        <p className="text-base text-[var(--muted)] mt-1 flex items-center gap-1">
                          <span className="inline-block w-3 h-3 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
                          Checking availability…
                        </p>
                      )}
                      {precheck[item.plan_code]?.available === true && precheck[item.plan_code]?.etaSeconds != null && (
                        <p className="text-base text-[var(--success)] mt-1">✓ Available · Usually delivered in ~{precheck[item.plan_code]!.etaSeconds}s</p>
                      )}
                      {precheck[item.plan_code]?.available === false && (
                        <p className="text-base text-[var(--error)] mt-1">
                          ✗ Currently unavailable
                          {precheck[item.plan_code]?.reason ? ` (${precheck[item.plan_code]!.reason})` : ''}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
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
                          <button onClick={() => updateQuantity(item.plan_code, -1)} className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] hover:border-[var(--primary)] flex items-center justify-center transition-colors">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" /></svg>
                          </button>
                          <span className="w-6 text-center font-medium">{item.quantity}</span>
                          <button onClick={() => updateQuantity(item.plan_code, 1)} className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] hover:border-[var(--primary)] flex items-center justify-center transition-colors">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                          </button>
                        </div>
                      );
                    })()}
                    <span className="font-semibold text-[var(--primary)] w-28 text-right">
                      {formatPrice(item.price_ngn || 0)}
                    </span>
                    <button onClick={() => removeItem(item.plan_code)} className="w-8 h-8 rounded-lg hover:bg-[var(--error)]/10 flex items-center justify-center text-[var(--muted)] hover:text-[var(--error)] transition-colors" title="Remove">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 p-4 rounded-xl bg-[var(--card)] border border-[var(--border)]">
            <div className="flex justify-between items-center">
              <span className="text-[var(--muted)]">Payment amount</span>
              <span className="text-lg font-bold text-[var(--primary)]">{formatPrice(cartTotal)}</span>
            </div>
            <p className="text-base text-[var(--muted)] mt-1 text-right">Confirmed on payment page</p>
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
            <p className="text-base text-[var(--muted)] mt-2">We&apos;ll email your receipt after payment. No spam — ever.</p>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-[var(--error)]/10 border border-[var(--error)]/20 text-[var(--error)] text-sm">
            <p>{error}</p>
            {inflight && (
              <button
                type="button"
                onClick={handleCancelInflight}
                className="mt-2 underline underline-offset-2 font-medium hover:opacity-80"
              >
                Cancel this payment and start over
              </button>
            )}
          </div>
        )}

        {/* Payment Gateway */}
        <div className="mb-6">
          <p className="text-sm font-medium mb-2 text-[var(--muted)]">Payment method</p>
          <div className="grid grid-cols-2 gap-2">
            {GATEWAY_ORDER.map(gw => {
              const info = gateways[gw];
              const selected = gateway === gw;
              const isAvailable = info?.available;
              return (
                <button
                  key={gw}
                  type="button"
                  disabled={!isAvailable || gatewaysLoading}
                  onClick={() => isAvailable && setGateway(gw)}
                  className={`flex items-center gap-3 p-3 rounded-xl border text-left transition-colors relative ${
                    selected && isAvailable
                      ? 'border-[var(--primary)] bg-[var(--primary)]/10'
                      : isAvailable
                        ? 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/40'
                        : 'border-[var(--border)] bg-[var(--card)] opacity-40 cursor-not-allowed'
                  }`}
                >
                  <span className="text-xl">{info?.icon}</span>
                  <div className="min-w-0 flex-1">
                    <span className={`block text-sm font-semibold ${selected && isAvailable ? 'text-[var(--primary)]' : 'text-[var(--foreground)]'}`}>
                      {info?.label}
                    </span>
                    <span className="block text-xs text-[var(--muted)] truncate">
                      {isAvailable ? info?.description : 'Unavailable'}
                    </span>
                  </div>
                  {!isAvailable && (
                    <span className="absolute top-1 right-2 text-xs font-bold uppercase tracking-wider text-[var(--muted)]">Coming soon</span>
                  )}
                </button>
              );
            })}
          </div>
          <p className="text-base text-[var(--muted)] mt-2">All transactions are processed securely. You'll be redirected to complete your payment.</p>
        </div>

        {/* Pay Button */}
        <button
          onClick={handlePay}
          disabled={payDisabled}
          className="w-full py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:opacity-50 disabled:cursor-not-allowed text-black font-semibold rounded-xl transition-colors text-lg"
        >
          {loading
            ? 'Redirecting to payment...'
            : timedOut
              ? 'Session expired'
              : !allChecked
                ? 'Checking availability...'
                : anyUnavailable
                  ? 'Some items unavailable'
                  : !isGatewayAvailable
                    ? 'Select a payment method'
                    : `Pay with ${gateways[gateway]?.label || gateway}`}
        </button>

        <p className="text-base text-center text-[var(--muted)] mt-3">
          Your proxy credentials will be shown on the next page.
        </p>
      </div>
    </div>
  );
}
