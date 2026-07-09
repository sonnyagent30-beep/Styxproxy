'use client';

import { useRef, useEffect, useState } from 'react';

// Country locations with lat/lng
const LOCATIONS = [
  // ISP Countries
  { lat: 51.5074, lng: -0.1278, name: 'UK', country: 'United Kingdom', region: 'Europe', flag: '🇬🇧', type: 'ISP' },
  { lat: 40.7128, lng: -74.006, name: 'US', country: 'United States', region: 'North America', flag: '🇺🇸', type: 'ISP' },
  { lat: 52.52, lng: 13.405, name: 'DE', country: 'Germany', region: 'Europe', flag: '🇩🇪', type: 'ISP' },
  { lat: 48.8566, lng: 2.3522, name: 'FR', country: 'France', region: 'Europe', flag: '🇫🇷', type: 'ISP' },
  { lat: 45.5017, lng: -73.5673, name: 'CA', country: 'Canada', region: 'North America', flag: '🇨🇦', type: 'ISP' },
  { lat: 35.6762, lng: 139.6503, name: 'JP', country: 'Japan', region: 'Asia Pacific', flag: '🇯🇵', type: 'ISP' },
  { lat: -33.8688, lng: 151.2093, name: 'AU', country: 'Australia', region: 'Oceania', flag: '🇦🇺', type: 'ISP' },
  { lat: -23.5505, lng: -46.6333, name: 'BR', country: 'Brazil', region: 'South America', flag: '🇧🇷', type: 'ISP' },
  { lat: 1.3521, lng: 103.8198, name: 'SG', country: 'Singapore', region: 'Asia Pacific', flag: '🇸🇬', type: 'ISP' },
  // Residential
  { lat: 35.0, lng: -40.0, name: 'RES', country: 'Residential', region: 'Global', flag: '🌍', type: 'RESIDENTIAL' },
  // Mobile 4G
  { lat: 25.0, lng: 45.0, name: 'MOB', country: 'Mobile 4G', region: 'Global', flag: '📱', type: 'MOBILE' },
  // Datacenter
  { lat: 30.0, lng: -10.0, name: 'DC', country: 'Datacenter', region: 'Global', flag: '🏢', type: 'DC' },
];

// Featured location for the floating callout card (rotates through ISP countries)
const FEATURED = LOCATIONS[0];

// Helper to project lat/lng to 2D screen coords (simple equirectangular projection)
function latLngToVec2(lat: number, lng: number, size: number, center: number) {
  const x = center + (lng / 180) * (size / 2);
  const y = center - (lat / 90) * (size / 2);
  return [x, y];
}

