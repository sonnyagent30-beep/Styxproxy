'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { 
  Globe, 
  House, 
  DeviceMobile, 
  HardDrives, 
  ArrowsClockwise,
  Check,
  X,
  MagnifyingGlass,
  CaretDown
} from '@phosphor-icons/react';
import { formatPrice, COUNTRIES } from '@/lib/products';
import { Flag } from '@/components/ui/Flag';
import type { CatalogResponse, CatalogTemplate, CatalogVariant } from '@/types';

// FAQ data (kept from original)
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

// Region mapping
type Region = 'Africa' | 'Europe' | 'Americas' | 'Asia-Pacific';

const REGIONS: Region[] = ['Africa', 'Europe', 'Americas', 'Asia-Pacific'];

// Map COUNTRIES region to our display regions
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
      return 'Americas'; // fallback
  }
}

// Product type display info
const PRODUCT_TYPES = ['isp', 'residential', 'mobile', 'datacenter'] as const;
type ProductType = typeof PRODUCT_TYPES[number];

const productTypeInfo: Record<ProductType, { label: string; icon: React.ReactNode; desc: string; priceFrom: string }> = {
  isp: {
    label: 'ISP Proxies',
    icon: <Globe size={24} />,
    desc: 'Static IPs from real ISPs • Ban replacement included',
    priceFrom: 'From ₦6,500/IP/month',
  },
  residential: {
    label: 'Residential',
    icon: <House size={24} />,
    desc: 'Real home device IPs • Highest success rate',
    priceFrom: 'From ₦15,000/month',
  },
  mobile: {
    label: 'Mobile 4G',
    icon: <DeviceMobile size={24} />,
    desc: 'Real 4G/5G carrier IPs • 7-day ban replacement',
    priceFrom: 'From ₦20,000/month',
  },
  datacenter: {
    label: 'Datacenter',
    icon: <HardDrives size={24} />,
    desc: 'Cloud server IPs • Fastest speeds',
    priceFrom: 'From ₦3,500/month',
  },
};

interface CountryVariant {
  country: string;
  countryName: string;
  countryCode: string;
  region: Region;
  planType: ProductType;
  price: number;
  inStock: boolean;
}

