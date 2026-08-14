'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { 
  Globe, House, HardDrives, DeviceMobile, Lightning, Clock, Check, X,
  Desktop, Rocket, Target, CaretDown, ArrowRight, Warning, Heart, Star,
  CurrencyNgn
} from '@phosphor-icons/react';

// Product data matching the HTML mockup
const PRODUCTS = [
  {
    key: 'ISP',
    name: 'ISP Proxy',
    coverName: 'Baseline Identity',
    tagline: 'Your registered ISP address. Stable, fast, hard to flag.',
    description: 'Static IP from a real ISP. Looks like a genuine home connection without the bandwidth limits of actual residential. The professional\'s choice for sneaker bots, ticket drops, and automation at scale.',
    price: '₦6,500',
    priceUnit: 'per IP/mo',
    countries: 45,
    uptime: '99.9%',
    latency: '<50ms',
    tags: ['Static IP', 'High Speed'],
    bestFor: ['Sneaker bots', 'Ticket drops', 'Account creation', 'Automation'],
    stats: { detection: 70, speed: 80, geo: 65, cost: 85 },
    gauge: { value: '~30d', color: 'warning', typical: '30d', hot: '7d', lowRisk: '90d' },
    radar: [34, 114, 109, 80, 46, 51],
    polygonPoints: '148.0,80.0 111.0,133.69 50.5,131.1 30.0,80.0 65.5,54.89 111.0,26.31',
    threatView: [
      { platform: 'Google', risk: 'Low', segments: 4, desc: 'Real ISP allocation. Usually passes reCAPTCHA. Occasional manual review.' },
      { platform: 'Cloudflare', risk: 'Low', segments: 3, desc: 'Most ISP ranges are whitelisted. Fast passthrough with minimal friction.' },
      { platform: 'Banks', risk: 'Medium', segments: 3, desc: 'Some banks flag datacenter-adjacent IPs. Works in most regions.' },
    ],
  },
  {
    key: 'RESIDENTIAL',
    name: 'Residential',
    coverName: 'Deep Cover',
    tagline: 'A real home address. Nearly impossible to detect.',
    description: 'Real IPs from actual home devices worldwide. The gold standard for anonymity. Every request looks like a genuine person browsing from their house. Social media, scraping, brand monitoring — this is the cover that rarely burns.',
    price: '₦15,000',
    priceUnit: 'per month',
    countries: 90,
    uptime: '94%',
    latency: '<100ms',
    tags: ['Real Home IP', 'Highest Anonymity'],
    bestFor: ['Social media', 'Brand monitoring', 'Web scraping', 'Price aggregation'],
    stats: { detection: 92, speed: 55, geo: 75, cost: 50 },
    gauge: { value: '~45d', color: 'primary', typical: '45d', hot: '14d', lowRisk: '180d' },
    radar: [76, 117, 106, 80, 40, 49],
    polygonPoints: '133.0,80.0 117.6,145.13 47.5,136.29 15.0,80.0 55.0,36.7 117.6,14.87',
    featured: true,
    threatView: [
      { platform: 'Google', risk: 'Very low', segments: 5, desc: 'Looks like a real home user. Google sees it as genuine traffic. Best reCAPTCHA pass rate of any proxy type.' },
      { platform: 'Cloudflare', risk: 'Low', segments: 4, desc: 'Passes all fingerprint checks. Real residential ASNs are broadly whitelisted across platforms.' },
      { platform: 'Banks', risk: 'Low', segments: 4, desc: 'Most retail banking sites accept residential IPs without friction. No additional friction or flags triggered.' },
    ],
  },
  {
    key: 'MOBILE',
    name: 'Mobile 4G',
    coverName: 'Ghost Protocol',
    tagline: 'Carrier-issued IP. Mobile network-level anonymity.',
    description: 'Real IPs from mobile carrier networks. No device fingerprint to match. The hardest cover to burn because it carries the full credibility of a mobile subscriber. For high-value operations where every request must look like a genuine mobile user on a real carrier.',
    price: '₦20,000',
    priceUnit: 'per month',
    countries: 30,
    uptime: '96%',
    latency: '<80ms',
    tags: ['Carrier IP', 'No Device FP', 'Rotating/Static'],
    bestFor: ['Ad verification', 'App testing', 'Social media', 'Account mgmt'],
    stats: { detection: 96, speed: 60, geo: 88, cost: 38 },
    gauge: { value: '~60d', color: 'primary', typical: '60d', hot: '21d', lowRisk: '180d' },
    radar: [72, 119, 102, 80, 38, 46],
    polygonPoints: '136.0,80.0 118.8,147.2 43.6,143.05 0.0,80.0 51.4,30.46 118.8,12.8',
    threatView: [
      { platform: 'Google', risk: 'Very low', segments: 5, desc: 'Carrier IPs are rarely flagged. Mobile ASNs have the highest trust score across Google\'s systems.' },
      { platform: 'Cloudflare', risk: 'Low', segments: 4, desc: 'Mobile carrier traffic is indistinguishable from regular mobile browsing. Broad platform acceptance.' },
      { platform: 'Banks', risk: 'Low', segments: 4, desc: 'Mobile banking is the default for billions of users. Carrier IPs blend in perfectly.' },
    ],
  },
  {
    key: 'DATACENTER',
    name: 'Datacenter',
    coverName: 'Fast Lane',
    tagline: 'Maximum speed. Known datacenter ranges. Accept the tradeoff.',
    description: 'Fastest throughput at the lowest cost. Datacenter IPs are well-known to detection systems — expect CAPTCHAs on sensitive platforms. For bulk operations, SEO tools, and traffic routing where stealth is not the priority.',
    price: '₦3,500',
    priceUnit: 'per month',
    countries: 120,
    uptime: '99%',
    latency: '<5ms',
    tags: ['Cloud IP', 'High Detection'],
    bestFor: ['SEO tools', 'Traffic routing', 'Data collection', 'Bulk requests'],
    stats: { detection: 25, speed: 98, geo: 90, cost: 95 },
    gauge: { value: '~7d', color: 'danger', typical: '7d', hot: '1d', lowRisk: '30d' },
    radar: [92, 130, 130, 92, 66, 66],
    polygonPoints: '158.8,80.0 97.5,110.31 43.0,144.09 52.8,80.0 68.5,60.08 97.5,49.69',
    statusDot: 'warn',
    threatView: [
      { platform: 'Google', risk: 'High', segments: 2, desc: 'Known datacenter ranges are flagged. Expect CAPTCHA failures and manual review triggers.' },
      { platform: 'Cloudflare', risk: 'Medium', segments: 3, desc: 'Some datacenter IPs blocked by default. Rotate IPs frequently to stay through.' },
      { platform: 'Banks', risk: 'High', segments: 2, desc: 'Banking fraud systems flag datacenter IPs aggressively. Do not use for account access.' },
    ],
  },
];

