'use client';

import { useRef, useEffect, useState } from 'react';

// Country locations with lat/lng
const LOCATIONS = [
  { lat: 51.5074, lng: -0.1278, name: 'UK', country: 'United Kingdom', region: 'Europe', flag: '🇬🇧', type: 'ISP' },
  { lat: 40.7128, lng: -74.006, name: 'US', country: 'United States', region: 'North America', flag: '🇺🇸', type: 'ISP' },
  { lat: 52.52, lng: 13.405, name: 'DE', country: 'Germany', region: 'Europe', flag: '🇩🇪', type: 'ISP' },
  { lat: 48.8566, lng: 2.3522, name: 'FR', country: 'France', region: 'Europe', flag: '🇫🇷', type: 'ISP' },
  { lat: 45.5017, lng: -73.5673, name: 'CA', country: 'Canada', region: 'North America', flag: '🇨🇦', type: 'ISP' },
  { lat: 35.6762, lng: 139.6503, name: 'JP', country: 'Japan', region: 'Asia Pacific', flag: '🇯🇵', type: 'ISP' },
  { lat: -33.8688, lng: 151.2093, name: 'AU', country: 'Australia', region: 'Oceania', flag: '🇦🇺', type: 'ISP' },
  { lat: -23.5505, lng: -46.6333, name: 'BR', country: 'Brazil', region: 'South America', flag: '🇧🇷', type: 'ISP' },
  { lat: 1.3521, lng: 103.8198, name: 'SG', country: 'Singapore', region: 'Asia Pacific', flag: '🇸🇬', type: 'ISP' },
  { lat: 35.0, lng: -40.0, name: 'RES', country: 'Residential', region: 'Global', flag: '🌍', type: 'RESIDENTIAL' },
  { lat: 25.0, lng: 45.0, name: 'MOB', country: 'Mobile 4G', region: 'Global', flag: '📱', type: 'MOBILE' },
  { lat: 30.0, lng: -10.0, name: 'DC', country: 'Datacenter', region: 'Global', flag: '🏢', type: 'DC' },
];

const ISP_LOCATIONS = LOCATIONS.filter(l => l.type === 'ISP');

function markerColor(type: string): [number, number, number] {
  if (type === 'ISP') return [99, 102, 241];
  if (type === 'RESIDENTIAL') return [168, 85, 247];
  if (type === 'MOBILE') return [59, 130, 246];
  return [249, 115, 22];
}

// Cobe configs for light and dark mode
const COBE_CONFIG = {
  dark: {
    baseColor: [0.08, 0.08, 0.12],    // near-black sphere
    mapBrightness: 0.8,
    mapSamples: 18000,
    diffuse: 0.6,
    glowColor: [0.3, 0.1, 0.6],
    markerColor: [99, 102, 241],
    arcColor: [99, 102, 241, 0.5] as unknown as [number, number, number],
  },
  light: {
    baseColor: [0.85, 0.85, 0.88],    // light gray sphere
    mapBrightness: 1.2,
    mapSamples: 18000,
    diffuse: 0.4,
    glowColor: [0.5, 0.3, 0.9],
    markerColor: [99, 102, 241],
    arcColor: [99, 102, 241, 0.5] as unknown as [number, number, number],
  },
};

