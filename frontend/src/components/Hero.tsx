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

        {/* Contact Section */}
        <div id="contact" className="mt-24">
          <h2 className="text-2xl font-bold text-center mb-4">Get In Touch</h2>
          <p className="text-[var(--muted)] text-center mb-8 max-w-xl mx-auto">
            Have questions? Need help? Reach out through any of these channels and we'll get back to you ASAP.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href="https://wa.me/2347032981049"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full sm:w-auto px-6 py-3 bg-[#25D366] hover:bg-[#20BD5A] text-white font-semibold rounded-xl transition-all hover:scale-105"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
              </svg>
              WhatsApp
            </a>
            <a
              href="https://t.me/BuncheBot"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full sm:w-auto px-6 py-3 bg-[#0088CC] hover:bg-[#0077B5] text-white font-semibold rounded-xl transition-all hover:scale-105"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
              </svg>
              Telegram
            </a>
            <a
              href="mailto:oyebiyiayomide30@gmail.com"
              className="flex items-center justify-center gap-2 w-full sm:w-auto px-6 py-3 bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-semibold rounded-xl transition-all hover:bg-[var(--card-hover)]"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Email
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
