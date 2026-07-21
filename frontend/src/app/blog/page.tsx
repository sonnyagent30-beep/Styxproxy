import { Metadata } from 'next';
import { api } from '@/lib/api';
import { DEMO_POSTS, getAllTags } from '@/data/blog-posts';
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
  try {
    const result = await api.getBlogPosts(1, 9);
    if (result.data && result.data.posts.length > 0) {
      return result.data;
    }
  } catch (err) {
    console.error('Failed to fetch blog posts:', err);
  }
  // Fallback to demo posts if API fails or returns empty
  const sortedDemo = [...DEMO_POSTS].sort(
    (a, b) =>
      new Date(b.published_at || b.created_at).getTime() -
      new Date(a.published_at || a.created_at).getTime()
  );
  return {
    posts: sortedDemo,
    pagination: {
      page: 1,
      limit: 9,
      total_items: sortedDemo.length,
      total_pages: 1,
      has_next: false,
      has_prev: false,
    },
  };
}

async function getTags(): Promise<string[]> {
  try {
    // Fetch all posts to extract unique tags
    const result = await api.getBlogPosts(1, 100);
    if (result.data && result.data.posts.length > 0) {
      const tagSet = new Set<string>();
      result.data.posts.forEach((post) => {
        (post.tags || []).forEach((tag) => tagSet.add(tag));
      });
      return Array.from(tagSet).sort();
    }
  } catch (err) {
    console.error('Failed to fetch tags:', err);
  }
  // Fallback
  return getAllTags();
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