export default function GlobeMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const globeRef = useRef<{ update: (s: object) => void; destroy: () => void } | null>(null);
  const [featuredLocation, setFeaturedLocation] = useState(ISP_LOCATIONS[0]);
  const [isDark, setIsDark] = useState(true);

  // Detect light/dark mode
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  // Rotate featured location every 4 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const idx = Math.floor(Date.now() / 4000) % ISP_LOCATIONS.length;
      setFeaturedLocation(ISP_LOCATIONS[idx]);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Initialize / update cobe globe when theme changes
  useEffect(() => {
    let mounted = true;
    let animationId: number;

    async function initGlobe() {
      if (!canvasRef.current) return;
      try {
        const { default: createGlobe } = await import('cobe');

        // Destroy old globe if exists
        if (globeRef.current) {
          globeRef.current.destroy();
          globeRef.current = null;
        }

        if (!mounted) return;

        const config = isDark ? COBE_CONFIG.dark : COBE_CONFIG.light;

        // Build markers
        const markers = LOCATIONS.map(loc => ({
          location: [loc.lat, loc.lng] as [number, number],
          size: loc.type === 'ISP' ? 0.9 : 0.5,
          color: markerColor(loc.type) as [number, number, number],
        }));

        // Build arcs from UK to other ISP countries
        const arcs = ISP_LOCATIONS.slice(1).map(loc => ({
          from: [ISP_LOCATIONS[0].lat, ISP_LOCATIONS[0].lng] as [number, number],
          to: [loc.lat, loc.lng] as [number, number],
          color: config.arcColor as unknown as [number, number, number],
        }));

        let rotation = 0;

        const globe = createGlobe(canvasRef.current, {
          width: 600,
          height: 600,
          phi: 0,
          theta: 0,
          mapSamples: config.mapSamples,
          mapBrightness: config.mapBrightness,
          baseColor: config.baseColor as [number, number, number],
          markerColor: config.markerColor as [number, number, number],
          glowColor: config.glowColor as [number, number, number],
          markers,
          arcs,
          arcColor: config.arcColor,
          arcWidth: 1.2,
          arcHeight: 0.25,
          diffuse: config.diffuse,
          devicePixelRatio: Math.min(window.devicePixelRatio, 2),
          dark: isDark ? 1 : 0,
        });

        globeRef.current = globe;

        const animate = () => {
          if (!globeRef.current) return;
          rotation += 0.0025;
          globeRef.current.update({ theta: rotation });
          animationId = requestAnimationFrame(animate);
        };
        animationId = requestAnimationFrame(animate);
      } catch (e) {
        console.error('Failed to load cobe:', e);
      }
    }

    initGlobe();

    return () => {
      mounted = false;
      cancelAnimationFrame(animationId);
      if (globeRef.current) {
        try { globeRef.current.destroy(); } catch (_) {}
        globeRef.current = null;
      }
    };
  }, [isDark]);

  return (
    <div className="relative w-full flex flex-col items-center">
      <div className="relative w-full" style={{ height: '380px' }}>
        {/* Globe canvas */}
        <div className="absolute inset-0 flex items-center justify-center">
          <canvas
            ref={canvasRef}
            width={600}
            height={600}
            className="w-full h-full max-w-[380px] max-h-[380px]"
          />
        </div>

        {/* Featured location callout card */}
        <div
          className="absolute bg-white rounded-2xl shadow-2xl p-4 flex items-center gap-3 transition-all duration-700"
          style={{
            right: '8%',
            top: '15%',
            minWidth: '160px',
            animation: 'floatCard 3s ease-in-out infinite',
          }}
        >
          <span className="text-3xl">{featuredLocation.flag}</span>
          <div>
            <p className="font-bold text-sm text-gray-900 leading-tight">{featuredLocation.country}</p>
            <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
              <svg className="w-3 h-3 text-indigo-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
              </svg>
              {featuredLocation.region}
            </p>
          </div>
        </div>

        {/* Country count badge */}
        <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur rounded-xl px-3 py-2 shadow-lg border border-gray-100">
          <p className="text-xs text-gray-500">9 Countries</p>
          <p className="text-sm font-bold text-gray-900">ISP Coverage</p>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-5 mt-5 text-sm">
        <span className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 inline-block" />
          <span className="text-gray-400">ISP Proxies</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-purple-500 inline-block" />
          <span className="text-gray-400">Residential</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" />
          <span className="text-gray-400">Mobile 4G</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block" />
          <span className="text-gray-400">Datacenter</span>
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