export default function GlobeMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [featuredLocation, setFeaturedLocation] = useState(FEATURED);
  const cobeRef = useRef<unknown>(null);

  // Rotate through featured locations
  useEffect(() => {
    const interval = setInterval(() => {
      const idx = Math.floor(Date.now() / 4000) % 9; // cycle through first 9 (ISP countries)
      setFeaturedLocation(LOCATIONS[idx]);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Initialize cobe globe
  useEffect(() => {
    let mounted = true;
    
    async function initGlobe() {
      try {
        const cobe = await import('cobe');
        
        if (!mounted || !canvasRef.current) return;
        
        const canvas = canvasRef.current;
        
        // Create cobe globe with correct API
        cobeRef.current = cobe.default(canvas, {
          width: 1000,
          height: 1000,
          phi: 0,
          theta: 0,
          dark: 1,
          diffuse: 0.15,
          mapSamples: 10000,
          mapBrightness: 1,
          baseColor: [0.1, 0.1, 0.15],    // dark purple-ish base
          markerColor: [0.4, 0.4, 1],      // purple markers
          glowColor: [0.3, 0.3, 0.8],       // glow color
          devicePixelRatio: typeof window !== 'undefined' ? window.devicePixelRatio : 1,
        });
      } catch (e) {
        console.error('Failed to load cobe:', e);
      }
    }
    
    initGlobe();
    
    return () => {
      mounted = false;
    };
  }, []);

  // Get marker color based on type
  const getMarkerColor = (type: string) => {
    const colors: Record<string, string> = {
      ISP: '#6366f1',
      RESIDENTIAL: '#a855f7',
      MOBILE: '#3b82f6',
      DC: '#f97316',
    };
    return colors[type] || '#6366f1';
  };

  return (
    <div className="relative w-full flex flex-col items-center">
      {/* Globe container */}
      <div className="relative w-full" style={{ height: '380px' }}>
        {/* Cobe Globe Canvas */}
        <div className="absolute inset-0 flex items-center justify-center">
          <canvas
            ref={canvasRef}
            width={1000}
            height={1000}
            className="w-full h-full max-w-[380px] max-h-[380px]"
            style={{ opacity: 0.9 }}
          />
        </div>

        {/* SVG Overlay for arcs and dots */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox="0 0 600 600"
          style={{ overflow: 'visible' }}
        >
          <defs>
            {/* Purple glow filter */}
            <filter id="purple-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="dot-glow" x="-100%" y="-100%" width="300%" height="300%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            {/* Gradient for arcs */}
            <linearGradient id="arc-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.1" />
              <stop offset="50%" stopColor="#6366f1" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#a855f7" stopOpacity="1" />
            </linearGradient>
          </defs>

          {/* Arcs from center to each location */}
          {LOCATIONS.filter(l => l.type === 'ISP').map((loc, i) => {
            const [x, y] = latLngToVec2(loc.lat, loc.lng, 260, 300);
            const cx = 300, cy = 300;
            // Control point for the arc curve
            const mx = (cx + x) / 2;
            const my = Math.min(cy, y) - 30;
            return (
              <g key={loc.name}>
                {/* Arc path */}
                <path
                  d={`M ${cx} ${cy} Q ${mx} ${my} ${x} ${y}`}
                  fill="none"
                  stroke="url(#arc-gradient)"
                  strokeWidth="1.5"
                  opacity="0.4"
                />
                {/* Glowing dot at end */}
                <circle
                  cx={x}
                  cy={y}
                  r="4"
                  fill={getMarkerColor(loc.type)}
                  filter="url(#dot-glow)"
                  opacity="0.7"
                >
                  <animate attributeName="r" values="3;6;3" dur={`${2 + i * 0.2}s`} repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.5;1;0.5" dur={`${2 + i * 0.2}s`} repeatCount="indefinite" />
                </circle>
                {/* Solid dot on top */}
                <circle cx={x} cy={y} r="2.5" fill="#a855f7" />
              </g>
            );
          })}
        </svg>

        {/* Featured location callout card */}
        <div
          className="absolute bg-white rounded-2xl shadow-xl p-3 flex items-center gap-2 transition-all duration-700"
          style={{
            right: '10%',
            top: '20%',
            minWidth: '140px',
            animation: 'float 3s ease-in-out infinite',
          }}
        >
          <span className="text-2xl">{featuredLocation.flag}</span>
          <div>
            <p className="font-bold text-sm text-gray-900">{featuredLocation.country}</p>
            <p className="text-xs text-gray-500 flex items-center gap-1">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
              </svg>
              {featuredLocation.region}
            </p>
          </div>
        </div>

        {/* Country count badge */}
        <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur rounded-xl px-3 py-2 shadow-lg">
          <p className="text-xs text-gray-500">9 Countries</p>
          <p className="text-sm font-bold text-gray-900">ISP Coverage</p>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-4 mt-4 text-sm">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 inline-block" />
          <span className="text-gray-400">ISP Proxies</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-purple-500 inline-block" />
          <span className="text-gray-400">Residential</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" />
          <span className="text-gray-400">Mobile 4G</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block" />
          <span className="text-gray-400">Datacenter</span>
        </span>
      </div>

      {/* Add float animation to CSS */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
      `}</style>
    </div>
  );
}
