import Link from 'next/link';

export const metadata = {
  title: 'Cookie Policy — Styxproxy',
  description: 'What cookies and storage we use, why, and how to control them.',
};

export default function CookiePolicy() {
  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Hero background layers */}
      <div className="absolute inset-0 hero-bg-grid" />
      <div className="absolute inset-0 hero-bg-rings" />
      <div className="absolute inset-0 hero-bg-vignette" />
      <div className="hero-orb hero-orb-1" />
      <div className="hero-orb hero-orb-2" />

      <main className="relative z-10 flex-1 pt-28 pb-20">
        <div className="max-w-2xl mx-auto px-6">

          {/* Article card */}
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl card-depth overflow-hidden">
            <div className="p-8 sm:p-10">
              {/* Page header */}
              <div className="mb-8">
                <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">Legal</p>
                <h1 className="text-3xl font-black text-[var(--foreground)] mb-2">Cookie Policy</h1>
                <p className="text-[var(--muted)] text-sm">Effective Date: 2026-07-13 · Last Updated: 2026-07-13</p>
              </div>
              <div className="border-t border-[var(--border)] mb-8" />

              <section className="mb-8">
                <p className="text-[var(--muted)] leading-relaxed mb-3">
                  Styxproxy runs on a strict anonymity policy: we collect as little as we can.
                  This page documents every piece of storage we touch, what it does, and how to clear it.
                  If we add anything new, this page will be updated before the change ships.
                </p>
                <p className="text-[var(--muted)] leading-relaxed">
                  TL;DR — we use <strong>localStorage</strong> for one anonymous device identifier
                  and one order-history list. We use <strong>sessionStorage</strong> for your cart
                  and active payment reference. We do not use third-party tracking cookies.
                  We do not fingerprint your device.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-xl font-bold mb-4">What we store</h2>

                {[
                  ['localStorage.styxproxy_device_id', 'A UUID generated on your first visit. Lets the website remember your order history and prevents duplicate payments. No PII — just a random number tied to your browser. Cleared only if you clear site data. We never sync this to our servers.'],
                  ['localStorage.styxproxy_orders', 'Last 50 orders you placed on this device (tx_ref, plan_code, amount, status). Lets you revisit order history without logging in. Cleared only if you clear site data. Never leaves your browser.'],
                  ['localStorage.styxproxy_inflight_order', 'Tracks an in-progress payment (tx_ref + plan_code). Auto-expires after 5 minutes. Prevents accidental double-payments if you click "Pay" twice.'],
                  ['sessionStorage.styxproxy_cart', 'Your shopping cart contents. Cleared when you close the browser tab.'],
                  ['sessionStorage.styxproxy_consent', 'Flag set to "1" after you accept or decline the consent gate. We don\'t remember the choice across sessions — you can change your mind anytime.'],
                  ['sessionStorage.styxproxy_email', 'Email you optionally provided at checkout for receipt delivery. Cleared when the tab closes. We never see this value.'],
                ].map(([key, desc]) => (
                  <div key={key} className="bg-[var(--background)] border border-[var(--border)] rounded-xl p-5 mb-3">
                    <h3 className="font-semibold mb-2 text-[var(--foreground)]"><code>{key}</code></h3>
                    <p className="text-sm text-[var(--muted)]">{desc}</p>
                  </div>
                ))}
              </section>

              <section className="mb-8">
                <h2 className="text-xl font-bold mb-4">What we do NOT use</h2>
                <ul className="list-disc list-inside text-[var(--muted)] space-y-2">
                  <li>No third-party tracking cookies (Google Analytics, Facebook Pixel, etc.)</li>
                  <li>No fingerprinting — we do not combine screen size, fonts, timezone, or user agent</li>
                  <li>No advertising IDs</li>
                  <li>No cross-site cookies</li>
                  <li>No server-side session tracking of anonymous web visitors</li>
                </ul>
              </section>

              <section className="mb-8">
                <h2 className="text-xl font-bold mb-4">Third-party services on payment pages</h2>
                <p className="text-[var(--muted)] leading-relaxed mb-3">
                  When you click "Pay", you are redirected to <strong>Flutterwave</strong> to complete payment.
                  Flutterwave is the payment processor — they have their own privacy policy and cookie use.
                  Once you leave our site for theirs, this policy no longer applies.
                </p>
                <p className="text-[var(--muted)] leading-relaxed">
                  We chose Flutterwave because they accept NGN bank transfer and card payments
                  without forcing an account on the customer. Their checkout is anonymous-by-default for the payer.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-xl font-bold mb-4">How to clear our cookies</h2>
                <p className="text-[var(--muted)] leading-relaxed mb-3">
                  Clear site data in your browser to wipe all Styxproxy storage:
                </p>
                <ul className="list-disc list-inside text-[var(--muted)] space-y-1 mb-3">
                  <li><strong>Chrome:</strong> Settings → Privacy and Security → Cookies and other site data → See all site data and permissions → search "styxproxy" → Remove</li>
                  <li><strong>Firefox:</strong> Settings → Privacy & Security → Cookies and Site Data → Manage Data → search "styxproxy" → Remove Selected</li>
                  <li><strong>Safari:</strong> Develop → Empty Caches (or Safari → Clear History → All History)</li>
                </ul>
                <p className="text-[var(--muted)] leading-relaxed">
                  Or use a private/incognito window — that starts fresh on every visit.
                </p>
              </section>

              <section className="mb-8">
                <h2 className="text-xl font-bold mb-4">Questions</h2>
                <p className="text-[var(--muted)] leading-relaxed">
                  Reach us via{' '}
                  <Link href="/contact" className="text-[var(--primary)] hover:underline">contact form</Link>{' '}
                  or email <a href="mailto:privacy@styxproxy.com" className="text-[var(--primary)] hover:underline">privacy@styxproxy.com</a>.
                </p>
              </section>

              <div className="border-t border-[var(--border)] pt-6">
                <p className="text-xs text-[var(--muted)] text-center">
                  Related:{' '}
                  <Link href="/legal/terms" className="text-[var(--primary)] hover:underline">Terms</Link> ·{' '}
                  <Link href="/legal/privacy" className="text-[var(--primary)] hover:underline">Privacy</Link> ·{' '}
                  <Link href="/legal/aup" className="text-[var(--primary)] hover:underline">AUP</Link> ·{' '}
                  <Link href="/refund-policy" className="text-[var(--primary)] hover:underline">Refund Policy</Link>
                </p>
              </div>
            </div>
          </div>

          {/* CTA */}
          <div className="mt-8 text-center p-6 bg-[var(--card)] border border-[var(--border)] rounded-2xl">
            <p className="text-[var(--muted)] text-sm mb-3">Questions about our cookie use?</p>
            <Link href="/contact" className="text-[var(--primary)] font-semibold hover:underline text-sm">
              Contact us →
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
