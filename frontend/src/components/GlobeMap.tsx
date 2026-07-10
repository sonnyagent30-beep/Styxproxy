// @ts-nocheck — react-globe.gl types are incomplete; runtime works correctly
'use client';

import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import type { GlobeMethods } from 'react-globe.gl';
import { feature } from 'topojson-client';
import type { Topology, GeometryCollection } from 'topojson-specification';

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

const BUNCHE_GREEN = '#10B981';
const ACCENT_PURPLE = '#8B3FE8';

function SunIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  );
}

export default function GlobeMap() {
  const globeRef = useRef<GlobeMethods | null>(null);
  const [isDark, setIsDark] = useState(true);
  const [featuredIdx, setFeaturedIdx] = useState(0);
  const [dims, setDims] = useState({ w: 520, h: 520 });
  const [ready, setReady] = useState(false);
  const [containerOpacity, setContainerOpacity] = useState(0);
  const [worldGeojson, setWorldGeojson] = useState<GeoJSON.FeatureCollection | null>(null);

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

  // Fetch world countries GeoJSON for continent dots
  useEffect(() => {
    fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
      .then(r => r.json())
      .then((topo: Topology) => {
        const countries = feature(
          topo,
          topo.objects.countries as GeometryCollection
        ) as GeoJSON.FeatureCollection;
        setWorldGeojson(countries);
      })
      .catch(() => {});
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
    if (!globeRef.current) return;
    const loc = LOCATIONS[featuredIdx];
    try {
      globeRef.current.pointOfView({ lat: loc.lat, lng: loc.lng, altitude: 2.2 }, 1800);
    } catch (_) {}
  }, [featuredIdx]);

  const toggleTheme = () => setIsDark(d => !d);

  const featured = LOCATIONS[featuredIdx];

  // Globe colors per theme
  const sphereColor = isDark ? 'rgba(12,12,28,1)' : 'rgba(235,235,245,1)';
  const polygonFill = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(30,30,50,0.08)';
  const polygonStroke = isDark ? 'rgba(255,255,255,0.18)' : 'rgba(30,30,50,0.2)';
  const dotColor = isDark ? 'rgba(255,255,255,0.55)' : 'rgba(30,30,50,0.45)';
  const atmosphereColor = isDark ? BUNCHE_GREEN : '#6ea0ff';

  return (
    <div
      className="relative w-full overflow-hidden"
      style={{
        height: 480,
        minHeight: 480,
        background: isDark ? '#0a0a0f' : '#f4f4f5',
      }}
    >
      {/* Theme toggle button */}
      <button
        onClick={toggleTheme}
        className="absolute top-3 right-3 z-30 rounded-xl p-2.5 border shadow-lg transition-all duration-200 hover:scale-105"
        style={{
          background: isDark ? 'rgba(26,26,46,0.9)' : 'rgba(255,255,255,0.9)',
          borderColor: isDark ? `${BUNCHE_GREEN}33` : '#e4e4e7',
          color: isDark ? '#f4f4f5' : '#18181b',
        }}
        aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        <AnimatePresence mode="wait" initial={false}>
          {isDark ? (
            <motion.div key="moon" initial={{ opacity: 0, rotate: -90, scale: 0.5 }} animate={{ opacity: 1, rotate: 0, scale: 1 }} exit={{ opacity: 0, rotate: 90, scale: 0.5 }} transition={{ duration: 0.2 }}>
              <MoonIcon />
            </motion.div>
          ) : (
            <motion.div key="sun" initial={{ opacity: 0, rotate: 90, scale: 0.5 }} animate={{ opacity: 1, rotate: 0, scale: 1 }} exit={{ opacity: 0, rotate: -90, scale: 0.5 }} transition={{ duration: 0.2 }}>
              <SunIcon />
            </motion.div>
          )}
        </AnimatePresence>
      </button>

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
          ref={globeRef}
          width={dims.w}
          height={dims.h}
          // Dark/light sphere base
          globeColor={sphereColor}
          nightColor={isDark ? 'rgba(5,5,15,1)' : 'rgba(180,180,200,1)'}
          // Atmosphere
          atmosphereColor={atmosphereColor}
          atmosphereAltitude={0.18}
          // World countries as polygon dots — continents as dot outlines
          polygonsData={worldGeojson?.features ?? []}
          polygonCapColor={() => polygonFill}
          polygonSideColor={() => polygonStroke}
          polygonStrokeColor={() => dotColor}
          polygonLabel={() => ''}
          // Country markers — green dots
          pointsData={LOCATIONS}
          pointLat="lat"
          pointLng="lng"
          pointColor={() => BUNCHE_GREEN}
          pointRadius={0.55}
          pointAltitude={0.007}
          // Featured country — glowing purple ring
          ringsData={ready ? [{
            lat: featured.lat,
            lng: featured.lng,
          }] : []}
          ringColor={() => ACCENT_PURPLE}
          ringMaxRadius={3.5}
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
          <div
            className="rounded-2xl shadow-2xl p-4 flex items-center gap-3 border backdrop-blur-md"
            style={{
              background: isDark ? 'rgba(26,26,46,0.92)' : 'rgba(255,255,255,0.92)',
              borderColor: isDark ? `${ACCENT_PURPLE}55` : '#e4e4e7',
            }}
          >
            <span className="text-3xl">{featured.flag}</span>
            <div>
              <p className="font-bold text-sm" style={{ color: isDark ? '#f4f4f5' : '#18181b' }}>
                {featured.name}
              </p>
              <p className="text-xs mt-0.5 flex items-center gap-1" style={{ color: '#71717a' }}>
                <svg className="w-3 h-3" style={{ color: BUNCHE_GREEN }} fill="currentColor" viewBox="0 0 20 20">
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
          background: isDark ? 'rgba(26,26,46,0.9)' : 'rgba(255,255,255,0.9)',
          borderColor: isDark ? `${BUNCHE_GREEN}33` : '#e4e4e7',
          opacity: ready ? 1 : 0,
          transition: 'opacity 400ms',
        }}
      >
        <p className="text-xs" style={{ color: '#71717a' }}>9 Countries</p>
        <p className="text-sm font-bold" style={{ color: BUNCHE_GREEN }}>ISP Coverage</p>
      </div>

      {/* Orbital ring decoration */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden flex items-center justify-center z-0">
        <motion.div
          className="rounded-full"
          style={{
            width: dims.w * 0.87,
            height: dims.w * 0.87,
            border: `1px solid ${BUNCHE_GREEN}18`,
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
        />
      </div>
    </div>
  );
}
