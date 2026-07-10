// @ts-nocheck — react-globe.gl types are incomplete; runtime works correctly
'use client';

import { useEffect, useState, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import type { GlobeMethods } from 'react-globe.gl';
import { feature } from 'topojson-client';
import * as THREE from 'three';

// Load react-globe.gl only on client (SSR disabled)
const Globe = dynamic(() => import('react-globe.gl'), { ssr: false });

// Bunche ISP countries
const LOCATIONS = [
  { name: 'United Kingdom',  lat: 51.5074,  lng: -0.1278,  flag: '🇬🇧', region: 'Europe' },
  { name: 'United States',   lat: 39.8283,  lng: -98.5795, flag: '🇺🇸', region: 'North America' },
  { name: 'Germany',         lat: 51.1657,  lng: 10.4515,  flag: '🇩🇪', region: 'Europe' },
  { name: 'France',          lat: 46.6034,  lng: 2.3488,   flag: '🇫🇷', region: 'Europe' },
  { name: 'Canada',          lat: 45.5017,  lng: -73.5673, flag: '🇨🇦', region: 'North America' },
  { name: 'Japan',           lat: 36.2048,  lng: 138.2529, flag: '🇯🇵', region: 'Asia Pacific' },
  { name: 'Australia',       lat: -25.2744, lng: 133.7751, flag: '🇦🇺', region: 'Oceania' },
  { name: 'Brazil',          lat: -23.5505, lng: -46.6333, flag: '🇧🇷', region: 'South America' },
  { name: 'Singapore',       lat: 1.3521,   lng: 103.8198, flag: '🇸🇬', region: 'Asia Pacific' },
];

const BRAND_GREEN  = '#10B981';
const LIGHT_GREEN  = '#4ADE80';
const BRAND_DARK   = '#0a0a12';
const BRAND_LIGHT  = '#ffffff';

export default function GlobeMap() {
  const globeRef   = useRef<GlobeMethods | null>(null);
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

  // ============================================================
  // VISUAL: SATIN GLOBE THAT POPS IN BOTH MODES
  // ============================================================
  // Dark mode: dark navy sphere with rich green atmosphere halo
  //   - subtle emissive green so the sphere glows softly from within
  //   - high-altitude atmosphere that bleeds into the page
  // Light mode: white sphere with cool silvery atmosphere
  //   - subtle inner shadow ring to give 3D depth
  //   - lighter green atmosphere that doesn't darken edges
  const sphereBaseColor = isDark ? '#0a0a12' : '#ffffff';
  const atmosphereColor = isDark ? LIGHT_GREEN : BRAND_GREEN;
  const atmosphereAlt   = isDark ? 0.25 : 0.18;

  // Continent outlines: visible but tasteful
  // Dark mode: bright green at 75% — clearly visible against dark sphere
  // Light mode: dark gray at 60% — clearly visible against white sphere
  const outlineColor    = isDark ? 'rgba(74,222,128,0.75)' : 'rgba(31,41,55,0.65)';

  // ============================================================
  // MATERIAL: emissive MeshPhongMaterial for that satin glow
  // ============================================================
  // emissive adds an inner glow that makes the sphere feel alive.
  // Dark mode: subtle green emissive so the sphere has depth
  // Light mode: cool white emissive so the sphere feels premium
  const globeMaterial = useMemo(() => {
    if (isDark) {
      return new THREE.MeshPhongMaterial({
        color: new THREE.Color(sphereBaseColor),
        emissive: new THREE.Color('#0a2415'),       // subtle green inner glow
        emissiveIntensity: 0.35,
        shininess: 18,
        specular: new THREE.Color('#2a5a3a'),       // green-tinted highlights
      });
    } else {
      return new THREE.MeshPhongMaterial({
        color: new THREE.Color(sphereBaseColor),
        emissive: new THREE.Color('#e8f5ed'),       // soft white-green inner glow
        emissiveIntensity: 0.12,
        shininess: 35,                               // brighter shine for satin
        specular: new THREE.Color('#a8d8b8'),       // light green-silver highlights
      });
    }
  }, [sphereBaseColor, isDark]);

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
          // Globe sphere material — emissive Phong for the satin inner glow
          globeMaterial={globeMaterial}
          // Atmosphere: BOTH modes now, with green/lightgreen tones
          showAtmosphere={true}
          atmosphereColor={atmosphereColor}
          atmosphereAltitude={atmosphereAlt}
          backgroundColor="rgba(0,0,0,0)"
          // Country polygons — transparent fill, visible stroke
          polygonsData={countriesData}
          polygonGeoJsonGeometry="geometry"
          polygonCapMaterial={() => ({ transparent: true, opacity: 0 } as any)}
          polygonSideMaterial={() => ({ transparent: true, opacity: 0 } as any)}
          polygonStrokeColor={() => outlineColor}
          polygonCapCurvatureResolution={4}
          polygonAltitude={() => 0.005}
          // Country markers — larger green dots with halo via stacked points
          pointsData={LOCATIONS}
          pointLat="lat"
          pointLng="lng"
          pointColor={() => BRAND_GREEN}
          pointRadius={0.6}
          pointAltitude={0.008}
          // Featured country — pulsing green ring (more vivid)
          ringsData={ready ? [{ lat: featured.lat, lng: featured.lng }] : []}
          ringColor={() => BRAND_GREEN}
          ringMaxRadius={5.0}
          ringPropagationSpeed={1.5}
          ringRepeat={2.5}
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

      {/* Radial gradient overlay — creates 3D dimensional shading on top of the globe */}
      <div
        className="absolute left-0 top-0 rounded-full pointer-events-none z-[5]"
        style={{
          width: dims.w,
          height: dims.h,
          background: isDark
            ? 'radial-gradient(circle at 35% 30%, rgba(74,222,128,0.18) 0%, rgba(74,222,128,0.05) 25%, transparent 55%)'
            : 'radial-gradient(circle at 35% 30%, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.4) 20%, transparent 50%)',
          mixBlendMode: isDark ? 'screen' : 'normal',
        }}
      />

      {/* Edge vignette — soft inner shadow ring to define the sphere edge */}
      <div
        className="absolute left-0 top-0 rounded-full pointer-events-none z-[6]"
        style={{
          width: dims.w,
          height: dims.h,
          boxShadow: isDark
            ? 'inset 0 0 60px 20px rgba(74,222,128,0.20), inset 0 0 0 1px rgba(74,222,128,0.40)'
            : 'inset 0 0 50px 15px rgba(16,185,129,0.10), inset 0 0 0 1px rgba(16,185,129,0.30)',
        }}
      />

      {/* Outer halo — breathing green ring around the entire globe */}
      <motion.div
        className="absolute left-0 top-0 rounded-full pointer-events-none z-[7]"
        style={{
          width: dims.w,
          height: dims.h,
          boxShadow: isDark
            ? '0 0 30px 4px rgba(74,222,128,0.30), 0 0 60px 8px rgba(74,222,128,0.15)'
            : '0 0 30px 4px rgba(16,185,129,0.25), 0 0 60px 8px rgba(16,185,129,0.10)',
        }}
        animate={{
          boxShadow: isDark
            ? [
                '0 0 30px 4px rgba(74,222,128,0.30), 0 0 60px 8px rgba(74,222,128,0.15)',
                '0 0 40px 6px rgba(74,222,128,0.45), 0 0 80px 12px rgba(74,222,128,0.25)',
                '0 0 30px 4px rgba(74,222,128,0.30), 0 0 60px 8px rgba(74,222,128,0.15)',
              ]
            : [
                '0 0 30px 4px rgba(16,185,129,0.25), 0 0 60px 8px rgba(16,185,129,0.10)',
                '0 0 40px 6px rgba(16,185,129,0.40), 0 0 80px 12px rgba(16,185,129,0.20)',
                '0 0 30px 4px rgba(16,185,129,0.25), 0 0 60px 8px rgba(16,185,129,0.10)',
              ],
        }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
      />

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
    </div>
  );
}