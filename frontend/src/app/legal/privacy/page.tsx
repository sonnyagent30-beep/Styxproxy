import React from 'react';
import { content } from '@/lib/legal/privacy.js';

// Strip dangerous tags/attrs from HTML legal content
function sanitize(html: string): string {
  return html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/\son\w+\s*=/gi, 'data-removed=')
    .replace(/javascript:/gi, '')
    .replace(/data:/gi, '')
    .replace(/<iframe\b[^>]*>[\s\S]*?<\/iframe>/gi, '')
    .replace(/<form\b[^>]*>[\s\S]*?<\/form>/gi, '')
    .replace(/<input\b[^>]*>/gi, '')
    .replace(/<button\b[^>]*>[\s\S]*?<\/button>/gi, '');
}

export default function Privacy() {
  const clean = sanitize(content);

  return (
    <main className="flex-1 px-4 py-24">
      <article className="max-w-3xl mx-auto">
        <div className="mb-10">
          <h1 className="text-4xl font-bold mb-4">Privacy Policy</h1>
          <p className="text-[var(--muted)] text-sm">Effective Date: 2026-07-01</p>
        </div>
        <div
          className="legal-content"
          dangerouslySetInnerHTML={{ __html: clean }}
          style={{ color: 'var(--muted)', lineHeight: 1.8 }}
        />
      </article>
    </main>
  );
}
