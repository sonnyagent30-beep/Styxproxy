'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import api from '@/lib/api';
import { CharonConversation, CharonLogEntry } from '@/types';

export default function CharonAdminPage() {
  const [activeTab, setActiveTab] = useState<'conversations' | 'logs' | 'stream'>('conversations');
  const [conversations, setConversations] = useState<CharonConversation[]>([]);
  const [logs, setLogs] = useState<CharonLogEntry[]>([]);
  const [totalConversations, setTotalConversations] = useState(0);
  const [totalLogs, setTotalLogs] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Filters
  const [filterConversationId, setFilterConversationId] = useState('');
  const [filterChannel, setFilterChannel] = useState('');
  const [filterEscalated, setFilterEscalated] = useState<boolean | null>(null);
  
  // Pagination
  const [page, setPage] = useState(1);
  const limit = 50;

  // SSE Stream
  const [streamEvents, setStreamEvents] = useState<Array<{ ts: string; data: unknown }>>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Load conversations
  const loadConversations = useCallback(async () => {
    setLoading(true);
    const result = await api.getCharonConversations(page, limit);
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setConversations(result.data.conversations);
      setTotalConversations(result.data.total);
    }
    setLoading(false);
  }, [page]);

  // Load logs
  const loadLogs = useCallback(async () => {
    setLoading(true);
    const result = await api.getCharonLogs(
      limit,
      (page - 1) * limit,
      filterConversationId || undefined,
      filterChannel || undefined,
      filterEscalated ?? undefined
    );
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setLogs(result.data.logs);
      setTotalLogs(result.data.total);
    }
    setLoading(false);
  }, [page, filterConversationId, filterChannel, filterEscalated]);

  // Connect to SSE stream
  const connectStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    
    const streamUrl = api.getCharonStreamUrl();
    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStreamEvents(prev => [...prev.slice(-99), { ts: new Date().toISOString(), data }]);
      } catch {
        // Ignore parse errors
      }
    };
    
    eventSource.onerror = () => {
      eventSource.close();
      // Try to reconnect after 3 seconds
      setTimeout(() => {
        if (activeTab === 'stream') {
          connectStream();
        }
      }, 3000);
    };
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'conversations') {
      loadConversations();
    } else if (activeTab === 'logs') {
      loadLogs();
    } else if (activeTab === 'stream') {
      connectStream();
    }
  }, [activeTab, loadConversations, loadLogs, connectStream]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const formatDate = (ts: string) => {
    if (!ts) return '-';
    return new Date(ts).toLocaleString();
  };

  return (
    <div className="min-h-screen pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">
            Charon <span className="gradient-text">Admin</span>
          </h1>
          <p className="text-[var(--muted)]">Monitor Charon conversations, logs, and live events</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex space-x-2 mb-6 overflow-x-auto">
          {(['conversations', 'logs', 'stream'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => { setActiveTab(tab); setPage(1); setError(''); }}
              className={`px-6 py-2 rounded-full font-medium capitalize transition-all whitespace-nowrap ${
                activeTab === tab
                  ? 'bg-[var(--primary)] text-black'
                  : 'bg-[var(--card)] text-[var(--muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          
          {/* Conversations Tab */}
          {activeTab === 'conversations' && (
            <div>
              <div className="mb-4 flex justify-between items-center">
                <p className="text-[var(--muted)]">{totalConversations} total conversations</p>
              </div>
              
              {loading ? (
                <div className="text-center py-12 text-[var(--muted)]">Loading...</div>
              ) : conversations.length === 0 ? (
                <div className="text-center py-12 text-[var(--muted)]">No conversations yet</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-[var(--muted)] text-sm border-b border-[var(--border)]">
                        <th className="pb-3 pr-4">Conversation ID</th>
                        <th className="pb-3 pr-4">Last Message</th>
                        <th className="pb-3 pr-4">Messages</th>
                        <th className="pb-3 pr-4">Last Activity</th>
                        <th className="pb-3">Escalated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {conversations.map((conv) => (
                        <tr key={conv.conversation_id} className="border-b border-[var(--border)]/50 hover:bg-[var(--card-hover)]">
                          <td className="py-3 pr-4 font-mono text-sm">{conv.conversation_id.slice(0, 12)}...</td>
                          <td className="py-3 pr-4 text-sm max-w-xs truncate">{conv.last_message}</td>
                          <td className="py-3 pr-4 text-sm">{conv.message_count}</td>
                          <td className="py-3 pr-4 text-sm text-[var(--muted)]">{formatDate(conv.last_message_at)}</td>
                          <td className="py-3">
                            {conv.escalated ? (
                              <span className="px-2 py-1 text-xs rounded-full bg-red-500/20 text-red-400">Yes</span>
                            ) : (
                              <span className="text-[var(--muted)]">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Logs Tab */}
          {activeTab === 'logs' && (
            <div>
              {/* Filters */}
              <div className="mb-6 flex flex-wrap gap-4">
                <input
                  type="text"
                  placeholder="Conversation ID"
                  value={filterConversationId}
                  onChange={(e) => setFilterConversationId(e.target.value)}
                  className="px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] text-sm focus:outline-none focus:border-[var(--primary)]"
                />
                <select
                  value={filterChannel}
                  onChange={(e) => setFilterChannel(e.target.value)}
                  className="px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] text-sm focus:outline-none focus:border-[var(--primary)]"
                >
                  <option value="">All Channels</option>
                  <option value="web">Web</option>
                  <option value="telegram">Telegram</option>
                  <option value="whatsapp">WhatsApp</option>
                </select>
                <select
                  value={filterEscalated === null ? '' : filterEscalated.toString()}
                  onChange={(e) => setFilterEscalated(e.target.value === '' ? null : e.target.value === 'true')}
                  className="px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] text-sm focus:outline-none focus:border-[var(--primary)]"
                >
                  <option value="">All Escalations</option>
                  <option value="true">Escalated</option>
                  <option value="false">Not Escalated</option>
                </select>
                <button
                  onClick={() => { setPage(1); loadLogs(); }}
                  className="px-4 py-2 rounded-lg bg-[var(--primary)] text-black font-medium text-sm hover:opacity-90"
                >
                  Apply Filters
                </button>
              </div>

              <div className="mb-4 flex justify-between items-center">
                <p className="text-[var(--muted)]">{totalLogs} total logs</p>
              </div>
              
              {loading ? (
                <div className="text-center py-12 text-[var(--muted)]">Loading...</div>
              ) : logs.length === 0 ? (
                <div className="text-center py-12 text-[var(--muted)]">No logs found</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-[var(--muted)] text-sm border-b border-[var(--border)]">
                        <th className="pb-3 pr-4">Time</th>
                        <th className="pb-3 pr-4">Channel</th>
                        <th className="pb-3 pr-4">User Message</th>
                        <th className="pb-3 pr-4">Response</th>
                        <th className="pb-3 pr-4">Scenario</th>
                        <th className="pb-3">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {logs.map((log, idx) => (
                        <tr key={idx} className="border-b border-[var(--border)]/50 hover:bg-[var(--card-hover)]">
                          <td className="py-3 pr-4 text-sm text-[var(--muted)]">{formatDate(log.ts)}</td>
                          <td className="py-3 pr-4 text-sm font-mono">{log.channel}</td>
                          <td className="py-3 pr-4 text-sm max-w-xs truncate">{log.user_message}</td>
                          <td className="py-3 pr-4 text-sm max-w-xs truncate">{log.response || '-'}</td>
                          <td className="py-3 pr-4 text-sm font-mono">{log.scenario_id || '-'}</td>
                          <td className="py-3">
                            {log.escalated ? (
                              <span className="px-2 py-1 text-xs rounded-full bg-red-500/20 text-red-400">Escalated</span>
                            ) : log.error ? (
                              <span className="px-2 py-1 text-xs rounded-full bg-yellow-500/20 text-yellow-400">Error</span>
                            ) : (
                              <span className="px-2 py-1 text-xs rounded-full bg-green-500/20 text-green-400">OK</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Stream Tab */}
          {activeTab === 'stream' && (
            <div>
              <div className="mb-4 flex justify-between items-center">
                <p className="text-[var(--muted)]">Live event stream from Charon</p>
                <span className="flex items-center gap-2 text-sm text-green-400">
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                  Connected
                </span>
              </div>
              
              <div className="bg-[var(--card-hover)] rounded-lg p-4 h-[500px] overflow-y-auto font-mono text-sm">
                {streamEvents.length === 0 ? (
                  <div className="text-center py-12 text-[var(--muted)]">Waiting for events...</div>
                ) : (
                  streamEvents.map((event, idx) => (
                    <div key={idx} className="mb-2 pb-2 border-b border-[var(--border)]/30">
                      <span className="text-[var(--muted)]">[{formatDate(event.ts)}]</span>{' '}
                      <pre className="inline whitespace-pre-wrap break-all">{JSON.stringify(event.data, null, 2)}</pre>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
