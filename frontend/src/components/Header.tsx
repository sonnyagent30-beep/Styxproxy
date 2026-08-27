'use client';

import Link from 'next/link';
import Logo from '@/components/Logo';
import { useState } from 'react';
import { List, X } from '@phosphor-icons/react';

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { href: '/products', label: 'Products' },
    { href: '/pricing', label: 'Pricing' },
    { href: '/how-it-works', label: 'How It Works' },
    { href: '/about', label: 'About' },
    { href: '/blog', label: 'Blog' },
    { href: '/contact', label: 'Contact' },
    { href: '/order/status', label: 'Order Status' },
  ];

  return (
    <header style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 50, background: 'var(--background)', borderBottom: '1px solid var(--border)', backdropFilter: 'blur(12px)' }}>
      <div style={{ maxWidth: '80rem', margin: '0 auto', padding: '0 1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '4rem' }}>
          {/* Logo */}
          <Logo height={36} />

          {/* Desktop Navigation */}
          <nav style={{ display: 'flex', alignItems: 'center', gap: '2rem' }} className="hidden md:flex">
            {navLinks.map(link => (
              <Link
                key={link.href}
                href={link.href}
                style={{ color: 'var(--muted)', textDecoration: 'none' }}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* CTA Button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }} className="hidden md:flex">
            <Link
              href="/order"
              style={{ padding: '0.5rem 1rem', background: 'var(--primary)', color: '#000', fontWeight: 500, borderRadius: '0.5rem', textDecoration: 'none' }}
            >
              Get Proxy
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            style={{ padding: '0.5rem', color: 'var(--muted)', background: 'none', border: 'none', cursor: 'pointer' }}
            className="md:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <List className="w-6 h-6" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div style={{ position: 'fixed', inset: 0, top: '4rem', zIndex: 100, background: 'var(--background)', overflowY: 'auto' }} className="md:hidden">
          <nav style={{ display: 'flex', flexDirection: 'column', padding: '1.5rem' }}>
            {navLinks.map(link => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                style={{ padding: '1rem 0.5rem', fontSize: '1.125rem', fontWeight: 500, color: 'var(--foreground)', textDecoration: 'none', borderBottom: '1px solid var(--border)' }}
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/order"
              onClick={() => setMobileMenuOpen(false)}
              style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: 'var(--primary)', color: '#000', fontWeight: 500, borderRadius: '0.5rem', textAlign: 'center', textDecoration: 'none' }}
            >
              Get Proxy
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
