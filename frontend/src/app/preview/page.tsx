'use client';

import { useState } from 'react';
import Head from 'next/head';

// Mock data for all preview states
const MOCK_ORDER = {
  order_id: 'ORD-2025-XXXXX',
  status: 'fulfilled',
  plan_type: 'ISP Proxy',
  country: 'United Kingdom',
  amount_paid_ngn: 6500,
  tx_ref: 'TXF-DANNION-PREVIEW',
  styxproxy_credential: {
    bun_username: 'demo_user_4821',
    upstream_proxy_ip: '185.199.228.105',
    upstream_proxy_port: 8080,
    expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  },
  created_at: new Date().toISOString(),
  expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
};

const MOCK_CART = [
  { plan_code: 'ISP-UK-1', name: 'UK ISP Proxy', flag: '🇬🇧', price_ngn: 6500, quantity: 1 },
];

// ─── Thank-you preview ───────────────────────────────────────────
function ThankYouPreview() {
  const order = MOCK_ORDER;
  const cart = MOCK_CART;
  const txRef = MOCK_ORDER.tx_ref;
  const isSuccess = true;

  return (
    <div className="max-w-lg w-full">
      <div className="text-center mb-2">
        <span className="text-xs font-mono text-[var(--muted)] bg-[var(--card)] px-2 py-1 rounded border border-[var(--border)]">
          PREVIEW — /thank-you?tx_ref={txRef}
        </span>
      </div>

      <div className="animate-fade-in">
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--primary)]/20 flex items-center justify-center">
            <svg className="w-8 h-8 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-[var(--primary)] mb-2">Order Complete!</h1>
          <p className="text-[var(--muted)]">
            Your proxies are ready. Here are your credentials:
          </p>
        </div>

        {/* Credentials Card */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Proxy Credentials</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-[var(--muted)]">Username</label>
              <p className="font-mono text-lg">{order.styxproxy_credential?.bun_username}</p>
            </div>
            <div>
              <label className="text-sm text-[var(--muted)]">Proxy Address</label>
              <p className="font-mono text-lg">
                {order.styxproxy_credential?.upstream_proxy_ip}:{order.styxproxy_credential?.upstream_proxy_port}
              </p>
            </div>
            <div>
              <label className="text-sm text-[var(--muted)]">Format</label>
              <p className="font-mono text-sm text-[var(--muted)] break-all">
                {order.styxproxy_credential?.bun_username}:your_password@185.199.228.105:8080
              </p>
            </div>
            <div>
              <label className="text-sm text-[var(--muted)]">Expires</label>
              <p className="font-medium">
                {new Date(order.styxproxy_credential?.expires_at!).toLocaleDateString('en-NG', {
                  year: 'numeric', month: 'long', day: 'numeric',
                })}
              </p>
            </div>
          </div>
        </div>

        {/* Order Summary */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-[var(--muted)]">Order ID</span>
              <p className="font-medium">{order.order_id}</p>
            </div>
            <div>
              <span className="text-[var(--muted)]">Amount Paid</span>
              <p className="font-medium">₦{cart[0].price_ngn.toLocaleString('en-NG')}</p>
            </div>
            <div>
              <span className="text-[var(--muted)]">Status</span>
              <p className="font-medium text-[var(--primary)] capitalize">{order.status}</p>
            </div>
            <div>
              <span className="text-[var(--muted)]">Items</span>
              <p className="font-medium">{cart.reduce((s, i) => s + i.quantity, 0)} proxies</p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <button className="w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors flex items-center justify-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download Receipt (PDF)
          </button>
          <a href="/preview/manage" className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors">
            Manage Order →
          </a>
          <a href="/preview/checkout" className="block w-full px-6 py-3 text-[var(--muted)] hover:text-[var(--foreground)] text-center transition-colors">
            Order Another →
          </a>
        </div>
      </div>
    </div>
  );
}

