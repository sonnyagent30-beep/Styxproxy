'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import api from '@/lib/api';
import type { GlobalSearchResult, GlobalSearchResponse } from '@/types';

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const query = searchParams.get('q') || '';
  
  const [results, setResults] = useState<GlobalSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState(query);

  const performSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults(null);
      return;
    }
    
    setLoading(true);
    setError('');
    
    const result = await api.globalSearch(q);
    
    if (result.error) {
      setError(result.error);
    } else {
      setResults(result.data || null);
    }
    
    setLoading(false);
  }, []);

  useEffect(() => {
    if (query) {
      setSearchQuery(query);
      performSearch(query);
    } else {
      setResults(null);
    }
  }, [query, performSearch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/admin/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  // Group results by type
  const customers = results?.results.filter(r => r.type === 'customer') || [];
  const orders = results?.results.filter(r => r.type === 'order') || [];
  const tickets = results?.results.filter(r => r.type === 'ticket') || [];
  const contactSubmissions = results?.results.filter(r => r.type === 'contact_submission') || [];

  const hasResults = results && results.results.length > 0;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl lg:text-4xl font-bold mb-2">Search Results</h1>
        <p className="text-[var(--muted)]">Search across customers, orders, tickets, and contact submissions</p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="mb-8">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search customers, orders, tickets..."
              className="w-full px-4 py-3 pl-12 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)] text-[var(--foreground)]"
            />
            <svg className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <button
            type="submit"
            disabled={loading || !searchQuery.trim()}
            className="px-6 py-3 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={() => setError('')} className="ml-4 text-red-300 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="space-y-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="h-6 bg-[var(--card-hover)] rounded w-32 mb-4"></div>
              <div className="space-y-3">
                <div className="h-20 bg-[var(--card)] rounded-xl border border-[var(--border)]"></div>
                <div className="h-20 bg-[var(--card)] rounded-xl border border-[var(--border)]"></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No Query */}
      {!loading && !query && (
        <div className="text-center py-12 text-[var(--muted)]">
          <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p>Enter a search term to find customers, orders, tickets, and more</p>
        </div>
      )}

      {/* No Results */}
      {!loading && query && !hasResults && (
        <div className="text-center py-12 text-[var(--muted)]">
          <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>No results for '{query}'</p>
        </div>
      )}

      {/* Results */}
      {!loading && hasResults && (
        <div className="grid md:grid-cols-2 gap-6">
          {/* Customers */}
          {customers.length > 0 && (
            <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
              <div className="p-4 border-b border-[var(--border)]">
                <h2 className="font-semibold flex items-center gap-2">
                  <span>👥</span> Customers ({customers.length})
                </h2>
              </div>
              <div className="divide-y divide-[var(--border)]">
                {customers.map((result) => (
                  <a
                    key={result.id}
                    href={result.url || '#'}
                    className="block p-4 hover:bg-[var(--card-hover)] transition-colors"
                  >
                    <p className="font-medium">{result.title}</p>
                    <p className="text-sm text-[var(--muted)]">{result.subtitle}</p>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Orders */}
          {orders.length > 0 && (
            <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
              <div className="p-4 border-b border-[var(--border)]">
                <h2 className="font-semibold flex items-center gap-2">
                  <span>📦</span> Orders ({orders.length})
                </h2>
              </div>
              <div className="divide-y divide-[var(--border)]">
                {orders.map((result) => (
                  <a
                    key={result.id}
                    href={result.url || '#'}
                    className="block p-4 hover:bg-[var(--card-hover)] transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-medium font-mono text-sm">{result.title}</p>
                    </div>
                    <p className="text-sm text-[var(--muted)]">{result.subtitle}</p>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Tickets */}
          {tickets.length > 0 && (
            <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
              <div className="p-4 border-b border-[var(--border)]">
                <h2 className="font-semibold flex items-center gap-2">
                  <span>🎫</span> Tickets ({tickets.length})
                </h2>
              </div>
              <div className="divide-y divide-[var(--border)]">
                {tickets.map((result) => (
                  <a
                    key={result.id}
                    href={result.url || '#'}
                    className="block p-4 hover:bg-[var(--card-hover)] transition-colors"
                  >
                    <p className="font-medium">{result.title}</p>
                    <p className="text-sm text-[var(--muted)]">{result.subtitle}</p>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Contact Submissions */}
          {contactSubmissions.length > 0 && (
            <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
              <div className="p-4 border-b border-[var(--border)]">
                <h2 className="font-semibold flex items-center gap-2">
                  <span>📬</span> Contact Submissions ({contactSubmissions.length})
                </h2>
              </div>
              <div className="divide-y divide-[var(--border)]">
                {contactSubmissions.map((result) => (
                  <a
                    key={result.id}
                    href={result.url || '#'}
                    className="block p-4 hover:bg-[var(--card-hover)] transition-colors"
                  >
                    <p className="font-medium">{result.title}</p>
                    <p className="text-sm text-[var(--muted)]">{result.subtitle}</p>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Summary */}
      {!loading && hasResults && (
        <div className="mt-6 p-4 rounded-xl bg-[var(--primary)]/10 border border-[var(--primary)]/30">
          <p className="text-sm">
            Found <span className="font-bold">{results?.total || 0}</span> results for '{query}'
          </p>
        </div>
      )}
    </div>
  );
}
