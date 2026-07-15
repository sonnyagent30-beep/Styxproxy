'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { api } from '@/lib/api';
import type { BlogPost } from '@/types';

// Demo blog posts — used when API is unavailable (local dev, no DB)
const DEMO_POSTS: BlogPost[] = [
  {
    id: 'demo-1',
    slug: 'residential-vs-datacenter-proxies',
    title: 'Residential vs Datacenter Proxies: Which Should You Choose?',
    excerpt: 'Understand the fundamental differences between residential and datacenter proxies and which one fits your use case.',
    content: '',
    cover_image_url: '/blog/cover-1.png',
    author: 'Oyebiyi Ayomide',
    status: 'published',
    view_count: 0,
    updated_at: '2026-06-01T09:00:00Z',
    tags: ['proxies', 'residential', 'datacenter', 'guide'],
    created_at: '2026-06-01T09:00:00Z',
    published_at: '2026-06-01T09:00:00Z',
  },
  {
    id: 'demo-2',
    slug: 'how-to-configure-socks5-proxies',
    title: 'How to Configure SOCKS5 Proxies in 5 Minutes',
    excerpt: 'A practical step-by-step guide to configuring your Sytxproxy SOCKS5 credentials in any application.',
    content: '',
    cover_image_url: '/blog/cover-2.png',
    author: 'Oyebiyi Ayomide',
    status: 'published',
    view_count: 0,
    updated_at: '2026-06-08T10:00:00Z',
    tags: ['tutorial', 'socks5', 'configuration'],
    created_at: '2026-06-08T10:00:00Z',
    published_at: '2026-06-08T10:00:00Z',
  },
  {
    id: 'demo-3',
    slug: 'web-scraping-nigeria-guide',
    title: 'Web Scraping in Nigeria: A Practical Guide for 2026',
    excerpt: 'Everything you need to know about scraping Nigerian websites legally and effectively in 2026.',
    content: '',
    cover_image_url: '/blog/cover-3.png',
    author: 'Oyebiyi Ayomide',
    status: 'published',
    view_count: 0,
    updated_at: '2026-06-15T08:00:00Z',
    tags: ['nigeria', 'web-scraping', 'data'],
    created_at: '2026-06-15T08:00:00Z',
    published_at: '2026-06-15T08:00:00Z',
  },
  {
    id: 'demo-4',
    slug: 'http-vs-socks5-vs-https-proxies',
    title: 'HTTP vs SOCKS5 vs HTTPS Proxies: Complete Comparison',
    excerpt: 'A technical breakdown of HTTP, HTTPS, and SOCKS5 proxy protocols and which one you should use.',
    content: '',
    cover_image_url: '/blog/cover-4.png',
    author: 'Oyebiyi Ayomide',
    status: 'published',
    view_count: 0,
    updated_at: '2026-06-22T11:00:00Z',
    tags: ['technical', 'socks5', 'http', 'comparison'],
    created_at: '2026-06-22T11:00:00Z',
    published_at: '2026-06-22T11:00:00Z',
  },
  {
    id: 'demo-5',
    slug: 'web-automation-stack-nigerian-businesses',
    title: 'Building an Affordable Web Automation Stack for Nigerian Businesses',
    excerpt: 'How Nigerian businesses can build a professional web automation infrastructure for under ₦20,000/month.',
    content: '',
    cover_image_url: '/blog/cover-5.png',
    author: 'Oyebiyi Ayomide',
    status: 'published',
    view_count: 0,
    updated_at: '2026-07-01T09:30:00Z',
    tags: ['automation', 'business', 'nigeria'],
    created_at: '2026-07-01T09:30:00Z',
    published_at: '2026-07-01T09:30:00Z',
  },
  {
    id: 'demo-6',
    slug: 'proxy-authentication-methods',
    title: 'Proxy Authentication Methods Explained: IP Whitelist vs Username/Password',
    excerpt: 'IP whitelisting vs username/password — which proxy authentication method is right for your use case.',
    content: '',
    cover_image_url: '/blog/cover-6.png',
    author: 'Oyebiyi Ayomide',
    status: 'published',
    view_count: 0,
    updated_at: '2026-07-05T10:00:00Z',
    tags: ['security', 'authentication', 'technical'],
    created_at: '2026-07-05T10:00:00Z',
    published_at: '2026-07-05T10:00:00Z',
  },
  {
    id: 'demo-7',
    slug: '4g-mobile-proxies-social-media',
    title: '4G Mobile Proxies: The Secret Weapon for Social Media Automation',
    excerpt: 'How 4G mobile proxies from Nigerian carriers provide unmatched stealth for social media automation.',
    content: '',
    cover_image_url: '/blog/cover-7.png',
    author: 'Oyebiyi Ayomide',
    status: 'published',
    view_count: 0,
    updated_at: '2026-07-08T08:00:00Z',
    tags: ['mobile', 'social-media', '4g', 'nigeria'],
    created_at: '2026-07-08T08:00:00Z',
    published_at: '2026-07-08T08:00:00Z',
  },
  {
    id: 'demo-8',
    slug: 'speed-vs-security-proxy-tradeoff',
    title: 'Speed vs Security: The Proxy Trade-off You Need to Understand',
    excerpt: 'Optimize your proxy setup by understanding the real trade-offs between speed and security.',
    content: '',
    cover_image_url: '/blog/cover-8.png',
    author: 'Oyebiyi Ayomide',
    status: 'published',
    view_count: 0,
    updated_at: '2026-07-10T11:00:00Z',
    tags: ['security', 'speed', 'performance'],
    created_at: '2026-07-10T11:00:00Z',
    published_at: '2026-07-10T11:00:00Z',
  },
  {
    id: 'demo-9',
    slug: 'bypassing-geo-restrictions-nigeria',
    title: 'Bypassing Geo-Restrictions: A Practical Guide for Nigerian Internet Users',
    excerpt: 'A clear-eyed look at how proxies help Nigerian users access geo-restricted content legally.',
    content: '',
    cover_image_url: '/blog/cover-9.png',
    author: 'Oyebiyi Ayomide',
    status: 'published',
    view_count: 0,
    updated_at: '2026-07-12T09:00:00Z',
    tags: ['geo-restrictions', 'privacy', 'legal'],
    created_at: '2026-07-12T09:00:00Z',
    published_at: '2026-07-12T09:00:00Z',
  },
  {
    id: 'demo-10',
    slug: 'nigeria-africa-proxy-hub',
    title: 'Why Nigeria Is Becoming Africa\'s Proxy Hub',
    excerpt: 'How Nigeria is positioning itself as Africa\'s premier destination for quality proxy services.',
    content: '',
    cover_image_url: '/blog/cover-10.png',
    author: 'Oyebiyi Ayomide',
    status: 'published',
    view_count: 0,
    updated_at: '2026-07-14T10:00:00Z',
    tags: ['nigeria', 'africa', 'market', 'trends'],
    created_at: '2026-07-14T10:00:00Z',
    published_at: '2026-07-14T10:00:00Z',
  },
];

