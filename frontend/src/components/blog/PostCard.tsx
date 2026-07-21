'use client';

import Link from 'next/link';
import Image from 'next/image';
import type { BlogPost } from '@/types';

interface PostCardProps {
  post: BlogPost;
}

export default function PostCard({ post }: PostCardProps) {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const estimateReadTime = (content: string): number => {
    const words = content.replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;
    return Math.max(1, Math.ceil(words / 200));
  };

  const readTime = estimateReadTime(post.content || post.excerpt || '');

  return (
    <article className="group relative bg-[var(--surface)] border border-[var(--border)] rounded-2xl overflow-hidden hover:border-[var(--primary)]/50 transition-all duration-300 hover:shadow-[0_0_30px_rgba(var(--primary-rgb,100,181,246),0.15)]">
      {/* Cover Image */}
      {post.cover_image_url && (
        <Link href={`/blog/${post.slug}`} className="block relative aspect-[16/10] overflow-hidden">
          <Image
            src={post.cover_image_url}
            alt={post.title}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-500"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        </Link>
      )}

      {/* Content */}
      <div className="p-5">
        {/* Tags */}
        {post.tags && post.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {post.tags.slice(0, 2).map((tag) => (
              <Link
                key={tag}
                href={`/blog/tag/${encodeURIComponent(tag)}`}
                className="text-xs font-medium text-[var(--primary)] hover:text-[var(--primary)]/80 transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                #{tag}
              </Link>
            ))}
          </div>
        )}

        {/* Title */}
        <Link href={`/blog/${post.slug}`}>
          <h2 className="text-lg font-bold text-[var(--foreground)] tracking-[-0.02em] leading-tight mb-2 group-hover:text-[var(--primary)] transition-colors line-clamp-2">
            {post.title}
          </h2>
        </Link>

        {/* Excerpt */}
        <p className="text-sm text-[var(--muted)] leading-relaxed mb-4 line-clamp-2">
          {post.excerpt}
        </p>

        {/* Meta */}
        <div className="flex items-center justify-between pt-4 border-t border-[var(--border)]">
          <Link
            href={`/blog/author/${encodeURIComponent(post.author)}`}
            className="flex items-center gap-2 group/author"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-black text-xs font-bold flex-shrink-0">
              {post.author?.charAt(0)}
            </div>
            <span className="text-xs font-medium text-[var(--muted)] group-hover/author:text-[var(--foreground)] transition-colors">
              {post.author}
            </span>
          </Link>

          <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
            <time dateTime={post.published_at || post.created_at}>
              {formatDate(post.published_at || post.created_at)}
            </time>
            <span>·</span>
            <span>{readTime} min</span>
          </div>
        </div>
      </div>
    </article>
  );
}
