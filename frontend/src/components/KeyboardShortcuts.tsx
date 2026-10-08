'use client';

import { useEffect, useState, useCallback } from 'react';

interface KeyboardShortcutsProps {
  onOpenHelp: () => void;
}

const keyToPath: Record<string, string> = {
  'g d': '/admin/dashboard',
  'g o': '/admin/orders',
  'g c': '/admin/customers',
  'g p': '/admin/plans',
  'g a': '/admin/analytics',
  'g s': '/admin/settings',
  'g t': '/admin/team',
  'g b': '/admin/blog',
  'g e': '/admin/escalations',
  'g u': '/admin/support',
  'g r': '/admin/audit-log',
  'g v': '/admin/secrets',
  'g n': '/admin/permissions',
  'g l': '/admin/rls',
  'g f': '/admin/profile',
};

export default function KeyboardShortcuts({ onOpenHelp }: KeyboardShortcutsProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!mounted) return;

    const target = e.target as HTMLElement;
    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT' || target.isContentEditable;
    if (isInput) return;

    if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      onOpenHelp();
      return;
    }

    if (e.key !== 'g' || e.ctrlKey || e.metaKey || e.altKey) return;

    e.preventDefault();

    const handleSecondKey = (ev: KeyboardEvent) => {
      document.removeEventListener('keydown', handleSecondKey);

      const combo = `g ${ev.key.toLowerCase()}`;
      const path = keyToPath[combo];

      if (path) {
        ev.preventDefault();
        window.location.href = path;
      }
    };

    document.addEventListener('keydown', handleSecondKey);
  }, [mounted, onOpenHelp]);

  useEffect(() => {
    if (!mounted) return;

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [mounted, handleKeyDown]);

  return null;
}
