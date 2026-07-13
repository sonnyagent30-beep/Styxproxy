'use client';

import { useEffect, useState } from 'react';

const DEVICE_ID_KEY = 'styxproxy_device_id';
const INFLIGHT_KEY = 'styxproxy_inflight_order';
const ORDERS_KEY = 'styxproxy_orders';

/**
 * Generate a UUIDv4 (uses crypto.randomUUID if available, fallback to manual).
 */
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Get or create the device ID for this browser.
 * Anonymous identity — UUID stored in localStorage.
 * Survives tab close, cleared only when user clears site data.
 */
export function getDeviceId(): string {
  if (typeof window === 'undefined') return '';
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = generateUUID();
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

export function useDeviceId(): string | null {
  const [id, setId] = useState<string | null>(null);
  useEffect(() => {
    setId(getDeviceId());
  }, []);
  return id;
}

/**
 * In-flight order tracking — prevents double payments at the frontend layer.
 *
 * When a customer clicks "Pay", we record (tx_ref, device_id, plan_code, created_at)
 * in localStorage. If they click "Pay" again within 5 minutes:
 *   - read the existing record
 *   - return the existing tx_ref (don't create a new order)
 *   - show a toast: "Payment in progress for order ORD-XXXX"
 *
 * After 5 minutes (or webhook confirmation), the record is cleared.
 */
export type InflightOrder = {
  tx_ref: string;
  plan_code: string;
  created_at: number; // unix ms
  device_id: string;
};

export function getInflightOrder(): InflightOrder | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(INFLIGHT_KEY);
  if (!raw) return null;
  try {
    const order = JSON.parse(raw) as InflightOrder;
    // Expire after 5 minutes — assume abandoned/aborted
    if (Date.now() - order.created_at > 5 * 60 * 1000) {
      localStorage.removeItem(INFLIGHT_KEY);
      return null;
    }
    return order;
  } catch {
    return null;
  }
}

export function setInflightOrder(order: InflightOrder): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(INFLIGHT_KEY, JSON.stringify(order));
}

export function clearInflightOrder(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(INFLIGHT_KEY);
}

/**
 * Try to start an order — returns the existing tx_ref if there's an in-flight one
 * for the same plan_code, or starts a new one.
 *
 * Returns: { tx_ref: string, is_resume: boolean }
 *   is_resume=true means we reused an existing in-flight order
 */
export function tryStartOrder(plan_code: string, generateTxRef: () => string): {
  tx_ref: string;
  is_resume: boolean;
} {
  const deviceId = getDeviceId();
  const inflight = getInflightOrder();

  if (inflight && inflight.device_id === deviceId && inflight.plan_code === plan_code) {
    return { tx_ref: inflight.tx_ref, is_resume: true };
  }

  // Different plan or no inflight — start fresh
  const tx_ref = generateTxRef();
  setInflightOrder({
    tx_ref,
    plan_code,
    created_at: Date.now(),
    device_id: deviceId,
  });
  return { tx_ref, is_resume: false };
}

/**
 * Order history — list of orders placed from this device.
 * Lets customers come back and find past orders without login.
 */
export type OrderHistoryEntry = {
  tx_ref: string;
  order_id: string;
  plan_code: string;
  country: string;
  amount: number;
  status: string;
  created_at: string; // ISO
};

export function getOrderHistory(): OrderHistoryEntry[] {
  if (typeof window === 'undefined') return [];
  const raw = localStorage.getItem(ORDERS_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as OrderHistoryEntry[];
  } catch {
    return [];
  }
}

export function addToOrderHistory(entry: OrderHistoryEntry): void {
  if (typeof window === 'undefined') return;
  const history = getOrderHistory();
  // De-dupe by tx_ref, keep newest first
  const filtered = history.filter((o) => o.tx_ref !== entry.tx_ref);
  filtered.unshift(entry);
  // Cap at 50
  const capped = filtered.slice(0, 50);
  localStorage.setItem(ORDERS_KEY, JSON.stringify(capped));
}

export function clearOrderHistory(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(ORDERS_KEY);
}
