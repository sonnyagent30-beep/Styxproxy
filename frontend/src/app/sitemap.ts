import { MetadataRoute } from 'next';
import { api } from '@/lib/api';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com';

// Force dynamic — sitemap is built at request time so it can call the live API.
// Without this, build-time fetch fails on Vercel (no API server in build context)
// and the route silently serves an empty/404 result.
export const dynamic = 'force-dynamic';
export const revalidate = 3600; // refresh hourly

// Static pages always included
const staticPages: MetadataRoute.Sitemap = [
  { url: BASE_URL, lastModified: new Date(), changeFrequency: 'weekly', priority: 1 },
  { url: `${BASE_URL}/about`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.8 },
  { url: `${BASE_URL}/pricing`, lastModified: new Date(), changeFrequency: 'weekly', priority: 0.9 },
  { url: `${BASE_URL}/blog`, lastModified: new Date(), changeFrequency: 'daily', priority: 0.9 },
  { url: `${BASE_URL}/how-it-works`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.7 },
  { url: `${BASE_URL}/contact`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.6 },
  { url: `${BASE_URL}/products`, lastModified: new Date(), changeFrequency: 'weekly', priority: 0.8 },
  { url: `${BASE_URL}/order`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.7 },
  { url: `${BASE_URL}/manage`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.5 },
  { url: `${BASE_URL}/legal`, lastModified: new Date(), changeFrequency: 'yearly', priority: 0.3 },
  { url: `${BASE_URL}/cookie-policy`, lastModified: new Date(), changeFrequency: 'yearly', priority: 0.3 },
  { url: `${BASE_URL}/refund-policy`, lastModified: new Date(), changeFrequency: 'yearly', priority: 0.3 },
];

async function getBlogPosts(): Promise<MetadataRoute.Sitemap> {
  try {
    const result = await api.getBlogPosts(1, 100);
    if (!result.data?.posts) return [];

    return result.data.posts.map((post) => ({
      url: `${BASE_URL}/blog/${post.slug}`,
      lastModified: new Date(post.updated_at || post.created_at),
      changeFrequency: 'monthly' as const,
      priority: 0.7,
    }));
  } catch {
    // If API is down, return empty — don't block sitemap generation
    console.error('[sitemap] Failed to fetch blog posts');
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [blogPosts] = await Promise.all([getBlogPosts()]);

  return [...staticPages, ...blogPosts];
}
