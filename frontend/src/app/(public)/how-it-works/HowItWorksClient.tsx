'use client';

import Link from 'next/link';
import { Lightning, Lock, ArrowsClockwise, ChartBar, Headset, ShieldCheck, Globe, CreditCard, Rocket } from '@phosphor-icons/react';

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
    icon: <Lightning className="w-6 h-6" />,
  },
  {
    title: 'Private and secure',
    description: 'Every proxy is tested before delivery. No shared credentials. Your access is exclusive.',
    icon: <Lock className="w-6 h-6" />,
  },
  {
    title: 'Easy rotation',
    description: 'Rotate IPs instantly via dashboard or API. Dante-based credential rotation means zero downtime.',
    icon: <ArrowsClockwise className="w-6 h-6" />,
  },
  {
    title: 'Real-time monitoring',
    description: 'Track usage, view bandwidth, and manage all your proxies from a single dashboard.',
    icon: <ChartBar className="w-6 h-6" />,
  },
  {
    title: 'Human support',
    description: 'Talk to a real person via WhatsApp, Telegram, or email. No bots, no ticket queues.',
    icon: <Headset className="w-6 h-6" />,
  },
  {
    title: 'Ban replacement',
    description: 'Banned proxy? We replace it at no cost. Covered for ISP and Residential within your billing period.',
    icon: <ShieldCheck className="w-6 h-6" />,
  },
];

export default function HowItWorksClient() {
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
                    <Globe className="w-16 h-16 text-[var(--primary)]" />
                  ) : i === 1 ? (
                    <CreditCard className="w-16 h-16 text-[var(--primary)]" />
                  ) : (
                    <Rocket className="w-16 h-16 text-[var(--primary)]" />
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
