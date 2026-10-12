import LatestBlogPosts from '@/components/LatestBlogPosts';
import { api } from '@/lib/api';
import type { BlogPost } from '@/types';

export const dynamic = 'force-dynamic';

export default async function LatestBlogPostsServer() {
  let posts: BlogPost[] = [];
  try {
    const result = await api.getBlogPosts(1, 3);
    if (result.data?.posts) {
      posts = result.data.posts;
    }
  } catch {
    // render nothing on error
  }
  return <LatestBlogPosts initialPosts={posts} />;
}
