'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { loadCatalog, formatPrice, COUNTRIES, type CountryInfo } from '@/lib/products';
import type { Product, CatalogTemplate } from '@/types';
import { Globe, House, HardDrives, Clock, Lightning, Desktop, DeviceMobile, Check } from '@phosphor-icons/react';

interface CategoryInfo {
  key: string;
  icon: React.ReactNode;
  name: string;
  coverName: string;
  tagline: string;
  description: string;
  bestFor: string;
  price: string;
  countryCount: number;
}

const PRODUCT_CATEGORIES: Omit<CategoryInfo, 'countryCount'>[] = [
  {
    key: 'ISP',
    name: 'ISP Proxy',
    coverName: 'Baseline Identity',
    tagline: 'Your registered ISP address. Stable, fast, hard to flag.',
    description: 'Static IP from a real ISP. Looks like a genuine home connection — but without the bandwidth limits of actual residential. The professional\'s choice.',
    bestFor: 'Sneaker bots, ticket drops, account creation, automation',
    price: 'From ₦6,500/IP/month',
    icon: <Desktop className="w-8 h-8" weight="regular" />,
  },
  {
    key: 'RESIDENTIAL',
    name: 'Residential',
    coverName: 'Deep Cover',
    tagline: 'A real home address. Nearly impossible to detect.',
    description: 'Real IPs from actual home devices worldwide. The gold standard for anonymity. Every request looks like a genuine person browsing from their house.',
    bestFor: 'Social media management, brand monitoring, web scraping, price aggregation',
    price: 'From ₦15,000/month',
    icon: <House className="w-8 h-8" weight="regular" />,
  },
  {
    key: 'MOBILE',
    name: 'Mobile 4G',
    coverName: 'Ghost Protocol',
    tagline: '4G/5G IPs. Not traceable to a device.',
    description: 'Mobile carrier IPs with carrier-level anonymity. The hardest to block because they look exactly like real mobile users on real carrier networks.',
    bestFor: 'Ad verification, app testing, location testing, mobile-specific campaigns',
    price: 'From ₦20,000/month',
    icon: <DeviceMobile className="w-8 h-8" weight="regular" />,
  },
  {
    key: 'DATACENTER',
    name: 'Datacenter',
    coverName: 'Fast Lane',
    tagline: 'Raw speed. Pass through hostile territory at full throttle.',
    description: 'Cloud server IPs. The fastest option by a wide margin. Lower anonymity, but when you need speed above all else, this is it.',
    bestFor: 'General browsing, SEO tools, traffic routing, bulk operations',
    price: 'From ₦3,500/month',
    icon: <HardDrives className="w-8 h-8" weight="regular" />,
  },
];

