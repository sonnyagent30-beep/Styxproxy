import { Metadata } from 'next';
import { api } from '@/lib/api';
import BlogFeed from '@/components/blog/BlogFeed';

export const metadata: Metadata = {
  title: 'Blog | Styxproxy',
  description: 'Notes on proxies, automation, anonymity, and building infrastructure that works.',
  openGraph: {
    title: 'Blog | Styxproxy',
    description: 'Notes on proxies, automation, anonymity, and building infrastructure that works.',
    type: 'website',
    siteName: 'Styxproxy',
  },
};

async function getPosts() {
  // Single source of truth: the api. No demo fallback (P0-6).
  // If the api is down we want the admin to see "no posts" + an error
  // message, not silently serve fake content that masks the outage.
  const result = await api.getBlogPosts(1, 9);
  return result.data || { posts: [], pagination: { page: 1, limit: 9, total_items: 0, total_pages: 0, has_next: false, has_prev: false } };
}

async function getTags(): Promise<string[]> {
  const result = await api.getBlogPosts(1, 100);
  if (result.data && result.data.posts.length > 0) {
    const tagSet = new Set<string>();
    result.data.posts.forEach((post) => {
      (post.tags || []).forEach((tag) => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }
  return [];
}

export const dynamic = 'force-dynamic';

export default async function BlogPage() {
  const [postsData, tags] = await Promise.all([getPosts(), getTags()]);

  return (
    <BlogFeed
      initialPosts={postsData.posts}
      initialTags={tags}
      initialPage={1}
      hasMore={postsData.pagination.has_next}
    />
  );
}