// ─── Manage preview ─────────────────────────────────────────────
function ManagePreview() {
  const order = MOCK_ORDER;
  const isActive = true;

  return (
    <div className="max-w-xl w-full">
      <div className="text-center mb-2">
        <span className="text-xs font-mono text-[var(--muted)] bg-[var(--card)] px-2 py-1 rounded border border-[var(--border)]">
          PREVIEW — /manage
        </span>
      </div>

      <div className="space-y-4 animate-fade-in">
        {/* Status Banner */}
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
            <span className="text-xs font-mono px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-400">
              {order.status}
            </span>
          </div>
        </div>

        {/* Order Details Card */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Order Details</h2>
          <div className="space-y-3">
            {[
              ['Order ID', order.order_id],
              ['Transaction Ref', order.tx_ref],
              ['Plan', order.plan_type],
              ['Country', order.country],
              ['Amount Paid', `₦${order.amount_paid_ngn.toLocaleString('en-NG')}`],
              ['Ordered', new Date(order.created_at!).toLocaleDateString('en-NG', { year: 'numeric', month: 'short', day: 'numeric' })],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0">
                <span className="text-sm text-[var(--muted)]">{label}</span>
                <span className="text-sm font-mono font-medium">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Credentials Card */}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wide">Your Proxy Credentials</h2>
          <div className="space-y-3">
            {[
              { label: 'Username', value: order.styxproxy_credential?.bun_username },
              { label: 'Proxy Address', value: `${order.styxproxy_credential?.upstream_proxy_ip}:${order.styxproxy_credential?.upstream_proxy_port}` },
            ].map(({ label, value }) => (
              <div key={label} className="bg-[var(--background)] rounded-xl p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-[var(--muted)]">{label}</span>
                  <button className="text-xs text-[var(--primary)] hover:underline">Copy</button>
                </div>
                <p className="font-mono text-sm font-medium">{value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-2 gap-3 pt-2">
          <a href="/order" className="px-5 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl text-sm text-center transition-colors">
            Order Another
          </a>
          <a href="https://t.me/StyxproxyBot" className="px-5 py-3 bg-[#0088cc] hover:bg-[#006699] text-white font-semibold rounded-xl text-sm text-center transition-colors">
            Get Support
          </a>
        </div>
      </div>
    </div>
  );
}

// ─── Checkout preview ───────────────────────────────────────────
function CheckoutPreview() {
  const [selected, setSelected] = useState('card');

  return (
    <div className="max-w-lg w-full">
      <div className="text-center mb-2">
        <span className="text-xs font-mono text-[var(--muted)] bg-[var(--card)] px-2 py-1 rounded border border-[var(--border)]">
          PREVIEW — /order/checkout
        </span>
      </div>

      <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Order Summary</h2>
        <div className="space-y-3 mb-4">
          {MOCK_CART.map(item => (
            <div key={item.plan_code} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg">{item.flag}</span>
                <span className="text-sm font-medium">{item.name} × {item.quantity}</span>
              </div>
              <span className="text-sm font-semibold">₦{item.price_ngn.toLocaleString('en-NG')}</span>
            </div>
          ))}
        </div>
        <div className="border-t border-[var(--border)] pt-3 flex items-center justify-between">
          <span className="font-semibold">Total</span>
          <span className="font-bold text-lg" style={{ color: 'var(--primary)' }}>
            ₦{MOCK_CART[0].price_ngn.toLocaleString('en-NG')}
          </span>
        </div>
      </div>

      {/* Payment Methods */}
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Select Payment Method</h2>
        <div className="space-y-2">
          {[
            { id: 'card', label: '💳 Card (Visa/Mastercard)', sub: 'Instant confirmation' },
            { id: 'bank', label: '🏦 Bank Transfer', sub: 'Nigeria: Access, UBA, GTBank' },
            { id: 'ussd', label: '📱 USSD', sub: 'Nigerian cards' },
            { id: 'qr', label: '📲 QR Code', sub: 'Scan with any banking app' },
          ].map(method => (
            <button
              key={method.id}
              onClick={() => setSelected(method.id)}
              className={`w-full flex items-center gap-3 p-4 rounded-xl border text-left transition-all ${
                selected === method.id
                  ? 'border-[var(--primary)] bg-[var(--primary)]/5'
                  : 'border-[var(--border)] hover:border-[var(--primary)]'
              }`}
            >
              <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                selected === method.id ? 'border-[var(--primary)]' : 'border-[var(--border)]'
              }`}>
                {selected === method.id && (
                  <div className="w-2.5 h-2.5 rounded-full bg-[var(--primary)]" />
                )}
              </div>
              <div>
                <p className="text-sm font-medium">{method.label}</p>
                <p className="text-xs text-[var(--muted)]">{method.sub}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Pay Button */}
      <button className="w-full px-6 py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-bold rounded-xl transition-colors text-base">
        Pay ₦{MOCK_CART[0].price_ngn.toLocaleString('en-NG')} →
      </button>

      <p className="text-xs text-center text-[var(--muted)] mt-3">
        Secured by Flutterwave. Your card details are never stored.
      </p>
    </div>
  );
}

// ─── Main preview page ──────────────────────────────────────────
export default function PreviewPage() {
  const [tab, setTab] = useState<'thank-you' | 'manage' | 'checkout'>('thank-you');

  return (
    <>
      <Head>
        <title>Page Preview — Styxproxy</title>
      </Head>
      <main className="min-h-screen bg-[var(--background)] flex flex-col">
        {/* Sticky preview banner */}
        <div className="sticky top-0 z-50 bg-amber-600 text-white text-center py-2 px-4 text-sm font-medium">
          🔍 <strong>Preview Mode</strong> — This is a simulated preview. Not connected to live backend.
          {' '}
          <a href="/" className="underline">← Back to homepage</a>
        </div>

        {/* Page tabs */}
        <div className="border-b border-[var(--border)] bg-[var(--card)]">
          <div className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto">
            {([
              ['thank-you', '✅ Thank-You / Receipt'],
              ['manage', '📋 Manage Order'],
              ['checkout', '🛒 Checkout / Payment'],
            ] as const).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  tab === key
                    ? 'border-[var(--primary)] text-[var(--primary)]'
                    : 'border-transparent text-[var(--muted)] hover:text-[var(--foreground)]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex items-start justify-center px-4 py-12">
          {tab === 'thank-you' && <ThankYouPreview />}
          {tab === 'manage' && <ManagePreview />}
          {tab === 'checkout' && <CheckoutPreview />}
        </div>
      </main>
    </>
  );
}
