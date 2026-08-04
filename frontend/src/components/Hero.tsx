'use client';

import { useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';

const GlobeMap = dynamic(() => import('@/components/GlobeMap'), { ssr: false });

const TYPEWRITER_WORDS = ['untraceable', 'unrestricted', 'verified', 'instant', 'anonymous'];

const FAQ_DATA = [
  { q: 'How fast is delivery?', a: 'Your proxy credentials are delivered instantly, typically within 3 seconds of payment confirmation.' },
  { q: 'Do I need an account?', a: 'No account required. Select your proxy, pay, and receive credentials immediately.' },
  { q: 'What protocols do you support?', a: 'HTTP, HTTPS, SOCKS4, and SOCKS5. Works with any standard proxy client or browser.' },
  { q: 'What is your refund policy?', a: '24-hour refund for valid issues. Contact support within 24 hours if your proxies are not working.' },
  { q: 'Which countries are available?', a: '120+ countries. Visit our products page to check specific country availability.' },
];

const FEATURES = [
  { icon: 'M13 10V3L4 14h7v7l9-11h-7z', title: 'Instant Delivery', desc: 'Proxies live in under 3 seconds after payment' },
  { icon: 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z', title: 'Anonymous Access', desc: 'Zero logs. Zero tracking. No footprint.' },
  { icon: 'M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z', title: 'All Protocols', desc: 'HTTP, HTTPS, SOCKS4 and SOCKS5' },
  { icon: 'M3.6 9h16.8M3.6 15h16.8M12 3a15.3 15.3 0 014 9 15.3 15.3 0 01-4 9 15.3 15.3 0 01-4-9 15.3 15.3 0 014-9z', title: 'Global Coverage', desc: '120+ countries worldwide' },
  { icon: 'M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z', title: '99.9% Uptime', desc: 'Reliable, consistent performance' },
  { icon: 'M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z', title: 'AI Support', desc: 'Help via chat anytime, anywhere' },
];

const PRODUCTS = [
  { icon: 'M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25H6a2.25 2.25 0 01-2.25-2.25v7.5A2.25 2.25 0 016 21h12a2.25 2.25 0 012.25-2.25v-7.5A2.25 2.25 0 0118 11.25h-1.5z', name: 'ISP Proxy', desc: 'Static IPs from ISPs. Fast, reliable.' },
  { icon: 'M3.6 9h16.8M3.6 15h16.8M12 3a15.3 15.3 0 014 9 15.3 15.3 0 01-4 9 15.3 15.3 0 01-4-9 15.3 15.3 0 014-9z', name: 'Residential', desc: 'Real device IPs from homes. High anonymity.' },
  { icon: 'M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 9.75h3', name: 'Mobile 4G', desc: '4G/5G mobile IPs. Perfect for social media.' },
  { icon: 'M5.25 12H3m0 0l2-2m-2 2l2 2M19 12h2m0 0l2-2m-2 2l2 2M9 4H7a2 2 0 00-2 2v2m0 8v2a2 2 0 002 2h2m8-16h2a2 2 0 012 2v2m0 8v2a2 2 0 01-2 2h-2', name: 'Datacenter', desc: 'Cloud server IPs. Fastest speeds.' },
];

const STATS = [
  { value: '$2M+', label: 'processed' },
  { value: '15,000+', label: 'customers' },
  { value: '4.8/5', label: 'rating' },
  { value: '120+', label: 'countries' },
];

function CardDepth({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`relative group ${className}`}>
      {/* 3D depth shadow beneath */}
      <div className="absolute -inset-0.5 rounded-2xl bg-gradient-to-br from-[var(--primary)]/20 via-transparent to-transparent opacity-0 group-hover:opacity-100 blur-sm transition-opacity duration-300 -z-10 translate-y-2 group-hover:translate-y-1" />
      {/* Card */}
      <div className="relative rounded-2xl bg-[var(--card)] border border-[var(--border)] p-6 group-hover:border-[var(--primary)]/50 transition-all duration-200 group-hover:-translate-y-1 group-hover:shadow-[0_12px_40px_rgba(10,210,90,0.08),0_4px_12px_rgba(0,0,0,0.4)]">
        {children}
      </div>
    </div>
  );
}

function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-[var(--border)] last:border-0">
      <button onClick={() => setOpen((o) => !o)}
        className="w-full py-5 flex items-center justify-between text-left hover:text-[var(--primary)] transition-colors duration-150">
        <span className="font-medium text-[var(--foreground)] pr-4">{q}</span>
        <svg className={`w-5 h-5 shrink-0 transition-transform duration-150 ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div className={`overflow-hidden transition-all duration-150 ${open ? 'max-h-40 pb-5' : 'max-h-0'}`}>
        <p className="text-[var(--muted)]">{a}</p>
      </div>
    </div>
  );
}

export default function Hero() {
  const [typewriterIdx, setTypewriterIdx] = useState(0);

  // Typewriter cycle
  useState(() => {
    const id = setInterval(() => setTypewriterIdx((i) => (i + 1) % TYPEWRITER_WORDS.length), 3000);
    return () => clearInterval(id);
  });

  return (
    <div className="min-h-screen overflow-x-hidden">

      {/* ── HERO ── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center pt-20 pb-16">
        {/* Noise texture overlay */}
        <div
          className="absolute inset-0 pointer-events-none opacity-[0.03] dark:opacity-[0.05]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
            backgroundSize: '200px 200px',
          }}
        />

        {/* Lime glow aura behind globe */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full bg-[var(--primary)] opacity-[0.06] blur-[160px] pointer-events-none" />

        {/* Top accent line */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-24 bg-gradient-to-b from-[var(--primary)] to-transparent opacity-40" />

        <div className="relative z-10 w-full max-w-5xl mx-auto px-6 flex flex-col items-center">

          {/* Globe with glow depth */}
          <div className="w-full max-w-md mx-auto mb-8 relative">
            <div className="absolute inset-0 rounded-full bg-[var(--primary)]/15 blur-3xl scale-95" />
            <GlobeMap />
          </div>

          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[var(--primary)]/30 bg-[var(--primary)]/5 mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] animate-pulse" />
            <span className="text-xs font-medium tracking-widest uppercase text-[var(--muted)]">
              AI-Powered Proxy Intelligence
            </span>
          </div>

          {/* Headline — impeccable tracking: -0.03em, 6rem ceiling */}
          <h1 className="text-center text-5xl sm:text-6xl lg:text-7xl font-black tracking-[-0.03em] leading-[1.05] mb-6 text-[var(--foreground)]">
            <span>Cross the Styx.</span>
            <br />
            <span className="text-[var(--primary)]">Stay {TYPEWRITER_WORDS[typewriterIdx]}</span>
          </h1>

          {/* Sub — no aphorisms */}
          <p className="text-center text-lg sm:text-xl text-[var(--muted)] max-w-2xl mb-10 leading-relaxed">
            ISP, Residential, Mobile and Datacenter proxies. Delivered in seconds.
          </p>

          {/* CTAs — 3D elevated */}
          <div className="flex flex-col sm:flex-row items-center gap-3 mb-6 w-full sm:w-auto">
            <Link href="/products"
              className="relative w-full sm:w-auto min-w-[200px] px-8 py-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] font-semibold text-center text-sm transition-all duration-200 hover:-translate-y-1 hover:border-[var(--primary)]/60 hover:shadow-[0_16px_40px_rgba(0,0,0,0.5),0_4px_12px_rgba(10,210,90,0.15)]">
              View Products
            </Link>
            <Link href="/order"
              className="relative w-full sm:w-auto min-w-[200px] px-8 py-4 rounded-2xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-bold text-center text-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_20px_50px_rgba(10,210,90,0.4),0_6px_16px_rgba(10,210,90,0.2)]">
              Order Now
            </Link>
          </div>

          {/* WhatsApp + Telegram — 3D elevated, same width */}
          <div className="flex flex-col sm:flex-row items-center gap-3 mb-10 w-full sm:w-auto">
            <a href="https://wa.me/2347032981049" target="_blank" rel="noopener noreferrer"
              className="relative w-full sm:w-auto min-w-[200px] flex items-center justify-center gap-2 px-8 py-4 rounded-2xl bg-[#25D366] hover:bg-[#1fb855] text-white font-bold text-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_20px_50px_rgba(37,211,102,0.45)]">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
              WhatsApp
            </a>
            <a href="https://t.me/StyxproxyBot" target="_blank" rel="noopener noreferrer"
              className="relative w-full sm:w-auto min-w-[200px] flex items-center justify-center gap-2 px-8 py-4 rounded-2xl bg-[#0088cc] hover:bg-[#0077aa] text-white font-bold text-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_20px_50px_rgba(0,136,204,0.45)]">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
              Telegram
            </a>
          </div>

          {/* Trust indicators */}
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[var(--muted)] text-xs font-medium tracking-wide">
            {[
              { icon: 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z', t: 'Instant delivery' },
              { icon: 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z', t: 'No account needed' },
              { icon: 'M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z', t: 'Verified proxies' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                </svg>
                {item.t}
              </div>
            ))}
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2">
          <span className="text-[10px] tracking-[0.25em] uppercase text-[var(--muted)] opacity-40">Scroll</span>
          <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent" />
        </div>
      </section>

      {/* ── STATS STRIP ── */}
      <section className="relative border-y border-[var(--border)] bg-[var(--surface)]">
        <div className="absolute inset-0 bg-gradient-to-b from-[var(--primary)]/4 to-transparent" />
        <div className="relative max-w-6xl mx-auto px-6 py-12">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {STATS.map((stat, i) => (
              <div key={i} className="text-center">
                <div className="text-3xl sm:text-4xl lg:text-5xl font-black text-[var(--foreground)] tracking-tight">{stat.value}</div>
                <div className="text-xs text-[var(--muted)] mt-2 font-medium tracking-widest uppercase">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="py-24 lg:py-32 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="mb-14">
            <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--foreground)] leading-tight">
              Built for those who<br />
              <span className="text-[var(--muted)]">move in silence.</span>
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f, i) => (
              <CardDepth key={i}>
                <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-5">
                  <svg className="w-6 h-6 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
                    <path d={f.icon} />
                  </svg>
                </div>
                <h3 className="text-base font-bold text-[var(--foreground)] mb-2">{f.title}</h3>
                <p className="text-sm text-[var(--muted)] leading-relaxed">{f.desc}</p>
              </CardDepth>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="py-24 lg:py-32 px-6 bg-[var(--surface)]">
        <div className="max-w-6xl mx-auto">
          <div className="mb-14">
            <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--foreground)] leading-tight">
              Up and running<br />
              <span className="text-[var(--muted)]">in three steps.</span>
            </h2>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {[
              { n: '01', title: 'Choose Your Proxy', desc: 'ISP, Residential, Mobile 4G or Datacenter. Pick your country and plan.' },
              { n: '02', title: 'Pay and Get Credentials', desc: 'Pay with card or bank transfer. Your proxy details arrive instantly.' },
              { n: '03', title: 'Start Using', desc: 'Configure in your bot, scraper or browser. Works immediately.' },
            ].map((item, i) => (
              <CardDepth key={i}>
                <div className="inline-block px-3 py-1 rounded-full bg-[var(--primary)] text-black text-xs font-black tracking-wider mb-4">
                  {item.n}
                </div>
                <h3 className="text-lg font-bold text-[var(--foreground)] mb-2">{item.title}</h3>
                <p className="text-sm text-[var(--muted)] leading-relaxed">{item.desc}</p>
              </CardDepth>
            ))}
          </div>
        </div>
      </section>

      {/* ── PRODUCTS ── */}
      <section className="py-24 lg:py-32 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="mb-14">
            <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--foreground)] leading-tight">
              Four ways to<br />
              <span className="text-[var(--muted)]">stay invisible.</span>
            </h2>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
            {PRODUCTS.map((p, i) => (
              <CardDepth key={i}>
                <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-5">
                  <svg className="w-6 h-6 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
                    <path d={p.icon} />
                  </svg>
                </div>
                <h3 className="text-base font-bold text-[var(--foreground)] mb-1">{p.name}</h3>
                <p className="text-xs text-[var(--muted)] leading-relaxed mb-4">{p.desc}</p>
                <Link href="/products" className="text-xs font-bold text-[var(--primary)] hover:underline tracking-wide">
                  View pricing
                </Link>
              </CardDepth>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="py-24 lg:py-32 px-6 bg-[var(--surface)]">
        <div className="max-w-3xl mx-auto">
          <div className="mb-10">
            <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--foreground)]">Questions?</h2>
          </div>
          <div className="relative rounded-2xl bg-[var(--card)] border border-[var(--border)] px-6 shadow-[0_8px_40px_rgba(0,0,0,0.4)]">
            {FAQ_DATA.map((item, i) => <FAQItem key={i} q={item.q} a={item.a} />)}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] mb-5">
            Ready to cross the Styx?
          </h2>
          <p className="text-[var(--muted)] mb-10 text-lg">No signup required.</p>
          <Link href="/order"
            className="relative inline-block px-14 py-5 rounded-2xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-black text-base transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_24px_60px_rgba(10,210,90,0.5),0_8px_20px_rgba(10,210,90,0.25)]">
            Order Now
          </Link>
        </div>
      </section>

    </div>
  );
}
