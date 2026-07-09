// @ts-nocheck
'use client';

import { useState, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';

// ISP Countries (9 locations with lat/long)
const ispLocations = [
  { lat: 51.5074, lng: -0.1278, name: 'UK', type: 'ISP' },       // London
  { lat: 40.7128, lng: -74.006, name: 'US', type: 'ISP' },        // New York
  { lat: 52.52, lng: 13.405, name: 'DE', type: 'ISP' },          // Berlin
  { lat: 48.8566, lng: 2.3522, name: 'FR', type: 'ISP' },         // Paris
  { lat: 45.5017, lng: -73.5673, name: 'CA', type: 'ISP' },       // Montreal
  { lat: 35.6762, lng: 139.6503, name: 'JP', type: 'ISP' },       // Tokyo
  { lat: -33.8688, lng: 151.2093, name: 'AU', type: 'ISP' },      // Sydney
  { lat: -23.5505, lng: -46.6333, name: 'BR', type: 'ISP' },      // São Paulo
  { lat: 1.3521, lng: 103.8198, name: 'SG', type: 'ISP' },       // Singapore
];

// Residential and Mobile (Global — 1 representative dot each)
const globalLocations = [
  { lat: 35.0, lng: -40.0, name: 'Residential', type: 'RESIDENTIAL' },
  { lat: 25.0, lng: 45.0, name: 'Mobile 4G', type: 'MOBILE' },
];

// Datacenter (1 dot)
const dcLocations = [
  { lat: 30.0, lng: -10.0, name: 'Datacenter', type: 'DC' },
];

// Dot colors (match Bunche theme)
const getDotColor = (type: string) => {
  const colors: Record<string, string> = {
    ISP: '#10B981',          // Bunche green
    RESIDENTIAL: '#a855f7',  // Purple
    MOBILE: '#3b82f6',       // Blue
    DC: '#f97316',           // Orange
  };
  return colors[type] || '#10B981';
};

export default function GlobeMap() {
  const [dimensions, setDimensions] = useState({ width: 800, height: 420 });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const globeRef = useRef<any>(null);

  // Combine all locations and add color property
  const allLocations = [...ispLocations, ...globalLocations, ...dcLocations].map(loc => ({
    ...loc,
    color: getDotColor(loc.type)
  }));

  // Set up auto-rotation after globe mounts
  useEffect(() => {
    if (globeRef.current) {
      const controls = globeRef.current.controls();
      if (controls) {
        controls.autoRotate = true;
        controls.autoRotateSpeed = 0.5;
      }
      // Set initial view angle
      globeRef.current.pointOfView({ lat: 20, lng: 0, altitude: 2.5 });
    }
  }, []);

  // Update dimensions on window resize
  useEffect(() => {
    const updateDimensions = () => {
      if (typeof window !== 'undefined') {
        const width = Math.min(window.innerWidth - 32, 800);
        setDimensions({ width, height: 420 });
      }
    };
    
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Dynamically import the globe component
  const ReactGlobe = dynamic(() => import('react-globe.gl'), {
    ssr: false,
    loading: () => (
      <div className="w-full h-[420px] flex items-center justify-center">
        <span className="text-[var(--muted)]">Loading globe...</span>
      </div>
    ),
  });

  return (
    <div className="relative w-full">
      {/* Header */}
      <div className="text-center mb-4">
        <h2 className="text-2xl font-bold">🌍 Bunche Global Coverage</h2>
        <p className="text-[var(--muted)] text-sm">9 ISP Countries · Residential · Mobile 4G · Datacenter</p>
      </div>
      
      {/* Globe */}
      <div className="w-full rounded-2xl overflow-hidden" style={{ height: '420px' }}>
        <ReactGlobe
          ref={globeRef}
          width={dimensions.width}
          height={dimensions.height}
          globeImageUrl="//unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
          pointsData={allLocations}
          pointLat="lat"
          pointLng="lng"
          pointColor="color"
          pointAltitude={0.01}
          pointRadius={0.8}
          atmosphereColor="#10B981"
          atmosphereAltitude={0.15}
          enablePointerInteraction={false}
          enableZoom={false}
          animateIn={true}
        />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-4 mt-4 text-sm">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-[#10B981] inline-block" /> 
          ISP Proxies
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-[#a855f7] inline-block" /> 
          Residential
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-[#3b82f6] inline-block" /> 
          Mobile 4G
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-[#f97316] inline-block" /> 
          Datacenter
        </span>
      </div>
    </div>
  );
}
