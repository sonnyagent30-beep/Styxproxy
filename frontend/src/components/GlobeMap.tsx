/* eslint-disable @typescript-eslint/ban-ts-comment */

// @ts-nocheck — react-globe.gl types are incomplete; runtime works correctly

/* eslint-disable @typescript-eslint/ban-ts-comment, react-hooks/set-state-in-effect */
'use client';

import { useEffect, useState, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import type { GlobeMethods } from 'react-globe.gl';
import { feature } from 'topojson-client';
import * as THREE from 'three';
import { COUNTRIES, PRODUCT_COUNTRIES, type CountryInfo } from '@/lib/products';
import { Flag } from '@/components/ui/Flag';

// Load react-globe.gl only on client (SSR disabled)
const Globe = dynamic(() => import('react-globe.gl'), { ssr: false });

// Brand colors — Styxproxy #0AD25A / #2AED6C
const BRAND_GREEN        = '#0AD25A';
const BRAND_GREEN_LIGHT  = '#2AED6C';

// Short display names for product types
const PRODUCT_SHORT_NAMES: Record<string, string> = {
  ISP:         'ISP',
  RESIDENTIAL: 'Residential',
  MOBILE:      'Mobile 4G',
  DC:          'Datacenter',
};

interface GlobeMapProps {
  /**
   * Filter the globe to show only countries available for this product type.
   * - 'ALL' or undefined → show every country we sell in
   * - 'ISP' | 'RESIDENTIAL' | 'MOBILE' | 'DC' → show that product's country list
   */
  productType?: string;
}

export default function GlobeMap({ productType }: GlobeMapProps = {}) {
  const globeRef   = useRef<GlobeMethods | null>(null);
  const [isDark, setIsDark]               = useState(true);
  const [featuredIdx, setFeaturedIdx]     = useState(0);
  const [dims, setDims]                   = useState({ w: 520, h: 520 });
  const [ready, setReady]                 = useState(false);
  const [containerOpacity, setContainerOpacity] = useState(0);
  const [countriesData, setCountriesData] = useState<object[]>([]);

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

  // Pan camera when featured country changes
  useEffect(() => {
    if (!globeRef.current || !ready || LOCATIONS.length === 0) return;
    const loc = LOCATIONS[featuredIdx];
    if (!loc) return;
    try {
      globeRef.current.pointOfView({ lat: loc.lat, lng: loc.lng, altitude: 2.2 }, 1800);
    } catch (_) {}
  }, [featuredIdx, ready, LOCATIONS]);

  // ============================================================
  // MINIMAL GLOBE — just sphere + soft outer glow
  // ============================================================
  const sphereBaseColor = isDark ? '#0a0a12' : '#fafafa';

  // Single atmosphere color — same brand green in both modes
  const atmosphereColor = BRAND_GREEN_LIGHT;
  const atmosphereAlt   = 0.15;

  // Continent outlines — subtle brand-aligned in both modes.
  // Dark mode: dim sage green. Light mode: slate gray. Both 25-30% opacity max.
  const outlineColor    = isDark ? 'rgba(10,210,90,0.25)' : 'rgba(100, 116, 139, 0.30)';
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

  return (
    <div id="globe-container" className="relative w-full" style={{ height: 480, minHeight: 480 }}>
      {/* Globe canvas — centered within container */}
      <div
        className="absolute left-1/2 top-0 flex items-center"
        style={{ width: dims.w, height: dims.h, transform: 'translateX(-50%)', opacity: containerOpacity, transition: 'opacity 700ms ease' }}
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
          arcsData={[]}
          autoRotate={true}
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

      {/* Featured country callout */}
      <div
        className="absolute pointer-events-none z-20"
        style={{ right: '4%', top: '8%', minWidth: 165, opacity: ready ? 1 : 0, transition: 'opacity 400ms' }}
      >
        <div className={`rounded-2xl shadow-2xl p-4 flex items-center gap-3 border backdrop-blur-md ${isDark ? 'bg-[rgba(10,10,20,0.88)]' : 'bg-white shadow-lg'} ${isDark ? 'border-[rgba(10,210,90,0.3)]' : 'border-[rgba(10,210,90,0.4)]'}`}>
          {featured && <Flag countryCode={featured.code} size={36} />}
          <div>
            <p className={`font-bold text-sm ${isDark ? 'text-zinc-100' : 'text-zinc-800'}`}>{featured?.name}</p>
            <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>{featured?.region}</p>
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

      {/* Coverage badge */}
      <div
        className={`absolute bottom-4 left-4 rounded-xl px-3 py-2 shadow-lg border z-20`}
        style={{
          background: isDark ? 'rgba(10,10,20,0.88)' : 'white',
          borderColor: isDark ? 'rgba(10,210,90,0.3)' : 'rgba(10,210,90,0.4)',
          opacity: ready ? 1 : 0,
          transition: 'opacity 400ms',
        }}
      >
        <p className="text-xs font-medium" style={{ color: BRAND_GREEN }}>Live Coverage</p>
        <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
          {productType && productType !== 'ALL'
            ? `${PRODUCT_SHORT_NAMES[productType] ?? productType} plans available`
            : 'All plans — ISP, Residential, Mobile & DC'}
        </p>
      </div>
    </div>
  );
}