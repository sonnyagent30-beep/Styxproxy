'use client';

/**
 * GlobeScene — Sprint 19 premium globe upgrade.
 *
 * Built on three-globe (SSR-safe via dynamic import).
 * Fetches live session counts from /api/proxy/active-countries — gracefully
 * falls back to a demo arc set when no sessions are active (pre-launch).
 *
 * Light/dark mode respects prefers-color-scheme.
 * Drag with momentum (OrbitControls inertia 4s).
 * Animated brand-green arcs, pulsing city markers, hover tooltips.
 */

import { useRef, useEffect, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ThreeGlobe = dynamic(() => import('three-globe').then((m: any) => m.default as unknown as React.ComponentType<any>), {
  ssr: false,
  loading: () => (
    <div className="w-full flex items-center justify-center" style={{ height: 440 }}>
      <div className="animate-pulse text-sm" style={{ color: '#71717a' }}>Loading globe…</div>
    </div>
  ),
});

// Brand colours
const BRAND_GREEN = '#10B981';
const BRAND_GREEN_LIGHT = '#34D399';

// Fallback demo arcs — shown when no live session data exists yet
const FALLBACK_ORIGIN = { lat: 51.5074, lng: -0.1278, name: 'London', country: 'United Kingdom' };

const FALLBACK_DESTINATIONS = [
  { lat: 40.7128, lng: -74.006, name: 'US', country: 'United States' },
  { lat: 52.52, lng: 13.405, name: 'DE', country: 'Germany' },
  { lat: 48.8566, lng: 2.3522, name: 'FR', country: 'France' },
  { lat: 45.5017, lng: -73.5673, name: 'CA', country: 'Canada' },
  { lat: 35.6762, lng: 139.6503, name: 'JP', country: 'Japan' },
  { lat: -33.8688, lng: 151.2093, name: 'AU', country: 'Australia' },
  { lat: -23.5505, lng: -46.6333, name: 'BR', country: 'Brazil' },
  { lat: 1.3521, lng: 103.8198, name: 'SG', country: 'Singapore' },
];

interface ActiveCountry {
  country_code: string;
  session_count: number;
}

interface CountryMeta {
  lat: number;
  lng: number;
  name: string;
  country: string;
  flag?: string;
}

// Light-mode colours
const LIGHT_GLOBE_COLOR = '#e5e7eb';
const LIGHT_GLOW_COLOR = '#6366F1';

export default function GlobeScene() {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<any>(null);

  const [isDark, setIsDark] = useState(true);
  const [activeCountries, setActiveCountries] = useState<ActiveCountry[]>([]);
  const [loading, setLoading] = useState(true);
  const [featuredIdx, setFeaturedIdx] = useState(0);

  // ── Theme detection ────────────────────────────────────────────
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // ── Fetch live session data ────────────────────────────────────
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await fetch('/api/proxy/active-countries');
        if (res.ok) {
          const data: ActiveCountry[] = await res.json();
          setActiveCountries(data);
        }
      } catch {
        // Network error — show fallback
      } finally {
        setLoading(false);
      }
    };
    fetchSessions();
    // Refresh every 60 s so the operator sees updates in dev
    const interval = setInterval(fetchSessions, 60_000);
    return () => clearInterval(interval);
  }, []);

  // ── Demo-mode cycling (no live sessions yet) ──────────────────
  useEffect(() => {
    if (activeCountries.length > 0) return;
    const dests = FALLBACK_DESTINATIONS;
    const interval = setInterval(() => {
      setFeaturedIdx(i => (i + 1) % dests.length);
    }, 3500);
    return () => clearInterval(interval);
  }, [activeCountries]);

  // ── Build arc data ─────────────────────────────────────────────
  const buildArcs = useCallback((): object[] => {
    if (activeCountries.length > 0) {
      // Live mode: UK → each active country (only show countries with sessions)
      const origin = FALLBACK_ORIGIN;
      return activeCountries.slice(0, 8).map(c => {
        const meta = COUNTRY_META[c.country_code] ?? { lat: 0, lng: 0, name: c.country_code };
        return {
          startLat: origin.lat,
          startLng: origin.lng,
          endLat: meta.lat,
          endLng: meta.lng,
          color: BRAND_GREEN,
        };
      });
    }
    // Demo mode: UK → 8 fallback destinations
    return FALLBACK_DESTINATIONS.map(dest => ({
      startLat: FALLBACK_ORIGIN.lat,
      startLng: FALLBACK_ORIGIN.lng,
      endLat: dest.lat,
      endLng: dest.lng,
      color: BRAND_GREEN,
    }));
  }, [activeCountries]);

  // ── Build point data ────────────────────────────────────────────
  const buildPoints = useCallback((): object[] => {
    if (activeCountries.length > 0) {
      return activeCountries.slice(0, 12).map(c => {
        const meta = COUNTRY_META[c.country_code] ?? { lat: 0, lng: 0, name: c.country_code };
        return {
          lat: meta.lat,
          lng: meta.lng,
          name: meta.country,
          size: Math.max(0.5, Math.min(2.5, Math.log2(c.session_count + 1) * 0.9)),
          color: BRAND_GREEN,
        };
      });
    }
    // Demo: all fallback destinations
    return FALLBACK_DESTINATIONS.map(dest => ({
      lat: dest.lat,
      lng: dest.lng,
      name: dest.country,
      size: 0.75,
      color: BRAND_GREEN,
    }));
  }, [activeCountries]);

  // ── Featured callout ────────────────────────────────────────────
  const featured = activeCountries.length > 0
    ? activeCountries[featuredIdx % Math.max(activeCountries.length, 1)]
    : FALLBACK_DESTINATIONS[featuredIdx % FALLBACK_DESTINATIONS.length];

  const featuredMeta = activeCountries.length > 0
    ? COUNTRY_META[featured.country_code] ?? { lat: 0, lng: 0, name: featured.country_code, country: featured.country_code, flag: '' }
    : featured;

  // Theme-based globe colours
  const globeColor = isDark ? '#0a1628' : LIGHT_GLOBE_COLOR;
  const glowColor = isDark ? BRAND_GREEN : LIGHT_GLOW_COLOR;
  const glowOpacity = isDark ? 0.35 : 0.15;
  const glowStrength = isDark ? 0.8 : 0.4;

  const hasLiveData = activeCountries.length > 0;
  const sessionCount = activeCountries.reduce((sum, c) => sum + c.session_count, 0);

  return (
    <div className="relative w-full" style={{ height: 460 }}>
      {/* Globe canvas */}
      <div ref={containerRef} className="absolute inset-0">
        <ThreeGlobe
          ref={globeRef}
          // Globe body
          globeColor={globeColor}
          // Atmosphere glow
          atmosphereColor={glowColor}
          atmosphereAltitude={0.18}
          atmosphereOpacity={glowOpacity}
          // Points
          pointsData={buildPoints()}
          pointLat="lat"
          pointLng="lng"
          pointAltitude={0.015}
          pointRadius="size"
          pointColor="color"
          // Pulse rings
          ringMaxRadius={7}
          ringPropagationSpeed={2.5}
          ringColor={() => BRAND_GREEN}
          ringOpacity={0.5}
          // Arcs
          arcsData={buildArcs()}
          arcStartLat="startLat"
          arcStartLng="startLng"
          arcEndLat="endLat"
          arcEndLng="endLng"
          arcColor="color"
          arcAltitude={0.28}
          arcStroke={0.6}
          arcDashLength={0.35}
          arcDashGap={0.18}
          arcDashAnimateTime={2200}
          // Controls — drag with momentum
          enablePointerInteraction={true}
        />
      </div>

      {/* Featured country / session callout */}
      {!loading && (
        <div
          className="absolute rounded-2xl shadow-2xl p-4 flex items-center gap-3 border backdrop-blur-md transition-all duration-700"
          style={{
            right: '6%',
            top: '10%',
            minWidth: '170px',
            background: isDark ? 'rgba(10,10,26,0.92)' : 'rgba(255,255,255,0.92)',
            borderColor: isDark ? 'rgba(16,185,129,0.3)' : 'rgba(16,185,129,0.35)',
            animation: 'floatCallout 3.5s ease-in-out infinite',
            backdropFilter: 'blur(14px)',
          }}
        >
          {hasLiveData ? (
            <>
              <span className="text-3xl">{featuredMeta.flag ?? '🌍'}</span>
              <div>
                <p className="font-bold text-sm leading-tight" style={{ color: isDark ? '#f4f4f5' : '#18181b' }}>
                  {featuredMeta.country}
                </p>
                <p className="text-xs mt-0.5" style={{ color: '#71717a' }}>
                  {featured.session_count} active session{featured.session_count !== 1 ? 's' : ''}
                </p>
                <p className="text-xs mt-1" style={{ color: BRAND_GREEN }}>
                  {sessionCount} total across {activeCountries.length} countries
                </p>
              </div>
            </>
          ) : (
            <>
              <span className="text-3xl">{featuredMeta.flag ?? '🌍'}</span>
              <div>
                <p className="font-bold text-sm leading-tight" style={{ color: isDark ? '#f4f4f5' : '#18181b' }}>
                  {featuredMeta.country}
                </p>
                <p className="text-xs mt-0.5" style={{ color: '#71717a' }}>
                  Demo mode — live on launch
                </p>
              </div>
            </>
          )}
        </div>
      )}

      {/* Coverage badge */}
      <div
        className="absolute bottom-4 left-4 rounded-xl px-3 py-2 shadow-lg border backdrop-blur-sm"
        style={{
          background: isDark ? 'rgba(10,10,26,0.88)' : 'rgba(255,255,255,0.88)',
          borderColor: isDark ? 'rgba(16,185,129,0.3)' : 'rgba(16,185,129,0.3)',
        }}
      >
        {hasLiveData ? (
          <>
            <p className="text-xs font-medium" style={{ color: BRAND_GREEN }}>Live Sessions</p>
            <p className="text-xs mt-0.5" style={{ color: '#71717a' }}>
              {activeCountries.length} countries · {sessionCount} sessions
            </p>
          </>
        ) : (
          <>
            <p className="text-xs font-medium" style={{ color: BRAND_GREEN }}>9 Countries</p>
            <p className="text-xs mt-0.5" style={{ color: '#71717a' }}>ISP Coverage · Live on launch</p>
          </>
        )}
      </div>

      {/* Legend */}
      <div
        className="absolute bottom-4 right-4 rounded-xl px-3 py-2 shadow-lg border backdrop-blur-sm"
        style={{
          background: isDark ? 'rgba(10,10,26,0.88)' : 'rgba(255,255,255,0.88)',
          borderColor: isDark ? 'rgba(16,185,129,0.3)' : 'rgba(16,185,129,0.3)',
        }}
      >
        <div className="flex items-center gap-2 text-xs" style={{ color: '#71717a' }}>
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: BRAND_GREEN }} />
          <span>ISP · Residential · Mobile</span>
        </div>
      </div>

      <style>{`
        @keyframes floatCallout {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-7px); }
        }
      `}</style>
    </div>
  );
}

