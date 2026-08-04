'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Check, Broadcast, House, DeviceMobile, HardDrives, Globe, ArrowsClockwise } from '@phosphor-icons/react';
import { formatPrice, COUNTRIES } from '@/lib/products';
import type { CatalogResponse, CatalogTemplate, CatalogVariant } from '@/types';

const comparison = [
  { type: 'ISP Proxies', speed: 'High', detection: 'Low', anonymity: 'High', reliability: 'High', price: 'From ₦6,500' },
  { type: 'Residential', speed: 'Medium', detection: 'Very Low', anonymity: 'Very High', reliability: 'High', price: 'From ₦5,000' },
  { type: 'Mobile 4G', speed: 'Medium', detection: 'Extremely Low', anonymity: 'Highest', reliability: 'Medium', price: 'From ₦20,000' },
  { type: 'Datacenter', speed: 'High', detection: 'High', anonymity: 'Low', reliability: 'High', price: 'From ₦2,500' },
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

interface CountryPrice {
  country: string;
  countryName: string;
  flag: string;
  price: number;
  inStock: boolean;
}

function getIconForPlanType(planType: string) {
  switch (planType.toLowerCase()) {
    case 'datacenter':
      return <HardDrives size={20} />;
    case 'residential':
      return <House size={20} />;
    case 'mobile':
      return <DeviceMobile size={20} />;
    case 'isp':
      return <Globe size={20} />;
    default:
      return <Globe size={20} />;
  }
}

function getLabelForPlanType(planType: string): string {
  switch (planType.toLowerCase()) {
    case 'datacenter':
      return 'Datacenter';
    case 'residential':
      return 'Residential';
    case 'mobile':
      return 'Mobile 4G';
    case 'isp':
      return 'ISP Proxies';
    default:
      return planType;
  }
}

function extractCountryPrices(variants: CatalogVariant[]): CountryPrice[] {
  const countryMap = new Map<string, CountryPrice>();
  
  for (const variant of variants) {
    const countryCode = variant.country.toUpperCase();
    const countryInfo = COUNTRIES[countryCode];
    const countryName = countryInfo?.name || countryCode;
    const flag = countryInfo?.flag || '🌍';
    
    const existing = countryMap.get(countryCode);
    if (!existing || variant.price_ngn < existing.price) {
      countryMap.set(countryCode, {
        country: countryCode,
        countryName,
        flag,
        price: variant.price_ngn,
        inStock: variant.is_active,
      });
    }
  }
  
  return Array.from(countryMap.values()).sort((a, b) => a.countryName.localeCompare(b.countryName));
}

export default function PricingClient() {
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchCatalog() {
      try {
        const res = await fetch('/api/catalog', { cache: 'no-store' });
        if (!res.ok) {
          throw new Error(`Failed to fetch catalog: ${res.status}`);
        }
        const data: CatalogResponse = await res.json();
        setCatalog(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load pricing');
      } finally {
        setLoading(false);
      }
    }
    fetchCatalog();
  }, []);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    window.location.reload();
  };

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

      {/* Plans by category - loaded from API */}
      <div className="relative max-w-6xl mx-auto px-6 pb-20 space-y-16">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3 text-[var(--muted)]">
              <ArrowsClockwise className="animate-spin" size={24} />
              <span>Loading pricing...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <p className="text-red-400">{error}</p>
            <button
              onClick={handleRetry}
              className="px-6 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-lg transition-all duration-200"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && catalog && catalog.templates.map((template: CatalogTemplate) => {
          const countryPrices = extractCountryPrices(template.variants);
          const planLabel = getLabelForPlanType(template.plan_type);
          
          return (
            <div key={template.plan_type}>
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)]">
                  {getIconForPlanType(template.plan_type)}
                </div>
                <h2 className="text-2xl font-bold tracking-[-0.02em]">{planLabel}</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {countryPrices.map((cp) => (
                  <div
                    key={cp.country}
                    className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5 hover:border-[var(--primary)] transition-all duration-200 card-depth"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <span className="text-2xl">{cp.flag}</span>
                      <div className="text-right">
                        <span className="text-[var(--primary)] font-bold text-lg">{formatPrice(cp.price)}</span>
                        <p className="text-[var(--muted)] text-xs">per month</p>
                      </div>
                    </div>
                    <p className="font-medium mb-1">{cp.countryName}</p>
                    <div className="flex items-center gap-2 mb-3">
                      {cp.inStock ? (
                        <span className="inline-flex items-center gap-1 text-xs text-green-400">
                          <Check size={12} weight="bold" />
                          In stock
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-red-400">
                          Out of stock
                        </span>
                      )}
                    </div>
                    <Link
                      href="/order"
                      className="mt-4 block w-full py-2.5 px-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold text-sm rounded-lg text-center transition-all duration-200"
                    >
                      Order Now
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          );
        })}


        {/* Fallback: If no catalog loaded, show static placeholder message */}
        {!loading && !error && !catalog && (
          <div className="text-center py-12">
            <p className="text-[var(--muted)]">No pricing data available. Please check back later.</p>
          </div>
        )}

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
