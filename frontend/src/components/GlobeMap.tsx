// @ts-nocheck — react-globe.gl types are incomplete; runtime works correctly
'use client';

import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import type { GlobeMethods } from 'react-globe.gl';
import { feature } from 'topojson-client';

// Load react-globe.gl only on client (SSR disabled)
const Globe = dynamic(() => import('react-globe.gl'), { ssr: false });

// Bunche ISP countries
const LOCATIONS = [
  { name: 'United Kingdom',  lat: 51.5074,  lng: -0.1278,  flag: '🇬🇧', region: 'Europe' },
  { name: 'United States',   lat: 39.8283,  lng: -98.5795, flag: '🇺🇸', region: 'North America' },
  { name: 'Germany',        lat: 51.1657,  lng: 10.4515,  flag: '🇩🇪', region: 'Europe' },
  { name: 'France',          lat: 46.6034,  lng: 2.3488,   flag: '🇫🇷', region: 'Europe' },
  { name: 'Canada',          lat: 45.5017,  lng: -73.5673, flag: '🇨🇦', region: 'North America' },
  { name: 'Japan',           lat: 36.2048,  lng: 138.2529, flag: '🇯🇵', region: 'Asia Pacific' },
  { name: 'Australia',       lat: -25.2744, lng: 133.7751, flag: '🇦🇺', region: 'Oceania' },
  { name: 'Brazil',          lat: -23.5505, lng: -46.6333, flag: '🇧🇷', region: 'South America' },
  { name: 'Singapore',       lat: 1.3521,   lng: 103.8198, flag: '🇸🇬', region: 'Asia Pacific' },
];

const BRAND_GREEN = '#10B981';
const LIGHT_GREEN = '#4ADE80';
const WORLD_TOPO  = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

export default function GlobeMap() {
  const globeRef        = useRef<GlobeMethods | null>(null);
  const [isDark, setIsDark]               = useState(true);
  const [featuredIdx, setFeaturedIdx]     = useState(0);
  const [dims, setDims]                   = useState({ w: 520, h: 520 });
  const [ready, setReady]                 = useState(false);
  const [containerOpacity, setContainerOpacity] = useState(0);
  const [countriesData, setCountriesData] = useState<object[]>([]);

  // Detect system theme
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mq.matches);
    const handler = (e: MediaQueryQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Fetch world countries TopoJSON and convert to GeoJSON features
  useEffect(() => {
    const topoUrl = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';
    fetch(topoUrl)
      .then(r => r.json())
      .then(topo => {
        const countries = feature(
          topo as { objects: { countries: object } },
          (topo.objects as { countries: object }).countries
        ) as { features: object[] };
        setCountriesData(countries.features);
      })
      .catch(() => setCountriesData([]));
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

  // Pan camera when featured country changes
  useEffect(() => {
    if (!globeRef.current || !ready) return;
    const loc = LOCATIONS[featuredIdx];
    try {
      globeRef.current.pointOfView({ lat: loc.lat, lng: loc.lng, altitude: 2.2 }, 1800);
    } catch (_) {}
  }, [featuredIdx, ready]);

  // Per-theme colors — globe color = page background so globe "disappears" into the page
  // Atmosphere glow then creates a visible green edge outline around the globe
  //
  // Light mode: bg #fafafa, atmosphere green edge = globe "aware" of light theme
  // Dark mode: bg #0f0f0f, atmosphere green edge = globe "aware" of dark theme
  const globeBase        = isDark ? '#0f0f0f' : '#fafafa';
  const atmosphereColor  = BRAND_GREEN; // Always green for Bunche branding
  const atmosphereAlt     = isDark ? 0.15 : 0.22; // Higher = bigger/more visible atmosphere
  // Continent outlines: visible but not overpowering the atmosphere
  const outlineColor     = isDark ? '#16A34A' : '#374151';

  const featured = LOCATIONS[featuredIdx];

  return (
    <div className="relative w-full overflow-hidden" style={{ height: 480, minHeight: 480 }}>
      {/* Globe canvas */}
      <div
        className="absolute left-0 top-0 flex items-center justify-center"
        style={{ width: dims.w, height: dims.h, opacity: containerOpacity, transition: 'opacity 700ms ease' }}
      >
        <Globe
          key={isDark ? 'dark' : 'light'}
          ref={globeRef}
          width={dims.w}
          height={dims.h}
          // Globe sphere base color — plain strings, no day/night split
          globeColor={globeBase}
          // Force no night texture — transparent 1x1 PNG to prevent default dark texture
          nightImage="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
          backgroundColor="rgba(0,0,0,0)"
          // Atmosphere glow
          atmosphereColor={atmosphereColor}
          atmosphereAltitude={atmosphereAlt}
          // Continent outlines — polygons with transparent fills + colored strokes
          hexPolygonsData={[]}
          polygonsData={countriesData}
          polygonGeoJsonGeometry={(d: object) => (d as { geometry: object }).geometry}
          polygonCapColor={() => 'rgba(0,0,0,0)'}
          polygonSideColor={() => 'rgba(0,0,0,0)'}
          polygonStrokeColor={() => outlineColor}
          polygonAltitude={() => 0.001}
          // Country markers — brand green
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
          <div className={`rounded-2xl shadow-2xl p-4 flex items-center gap-3 border backdrop-blur-md ${isDark ? 'bg-[rgba(10,10,20,0.88)]' : 'bg-white shadow-lg'} ${isDark ? 'border-[rgba(16,185,129,0.3)]' : 'border-[rgba(16,185,129,0.4)]'}`}>
            <span className="text-3xl">{featured.flag}</span>
            <div>
              <p className={`font-bold text-sm ${isDark ? 'text-zinc-100' : 'text-zinc-800'}`}>{featured.name}</p>
              <p className={`text-xs mt-0.5 flex items-center gap-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
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
        className={`absolute bottom-4 left-4 rounded-xl px-3 py-2 shadow-lg border z-20`}
        style={{
          background: isDark ? 'rgba(10,10,20,0.88)' : 'white',
          borderColor: isDark ? 'rgba(16,185,129,0.3)' : 'rgba(16,185,129,0.4)',
          opacity: ready ? 1 : 0,
          transition: 'opacity 400ms',
        }}
      >
        <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>9 Countries</p>
        <p className="text-sm font-bold" style={{ color: BRAND_GREEN }}>ISP Coverage</p>
      </div>

      {/* Orbital ring decoration */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden flex items-center justify-center z-0">
        <motion.div
          className="rounded-full"
          style={{ width: dims.w * 0.87, height: dims.w * 0.87, border: `1px solid ${BRAND_GREEN}18` }}
          animate={{ rotate: 360 }}
          transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
        />
      </div>
    </div>
  );
}
