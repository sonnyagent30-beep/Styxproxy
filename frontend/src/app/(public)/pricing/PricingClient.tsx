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

// Product type definitions matching HTML mockup
const PRODUCTS = [
  {
    key: 'isp',
    name: 'ISP Proxy',
    type: 'Static IP · Real ISP',
    price: '₦6,500/IP',
    per: 'mo',
    badge: 'Baseline',
    badgeColor: 'rgba(180,120,80,0.1)',
    badgeBorder: 'rgba(180,120,80,0.25)',
    badgeText: 'rgba(180,120,80,0.9)',
    iconBg: 'rgba(180,120,80,0.1)',
    iconBorder: 'rgba(180,120,80,0.2)',
    iconColor: 'rgba(180,120,80,0.8)',
    coverage: '45 countries',
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
    price: '₦15,000',
    per: 'mo',
    badge: 'Top Pick',
    badgeColor: 'var(--primary)',
    badgeBorder: 'var(--primary)',
    badgeText: '#000',
    iconBg: 'rgba(251,191,36,0.1)',
    iconBorder: 'rgba(251,191,36,0.2)',
    iconColor: 'rgba(251,191,36,0.9)',
    coverage: '90 countries',
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
    price: '₦20,000',
    per: 'mo',
    badge: 'Ghost Protocol',
    badgeColor: 'rgba(148,163,184,0.1)',
    badgeBorder: 'rgba(148,163,184,0.2)',
    badgeText: 'rgba(148,163,184,0.9)',
    iconBg: 'rgba(148,163,184,0.08)',
    iconBorder: 'rgba(148,163,184,0.15)',
    iconColor: 'rgba(148,163,184,0.8)',
    coverage: '30 countries',
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
    price: '₦3,500',
    per: 'mo',
    badge: 'Fast Lane',
    badgeColor: 'rgba(239,68,68,0.08)',
    badgeBorder: 'rgba(239,68,68,0.2)',
    badgeText: 'var(--error)',
    iconBg: 'rgba(140,100,60,0.08)',
    iconBorder: 'rgba(140,100,60,0.2)',
    iconColor: 'rgba(140,100,60,0.6)',
    coverage: '120 countries',
    banRisk: 'High',
    banRiskLevel: 'danger',
    speed: '10 Gbps',
    replacement: 'N/A',
    coins: ['bronze'],
    outline: true,
  },
];

// Country data from lib/products mapped to our display format
function getCountryData() {
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
}

export default function PricingClient() {
  const [searchQuery, setSearchQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showCountryGrid, setShowCountryGrid] = useState(false);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);
  
  const countryData = useMemo(() => getCountryData(), []);

  // Filter countries based on search
  const filteredCountries = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase();
    return countryData
      .filter(c => c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q))
      .slice(0, 5);
  }, [searchQuery, countryData]);

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
      <div className="relative overflow-hidden pt-32 pb-16 px-6">
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-rings" />
        <div className="absolute inset-0 hero-bg-vignette" />
        <div className="hero-orb-1" />
        <div className="hero-orb-2" />

        <div className="relative text-center max-w-3xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-[-0.03em]">
            Transparent access. No hidden costs.
          </h1>
          <p className="text-[var(--muted)] text-lg max-w-xl mx-auto leading-relaxed">
            Find a country. See the available proxy types and pricing. Order in seconds.
          </p>
        </div>
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
          <div className="country-detail-card">
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
            {PRODUCTS.map(product => (
              <div key={product.key} className="product-row">
                <div 
                  className="product-icon"
                  style={{ 
                    background: product.featured ? 'rgba(251,191,36,0.1)' : 'rgba(10,210,90,0.08)',
                    border: `1px solid ${product.featured ? 'rgba(251,191,36,0.2)' : 'rgba(10,210,90,0.15)'}`
                  }}
                >
                  {product.key === 'isp' && <Globe size={18} style={{ color: product.iconColor }} />}
                  {product.key === 'residential' && <House size={18} style={{ color: product.iconColor }} />}
                  {product.key === 'mobile' && <DeviceMobile size={18} style={{ color: product.iconColor }} />}
                  {product.key === 'datacenter' && <HardDrives size={18} style={{ color: product.iconColor }} />}
                </div>
                <div className="product-info">
                  <div className="product-name">{product.name}</div>
                  <div className="product-type">{product.type}</div>
                </div>
                <div className="product-price">
                  {product.price}<span>/{product.per}</span>
                </div>
                <div className="product-avail">Available</div>
                <Link 
                  href="/order" 
                  className={`cta-btn ${product.outline ? 'outline' : ''}`}
                >
                  Order →
                </Link>
              </div>
            ))}
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
        <div className="country-grid">
          {countryData.map(c => (
            <div 
              key={c.code} 
              className="country-tile"
              onClick={() => selectCountry(c.code)}
            >
              <span className="flag">{c.flag}</span>
              <div className="name">{c.name}</div>
              <div className="region">{c.region}</div>
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
            className="btn-primary inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold rounded-xl"
          >
            <Globe size={18} />
            View all countries
          </Link>
        </div>
      )}

      {/* Plan Overview */}
      <div className="max-w-6xl mx-auto px-6 pb-12">
        <div className="section-divider-glow mb-12" />
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold tracking-[-0.02em] mb-2">Proxy Plans Overview</h2>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>All plans include ban replacement. Prices per month.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {PRODUCTS.map(product => (
            <div key={product.key} className={`plan-card ${product.featured ? 'featured' : ''}`}>
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
                <div 
                  className="plan-icon"
                  style={{ 
                    background: product.iconBg, 
                    border: `1px solid ${product.iconBorder}` 
                  }}
                >
                  {product.key === 'isp' && <Globe size={20} style={{ color: product.iconColor }} />}
                  {product.key === 'residential' && <House size={20} style={{ color: product.iconColor }} />}
                  {product.key === 'mobile' && <DeviceMobile size={20} style={{ color: product.iconColor }} />}
                  {product.key === 'datacenter' && <HardDrives size={20} style={{ color: product.iconColor }} />}
                </div>
                <div>
                  <div className="plan-title">{product.name}</div>
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
                  <span className="font-bold" style={{ color: 'var(--primary)', fontSize: '1.125rem' }}>
                    {product.price}
                  </span>
                  <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>/{product.per}</span>
                </div>
              </div>
              <div className="plan-spec">
                <div className="spec-dot" />
                <span className="spec-label">Coverage</span>
                <span className="spec-val">{product.coverage}</span>
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
      <div className="max-w-6xl mx-auto px-6 pb-12">
        <div className="section-divider-glow mb-12" />
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold tracking-[-0.02em] mb-2">Common questions</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {faqs.map(faq => (
            <div key={faq.q} className="faq-item">
              <h3>{faq.q}</h3>
              <p>{faq.a}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA Section */}
      <div className="max-w-6xl mx-auto px-6 pb-8">
        <div className="section-divider-glow mt-8 mb-8" />
        <div className="text-center pb-8">
          <p className="text-sm mb-4" style={{ color: 'var(--muted)' }}>Need bulk access or a custom jurisdiction?</p>
          <Link href="/contact" className="btn-outline">
            Contact Us
          </Link>
        </div>
      </div>
    </main>
  );
}
