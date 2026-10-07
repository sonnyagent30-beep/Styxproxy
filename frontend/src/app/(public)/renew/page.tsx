import { Suspense } from 'react';
import type { Metadata } from 'next';
import RenewalClient from './RenewalClient';

export const metadata: Metadata = {
  title: 'Renew Proxy',
  description: 'Renew your proxy subscription — add more data or extend your expiry.',
  alternates: { canonical: 'https://styxproxy.com/renew' },
};

export default function RenewPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="text-[var(--muted)]">Loading...</div></div>}>
      <RenewalClient />
    </Suspense>
  );
}
