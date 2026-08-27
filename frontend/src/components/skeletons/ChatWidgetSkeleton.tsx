'use client';

export function ChatWidgetSkeleton() {
  return (
    <div className="fixed bottom-6 right-6 z-50">
      <div className="w-14 h-14 rounded-full bg-[var(--primary)]/30 animate-pulse" />
    </div>
  );
}

export function HeaderSkeleton() {
  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--background)]/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="w-32 h-8 bg-[var(--card)] rounded animate-pulse" />
        <div className="flex gap-4">
          <div className="w-16 h-8 bg-[var(--card)] rounded animate-pulse" />
          <div className="w-16 h-8 bg-[var(--card)] rounded animate-pulse" />
          <div className="w-16 h-8 bg-[var(--card)] rounded animate-pulse" />
        </div>
      </div>
    </header>
  );
}

export function HeroSkeleton() {
  return (
    <section className="relative py-24 lg:py-32 px-6">
      <div className="max-w-6xl mx-auto text-center space-y-6">
        <div className="w-3/4 h-12 bg-[var(--card)] rounded mx-auto animate-pulse" />
        <div className="w-2/3 h-6 bg-[var(--card)] rounded mx-auto animate-pulse" />
        <div className="w-1/2 h-6 bg-[var(--card)] rounded mx-auto animate-pulse" />
        <div className="flex gap-4 justify-center mt-8">
          <div className="w-32 h-12 bg-[var(--primary)]/30 rounded animate-pulse" />
          <div className="w-32 h-12 bg-[var(--card)] rounded animate-pulse" />
        </div>
      </div>
    </section>
  );
}

export function ProductCardSkeleton() {
  return (
    <div className="rounded-2xl bg-[var(--card)] border border-[var(--border)] p-6 space-y-4">
      <div className="w-12 h-12 bg-[var(--surface)] rounded-full animate-pulse" />
      <div className="w-3/4 h-6 bg-[var(--surface)] rounded animate-pulse" />
      <div className="space-y-2">
        <div className="w-full h-4 bg-[var(--surface)] rounded animate-pulse" />
        <div className="w-5/6 h-4 bg-[var(--surface)] rounded animate-pulse" />
      </div>
      <div className="w-1/3 h-8 bg-[var(--surface)] rounded animate-pulse" />
    </div>
  );
}

export function BlogPostCardSkeleton() {
  return (
    <div className="rounded-2xl bg-[var(--card)] border border-[var(--border)] overflow-hidden">
      <div className="aspect-[16/9] bg-[var(--surface)] animate-pulse" />
      <div className="p-5 space-y-3">
        <div className="w-1/4 h-3 bg-[var(--surface)] rounded animate-pulse" />
        <div className="w-3/4 h-5 bg-[var(--surface)] rounded animate-pulse" />
        <div className="w-full h-4 bg-[var(--surface)] rounded animate-pulse" />
        <div className="w-2/3 h-4 bg-[var(--surface)] rounded animate-pulse" />
      </div>
    </div>
  );
}

export function FooterSkeleton() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--card)] py-12 px-6">
      <div className="max-w-7xl mx-auto grid grid-cols-4 gap-8">
        <div className="space-y-4">
          <div className="w-32 h-6 bg-[var(--surface)] rounded animate-pulse" />
          <div className="w-full h-4 bg-[var(--surface)] rounded animate-pulse" />
          <div className="w-2/3 h-4 bg-[var(--surface)] rounded animate-pulse" />
        </div>
        {[1, 2, 3].map(i => (
          <div key={i} className="space-y-3">
            <div className="w-24 h-5 bg-[var(--surface)] rounded animate-pulse" />
            <div className="w-full h-4 bg-[var(--surface)] rounded animate-pulse" />
            <div className="w-full h-4 bg-[var(--surface)] rounded animate-pulse" />
            <div className="w-2/3 h-4 bg-[var(--surface)] rounded animate-pulse" />
          </div>
        ))}
      </div>
    </footer>
  );
}
