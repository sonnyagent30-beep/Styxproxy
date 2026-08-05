'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function PlanSettingsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/admin/plans');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-[var(--muted)]">Redirecting...</div>
    </div>
  );
}
