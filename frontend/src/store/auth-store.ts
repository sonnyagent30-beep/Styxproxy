'use client';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthStore {
  token: string | null;
  adminId: string | null;
  adminName: string | null;
  setAuth: (token: string, adminId: string, adminName: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      adminId: null,
      adminName: null,
      setAuth: (token, adminId, adminName) => set({ token, adminId, adminName }),
      clearAuth: () => set({ token: null, adminId: null, adminName: null }),
    }),
    { name: 'styxproxy_admin_auth' }
  )
);
