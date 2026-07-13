'use client';

import { useEffect } from 'react';
import { useDeviceSession } from '@/lib/use-device-session';

/**
 * Mounts once in the root layout. Initializes the anonymous device session
 * with the backend on every page load (refreshes JWT cookie).
 *
 * Backend auto-creates an anonymous PlatformAccount tied to this browser's
 * device_id (UUID in localStorage). No login required.
 */
export default function SessionInitializer() {
  useDeviceSession();
  return null;
}