'use client';

import { useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import type { AdminMeResponse } from '@/types';

export default function AdminDashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [admin, setAdmin] = useState<AdminMeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [headerSearch, setHeaderSearch] = useState('');

  // Only run auth check ONCE on mount, not on every pathname change
  useEffect(() => {
    checkAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkAuth = async () => {
    const token = api.getAdminToken();
    if (!token) {
      router.push('/admin/login');
      return;
    }
    try {
      const result = await api.getAdminMe();
      if (result.error || !result.data) {
        // Only redirect if the token is actually invalid (401), not on network errors
        if (result.error?.toLowerCase().includes('authorization') ||
            result.error?.toLowerCase().includes('unauthorized') ||
            result.error?.toLowerCase().includes('401')) {
          api.setAdminToken(null);
          router.push('/admin/login');
        } else {
          // Network/server error — show what's available but don't kick them out
          console.error('Failed to fetch admin info:', result.error);
          setLoading(false);
        }
        return;
      }
      setAdmin(result.data);
      setLoading(false);
    } catch (err) {
      // Don't kick user out on network blip — log and stop loading
      console.error('Auth check failed:', err);
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await api.adminLogout();
    api.setAdminToken(null);
    router.push('/admin/login');
  };

  const handleHeaderSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (headerSearch.trim()) {
      router.push(`/admin/search?q=${encodeURIComponent(headerSearch.trim())}`);
    }
  };

  const isSuperAdmin = admin?.role === 'superadmin';

  const navItems = [
    { href: '/admin/dashboard', label: 'Dashboard', icon: '📊' },
    { href: '/admin/orders', label: 'Orders', icon: '📦' },
    { href: '/admin/customers', label: 'Customers', icon: '👥' },
    { href: '/admin/credentials', label: 'Credentials', icon: '🔑' },
    { href: '/admin/plans', label: 'Plans', icon: '💰' },
    { href: '/admin/charon', label: 'Charon', icon: '🧠' },
    { href: '/admin/charon/eval', label: 'Charon Eval', icon: '✅' },
    { href: '/admin/escalations', label: 'Escalations', icon: '🚨' },
    { href: '/admin/support', label: 'Support', icon: '✉️' },
    { href: '/admin/blog', label: 'Blog', icon: '📝' },
    ...(isSuperAdmin ? [
      { href: '/admin/admins', label: 'Admins', icon: '🛡️' },
      { href: '/admin/team', label: 'Team', icon: '👤' },
      { href: '/admin/audit-log', label: 'Audit', icon: '🔍' },
      { href: '/admin/providers', label: 'Providers', icon: '🌐' },
      { href: '/admin/settings', label: 'Settings', icon: '⚙️' },
    ] : []),
    { href: '/admin/profile', label: 'Profile', icon: '🔐' },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-[var(--card)] border-b border-[var(--border)] flex items-center justify-between px-4 z-50">
        <div className="flex items-center gap-3">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 hover:bg-[var(--card-hover)] rounded-lg">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="font-bold">Styxproxy Admin</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-[var(--muted)]">{admin?.role}</span>
          <button onClick={handleLogout} className="p-2 text-[var(--muted)] hover:text-[var(--foreground)]">
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
        
        {/* Global Search */}
        <div className="p-4 border-b border-[var(--border)]">
          <form onSubmit={handleHeaderSearch}>
            <div className="relative">
              <input
                type="text"
                value={headerSearch}
                onChange={(e) => setHeaderSearch(e.target.value)}
                placeholder="Search..."
                className="w-full px-3 py-2 pl-9 text-sm rounded-lg bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)] text-[var(--foreground)] placeholder:text-[var(--muted)]"
              />
              <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </form>
        </div>
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <Link key={item.href} href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
                  isActive ? 'bg-[var(--primary)]/10 text-[var(--primary)]' : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-hover)]'
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
              <p className="font-medium text-sm truncate" title={admin?.email}>{admin?.email}</p>
              <p className="text-xs text-[var(--muted)] capitalize">{admin?.role}</p>
            </div>
            <button onClick={handleLogout} className="p-2 text-[var(--muted)] hover:text-red-400 transition-colors" title="Logout">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 bg-black/50 z-40" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Mobile Sidebar */}
      <aside className={`lg:hidden fixed left-0 top-16 bottom-0 w-64 bg-[var(--card)] border-r border-[var(--border)] z-50 transform transition-transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <Link key={item.href} href={item.href} onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
                  isActive ? 'bg-[var(--primary)]/10 text-[var(--primary)]' : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-hover)]'
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
