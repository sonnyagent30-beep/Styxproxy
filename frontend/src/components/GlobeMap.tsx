// @ts-nocheck — react-globe.gl types are incomplete; runtime works correctly
'use client';

import { useEffect, useState, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import type { GlobeMethods } from 'react-globe.gl';
import { feature } from 'topojson-client';
import * as THREE from 'three';
import { COUNTRIES, PRODUCT_COUNTRIES, type CountryInfo } from '@/lib/products';

const Globe = dynamic(() => import('react-globe.gl'), { ssr: false });

const BRAND_GREEN       = '#0AD25A';
const BRAND_GREEN_LIGHT = '#2AED6C';

interface GlobeMapProps {
  productType?: string;
}

export default function GlobeMap({ productType }: GlobeMapProps = {}) {
  const globeRef = useRef<GlobeMethods | null>(null);
  const [isDark, setIsDark] = useState(true);
  const [dims, setDims] = useState({ w: 520, h: 520 });
  const [ready, setReady] = useState(false);
  const [containerOpacity, setContainerOpacity] = useState(0);
  const [countriesData, setCountriesData] = useState<object[]>([]);

  const visibleLocations: CountryInfo[] = useMemo(() => {
    if (!productType || productType === 'ALL') {
      return Object.values(COUNTRIES);
    }
    const codes = PRODUCT_COUNTRIES[productType] || [];
    return codes.map(c => COUNTRIES[c]).filter(Boolean);
  }, [productType]);

  const LOCATIONS = visibleLocations;

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  useEffect(() => {
    const sources = [
      '/world-countries-110m.json',
      'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json',
      'https://unpkg.com/world-atlas@2/countries-110m.json',
    ];
    const tryLoad = (idx: number) => {
      if (idx >= sources.length) { setCountriesData([]); return; }
      fetch(sources[idx])
        .then(r => r.json())
        .then(topo => {
          const countries = feature(
            topo as { objects: { countries: object } },
            (topo.objects as { countries: object }).countries
          ) as { features: object[] };
          setCountriesData(countries.features);
        })
        .catch((e: Error) => tryLoad(idx + 1));
    };
    tryLoad(0);
  }, []);

  useEffect(() => {
    const update = () => {
      const container = document.getElementById('globe-container');
      const containerW = container ? container.offsetWidth : window.innerWidth;
      const size = Math.min(containerW, 640);
      setDims({ w: Math.round(size), h: Math.round(size) });
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  const sphereBaseColor = isDark ? '#0a0a12' : '#fafafa';
  const atmosphereColor = BRAND_GREEN_LIGHT;
  const atmosphereAlt   = 0.15;
  const outlineColor   = isDark ? 'rgba(132, 204, 22, 0.25)' : 'rgba(100, 116, 139, 0.30)';

  const globeMaterial = useMemo(() => {
    return new THREE.MeshPhongMaterial({
      color: new THREE.Color(sphereBaseColor),
      specular: new THREE.Color(isDark ? '#1a3a28' : '#cccccc'),
      shininess: isDark ? 15 : 20,
      emissive: new THREE.Color(isDark ? '#0a2018' : '#e8f5e9'),
      emissiveIntensity: isDark ? 0.12 : 0.05,
    });
  }, [sphereBaseColor, isDark]);

  return (
    <div
      id="globe-container"
      className="relative w-full"
      style={{ height: 480, minHeight: 480 }}
      aria-label="Interactive globe showing proxy coverage in 120+ countries"
    >
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
          pointsData={LOCATIONS}
          pointLat="lat"
          pointLng="lng"
          pointColor={() => BRAND_GREEN}
          pointRadius={0.55}
          pointAltitude={0.007}
          ringsData={LOCATIONS.slice(0, 1)}
          ringColor={() => BRAND_GREEN}
          ringMaxRadius={3.5}
          ringPropagationSpeed={1.0}
          ringRepeat={1.5}
          autoRotate={true}
          autoRotateSpeed={0.3}
          onGlobeReady={() => {
            setContainerOpacity(1);
            setTimeout(() => setReady(true), 300);
          }}
        />
      </div>

      <div
        className="absolute bottom-4 left-4 rounded-xl px-3 py-2 shadow-lg border z-20"
        style={{
          background: isDark ? 'rgba(10,10,20,0.88)' : 'white',
          borderColor: isDark ? 'rgba(10,210,90,0.3)' : 'rgba(10,210,90,0.4)',
          opacity: ready ? 1 : 0,
          transition: 'opacity 400ms',
        }}
      >
        <p className="text-xs font-medium" style={{ color: BRAND_GREEN }}>Live Coverage</p>
        <p className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
          120+ countries — All plans
        </p>
      </div>

      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {ready ? 'Globe showing proxy coverage in 120+ countries' : ''}
      </div>
    </div>
  );
}
