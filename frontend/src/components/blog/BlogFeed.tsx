'use client';

import { useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { MagnifyingGlass } from '@phosphor-icons/react';
import { api } from '@/lib/api';
import type { BlogPost } from '@/types';
import PostCard from './PostCard';
import { PostCardSkeletonGrid } from '@/components/Skeletons';

interface BlogFeedProps {
  initialPosts: BlogPost[];
  initialTags: string[];
  initialPage: number;
  hasMore: boolean;
}

export default function BlogFeed({
  initialPosts,
  initialTags,
  initialPage,
  hasMore: initialHasMore,
}: BlogFeedProps) {
  const [posts, setPosts] = useState<BlogPost[]>(initialPosts);
  const [page, setPage] = useState(initialPage);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(initialHasMore);
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [query, setQuery] = useState('');

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    setLoading(true);
    try {
      const nextPage = page + 1;
      const result = await api.getBlogPosts(nextPage, 9, activeTag || undefined);
      if (result.data) {
        setPosts((prev) => [...prev, ...result.data!.posts]);
        setPage(nextPage);
        setHasMore(result.data.pagination.has_next);
      }
    } catch (err) {
      console.error('Failed to load more posts:', err);
    } finally {
      setLoading(false);
    }
  }, [loading, hasMore, page, activeTag]);

  // Reset when tag changes
  const handleTagChange = (tag: string | null) => {
    setActiveTag(tag);
    setPage(1);
    setHasMore(true);
    // Fetch fresh posts for this tag
    (async () => {
      setLoading(true);
      try {
        const result = await api.getBlogPosts(1, 9, tag || undefined);
        if (result.data) {
          setPosts(result.data.posts);
          setHasMore(result.data.pagination.has_next);
        } else {
          // Fallback to empty on API error
          setPosts([]);
          setHasMore(false);
        }
      } catch (err) {
        console.error('Failed to fetch posts:', err);
        setPosts([]);
        setHasMore(false);
      } finally {
        setLoading(false);
      }
    })();
  };

  return (
    <>
      {/* Hero Section */}
      <div className="relative overflow-hidden pt-12 pb-16 px-6">
        <div className="absolute inset-0 hero-bg-grid" aria-hidden="true" />
        <div className="absolute inset-0 hero-bg-rings" aria-hidden="true" />
        <div className="absolute inset-0 hero-bg-vignette" aria-hidden="true" />
        <div className="hero-orb hero-orb-1" aria-hidden="true" />
        <div className="hero-orb hero-orb-2" aria-hidden="true" />
        <div className="hero-orb hero-orb-3" aria-hidden="true" />

        <div className="relative text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[var(--primary)]/30 bg-[var(--primary)]/5 mb-6 mx-auto">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] shadow-[0_0_8px_var(--primary)] animate-pulse" />
            <span className="text-xs font-medium tracking-widest uppercase text-[var(--muted)]">
              The Styxproxy Blog
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-black tracking-tight mb-6">
            Notes from the<br />
            <span className="text-[var(--primary)]">trenches.</span>
          </h1>
          <p className="text-lg max-w-xl mx-auto leading-relaxed text-[var(--muted)]">
            Guides on proxies, anonymity, automation, and the infrastructure that keeps the web working.
          </p>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="flex flex-col items-center gap-2 py-8">
        <span className="text-[10px] tracking-[0.3em] uppercase text-[var(--muted)] opacity-50">Scroll</span>
        <div className="w-px h-10 bg-gradient-to-b from-[var(--primary)]/60 to-transparent animate-pulse" />
      </div>

      {/* Filter Bar */}
      <div className="max-w-6xl mx-auto px-6 pb-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="relative flex-1 max-w-md">
            <MagnifyingGlass size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search posts..."
              className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)] text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)]/60 transition-colors"
            />
          </div>
          <Link
            href="/blog"
            onClick={() => handleTagChange(null)}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-all duration-200 flex-shrink-0 ${
              !activeTag
                ? 'bg-[var(--primary)] text-black font-bold'
                : 'bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)] hover:border-[var(--primary)]/60'
            }`}
          >
            All posts
          </Link>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
          {filtered.map((tag) => (
            <Link
              key={tag}
              href={`/blog/tag/${encodeURIComponent(tag)}`}
              onClick={() => handleTagChange(tag)}
              className={`inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200 flex-shrink-0 ${
                tag === activeTag
                  ? 'bg-[var(--primary)] text-black font-bold'
                  : 'bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)] hover:border-[var(--primary)]/60'
              }`}
            >
              #{tag}
            </Link>
          ))}
        </div>
      </div>

      {/* Grid */}
      <div className="max-w-6xl mx-auto px-6">
        <div className="section-divider-glow mb-12" />
        {posts.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
            {posts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        ) : loading ? (
          <PostCardSkeletonGrid count={6} />
        ) : (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-full bg-[var(--card)] border border-[var(--border)] flex items-center justify-center mx-auto mb-6">
              <MagnifyingGlass size={24} className="text-[var(--muted)]" />
            </div>
            <p className="text-[var(--muted)] text-lg mb-2">No posts found</p>
            <p className="text-sm text-[var(--muted)] mb-6">Try a different search or tag.</p>
            {activeTag && (
              <Link
                href="/blog"
                onClick={() => handleTagChange(null)}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)] text-sm font-medium text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
              >
                View all posts
              </Link>
            )}
          </div>
        )}
      </div>

      {/* Load More */}
      {hasMore && posts.length > 0 && (
        <div className="mt-12 text-center">
          <button
            onClick={loadMore}
            disabled={loading}
            className="px-8 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] font-medium hover:border-[var(--primary)]/60 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Loading...
              </span>
            ) : (
              'Load more'
            )}
          </button>
        </div>
      )}

      {/* No more posts indicator */}
      {!hasMore && posts.length > 0 && (
        <p className="text-center text-[var(--muted)] text-sm mt-12">
          You&apos;ve reached the end
        </p>
      )}
    </>
  );
}
