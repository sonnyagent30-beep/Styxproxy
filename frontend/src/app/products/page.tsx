'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import { products, formatPrice, COUNTRIES, type CountryInfo } from '@/lib/products';

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
  const [carouselIdx, setCarouselIdx] = useState(0);
  const touchStartX = useRef(0);
  const touchDeltaX = useRef(0);

  return (
    <div className="min-h-screen pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Page Header */}
        <div className="text-center mb-12">
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
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-8 max-w-2xl mx-auto">
          {[
            { label: 'Uptime', value: '99.9%', icon: <svg className="w-6 h-6 text-[var(--primary)] mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> },
            { label: 'IP Pool', value: '50K+ IPs', icon: <svg className="w-6 h-6 text-[var(--primary)] mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9 9 0 100-18 9 9 0 000 18z"/><path strokeLinecap="round" strokeLinejoin="round" d="M3.6 9h16.8M3.6 15h16.8M12 3a15.3 15.3 0 014 9 15.3 15.3 0 01-4 9 15.3 15.3 0 01-4-9 15.3 15.3 0 014-9z"/></svg> },
            { label: 'Speed', value: '1 Gbps', icon: <svg className="w-6 h-6 text-[var(--primary)] mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"/></svg> },
            { label: 'Delivery', value: 'Instant', icon: <svg className="w-6 h-6 text-[var(--primary)] mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12"/></svg> },
          ].map(({ label, value, icon }) => (
            <div key={label} className="bg-[var(--card)] border border-[var(--border)] rounded-xl px-3 py-3 text-center">
              <div className="mb-1 flex justify-center">{icon}</div>
              <div className="text-xl font-bold" style={{ color: 'var(--primary)' }}>{value}</div>
              <div className="text-xs text-[var(--muted)]">{label}</div>
            </div>
          ))}
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-wrap justify-center gap-3 mt-8 mb-6">
          <Link
            href="/order"
            className="px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors min-w-[160px] text-center"
          >
            Get Instant Access
          </Link>
          <a
            href="https://t.me/BuncheBot"
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 bg-[#0088cc] hover:bg-[#006699] text-white font-semibold rounded-xl transition-colors min-w-[160px] text-center"
          >
            Start via Telegram
          </a>
          <a
            href="https://wa.me/2347032981049"
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 bg-[#25D366] hover:bg-[#1da851] text-white font-semibold rounded-xl transition-colors min-w-[160px] text-center"
          >
            Chat on WhatsApp
          </a>
        </div>

        <div className="mb-16"></div>

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

        {/* Comparison — 3D Carousel */}
        <div className="mb-20">
          <h2 className="text-2xl font-bold text-center mb-8">Compare Proxy Types</h2>

          {/* Carousel container */}
          <div className="relative max-w-5xl mx-auto">
            {/* Prev / Next buttons */}
            <button
              onClick={() => setCarouselIdx(i => (i - 1 + 4) % 4)}
              className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-2 sm:-translate-x-14 z-10 w-10 h-10 rounded-full bg-[var(--card)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5"/></svg>
            </button>
            <button
              onClick={() => setCarouselIdx(i => (i + 1) % 4)}
              className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-2 sm:translate-x-14 z-10 w-10 h-10 rounded-full bg-[var(--card)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/></svg>
            </button>

            {/* 3D Carousel Track — swipeable */}
            <div className="overflow-hidden">
              <div
                className="flex transition-transform duration-500 ease-out select-none"
                style={{ transform: `translateX(calc(-${carouselIdx * 25}%))` }}
                onTouchStart={e => {
                  touchStartX.current = e.touches[0].clientX;
                  touchDeltaX.current = 0;
                }}
                onTouchMove={e => {
                  touchDeltaX.current = e.touches[0].clientX - touchStartX.current;
                }}
                onTouchEnd={() => {
                  const threshold = 50;
                  if (touchDeltaX.current < -threshold) setCarouselIdx(i => (i + 1) % 4);
                  else if (touchDeltaX.current > threshold) setCarouselIdx(i => (i - 1 + 4) % 4);
                  touchDeltaX.current = 0;
                }}
              >
                {/* ISP */}
                <div className="w-full flex-shrink-0 px-4 sm:px-16">
                  <div className="relative max-w-sm mx-auto" style={{ perspective: '1200px' }}>
                    <div
                      className="relative bg-[var(--card)] border border-[var(--border)] rounded-2xl p-8 transition-transform duration-500"
                      style={{
                        transformStyle: 'preserve-3d',
                        transform: carouselIdx === 0
                          ? 'rotateY(0deg) scale(1.05) translateZ(30px)'
                          : 'rotateY(15deg) scale(0.95)',
                        opacity: carouselIdx === 0 ? 1 : 0.5,
                        filter: carouselIdx === 0 ? 'none' : 'blur(2px)',
                      }}
                    >
                      <div className="absolute top-0 left-0 right-0 h-1.5 rounded-t-2xl bg-[var(--primary)]" />
                      <div className="flex flex-col items-center text-center">
                        <div className="w-16 h-16 rounded-2xl bg-[var(--primary)]/15 flex items-center justify-center mb-4">
                          <svg className="w-8 h-8 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9 9 0 100-18 9 9 0 000 18z"/><path strokeLinecap="round" strokeLinejoin="round" d="M3.6 9h16.8M3.6 15h16.8M12 3a15.3 15.3 0 014 9 15.3 15.3 0 01-4 9 15.3 15.3 0 01-4-9 15.3 15.3 0 014-9z"/></svg>
                        </div>
                        <h3 className="text-xl font-bold mb-1">ISP Proxies</h3>
                        <p className="text-sm text-[var(--muted)] mb-6">Fast &amp; stable ISP IPs from data centers</p>
                        <div className="w-full space-y-4 mb-6">
                          {[{ label: 'Speed', value: 'High', bar: 90 },{ label: 'Detection Risk', value: 'Low', bar: 30 },{ label: 'Anonymity', value: 'High', bar: 75 },{ label: 'Reliability', value: 'High', bar: 85 }].map(({ label, value, bar }) => (
                            <div key={label}>
                              <div className="flex justify-between text-xs mb-1.5">
                                <span className="text-[var(--muted)]">{label}</span>
                                <span className="font-medium text-[var(--foreground)]">{value}</span>
                              </div>
                              <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                                <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${bar}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="pt-4 border-t border-[var(--border)] w-full">
                          <p className="text-xs text-[var(--muted)] mb-1">From</p>
                          <p className="text-2xl font-bold" style={{ color: 'var(--primary)' }}>N6,500<span className="text-sm font-normal text-[var(--muted)]">/mo</span></p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Residential */}
                <div className="w-full flex-shrink-0 px-4 sm:px-16">
                  <div className="relative max-w-sm mx-auto" style={{ perspective: '1200px' }}>
                    <div
                      className="relative bg-[var(--card)] border border-[var(--border)] rounded-2xl p-8 transition-transform duration-500"
                      style={{
                        transformStyle: 'preserve-3d',
                        transform: carouselIdx === 1
                          ? 'rotateY(0deg) scale(1.05) translateZ(30px)'
                          : 'rotateY(15deg) scale(0.95)',
                        opacity: carouselIdx === 1 ? 1 : 0.5,
                        filter: carouselIdx === 1 ? 'none' : 'blur(2px)',
                      }}
                    >
                      <div className="absolute top-0 left-0 right-0 h-1.5 rounded-t-2xl bg-[var(--primary)]" />
                      <div className="flex flex-col items-center text-center">
                        <div className="w-16 h-16 rounded-2xl bg-[var(--primary)]/15 flex items-center justify-center mb-4">
                          <svg className="w-8 h-8 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"/></svg>
                        </div>
                        <h3 className="text-xl font-bold mb-1">Residential</h3>
                        <p className="text-sm text-[var(--muted)] mb-6">Real home IPs from real devices</p>
                        <div className="w-full space-y-4 mb-6">
                          {[{ label: 'Speed', value: 'Medium', bar: 60 },{ label: 'Detection Risk', value: 'Very Low', bar: 15 },{ label: 'Anonymity', value: 'Very High', bar: 95 },{ label: 'Reliability', value: 'High', bar: 80 }].map(({ label, value, bar }) => (
                            <div key={label}>
                              <div className="flex justify-between text-xs mb-1.5">
                                <span className="text-[var(--muted)]">{label}</span>
                                <span className="font-medium text-[var(--foreground)]">{value}</span>
                              </div>
                              <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                                <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${bar}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="pt-4 border-t border-[var(--border)] w-full">
                          <p className="text-xs text-[var(--muted)] mb-1">From</p>
                          <p className="text-2xl font-bold" style={{ color: 'var(--primary)' }}>N5,000<span className="text-sm font-normal text-[var(--muted)]">/5GB</span></p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Mobile */}
                <div className="w-full flex-shrink-0 px-4 sm:px-16">
                  <div className="relative max-w-sm mx-auto" style={{ perspective: '1200px' }}>
                    <div
                      className="relative bg-[var(--card)] border border-[var(--border)] rounded-2xl p-8 transition-transform duration-500"
                      style={{
                        transformStyle: 'preserve-3d',
                        transform: carouselIdx === 2
                          ? 'rotateY(0deg) scale(1.05) translateZ(30px)'
                          : 'rotateY(15deg) scale(0.95)',
                        opacity: carouselIdx === 2 ? 1 : 0.5,
                        filter: carouselIdx === 2 ? 'none' : 'blur(2px)',
                      }}
                    >
                      <div className="absolute top-0 left-0 right-0 h-1.5 rounded-t-2xl bg-[var(--primary)]" />
                      <div className="flex flex-col items-center text-center">
                        <div className="w-16 h-16 rounded-2xl bg-[var(--primary)]/15 flex items-center justify-center mb-4">
                          <svg className="w-8 h-8 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/><path strokeLinecap="round" strokeLinejoin="round" d="M9 9.563A9 9 0 1112 15.5M15 15.5V18m0-2.5a2.5 2.5 0 10-5 0 2.5 2.5 0 005 0z"/></svg>
                        </div>
                        <h3 className="text-xl font-bold mb-1">Mobile 4G</h3>
                        <p className="text-sm text-[var(--muted)] mb-6">Real 4G/LTE carrier IPs</p>
                        <div className="w-full space-y-4 mb-6">
                          {[{ label: 'Speed', value: 'Medium', bar: 55 },{ label: 'Detection Risk', value: 'Extremely Low', bar: 8 },{ label: 'Anonymity', value: 'Maximum', bar: 100 },{ label: 'Reliability', value: 'High', bar: 80 }].map(({ label, value, bar }) => (
                            <div key={label}>
                              <div className="flex justify-between text-xs mb-1.5">
                                <span className="text-[var(--muted)]">{label}</span>
                                <span className="font-medium text-[var(--foreground)]">{value}</span>
                              </div>
                              <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                                <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${bar}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="pt-4 border-t border-[var(--border)] w-full">
                          <p className="text-xs text-[var(--muted)] mb-1">From</p>
                          <p className="text-2xl font-bold" style={{ color: 'var(--primary)' }}>N20,000<span className="text-sm font-normal text-[var(--muted)]">/5GB</span></p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Datacenter */}
                <div className="w-full flex-shrink-0 px-4 sm:px-16">
                  <div className="relative max-w-sm mx-auto" style={{ perspective: '1200px' }}>
                    <div
                      className="relative bg-[var(--card)] border border-[var(--border)] rounded-2xl p-8 transition-transform duration-500"
                      style={{
                        transformStyle: 'preserve-3d',
                        transform: carouselIdx === 3
                          ? 'rotateY(0deg) scale(1.05) translateZ(30px)'
                          : 'rotateY(15deg) scale(0.95)',
                        opacity: carouselIdx === 3 ? 1 : 0.5,
                        filter: carouselIdx === 3 ? 'none' : 'blur(2px)',
                      }}
                    >
                      <div className="absolute top-0 left-0 right-0 h-1.5 rounded-t-2xl bg-[var(--primary)]" />
                      <div className="flex flex-col items-center text-center">
                        <div className="w-16 h-16 rounded-2xl bg-[var(--primary)]/15 flex items-center justify-center mb-4">
                          <svg className="w-8 h-8 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 12H3m0 0l2-2m-2 2l2 2M19 12h2m0 0l2-2m-2 2l2 2M9 4H7a2 2 0 00-2 2v2m0 8v2a2 2 0 002 2h2m8-16h2a2 2 0 012 2v2m0 8v2a2 2 0 01-2 2h-2"/></svg>
                        </div>
                        <h3 className="text-xl font-bold mb-1">Datacenter</h3>
                        <p className="text-sm text-[var(--muted)] mb-6">Budget cloud server IPs</p>
                        <div className="w-full space-y-4 mb-6">
                          {[{ label: 'Speed', value: 'Very High', bar: 95 },{ label: 'Detection Risk', value: 'High', bar: 70 },{ label: 'Anonymity', value: 'Medium', bar: 45 },{ label: 'Reliability', value: 'High', bar: 85 }].map(({ label, value, bar }) => (
                            <div key={label}>
                              <div className="flex justify-between text-xs mb-1.5">
                                <span className="text-[var(--muted)]">{label}</span>
                                <span className="font-medium text-[var(--foreground)]">{value}</span>
                              </div>
                              <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                                <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${bar}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="pt-4 border-t border-[var(--border)] w-full">
                          <p className="text-xs text-[var(--muted)] mb-1">From</p>
                          <p className="text-2xl font-bold" style={{ color: 'var(--primary)' }}>N3,500<span className="text-sm font-normal text-[var(--muted)]">/mo</span></p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Dot indicators */}
            <div className="flex justify-center gap-2 mt-6">
              {[0,1,2,3].map(i => (
                <button
                  key={i}
                  onClick={() => setCarouselIdx(i)}
                  className="h-2 rounded-full transition-all duration-300"
                  style={{
                    width: carouselIdx === i ? 24 : 8,
                    background: carouselIdx === i ? 'var(--primary)' : 'var(--border)',
                  }}
                />
              ))}
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
                      {product.country !== 'GLOBAL' ? COUNTRIES[product.country]?.name || product.country : '🌍'}
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
