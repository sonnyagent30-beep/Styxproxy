'use client';

import Link from 'next/link';
import Image from 'next/image';
import type { BlogPost } from '@/types';

interface PostCardProps {
  post: BlogPost;
}

const POST_AUTHOR = 'Styxproxy Team';

/**
 * Editorial-style post card.
 * - 16/9 cover image
 * - Author header (Styxproxy Team + S initial)
 * - Title + excerpt + tag pills
 * - Quick Read badge for thin posts (< 250 words)
 * - .reveal for scroll animation, card-depth for shadow
 */
export default function PostCard({ post }: PostCardProps) {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const estimateReadTime = (content: string): number => {
    const words = content.replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;
    return Math.max(1, Math.ceil(words / 200));
  };

  const readTime = estimateReadTime(post.content || post.excerpt || '');
  const isThin = (post.content || '').replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length < 250;

  return (
    <article
      className="group rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth overflow-hidden"
      data-testid="post-card"
    >
      {/* Author header */}
      <header className="flex items-center justify-between px-5 py-4">
        <Link
          href={`/blog/author/${encodeURIComponent(POST_AUTHOR)}`}
          className="flex items-center gap-3 min-w-0"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="w-8 h-8 rounded-full bg-[var(--primary)] flex items-center justify-center text-black text-xs font-black flex-shrink-0">
            S
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-[var(--foreground)] truncate">
              Styxproxy Team
            </p>
            <p className="text-xs text-[var(--muted)]">
              {formatDate(post.published_at || post.created_at)} · {readTime} min read
            </p>
          </div>
        </Link>
        <div className="flex items-center gap-2">
          {isThin && (
            <span className="text-[10px] font-bold tracking-widest uppercase text-[var(--muted)] bg-[var(--surface)] px-2 py-0.5 rounded">
              Quick Read
            </span>
          )}
          {post.featured && (
            <span className="text-[10px] font-bold tracking-widest uppercase text-[var(--primary)] bg-[var(--primary)]/10 px-2.5 py-1 rounded-full">
              Featured
            </span>
          )}
        </div>
      </header>

      {/* Cover image — 16/9 editorial ratio */}
      {post.cover_image_url ? (
        <Link
          href={`/blog/${post.slug}`}
          className="block relative aspect-[16/9] overflow-hidden bg-[var(--surface)]"
          aria-label={post.title}
        >
          <Image
            src={post.cover_image_url}
            alt={post.title}
            fill
            sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 600px"
            className="object-cover brightness-95 group-hover:brightness-105 group-hover:scale-[1.02] transition-all duration-500"
          />
        </Link>
      ) : (
        <Link
          href={`/blog/${post.slug}`}
          className="block aspect-[16/9] bg-gradient-to-br from-[var(--card)] to-[var(--surface)]"
        />
      )}

      {/* Caption — title + excerpt + tags */}
      <Link href={`/blog/${post.slug}`} className="block px-5 pb-5 pt-2">
        <h2 className="text-lg sm:text-xl font-bold text-[var(--foreground)] tracking-[-0.02em] leading-snug mb-2 line-clamp-2 group-hover:text-[var(--primary)] transition-colors">
          {post.title}
        </h2>
        <p className="text-sm text-[var(--muted)] leading-relaxed mb-4 line-clamp-2">
          {post.excerpt}
        </p>
        {post.tags && post.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {post.tags.slice(0, 2).map((tag) => (
              <span
                key={tag}
                className="text-[11px] font-medium text-[var(--muted)] bg-[var(--surface)] px-2 py-0.5 rounded"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
      </Link>
    </article>
  );
}
