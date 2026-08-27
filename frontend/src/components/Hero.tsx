'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { CaretDown, WhatsappLogo, TelegramLogo, Lightning, Shield, Lock, Globe, Clock, Headset, House, DeviceMobile, HardDrives, Desktop, Check } from '@phosphor-icons/react';

import GlobeErrorBoundary from '@/components/GlobeErrorBoundary';
import LatestBlogPosts from '@/components/LatestBlogPosts';

const GlobeMap = dynamic(() => import('@/components/GlobeMap'), { ssr: false });

const TYPEWRITER_WORDS = ['untraceable', 'unrestricted', 'verified', 'instant', 'anonymous'];

const PRODUCT_TABS: { key: string; label: string; icon: typeof Desktop }[] = [
  { key: 'ALL',   label: 'All',          icon: Globe },
  { key: 'ISP',   label: 'ISP Proxy',    icon: Desktop },
  { key: 'RESIDENTIAL', label: 'Residential', icon: House },
  { key: 'MOBILE',     label: 'Mobile',        icon: DeviceMobile },
  { key: 'DC',         label: 'Datacenter',     icon: HardDrives },
];

const FAQ_DATA = [
  { q: 'How fast is delivery?', a: 'Your proxy credentials are delivered instantly — typically within 3 seconds of payment confirmation. No waiting, no queues.' },
  { q: 'Do I need an account?', a: 'No account required. Simply select your proxy, pay, and receive your credentials immediately via the dashboard or WhatsApp/Telegram.' },
  { q: 'What protocols do you support?', a: 'We support HTTP, HTTPS, SOCKS4, and SOCKS5 protocols. All proxies work with any standard proxy client or browser.' },
  { q: 'What is your refund policy?', a: 'We offer a 24-hour refund policy for valid issues. Contact support within 24 hours of purchase if your proxies are not working as expected.' },
  { q: 'Which countries are available?', a: 'We have proxies available in 120+ countries worldwide. Visit our products page to see specific country availability for each proxy type.' },
];

const FEATURES = [
  { icon: Lightning, title: 'Instant Delivery', desc: 'Proxies ready in under 3 seconds' },
  { icon: Shield, title: 'Anonymous Access', desc: 'No logs, no tracking, no footprint' },
  { icon: Lock, title: 'All Protocols', desc: 'HTTP, HTTPS, SOCKS4 & SOCKS5' },
  { icon: Globe, title: 'Global Coverage', desc: '120+ countries worldwide' },
  { icon: Clock, title: '99.9% Uptime', desc: 'Reliable, consistent performance' },
  { icon: Headset, title: '24/7 AI Support', desc: 'AI-assisted help via chat — anytime' },
];

const PRODUCTS = [
  { icon: Desktop, name: 'ISP Proxy', desc: 'Static residential IPs from ISPs. Fast & reliable.' },
  { icon: House, name: 'Residential', desc: 'Real device IPs from homes worldwide. High anonymity.' },
  { icon: DeviceMobile, name: 'Mobile 4G', desc: '4G/5G mobile IPs. Perfect for social media.' },
  { icon: HardDrives, name: 'Datacenter', desc: 'Cloud server IPs. Fastest speeds, best prices.' },
];

const STATS = [
  { value: '$2M+', label: 'processed', isText: true },
  { value: '15,000+', label: 'customers', isText: true },
  { value: '4.8/5', label: 'rating', isText: true },
  { value: '120+', label: 'countries', isText: true },
];

