'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AdminPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to dashboard
    router.replace('/admin/dashboard');
  }, [router]);

  return (
    <div className="min-h-screen pt-24 flex items-center justify-center">
      <div className="animate-pulse text-[var(--muted)]">Loading...</div>
    </div>
  );
}
