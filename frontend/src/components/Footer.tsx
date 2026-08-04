'use client';

import Link from 'next/link';

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-[var(--border)] bg-[var(--card)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">

        {/* Top: brand + tagline + social */}
        <div className="mb-12">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-8">

            {/* Brand */}
            <div className="max-w-xs">
              <Link href="/" className="inline-flex items-center gap-3 mb-4 group">
                <picture>
                  <source srcSet="/footer-logo-dark.png" media="(prefers-color-scheme: dark)" />
                  <img src="/footer-logo-light.png" alt="Styxproxy" className="h-10 w-auto object-contain" />
                </picture>
              </Link>
              <p className="text-sm text-[var(--muted)] leading-relaxed">
                AI-powered proxy intelligence for those who move in silence.
              </p>
            </div>

            {/* Social */}
            <div className="flex items-center gap-3 shrink-0">
              <a href="https://t.me/StyxproxyBot" target="_blank" rel="noopener noreferrer"
                className="w-10 h-10 rounded-xl bg-[#0088cc] hover:bg-[#006699] flex items-center justify-center transition-all duration-200"
                aria-label="Telegram">
                <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                </svg>
              </a>
              <a href="https://wa.me/2347032981049" target="_blank" rel="noopener noreferrer"
                className="w-10 h-10 rounded-xl bg-[#25D366] hover:bg-[#1da851] flex items-center justify-center transition-all duration-200"
                aria-label="WhatsApp">
                <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                </svg>
              </a>
              <a href="mailto:support@styxproxy.com"
                className="w-10 h-10 rounded-xl bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--primary)]/40 flex items-center justify-center transition-all duration-200"
                aria-label="Email support">
                <svg className="w-5 h-5 text-[var(--muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="4" width="20" height="16" rx="2" />
                  <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                </svg>
              </a>
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="relative py-8 border-t border-b border-[var(--border)]">
          <div className="absolute inset-x-6 top-1/2 -translate-y-1/2 h-px bg-gradient-to-r from-transparent via-[var(--primary)]/40 to-transparent pointer-events-none" />
        </div>

        {/* Links grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 py-10">

          <div>
            <h4 className="font-semibold text-[var(--foreground)] mb-4 text-sm">Product</h4>
            <ul className="space-y-3 text-sm text-[var(--muted)]">
              <li><Link href="/products" className="hover:text-[var(--primary)] transition-colors duration-150">Products</Link></li>
              <li><Link href="/pricing" className="hover:text-[var(--primary)] transition-colors duration-150">Pricing</Link></li>
              <li><Link href="/blog" className="hover:text-[var(--primary)] transition-colors duration-150">Blog</Link></li>
              <li><Link href="/contact" className="hover:text-[var(--primary)] transition-colors duration-150">Contact</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-[var(--foreground)] mb-4 text-sm">Resources</h4>
            <ul className="space-y-3 text-sm text-[var(--muted)]">
              <li><Link href="/how-it-works" className="hover:text-[var(--primary)] transition-colors duration-150">How It Works</Link></li>
              <li><Link href="/about" className="hover:text-[var(--primary)] transition-colors duration-150">About</Link></li>
              <li><Link href="/manage" className="hover:text-[var(--primary)] transition-colors duration-150">Manage Order</Link></li>
              <li><a href="https://t.me/StyxproxyBot" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--primary)] transition-colors duration-150">Telegram Bot</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-[var(--foreground)] mb-4 text-sm">Legal</h4>
            <ul className="space-y-3 text-sm text-[var(--muted)]">
              <li><Link href="/legal/terms" className="hover:text-[var(--primary)] transition-colors duration-150">Terms of Service</Link></li>
              <li><Link href="/legal/privacy" className="hover:text-[var(--primary)] transition-colors duration-150">Privacy Policy</Link></li>
              <li><Link href="/legal/aup" className="hover:text-[var(--primary)] transition-colors duration-150">Acceptable Use</Link></li>
              <li><Link href="/refund-policy" className="hover:text-[var(--primary)] transition-colors duration-150">Refund Policy</Link></li>
              <li><Link href="/cookie-policy" className="hover:text-[var(--primary)] transition-colors duration-150">Cookie Policy</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-[var(--foreground)] mb-4 text-sm">Support</h4>
            <ul className="space-y-3 text-sm text-[var(--muted)]">
              <li><a href="mailto:support@styxproxy.com" className="hover:text-[var(--primary)] transition-colors duration-150">support@styxproxy.com</a></li>
              <li className="flex items-center gap-2 pt-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] animate-pulse" />
                <span className="text-[var(--primary)] text-xs font-medium">Systems operational</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-8 flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-sm text-[var(--muted)]">
            &copy; {year} Styxproxy. All rights reserved.
          </p>
          <p className="text-xs text-[var(--muted)] italic opacity-60">
            Charon guides the way. You remain unseen.
          </p>
        </div>

      </div>
    </footer>
  );
}
