'use client';

import Link from 'next/link';
import { products, formatPrice } from '@/lib/products';
import GlobeViz from '@/components/GlobeViz';

// Product category data
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
    availableIn: ['UK', 'US', 'DE', 'FR', 'CA', 'JP', 'AU', 'BR', 'SG'],
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

// Comparison data
const comparisonData = [
  {
    feature: 'Speed',
    ISP: 'High',
    Residential: 'Medium',
    Mobile: 'Medium',
    Datacenter: 'Very High',
  },
  {
    feature: 'Detection',
    ISP: 'Low',
    Residential: 'Very Low',
    Mobile: 'Very Low',
    Datacenter: 'High',
  },
  {
    feature: 'Best For',
    ISP: 'Scraping, automation',
    Residential: 'Sneakers, ticketing',
    Mobile: 'Social media, ads',
    Datacenter: 'General browsing',
  },
];

export default function ProductsPage() {
  return (
    <div className="min-h-screen pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Globe Viz Hero Section */}
        <div className="mb-12">
          <GlobeViz />
        </div>

        {/* Product Category Cards */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
          {categories.map((category) => (
            <div
              key={category.key}
              className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 flex flex-col hover:border-[var(--primary)] transition-colors"
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

              {/* Available In (for ISP) */}
              {category.availableIn && (
                <div className="mb-4">
                  <span className="text-xs text-[var(--muted)]">Available in:</span>
                  <p className="text-sm">{category.availableIn.join(', ')}</p>
                </div>
              )}

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

              {/* Order Now Button */}
              <Link
                href="/order"
                className="w-full px-4 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors text-center"
              >
                Order Now →
              </Link>
            </div>
          ))}
        </div>

        {/* Comparison Table */}
        <div className="mb-20">
          <h2 className="text-2xl font-bold text-center mb-8">Compare Proxy Types</h2>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left py-4 px-4 font-semibold">Feature</th>
                  <th className="text-center py-4 px-4 font-semibold">ISP</th>
                  <th className="text-center py-4 px-4 font-semibold">Residential</th>
                  <th className="text-center py-4 px-4 font-semibold">Mobile 4G</th>
                  <th className="text-center py-4 px-4 font-semibold">Datacenter</th>
                </tr>
              </thead>
              <tbody>
                {comparisonData.map((row, idx) => (
                  <tr key={idx} className="border-b border-[var(--border)]">
                    <td className="py-4 px-4 text-[var(--muted)]">{row.feature}</td>
                    <td className="text-center py-4 px-4">{row.ISP}</td>
                    <td className="text-center py-4 px-4">{row.Residential}</td>
                    <td className="text-center py-4 px-4">{row.Mobile}</td>
                    <td className="text-center py-4 px-4">{row.Datacenter}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pricing Reference Grid */}
        <div>
          <h2 className="text-2xl font-bold text-center mb-8">All Products & Pricing</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {products.map((product) => (
              <div
                key={product.plan_code}
                className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 flex items-center justify-between"
              >
                <div>
                  <span className="font-medium">{product.country}</span>
                  <span className="text-[var(--muted)] text-sm ml-2">({product.plan_type})</span>
                </div>
                <span className="font-semibold text-[var(--primary)]">
                  {formatPrice(product.price_ngn)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-20 p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)] text-center">
          <h2 className="text-2xl font-bold mb-4">Need Help Choosing?</h2>
          <p className="text-[var(--muted)] mb-6 max-w-xl mx-auto">
            Not sure which proxy type is right for you? Our team can help you make the best choice for your use case.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="/order"
              className="px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors"
            >
              Start Ordering
            </Link>
            <a
              href="https://wa.me/2347032981049"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-xl transition-colors"
            >
              Chat on WhatsApp
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
