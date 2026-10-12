import LatestBlogPostsGraph from '@/components/LatestBlogPostsGraph';
import { api } from '@/lib/api';
import type { BlogCategory, BlogPost } from '@/types';

export const dynamic = 'force-dynamic';

export default async function LatestBlogPostsServer() {
  let posts: BlogPost[] = [];
  let categories: BlogCategory[] = [];
  try {
    const [postsResult, categoriesResult] = await Promise.all([
      api.getBlogPosts(1, 6),
      api.getBlogCategories(),
    ]);
    if (postsResult.data?.posts) {
      posts = postsResult.data.posts;
    }
    if (categoriesResult.data?.categories) {
      categories = categoriesResult.data.categories;
    }
  } catch {
    // render nothing on error
  }
  return <LatestBlogPostsGraph initialPosts={posts} categories={categories} />;
}
