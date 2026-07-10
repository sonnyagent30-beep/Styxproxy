'use client';

import { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyGlobe = React.ComponentProps<'div'> & Record<string, any>;

// Dynamically import react-globe.gl (SSR disabled)
const Globe = dynamic(() => import('react-globe.gl'), { ssr: false }) as React.ComponentType<AnyGlobe>;

// Bunche green as primary accent
const BUNCHE_GREEN = '#10B981';

// Country data — Bunche ISP countries
const LOCATIONS = [
  { name: 'United Kingdom', location: [51.5074, -0.1278], flag: '🇬🇧', region: 'Europe' },
  { name: 'United States',   location: [39.8283, -98.5795], flag: '🇺🇸', region: 'North America' },
  { name: 'Germany',        location: [51.1657, 10.4515], flag: '🇩🇪', region: 'Europe' },
  { name: 'France',         location: [46.6034, 2.3488], flag: '🇫🇷', region: 'Europe' },
  { name: 'Canada',          location: [45.5017, -73.5673], flag: '🇨🇦', region: 'North America' },
  { name: 'Japan',           location: [36.2048, 138.2529], flag: '🇯🇵', region: 'Asia Pacific' },
  { name: 'Australia',       location: [-25.2744, 133.7751], flag: '🇦🇺', region: 'Oceania' },
  { name: 'Brazil',          location: [-23.5505, -46.6333], flag: '🇧🇷', region: 'South America' },
  { name: 'Singapore',       location: [1.3521, 103.8198], flag: '🇸🇬', region: 'Asia Pacific' },
];

// Atlasproxies-style dark config
const DARK_CONFIG = {
  phi: 0,
  theta: 0.2,
  dark: 1,
  diffuse: 1.2,
  instrument: 'brush' as const,
  mapSamples: 12000,       // dotted/halftone globe texture (was 24000)
  mapBrightness: 6,
  baseColor: [0.15, 0.15, 0.15] as [number, number, number],
  glowColor: [0.05, 0.05, 0.05] as [number, number, number],
  glowRadiusScale: 0.1,
  atmosphereColor: BUNCHE_GREEN,
  atmosphereAltitude: 0.15,
  ringsData: [] as { lat: number; lng: number }[],
  ringMaxRadius: 3,
  ringRepeatPeriod: 1500,
  ringPropagationSpeed: 2,
  ringColor: () => BUNCHE_GREEN,
  arcsData: [] as { startLat: number; startLng: number; endLat: number; endLng: number; color: () => string }[],
  arcStartLat: 'startLat',
  arcStartLng: 'startLng',
  arcEndLat: 'endLat',
  arcEndLng: 'endLng',
  arcColor: 'color',
  arcAltitude: 0.3,
  arcStroke: 0.6,
  // Points = markers
  pointsData: [] as { lat: number; lng: number; name: string; flag: string; region: string }[],
  pointLat: 'lat',
  pointLng: 'lng',
  pointAltitude: 0.01,
  pointColor: () => '#7C3AED',
  pointRadius: 0.04,
};

// Atlasproxies-style light config
const LIGHT_CONFIG = {
  ...DARK_CONFIG,
  dark: 0,
  diffuse: 2,
  mapBrightness: 1.8,
  baseColor: [0.95, 0.95, 0.95] as [number, number, number],
  glowColor: [1, 1, 1] as [number, number, number],
  glowRadiusScale: 0.05,
  atmosphereColor: '#6366F1',
};

// Loading skeleton — Atlasproxies concentric rings + globe SVG
function LoadingSkeleton({ isDark }: { isDark: boolean }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center">
      {/* Outermost ring */}
      <div
        className="absolute rounded-full"
        style={{
          inset: '5%',
          border: `1px solid ${isDark ? 'rgba(16,185,129,0.12)' : 'rgba(99,102,241,0.12)'}`,
        }}
      />
      {/* Middle ring */}
      <div
        className="absolute rounded-full"
        style={{
          inset: '15%',
          border: `1px solid ${isDark ? 'rgba(16,185,129,0.12)' : 'rgba(99,102,241,0.12)'}`,
        }}
      />
      {/* Innermost with gradient glow */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div
          className="relative rounded-full"
          style={{
            width: '72%',
            aspectRatio: '1',
            border: `1px solid ${isDark ? 'rgba(16,185,129,0.18)' : 'rgba(99,102,241,0.18)'}`,
            background: isDark
              ? 'radial-gradient(circle at 40% 35%, rgba(16,185,129,0.12) 0%, rgba(124,58,237,0.06) 50%, transparent 70%)'
              : 'radial-gradient(circle at 40% 35%, rgba(99,102,241,0.10) 0%, rgba(16,185,129,0.05) 50%, transparent 70%)',
            boxShadow: isDark
              ? '0 0 80px rgba(16,185,129,0.10), 0 0 40px rgba(124,58,237,0.05)'
              : '0 0 60px rgba(99,102,241,0.08)',
          }}
        />
      </div>
      {/* Globe SVG icon */}
      <div className="absolute inset-0 flex items-center justify-center">
        <svg
          className="w-1/3 h-1/3"
          style={{ color: isDark ? 'rgba(16,185,129,0.4)' : 'rgba(99,102,241,0.4)' }}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <ellipse cx="12" cy="12" rx="6" ry="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
        </svg>
      </div>
    </div>
  );
}

export default function GlobeMap() {
  const [isDark, setIsDark] = useState(true);
  const [globeLoaded, setGlobeLoaded] = useState(false);
  const [featuredIdx, setFeaturedIdx] = useState(0);
  const [containerOpacity, setContainerOpacity] = useState(0);

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
      setFeaturedIdx(i => (i + 1) % LOCATIONS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Points = country markers
  const points = useMemo(() =>
    LOCATIONS.map(l => ({
      lat: l.location[0],
      lng: l.location[1],
      name: l.name,
      flag: l.flag,
      region: l.region,
    })),
    []
  );

  // Arcs from UK to all others (Bunche green)
  const arcs = useMemo(() => {
    const uk = LOCATIONS[0];
    return LOCATIONS.slice(1).map(l => ({
      startLat: uk.location[0],
      startLng: uk.location[1],
      endLat: l.location[0],
      endLng: l.location[1],
      color: () => BUNCHE_GREEN,
    }));
  }, []);

  // Rings for each location
  const rings = useMemo(() =>
    LOCATIONS.map(l => ({ lat: l.location[0], lng: l.location[1] })),
    []
  );

  const config = isDark ? DARK_CONFIG : LIGHT_CONFIG;

  return (
    <div
      className="relative w-full"
      style={{ height: 520 }}
    >
      {/* Globe canvas — starts transparent, fades in */}
      <div
        className="absolute inset-0 mx-auto"
        style={{
          maxWidth: 600,
          opacity: containerOpacity,
          transition: 'opacity 700ms ease',
        }}
      >
        <Globe
          {...config}
          ringsData={rings}
          arcsData={arcs}
          pointsData={points}
          width={600}
          height={600}
          onGlobeReady={() => {
            setTimeout(() => setContainerOpacity(1), 50);
            setGlobeLoaded(true);
          }}
        />
      </div>

      {/* Loading skeleton — shown while globe initializes */}
      <AnimatePresence>
        {!globeLoaded && (
          <motion.div
            key="skeleton"
            className="absolute inset-0 mx-auto"
            style={{ maxWidth: 600 }}
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <LoadingSkeleton isDark={isDark} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Featured country callout card — Atlasproxies style */}
      <AnimatePresence mode="wait">
        <motion.div
          key={featuredIdx}
          className="absolute pointer-events-none"
          style={{ right: '5%', top: '10%', minWidth: 165 }}
          initial={{ opacity: 0, scale: 0.8, y: 8 }}
          animate={{ opacity: globeLoaded ? 1 : 0, scale: globeLoaded ? 1 : 0.8, y: 0 }}
          exit={{ opacity: 0, scale: 0.8, y: 8 }}
          transition={{ duration: 0.45, ease: 'backOut', delay: 0.15 }}
        >
          <div
            className="rounded-2xl shadow-2xl p-4 flex items-center gap-3 border"
            style={{
              background: isDark ? 'rgba(26,26,46,0.93)' : 'rgba(255,255,255,0.93)',
              borderColor: isDark ? `${BUNCHE_GREEN}33` : '#e4e4e7',
              backdropFilter: 'blur(12px)',
            }}
          >
            <span className="text-3xl">{LOCATIONS[featuredIdx].flag}</span>
            <div>
              <p
                className="font-bold text-sm leading-tight"
                style={{ color: isDark ? '#f4f4f5' : '#18181b' }}
              >
                {LOCATIONS[featuredIdx].name}
              </p>
              <p className="text-xs mt-0.5 flex items-center gap-1" style={{ color: '#71717a' }}>
                <svg
                  className="w-3 h-3"
                  style={{ color: BUNCHE_GREEN }}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
                    clipRule="evenodd"
                  />
                </svg>
                {LOCATIONS[featuredIdx].region}
              </p>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Coverage badge — bottom left */}
      <div
        className="absolute bottom-4 left-4 rounded-xl px-3 py-2 shadow-lg border backdrop-blur-sm"
        style={{
          background: isDark ? 'rgba(26,26,46,0.9)' : 'rgba(255,255,255,0.9)',
          borderColor: isDark ? `${BUNCHE_GREEN}33` : '#e4e4e7',
        }}
      >
        <p className="text-xs" style={{ color: '#71717a' }}>9 Countries</p>
        <p className="text-sm font-bold" style={{ color: BUNCHE_GREEN }}>ISP Coverage</p>
      </div>

      {/* Rotating orbital ring — Atlasproxies style */}
      <div className="absolute pointer-events-none" style={{ inset: 0 }}>
        <motion.div
          className="absolute rounded-full"
          style={{
            top: '50%',
            left: '50%',
            width: 280,
            height: 280,
            marginTop: -140,
            marginLeft: -140,
            border: `1px solid ${BUNCHE_GREEN}20`,
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
        />
      </div>
    </div>
  );
}
