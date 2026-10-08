'use client';

import dynamic from 'next/dynamic';

const ConsentGate = dynamic(() => import('@/components/ConsentGate'), { ssr: false });

export default function ConsentGateWrapper() {
  return <ConsentGate />;
}
