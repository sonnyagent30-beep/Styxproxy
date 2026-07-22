'use client';

import { useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import type { AdminMeResponse } from '@/types';

interface AdminLayoutProps {
  children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [admin, setAdmin] = useState<AdminMeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Pages that don't require auth — render empty (no nav shell)
  // `/admin/login` is always public.
  // `/admin/setup` is only public when the system actually needs setup
  // (no admin exists yet). Once an admin exists, the setup page itself
  // redirects to /admin/login via checkSetupStatus().
  const alwaysPublicAdminPages = ['/admin/login'];
  const [setupRequired, setSetupRequired] = useState<boolean | null>(null);

  useEffect(() => {
    const isPublic = (path: string) =>
      alwaysPublicAdminPages.some((p) => path?.startsWith(p)) ||
      (path?.startsWith('/admin/setup') && setupRequired === true);

    if (alwaysPublicAdminPages.some((p) => pathname?.startsWith(p))) {
      setLoading(false);
      return;
    }

    // /admin/setup: check if setup is required (no admin exists yet)
    if (pathname?.startsWith('/admin/setup')) {
      checkSetupRequired();
      return;
    }

    // Protected pages: full auth check
    setLoading(true);
    checkAuth();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, setupRequired]);

  const checkSetupRequired = async () => {
    const result = await api.checkAdminSetupStatus();
    if (result.data?.setup_required === true) {
      // No admin yet — allow setup page to render
      setSetupRequired(true);
      setLoading(false);
    } else {
      // Admin exists — redirect to login
      router.push('/admin/login');
    }
  };

  const checkAuth = async () => {
    const token = api.getAdminToken();
    if (!token) {
      router.push('/admin/login');
      return;
    }

    const result = await api.getAdminMe();
    if (result.error) {
      api.setAdminToken(null);
      router.push('/admin/login');
      return;
    }

    setAdmin(result.data || null);
    setLoading(false);
  };

  const handleLogout = async () => {
    await api.adminLogout();
    api.setAdminToken(null);
    router.push('/admin/login');
  };

  const isSuperAdmin = admin?.role === 'superadmin';

  const navItems = [
    { href: '/admin/dashboard', label: 'Dashboard', icon: '📊' },
    { href: '/admin/orders', label: 'Orders', icon: '📦' },
    { href: '/admin/customers', label: 'Customers', icon: '👥' },
    { href: '/admin/credentials', label: 'Credentials', icon: '🔑' },
    { href: '/admin/plans', label: 'Plans', icon: '💰' },
    { href: '/admin/contact-submissions', label: 'Contact', icon: '📨' },
    { href: '/admin/escalations', label: 'Escalations', icon: '⚡' },
    { href: '/admin/charon', label: 'Charon', icon: '🧠' },
    { href: '/admin/support', label: 'Support', icon: '✉️' },
    { href: '/admin/blog', label: 'Blog', icon: '📝' },
    // SuperAdmin only
    ...(isSuperAdmin
      ? [
          { href: '/admin/team', label: 'Team', icon: '👤' },
          { href: '/admin/features', label: 'Features', icon: '⚙️' },
        ]
      : []),
  ];

  // ── Public pages: no nav shell ──────────────────────────────────────────────
  const isPublicPage =
    alwaysPublicAdminPages.some((p) => pathname?.startsWith(p)) ||
    (pathname?.startsWith('/admin/setup') && setupRequired === true);

  if (loading && !isPublicPage) {
    return (
      <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </div>
    );
  }

  // Still loading auth check on protected pages — show spinner only
  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </div>
    );
  }

  // ── Public pages after loading: plain page, no nav ─────────────────────────
  if (isPublicPage) {
    return <>{children}</>;
  }

  // ── Protected pages: full nav shell ────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-[var(--card)] border-b border-[var(--border)] flex items-center justify-between px-4 z-50">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-[var(--card-hover)] rounded-lg"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="font-bold">Styxproxy Admin</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-[var(--muted)]">{admin?.role}</span>
          <button
            onClick={handleLogout}
            className="p-2 text-[var(--muted)] hover:text-[var(--foreground)]"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </header>

      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col fixed left-0 top-0 bottom-0 w-64 bg-[var(--card)] border-r border-[var(--border)] z-40">
        <div className="h-16 flex items-center px-6 border-b border-[var(--border)]">
          <Link href="/admin/dashboard" className="text-xl font-bold">
            Styxproxy <span className="gradient-text">Admin</span>
          </Link>
        </div>
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
                  isActive
                    ? 'bg-[var(--primary)]/10 text-[var(--primary)]'
                    : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-hover)]'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-[var(--border)]">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-sm">{admin?.email}</p>
              <p className="text-xs text-[var(--muted)] capitalize">{admin?.role}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 text-[var(--muted)] hover:text-red-400 transition-colors"
              title="Logout"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Mobile Sidebar */}
      <aside
        className={`lg:hidden fixed left-0 top-16 bottom-0 w-64 bg-[var(--card)] border-r border-[var(--border)] z-50 transform transition-transform ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
                  isActive
                    ? 'bg-[var(--primary)]/10 text-[var(--primary)]'
                    : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-hover)]'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="lg:ml-64 pt-16 lg:pt-0 min-h-screen">
        <div className="p-4 lg:p-8">{children}</div>
      </main>
    </div>
  );
}
