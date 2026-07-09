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
    provider: 'proxy-seller',
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
    provider: 'proxy-seller',
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
    provider: 'proxy-seller',
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
    provider: 'proxy-seller',
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
    provider: 'proxy-seller',
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
    provider: 'proxy-seller',
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
    provider: 'proxy-seller',
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
    provider: 'proxy-seller',
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
    provider: 'proxy-seller',
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
    provider: 'dataimpulse',
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
    provider: 'dataimpulse',
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
    provider: 'dataimpulse',
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
    provider: 'dataimpulse',
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
    provider: 'proxy-seller',
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
