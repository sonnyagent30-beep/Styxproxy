import BlogCard from './BlogCard';
import type { BlogPost } from '@/types';

interface Props {
  posts: BlogPost[];
  excludeSlug: string;
}

export default function RelatedPosts({ posts, excludeSlug }: Props) {
  const related = posts.filter(p => p.slug !== excludeSlug).slice(0, 3);
  if (!related.length) return null;

  return (
    <section className="mt-16 pt-8 border-t border-[var(--border)]">
      <h3 className="text-lg font-bold text-[var(--foreground)] mb-6">Related Posts</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {related.map((post) => (
          <BlogCard key={post.id} post={post} />
        ))}
      </div>
    </section>
  );
}
