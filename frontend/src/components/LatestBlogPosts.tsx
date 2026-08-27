'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import type { BlogPost } from '@/types';
import { api } from '@/lib/api';

interface Props {
  initialPosts?: BlogPost[];
}

export default function LatestBlogPosts({ initialPosts = [] }: Props) {
  const [posts, setPosts] = useState<BlogPost[]>(initialPosts);
  const [loading, setLoading] = useState(!initialPosts.length);

  useEffect(() => {
    if (initialPosts.length > 0) return;
    let cancelled = false;
    (async () => {
      try {
        const result = await api.getBlogPosts(1, 3);
        if (!cancelled && result.data?.posts) {
          setPosts(result.data.posts);
        }
      } catch {
        // render nothing on error
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [initialPosts]);

  if (loading) {
    return (
      <section className="py-24 lg:py-32 px-6 bg-[var(--surface)]">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-2xl bg-[var(--card)] border border-[var(--border)] overflow-hidden animate-pulse">
                <div className="aspect-[16/9] bg-[var(--surface)]" />
                <div className="p-5 space-y-3">
                  <div className="h-3 w-16 bg-[var(--surface)] rounded" />
                  <div className="h-4 w-full bg-[var(--surface)] rounded" />
                  <div className="h-4 w-2/3 bg-[var(--surface)] rounded" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (!posts || posts.length === 0) return null;

  const estimateReadTime = (content: string): number => {
    const words = content
      .replace(/<[^>]+>/g, '')
      .split(/\s+/)
      .filter(Boolean).length;
    return Math.max(1, Math.ceil(words / 200));
  };

  return (
    <section className="py-24 lg:py-32 px-6 bg-[var(--surface)]">
      <div className="max-w-6xl mx-auto">
        <div className="mb-12">
          <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">
            Latest from the blog
          </p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight">
            Notes from the<br />
            <span className="text-[var(--muted)]">trenches.</span>
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {initialPosts.map((post) => {
            const readTime = estimateReadTime(post.content || post.excerpt || '');
            return (
              <article
                key={post.id}
                className="group rounded-2xl bg-[var(--card)] border border-[var(--border)] card-depth overflow-hidden"
              >
                <Link href={`/blog/${post.slug}`} className="block">
                  <div className="relative aspect-[16/9] overflow-hidden bg-[var(--surface)]">
                    {post.cover_image_url && (
                      <Image
                        src={post.cover_image_url}
                        alt={post.title}
                        fill
                        className="object-cover brightness-95 group-hover:brightness-105 group-hover:scale-[1.02] transition-all duration-500"
                        sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 400px"
                      />
                    )}
                  </div>
                  <div className="p-5">
                    {post.tags && post.tags[0] && (
                      <span className="text-[11px] font-medium text-[var(--primary)] uppercase tracking-wider">
                        #{post.tags[0]}
                      </span>
                    )}
                    <h3 className="text-base font-bold text-[var(--foreground)] tracking-[-0.01em] leading-snug mt-2 mb-2 line-clamp-2 group-hover:text-[var(--primary)] transition-colors">
                      {post.title}
                    </h3>
                    <p className="text-sm text-[var(--muted)] line-clamp-2 leading-relaxed">
                      {post.excerpt}
                    </p>
                    <div className="flex items-center gap-2 mt-4 text-xs text-[var(--muted)]">
                      <span className="font-medium text-[var(--foreground)]">Styxproxy Team</span>
                      <span>·</span>
                      <span>{readTime} min read</span>
                    </div>
                  </div>
                </Link>
              </article>
            );
          })}
        </div>
        <div className="mt-10 text-center">
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] text-sm font-bold text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
          >
            View all posts
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 256 256"><path d="M221.66,133.66l-72,72a8,8,0,0,1-11.32-11.32L196.69,136H40a8,8,0,0,1,0-16H196.69L138.34,61.66a8,8,0,0,1,11.32-11.32l72,72A8,8,0,0,1,221.66,133.66Z" /></svg>
          </Link>
        </div>
      </div>
    </section>
  );
}
