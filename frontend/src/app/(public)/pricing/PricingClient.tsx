'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import Link from 'next/link';
import {
  Globe,
  House,
  DeviceMobile,
  HardDrives,
  MagnifyingGlass,
  ArrowLeft,
  Check
} from '@phosphor-icons/react';
import { COUNTRIES } from '@/lib/products';
import { Flag } from '@/components/ui/Flag';

// ── Types ──────────────────────────────────────────────────────────────────────

interface CatalogVariant {
  plan_code: string;
  plan_type: string;
  country: string;
  rotation_mode: string;
  price_ngn: number;
  quantity: number;
  duration_days: number;
  features: string[];
  in_stock: boolean;
}

interface CatalogTemplate {
  plan_type: string;
  rotation_mode_options: string[];
  available_countries: string[];
  base_quantity_gb: number;
  base_price_ngn: number;
  base_price_per_gb: number;
  base_price_per_ip: number;
  min_gb: number;
  max_gb: number;
  gb_tiers: number[];
  supports_city: boolean;
  cities: Record<string, unknown>;
  duration_days: number;
  static_price_multiplier: number;
  supports_country_change: boolean;
  description: string;
  variants: CatalogVariant[];
}

interface CatalogResponse {
  templates: CatalogTemplate[];
  countries_supported: string[];
  rotation_modes_supported: string[];
}

// ── Static fallback products (used when API is unavailable) ───────────────────

const FALLBACK_PRODUCTS = [
  {
    key: 'isp',
    name: 'ISP Proxy',
    type: 'Static IP · Real ISP',
    price: '₦6,500',
    per: 'IP/mo',
    badge: 'Baseline',
    badgeColor: 'rgba(180,120,80,0.1)',
    badgeBorder: 'rgba(180,120,80,0.25)',
    badgeText: 'rgba(180,120,80,0.9)',
    coverage: 45,
    banRisk: 'Moderate',
    banRiskLevel: 'warn',
    speed: 'High',
    replacement: 'Included',
    coins: ['copper', 'copper', 'copper'],
  },
  {
    key: 'residential',
    name: 'Residential',
    type: 'Real Home IP · Deep Cover',
    price: '₦1,000',
    per: 'GB/mo',
    badge: 'Top Pick',
    badgeColor: 'var(--primary)',
    badgeBorder: 'var(--primary)',
    badgeText: '#000',
    coverage: 45,
    banRisk: 'Low',
    banRiskLevel: '',
    speed: 'Good',
    replacement: '7-day SLA',
    coins: ['gold'],
    featured: true,
  },
  {
    key: 'mobile',
    name: 'Mobile 4G',
    type: 'Carrier IP · No Fingerprint',
    price: '₦1,500',
    per: 'GB/mo',
    badge: 'Ghost Protocol',
    badgeColor: 'rgba(148,163,184,0.1)',
    badgeBorder: 'rgba(148,163,184,0.2)',
    badgeText: 'rgba(148,163,184,0.9)',
    coverage: 45,
    banRisk: 'Very Low',
    banRiskLevel: '',
    speed: '4G LTE',
    replacement: '7-day cover',
    coins: ['silver', 'gold'],
  },
  {
    key: 'datacenter',
    name: 'Datacenter',
    type: 'Cloud IP · Maximum Speed',
    price: '₦2,500',
    per: 'IP/mo',
    badge: 'Fast Lane',
    badgeColor: 'rgba(239,68,68,0.08)',
    badgeBorder: 'rgba(239,68,68,0.2)',
    badgeText: 'var(--error)',
    coverage: 45,
    banRisk: 'High',
    banRiskLevel: 'danger',
    speed: '10 Gbps',
    replacement: 'N/A',
    coins: ['bronze'],
    outline: true,
  },
];

// Map DB plan_type to our product key
const planTypeToKey: Record<string, string> = {
  'dc': 'datacenter',
  'isp': 'isp',
  'residential': 'residential',
  'mobile': 'mobile',
};

const keyToPlanType: Record<string, string> = {
  'datacenter': 'dc',
  'isp': 'isp',
  'residential': 'residential',
  'mobile': 'mobile',
};

// FAQ data
const faqs = [
  {
    q: 'How fast is delivery?',
    a: 'Credentials are delivered instantly after payment — usually within 30 seconds.',
  },
  {
    q: 'What payment methods do you accept?',
    a: 'Card, Bank Transfer, USSD, and QR code via Flutterwave. All major Nigerian banks supported.',
  },
  {
    q: 'Can I get a refund?',
    a: 'If your proxy is banned within the first 24 hours and our team cannot replace it, you get a full refund.',
  },
  {
    q: 'What is your ban replacement policy?',
    a: 'We replace banned ISP and Residential proxies at no cost within your subscription period. Mobile 4G proxies are covered for the first 7 days.',
  },
];

