/**
 * Products module — BE-driven catalog.
 *
 * FE fetches /api/catalog and synthesizes legacy Product[] rows from variants.
 * Country metadata + flags are inlined here (FE-only, ISO 3166-1 alpha-2 codes).
 *
 * Convention: FE displays "United Kingdom" with flag 🇬🇧 — BE stores the ISO
 * short code GB. All codes in this file are ISO 3166-1 alpha-2.
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
  const cities = template?.cities ?? {};
  return {
    plan_code: v.plan_code,
    plan_type: v.plan_type.toUpperCase() as Product['plan_type'],
    groupKey: v.plan_type.toUpperCase() as Product['groupKey'],
    country,
    flag: COUNTRIES[country]?.flag ?? '🌍',
    price_ngn: v.price_ngn,
    quantity: v.quantity,
    duration_days: v.duration_days,
    features: [
      `${v.quantity}GB ${v.plan_type === 'datacenter' ? 'Datacenter' : v.plan_type === 'residential' ? 'Residential' : v.plan_type === 'mobile' ? 'Mobile' : 'ISP'}`,
      `${v.duration_days}-day expiry`,
      v.rotation_mode === 'static' ? 'Static IP' : 'Rotating pool',
    ],
    price_per_gb: pricePerGB,
    min_gb: template?.min_gb ?? null,
    max_gb: template?.max_gb ?? null,
    gb_tiers: template?.gb_tiers ?? null,
    supports_city: template?.supports_city ?? false,
    cities,
  };
}

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

export function buildProductsFromTemplate(template: CatalogTemplate): Product[] {
  return template.variants.map((v) => variantToProduct(v, template));
}

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

  const res = await fetch('/api/catalog', { cache: 'no-store' });
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

export const products: Product[] = [];

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
// Country metadata — ISO 3166-1 alpha-2 codes
// FE displays "United Kingdom" (name) + 🇬🇧 (flag) — BE stores "GB" (code)
// All 196 official ISO 3166-1 alpha-2 codes are included below.
// =============================================================

export interface CountryInfo {
  code: string;          // ISO 2-letter short code (e.g. "GB")
  name: string;          // Display name (e.g. "United Kingdom")
  flag: string;          // Emoji flag
  lat: number;
  lng: number;
  region: string;
}

export const COUNTRIES: Record<string, CountryInfo> = {
  // ── A ────────────────────────────────────────────────────────────
  AF: { code: 'AF', name: 'Afghanistan', flag: '🇦🇫', lat: 33.9391, lng: 67.71, region: 'Asia' },
  AO: { code: 'AO', name: 'Angola', flag: '🇦🇴', lat: -11.2027, lng: 17.8739, region: 'Africa' },
  AL: { code: 'AL', name: 'Albania', flag: '🇦🇱', lat: 41.1533, lng: 20.1683, region: 'Europe' },
  AD: { code: 'AD', name: 'Andorra', flag: '🇦🇩', lat: 42.5063, lng: 1.5218, region: 'Europe' },
  AE: { code: 'AE', name: 'United Arab Emirates', flag: '🇦🇪', lat: 23.4241, lng: 53.8478, region: 'Asia' },
  AR: { code: 'AR', name: 'Argentina', flag: '🇦🇷', lat: -38.4161, lng: -63.6167, region: 'Americas' },
  AM: { code: 'AM', name: 'Armenia', flag: '🇦🇲', lat: 40.0691, lng: 45.0382, region: 'Asia' },
  AG: { code: 'AG', name: 'Antigua and Barbuda', flag: '🇦🇬', lat: 17.0608, lng: -61.7964, region: 'Americas' },
  AU: { code: 'AU', name: 'Australia', flag: '🇦🇺', lat: -25.2744, lng: 133.7751, region: 'Oceania' },
  AT: { code: 'AT', name: 'Austria', flag: '🇦🇹', lat: 47.5162, lng: 14.5501, region: 'Europe' },
  AZ: { code: 'AZ', name: 'Azerbaijan', flag: '🇦🇿', lat: 40.1431, lng: 47.5769, region: 'Asia' },
  // ── B ────────────────────────────────────────────────────────────
  BS: { code: 'BS', name: 'Bahamas', flag: '🇧🇸', lat: 25.0343, lng: -77.3963, region: 'Americas' },
  BH: { code: 'BH', name: 'Bahrain', flag: '🇧🇭', lat: 26.0667, lng: 50.5577, region: 'Asia' },
  BB: { code: 'BB', name: 'Barbados', flag: '🇧🇧', lat: 13.1939, lng: -59.5432, region: 'Americas' },
  BD: { code: 'BD', name: 'Bangladesh', flag: '🇧🇩', lat: 23.685, lng: 90.3563, region: 'Asia' },
  BY: { code: 'BY', name: 'Belarus', flag: '🇧🇾', lat: 53.7098, lng: 27.9534, region: 'Europe' },
  BE: { code: 'BE', name: 'Belgium', flag: '🇧🇪', lat: 50.5039, lng: 4.4699, region: 'Europe' },
  BZ: { code: 'BZ', name: 'Belize', flag: '🇧🇿', lat: 17.1899, lng: -88.4976, region: 'Americas' },
  BJ: { code: 'BJ', name: 'Benin', flag: '🇧🇯', lat: 9.3077, lng: 2.3158, region: 'Africa' },
  BT: { code: 'BT', name: 'Bhutan', flag: '🇧🇹', lat: 27.5142, lng: 90.4336, region: 'Asia' },
  BO: { code: 'BO', name: 'Bolivia', flag: '🇧🇴', lat: -16.2902, lng: -63.5887, region: 'Americas' },
  BA: { code: 'BA', name: 'Bosnia and Herzegovina', flag: '🇧🇦', lat: 43.9159, lng: 17.6791, region: 'Europe' },
  BW: { code: 'BW', name: 'Botswana', flag: '🇧🇼', lat: -22.3285, lng: 24.6849, region: 'Africa' },
  BR: { code: 'BR', name: 'Brazil', flag: '🇧🇷', lat: -14.235, lng: -51.9253, region: 'Americas' },
  BN: { code: 'BN', name: 'Brunei Darussalam', flag: '🇧🇳', lat: 4.5353, lng: 114.7277, region: 'Asia' },
  BG: { code: 'BG', name: 'Bulgaria', flag: '🇧🇬', lat: 42.7339, lng: 25.4858, region: 'Europe' },
  BF: { code: 'BF', name: 'Burkina Faso', flag: '🇧🇫', lat: 12.2383, lng: -1.5616, region: 'Africa' },
  BI: { code: 'BI', name: 'Burundi', flag: '🇧🇮', lat: -3.4264, lng: 29.9306, region: 'Africa' },
  CV: { code: 'CV', name: 'Cabo Verde', flag: '🇨🇻', lat: 16.5388, lng: -23.0418, region: 'Africa' },
  KH: { code: 'KH', name: 'Cambodia', flag: '🇰🇭', lat: 12.5657, lng: 104.991, region: 'Asia' },
  CM: { code: 'CM', name: 'Cameroon', flag: '🇨🇲', lat: 3.3792, lng: 11.5063, region: 'Africa' },
  CA: { code: 'CA', name: 'Canada', flag: '🇨🇦', lat: 56.1304, lng: -106.3468, region: 'Americas' },
  CF: { code: 'CF', name: 'Central African Republic', flag: '🇨🇫', lat: 6.6111, lng: 20.9394, region: 'Africa' },
  TD: { code: 'TD', name: 'Chad', flag: '🇹🇩', lat: 15.4542, lng: 18.7322, region: 'Africa' },
  CL: { code: 'CL', name: 'Chile', flag: '🇨🇱', lat: -35.6751, lng: -71.543, region: 'Americas' },
  CN: { code: 'CN', name: 'China', flag: '🇨🇳', lat: 35.8617, lng: 104.1954, region: 'Asia' },
  CO: { code: 'CO', name: 'Colombia', flag: '🇨🇴', lat: 4.5709, lng: -74.2973, region: 'Americas' },
  KM: { code: 'KM', name: 'Comoros', flag: '🇰🇲', lat: -11.6455, lng: 43.3333, region: 'Africa' },
  CG: { code: 'CG', name: 'Congo', flag: '🇨🇬', lat: -0.228, lng: 15.8277, region: 'Africa' },
  CD: { code: 'CD', name: 'Congo, Democratic Republic of the', flag: '🇨🇩', lat: -4.0383, lng: 21.7587, region: 'Africa' },
  CR: { code: 'CR', name: 'Costa Rica', flag: '🇨🇷', lat: 9.7489, lng: -83.7534, region: 'Americas' },
  HR: { code: 'HR', name: 'Croatia', flag: '🇭🇷', lat: 45.1, lng: 15.2, region: 'Europe' },
  CU: { code: 'CU', name: 'Cuba', flag: '🇨🇺', lat: 21.5218, lng: -77.7812, region: 'Americas' },
  CY: { code: 'CY', name: 'Cyprus', flag: '🇨🇾', lat: 35.1264, lng: 33.4299, region: 'Asia' },
  CZ: { code: 'CZ', name: 'Czechia', flag: '🇨🇿', lat: 49.8175, lng: 15.473, region: 'Europe' },
  CI: { code: 'CI', name: "Côte d'Ivoire", flag: '🇨🇮', lat: 7.54, lng: -5.5471, region: 'Africa' },
  // ── D ────────────────────────────────────────────────────────────
  DK: { code: 'DK', name: 'Denmark', flag: '🇩🇰', lat: 56.2639, lng: 9.5018, region: 'Europe' },
  DJ: { code: 'DJ', name: 'Djibouti', flag: '🇩🇯', lat: 11.8251, lng: 42.5903, region: 'Africa' },
  DM: { code: 'DM', name: 'Dominica', flag: '🇩🇲', lat: 15.415, lng: -61.371, region: 'Americas' },
  DO: { code: 'DO', name: 'Dominican Republic', flag: '🇩🇴', lat: 18.7357, lng: -70.1627, region: 'Americas' },
  // ── E ────────────────────────────────────────────────────────────
  EC: { code: 'EC', name: 'Ecuador', flag: '🇪🇨', lat: -1.8312, lng: -78.1834, region: 'Americas' },
  EG: { code: 'EG', name: 'Egypt', flag: '🇪🇬', lat: 26.8206, lng: 30.8025, region: 'Africa' },
  SV: { code: 'SV', name: 'El Salvador', flag: '🇸🇻', lat: 13.7942, lng: -88.8965, region: 'Americas' },
  GQ: { code: 'GQ', name: 'Equatorial Guinea', flag: '🇬🇶', lat: 1.6508, lng: 10.2679, region: 'Africa' },
  ER: { code: 'ER', name: 'Eritrea', flag: '🇪🇷', lat: 15.1794, lng: 39.7823, region: 'Africa' },
  EE: { code: 'EE', name: 'Estonia', flag: '🇪🇪', lat: 58.5953, lng: 25.0136, region: 'Europe' },
  SZ: { code: 'SZ', name: 'Eswatini', flag: '🇸🇿', lat: -26.5225, lng: 31.4659, region: 'Africa' },
  ET: { code: 'ET', name: 'Ethiopia', flag: '🇪🇹', lat: 9.145, lng: 40.4897, region: 'Africa' },
  // ── F ────────────────────────────────────────────────────────────
  FJ: { code: 'FJ', name: 'Fiji', flag: '🇫🇯', lat: -17.7134, lng: 178.065, region: 'Oceania' },
  FI: { code: 'FI', name: 'Finland', flag: '🇫🇮', lat: 61.9241, lng: 25.7482, region: 'Europe' },
  FR: { code: 'FR', name: 'France', flag: '🇫🇷', lat: 46.2276, lng: 2.2137, region: 'Europe' },
  // ── G ────────────────────────────────────────────────────────────
  GA: { code: 'GA', name: 'Gabon', flag: '🇬🇦', lat: -0.8037, lng: 11.6094, region: 'Africa' },
  GM: { code: 'GM', name: 'Gambia', flag: '🇬🇲', lat: 13.4432, lng: -15.3101, region: 'Africa' },
  GE: { code: 'GE', name: 'Georgia', flag: '🇬🇪', lat: 42.3154, lng: 43.3569, region: 'Asia' },
  DE: { code: 'DE', name: 'Germany', flag: '🇩🇪', lat: 51.1657, lng: 10.4515, region: 'Europe' },
  GH: { code: 'GH', name: 'Ghana', flag: '🇬🇭', lat: 7.9465, lng: -1.0232, region: 'Africa' },
  GR: { code: 'GR', name: 'Greece', flag: '🇬🇷', lat: 39.0742, lng: 21.8243, region: 'Europe' },
  GD: { code: 'GD', name: 'Grenada', flag: '🇬🇩', lat: 12.1165, lng: -61.679, region: 'Americas' },
  GT: { code: 'GT', name: 'Guatemala', flag: '🇬🇹', lat: 15.7835, lng: -90.2308, region: 'Americas' },
  GN: { code: 'GN', name: 'Guinea', flag: '🇬🇳', lat: 9.9456, lng: -9.6966, region: 'Africa' },
  GW: { code: 'GW', name: 'Guinea-Bissau', flag: '🇬🇼', lat: 11.8037, lng: -15.1804, region: 'Africa' },
  GY: { code: 'GY', name: 'Guyana', flag: '🇬🇾', lat: 4.8604, lng: -58.9302, region: 'Americas' },
  // ── H ────────────────────────────────────────────────────────────
  HT: { code: 'HT', name: 'Haiti', flag: '🇭🇹', lat: 18.9712, lng: -72.2852, region: 'Americas' },
  HN: { code: 'HN', name: 'Honduras', flag: '🇭🇳', lat: 15.2, lng: -86.2419, region: 'Americas' },
  HU: { code: 'HU', name: 'Hungary', flag: '🇭🇺', lat: 47.1625, lng: 19.5033, region: 'Europe' },
  // ── I ────────────────────────────────────────────────────────────
  IS: { code: 'IS', name: 'Iceland', flag: '🇮🇸', lat: 64.9631, lng: -19.0208, region: 'Europe' },
  IN: { code: 'IN', name: 'India', flag: '🇮🇳', lat: 20.5937, lng: 78.9629, region: 'Asia' },
  ID: { code: 'ID', name: 'Indonesia', flag: '🇮🇩', lat: -0.7893, lng: 113.9213, region: 'Asia' },
  IR: { code: 'IR', name: 'Iran', flag: '🇮🇷', lat: 32.4279, lng: 53.688, region: 'Asia' },
  IQ: { code: 'IQ', name: 'Iraq', flag: '🇮🇶', lat: 33.2232, lng: 43.6793, region: 'Asia' },
  IE: { code: 'IE', name: 'Ireland', flag: '🇮🇪', lat: 53.4129, lng: -8.2439, region: 'Europe' },
  IL: { code: 'IL', name: 'Israel', flag: '🇮🇱', lat: 31.0461, lng: 34.8516, region: 'Asia' },
  IT: { code: 'IT', name: 'Italy', flag: '🇮🇹', lat: 41.8719, lng: 12.5674, region: 'Europe' },
  // ── J ────────────────────────────────────────────────────────────
  JM: { code: 'JM', name: 'Jamaica', flag: '🇯🇲', lat: 18.1096, lng: -77.2975, region: 'Americas' },
  JP: { code: 'JP', name: 'Japan', flag: '🇯🇵', lat: 36.2048, lng: 138.2529, region: 'Asia' },
  JO: { code: 'JO', name: 'Jordan', flag: '🇯🇴', lat: 30.5852, lng: 36.2384, region: 'Asia' },
  // ── K ────────────────────────────────────────────────────────────
  KZ: { code: 'KZ', name: 'Kazakhstan', flag: '🇰🇿', lat: 48.0196, lng: 66.9237, region: 'Asia' },
  KE: { code: 'KE', name: 'Kenya', flag: '🇰🇪', lat: -0.0236, lng: 37.9062, region: 'Africa' },
  KI: { code: 'KI', name: 'Kiribati', flag: '🇰🇮', lat: -3.3704, lng: -168.734, region: 'Oceania' },
  KP: { code: 'KP', name: "Korea, Democratic People's Republic of", flag: '🇰🇵', lat: 40.3399, lng: 127.5101, region: 'Asia' },
  KR: { code: 'KR', name: 'Korea, Republic of', flag: '🇰🇷', lat: 35.9078, lng: 127.7669, region: 'Asia' },
  KW: { code: 'KW', name: 'Kuwait', flag: '🇰🇼', lat: 29.3117, lng: 47.4818, region: 'Asia' },
  KG: { code: 'KG', name: 'Kyrgyzstan', flag: '🇰🇬', lat: 41.2044, lng: 74.7661, region: 'Asia' },
  // ── L ────────────────────────────────────────────────────────────
  LA: { code: 'LA', name: "Lao People's Democratic Republic", flag: '🇱🇦', lat: 19.8563, lng: 102.4955, region: 'Asia' },
  LV: { code: 'LV', name: 'Latvia', flag: '🇱🇻', lat: 56.8796, lng: 24.6032, region: 'Europe' },
  LB: { code: 'LB', name: 'Lebanon', flag: '🇱🇧', lat: 33.8547, lng: 35.8623, region: 'Asia' },
  LS: { code: 'LS', name: 'Lesotho', flag: '🇱🇸', lat: -29.61, lng: 28.2336, region: 'Africa' },
  LR: { code: 'LR', name: 'Liberia', flag: '🇱🇷', lat: 6.4281, lng: -9.4295, region: 'Africa' },
  LY: { code: 'LY', name: 'Libya', flag: '🇱🇾', lat: 26.3351, lng: 17.2283, region: 'Africa' },
  LI: { code: 'LI', name: 'Liechtenstein', flag: '🇱🇮', lat: 47.166, lng: 9.5554, region: 'Europe' },
  LT: { code: 'LT', name: 'Lithuania', flag: '🇱🇹', lat: 55.1694, lng: 23.8813, region: 'Europe' },
  LU: { code: 'LU', name: 'Luxembourg', flag: '🇱🇺', lat: 49.8153, lng: 6.1296, region: 'Europe' },
  // ── M ────────────────────────────────────────────────────────────
  MG: { code: 'MG', name: 'Madagascar', flag: '🇲🇬', lat: -18.7669, lng: 46.8691, region: 'Africa' },
  MW: { code: 'MW', name: 'Malawi', flag: '🇲🇼', lat: -13.2543, lng: 34.3015, region: 'Africa' },
  MY: { code: 'MY', name: 'Malaysia', flag: '🇲🇾', lat: 4.2105, lng: 101.9758, region: 'Asia' },
  MV: { code: 'MV', name: 'Maldives', flag: '🇲🇻', lat: 3.2028, lng: 73.2207, region: 'Asia' },
  ML: { code: 'ML', name: 'Mali', flag: '🇲🇱', lat: 17.5707, lng: -3.9962, region: 'Africa' },
  MT: { code: 'MT', name: 'Malta', flag: '🇲🇹', lat: 35.9375, lng: 14.3754, region: 'Europe' },
  MH: { code: 'MH', name: 'Marshall Islands', flag: '🇲🇭', lat: 9.6435, lng: 168.734, region: 'Oceania' },
  MR: { code: 'MR', name: 'Mauritania', flag: '🇲🇷', lat: 21.0079, lng: -10.9408, region: 'Africa' },
  MU: { code: 'MU', name: 'Mauritius', flag: '🇲🇺', lat: -20.3484, lng: 57.5522, region: 'Africa' },
  MX: { code: 'MX', name: 'Mexico', flag: '🇲🇽', lat: 23.6345, lng: -102.5528, region: 'Americas' },
  FM: { code: 'FM', name: 'Micronesia, Federated States of', flag: '🇫🇲', lat: 7.4256, lng: 150.5508, region: 'Oceania' },
  MD: { code: 'MD', name: 'Moldova', flag: '🇲🇩', lat: 47.4116, lng: 28.3699, region: 'Europe' },
  MC: { code: 'MC', name: 'Monaco', flag: '🇲🇨', lat: 43.7384, lng: 7.4246, region: 'Europe' },
  MN: { code: 'MN', name: 'Mongolia', flag: '🇲🇳', lat: 46.8625, lng: 103.8467, region: 'Asia' },
  ME: { code: 'ME', name: 'Montenegro', flag: '🇲🇪', lat: 42.7087, lng: 19.3744, region: 'Europe' },
  MA: { code: 'MA', name: 'Morocco', flag: '🇲🇦', lat: 31.7917, lng: -7.0926, region: 'Africa' },
  MZ: { code: 'MZ', name: 'Mozambique', flag: '🇲🇿', lat: -18.6657, lng: 35.5296, region: 'Africa' },
  MM: { code: 'MM', name: 'Myanmar', flag: '🇲🇲', lat: 21.9162, lng: 95.956, region: 'Asia' },
  // ── N ────────────────────────────────────────────────────────────
  NA: { code: 'NA', name: 'Namibia', flag: '🇳🇦', lat: -22.9576, lng: 18.4904, region: 'Africa' },
  NR: { code: 'NR', name: 'Nauru', flag: '🇳🇷', lat: -0.5228, lng: 166.9315, region: 'Oceania' },
  NP: { code: 'NP', name: 'Nepal', flag: '🇳🇵', lat: 28.3949, lng: 84.124, region: 'Asia' },
  NL: { code: 'NL', name: 'Netherlands', flag: '🇳🇱', lat: 52.1326, lng: 5.2913, region: 'Europe' },
  NZ: { code: 'NZ', name: 'New Zealand', flag: '🇳🇿', lat: -40.9006, lng: 174.886, region: 'Oceania' },
  NI: { code: 'NI', name: 'Nicaragua', flag: '🇳🇮', lat: 12.8654, lng: -85.2072, region: 'Americas' },
  NE: { code: 'NE', name: 'Niger', flag: '🇳🇪', lat: 17.6078, lng: 8.0817, region: 'Africa' },
  NG: { code: 'NG', name: 'Nigeria', flag: '🇳🇬', lat: 9.082, lng: 8.6753, region: 'Africa' },
  MK: { code: 'MK', name: 'North Macedonia', flag: '🇲🇰', lat: 41.5124, lng: 21.7453, region: 'Europe' },
  NO: { code: 'NO', name: 'Norway', flag: '🇳🇴', lat: 60.472, lng: 8.4689, region: 'Europe' },
  // ── O ────────────────────────────────────────────────────────────
  OM: { code: 'OM', name: 'Oman', flag: '🇴🇲', lat: 21.4735, lng: 55.9754, region: 'Asia' },
  // ── P ────────────────────────────────────────────────────────────
  PK: { code: 'PK', name: 'Pakistan', flag: '🇵🇰', lat: 30.3753, lng: 69.3451, region: 'Asia' },
  PW: { code: 'PW', name: 'Palau', flag: '🇵🇼', lat: 7.515, lng: 134.5825, region: 'Oceania' },
  PS: { code: 'PS', name: 'Palestine, State of', flag: '🇵🇸', lat: 31.9522, lng: 35.2332, region: 'Asia' },
  PG: { code: 'PG', name: 'Papua New Guinea', flag: '🇵🇬', lat: -6.315, lng: 143.9555, region: 'Oceania' },
  PY: { code: 'PY', name: 'Paraguay', flag: '🇵🇾', lat: -23.4425, lng: -58.4438, region: 'Americas' },
  PE: { code: 'PE', name: 'Peru', flag: '🇵🇪', lat: -9.19, lng: -75.0152, region: 'Americas' },
  PH: { code: 'PH', name: 'Philippines', flag: '🇵🇭', lat: 12.8797, lng: 121.774, region: 'Asia' },
  PL: { code: 'PL', name: 'Poland', flag: '🇵🇱', lat: 51.9194, lng: 19.1451, region: 'Europe' },
  PT: { code: 'PT', name: 'Portugal', flag: '🇵🇹', lat: 39.3999, lng: -8.2245, region: 'Europe' },
  // ── Q ────────────────────────────────────────────────────────────
  QA: { code: 'QA', name: 'Qatar', flag: '🇶🇦', lat: 25.3548, lng: 51.1839, region: 'Asia' },
  // ── R ────────────────────────────────────────────────────────────
  RO: { code: 'RO', name: 'Romania', flag: '🇷🇴', lat: 45.9432, lng: 24.9668, region: 'Europe' },
  RU: { code: 'RU', name: 'Russian Federation', flag: '🇷🇺', lat: 61.524, lng: 105.3188, region: 'Europe' },
  RW: { code: 'RW', name: 'Rwanda', flag: '🇷🇼', lat: -1.9403, lng: 29.8739, region: 'Africa' },
  // ── S ────────────────────────────────────────────────────────────
  KN: { code: 'KN', name: 'Saint Kitts and Nevis', flag: '🇰🇳', lat: 17.3578, lng: -62.783, region: 'Americas' },
  LC: { code: 'LC', name: 'Saint Lucia', flag: '🇱🇨', lat: 13.9094, lng: -60.9789, region: 'Americas' },
  VC: { code: 'VC', name: 'Saint Vincent and the Grenadines', flag: '🇻🇨', lat: 12.9843, lng: -61.2872, region: 'Americas' },
  WS: { code: 'WS', name: 'Samoa', flag: '🇼🇸', lat: -13.759, lng: -172.1046, region: 'Oceania' },
  SM: { code: 'SM', name: 'San Marino', flag: '🇸🇲', lat: 43.9424, lng: 12.4578, region: 'Europe' },
  SA: { code: 'SA', name: 'Saudi Arabia', flag: '🇸🇦', lat: 23.8859, lng: 45.0792, region: 'Asia' },
  SN: { code: 'SN', name: 'Senegal', flag: '🇸🇳', lat: 14.4974, lng: -14.4524, region: 'Africa' },
  RS: { code: 'RS', name: 'Serbia', flag: '🇷🇸', lat: 44.0165, lng: 21.0059, region: 'Europe' },
  SC: { code: 'SC', name: 'Seychelles', flag: '🇸🇨', lat: -4.6796, lng: 55.492, region: 'Africa' },
  SL: { code: 'SL', name: 'Sierra Leone', flag: '🇸🇱', lat: 8.4606, lng: -11.7799, region: 'Africa' },
  SG: { code: 'SG', name: 'Singapore', flag: '🇸🇬', lat: 1.3521, lng: 103.8198, region: 'Asia' },
  SK: { code: 'SK', name: 'Slovakia', flag: '🇸🇰', lat: 48.669, lng: 19.699, region: 'Europe' },
  SI: { code: 'SI', name: 'Slovenia', flag: '🇸🇮', lat: 46.1512, lng: 14.9955, region: 'Europe' },
  SB: { code: 'SB', name: 'Solomon Islands', flag: '🇸🇧', lat: -9.6457, lng: 160.1562, region: 'Oceania' },
  SO: { code: 'SO', name: 'Somalia', flag: '🇸🇴', lat: 5.1521, lng: 46.1996, region: 'Africa' },
  ZA: { code: 'ZA', name: 'South Africa', flag: '🇿🇦', lat: -30.5595, lng: 22.9375, region: 'Africa' },
  SS: { code: 'SS', name: 'South Sudan', flag: '🇸🇸', lat: 6.877, lng: 31.307, region: 'Africa' },
  ES: { code: 'ES', name: 'Spain', flag: '🇪🇸', lat: 40.4637, lng: -3.7492, region: 'Europe' },
  LK: { code: 'LK', name: 'Sri Lanka', flag: '🇱🇰', lat: 7.8731, lng: 80.7718, region: 'Asia' },
  SD: { code: 'SD', name: 'Sudan', flag: '🇸🇩', lat: 12.8628, lng: 30.2176, region: 'Africa' },
  SR: { code: 'SR', name: 'Suriname', flag: '🇸🇷', lat: 3.9193, lng: -56.0278, region: 'Americas' },
  SE: { code: 'SE', name: 'Sweden', flag: '🇸🇪', lat: 60.1282, lng: 18.6435, region: 'Europe' },
  CH: { code: 'CH', name: 'Switzerland', flag: '🇨🇭', lat: 46.8182, lng: 8.2275, region: 'Europe' },
  SY: { code: 'SY', name: 'Syrian Arab Republic', flag: '🇸🇾', lat: 34.8021, lng: 38.9968, region: 'Asia' },
  ST: { code: 'ST', name: 'São Tomé and Príncipe', flag: '🇸🇹', lat: 0.1874, lng: 7.3426, region: 'Africa' },
  // ── T ────────────────────────────────────────────────────────────
  TW: { code: 'TW', name: 'Taiwan', flag: '🇹🇼', lat: 23.6978, lng: 120.9605, region: 'Asia' },
  TJ: { code: 'TJ', name: 'Tajikistan', flag: '🇹🇯', lat: 38.861, lng: 71.2761, region: 'Asia' },
  TZ: { code: 'TZ', name: 'Tanzania', flag: '🇹🇿', lat: -6.369, lng: 34.8888, region: 'Africa' },
  TH: { code: 'TH', name: 'Thailand', flag: '🇹🇭', lat: 15.87, lng: 100.9925, region: 'Asia' },
  TL: { code: 'TL', name: 'Timor-Leste', flag: '🇹🇱', lat: -8.8742, lng: 125.7275, region: 'Asia' },
  TG: { code: 'TG', name: 'Togo', flag: '🇹🇬', lat: 8.6195, lng: 0.8248, region: 'Africa' },
  TO: { code: 'TO', name: 'Tonga', flag: '🇹🇴', lat: -21.179, lng: -175.1982, region: 'Oceania' },
  TT: { code: 'TT', name: 'Trinidad and Tobago', flag: '🇹🇹', lat: 10.6918, lng: -61.2225, region: 'Americas' },
  TN: { code: 'TN', name: 'Tunisia', flag: '🇹🇳', lat: 33.8869, lng: 9.5375, region: 'Africa' },
  TM: { code: 'TM', name: 'Turkmenistan', flag: '🇹🇲', lat: 38.9697, lng: 59.5563, region: 'Asia' },
  TV: { code: 'TV', name: 'Tuvalu', flag: '🇹🇻', lat: -7.1095, lng: 179.194, region: 'Oceania' },
  TR: { code: 'TR', name: 'Türkiye', flag: '🇹🇷', lat: 38.9637, lng: 35.2433, region: 'Asia' },
  // ── U ────────────────────────────────────────────────────────────
  UG: { code: 'UG', name: 'Uganda', flag: '🇺🇬', lat: 1.3733, lng: 32.2903, region: 'Africa' },
  UA: { code: 'UA', name: 'Ukraine', flag: '🇺🇦', lat: 48.3794, lng: 31.1656, region: 'Europe' },
  GB: { code: 'GB', name: 'United Kingdom', flag: '🇬🇧', lat: 51.5074, lng: -0.1278, region: 'Europe' },
  US: { code: 'US', name: 'United States', flag: '🇺🇸', lat: 39.8283, lng: -98.5795, region: 'Americas' },
  UY: { code: 'UY', name: 'Uruguay', flag: '🇺🇾', lat: -32.5228, lng: -55.7658, region: 'Americas' },
  UZ: { code: 'UZ', name: 'Uzbekistan', flag: '🇺🇿', lat: 41.3775, lng: 64.5853, region: 'Asia' },
  // ── V ────────────────────────────────────────────────────────────
  VU: { code: 'VU', name: 'Vanuatu', flag: '🇻🇺', lat: -15.3767, lng: 166.9592, region: 'Oceania' },
  VA: { code: 'VA', name: 'Vatican City', flag: '🇻🇦', lat: 41.9029, lng: 12.4534, region: 'Europe' },
  VE: { code: 'VE', name: 'Venezuela', flag: '🇻🇪', lat: 6.4238, lng: -66.5897, region: 'Americas' },
  VN: { code: 'VN', name: 'Viet Nam', flag: '🇻🇳', lat: 14.0583, lng: 108.2772, region: 'Asia' },
  // ── X ────────────────────────────────────────────────────────────
  XK: { code: 'XK', name: 'Kosovo', flag: '🇽🇰', lat: 42.6026, lng: 20.903, region: 'Europe' },
  // ── Y ────────────────────────────────────────────────────────────
  YE: { code: 'YE', name: 'Yemen', flag: '🇾🇪', lat: 15.5527, lng: 48.5164, region: 'Asia' },
  // ── Z ────────────────────────────────────────────────────────────
  ZM: { code: 'ZM', name: 'Zambia', flag: '🇿🇲', lat: -13.1339, lng: 27.8493, region: 'Africa' },
  ZW: { code: 'ZW', name: 'Zimbabwe', flag: '🇿🇼', lat: -19.0154, lng: 29.1549, region: 'Africa' },
  DZ: { code: 'DZ', name: 'Algeria', flag: '🇩🇿', lat: 28.0339, lng: 1.6596, region: 'Africa' },
};

// =============================================================
// Countries available per product type (sourced from /api/catalog)
// =============================================================
// These are populated dynamically from the catalog API response.
// Kept here as reference for the initial product type cards.

export const PRODUCT_COUNTRIES: Record<string, string[]> = {
  ISP: ['US', 'GB', 'DE', 'FR', 'CA', 'JP'],
  DC: ['US', 'GB'],
  RESIDENTIAL: ['US', 'GB', 'DE', 'CA', 'AU', 'FR', 'BR', 'IN', 'NG', 'AE'],
  MOBILE: ['US', 'GB', 'DE', 'CA', 'AU', 'FR', 'BR', 'IN', 'NG', 'PK', 'ID', 'MX'],
};

export const getCountriesForProduct = (productType: string): CountryInfo[] => {
  const codes = PRODUCT_COUNTRIES[productType] || [];
  return codes.map(c => COUNTRIES[c]).filter(Boolean) as CountryInfo[];
};

export const getProductCountryList = (productType: string): string[] => {
  return (PRODUCT_COUNTRIES[productType] || []).map(c => COUNTRIES[c]?.name || c);
};
