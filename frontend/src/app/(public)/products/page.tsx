'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { loadCatalog, formatPrice, COUNTRIES, type CountryInfo } from '@/lib/products';
import { useChannelFlags } from '@/lib/feature-flags';
import type { Product, CatalogTemplate } from '@/types';
import { Globe, House, HardDrives, Clock, Lightning, Rocket, Check, CaretLeft, CaretRight } from '@phosphor-icons/react';

// Build dynamic categories from the catalog (BE-driven — no hardcoded ISP/MOBILE)
function buildCategories(templates: CatalogTemplate[]) {
  const labels: Record<string, { name: string; description: string; price: string }> = {
    datacenter: {
      name: 'Datacenter',
      description: 'Fast datacenter proxies for general purpose use',
      price: 'From ₦3,500',
    },
    residential: {
      name: 'Residential',
      description: 'Real residential IPs. Harder to detect and block.',
      price: 'From ₦5,000',
    },
  };

  return templates.map((t) => {
    const meta = labels[t.plan_type] || {
      name: t.plan_type.charAt(0).toUpperCase() + t.plan_type.slice(1),
      description: `${t.plan_type} proxies`,
      price: 'View pricing',
    };
    const countries = (t.available_countries || [])
      .map((c) => COUNTRIES[c] || COUNTRIES[c.replace('GB', 'UK')])
      .filter(Boolean) as CountryInfo[];
    return {
      key: t.plan_type,
      icon: getIcon(t.plan_type),
      name: meta.name,
      description: meta.description,
      price: meta.price,
      features: buildFeatures(t),
      countryCount: countries.length,
      countries,
    };
  });
}

function getIcon(planType: string) {
  if (planType === 'residential') {
    return <House className="w-8 h-8" weight="regular" />;
  }
  if (planType === 'datacenter') {
    return <HardDrives className="w-8 h-8" weight="regular" />;
  }
  return <Globe className="w-8 h-8" weight="regular" />;
}

function buildFeatures(t: CatalogTemplate): string[] {
  const features = [`Up to ${t.base_quantity_gb}GB included`];
  if (t.rotation_mode_options.includes('static')) {
    features.push('Static IP. Same address every request.');
  }
  if (t.rotation_mode_options.includes('rotating')) {
    features.push('Rotating pool. IP changes per request.');
  }
  if (t.plan_type === 'datacenter') {
    features.push('Lightning fast speeds');
    features.push('HTTP/SOCKS5 support');
  } else if (t.plan_type === 'residential') {
    features.push('Highest success rate');
    features.push('Ideal for sneakers and ticketing');
  }
  return features;
}