// Region mapping
type Region = 'Africa' | 'Europe' | 'Americas' | 'Asia-Pacific';

const REGIONS: Region[] = ['Africa', 'Europe', 'Americas', 'Asia-Pacific'];

function getDisplayRegion(countryRegion: string): Region {
  switch (countryRegion) {
    case 'Africa':
      return 'Africa';
    case 'Europe':
      return 'Europe';
    case 'Americas':
      return 'Americas';
    case 'Asia':
    case 'Oceania':
      return 'Asia-Pacific';
    default:
      return 'Americas';
  }
}

export default function PricingClient() {
  const [searchQuery, setSearchQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showCountryGrid, setShowCountryGrid] = useState(false);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [catalogTemplates, setCatalogTemplates] = useState<CatalogTemplate[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const searchRef = useRef<HTMLDivElement>(null);

  // Fetch catalog from API
  useEffect(() => {
    async function fetchCatalog() {
      try {
        const response = await fetch('/api/catalog', {
          signal: AbortSignal.timeout(10000),
        });
        if (!response.ok) throw new Error('API error');
        const data: CatalogResponse = await response.json();
        setCatalogTemplates(data.templates || []);
      } catch {
        // Fall back to empty — FALLBACK_PRODUCTS used
      } finally {
        setCatalogLoading(false);
      }
    }
    fetchCatalog();
  }, []);

  // Derive products from catalog data, merged with fallback metadata
  const products = useMemo(() => {
    if (catalogLoading) return FALLBACK_PRODUCTS;
    if (catalogTemplates.length === 0) return FALLBACK_PRODUCTS;

    return FALLBACK_PRODUCTS.map((fallback) => {
      const dbPlanType = keyToPlanType[fallback.key];
      const apiTemplate = catalogTemplates.find(t => t.plan_type === dbPlanType);
      if (!apiTemplate) return fallback;

      const isIpBased = dbPlanType === 'dc' || dbPlanType === 'isp';
      const unitPrice = isIpBased
        ? apiTemplate.base_price_per_ip
        : apiTemplate.base_price_per_gb;

      const formattedPrice = unitPrice > 0
        ? `₦${Math.round(unitPrice).toLocaleString('en-NG')}`
        : fallback.price;

      return {
        ...fallback,
        price: formattedPrice,
        coverage: apiTemplate.available_countries.length,
      };
    });
  }, [catalogTemplates, catalogLoading]);

  // Derive active countries from catalog (only show countries with at least one product)
  const activeCountryData = useMemo(() => {
    const activeCodes = new Set<string>();
    for (const t of catalogTemplates) {
      for (const v of t.variants) {
        activeCodes.add(v.country);
      }
    }
    const countries = [];
    for (const [code, info] of Object.entries(COUNTRIES)) {
      if (activeCodes.has(code)) {
        // Find lowest price across all variants for this country
        let lowestPrice: number | null = null;
        for (const t of catalogTemplates) {
          const variant = t.variants.find(v => v.country === code);
          if (variant && variant.price_ngn > 0) {
            if (lowestPrice === null || variant.price_ngn < lowestPrice) {
              lowestPrice = variant.price_ngn;
            }
          }
        }
        const priceLabel = lowestPrice !== null
          ? `From ₦${Math.round(lowestPrice).toLocaleString('en-NG')}`
          : null;
        countries.push({
          code,
          name: info.name,
          flag: info.flag || code,
          region: getDisplayRegion(info.region || 'Americas'),
          priceLabel,
        });
      }
    }
    return countries;
  }, [catalogTemplates]);

  // Country data from lib/products (all)
  const countryData = useMemo(() => {
    const countries = [];
    for (const [code, info] of Object.entries(COUNTRIES)) {
      countries.push({
        code,
        name: info.name,
        flag: info.flag || code,
        region: getDisplayRegion(info.region || 'Americas'),
      });
    }
    return countries;
  }, []);

  // Get price for a specific country + product
  const getCountryPrice = (countryCode: string, planKey: string) => {
    const dbPlanType = keyToPlanType[planKey];
    const template = catalogTemplates.find(t => t.plan_type === dbPlanType);
    if (!template) return null;
    const variant = template.variants.find(v => v.country === countryCode);
    if (!variant) return null;
    return `₦${Math.round(variant.price_ngn).toLocaleString('en-NG')}`;
  };

  // Country detail: products with per-country prices
  const selectedCountryProducts = useMemo(() => {
    if (!selectedCountry || catalogLoading) return null;
    return products.map(product => {
      const price = getCountryPrice(selectedCountry, product.key);
      return { ...product, price: price || product.price };
    });
  }, [selectedCountry, catalogTemplates, catalogLoading, products]);

  // Filter countries based on search
  const filteredCountries = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase();
    return activeCountryData
      .filter(c => c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q))
      .slice(0, 5);
  }, [searchQuery, activeCountryData]);

  // Click outside handler
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Scroll-reveal observer
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

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setShowSuggestions(true);
  };

  const selectCountry = (code: string) => {
    setSearchQuery('');
    setShowSuggestions(false);
    setSelectedCountry(code);
    setShowCountryGrid(false);
  };

  const showCountryGridView = () => {
    setShowCountryGrid(true);
    setSelectedCountry(null);
  };

  const hideCountryGridView = () => {
    setShowCountryGrid(false);
  };

  const selectedCountryData = selectedCountry 
    ? countryData.find(c => c.code === selectedCountry)
    : null;

  return (
    <main className="min-h-screen text-[var(--foreground)]">
      {/* Hero Section */}
      <div className="relative overflow-hidden pt-12 pb-16 px-6">
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-rings" />
        <div className="absolute inset-0 hero-bg-vignette" />
        <div className="hero-orb-1" />
        <div className="hero-orb-2" />
        <div className="hero-orb-3" />

        <div className="relative text-center max-w-3xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[var(--primary)]/30 bg-[var(--primary)]/5 mb-6 mx-auto">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] shadow-[0_0_8px_var(--primary)] animate-pulse" />
            <span className="text-xs font-medium tracking-widest uppercase text-[var(--muted)]">
              Transparent Pricing
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight mb-6">
            Transparent access.<br />
            <span className="text-[var(--primary)]">No hidden costs.</span>
          </h1>
          <p className="text-lg max-w-xl mx-auto leading-relaxed text-[var(--muted)]">
            Find a country. See the available proxy types and pricing. Order in seconds.
          </p>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="flex flex-col items-center gap-2 py-8">
        <span className="text-[10px] tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">Scroll</span>
        <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
      </div>

      {/* Country Search */}
      <div className="max-w-6xl mx-auto px-6 pb-8">
        <div className="search-wrap" ref={searchRef}>
          <MagnifyingGlass size={20} className="search-icon" />
          <input
            type="text"
            id="countrySearch"
            placeholder="Search country (e.g. Nigeria, US, Germany...)"
            value={searchQuery}
            onChange={handleSearchChange}
            onFocus={() => searchQuery && setShowSuggestions(true)}
            className="search-input"
          />
          {showSuggestions && searchQuery && (
            <div className="suggestions-dropdown show">
              {filteredCountries.length > 0 ? (
                filteredCountries.map(c => (
                  <div 
                    key={c.code} 
                    className="suggestion-item"
                    onClick={() => selectCountry(c.code)}
                  >
                    <span className="flag">{c.flag}</span>
                    <span className="country-name">{c.name}</span>
                    {c.priceLabel && <span className="country-price">{c.priceLabel}</span>}
                    <span className="country-code">{c.region}</span>
                  </div>
                ))
              ) : (
                <div className="suggestion-item" style={{ color: 'var(--muted)', cursor: 'default' }}>
                  No countries found
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Country Detail (shown on selection) */}
      {selectedCountryData && (
        <div className="max-w-6xl mx-auto px-6 pb-16">
          <div className="country-detail-card p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth">
            <div className="country-detail-header">
              <span className="flag">{selectedCountryData.flag}</span>
              <div>
                <h2>{selectedCountryData.name}</h2>
                <div className="region-tag">{selectedCountryData.region}</div>
              </div>
              <button className="back-btn" onClick={() => setSelectedCountry(null)}>
                <ArrowLeft size={14} />
                All countries
              </button>
            </div>
            {/* Product cards */}
            <div className="country-products-grid">
              {(selectedCountryProducts || products).map(product => (
                <div key={product.key} className="country-product-card card-depth p-5">
                  <div className="flex items-center gap-4 mb-4">
                    <div className="product-icon" style={{ background: 'rgba(10,210,90,0.08)', border: '1px solid rgba(10,210,90,0.15)' }}>
                      {product.key === 'isp' && <Globe size={18} style={{ color: 'rgba(180,120,80,0.8)' }} />}
                      {product.key === 'residential' && <House size={18} style={{ color: 'var(--primary)' }} />}
                      {product.key === 'mobile' && <DeviceMobile size={18} style={{ color: 'rgba(148,163,184,0.8)' }} />}
                      {product.key === 'datacenter' && <HardDrives size={18} style={{ color: 'rgba(140,100,60,0.6)' }} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="product-name">{product.name}</div>
                      <div className="product-type">{product.type}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="product-price">{product.price}<span>/{product.per}</span></div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="product-avail">● Available</span>
                    <Link
                      href="/order"
                      className="cta-btn"
                    >
                      Order →
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Browse Countries Grid */}
      <div className={`max-w-6xl mx-auto px-6 pb-20 ${!showCountryGrid ? 'hidden' : ''}`}>
        <div className="text-center mb-6">
          <button 
            onClick={hideCountryGridView} 
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium hide-countries-btn"
          >
            <ArrowLeft size={16} />
            Hide countries
          </button>
        </div>
        <div className="country-grid gap-4">
          {activeCountryData.map(c => (
            <div
              key={c.code}
              className="country-tile p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth"
              onClick={() => selectCountry(c.code)}
            >
              <span className="flag">{c.flag}</span>
              <div className="name">{c.name}</div>
              <div className="region">{c.region}</div>
              {c.priceLabel && <div className="country-price">{c.priceLabel}</div>}
            </div>
          ))}
        </div>
      </div>

      {/* View All Countries Button */}
      {!showCountryGrid && !selectedCountry && (
        <div className="text-center pb-16">
          <Link 
            href="#" 
            onClick={(e) => { e.preventDefault(); showCountryGridView(); }}
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-black text-base transition-all duration-200 hover:shadow-[0_0_30px_rgba(10,210,90,0.3)]"
          >
            <Globe size={18} />
            View all countries
          </Link>
        </div>
      )}

      {/* Plan Overview */}
      <div className="max-w-6xl mx-auto px-6 pb-16">
        <div className="section-divider-glow mb-12" />
        <div className="text-center mb-10">
          <span className="text-xs uppercase tracking-widest text-[var(--primary)]">Plans</span>
          <h2 className="text-2xl font-bold tracking-[-0.02em] mt-2 mb-2">Proxy Plans Overview</h2>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>All plans include ban replacement. Prices per month.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {products.map(product => (
            <div key={product.key} className={`plan-card p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth reveal ${product.featured ? 'featured' : ''}`}>
              <span
                className="plan-badge"
                style={{
                  background: product.badgeColor,
                  border: `1px solid ${product.badgeBorder}`,
                  color: product.badgeText
                }}
              >
                {product.badge}
              </span>
              <div className="plan-header">
                <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center flex-shrink-0">
                  {product.key === 'isp' && <Globe size={20} className="text-[var(--primary)]" />}
                  {product.key === 'residential' && <House size={20} className="text-[var(--primary)]" />}
                  {product.key === 'mobile' && <DeviceMobile size={20} className="text-[var(--primary)]" />}
                  {product.key === 'datacenter' && <HardDrives size={20} className="text-[var(--primary)]" />}
                </div>
                <div>
                  <div className="text-base font-bold">{product.name}</div>
                  <div className="plan-subtitle">{product.type}</div>
                </div>
              </div>
              <div className="toll-row">
                <div style={{ display: 'flex', gap: '3px' }}>
                  {product.coins.map((coin, i) => (
                    <div key={i} className={`toll-coin coin-${coin}`} />
                  ))}
                </div>
                <div>
                  <span className="text-xl font-bold text-[var(--primary)]">
                    {product.price}
                  </span>
                  <span className="text-xs text-[var(--muted)]">/{product.per}</span>
                </div>
              </div>
              <div className="plan-spec">
                <div className="spec-dot" />
                <span className="spec-label">Coverage</span>
                <span className="spec-val">{product.coverage} countries</span>
              </div>
              <div className="plan-spec">
                <div className={`spec-dot ${product.banRiskLevel}`} />
                <span className="spec-label">Ban risk</span>
                <span className={`spec-val ${product.banRiskLevel}`}>{product.banRisk}</span>
              </div>
              <div className="plan-spec">
                <div className="spec-dot" />
                <span className="spec-label">Speed</span>
                <span className="spec-val">{product.speed}</span>
              </div>
              <div className="plan-spec">
                <div className="spec-dot" />
                <span className="spec-label">Ban replacement</span>
                <span className="spec-val">{product.replacement}</span>
              </div>
              <Link 
                href="/order" 
                className={`cta-link ${product.outline ? 'outline-link' : ''}`}
              >
                View Plans
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* FAQ Section */}
      <div className="max-w-6xl mx-auto px-6 pb-16">
        <div className="section-divider-glow mb-12" />
        <div className="text-center mb-8">
          <span className="text-xs uppercase tracking-widest text-[var(--primary)]">FAQ</span>
          <h2 className="text-2xl font-bold tracking-[-0.02em] mt-2 mb-2">Common questions</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {faqs.map(faq => (
            <div key={faq.q} className="faq-item p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth reveal">
              <h3>{faq.q}</h3>
              <p>{faq.a}</p>
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
        <p className="mb-10 text-lg text-[var(--muted)]">Start in seconds. No signup required.</p>
        <Link href="/order"
          className="inline-block px-12 py-5 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-black text-lg transition-all duration-200 hover:shadow-[0_0_40px_rgba(10,210,90,0.35)]">
          Get Instant
        </Link>
      </div>
    </main>
  );
}
