'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { BlogPost } from '@/types';
import PostRow from '@/components/blog/PostRow';

export default function LatestBlogPosts() {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchPosts() {
      try {
        const result = await api.getBlogPosts(1, 3);
        if (cancelled) return;
        if (result.data && result.data.posts.length > 0) {
          setPosts(result.data.posts);
        }
      } catch {
        // render nothing on error
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchPosts();
    return () => { cancelled = true; };
  }, []);

  if (loading || posts.length === 0) return null;

  return (
    <section className="py-24 lg:py-32 px-6 bg-[var(--surface)]">
      <div className="max-w-4xl mx-auto">
        <div className="mb-12">
          <p className="text-xs font-medium tracking-[0.3em] uppercase text-[var(--primary)] mb-3">
            Latest from the blog
          </p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight">
            Notes from the
            <br />
            <span className="text-[var(--muted)]">trenches.</span>
          </h2>
        </div>
        <div className="reveal">
          {posts.map((post) => (
            <PostRow key={post.id} post={post} variant="compact" />
          ))}
        </div>
        <div className="mt-10 text-center reveal">
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 text-sm font-bold text-[var(--primary)] hover:underline tracking-wide"
          >
            View all posts
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
            </svg>
          </Link>
        </div>
      </div>
    </section>
  );
}
