import { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { api } from '@/lib/api';
import { getDemoPostBySlug, DEMO_POSTS } from '@/data/blog-posts';
import type { BlogPost } from '@/types';
import ShareSidebar from '@/components/blog/ShareSidebar';
import PrevNextNav from '@/components/blog/PrevNextNav';
import RelatedPosts from '@/components/blog/RelatedPosts';

interface Props {
  params: Promise<{ slug: string }>;
}

function generateJsonLd(post: BlogPost, siteUrl: string) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: post.title,
    description: post.excerpt,
    image: post.cover_image_url ? `${siteUrl}${post.cover_image_url}` : `${siteUrl}/og-image.png`,
    datePublished: post.published_at || post.created_at,
    dateModified: post.updated_at,
    author: { '@type': 'Person', name: post.author },
    publisher: {
      '@type': 'Organization',
      name: 'Styxproxy',
      logo: { '@type': 'ImageObject', url: `${siteUrl}/logo.png` },
    },
    mainEntityOfPage: { '@type': 'WebPage', '@id': `${siteUrl}/blog/${post.slug}` },
  };
}

function estimateReadTime(content: string): number {
  const words = content.replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 200));
}

async function resolvePost(slug: string): Promise<BlogPost | null> {
  try {
    const result = await api.getBlogPost(slug);
    if (result.data) return result.data;
  } catch (_) {}
  return getDemoPostBySlug(slug) || null;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = await resolvePost(slug);
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com';

  if (!post) return { title: 'Post Not Found | Styxproxy Blog' };

  return {
    title: `${post.title} | Styxproxy Blog`,
    description: post.excerpt,
    keywords: post.tags || ['proxy', 'automation'],
    authors: [{ name: post.author }],
    openGraph: {
      type: 'article',
      url: `${siteUrl}/blog/${post.slug}`,
      title: post.title,
      description: post.excerpt,
      images: [{
        url: post.cover_image_url ? `${siteUrl}${post.cover_image_url}` : `${siteUrl}/og-image.png`,
        width: 1200,
        height: 630,
        alt: post.title,
      }],
      siteName: 'Styxproxy',
      publishedTime: post.published_at,
      modifiedTime: post.updated_at,
    },
    twitter: {
      card: 'summary_large_image',
      title: post.title,
      description: post.excerpt,
      images: [post.cover_image_url ? `${siteUrl}${post.cover_image_url}` : `${siteUrl}/og-image.png`],
    },
  };
}

export async function generateStaticParams() {
  return DEMO_POSTS.map((post) => ({ slug: post.slug }));
}

export default async function BlogPostPage({ params }: Props) {
  const { slug } = await params;
  const post = await resolvePost(slug);
  if (!post) notFound();

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com';
  const jsonLd = generateJsonLd(post, siteUrl);
  const readTime = estimateReadTime(post.content || post.excerpt || '');

  // Find prev/next
  const sorted = DEMO_POSTS.sort(
    (a, b) => new Date(b.published_at || b.created_at).getTime() -
               new Date(a.published_at || a.created_at).getTime()
  );
  const idx = sorted.findIndex(p => p.slug === slug);
  const prev = idx < sorted.length - 1 ? sorted[idx + 1] : null;
  const next = idx > 0 ? sorted[idx - 1] : null;

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <ShareSidebar title={post.title} url={post.slug} />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        {/* Back link */}
        <Link
          href="/blog"
          className="inline-flex items-center gap-1 text-sm text-[var(--muted)] hover:text-[var(--accent)] transition-colors mb-6"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          All posts
        </Link>

        {/* Cover image */}
        {post.cover_image_url && (
          <div className="relative w-full h-64 sm:h-80 rounded-2xl overflow-hidden mb-8">
            <Image
              src={post.cover_image_url}
              alt={post.title}
              fill
              priority
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 768px"
            />
          </div>
        )}

        {/* Tags */}
        {post.tags && post.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {post.tags.map((tag) => (
              <Link
                key={tag}
                href={`/blog/tag/${encodeURIComponent(tag)}`}
                className="px-3 py-1 rounded-full text-xs font-medium bg-[var(--surface)] border border-[var(--border)] text-[var(--accent)] hover:bg-[var(--accent)] hover:text-white transition-all"
              >
                #{tag}
              </Link>
            ))}
          </div>
        )}

        {/* Title */}
        <h1 className="text-2xl sm:text-3xl font-bold text-[var(--foreground)] mb-4 leading-tight">
          {post.title}
        </h1>

        {/* Meta row */}
        <div className="flex items-center gap-3 pb-6 border-b border-[var(--border)] mb-8">
          <div className="w-9 h-9 rounded-full bg-[var(--accent)] flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
            {post.author?.charAt(0)}
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--foreground)]">{post.author}</p>
            <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
              <time dateTime={post.published_at || post.created_at}>
                {new Date(post.published_at || post.created_at).toLocaleDateString('en-US', {
                  month: 'long',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </time>
              <span>·</span>
              <span>{readTime} min read</span>
            </div>
          </div>
        </div>

        {/* Content */}
        <div
          className="prose prose-invert max-w-none"
          dangerouslySetInnerHTML={{ __html: post.content }}
        />

        {/* Prev/Next navigation */}
        <PrevNextNav prev={prev} next={next} />

        {/* Related posts */}
        <RelatedPosts posts={DEMO_POSTS} excludeSlug={slug} />
      </main>
    </>
  );
}
