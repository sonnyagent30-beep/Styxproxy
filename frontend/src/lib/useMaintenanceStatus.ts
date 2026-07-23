'use client';

import { useEffect, useState } from 'react';

interface MaintenanceState {
  enabled: boolean;
  ready_at: string | null;
  message: string | null;
}

/**
 * Public read of maintenance state. Used by the maintenance page itself
 * and (optionally) by the public site to show a banner when enabled.
 */
export function useMaintenanceStatus() {
  const [state, setState] = useState<MaintenanceState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/api/maintenance', { cache: 'no-store' });
        if (cancelled) return;
        if (res.ok) {
          const data = (await res.json()) as MaintenanceState;
          setState(data);
        } else {
          setState({ enabled: false, ready_at: null, message: null });
        }
      } catch {
        if (!cancelled) {
          setState({ enabled: false, ready_at: null, message: null });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { state, loading };
}
