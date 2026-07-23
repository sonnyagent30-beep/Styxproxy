/**
 * Reusable skeleton components. Use these for loading states where
 * the real content is async (API fetches, image loads, etc).
 */

export function PostCardSkeleton() {
  return (
    <div
      className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl overflow-hidden animate-pulse"
      data-testid="post-card-skeleton"
    >
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="w-9 h-9 rounded-full bg-[var(--card)]" />
        <div className="flex-1 space-y-1.5">
          <div className="h-3 bg-[var(--card)] rounded w-1/3" />
          <div className="h-2 bg-[var(--card)] rounded w-1/2" />
        </div>
      </div>
      <div className="aspect-[4/5] bg-[var(--card)]" />
      <div className="p-4 space-y-2">
        <div className="h-4 bg-[var(--card)] rounded w-4/5" />
        <div className="h-3 bg-[var(--card)] rounded w-full" />
        <div className="h-3 bg-[var(--card)] rounded w-2/3" />
      </div>
    </div>
  );
}

export function PostCardSkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
      {Array.from({ length: count }).map((_, i) => (
        <PostCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function PostDetailSkeleton() {
  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-8 pb-16 animate-pulse">
      <div className="h-4 bg-[var(--card)] rounded w-1/4 mb-8" />
      <div className="aspect-[16/9] bg-[var(--card)] rounded-2xl mb-8" />
      <div className="space-y-3 mb-8">
        <div className="h-8 bg-[var(--card)] rounded w-3/4" />
        <div className="h-4 bg-[var(--card)] rounded w-1/2" />
      </div>
      <div className="space-y-3 max-w-[65ch] mx-auto">
        <div className="h-3 bg-[var(--card)] rounded w-full" />
        <div className="h-3 bg-[var(--card)] rounded w-full" />
        <div className="h-3 bg-[var(--card)] rounded w-4/5" />
        <div className="h-3 bg-[var(--card)] rounded w-full" />
        <div className="h-3 bg-[var(--card)] rounded w-3/4" />
      </div>
    </main>
  );
}

export function OrderSummarySkeleton() {
  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 animate-pulse">
      <div className="h-5 bg-[var(--card)] rounded w-1/3 mb-4" />
      <div className="space-y-2">
        <div className="h-3 bg-[var(--card)] rounded w-full" />
        <div className="h-3 bg-[var(--card)] rounded w-4/5" />
        <div className="h-3 bg-[var(--card)] rounded w-2/3" />
      </div>
    </div>
  );
}