export default function BlogPage() {
  const [posts, setPosts] = useState<BlogPost[]>(DEMO_POSTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(3);

  useEffect(() => {
    async function fetchPosts() {
      setLoading(true);
      const result = await api.getBlogPosts(page, 9);
      if (result.data) {
        setPosts(result.data.posts);
        setTotalPages(Math.ceil(result.data.pagination.total_items / 9));
      } else if (result.error) {
        // API unavailable — show demo posts
        setPosts(DEMO_POSTS);
        setTotalPages(Math.ceil(DEMO_POSTS.length / 9));
      }
      setLoading(false);
    }
    fetchPosts();
  }, [page]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-24 pb-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="animate-pulse space-y-8">
            <div className="h-12 bg-[var(--card)] rounded-lg w-1/3"></div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="bg-[var(--card)] border border-[var(--border)] rounded-2xl overflow-hidden">
                  <div className="h-48 bg-[var(--border)]"></div>
                  <div className="p-6 space-y-4">
                    <div className="h-6 bg-[var(--border)] rounded w-3/4"></div>
                    <div className="h-4 bg-[var(--border)] rounded w-full"></div>
                    <div className="h-4 bg-[var(--border)] rounded w-2/3"></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen pt-24 pb-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-2xl font-bold mb-4">Unable to load blog posts</h1>
          <p className="text-[var(--muted)] mb-6">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-24 pb-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl sm:text-5xl font-bold mb-4">
            <span className="gradient-text">Blog</span>
          </h1>
          <p className="text-lg text-[var(--muted)] max-w-2xl mx-auto">
            Latest news, tutorials, and insights about proxies, automation, and staying anonymous online.
          </p>
        </div>

        {posts.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-[var(--card)] border border-[var(--border)] flex items-center justify-center">
              <svg className="w-8 h-8 text-[var(--muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold mb-2">No posts yet</h2>
            <p className="text-[var(--muted)]">Check back soon for new content!</p>
          </div>
        ) : (
          <>
            {/* Featured Post (first one) */}
            {posts[0] && (
              <Link href={`/blog/${posts[0].slug}`} className="block mb-12 group">
                <article className="relative bg-[var(--card)] border border-[var(--border)] rounded-2xl overflow-hidden hover:border-[var(--primary)] transition-all">
                  <div className="grid lg:grid-cols-2 gap-0">
                    <div className="relative h-64 lg:h-80">
                      {posts[0].cover_image_url ? (
                        <Image
                          src={posts[0].cover_image_url}
                          alt={posts[0].title}
                          fill
                          className="object-cover"
                        />
                      ) : (
                        <div className="absolute inset-0 bg-gradient-to-br from-[var(--primary)]/20 to-[var(--accent)]/20 flex items-center justify-center">
                          <svg className="w-16 h-16 text-[var(--primary)]/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                          </svg>
                        </div>
                      )}
                    </div>
                    <div className="p-8 lg:p-12 flex flex-col justify-center">
                      <div className="flex items-center gap-3 mb-4">
                        {posts[0].tags && posts[0].tags[0] && (
                          <span className="px-3 py-1 text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] rounded-full">
                            {posts[0].tags[0]}
                          </span>
                        )}
                        <span className="text-sm text-[var(--muted)]">
                          {formatDate(posts[0].published_at || posts[0].created_at)}
                        </span>
                      </div>
                      <h2 className="text-2xl lg:text-3xl font-bold mb-4 group-hover:text-[var(--primary)] transition-colors">
                        {posts[0].title}
                      </h2>
                      <p className="text-[var(--muted)] line-clamp-3 mb-6">
                        {posts[0].excerpt}
                      </p>
                      <div className="flex items-center text-[var(--primary)] font-medium">
                        Read Article →
                      </div>
                    </div>
                  </div>
                </article>
              </Link>
            )}

            {/* Grid of remaining posts */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
              {posts.slice(1).map((post) => (
                <Link key={post.id} href={`/blog/${post.slug}`} className="group">
                  <article className="h-full bg-[var(--card)] border border-[var(--border)] rounded-2xl overflow-hidden hover:border-[var(--primary)] transition-all">
                    <div className="relative h-48">
                      {post.cover_image_url ? (
                        <Image
                          src={post.cover_image_url}
                          alt={post.title}
                          fill
                          className="object-cover"
                        />
                      ) : (
                        <div className="absolute inset-0 bg-gradient-to-br from-[var(--primary)]/10 to-[var(--accent)]/10 flex items-center justify-center">
                          <svg className="w-12 h-12 text-[var(--primary)]/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                          </svg>
                        </div>
                      )}
                    </div>
                    <div className="p-6">
                      <div className="flex items-center gap-3 mb-3">
                        {post.tags && post.tags[0] && (
                          <span className="px-2 py-0.5 text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] rounded-full">
                            {post.tags[0]}
                          </span>
                        )}
                        <span className="text-xs text-[var(--muted)]">
                          {formatDate(post.published_at || post.created_at)}
                        </span>
                      </div>
                      <h3 className="text-lg font-bold mb-2 group-hover:text-[var(--primary)] transition-colors line-clamp-2">
                        {post.title}
                      </h3>
                      <p className="text-sm text-[var(--muted)] line-clamp-2">
                        {post.excerpt}
                      </p>
                    </div>
                  </article>
                </Link>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 bg-[var(--card)] border border-[var(--border)] rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:border-[var(--primary)] transition-colors"
                >
                  ← Previous
                </button>
                <span className="px-4 py-2 text-[var(--muted)]">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 bg-[var(--card)] border border-[var(--border)] rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:border-[var(--primary)] transition-colors"
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
