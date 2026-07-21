'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import api from '@/lib/api';
import type { AdminMeResponse } from '@/types';

export interface AdminUser {
  admin_phone: string;
  role: string;
  totp_enabled: boolean;
  last_used?: string;
}

interface UseAdminAuthReturn {
  admin: AdminUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  logout: () => Promise<void>;
  refreshAdmin: () => Promise<void>;
}

/**
 * Centralized admin auth state and operations.
 * Reads token from localStorage (written by login/setup pages).
 * Falls back to cookie if localStorage is empty (SSR/reregular).
 */
export function useAdminAuth(): UseAdminAuthReturn {
  const [admin, setAdmin] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refreshRef = useRef<() => Promise<void> | undefined>(undefined);
  const hasFetched = useRef(false);

  const fetchAdmin = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getAdminMe();
      if (res.error) {
        setAdmin(null);
        setError(res.error);
        return;
      }
      const data = res.data as AdminMeResponse;
      setAdmin({
        admin_phone: data.admin_phone,
        role: data.role,
        totp_enabled: data.totp_enabled,
        last_used: (data as any).last_used,
      });
      setError(null);
    } catch {
      setAdmin(null);
      setError('Failed to verify session');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch admin once on mount
  useEffect(() => {
    if (hasFetched.current) return;
    hasFetched.current = true;
    fetchAdmin();
  }, [fetchAdmin]);

  // Exposed refresh for manual re-checks
  refreshRef.current = fetchAdmin;

  const logout = useCallback(async () => {
    try {
      await api.adminLogout();
    } catch {
      // Ignore logout errors — clear local state regardless
    } finally {
      api.clearAdminToken();
      setAdmin(null);
      setError(null);
      hasFetched.current = false;
    }
  }, []);

  return {
    admin,
    isLoading,
    isAuthenticated: !!admin && !error,
    error,
    logout,
    refreshAdmin: useCallback(async () => { if (refreshRef.current) await refreshRef.current(); }, []),
  };
}
