'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ThreeGlobe = dynamic(() => import('three-globe').then((m: any) => m.default as unknown as React.ComponentType<any>), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center" style={{ height: '380px' }}>
      <div className="animate-pulse text-sm" style={{ color: '#71717a' }}>Loading globe...</div>
    </div>
  ),
});

const COUNTRY_DATA = [
  { lat: 51.5074, lng: -0.1278, name: 'UK', country: 'United Kingdom', region: 'Europe', flag: '🇬🇧' },
  { lat: 40.7128, lng: -74.006, name: 'US', country: 'United States', region: 'North America', flag: '🇺🇸' },
  { lat: 52.52, lng: 13.405, name: 'DE', country: 'Germany', region: 'Europe', flag: '🇩🇪' },
  { lat: 48.8566, lng: 2.3522, name: 'FR', country: 'France', region: 'Europe', flag: '🇫🇷' },
  { lat: 45.5017, lng: -73.5673, name: 'CA', country: 'Canada', region: 'North America', flag: '🇨🇦' },
  { lat: 35.6762, lng: 139.6503, name: 'JP', country: 'Japan', region: 'Asia Pacific', flag: '🇯🇵' },
  { lat: -33.8688, lng: 151.2093, name: 'AU', country: 'Australia', region: 'Oceania', flag: '🇦🇺' },
  { lat: -23.5505, lng: -46.6333, name: 'BR', country: 'Brazil', region: 'South America', flag: '🇧🇷' },
  { lat: 1.3521, lng: 103.8198, name: 'SG', country: 'Singapore', region: 'Asia Pacific', flag: '🇸🇬' },
];

export default function GlobeViz() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [featured, setFeatured] = useState(COUNTRY_DATA[0]);
  const [isDark, setIsDark] = useState(true);
  const globeRef = useRef<any>(null);

  // Detect theme
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Cycle featured country every 4 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const idx = Math.floor(Date.now() / 4000) % COUNTRY_DATA.length;
      setFeatured(COUNTRY_DATA[idx]);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Build arc data: UK to all other countries
  const arcData = useCallback(() => {
    const uk = COUNTRY_DATA[0];
    return COUNTRY_DATA.slice(1).map(loc => ({
      startLat: uk.lat,
      startLng: uk.lng,
      endLat: loc.lat,
      endLng: loc.lng,
      color: '#10B981',
    }));
  }, []);

  // Build point data: all countries
  const pointData = useCallback(() => {
    return COUNTRY_DATA.map(loc => ({
      lat: loc.lat,
      lng: loc.lng,
      name: loc.country,
      size: 0.8,
      color: '#10B981',
    }));
  }, []);

  const globeConfig = {
    animateIn: true,
    rotateSpeed: 0.5,
  };

  // Theme-based colors
  const globeColor = isDark ? '#0a1628' : '#e5e7eb';
  const glowColor = isDark ? '#10B981' : '#6366F1';
  const glowOpacity = isDark ? 0.35 : 0.15;
  const glowStrength = isDark ? 0.8 : 0.4;

  return (
    <div className="relative w-full flex flex-col items-center">
      <div className="relative w-full" style={{ height: '380px' }}>
        {/* ThreeGlobe canvas */}
        <div ref={containerRef} className="absolute inset-0">
          <ThreeGlobe
            ref={globeRef}
            // Globe body
            globeColor={globeColor}
            // Atmosphere glow
            atmosphereColor={glowColor}
            atmosphereAltitude={0.18}
            // Points (dots)
            pointsData={pointData()}
            pointLat="lat"
            pointLng="lng"
            pointAltitude={0.015}
            pointRadius="size"
            pointColor="color"
            // Rings around points
            ringMaxRadius={6}
            ringPropagationSpeed={3}
            ringColor={() => '#10B981'}
            ringOpacity={0.6}
            // Arcs
            arcsData={arcData()}
            arcStartLat="startLat"
            arcStartLng="startLng"
            arcEndLat="endLat"
            arcEndLng="endLng"
            arcColor="color"
            arcAltitude={0.3}
            arcStroke={0.5}
            arcDashLength={0.4}
            arcDashGap={0.2}
            arcDashAnimateTime={2000}
            // Labels
            labelsData={COUNTRY_DATA}
            labelLat="lat"
            labelLng="lng"
            labelText="name"
            labelSize={0.6}
            labelColor={() => '#10B981'}
            labelDotRadius={0.3}
            labelDotOrientation={() => 'right'}
            labelAltitude={0.02}
          />
        </div>

        {/* Featured country callout */}
        <div
          className="absolute rounded-2xl shadow-2xl p-4 flex items-center gap-3 border transition-all duration-700"
          style={{
            right: '8%',
            top: '15%',
            minWidth: '165px',
            background: isDark ? 'rgba(26,26,46,0.95)' : 'rgba(255,255,255,0.95)',
            borderColor: isDark ? '#10B98133' : '#e4e4e7',
            animation: 'floatCard 3s ease-in-out infinite',
            backdropFilter: 'blur(12px)',
          }}
        >
          <span className="text-3xl">{featured.flag}</span>
          <div>
            <p className="font-bold text-sm leading-tight" style={{ color: isDark ? '#f4f4f5' : '#18181b' }}>
              {featured.country}
            </p>
            <p className="text-xs flex items-center gap-1 mt-0.5" style={{ color: '#71717a' }}>
              <svg className="w-3 h-3" style={{ color: '#10B981' }} fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
              </svg>
              {featured.region}
            </p>
          </div>
        </div>

        {/* Coverage badge */}
        <div
          className="absolute bottom-4 left-4 rounded-xl px-3 py-2 shadow-lg border backdrop-blur-sm"
          style={{
            background: isDark ? 'rgba(26,26,46,0.9)' : 'rgba(255,255,255,0.9)',
            borderColor: isDark ? '#10B98133' : '#e4e4e7',
          }}
        >
          <p className="text-xs" style={{ color: '#71717a' }}>9 Countries</p>
          <p className="text-sm font-bold" style={{ color: '#10B981' }}>ISP Coverage</p>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-5 mt-5 text-sm">
        <span className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: '#10B981' }} />
          <span style={{ color: '#71717a' }}>ISP Proxies</span>
        </span>
      </div>

      <style>{`
        @keyframes floatCard {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
      `}</style>
    </div>
  );
}
