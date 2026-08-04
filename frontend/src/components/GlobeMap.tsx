// @ts-nocheck — react-globe.gl types are incomplete; runtime works correctly
'use client';

import { useEffect, useState, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import type { GlobeMethods } from 'react-globe.gl';
import { feature } from 'topojson-client';
import * as THREE from 'three';
import { COUNTRIES, PRODUCT_COUNTRIES, type CountryInfo } from '@/lib/products';

// Load react-globe.gl only on client (SSR disabled)
const Globe = dynamic(() => import('react-globe.gl'), { ssr: false });

// Brand colors — CORRECTED to match Styxproxy brand
const BRAND_GREEN       = '#0AD25A';   // --primary (CORRECTED from #10B981)
const BRAND_GREEN_LIGHT = '#2AED6C';   // --primary-light (CORRECTED from #34D399)

// Short display names for product types
const PRODUCT_SHORT_NAMES: Record<string, string> = {
  ISP:         'ISP',
  RESIDENTIAL: 'Residential',
  MOBILE:      'Mobile 4G',
  DC:          'Datacenter',
};

// Country coordinates for arc traffic simulation
const COUNTRY_COORDS: Record<string, { lat: number; lng: number }> = {
  US: { lat: 37.0902, lng: -95.7129 },
  GB: { lat: 55.3781, lng: -3.4360 },
  DE: { lat: 51.1657, lng: 10.4515 },
  JP: { lat: 36.2048, lng: 138.2529 },
  SG: { lat: 1.3521, lng: 103.8198 },
  AU: { lat: -25.2744, lng: 133.7751 },
  BR: { lat: -14.2350, lng: -51.9253 },
  IN: { lat: 20.5937, lng: 78.9629 },
  NL: { lat: 52.1326, lng: 5.2913 },
  CA: { lat: 56.1304, lng: -106.3468 },
  FR: { lat: 46.2276, lng: 2.2137 },
  CH: { lat: 46.8182, lng: 8.2275 },
  HK: { lat: 22.3193, lng: 114.1694 },
  KR: { lat: 35.9078, lng: 127.7669 },
  SE: { lat: 60.1282, lng: 18.6435 },
};

interface GlobeMapProps {
  /**
   * Filter the globe to show only countries available for this product type.
   * - 'ALL' or undefined → show every country we sell in
   * - 'ISP' | 'RESIDENTIAL' | 'MOBILE' | 'DC' → show that product's country list
   */
  productType?: string;
}

// Generate random arc traffic data
const generateArcs = () => {
  const countryKeys = Object.keys(COUNTRY_COORDS);
  const arcs = [];
  const numArcs = 5 + Math.floor(Math.random() * 4); // 5-8 arcs
  
  for (let i = 0; i < numArcs; i++) {
    const srcIdx = Math.floor(Math.random() * countryKeys.length);
    let dstIdx = Math.floor(Math.random() * countryKeys.length);
    while (dstIdx === srcIdx) {
      dstIdx = Math.floor(Math.random() * countryKeys.length);
    }
    const src = COUNTRY_COORDS[countryKeys[srcIdx]];
    const dst = COUNTRY_COORDS[countryKeys[dstIdx]];
    arcs.push({
      startLat: src.lat,
      startLng: src.lng,
      endLat: dst.lat,
      endLng: dst.lng,
    });
  }
  return arcs;
};

export default function GlobeMap({ productType }: GlobeMapProps = {}) {
  const globeRef   = useRef<GlobeMethods | null>(null);
  const [isDark, setIsDark]               = useState(true);
  const [featuredIdx, setFeaturedIdx]     = useState(0);
  const [dims, setDims]                   = useState({ w: 520, h: 520 });
  const [ready, setReady]                 = useState(false);
  const [containerOpacity, setContainerOpacity] = useState(0);
  const [countriesData, setCountriesData] = useState<object[]>([]);
  const [arcsData, setArcsData]           = useState(generateArcs());
  const [connectionCount, setConnectionCount] = useState(0);
  const [showPing, setShowPing]           = useState(false);
  const [countryCounter, setCountryCounter] = useState(0);
  const [isHovering, setIsHovering]       = useState(false);
  const [autoRotate, setAutoRotate]       = useState(true);
  const prevFeaturedRef = useRef<number>(0);

  // Build the visible location array based on productType.
  // Pulls from the centralized PRODUCT_COUNTRIES map so the list is consistent
  // across the globe, the product cards, and any future page that surfaces coverage.
  const visibleLocations: CountryInfo[] = useMemo(() => {
    if (!productType || productType === 'ALL') {
      return Object.values(COUNTRIES);
    }
    const codes = PRODUCT_COUNTRIES[productType] || [];
    return codes.map(c => COUNTRIES[c]).filter(Boolean);
  }, [productType]);

  const LOCATIONS = visibleLocations;
  const TOTAL_COUNTRIES = 120; // Target for animated counter

  // Return which proxy types are available in a given country code
  const getProductsAtCountry = (code: string): string[] => {
    const available: string[] = [];
    if (PRODUCT_COUNTRIES.ISP?.includes(code))        available.push('ISP');
    if (PRODUCT_COUNTRIES.RESIDENTIAL?.includes(code)) available.push('Residential');
    if (PRODUCT_COUNTRIES.MOBILE?.includes(code))       available.push('Mobile 4G');
    if (PRODUCT_COUNTRIES.DC?.includes(code))           available.push('DC');
    return available;
  };

  // Detect system theme
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mq.matches);
    const handler = (e: MediaQueryQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Pre-fetch world countries TopoJSON and convert to GeoJSON
  useEffect(() => {
    console.info('[GlobeMap] component mounted');
    const sources = [
      '/world-countries-110m.json',
      'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json',
      'https://unpkg.com/world-atlas@2/countries-110m.json',
    ];
    const tryLoad = (idx: number) => {
      console.info('[GlobeMap] trying source:', sources[idx]);
      if (idx >= sources.length) {
        setCountriesData([]);
        return;
      }
      fetch(sources[idx])
        .then(r => {
          console.info('[GlobeMap] fetch response:', sources[idx], r.status);
          return r.json();
        })
        .then(topo => {
          const countries = feature(
            topo as { objects: { countries: object } },
            (topo.objects as { countries: object }).countries
          ) as { features: object[] };
          setCountriesData(countries.features);
          console.info('[GlobeMap] TopoJSON loaded:', countries.features.length, 'features');
        })
        .catch((e: Error) => { console.warn('[GlobeMap] Failed:', sources[idx], e.message); tryLoad(idx + 1); });
    };
    tryLoad(0);
  }, []);

  // Responsive sizing — globe takes full width of its container on all breakpoints
  useEffect(() => {
    const update = () => {
      // Read the container's actual pixel width (globe is inside a w-full parent)
      const container = document.getElementById('globe-container');
      const containerW = container ? container.offsetWidth : window.innerWidth;
      const size = Math.min(containerW, 640);
      setDims({ w: Math.round(size), h: Math.round(size) });
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  // Keep featuredIdx in bounds when LOCATIONS length changes (productType switch)
  useEffect(() => {
    setFeaturedIdx(i => (i % Math.max(LOCATIONS.length, 1)));
  }, [LOCATIONS.length]);

  // Cycle featured country every 4 seconds
  useEffect(() => {
    if (LOCATIONS.length === 0) return;
    const interval = setInterval(() => {
      setFeaturedIdx(i => (i + 1) % LOCATIONS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [LOCATIONS.length]);

  // Regenerate arcs every 20 seconds
  useEffect(() => {
    const arcInterval = setInterval(() => {
      setArcsData(generateArcs());
    }, 20000);
    return () => clearInterval(arcInterval);
  }, []);

  // Animate country counter on first load
  useEffect(() => {
    if (!ready) return;
    const duration = 1500;
    const steps = 30;
    const increment = TOTAL_COUNTRIES / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= TOTAL_COUNTRIES) {
        setCountryCounter(TOTAL_COUNTRIES);
        clearInterval(timer);
      } else {
        setCountryCounter(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [ready]);

  // Connection count animation on country change
  useEffect(() => {
    if (prevFeaturedRef.current !== featuredIdx && ready) {
      // Trigger ping animation
      setShowPing(true);
      setTimeout(() => setShowPing(false), 600);
      
      // Animate connection count
      const target = 50 + Math.floor(Math.random() * 450); // 50-500 connections
      const duration = 800;
      const steps = 20;
      const increment = target / steps;
      let current = 0;
      const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
          setConnectionCount(target);
          clearInterval(timer);
        } else {
          setConnectionCount(Math.floor(current));
        }
      }, duration / steps);
      prevFeaturedRef.current = featuredIdx;
      return () => clearInterval(timer);
    }
  }, [featuredIdx, ready]);

  // Pan camera when featured country changes
  useEffect(() => {
    if (!globeRef.current || !ready || LOCATIONS.length === 0) return;
    const loc = LOCATIONS[featuredIdx];
    if (!loc) return;
    try {
      globeRef.current.pointOfView({ lat: loc.lat, lng: loc.lng, altitude: 2.2 }, 1800);
    } catch (_) {}
  }, [featuredIdx, ready, LOCATIONS]);

  // Handle globe hover/click to stop auto-rotate
  const handleGlobeMouseEnter = () => setIsHovering(true);
  const handleGlobeMouseLeave = () => setIsHovering(false);

  useEffect(() => {
    setAutoRotate(!isHovering);
  }, [isHovering]);

  // ============================================================
  // MINIMAL GLOBE — just sphere + soft outer glow
  // ============================================================
  const sphereBaseColor = isDark ? '#0a0a12' : '#fafafa';

  // Single atmosphere color — same brand green in both modes
  const atmosphereColor = BRAND_GREEN_LIGHT;
  const atmosphereAlt   = 0.15;

  // Continent outlines — subtle brand-aligned in both modes.
  // Dark mode: dim sage green. Light mode: slate gray. Both 25-30% opacity max.
  const outlineColor    = isDark ? 'rgba(132, 204, 22, 0.25)' : 'rgba(100, 116, 139, 0.30)';
  // Sphere: PhongMaterial with warm brand emissive — satin sheen, not flat-matte.
  const globeMaterial = useMemo(() => {
      return new THREE.MeshPhongMaterial({
        color: new THREE.Color(sphereBaseColor),
        specular: new THREE.Color(isDark ? '#1a3a28' : '#cccccc'),
        shininess: isDark ? 15 : 20,
        emissive: new THREE.Color(isDark ? '#0a2018' : '#e8f5e9'),
        emissiveIntensity: isDark ? 0.12 : 0.05,
      });
    }, [sphereBaseColor, isDark]);
  const featured = LOCATIONS[featuredIdx];

  // Determine if featured country changed for ping animation
  const pingClass = showPing ? 'animate-ping' : '';

  return (
    <div 
      id="globe-container" 
      className="relative w-full"
      style={{ height: 480, minHeight: 480 }}
      aria-label="Interactive globe showing proxy coverage in 120+ countries"
    >
      {/* Globe canvas — centered within container */}
      <div
        className="absolute left-1/2 top-0 flex items-center"
        style={{ width: dims.w, height: dims.h, transform: 'translateX(-50%)', opacity: containerOpacity, transition: 'opacity 700ms ease' }}
        onMouseEnter={handleGlobeMouseEnter}
        onMouseLeave={handleGlobeMouseLeave}
        onClick={handleGlobeMouseEnter}
      >
        <Globe
          ref={globeRef}
          width={dims.w}
          height={dims.h}
          globeMaterial={globeMaterial}
          showAtmosphere={true}
          atmosphereColor={atmosphereColor}
          atmosphereAltitude={atmosphereAlt}
          backgroundColor="rgba(0,0,0,0)"
          polygonsData={countriesData}
          polygonGeoJsonGeometry={(d: object) => (d as { geometry: object }).geometry}
          polygonCapColor={() => 'rgba(0,0,0,0)'}
          polygonSideColor={() => 'rgba(0,0,0,0)'}
          polygonStrokeColor={() => outlineColor}
          polygonStrokeWidth={2.0}
          polygonCapCurvatureResolution={5}
          polygonAltitude={0.005}
          // Country markers — filtered by productType
          pointsData={LOCATIONS}
          pointLat="lat"
          pointLng="lng"
          pointColor={() => BRAND_GREEN}
          pointRadius={0.55}
          pointAltitude={0.007}
          // Featured country pulse ring
          ringsData={ready && featured ? [{ lat: featured.lat, lng: featured.lng }] : []}
          ringColor={() => BRAND_GREEN}
          ringMaxRadius={4.5}
          ringPropagationSpeed={1.4}
          ringRepeat={2.2}
          // Animated arc traffic
          arcsData={arcsData}
          arcStartLat="startLat"
          arcStartLng="startLng"
          arcEndLat="endLat"
          arcEndLng="endLng"
          arcColor={() => BRAND_GREEN}
          arcAltitude={0.3}
          arcStroke={0.5}
          arcDashLength={0.3}
          arcDashGap={0.15}
          arcDashAnimateTime={3000}
          arcDashInitialGap={1}
          // Auto-rotate with user interaction override
          autoRotate={autoRotate}
          autoRotateSpeed={0.3}
          onGlobeReady={() => {
            setContainerOpacity(1);
            setTimeout(() => setReady(true), 300);
            if (globeRef.current && LOCATIONS[0]) {
              try {
                globeRef.current.pointOfView({ lat: LOCATIONS[0].lat, lng: LOCATIONS[0].lng, altitude: 2.2 }, 0);
              } catch (_) {}
            }
          }}
        />
      </div>

      {/* Featured country callout — shows country name + all products available there */}
      <div
        key={`${featuredIdx}-${productType}`}
        className={`absolute pointer-events-none z-20 transition-all duration-300 ease-out ${ready ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1.5'} ${showPing ? 'animate-pulse' : ''}`}
        style={{ right: '4%', top: '8%', minWidth: 165 }}
      >
        {/* Ping ring indicator when country changes */}
        {showPing && (
          <div 
            className="absolute -inset-2 rounded-2xl animate-ping opacity-30" 
            style={{ backgroundColor: BRAND_GREEN }}
          />
        )}
        <div className={`relative rounded-2xl shadow-2xl p-4 flex items-center gap-3 border backdrop-blur-md ${isDark ? 'bg-[rgba(10,10,20,0.88)]' : 'bg-white shadow-lg'} ${isDark ? 'border-[rgba(10,210,90,0.3)]' : 'border-[rgba(10,210,90,0.4)]'}`}>
          <span className="text-3xl">{featured?.flag}</span>
          <div>
            <p className={`font-bold text-sm ${isDark ? 'text-zinc-100' : 'text-zinc-800'}`}>{featured?.name}</p>
            <p className={`text-xs mt-0.5 flex items-center gap-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
              <svg className="w-3 h-3" style={{ color: BRAND_GREEN }} fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
              </svg>
              {featured?.region}
            </p>
            {/* Connection count */}
            <p className="text-[10px] mt-1" style={{ color: BRAND_GREEN }}>
              {connectionCount.toLocaleString()} connections
            </p>
            {/* Show only the proxy types actually available in this country */}
            <div className="flex flex-wrap gap-1 mt-1.5">
              {(featured ? getProductsAtCountry(featured.code) : []).map(pt => (
                <span
                  key={pt}
                  className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                  style={{ background: 'rgba(10,210,90,0.15)', color: BRAND_GREEN }}
                >
                  {pt}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Coverage badge — shows animated country counter */}
      <div
        className={`absolute bottom-4 left-4 rounded-xl px-3 py-2 shadow-lg border z-20 transition-opacity duration-400`}
        style={{
          background: isDark ? 'rgba(10,10,20,0.88)' : 'white',
          borderColor: isDark ? 'rgba(10,210,90,0.3)' : 'rgba(10,210,90,0.4)',
          opacity: ready ? 1 : 0,
        }}
      >
        <p className="text-xs font-medium" style={{ color: BRAND_GREEN }}>Live Coverage</p>
        <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
          {productType && productType !== 'ALL'
            ? `${PRODUCT_SHORT_NAMES[productType] ?? productType} plans available`
            : (
              <>
                <span className="font-bold" style={{ color: BRAND_GREEN }}>{countryCounter}+</span> countries — All plans
              </>
            )
          }
        </p>
      </div>

      {/* Screen reader only - current country announcement */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {ready && featured ? `Showing proxy coverage in ${featured.name}, ${featured.region}. ${connectionCount.toLocaleString()} active connections.` : ''}
      </div>
    </div>
  );
}
