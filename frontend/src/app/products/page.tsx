'use client';

import { useState } from 'react';
import Link from 'next/link';
import { products, formatPrice, COUNTRIES, type CountryInfo } from '@/lib/products';

import GlobeMap from '@/components/GlobeMap';

// Country lists per product type — drives both the category cards AND the globe
const PRODUCT_COUNTRIES: Record<string, string[]> = {
  ISP:         ['UK', 'US', 'DE', 'FR', 'CA', 'JP', 'AU', 'BR', 'SG'],
  RESIDENTIAL: ['US', 'UK', 'DE', 'FR', 'CA', 'JP', 'AU', 'BR', 'IT', 'ES', 'NL', 'IN', 'MX', 'AR'],
  MOBILE:      ['US', 'UK', 'DE', 'FR', 'CA', 'JP', 'AU', 'BR', 'IT', 'ES'],
  DC:          ['US', 'UK', 'DE', 'NL', 'JP', 'SG', 'AU', 'CA', 'FR', 'IT', 'ES', 'BR', 'IN', 'AE', 'HK'],
};

const getCountries = (codes: string[]): CountryInfo[] => codes.map(c => COUNTRIES[c]).filter(Boolean);

// Category metadata — name, price, description, features. Countries are derived from PRODUCT_COUNTRIES.
const categories = [
  {
    key: 'ISP',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
      </svg>
    ),
    name: 'ISP Proxies',
    description: 'High-speed ISP IPs — ideal for web scraping and automation',
    price: '₦6,500/mo',
    features: [
      'Fast connection speeds',
      'Stable IP addresses',
      'Rotating & sticky options',
      'HTTP/SOCKS5 support',
    ],
  },
  {
    key: 'RESIDENTIAL',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
    name: 'Residential',
    description: 'Real residential IPs — harder to detect and block',
    price: 'From ₦5,000',
    features: [
      'Real home IP addresses',
      'Highest success rate',
      'Ideal for sneakers & ticketing',
      '30-day data window',
    ],
  },
  {
    key: 'MOBILE',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    ),
    name: 'Mobile 4G',
    description: 'Mobile carrier IPs — perfect for social media and ad verification',
    price: 'From ₦20,000',
    features: [
      'Carrier-grade IPs',
      'Maximum anonymity',
      'Best for social media',
      'Unlimited bandwidth',
    ],
  },
  {
    key: 'DC',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
      </svg>
    ),
    name: 'Datacenter',
    description: 'Fast datacenter proxies for general purpose use',
    price: '₦2,500/mo',
    features: [
      'Lightning fast speeds',
      'Cost-effective',
      'High concurrent requests',
      'Global locations',
    ],
  },
];

