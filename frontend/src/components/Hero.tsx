'use client';

import Link from 'next/link';

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center pt-16 overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-[var(--background)] via-[var(--card)] to-[var(--background)]" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[var(--primary)]/10 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[var(--accent)]/10 rounded-full blur-3xl" />
      
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Badge */}
        <div className="inline-flex items-center px-4 py-2 rounded-full bg-[var(--card)] border border-[var(--border)] mb-8 animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-[var(--primary)] mr-2 animate-pulse" />
          <span className="text-sm text-[var(--muted)]">3 ways to order — Instant, Telegram, or WhatsApp</span>
        </div>

        {/* Main Headline */}
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6 animate-slide-up">
          <span className="text-[var(--foreground)]">Nigeria's Anonymous </span>
          <span className="gradient-text">Proxy Reseller</span>
        </h1>

        {/* Subheadline */}
        <p className="text-xl sm:text-2xl text-[var(--muted)] mb-10 max-w-3xl mx-auto animate-slide-up" style={{ animationDelay: '0.1s' }}>
          ISP, Residential, Datacenter & Mobile 4G proxies. Order instantly, via Telegram, 
          or on WhatsApp. Pay in NGN. Get credentials on the spot.
        </p>

        {/* CTA Buttons — 3 Ways */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up" style={{ animationDelay: '0.2s' }}>
          <Link
            href="/order"
            className="w-full sm:w-auto px-8 py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl text-lg transition-all hover:scale-105 hover:shadow-lg hover:shadow-[var(--primary)]/20"
          >
            ⚡ Get Instant
          </Link>
          <a
            href="https://t.me/BuncheBot"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full sm:w-auto px-8 py-4 bg-[#0088CC] hover:bg-[#0077B5] text-white font-semibold rounded-xl text-lg transition-all hover:scale-105"
          >
            💬 Order on Telegram
          </a>
          <a
            href="https://wa.me/2347032981049"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full sm:w-auto px-8 py-4 border border-[var(--border)] hover:border-[#25D366] text-[var(--foreground)] font-semibold rounded-xl text-lg transition-all hover:bg-[var(--card)]"
          >
            📱 WhatsApp
          </a>
        </div>

        {/* Trust Indicators */}
        <div className="mt-16 flex flex-wrap items-center justify-center gap-8 text-[var(--muted)] animate-fade-in" style={{ animationDelay: '0.3s' }}>
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5 text-[var(--primary)]" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span>Instant Delivery</span>
          </div>
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5 text-[var(--primary)]" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span>24/7 Support</span>
          </div>
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5 text-[var(--primary)]" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span>Free Replacement</span>
          </div>
        </div>

        {/* How It Works Preview */}
        <div id="how-it-works" className="mt-24 text-left">
          <h2 className="text-2xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/20 flex items-center justify-center mb-4">
                <span className="text-[var(--primary)] font-bold text-xl">1</span>
              </div>
              <h3 className="text-lg font-semibold mb-2">Choose Your Channel</h3>
              <p className="text-[var(--muted)]">Order instantly on the web, or via Telegram or WhatsApp. No account needed.</p>
            </div>
            <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/20 flex items-center justify-center mb-4">
                <span className="text-[var(--primary)] font-bold text-xl">2</span>
              </div>
              <h3 className="text-lg font-semibold mb-2">Pay Securely</h3>
              <p className="text-[var(--muted)]">Pay securely via Flutterwave. Bank transfer, card, USSD, or QR — all in NGN.</p>
            </div>
            <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/20 flex items-center justify-center mb-4">
                <span className="text-[var(--primary)] font-bold text-xl">3</span>
              </div>
              <h3 className="text-lg font-semibold mb-2">Get Your Proxy</h3>
              <p className="text-[var(--muted)]">Receive your proxy credentials instantly. No waiting. Valid until your plan expires.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
