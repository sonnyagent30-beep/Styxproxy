// @ts-nocheck — react-globe.gl types are incomplete; runtime works correctly
'use client';

import { useEffect, useState, useRef } from 'react';
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

const BUNCHE_GREEN = '#10B981';

function LoadingSkeleton({ isDark }: { isDark: boolean }) {
  const ring = isDark ? 'rgba(16,185,129,0.1)' : 'rgba(99,102,241,0.1)';
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div style={{ width: '62%', aspectRatio: '1', borderRadius: '50%', border: `1px solid ${ring}`, boxShadow: isDark ? '0 0 60px rgba(16,185,129,0.08)' : '0 0 40px rgba(99,102,241,0.06)' }} />
      <div style={{ position: 'absolute', width: '78%', aspectRatio: '1', borderRadius: '50%', border: `1px solid ${ring}` }} />
      <div style={{ position: 'absolute', width: '92%', aspectRatio: '1', borderRadius: '50%', border: `1px solid ${ring}` }} />
      <svg className="absolute w-1/4 h-1/4 opacity-30" style={{ color: isDark ? '#10B981' : '#6366F1' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
        <circle cx="12" cy="12" r="10" /><ellipse cx="12" cy="12" rx="6" ry="10" /><line x1="2" y1="12" x2="22" y2="12" />
      </svg>
    </div>
  );
}

export default function GlobeMap() {
  const globeRef = useRef<GlobeMethods | null>(null);
  const [isDark, setIsDark] = useState(true);
  const [featuredIdx, setFeaturedIdx] = useState(0);
  const [dims, setDims] = useState({ w: 520, h: 520 });
  const [ready, setReady] = useState(false);
  const [containerOpacity, setContainerOpacity] = useState(0);

  // Detect theme
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Responsive sizing — container fills available width
  useEffect(() => {
    const update = () => {
      // Globe should fill the left half of the hero on desktop
      // On mobile it fills full width
      const container = document.getElementById('globe-container');
      if (container) {
        const w = container.offsetWidth;
        const size = Math.min(w, 600);
        setDims({ w: Math.round(size), h: Math.round(size) });
      } else {
        // Fallback: use window width (max 600 for globe size)
        const size = Math.min(window.innerWidth, 600);
        setDims({ w: Math.round(size), h: Math.round(size) });
      }
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
    if (!globeRef.current) return;
    const loc = LOCATIONS[featuredIdx];
    try {
      globeRef.current.pointOfView({ lat: loc.lat, lng: loc.lng, altitude: 2.2 }, 1800);
    } catch (_) {}
  }, [featuredIdx]);

  const bgColor = isDark ? '#0a0a0f' : '#f4f4f5';
  const featured = LOCATIONS[featuredIdx];

  return (
    <div
      id="globe-container"
      className="relative w-full overflow-hidden"
      style={{ height: 480, background: bgColor, minHeight: 480 }}
    >
      {/* Globe canvas — react-globe.gl manages its own canvas */}
      <div
        className="absolute inset-0 flex items-center justify-center"
        style={{
          width: dims.w,
          height: dims.h,
          margin: 'auto',
          opacity: containerOpacity,
          transition: 'opacity 700ms ease',
        }}
      >
        <Globe
          ref={globeRef}
          width={dims.w}
          height={dims.h}
          // Globe sphere colors — dark for dark mode, light for light mode
          globeColor={isDark ? 'rgba(20,20,40,1)' : 'rgba(220,220,240,1)'}
          nightColor={isDark ? 'rgba(5,5,15,1)' : 'rgba(160,160,180,1)'}
          // Green atmosphere glow
          atmosphereColor={BUNCHE_GREEN}
          atmosphereAltitude={0.18}
          // Country markers — green dots (no arcs, no rings)
          pointsData={LOCATIONS}
          pointLat="lat"
          pointLng="lng"
          pointColor={() => BUNCHE_GREEN}
          pointRadius={0.5}
          pointAltitude={0.007}
          // No arcs between countries
          arcsData={[]}
          // No rings
          ringsData={[]}
          // No polygon borders
          polygonsData={[]}
          // Auto-rotate slowly
          autoRotate={true}
          autoRotateSpeed={0.35}
          // Initial camera
          onGlobeReady={() => {
            setContainerOpacity(1);
            setTimeout(() => setReady(true), 200);
            if (globeRef.current) {
              try {
                globeRef.current.pointOfView({ lat: LOCATIONS[0].lat, lng: LOCATIONS[0].lng, altitude: 2.2 }, 0);
              } catch (_) {}
            }
          }}
        />
      </div>

      {/* Loading skeleton */}
      <AnimatePresence>
        {!ready && (
          <motion.div
            className="absolute inset-0 flex items-center justify-center pointer-events-none"
            style={{ width: dims.w, height: dims.h, margin: 'auto' }}
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <LoadingSkeleton isDark={isDark} />
          </motion.div>
        )}
      </AnimatePresence>

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
              borderColor: isDark ? `${BUNCHE_GREEN}33` : '#e4e4e7',
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
      {ready && (
        <div
          className="absolute bottom-4 left-4 rounded-xl px-3 py-2 shadow-lg border backdrop-blur-sm z-20"
          style={{
            background: isDark ? 'rgba(26,26,46,0.9)' : 'rgba(255,255,255,0.9)',
            borderColor: isDark ? `${BUNCHE_GREEN}33` : '#e4e4e7',
          }}
        >
          <p className="text-xs" style={{ color: '#71717a' }}>9 Countries</p>
          <p className="text-sm font-bold" style={{ color: BUNCHE_GREEN }}>ISP Coverage</p>
        </div>
      )}

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
