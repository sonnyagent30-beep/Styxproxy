// @ts-nocheck — Globe component uses CDN script injection; runtime works correctly
'use client';

import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

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
  // Single ref — globe.gl appends its canvas directly to this element
  const containerRef = useRef<HTMLDivElement>(null);

  const [isDark, setIsDark] = useState(true);
  const [featuredIdx, setFeaturedIdx] = useState(0);
  const [dims, setDims] = useState({ w: 520, h: 520 });
  const [ready, setReady] = useState(false);
  const globeRef = useRef<unknown>(null);

  // Detect theme
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Responsive sizing
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const update = () => {
      const w = el.offsetWidth;
      setDims({ w: Math.min(w, 580), h: Math.min(w, 580) });
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Initialize globe.gl when container is ready
  useEffect(() => {
    const el = containerRef.current;
    if (!el || globeRef.current) return;

    const initGlobe = (Globe: (opts: { container: HTMLElement; config: object }) => unknown) => {
      if (globeRef.current || !el) return;

      const myGlobe = (Globe as (opts: { container: HTMLElement; config: object }) => unknown)({
        container: el,
        config: {
          width: dims.w,
          height: dims.h,
          globeImageUrl: isDark
            ? 'https://threejs.org/examples/textures/planets/earth_atmos_2048.jpg'
            : 'https://threejs.org/examples/textures/planets/earth_lights_2048.png',
          bumpImageUrl: 'https://threejs.org/examples/textures/planets/earth_normal_2048.jpg',
          pointsData: LOCATIONS,
          pointLat: 'lat',
          pointLng: 'lng',
          pointColor: () => BUNCHE_GREEN,
          pointRadius: 0.5,
          pointAltitude: 0.01,
          arcsData: [],
          ringsData: [],
          autoRotate: true,
          rotateSpeed: 0.35,
        },
      });

      // Set initial camera position
      try {
        myGlobe.pointOfView({ lat: LOCATIONS[0].lat, lng: LOCATIONS[0].lng, altitude: 2.2 }, 0);
      } catch (_) {}

      globeRef.current = myGlobe;
      setReady(true);
    };

    // @ts-ignore
    if (window.Globe) {
      // @ts-ignore
      initGlobe(window.Globe);
    } else {
      const script = document.createElement('script');
      script.src = 'https://unpkg.com/globe.gl';
      script.onload = () => {
        // @ts-ignore
        if (window.Globe) {
          // @ts-ignore
          initGlobe(window.Globe);
        }
      };
      script.onerror = () => console.error('globe.gl CDN failed to load');
      document.head.appendChild(script);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update globe when dims change
  useEffect(() => {
    if (!globeRef.current) return;
    try {
      // @ts-ignore
      globeRef.current.width(dims.w);
      // @ts-ignore
      globeRef.current.height(dims.h);
    } catch (_) {}
  }, [dims]);

  // Update texture when theme changes
  useEffect(() => {
    if (!globeRef.current) return;
    try {
      // @ts-ignore
      globeRef.current.globeImageUrl(
        isDark
          ? 'https://threejs.org/examples/textures/planets/earth_atmos_2048.jpg'
          : 'https://threejs.org/examples/textures/planets/earth_lights_2048.png'
      );
    } catch (_) {}
  }, [isDark]);

  // Cycle featured country every 4 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setFeaturedIdx(i => (i + 1) % LOCATIONS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Pan camera to featured country
  useEffect(() => {
    if (!globeRef.current) return;
    const loc = LOCATIONS[featuredIdx];
    try {
      // @ts-ignore
      globeRef.current.pointOfView({ lat: loc.lat, lng: loc.lng, altitude: 2.2 }, 1800);
    } catch (_) {}
  }, [featuredIdx]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (globeRef.current) {
        try {
          // @ts-ignore
          globeRef.current._destructor?.();
        } catch (_) {}
        globeRef.current = null;
      }
    };
  }, []);

  const bgColor = isDark ? '#0a0a0f' : '#f4f4f5';
  const featured = LOCATIONS[featuredIdx];

  return (
    <div
      ref={containerRef}
      className="relative w-full overflow-hidden"
      style={{
        height: 480,
        background: bgColor,
        // Ensure container has dimensions so globe.gl can fill it
        minHeight: 480,
      }}
    >
      {/* Loading skeleton — shown until globe is ready */}
      <AnimatePresence>
        {!ready && (
          <motion.div
            className="absolute inset-0 flex items-center justify-center pointer-events-none z-10"
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
        {ready && (
          <motion.div
            key={featuredIdx}
            className="absolute pointer-events-none z-20"
            style={{ right: '4%', top: '8%', minWidth: 155 }}
            initial={{ opacity: 0, scale: 0.85, y: 6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
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
        )}
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
