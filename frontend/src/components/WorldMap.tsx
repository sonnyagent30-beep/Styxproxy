'use client';

import { useState, useEffect } from 'react';

// Country data with SVG coordinates (viewBox: 0 0 1000 500)
const COUNTRIES = [
  { name: 'UK', country: 'United Kingdom', region: 'Europe', flag: '🇬🇧', x: 470, y: 140, type: 'ISP' },
  { name: 'US', country: 'United States', region: 'North America', flag: '🇺🇸', x: 180, y: 160, type: 'ISP' },
  { name: 'DE', country: 'Germany', region: 'Europe', flag: '🇩🇪', x: 510, y: 150, type: 'ISP' },
  { name: 'FR', country: 'France', region: 'Europe', flag: '🇫🇷', x: 490, y: 160, type: 'ISP' },
  { name: 'CA', country: 'Canada', region: 'North America', flag: '🇨🇦', x: 170, y: 120, type: 'ISP' },
  { name: 'JP', country: 'Japan', region: 'Asia Pacific', flag: '🇯🇵', x: 840, y: 170, type: 'ISP' },
  { name: 'AU', country: 'Australia', region: 'Oceania', flag: '🇦🇺', x: 830, y: 370, type: 'ISP' },
  { name: 'BR', country: 'Brazil', region: 'South America', flag: '🇧🇷', x: 290, y: 340, type: 'ISP' },
  { name: 'SG', country: 'Singapore', region: 'Asia Pacific', flag: '🇸🇬', x: 770, y: 270, type: 'ISP' },
];

// Connections from UK to all other ISP countries
const CONNECTIONS = [
  { from: 'UK', to: 'US' },
  { from: 'UK', to: 'DE' },
  { from: 'UK', to: 'FR' },
  { from: 'UK', to: 'CA' },
  { from: 'UK', to: 'JP' },
  { from: 'UK', to: 'AU' },
  { from: 'UK', to: 'BR' },
  { from: 'UK', to: 'SG' },
];

// Simplified continent shapes (abstract network diagram style)
const CONTINENTS = [
  // North America
  'M 120,80 L 280,80 L 300,100 L 280,150 L 220,180 L 150,170 L 100,130 L 90,100 Z',
  // South America
  'M 220,280 L 320,280 L 350,320 L 320,420 L 250,450 L 200,400 L 190,320 Z',
  // Europe
  'M 420,80 L 520,80 L 540,100 L 530,150 L 470,160 L 410,140 L 400,110 Z',
  // Africa
  'M 420,180 L 530,180 L 560,230 L 540,320 L 470,360 L 410,320 L 400,250 L 400,180 Z',
  // Asia
  'M 540,80 L 780,80 L 850,120 L 870,180 L 820,220 L 720,200 L 640,180 L 560,150 L 540,110 Z',
  // Australia
  'M 780,320 L 880,320 L 920,370 L 890,430 L 800,430 L 760,370 Z',
];

// Fun country facts for the callout
const COUNTRY_FACTS: Record<string, string> = {
  UK: 'London HQ • 99.9% uptime',
  US: '15+ datacenters • 10Gbps speeds',
  DE: 'Frankfurt hub • EU compliance',
  FR: 'Paris presence • Low latency',
  CA: 'Toronto/Vancouver • North America',
  JP: 'Tokyo edge • Asia-Pacific hub',
  AU: 'Sydney presence • Oceania coverage',
  BR: 'São Paulo gateway • LATAM access',
  SG: 'Singapore hub • Asia connectivity',
};

