/* eslint-disable react-hooks/set-state-in-effect */
'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

interface Conversation {
  id: string;
  session_id: string;
  channel: string;
  status: string;
  escalated: boolean;
  message_count: number;
  tokens_used: number;
  rating: number | null;
  started_at: string;
  last_activity_at: string;
}

interface Message {
  id: string;
  role: string;
  content: string;
  tool_calls?: { tool: string; params?: Record<string, unknown> }[] | null;
  tokens_used: number;
  ts: string;
}

interface ConversationDetail {
  conversation: Conversation;
  messages: Message[];
}

export default function AdminConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<'all' | 'escalated' | 'active' | 'rated'>('all');
  const [rating, setRating] = useState<{ [id: string]: number }>({});

  const loadConversations = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await api.getCharonConversations(1, 100);
      if (result.data) {
        let convs = result.data.conversations || [];
        if (filter === 'escalated') convs = convs.filter(c => c.escalated);
        if (filter === 'active') convs = convs.filter(c => (c as any).status === 'active');
        if (filter === 'rated') convs = convs.filter(c => c.rating != null);
        setConversations(convs);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  const selectConversation = async (id: string) => {
    try {
      // Fetch all conversations and find the one we need
      // (no single-conversation API endpoint available)
      const result = await api.getCharonConversations(1, 100);
      if (result.data) {
        const found = (result.data.conversations || []).find((c: Conversation) => c.conversation_id === id);
        if (found) {
          // For detail view, we need to fetch logs for this conversation
          const logsResult = await api.getCharonLogs(100, 0, id);
          if (logsResult.data) {
            setSelected({
              conversation: found as any,
              messages: (logsResult.data.logs || []).map((log: any) => ({
                id: log.conversation_id + '-' + log.ts,
                role: 'assistant',
                content: log.response || log.user_message,
                tool_calls: log.tool_calls || null,
                tokens_used: 0,
                ts: log.ts,
              })),
            });
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load conversation');
    }
  };

  const submitRating = async (id: string, value: number) => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('admin_token') || '' : '';
      await fetch(`/api/v1/charon/conversations/${id}/rate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ rating: value }),
      });
      setRating(prev => ({ ...prev, [id]: value }));
      loadConversations();
    } catch (e) {
      // silent
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Charon Conversations</h1>

      {error && (
        <div className="mb-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400" role="alert">
          {error}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-2 mb-4">
        {(['all', 'escalated', 'active', 'rated'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === f ? 'bg-[var(--primary)] text-black' : 'bg-[var(--card)] border border-[var(--border)]'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Conversation list */}
        <div className="lg:col-span-1 bg-[var(--card)] rounded-xl border border-[var(--border)] overflow-hidden">
          <div className="p-3 border-b border-[var(--border)] font-medium text-sm">
            {conversations.length} conversations
          </div>
          <div className="max-h-[60vh] overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-[var(--muted)]">Loading...</div>
            ) : conversations.length === 0 ? (
              <div className="p-4 text-center text-[var(--muted)]">No conversations</div>
            ) : (
              conversations.map(c => (
                <button
                  key={c.id}
                  onClick={() => selectConversation(c.id)}
                  className={`w-full text-left p-3 border-b border-[var(--border)] hover:bg-[var(--card-hover)] ${
                    selected?.conversation.id === c.id ? 'bg-[var(--card-hover)]' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[var(--muted)]">
                      {new Date(c.last_activity_at).toLocaleDateString()}
                    </span>
                    {c.escalated && (
                      <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 text-xs rounded">
                        Escalated
                      </span>
                    )}
                  </div>
                  <p className="text-sm truncate mt-1">
                    {c.message_count} messages · {c.channel}
                  </p>
                  {c.rating && (
                    <div className="flex gap-0.5 mt-1">
                      {[1, 2, 3, 4, 5].map(star => (
                        <span key={star} className={star <= c.rating! ? 'text-yellow-400' : 'text-[var(--muted)]'}>
                          ★
                        </span>
                      ))}
                    </div>
                  )}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Conversation detail */}
        <div className="lg:col-span-2 bg-[var(--card)] rounded-xl border border-[var(--border)] overflow-hidden">
          {selected ? (
            <div className="flex flex-col h-[70vh]">
              {/* Header */}
              <div className="p-4 border-b border-[var(--border)] flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">
                    {selected.conversation.channel} · {selected.conversation.message_count} messages
                  </p>
                  <p className="text-xs text-[var(--muted)]">
                    Started {new Date(selected.conversation.started_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {[1, 2, 3, 4, 5].map(star => (
                    <button
                      key={star}
                      onClick={() => submitRating(selected.conversation.id, star)}
                      className={`text-xl ${
                        star <= (rating[selected.conversation.id] || selected.conversation.rating || 0)
                          ? 'text-yellow-400'
                          : 'text-[var(--muted)] hover:text-yellow-400'
                      }`}
                      aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
                    >
                      ★
                    </button>
                  ))}
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {selected.messages.map(m => (
                  <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[80%] px-3 py-2 rounded-2xl text-sm ${
                        m.role === 'user'
                          ? 'bg-[var(--primary)] text-black'
                          : 'bg-[var(--background)] border border-[var(--border)]'
                      }`}
                    >
                      <p className="whitespace-pre-wrap break-words">{m.content}</p>
                      {m.tool_calls && m.tool_calls.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-[var(--border)] text-xs text-[var(--muted)]">
                          Tools: {m.tool_calls.map(tc => tc.tool).join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-[70vh] flex items-center justify-center text-[var(--muted)]">
              Select a conversation to view
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
