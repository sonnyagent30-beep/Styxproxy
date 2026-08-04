'use client';

import Link from 'next/link';
import { Check, Broadcast, House, DeviceMobile, HardDrives } from '@phosphor-icons/react';

const plans = [
  {
    category: 'ISP Proxies',
    planType: 'isp',
    plans: [
      { name: 'United Kingdom', price: '₦6,500', period: '/mo', flag: 'GB' },
      { name: 'United States', price: '₦6,500', period: '/mo', flag: 'US' },
      { name: 'Germany', price: '₦6,500', period: '/mo', flag: 'DE' },
      { name: 'France', price: '₦6,500', period: '/mo', flag: 'FR' },
      { name: 'Canada', price: '₦6,500', period: '/mo', flag: 'CA' },
      { name: 'Japan', price: '₦7,500', period: '/mo', flag: 'JP' },
      { name: 'Australia', price: '₦7,500', period: '/mo', flag: 'AU' },
      { name: 'Brazil', price: '₦7,500', period: '/mo', flag: 'BR' },
      { name: 'Singapore', price: '₦7,500', period: '/mo', flag: 'SG' },
    ],
  },
  {
    category: 'Residential',
    planType: 'residential',
    plans: [
      { name: 'Global 5GB Data', price: '₦5,000', period: '/mo', flag: 'GL' },
      { name: 'Global 10GB Data', price: '₦9,000', period: '/mo', flag: 'GL' },
    ],
  },
  {
    category: 'Mobile 4G',
    planType: 'mobile',
    plans: [
      { name: 'Global 5GB 4G Data', price: '₦20,000', period: '/mo', flag: 'GL' },
      { name: 'Global 10GB 4G Data', price: '₦35,000', period: '/mo', flag: 'GL' },
    ],
  },
  {
    category: 'Datacenter',
    planType: 'datacenter',
    plans: [
      { name: 'Global Datacenter Proxy', price: '₦2,500', period: '/mo', flag: 'GL' },
    ],
  },
];

const comparison = [
  { type: 'ISP Proxies', speed: 'High', detection: 'Low', anonymity: 'High', reliability: 'High', price: '₦6,500' },
  { type: 'Residential', speed: 'Medium', detection: 'Very Low', anonymity: 'Very High', reliability: 'High', price: '₦5,000' },
  { type: 'Mobile 4G', speed: 'Medium', detection: 'Extremely Low', anonymity: 'Highest', reliability: 'Medium', price: '₦20,000' },
  { type: 'Datacenter', speed: 'High', detection: 'High', anonymity: 'Low', reliability: 'High', price: '₦2,500' },
];

const faqs = [
  {
    q: 'How fast is delivery?',
    a: 'Credentials are delivered instantly after payment confirmation. Usually within 30 seconds.',
  },
  {
    q: 'What payment methods do you accept?',
    a: 'Card, Bank Transfer, USSD, and QR code via Flutterwave. All major Nigerian banks supported.',
  },
  {
    q: 'Can I get a refund?',
    a: 'Yes. If your proxy is banned within the first 24 hours and our team cannot replace it, you get a full refund.',
  },
  {
    q: 'What is your ban replacement policy?',
    a: 'We replace banned ISP and Residential proxies at no cost within your subscription period. Mobile 4G proxies are covered for the first 7 days.',
  },
];

function Flag({ code }: { code: string }) {
  const flags: Record<string, string> = {
    GB: '🇬🇧', US: '🇺🇸', DE: '🇩🇪', FR: '🇫🇷', CA: '🇨🇦',
    JP: '🇯🇵', AU: '🇦🇺', BR: '🇧🇷', SG: '🇸🇬', GL: '🌍',
  };
  return <span>{flags[code] || '🌍'}</span>;
}

