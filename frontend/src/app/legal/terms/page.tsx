import React from 'react';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import { content } from '@/lib/legal/terms.js';

export default function Terms() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 px-4 py-24">
        <article className="max-w-3xl mx-auto">
          <div className="mb-10">
            <h1 className="text-4xl font-bold mb-4">Terms of Service</h1>
            <p className="text-[var(--muted)] text-sm">Effective Date: 2026-07-01</p>
          </div>
          <div
            className="legal-content"
            dangerouslySetInnerHTML={{ __html: content }}
            style={{
              color: 'var(--muted)',
              lineHeight: 1.8,
            }}
          />
        </article>
      </main>
      <Footer />
    </div>
  );
}
