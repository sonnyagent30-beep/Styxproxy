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
    cta: 'View products →',
    ctaHref: '/products',
  },
  {
    number: '02',
    title: 'Pay & get credentials',
    description:
      'Complete payment via Flutterwave. Your proxy credentials are delivered instantly to your dashboard, email, WhatsApp, and Telegram — all in under 30 seconds.',
    details: ['Instant delivery', 'WhatsApp + Telegram + Email', 'No account required'],
    cta: 'Start ordering →',
    ctaHref: '/order',
  },
  {
    number: '03',
    title: 'Use immediately',
    description:
      'Connect using HTTP/SOCKS5 in any browser, bot, or application. Rotate IPs, manage credentials, and monitor usage from your dashboard.',
    details: ['HTTP/SOCKS5 support', 'Rotate IPs on demand', 'Dashboard management'],
    cta: 'Order now →',
    ctaHref: '/order',
  },
];

const features = [
  {
    icon: '⚡',
    title: 'Instant delivery',
    description: 'Credentials delivered within 30 seconds of payment. No waiting, no manual activation.',
  },
  {
    icon: '🔒',
    title: 'Private & secure',
    description: 'Every proxy is tested before delivery. No shared credentials. Your access is exclusive.',
  },
  {
    icon: '🔄',
    title: 'Easy rotation',
    description: 'Rotate IPs instantly via dashboard or API. Dante-based credential rotation means zero downtime.',
  },
  {
    icon: '📊',
    title: 'Real-time monitoring',
    description: 'Track usage, view bandwidth, and manage all your proxies from a single dashboard.',
  },
  {
    icon: '💬',
    title: 'Human support',
    description: 'Talk to a real person via WhatsApp, Telegram, or email. No bots, no ticket queues.',
  },
  {
    icon: '🛡️',
    title: 'Ban replacement',
    description: 'Banned proxy? We replace it at no cost. Covered for ISP and Residential within your billing period.',
  },
];

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      {/* Hero */}
      <div className="pt-32 pb-20 px-6 text-center">
        <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-[-0.03em]">
          Proxy in seconds,{' '}
          <span className="text-[#0AD25A]">not days.</span>
        </h1>
        <p className="text-[var(--muted)] text-lg max-w-xl mx-auto">
          Three steps between you and a working proxy. No sign-up, no waiting,
          no complexity.
        </p>
        <div className="flex items-center justify-center gap-4 mt-8">
          <Link
            href="/order"
            className="py-3 px-8 bg-[#0AD25A] text-[#0a0a0a] font-semibold rounded-lg hover:bg-[#22FF7A] transition-colors duration-200"
          >
            Order Now
          </Link>
          <Link
            href="/products"
            className="py-3 px-8 border border-[var(--border)] rounded-lg hover:border-[#0AD25A] transition-colors duration-200"
          >
            View Products
          </Link>
        </div>
      </div>

      {/* Steps */}
      <div className="max-w-5xl mx-auto px-6 pb-20">
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
                  <div className="w-14 h-14 rounded-full bg-[#0AD25A] flex items-center justify-center">
                    <span className="text-[#0a0a0a] font-bold text-lg">{step.number}</span>
                  </div>
                  {/* Connector dot */}
                  <div className="w-2.5 h-2.5 rounded-full bg-[#0AD25A]" />
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
                    className="inline-block text-sm font-semibold text-[#0AD25A] hover:underline"
                  >
                    {step.cta}
                  </Link>
                </div>

                {/* Visual placeholder — different illustration per step */}
                <div className="hidden md:flex flex-shrink-0 w-48 h-36 bg-[var(--surface)] border border-[var(--border)] rounded-2xl items-center justify-center">
                  <span className="text-5xl">
                    {i === 0 ? '🌐' : i === 1 ? '💳' : '🚀'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Features grid */}
      <div className="bg-[var(--surface)] py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold mb-10 text-center tracking-[-0.02em]">
            Everything you need
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="p-6 bg-[var(--background)] border border-[var(--border)] rounded-xl hover:border-[#0AD25A]/30 transition-colors duration-200"
              >
                <span className="text-3xl mb-4 block">{f.icon}</span>
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
          className="inline-block py-3 px-8 bg-[#0AD25A] text-[#0a0a0a] font-semibold rounded-lg hover:bg-[#22FF7A] transition-colors duration-200"
        >
          Order Now →
        </Link>
      </div>
    </main>
  );
}