function AnimatedCounter({ target, suffix = '', duration = 2000 }: { target: number; suffix?: string; duration?: number }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;
          const startTime = performance.now();
          const tick = (now: number) => {
            const progress = Math.min((now - startTime) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(Math.floor(eased * target));
            if (progress < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        }
      },
      { threshold: 0.5 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [target, duration]);

  return <span ref={ref}>{count}{suffix}</span>;
}

function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-[var(--border)] last:border-0">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full py-5 flex items-center justify-between text-left hover:text-[var(--primary)] transition-colors duration-200"
      >
        <span className="font-medium text-[var(--foreground)] pr-4">{q}</span>
        <CaretDown className={`w-5 h-5 shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      <div className={`overflow-hidden transition-all duration-200 ${open ? 'max-h-40 pb-5' : 'max-h-0'}`}>
        <p className="text-[var(--muted)]">{a}</p>
      </div>
    </div>
  );
}

export default function Hero() {
  const [typewriterIdx, setTypewriterIdx] = useState(0);
  const [activeTab, setActiveTab] = useState('ALL');
  const [enabledCountries, setEnabledCountries] = useState<Set<string>>(new Set());
  const heroRef = useRef<HTMLDivElement>(null);

  // Fetch admin-enabled countries from the backend and pass to GlobeMap
  useEffect(() => {
    fetch('/api/countries')
      .then(r => r.json())
      .then(data => {
        const codes = (data.countries ?? []).map((c: { code: string }) => c.code);
        setEnabledCountries(new Set(codes));
      })
      .catch(() => {
        // On error, leave enabledCountries empty — GlobeMap falls back to PRODUCT_COUNTRIES
      });
  }, []);

  useEffect(() => {
    const id = setInterval(() => setTypewriterIdx((i) => (i + 1) % TYPEWRITER_WORDS.length), 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div ref={heroRef} className="min-h-screen overflow-x-hidden">

      {/* ── HERO ── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center pt-20 pb-16">

        {/* Layer 1: Dot grid */}
        <div className="absolute inset-0 hero-bg-grid opacity-100 pointer-events-none" />

        {/* Layer 2: Radial depth glow */}
        <div className="absolute inset-0 hero-bg-rings opacity-100 pointer-events-none" />

        {/* Layer 3: Vignette edges */}
        <div className="absolute inset-0 hero-bg-vignette opacity-100 pointer-events-none" />

        {/* Layer 4: Ambient orbs — centred behind globe */}
        <div className="hero-orb hero-orb-1" />
        <div className="hero-orb hero-orb-2" />
        <div className="hero-orb hero-orb-3" />

        {/* Top accent line */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-20 bg-gradient-to-b from-[var(--primary)] to-transparent opacity-50" />

        <div className="relative z-10 w-full max-w-5xl mx-auto px-6 flex flex-col items-center">

          {/* Globe + tabs */}
          <div className="w-full max-w-xl mx-auto mb-6">
            <GlobeErrorBoundary>
              <GlobeMap productType={activeTab === 'ALL' ? undefined : activeTab} enabledCountries={enabledCountries} />
            </GlobeErrorBoundary>
            {/* Tab switcher — BELOW the globe */}
            <div className="flex items-center justify-center gap-1.5 overflow-x-auto pb-1 md:pb-0 mt-3">
              {PRODUCT_TABS.map(({ key, label, icon: Icon }) => {
                const isActive = activeTab === key;
                return (
                  <button
                    key={key}
                    onClick={() => setActiveTab(key)}
                    className={`flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-all duration-200 border whitespace-nowrap ${
                      isActive
                        ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]'
                        : 'border-[var(--border)] bg-[var(--card)] text-[var(--muted)] hover:border-[var(--primary)]/40 hover:text-[var(--foreground)]'
                    }`}
                  >
                    <Icon size={12} />
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[var(--primary)]/30 bg-[var(--primary)]/5 mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] animate-pulse" />
            <span className="text-xs font-medium tracking-widest uppercase text-[var(--muted)]">
              AI-Powered Proxy Intelligence
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-center text-5xl sm:text-6xl lg:text-7xl xl:text-8xl font-black tracking-tight leading-[1.05] mb-6">
            <span className="text-[var(--foreground)]">Cross the Styx.</span>
            <br />
            <span className="text-[var(--primary)]">Stay {TYPEWRITER_WORDS[typewriterIdx]}</span>
          </h1>

          {/* Sub */}
          <p className="text-center text-lg sm:text-xl text-[var(--muted)] max-w-2xl mb-10 leading-relaxed">
            ISP, Residential, Mobile &amp; Datacenter proxies — delivered in seconds.
            <br className="hidden sm:block" />Leave no footprint.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center gap-3 mb-6 w-full sm:w-auto">
            <Link href="/products"
              className="w-full sm:w-auto min-w-[200px] px-8 py-4 rounded-xl border border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] text-[var(--foreground)] font-semibold text-center card-depth transition-all duration-200">
              View Products
            </Link>
            <Link href="/order"
              className="w-full sm:w-auto min-w-[200px] px-8 py-4 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-black text-center transition-all duration-200 hover:shadow-[0_0_30px_rgba(10,210,90,0.3)]">
              Get Instant
            </Link>
          </div>

          {/* WhatsApp + Telegram */}
          <div className="flex flex-col sm:flex-row items-center gap-3 mb-6 w-full sm:w-auto">
            <a href="https://wa.me/2347032981049" target="_blank" rel="noopener noreferrer"
              className="w-full sm:w-auto min-w-[200px] flex items-center justify-center gap-2.5 px-8 py-4 rounded-xl bg-[#25D366] hover:bg-[#1fb855] text-white font-black text-center text-base transition-all duration-200 shadow-[0_4px_20px_rgba(37,211,102,0.35)] hover:shadow-[0_6px_28px_rgba(37,211,102,0.5)]">
              <WhatsappLogo className="w-5 h-5" />
              WhatsApp
            </a>
            <a href="https://t.me/StyxproxyBot" target="_blank" rel="noopener noreferrer"
              className="w-full sm:w-auto min-w-[200px] flex items-center justify-center gap-2.5 px-8 py-4 rounded-xl bg-[#0088cc] hover:bg-[#0077aa] text-white font-black text-center text-base transition-all duration-200 shadow-[0_4px_20px_rgba(0,136,204,0.35)] hover:shadow-[0_6px_28px_rgba(0,136,204,0.5)]">
              <TelegramLogo className="w-5 h-5" />
              Telegram
            </a>
          </div>

          {/* Trust indicators */}
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[var(--muted)] text-xs font-medium tracking-wide">
            {[
              { icon: Lightning, t: 'Instant Delivery' },
              { icon: Shield, t: 'No Account Needed' },
              { icon: Check, t: 'Verified Proxies' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <item.icon className="w-3.5 h-3.5 text-[var(--primary)]" weight="bold" />
                {item.t}
              </div>
            ))}
          </div>
        </div>

      </section>

      {/* Scroll indicator */}
      <div className="flex flex-col items-center gap-2 py-8">
        <span className="text-[10px] tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">Scroll</span>
        <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
      </div>

      {/* ── STATS STRIP ── */}
      <section className="border-y border-[var(--border)] bg-[var(--surface)]">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {STATS.map((stat, i) => (
              <div key={i} className="text-center">
                <div className="text-3xl sm:text-4xl lg:text-5xl font-black text-[var(--foreground)] tracking-tight">
                  {stat.value}
                </div>
                <div className="text-xs text-[var(--muted)] mt-2 font-medium tracking-widest uppercase">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section divider */}
      <div className="section-divider-glow" />

      {/* ── FEATURES ── */}
      <section className="py-24 lg:py-32 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16">
            <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">What you get</p>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight">
              Built for those who
              <br />
              <span className="text-[var(--muted)]">move in silence.</span>
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => (
              <div key={i}
                className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth">
                <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-5">
                  {f.icon && <f.icon className="w-6 h-6 text-[var(--primary)]" />}
                </div>
                <h3 className="text-base font-bold text-[var(--foreground)] mb-2">{f.title}</h3>
                <p className="text-sm text-[var(--muted)] leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section divider */}
      <div className="section-divider" />

      {/* ── HOW IT WORKS ── */}
      <section className="py-24 lg:py-32 px-6 bg-[var(--surface)]">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16">
            <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">Simple process</p>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight">
              Up and running
              <br />
              <span className="text-[var(--muted)]">in 3 steps.</span>
            </h2>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {[
              { step: '01', title: 'Choose Your Proxy', desc: 'Select ISP, Residential, Mobile 4G, or Datacenter. Pick your country and plan.' },
              { step: '02', title: 'Pay & Get Credentials', desc: 'Pay with card or bank transfer. Your proxy details arrive instantly.' },
              { step: '03', title: 'Start Using', desc: 'Configure in your bot, scraper, or browser. Works immediately.' },
            ].map((item, i) => (
              <div key={i}
                className="relative p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth">
                <div className="absolute -top-3 left-8 px-3 py-1 rounded-full bg-[var(--primary)] text-black text-xs font-black tracking-wider">
                  {item.step}
                </div>
                <div className="pt-2">
                  <h3 className="text-lg font-bold text-[var(--foreground)] mb-3">{item.title}</h3>
                  <p className="text-sm text-[var(--muted)] leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section divider */}
      <div className="section-divider" />

      {/* ── PRODUCTS ── */}
      <section className="py-24 lg:py-32 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16">
            <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">Proxy types</p>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight">
              Four ways to
              <br />
              <span className="text-[var(--muted)]">stay invisible.</span>
            </h2>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {PRODUCTS.map((p, i) => (
              <div key={i}
                className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth">
                <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-5">
                  {p.icon && <p.icon className="w-6 h-6 text-[var(--primary)]" />}
                </div>
                <h3 className="text-base font-bold text-[var(--foreground)] mb-2">{p.name}</h3>
                <p className="text-xs text-[var(--muted)] leading-relaxed mb-4">{p.desc}</p>
                <Link href="/products" className="text-xs font-bold text-[var(--primary)] hover:underline tracking-wide">
                  Learn more &rarr;
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section divider */}
      <div className="section-divider-glow" />

      {/* ── SOCIAL PROOF ── */}
      <section className="py-20 px-6 bg-[var(--surface)] border-y border-[var(--border)]">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm text-[var(--muted)] mb-10 font-medium tracking-wide">
            Trusted by developers and businesses worldwide
          </p>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {STATS.map((item, i) => (
              <div key={i} className="text-center">
                <div className="text-2xl sm:text-3xl font-black text-[var(--foreground)]">{item.value}</div>
                <div className="text-xs text-[var(--muted)] mt-1 uppercase tracking-wider font-medium">{item.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section divider */}
      <div className="section-divider" />

      {/* ── LATEST FROM THE BLOG ── */}
      <LatestBlogPosts />

      {/* Section divider */}
      <div className="section-divider" />

      {/* ── FAQ ── */}
      <section className="py-24 lg:py-32 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="mb-12">
            <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">FAQ</p>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--foreground)]">Questions?</h2>
          </div>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] px-6">
            {FAQ_DATA.map((item, i) => <FAQItem key={i} q={item.q} a={item.a} />)}
          </div>
        </div>
      </section>

      {/* Section divider */}
      <div className="section-divider" />

      {/* ── CTA ── */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] mb-5">
            Ready to cross the Styx?
          </h2>
          <p className="text-[var(--muted)] mb-10 text-lg">Start in seconds. No signup required.</p>
          <Link href="/order"
            className="inline-block px-12 py-5 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-black text-lg transition-all duration-200 hover:shadow-[0_0_40px_rgba(10,210,90,0.35)]">
            Get Instant
          </Link>
        </div>
      </section>

    </div>
  );
}
