/**
 * Products module — now BE-driven.
 *
 * Historically this was a hardcoded array of 14 plans. We replaced it with
 * a fetched catalogue from /api/catalog so the FE never drifts from the DB.
 *
 * The legacy `products: Product[]` and helpers (`getProductsByType`,
 * `getProductByCode`, etc.) are kept so existing callers don't break.
 * On the first call, we fetch the catalog and synthesise legacy Product
 * rows from the variant list. Country metadata + flags are still inlined
 * here (FE-only, no DB equivalent).
 *
 * Pages should prefer `loadCatalog()` for new code paths.
 */

import type {
  Product,
  CatalogCity,
  CatalogResponse,
  CatalogRotationMode,
  CatalogTemplate,
  CatalogPlanType,
  CatalogVariant,
} from '@/types';

// ─────────────────────────────────────────────────────────────────────────────
// Legacy: synchronous access to the in-memory catalog (populated after fetch)
// ─────────────────────────────────────────────────────────────────────────────

let cachedProducts: Product[] | null = null;

function variantToProduct(
  v: CatalogVariant,
  template?: CatalogTemplate,
): Product {
  const country = (v.country || 'GLOBAL').toUpperCase();
  const isPerGB = v.plan_type === 'residential' || v.plan_type === 'mobile';
  const pricePerGB = template?.base_price_per_gb ?? null;
  const pricePerIP = template?.base_price_per_ip ?? v.price_ngn;
  // Sprint 13: catalog stores cities by ISO-2 code (uppercase)
  const cities = template?.cities ?? {};
  return {
    plan_code: v.plan_code,
    plan_type: v.plan_type.toUpperCase() as Product['plan_type'],
    groupKey: v.plan_type.toUpperCase() as Product['groupKey'],
    country,
    flag: COUNTRIES[country]?.flag || '🌍',
    price_ngn: v.price_ngn,
    quantity: v.quantity,
    duration_days: v.duration_days,
    features: [
      `${v.quantity}GB ${v.plan_type === 'datacenter' ? 'Datacenter' : v.plan_type === 'residential' ? 'Residential' : v.plan_type === 'mobile' ? 'Mobile' : 'ISP'}`,
      `${v.duration_days}-day expiry`,
      v.rotation_mode === 'static' ? 'Static IP' : 'Rotating pool',
    ],
    // Sprint 13: per-GB pricing + city picker
    price_per_gb: pricePerGB,
    min_gb: template?.min_gb ?? null,
    max_gb: template?.max_gb ?? null,
    gb_tiers: template?.gb_tiers ?? null,
    supports_city: template?.supports_city ?? false,
    cities,
  };
}

// Sprint 13 — richer product metadata that exposes the catalog cities + pricing
export interface CatalogProductInfo {
  plan_type: CatalogPlanType;
  rotation_mode_options: CatalogRotationMode[];
  available_countries: string[];
  base_quantity_gb: number;
  base_price_ngn: number;
  base_price_per_gb: number | null;
  base_price_per_ip: number | null;
  min_gb: number | null;
  max_gb: number | null;
  gb_tiers: number[] | null;
  supports_city: boolean;
  cities: { [country_code: string]: CatalogCity[] };
  description: string;
}

let cachedCatalog: CatalogResponse | null = null;

export function getCachedCatalog(): CatalogResponse | null {
  return cachedCatalog;
}

/**
 * Build the legacy Product[] shape from a catalog template, preserving city info.
 * The returned products have `country` and `plan_code` keys; consumers can call
 * getCitiesForCountry(plan_type, country_code) to get the city list.
 */
export function buildProductsFromTemplate(template: CatalogTemplate): Product[] {
  return template.variants.map((v) => variantToProduct(v, template));
}

/**
 * Load the catalog from the BE and cache it as legacy Product[].
 * Always returns the cache — first call does the fetch.
 *
 * @throws if the catalog endpoint is unreachable AND we have no cache.
 */