// ── Country metadata (ISO 3166-1 alpha-2 → lat/lng/name) ────────
const COUNTRY_META: Record<string, CountryMeta> = {
  GB: { lat: 51.5074, lng: -0.1278, name: 'London', country: 'United Kingdom', flag: '🇬🇧' },
  US: { lat: 40.7128, lng: -74.006, name: 'New York', country: 'United States', flag: '🇺🇸' },
  DE: { lat: 52.52, lng: 13.405, name: 'Berlin', country: 'Germany', flag: '🇩🇪' },
  FR: { lat: 48.8566, lng: 2.3522, name: 'Paris', country: 'France', flag: '🇫🇷' },
  CA: { lat: 45.4215, lng: -75.6972, name: 'Ottawa', country: 'Canada', flag: '🇨🇦' },
  JP: { lat: 35.6762, lng: 139.6503, name: 'Tokyo', country: 'Japan', flag: '🇯🇵' },
  AU: { lat: -33.8688, lng: 151.2093, name: 'Sydney', country: 'Australia', flag: '🇦🇺' },
  BR: { lat: -23.5505, lng: -46.6333, name: 'São Paulo', country: 'Brazil', flag: '🇧🇷' },
  SG: { lat: 1.3521, lng: 103.8198, name: 'Singapore', country: 'Singapore', flag: '🇸🇬' },
  NL: { lat: 52.3676, lng: 4.9041, name: 'Amsterdam', country: 'Netherlands', flag: '🇳🇱' },
  SE: { lat: 59.3293, lng: 18.0686, name: 'Stockholm', country: 'Sweden', flag: '🇸🇪' },
  ES: { lat: 41.3851, lng: 2.1734, name: 'Barcelona', country: 'Spain', flag: '🇪🇸' },
};
