import Link from 'next/link';
import Image from 'next/image';
import type { BlogPost } from '@/types';
import TagPill from './TagPill';

interface Props {
  post: BlogPost;
  featured?: boolean;
  imagePosition?: 'left' | 'right';
}

function estimateReadTime(content: string): number {
  const words = content.replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 200));
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function PostRow({ post, featured = false, imagePosition = 'left' }: Props) {
  const readTime = estimateReadTime(post.content || post.excerpt || '');
  const tags = post.tags?.slice(0, 2) || [];

  const imageOrder = imagePosition === 'right' ? 'md:order-2' : '';
  const contentOrder = imagePosition === 'right' ? 'md:order-1' : '';

  return (
    <Link
      href={`/blog/${post.slug}`}
      className="group block"
    >
      <article
        className={`grid gap-6 md:gap-10 items-center ${
          featured ? 'md:grid-cols-[1.4fr_1fr] md:gap-12' : 'md:grid-cols-2'
        } py-10 border-t border-[var(--border)]`}
      >
        {/* Image */}
        <div className={`relative w-full ${featured ? 'aspect-[4/3]' : 'aspect-[3/2]'} overflow-hidden rounded-xl bg-[var(--surface)] ${imageOrder}`}>
          {post.cover_image_url && (
            <Image
              src={post.cover_image_url}
              alt={post.title}
              fill
              priority={featured}
              className="object-cover brightness-95 group-hover:brightness-110 transition-[filter] duration-300"
              sizes={featured ? '(max-width: 768px) 100vw, 60vw' : '(max-width: 768px) 100vw, 50vw'}
            />
          )}
        </div>

        {/* Content */}
        <div className={`min-w-0 ${contentOrder}`}>
          {/* Tags */}
          {tags.length > 0 && (
            <div className="flex items-center gap-1.5 mb-3">
              {tags.map((tag) => (
                <TagPill key={tag} tag={tag} size="sm" />
              ))}
            </div>
          )}

          {/* Title */}
          <h2
            className={`font-bold text-white group-hover:text-[var(--primary)] transition-colors duration-200 leading-[1.15] tracking-[-0.02em] mb-3 line-clamp-3 ${
              featured ? 'text-3xl sm:text-4xl md:text-5xl' : 'text-2xl sm:text-3xl'
            }`}
            style={{ textWrap: 'balance' }}
          >
            {post.title}
          </h2>

          {/* Excerpt */}
          <p className={`text-[var(--muted)] leading-relaxed mb-5 line-clamp-3 ${featured ? 'text-base md:text-lg' : 'text-sm md:text-base'}`}>
            {post.excerpt}
          </p>

          {/* Meta */}
          <div className="flex items-center gap-2.5 text-xs text-[var(--muted)]">
            <div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-bold text-[11px] flex-shrink-0">
              {post.author?.charAt(0)}
            </div>
            <span className="font-medium text-white">{post.author}</span>
            <span className="text-[var(--muted)]">·</span>
            <time dateTime={post.published_at || post.created_at}>
              {formatDate(post.published_at || post.created_at)}
            </time>
            <span className="text-[var(--muted)]">·</span>
            <span>{readTime} min read</span>
          </div>
        </div>
      </article>
    </Link>
  );
}
