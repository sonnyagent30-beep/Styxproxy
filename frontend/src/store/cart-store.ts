'use client';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface CartItem {
  plan_code: string;
  name: string;
  flag: string;
  price_ngn: number;
  plan_type: string;
  country: string;
  city?: string;
  gb_tier?: number;
  quantity?: number;
  gb_per_ip?: number;
  plan_id: number;
  variant_id: number;
  template_label: string;
}

interface CartStore {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (index: number) => void;
  clearCart: () => void;
  total: () => number;
}

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],
      addItem: (item) => set((state) => ({ items: [...state.items, item] })),
      removeItem: (index) =>
        set((state) => ({ items: state.items.filter((_, i) => i !== index) })),
      clearCart: () => set({ items: [] }),
      total: () => get().items.reduce((sum, item) => sum + item.price_ngn, 0),
    }),
    { name: 'styxproxy_cart' }
  )
);
