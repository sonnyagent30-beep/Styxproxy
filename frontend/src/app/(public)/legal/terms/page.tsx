import React from 'react';
import Link from 'next/link';
import { content } from '@/lib/legal/terms.js';
import LegalContent from '@/components/LegalContent';

export default function Terms() {
  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Hero background layers */}
      <div className="absolute inset-0 hero-bg-grid" />
      <div className="absolute inset-0 hero-bg-rings" />
      <div className="absolute inset-0 hero-bg-vignette" />
      <div className="hero-orb hero-orb-1" />
      <div className="hero-orb hero-orb-2" />

      <main className="relative z-10 flex-1 pt-28 pb-20">
        <div className="max-w-2xl mx-auto px-6">
          {/* Article card */}
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl card-depth overflow-hidden">
            <div className="p-8 sm:p-10">
              <div className="mb-8">
                <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">Legal</p>
                <h1 className="text-3xl font-black text-[var(--foreground)] mb-2">Terms of Service</h1>
                <p className="text-[var(--muted)] text-sm">Effective Date: 2026-07-01</p>
              </div>
              <div className="border-t border-[var(--border)] mb-8" />
              <div style={{ color: 'var(--muted)', lineHeight: 1.8 }} className="text-sm">
                <LegalContent content={content} />
              </div>
            </div>
          </div>

          {/* CTA */}
          <div className="mt-8 text-center p-6 bg-[var(--card)] border border-[var(--border)] rounded-2xl">
            <p className="text-[var(--muted)] text-sm mb-3">Questions about our terms?</p>
            <Link href="/contact" className="text-[var(--primary)] font-semibold hover:underline text-sm">
              Contact us →
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
