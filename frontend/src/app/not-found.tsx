'use client';

import Link from 'next/link';

export default function NotFound() {
  return (
    <main className="flex-1 flex items-start justify-center px-4 pt-32">
      <div className="text-center max-w-md w-full">
        {/* 404 Typography */}
        <div className="mb-8">
          <h1 className="text-[10rem] sm:text-[14rem] font-black leading-none text-[var(--card-hover)] select-none">
            404
          </h1>
        </div>

        {/* Message */}
        <div className="-mt-6 mb-8">
          <h2 className="text-2xl font-bold mb-3">
            Lost in the <span className="gradient-text">Styx</span>
          </h2>
          <p className="text-[var(--muted)] text-sm leading-relaxed">
            The page you&apos;re looking for has drifted beyond the river&apos;s edge.
            It may have moved, been removed, or never existed.
          </p>
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <Link
            href="/"
            className="block w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors"
          >
            Cross Back Home
          </Link>
          <Link
            href="/order"
            className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-xl transition-colors"
          >
            Order Proxies
          </Link>
        </div>
      </div>
    </main>
  );
}
