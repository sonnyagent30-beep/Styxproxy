// Country-page helper — pure functions for picking countries per product type
// Built on top of the centralized PRODUCT_COUNTRIES in /lib/products.ts.

import { COUNTRIES, PRODUCT_COUNTRIES, type CountryInfo } from './products';

/**
 * Returns true if this product type supports per-country plan selection.
 * Right now only ISP has dedicated per-country plans.
 * Residential/Mobile/DC are GLOBAL plans you can pin to a country at order time.
 */
export function productSupportsCountryPlans(planType: string): boolean {
  return planType === 'ISP';
}

/**
 * Returns the list of country codes valid for a product type.
 * Used by the order modal to render the country picker.
 */
export function getAvailableCountries(planType: string): CountryInfo[] {
  const codes = PRODUCT_COUNTRIES[planType] || [];
  return codes.map(c => COUNTRIES[c]).filter(Boolean);
}

/**
 * Build the display name for a plan in the order modal.
 * For ISP: "{Country} ISP"
 * For Residential/Mobile/DC: "{Country} · {plan_description}"
 */
export function formatPlanName(product: { plan_type: string; country: string; features: string[] }): string {
  switch (product.plan_type) {
    case 'ISP':
      return `${product.country} ISP`;
    case 'RESIDENTIAL':
      return `Residential — ${product.features[0] || ''}`;
    case 'MOBILE':
      return `Mobile 4G — ${product.features[0] || ''}`;
    case 'DC':
      return 'Datacenter Proxy';
    default:
      return product.country;
  }
}
