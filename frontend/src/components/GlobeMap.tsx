'use client';

import { Canvas, useFrame } from '@react-three/fiber';
import { useRef, useEffect, useState, useMemo } from 'react';
import * as THREE from 'three';

// Earth textures (dark and light variants)
const EARTH_TEXTURES = {
  dark: {
    map: 'https://unpkg.com/three-globe@2.31.0/example/img/earth-dark.jpg',
    bump: 'https://unpkg.com/three-globe@2.31.0/example/img/earth-topology.png',
  },
  light: {
    map: 'https://unpkg.com/three-globe@2.31.0/example/img/earth-blue-marble.jpg',
    bump: 'https://unpkg.com/three-globe@2.31.0/example/img/earth-topology.png',
  },
};

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

const TYPE_COLORS: Record<string, string> = {
  ISP: '#10B981',         // Bunche green
  RESIDENTIAL: '#a855f7', // purple
  MOBILE: '#3b82f6',      // blue
  DC: '#f97316',          // orange
};

function latLngToVector3(lat: number, lng: number, radius = 1): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

// Colored arc between two points
function Arc({
  from,
  to,
  color,
}: {
  from: { lat: number; lng: number };
  to: { lat: number; lng: number };
  color: string;
}) {
  const points = useMemo(() => {
    const start = latLngToVector3(from.lat, from.lng, 1);
    const end = latLngToVector3(to.lat, to.lng, 1);
    const mid = start.clone().add(end).multiplyScalar(0.5).normalize().multiplyScalar(1.18);
    const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
    return curve.getPoints(50);
  }, [from.lat, from.lng, to.lat, to.lng]);

  const geometry = useMemo(() => {
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [points]);

  const material = useMemo(() => {
    return new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity: 0.7,
    });
  }, [color]);

  return <primitive object={new THREE.Line(geometry, material)} />;
}

// Pulsing marker dot
function Marker({ location }: { location: typeof LOCATIONS[0] }) {
  const ringRef = useRef<THREE.Mesh>(null);
  const dotRef = useRef<THREE.Mesh>(null);
  const pos = useMemo(() => latLngToVector3(location.lat, location.lng, 1.02), [location.lat, location.lng]);
  const color = TYPE_COLORS[location.type] || '#10B981';

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const pulse = (Math.sin(t * 2 + location.lat) + 1) / 2;
    if (ringRef.current) {
      ringRef.current.scale.setScalar(1 + pulse * 0.8);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity = 0.4 * (1 - pulse);
    }
    if (dotRef.current) {
      dotRef.current.scale.setScalar(0.8 + pulse * 0.3);
    }
  });

  return (
    <group position={pos}>
      {/* Outer pulsing ring */}
      <mesh ref={ringRef}>
        <ringGeometry args={[0.025, 0.038, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.4} side={THREE.DoubleSide} />
      </mesh>
      {/* Solid center dot */}
      <mesh ref={dotRef}>
        <sphereGeometry args={[0.02, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
}

// Atmosphere glow
function Atmosphere({ isDark }: { isDark: boolean }) {
  const color = isDark ? '#10B981' : '#6366F1';
  const opacity = isDark ? 0.12 : 0.06;
  return (
    <mesh scale={1.18}>
      <sphereGeometry args={[1, 64, 64]} />
      <meshBasicMaterial color={color} transparent opacity={opacity} side={THREE.BackSide} />
    </mesh>
  );
}

// Main globe mesh
function GlobeSphere({ isDark, mapUrl, bumpUrl }: {
  isDark: boolean;
  mapUrl: string;
  bumpUrl: string;
}) {
  const meshRef = useRef<THREE.Mesh>(null);

  const { mapTexture, bumpTexture } = useMemo(() => {
    const loader = new THREE.TextureLoader();
    return {
      mapTexture: loader.load(mapUrl),
      bumpTexture: loader.load(bumpUrl),
    };
  }, [mapUrl, bumpUrl]);

  // Flip texture horizontally (Earth maps are usually offset)
  useEffect(() => {
    if (mapTexture) {
      mapTexture.wrapS = THREE.RepeatWrapping;
      mapTexture.repeat.set(-1, 1);
      mapTexture.needsUpdate = true;
    }
    if (bumpTexture) {
      bumpTexture.wrapS = THREE.RepeatWrapping;
      bumpTexture.repeat.set(-1, 1);
      bumpTexture.needsUpdate = true;
    }
  }, [mapTexture, bumpTexture]);

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1, 64, 64]} />
      <meshStandardMaterial
        map={mapTexture}
        bumpMap={bumpTexture}
        bumpScale={isDark ? 0.04 : 0.08}
        emissive={new THREE.Color('#10B981')}
        emissiveIntensity={isDark ? 0.06 : 0.02}
        roughness={0.7}
        metalness={0.1}
      />
    </mesh>
  );
}

