'use client';

import dynamic from 'next/dynamic';

// NOTE: no `ssr: false` here. This component wraps {children} in app/layout.tsx,
// and `ssr: false` on a wrapper of the whole tree forces every route to bail out
// to client-side rendering (BAILOUT_TO_CLIENT_SIDE_RENDERING) — which is why the
// server-rendered <h1>/<h2> never reached the HTML and crawlers saw an empty
// shell. A React context provider renders fine on the server; Toast.tsx uses no
// browser APIs at module scope, so it is safe to render there.
//
// dynamic() is kept purely so the toast bundle stays out of the critical path;
// it now renders on the server as well as the client.
const ToastProvider = dynamic(() => import('@/components/Toast').then(mod => mod.ToastProvider));

export default function ToastProviderWrapper({ children }: { children: React.ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}
