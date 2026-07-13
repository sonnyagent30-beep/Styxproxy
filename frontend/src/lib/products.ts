import { Product } from '@/types';

export const products: Product[] = [
  // ISP Proxies - UK/US/DE/FR/CA
  {
    plan_code: 'ISP-UK-1',
    plan_type: 'ISP',
    groupKey: 'ISP',
    country: 'UK',
    flag: '🇬🇧',
    price_ngn: 6500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
  },
  {
    plan_code: 'ISP-US-1',
    plan_type: 'ISP',
    groupKey: 'ISP',
    country: 'US',
    flag: '🇺🇸',
    price_ngn: 6500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
  },
  {
    plan_code: 'ISP-DE-1',
    plan_type: 'ISP',
    groupKey: 'ISP',
    country: 'DE',
    flag: '🇩🇪',
    price_ngn: 6500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
  },
  {
    plan_code: 'ISP-FR-1',
    plan_type: 'ISP',
    groupKey: 'ISP',
    country: 'FR',
    flag: '🇫🇷',
    price_ngn: 6500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
  },
  {
    plan_code: 'ISP-CA-1',
    plan_type: 'ISP',
    groupKey: 'ISP',
    country: 'CA',
    flag: '🇨🇦',
    price_ngn: 6500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
  },
  // ISP Proxies - JP/AU/BR/SG
  {
    plan_code: 'ISP-JP-1',
    plan_type: 'ISP',
    groupKey: 'ISP',
    country: 'JP',
    flag: '🇯🇵',
    price_ngn: 7500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
  },
  {
    plan_code: 'ISP-AU-1',
    plan_type: 'ISP',
    groupKey: 'ISP',
    country: 'AU',
    flag: '🇦🇺',
    price_ngn: 7500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
  },
  {
    plan_code: 'ISP-BR-1',
    plan_type: 'ISP',
    groupKey: 'ISP',
    country: 'BR',
    flag: '🇧🇷',
    price_ngn: 7500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
  },
  {
    plan_code: 'ISP-SG-1',
    plan_type: 'ISP',
    groupKey: 'ISP',
    country: 'SG',
    flag: '🇸🇬',
    price_ngn: 7500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
  },
  // Residential Proxies
  {
    plan_code: 'RES-5GB',
    plan_type: 'RESIDENTIAL',
    groupKey: 'RESIDENTIAL',
    country: 'GLOBAL',
    flag: '🌍',
    price_ngn: 5000,
    quantity: 5,
    duration_days: 30,
    features: ['5GB Data', 'No expiry until used', 'Residential IPs'],
  },
  {
    plan_code: 'RES-10GB',
    plan_type: 'RESIDENTIAL',
    groupKey: 'RESIDENTIAL',
    country: 'GLOBAL',
    flag: '🌍',
    price_ngn: 9000,
    quantity: 10,
    duration_days: 30,
    features: ['10GB Data', 'No expiry until used', 'Residential IPs'],
  },
  // Mobile 4G Proxies
  {
    plan_code: 'MOB-4G-5GB',
    plan_type: 'MOBILE',
    groupKey: 'MOBILE',
    country: 'GLOBAL',
    flag: '📱',
    price_ngn: 20000,
    quantity: 5,
    duration_days: 30,
    features: ['5GB 4G Data', '30-day window', 'Mobile IPs'],
  },
  {
    plan_code: 'MOB-4G-10GB',
    plan_type: 'MOBILE',
    groupKey: 'MOBILE',
    country: 'GLOBAL',
    flag: '📱',
    price_ngn: 35000,
    quantity: 10,
    duration_days: 30,
    features: ['10GB 4G Data', '30-day window', 'Mobile IPs'],
  },
  // Datacenter
  {
    plan_code: 'DC-1',
    plan_type: 'DC',
    groupKey: 'DC',
    country: 'GLOBAL',
    flag: '🏢',
    price_ngn: 2500,
    quantity: 1,
    duration_days: 30,
    features: ['Datacenter Proxy', '30-day expiry', 'Fast speeds'],
  },
];

export const getProductsByType = (type: string): Product[] => {
  return products.filter(p => p.plan_type === type);
};

export const getProductsByGroup = (group: string): Product[] => {
  return products.filter(p => p.groupKey === group);
};

export const getProductByCode = (code: string): Product | undefined => {
  return products.find(p => p.plan_code === code);
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
// Countries available per product type
// =============================================================
// Sourced from upstream provider coverage (Jul 2026):
// - ISP and Datacenter: full country coverage at provider-side
// - Residential: ~195 countries available; curated subset below
// - Mobile: ~100 countries available; curated subset below
//
// Below we surface a curated subset for the globe and order picker.
// =============================================================
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
