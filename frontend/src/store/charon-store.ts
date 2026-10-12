"use client";
import { create } from 'zustand';

// ── Types ────────────────────────────────────────────────────────────────────

export interface ToolCall {
  tool: string;
  params?: Record<string, unknown>;
  result?: unknown;
  error?: string;
}

export interface CharonMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  /** True while SSE tokens are still arriving */
  isStreaming?: boolean;
  /** True if this is a proactive trigger message (not user-initiated) */
  isProactive?: boolean;
  escalated?: boolean;
  tool_calls?: ToolCall[];
  tokens_used?: number;
}

export interface PageContext {
  page_type?: string;
  path?: string;
  themes?: string[];
  session_pages?: number;
  session_duration_s?: number;
  cart_active?: boolean;
  plan_being_viewed?: string;
  [key: string]: unknown;
}

export interface ProactiveMessage {
  id: string;
  triggerId: string;
  message: string;
  dismissAfterMs: number;
  delayMs: number;
}

// ── Store shape ──────────────────────────────────────────────────────────────

interface CharonStore {
  // Session
  sessionId: string | null;
  setSessionId: (id: string) => void;

  // Messages
  messages: CharonMessage[];
  addMessage: (msg: CharonMessage) => void;
  updateMessage: (id: string, patch: Partial<CharonMessage>) => void;
  appendToMessage: (id: string, chunk: string) => void;
  clearMessages: () => void;

  // UI state
  isOpen: boolean;
  isMinimized: boolean;
  isTyping: boolean;
  setOpen: (open: boolean) => void;
  setMinimized: (minimized: boolean) => void;
  setTyping: (typing: boolean) => void;

  // Streaming
  streamingMessageId: string | null;
  setStreamingMessageId: (id: string | null) => void;

  // Proactive messages
  proactiveMessage: ProactiveMessage | null;
  setProactiveMessage: (msg: ProactiveMessage | null) => void;

  // Page context
  pageContext: PageContext;
  setPageContext: (ctx: PageContext) => void;

  // Reset
  reset: () => void;
}

// ── Store ────────────────────────────────────────────────────────────────────

export const useCharonStore = create<CharonStore>()((set) => ({
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),

  messages: [],
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  updateMessage: (id, patch) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),
  appendToMessage: (id, chunk) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + chunk } : m,
      ),
    })),
  clearMessages: () => set({ messages: [] }),

  isOpen: false,
  isMinimized: false,
  isTyping: false,
  setOpen: (open) => set({ isOpen: open, isMinimized: false }),
  setMinimized: (minimized) => set({ isMinimized: minimized, isOpen: !minimized }),
  setTyping: (typing) => set({ isTyping: typing }),

  streamingMessageId: null,
  setStreamingMessageId: (id) => set({ streamingMessageId: id }),

  proactiveMessage: null,
  setProactiveMessage: (msg) => set({ proactiveMessage: msg }),

  pageContext: {},
  setPageContext: (ctx) => set({ pageContext: ctx }),

  reset: () =>
    set({
      sessionId: null,
      messages: [],
      isOpen: false,
      isMinimized: false,
      isTyping: false,
      streamingMessageId: null,
      proactiveMessage: null,
      pageContext: {},
    }),
}));
