import Link from 'next/link';
import Image from 'next/image';
import type { BlogPost } from '@/types';

interface Props {
  prev?: BlogPost | null;
  next?: BlogPost | null;
}

export default function PostNav({ prev, next }: Props) {
  if (!prev && !next) return null;

  return (
    <nav className="mt-20 pt-10 border-t border-[var(--border)] space-y-4">
      {prev && (
        <Link
          href={`/blog/${prev.slug}`}
          className="group flex items-center gap-5 p-4 rounded-xl border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
        >
          <div className="flex-shrink-0 text-[var(--muted)] group-hover:text-[var(--primary)] transition-colors">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </div>
          {prev.cover_image_url && (
            <div className="relative w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden bg-[var(--surface)]">
              <Image src={prev.cover_image_url} alt={prev.title} fill className="object-cover" sizes="64px" />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-xs text-[var(--muted)] mb-0.5">Previous</p>
            <p className="text-sm font-medium text-white group-hover:text-[var(--primary)] transition-colors line-clamp-2 leading-snug">
              {prev.title}
            </p>
          </div>
        </Link>
      )}

      {next && (
        <Link
          href={`/blog/${next.slug}`}
          className="group flex items-center gap-5 p-4 rounded-xl border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
        >
          <div className="min-w-0 flex-1 text-right">
            <p className="text-xs text-[var(--muted)] mb-0.5">Next</p>
            <p className="text-sm font-medium text-white group-hover:text-[var(--primary)] transition-colors line-clamp-2 leading-snug">
              {next.title}
            </p>
          </div>
          {next.cover_image_url && (
            <div className="relative w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden bg-[var(--surface)]">
              <Image src={next.cover_image_url} alt={next.title} fill className="object-cover" sizes="64px" />
            </div>
          )}
          <div className="flex-shrink-0 text-[var(--muted)] group-hover:text-[var(--primary)] transition-colors">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </div>
        </Link>
      )}
    </nav>
  );
}
