'use client';
import Link from 'next/link';
import TagPill from './TagPill';

interface Props {
  tags: string[];
  activeTag?: string;
}

export default function TagFilter({ tags, activeTag }: Props) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 scrollbar-hide">
      <Link
        href="/blog"
        className={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium transition-colors duration-200 flex-shrink-0 ${
          !activeTag
            ? 'bg-[var(--primary)] text-black'
            : 'bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)] hover:text-white hover:border-[var(--primary)]'
        }`}
      >
        All
      </Link>
      {tags.map((tag) => (
        <div key={tag} className="flex-shrink-0">
          <TagPill tag={tag} active={tag === activeTag} />
        </div>
      ))}
    </div>
  );
}
