import Link from 'next/link';
import Image from 'next/image';
import type { BlogPost } from '@/types';
import TagPill from './TagPill';

interface Props {
  post: BlogPost;
  variant?: 'hero' | 'feature' | 'standard' | 'compact';
  imagePosition?: 'left' | 'right' | 'top';
}

function estimateReadTime(content: string): number {
  const words = content.replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 200));
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function PostRow({
  post,
  variant = 'standard',
  imagePosition = 'left',
}: Props) {
  const readTime = estimateReadTime(post.content || post.excerpt || '');
  const tags = post.tags?.slice(0, 2) || [];

  if (variant === 'hero') {
    return (
      <Link href={`/blog/${post.slug}`} className="group block">
        <article className="relative aspect-[16/9] sm:aspect-[21/9] overflow-hidden rounded-2xl bg-[var(--surface)]">
          {post.cover_image_url && (
            <Image
              src={post.cover_image_url}
              alt={post.title}
              fill
              priority
              className="object-cover brightness-90 group-hover:brightness-100 transition-[filter] duration-500"
              sizes="(max-width: 768px) 100vw, 1200px"
            />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-transparent" />
          <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-10">
            {tags.length > 0 && (
              <div className="flex items-center gap-1.5 mb-3">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-[var(--primary)] text-black"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            )}
            <h2
              className="font-bold text-white group-hover:text-[var(--primary)] transition-colors leading-[1.05] tracking-[-0.03em] mb-3 text-2xl sm:text-4xl md:text-5xl max-w-3xl"
              style={{ textWrap: 'balance' }}
            >
              {post.title}
            </h2>
            <p className="text-sm sm:text-base text-white/80 leading-relaxed mb-4 max-w-2xl line-clamp-2">
              {post.excerpt}
            </p>
            <div className="flex items-center gap-2 text-xs text-white/70">
              <div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-bold text-[11px] flex-shrink-0">
                {post.author?.charAt(0)}
              </div>
              <span className="font-medium text-white">{post.author}</span>
              <span>·</span>
              <time>{formatDate(post.published_at || post.created_at)}</time>
              <span>·</span>
              <span>{readTime} min read</span>
            </div>
          </div>
        </article>
      </Link>
    );
  }

  if (variant === 'feature') {
    return (
      <Link href={`/blog/${post.slug}`} className="group block">
        <article className="grid md:grid-cols-[1.4fr_1fr] gap-6 md:gap-10 items-center py-10 border-t border-[var(--border)]">
          <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-[var(--surface)]">
            {post.cover_image_url && (
              <Image
                src={post.cover_image_url}
                alt={post.title}
                fill
                className="object-cover brightness-95 group-hover:brightness-110 transition-[filter] duration-300"
                sizes="(max-width: 768px) 100vw, 60vw"
              />
            )}
          </div>
          <div className="min-w-0">
            {tags.length > 0 && (
              <div className="flex items-center gap-1.5 mb-3">
                {tags.map((tag) => <TagPill key={tag} tag={tag} size="sm" />)}
              </div>
            )}
            <h2
              className="font-bold text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors leading-[1.15] tracking-[-0.02em] mb-3 text-2xl sm:text-3xl md:text-4xl line-clamp-3"
              style={{ textWrap: 'balance' }}
            >
              {post.title}
            </h2>
            <p className="text-[var(--muted)] leading-relaxed mb-5 line-clamp-3 text-sm sm:text-base">
              {post.excerpt}
            </p>
            <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
              <div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-bold text-[11px] flex-shrink-0">
                {post.author?.charAt(0)}
              </div>
              <span className="font-medium text-white">{post.author}</span>
              <span>·</span>
              <time>{formatDate(post.published_at || post.created_at)}</time>
              <span>·</span>
              <span>{readTime} min read</span>
            </div>
          </div>
        </article>
      </Link>
    );
  }

  if (variant === 'compact') {
    return (
      <Link href={`/blog/${post.slug}`} className="group block">
        <article className="flex gap-4 p-3 -m-3 rounded-xl hover:bg-[var(--surface)]/50 transition-colors">
          <div className="relative w-20 h-20 sm:w-24 sm:h-24 flex-shrink-0 rounded-lg overflow-hidden bg-[var(--surface)]">
            {post.cover_image_url && (
              <Image
                src={post.cover_image_url}
                alt={post.title}
                fill
                className="object-cover"
                sizes="96px"
              />
            )}
          </div>
          <div className="flex-1 min-w-0">
            {tags.length > 0 && (
              <span className="text-[10px] font-medium text-[var(--primary)] uppercase tracking-wider">
                {tags[0]}
              </span>
            )}
            <h3 className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors line-clamp-2 leading-snug mb-1 mt-1">
              {post.title}
            </h3>
            <div className="flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
              <span>{post.author}</span>
              <span>·</span>
              <span>{readTime} min</span>
            </div>
          </div>
        </article>
      </Link>
    );
  }

  // standard — image left or right
  const imageOrder = imagePosition === 'right' ? 'md:order-2' : '';
  const contentOrder = imagePosition === 'right' ? 'md:order-1' : '';

  return (
    <Link href={`/blog/${post.slug}`} className="group block">
      <article
        className={`grid md:grid-cols-2 gap-6 md:gap-10 items-center py-10 border-t border-[var(--border)]`}
      >
        <div className={`relative aspect-[3/2] overflow-hidden rounded-xl bg-[var(--surface)] ${imageOrder}`}>
          {post.cover_image_url && (
            <Image
              src={post.cover_image_url}
              alt={post.title}
              fill
              className="object-cover brightness-95 group-hover:brightness-110 transition-[filter] duration-300"
              sizes="(max-width: 768px) 100vw, 50vw"
            />
          )}
        </div>
        <div className={`min-w-0 ${contentOrder}`}>
          {tags.length > 0 && (
            <div className="flex items-center gap-1.5 mb-3">
              {tags.map((tag) => <TagPill key={tag} tag={tag} size="sm" />)}
            </div>
          )}
          <h2
            className="font-bold text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors leading-[1.15] tracking-[-0.02em] mb-3 text-xl sm:text-2xl md:text-3xl line-clamp-3"
            style={{ textWrap: 'balance' }}
          >
            {post.title}
          </h2>
          <p className="text-[var(--muted)] leading-relaxed mb-5 line-clamp-3 text-sm">
            {post.excerpt}
          </p>
          <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
            <div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-bold text-[11px] flex-shrink-0">
              {post.author?.charAt(0)}
            </div>
            <span className="font-medium text-white">{post.author}</span>
            <span>·</span>
            <time>{formatDate(post.published_at || post.created_at)}</time>
            <span>·</span>
            <span>{readTime} min read</span>
          </div>
        </div>
      </article>
    </Link>
  );
}
