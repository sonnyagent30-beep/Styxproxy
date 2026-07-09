'use client';

import { Canvas, useFrame } from '@react-three/fiber';
import { useRef, useEffect, useState, useMemo } from 'react';
import * as THREE from 'three';

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
const PURPLE = '#6366F1';

// Convert lat/lng to 3D sphere coordinates
function latLngToVector3(lat: number, lng: number, radius: number = 1): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

// Globe sphere with dots texture effect
function GlobeSphere({ isDark }: { isDark: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null);
  
  // Create a dotted sphere material using custom shader or points
  const geometry = useMemo(() => new THREE.SphereGeometry(1, 64, 64), []);
  
  // Create dot pattern texture
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 256;
    const ctx = canvas.getContext('2d')!;
    
    // Background
    ctx.fillStyle = isDark ? '#0a0a14' : '#d4d4d8';
    ctx.fillRect(0, 0, 512, 256);
    
    // Draw dots in a grid pattern
    ctx.fillStyle = isDark ? '#1a1a2e' : '#a1a1aa';
    for (let i = 0; i < 2000; i++) {
      const x = Math.random() * 512;
      const y = Math.random() * 256;
      const size = Math.random() * 1.5 + 0.5;
      ctx.beginPath();
      ctx.arc(x, y, size, 0, Math.PI * 2);
      ctx.fill();
    }
    
    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    return tex;
  }, [isDark]);
  
  return (
    <mesh ref={meshRef} geometry={geometry}>
      <meshStandardMaterial
        map={texture}
        color={isDark ? '#0a0a14' : '#d4d4d8'}
        emissive={new THREE.Color(PURPLE)}
        emissiveIntensity={0.05}
        roughness={0.8}
        metalness={0.1}
      />
    </mesh>
  );
}

// Atmosphere glow effect
function Atmosphere({ isDark }: { isDark: boolean }) {
  return (
    <mesh scale={1.15}>
      <sphereGeometry args={[1, 32, 32]} />
      <meshBasicMaterial
        color={PURPLE}
        transparent
        opacity={isDark ? 0.15 : 0.08}
        side={THREE.BackSide}
      />
    </mesh>
  );
}

// Marker dot at a location
function Marker({ location, isDark }: { location: typeof LOCATIONS[0]; isDark: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const pos = useMemo(() => latLngToVector3(location.lat, location.lng, 1.01), [location.lat, location.lng]);
  
  const color = useMemo(() => {
    if (location.type === 'ISP') return PURPLE;
    if (location.type === 'RESIDENTIAL') return '#a855f7';
    if (location.type === 'MOBILE') return '#3b82f6';
    return '#f97316';
  }, [location.type]);
  
  useFrame(({ clock }) => {
    if (meshRef.current) {
      const scale = 1 + Math.sin(clock.getElapsedTime() * 2 + location.lat) * 0.1;
      meshRef.current.scale.setScalar(scale);
    }
  });
  
  return (
    <mesh ref={meshRef} position={pos}>
      <sphereGeometry args={[0.02, 16, 16]} />
      <meshBasicMaterial color={color} />
    </mesh>
  );
}

// Glowing arc from origin to destination
function Arc({ from, to, isDark }: { from: typeof LOCATIONS[0]; to: typeof LOCATIONS[0]; isDark: boolean }) {
  const points = useMemo(() => {
    const start = latLngToVector3(from.lat, from.lng, 1);
    const end = latLngToVector3(to.lat, to.lng, 1);
    
    // Create curved path using quadratic bezier
    const mid = start.clone().add(end).multiplyScalar(0.5).normalize().multiplyScalar(1.15);
    
    const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
    return curve.getPoints(50);
  }, [from, to]);
  
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    return geo;
  }, [points]);
  
  const material = useMemo(() => 
    new THREE.LineBasicMaterial({ color: PURPLE, transparent: true, opacity: 0.5 }), 
  []);
  
  return (
    <primitive object={new THREE.Line(geometry, material)} />
  );
}

// Main globe component
function Globe({ isDark }: { isDark: boolean }) {
  const groupRef = useRef<THREE.Group>(null);
  
  // Auto-rotate
  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.002;
    }
  });
  
  return (
    <group ref={groupRef}>
      <GlobeSphere isDark={isDark} />
      <Atmosphere isDark={isDark} />
      
      {/* Markers */}
      {LOCATIONS.map((loc, idx) => (
        <Marker key={idx} location={loc} isDark={isDark} />
      ))}
      
      {/* Arcs from UK to other ISP locations */}
      {ISP_LOCATIONS.slice(1).map((loc, idx) => (
        <Arc key={idx} from={ISP_LOCATIONS[0]} to={loc} isDark={isDark} />
      ))}
    </group>
  );
}

export default function GlobeMap() {
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

  return (
    <div className="relative w-full flex flex-col items-center">
      <div className="relative w-full" style={{ height: '380px' }}>
        {/* Globe canvas */}
        <div className="absolute inset-0 flex items-center justify-center">
          <Canvas
            camera={{ position: [0, 0, 2.5], fov: 45 }}
            style={{ width: '100%', height: '100%' }}
          >
            <ambientLight intensity={0.5} />
            <pointLight position={[5, 5, 5]} intensity={0.5} />
            <pointLight position={[-5, -5, -5]} intensity={0.3} />
            <Globe isDark={isDark} />
          </Canvas>
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
