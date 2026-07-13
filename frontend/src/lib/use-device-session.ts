'use client';

import { useEffect, useState } from 'react';
import { apiFetch, getDeviceId } from './device-id';

/**
 * Hook that initializes an anonymous session with the backend.
 * - On first call to a protected endpoint, backend creates a PlatformAccount
 *   tied to this device_id (no name, anonymous)
 * - JWT is set as httpOnly cookie by backend, automatically included in requests
 *
 * Returns true once the session has been initialized (so we know we can call APIs).
 */
export function useDeviceSession(): boolean {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      const deviceId = getDeviceId();
      if (!deviceId) return;

      try {
        // Ping a session/init endpoint to register this device + get JWT cookie
        const res = await apiFetch('/api/session/init', {
          method: 'POST',
          body: JSON.stringify({ device_id: deviceId }),
        });
        if (!cancelled) setReady(res.ok);
      } catch {
        if (!cancelled) setReady(false);
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, []);

  return ready;
}