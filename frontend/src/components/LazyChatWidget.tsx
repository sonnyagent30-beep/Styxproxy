'use client';

import { lazy, Suspense, useEffect, useState } from 'react';
import { ChatWidgetSkeleton } from '@/components/skeletons/ChatWidgetSkeleton';

// Lazy load ChatWidget to reduce initial bundle
const ChatWidget = lazy(() => import('@/components/ChatWidget'));

export function LazyChatWidget() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    // Delay loading to prioritize above-the-fold content
    const timer = setTimeout(() => setShow(true), 1500);
    return () => clearTimeout(timer);
  }, []);

  if (!show) return <ChatWidgetSkeleton />;

  return (
    <Suspense fallback={<ChatWidgetSkeleton />}>
      <ChatWidget />
    </Suspense>
  );
}
