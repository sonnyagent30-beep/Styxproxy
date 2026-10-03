import { redirect } from 'next/navigation';
import { Suspense } from 'react';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Manage Order',
  description: 'Look up your order status and proxy credentials by order ID or transaction reference.',
  alternates: { canonical: 'https://styxproxy.com/manage' },
};

export default function ManagePage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="text-[var(--muted)]">Loading...</div></div>}>
      <ManageRedirectInner searchParams={searchParams} />
    </Suspense>
  );
}

async function ManageRedirectInner({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const ref = params.ref || params.order_id || '';
  const query = ref ? `?order_id=${encodeURIComponent(ref)}` : '';
  redirect(`/order/status${query}`);
}
