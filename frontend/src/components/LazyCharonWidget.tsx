'use client';

import { lazy, Suspense, useEffect, useState } from 'react';

const CharonWidget = lazy(() => import('@/components/CharonWidget'));

export function LazyCharonWidget() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShow(true), 1500);
    return () => clearTimeout(timer);
  }, []);

  if (!show) return null;

  return (
    <Suspense fallback={null}>
      <CharonWidget />
    </Suspense>
  );
}
