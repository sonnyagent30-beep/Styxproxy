'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { CharonConversation, CharonLogEntry } from '@/types';

// SVG Icons as components
const ChatIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
);

const ListIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
  </svg>
);

const ChevronLeftIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
  </svg>
);

const ChevronRightIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const FilterIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
  </svg>
);

const ClearIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const ClockIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function truncateText(text: string, maxLength: number): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

export default function AdminCharonConversationsPage() {
  const [activeTab, setActiveTab] = useState<'conversations' | 'logs'>('conversations');
  
  // Conversations state
  const [conversations, setConversations] = useState<CharonConversation[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [conversationsError, setConversationsError] = useState('');
  const [conversationsTotal, setConversationsTotal] = useState(0);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  
  // Logs state
  const [logs, setLogs] = useState<CharonLogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState('');
  const [logsTotal, setLogsTotal] = useState(0);
  
  // Filter state
  const [logOffset, setLogOffset] = useState(0);
  const [filterConversationId, setFilterConversationId] = useState('');
  const [filterChannel, setFilterChannel] = useState('');
  const [filterEscalated, setFilterEscalated] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');

  const LOG_LIMIT = 50;

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    setConversationsLoading(true);
    setConversationsError('');
    const result = await api.getCharonConversations(1, 100);
    if (result.error) {
      setConversationsError(result.error);
    } else if (result.data) {
      setConversations(result.data.conversations || []);
      setConversationsTotal(result.data.total || 0);
    }
    setConversationsLoading(false);
  };

  const loadLogs = useCallback(async (offset: number = 0) => {
    setLogsLoading(true);
    setLogsError('');
    
    const conversationId = filterConversationId || selectedConversationId || undefined;
    const escalated = filterEscalated === 'yes' ? true : filterEscalated === 'no' ? false : undefined;
    const channel = filterChannel || undefined;
    const dateFrom = filterDateFrom || undefined;
    const dateTo = filterDateTo || undefined;
    
    const result = await api.getCharonLogs(
      LOG_LIMIT,
      offset,
      conversationId,
      channel,
      escalated,
      dateFrom,
      dateTo
    );
    
    if (result.error) {
      setLogsError(result.error);
    } else if (result.data) {
      setLogs(result.data.logs || []);
      setLogsTotal(result.data.total || 0);
      setLogOffset(result.data.offset || 0);
    }
    setLogsLoading(false);
  }, [filterConversationId, selectedConversationId, filterChannel, filterEscalated, filterDateFrom, filterDateTo]);

  // Load logs when tab changes to logs or filters change
  useEffect(() => {
    if (activeTab === 'logs') {
      loadLogs(0);
    }
  }, [activeTab, filterConversationId, filterChannel, filterEscalated, filterDateFrom, filterDateTo, selectedConversationId]);

  const handleConversationClick = (conversationId: string) => {
    setSelectedConversationId(conversationId);
    setFilterConversationId('');
    setActiveTab('logs');
  };

  const handleFilterChange = () => {
    setSelectedConversationId(null);
    setLogOffset(0);
    loadLogs(0);
  };

  const clearFilters = () => {
    setFilterConversationId('');
    setFilterChannel('');
    setFilterEscalated('');
    setFilterDateFrom('');
    setFilterDateTo('');
    setSelectedConversationId(null);
  };

  const handlePrevPage = () => {
    if (logOffset > 0) {
      loadLogs(Math.max(0, logOffset - LOG_LIMIT));
    }
  };

  const handleNextPage = () => {
    if (logOffset + LOG_LIMIT < logsTotal) {
      loadLogs(logOffset + LOG_LIMIT);
    }
  };

  const hasActiveFilters = filterConversationId || filterChannel || filterEscalated || filterDateFrom || filterDateTo || selectedConversationId;

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl lg:text-4xl font-bold mb-2">
          Charon <span className="text-[var(--primary)]">Conversations</span>
        </h1>
        <p className="text-[var(--muted)]">View and manage Charon conversation logs</p>
      </div>

      {conversationsError && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-between">
          <span>{conversationsError}</span>
          <button onClick={() => setConversationsError('')} className="text-red-300 hover:text-white ml-4">[x]</button>
        </div>
      )}

      {logsError && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-between">
          <span>{logsError}</span>
          <button onClick={() => setLogsError('')} className="text-red-300 hover:text-white ml-4">[x]</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('conversations')}
          className={`px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-all ${
            activeTab === 'conversations'
              ? 'bg-[var(--primary)] text-black'
              : 'bg-[var(--card)] text-[var(--muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
          }`}
        >
          <ChatIcon />
          Conversations
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={`px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-all ${
            activeTab === 'logs'
              ? 'bg-[var(--primary)] text-black'
              : 'bg-[var(--card)] text-[var(--muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
          }`}
        >
          <ListIcon />
          Logs
        </button>
      </div>

      {/* Conversations Tab */}
      {activeTab === 'conversations' && (
        <div className="p-6 rounded-xl bg-[var(--card)] border border-[var(--border)]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">All Conversations</h2>
            <span className="text-sm text-[var(--muted)]">{conversationsTotal} total</span>
          </div>
          
          {conversationsLoading ? (
            <p className="text-center py-8 text-[var(--muted)]">Loading...</p>
          ) : conversations.length === 0 ? (
            <p className="text-center py-8 text-[var(--muted)]">No conversations yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-sm text-[var(--muted)]">
                    <th className="pb-3 pr-4 font-medium">Conversation ID</th>
                    <th className="pb-3 pr-4 font-medium">Last Message</th>
                    <th className="pb-3 pr-4 font-medium">Messages</th>
                    <th className="pb-3 pr-4 font-medium">Escalated</th>
                    <th className="pb-3 font-medium">Last Activity</th>
                  </tr>
                </thead>
                <tbody>
                  {conversations.map((conv) => (
                    <tr
                      key={conv.conversation_id}
                      onClick={() => handleConversationClick(conv.conversation_id)}
                      className="border-b border-[var(--border)] cursor-pointer hover:bg-[var(--card-hover)] transition-colors"
                    >
                      <td className="py-3 pr-4 font-mono text-sm">
                        {truncateText(conv.conversation_id, 20)}
                      </td>
                      <td className="py-3 pr-4 text-sm">
                        {truncateText(conv.last_message, 60)}
                      </td>
                      <td className="py-3 pr-4 text-sm">
                        {conv.message_count}
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                          conv.escalated 
                            ? 'bg-red-500/20 text-red-400' 
                            : 'bg-[var(--card-hover)] text-[var(--muted)]'
                        }`}>
                          {conv.escalated ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td className="py-3 text-sm text-[var(--muted)]">
                        <span className="flex items-center gap-1">
                          <ClockIcon />
                          {formatRelativeTime(conv.last_message_at)}
                        </span>
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
        <div className="space-y-4">
          {/* Filters */}
          <div className="p-4 rounded-xl bg-[var(--card)] border border-[var(--border)]">
            <div className="flex items-center gap-2 mb-4">
              <FilterIcon />
              <span className="font-medium">Filters</span>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="ml-auto text-sm text-[var(--muted)] hover:text-[var(--foreground)] flex items-center gap-1"
                >
                  <ClearIcon />
                  Clear
                </button>
              )}
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <div>
                <label className="block text-xs text-[var(--muted)] mb-1">Conversation ID</label>
                <input
                  type="text"
                  value={selectedConversationId || filterConversationId}
                  onChange={(e) => {
                    setSelectedConversationId(null);
                    setFilterConversationId(e.target.value);
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && handleFilterChange()}
                  placeholder="Filter by ID..."
                  className="w-full px-3 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none text-sm"
                />
              </div>
              
              <div>
                <label className="block text-xs text-[var(--muted)] mb-1">Channel</label>
                <select
                  value={filterChannel}
                  onChange={(e) => setFilterChannel(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none text-sm"
                >
                  <option value="">All</option>
                  <option value="web">Web</option>
                  <option value="telegram">Telegram</option>
                  <option value="whatsapp">WhatsApp</option>
                </select>
              </div>
              
              <div>
                <label className="block text-xs text-[var(--muted)] mb-1">Escalated</label>
                <select
                  value={filterEscalated}
                  onChange={(e) => setFilterEscalated(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none text-sm"
                >
                  <option value="">All</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </div>
              
              <div>
                <label className="block text-xs text-[var(--muted)] mb-1">Date From</label>
                <input
                  type="date"
                  value={filterDateFrom}
                  onChange={(e) => setFilterDateFrom(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none text-sm"
                />
              </div>
              
              <div>
                <label className="block text-xs text-[var(--muted)] mb-1">Date To</label>
                <input
                  type="date"
                  value={filterDateTo}
                  onChange={(e) => setFilterDateTo(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none text-sm"
                />
              </div>
              
              <div className="flex items-end">
                <button
                  onClick={handleFilterChange}
                  className="w-full px-4 py-2 rounded-lg bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity text-sm"
                >
                  Apply
                </button>
              </div>
            </div>
          </div>

          {/* Active filter indicator */}
          {selectedConversationId && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-[var(--muted)]">Viewing logs for:</span>
              <span className="font-mono bg-[var(--card-hover)] px-2 py-1 rounded">
                {truncateText(selectedConversationId, 30)}
              </span>
              <button onClick={() => setSelectedConversationId(null)} className="text-[var(--muted)] hover:text-white">
                <ClearIcon />
              </button>
            </div>
          )}

          {/* Logs Table */}
          <div className="p-6 rounded-xl bg-[var(--card)] border border-[var(--border)]">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Log Entries</h2>
              <span className="text-sm text-[var(--muted)]">
                Showing {logs.length} of {logsTotal}
              </span>
            </div>
            
            {logsLoading ? (
              <p className="text-center py-8 text-[var(--muted)]">Loading...</p>
            ) : logs.length === 0 ? (
              <p className="text-center py-8 text-[var(--muted)]">No logs found</p>
            ) : (
              <div className="space-y-4">
                {logs.map((log, index) => (
                  <div
                    key={`${log.conversation_id}-${log.ts}-${index}`}
                    className="p-4 rounded-lg bg-[var(--card-hover)] border border-[var(--border)]"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-[var(--muted)]">
                          {new Date(log.ts).toLocaleString('en-US', { 
                            month: 'short', 
                            day: 'numeric',
                            hour: '2-digit', 
                            minute: '2-digit',
                            second: '2-digit'
                          })}
                        </span>
                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-[var(--surface)] text-[var(--muted)] uppercase">
                          {log.channel || 'unknown'}
                        </span>
                        {log.escalated && (
                          <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-500/20 text-red-400">
                            Escalated
                          </span>
                        )}
                        {log.scenario_id && (
                          <span className="text-xs text-[var(--muted)] font-mono">
                            Scenario: {log.scenario_id}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-[var(--muted)] font-mono">
                        {truncateText(log.conversation_id, 16)}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-[var(--muted)] mb-1">User Message</p>
                        <p className="text-sm bg-[var(--surface)] p-2 rounded">
                          {truncateText(log.user_message, 200)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-[var(--muted)] mb-1">Response</p>
                        <p className="text-sm bg-[var(--surface)] p-2 rounded">
                          {log.response ? truncateText(log.response, 200) : '-'}
                        </p>
                      </div>
                    </div>
                    
                    {log.error && (
                      <div className="mt-2">
                        <p className="text-xs text-red-400 mb-1">Error</p>
                        <p className="text-sm bg-red-500/10 p-2 rounded text-red-300">
                          {log.error}
                        </p>
                      </div>
                    )}
                    
                    {log.tool_calls && log.tool_calls.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-[var(--muted)] mb-1">Tool Calls ({log.tool_calls.length})</p>
                        <div className="space-y-1">
                          {log.tool_calls.map((tool, tIndex) => (
                            <div key={tIndex} className="text-xs bg-[var(--surface)] p-2 rounded font-mono">
                              <span className="text-[var(--primary)]">{tool.tool}</span>
                              {tool.error && (
                                <span className="text-red-400 ml-2">Error: {tool.error}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {/* Pagination */}
            {logsTotal > LOG_LIMIT && (
              <div className="flex items-center justify-between mt-6 pt-4 border-t border-[var(--border)]">
                <button
                  onClick={handlePrevPage}
                  disabled={logOffset === 0}
                  className="flex items-center gap-1 px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  <ChevronLeftIcon />
                  Previous
                </button>
                <span className="text-sm text-[var(--muted)]">
                  Page {Math.floor(logOffset / LOG_LIMIT) + 1} of {Math.ceil(logsTotal / LOG_LIMIT)}
                </span>
                <button
                  onClick={handleNextPage}
                  disabled={logOffset + LOG_LIMIT >= logsTotal}
                  className="flex items-center gap-1 px-4 py-2 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  Next
                  <ChevronRightIcon />
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