export default function ProductsPage() {
  const [activeProduct, setActiveProduct] = useState<string | null>(null);
  const [carouselIdx, setCarouselIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [catalogProducts, setCatalogProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<ReturnType<typeof buildCategories>>([]);
  const touchStartX = useRef(0);
  const touchDeltaX = useRef(0);

  const { isChannelEnabled, getChannelUrl } = useChannelFlags();

  useEffect(() => {
    loadCatalog()
      .then((products) => {
        setCatalogProducts(products);
        return fetch('/api/catalog', { cache: 'no-store' }).then((r) => r.json());
      })
      .then((data) => {
        const cats = buildCategories(data.templates || []);
        setCategories(cats);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load catalog:', err);
        setError('Failed to load products. Please refresh.');
        setLoading(false);
      });
  }, []);

  const totalCountries = new Set(
    categories.flatMap((c) => c.countries.map((g) => g.code))
  ).size;

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

  const activeCats = categories.length > 0 ? categories : [];

  return (
    <div className="min-h-screen">
      {/* Page hero with background */}
      <div className="relative overflow-hidden pt-24 pb-12 px-4">
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-rings" />
        <div className="absolute inset-0 hero-bg-vignette" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 hero-orb-1" />
        <div className="absolute bottom-1/3 right-1/4 w-80 h-80 hero-orb-2" />

        <div className="relative max-w-7xl mx-auto">
          {/* Page Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl sm:text-5xl font-bold mb-4 leading-tight">
              Lightning-fast proxies,<br />
              <span className="text-[var(--primary)]">built to scale.</span>
            </h1>
            <p className="text-base sm:text-lg mb-6 text-[var(--muted)]">
              {activeProduct
                ? <>Showing coverage for <span className="font-medium text-[var(--foreground)]">{activeCats.find(c => c.key === activeProduct)?.name}</span>. Click another card to switch.</>
                : <>{activeCats.map(c => c.name).join(', ')} proxies. Available in <span className="font-medium text-[var(--foreground)]">{totalCountries}+ countries</span> worldwide.</>
              }
            </p>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto">
            {[
              { label: 'Uptime', value: '99.9%', icon: <Clock className="w-6 h-6 text-[var(--primary)] mx-auto" weight="regular" /> },
              { label: 'IP Pool', value: '50K+ IPs', icon: <Globe className="w-6 h-6 text-[var(--primary)] mx-auto" weight="regular" /> },
              { label: 'Speed', value: '1 Gbps', icon: <Lightning className="w-6 h-6 text-[var(--primary)] mx-auto" weight="regular" /> },
              { label: 'Delivery', value: 'Instant', icon: <Rocket className="w-6 h-6 text-[var(--primary)] mx-auto" weight="regular" /> },
            ].map(({ label, value, icon }) => (
              <div key={label} className="bg-[var(--card)] border border-[var(--border)] rounded-xl px-3 py-3 text-center card-depth">
                <div className="mb-1 flex justify-center">{icon}</div>
                <div className="text-xl font-bold text-[var(--primary)]">{value}</div>
                <div className="text-xs text-[var(--muted)]">{label}</div>
              </div>
            ))}
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-wrap justify-center gap-3 mt-8 mb-6">
            <Link href="/order" className="min-w-[200px] px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-all duration-200 text-center">
              Get Instant Access
            </Link>
            {isChannelEnabled('telegram') ? (
              <a href={getChannelUrl('telegram') || 'https://t.me/StyxproxyBot'} target="_blank" rel="noopener noreferrer" className="min-w-[200px] px-6 py-3 bg-[#0088cc] hover:bg-[#006699] text-white font-semibold rounded-xl transition-all duration-200 text-center">
                Start via Telegram
              </a>
            ) : (
              <span className="min-w-[200px] px-6 py-3 bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] font-semibold rounded-xl text-center">
                Telegram (coming soon)
              </span>
            )}
            {isChannelEnabled('whatsapp') ? (
              <a href={getChannelUrl('whatsapp') || 'https://wa.me/2347032981049'} target="_blank" rel="noopener noreferrer" className="min-w-[200px] px-6 py-3 bg-[#25D366] hover:bg-[#1da851] text-white font-semibold rounded-xl transition-all duration-200 text-center">
                Chat on WhatsApp
              </a>
            ) : (
              <span className="min-w-[200px] px-6 py-3 bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] font-semibold rounded-xl text-center">
                WhatsApp (coming soon)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="mb-16"></div>

        {/* Product Category Cards */}
        {activeCats.length > 0 && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
            {activeCats.map((category) => {
              const isActive = activeProduct === category.key;
              return (
                <button
                  key={category.key}
                  type="button"
                  onClick={() => setActiveProduct(isActive ? null : category.key)}
                  className={`text-left bg-[var(--card)] border rounded-2xl p-6 flex flex-col transition-all ${
                    isActive
                      ? 'border-[var(--primary)] ring-2 ring-[var(--primary)]/30'
                      : 'border-[var(--border)] hover:border-[var(--primary)]'
                  }`}
                  style={{ boxShadow: isActive ? '0 0 0 1px var(--primary), 0 4px 16px rgba(10,210,90,0.1)' : undefined }}
                >
                  <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] mb-4">
                    {category.icon}
                  </div>
                  <h3 className="text-lg font-bold mb-2">{category.name}</h3>
                  <p className="text-sm text-[var(--muted)] mb-4">{category.description}</p>
                  <div className="text-lg font-semibold text-[var(--primary)] mb-4">
                    {category.price}
                  </div>
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-[var(--muted)]">Available in:</span>
                      <span className="text-xs font-semibold text-[var(--primary)]">
                        {category.countryCount} countries
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {category.countries.slice(0, 8).map((c) => (
                        <span
                          key={c.code}
                          title={c.name}
                          className="inline-flex items-center justify-center w-7 h-7 rounded-md bg-[var(--background)] border border-[var(--border)] text-base leading-none"
                        >
                          {c.flag}
                        </span>
                      ))}
                      {category.countryCount > 8 && (
                        <span className="inline-flex items-center justify-center w-7 h-7 rounded-md bg-[var(--background)] border border-[var(--border)] text-xs text-[var(--muted)]">
                          +{category.countryCount - 8}
                        </span>
                      )}
                    </div>
                  </div>
                  <ul className="space-y-2 mb-6 flex-1">
                    {category.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-[var(--muted)]">
                        <Check className="w-4 h-4 text-[var(--primary)] mt-0.5 flex-shrink-0" weight="bold" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Link
                    href="/order"
                    onClick={(e) => e.stopPropagation()}
                    className="w-full px-4 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-all duration-200 text-center"
                  >
                    {isActive ? 'Showing on globe' : 'Order Now →'}
                  </Link>
                </button>
              );
            })}
          </div>
        )}

        {/* Comparison — 3D Carousel */}
        {activeCats.length > 0 && (
          <div className="mb-20">
            <h2 className="text-2xl font-bold text-center mb-8">Compare Proxy Types</h2>
            <div className="relative max-w-3xl mx-auto">
              <button
                onClick={() => setCarouselIdx(i => (i - 1 + activeCats.length) % activeCats.length)}
                className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-4 sm:-translate-x-16 z-10 w-11 h-11 rounded-full bg-[var(--card)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] hover:bg-[var(--card-hover)] transition-all duration-200"
              >
                <CaretLeft className="w-5 h-5" weight="bold" />
              </button>
              <button
                onClick={() => setCarouselIdx(i => (i + 1) % activeCats.length)}
                className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-4 sm:translate-x-16 z-10 w-11 h-11 rounded-full bg-[var(--card)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] hover:bg-[var(--card-hover)] transition-all duration-200"
              >
                <CaretRight className="w-5 h-5" weight="bold" />
              </button>
              <div
                className="relative select-none"
                style={{ height: 420, perspective: '1000px' }}
                onTouchStart={e => { touchStartX.current = e.touches[0].clientX; touchDeltaX.current = 0; }}
                onTouchMove={e => { touchDeltaX.current = e.touches[0].clientX - touchStartX.current; }}
                onTouchEnd={() => {
                  const threshold = 60;
                  if (touchDeltaX.current < -threshold) setCarouselIdx(i => (i + 1) % activeCats.length);
                  else if (touchDeltaX.current > threshold) setCarouselIdx(i => (i - 1 + activeCats.length) % activeCats.length);
                  touchDeltaX.current = 0;
                }}
              >
                {activeCats.map((cat, idx) => (
                  <div
                    key={cat.key}
                    className="absolute inset-0 bg-[var(--card)] border rounded-2xl p-6 flex flex-col transition-all duration-500"
                    style={{
                      transform: carouselIdx === idx
                        ? 'translateZ(0px) scale(1) rotateY(0deg)'
                        : carouselIdx === (idx + 1) % activeCats.length
                        ? 'translateZ(-60px) scale(0.88) rotateY(18deg) translateX(30px)'
                        : carouselIdx === (idx - 1 + activeCats.length) % activeCats.length
                        ? 'translateZ(-60px) scale(0.88) rotateY(-18deg) translateX(-30px)'
                        : 'translateZ(-80px) scale(0.82)',
                      opacity: carouselIdx === idx ? 1 : 0.4,
                      pointerEvents: carouselIdx === idx ? 'auto' : 'none',
                      zIndex: carouselIdx === idx ? 4 : 1,
                      boxShadow: carouselIdx === idx
                        ? '0 4px 12px rgba(0,0,0,0.6), 0 12px 40px rgba(0,0,0,0.5)'
                        : '0 1px 3px rgba(0,0,0,0.4)',
                    }}
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-xl bg-[var(--primary)]/15 flex items-center justify-center flex-shrink-0 text-[var(--primary)]">
                        {cat.icon}
                      </div>
                      <div>
                        <h3 className="font-bold">{cat.name}</h3>
                        <p className="text-xs text-[var(--muted)]">{cat.description}</p>
                      </div>
                      <div className="ml-auto">
                        <span className="text-lg font-bold text-[var(--primary)]">{cat.price.split(' ')[0]}</span>
                      </div>
                    </div>
                    <div className="flex-1 space-y-2.5">
                      {cat.features.slice(0, 4).map((f, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm text-[var(--muted)]">
                          <Check className="w-3 h-3 text-[var(--primary)] flex-shrink-0" weight="bold" />
                          {f}
                        </div>
                      ))}
                    </div>
                    <Link href="/order" onClick={e => e.stopPropagation()} className="mt-4 w-full py-2.5 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl text-sm text-center transition-all duration-200">
                      Order {cat.name} →
                    </Link>
                  </div>
                ))}
              </div>
              <div className="flex justify-center gap-2 mt-6">
                {activeCats.map((_, i) => (
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
        )}

        {/* All Products & Pricing */}
        {catalogProducts.length > 0 && (
          <div className="mb-20">
            <h2 className="text-2xl font-bold text-center mb-8">All Products and Pricing</h2>
            <div className="space-y-10">
              {activeCats.map((cat) => {
                const catProducts = catalogProducts.filter(
                  (p) => p.plan_type.toUpperCase() === cat.key.toUpperCase()
                );
                if (catProducts.length === 0) return null;
                return (
                  <div key={cat.key}>
                    <div className="flex items-center gap-2 mb-4">
                      <div className="w-8 h-8 rounded-lg bg-[var(--primary)]/15 flex items-center justify-center text-[var(--primary)]">
                        {cat.icon}
                      </div>
                      <h3 className="font-bold text-lg">{cat.name}</h3>
                      <span className="ml-auto text-xs text-[var(--muted)] bg-[var(--card)] border border-[var(--border)] rounded-full px-3 py-1">
                        {catProducts.length} plans
                      </span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {catProducts.map((product) => (
                        <div key={product.plan_code} className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 hover:border-[var(--primary)] transition-all duration-200 card-depth">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <span className="text-lg">{product.flag}</span>
                              <div>
                                <p className="font-semibold text-sm">
                                  {COUNTRIES[product.country]?.name || product.country}
                                </p>
                                <p className="text-xs text-[var(--muted)]">{product.features[0]}</p>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-xs text-[var(--muted)] mb-0.5">Starting from</p>
                              <p className="text-lg font-bold text-[var(--primary)]">
                                {formatPrice(product.price_ngn)}
                              </p>
                            </div>
                            <Link
                              href={`/order?plan=${product.plan_code}`}
                              className="px-3 py-1.5 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-lg text-xs transition-all duration-200"
                            >
                              Order
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* CTA Section */}
        <div className="mt-20 p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)] text-center card-depth">
          <h2 className="text-2xl font-bold mb-4">Need Help Choosing?</h2>
          <p className="text-[var(--muted)] mb-6 max-w-xl mx-auto">
            Tell us what you need and we will recommend the right proxy type and country mix.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/order" className="min-w-[200px] px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-all duration-200 text-center">
              Start Ordering
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
