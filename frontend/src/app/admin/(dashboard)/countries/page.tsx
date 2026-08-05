'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function CountriesRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/admin/plans?tab=countries');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-[var(--muted)]">Redirecting...</div>
    </div>
  );
}
