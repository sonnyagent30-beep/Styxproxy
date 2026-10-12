import { MetadataRoute } from 'next';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com';

// Keep this dynamic in case the build target caches a stale robots body.
// Robots content rarely changes — runtime cost is minimal.
export const dynamic = 'force-dynamic';
export const revalidate = 86400; // refresh daily

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin/', '/api/', '/api-proxy/', '/receipt/'],
      },
    ],
    sitemap: `${BASE_URL}/sitemap.xml`,
    host: BASE_URL,
  };
}
