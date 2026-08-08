'use client';

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { ApiResponse } from '@/types';

type FunnelStage = {
  stage: string;
  count: number;
  conversion_rate: number | null;
};

type FunnelData = {
  total_events: number;
  stages: FunnelStage[];
  period_days: number;
};

type AnalyticsEvent = {
  id: number;
  event_name: string;
  session_id: string | null;
  customer_phone: string | null;
  country: string | null;
  plan_code: string | null;
  channel: string;
  meta: Record<string, unknown>;
  created_at: string;
};

const FUNNEL_STAGE_LABELS: Record<string, string> = {
  page_view: 'Page View',
  plan_viewed: 'Plan Viewed',
  cart_added: 'Added to Cart',
  checkout_started: 'Checkout Started',
  payment_link_sent: 'Payment Link Sent',
  payment_completed: 'Payment Completed',
  trial_claimed: 'Trial Claimed',
};

const EVENT_COLORS: Record<string, string> = {
  page_view: '#6366f1',
  plan_viewed: '#8b5cf6',
  cart_added: '#f59e0b',
  checkout_started: '#f97316',
  payment_link_sent: '#3b82f6',
  payment_completed: '#22c55e',
  trial_claimed: '#14b8a6',
};

export default function AdminAnalyticsPage() {
  const [funnelData, setFunnelData] = useState<FunnelData | null>(null);
  const [events, setEvents] = useState<AnalyticsEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [eventFilter, setEventFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [totalEvents, setTotalEvents] = useState(0);
  const limit = 30;

  const loadFunnel = useCallback(async () => {
    const res = await api.getAnalyticsFunnel() as ApiResponse<FunnelData>;
    if (res.error) {
      setError(res.error);
    } else {
      setFunnelData(res.data || null);
    }
  }, []);

  const loadEvents = useCallback(async () => {
    const res = await api.getAnalyticsEvents(page, limit, eventFilter) as ApiResponse<{ events: AnalyticsEvent[]; total: number }>;
    if (!res.error) {
      setEvents(res.data?.events || []);
      setTotalEvents(res.data?.total || 0);
    }
  }, [page, eventFilter]);

  useEffect(() => {
    Promise.all([loadFunnel(), loadEvents()]).finally(() => setLoading(false));
  }, [loadFunnel, loadEvents]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-[var(--muted)]">Loading analytics...</div>
      </div>
    );
  }

  const filteredFunnel = funnelData?.stages.filter(s =>
    eventFilter === 'all' || s.stage === eventFilter
  ) || [];

  const maxCount = Math.max(...(filteredFunnel.map(s => s.count) || [1]));

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <div className="p-6 max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Analytics</h1>
            <p className="text-[var(--muted)] mt-1">
              Customer journey funnel — {funnelData?.period_days || 30} day period
            </p>
          </div>
          <div className="flex gap-2">
            <select
              value={eventFilter}
              onChange={e => { setEventFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 rounded-lg bg-[var(--card)] border border-[var(--border)] text-sm"
            >
              <option value="all">All events</option>
              {Object.keys(FUNNEL_STAGE_LABELS).map(s => (
                <option key={s} value={s}>{FUNNEL_STAGE_LABELS[s]}</option>
              ))}
            </select>
            <button
              onClick={() => { setLoading(true); Promise.all([loadFunnel(), loadEvents()]).finally(() => setLoading(false)); }}
              className="px-4 py-2 rounded-lg bg-[var(--card)] border border-[var(--border)] text-sm hover:bg-[var(--card-hover)]"
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Funnel */}
        <div className="bg-[var(--card)] rounded-xl border border-[var(--border)] p-6">
          <h2 className="text-lg font-semibold mb-6">Conversion Funnel</h2>

          {filteredFunnel.length === 0 ? (
            <p className="text-[var(--muted)] text-sm py-8 text-center">
              No funnel data yet. Once customers start flowing through the site, data will appear here.
            </p>
          ) : (
            <div className="space-y-4">
              {filteredFunnel.map((stage) => {
                const pct = maxCount > 0 ? (stage.count / maxCount) * 100 : 0;
                const convPct = stage.conversion_rate !== null
                  ? `${(stage.conversion_rate * 100).toFixed(1)}%`
                  : '—';
                const color = EVENT_COLORS[stage.stage] || '#6366f1';

                return (
                  <div key={stage.stage} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">
                        {FUNNEL_STAGE_LABELS[stage.stage] || stage.stage}
                      </span>
                      <div className="flex items-center gap-4 text-[var(--muted)]">
                        <span>{stage.count.toLocaleString()} users</span>
                        <span className="text-xs px-2 py-0.5 rounded bg-[var(--background)]">
                          {convPct} conversion
                        </span>
                      </div>
                    </div>
                    <div className="h-3 rounded-full bg-[var(--background)] overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Events Log */}
        <div className="bg-[var(--card)] rounded-xl border border-[var(--border)] p-6">
          <h2 className="text-lg font-semibold mb-4">
            Event Log — {totalEvents.toLocaleString()} total
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--muted)] border-b border-[var(--border)]">
                  <th className="pb-3 font-medium">Event</th>
                  <th className="pb-3 font-medium">Session</th>
                  <th className="pb-3 font-medium">Country</th>
                  <th className="pb-3 font-medium">Channel</th>
                  <th className="pb-3 font-medium">Plan</th>
                  <th className="pb-3 font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {events.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-[var(--muted)]">
                      No events recorded yet.
                    </td>
                  </tr>
                ) : events.map(event => (
                  <tr key={event.id} className="hover:bg-[var(--card-hover)]">
                    <td className="py-3">
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                        style={{
                          backgroundColor: `${EVENT_COLORS[event.event_name] || '#6366f1'}20`,
                          color: EVENT_COLORS[event.event_name] || '#6366f1',
                        }}
                      >
                        {FUNNEL_STAGE_LABELS[event.event_name] || event.event_name}
                      </span>
                    </td>
                    <td className="py-3 text-[var(--muted)] font-mono text-xs">
                      {event.session_id ? `${event.session_id.slice(0, 8)}...` : '—'}
                    </td>
                    <td className="py-3">{event.country || '—'}</td>
                    <td className="py-3 text-[var(--muted)]">{event.channel}</td>
                    <td className="py-3 text-[var(--muted)] text-xs">{event.plan_code || '—'}</td>
                    <td className="py-3 text-[var(--muted)] text-xs">
                      {new Date(event.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalEvents > limit && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-[var(--border)]">
              <span className="text-sm text-[var(--muted)]">
                Page {page} — {(page - 1) * limit + 1}–{Math.min(page * limit, totalEvents)} of {totalEvents.toLocaleString()}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1 rounded bg-[var(--card)] border border-[var(--border)] text-sm disabled:opacity-40"
                >
                  ← Prev
                </button>
                <button
                  disabled={page * limit >= totalEvents}
                  onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1 rounded bg-[var(--card)] border border-[var(--border)] text-sm disabled:opacity-40"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
