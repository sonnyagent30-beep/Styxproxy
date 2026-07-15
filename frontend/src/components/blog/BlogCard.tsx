import Link from 'next/link';
import Image from 'next/image';
import type { BlogPost } from '@/types';

interface Props {
  post: BlogPost;
  featured?: boolean;
}

function estimateReadTime(content: string): number {
  const words = content.replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 200));
}

export default function BlogCard({ post, featured = false }: Props) {
  const readTime = estimateReadTime(post.content || post.excerpt || '');
  const displayTags = post.tags?.slice(0, 2) || [];

  if (featured) {
    return (
      <Link href={`/blog/${post.slug}`} className="block group">
        <article className="relative rounded-2xl overflow-hidden bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)] transition-all duration-300">
          <div className="relative h-64 sm:h-80 w-full">
            {post.cover_image_url ? (
              <Image
                src={post.cover_image_url}
                alt={post.title}
                fill
                className="object-cover group-hover:scale-105 transition-transform duration-500"
                sizes="(max-width: 768px) 100vw, 800px"
              />
            ) : (
              <div className="absolute inset-0 bg-gradient-to-br from-[var(--accent)]/20 to-[var(--accent)]/5" />
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-6">
              <div className="flex items-center gap-3 mb-3">
                {displayTags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--accent)] text-white"
                  >
                    #{tag}
                  </span>
                ))}
                <span className="text-xs text-white/70">{readTime} min read</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-white mb-2 group-hover:text-[var(--accent)] transition-colors">
                {post.title}
              </h2>
              <p className="text-sm text-white/80 line-clamp-2">{post.excerpt}</p>
              <div className="flex items-center gap-2 mt-3">
                <div className="w-7 h-7 rounded-full bg-[var(--accent)] flex items-center justify-center text-xs font-bold text-white">
                  {post.author?.charAt(0)}
                </div>
                <span className="text-xs text-white/70">{post.author}</span>
                <span className="text-xs text-white/50">
                  {new Date(post.published_at || post.created_at).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </span>
              </div>
            </div>
          </div>
        </article>
      </Link>
    );
  }

  return (
    <Link href={`/blog/${post.slug}`} className="block group">
      <article className="flex gap-4 p-3 rounded-xl hover:bg-[var(--surface)] transition-all duration-200 border border-transparent hover:border-[var(--border)]">
        {post.cover_image_url && (
          <div className="relative w-20 h-20 sm:w-24 sm:h-24 flex-shrink-0 rounded-lg overflow-hidden">
            <Image
              src={post.cover_image_url}
              alt={post.title}
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-300"
              sizes="96px"
            />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            {displayTags.map((tag) => (
              <span
                key={tag}
                className="text-xs font-medium text-[var(--accent)]"
              >
                #{tag}
              </span>
            ))}
            <span className="text-xs text-[var(--muted)]">{readTime} min</span>
          </div>
          <h3 className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--accent)] transition-colors line-clamp-2 leading-snug mb-1">
            {post.title}
          </h3>
          <p className="text-xs text-[var(--muted)] line-clamp-2 leading-relaxed">
            {post.excerpt}
          </p>
        </div>
      </article>
    </Link>
  );
}
