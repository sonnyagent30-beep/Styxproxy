import { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Pricing | Styxproxy',
  description: 'Transparent pricing for ISP, Residential, Mobile 4G & Datacenter proxies. No hidden fees.',
};

const plans = [
  {
    category: 'ISP Proxies',
    icon: '🌐',
    color: 'bg-[#0AD25A]',
    plans: [
      { name: 'United Kingdom', price: '₦6,500', period: '/mo', flag: '🇬🇧' },
      { name: 'United States', price: '₦6,500', period: '/mo', flag: '🇺🇸' },
      { name: 'Germany', price: '₦6,500', period: '/mo', flag: '🇩🇪' },
      { name: 'France', price: '₦6,500', period: '/mo', flag: '🇫🇷' },
      { name: 'Canada', price: '₦6,500', period: '/mo', flag: '🇨🇦' },
      { name: 'Japan', price: '₦7,500', period: '/mo', flag: '🇯🇵' },
      { name: 'Australia', price: '₦7,500', period: '/mo', flag: '🇦🇺' },
      { name: 'Brazil', price: '₦7,500', period: '/mo', flag: '🇧🇷' },
      { name: 'Singapore', price: '₦7,500', period: '/mo', flag: '🇸🇬' },
    ],
  },
  {
    category: 'Residential',
    icon: '🏠',
    color: 'bg-[#0AD25A]',
    plans: [
      { name: 'Global 5GB Data', price: '₦5,000', period: '/mo', flag: '🌍' },
      { name: 'Global 10GB Data', price: '₦9,000', period: '/mo', flag: '🌍' },
    ],
  },
  {
    category: 'Mobile 4G',
    icon: '📱',
    color: 'bg-[#0AD25A]',
    plans: [
      { name: 'Global 5GB 4G Data', price: '₦20,000', period: '/mo', flag: '🌍' },
      { name: 'Global 10GB 4G Data', price: '₦35,000', period: '/mo', flag: '🌍' },
    ],
  },
  {
    category: 'Datacenter',
    icon: '🖥️',
    color: 'bg-[#0AD25A]',
    plans: [
      { name: 'Global Datacenter Proxy', price: '₦2,500', period: '/mo', flag: '🌍' },
    ],
  },
];

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      {/* Header */}
      <div className="pt-32 pb-16 px-6 text-center">
        <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-[-0.03em]">
          Simple, transparent pricing.
        </h1>
        <p className="text-[var(--muted)] text-lg max-w-xl mx-auto">
          No hidden fees. No surprises. Pay for what you need.
        </p>
      </div>

      {/* Comparison banner */}
      <div className="max-w-6xl mx-auto px-6 mb-12">
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 md:p-8">
          <h2 className="text-lg font-semibold mb-6 text-center">Proxy type comparison</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { type: 'ISP Proxies', speed: 'High', detection: 'Low', anonymity: 'High', reliability: 'High', price: '₦6,500' },
              { type: 'Residential', speed: 'Medium', detection: 'Very Low', anonymity: 'Very High', reliability: 'High', price: '₦5,000' },
              { type: 'Mobile 4G', speed: 'Medium', detection: 'Extremely Low', anonymity: 'Highest', reliability: 'Medium', price: '₦20,000' },
              { type: 'Datacenter', speed: 'High', detection: 'High', anonymity: 'Low', reliability: 'High', price: '₦2,500' },
            ].map((row) => (
              <div key={row.type} className="space-y-3">
                <h3 className="font-semibold text-sm">{row.type}</h3>
                <div>
                  <div className="flex justify-between text-xs text-[var(--muted)] mb-1">
                    <span>Speed</span>
                  </div>
                  <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${row.speed === 'High' ? 'w-[85%]' : row.speed === 'Medium' ? 'w-[55%]' : 'w-[40%]'} bg-[#0AD25A]`} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-[var(--muted)] mb-1">
                    <span>Detection Risk</span>
                  </div>
                  <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${row.detection === 'Very Low' || row.detection === 'Extremely Low' ? 'w-[15%]' : row.detection === 'Low' ? 'w-[30%]' : 'w-[80%]'} bg-[#0AD25A]`} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-[var(--muted)] mb-1">
                    <span>Anonymity</span>
                  </div>
                  <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${row.anonymity === 'Highest' ? 'w-[95%]' : row.anonymity === 'Very High' ? 'w-[80%]' : row.anonymity === 'High' ? 'w-[70%]' : 'w-[25%]'} bg-[#0AD25A]`} />
                  </div>
                </div>
                <div className="pt-2 border-t border-[var(--border)]">
                  <span className="text-[#0AD25A] font-bold text-sm">{row.price}</span>
                  <span className="text-[var(--muted)] text-xs">/mo</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Plans by category */}
      <div className="max-w-6xl mx-auto px-6 pb-20 space-y-16">
        {plans.map((section) => (
          <div key={section.category}>
            <div className="flex items-center gap-3 mb-6">
              <span className="text-2xl">{section.icon}</span>
              <h2 className="text-2xl font-bold tracking-[-0.02em]">{section.category}</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {section.plans.map((plan) => (
                <div
                  key={plan.name}
                  className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5 hover:border-[#0AD25A]/40 transition-colors duration-200"
                >
                  <div className="flex items-start justify-between mb-3">
                    <span className="text-2xl">{plan.flag}</span>
                    <span className="text-[#0AD25A] font-bold text-lg">{plan.price}</span>
                  </div>
                  <p className="font-medium mb-1">{plan.name}</p>
                  <p className="text-[var(--muted)] text-sm">per month · auto-renews</p>
                  <Link
                    href="/order"
                    className="mt-4 block w-full py-2.5 px-4 bg-[#0AD25A] text-[#0a0a0a] font-semibold text-sm rounded-lg text-center hover:bg-[#22FF7A] transition-colors duration-200"
                  >
                    Order Now →
                  </Link>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* FAQ */}
        <div className="pt-8">
          <h2 className="text-2xl font-bold mb-6 text-center tracking-[-0.02em]">
            Common questions
          </h2>
          <div className="max-w-2xl mx-auto space-y-3">
            {[
              {
                q: 'How fast is delivery?',
                a: 'Credentials are delivered instantly after payment confirmation — usually within 30 seconds.',
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
            ].map((faq) => (
              <div key={faq.q} className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5">
                <h3 className="font-semibold mb-2">{faq.q}</h3>
                <p className="text-[var(--muted)] text-sm">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center pt-8">
          <p className="text-[var(--muted)] mb-4">Need something custom?</p>
          <Link href="/contact" className="inline-block py-3 px-8 border border-[#0AD25A] text-[#0AD25A] rounded-lg font-semibold hover:bg-[#0AD25A] hover:text-[#0a0a0a] transition-colors duration-200">
            Contact us for bulk pricing
          </Link>
        </div>
      </div>
    </main>
  );
}
