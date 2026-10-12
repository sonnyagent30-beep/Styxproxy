'use client';

/**
 * CityPicker — country + city dropdowns for residential/mobile plans.
 *
 * User picks country (e.g. "GB"), then optionally picks a city (e.g. "London")
 * or "Random" (no constraint, provider picks from the country pool).
 *
 * Used by:
 * - /products page (inline)
 * - /order/checkout page (cart review)
 * - any future page that lets the customer pick a proxy location
 */

import { useEffect, useMemo, useState } from 'react';
import type { CatalogCity } from '@/types';
import { getCitiesForCountry, loadFullCatalog } from '@/lib/products';

interface CityPickerProps {
  planType: string;                           // 'residential' | 'mobile' | 'datacenter' | 'isp'
  country: string;                            // ISO alpha-2 (e.g. 'GB')
  onCountryChange?: (country: string) => void;
  onCityChange: (city: CatalogCity | null) => void;  // null = random
  selectedCityId?: number | null;
  disabled?: boolean;
  /** Show labels for the dropdowns. Default true. */
  showLabels?: boolean;
  /** Compact mode for inline use (smaller text). Default false. */
  compact?: boolean;
}

export function CityPicker({
  planType,
  country,
  onCountryChange,
  onCityChange,
  selectedCityId,
  disabled,
  showLabels = true,
  compact = false,
}: CityPickerProps) {
  const [availableCountries, setAvailableCountries] = useState<string[]>([]);
  const [selectedCityIdLocal, setSelectedCityIdLocal] = useState<number | null>(selectedCityId ?? null);

  // Load catalog on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { templates } = await loadFullCatalog();
        if (cancelled) return;
        const template = templates.find(
          (t) => t.plan_type.toLowerCase() === planType.toLowerCase(),
        );
        if (template) {
          setAvailableCountries(template.available_countries);
        }
      } catch {
        // fall back to empty list
      }
    })();
    return () => { cancelled = true; };
  }, [planType]);

  // Compute cities from catalog (no async fetch needed — synchronous lookup)
  const cities = useMemo(() => getCitiesForCountry(planType, country), [planType, country]);
  // If current selected city isn't in the new list, reset to random
  useEffect(() => {
    if (selectedCityIdLocal && !cities.find((c) => c.id === selectedCityIdLocal)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedCityIdLocal(null);
      onCityChange(null);
    }
  }, [cities, selectedCityIdLocal, onCityChange]);

  const isCityPicker = planType === 'residential' || planType === 'mobile';
  const supportsCity = planType === 'residential' || planType === 'mobile';

  const labelClass = compact ? 'text-xs text-[var(--muted)] mb-1' : 'text-sm font-medium mb-2';
  const selectClass = compact
    ? 'w-full px-2 py-1.5 text-sm rounded-lg bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none'
    : 'w-full px-3 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors';

  return (
    <div className="space-y-3">
      {/* Country selector */}
      <div>
        {showLabels && <label className={labelClass}>Country</label>}
        <select
          className={selectClass}
          value={country}
          onChange={(e) => onCountryChange?.(e.target.value)}
          disabled={disabled}
        >
          {availableCountries.map((cc) => (
            <option key={cc} value={cc}>
              {countryName(cc)} ({cc})
            </option>
          ))}
        </select>
      </div>

      {/* City selector (residential/mobile only) */}
      {isCityPicker && supportsCity && (
        <div>
          {showLabels && <label className={labelClass}>City (optional)</label>}
          <select
            className={selectClass}
            value={selectedCityIdLocal ?? ''}
            onChange={(e) => {
              const id = e.target.value ? parseInt(e.target.value, 10) : null;
              setSelectedCityIdLocal(id);
              const city = id ? cities.find((c) => c.id === id) ?? null : null;
              onCityChange(city);
            }}
            disabled={disabled}
          >
            <option value="">🎲 Random (any city in {countryName(country)})</option>
            {cities.map((city) => (
              <option key={city.id} value={city.id}>
                {city.city_name}
                {city.isp_name ? ` — ${city.isp_name}` : ''}
              </option>
            ))}
          </select>
          {!compact && (
            <p className="text-xs text-[var(--muted)] mt-1">
              Pick a city for exact geo-targeting, or leave as Random.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Country code → display name (lightweight, ISO 3166-1 alpha-2).
 * Kept here to avoid pulling in the full COUNTRIES map.
 */
const COUNTRY_NAMES: Record<string, string> = {
  US: 'United States', GB: 'United Kingdom', DE: 'Germany', CA: 'Canada',
  AU: 'Australia', FR: 'France', BR: 'Brazil', IN: 'India', NG: 'Nigeria',
  JP: 'Japan', SG: 'Singapore', AE: 'UAE', KR: 'South Korea', NL: 'Netherlands',
  ES: 'Spain', IT: 'Italy', MX: 'Mexico', AR: 'Argentina', ZA: 'South Africa',
  HK: 'Hong Kong', UK: 'United Kingdom', IE: 'Ireland', PL: 'Poland', SE: 'Sweden',
  CH: 'Switzerland', AT: 'Austria', BE: 'Belgium', NO: 'Norway', FI: 'Finland',
  DK: 'Denmark', PT: 'Portugal', GR: 'Greece', IL: 'Israel', TR: 'Turkey',
  RU: 'Russia', SA: 'Saudi Arabia', EG: 'Egypt', KE: 'Kenya', GH: 'Ghana',
  TH: 'Thailand', MY: 'Malaysia', ID: 'Indonesia', PH: 'Philippines', VN: 'Vietnam',
  PK: 'Pakistan', BD: 'Bangladesh', LK: 'Sri Lanka', NP: 'Nepal',
  CL: 'Chile', CO: 'Colombia', PE: 'Peru', VE: 'Venezuela',
  CR: 'Costa Rica', PA: 'Panama', DO: 'Dominican Republic', PR: 'Puerto Rico',
  NZ: 'New Zealand', FJ: 'Fiji',
};

export function countryName(code: string): string {
  return COUNTRY_NAMES[code.toUpperCase()] || code;
}
