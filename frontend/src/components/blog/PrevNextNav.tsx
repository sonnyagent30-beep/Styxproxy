import Link from 'next/link';
import Image from 'next/image';
import type { BlogPost } from '@/types';

interface Props {
  prev?: BlogPost | null;
  next?: BlogPost | null;
}

export default function PrevNextNav({ prev, next }: Props) {
  if (!prev && !next) return null;

  return (
    <nav className="flex items-stretch gap-4 mt-12 pt-8 border-t border-[var(--border)]">
      {prev ? (
        <Link
          href={`/blog/${prev.slug}`}
          className="flex-1 group flex items-center gap-3 p-4 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--surface)] transition-all"
        >
          <div className="flex-shrink-0">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5 text-[var(--muted)] group-hover:text-[var(--accent)] transition-colors">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </div>
          {prev.cover_image_url && (
            <div className="relative w-12 h-12 flex-shrink-0 rounded-lg overflow-hidden">
              <Image src={prev.cover_image_url} alt={prev.title} fill className="object-cover" sizes="48px" />
            </div>
          )}
          <div className="min-w-0">
            <p className="text-xs text-[var(--muted)] mb-0.5">← Previous</p>
            <p className="text-sm font-medium text-[var(--foreground)] group-hover:text-[var(--accent)] transition-colors line-clamp-2 leading-snug">
              {prev.title}
            </p>
          </div>
        </Link>
      ) : (
        <div className="flex-1" />
      )}

      {next ? (
        <Link
          href={`/blog/${next.slug}`}
          className="flex-1 group flex items-center justify-end gap-3 p-4 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--surface)] transition-all text-right"
        >
          <div className="min-w-0">
            <p className="text-xs text-[var(--muted)] mb-0.5">Next →</p>
            <p className="text-sm font-medium text-[var(--foreground)] group-hover:text-[var(--accent)] transition-colors line-clamp-2 leading-snug">
              {next.title}
            </p>
          </div>
          {next.cover_image_url && (
            <div className="relative w-12 h-12 flex-shrink-0 rounded-lg overflow-hidden">
              <Image src={next.cover_image_url} alt={next.title} fill className="object-cover" sizes="48px" />
            </div>
          )}
          <div className="flex-shrink-0">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5 text-[var(--muted)] group-hover:text-[var(--accent)] transition-colors">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </div>
        </Link>
      ) : (
        <div className="flex-1" />
      )}
    </nav>
  );
}
