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

  // Fetch world countries TopoJSON and convert to GeoJSON features — done at component mount
  // and converted to GeoJSON features BEFORE passing to react-globe.gl. This is the
  // proven approach: pre-fetched GeoJSON works reliably where hexTopoData URL access fails.
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
  // VISUAL DESIGN — premium globe in both modes
  // ============================================================
  // Sphere base color matches page background — globe "disappears" into the canvas.
  // Atmosphere glow provides the visible edge in dark mode.
  // CSS layer (radial gradient + edge vignette) provides the depth in both modes.
  const sphereBaseColor = isDark ? '#0a0a12' : '#fafafa';
  const atmosphereColor = isDark ? '#4ADE80' : BRAND_GREEN;
  const atmosphereAlt   = isDark ? 0.22 : 0.15;

  // Continent outlines: solid hex colors (NOT rgba) for guaranteed visibility
  // Dark mode: bright lime-green
  // Light mode: deep brand-green
  const outlineColor    = isDark ? '#84cc16' : '#16a34a';

  // ============================================================
  // MATERIAL: Emissive MeshPhongMaterial
  // ============================================================
  // Emissive adds inner glow — sphere feels alive, not flat.
  // Light mode: very subtle warm tint, satin specular for sheen.
  // Dark mode: subtle green emissive matches the brand.
  const globeMaterial = useMemo(() => {
    if (isDark) {
      return new THREE.MeshPhongMaterial({
        color: new THREE.Color(sphereBaseColor),
        emissive: new THREE.Color('#0a2415'),
        emissiveIntensity: 0.4,
        shininess: 20,
        specular: new THREE.Color('#2a5a3a'),
      });
    } else {
      return new THREE.MeshPhongMaterial({
        color: new THREE.Color(sphereBaseColor),
        emissive: new THREE.Color('#dcfce7'),
        emissiveIntensity: 0.18,
        shininess: 28,
        specular: new THREE.Color('#86efac'),
      });
    }
  }, [sphereBaseColor, isDark]);

  // ============================================================
  // CONTINENT MATERIAL — explicit MeshBasicMaterial with visible color.
  // This is what gets rendered for each country polygon. With opacity 0, the polygon
  // surface is invisible but the polygon STROKE (perimeter edges) shows in outlineColor.
  // We use polygonStrokeColor to control the stroke color.
  const continentMaterial = useMemo(() => {
    // Solid color material for continent fills when we need them visible.
    // When outlinesOnly is true, we use opacity 0 for invisible fills.
    return new THREE.MeshBasicMaterial({
      color: new THREE.Color(outlineColor),
      transparent: true,
      opacity: 0.0,  // transparent fill — only stroke shows
      side: THREE.DoubleSide,
    });
  }, [outlineColor]);

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
          // Globe sphere material
          globeMaterial={globeMaterial}
          // Atmosphere — only dark mode gets the full glow.
          // Light mode gets a much smaller, subtler atmosphere.
          showAtmosphere={true}
          atmosphereColor={atmosphereColor}
          atmosphereAltitude={atmosphereAlt}
          backgroundColor="rgba(0,0,0,0)"
          // Continent polygons — pre-fetched GeoJSON, transparent fills, visible strokes.
          // This is THE proven approach: polygonsData + polygonGeoJsonGeometry works.
          polygonsData={countriesData}
          polygonGeoJsonGeometry={(d: object) => (d as { geometry: object }).geometry}
          polygonCapColor={() => 'rgba(0,0,0,0)'}
          polygonSideColor={() => 'rgba(0,0,0,0)'}
          polygonStrokeColor={() => outlineColor}
          polygonCapCurvatureResolution={5}
          polygonAltitude={() => 0.005}
          // Country markers — bunche cities, brand green
          pointsData={LOCATIONS}
          pointLat="lat"
          pointLng="lng"
          pointColor={() => BRAND_GREEN}
          pointRadius={0.55}
          pointAltitude={0.007}
          // Featured country — pulsing green ring
          ringsData={ready ? [{ lat: featured.lat, lng: featured.lng }] : []}
          ringColor={() => BRAND_GREEN}
          ringMaxRadius={4.5}
          ringPropagationSpeed={1.4}
          ringRepeat={2.2}
          // No arcs
          arcsData={[]}
          // Auto-rotate
          autoRotate={true}
          autoRotateSpeed={0.3}
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

      {/* Radial gradient overlay — top-left lit sphere effect. Adds dimensional depth. */}
      <div
        className="absolute left-0 top-0 rounded-full pointer-events-none z-[5]"
        style={{
          width: dims.w,
          height: dims.h,
          background: isDark
            ? 'radial-gradient(circle at 30% 25%, rgba(74,222,128,0.10) 0%, transparent 45%)'
            : 'radial-gradient(circle at 30% 25%, rgba(255,255,255,0.85) 0%, rgba(255,255,255,0.3) 20%, transparent 50%)',
        }}
      />

      {/* Sphere edge vignette — soft inner shadow that defines the sphere edge */}
      <div
        className="absolute left-0 top-0 rounded-full pointer-events-none z-[6]"
        style={{
          width: dims.w,
          height: dims.h,
          boxShadow: isDark
            ? 'inset 0 0 80px 30px rgba(0,0,0,0.5), inset 0 0 0 1px rgba(74,222,128,0.45)'
            : 'inset 0 0 60px 20px rgba(16,185,129,0.08), inset 0 0 0 1px rgba(16,185,129,0.35)',
        }}
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