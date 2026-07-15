import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { api } from '@/lib/api';
import { getDemoPostBySlug, DEMO_POSTS } from '@/data/blog-posts';
import BlogPostClient from './BlogPostClient';
import type { BlogPost } from '@/types';

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

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = await resolvePost(slug);
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com';

  if (!post) {
    return { title: 'Post Not Found | Styxproxy Blog' };
  }

  const imageUrl = post.cover_image_url
    ? `${siteUrl}${post.cover_image_url}`
    : `${siteUrl}/og-image.png`;

  return {
    title: post.title,
    description: post.excerpt,
    keywords: post.tags || ['proxy', 'automation'],
    authors: [{ name: post.author }],
    openGraph: {
      type: 'article',
      url: `${siteUrl}/blog/${post.slug}`,
      title: post.title,
      description: post.excerpt,
      images: [{ url: imageUrl, width: 1200, height: 630, alt: post.title }],
      siteName: 'Styxproxy',
    },
    twitter: {
      card: 'summary_large_image',
      title: post.title,
      description: post.excerpt,
      images: [imageUrl],
    },
    alternates: { canonical: `${siteUrl}/blog/${post.slug}` },
  };
}

async function resolvePost(slug: string): Promise<BlogPost | null> {
  // Try API first
  try {
    const result = await api.getBlogPost(slug);
    if (result.data) return result.data;
  } catch (_) {
    // API unavailable — fall through to demo posts
  }

  // Fall back to demo posts (no DB needed)
  return getDemoPostBySlug(slug) || null;
}

export default async function BlogPostPage({ params }: Props) {
  const { slug } = await params;
  const post = await resolvePost(slug);

  if (!post) notFound();

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com';
  const jsonLd = generateJsonLd(post, siteUrl);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <BlogPostClient post={post} />
    </>
  );
}

// Static params so Next.js pre-renders all demo post pages
export async function generateStaticParams() {
  return DEMO_POSTS.map((post) => ({ slug: post.slug }));
}
