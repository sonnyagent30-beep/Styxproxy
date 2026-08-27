'use client';

import Link from 'next/link';
import Logo from '@/components/Logo';
import { useState } from 'react';
import { List, X } from '@phosphor-icons/react';

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass-card border-b border-[var(--border)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo — crisp SVG, theme-aware */}
          <Logo height={36} />

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            <Link
              href="/products"
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Products
            </Link>
            <Link
              href="/pricing"
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Pricing
            </Link>
            <Link
              href="/how-it-works"
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              How It Works
            </Link>
            <Link
              href="/about"
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              About
            </Link>
            <Link
              href="/blog"
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Blog
            </Link>
            <Link
              href="/contact"
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Contact
            </Link>
            <Link
              href="/manage"
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Manage
            </Link>
          </nav>

          {/* CTA Button */}
          <div className="hidden md:flex items-center space-x-4">
            <Link
              href="/order"
              className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
            >
              Get Proxy
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 text-[var(--muted)]"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <List className="w-6 h-6" />
            )}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div
            className="md:hidden fixed inset-0 top-16 bg-black/50 z-40"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}
        <div
          className="md:hidden overflow-hidden transition-all duration-300 ease-out"
          style={{
            maxHeight: mobileMenuOpen ? 'calc(100svh - 64px)' : '0',
            opacity: mobileMenuOpen ? 1 : 0,
          }}
        >
          <nav className="flex flex-col space-y-1 py-4 border-t border-[var(--border)]">
            {[
              ['/products', 'Products'],
              ['/pricing', 'Pricing'],
              ['/how-it-works', 'How It Works'],
              ['/about', 'About'],
              ['/blog', 'Blog'],
              ['/contact', 'Contact'],
              ['/manage', 'Manage'],
            ].map(([href, label]) => (
              <Link
                key={href}
                href={href}
                className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors py-2.5 px-1"
                onClick={() => setMobileMenuOpen(false)}
              >
                {label}
              </Link>
            ))}
            <Link
              href="/order"
              className="mt-2 px-4 py-2.5 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors text-center"
              onClick={() => setMobileMenuOpen(false)}
            >
              Get Proxy
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
