'use client';

import Link from 'next/link';
import { TelegramLogo, WhatsappLogo, Envelope } from '@phosphor-icons/react';

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-[var(--border)] bg-[var(--card)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">

        {/* Top: brand + tagline + social */}
        <div className="mb-12">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-8">

            {/* Brand with official logo */}
            <div className="max-w-xs">
              <Link href="/" className="inline-flex items-center gap-3 mb-4">
                <picture>
                  <source srcSet="/footer-logo-dark.png" media="(prefers-color-scheme: dark)" />
                  <img src="/footer-logo-light.png" alt="Styxproxy" className="h-10 w-auto object-contain" />
                </picture>
              </Link>
              <p className="text-sm text-[var(--muted)] leading-relaxed">
                Premium proxies delivered instantly. No account required.
              </p>
            </div>

            {/* Social buttons — 3D elevated */}
            <div className="flex items-center gap-3 shrink-0">
              <a href="https://t.me/StyxproxyBot" target="_blank" rel="noopener noreferrer"
                className="relative w-10 h-10 rounded-xl bg-[#0088cc] hover:bg-[#006699] flex items-center justify-center transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_8px_20px_rgba(0,136,204,0.4)]"
                aria-label="Telegram">
                <TelegramLogo className="w-5 h-5 text-white" />
              </a>
              <a href="https://wa.me/2347032981049" target="_blank" rel="noopener noreferrer"
                className="relative w-10 h-10 rounded-xl bg-[#25D366] hover:bg-[#1da851] flex items-center justify-center transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_8px_20px_rgba(37,211,102,0.4)]"
                aria-label="WhatsApp">
                <WhatsappLogo className="w-5 h-5 text-white" />
              </a>
              <a href="mailto:support@styxproxy.com"
                className="relative w-10 h-10 rounded-xl bg-[var(--card-hover)] border border-[var(--border-light)] flex items-center justify-center transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--primary)] hover:shadow-[0_8px_20px_rgba(10,210,90,0.25)]"
                aria-label="Email support">
                <Envelope className="w-5 h-5 text-[var(--foreground)]" />
              </a>
            </div>
          </div>
        </div>

        {/* Divider with gradient */}
        <div className="relative py-8 border-t border-b border-[var(--border)]">
          <div className="absolute inset-x-6 top-1/2 -translate-y-1/2 h-px bg-gradient-to-r from-transparent via-[var(--primary)]/30 to-transparent pointer-events-none" />
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
          <p className="text-xs text-[var(--muted)] opacity-50">
            Premium proxies for professionals
          </p>
        </div>

      </div>
    </footer>
  );
}
