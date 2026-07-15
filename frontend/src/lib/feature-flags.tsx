'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '@/lib/api';
import type { ChannelFeatureFlags } from '@/types';

interface ChannelFeatureFlagsContextType {
  flags: ChannelFeatureFlags;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  isChannelEnabled: (channel: 'telegram' | 'whatsapp') => boolean;
  getChannelUrl: (channel: 'telegram' | 'whatsapp') => string;
}

const defaultFlags: ChannelFeatureFlags = {
  telegram: { enabled: false, url: '' },
  whatsapp: { enabled: false, url: '' },
};

const ChannelFeatureFlagsContext = createContext<ChannelFeatureFlagsContextType>({
  flags: defaultFlags,
  loading: true,
  error: null,
  refresh: async () => {},
  isChannelEnabled: () => false,
  getChannelUrl: () => '',
});

export function ChannelFeatureFlagsProvider({ children }: { children: ReactNode }) {
  const [flags, setFlags] = useState<ChannelFeatureFlags>(defaultFlags);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    
    const result = await api.getChannelFeatureFlags();
    
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setFlags(result.data);
    }
    
    setLoading(false);
  };

  useEffect(() => {
    refresh();
  }, []);

  const isChannelEnabled = (channel: 'telegram' | 'whatsapp'): boolean => {
    return flags[channel]?.enabled ?? false;
  };

  const getChannelUrl = (channel: 'telegram' | 'whatsapp'): string => {
    return flags[channel]?.url ?? '';
  };

  return (
    <ChannelFeatureFlagsContext.Provider
      value={{
        flags,
        loading,
        error,
        refresh,
        isChannelEnabled,
        getChannelUrl,
      }}
    >
      {children}
    </ChannelFeatureFlagsContext.Provider>
  );
}

export function useChannelFlags() {
  const context = useContext(ChannelFeatureFlagsContext);
  if (!context) {
    throw new Error('useChannelFlags must be used within a ChannelFeatureFlagsProvider');
  }
  return context;
}
