'use client';
import { useRouter, usePathname } from 'next/navigation';
import { useSearchParams } from 'next/navigation';
import { useCallback } from 'react';

interface Props {
  tags: string[];
  activeTag?: string;
}

export default function TagFilter({ tags, activeTag }: Props) {
  const router = useRouter();
  const pathname = usePathname();

  const handleTagClick = useCallback(
    (tag: string) => {
      if (tag === activeTag) {
        router.push('/blog');
      } else {
        router.push(`/blog/tag/${encodeURIComponent(tag)}`);
      }
    },
    [activeTag, router]
  );

  if (!tags.length) return null;

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
      <button
        onClick={() => router.push('/blog')}
        className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 ${
          !activeTag
            ? 'bg-[var(--accent)] text-white shadow-sm'
            : 'bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)] border border-[var(--border)]'
        }`}
      >
        All
      </button>
      {tags.map((tag) => (
        <button
          key={tag}
          onClick={() => handleTagClick(tag)}
          className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 ${
            tag === activeTag
              ? 'bg-[var(--accent)] text-white shadow-sm'
              : 'bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)] border border-[var(--border)]'
          }`}
        >
          #{tag}
        </button>
      ))}
    </div>
  );
}
