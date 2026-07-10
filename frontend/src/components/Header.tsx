'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass-card border-b border-[var(--border)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <Image
              src="/header-icon-dark.png"
              alt="styxproxy"
              width={40}
              height={40}
              className="hidden dark:block w-10 h-10"
              priority
            />
            <Image
              src="/header-icon-light.png"
              alt="styxproxy"
              width={40}
              height={40}
              className="block dark:hidden w-10 h-10"
              priority
            />
            <span className="text-xl font-bold text-[var(--foreground)]">styxproxy</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            <Link 
              href="/products" 
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Products
            </Link>
            <Link 
              href="/order" 
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Order
            </Link>
            <Link
              href="/#how-it-works"
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              How It Works
            </Link>
            <Link 
              href="/manage" 
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Manage
            </Link>
            <Link 
              href="/contact" 
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Contact
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
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-[var(--border)]">
            <nav className="flex flex-col space-y-4">
              <Link
                href="/products"
                className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Products
              </Link>
              <Link
                href="/order"
                className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Order
              </Link>
              <Link
                href="/#how-it-works"
                className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                How It Works
              </Link>
              <Link
                href="/manage"
                className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Manage
              </Link>
              <Link
                href="/contact"
                className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Contact
              </Link>
              <Link
                href="/order"
                className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors text-center"
                onClick={() => setMobileMenuOpen(false)}
              >
                Get Proxy
              </Link>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
