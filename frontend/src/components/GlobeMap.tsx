// @ts-nocheck — react-globe.gl types are incomplete; runtime works correctly
'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import type { GlobeMethods } from 'react-globe.gl';

// Load react-globe.gl only on client (SSR disabled)
const Globe = dynamic(() => import('react-globe.gl'), { ssr: false });

// Bunche ISP countries
const LOCATIONS = [
  { name: 'United Kingdom', lat: 51.5074, lng: -0.1278,  flag: '🇬🇧', region: 'Europe' },
  { name: 'United States',  lat: 39.8283,  lng: -98.5795, flag: '🇺🇸', region: 'North America' },
  { name: 'Germany',        lat: 51.1657,  lng: 10.4515,  flag: '🇩🇪', region: 'Europe' },
  { name: 'France',         lat: 46.6034,  lng: 2.3488,   flag: '🇫🇷', region: 'Europe' },
  { name: 'Canada',         lat: 45.5017,  lng: -73.5673, flag: '🇨🇦', region: 'North America' },
  { name: 'Japan',          lat: 36.2048,  lng: 138.2529, flag: '🇯🇵', region: 'Asia Pacific' },
  { name: 'Australia',      lat: -25.2744, lng: 133.7751, flag: '🇦🇺', region: 'Oceania' },
  { name: 'Brazil',         lat: -23.5505, lng: -46.6333, flag: '🇧🇷', region: 'South America' },
  { name: 'Singapore',      lat: 1.3521,   lng: 103.8198, flag: '🇸🇬', region: 'Asia Pacific' },
];

const BRAND_GREEN  = '#10B981';
const LIGHT_GREEN  = '#4ADE80';
const LIGHT_GRAY   = '#6B7280';

// World countries GeoJSON for continent dots
const WORLD_COUNTRIES = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

