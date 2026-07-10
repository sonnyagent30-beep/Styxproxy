'use client';

import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';

// Dynamically import globe.gl (SSR disabled)
const Globe = dynamic(() => import('react-globe.gl'), { ssr: false });

// Bunche ISP countries
const LOCATIONS = [
  { name: 'United Kingdom', lat: 51.5074, lng: -0.1278, flag: '🇬🇧', region: 'Europe' },
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

// Loading skeleton — concentric rings while globe initializes
function LoadingSkeleton({ isDark }: { isDark: boolean }) {
  const ringColor = isDark ? 'rgba(16,185,129,0.1)' : 'rgba(99,102,241,0.1)';
  const glowColor = isDark
    ? 'radial-gradient(circle, rgba(16,185,129,0.1) 0%, transparent 70%)'
    : 'radial-gradient(circle, rgba(99,102,241,0.1) 0%, transparent 70%)';
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div style={{ width: '70%', aspectRatio: '1', borderRadius: '50%', border: `1px solid ${ringColor}`, boxShadow: glowColor }} />
      <div className="absolute" style={{ width: '85%', aspectRatio: '1', borderRadius: '50', border: `1px solid ${ringColor}` }} />
      <div className="absolute" style={{ width: '95%', aspectRatio: '1', borderRadius: '50', border: `1px solid ${ringColor}` }} />
      <svg className="absolute w-1/4 h-1/4 opacity-30" style={{ color: isDark ? '#10B981' : '#6366F1' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
        <circle cx="12" cy="12" r="10" /><ellipse cx="12" cy="12" rx="6" ry="10" /><line x1="2" y1="12" x2="22" y2="12" />
      </svg>
    </div>
  );
}

export default function GlobeMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeElRef = useRef<unknown>(null);
  const [globe, setGlobe] = useState<unknown>(null);
  const [isDark, setIsDark] = useState(true);
  const [globeLoaded, setGlobeLoaded] = useState(false);
  const [containerOpacity, setContainerOpacity] = useState(0);
  const [featuredIdx, setFeaturedIdx] = useState(0);
  const [dims, setDims] = useState({ w: 600, h: 600 });

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

  // Responsive sizing via ResizeObserver
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width } = entry.contentRect;
        const size = Math.min(width, 600);
        setDims({ w: Math.round(size), h: Math.round(size) });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Configure globe when it mounts / dims change / theme changes
  useEffect(() => {
    if (!globe) return;
    const g = globe as {
      width: (w: number) => void;
      height: (h: number) => void;
      globeImageUrl: (url: string | null) => void;
      bumpImageUrl: (url: string | null) => void;
      pointsData: (data: object[]) => void;
      pointColor: () => string;
      pointRadius: () => number;
      pointAltitude: () => number;
      ringsData: (data: object[]) => void;
      ringColor: () => string;
      ringMaxRadius: () => number;
      autoRotate: (val: boolean) => void;
      pauseAnimation: () => void;
    };

    // Size
    g.width(dims.w);
    g.height(dims.h);

    // Earth textures — use real NASA Blue Marble imagery
    if (isDark) {
      g.globeImageUrl('//unpkg.com/three-globe@2.31.0/example/img/earth-night.jpg');
      g.bumpImageUrl('//unpkg.com/three-globe@2.31.0/example/img/earth-topology.png');
    } else {
      g.globeImageUrl('//unpkg.com/three-globe@2.31.0/example/img/earth-blue-marble.jpg');
      g.bumpImageUrl('//unpkg.com/three-globe@2.31.0/example/img/earth-topology.png');
    }

    // Country markers — green dots
    g.pointsData(LOCATIONS);
    g.pointColor(() => BUNCHE_GREEN);
    g.pointRadius(0.5);
    g.pointAltitude(0.01);

    // No rings
    g.ringsData([]);

    // Auto-rotate slowly
    g.autoRotate(true);
  }, [globe, dims, isDark]);

  // Point the camera at each country on cycle
  useEffect(() => {
    if (!globe) return;
    const g = globe as { pointOfView: (p: { lat: number; lng: number; altitude: number }, ms: number) => void };
    const loc = LOCATIONS[featuredIdx];
    try {
      g.pointOfView({ lat: loc.lat, lng: loc.lng, altitude: 2.2 }, 1500);
    } catch (_) {}
  }, [featuredIdx, globe]);

  const bgColor = isDark ? '#0a0a0f' : '#f4f4f5';
  const featured = LOCATIONS[featuredIdx];

  return (
    <div ref={containerRef} className="relative w-full" style={{ height: 480, background: bgColor }}>
      {/* Globe canvas — fades in after init */}
      <div
        className="absolute inset-0 flex items-center justify-center mx-auto"
        style={{
          width: dims.w,
          height: dims.h,
          maxWidth: '100%',
          opacity: containerOpacity,
          transition: 'opacity 700ms ease',
        }}
      >
        {/* @ts-expect-error — globe.gl types are incomplete */}
        <Globe
          ref={globeElRef}
          onGlobeReady={() => {
            setTimeout(() => setContainerOpacity(1), 200);
            setGlobeLoaded(true);
          }}
          onGlobeInit={g => setGlobe(g)}
        />
      </div>

      {/* Loading skeleton while globe initializes */}
      <AnimatePresence>
        {!globeLoaded && (
          <motion.div
            className="absolute inset-0 flex items-center justify-center mx-auto pointer-events-none"
            style={{ maxWidth: dims.w, maxHeight: dims.h }}
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <LoadingSkeleton isDark={isDark} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Featured country callout card */}
      <AnimatePresence mode="wait">
        <motion.div
          key={featuredIdx}
          className="absolute pointer-events-none"
          style={{ right: '4%', top: '8%', minWidth: 160 }}
          initial={{ opacity: 0, scale: 0.85, y: 6 }}
          animate={{ opacity: globeLoaded ? 1 : 0, scale: globeLoaded ? 1 : 0.85, y: 0 }}
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

      {/* Orbital ring — decorative */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden flex items-center justify-center">
        <motion.div
          className="rounded-full"
          style={{
            width: dims.w * 0.88,
            height: dims.w * 0.88,
            border: `1px solid ${BUNCHE_GREEN}18`,
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
        />
      </div>
    </div>
  );
}