// Full globe with auto-rotation
function GlobeScene({ isDark }: { isDark: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.0015;
    }
  });

  const textures = isDark ? EARTH_TEXTURES.dark : EARTH_TEXTURES.light;

  return (
    <group ref={groupRef}>
      <GlobeSphere
        isDark={isDark}
        mapUrl={textures.map}
        bumpUrl={textures.bump}
      />
      <Atmosphere isDark={isDark} />

      {/* All markers */}
      {LOCATIONS.map((loc, i) => (
        <Marker key={i} location={loc} />
      ))}

      {/* Arcs from UK to other ISP countries — colored by destination type */}
      {ISP_LOCATIONS.slice(1).map((loc, i) => (
        <Arc
          key={i}
          from={ISP_LOCATIONS[0]}
          to={loc}
          color={TYPE_COLORS[loc.type]}
        />
      ))}
    </group>
  );
}

export default function GlobeMap() {
  const [featuredLocation, setFeaturedLocation] = useState(ISP_LOCATIONS[0]);
  const [isDark, setIsDark] = useState(true);
  const [loaded, setLoaded] = useState(false);

  // Detect theme
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Rotate featured country every 4 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const idx = Math.floor(Date.now() / 4000) % ISP_LOCATIONS.length;
      setFeaturedLocation(ISP_LOCATIONS[idx]);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const canvasBg = isDark ? '#0a0a0f' : '#f4f4f5';
  const cardBg = isDark ? '#1a1a2e' : '#ffffff';
  const cardText = isDark ? '#f4f4f5' : '#18181b';
  const cardSubtext = isDark ? '#71717a' : '#71717a';

  return (
    <div className="relative w-full flex flex-col items-center">
      <div className="relative w-full" style={{ height: '380px' }}>
        <Canvas
          camera={{ position: [0, 0, 3.2], fov: 40 }}
          style={{ background: canvasBg }}
          gl={{ antialias: true, alpha: false }}
        >
          <ambientLight intensity={isDark ? 0.3 : 0.8} />
          <directionalLight position={[5, 3, 5]} intensity={isDark ? 0.4 : 0.7} />
          <pointLight position={[-5, -3, -5]} intensity={isDark ? 0.2 : 0.3} />
          <GlobeScene isDark={isDark} />
        </Canvas>

        {/* Floating callout card — themed to match site */}
        <div
          className="absolute rounded-2xl shadow-2xl p-4 flex items-center gap-3 transition-all duration-700 border"
          style={{
            right: '8%',
            top: '15%',
            minWidth: '165px',
            background: cardBg,
            borderColor: isDark ? '#10B98133' : '#e4e4e7',
            animation: 'floatCard 3s ease-in-out infinite',
          }}
        >
          <span className="text-3xl">{featuredLocation.flag}</span>
          <div>
            <p className="font-bold text-sm leading-tight" style={{ color: cardText }}>
              {featuredLocation.country}
            </p>
            <p className="text-xs flex items-center gap-1 mt-0.5" style={{ color: cardSubtext }}>
              <svg className="w-3 h-3" style={{ color: '#10B981' }} fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
              </svg>
              {featuredLocation.region}
            </p>
          </div>
        </div>

        {/* Coverage badge */}
        <div
          className="absolute bottom-4 left-4 rounded-xl px-3 py-2 shadow-lg border backdrop-blur-sm"
          style={{
            background: isDark ? 'rgba(26,26,46,0.9)' : 'rgba(255,255,255,0.9)',
            borderColor: isDark ? '#10B98133' : '#e4e4e7',
          }}
        >
          <p className="text-xs" style={{ color: cardSubtext }}>9 Countries</p>
          <p className="text-sm font-bold" style={{ color: '#10B981' }}>ISP Coverage</p>
        </div>
      </div>

      {/* Legend — themed colors */}
      <div className="flex flex-wrap justify-center gap-5 mt-5 text-sm">
        <span className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: '#10B981' }} />
          <span style={{ color: '#71717a' }}>ISP Proxies</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: '#a855f7' }} />
          <span style={{ color: '#71717a' }}>Residential</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: '#3b82f6' }} />
          <span style={{ color: '#71717a' }}>Mobile 4G</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: '#f97316' }} />
          <span style={{ color: '#71717a' }}>Datacenter</span>
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