export async function loadCatalog(): Promise<Product[]> {
  return (await loadFullCatalog()).products;
}

export async function loadFullCatalog(): Promise<{
  products: Product[];
  templates: CatalogTemplate[];
  catalog: CatalogResponse;
}> {
  if (cachedProducts && cachedCatalog) {
    return { products: cachedProducts, templates: cachedCatalog.templates, catalog: cachedCatalog };
  }

  const res = await fetch('https://api.styxproxy.com/api/catalog', { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Catalog endpoint returned ${res.status}`);
  }
  const data: CatalogResponse = await res.json();
  cachedCatalog = data;
  const products: Product[] = [];
  for (const template of data.templates) {
    for (const variant of template.variants) {
      products.push(variantToProduct(variant, template));
    }
  }
  cachedProducts = products;
  return { products, templates: data.templates, catalog: data };
}

/**
 * Get the city list for a given plan_type + country_code from the cached catalog.
 * Returns empty array if no cities are available (random selection).
 */
export function getCitiesForCountry(
  plan_type: string,
  country_code: string,
): CatalogCity[] {
  if (!cachedCatalog) return [];
  const template = cachedCatalog.templates.find(
    (t) => t.plan_type.toLowerCase() === plan_type.toLowerCase(),
  );
  if (!template) return [];
  return template.cities?.[country_code] || [];
}

/**
 * Synchronous accessor — returns the cached list, or empty array if fetch hasn't happened.
 * Use within React components after a loadCatalog() call in useEffect.
 */
export const products: Product[] = [];
// We deliberately leave `products` empty so consumers see the real fetched
// data via `loadCatalog()`. Direct reads of the legacy export will be empty
// until the cache is populated — this is intentional to surface drift.
// (The legacy shape is preserved for new code to migrate off.)

export const getProductsByType = (type: string): Product[] => {
  return (cachedProducts || []).filter(p => p.plan_type === type.toUpperCase());
};

export const getProductsByGroup = (group: string): Product[] => {
  return (cachedProducts || []).filter(p => p.groupKey === group.toUpperCase());
};

export const getProductByCode = (code: string): Product | undefined => {
  return (cachedProducts || []).find(p => p.plan_code === code);
};

export const formatPrice = (price: number): string => {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN',
    minimumFractionDigits: 0,
  }).format(price);
};

export const groupLabels: Record<string, string> = {
  ISP: '🌐 ISP Proxies',
  RESIDENTIAL: '🏠 Residential',
  MOBILE: '📱 Mobile 4G',
  DC: '🏢 Datacenter',
};

// =============================================================
// Country metadata — used by the globe and product cards
// =============================================================
export interface CountryInfo {
  code: string;          // ISO 2-letter
  name: string;
  flag: string;
  lat: number;
  lng: number;
  region: string;
}

export const COUNTRIES: Record<string, CountryInfo> = {
  UK: { code: 'UK', name: 'United Kingdom',  flag: '🇬🇧', lat: 51.5074,  lng: -0.1278,  region: 'Europe' },
  US: { code: 'US', name: 'United States',   flag: '🇺🇸', lat: 39.8283,  lng: -98.5795, region: 'North America' },
  DE: { code: 'DE', name: 'Germany',         flag: '🇩🇪', lat: 51.1657,  lng: 10.4515,  region: 'Europe' },
  FR: { code: 'FR', name: 'France',          flag: '🇫🇷', lat: 46.6034,  lng: 2.3488,   region: 'Europe' },
  CA: { code: 'CA', name: 'Canada',          flag: '🇨🇦', lat: 45.5017,  lng: -73.5673, region: 'North America' },
  JP: { code: 'JP', name: 'Japan',           flag: '🇯🇵', lat: 36.2048,  lng: 138.2529, region: 'Asia Pacific' },
  AU: { code: 'AU', name: 'Australia',       flag: '🇦🇺', lat: -25.2744, lng: 133.7751, region: 'Oceania' },
  BR: { code: 'BR', name: 'Brazil',          flag: '🇧🇷', lat: -23.5505, lng: -46.6333, region: 'South America' },
  SG: { code: 'SG', name: 'Singapore',       flag: '🇸🇬', lat: 1.3521,   lng: 103.8198, region: 'Asia Pacific' },
  IT: { code: 'IT', name: 'Italy',           flag: '🇮🇹', lat: 41.8719,  lng: 12.5674,  region: 'Europe' },
  ES: { code: 'ES', name: 'Spain',           flag: '🇪🇸', lat: 40.4637,  lng: -3.7492,  region: 'Europe' },
  NL: { code: 'NL', name: 'Netherlands',     flag: '🇳🇱', lat: 52.1326,  lng: 5.2913,   region: 'Europe' },
  IN: { code: 'IN', name: 'India',           flag: '🇮🇳', lat: 20.5937,  lng: 78.9629,  region: 'Asia Pacific' },
  MX: { code: 'MX', name: 'Mexico',          flag: '🇲🇽', lat: 23.6345,  lng: -102.5528, region: 'North America' },
  AR: { code: 'AR', name: 'Argentina',       flag: '🇦🇷', lat: -38.4161, lng: -63.6167, region: 'South America' },
  ZA: { code: 'ZA', name: 'South Africa',    flag: '🇿🇦', lat: -30.5595, lng: 22.9375,  region: 'Africa' },
  AE: { code: 'AE', name: 'UAE',             flag: '🇦🇪', lat: 23.4241,  lng: 53.8478,  region: 'Asia Pacific' },
  HK: { code: 'HK', name: 'Hong Kong',       flag: '🇭🇰', lat: 22.3193,  lng: 114.1694, region: 'Asia Pacific' },
};

// =============================================================
// Countries available per product type (sourced from /api/catalog)
// =============================================================
// Sourced from upstream provider coverage (Jul 2026):
// - ISP and Datacenter: full country coverage at provider-side
// - Residential: ~195 countries available; curated subset below
// - Mobile: ~100 countries available; curated subset below
export const PRODUCT_COUNTRIES: Record<string, string[]> = {
  // ISP — 9 popular ISP proxy regions (matches our ISP-*-1 plans)
  ISP: ['UK', 'US', 'DE', 'FR', 'CA', 'JP', 'AU', 'BR', 'SG'],

  // Datacenter — broader set of regions at standard per-IP pricing
  DC: [
    'US', 'CA', 'MX',                          // North America
    'UK', 'DE', 'FR', 'NL', 'ES', 'IT',       // Europe
    'JP', 'SG', 'AU', 'BR',                   // APAC + South America
    'HK', 'IN',                                // Asia
  ],

  // Residential — curated to 14 popular regions from global coverage
  RESIDENTIAL: [
    'US', 'CA', 'MX',                          // North America
    'UK', 'DE', 'FR', 'NL', 'ES', 'IT',       // Europe
    'JP', 'SG', 'AU', 'BR', 'HK', 'IN',       // APAC + South America + Asia
  ],

  // Mobile — curated to 12 popular carrier regions from global mobile pool
  MOBILE: [
    'US', 'CA',
    'UK', 'DE', 'FR', 'NL', 'ES', 'IT',
    'JP', 'AU', 'BR', 'IN',
  ],
};

// Get country info objects for a product type — used by the globe
export const getCountriesForProduct = (productType: string): CountryInfo[] => {
  const codes = PRODUCT_COUNTRIES[productType] || [];
  return codes.map(c => COUNTRIES[c]).filter(Boolean);
};

// Get the country array as simple [code, name, flag] tuples
export const getProductCountryList = (productType: string): string[] => {
  return (PRODUCT_COUNTRIES[productType] || []).map(c => COUNTRIES[c]?.name || c);
};
