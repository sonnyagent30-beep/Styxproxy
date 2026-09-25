'use client';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CartItem } from '@/types';

export type { CartItem };

interface CartStore {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (index: number) => void;
  clearCart: () => void;
  total: () => number;
  setCart: (items: CartItem[]) => void;
}

let hydrated = false;

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],
      addItem: (item) => set((state) => ({ items: [...state.items, item] })),
      removeItem: (index) =>
        set((state) => ({ items: state.items.filter((_, i) => i !== index) })),
      clearCart: () => set({ items: [] }),
      total: () => get().items.reduce((sum, item) => sum + item.price_ngn, 0),
      setCart: (items) => set({ items }),
    }),
    { name: 'styxproxy_cart' }
  )
);

// Hydration guard - prevents SSR mismatch by only loading persisted state on client
export function useCartHydration() {
  if (typeof window === 'undefined') return false;
  if (hydrated) return true;
  useCartStore.persist.rehydrate().then(() => { hydrated = true; });
  return hydrated;
}
