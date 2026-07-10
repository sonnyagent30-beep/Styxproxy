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

const BRAND_GREEN  = '#10B981';
const LIGHT_GREEN  = '#4ADE80';
const WORLD_TOPO  = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

// Generate random points inside a polygon using ray casting
function pointsInPolygon(polygon: [number, number][], count: number): [number, number][] {
  const points: [number, number][] = [];
  let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity;
  for (const [lng, lat] of polygon) {
    minLng = Math.min(minLng, lng); maxLng = Math.max(maxLng, lng);
    minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat);
  }
  let attempts = 0;
  while (points.length < count && attempts < count * 20) {
    attempts++;
    const lng = minLng + Math.random() * (maxLng - minLng);
    const lat = minLat + Math.random() * (maxLat - minLat);
    if (pointInPolygon([lng, lat], polygon)) {
      points.push([lng, lat]);
    }
  }
  return points;
}

function pointInPolygon(point: [number, number], polygon: [number, number][]): boolean {
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
      inside = !inside;
    }
  }
  return inside;
}

// Parse TopoJSON → GeoJSON polygon coordinates
function getPolygonCoords(geometry: { type: string; coordinates: object }): [number, number][][] {
  if (geometry.type === 'Polygon') {
    return geometry.coordinates as [number, number][][];
  }
  if (geometry.type === 'MultiPolygon') {
    return (geometry.coordinates as [number, number][][][]).flat();
  }
  return [];
}

// Pre-generated continent dots (continent coverage points)
let continentDotsCache: { lat: number; lng: number }[] | null = null;

function getContinentDots(): { lat: number; lng: number }[] {
  if (continentDotsCache) return continentDotsCache;

  // Minimal world land polygon coords (pre-computed as [lng, lat] pairs)
  // These approximate major continent shapes — sampled densely
  const LAND_POLYGONS: [number, number][][] = [
    // North America
    [[-170,65],[-140,70],[-60,75],[0,85],[20,75],[40,45],[60,60],[80,65],[100,75],[170,65],[180,60],[170,45],[-170,45],[-170,65]],
    // Greenland
    [[-75,75],[-45,75],[-20,85],[0,75],[0,60],[-20,60],[-45,65],[-75,75]],
    // South America
    [[-80,10],[-40,-5],[-35,5],[-50,10],[-55,0],[-80,-5],[-80,10],[-80,0],[-75,-20],[-60,-25],[-35,-25],[-40,-5],[-80,10]],
    // Europe
    [[-10,35],[0,40],[5,38],[15,40],[25,50],[30,60],[40,65],[60,65],[70,70],[50,80],[10,70],[-10,60],[-5,35],[-10,35]],
    // Africa
    [[-20,35],[-5,35],[10,40],[30,35],[40,30],[50,10],[40,-5],[20,-10],[10,-35],[-20,-35],[-30,-20],[-20,5],[-18,15],[-20,35]],
    // Asia
    [[30,35],[40,35],[50,40],[60,35],[70,35],[80,25],[90,25],[100,20],[110,25],[120,20],[130,25],[140,35],[145,45],[160,55],[170,65],[180,65],[180,45],[170,40],[160,35],[140,30],[120,20],[100,25],[80,20],[60,20],[50,30],[40,30],[30,35]],
    // India
    [[65,30],[70,25],[80,20],[85,25],[90,25],[90,30],[80,30],[75,30],[70,30],[65,30]],
    // Southeast Asia
    [[95,20],[105,20],[110,15],[115,5],[120,5],[120,15],[115,20],[105,25],[100,25],[95,20]],
    // Japan
    [[128,40],[130,40],[135,40],[140,45],[145,45],[145,35],[140,35],[135,35],[130,35],[128,35],[128,40]],
    // Australia
    [[115,-20],[130,-15],[140,-15],[150,-25],[155,-30],[150,-40],[140,-35],[130,-35],[120,-35],[115,-25],[115,-20]],
    // New Zealand
    [[165,-45],[175,-45],[175,-35],[170,-35],[165,-35],[165,-45]],
    // UK
    [[-5,50],[0,50],[0,55],[5,58],[2,58],[-5,55],[-5,50]],
    // Iceland
    [[-25,63],[-13,63],[-13,67],[-25,67],[-25,63]],
    // Madagascar
    [[43,-25],[50,-25],[50,-12],[43,-12],[43,-25]],
    // Sri Lanka
    [[80,10],[82,10],[82,0],[80,0],[80,10]],
    // Philippines
    [[115,20],[120,20],[125,20],[125,5],[120,5],[115,5],[115,20]],
    // Indonesia
    [[95,-5],[110,-5],[115,5],[120,0],[130,0],[140,5],[140,-5],[130,-10],[120,-5],[110,-10],[100,-10],[95,-5]],
  ];

  const dots: { lat: number; lng: number }[] = [];
  for (const polygon of LAND_POLYGONS) {
    // Density: ~1 point per 50km² equivalent → sample based on bbox area
    const bboxArea = (Math.max(...polygon.map(p => p[0])) - Math.min(...polygon.map(p => p[0]))) *
                     (Math.max(...polygon.map(p => p[1])) - Math.min(...polygon.map(p => p[1])));
    const count = Math.max(15, Math.min(200, Math.floor(bboxArea * 2)));
    const pts = pointsInPolygon(polygon, count);
    for (const [lng, lat] of pts) {
      dots.push({ lat, lng });
    }
  }

  continentDotsCache = dots;
  return dots;
}

export default function GlobeMap() {
  const globeRef = useRef<GlobeMethods | null>(null);
  const [isDark, setIsDark] = useState(true);
  const [featuredIdx, setFeaturedIdx] = useState(0);
  const [dims, setDims] = useState({ w: 520, h: 520 });
  const [ready, setReady] = useState(false);
  const [containerOpacity, setContainerOpacity] = useState(0);
  const [continentDots, setContinentDots] = useState<{ lat: number; lng: number }[]>([]);

  // Detect system theme
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mq.matches);
    const handler = (e: MediaQueryEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Generate continent dots on client
  useEffect(() => {
    setContinentDots(getContinentDots());
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

  // Per-theme colors
  // Dark mode: dark sphere + light-green dots + green glow
  // Light mode: white sphere + dark dots + green glow ring
  const globeBase       = isDark ? '#0a0a12' : '#ffffff';
  const atmosphereColor = isDark ? LIGHT_GREEN : '#16a34a';
  const atmosphereAlt   = isDark ? 0.18 : 0.10;
  // Continent dots: light green (dark mode), dark gray (light mode)
  const continentDotColor  = isDark ? LIGHT_GREEN : '#374151';
  const continentDotRadius = isDark ? 0.25 : 0.22;

  const featured = LOCATIONS[featuredIdx];

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
          // Atmosphere glow
          atmosphereColor={atmosphereColor}
          atmosphereAltitude={atmosphereAlt}
          // Continent dots + country markers merged into one points layer
          // Differentiated by `type` property: 'continent' | 'country'
          pointsData={[
            ...continentDots.map(d => ({ ...d, type: 'continent' })),
            ...LOCATIONS.map(d => ({ ...d, type: 'country' })),
          ]}
          pointLat="lat"
          pointLng="lng"
          pointColor={(d: { type?: string }) =>
            d.type === 'country' ? BRAND_GREEN : continentDotColor
          }
          pointRadius={(d: { type?: string }) =>
            d.type === 'country' ? 0.55 : continentDotRadius
          }
          pointAltitude={(d: { type?: string }) =>
            d.type === 'country' ? 0.007 : 0.003
          }
          pointResolution={8}
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
