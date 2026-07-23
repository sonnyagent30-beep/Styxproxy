'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { BlogPost } from '@/types';
import PostCard from './PostCard';
import TagFilter from './TagFilter';

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
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
      {/* Header */}
      <header className="mb-10">
        <h1
          className="text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-[-0.03em] leading-[1.05] mb-3"
          style={{ textWrap: 'balance' }}
        >
          Blog
        </h1>
        <p className="text-base sm:text-lg text-[var(--muted)] max-w-2xl leading-relaxed">
          Notes on proxies, anonymity, and the infrastructure that keeps the web working.
        </p>
      </header>

      {/* Tag filter */}
      <div className="mb-10">
        <TagFilter
          tags={initialTags}
          activeTag={activeTag || undefined}
        />
      </div>

      {/* Instagram-style vertical feed: 1 column on mobile, 2 columns on
          desktop. No 3-column masonry — true Instagram feed is single-track
          for narrative flow. */}
      {posts.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <p className="text-[var(--muted)] text-lg">No posts found.</p>
          {activeTag && (
            <Link
              href="/blog"
              className="text-[var(--primary)] hover:underline mt-2 inline-block"
              onClick={() => handleTagChange(null)}
            >
              View all posts
            </Link>
          )}
        </div>
      )}

      {/* Load More */}
      {hasMore && posts.length > 0 && (
        <div className="mt-12 text-center">
          <button
            onClick={loadMore}
            disabled={loading}
            className="px-6 py-3 bg-[var(--surface)] border border-[var(--border)] text-white rounded-full font-medium hover:border-[var(--primary)]/60 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
    </main>
  );
}
