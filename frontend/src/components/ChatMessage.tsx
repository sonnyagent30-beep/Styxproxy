'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { CharonMessage } from '@/store/charon-store';

interface ChatMessageProps {
  message: CharonMessage;
  onRetry?: () => void;
}

/**
 * ChatMessage — individual message bubble for the Charon widget.
 * Renders user + assistant messages with markdown support.
 * Shows a typing indicator when the message is still streaming.
 * A4: Tables render with proper styling (header, hairlines, scroll).
 * A5: Interrupted replies show a "Reply was interrupted" + Retry affordance.
 */
export default function ChatMessage({ message, onRetry }: ChatMessageProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] px-4 py-2.5 rounded-2xl rounded-br-md bg-[var(--primary)] text-black text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%]">
        <div
          className={`px-4 py-2.5 rounded-2xl rounded-bl-md bg-[var(--card)] border border-[var(--border)] text-sm leading-relaxed text-[var(--foreground)] ${
            message.isStreaming ? 'charon-streaming' : ''
          }`}
        >
          {message.content ? (
            <div className="prose prose-sm prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0 prose-strong:text-[var(--primary-text)] prose-a:text-[var(--primary-text)] prose-a:underline">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  table: ({ node, ...props }) => (
                    <div className="overflow-x-auto my-2">
                      <table className="charon-table w-full text-xs" {...props} />
                    </div>
                  ),
                  thead: ({ node, ...props }) => (
                    <thead className="charon-table-header" {...props} />
                  ),
                  th: ({ node, ...props }) => (
                    <th className="charon-table-cell font-semibold text-left" {...props} />
                  ),
                  td: ({ node, ...props }) => (
                    <td className="charon-table-cell" {...props} />
                  ),
                  tr: ({ node, ...props }) => (
                    <tr className="charon-table-row" {...props} />
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          ) : (
            <span className="charon-typing-indicator inline-flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-[var(--muted)] animate-pulse" />
              <span className="inline-block w-2 h-2 rounded-full bg-[var(--muted)] animate-pulse [animation-delay:0.2s]" />
              <span className="inline-block w-2 h-2 rounded-full bg-[var(--muted)] animate-pulse [animation-delay:0.4s]" />
            </span>
          )}
        </div>

        {message.escalated && (
          <div className="mt-1.5 px-2 py-0.5 bg-amber-500/20 text-amber-400 text-xs rounded inline-block">
            Escalated to support
          </div>
        )}

        {/* A5: Interrupted reply affordance */}
        {message.interrupted && !message.isStreaming && (
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-xs text-[var(--muted)]">Reply was interrupted</span>
            {onRetry && (
              <button
                onClick={onRetry}
                className="text-xs text-[var(--primary-text)] hover:underline font-medium"
              >
                Retry
              </button>
            )}
          </div>
        )}

        {message.tokens_used !== undefined && !message.isStreaming && (
          <p className="mt-1 text-xs text-[var(--muted)] pl-1">
            {message.tokens_used} tokens used
          </p>
        )}
      </div>
    </div>
  );
}