export default function GlobeMap() {
  const globeRef  = useRef<GlobeMethods | null>(null);
  const [isDark, setIsDark] = useState(true);
  const [featuredIdx, setFeaturedIdx] = useState(0);
  const [dims, setDims] = useState({ w: 520, h: 520 });
  const [ready, setReady] = useState(false);
  const [containerOpacity, setContainerOpacity] = useState(0);

  // Detect system theme
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Responsive sizing
  useEffect(() => {
    const update = () => {
      const size = Math.min(window.innerWidth, 600);
      setDims({ w: Math.round(size), h: Math.round(size) });
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  // Cycle featured country every 4 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setFeaturedIdx(i => (i + 1) % LOCATIONS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const featured = LOCATIONS[featuredIdx];

  // Apply theme colors imperatively to the THREE.js scene objects
  const applyTheme = useCallback((globe: GlobeMethods, dark: boolean) => {
    try {
      const scene = globe.scene();
      if (!scene) return;

      const dotHex = dark ? LIGHT_GREEN : LIGHT_GRAY;
      const sphereHex = dark ? '0f0f1a' : 'ffffff';
      const atmHex = dark ? LIGHT_GREEN : '93C5FD';

      scene.traverse((obj: object) => {
        const o = obj as Record<string, unknown>;
        const mat = (o.material ?? o.side) as Record<string, unknown> | undefined;
        if (!mat) return;

        const material = mat as Record<string, unknown>;
        // THREE.MeshBasicMaterial / MeshStandardMaterial has a 'color' property
        const color = material.color as Record<string, (c: string) => void> | undefined;
        if (!color || typeof color.set !== 'function') return;

        // Get current hex
        const getHex = () => {
          try { return (color.getHexString ?? (() => ''))() as string; } catch { return ''; }
        };
        const hex = getHex();

        // Skip known fixed colors
        if (['10b981', '4ade80', '93c5fd'].includes(hex)) return;

        // Sphere / atmosphere / globe base
        if (hex === '0f0f1a' || hex === 'ffffff' || hex === '0a0a1e' || hex === '000000') {
          color.set(dark ? `#${sphereHex}` : `#${sphereHex}`);
          return;
        }

        // Anything else → continent dot color
        color.set(`#${dotHex.replace('#', '')}`);
      });
    } catch (_) {}
  }, []);

  // Apply theme whenever isDark changes AND globe is ready
  useEffect(() => {
    if (!ready || !globeRef.current) return;
    applyTheme(globeRef.current, isDark);
  }, [isDark, ready, applyTheme]);

  // Pan camera when featured country changes
  useEffect(() => {
    if (!globeRef.current || !ready) return;
    const loc = LOCATIONS[featuredIdx];
    try {
      globeRef.current.pointOfView({ lat: loc.lat, lng: loc.lng, altitude: 2.2 }, 1800);
    } catch (_) {}
  }, [featuredIdx, ready]);

  // Per-theme colors
  // Dark mode: dark sphere + light-green dots + green glow
  // Light mode: white sphere + dark dots + green glow ring
  const globeBase       = isDark ? '#0a0a12' : '#e8e8ec';
  const atmosphereColor = isDark ? LIGHT_GREEN : BRAND_GREEN;
  const atmosphereAlt   = isDark ? 0.18 : 0.14;
  const dotColorHex     = isDark ? LIGHT_GREEN : '#1F2937';

  return (
    <div
      className="relative w-full overflow-hidden"
      style={{ height: 480, minHeight: 480 }}
    >
      {/* Globe canvas */}
      <div
        className="absolute left-0 top-0 flex items-center justify-center"
        style={{
          width: dims.w,
          height: dims.h,
          opacity: containerOpacity,
          transition: 'opacity 700ms ease',
        }}
      >
        <Globe
          key={isDark ? 'dark' : 'light'}
          ref={globeRef}
          width={dims.w}
          height={dims.h}
          // Globe sphere base color
          globeColor={() => globeBase}
          nightColor={() => globeBase}
          backgroundColor="rgba(0,0,0,0)"
          // Atmosphere
          atmosphereColor={atmosphereColor}
          atmosphereAltitude={atmosphereAlt}
          // Continent dots — hex polygons with useDots
          hexPolygonsData={`${WORLD_COUNTRIES}`}
          hexPolygonGeoJsonGeometry={() => 'geometry'}
          hexPolygonUseDots={() => true}
          hexPolygonDotResolution={6}
          hexPolygonMargin={0.2}
          hexPolygonColor={() => dotColorHex}
          hexPolygonAltitude={() => 0.004}
          // Country markers
          pointsData={LOCATIONS}
          pointLat="lat"
          pointLng="lng"
          pointColor={() => BRAND_GREEN}
          pointRadius={0.55}
          pointAltitude={0.007}
          // Featured country — green ring
          ringsData={ready ? [{ lat: featured.lat, lng: featured.lng }] : []}
          ringColor={() => BRAND_GREEN}
          ringMaxRadius={4.0}
          ringPropagationSpeed={1.2}
          ringRepeat={2.2}
          // No arcs
          arcsData={[]}
          // Auto-rotate
          autoRotate={true}
          autoRotateSpeed={0.3}
          // On ready
          onGlobeReady={() => {
            setContainerOpacity(1);
            setTimeout(() => setReady(true), 300);
            if (globeRef.current) {
              try {
                globeRef.current.pointOfView({ lat: LOCATIONS[0].lat, lng: LOCATIONS[0].lng, altitude: 2.2 }, 0);
              } catch (_) {}
            }
          }}
        />
      </div>

      {/* Featured country callout */}
      <AnimatePresence mode="wait">
        <motion.div
          key={featuredIdx}
          className="absolute pointer-events-none z-20"
          style={{ right: '4%', top: '8%', minWidth: 155 }}
          initial={{ opacity: 0, scale: 0.85, y: 6 }}
          animate={{ opacity: ready ? 1 : 0, scale: ready ? 1 : 0.85, y: 0 }}
          exit={{ opacity: 0, scale: 0.85, y: 6 }}
          transition={{ duration: 0.4, ease: 'backOut', delay: 0.1 }}
        >
          <div className="rounded-2xl shadow-2xl p-4 flex items-center gap-3 border backdrop-blur-md bg-[rgba(10,10,20,0.88)] border-[rgba(16,185,129,0.3)]">
            <span className="text-3xl">{featured.flag}</span>
            <div>
              <p className="font-bold text-sm text-zinc-100">{featured.name}</p>
              <p className="text-xs mt-0.5 flex items-center gap-1 text-zinc-400">
                <svg className="w-3 h-3" style={{ color: BRAND_GREEN }} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                </svg>
                {featured.region}
              </p>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Coverage badge */}
      <div
        className="absolute bottom-4 left-4 rounded-xl px-3 py-2 shadow-lg border backdrop-blur-sm z-20"
        style={{
          background: 'rgba(10,10,20,0.88)',
          borderColor: 'rgba(16,185,129,0.3)',
          opacity: ready ? 1 : 0,
          transition: 'opacity 400ms',
        }}
      >
        <p className="text-xs text-zinc-400">9 Countries</p>
        <p className="text-sm font-bold" style={{ color: BRAND_GREEN }}>ISP Coverage</p>
      </div>

      {/* Orbital ring decoration */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden flex items-center justify-center z-0">
        <motion.div
          className="rounded-full"
          style={{
            width: dims.w * 0.87,
            height: dims.w * 0.87,
            border: `1px solid ${BRAND_GREEN}18`,
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
        />
      </div>
    </div>
  );
}
