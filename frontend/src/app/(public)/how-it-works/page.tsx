import { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'How It Works | Styxproxy',
  description: 'Order proxies in seconds. Get credentials instantly. Use on any device.',
};

const steps = [
  {
    number: '01',
    title: 'Pick your proxy',
    description:
      'Choose from ISP, Residential, Mobile 4G, or Datacenter proxies. Select your country and plan. Pay securely with card, bank transfer, USSD, or QR code.',
    details: ['9+ countries for ISP', '14+ countries for Residential', 'Instant activation'],
    cta: 'View products',
    ctaHref: '/products',
  },
  {
    number: '02',
    title: 'Pay and get credentials',
    description:
      'Complete payment via Flutterwave. Your proxy credentials are delivered instantly to your dashboard, email, WhatsApp, and Telegram. All in under 30 seconds.',
    details: ['Instant delivery', 'WhatsApp + Telegram + Email', 'No account required'],
    cta: 'Start ordering',
    ctaHref: '/order',
  },
  {
    number: '03',
    title: 'Use immediately',
    description:
      'Connect using HTTP/SOCKS5 in any browser, bot, or application. Rotate IPs, manage credentials, and monitor usage from your dashboard.',
    details: ['HTTP/SOCKS5 support', 'Rotate IPs on demand', 'Dashboard management'],
    cta: 'Order now',
    ctaHref: '/order',
  },
];

const features = [
  {
    title: 'Instant delivery',
    description: 'Credentials delivered within 30 seconds of payment. No waiting, no manual activation.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
      </svg>
    ),
  },
  {
    title: 'Private and secure',
    description: 'Every proxy is tested before delivery. No shared credentials. Your access is exclusive.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
      </svg>
    ),
  },
  {
    title: 'Easy rotation',
    description: 'Rotate IPs instantly via dashboard or API. Dante-based credential rotation means zero downtime.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
      </svg>
    ),
  },
  {
    title: 'Real-time monitoring',
    description: 'Track usage, view bandwidth, and manage all your proxies from a single dashboard.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
      </svg>
    ),
  },
  {
    title: 'Human support',
    description: 'Talk to a real person via WhatsApp, Telegram, or email. No bots, no ticket queues.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.355 0-2.697-.056-4.024-.166-1.133-.093-1.97-.965-1.97-2.017v-4.286c0-1.136.847-2.1 1.98-2.193.34-.027.68-.052 1.02-.072v3.091l3-3a9.02 9.02 0 011.583-.159z" />
      </svg>
    ),
  },
  {
    title: 'Ban replacement',
    description: 'Banned proxy? We replace it at no cost. Covered for ISP and Residential within your billing period.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    ),
  },
];

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen text-[var(--foreground)]">
      {/* Hero */}
      <div className="relative overflow-hidden pt-32 pb-20 px-6">
        {/* Background layers */}
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-rings" />
        <div className="absolute inset-0 hero-bg-vignette" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 hero-orb-1" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 hero-orb-2" />

        <div className="relative text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-[-0.03em]">
            Proxy in seconds,{' '}
            <span className="text-[var(--primary)]">not days.</span>
          </h1>
          <p className="text-[var(--muted)] text-lg max-w-xl mx-auto">
            Three steps between you and a working proxy. No sign-up, no waiting,
            no complexity.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
            <Link
              href="/order"
              className="min-w-[200px] px-8 py-4 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold text-center transition-all duration-200"
            >
              Order Now
            </Link>
            <Link
              href="/products"
              className="min-w-[200px] px-8 py-4 rounded-xl border border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] text-[var(--foreground)] font-semibold text-center card-depth transition-all duration-200"
            >
              View Products
            </Link>
          </div>
        </div>
      </div>

      {/* Steps */}
      <div className="relative max-w-5xl mx-auto px-6 pb-20">
        <div className="relative">
          {/* Connecting line */}
          <div className="hidden md:block absolute left-[60px] top-12 bottom-12 w-px bg-[var(--border)]" />

          <div className="space-y-16">
            {steps.map((step, i) => (
              <div
                key={step.number}
                className={`flex flex-col md:flex-row gap-8 items-start ${
                  i % 2 === 1 ? 'md:flex-row-reverse' : ''
                }`}
              >
                {/* Step number + icon */}
                <div className="flex-shrink-0 w-24 flex flex-col items-center gap-3">
                  <div className="w-14 h-14 rounded-full bg-[var(--primary)] flex items-center justify-center">
                    <span className="text-black font-bold text-lg">{step.number}</span>
                  </div>
                  {/* Connector dot */}
                  <div className="w-2.5 h-2.5 rounded-full bg-[var(--primary)]" />
                </div>

                {/* Content */}
                <div className="flex-1">
                  <h2 className="text-2xl md:text-3xl font-bold mb-3 tracking-[-0.02em]">
                    {step.title}
                  </h2>
                  <p className="text-[var(--muted)] mb-5 leading-relaxed max-w-xl">
                    {step.description}
                  </p>
                  <div className="flex flex-wrap gap-2 mb-6">
                    {step.details.map((d) => (
                      <span
                        key={d}
                        className="text-xs px-3 py-1.5 bg-[var(--surface)] border border-[var(--border)] rounded-full text-[var(--muted)]"
                      >
                        {d}
                      </span>
                    ))}
                  </div>
                  <Link
                    href={step.ctaHref}
                    className="inline-block text-sm font-semibold text-[var(--primary)] hover:underline"
                  >
                    {step.cta} →
                  </Link>
                </div>

                {/* Visual placeholder — different icon per step */}
                <div className="hidden md:flex flex-shrink-0 w-48 h-36 bg-[var(--surface)] border border-[var(--border)] rounded-2xl items-center justify-center">
                  {i === 0 ? (
                    <svg className="w-16 h-16 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9 9 0 100-18 9 9 0 000 18z"/><path strokeLinecap="round" strokeLinejoin="round" d="M3.6 9h16.8M3.6 15h16.8M12 3a15.3 15.3 0 014 9 15.3 15.3 0 01-4 9 15.3 15.3 0 01-4-9 15.3 15.3 0 014-9z"/>
                    </svg>
                  ) : i === 1 ? (
                    <svg className="w-16 h-16 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z"/>
                    </svg>
                  ) : (
                    <svg className="w-16 h-16 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z"/>
                    </svg>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Features grid */}
      <div className="bg-[var(--surface)] py-20 px-6">
        <div className="max-w-5xl mx-auto">
          {/* divider */}
          <div className="section-divider-glow mb-12" />
          <h2 className="text-3xl font-bold mb-10 text-center tracking-[-0.02em]">
            Everything you need
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="p-6 bg-[var(--background)] border border-[var(--border)] rounded-xl hover:border-[var(--primary)] transition-all duration-200 card-depth"
              >
                <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] mb-4">
                  {f.icon}
                </div>
                <h3 className="font-semibold mb-2">{f.title}</h3>
                <p className="text-[var(--muted)] text-sm leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="py-20 px-6 text-center">
        <h2 className="text-3xl font-bold mb-4 tracking-[-0.02em]">
          Ready to get started?
        </h2>
        <p className="text-[var(--muted)] mb-8">
          Proxies delivered in under 30 seconds.
        </p>
        <Link
          href="/order"
          className="inline-block min-w-[200px] px-8 py-4 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold text-center transition-all duration-200"
        >
          Order Now →
        </Link>
      </div>
    </main>
  );
}