export default function PricingClient() {
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRegion, setSelectedRegion] = useState<Region | 'All'>('All');
  const [selectedProductType, setSelectedProductType] = useState<ProductType | 'All'>('All');

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

  // Extract all country variants from catalog
  const allVariants = useMemo(() => {
    if (!catalog) return [];
    
    const variants: CountryVariant[] = [];
    
    for (const template of catalog.templates) {
      const planType = template.plan_type.toLowerCase() as ProductType;
      
      for (const variant of template.variants) {
        const countryCode = variant.country.toUpperCase();
        const countryInfo = COUNTRIES[countryCode];
        const countryRegion = countryInfo?.region || 'Americas';
        
        variants.push({
          country: countryCode,
          countryName: countryInfo?.name || countryCode,
          countryCode,
          region: getDisplayRegion(countryRegion),
          planType,
          price: variant.price_ngn,
          inStock: (variant as any).in_stock ?? true,
        });
      }
    }
    
    return variants;
  }, [catalog]);

  // Filter variants
  const filteredVariants = useMemo(() => {
    return allVariants.filter((v) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (!v.countryName.toLowerCase().includes(query) && 
            !v.country.toLowerCase().includes(query)) {
          return false;
        }
      }
      
      // Region filter
      if (selectedRegion !== 'All' && v.region !== selectedRegion) {
        return false;
      }
      
      // Product type filter
      if (selectedProductType !== 'All' && v.planType !== selectedProductType) {
        return false;
      }
      
      return true;
    });
  }, [allVariants, searchQuery, selectedRegion, selectedProductType]);

  // Group by region
  const groupedByRegion = useMemo(() => {
    const groups: Record<Region, CountryVariant[]> = {
      Africa: [],
      Europe: [],
      Americas: [],
      'Asia-Pacific': [],
    };
    
    for (const v of filteredVariants) {
      groups[v.region].push(v);
    }
    
    // Sort each region alphabetically by country name
    for (const region of REGIONS) {
      groups[region].sort((a, b) => a.countryName.localeCompare(b.countryName));
    }
    
    return groups;
  }, [filteredVariants]);

  // Get unique countries with their best prices per plan type
  const countryPlanPrices = useMemo(() => {
    const countryPlans: Record<string, Record<ProductType, { price: number; inStock: boolean }>> = {};
    
    for (const v of filteredVariants) {
      if (!countryPlans[v.country]) {
        countryPlans[v.country] = {} as any;
      }
      
      // Keep lowest price per plan type
      const existing = countryPlans[v.country][v.planType];
      if (!existing || v.price < existing.price) {
        countryPlans[v.country][v.planType] = {
          price: v.price,
          inStock: v.inStock,
        };
      }
    }
    
    return countryPlans;
  }, [filteredVariants]);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    window.location.reload();
  };

  return (
    <main className="min-h-screen text-[var(--foreground)]">
      {/* Hero Section */}
      <div className="relative overflow-hidden pt-32 pb-16 px-6">
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-rings" />
        <div className="absolute inset-0 hero-bg-vignette" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 hero-orb-1" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 hero-orb-2" />

        <div className="relative text-center max-w-3xl mx-auto">
          <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-4">
            Pricing
          </p>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-[-0.03em]">
            Transparent access. No hidden costs.
          </h1>
          <p className="text-[var(--muted)] text-lg max-w-xl mx-auto">
            Cross into 120+ jurisdictions. Here&apos;s what each one costs.
          </p>
        </div>
      </div>

      {/* Sticky Filter Bar */}
      <div className="sticky top-0 z-50 bg-[var(--surface)] border-b border-[var(--border)] px-6 py-4">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row gap-4 items-center">
          {/* Search Input */}
          <div className="relative flex-1 w-full md:w-auto">
            <MagnifyingGlass 
              size={20} 
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" 
            />
            <input
              type="text"
              placeholder="Search country..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-[var(--card)] border border-[var(--border)] rounded-lg text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)] transition-colors"
            />
          </div>

          {/* Region Tabs */}
          <div className="flex flex-wrap gap-1 bg-[var(--card)] p-1 rounded-lg">
            <button
              onClick={() => setSelectedRegion('All')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                selectedRegion === 'All'
                  ? 'bg-[var(--primary)] text-black'
                  : 'text-[var(--muted)] hover:text-[var(--foreground)]'
              }`}
            >
              All
            </button>
            {REGIONS.map((region) => (
              <button
                key={region}
                onClick={() => setSelectedRegion(region)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  selectedRegion === region
                    ? 'bg-[var(--primary)] text-black'
                    : 'text-[var(--muted)] hover:text-[var(--foreground)]'
                }`}
              >
                {region}
              </button>
            ))}
          </div>

          {/* Product Type Filter */}
          <div className="flex flex-wrap gap-1 bg-[var(--card)] p-1 rounded-lg">
            <button
              onClick={() => setSelectedProductType('All')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                selectedProductType === 'All'
                  ? 'bg-[var(--primary)] text-black'
                  : 'text-[var(--muted)] hover:text-[var(--foreground)]'
              }`}
            >
              All
            </button>
            {PRODUCT_TYPES.map((type) => (
              <button
                key={type}
                onClick={() => setSelectedProductType(type)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  selectedProductType === type
                    ? 'bg-[var(--primary)] text-black'
                    : 'text-[var(--muted)] hover:text-[var(--foreground)]'
                }`}
              >
                {productTypeInfo[type].label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-6 pb-20">
        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3 text-[var(--muted)]">
              <ArrowsClockwise className="animate-spin" size={24} />
              <span>Loading pricing...</span>
            </div>
          </div>
        )}

        {/* Error State */}
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

        {/* Countries by Region */}
        {!loading && !error && (
          <>
            {REGIONS.map((region) => {
              const regionCountries = groupedByRegion[region];
              if (regionCountries.length === 0) return null;

              return (
                <div key={region} className="mb-12">
                  <h2 className="text-xl font-semibold mb-6 flex items-center gap-3">
                    {region === 'Africa' && '🇿🇦'}
                    {region === 'Europe' && '🇪🇺'}
                    {region === 'Americas' && '🌎'}
                    {region === 'Asia-Pacific' && '🌏'}
                    <span>{region}</span>
                    <span className="text-sm font-normal text-[var(--muted)]">
                      ({regionCountries.length} {regionCountries.length === 1 ? 'country' : 'countries'})
                    </span>
                  </h2>
                  
                  <div className="grid gap-3">
                    {regionCountries.map((variant) => {
                      const countryKey = variant.country;
                      const plans = countryPlanPrices[countryKey] || {};
                      
                      return (
                        <div
                          key={`${countryKey}-${variant.planType}`}
                          className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4 hover:border-[var(--primary)] transition-all duration-200 card-depth"
                        >
                          <div className="flex items-center justify-between flex-wrap gap-4">
                            {/* Country Info */}
                            <div className="flex items-center gap-3">
                              <Flag countryCode={variant.country} size={32} />
                              <div>
                                <p className="font-semibold">{variant.countryName}</p>
                                <p className="text-xs text-[var(--muted)]">{variant.country}</p>
                              </div>
                            </div>

                            {/* Plan Types Available */}
                            <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                              {PRODUCT_TYPES.map((pt) => {
                                const planData = plans[pt];
                                if (!planData) return null;
                                
                                return (
                                  <div key={pt} className="flex items-center gap-2">
                                    <span className="text-sm text-[var(--muted)]">
                                      {productTypeInfo[pt].label}:
                                    </span>
                                    <span className="text-[var(--primary)] font-semibold text-sm">
                                      from {formatPrice(planData.price)}
                                    </span>
                                    {planData.inStock ? (
                                      <span className="inline-flex items-center gap-1 text-xs text-green-400">
                                        <Check size={12} weight="bold" />
                                      </span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 text-xs text-red-400">
                                        <X size={12} weight="bold" />
                                      </span>
                                    )}
                                  </div>
                                );
                              })}
                            </div>

                            {/* View Plans Button */}
                            <Link
                              href="/order"
                              className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold text-sm rounded-lg transition-all duration-200 whitespace-nowrap"
                            >
                              View Plans →
                            </Link>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}

            {/* Empty State */}
            {filteredVariants.length === 0 && (
              <div className="text-center py-16">
                <p className="text-[var(--muted)] text-lg">
                  No countries match your filters.
                </p>
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setSelectedRegion('All');
                    setSelectedProductType('All');
                  }}
                  className="mt-4 text-[var(--primary)] hover:underline"
                >
                  Clear filters
                </button>
              </div>
            )}
          </>
        )}

        {/* Product Type Summary Cards */}
        {!loading && !error && catalog && (
          <div className="pt-16 pb-12">
            <div className="section-divider-glow mb-12" />
            
            <h2 className="text-2xl font-bold mb-8 text-center tracking-[-0.02em]">
              Quick Reference
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {PRODUCT_TYPES.map((type) => (
                <div
                  key={type}
                  className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 card-depth hover:border-[var(--primary)] transition-all duration-200"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)]">
                      {productTypeInfo[type].icon}
                    </div>
                    <h3 className="font-semibold">{productTypeInfo[type].label}</h3>
                  </div>
                  
                  <p className="text-[var(--primary)] font-bold text-lg mb-2">
                    {productTypeInfo[type].priceFrom}
                  </p>
                  
                  <p className="text-[var(--muted)] text-sm">
                    {productTypeInfo[type].desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* FAQ Section */}
        {!loading && !error && (
          <>
            <div className="section-divider-glow" />
            
            <div className="pt-8">
              <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-4 text-center">
                Questions
              </p>
              <h2 className="text-2xl font-bold mb-6 text-center tracking-[-0.02em]">
                Common questions
              </h2>
              <div className="max-w-2xl mx-auto space-y-3">
                {faqs.map((faq) => (
                  <div 
                    key={faq.q} 
                    className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5 card-depth"
                  >
                    <h3 className="font-semibold mb-2">{faq.q}</h3>
                    <p className="text-[var(--muted)] text-sm">{faq.a}</p>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Final CTA */}
        <div className="section-divider-glow mt-16" />
        
        <div className="text-center pt-8 pb-8">
          <p className="text-[var(--muted)] mb-4">Need bulk access or custom jurisdiction?</p>
          <Link 
            href="/contact" 
            className="inline-block min-w-[200px] py-3 px-8 border-2 border-[var(--primary)] text-[var(--primary)] rounded-xl font-semibold hover:bg-[var(--primary)] hover:text-black transition-all duration-200 text-center"
          >
            Contact Us
          </Link>
        </div>
      </div>
    </main>
  );
}
