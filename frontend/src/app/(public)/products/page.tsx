'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { Globe, House, HardDrives, DeviceMobile, Lightning, Clock, Check, X } from '@phosphor-icons/react';

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

export default function ProductsPage() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [selectedMission, setSelectedMission] = useState<string | null>(null);
  const [visibleCards, setVisibleCards] = useState<Set<string>>(new Set());
  const cardRefs = useRef<Map<string, HTMLElement>>(new Map());

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

  const toggleExpand = (key: string) => {
    setExpanded(expanded === key ? null : key);
  };

  const [briefingDone, setBriefingDone] = useState(false);
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
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 256 256" fill="currentColor">
                <path d="M205.66 194.34a8 8 0 0 1-11.32 11.32L128 139.31l-66.34 66.35a8 8 0 0 1-11.32-11.32L116.69 128 50.34 61.66a8 8 0 0 1 11.32-11.32L128 116.69l66.34-66.35a8 8 0 0 1 11.32 11.32L139.31 128Z"/>
              </svg>
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
                { type: 'ISP', label: 'Speed Operations', icon: 'globe', desc: 'Sneaker bots, ticket drops, automation — where latency is the enemy.' },
                { type: 'RESIDENTIAL', label: 'Identity Operations', icon: 'house', desc: 'Social media, scraping, brand monitoring — maximum authenticity required.' },
                { type: 'MOBILE', label: 'Verification Ops', icon: 'mobile', desc: 'Ad verification, app testing, mobile campaigns — carrier-level stealth.' },
                { type: 'DATACENTER', label: 'Bulk Operations', icon: 'server', desc: 'SEO tools, traffic routing, data collection — speed over stealth.' },
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
                      {m.type === 'ISP' && (
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 256 256" className="text-[var(--primary)]">
                          <path fill="currentColor" d="M128 24a104 104 0 1 0 104 104A104.11 104.11 0 0 0 128 24Zm0 192a88 88 0 1 1 88-88 88.1 88.1 0 0 1-88 88Zm40-88a40 40 0 1 1-40-40 40 40 0 0 1 40 40Zm-64 0a24 24 0 1 0 24-24 24 24 0 0 0-24 24Z"/>
                        </svg>
                      )}
                      {m.type === 'RESIDENTIAL' && (
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 256 256" className="text-[var(--primary)]">
                          <path fill="currentColor" d="M240 208h-24v-56a16 16 0 0 0-16-16h-32V96a16 16 0 0 0-24.53-12.41l-32 24L75.31 82.41 48 95.29V136H24a16 16 0 0 0-16 16v56H16a8 8 0 0 0 0 16h224a8 8 0 0 0 0-16Z"/>
                        </svg>
                      )}
                      {m.type === 'MOBILE' && (
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 256 256" className="text-[var(--primary)]">
                          <path fill="currentColor" d="M176 16H80a24 24 0 0 0-24 24v176a24 24 0 0 0 24 24h96a24 24 0 0 0 24-24V40a24 24 0 0 0-24-24ZM80 32h96a8 8 0 0 1 8 8v128H72V40a8 8 0 0 1 8-8Zm96 192H80a8 8 0 0 1-8-8v-16h112v16a8 8 0 0 1-8 8Z"/>
                        </svg>
                      )}
                      {m.type === 'DATACENTER' && (
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 256 256" className="text-[var(--primary)]">
                          <path fill="currentColor" d="M232 96c0-30.88-22.51-56.42-52.07-59.83a8 8 0 0 0-3.86 15.66C194.45 54.06 216 78.34 216 96a60.07 60.07 0 0 1-46.07 57.77A15.92 15.92 0 0 0 176 160v40H96v-40a16 16 0 0 0-6.07-12.23A60.07 60.07 0 0 1 40 96c0-17.66 21.55-41.94 39.93-44.17a8 8 0 0 0-3.86-15.66C47.51 39.58 25 65.12 25 96c0 23.47 11.72 44.26 30 56.68V208H48a16 16 0 0 0-16 16v16a16 16 0 0 0 16 16h160a16 16 0 0 0 16-16v-16a16 16 0 0 0-16-16h-7v-55.32c18.28-12.42 30-33.21 30-56.68Z"/>
                        </svg>
                      )}
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
          <div className="flex flex-wrap justify-center gap-3">
            {[
              { label: 'Speed Ops', key: 'ISP' },
              { label: 'Identity Ops', key: 'RESIDENTIAL' },
              { label: 'Verification', key: 'MOBILE' },
              { label: 'Bulk Ops', key: 'DATACENTER' },
            ].map((mission) => (
              <button
                key={mission.key}
                onClick={() => handleMissionClick(mission.key)}
                className={`px-5 py-2.5 rounded-full text-sm font-medium transition-all duration-200 border ${
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
                    {product.key === 'ISP' && (
                      <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 256 256" className="text-[var(--primary)]">
                        <path fill="currentColor" d="M128 24a104 104 0 1 0 104 104A104.11 104.11 0 0 0 128 24Zm0 192a88 88 0 1 1 88-88 88.1 88.1 0 0 1-88 88Zm40-88a40 40 0 1 1-40-40 40 40 0 0 1 40 40Zm-64 0a24 24 0 1 0 24-24 24 24 0 0 0-24 24Z"/>
                      </svg>
                    )}
                    {product.key === 'RESIDENTIAL' && (
                      <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 256 256" className="text-[var(--primary)]">
                        <path fill="currentColor" d="M240 208h-24v-56a16 16 0 0 0-16-16h-32V96a16 16 0 0 0-24.53-12.41l-32 24L75.31 82.41 48 95.29V136H24a16 16 0 0 0-16 16v56H16a8 8 0 0 0 0 16h224a8 8 0 0 0 0-16Z"/>
                      </svg>
                    )}
                    {product.key === 'MOBILE' && (
                      <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 256 256" className="text-[var(--primary)]">
                        <path fill="currentColor" d="M176 16H80a24 24 0 0 0-24 24v176a24 24 0 0 0 24 24h96a24 24 0 0 0 24-24V40a24 24 0 0 0-24-24ZM80 32h96a8 8 0 0 1 8 8v128H72V40a8 8 0 0 1 8-8Zm96 192H80a8 8 0 0 1-8-8v-16h112v16a8 8 0 0 1-8 8Z"/>
                      </svg>
                    )}
                    {product.key === 'DATACENTER' && (
                      <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 256 256" className="text-[var(--primary)]">
                        <path fill="currentColor" d="M232 96c0-30.88-22.51-56.42-52.07-59.83a8 8 0 0 0-3.86 15.66C194.45 54.06 216 78.34 216 96a60.07 60.07 0 0 1-46.07 57.77A15.92 15.92 0 0 0 176 160v40H96v-40a16 16 0 0 0-6.07-12.23A60.07 60.07 0 0 1 40 96c0-17.66 21.55-41.94 39.93-44.17a8 8 0 0 0-3.86-15.66C47.51 39.58 25 65.12 25 96c0 23.47 11.72 44.26 30 56.68V208H48a16 16 0 0 0-16 16v16a16 16 0 0 0 16 16h160a16 16 0 0 0 16-16v-16a16 16 0 0 0-16-16h-7v-55.32c18.28-12.42 30-33.21 30-56.68Z"/>
                      </svg>
                    )}
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
                <div>
                  <span className="text-xs font-mono uppercase tracking-widest mb-2 block text-gray-500">Best for</span>
                  <div className="bestfor-strip overflow-x-auto">
                    {product.bestFor.map((item) => (
                      <span key={item} className="bestfor-tag">{item}</span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right: Visual metrics */}
              <div className="lg:w-72 flex-shrink-0">
                <div className="grid grid-cols-2 gap-4">
                  {/* Radar */}
                  <div className="p-4 rounded-xl bg-green-500/03 border border-[var(--border)]">
                    <p className="text-xs uppercase tracking-widest font-mono mb-3 text-gray-500">Anonymity Radar</p>
                    <div className="radar-chart">
                      <svg viewBox="0 0 160 160">
                        <polygon points="80,18 124,46 124,114 80,142 36,114 36,46" fill="none" stroke="rgba(10,210,90,0.08)" strokeWidth="1"/>
                        <polygon points="80,34 112,55 112,105 80,126 48,105 48,55" fill="none" stroke="rgba(10,210,90,0.08)" strokeWidth="1"/>
                        <polygon points="80,50 100,63 100,97 80,110 60,97 60,63" fill="none" stroke="rgba(10,210,90,0.06)" strokeWidth="1"/>
                        <line x1="80" y1="80" x2="80" y2="18" stroke="rgba(10,210,90,0.08)" strokeWidth="1"/>
                        <line x1="80" y1="80" x2="124" y2="46" stroke="rgba(10,210,90,0.08)" strokeWidth="1"/>
                        <line x1="80" y1="80" x2="124" y2="114" stroke="rgba(10,210,90,0.08)" strokeWidth="1"/>
                        <line x1="80" y1="80" x2="80" y2="142" stroke="rgba(10,210,90,0.08)" strokeWidth="1"/>
                        <line x1="80" y1="80" x2="36" y2="114" stroke="rgba(10,210,90,0.08)" strokeWidth="1"/>
                        <line x1="80" y1="80" x2="36" y2="46" stroke="rgba(10,210,90,0.08)" strokeWidth="1"/>
                        <polygon
                          className="radar-polygon"
                          points={getRadarPoints(product.radar)}
                          fill="rgba(10,210,90,0.12)"
                          stroke={product.statusDot === 'warn' ? 'var(--error)' : 'var(--primary)'}
                          strokeWidth="1.5"
                        />
                        {product.radar.map((v, i) => {
                          const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2;
                          const radius = (v / 140) * 60 + 20;
                          const cx = 80 + radius * Math.cos(angle);
                          const cy = 80 + radius * Math.sin(angle);
                          return <circle key={i} cx={cx} cy={cy} r="3" fill={product.statusDot === 'warn' ? 'var(--error)' : 'var(--primary)'} />;
                        })}
                        <text x="80" y="10" textAnchor="middle" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">SPD</text>
                        <text x="130" y="44" textAnchor="start" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">DET</text>
                        <text x="130" y="118" textAnchor="start" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">GEO</text>
                        <text x="80" y="158" textAnchor="middle" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">BAN</text>
                        <text x="26" y="118" textAnchor="end" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">CST</text>
                        <text x="26" y="44" textAnchor="end" fill="rgba(245,245,245,0.4)" fontSize="8" fontFamily="monospace">STB</text>
                      </svg>
                    </div>
                  </div>

                  {/* Gauge */}
                  <div className="p-4 rounded-xl bg-green-500/03 border border-[var(--border)]">
                    <p className="text-xs uppercase tracking-widest font-mono mb-3 text-gray-500">Cover Life</p>
                    <div className="gauge-wrap">
                      <svg className="gauge-svg" viewBox="0 0 120 80">
                        <path className="gauge-track" d="M 15 65 A 45 45 0 0 1 105 65"/>
                        <path
                          className="gauge-fill"
                          d="M 15 65 A 45 45 0 0 1 105 65"
                          stroke={product.gauge.color === 'warning' ? 'var(--warning)' : product.gauge.color === 'danger' ? 'var(--error)' : 'var(--primary)'}
                          strokeDasharray="141"
                          strokeDashoffset={141 * (1 - (product.gauge.color === 'warning' ? 0.4 : product.gauge.color === 'danger' ? 0.2 : 0.75))}
                        />
                        <text x="60" y="58" textAnchor="middle" className="gauge-text" style={{ fontSize: '13px', color: product.gauge.color === 'warning' ? 'var(--warning)' : product.gauge.color === 'danger' ? 'var(--error)' : 'var(--primary-light)' }}>{product.gauge.value}</text>
                        <text x="60" y="72" textAnchor="middle" className="gauge-text" style={{ fontSize: '8px', fill: 'var(--muted)' }}>TYPICAL</text>
                      </svg>
                    </div>
                    <div className="grid grid-cols-3 gap-1 mt-3 text-center">
                      <div>
                        <div className="text-xs font-bold" style={{ color: product.gauge.color === 'warning' ? 'var(--warning)' : product.gauge.color === 'danger' ? 'var(--error)' : 'var(--primary)' }}>{product.gauge.typical}</div>
                        <div className="text-xs text-gray-500">Typical</div>
                      </div>
                      <div>
                        <div className="text-xs font-bold" style={{ color: product.gauge.color === 'danger' ? 'var(--error)' : 'var(--warning)' }}>{product.gauge.hot}</div>
                        <div className="text-xs text-gray-500">Hot</div>
                      </div>
                      <div>
                        <div className="text-xs font-bold text-[var(--primary)]">{product.gauge.lowRisk}</div>
                        <div className="text-xs text-gray-500">Low risk</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Loadout stats */}
                <div className="mt-4 p-4 rounded-xl bg-green-500/03 border border-[var(--border)]">
                  <p className="text-xs uppercase tracking-widest font-mono mb-3 text-gray-500">Loadout Stats</p>
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
                      <span className="text-xs font-mono" style={{ color: product.statusDot === 'warn' ? 'var(--error)' : 'var(--primary)', minWidth: '28px', textAlign: 'right' }}>{product.stats.detection}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Speed</span>
                      <div className="stat-bar-wrap">
                        <div className="stat-bar-fill" style={{ width: `${product.stats.speed}%` }} />
                      </div>
                      <span className="text-xs font-mono text-[var(--primary)]" style={{ minWidth: '28px', textAlign: 'right' }}>{product.stats.speed}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Geo</span>
                      <div className="stat-bar-wrap">
                        <div className="stat-bar-fill" style={{ width: `${product.stats.geo}%` }} />
                      </div>
                      <span className="text-xs font-mono text-[var(--primary)]" style={{ minWidth: '28px', textAlign: 'right' }}>{product.stats.geo}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Cost</span>
                      <div className="stat-bar-wrap">
                        <div className="stat-bar-fill" style={{ width: `${product.stats.cost}%` }} />
                      </div>
                      <span className="text-xs font-mono text-[var(--primary)]" style={{ minWidth: '28px', textAlign: 'right' }}>{product.stats.cost}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Price row */}
            <div className="mt-5 pt-4 flex flex-wrap items-center gap-4 border-t border-[var(--border)]">
              <div>
                <span className="text-xs font-mono uppercase tracking-widest text-gray-500">Starting from</span>
                <div className="text-2xl font-bold mt-1 text-[var(--primary)]">
                  {product.price}
                  <span className="text-sm font-normal text-gray-500">/{product.priceUnit.split(' ')[1] || 'mo'}</span>
                </div>
              </div>
              <Link href="/order" className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-all duration-200">
                Deploy Cover
              </Link>
              <button
                onClick={() => toggleExpand(product.key)}
                className="btn-ghost flex items-center gap-2"
                aria-expanded={expanded === product.key}
                aria-controls={`expand-${product.key}`}
              >
                What they see
                <span className={`expand-icon ${expanded === product.key ? 'open' : ''}`}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 256 256" fill="currentColor">
                    <path d="M213.66 101.66l-80 80a8 8 0 0 1-11.32 0l-80-80a8 8 0 0 1 11.32-11.32L128 164.69l74.34-74.35a8 8 0 0 1 11.32 11.32Z"/>
                  </svg>
                </span>
              </button>
              <div className="text-xs ml-auto hidden lg:block text-gray-500">{product.countries} countries available</div>
            </div>

            {/* Expand: What They See */}
            <div className={`expand-body mt-6 ${expanded === product.key ? 'open' : ''}`} id={`expand-${product.key}`}>
              <div className="p-6 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                <p className="text-xs uppercase tracking-widest font-mono mb-5 text-gray-500">Adversary Detection View</p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {product.threatView.map((threat, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl"
                      style={{
                        background: threat.risk === 'High' ? 'rgba(239,68,68,0.04)' : threat.risk === 'Medium' ? 'rgba(245,158,11,0.04)' : 'rgba(10,210,90,0.04)',
                        border: `1px solid ${threat.risk === 'High' ? 'rgba(239,68,68,0.12)' : threat.risk === 'Medium' ? 'rgba(245,158,11,0.12)' : 'rgba(10,210,90,0.12)'}`
                      }}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-semibold">{threat.platform}</span>
                        <span
                          className="text-xs"
                          style={{
                            color: threat.risk === 'High' ? 'var(--error)' : threat.risk === 'Medium' ? 'var(--warning)' : 'var(--primary)'
                          }}
                        >
                          {threat.risk} risk
                        </span>
                      </div>
                      <div className="threat-bar-seg mb-2">
                        {[...Array(5)].map((_, i) => (
                          <span
                            key={i}
                            className={`threat-seg ${
                              i < threat.segments
                                ? threat.risk === 'High' ? 'lit-red'
                                  : threat.risk === 'Medium' ? 'lit-yellow'
                                  : 'lit-green'
                                : ''
                            }`}
                          />
                        ))}
                      </div>
                      <p className="text-xs leading-relaxed text-gray-400">{threat.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charon's Toll Pricing */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <div className="section-divider-glow mb-20" />

        {/* Header */}
        <div className="text-center mb-16 reveal">
          <div className="styx-coin">
            <div className="styx-coin-ring" />
            <div className="styx-coin-ring" />
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 256 256" className="text-[var(--primary)]">
              <path fill="currentColor" d="M232 96c0-30.88-22.51-56.42-52.07-59.83a8 8 0 0 0-3.86 15.66C194.45 54.06 216 78.34 216 96a60.07 60.07 0 0 1-46.07 57.77A15.92 15.92 0 0 0 176 160v40H96v-40a16 16 0 0 0-6.07-12.23A60.07 60.07 0 0 1 40 96c0-17.66 21.55-41.94 39.93-44.17a8 8 0 0 0-3.86-15.66C47.51 39.58 25 65.12 25 96c0 23.47 11.72 44.26 30 56.68V208H48a16 16 0 0 0-16 16v16a16 16 0 0 0 16 16h160a16 16 0 0 0 16-16v-16a16 16 0 0 0-16-16h-7v-55.32c18.28-12.42 30-33.21 30-56.68Z"/>
            </svg>
          </div>
          <p className="text-xs uppercase tracking-widest font-mono mb-4 text-gray-500">The Ferryman&apos;s Price</p>
          <h2 className="text-4xl font-bold mb-4 tracking-tight">Charon&apos;s Toll</h2>
          <p className="text-base max-w-lg mx-auto leading-relaxed text-gray-300">
            No toll, no passage. Each disguise carries its own price — the cost of crossing unseen.
          </p>
        </div>

        {/* Toll cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-12">
          {PRODUCTS.map((product, idx) => (
            <div
              key={product.key}
              className={`card-depth p-6 text-center reveal ${product.featured ? 'card-depth-primary' : ''}`}
              style={{ animationDelay: `${idx * 0.05}s` }}
            >
              {product.featured && (
                <div className="absolute -top-2.5 left-1/2 -translate-x-1/2">
                  <span className="text-[10px] font-bold px-3 py-0.5 rounded-full bg-[var(--primary)] text-black">Most Chosen</span>
                </div>
              )}
              <div className="styx-coin" style={{ width: '52px', height: '52px', margin: product.featured ? '0.5rem auto 1rem' : '0 auto 1rem' }}>
                <div className="styx-coin-ring" />
                {product.featured && <div className="styx-coin-ring" />}
                {product.key === 'ISP' && (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 256 256" className="text-[var(--primary)]">
                    <path fill="currentColor" d="M128 24a104 104 0 1 0 104 104A104.11 104.11 0 0 0 128 24Zm0 192a88 88 0 1 1 88-88 88.1 88.1 0 0 1-88 88Zm40-88a40 40 0 1 1-40-40 40 40 0 0 1 40 40Zm-64 0a24 24 0 1 0 24-24 24 24 0 0 0-24 24Z"/>
                  </svg>
                )}
                {product.key === 'RESIDENTIAL' && (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 256 256" className="text-[var(--primary)]">
                    <path fill="currentColor" d="M240 208h-24v-56a16 16 0 0 0-16-16h-32V96a16 16 0 0 0-24.53-12.41l-32 24L75.31 82.41 48 95.29V136H24a16 16 0 0 0-16 16v56H16a8 8 0 0 0 0 16h224a8 8 0 0 0 0-16Z"/>
                  </svg>
                )}
                {product.key === 'MOBILE' && (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 256 256" className="text-[var(--primary)]">
                    <path fill="currentColor" d="M176 16H80a24 24 0 0 0-24 24v176a24 24 0 0 0 24 24h96a24 24 0 0 0 24-24V40a24 24 0 0 0-24-24ZM80 32h96a8 8 0 0 1 8 8v128H72V40a8 8 0 0 1 8-8Zm96 192H80a8 8 0 0 1-8-8v-16h112v16a8 8 0 0 1-8 8Z"/>
                  </svg>
                )}
                {product.key === 'DATACENTER' && (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 256 256" className="text-[var(--primary)]">
                    <path fill="currentColor" d="M232 96c0-30.88-22.51-56.42-52.07-59.83a8 8 0 0 0-3.86 15.66C194.45 54.06 216 78.34 216 96a60.07 60.07 0 0 1-46.07 57.77A15.92 15.92 0 0 0 176 160v40H96v-40a16 16 0 0 0-6.07-12.23A60.07 60.07 0 0 1 40 96c0-17.66 21.55-41.94 39.93-44.17a8 8 0 0 0-3.86-15.66C47.51 39.58 25 65.12 25 96c0 23.47 11.72 44.26 30 56.68V208H48a16 16 0 0 0-16 16v16a16 16 0 0 0 16 16h160a16 16 0 0 0 16-16v-16a16 16 0 0 0-16-16h-7v-55.32c18.28-12.42 30-33.21 30-56.68Z"/>
                  </svg>
                )}
              </div>
              <div className="text-xs uppercase tracking-widest font-mono mb-2 text-gray-500">{product.name}</div>
              <div className="styx-value-badge mb-3">{product.price}</div>
              <div className="text-xs mb-4 text-gray-500">{product.priceUnit}</div>
              <div className="text-xs leading-relaxed text-gray-400">
                {product.key === 'ISP' && 'The minimum toll. Fast passage, moderate detection risk. Charon\'s seen these IPs before.'}
                {product.key === 'RESIDENTIAL' && 'Two coins for true passage. Charon\'s favourite — these IPs belong to real souls.'}
                {product.key === 'MOBILE' && 'Premium passage. Carrier signals bypass all checkpoints. Charon rarely refuses these.'}
                {product.key === 'DATACENTER' && 'The cheap toll. Speed over stealth. Charon warns you — risk accepted.'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Comparison Table */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <div className="section-divider-glow mb-16" />
        <div className="text-center mb-12 reveal">
          <h2 className="text-3xl font-bold mb-3 tracking-tight">Compare Disguises</h2>
          <p className="text-sm max-w-md mx-auto text-gray-500">Every cover has trade-offs. Here&apos;s the full breakdown.</p>
        </div>
        <div className="overflow-x-auto reveal">
          <table className="w-full" style={{ minWidth: '560px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th className="px-5 py-4 text-left text-xs uppercase font-mono text-gray-500"></th>
                <th className="px-5 py-4 text-center text-sm font-semibold">ISP</th>
                <th className="px-5 py-4 text-center text-sm font-bold text-[var(--primary)]">Residential</th>
                <th className="px-5 py-4 text-center text-sm font-semibold">Mobile 4G</th>
                <th className="px-5 py-4 text-center text-sm font-semibold">Datacenter</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-5 py-4 text-sm font-medium">Anonymity</td>
                <td className="px-5 py-4 text-center text-sm text-gray-400">High</td>
                <td className="px-5 py-4 text-center text-sm font-semibold text-[var(--primary)]">Very High</td>
                <td className="px-5 py-4 text-center text-sm font-semibold text-[var(--primary)]">Highest</td>
                <td className="px-5 py-4 text-center text-sm text-gray-400">Low</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-5 py-4 text-sm font-medium">Speed</td>
                <td className="px-5 py-4 text-center text-sm text-gray-400">Fast</td>
                <td className="px-5 py-4 text-center text-sm text-gray-400">Medium</td>
                <td className="px-5 py-4 text-center text-sm text-gray-400">Medium</td>
                <td className="px-5 py-4 text-center text-sm font-semibold text-[var(--primary)]">Very Fast</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-5 py-4 text-sm font-medium">Ban Resistance</td>
                <td className="px-5 py-4 text-center text-sm text-gray-400">~30 days</td>
                <td className="px-5 py-4 text-center text-sm font-semibold text-[var(--primary)]">~45 days</td>
                <td className="px-5 py-4 text-center text-sm font-semibold text-[var(--primary)]">~60 days</td>
                <td className="px-5 py-4 text-center text-sm text-red-500">~7 days</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-5 py-4 text-sm font-medium">Countries</td>
                <td className="px-5 py-4 text-center text-sm text-gray-400">45</td>
                <td className="px-5 py-4 text-center text-sm text-gray-400">90</td>
                <td className="px-5 py-4 text-center text-sm text-gray-400">30</td>
                <td className="px-5 py-4 text-center text-sm font-semibold text-[var(--primary)]">120</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-5 py-4 text-sm font-medium">Starting Price</td>
                <td className="px-5 py-4 text-center text-sm font-semibold text-[var(--primary)]">₦6,500/mo</td>
                <td className="px-5 py-4 text-center text-sm font-semibold text-[var(--primary)]">₦15,000/mo</td>
                <td className="px-5 py-4 text-center text-sm font-semibold text-[var(--primary)]">₦20,000/mo</td>
                <td className="px-5 py-4 text-center text-sm font-semibold text-[var(--primary)]">₦3,500/mo</td>
              </tr>
              <tr>
                <td className="px-5 py-4 text-sm font-medium">Best For</td>
                <td className="px-5 py-4 text-center text-xs text-gray-500">Sneakers, tickets</td>
                <td className="px-5 py-4 text-center text-xs text-gray-500">Social, scraping</td>
                <td className="px-5 py-4 text-center text-xs text-gray-500">Ad verification</td>
                <td className="px-5 py-4 text-center text-xs text-gray-500">Bulk, speed</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Stats + CTA */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="section-divider-glow mb-16" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 max-w-2xl mx-auto mb-20 reveal">
          <div className="card-depth p-6 text-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" className="mx-auto mb-3 text-[var(--primary)]" viewBox="0 0 256 256">
              <path fill="currentColor" d="M128 24a104 104 0 1 0 104 104A104.11 104.11 0 0 0 128 24Zm0 192a88 88 0 1 1 88-88 88.1 88.1 0 0 1-88 88Z"/>
            </svg>
            <p className="text-2xl font-bold leading-none mb-1">120+</p>
            <p className="text-xs text-gray-500">Countries</p>
          </div>
          <div className="card-depth p-6 text-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" className="mx-auto mb-3 text-[var(--primary)]" viewBox="0 0 256 256">
              <path fill="currentColor" d="M215.79 118.17a8 8 0 0 0-5-5.66L153.18 90.9l14.66-73.33a8 8 0 0 0-13.69-7l-112 120a8 8 0 0 0 3 13l57.63 21.61-76.8 61.43a8 8 0 0 0 3.63 13.71L128 248l110.21-66.92a8 8 0 0 0 3.58-13.91Z"/>
            </svg>
            <p className="text-2xl font-bold leading-none mb-1">Instant</p>
            <p className="text-xs text-gray-500">Delivery</p>
          </div>
          <div className="card-depth p-6 text-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" className="mx-auto mb-3 text-[var(--primary)]" viewBox="0 0 256 256">
              <path fill="currentColor" d="M128 24a104 104 0 1 0 104 104A104.11 104.11 0 0 0 128 24Zm0 192a88 88 0 1 1 88-88 88.1 88.1 0 0 1-88 88Zm40-88a40 40 0 1 1-40-40 40 40 0 0 1 40 40Z"/>
            </svg>
            <p className="text-2xl font-bold leading-none mb-1">99.9%</p>
            <p className="text-xs text-gray-500">Uptime</p>
          </div>
        </div>

        <div className="text-center reveal">
          <h2 className="text-4xl font-bold mb-4 tracking-tight">Ready to cross?</h2>
          <p className="mb-10 max-w-md mx-auto text-sm leading-relaxed text-gray-300">
            Every operation needs the right cover. Choose yours and deploy today.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link href="/order" className="inline-block px-10 py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-all duration-200 text-base">
              Get Started
            </Link>
            <Link href="/contact" className="inline-block px-10 py-4 border-2 border-[var(--primary)]/40 text-[var(--primary)] font-semibold rounded-xl hover:bg-[var(--primary)]/10 transition-all duration-200 text-base">
              Talk to an Agent
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