export default function PricingClient() {
  return (
    <main className="min-h-screen text-[var(--foreground)]">
      {/* Header */}
      <div className="relative overflow-hidden pt-32 pb-16 px-6">
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-rings" />
        <div className="absolute inset-0 hero-bg-vignette" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 hero-orb-1" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 hero-orb-2" />

        <div className="relative text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-[-0.03em]">
            Simple, transparent pricing.
          </h1>
          <p className="text-[var(--muted)] text-lg max-w-xl mx-auto">
            No hidden fees. No surprises. Pay for what you need.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
            <Link href="/order" className="min-w-[200px] px-8 py-4 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold text-center transition-all duration-200">
              Order Now
            </Link>
            <Link href="/how-it-works" className="min-w-[200px] px-8 py-4 rounded-xl border border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] text-[var(--foreground)] font-semibold text-center card-depth transition-all duration-200">
              How It Works
            </Link>
          </div>
        </div>
      </div>

      {/* Comparison banner */}
      <div className="relative max-w-6xl mx-auto px-6 mb-12">
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 md:p-8 card-depth">
          <h2 className="text-lg font-semibold mb-6 text-center">Proxy type comparison</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {comparison.map((row) => (
              <div key={row.type} className="space-y-3">
                <h3 className="font-semibold text-sm">{row.type}</h3>
                <div>
                  <div className="flex justify-between text-xs text-[var(--muted)] mb-1">
                    <span>Speed</span>
                  </div>
                  <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${row.speed === 'High' ? 'w-[85%]' : 'w-[55%]'} bg-[var(--primary)]`} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-[var(--muted)] mb-1">
                    <span>Detection Risk</span>
                  </div>
                  <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${row.detection === 'Very Low' || row.detection === 'Extremely Low' ? 'w-[15%]' : row.detection === 'Low' ? 'w-[30%]' : 'w-[80%]'} bg-[var(--primary)]`} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-[var(--muted)] mb-1">
                    <span>Anonymity</span>
                  </div>
                  <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${row.anonymity === 'Highest' ? 'w-[95%]' : row.anonymity === 'Very High' ? 'w-[80%]' : row.anonymity === 'High' ? 'w-[70%]' : 'w-[25%]'} bg-[var(--primary)]`} />
                  </div>
                </div>
                <div className="pt-2 border-t border-[var(--border)]">
                  <span className="text-[var(--primary)] font-bold text-sm">{row.price}</span>
                  <span className="text-[var(--muted)] text-xs">/mo</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Plans by category */}
      <div className="relative max-w-6xl mx-auto px-6 pb-20 space-y-16">
        {plans.map((section) => (
          <div key={section.category}>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)]">
                {section.planType === 'isp' ? (
                  <Broadcast size={20} />
                ) : section.planType === 'residential' ? (
                  <House size={20} />
                ) : section.planType === 'mobile' ? (
                  <DeviceMobile size={20} />
                ) : (
                  <HardDrives size={20} />
                )}
              </div>
              <h2 className="text-2xl font-bold tracking-[-0.02em]">{section.category}</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {section.plans.map((plan) => (
                <div
                  key={plan.name}
                  className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5 hover:border-[var(--primary)] transition-all duration-200 card-depth"
                >
                  <div className="flex items-start justify-between mb-3">
                    <span className="text-2xl"><Flag code={plan.flag} /></span>
                    <span className="text-[var(--primary)] font-bold text-lg">{plan.price}</span>
                  </div>
                  <p className="font-medium mb-1">{plan.name}</p>
                  <p className="text-[var(--muted)] text-sm">per month. Auto-renews.</p>
                  <Link
                    href="/order"
                    className="mt-4 block w-full py-2.5 px-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold text-sm rounded-lg text-center transition-all duration-200"
                  >
                    Order Now →
                  </Link>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* divider */}
        <div className="section-divider-glow" />

        {/* FAQ */}
        <div className="pt-8">
          <h2 className="text-2xl font-bold mb-6 text-center tracking-[-0.02em]">
            Common questions
          </h2>
          <div className="max-w-2xl mx-auto space-y-3">
            {faqs.map((faq) => (
              <div key={faq.q} className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5 card-depth">
                <h3 className="font-semibold mb-2">{faq.q}</h3>
                <p className="text-[var(--muted)] text-sm">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>

        {/* divider */}
        <div className="section-divider-glow mt-16" />

        {/* CTA */}
        <div className="text-center pt-8">
          <p className="text-[var(--muted)] mb-4">Need something custom?</p>
          <Link href="/contact" className="inline-block min-w-[200px] py-3 px-8 border border-[var(--primary)] text-[var(--primary)] rounded-xl font-semibold hover:bg-[var(--primary)] hover:text-black transition-all duration-200 text-center">
            Contact us for bulk pricing
          </Link>
        </div>
      </div>
    </main>
  );
}