export default function ProductsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [selectedMission, setSelectedMission] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/catalog', { cache: 'no-store' })
      .then((r) => r.json())
      .then((data: { templates?: CatalogTemplate[] }) => {
        const templates = data.templates || [];
        
        const countryCountMap: Record<string, number> = {};
        for (const t of templates) {
          const key = t.plan_type.toUpperCase();
          countryCountMap[key] = (t.available_countries || []).length;
        }

        const cats: CategoryInfo[] = PRODUCT_CATEGORIES.map((cat) => ({
          ...cat,
          countryCount: countryCountMap[cat.key] || 0,
        }));
        
        setCategories(cats);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load catalog:', err);
        setError('Failed to load products. Please refresh.');
        setLoading(false);
      });
  }, []);

  const handleMissionClick = (key: string) => {
    setSelectedMission(key);
    const element = document.getElementById(`product-${key.toLowerCase()}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const comparisonData = [
    { feature: 'Speed', isp: 'Fast', residential: 'Medium', mobile: 'Medium', datacenter: 'Very Fast' },
    { feature: 'Detection Risk', isp: 'Low', residential: 'Very Low', mobile: 'Extremely Low', datacenter: 'High' },
    { feature: 'Anonymity', isp: 'High', residential: 'Very High', mobile: 'Highest', datacenter: 'Low' },
    { feature: 'Stability', isp: 'High', residential: 'High', mobile: 'Medium', datacenter: 'High' },
    { feature: 'Best For', isp: 'Sneakers, tickets', residential: 'Social, scraping', mobile: 'Ad verification', datacenter: 'Bulk, speed' },
  ];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
          <p className="mt-4 text-[var(--muted)]">Loading products...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-[var(--primary)] text-black rounded-xl font-semibold transition-all duration-200 hover:bg-[var(--primary-dark)]"
          >
            Refresh
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative overflow-hidden pt-24 pb-16 px-4">
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-rings" />
        <div className="absolute inset-0 hero-bg-vignette" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 hero-orb-1" />
        <div className="absolute bottom-1/3 right-1/4 w-80 h-80 hero-orb-2" />

        <div className="relative max-w-7xl mx-auto">
          {/* Page Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl sm:text-5xl font-bold mb-4 leading-tight">
              Not all disguises are created equal.
            </h1>
            <p className="text-lg sm:text-xl text-[var(--foreground)] mb-3">
              Choose the right cover for your operation.
            </p>
            <p className="text-sm text-[var(--muted)]">
              ISP · Residential · Mobile · Datacenter — know the difference before you buy.
            </p>
          </div>

          {/* What's your mission? */}
          <div className="mb-12">
            <h2 className="text-lg font-semibold text-center mb-4 text-[var(--foreground)]">
              What&apos;s your mission?
            </h2>
            <div className="flex flex-wrap justify-center gap-3">
              {[
                { label: '👟 Sneakers & Tickets', key: 'ISP' },
                { label: '📱 Social Media', key: 'RESIDENTIAL' },
                { label: '🔍 Ad Verification', key: 'MOBILE' },
                { label: '🌐 General Browsing', key: 'DATACENTER' },
              ].map((mission) => (
                <button
                  key={mission.key}
                  onClick={() => handleMissionClick(mission.key)}
                  className={`px-5 py-2.5 rounded-xl font-medium transition-all duration-200 ${
                    selectedMission === mission.key
                      ? 'bg-[var(--primary)] text-black'
                      : 'bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] hover:border-[var(--primary)]'
                  }`}
                >
                  {mission.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        {/* Product Cover Cards - 2x2 Grid */}
        <div className="grid sm:grid-cols-2 gap-6 mb-20">
          {categories.map((cat) => (
            <div
              key={cat.key}
              id={`product-${cat.key.toLowerCase()}`}
              className={`bg-[var(--card)] border rounded-2xl p-6 transition-all duration-300 card-depth ${
                selectedMission === cat.key
                  ? 'border-[var(--primary)] ring-2 ring-[var(--primary)]/30'
                  : 'border-[var(--border)] hover:border-[var(--primary)]'
              }`}
            >
              <div className="flex items-start gap-4 mb-4">
                <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] flex-shrink-0">
                  {cat.icon}
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-bold mb-1">{cat.name}</h3>
                  <p className="text-sm text-[var(--primary)] font-medium mb-2">{cat.coverName}</p>
                  <p className="text-sm text-[var(--foreground)] font-semibold">{cat.tagline}</p>
                </div>
              </div>

              <p className="text-sm text-[var(--muted)] mb-4 leading-relaxed">
                {cat.description}
              </p>

              <div className="mb-4">
                <p className="text-xs text-[var(--muted)] mb-1">Best for:</p>
                <p className="text-sm text-[var(--foreground)]">{cat.bestFor}</p>
              </div>

              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-[var(--muted)]" weight="regular" />
                  <span className="text-sm text-[var(--muted)]">
                    {cat.countryCount > 0 ? `${cat.countryCount} countries` : 'View coverage'}
                  </span>
                </div>
                <span className="text-lg font-bold text-[var(--primary)]">{cat.price}</span>
              </div>

              <Link
                href="/order"
                className="w-full px-4 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-all duration-200 text-center block"
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
            <table className="w-full bg-[var(--card)] border border-[var(--border)] rounded-2xl overflow-hidden">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--muted)]"></th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-[var(--foreground)]">ISP</th>
                  <th className="px-4 py-3 text-center text-sm font-bold text-[var(--primary)] bg-[var(--primary)]/5">
                    Residential
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-[var(--foreground)]">Mobile</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-[var(--foreground)]">Datacenter</th>
                </tr>
              </thead>
              <tbody>
                {comparisonData.map((row, idx) => (
                  <tr key={row.feature} className={idx !== comparisonData.length - 1 ? 'border-b border-[var(--border)]' : ''}>
                    <td className="px-4 py-3 text-sm font-medium text-[var(--foreground)]">{row.feature}</td>
                    <td className="px-4 py-3 text-center text-sm text-[var(--muted)]">{row.isp}</td>
                    <td className="px-4 py-3 text-center text-sm font-medium text-[var(--primary)] bg-[var(--primary)]/5">{row.residential}</td>
                    <td className="px-4 py-3 text-center text-sm text-[var(--muted)]">{row.mobile}</td>
                    <td className="px-4 py-3 text-center text-sm text-[var(--muted)]">{row.datacenter}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Coverage Stats Bar */}
        <div className="grid grid-cols-3 gap-4 max-w-2xl mx-auto mb-20">
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 text-center card-depth">
            <Globe className="w-8 h-8 text-[var(--primary)] mx-auto mb-2" weight="regular" />
            <p className="text-xl font-bold text-[var(--foreground)]">120+</p>
            <p className="text-xs text-[var(--muted)]">Countries</p>
          </div>
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 text-center card-depth">
            <Lightning className="w-8 h-8 text-[var(--primary)] mx-auto mb-2" weight="regular" />
            <p className="text-xl font-bold text-[var(--foreground)]">Instant</p>
            <p className="text-xs text-[var(--muted)]">Delivery</p>
          </div>
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 text-center card-depth">
            <Clock className="w-8 h-8 text-[var(--primary)] mx-auto mb-2" weight="regular" />
            <p className="text-xl font-bold text-[var(--foreground)]">99.9%</p>
            <p className="text-xs text-[var(--muted)]">Uptime</p>
          </div>
        </div>

        {/* Final CTA */}
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-6">Ready to cross the Styx?</h2>
          <Link
            href="/order"
            className="inline-block px-8 py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-all duration-200 text-lg"
          >
            Get Started →
          </Link>
        </div>
      </div>
    </div>
  );
}
