'use client';

import { useState } from 'react';
import { generateReceiptPDF } from '@/lib/pdf-receipt';
import { useToast } from '@/components/Toast';
import { formatPrice } from '@/lib/products';
// ─── Mock data ────────────────────────────────────────────────────

const MOCK_ORDER = {
  order_id: 'ORD-2025-XXXXX',
  status: 'fulfilled',
  plan_type: 'ISP Proxy',
  country: 'United Kingdom',
  amount_paid_ngn: 6500,
  tx_ref: 'TXF-DANNION-PREVIEW',
  styxproxy_credential: {
    styxproxy_username: 'demo_user_4821',
    styxproxy_password: 'proxyPass_4821!',
    upstream_proxy_ip: '185.199.228.105',
    upstream_proxy_port: 8080,
    expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  },
  created_at: new Date().toISOString(),
  expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  is_renewable: true,
  rotation_count: 1,
  max_rotations: 3,
};

const MOCK_CART = [
  { plan_code: 'ISP-UK-1', name: 'UK ISP Proxy', flag: '🇬🇧', price_ngn: 6500, quantity: 1 },
];

// ─── PDF download ─────────────────────────────────────────────────

function handleDownloadReceipt() {
  generateReceiptPDF(MOCK_ORDER, MOCK_CART, MOCK_ORDER.tx_ref, 'styxproxy-receipt-TXF-DANNION-PREVIEW.pdf');
}

// ─── Manage preview ─────────────────────────────────────────────


