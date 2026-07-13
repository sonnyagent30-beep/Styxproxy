'use client';

import { useEffect, useState } from 'react';

const DEVICE_ID_KEY = 'styxproxy_device_id';

/**
 * Generate a UUIDv4 (uses crypto.randomUUID if available, fallback to manual).
 */
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Get or create the device ID for this browser.
 * Persists in localStorage — survives tab/browser close.
 * This is the anonymous identity for the customer.
 * No PII — just a UUID tied to this browser.
 */
export function getDeviceId(): string {
  if (typeof window === 'undefined') {
    return ''; // SSR — no device ID yet
  }
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = generateUUID();
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

/**
 * React hook that returns the device ID (client-side only).
 * Returns null during SSR / before hydration.
 */
export function useDeviceId(): string | null {
  const [id, setId] = useState<string | null>(null);

  useEffect(() => {
    setId(getDeviceId());
  }, []);

  return id;
}

/**
 * API client wrapper that auto-injects the device ID header.
 * Use this for all /api/* calls from the website.
 */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const deviceId = getDeviceId();
  const headers = new Headers(init.headers);
  if (deviceId) {
    headers.set('X-Device-Id', deviceId);
  }
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  return fetch(path, {
    ...init,
    headers,
    credentials: 'include', // send/receive httpOnly cookies (JWT)
  });
}