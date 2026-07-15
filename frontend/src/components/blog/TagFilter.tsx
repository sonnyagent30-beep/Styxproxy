'use client';
import Link from 'next/link';
import { useState } from 'react';
import TagPill from './TagPill';

interface Props {
  tags: string[];
  activeTag?: string;
}

export default function TagFilter({ tags, activeTag }: Props) {
  const [query, setQuery] = useState('');

  const filtered = query
    ? tags.filter((t) => t.toLowerCase().includes(query.toLowerCase()))
    : tags;

  return (
    <div className="space-y-4">
      {/* Search + All */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search posts..."
            className="w-full pl-10 pr-3 py-2 rounded-full bg-[var(--surface)] border border-[var(--border)] text-sm text-white placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)]/60 transition-colors"
          />
        </div>
        <Link
          href="/blog"
          className={`px-4 py-2 rounded-full text-xs font-medium transition-all duration-200 flex-shrink-0 ${
            !activeTag
              ? 'bg-[var(--primary)] text-black'
              : 'bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)] hover:text-white hover:border-[var(--primary)]/60'
          }`}
        >
          All posts
        </Link>
      </div>

      {/* Tag chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 scrollbar-hide">
        {filtered.map((tag) => (
          <div key={tag} className="flex-shrink-0">
            <TagPill tag={tag} active={tag === activeTag} />
          </div>
        ))}
        {filtered.length === 0 && (
          <span className="text-xs text-[var(--muted)] py-2">No tags match "{query}"</span>
        )}
      </div>
    </div>
  );
}
