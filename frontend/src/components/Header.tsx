'use client';

import Link from 'next/link';
import { useState } from 'react';
import { List, X } from '@phosphor-icons/react';
import Logo from '@/components/Logo';

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const links = [
    { href: '/products', label: 'Products' },
    { href: '/pricing', label: 'Pricing' },
    { href: '/how-it-works', label: 'How It Works' },
    { href: '/about', label: 'About' },
    { href: '/blog', label: 'Blog' },
    { href: '/contact', label: 'Contact' },
    { href: '/order/status', label: 'Order Status' },
  ];

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-[200] bg-[var(--background)]/95 backdrop-blur-md border-b border-[var(--border)]">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          {/* Logo */}
          <Logo height={36} />

          {/* Desktop nav */}
          <nav className="hidden lg:flex items-center gap-8">
            {links.map(l => (
              <Link key={l.href} href={l.href} className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors text-sm font-medium">
                {l.label}
              </Link>
            ))}
          </nav>

          {/* Desktop CTA */}
          <div className="hidden lg:flex items-center gap-3">
            <Link href="/order" className="px-5 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-lg text-sm transition-colors">
              Get Proxy
            </Link>
          </div>

          {/* Mobile toggle */}
          <button
            className="lg:hidden p-2 text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            onClick={() => setMobileOpen(o => !o)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X weight="bold" className="w-6 h-6" /> : <List weight="bold" className="w-6 h-6" />}
          </button>
        </div>
      </header>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-[199] bg-black/60" onClick={() => setMobileOpen(false)} />
      )}

      {/* Mobile slide-down panel */}
      <div
        className="lg:hidden fixed top-16 left-0 right-0 z-[200] bg-[var(--background)] border-b border-[var(--border)] transition-all duration-300 ease-out overflow-hidden"
        style={{ maxHeight: mobileOpen ? '100dvh' : 0, opacity: mobileOpen ? 1 : 0 }}
      >
        <nav className="flex flex-col p-6 gap-1">
          {links.map(l => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setMobileOpen(false)}
              className="text-[var(--foreground)] hover:text-[var(--primary)] hover:bg-[var(--card-hover)] transition-colors py-4 px-4 text-base font-medium rounded-xl"
            >
              {l.label}
            </Link>
          ))}
          <div className="mt-4 pt-4 border-t border-[var(--border)]">
            <Link
              href="/order"
              onClick={() => setMobileOpen(false)}
              className="block w-full text-center px-5 py-3.5 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl text-base transition-colors"
            >
              Get Proxy
            </Link>
          </div>
        </nav>
      </div>
    </>
  );
}
