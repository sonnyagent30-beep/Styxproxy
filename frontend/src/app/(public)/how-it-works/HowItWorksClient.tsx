'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { Lightning, Lock, ArrowsClockwise, ChartBar, Headset, ShieldCheck, Globe, CreditCard, Rocket } from '@phosphor-icons/react';

const steps = [
  {
    number: '01',
    title: 'Pick your proxy',
    description:
      'Choose from ISP, Residential, Mobile 4G, or Datacenter proxies. Select your country and plan. Pay securely with card, bank transfer, USSD, or QR code.',
    details: ['ISP · Residential · Mobile · DC', 'Country-level targeting', 'Instant activation'],
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

const stepVisuals = [Globe, CreditCard, Rocket];

export default function HowItWorksClient() {
  // Scroll-reveal observer — same pattern as PricingClient / products
  useEffect(() => {
    const revealEls = document.querySelectorAll('.reveal');
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.05, rootMargin: '0px 0px -10% 0px' }
    );
    revealEls.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <main className="min-h-screen text-[var(--foreground)]">
      {/* Hero Section */}
      <div className="relative overflow-hidden pt-12 pb-16 px-6">
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-rings" />
        <div className="absolute inset-0 hero-bg-vignette" />
        <div className="hero-orb hero-orb-1" />
        <div className="hero-orb hero-orb-2" />
        <div className="hero-orb hero-orb-3" />

        <div className="relative text-center max-w-3xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[var(--primary)]/30 bg-[var(--primary)]/5 mb-6 mx-auto">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] shadow-[0_0_8px_var(--primary)] animate-pulse" />
            <span className="text-xs font-medium tracking-widest uppercase text-[var(--muted)]">
              How It Works
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight mb-6">
            Proxy in seconds,<br />
            <span className="text-[var(--primary)]">not days.</span>
          </h1>
          <p className="text-lg max-w-xl mx-auto leading-relaxed text-[var(--muted)]">
            Three steps between you and a working proxy. No sign-up, no waiting,
            no complexity.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
            <Link
              href="/order"
              className="min-w-[200px] px-8 py-4 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold text-center transition-all duration-200 hover:shadow-[0_0_40px_rgba(10,210,90,0.35)]"
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

      {/* Scroll indicator */}
      <div className="flex flex-col items-center gap-2 py-8">
        <span className="text-[10px] tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">Scroll</span>
        <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
      </div>

      {/* Steps */}
      <div className="relative max-w-6xl mx-auto px-6 pb-20">
        <div className="relative">
          {/* Connecting line */}
          <div className="hidden md:block absolute left-[60px] top-12 bottom-12 w-px bg-[var(--border)]" />

          <div className="space-y-16">
            {steps.map((step, i) => {
              const Visual = stepVisuals[i];
              return (
                <div
                  key={step.number}
                  className={`reveal flex flex-col md:flex-row gap-8 items-start ${
                    i % 2 === 1 ? 'md:flex-row-reverse' : ''
                  }`}
                >
                  {/* Step number + connector */}
                  <div className="flex-shrink-0 w-24 flex flex-col items-center gap-3">
                    <div className="w-14 h-14 rounded-full bg-[var(--primary)] flex items-center justify-center shadow-[0_0_24px_rgba(10,210,90,0.3)]">
                      <span className="text-black font-black text-lg">{step.number}</span>
                    </div>
                    <div className="w-2.5 h-2.5 rounded-full bg-[var(--primary)]" />
                  </div>

                  {/* Content */}
                  <div className="flex-1">
                    <h2 className="text-2xl sm:text-3xl lg:text-4xl font-black mb-3 tracking-tight">
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

                  {/* Visual */}
                  <div className="hidden md:flex flex-shrink-0 w-48 h-36 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth items-center justify-center">
                    <Visual className="w-16 h-16 text-[var(--primary)]" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Features grid */}
      <div className="max-w-6xl mx-auto px-6 pb-16">
        <div className="section-divider-glow mb-12" />
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black mb-10 text-center tracking-tight">
          Everything you need
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => (
            <div
              key={f.title}
              className="reveal p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth hover:border-[var(--primary)] transition-all duration-200"
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

      {/* CTA */}
      <div className="max-w-3xl mx-auto text-center px-6 pb-32">
        <div className="section-divider-glow mb-16" />
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight mb-5">
          Ready to cross the Styx?
        </h2>
        <p className="mb-10 text-lg text-[var(--muted)]">
          Proxies delivered in under 30 seconds. No signup required.
        </p>
        <Link
          href="/order"
          className="inline-block px-12 py-5 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-black text-lg transition-all duration-200 hover:shadow-[0_0_40px_rgba(10,210,90,0.35)]"
        >
          Get Instant
        </Link>
      </div>
    </main>
  );
}
