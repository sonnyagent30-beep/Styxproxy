'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function PlanSettingsPage() {
  const router = useRouter();

  useEffect(() => {
    // This route is deprecated — consolidated into /admin/plans
    router.replace('/admin/plans');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
