
/* eslint-disable @next/next/no-html-link-for-pages, @typescript-eslint/no-explicit-any */
import { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { api } from '@/lib/api';
import type { BlogPost } from '@/types';
import TagPill from '@/components/blog/TagPill';
import EngagementRow from '@/components/blog/EngagementRow';

interface Props {
  params: Promise<{ slug: string }>;
}

const POST_AUTHOR = 'Styxproxy Team';

function generateJsonLd(post: BlogPost, siteUrl: string) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: post.title,
    description: post.excerpt,
    image: post.cover_image_url ? `${siteUrl}${post.cover_image_url}` : `${siteUrl}/og-image.png`,
    datePublished: post.published_at || post.created_at,
    dateModified: post.updated_at,
    author: { '@type': 'Person', name: POST_AUTHOR },
    publisher: {
      '@type': 'Organization',
      name: 'Styxproxy',
      logo: { '@type': 'ImageObject', url: `${siteUrl}/logo.png` },
    },
    mainEntityOfPage: { '@type': 'WebPage', '@id': `${siteUrl}/blog/${post.slug}` },
  };
}

// P0-6: BreadcrumbList JSON-LD for SEO. Read by Google for
// rich-result breadcrumb display in search.
function generateBreadcrumbJsonLd(post: BlogPost, siteUrl: string) {
  const cat = (post.tags && post.tags[0]) || null;
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: `${siteUrl}` },
      { '@type': 'ListItem', position: 2, name: 'Blog', item: `${siteUrl}/blog` },
      ...(cat
        ? [{ '@type': 'ListItem', position: 3, name: cat, item: `${siteUrl}/blog/tag/${encodeURIComponent(cat)}` }]
        : []),
      { '@type': 'ListItem', position: cat ? 4 : 3, name: post.title, item: `${siteUrl}/blog/${post.slug}` },
    ],
  };
}

function estimateReadTime(content: string): number {
  const words = content.replace(/<[^>]+>/g, '').split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 200));
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
}

async function resolvePost(slug: string): Promise<BlogPost | null> {
  try {
    const result = await api.getBlogPost(slug);
    if (result.data) return result.data;
  } catch (_) {}
  return null;
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
    authors: [{ name: POST_AUTHOR }],
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
  return [];
}

export default async function BlogPostPage({ params }: Props) {
  const { slug } = await params;
  const post = await resolvePost(slug);
  if (!post) notFound();

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com';
  const jsonLd = generateJsonLd(post, siteUrl);
  const readTime = estimateReadTime(post.content || post.excerpt || '');
  const breadcrumbJsonLd = generateBreadcrumbJsonLd(post, siteUrl);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
      />

      {/* Hero / Title Block */}
      <section className="relative overflow-hidden pt-16 pb-12 px-6">
        <div className="absolute inset-0 hero-bg-grid" aria-hidden="true" />
        <div className="absolute inset-0 hero-bg-rings" aria-hidden="true" />
        <div className="absolute inset-0 hero-bg-vignette" aria-hidden="true" />
        <div className="hero-orb hero-orb-1" aria-hidden="true" />
        <div className="hero-orb hero-orb-2" aria-hidden="true" />
        <div className="hero-orb hero-orb-3" aria-hidden="true" />

        <div className="relative max-w-3xl mx-auto">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-2 text-sm text-[var(--muted)] mb-6">
            <Link href="/blog" className="hover:text-[var(--primary)] transition-colors">
              Blog
            </Link>
            {post.tags && post.tags[0] && (
              <>
                <span>/</span>
                <Link
                  href={`/blog/tag/${encodeURIComponent(post.tags[0])}`}
                  className="hover:text-[var(--primary)] transition-colors"
                >
                  #{post.tags[0]}
                </Link>
              </>
            )}
          </nav>

          {/* Tags */}
          {post.tags && post.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-5">
              {post.tags.map((tag) => (
                <Link
                  key={tag}
                  href={`/blog/tag/${encodeURIComponent(tag)}`}
                  className="px-3 py-1 text-xs font-medium bg-[var(--card)] border border-[var(--border)] text-[var(--muted)] rounded-full hover:text-[var(--foreground)] hover:border-[var(--primary)]/60 transition-colors"
                >
                  #{tag}
                </Link>
              ))}
            </div>
          )}

          {/* Title — exactly one h1 per page */}
          <h1
            className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-[var(--foreground)] leading-[1.05] mb-6"
            style={{ textWrap: 'balance' }}
          >
            {post.title}
          </h1>

          {/* Excerpt */}
          <p className="text-lg sm:text-xl text-[var(--muted)] leading-relaxed mb-8 max-w-2xl">
            {post.excerpt}
          </p>

          {/* Author + meta */}
          <div className="flex items-center gap-3 pb-8 border-b border-[var(--border)]">
            <Link href={`/blog/author/${encodeURIComponent(POST_AUTHOR)}`} className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-full bg-[var(--primary)] flex items-center justify-center text-black font-black text-sm flex-shrink-0">
                S
              </div>
              <div>
                <p className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors">
                  Styxproxy Team
                </p>
                <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
                  <time dateTime={post.published_at || post.created_at}>
                    {formatDate(post.published_at || post.created_at)}
                  </time>
                  <span>·</span>
                  <span>{readTime} min read</span>
                </div>
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* Cover Image (below hero) */}
      {post.cover_image_url && (
        <div className="max-w-4xl mx-auto px-6 mt-10 mb-8">
          <div className="relative w-full aspect-[16/9] overflow-hidden rounded-2xl bg-[var(--surface)]">
            <Image
              src={post.cover_image_url}
              alt={post.title}
              fill
              priority
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 896px"
            />
          </div>
        </div>
      )}

      {/* Article body */}
      <article
        className="prose-styx max-w-[65ch] mx-auto px-6"
        dangerouslySetInnerHTML={{ __html: post.content }}
      />

      {/* Engagement row — inline reactions, save, share, link */}
      <EngagementRow
        postSlug={post.slug}
        postTitle={post.title}
        initialViews={post.view_count || 0}
      />

      {/* Tag cross-link — "explore more in #tag" */}
      {post.tags && post.tags.length > 0 && (
        <div className="mt-12 pt-8 border-t border-[var(--border)] max-w-[65ch] mx-auto px-6">
          <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider mb-4">
            Explore more
          </p>
          <div className="flex flex-wrap gap-2">
            {post.tags.map((tag) => (
              <TagPill key={tag} tag={tag} />
            ))}
          </div>
        </div>
      )}
    </>
  );
}
