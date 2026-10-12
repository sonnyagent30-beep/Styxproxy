'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { CaretDown, WhatsappLogo, TelegramLogo, Lightning, Shield, Lock, Globe, Clock, Headset, House, DeviceMobile, HardDrives, Desktop, Check } from '@phosphor-icons/react';

import GlobeErrorBoundary from '@/components/GlobeErrorBoundary';
import { reportError } from '@/lib/sentry';

const GlobeMap = dynamic(() => import('@/components/GlobeMap'), { ssr: false });

const TYPEWRITER_WORDS = ['unknown', 'unrestricted', 'verified', 'instant', 'anonymous'];

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
  { q: 'Which countries are available?', a: 'Visit our products page to see current country availability for each proxy type.' },
];

const FEATURES = [
  { icon: Lightning, title: 'Instant Delivery', desc: 'Proxies ready in under 3 seconds' },
  { icon: Shield, title: 'Anonymous Access', desc: 'No account, no identity, no log of what you do' },
  { icon: Lock, title: 'All Protocols', desc: 'HTTP, HTTPS, SOCKS4 & SOCKS5' },
  { icon: Globe, title: 'Global Coverage', desc: 'Proxies across Africa, Europe, the Americas and Asia' },
  { icon: Clock, title: 'Always-On Network', desc: 'Monitored around the clock' },
  { icon: Headset, title: '24/7 AI Support', desc: 'AI-assisted help via chat — anytime' },
];

const PRODUCTS = [
  { icon: Desktop, name: 'ISP Proxy', desc: 'Static residential IPs from ISPs. Fast & reliable.' },
  { icon: House, name: 'Residential', desc: 'Real device IPs from homes worldwide. High anonymity.' },
  { icon: DeviceMobile, name: 'Mobile 4G', desc: '4G/5G mobile IPs. Perfect for social media.' },
  { icon: HardDrives, name: 'Datacenter', desc: 'Cloud server IPs. Fastest speeds, best prices.' },
];

/**
 * Homepage stats strip.
 *
 * Every figure here is FLAG-GATED and served by /api/platform-stats — none are
 * hardcoded. This strip previously shipped `$2M+ processed`, `15,000+
 * customers`, `4.8/5 rating` and `120+ countries` with no source behind them.
 * On a trust-sensitive market an unsourced rating is a liability: the first
 * customer who checks and finds nothing stops trusting every other number on
 * the page.
 *
 * While a stat's flag is OFF (or its value isn't computable) the API returns
 * placeholder copy and we render that. Flipping the flag in the admin
 * dashboard swaps in the real figure with no deploy.
 *
 * FALLBACK is only for the window before the request resolves or if the API is
 * unreachable — it is placeholder copy, never a claim.
 */
const STAT_FALLBACK = [
  { key: 'revenue', value: 'Secure payments', label: 'processed' },
  { key: 'customers', value: 'Trusted by early users', label: 'customers' },
  { key: 'rating', value: 'Rated by real users', label: 'rating' },
  { key: 'countries', value: 'Global coverage', label: 'countries' },
];

