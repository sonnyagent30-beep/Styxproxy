'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';

/**
 * Checkout Disabled Banner
 *
 * Shown when the checkout_disabled feature flag is enabled.
 * Polls the public checkout-status endpoint and displays a warning
 * banner to inform customers that checkout is temporarily unavailable.
 *
 * This is used during incidents where payment processing is broken —
 * customers see a clear message instead of mysterious payment failures.
 */

interface CheckoutStatus {
  disabled: boolean;
  message?: string;
}

export default function CheckoutDisabledBanner() {
  const [status, setStatus] = useState<CheckoutStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const result = await api.getCheckoutStatus();
        if (result.data) {
          setStatus(result.data);
        }
      } catch (error) {
        // Silently fail — don't show banner if we can't check status
        console.error('Failed to check checkout status:', error);
      } finally {
        setLoading(false);
      }
    };

    checkStatus();

    // Poll every 60 seconds to stay in sync
    const interval = setInterval(checkStatus, 60000);
    return () => clearInterval(interval);
  }, []);

  // Don't show if loading, not disabled, or dismissed
  if (loading || !status || !status.disabled || dismissed) {
    return null;
  }

  return (
    <div className="relative bg-amber-500/10 border-b border-amber-500/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {/* Warning icon */}
            <svg
              className="w-5 h-5 text-amber-500 flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>

            {/* Message */}
            <p className="text-sm text-amber-700 dark:text-amber-300 truncate">
              <span className="font-medium">Checkout temporarily disabled.</span>{' '}
              <span className="hidden sm:inline">
                {status.message || 'Please contact support or try again later.'}
              </span>
              <span className="sm:hidden">Contact support for help.</span>
            </p>
          </div>

          {/* Dismiss button */}
          <button
            onClick={() => setDismissed(true)}
            className="p-1 text-amber-600 hover:text-amber-800 dark:hover:text-amber-400 transition-colors flex-shrink-0"
            aria-label="Dismiss"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