export default function ProductsPage() {
  // Active filter for the globe — null means "all countries from all products"
  const [activeProduct, setActiveProduct] = useState<string | null>(null);

  return (
    <div className="min-h-screen pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Globe + Headline Hero */}
        <div className="flex flex-col lg:flex-row items-center gap-8 mb-16">
          {/* Globe — filtered by selected product type */}
          <div className="w-full lg:w-1/2">
            <GlobeMap productType={activeProduct || 'ALL'} />
          </div>

          {/* Headline */}
          <div className="w-full lg:w-1/2 text-center lg:text-left">
            <h1 className="text-4xl sm:text-5xl font-bold mb-4 leading-tight" style={{ color: 'var(--foreground)' }}>
              Lightning-fast proxies,<br />
              <span style={{ color: 'var(--primary)' }}>built to scale.</span>
            </h1>
            <p className="text-base sm:text-lg mb-6" style={{ color: 'var(--muted)' }}>
              {activeProduct
                ? <>Showing coverage for <span className="font-medium" style={{ color: 'var(--foreground)' }}>{categories.find(c => c.key === activeProduct)?.name}</span> — click another card to switch.</>
                : <>ISP, Residential, Mobile 4G &amp; Datacenter proxies — available in <span className="font-medium" style={{ color: 'var(--foreground)' }}>18+ countries</span> worldwide.</>
              }
            </p>
            {/* Stats Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-8">
              {[
                { label: 'Uptime', value: '99.9%', icon: '🟢' },
                { label: 'IP Pool', value: '50K+ IPs', icon: '🌐' },
                { label: 'Speed', value: '1 Gbps', icon: '⚡' },
                { label: 'Delivery', value: 'Instant', icon: '🚀' },
              ].map(({ label, value, icon }) => (
                <div key={label} className="bg-[var(--card)] border border-[var(--border)] rounded-xl px-3 py-3 text-center">
                  <div className="text-base mb-0.5">{icon}</div>
                  <div className="text-xl font-bold" style={{ color: 'var(--primary)' }}>{value}</div>
                  <div className="text-xs text-[var(--muted)]">{label}</div>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap justify-center lg:justify-start gap-3">
              <Link
                href="/order"
                className="px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors min-w-[160px] text-center"
              >
                Get Instant Access
              </Link>
              <a
                href="https://t.me/buncheproxybot"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] font-medium rounded-xl transition-colors min-w-[160px] text-center"
                style={{ color: 'var(--foreground)' }}
              >
                Start via Telegram
              </a>
            </div>
          </div>
        </div>

        {/* Product Category Cards — clicking filters the globe */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
          {categories.map((category) => {
            const isActive = activeProduct === category.key;
            const countryList = getCountries(PRODUCT_COUNTRIES[category.key] || []);
            return (
              <button
                key={category.key}
                type="button"
                onClick={() => setActiveProduct(isActive ? null : category.key)}
                className={`text-left bg-[var(--card)] border rounded-2xl p-6 flex flex-col transition-all cursor-pointer ${
                  isActive
                    ? 'border-[var(--primary)] ring-2 ring-[var(--primary)]/30 shadow-lg'
                    : 'border-[var(--border)] hover:border-[var(--primary)]'
                }`}
              >
                {/* Icon */}
                <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] mb-4">
                  {category.icon}
                </div>

                {/* Name & Description */}
                <h3 className="text-lg font-bold mb-2">{category.name}</h3>
                <p className="text-sm text-[var(--muted)] mb-4">{category.description}</p>

                {/* Price */}
                <div className="text-lg font-semibold text-[var(--primary)] mb-4">
                  {category.price}
                </div>

                {/* Available countries — flag chips */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-[var(--muted)]">Available in:</span>
                    <span className="text-xs font-semibold text-[var(--primary)]">
                      {countryList.length} countries
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {countryList.map(c => (
                      <span
                        key={c.code}
                        title={c.name}
                        className="inline-flex items-center justify-center w-7 h-7 rounded-md bg-[var(--background)] border border-[var(--border)] text-base leading-none"
                      >
                        {c.flag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Features */}
                <ul className="space-y-2 mb-6 flex-1">
                  {category.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-[var(--muted)]">
                      <svg className="w-4 h-4 text-[var(--primary)] mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>

                {/* Action — either "View on globe" or "Order Now" */}
                <Link
                  href="/order"
                  onClick={(e) => e.stopPropagation()}
                  className="w-full px-4 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors text-center"
                >
                  {isActive ? '✓ Showing on globe' : 'Order Now →'}
                </Link>
              </button>
            );
          })}
        </div>

        {/* Comparison Cards — 3D style */}
        <div className="mb-20">
          <h2 className="text-2xl font-bold text-center mb-8">Compare Proxy Types</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* ISP Card */}
            <div className="group relative" style={{ perspective: '1000px' }}>
              <div className="relative bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 transition-all duration-300 group-hover:-translate-y-1 group-hover:shadow-xl" style={{ transformStyle: 'preserve-3d', '--tw-shadow-color': 'rgba(16,185,129,0.15)' } as React.CSSProperties}>
                <div className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl bg-[var(--primary)]" />
                <div className="text-3xl mb-3">🌐</div>
                <h3 className="text-lg font-bold mb-1">ISP Proxies</h3>
                <p className="text-sm text-[var(--muted)] mb-4">Fast &amp; stable datacenter-grade IPs</p>
                <div className="space-y-3">
                  {[
                    { label: 'Speed', value: 'High', bar: 90 },
                    { label: 'Detection', value: 'Low', bar: 30 },
                    { label: 'Anonymity', value: 'High', bar: 75 },
                    { label: 'Reliability', value: 'High', bar: 85 },
                  ].map(({ label, value, bar }) => (
                    <div key={label}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[var(--muted)]">{label}</span>
                        <span className="font-medium">{value}</span>
                      </div>
                      <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-[var(--primary)] transition-all" style={{ width: `${bar}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-5 pt-4 border-t border-[var(--border)]">
                  <p className="text-xs text-[var(--muted)] mb-1">From</p>
                  <p className="text-xl font-bold" style={{ color: 'var(--primary)' }}>₦6,500<span className="text-xs font-normal text-[var(--muted)]">/mo</span></p>
                </div>
              </div>
            </div>

            {/* Residential Card */}
            <div className="group relative" style={{ perspective: '1000px' }}>
              <div className="relative bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 transition-all duration-300 group-hover:-translate-y-1 group-hover:shadow-xl" style={{ transformStyle: 'preserve-3d', '--tw-shadow-color': 'rgba(16,185,129,0.15)' } as React.CSSProperties}>
                <div className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl bg-[var(--primary)]" />
                <div className="text-3xl mb-3">🏠</div>
                <h3 className="text-lg font-bold mb-1">Residential</h3>
                <p className="text-sm text-[var(--muted)] mb-4">Real ISP IPs from real devices</p>
                <div className="space-y-3">
                  {[
                    { label: 'Speed', value: 'Medium', bar: 60 },
                    { label: 'Detection', value: 'Very Low', bar: 15 },
                    { label: 'Anonymity', value: 'Very High', bar: 95 },
                    { label: 'Reliability', value: 'High', bar: 80 },
                  ].map(({ label, value, bar }) => (
                    <div key={label}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[var(--muted)]">{label}</span>
                        <span className="font-medium">{value}</span>
                      </div>
                      <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-[var(--primary)] transition-all" style={{ width: `${bar}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-5 pt-4 border-t border-[var(--border)]">
                  <p className="text-xs text-[var(--muted)] mb-1">From</p>
                  <p className="text-xl font-bold" style={{ color: 'var(--primary)' }}>₦5,000<span className="text-xs font-normal text-[var(--muted)]">/5GB</span></p>
                </div>
              </div>
            </div>

            {/* Mobile Card */}
            <div className="group relative" style={{ perspective: '1000px' }}>
              <div className="relative bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 transition-all duration-300 group-hover:-translate-y-1 group-hover:shadow-xl" style={{ transformStyle: 'preserve-3d', '--tw-shadow-color': 'rgba(16,185,129,0.15)' } as React.CSSProperties}>
                <div className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl bg-[var(--primary)]" />
                <div className="text-3xl mb-3">📱</div>
                <h3 className="text-lg font-bold mb-1">Mobile 4G</h3>
                <p className="text-sm text-[var(--muted)] mb-4">Real 4G/LTE carrier IPs</p>
                <div className="space-y-3">
                  {[
                    { label: 'Speed', value: 'Medium', bar: 55 },
                    { label: 'Detection', value: 'Extremely Low', bar: 8 },
                    { label: 'Anonymity', value: 'Max', bar: 100 },
                    { label: 'Reliability', value: 'High', bar: 80 },
                  ].map(({ label, value, bar }) => (
                    <div key={label}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[var(--muted)]">{label}</span>
                        <span className="font-medium">{value}</span>
                      </div>
                      <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-[var(--primary)] transition-all" style={{ width: `${bar}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-5 pt-4 border-t border-[var(--border)]">
                  <p className="text-xs text-[var(--muted)] mb-1">From</p>
                  <p className="text-xl font-bold" style={{ color: 'var(--primary)' }}>₦20,000<span className="text-xs font-normal text-[var(--muted)]">/5GB</span></p>
                </div>
              </div>
            </div>

            {/* Datacenter Card */}
            <div className="group relative" style={{ perspective: '1000px' }}>
              <div className="relative bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 transition-all duration-300 group-hover:-translate-y-1 group-hover:shadow-xl" style={{ transformStyle: 'preserve-3d', '--tw-shadow-color': 'rgba(16,185,129,0.15)' } as React.CSSProperties}>
                <div className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl bg-[var(--primary)]" />
                <div className="text-3xl mb-3">🏢</div>
                <h3 className="text-lg font-bold mb-1">Datacenter</h3>
                <p className="text-sm text-[var(--muted)] mb-4">Budget-friendly cloud server IPs</p>
                <div className="space-y-3">
                  {[
                    { label: 'Speed', value: 'Very High', bar: 95 },
                    { label: 'Detection', value: 'High', bar: 70 },
                    { label: 'Anonymity', value: 'Medium', bar: 45 },
                    { label: 'Reliability', value: 'High', bar: 85 },
                  ].map(({ label, value, bar }) => (
                    <div key={label}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[var(--muted)]">{label}</span>
                        <span className="font-medium">{value}</span>
                      </div>
                      <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-[var(--primary)] transition-all" style={{ width: `${bar}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-5 pt-4 border-t border-[var(--border)]">
                  <p className="text-xs text-[var(--muted)] mb-1">From</p>
                  <p className="text-xl font-bold" style={{ color: 'var(--primary)' }}>₦2,500<span className="text-xs font-normal text-[var(--muted)]">/mo</span></p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* All Products & Pricing Table */}
        <div className="mb-20">
          <h2 className="text-2xl font-bold text-center mb-8">All Products &amp; Pricing</h2>
          <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--card)]">
                  <th className="text-left py-4 px-4 font-semibold text-sm">Proxy Type</th>
                  <th className="text-left py-4 px-4 font-semibold text-sm hidden sm:table-cell">Country</th>
                  <th className="text-left py-4 px-4 font-semibold text-sm hidden md:table-cell">Specs</th>
                  <th className="text-right py-4 px-4 font-semibold text-sm">Price</th>
                  <th className="py-4 px-4"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {products.map((product) => (
                  <tr key={product.plan_code} className="bg-[var(--card)] hover:bg-[var(--card-hover)] transition-colors">
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{product.flag}</span>
                        <div>
                          <p className="font-semibold text-sm">{product.plan_type}</p>
                          <p className="text-xs text-[var(--muted)] sm:hidden">{product.country !== 'GLOBAL' ? product.country : 'Global'}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-sm text-[var(--muted)] hidden sm:table-cell">
                      {product.country !== 'GLOBAL' ? COUNTRIES[product.country]?.name || product.country : '🌍 Global'}
                    </td>
                    <td className="py-4 px-4 text-xs text-[var(--muted)] hidden md:table-cell">
                      {product.features.slice(0, 3).join(' · ')}
                    </td>
                    <td className="py-4 px-4 text-right">
                      <span className="font-bold" style={{ color: 'var(--primary)' }}>{formatPrice(product.price_ngn)}</span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <Link
                        href={`/order?plan=${product.plan_code}`}
                        className="px-3 py-1.5 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-lg text-xs transition-colors"
                      >
                        Order
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-20 p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)] text-center">
          <h2 className="text-2xl font-bold mb-4">Need Help Choosing?</h2>
          <p className="text-[var(--muted)] mb-6 max-w-xl mx-auto">
            Tell us what you need and we'll recommend the right proxy type and country mix.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/order"
              className="px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors"
            >
              Start Ordering
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
