'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { ArrowRight, ArrowUpRight } from '@phosphor-icons/react';

const steps = [
  {
    number: 1,
    title: 'Choose your proxy',
    description:
      'Select from ISP, Residential, Mobile 4G, or Datacenter proxies. Target specific countries, cities, or carriers.',
    features: ['ISP · Residential · Mobile 4G · Datacenter', 'Country and city-level targeting', 'Instant activation'],
    href: '/products',
    cta: 'View products',
  },
  {
    number: 2,
    title: 'Pay securely',
    description:
      'Complete payment via Flutterwave, Paystack, or card. Your proxy credentials are delivered instantly — to your email, WhatsApp, and Telegram.',
    features: ['Delivery within 30 seconds', 'Multiple payment channels', 'No account required'],
    href: '/order',
    cta: 'Start ordering',
  },
  {
    number: 3,
    title: 'Connect and use',
    description:
      'Use HTTP or SOCKS5 in any browser, bot, or application. Rotate IPs, monitor usage, and manage everything from your dashboard.',
    features: ['HTTP and SOCKS5 support', 'On-demand IP rotation', 'Real-time dashboard'],
    href: '/order',
    cta: 'Order now',
  },
];

const features = [
  {
    title: 'Instant delivery',
    description: 'Credentials arrive within 30 seconds of payment confirmation. No manual activation, no waiting.',
  },
  {
    title: 'Exclusive access',
    description: 'Every proxy is tested before delivery. Your credentials are never shared with another customer.',
  },
  {
    title: 'Flexible rotation',
    description: 'Rotate IPs instantly via dashboard or API. Automated rotation means zero interruption to your workflow.',
  },
  {
    title: 'Usage monitoring',
    description: 'Track bandwidth, view active proxies, and manage your entire inventory from a single dashboard.',
  },
  {
    title: 'Human support',
    description: 'Reach a real person via WhatsApp, Telegram, or email. No ticket queues, no automated responses.',
  },
  {
    title: 'Free replacements',
    description: 'Banned proxy? We replace it at no cost within your billing period for ISP and Residential plans.',
  },
];

function AnimatedSection({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 },
    );

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="transition-all duration-700 ease-out"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(24px)',
        transitionDelay: `${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

export default function HowItWorksClient() {
  return (
    <main className="min-h-screen text-[var(--foreground)]">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-vignette" />

        <div className="relative max-w-4xl mx-auto px-6 pt-24 pb-20 text-center">
          <h1
            className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.1]"
            style={{ letterSpacing: '-0.03em' }}
          >
            Proxy in seconds,
            <br />
            <span className="text-[var(--primary)]">not days.</span>
          </h1>
          <p
            className="mt-6 text-lg max-w-xl mx-auto leading-relaxed text-[var(--muted)]"
          >
            Three steps between you and a working proxy. No sign-up, no waiting, no complexity.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-10">
            <Link
              href="/order"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold transition-all duration-200 hover:shadow-[0_0_40px_rgba(10,210,90,0.35)]"
            >
              Order now
              <ArrowRight weight="bold" className="w-4 h-4" />
            </Link>
            <Link
              href="/products"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl border border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] text-[var(--foreground)] font-semibold transition-all duration-200"
            >
              Compare proxy types
              <ArrowUpRight weight="bold" className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Steps */}
      <section className="max-w-5xl mx-auto px-6 pb-28">
        <div className="space-y-20">
          {steps.map((step, i) => (
            <AnimatedSection key={step.number} delay={i * 100}>
              <div className="grid md:grid-cols-[80px_1fr] gap-6 md:gap-10">
                {/* Step number */}
                <div className="flex md:flex-col items-center md:items-start gap-4">
                  <div
                    className="w-16 h-16 rounded-2xl flex items-center justify-center flex-shrink-0"
                    style={{
                      background: 'rgba(10, 210, 90, 0.08)',
                      border: '1px solid rgba(10, 210, 90, 0.2)',
                    }}
                  >
                    <span className="text-2xl font-bold text-[var(--primary)]">{step.number}</span>
                  </div>
                </div>

                {/* Content */}
                <div>
                  <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-4">
                    {step.title}
                  </h2>
                  <p className="text-[var(--muted)] leading-relaxed max-w-xl mb-6">
                    {step.description}
                  </p>

                  <div className="flex flex-wrap gap-2 mb-6">
                    {step.features.map((feature) => (
                      <span
                        key={feature}
                        className="text-xs px-3 py-1.5 rounded-full border"
                        style={{
                          background: 'var(--surface)',
                          borderColor: 'var(--border)',
                          color: 'var(--muted)',
                        }}
                      >
                        {feature}
                      </span>
                    ))}
                  </div>

                  <Link
                    href={step.href}
                    className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--primary)] hover:underline underline-offset-4"
                  >
                    {step.cta}
                    <ArrowRight weight="bold" className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </AnimatedSection>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 pb-28">
        <AnimatedSection>
          <div className="max-w-xl mb-14">
            <h2
              className="text-3xl sm:text-4xl font-bold tracking-tight"
              style={{ letterSpacing: '-0.02em' }}
            >
              Everything you need
            </h2>
            <p className="mt-4 text-[var(--muted)] leading-relaxed">
              Built for professionals who need reliable, fast, and flexible proxy access.
            </p>
          </div>
        </AnimatedSection>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feature, i) => (
            <AnimatedSection key={feature.title} delay={i * 60}>
              <div
                className="p-6 rounded-2xl h-full transition-all duration-200 hover:border-[var(--primary)]"
                style={{
                  background: 'var(--card)',
                  border: '1px solid var(--border)',
                }}
              >
                <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
                <p className="text-[var(--muted)] text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </AnimatedSection>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 pb-32 text-center">
        <AnimatedSection>
          <h2
            className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight mb-5"
            style={{ letterSpacing: '-0.02em' }}
          >
            Ready to get started?
          </h2>
          <p className="text-lg text-[var(--muted)] mb-10 leading-relaxed">
            Proxies delivered in under 30 seconds. No signup required.
          </p>
          <Link
            href="/order"
            className="inline-flex items-center gap-2 px-10 py-5 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-bold text-lg transition-all duration-200 hover:shadow-[0_0_40px_rgba(10,210,90,0.35)]"
          >
            Order now
            <ArrowRight weight="bold" className="w-5 h-5" />
          </Link>
        </AnimatedSection>
      </section>
    </main>
  );
}
