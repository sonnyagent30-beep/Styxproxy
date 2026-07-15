import { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { api } from '@/lib/api';
import { getDemoPostBySlug, DEMO_POSTS } from '@/data/blog-posts';
import type { BlogPost } from '@/types';
import TagPill from '@/components/blog/TagPill';
import ShareButtons from '@/components/blog/ShareButtons';
import PostNav from '@/components/blog/PostNav';

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

  // Find prev/next (chronological: previous is older, next is newer)
  const sorted = [...DEMO_POSTS].sort(
    (a, b) => new Date(b.published_at || b.created_at).getTime() -
               new Date(a.published_at || a.created_at).getTime()
  );
  const idx = sorted.findIndex(p => p.slug === slug);
  const prev = idx < sorted.length - 1 ? sorted[idx + 1] : null;
  const next = idx > 0 ? sorted[idx - 1] : null;

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-8 pb-16">
        {/* Back link */}
        <Link
          href="/blog"
          className="inline-flex items-center gap-1.5 text-sm text-[var(--muted)] hover:text-[var(--primary)] transition-colors mb-8"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          All posts
        </Link>

        {/* Cover image */}
        {post.cover_image_url && (
          <div className="relative w-full aspect-[16/9] overflow-hidden rounded-xl bg-[var(--surface)] mb-10">
            <Image
              src={post.cover_image_url}
              alt={post.title}
              fill
              priority
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 896px"
            />
          </div>
        )}

        {/* Tags */}
        {post.tags && post.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-5">
            {post.tags.map((tag) => (
              <TagPill key={tag} tag={tag} />
            ))}
          </div>
        )}

        {/* Title */}
        <h1
          className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-[-0.03em] leading-[1.1] mb-6"
          style={{ textWrap: 'balance' }}
        >
          {post.title}
        </h1>

        {/* Meta */}
        <div className="flex items-center gap-3 pb-8 border-b border-[var(--border)] mb-10">
          <div className="w-10 h-10 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-bold flex-shrink-0">
            {post.author?.charAt(0)}
          </div>
          <div>
            <p className="text-sm font-medium text-white">{post.author}</p>
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

        {/* Article body — centered editorial column, max ~65ch */}
        <article
          className="prose-styx max-w-[65ch] mx-auto"
          dangerouslySetInnerHTML={{ __html: post.content }}
        />

        {/* Share buttons — inline, centered */}
        <div className="max-w-[65ch] mx-auto">
          <ShareButtons title={post.title} slug={post.slug} />
        </div>

        {/* Prev / next */}
        <PostNav prev={prev} next={next} />
      </main>
    </>
  );
}