export default function WorldMap() {
  const [featuredIndex, setFeaturedIndex] = useState(0);
  const [isDark, setIsDark] = useState(true);

  // Detect color scheme
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDark(mediaQuery.matches);
    
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  // Cycle through countries every 4 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setFeaturedIndex((prev) => (prev + 1) % COUNTRIES.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const featuredCountry = COUNTRIES[featuredIndex];
  const uk = COUNTRIES.find(c => c.name === 'UK')!;

  return (
    <div className="relative w-full h-[380px] overflow-hidden rounded-2xl bg-[var(--card)] border border-[var(--border)]">
      <svg
        viewBox="0 0 1000 500"
        className="w-full h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* Gradient for map fill */}
          <linearGradient id="mapGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={isDark ? '#1a1a2e' : '#f0f4f8'} />
            <stop offset="100%" stopColor={isDark ? '#0f0f1a' : '#e2e8f0'} />
          </linearGradient>
          
          {/* Glow filter for dots */}
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          
          {/* Animated dash pattern for connections */}
          <style>
            {`
              @keyframes flowData {
                from { stroke-dashoffset: 0; }
                to { stroke-dashoffset: -24; }
              }
              @keyframes pulse {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.8); opacity: 0; }
              }
              @keyframes pulseDot {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.5); opacity: 0.6; }
              }
              .connection-line {
                stroke-dasharray: 8 4;
                animation: flowData 1.5s linear infinite;
              }
              .pulse-ring {
                transform-origin: center;
                animation: pulse 2s ease-out infinite;
              }
              .marker-dot {
                transform-origin: center;
                animation: pulseDot 2s ease-in-out infinite;
              }
            `}
          </style>
        </defs>

        {/* Simplified continent outlines */}
        <g className="opacity-30" fill="none" stroke={isDark ? '#4a5568' : '#94a3b8'} strokeWidth="2">
          {CONTINENTS.map((path, i) => (
            <path key={i} d={path} />
          ))}
        </g>

        {/* Connection lines from UK */}
        <g>
          {CONNECTIONS.map((conn, i) => {
            const fromCountry = COUNTRIES.find(c => c.name === conn.from)!;
            const toCountry = COUNTRIES.find(c => c.name === conn.to)!;
            
            return (
              <line
                key={i}
                x1={fromCountry.x}
                y1={fromCountry.y}
                x2={toCountry.x}
                y2={toCountry.y}
                className="connection-line"
                stroke="#10B981"
                strokeWidth="1.5"
                strokeOpacity="0.6"
              />
            );
          })}
        </g>

        {/* Country markers */}
        <g>
          {COUNTRIES.map((country, i) => {
            const isFeatured = country.name === featuredCountry.name;
            const isUK = country.name === 'UK';
            
            return (
              <g key={country.name}>
                {/* Pulse ring for featured country */}
                {isFeatured && (
                  <circle
                    cx={country.x}
                    cy={country.y}
                    r="20"
                    className="pulse-ring"
                    fill="none"
                    stroke="#10B981"
                    strokeWidth="2"
                  />
                )}
                
                {/* Main dot */}
                <circle
                  cx={country.x}
                  cy={country.y}
                  r={isFeatured ? 8 : isUK ? 7 : 6}
                  className="marker-dot"
                  fill={isFeatured || isUK ? '#10B981' : '#10B981'}
                  filter="url(#glow)"
                  style={{ opacity: isFeatured ? 1 : 0.8 }}
                />
                
                {/* Country label */}
                <text
                  x={country.x}
                  y={country.y + 22}
                  textAnchor="middle"
                  className="text-[10px] font-medium"
                  fill={isDark ? '#e2e8f0' : '#1e293b'}
                  style={{ fontSize: '11px' }}
                >
                  {country.flag} {country.name}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Floating callout card */}
      <div className="absolute top-4 right-4 bg-[var(--card)]/95 backdrop-blur-sm border border-[var(--border)] rounded-xl p-4 min-w-[200px] shadow-lg">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">{featuredCountry.flag}</span>
          <div>
            <h3 className="font-bold text-[var(--foreground)]">{featuredCountry.country}</h3>
            <p className="text-xs text-[var(--muted)]">{featuredCountry.region}</p>
          </div>
        </div>
        <p className="text-sm text-[var(--muted)] border-t border-[var(--border)] pt-2 mt-2">
          {COUNTRY_FACTS[featuredCountry.name]}
        </p>
        <div className="flex gap-1 mt-3 justify-center">
          {COUNTRIES.map((_, i) => (
            <div
              key={i}
              className={`w-1.5 h-1.5 rounded-full transition-colors ${
                i === featuredIndex ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Title overlay */}
      <div className="absolute bottom-4 left-4">
        <h2 className="text-2xl font-bold text-[var(--foreground)]">Global ISP Network</h2>
        <p className="text-sm text-[var(--muted)]">9 countries • 99.9% uptime SLA</p>
      </div>
    </div>
  );
}
