'use client';
import { create } from 'zustand';

interface CharonMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface CharonStore {
  sessionId: string | null;
  messages: CharonMessage[];
  isOpen: boolean;
  isMinimized: boolean;
  setSessionId: (id: string) => void;
  addMessage: (msg: CharonMessage) => void;
  setOpen: (open: boolean) => void;
  setMinimized: (minimized: boolean) => void;
  reset: () => void;
}

export const useCharonStore = create<CharonStore>()((set) => ({
  sessionId: null,
  messages: [],
  isOpen: false,
  isMinimized: false,
  setSessionId: (id) => set({ sessionId: id }),
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  setOpen: (open) => set({ isOpen: open, isMinimized: false }),
  setMinimized: (minimized) => set({ isMinimized: minimized, isOpen: !minimized }),
  reset: () => set({ sessionId: null, messages: [], isOpen: false, isMinimized: false }),
}));