// Radar chart points for SVG
const RADAR_POINTS = [
  { x: 80, y: 18 },  // Speed (top)
  { x: 124, y: 46 }, // Detection (top-right)
  { x: 124, y: 114 }, // Geo (bottom-right)
  { x: 80, y: 142 }, // Ban (bottom)
  { x: 36, y: 114 }, // Cost (bottom-left)
  { x: 36, y: 46 },  // Stealth (top-left)
];

function getRadarPoints(values: number[]): string {
  return values.map((v, i) => {
    const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2;
    const radius = (v / 140) * 60 + 20;
    return `${80 + radius * Math.cos(angle)},${80 + radius * Math.sin(angle)}`;
  }).join(' ');
}

function parsePolygonPoints(pts: string): { x: number; y: number }[] {
  return pts.split(' ').map((p) => {
    const [x, y] = p.split(',').map(Number);
    return { x, y };
  });
}

export default function ProductsPage() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [selectedMission, setSelectedMission] = useState<string | null>(null);
  const [visibleCards, setVisibleCards] = useState<Set<string>>(new Set());
  const cardRefs = useRef<Map<string, HTMLElement>>(new Map());

  // Product card individual observers
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setVisibleCards((prev) => new Set([...prev, entry.target.id]));
          }
        });
      },
      { threshold: 0.1 }
    );

    cardRefs.current.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  // Global reveal observer — makes all .reveal elements visible on scroll
  useEffect(() => {
    const revealEls = document.querySelectorAll('.reveal');
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.05 }
    );
    revealEls.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const toggleExpand = (key: string) => {
    setExpanded(expanded === key ? null : key);
  };

  const [briefingDone] = useState(false);
  const [showBriefingModal, setShowBriefingModal] = useState(false);
  const [briefingProfile, setBriefingProfile] = useState<{ type: string; text: string } | null>(null);

  const handleMissionClick = (key: string) => {
    setSelectedMission(key);
    const element = document.getElementById(`product-${key}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      element.style.transition = 'box-shadow 0.3s';
      element.style.boxShadow = '0 0 0 2px var(--primary), 0 0 40px rgba(10,210,90,0.15)';
      setTimeout(() => {
        element.style.boxShadow = '';
      }, 2000);
    }
  };

  const selectBriefing = (type: string) => {
    const profiles: Record<string, string> = {
      ISP: '"Baseline Identity." Fast and stable. ISP speed with home-IP credibility. Ideal for sneaker bots, ticket drops, and high-frequency automation where latency is the enemy.',
      RESIDENTIAL: '"Deep Cover." Real home IPs from actual devices. Maximum authenticity and the highest ban resistance of any cover. Best for social media management, scraping, and anywhere detection is fatal.',
      MOBILE: '"Ghost Protocol." Carrier-grade anonymity with no device fingerprint. The hardest cover to burn. For high-value operations where every request must look like a genuine mobile user.',
      DATACENTER: '"Fast Lane." Maximum throughput at minimum cost. Accept the detection tradeoff — these IPs are well-known. For bulk operations, SEO tools, and traffic routing where stealth is not the priority.',
    };
    setBriefingProfile({ type, text: profiles[type] || '' });
  };

  const acceptMission = () => {
    sessionStorage.setItem('briefingDone', '1');
    setShowBriefingModal(false);
    if (briefingProfile) {
      handleMissionClick(briefingProfile.type);
    }
  };

  const skipBriefing = () => {
    sessionStorage.setItem('briefingDone', '1');
    setShowBriefingModal(false);
  };

  // showBriefing fires once on mount if not already done
  useEffect(() => {
    if (!sessionStorage.getItem('briefingDone')) {
      const timer = setTimeout(() => {
        setShowBriefingModal(true);
      }, 600);
      return () => clearTimeout(timer);
    }
  }, []);

  // Escape key closes modal
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showBriefingModal) skipBriefing();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [showBriefingModal]);

  return (
    <div className="min-h-screen">
      {/* Briefing Modal */}
      {showBriefingModal && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Choose your proxy cover"
        >
          <div className="modal-box">
            <button
              className="modal-close"
              onClick={skipBriefing}
              aria-label="Close modal"
            >
              <X weight="bold" className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-6">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse flex-shrink-0"
                style={{ boxShadow: '0 0 8px var(--error)' }} />
              <span className="text-xs uppercase tracking-widest font-mono text-gray-500">
                Classified // Eyes Only
              </span>
            </div>

            <h2 className="text-2xl font-bold mb-3 leading-tight text-[var(--primary-light)] tracking-tight">
              Choose your cover.
            </h2>
            <p className="text-sm mb-6 leading-relaxed text-gray-400">
              Each disguise has a distinct signature. Pick the one that fits your operation.
            </p>

            <p className="text-xs uppercase tracking-widest font-mono mb-4 text-gray-500">
              Primary objective:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
              {[
                { type: 'ISP', label: 'Speed Operations', icon: Desktop, desc: 'Sneaker bots, ticket drops, automation — where latency is the enemy.' },
                { type: 'RESIDENTIAL', label: 'Identity Operations', icon: House, desc: 'Social media, scraping, brand monitoring — maximum authenticity required.' },
                { type: 'MOBILE', label: 'Verification Ops', icon: DeviceMobile, desc: 'Ad verification, app testing, mobile campaigns — carrier-level stealth.' },
                { type: 'DATACENTER', label: 'Bulk Operations', icon: HardDrives, desc: 'SEO tools, traffic routing, data collection — speed over stealth.' },
              ].map((m) => (
                <button
                  key={m.type}
                  onClick={() => selectBriefing(m.type)}
                  className={`p-4 rounded-xl text-left transition-all duration-200 border ${
                    briefingProfile?.type === m.type
                      ? 'border-[var(--primary)] bg-[var(--primary)]/10'
                      : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/40'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-[var(--primary)]/10 flex-shrink-0">
                      <m.icon weight="fill" className="text-[var(--primary)] w-[18px] h-[18px]" />
                    </div>
                    <div className="font-bold text-sm">{m.label}</div>
                  </div>
                  <div className="text-xs leading-relaxed text-gray-400">{m.desc}</div>
                </button>
              ))}
            </div>

            {briefingProfile && (
              <div className="mb-5 p-4 rounded-xl bg-[var(--primary)]/05 border border-[var(--primary)]/20">
                <div className="text-xs uppercase tracking-widest font-mono mb-2 text-[var(--primary)]">Briefing</div>
                <div className="text-sm leading-relaxed">{briefingProfile.text}</div>
              </div>
            )}

            <div className="flex gap-3 mt-6">
              <button
                onClick={acceptMission}
                disabled={!briefingProfile}
                className="flex-1 text-center py-3 rounded-xl font-semibold text-black bg-[var(--primary)] hover:bg-[var(--primary-dark)] transition-all duration-200 disabled:opacity-40"
              >
                Begin Operation
              </button>
              <button
                onClick={skipBriefing}
                className="px-6 py-3 rounded-xl border border-[var(--border)] text-gray-300 hover:border-[var(--primary)]/40 transition-all duration-200"
              >
                Skip
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Ticker */}
      <div className="ticker-wrap">
        <div className="ticker-track">
          <span className="ticker-item"><span className="ticker-dot"></span><span className="ticker-value">847</span> requests routed</span>
          <span className="ticker-item"><span className="ticker-dot"></span><span className="ticker-value">4.2</span> TB transferred</span>
          <span className="ticker-item"><span className="ticker-dot"></span><span className="ticker-value text-red-500">0</span> detections</span>
          <span className="ticker-item"><span className="ticker-dot"></span><span className="ticker-value">12</span> active operations</span>
          <span className="ticker-item"><span className="ticker-dot"></span>Residential <span className="ticker-value">94%</span> uptime</span>
          <span className="ticker-item"><span className="ticker-dot"></span>ISP <span className="ticker-value">97%</span> uptime</span>
          <span className="ticker-item"><span className="ticker-dot"></span><span className="ticker-value">127</span> jurisdictions</span>
          <span className="ticker-item"><span className="ticker-dot"></span>Avg response <span className="ticker-value">23</span>ms</span>
          {/* Duplicate for seamless loop */}
          <span className="ticker-item"><span className="ticker-dot"></span><span className="ticker-value">847</span> requests routed</span>
          <span className="ticker-item"><span className="ticker-dot"></span><span className="ticker-value">4.2</span> TB transferred</span>
          <span className="ticker-item"><span className="ticker-dot"></span><span className="ticker-value text-red-500">0</span> detections</span>
          <span className="ticker-item"><span className="ticker-dot"></span><span className="ticker-value">12</span> active operations</span>
          <span className="ticker-item"><span className="ticker-dot"></span>Residential <span className="ticker-value">94%</span> uptime</span>
          <span className="ticker-item"><span className="ticker-dot"></span>ISP <span className="ticker-value">97%</span> uptime</span>
          <span className="ticker-item"><span className="ticker-dot"></span><span className="ticker-value">127</span> jurisdictions</span>
          <span className="ticker-item"><span className="ticker-dot"></span>Avg response <span className="ticker-value">23</span>ms</span>
        </div>
      </div>

      {/* Hero */}
      <div className="relative overflow-hidden pt-24 pb-12 px-4">
        <div className="absolute inset-0 hero-bg-grid" />
        <div className="absolute inset-0 hero-bg-vignette" />

        <div className="relative max-w-7xl mx-auto">
          <div className="text-center mb-6">
            <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border border-green-500/25 bg-green-500/4">
              <div className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] shadow-[0_0_8px_var(--primary)] animate-pulse" />
              <span className="text-xs font-mono uppercase tracking-widest text-[var(--primary)]">Disguise Catalog</span>
            </div>

            <h1 className="text-4xl sm:text-5xl font-bold mt-6 mb-5 tracking-tight">
              Not all disguises<br />
              <span className="text-[var(--primary)]">are equal.</span>
            </h1>

            <p className="text-base mb-2 max-w-lg mx-auto leading-relaxed text-gray-300">
              ISP · Residential · Mobile · Datacenter
            </p>
            <p className="text-sm max-w-md mx-auto leading-relaxed text-gray-500">
              Know the difference before you buy. Your anonymity depends on choosing the right cover.
            </p>
          </div>

          {/* Mission quick-nav */}
          <div className="flex items-center justify-center gap-2 sm:gap-3">
            {[
              { label: 'Speed Ops', key: 'ISP' },
              { label: 'Identity Ops', key: 'RESIDENTIAL' },
              { label: 'Verification', key: 'MOBILE' },
              { label: 'Bulk Ops', key: 'DATACENTER' },
            ].map((mission) => (
              <button
                key={mission.key}
                onClick={() => handleMissionClick(mission.key)}
                className={`px-2 sm:px-3 md:px-5 py-2 rounded-full text-xs sm:text-sm font-medium transition-all duration-200 border whitespace-nowrap ${
                  selectedMission === mission.key
                    ? 'bg-[var(--primary)] text-black border-[var(--primary)]'
                    : 'bg-[var(--card)] border-[var(--border)] text-gray-300 hover:border-[var(--primary)] hover:text-[var(--primary)]'
                }`}
              >
                {mission.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Product Cards */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        {PRODUCTS.map((product) => (
          <div
            key={product.key}
            id={`product-${product.key}`}
            ref={(el) => { if (el) cardRefs.current.set(`product-${product.key}`, el); }}
            className={`reveal mb-8 p-6 ${product.featured ? 'card-depth-primary' : 'card-depth'} ${
              visibleCards.has(`product-${product.key}`) ? 'visible' : ''
            }`}
          >
            {/* Featured badge */}
            {product.featured && (
              <div className="absolute -top-3 left-8">
                <span className="text-xs font-bold px-4 py-1 rounded-full bg-[var(--primary)] text-black">Top Pick</span>
              </div>
            )}

            <div className="flex flex-col lg:flex-row lg:items-start gap-8">
              {/* Left: Identity */}
              <div className="flex-1">
                <div className="flex items-start gap-5 mb-5">
                  <div className="w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 bg-green-500/8 border border-green-500/15">
                    {product.key === 'ISP' && <Desktop weight="fill" className="text-[var(--primary)] w-[26px] h-[26px]" />}
                    {product.key === 'RESIDENTIAL' && <House weight="fill" className="text-[var(--primary)] w-[26px] h-[26px]" />}
                    {product.key === 'MOBILE' && <DeviceMobile weight="fill" className="text-[var(--primary)] w-[26px] h-[26px]" />}
                    {product.key === 'DATACENTER' && <HardDrives weight="fill" className="text-[var(--primary)] w-[26px] h-[26px]" />}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <div className={`status-dot ${product.statusDot || ''}`} />
                      <h3 className="text-2xl font-bold tracking-tight">{product.name}</h3>
                    </div>
                    <span className={`text-xs font-mono uppercase px-3 py-1 rounded-full ${
                      product.statusDot === 'warn'
                        ? 'bg-red-500/8 border border-red-500/20 text-red-500'
                        : 'bg-green-500/8 border border-green-500/20 text-[var(--primary)]'
                    }`}>
                      {product.coverName}
                    </span>
                    <p className="text-sm leading-relaxed mt-2 text-gray-300">
                      {product.tagline}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0 lg:hidden">
                    <div className="text-2xl font-bold text-[var(--primary)]">{product.price}</div>
                    <div className="text-xs text-gray-500">{product.priceUnit}</div>
                  </div>
                </div>

                {/* Mini chips */}
                <div className="mini-chips mb-5">
                  <div className="mini-chip"><span className="chip-val">{product.countries}</span> Countries</div>
                  <div className="mini-chip"><span className="chip-val">{product.uptime}</span> Uptime</div>
                  <div className="mini-chip"><span className="chip-val">{product.latency}</span> Latency</div>
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-2 mb-5">
                  {product.tags.map((tag) => (
                    <span
                      key={tag}
                      className={`text-xs px-3 py-1 rounded-full ${
                        tag === 'High Detection' || tag === 'High Speed'
                          ? 'bg-amber-500/8 border border-amber-500/20 text-amber-500'
                          : 'bg-green-500/6 border border-green-500/15 text-green-400'
                      }`}
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                <p className="text-sm leading-relaxed mb-4 text-gray-400">
                  {product.description}
                </p>

                {/* Best for */}
                <div className="mb-5">
                  <p className="text-xs uppercase tracking-widest font-mono mb-2 text-gray-500">Best for</p>
                  <div className="bestfor-strip">
                    {product.bestFor.map((item) => (
                      <span key={item} className="bestfor-tag">{item}</span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right: Visual metrics — 2-col grid (radar + gauge) + loadout stats below */}
              <div className="lg:w-72 flex-shrink-0">
                <div className="grid grid-cols-2 gap-4">
                  {/* Radar chart */}
                  <div className="p-4 rounded-xl" style={{ background: 'rgba(10,210,90,0.03)', border: '1px solid var(--border)' }}>
                    <p className="text-xs uppercase tracking-widest font-mono mb-3" style={{ color: 'var(--muted)', letterSpacing: '0.1em' }}>Anonymity Radar</p>
                    <div className="radar-chart">
                      <svg viewBox="0 0 160 160" className="w-full">
                        {[40, 60, 80, 100].map((r) => (
                          <circle key={r} cx="80" cy="80" r={r} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
                        ))}
                        {RADAR_POINTS.map((p) => (
                          <line key={`${p.x}-${p.y}`} x1="80" y1="80" x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
                        ))}
                        <polygon
                          className="radar-polygon"
                          points={product.polygonPoints}
                          fill="rgba(10,210,90,0.12)"
                          stroke={product.statusDot === 'warn' ? 'var(--error)' : 'var(--primary)'}
                          strokeWidth="1.5"
                        />
                        {/* Endpoint dots — computed from polygonPoints */}
                        {parsePolygonPoints(product.polygonPoints).map((pt, i) => (
                          <circle key={i} cx={pt.x} cy={pt.y} r="3" fill={product.statusDot === 'warn' ? 'var(--error)' : 'var(--primary)'} />
                        ))}
                        {/* Axis labels */}
                        <text x="80" y="10" textAnchor="middle" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">SPD</text>
                        <text x="130" y="44" textAnchor="start" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">DET</text>
                        <text x="130" y="118" textAnchor="start" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">GEO</text>
                        <text x="80" y="158" textAnchor="middle" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">BAN</text>
                        <text x="26" y="118" textAnchor="end" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">CST</text>
                        <text x="26" y="44" textAnchor="end" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">STB</text>
                      </svg>
                    </div>
                  </div>

                  {/* Cover life gauge */}
                  <div className="p-4 rounded-xl" style={{ background: 'rgba(10,210,90,0.03)', border: '1px solid var(--border)' }}>
                    <p className="text-xs uppercase tracking-widest font-mono mb-3" style={{ color: 'var(--muted)', letterSpacing: '0.1em' }}>Cover Life</p>
                    <div className="gauge-wrap">
                      <svg className="gauge-svg" viewBox="0 0 120 80">
                        <path className="gauge-track" d="M 15 65 A 45 45 0 0 1 105 65" />
                        <path
                          className="gauge-fill"
                          d="M 15 65 A 45 45 0 0 1 105 65"
                          stroke={product.gauge.color === 'warning' ? 'var(--warning)' : product.gauge.color === 'danger' ? 'var(--error)' : 'var(--primary)'}
                          strokeDasharray="141"
                          strokeDashoffset={product.gauge.color === 'danger' ? '113' : product.gauge.color === 'warning' ? '82' : '35'}
                        />
                        <text x="60" y="58" textAnchor="middle" style={{ fontSize: '13px', fill: product.gauge.color === 'danger' ? 'var(--error)' : product.gauge.color === 'warning' ? 'var(--warning)' : 'var(--primary)' }}>{product.gauge.value}</text>
                        <text x="60" y="72" textAnchor="middle" style={{ fontSize: '8px', fill: 'var(--muted)' }}>TYPICAL</text>
                      </svg>
                    </div>
                    <div className="grid grid-cols-3 gap-1 mt-3 text-center">
                      <div>
                        <div className="text-xs font-bold" style={{ color: product.gauge.color === 'danger' ? 'var(--error)' : product.gauge.color === 'warning' ? 'var(--warning)' : 'var(--primary)' }}>{product.gauge.typical}</div>
                        <div className="text-xs" style={{ color: 'var(--muted)' }}>Typical</div>
                      </div>
                      <div>
                        <div className="text-xs font-bold" style={{ color: product.gauge.color === 'danger' ? 'var(--error)' : 'var(--warning)' }}>{product.gauge.hot}</div>
                        <div className="text-xs" style={{ color: 'var(--muted)' }}>Hot</div>
                      </div>
                      <div>
                        <div className="text-xs font-bold" style={{ color: 'var(--primary)' }}>{product.gauge.lowRisk}</div>
                        <div className="text-xs" style={{ color: 'var(--muted)' }}>Low risk</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Loadout stats */}
                <div className="mt-4 p-4 rounded-xl" style={{ background: 'rgba(10,210,90,0.03)', border: '1px solid var(--border)' }}>
                  <p className="text-xs uppercase tracking-widest font-mono mb-3" style={{ color: 'var(--muted)', letterSpacing: '0.1em' }}>Loadout Stats</p>
                  <div className="space-y-3">
                    <div className="stat-row">
                      <span className="stat-label">Detection</span>
                      <div className="stat-bar-wrap">
                        <div
                          className="stat-bar-fill"
                          style={{
                            width: `${product.stats.detection}%`,
                            background: product.statusDot === 'warn'
                              ? 'linear-gradient(90deg,rgba(239,68,68,0.6),var(--error))'
                              : 'linear-gradient(90deg, rgba(10,210,90,0.6), var(--primary))'
                          }}
                        />
                      </div>
                      <span className="text-xs font-mono min-w-[28px] text-right" style={{ color: product.statusDot === 'warn' ? 'var(--error)' : 'var(--primary)' }}>
                        {product.stats.detection}
                      </span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Speed</span>
                      <div className="stat-bar-wrap"><div className="stat-bar-fill" style={{ width: `${product.stats.speed}%` }} /></div>
                      <span className="text-xs font-mono min-w-[28px] text-right" style={{ color: 'var(--primary)' }}>{product.stats.speed}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Geo</span>
                      <div className="stat-bar-wrap"><div className="stat-bar-fill" style={{ width: `${product.stats.geo}%` }} /></div>
                      <span className="text-xs font-mono min-w-[28px] text-right" style={{ color: 'var(--primary)' }}>{product.stats.geo}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Cost</span>
                      <div className="stat-bar-wrap"><div className="stat-bar-fill" style={{ width: `${product.stats.cost}%` }} /></div>
                      <span className="text-xs font-mono min-w-[28px] text-right" style={{ color: 'var(--primary)' }}>{product.stats.cost}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Price row */}
            <div className="mt-5 pt-5 flex flex-wrap items-center gap-6" style={{ borderTop: '1px solid var(--border)' }}>
              <div>
                <span className="text-xs font-mono uppercase tracking-widest text-gray-500" style={{ letterSpacing: '0.1em' }}>Starting from</span>
                <div className="text-2xl font-bold mt-1 text-[var(--primary)]">
                  {product.price}
                  <span className="text-sm font-normal text-gray-500">/{product.priceUnit === 'per IP/mo' ? 'mo' : 'mo'}</span>
                </div>
              </div>
              <Link href="/order" className="btn-primary">Deploy Cover</Link>
              <button 
                onClick={() => toggleExpand(product.key)}
                className="btn-ghost"
                aria-expanded={expanded === product.key}
                aria-controls={`expand-${product.key}`}
              >
                What they see <CaretDown weight="bold" className={`expand-icon w-3 h-3 ${expanded === product.key ? 'open' : ''}`} />
              </button>
              <div className="text-xs ml-auto hidden lg:block text-gray-500">{product.countries} countries available</div>
            </div>

            {/* Expand section */}
            <div className={`expand-body mt-6 ${expanded === product.key ? 'open' : ''}`} id={`expand-${product.key}`}>
              <div className="p-6 rounded-xl" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                <p className="text-xs uppercase tracking-widest font-mono mb-5" style={{ color: 'var(--muted)', letterSpacing: '0.1em' }}>Adversary Detection View</p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {product.threatView.map((threat) => (
                    <div 
                      key={threat.platform}
                      className="p-4 rounded-xl"
                      style={{ 
                        background: threat.risk === 'High' ? 'rgba(239,68,68,0.04)' : threat.risk === 'Medium' ? 'rgba(245,158,11,0.04)' : 'rgba(10,210,90,0.04)',
                        border: `1px solid ${threat.risk === 'High' ? 'rgba(239,68,68,0.12)' : threat.risk === 'Medium' ? 'rgba(245,158,11,0.12)' : 'rgba(10,210,90,0.12)'}`
                      }}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-semibold">{threat.platform}</span>
                        <span className={`text-xs ${
                          threat.risk === 'High' ? 'text-red-500' : threat.risk === 'Medium' ? 'text-amber-500' : 'text-[var(--primary)]'
                        }`}>
                          {threat.risk} risk
                        </span>
                      </div>
                      <div className="threat-bar-seg mb-2">
                        {[...Array(5)].map((_, i) => (
                          <span 
                            key={i} 
                            className={`threat-seg ${
                              i < threat.segments 
                                ? threat.risk === 'High' ? 'lit-red' : threat.risk === 'Medium' ? 'lit-yellow' : 'lit-green'
                                : ''
                            }`}
                          />
                        ))}
                      </div>
                      <p className="text-xs leading-relaxed text-gray-500">{threat.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charon's Toll */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <div className="section-divider-glow mb-20"></div>

        {/* Header */}
        <div className="text-center mb-16 reveal visible">
          <div className="styx-coin" style={{ margin: '0 auto 1.5rem' }}>
            <div className="styx-coin-ring"></div>
            <div className="styx-coin-ring"></div>
            <HardDrives weight="fill" className="w-7 h-7 text-[var(--primary)]" style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
          </div>
          <p className="text-xs uppercase tracking-widest font-mono mb-4" style={{ color: 'var(--muted)', letterSpacing: '0.15em' }}>The Ferryman&apos;s Price</p>
          <h2 className="text-4xl font-bold mb-4 leading-tight" style={{ letterSpacing: '-0.03em' }}>Charon&apos;s Toll</h2>
          <p className="text-base max-w-lg mx-auto leading-relaxed" style={{ color: 'var(--muted-light)' }}>
            No toll, no passage. Each disguise carries its own price — the cost of crossing unseen.
          </p>
        </div>

        {/* Toll cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-12">
          {/* ISP Toll */}
          <div className="card p-6 text-center reveal visible" style={{ animationDelay: '0.05s' }}>
            <div className="styx-coin" style={{ width: '52px', height: '52px', margin: '0 auto 1rem', position: 'relative' }}>
              <div className="styx-coin-ring"></div>
              <Desktop weight="fill" className="text-[var(--primary)] w-5 h-5" style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
            </div>
            <div className="text-xs uppercase tracking-widest font-mono mb-2" style={{ color: 'var(--muted)', letterSpacing: '0.1em' }}>ISP</div>
            <div className="styx-value-badge mb-3">₦6,500</div>
            <div className="text-xs mb-4" style={{ color: 'var(--muted)' }}>per IP / month</div>
            <div className="text-xs leading-relaxed" style={{ color: 'var(--muted-light)' }}>The minimum toll. Fast passage, moderate detection risk. Charon&apos;s seen these IPs before.</div>
          </div>

          {/* Residential Toll (featured) */}
          <div className="card-depth-primary p-6 text-center reveal visible" style={{ animationDelay: '0.1s', position: 'relative' }}>
            <div className="absolute -top-2.5 left-1/2 -translate-x-1/2">
              <span className="text-[10px] font-bold px-3 py-0.5 rounded-full" style={{ background: 'var(--primary)', color: '#000', letterSpacing: '0.05em' }}>Most Chosen</span>
            </div>
            <div className="styx-coin" style={{ width: '52px', height: '52px', margin: '0.5rem auto 1rem', position: 'relative' }}>
              <div className="styx-coin-ring"></div>
              <div className="styx-coin-ring"></div>
              <House weight="fill" className="text-[var(--primary)] w-5 h-5" style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
            </div>
            <div className="text-xs uppercase tracking-widest font-mono mb-2" style={{ color: 'var(--muted)', letterSpacing: '0.1em' }}>Residential</div>
            <div className="styx-value-badge mb-3">₦15,000</div>
            <div className="text-xs mb-4" style={{ color: 'var(--muted)' }}>per month</div>
            <div className="text-xs leading-relaxed" style={{ color: 'var(--muted-light)' }}>Two coins for true passage. Charon&apos;s favourite — these IPs belong to real souls.</div>
          </div>

          {/* Mobile Toll */}
          <div className="card p-6 text-center reveal visible" style={{ animationDelay: '0.15s' }}>
            <div className="styx-coin" style={{ width: '52px', height: '52px', margin: '0 auto 1rem', position: 'relative' }}>
              <div className="styx-coin-ring"></div>
              <div className="styx-coin-ring"></div>
              <DeviceMobile weight="fill" className="text-[var(--primary)] w-5 h-5" style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
            </div>
            <div className="text-xs uppercase tracking-widest font-mono mb-2" style={{ color: 'var(--muted)', letterSpacing: '0.1em' }}>Mobile 4G</div>
            <div className="styx-value-badge mb-3">₦20,000</div>
            <div className="text-xs mb-4" style={{ color: 'var(--muted)' }}>per month</div>
            <div className="text-xs leading-relaxed" style={{ color: 'var(--muted-light)' }}>Premium passage. Carrier signals bypass all checkpoints. Charon rarely refuses these.</div>
          </div>

          {/* Datacenter Toll */}
          <div className="card p-6 text-center reveal visible" style={{ animationDelay: '0.2s' }}>
            <div className="styx-coin" style={{ width: '52px', height: '52px', margin: '0 auto 1rem', position: 'relative' }}>
              <div className="styx-coin-ring"></div>
              <HardDrives weight="fill" className="text-[var(--primary)] w-5 h-5" style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
            </div>
            <div className="text-xs uppercase tracking-widest font-mono mb-2" style={{ color: 'var(--muted)', letterSpacing: '0.1em' }}>Datacenter</div>
            <div className="styx-value-badge mb-3">₦3,500</div>
            <div className="text-xs mb-4" style={{ color: 'var(--muted)' }}>per month</div>
            <div className="text-xs leading-relaxed" style={{ color: 'var(--muted-light)' }}>The cheap toll. Speed over stealth. Charon warns you — risk accepted.</div>
          </div>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <div className="section-divider-glow mb-16"></div>
        <div className="text-center mb-12 reveal visible">
          <h2 className="text-3xl font-bold mb-3" style={{ letterSpacing: '-0.02em' }}>Compare Disguises</h2>
          <p className="text-sm max-w-md mx-auto" style={{ color: 'var(--muted)' }}>Every cover has trade-offs. Here&apos;s the full breakdown.</p>
        </div>
        <div className="overflow-x-auto reveal visible">
          <table className="w-full" style={{ minWidth: '560px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th className="px-5 py-4 text-left text-xs uppercase font-mono" style={{ color: 'var(--muted)', letterSpacing: '0.1em' }}></th>
                <th className="px-5 py-4 text-center text-sm font-semibold">ISP</th>
                <th className="px-5 py-4 text-center text-sm font-bold" style={{ color: 'var(--primary)' }}>Residential</th>
                <th className="px-5 py-4 text-center text-sm font-semibold">Mobile 4G</th>
                <th className="px-5 py-4 text-center text-sm font-semibold">Datacenter</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-5 py-4 text-sm font-medium">Anonymity</td>
                <td className="px-5 py-4 text-center text-sm" style={{ color: 'var(--muted-light)' }}>High</td>
                <td className="px-5 py-4 text-center text-sm font-semibold" style={{ color: 'var(--primary)' }}>Very High</td>
                <td className="px-5 py-4 text-center text-sm font-semibold" style={{ color: 'var(--primary)' }}>Highest</td>
                <td className="px-5 py-4 text-center text-sm" style={{ color: 'var(--muted-light)' }}>Low</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-5 py-4 text-sm font-medium">Speed</td>
                <td className="px-5 py-4 text-center text-sm" style={{ color: 'var(--muted-light)' }}>Fast</td>
                <td className="px-5 py-4 text-center text-sm" style={{ color: 'var(--muted-light)' }}>Medium</td>
                <td className="px-5 py-4 text-center text-sm" style={{ color: 'var(--muted-light)' }}>Medium</td>
                <td className="px-5 py-4 text-center text-sm font-semibold" style={{ color: 'var(--primary)' }}>Very Fast</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-5 py-4 text-sm font-medium">Ban Resistance</td>
                <td className="px-5 py-4 text-center text-sm" style={{ color: 'var(--muted-light)' }}>~30 days</td>
                <td className="px-5 py-4 text-center text-sm font-semibold" style={{ color: 'var(--primary)' }}>~45 days</td>
                <td className="px-5 py-4 text-center text-sm font-semibold" style={{ color: 'var(--primary)' }}>~60 days</td>
                <td className="px-5 py-4 text-center text-sm" style={{ color: 'var(--danger)' }}>~7 days</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-5 py-4 text-sm font-medium">Countries</td>
                <td className="px-5 py-4 text-center text-sm" style={{ color: 'var(--muted-light)' }}>45</td>
                <td className="px-5 py-4 text-center text-sm" style={{ color: 'var(--muted-light)' }}>90</td>
                <td className="px-5 py-4 text-center text-sm" style={{ color: 'var(--muted-light)' }}>30</td>
                <td className="px-5 py-4 text-center text-sm font-semibold" style={{ color: 'var(--primary)' }}>120</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-5 py-4 text-sm font-medium">Starting Price</td>
                <td className="px-5 py-4 text-center text-sm font-semibold" style={{ color: 'var(--primary)' }}>₦6,500/mo</td>
                <td className="px-5 py-4 text-center text-sm font-semibold" style={{ color: 'var(--primary)' }}>₦15,000/mo</td>
                <td className="px-5 py-4 text-center text-sm font-semibold" style={{ color: 'var(--primary)' }}>₦20,000/mo</td>
                <td className="px-5 py-4 text-center text-sm font-semibold" style={{ color: 'var(--primary)' }}>₦3,500/mo</td>
              </tr>
              <tr>
                <td className="px-5 py-4 text-sm font-medium">Best For</td>
                <td className="px-5 py-4 text-center text-xs" style={{ color: 'var(--muted)' }}>Sneakers, tickets</td>
                <td className="px-5 py-4 text-center text-xs" style={{ color: 'var(--muted)' }}>Social, scraping</td>
                <td className="px-5 py-4 text-center text-xs" style={{ color: 'var(--muted)' }}>Ad verification</td>
                <td className="px-5 py-4 text-center text-xs" style={{ color: 'var(--muted)' }}>Bulk, speed</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Stats + CTA */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-32">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 max-w-2xl mx-auto mb-20 reveal visible">
          <div className="card p-6 text-center">
            <Globe weight="fill" className="w-[26px] h-[26px] mx-auto mb-3 text-[var(--primary)]" />
            <p className="text-2xl font-bold leading-none mb-1">120+</p>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>Countries</p>
          </div>
          <div className="card p-6 text-center">
            <Rocket weight="fill" className="w-[26px] h-[26px] mx-auto mb-3 text-[var(--primary)]" />
            <p className="text-2xl font-bold leading-none mb-1">Instant</p>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>Delivery</p>
          </div>
          <div className="card p-6 text-center">
            <Target weight="fill" className="w-[26px] h-[26px] mx-auto mb-3 text-[var(--primary)]" />
            <p className="text-2xl font-bold leading-none mb-1">99.9%</p>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>Uptime</p>
          </div>
        </div>

        <div className="text-center reveal visible">
          <h2 className="text-4xl font-bold mb-4" style={{ letterSpacing: '-0.03em' }}>Ready to cross?</h2>
          <p className="mb-10 max-w-md mx-auto text-sm leading-relaxed" style={{ color: 'var(--muted-light)' }}>
            Every operation needs the right cover. Choose yours and deploy today.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link href="/order" className="btn-primary text-base px-10 py-4">Get Started</Link>
            <Link href="/contact" className="btn-outline text-base px-10 py-4">Talk to an Agent</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
