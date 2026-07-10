'use client';

import { useEffect, useState } from 'react';

export default function ConsentGate() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const accepted = sessionStorage.getItem('styxproxy_consent');
    if (!accepted) {
      // Delay popup by 5 seconds so user gets a glimpse of the platform
      const timer = setTimeout(() => setVisible(true), 5000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    sessionStorage.setItem('styxproxy_consent', '1');
    setVisible(false);
  };

  const handleLeave = () => {
    window.location.href = 'https://www.google.com';
  };

  if (!visible) return null;

  return (
    <>
      {/* Blur overlay */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 99998,
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          background: 'rgba(0, 0, 0, 0.3)',
        }}
      />

      {/* Modal */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 99999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1rem',
        }}
      >
        <div
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: '1.5rem',
            padding: '2.5rem',
            maxWidth: '460px',
            width: '100%',
            boxShadow: '0 25px 60px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.05)',
          }}
        >
          {/* Logo + name */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', marginBottom: '1.75rem' }}>
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '50%',
                background: 'var(--primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <span style={{ color: '#000', fontSize: '1.1rem', fontWeight: 800 }}>S</span>
            </div>
            <div>
              <p style={{ color: 'var(--foreground)', fontWeight: 700, fontSize: '1rem', lineHeight: 1.2 }}>
                Styxproxy
              </p>
              <p style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>
                Anonymous Proxy Service
              </p>
            </div>
          </div>

          {/* Divider */}
          <div style={{ height: '1px', background: 'var(--border)', marginBottom: '1.5rem' }} />

          {/* Text */}
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem', lineHeight: 1.7, marginBottom: '1.25rem' }}>
            Before you continue, please read and accept our terms. By entering Styxproxy you agree to:
          </p>

          {/* Legal links */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '2rem' }}>
            {[
              { label: 'Terms of Service', href: '/legal/terms' },
              { label: 'Refund Policy', href: '/refund-policy' },
              { label: 'Privacy Policy', href: '/legal/privacy' },
              { label: 'Acceptable Use Policy', href: '/legal/aup' },
            ].map(({ label, href }) => (
              <a
                key={href}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: 'var(--foreground)',
                  fontSize: '0.875rem',
                  textDecoration: 'none',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border)',
                  background: 'var(--background)',
                  transition: 'border-color 0.15s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--primary)')}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
              >
                <span>{label}</span>
                <svg style={{ width: '14px', height: '14px', color: 'var(--muted)', flexShrink: 0 }} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                </svg>
              </a>
            ))}
          </div>

          {/* Buttons */}
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              onClick={handleAccept}
              style={{
                flex: 1,
                padding: '0.875rem',
                background: 'var(--primary)',
                color: '#000',
                fontWeight: 700,
                fontSize: '0.9rem',
                border: 'none',
                borderRadius: '0.75rem',
                cursor: 'pointer',
                transition: 'opacity 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
            >
              Accept & Enter
            </button>

            <button
              onClick={handleLeave}
              style={{
                flex: 1,
                padding: '0.875rem',
                background: 'transparent',
                color: 'var(--muted)',
                fontWeight: 600,
                fontSize: '0.9rem',
                border: '1px solid var(--border)',
                borderRadius: '0.75rem',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#444';
                e.currentTarget.style.color = 'var(--foreground)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.color = 'var(--muted)';
              }}
            >
              Leave Site
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