function ThankYouPreview() {
  const order = MOCK_ORDER;
  const txRef = MOCK_ORDER.tx_ref;

  return (
    <div className="max-w-lg w-full">
      <div className="text-center mb-6">
        <span className="text-xs font-mono text-[var(--muted)] bg-[var(--card)] px-2 py-1 rounded border border-[var(--border)]">
          PREVIEW — /thank-you
        </span>
      </div>

      <div className="space-y-4">
        {/* Success banner */}
        <div className="rounded-2xl p-5 border bg-emerald-500/10 border-emerald-500/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-sm text-emerald-400">Order Complete!</p>
              <p className="text-xs text-[var(--muted)] mt-0.5">Your proxy credentials are ready</p>
            </div>
          </div>
        </div>

        {/* Order info */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
          <div className="grid grid-cols-2 gap-4">
            {[
              ['Transaction Ref', order.tx_ref],
              ['Order ID', order.order_id],
              ['Plan', order.plan_type],
              ['Amount Paid', `N${order.amount_paid_ngn.toLocaleString('en-NG')}`],
            ].map(([label, value]) => (
              <div key={label}>
                <span className="text-xs text-[var(--muted)]">{label}</span>
                <p className="font-mono text-sm font-medium mt-0.5">{value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Credentials */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Proxy Credentials</h2>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-xs text-[var(--muted)]">Username</span>
                <p className="font-mono text-sm font-medium mt-0.5">{order.styxproxy_credential.styxproxy_username}</p>
              </div>
              <div>
                <span className="text-xs text-[var(--muted)]">Password</span>
                <p className="font-mono text-sm font-medium mt-0.5">{order.styxproxy_credential.styxproxy_password}</p>
              </div>
            </div>
            <div className="bg-[var(--background)] rounded-xl p-4">
              <span className="text-xs text-[var(--muted)]">Full Format</span>
              <p className="font-mono text-xs text-[var(--muted)] break-all leading-relaxed">
                http://{order.styxproxy_credential.styxproxy_username}:{order.styxproxy_credential.styxproxy_password}@{order.styxproxy_credential.upstream_proxy_ip}:{order.styxproxy_credential.upstream_proxy_port}
              </p>
            </div>
            <div className="bg-[var(--background)] rounded-xl p-4">
              <span className="text-xs text-[var(--muted)]">Expires</span>
              <p className="font-medium text-sm">
                {new Date(order.styxproxy_credential.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'long', day: 'numeric' })}
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <button
            onClick={handleDownloadReceipt}
            className="w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download Receipt (PDF)
          </button>
          <a href="/manage" className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors">
            Manage Order →
          </a>
          <a href="/order" className="block w-full px-6 py-3 text-[var(--muted)] hover:text-[var(--foreground)] text-center transition-colors">
            Order Another →
          </a>
        </div>
      </div>
    </div>
  );
}


function ManagePreview() {
  const order = MOCK_ORDER;
  const rotationsLeft = (order.max_rotations ?? 3) - (order.rotation_count ?? 0);

  return (
    <div className="max-w-xl w-full">
      <div className="text-center mb-6">
        <span className="text-xs font-mono text-[var(--muted)] bg-[var(--card)] px-2 py-1 rounded border border-[var(--border)]">
          PREVIEW — /manage
        </span>
      </div>

      <div className="space-y-4">
        {/* Status banner */}
        <div className="rounded-2xl p-5 border bg-emerald-500/10 border-emerald-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p className="font-semibold text-sm text-emerald-400">Proxy Active</p>
                <p className="text-xs text-[var(--muted)] mt-0.5">Your proxy credentials are ready</p>
              </div>
            </div>
            <span className="text-xs font-mono px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-400 capitalize">
              {order.status}
            </span>
          </div>
        </div>

        {/* Order details */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Order Details</h2>
          <div className="space-y-3">
            {[
              ['Order ID', order.order_id],
              ['Transaction Ref', order.tx_ref],
              ['Plan', order.plan_type],
              ['Country', order.country],
              ['Amount Paid', `N${order.amount_paid_ngn.toLocaleString('en-NG')}`],
              ['Expiry', new Date(order.expires_at).toLocaleDateString('en-NG', { year: 'numeric', month: 'short', day: 'numeric' })],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0">
                <span className="text-sm text-[var(--muted)]">{label}</span>
                <span className="text-sm font-mono font-medium">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Credentials */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wide">Your Proxy Credentials</h2>
            <span className="text-xs text-[var(--muted)]">{rotationsLeft} rotation{rotationsLeft !== 1 ? 's' : ''} left</span>
          </div>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3"><div><span className="text-xs text-[var(--muted)]">Username</span><p className="font-mono text-sm font-medium mt-0.5">{MOCK_ORDER.styxproxy_credential.styxproxy_username}</p></div><div><span className="text-xs text-[var(--muted)]">Password</span><p className="font-mono text-sm font-medium mt-0.5">{MOCK_ORDER.styxproxy_credential.styxproxy_password}</p></div></div>
            <div className="bg-[var(--background)] rounded-xl p-4">
              <span className="text-xs text-[var(--muted)]">Full Format</span>
              <p className="font-mono text-xs text-[var(--muted)] break-all leading-relaxed">
                http://{order.styxproxy_credential.styxproxy_username}:{order.styxproxy_credential.styxproxy_password}@{order.styxproxy_credential.upstream_proxy_ip}:{order.styxproxy_credential.upstream_proxy_port}
              </p>
            </div>

            {/* Rotate */}
            <button
              className="w-full px-4 py-2.5 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-xl transition-colors text-sm flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Rotate Proxy Key ({rotationsLeft} left)
            </button>

            {/* Renew */}
            <button
              className="w-full px-4 py-2.5 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-xl transition-colors text-sm flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Renew This Proxy
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-2 gap-3">
          <a href="/order" className="px-5 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl text-sm text-center transition-colors">
            Order Another
          </a>
          <button
            className="px-5 py-3 bg-[#0088cc] hover:bg-[#006699] text-white font-semibold rounded-xl text-sm text-center transition-colors"
          >
            Get Support
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Checkout preview ───────────────────────────────────────────

function CheckoutPreview() {
  const [selected, setSelected] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);

  const methods = [
    { id: 'card', label: 'Card Payment', sub: 'Visa, Mastercard', icon: '💳' },
    { id: 'transfer', label: 'Bank Transfer', sub: 'Access, UBA, GTBank', icon: '🏦' },
    { id: 'ussd', label: 'USSD', sub: 'Nigerian cards only', icon: '📱' },
    { id: 'qr', label: 'QR Code', sub: 'Any banking app', icon: '📲' },
  ];

  const handlePay = () => {
    if (!selected) return;
    setPaying(true);
    setTimeout(() => {
      window.location.href = '/thank-you?tx_ref=TXF-DEMO-CHECKOUT';
    }, 2000);
  };

  return (
    <div className="max-w-lg w-full">
      <div className="text-center mb-6">
        <span className="text-xs font-mono text-[var(--muted)] bg-[var(--card)] px-2 py-1 rounded border border-[var(--border)]">
          PREVIEW — /order/checkout
        </span>
      </div>

      <div className="space-y-4">
        {/* Order summary */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Order Summary</h2>
          <div className="space-y-3">
            {MOCK_CART.map((item) => (
              <div key={item.plan_code} className="flex items-center justify-between py-2 border-b border-[var(--border)]">
                <span className="text-sm">{item.flag} {item.name} × {item.quantity}</span>
                <span className="font-mono text-sm">N{item.price_ngn.toLocaleString('en-NG')}</span>
              </div>
            ))}
            <div className="flex items-center justify-between pt-2">
              <span className="font-semibold">Total</span>
              <span className="font-mono font-bold text-[var(--primary)]">N 6,500</span>
            </div>
          </div>
        </div>

        {/* Payment methods */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Payment Method</h2>
          <div className="space-y-3">
            {methods.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelected(m.id)}
                className={`w-full flex items-center gap-4 p-4 rounded-xl border transition-colors text-left ${
                  selected === m.id
                    ? 'border-[var(--primary)] bg-[var(--primary)]/5'
                    : 'border-[var(--border)] hover:border-[var(--primary)]'
                }`}
              >
                <span className="text-2xl">{m.icon}</span>
                <div>
                  <p className="font-medium text-sm">{m.label}</p>
                  <p className="text-xs text-[var(--muted)]">{m.sub}</p>
                </div>
                {selected === m.id && (
                  <svg className="w-5 h-5 text-[var(--primary)] ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>
            ))}
          </div>
          <p className="text-xs text-[var(--muted)] mt-3 text-center">
            🔒 All payments secured by Flutterwave
          </p>
        </div>

        {/* Pay button */}
        <button
          onClick={handlePay}
          disabled={!selected || paying}
          className="w-full px-6 py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-bold rounded-xl transition-colors text-sm disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {paying ? (
            <>
              <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
              Redirecting to Flutterwave…
            </>
          ) : (
            'Pay N 6,500 Now'
          )}
        </button>
      </div>
    </div>
  );
}

// ─── Main preview page ───────────────────────────────────────────

export default function PreviewPage() {
  const [activeTab, setActiveTab] = useState<'thankyou' | 'manage' | 'checkout'>('thankyou');

  const tabs = [
    { id: 'thankyou' as const, label: 'Thank You' },
    { id: 'manage' as const, label: 'Manage' },
    { id: 'checkout' as const, label: 'Checkout' },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-[var(--background)]">
      <div className="flex-1 px-4 pt-24 pb-16">
          {/* Hero banner — changes per tab */}
          <div className="text-center mb-8">
            {activeTab === 'thankyou' && (
              <>
                <h1 className="text-3xl sm:text-4xl font-bold mb-3 leading-tight" style={{ color: 'var(--foreground)' }}>
                  Payment Confirmed,<br /><span style={{ color: 'var(--primary)' }}>Proxy Ready.</span>
                </h1>
                <p className="text-base" style={{ color: 'var(--muted)' }}>
                  Your credentials are ready. Download your receipt or manage your order below.
                </p>
              </>
            )}
            {activeTab === 'manage' && (
              <>
                <h1 className="text-3xl sm:text-4xl font-bold mb-3 leading-tight" style={{ color: 'var(--foreground)' }}>
                  Manage Your<br /><span style={{ color: 'var(--primary)' }}>Proxy Order.</span>
                </h1>
                <p className="text-base" style={{ color: 'var(--muted)' }}>
                  Rotate keys, renew proxies, or contact support — all in one place.
                </p>
              </>
            )}
            {activeTab === 'checkout' && (
              <>
                <h1 className="text-3xl sm:text-4xl font-bold mb-3 leading-tight" style={{ color: 'var(--foreground)' }}>
                  Complete Your<br /><span style={{ color: 'var(--primary)' }}>Order.</span>
                </h1>
                <p className="text-base" style={{ color: 'var(--muted)' }}>
                  Choose your payment method. All transactions secured by Flutterwave.
                </p>
              </>
            )}
          </div>

          {/* Tab navigation */}
          <div className="flex justify-center gap-2 mb-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-[var(--primary)] text-black'
                    : 'bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] hover:border-[var(--primary)]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Context bar — relevant info per tab */}
          <div className="max-w-2xl mx-auto mb-8 grid grid-cols-3 gap-3 text-center">
            {activeTab === 'thankyou' && [
              { label: 'Order', value: 'Complete' },
              { label: 'Delivery', value: 'Instant' },
              { label: 'Support', value: '24/7' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-[var(--card)] border border-[var(--border)] rounded-xl px-3 py-2">
                <div className="text-sm font-bold" style={{ color: 'var(--primary)' }}>{value}</div>
                <div className="text-xs text-[var(--muted)]">{label}</div>
              </div>
            ))}
            {activeTab === 'manage' && [
              { label: 'Rotation', value: '3x' },
              { label: 'Auto-Renew', value: 'On' },
              { label: 'Support', value: '24/7' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-[var(--card)] border border-[var(--border)] rounded-xl px-3 py-2">
                <div className="text-sm font-bold" style={{ color: 'var(--primary)' }}>{value}</div>
                <div className="text-xs text-[var(--muted)]">{label}</div>
              </div>
            ))}
            {activeTab === 'checkout' && [
              { label: 'Payment', value: 'Secure' },
              { label: 'Methods', value: '4 ways' },
              { label: 'Delivery', value: 'Instant' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-[var(--card)] border border-[var(--border)] rounded-xl px-3 py-2">
                <div className="text-sm font-bold" style={{ color: 'var(--primary)' }}>{value}</div>
                <div className="text-xs text-[var(--muted)]">{label}</div>
              </div>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex justify-center">
            {activeTab === 'thankyou' && <ThankYouPreview />}
            {activeTab === 'manage' && <ManagePreview />}
            {activeTab === 'checkout' && <CheckoutPreview />}
          </div>
        </div>
    </div>
  );
}
