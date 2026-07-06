import { Product } from '@/types';

export const products: Product[] = [
  // ISP Proxies - UK/US/DE/FR/CA
  {
    plan_code: 'ISP-UK-1',
    plan_type: 'ISP',
    country: 'UK',
    price_ngn: 6500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
    provider: 'proxy-seller',
  },
  {
    plan_code: 'ISP-US-1',
    plan_type: 'ISP',
    country: 'US',
    price_ngn: 6500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
    provider: 'proxy-seller',
  },
  {
    plan_code: 'ISP-DE-1',
    plan_type: 'ISP',
    country: 'DE',
    price_ngn: 6500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
    provider: 'proxy-seller',
  },
  {
    plan_code: 'ISP-FR-1',
    plan_type: 'ISP',
    country: 'FR',
    price_ngn: 6500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
    provider: 'proxy-seller',
  },
  {
    plan_code: 'ISP-CA-1',
    plan_type: 'ISP',
    country: 'CA',
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
    country: 'JP',
    price_ngn: 7500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
    provider: 'proxy-seller',
  },
  {
    plan_code: 'ISP-AU-1',
    plan_type: 'ISP',
    country: 'AU',
    price_ngn: 7500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
    provider: 'proxy-seller',
  },
  {
    plan_code: 'ISP-BR-1',
    plan_type: 'ISP',
    country: 'BR',
    price_ngn: 7500,
    quantity: 1,
    duration_days: 30,
    features: ['High-speed ISP', 'Fresh IPs', '30-day expiry'],
    provider: 'proxy-seller',
  },
  {
    plan_code: 'ISP-SG-1',
    plan_type: 'ISP',
    country: 'SG',
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
    country: 'GLOBAL',
    price_ngn: 5000,
    quantity: 5,
    duration_days: 30,
    features: ['5GB Data', 'No expiry until used', 'Residential IPs'],
    provider: 'dataimpulse',
  },
  {
    plan_code: 'RES-10GB',
    plan_type: 'RESIDENTIAL',
    country: 'GLOBAL',
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
    country: 'GLOBAL',
    price_ngn: 20000,
    quantity: 5,
    duration_days: 30,
    features: ['5GB 4G Data', '30-day window', 'Mobile IPs'],
    provider: 'dataimpulse',
  },
  {
    plan_code: 'MOB-4G-10GB',
    plan_type: 'MOBILE',
    country: 'GLOBAL',
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
    country: 'GLOBAL',
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