interface PlatformStat {
  key: string;
  label: string;
  enabled: boolean;
  value: string | null;
  placeholder: string;
}

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
        className="w-full py-5 flex items-center justify-between text-left hover:text-[var(--primary-text)] transition-colors duration-200"
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
  // null  = we do not know yet, or the fetch failed  → GlobeMap falls back to
  //         its own /api/catalog-derived list.
  // Set   = authoritative answer from the admin dashboard, INCLUDING an empty
  //         set (dashboard has everything disabled). GlobeMap must render that
  //         as "nothing is for sale", not as "no data".
  const [enabledCountries, setEnabledCountries] = useState<Set<string> | null>(null);
  // Flag-gated stats. Starts null so the strip renders placeholder copy until
  // the API answers — never a hardcoded claim.
  const [platformStats, setPlatformStats] = useState<PlatformStat[] | null>(null);
  const heroRef = useRef<HTMLDivElement>(null);

  // Fetch flag-gated stats. On any failure we keep the placeholder copy: a
  // stats strip must never fall back to an unbacked number.
  useEffect(() => {
    let cancelled = false;
    fetch('/api/platform-stats')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (cancelled || !d?.stats) return;
        setPlatformStats(d.stats);
      })
      .catch(() => { /* placeholders stand */ });
    return () => { cancelled = true; };
  }, []);

  // What actually renders in the strip. Real value only when the API says the
  // stat is enabled AND carries a value; otherwise the placeholder copy.
  const statsToRender = (platformStats ?? []).length
    ? platformStats!.map((s) => ({
        key: s.key,
        value: s.enabled && s.value ? s.value : s.placeholder,
        label: s.label,
      }))
    : STAT_FALLBACK;

  // Fetch admin-enabled countries from the backend and pass to GlobeMap.
  //
  // The empty-array trap this guards against: an empty `countries` array is a
  // *successful* response, so `.catch()` never fires. Treating "[]" as an error
  // silently re-enabled the hardcoded PRODUCT_COUNTRIES fallback and made the
  // admin dashboard's availability controls do nothing on the homepage — which
  // is exactly how a regression in /api/countries shipped unnoticed. So:
  //   non-2xx / unparseable body → error → stay null (fallback, but reported)
  //   200 with a countries array  → authoritative, even when empty
  useEffect(() => {
    let cancelled = false;
    fetch('/api/countries')
      .then(r => {
        if (!r.ok) throw new Error(`/api/countries responded ${r.status}`);
        return r.json();
      })
      .then((data: { countries?: { code: string }[] }) => {
        if (cancelled) return;
        if (!Array.isArray(data?.countries)) {
          throw new Error('/api/countries returned no countries array');
        }
        setEnabledCountries(new Set(data.countries.map(c => c.code)));
        if (data.countries.length === 0) {
          // Legitimate only if the dashboard truly disabled everything. It is
          // also the signature of the /api/countries regression this replaced,
          // so make it visible instead of letting the fallback paper over it.
          reportError(
            new Error('/api/countries returned zero enabled countries'),
            { component: 'Hero', endpoint: '/api/countries' }
          );
        }
      })
      .catch(err => {
        if (cancelled) return;
        // Leave null → GlobeMap falls back. But do not fail silently: a broken
        // availability endpoint must be visible in Sentry, not just a stale map.
        reportError(err, { component: 'Hero', endpoint: '/api/countries' });
      });
    return () => { cancelled = true; };
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
                    className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-all duration-200 border whitespace-nowrap ${
                      isActive
                        ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary-text)]'
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
          <h1 className="text-center text-4xl sm:text-6xl lg:text-7xl xl:text-8xl font-black tracking-tight leading-[1.05] mb-6">
            <span className="text-[var(--foreground)]">Cross the Styx.</span>
            <br />
            <span className="text-[var(--primary-text)]">Stay {TYPEWRITER_WORDS[typewriterIdx]}</span>
          </h1>

          {/* Sub */}
          <p className="text-center text-lg sm:text-xl text-[var(--muted)] max-w-2xl mb-10 leading-relaxed">
            ISP, Residential, Mobile &amp; Datacenter proxies — delivered in seconds.
            <br className="hidden sm:block" />Charon doesn&apos;t ask your name.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center gap-3 mb-6 w-full sm:w-auto">
            <Link href="/products"
              className="w-full sm:w-auto min-w-[200px] px-8 py-4 rounded-xl border border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] text-[var(--foreground)] font-semibold text-center card-depth transition-all duration-200">
              View Products
            </Link>
            <Link href="/order"
              className="w-full sm:w-auto min-w-[200px] px-8 py-4 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-black text-center transition-all duration-200 hover:shadow-[0_0_30px_rgba(10,210,90,0.3)]">
              Get Proxy
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
                <item.icon className="w-3.5 h-3.5 text-[var(--primary-text)]" weight="bold" />
                {item.t}
              </div>
            ))}
          </div>
        </div>

      </section>

      {/* Scroll indicator */}
      <div className="flex flex-col items-center gap-2 py-8">
        <span className="text-xs tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">Scroll</span>
        <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
      </div>

      {/* ── STATS STRIP ── */}
      <section className="border-y border-[var(--border)] bg-[var(--surface)]">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {statsToRender.map((stat, i) => (
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
      <section className="py-16 sm:py-24 lg:py-32 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16">
            <p className="text-base font-medium tracking-[0.3em] uppercase text-[var(--primary-text)] mb-3">What you get</p>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight">
              Built for those who
              <br />
              <span className="text-[var(--muted)]">travel unnamed.</span>
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => (
              <div key={i}
                className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth">
                <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-5">
                  {f.icon && <f.icon className="w-6 h-6 text-[var(--primary-text)]" />}
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
      <section className="py-16 sm:py-24 lg:py-32 px-6 bg-[var(--surface)]">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16">
            <p className="text-base font-medium tracking-[0.3em] uppercase text-[var(--primary-text)] mb-3">Simple process</p>
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
      <section className="py-16 sm:py-24 lg:py-32 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16">
            <p className="text-base font-medium tracking-[0.3em] uppercase text-[var(--primary-text)] mb-3">Proxy types</p>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight">
              Four ways to
              <br />
              <span className="text-[var(--muted)]">change where you appear.</span>
            </h2>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {PRODUCTS.map((p, i) => (
              <div key={i}
                className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth">
                <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-5">
                  {p.icon && <p.icon className="w-6 h-6 text-[var(--primary-text)]" />}
                </div>
                <h3 className="text-base font-bold text-[var(--foreground)] mb-2">{p.name}</h3>
                <p className="text-base text-[var(--muted)] leading-relaxed mb-4">{p.desc}</p>
                <Link href="/products" className="text-xs font-bold text-[var(--primary-text)] hover:underline tracking-wide">
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
            Built for teams and developers working across borders
          </p>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {statsToRender.map((item, i) => (
              <div key={i} className="text-center">
                <div className="text-2xl sm:text-3xl font-black text-[var(--foreground)]">{item.value}</div>
                <div className="text-xs text-[var(--muted)] mt-1 uppercase tracking-wider font-medium">{item.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="py-16 sm:py-24 lg:py-32 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="mb-12">
            <p className="text-base font-medium tracking-[0.3em] uppercase text-[var(--primary-text)] mb-3">FAQ</p>
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
            Get Proxy
          </Link>
        </div>
      </section>

    </div>
  );
}
