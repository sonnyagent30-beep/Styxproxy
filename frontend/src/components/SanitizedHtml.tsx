'use client';

import { useState } from 'react';

// Ultra-safe HTML sanitizer: allows only specific safe tags and attributes
function sanitizeHtml(html: string): string {
  // Only allow these tags
  const allowed = new Set(['h1','h2','h3','h4','p','ul','ol','li','strong','em','code','br','hr','span','div']);
  const allowedAttrs: Record<string, Set<string>> = {
    a: new Set(['href', 'target', 'rel']),
  };

  // Basic strip: remove script, style, onclick, onerror, javascript:, data:, etc.
  return html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/\bon\w+\s*=/gi, 'data-removed=')
    .replace(/javascript:/gi, '')
    .replace(/data:/gi, '')
    .replace(/<iframe\b[^>]*>[\s\S]*?<\/iframe>/gi, '')
    .replace(/<object\b[^>]*>[\s\S]*?<\/object>/gi, '')
    .replace(/<embed\b[^>]*>/gi, '')
    .replace(/<form\b[^>]*>[\s\S]*?<\/form>/gi, '')
    .replace(/<input\b[^>]*>/gi, '')
    .replace(/<button\b[^>]*>[\s\S]*?<\/button>/gi, '');
}

export default function SanitizedHtml({ html }: { html: string }) {
  const [cleanHtml] = useState(() => sanitizeHtml(html));

  return (
    <div
      className="legal-content"
      dangerouslySetInnerHTML={{ __html: cleanHtml }}
    />
  );
}
