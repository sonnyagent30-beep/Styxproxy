'use client';

import dynamic from 'next/dynamic';

const ToastProvider = dynamic(() => import('@/components/Toast').then(mod => mod.ToastProvider), { ssr: false });

export default function ToastProviderWrapper({ children }: { children: React.ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}
