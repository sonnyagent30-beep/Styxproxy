import Link from 'next/link';

export const metadata = {
  title: 'Cookie Policy — Styxproxy',
  description: 'What cookies and storage we use, why, and how to control them.',
};

export default function CookiePolicy() {
  return (
    <main className="flex-1 px-4 py-24">
      <article className="max-w-3xl mx-auto">
        <header className="mb-10">
          <h1 className="text-4xl font-bold mb-3">Cookie Policy</h1>
          <p className="text-[var(--muted)] text-sm">Effective Date: 2026-07-13 · Last Updated: 2026-07-13</p>
        </header>

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
          <h2 className="text-2xl font-bold mb-3">What we store</h2>

          <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 mb-4">
            <h3 className="font-semibold mb-2"><code>localStorage.styxproxy_device_id</code></h3>
            <p className="text-sm text-[var(--muted)]">
              A UUID generated on your first visit. Lets the website remember your order history
              and prevents duplicate payments. No PII — just a random number tied to your browser.
              Cleared only if you clear site data. We never sync this to our servers.
            </p>
          </div>

          <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 mb-4">
            <h3 className="font-semibold mb-2"><code>localStorage.styxproxy_orders</code></h3>
            <p className="text-sm text-[var(--muted)]">
              Last 50 orders you placed on this device (tx_ref, plan_code, amount, status).
              Lets you revisit order history without logging in. Cleared only if you clear site data.
              Never leaves your browser.
            </p>
          </div>

          <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 mb-4">
            <h3 className="font-semibold mb-2"><code>localStorage.styxproxy_inflight_order</code></h3>
            <p className="text-sm text-[var(--muted)]">
              Tracks an in-progress payment (tx_ref + plan_code). Auto-expires after 5 minutes.
              Prevents accidental double-payments if you click &ldquo;Pay&rdquo; twice.
            </p>
          </div>

          <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 mb-4">
            <h3 className="font-semibold mb-2"><code>sessionStorage.styxproxy_cart</code></h3>
            <p className="text-sm text-[var(--muted)]">
              Your shopping cart contents. Cleared when you close the browser tab.
            </p>
          </div>

          <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 mb-4">
            <h3 className="font-semibold mb-2"><code>sessionStorage.styxproxy_consent</code></h3>
            <p className="text-sm text-[var(--muted)]">
              Flag set to &ldquo;1&rdquo; after you accept or decline the consent gate.
              We don&apos;t remember the choice across sessions — you can change your mind anytime.
            </p>
          </div>

          <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 mb-4">
            <h3 className="font-semibold mb-2"><code>sessionStorage.styxproxy_email</code></h3>
            <p className="text-sm text-[var(--muted)]">
              Email you optionally provided at checkout for receipt delivery.
              Cleared when the tab closes. We never see this value.
            </p>
          </div>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold mb-3">What we do NOT use</h2>
          <ul className="list-disc list-inside text-[var(--muted)] space-y-2 ml-4">
            <li>No third-party tracking cookies (Google Analytics, Facebook Pixel, etc.)</li>
            <li>No fingerprinting — we do not combine screen size, fonts, timezone, or user agent</li>
            <li>No advertising IDs</li>
            <li>No cross-site cookies</li>
            <li>No server-side session tracking of anonymous web visitors</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold mb-3">Third-party services on payment pages</h2>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            When you click &ldquo;Pay&rdquo;, you are redirected to <strong>Flutterwave</strong> to complete payment.
            Flutterwave is the payment processor — they have their own privacy policy and cookie use.
            Once you leave our site for theirs, this policy no longer applies.
          </p>
          <p className="text-[var(--muted)] leading-relaxed">
            We chose Flutterwave because they accept NGN bank transfer and card payments
            without forcing an account on the customer. Their checkout is anonymous-by-default for the payer.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold mb-3">How to clear our cookies</h2>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            Clear site data in your browser to wipe all Styxproxy storage:
          </p>
          <ul className="list-disc list-inside text-[var(--muted)] space-y-1 ml-4 mb-3">
            <li><strong>Chrome:</strong> Settings → Privacy and Security → Cookies and other site data → See all site data and permissions → search &ldquo;styxproxy&rdquo; → Remove</li>
            <li><strong>Firefox:</strong> Settings → Privacy & Security → Cookies and Site Data → Manage Data → search &ldquo;styxproxy&rdquo; → Remove Selected</li>
            <li><strong>Safari:</strong> Develop → Empty Caches (or Safari → Clear History → All History)</li>
          </ul>
          <p className="text-[var(--muted)] leading-relaxed">
            Or use a private/incognito window — that starts fresh on every visit.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold mb-3">Questions</h2>
          <p className="text-[var(--muted)] leading-relaxed">
            Reach us via{' '}
            <Link href="/contact" className="text-[var(--primary)] hover:underline">contact form</Link>{' '}
            or email <a href="mailto:privacy@styxproxy.com" className="text-[var(--primary)] hover:underline">privacy@styxproxy.com</a>.
          </p>
        </section>

        <section className="text-xs text-[var(--muted)] text-center pt-6 border-t border-[var(--border)]">
          <p>
            Related:{' '}
            <Link href="/legal/terms" className="text-[var(--primary)] hover:underline">Terms</Link> ·{' '}
            <Link href="/legal/privacy" className="text-[var(--primary)] hover:underline">Privacy</Link> ·{' '}
            <Link href="/legal/aup" className="text-[var(--primary)] hover:underline">AUP</Link> ·{' '}
            <Link href="/refund-policy" className="text-[var(--primary)] hover:underline">Refund Policy</Link>
          </p>
        </section>
      </article>
    </main>
  );
}